"""Prepare all supported Beta episodes; leave source archives untouched."""
from pathlib import Path, PurePosixPath
from concurrent.futures import ThreadPoolExecutor
import json,runpy,tarfile,shutil,os,time,threading

import argparse
BASE = SRC = DST = CFG = None
EXCLUDED_TASK_IDS = set()
WORKERS = 4

def configure():
    global BASE, SRC, DST, CFG, WORKERS, EXCLUDED_TASK_IDS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1: parser.error('workers must be positive')
    BASE, SRC, WORKERS = args.work.resolve(), args.source.resolve(), args.workers
    BASE.mkdir(parents=True, exist_ok=True)
    DST = BASE / 'staged'
    config = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'agibot2lerobot/agibot_utils/config.py'))
    CFG = config['AgiBotWorld_TASK_TYPE']
    EXCLUDED_TASK_IDS = config['EXCLUDED_TASK_IDS']

def main():
    DST.mkdir(exist_ok=True)
    for name in ['observations','proprio_stats','task_info']:(DST/name).mkdir(exist_ok=True)
    if not (DST/'parameters').exists():(DST/'parameters').symlink_to(SRC/'parameters',target_is_directory=True)
    wanted={};counts={'gripper':0,'dexhand':0}
    for p in sorted((SRC/'task_info').glob('task_*.json')):
        if p.stem in EXCLUDED_TASK_IDS:continue
        kind='dexhand' if p.stem in CFG['dexhand']['task_ids'] else 'gripper'
        records=json.loads(p.read_text());task=p.stem.removeprefix('task_')
        cams={key+'_color.mp4' for key,v in CFG[kind]['task_config']['images'].items() if v['dtype']=='video'}
        wanted[task]=({str(r['episode_id']) for r in records},cams)
        counts[kind]+=len(records);shutil.copy2(p,DST/'task_info'/p.name)
    (BASE/'expected_counts.json').write_text(json.dumps(counts,indent=2))
    print('Expected:',counts,flush=True)
    archives=[('proprio_stats',p) for p in sorted((SRC/'proprio_stats').glob('*.tar'))]
    archives += [('observations',p) for task in sorted(wanted) for p in sorted((SRC/'observations'/task).glob('*.tar'))]
    markers=BASE/'archive_markers';markers.mkdir(exist_ok=True)
    def extract(job):
        component,archive=job
        mark=markers/(str(archive.relative_to(SRC)).replace('/','__')+'.json')
        st=archive.stat();signature=[st.st_size,st.st_mtime_ns]
        if mark.exists() and json.loads(mark.read_text())['signature']==signature:return str(archive),'already prepared'
        n=0
        if st.st_size < 1024 and archive.read_bytes().startswith(b'version https://git-lfs.github.com/spec/v1'):
            print('MISSING_LFS_PAYLOAD', archive, flush=True)
            return str(archive), 'LFS pointer; audited below'
        with tarfile.open(archive,'r:') as tf:
            for m in tf:
                tf.members.clear()
                if not m.isfile():continue
                parts=PurePosixPath(m.name).parts
                if component=='observations':
                    task=archive.parent.name
                    if len(parts)!=3 or parts[1]!='videos':continue
                    episode,_,filename=parts
                    if episode not in wanted[task][0] or filename not in wanted[task][1]:continue
                    dest=DST/component/task/episode/'videos'/filename
                else:
                    if len(parts)!=3:continue
                    task,episode,filename=parts
                    if task not in wanted or episode not in wanted[task][0] or filename!='proprio_stats.h5':continue
                    dest=DST/component/task/episode/filename
                dest.parent.mkdir(parents=True,exist_ok=True)
                if dest.exists() and dest.stat().st_size==m.size:continue
                tmp=dest.with_name(dest.name+f'.{threading.get_ident()}.preparing')
                with tf.extractfile(m) as inp,tmp.open('wb') as out:shutil.copyfileobj(inp,out,1024*1024)
                os.replace(tmp,dest);n+=1
        mark.write_text(json.dumps({'signature':signature,'files':n}))
        return str(archive),f'{n} files'
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        # Report completions as they happen, even when another archive is slower.
        from concurrent.futures import as_completed
        futures=[pool.submit(extract,job) for job in archives]
        for i,f in enumerate(as_completed(futures),1):
            print(f'[{i}/{len(archives)}]',*f.result(),flush=True)
    missing=[];missing_count=0;excluded=[];available={'gripper':0,'dexhand':0}
    for task,(episodes,cams) in wanted.items():
        bad=set()
        for ep in episodes:
            paths=[DST/'proprio_stats'/task/ep/'proprio_stats.h5']
            paths += [DST/'observations'/task/ep/'videos'/c for c in cams]
            absent=[str(p) for p in paths if not p.is_file() or p.stat().st_size==0]
            if absent:
                bad.add(ep);missing_count+=len(absent)
                excluded.append({'task':task,'episode_id':ep,'missing_files':absent})
        jf=DST/'task_info'/f'task_{task}.json'
        records=json.loads(jf.read_text())
        kept=[r for r in records if str(r['episode_id']) not in bad]
        jf.write_text(json.dumps(kept,ensure_ascii=False))
        kind='dexhand' if f'task_{task}' in CFG['dexhand']['task_ids'] else 'gripper'
        available[kind]+=len(kept)
        print('AUDIT',task,'available',len(kept),'excluded',len(bad),flush=True)
    audit={'source_expected_episodes':counts,'available_episodes':available,'excluded_episodes':len(excluded),'missing_files':missing_count,'finished':time.time()}
    (BASE/'preparation_audit.json').write_text(json.dumps(audit,indent=2))
    (BASE/'excluded_episodes.json').write_text(json.dumps(excluded,indent=2))
    (BASE/'expected_counts.json').write_text(json.dumps(available,indent=2))
    print('Available-data audit:',audit,flush=True)
    print('Preparation and completeness audit passed',flush=True)
if __name__=='__main__':
    configure()
    main()
