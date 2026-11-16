"""Lossless-video InternData A1 -> unified LeRobot v3 converter."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,copy,json,shutil,time
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from lerobot.datasets.compute_stats import get_feature_stats, aggregate_stats

DEFAULT={'timestamp','frame_index','episode_index','index','task_index'}

def dump(p,obj):
    def default(v):
        if isinstance(v,np.ndarray):return v.tolist()
        if isinstance(v,np.generic):return v.item()
        raise TypeError(type(v))
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=default)+'\n')

def schema(info):
    src=info['features'];spec={};features={}
    def add(key,kind,columns,names,description):
        spec[key]=(kind,columns)
        features[key]={'dtype':'float32','shape':[len(names)],'names':{'motors':names},'description':description+' Source: '+', '.join(columns)+'.'}
    arms=2 if any('left_joint' in k for k in src) or 'states.effector.position' in src or 'observation.state' in src else 1
    for prefix,original in [('state','states'),('action','actions')]:
        if f'{original}.left_joint.position' in src:
            cols=[f'{original}.{s}_{part}.position' for s in ['left','right'] for part in ['joint','gripper']];kind='concat'
        elif f'{original}.effector.position' in src:
            cols=[f'{original}.joint.position',f'{original}.effector.position'];kind='a2d'
        elif ('observation.state' if prefix=='state' else 'action') in src:
            cols=['observation.state' if prefix=='state' else 'action'];kind='concat'
        else:cols=[f'{original}.joint.position',f'{original}.gripper.position'];kind='concat'
        for k in cols:
            if k not in src:raise ValueError(f'Missing required {k}')
        names=[]
        for k in cols:
            n=src[k].get('names');n=n.get('motors') if isinstance(n,dict) else n
            names += n if isinstance(n,list) and len(n)==src[k]['shape'][0] else [f'{k}[{i}]' for i in range(src[k]['shape'][0])]
        if kind=='a2d':
            assert src[cols[0]]['shape']==[14] and src[cols[1]]['shape']==[2]
            names=names[:7]+[names[14]]+names[7:14]+[names[15]]
        add(prefix+'.qpos',kind,cols,names,'Source-native joint/effector positions, ordered left arm + left effector + right arm + right effector for bimanual robots; no unit conversion or normalization.')
        if prefix=='action':add('action.qpos_valid','qvalid',[],['left','right'] if arms==2 else ['arm'],'Per-arm finite action target validity; invalid arms are zero-filled.')
        poses=[f'{original}.{s}ee_to_robot_pose' for s in (['left_','right_'] if arms==2 else [''])]
        present=[p in src for p in poses]
        if any(present) and not all(present):raise ValueError(f'Incomplete bimanual pose fields: {poses}')
        if all(present):
            for p in poses:
                n=src[p].get('names');assert n==['position.x','position.y','position.z','quaternion.w','quaternion.x','quaternion.y','quaternion.z'],(p,n)
        add(prefix+'.ee','pose' if all(present) else 'absent_pose',poses if all(present) else [],[f'{side}.{n}' for side in (['left','right'] if arms==2 else ['arm']) for n in ['x','y','z','qx','qy','qz','qw']], 'End-effector pose in robot frame, source position units preserved; normalized xyzw quaternion. Missing/invalid poses are zero-filled; consult validity mask.')
        add(prefix+'.ee_valid','pose_valid',[],['left','right'] if arms==2 else ['arm'],'Pose validity; 0 marks missing or invalid source pose.')
        waist=f'{original}.waist.position'
        if waist in src:
            n=src[waist].get('names');n=n.get('motors') if isinstance(n,dict) else n
            add(prefix+'.waist','concat',[waist],n or [f'waist_{i}' for i in range(src[waist]['shape'][0])],'Source-native waist position, no unit conversion.')
    cameras={k:'observation.images.'+k.removeprefix('images.rgb.') for k,v in src.items() if v['dtype']=='video'}
    for old,new in cameras.items():features[new]=copy.deepcopy(src[old])
    for k,v in src.items():
        if k in DEFAULT or 'camera_' in k:features[k]=copy.deepcopy(v)
    return spec,features,cameras,arms

def transform(df,spec,features,arms):
    out={};valid={}
    def arr(k):
        # Later physical ARX episodes use split columns instead of packed qpos.
        if k in ['observation.state','action'] and k not in df:
            prefix='states' if k=='observation.state' else 'actions'
            return np.concatenate([np.stack(df[f'{prefix}.{side}_{part}.position'].to_numpy()).astype(np.float32).reshape(len(df),-1) for side in ['left','right'] for part in ['joint','gripper']],axis=1)
        return np.stack(df[k].to_numpy()).astype(np.float32).reshape(len(df),-1)
    for key,(kind,cols) in spec.items():
        prefix=key.split('.')[0]
        if kind in ['concat','a2d']:
            vals=[arr(k) for k in cols]
            if kind=='a2d':a=np.concatenate([vals[0][:,:7],vals[1][:,:1],vals[0][:,7:],vals[1][:,1:]],axis=1)
            else:a=np.concatenate(vals,axis=1)
            if key=='action.qpos':
                assert a.shape[1]%arms==0
                v=np.isfinite(a.reshape(len(a),arms,-1)).all(axis=2);a=a.copy();a.reshape(len(a),arms,-1)[~v]=0;valid['q']=v.astype(np.float32)
            elif not np.isfinite(a).all():raise ValueError(f'Nonfinite required source {key}')
        elif kind in ['pose','absent_pose']:
            a=np.zeros((len(df),arms,7),np.float32);v=np.zeros((len(df),arms),np.float32)
            for i,k in enumerate(cols):
                pose=arr(k)[:,[0,1,2,4,5,6,3]];norm=np.linalg.norm(pose[:,3:],axis=1);ok=np.isfinite(pose).all(axis=1)&(norm>1e-8)
                pose[~ok]=0;pose[ok,3:]/=norm[ok,None];a[:,i]=pose;v[:,i]=ok
            a=a.reshape(len(df),arms*7);valid[prefix]=v
        elif kind=='qvalid':a=valid['q']
        else:a=valid[prefix]
        assert a.shape==(len(df),features[key]['shape'][0]),(key,a.shape,features[key]['shape'])
        out[key]=a
    for k in features:
        if k in df and k not in out:out[k]=np.asarray(df[k].tolist()) if features[k]['dtype']!='video' else df[k].to_numpy()
    return out

def stats(arrays):
    return {k:get_feature_stats(v,axis=0,keepdims=v.ndim==1) for k,v in arrays.items()}

def convert_root(source,output,workers=8,limit=0):
    source,output=Path(source),Path(output);start=time.monotonic()
    if output.exists():raise FileExistsError(output)
    info=json.loads((source/'meta/info.json').read_text());original_info=copy.deepcopy(info);spec,features,cameras,arms=schema(info)
    v3=info['codebase_version'].startswith('v3');output.mkdir(parents=True)
    if v3:
        source_episodes=pd.concat([pq.read_table(p).to_pandas() for p in sorted((source/'meta/episodes').rglob('*.parquet'))],ignore_index=True)
        pairs=sorted(set(zip(source_episodes['data/chunk_index'],source_episodes['data/file_index'])))
        files=[source/info['data_path'].format(chunk_index=int(c),file_index=int(f)) for c,f in pairs]
        allowed_episodes=set(int(e) for e in source_episodes['episode_index'])
    else:
        records=[json.loads(x) for x in (source/'meta/episodes.jsonl').read_text().splitlines() if x]
        available={str(p.relative_to(source)) for p in (source/'data').rglob('*.parquet')}
        available_videos={str(p.relative_to(source)) for p in (source/'videos').rglob('*.mp4')}
        accepted=[];excluded=[];files=[]
        for rec in records:
            eid=int(rec['episode_index']);rel=info['data_path'].format(episode_chunk=eid//info['chunks_size'],episode_index=eid)
            missing=[] if rel in available else [rel]
            for key in cameras:
                vr=info['video_path'].format(episode_chunk=eid//info['chunks_size'],episode_index=eid,video_key=key)
                if vr not in available_videos:missing.append(vr)
            if missing:excluded.append({'source_episode_index':eid,'missing':missing});continue
            accepted.append(rec);files.append(source/rel)
        if limit:files=files[:limit]
        records=accepted[:limit] if limit else accepted;source_to_new={int(r['episode_index']):i for i,r in enumerate(records)}
        allowed_episodes=set(source_to_new);offsets=np.cumsum([0]+[int(r['length']) for r in records])
        task_names=list(dict.fromkeys(r['tasks'][0] for r in records));task_map={t:i for i,t in enumerate(task_names)}
        assert all(len(r['tasks'])==1 for r in records)
        dump(output/'meta/source_issues.json',{'declared_episodes':info['total_episodes'],'available_episodes':len(records),'excluded':excluded,'repair':'Rebuild frame/episode/task indices from per-episode manifest and file names.'})
        info=copy.deepcopy(info);info.update(total_episodes=len(records),total_frames=int(offsets[-1]),total_tasks=len(task_names),splits={'train':f'0:{len(records)}'})
    assert len(allowed_episodes)==info['total_episodes']
    assert files,'No data Parquet files'
    counts=[];ep_stats={};ep_locations={}
    def data_job(item):
        file_index,p=item;rel=p.relative_to(source) if v3 else Path(f'data/chunk-{file_index//1000:03d}/file-{file_index%1000:03d}.parquet')
        dest=output/rel;dest.parent.mkdir(parents=True,exist_ok=True);reader=pq.ParquetFile(p);writer=None;results={};locations={};rows=0
        try:
            batches=(reader.read_row_group(rg) for rg in range(reader.num_row_groups)) if v3 else [reader.read()]
            for batch in batches:
                frame=batch.to_pandas()
                if not v3:
                    assert len(frame)==records[file_index]['length'],(p,len(frame),records[file_index]['length'])
                    frame['episode_index']=file_index
                    frame['index']=np.arange(offsets[file_index],offsets[file_index+1],dtype=np.int64)
                    frame['frame_index']=np.arange(len(frame),dtype=np.int64)
                    frame['task_index']=task_map[records[file_index]['tasks'][0]]
                for eid,df in frame.groupby('episode_index',sort=False):
                    arrays=transform(df,spec,features,arms);columns={}
                    for k,a in arrays.items():
                        if a.ndim>1 and a.shape[1:]==(1,):columns[k]=pa.array(a[:,0],type=pa.float32())
                        elif a.ndim>1:columns[k]=pa.array(a.tolist(),type=pa.list_(pa.float32()))
                        else:columns[k]=pa.array(a)
                    table=pa.table(columns)
                    if writer is None:writer=pq.ParquetWriter(dest,table.schema,compression='snappy')
                    writer.write_table(table);rows+=len(df)
                    if int(eid) in results:raise ValueError('Source episode spans row groups; requires explicit regrouping')
                    results[int(eid)]=stats(arrays);locations[int(eid)]=(file_index//1000,file_index%1000,int(df['index'].iloc[0]),int(df['index'].iloc[-1])+1)
        finally:
            if writer:writer.close()
        return rows,results,locations
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for rows,st,loc in pool.map(data_job,enumerate(files)):
            assert not (ep_stats.keys() & st.keys()),'Episode spans source files'
            counts.append(rows);ep_stats.update(st);ep_locations.update(loc)
    assert sum(counts)==info['total_frames'];assert len(ep_stats)==info['total_episodes']
    video_jobs=[]
    for old,new in cameras.items():
        for p in (source/'videos').rglob('*.mp4'):
            parts=p.relative_to(source).parts
            if old not in parts:continue
            if v3:rel=Path(*[new if x==old else x for x in parts])
            else:
                eid=int(p.stem.removeprefix('episode_'))
                if eid not in allowed_episodes:continue
                eid=source_to_new[eid]
                rel=Path(f'videos/{new}/chunk-{eid//1000:03d}/file-{eid%1000:03d}.mp4')
            video_jobs.append((p,output/rel))
    def cp(job):
        src,dst=job;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    with ThreadPoolExecutor(max_workers=workers) as pool:list(pool.map(cp,video_jobs))
    (output/'meta').mkdir(exist_ok=True)
    if v3:
        episodes=pd.concat([pq.read_table(p).to_pandas() for p in sorted((source/'meta/episodes').rglob('*.parquet'))],ignore_index=True)
        shutil.copy2(source/'meta/tasks.parquet',output/'meta/tasks.parquet')
    else:
        episodes=pd.DataFrame(records)
        episodes['source_episode_index']=episodes['episode_index'];episodes['episode_index']=np.arange(len(records),dtype=np.int64)
        pd.DataFrame({'task_index':range(len(task_names))},index=pd.Index(task_names,name='task')).to_parquet(output/'meta/tasks.parquet')
        for row in episodes.index:
            eid=int(episodes.at[row,'episode_index']);c,f,startidx,endidx=ep_locations[eid]
            for k,v in {'data/chunk_index':c,'data/file_index':f,'dataset_from_index':startidx,'dataset_to_index':endidx,'meta/episodes/chunk_index':0,'meta/episodes/file_index':0}.items():episodes.at[row,k]=v
            for old,new in cameras.items():
                for k,v in {'chunk_index':eid//1000,'file_index':eid%1000,'from_timestamp':0.0,'to_timestamp':float(episodes.at[row,'length'])/info['fps']}.items():episodes.at[row,f'videos/{old}/{k}']=v
    keep_stats={k for k in features if k not in spec}
    rename={}
    for col in episodes.columns:
        for old,new in cameras.items():
            if col.startswith('videos/'+old+'/') or col.startswith('stats/'+old+'/'):rename[col]=col.replace(old,new,1)
    episodes=episodes.rename(columns=rename)
    episodes=episodes.drop(columns=[k for k in episodes if k.startswith('stats/') and k.split('/')[1] not in keep_stats],errors='ignore')
    new_stats_columns={}
    for key in next(iter(ep_stats.values())):
        for stat in next(iter(ep_stats.values()))[key]:
            new_stats_columns[f'stats/{key}/{stat}']=[np.asarray(ep_stats[int(e)][key][stat]).tolist() for e in episodes['episode_index']]
    episodes=episodes.drop(columns=list(new_stats_columns),errors='ignore')
    episodes=pd.concat([episodes,pd.DataFrame(new_stats_columns,index=episodes.index)],axis=1)
    # Repack episode metadata into one canonical metadata file and update pointers.
    episodes['meta/episodes/chunk_index']=0;episodes['meta/episodes/file_index']=0
    for col in episodes:
        if col.endswith('/chunk_index') or col.endswith('/file_index'):episodes[col]=episodes[col].astype('int64')
    dest=output/'meta/episodes/chunk-000/file-000.parquet';dest.parent.mkdir(parents=True);episodes.to_parquet(dest,index=False)
    total_stats=aggregate_stats(list(ep_stats.values()))
    old_stats=json.loads((source/'meta/stats.json').read_text()) if (source/'meta/stats.json').exists() else {}
    if not v3 and (source/'meta/episodes_stats.jsonl').exists():
        entries=[json.loads(x) for x in (source/'meta/episodes_stats.jsonl').read_text().splitlines() if x]
        ss=[e['stats'] for e in entries if int(e['episode_index']) in allowed_episodes]
        old_stats=aggregate_stats([{k:{a:np.asarray(v) for a,v in st.items()} for k,st in s.items()} for s in ss])
    for old,new in cameras.items():
        if old in old_stats:total_stats[new]=old_stats[old]
    newinfo=copy.deepcopy(info);newinfo.update(codebase_version='v3.0',features=features,data_path='data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet',video_path='videos/{video_key}/chunk-{chunk_index:03d}/file-{file_index:03d}.mp4')
    newinfo.pop('total_chunks',None);newinfo.pop('total_videos',None)
    dump(output/'meta/info.json',newinfo);dump(output/'meta/stats.json',total_stats);dump(output/'meta/source_info.json',original_info)
    summary={'source':str(source),'output':str(output),'episodes':len(ep_stats),'frames':sum(counts),'seconds':time.monotonic()-start,'videos':len(video_jobs),'waist':'state.waist' in features,'status':'complete'}
    dump(output/'meta/conversion.json',summary);return summary

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);p.add_argument('--workers',type=int,default=8);a=p.parse_args();print(json.dumps(convert_root(a.source,a.output,a.workers)),flush=True)
