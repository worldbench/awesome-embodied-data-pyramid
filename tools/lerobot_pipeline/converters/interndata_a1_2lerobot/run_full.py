"""Four independent archive workers, eight I/O/Parquet threads per worker."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import json,os,shutil,tarfile,time,traceback,multiprocessing,fcntl
from convert import convert_root,dump

BASE=Path(os.environ.get('INTERN_WORK','work/interndata'))
SOURCE=Path(os.environ.get('INTERN_SOURCE','raw/InternData-A1'))
OUTPUT=Path(os.environ.get('INTERN_OUTPUT','converted/InternData_A1_v3'))

def run_job(job, selected_roots=None):
    kind,path=job;path=Path(path);start=time.monotonic()
    rel=path.relative_to(SOURCE/'sim_updated_lerobotv30') if kind=='sim' else Path(path.name)
    ident=kind+'__'+str(rel).replace('/','__').removesuffix('.tar.gz')
    marker=BASE/'jobs'/f'{ident}.json'
    if marker.exists():
        previous=json.loads(marker.read_text())
        if previous['status']=='complete':return previous
    stage=BASE/'staged'/ident;partial_outputs=[]
    try:
        if kind=='sim':
            if not (stage/'.extracted').exists():
                if stage.exists():shutil.rmtree(stage)
                stage.mkdir(parents=True)
                with tarfile.open(path,'r|gz') as tf:
                    for member in tf:
                        tf.members.clear()
                        if not (member.isfile() or member.isdir()):raise ValueError(f'Unsupported archive member: {member.name}')
                        tf.extract(member,stage,filter='data')
                (stage/'.extracted').touch()
            roots=sorted(p.parent.parent for p in stage.rglob('meta/info.json'))
            if not roots:raise ValueError('No LeRobot dataset metadata in archive')
        else:roots=[path]
        excluded_roots=[]
        if selected_roots is not None:
            wanted=set(selected_roots)
            selected=[root for root in roots if root.name in wanted]
            if len(selected)!=len(wanted) or {root.name for root in selected}!=wanted:
                raise ValueError(f'Selected source roots changed: {ident}')
            excluded_roots=[str(root.relative_to(stage)) for root in roots if root not in selected]
            roots=selected
        results=[]
        for root in roots:
            dest=OUTPUT/'sim'/rel.parent/root.relative_to(stage) if kind=='sim' else OUTPUT/'physical'/path.name
            if (dest/'meta/conversion.json').exists():
                results.append(json.loads((dest/'meta/conversion.json').read_text()));continue
            if dest.exists():raise FileExistsError(dest)
            partial=dest.with_name(dest.name+'.partial')
            if partial.exists():shutil.rmtree(partial)
            partial_outputs.append(str(partial))
            result=convert_root(root,partial,workers=8)
            # Basic read-back of every final dataset before publishing its directory.
            import pyarrow.parquet as pq
            info=json.loads((partial/'meta/info.json').read_text())
            n=sum(pq.read_metadata(p).num_rows for p in (partial/'data').rglob('*.parquet'))
            if n!=info['total_frames']:raise ValueError('Final frame count mismatch')
            result['output']=str(dest);dump(partial/'meta/conversion.json',result)
            partial.rename(dest);results.append(result)
        report={'job':ident,'source':str(path),'status':'complete','seconds':time.monotonic()-start,'archive_bytes':path.stat().st_size if kind=='sim' else 0,'datasets':results,'excluded_roots':excluded_roots,'episodes':sum(r['episodes'] for r in results),'frames':sum(r['frames'] for r in results)}
        dump(marker,report)
        if kind=='sim':shutil.rmtree(stage)
        return report
    except Exception:
        report={'job':ident,'source':str(path),'status':'failed','seconds':time.monotonic()-start,'error':traceback.format_exc(),'partial_outputs':partial_outputs}
        dump(marker,report);return report

def main():
    global BASE, SOURCE, OUTPUT
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--exclude-job',action='append',default=[])
    parser.add_argument('--job-roots',action='append',default=[],help='Restrict one job: job_id=root1,root2')
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    BASE,SOURCE,OUTPUT=args.work.resolve(),args.source.resolve(),args.output.resolve()
    os.environ.update(INTERN_WORK=str(BASE),INTERN_SOURCE=str(SOURCE),INTERN_OUTPUT=str(OUTPUT))
    BASE.mkdir(parents=True,exist_ok=True);lock=(BASE/'run.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    archives=sorted((SOURCE/'sim_updated_lerobotv30').glob('*/*/*.tar.gz'),key=lambda p:p.stat().st_size)
    physical=sorted(p.parent.parent for p in (SOURCE/'physical').glob('*/meta/info.json'))
    jobs=[('physical',str(p)) for p in physical]+[('sim',str(p)) for p in archives]
    def job_id(job):
        kind,path=job;path=Path(path)
        rel=path.relative_to(SOURCE/'sim_updated_lerobotv30') if kind=='sim' else Path(path.name)
        return kind+'__'+str(rel).replace('/','__').removesuffix('.tar.gz')
    root_filters={}
    for value in args.job_roots:
        key,sep,roots=value.partition('=')
        if not sep or not roots or key in root_filters:raise ValueError(f'Invalid job-roots: {value}')
        root_filters[key]=roots.split(',')
    if set(root_filters)&set(args.exclude_job):raise ValueError('Job cannot be both excluded and selected')
    unknown=(set(args.exclude_job)|set(root_filters))-{job_id(j) for j in jobs}
    if unknown:raise ValueError(f'Unknown exclusions: {unknown}')
    dump(BASE/'explicit_exclusions.json',{'jobs':args.exclude_job,'job_roots':root_filters})
    jobs=[j for j in jobs if job_id(j) not in args.exclude_job]
    if not jobs:raise ValueError('No input jobs')
    dump(BASE/'full_manifest.json' ,{'source_version':'sim_updated_lerobotv30 + physical','archives':len(archives),'archive_bytes':sum(p.stat().st_size for p in archives),'jobs':jobs})
    start=time.time();completed=[]
    dump(BASE/'status.json',{'phase':'running','started':start,'jobs_total':len(jobs),'jobs_done':0,'jobs_failed':0})
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures=[pool.submit(run_job,j,root_filters.get(job_id(j))) for j in jobs]
        for f in as_completed(futures):
            r=f.result();completed.append(r)
            status={'phase':'running','started':start,'elapsed_seconds':time.time()-start,'jobs_total':len(jobs),'jobs_done':len(completed),'jobs_failed':sum(x['status']=='failed' for x in completed),'episodes_done':sum(x.get('episodes',0) for x in completed),'frames_done':sum(x.get('frames',0) for x in completed),'last_job':r['job']}
            status['archive_bytes_done']=sum(x.get('archive_bytes',0) for x in completed)
            dump(BASE/'status.json',status);print(json.dumps(status),flush=True)
            if r['status']=='failed':print(r['error'],flush=True)
    status['phase']='completed_with_errors' if status['jobs_failed'] else 'complete';dump(BASE/'status.json',status)
    if status['jobs_failed']:raise SystemExit(1)
if __name__=='__main__':main()
