"""Aggregate preserved episode datasets by original task_id with resumable publication."""
import os,json,re,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import multiprocessing

def one_group(job):
    task_id,roots,output=job
    from generic_converter.pipeline import aggregate_roots
    output=Path(output); marker=output/'TASK_COMPLETE.json'
    if marker.exists():
        d=json.loads(marker.read_text());assert d['episodes']==len(roots);return d
    partial=output.with_name(output.name+'.inprogress')
    if partial.exists():partial.rename(partial.with_name(partial.name+'.backup_'+str(time.time_ns())))
    assert not output.exists(),f'Unmarked output exists: {output}'
    aggregate_roots(roots,partial,aggr_repo_id='agibot_beta/'+task_id)
    info=json.loads((partial/'meta/info.json').read_text())
    assert info['total_episodes']==len(roots),(task_id,info['total_episodes'],len(roots))
    for key in ['state.waist','action.waist']:assert info['features'][key]['shape']==[2]
    result={'task_id':task_id,'episodes':len(roots),'frames':info['total_frames'],'completed':time.time()}
    (partial/'TASK_COMPLETE.json').write_text(json.dumps(result,indent=2))
    partial.rename(output)
    return result

def aggregate_by_task(roots,output,workers=None):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    groups={}
    for root in roots:
        root=Path(root)
        match=re.fullmatch(r'(task_\d+)_episode_\d+',root.name)
        if not match:raise ValueError(f'Unexpected episode directory: {root}')
        groups.setdefault(match[1],[]).append(str(root))
    jobs=[(task,sorted(rs),str(output/task)) for task,rs in sorted(groups.items())]
    (output/'TASK_MANIFEST.json').write_text(json.dumps({'episodes':len(roots),'tasks':len(jobs),'groups':{k:len(v) for k,v in groups.items()}},indent=2))
    results=[]
    with ProcessPoolExecutor(max_workers=workers or int(os.environ.get('BETA_AGGREGATE_WORKERS','4')),mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(one_group,j) for j in jobs]
        for f in as_completed(futures):
            result=f.result();results.append(result)
            print('TASK_COMPLETED',json.dumps(result),flush=True)
    assert sum(x['episodes'] for x in results)==len(roots)
    (output/'ALL_TASKS_COMPLETE.json').write_text(json.dumps({'episodes':len(roots),'tasks':len(results),'completed':time.time()},indent=2))

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--expected',type=int,required=True);p.add_argument('--workers',type=int,default=4);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    roots=sorted(Path(a.source).iterdir())
    if a.smoke:roots=roots[:2]
    else:assert len(roots)==a.expected,(len(roots),a.expected)
    aggregate_by_task(roots,a.output,a.workers)
