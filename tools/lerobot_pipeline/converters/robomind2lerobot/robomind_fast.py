"""Archive-aware, bounded-memory RoboMIND v1.2 -> LeRobot v3 converter.

Uses the existing embodiment configs/numeric mapping. RGB only, 30 Hz, native
resolution and original color convention. Unknown schemas fail explicitly.
Completed archive checkpoints can be reused with the SAME saved inventory.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED
from collections import defaultdict
import contextlib
import copy
import fcntl
import hashlib
import io
import json
import multiprocessing as mp
import os
from pathlib import Path
import queue
import shutil
import sys
import tarfile
import tempfile
import time
from types import MethodType

from archive_input import PartsReader, inventory, SUPPORTED

VERSION = 'robomind-archive-stream-v1'


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    os.replace(temp, path)


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()[:16]


def source_fingerprint(row):
    return [{'path': p['path'], 'size': (s := Path(p['path']).stat()).st_size,
             'mtime_ns': s.st_mtime_ns} for p in row['parts']]


def record_archive_failure(work, row, error):
    path = Path(work)/'failed_archives.json'
    records = json.loads(path.read_text()) if path.exists() else {}
    records[identity(row)] = {'archive': row, 'error': str(error),
                              'source_fingerprint': source_fingerprint(row), 'updated': time.time()}
    write_json(path, records)
    return records


def pending_archive_rows(work, rows):
    """Defer unchanged failed inputs, but never count them as completed."""
    path = Path(work)/'failed_archives.json'
    recorded = json.loads(path.read_text()) if path.exists() else {}
    pending, deferred = [], {}
    for row in rows:
        key = identity(row)
        failure = recorded.get(key)
        if ((Path(work)/'archives'/key/'COMPLETED.json').exists()
                or failure is None or failure['source_fingerprint'] != source_fingerprint(row)):
            pending.append(row)
        else:
            deferred[key] = failure
    return pending, deferred


def require_all_archives(results, rows, failures):
    if failures or {identity(r['archive']) for r in results} != {identity(r) for r in rows}:
        raise RuntimeError(f'Conversion incomplete: {len(results)}/{len(rows)} archives; '
                           f'{len(failures)} require repair. Final aggregation is blocked.')


def feed_lossless(self, key, frame):
    if not self._episode_active:
        raise RuntimeError('Encoder episode is not active')
    frame = frame.copy()
    while self._threads[key].is_alive():
        try:
            self._frame_queues[key].put(frame, timeout=0.25)
            return
        except queue.Full:
            pass
    raise RuntimeError(f'Encoder failed: {key}')


def decode_one(raw, flip, shape):
    import cv2
    import numpy as np
    if isinstance(raw, bytes):
        raw = np.frombuffer(raw, np.uint8)
    else:
        raw = np.asarray(raw)
    if raw.ndim == 3 and raw.shape[-1] == 3:
        image = raw
    else:
        image = cv2.imdecode(raw.astype(np.uint8, copy=False), cv2.IMREAD_COLOR)
        if image is None and raw.size == int(np.prod(shape)):
            image = raw.reshape(shape)
        if image is None:
            # Legacy archives also contain flat, uncompressed RGB at a
            # resolution different from the embodiment's default config.
            # Match the original converter and preserve native resolution.
            raw_shapes = {921600: (480, 640, 3), 2764800: (720, 1280, 3)}
            if raw.size in raw_shapes:
                image = raw.reshape(raw_shapes[raw.size])
    if image is None or image.ndim != 3 or image.shape[-1] != 3:
        raise ValueError(f'Cannot decode RGB: shape={raw.shape}')
    if flip:
        image = image[..., ::-1]
    return np.ascontiguousarray(image)


def source_split(member_name):
    parts = Path(member_name).parts
    tail = parts[parts.index('success_episodes') + 1:]
    if len(tail) == 4 and tail[-2:] == ('data', 'trajectory.hdf5'):
        if tail[0] in ('train', 'val', 'validation'):
            return 'train' if tail[0] == 'train' else 'validation'
    if len(tail) == 3 and tail[-2:] == ('data', 'trajectory.hdf5'):
        # The source provides no split: keep it separate, never invent train/val.
        return 'unspecified'
    raise ValueError(f'Unrecognized source split: {member_name}')


def select_rgb_keys(expected, available, embodiment, member_name, documented_two_camera):
    expected, available = list(expected), set(available)
    missing = set(expected) - available
    if not missing:
        return expected
    source = str(Path(f'h5_{embodiment}') / member_name)
    if (embodiment == 'franka_3rgb' and source in documented_two_camera
            and missing == {'camera_top'}
            and available == {'camera_left', 'camera_right'}):
        return [k for k in expected if k in available]
    raise ValueError(f'Undocumented missing RGB cameras: {member_name}; '
                     f'missing={sorted(missing)}, available={sorted(available)}')


def scratch_budget(free_bytes, workers, requested_gib):
    # Reserve 2 GiB for the system and avoid overcommitting local disk when
    # increasing workers. Larger HDF5 episodes go to the existing NAS scratch.
    budget = min(requested_gib, (free_bytes / 2**30 - 2) / workers)
    if budget < 0.25:
        raise ValueError('Insufficient scratch space for worker budgets')
    return budget


def worker(row, settings):
    # Heavy imports stay in child processes; each has its own HDF5 handle.
    import av
    import cv2
    import h5py
    import numpy as np
    from lerobot.datasets.lerobot_dataset import LeRobotDataset
    from lerobot.configs.video import RGBEncoderConfig
    from robomind_uitls.configs import ROBOMIND_CONFIG
    from robomind_uitls.lerobot_uitls import generate_features_from_config, remap_numeric_arrays
    cv2.setNumThreads(1)
    av.logging.set_level(av.logging.ERROR)
    started = time.monotonic()
    key = identity(row)
    work = Path(settings['work'])
    job = work / 'archives' / key
    marker = job / 'COMPLETED.json'
    signature = identity({'row': row, 'version': VERSION, 'limit': settings['episodes'],
                          'shard_episodes': settings['shard_episodes'], 'codec': 'h264-crf23-gop2'})
    for part in row['parts']:
        if Path(part['path']).stat().st_size != part['size']:
            raise ValueError(f'Source archive size changed: {part["path"]}')
    if marker.exists():
        saved = json.loads(marker.read_text())
        if saved['signature'] != signature:
            raise ValueError(f'Checkpoint settings changed: {job}')
        for s in saved['shards']:
            if not (Path(s['path']) / 'meta/info.json').is_file():
                raise FileNotFoundError(s['path'])
        return saved
    if job.exists():
        backup = work / 'failed_attempts' / f'{key}-{time.time_ns()}'
        backup.parent.mkdir(parents=True, exist_ok=True)
        job.rename(backup)
    job.mkdir(parents=True)
    scratch = Path(settings['scratch'])
    scratch.mkdir(parents=True, exist_ok=True)
    config = copy.deepcopy(ROBOMIND_CONFIG[row['embodiment']])
    two_camera_file = Path(settings['source'])/'static/franka_3rgb_2cam_paths.md'
    documented_two_camera = set()
    if row['embodiment'] == 'franka_3rgb' and two_camera_file.exists():
        documented_two_camera = {str(Path(line.strip())) for line in two_camera_file.read_text().splitlines() if line.strip()}
    flip = row['embodiment'] in {'franka_1rgb', 'franka_3rgb', 'franka_fr3_dual', 'ur_1rgb'}
    annotation_file = Path(settings['source'])/'static/language_description_annotation_json'/f'h5_{row["embodiment"]}.json'
    annotations = {}
    if annotation_file.exists():
        for a in json.loads(annotation_file.read_text()):
            if row['task'] in a.get('id', ''):
                annotations[Path(a['id']).parent.name] = a.get('response')
    writers, shards = {}, []
    counts = {'saved': 0, 'short': 0, 'frames': 0, 'hdf5_bytes': 0}
    last_progress = 0
    reader = PartsReader([p['path'] for p in row['parts']])

    def progress(force=False):
        nonlocal last_progress
        if force or time.monotonic() - last_progress > 20:
            last_progress = time.monotonic()
            write_json(job/'progress.json', {**counts, 'task': row['task'], 'compressed_bytes_read': reader.bytes_read,
                       'seconds': time.monotonic()-started, 'updated': time.time()})

    def finish(group):
        item = writers.pop(group)
        dataset, records = item['dataset'], item['records']
        dataset.finalize()
        if settings['mode']=='smoke':
            import pyarrow.parquet as pq
            written=[]
            for f in sorted((dataset.root/'data').rglob('*.parquet')):
                written.extend(pq.read_table(f).to_pylist())
            offset=0
            for record in records:
                tail=written[offset:offset+record['frames']]
                for k,digest in record['numeric_sha256'].items():
                    values=np.asarray([r[k] for r in tail],np.float32)
                    if hashlib.sha256(values.tobytes()).hexdigest()!=digest:
                        raise ValueError(f'Numeric round-trip mismatch: {k}')
                offset+=record['frames']
        # Retain split/source/annotation provenance alongside standard LeRobot metadata.
        write_json(dataset.root/'meta/source_episodes.json', records)
        info_path = dataset.root/'meta/info.json'
        info = json.loads(info_path.read_text())
        info['splits'] = {item['split']: f'0:{len(records)}'}
        write_json(info_path, info)
        # Check actual encoded stream counts on every finalized shard. Smoke fully decodes too.
        expected = sum(r['frames'] for r in records)
        for camera in dataset.meta.video_keys:
            actual = 0
            for video in (dataset.root/'videos'/camera).rglob('*.mp4'):
                with av.open(str(video)) as container:
                    actual += (sum(1 for _ in container.decode(video=0))
                               if settings['mode']=='smoke' else container.streams.video[0].frames)
            if actual != expected:
                raise ValueError(f'Frame count mismatch {camera}: {actual} != {expected}')
        shards.append({'path': str(dataset.root), 'group': group, 'frames': expected, 'episodes': len(records)})

    with ThreadPoolExecutor(max_workers=settings['decode_threads']) as decoders:
        with io.BufferedReader(reader, buffer_size=1024*1024) as buffered:
            with tarfile.open(fileobj=buffered, mode='r|gz', bufsize=1024*1024) as archive:
                for member in archive:
                    progress()
                    if not member.isfile() or not member.name.endswith('trajectory.hdf5'):
                        continue
                    parts = Path(member.name).parts
                    if 'success_episodes' not in parts:
                        continue
                    split = source_split(member.name)
                    if member.size > settings['max_hdf5_gib'] * 2**30:
                        raise ValueError(f'HDF5 exceeds scratch budget: {member.name}: {member.size}')
                    episode_scratch = scratch
                    if member.size > settings.get('scratch_budget_gib', settings['local_hdf5_gib']) * 2**30:
                        episode_scratch = work/'large_hdf5_scratch'
                        episode_scratch.mkdir(parents=True,exist_ok=True)
                    if shutil.disk_usage(episode_scratch).free < member.size + 2*2**30:
                        raise RuntimeError('Scratch disk has insufficient free space')
                    with tempfile.TemporaryDirectory(prefix='robomind-', dir=episode_scratch) as tmp:
                        h5_path = Path(tmp)/'trajectory.hdf5'
                        with archive.extractfile(member) as src, h5_path.open('wb') as dst:
                            shutil.copyfileobj(src, dst, 1024*1024)
                        counts['hdf5_bytes'] += member.size
                        with h5py.File(h5_path, 'r') as h5:
                            numeric = {}
                            for section, prefix, source in [('states','state','puppet'), ('actions','action','master')]:
                                arrays = {k: np.asarray(h5[f'{source}/{k}'], np.float32) for k in config[section]}
                                numeric.update(remap_numeric_arrays(arrays, config, section, prefix,
                                               include_action_validity=(section=='actions')))
                            n = len(next(iter(numeric.values())))
                            if n < 50:
                                counts['short'] += 1
                                continue
                            if any(len(a)!=n or not np.isfinite(a).all() for a in numeric.values()):
                                raise ValueError(f'Invalid numeric lengths/values: {member.name}')
                            rgb = h5['observations/rgb_images']
                            keys = select_rgb_keys([k for k in config['images'] if 'depth' not in k],
                                                   rgb.keys(), row['embodiment'], member.name, documented_two_camera)
                            cameras = {k:rgb[k] for k in keys}
                            if any(len(a)!=n for a in cameras.values()):
                                raise ValueError(f'Camera/numeric length mismatch: {member.name}')
                            episode_config = copy.deepcopy(config)
                            episode_config['images'] = {k:v for k,v in episode_config['images'].items()
                                                        if k in cameras or 'depth' in k}
                            first = {k: decode_one(a[0],flip,config['images'][k]['shape']) for k,a in cameras.items()}
                            for k,image in first.items():
                                episode_config['images'][k]['shape'] = image.shape
                            features = {k:v for k,v in generate_features_from_config(episode_config,row['embodiment']).items() if 'depth' not in k}
                            group = f'RoboMIND_v12_{row["benchmark"]}_{row["embodiment"]}_{split}_{identity(features)[:8]}'
                            if group not in writers:
                                root = job/group/f'shard-{len(shards):05d}'
                                dataset = LeRobotDataset.create(repo_id=f'robomind/{group}', root=root,
                                    fps=30, robot_type=row['embodiment'], features=features,
                                    video_backend='pyav', streaming_encoding=True, encoder_queue_maxsize=4,
                                    encoder_threads=settings['encoder_threads'], metadata_buffer_size=1,
                                    rgb_encoder=RGBEncoderConfig(vcodec='h264',preset='veryfast',crf=23,g=2))
                                encoder=dataset.writer._streaming_encoder
                                encoder.feed_frame=MethodType(feed_lossless,encoder)
                                writers[group]={'dataset':dataset,'records':[],'split':split}
                            item=writers[group]; dataset=item['dataset']
                            for i in range(n):
                                jobs={k:decoders.submit(decode_one,a[i],flip,episode_config['images'][k]['shape']) for k,a in cameras.items()}
                                frame={k:a[i] for k,a in numeric.items()}
                                for k, future in jobs.items():
                                    image=future.result()
                                    if image.shape != first[k].shape:
                                        raise ValueError(f'Camera resolution changes within episode: {k}')
                                    frame[f'observation.images.{k}']=image
                                frame['task']=row['instruction']
                                dataset.add_frame(frame)
                                if i % 300 == 0:progress()
                            dataset.save_episode()
                            ep_id=Path(member.name).parent.parent.name
                            item['records'].append({'source':member.name,'split':split,'frames':n,
                                'instruction':row['instruction'],'action_config':annotations.get(ep_id),
                                'source_rgb_cameras':sorted(rgb.keys()), 'output_rgb_cameras':sorted(cameras),
                                'camera_schema_evidence':('static/franka_3rgb_2cam_paths.md'
                                    if len(cameras) < len([k for k in config['images'] if 'depth' not in k]) else 'embodiment_config'),
                                'numeric_sha256':{k:hashlib.sha256(a.tobytes()).hexdigest() for k,a in numeric.items()}})
                            counts['saved']+=1; counts['frames']+=n
                            if len(item['records']) >= settings['shard_episodes']:
                                finish(group)
                            progress(True)
                    if settings['episodes'] and counts['saved'] >= settings['episodes']:
                        break
    for group in list(writers):finish(group)
    result={**counts,'signature':signature,'archive':row,'shards':shards,
            'compressed_bytes_read':reader.bytes_read,'seconds':time.monotonic()-started}
    if not counts['saved']:
        raise ValueError(f'No usable episodes in archive: {row["task"]}')
    write_json(marker,result)
    return result


def aggregate(results, output_base, work):
    from lerobot.datasets.aggregate import aggregate_datasets
    groups=defaultdict(list)
    for r in results:
        for s in r['shards']:groups[s['group']].append(s)
    outputs=[]
    for name, shards in sorted(groups.items()):
        write_json(Path(work)/'progress.json',{'stage':'aggregation','dataset':name,
                   'completed_datasets':len(outputs),'total_datasets':len(groups),'updated':time.time()})
        shards.sort(key=lambda s:s['path'])
        output=Path(output_base)/name
        signature=identity(shards)
        marker=output/'meta/fast_completed.json'
        if marker.exists():
            if json.loads(marker.read_text())['signature']!=signature:raise ValueError(f'Output conflict: {output}')
            outputs.append(str(output));continue
        if output.exists():raise FileExistsError(f'Inspect incomplete output: {output}')
        stage=Path(work)/'aggregate'/name
        if stage.exists():
            backup=Path(work)/'failed_attempts'/f'{name}-{time.time_ns()}'
            backup.parent.mkdir(parents=True,exist_ok=True);stage.rename(backup)
        print(f'AGGREGATE {name}: {len(shards)} shards',flush=True)
        aggregate_datasets(repo_ids=[None]*len(shards),roots=[Path(s['path']) for s in shards],
                           aggr_repo_id=name,aggr_root=stage,concatenate_data=False,concatenate_videos=False)
        for field in ['total_frames','total_episodes']:
            info=json.loads((stage/'meta/info.json').read_text())
            expected=sum(s['frames' if field=='total_frames' else 'episodes'] for s in shards)
            if info[field]!=expected:raise ValueError(f'Aggregate {field} mismatch')
        split = name.rsplit('_', 2)[-2]
        if split not in ('train', 'validation', 'unspecified'):
            raise ValueError(f'Unrecognized output split: {name}')
        info['splits']={split:f'0:{info["total_episodes"]}'}
        write_json(stage/'meta/info.json',info)
        write_json(stage/'meta/source_shards.json',shards)
        records=[]
        for s in shards:records.extend(json.loads((Path(s['path'])/'meta/source_episodes.json').read_text()))
        write_json(stage/'meta/source_episodes.json',records)
        write_json(stage/'meta/fast_completed.json',{'signature':signature,'version':VERSION})
        output.parent.mkdir(parents=True,exist_ok=True);stage.rename(output);outputs.append(str(output))
    return outputs


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--mode',choices=['inventory','smoke','full'],default='inventory')
    parser.add_argument('--source',required=True)
    parser.add_argument('--output-base',required=True)
    parser.add_argument('--work',required=True)
    parser.add_argument('--scratch',required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--decode-threads',type=int,default=2)
    parser.add_argument('--encoder-threads',type=int,default=1)
    parser.add_argument('--shard-episodes',type=int,default=16)
    parser.add_argument('--episodes',type=int,default=2,help='Per-archive smoke limit; full always reads all')
    parser.add_argument('--embodiments',nargs='+',choices=sorted(SUPPORTED))
    parser.add_argument('--max-hdf5-gib',type=float,default=32)
    parser.add_argument('--local-hdf5-gib',type=float,default=4,
                        help='Larger episodes use NAS scratch, preserving limited local disk')
    parser.add_argument('--exclude-task', action='append', default=[], help='Explicit source task exclusions, recorded before conversion')
    args=parser.parse_args()
    for name in ['workers','decode_threads','encoder_threads','shard_episodes','episodes','max_hdf5_gib','local_hdf5_gib']:
        if getattr(args,name)<=0:parser.error(f'{name} must be positive')
    work=Path(args.work);work.mkdir(parents=True,exist_ok=True)
    with (work/'run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        plan_path=work/'inventory.json'
        if plan_path.exists():plan=json.loads(plan_path.read_text())
        else:plan=inventory(args.source);write_json(plan_path,plan)
        if plan['root']!=args.source:raise ValueError('Inventory source changed')
        rows=[r for r in plan['archives'] if r['embodiment'] in SUPPORTED]
        excluded = []
        for task in args.exclude_task:
            matches = [row for row in rows if row['task'] == task]
            if len(matches) != 1: raise ValueError(f'Exclusion must match exactly one archive: {task}')
            excluded.extend(matches)
        rows = [row for row in rows if row not in excluded]
        write_json(work/'explicit_exclusions.json', {'tasks': args.exclude_task, 'archives': excluded})
        if args.embodiments:rows=[r for r in rows if r['embodiment'] in args.embodiments]
        print(json.dumps({'archives':len(rows),'TiB':sum(r['bytes'] for r in rows)/2**40,
              'unsupported_archives':len(plan['unsupported']),'missing_instructions':len(plan['missing_instructions'])}),flush=True)
        if args.mode=='inventory':return
        missing = [r for r in plan['missing_instructions'] if r['embodiment'] in SUPPORTED
                   and (not args.embodiments or r['embodiment'] in args.embodiments)]
        if args.mode=='full' and missing:
            raise ValueError('Missing instructions: resolve inventory entries before full conversion')
        if args.mode=='smoke':
            rows=[min((r for r in rows if r['embodiment']==emb),key=lambda r:r['bytes'])
                  for emb in sorted({r['embodiment'] for r in rows})]
        if not rows:raise ValueError('No archives selected')
        settings=vars(args).copy()
        if args.mode=='full':settings['episodes']=0
        Path(args.scratch).mkdir(parents=True,exist_ok=True)
        effective_scratch_gib = scratch_budget(shutil.disk_usage(args.scratch).free,
                                              min(args.workers,len(rows)), args.local_hdf5_gib)
        config_file=work/'run_config.json'
        stable={k:v for k,v in settings.items() if k not in ['workers','decode_threads','encoder_threads']}
        if config_file.exists() and json.loads(config_file.read_text())!=stable:
            raise ValueError('Use a new work directory for changed mode/settings')
        write_json(config_file,stable)
        settings['scratch_budget_gib'] = effective_scratch_gib
        write_json(work/'runtime_config.json', {**settings, 'updated':time.time()})
        print(f'RUNTIME workers={args.workers}; local HDF5 budget={effective_scratch_gib:.2f} GiB/worker; larger episodes use NAS',flush=True)
        failure = work/'FAILED.json'
        if failure.exists():
            history = work/'failure_history'
            history.mkdir(exist_ok=True)
            failure.rename(history/f'FAILED-{time.time_ns()}.json')
        # Large archives start first, reducing an expensive single-worker tail.
        rows.sort(key=lambda r:r['bytes'],reverse=True)
        eligible, failures = pending_archive_rows(work, rows)
        started=time.monotonic();started_wall=time.time();results=[];pending={};iterator=iter(eligible)
        if failures:
            print(f'REPAIR_REQUIRED {len(failures)} unchanged failed archives; '
                  'continuing other archives without declaring full completion', flush=True)
            first_failure=next(iter(failures.values()))
            write_json(work/'FAILED.json', {**first_failure, 'failures':list(failures.values()),
                                           'other_archives_continuing': True})
        baseline_bytes=0
        for row in rows:
            if (work/'archives'/identity(row)/'COMPLETED.json').exists():baseline_bytes+=row['bytes']
        with ProcessPoolExecutor(max_workers=args.workers,mp_context=mp.get_context('spawn')) as pool:
            def submit():
                row=next(iterator,None)
                if row is not None:pending[pool.submit(worker,row,settings)]=row
            for _ in range(args.workers):submit()
            while pending:
                done,_=wait(pending,timeout=30,return_when=FIRST_COMPLETED)
                for future in done:
                    row=pending.pop(future)
                    try:result=future.result()
                    except Exception as exc:
                        recorded=record_archive_failure(work,row,repr(exc))
                        failures[identity(row)]=recorded[identity(row)]
                        write_json(work/'FAILED.json',{**failures[identity(row)],
                                   'failures':list(failures.values()),'other_archives_continuing':True})
                        print(f'ARCHIVE_FAILED {row["embodiment"]}/{row["task"]}: {exc!r}; '
                              'retained for repair; other archives continue',flush=True)
                        submit()
                        continue
                    results.append(result);submit()
                    print(f'SAVED {row["embodiment"]}/{row["task"]}: {result["saved"]} episodes, {result["frames"]} frames, {result["seconds"]:.1f}s',flush=True)
                active=[]
                for row in pending.values():
                    p=work/'archives'/identity(row)/'progress.json'
                    if p.exists():
                        current=json.loads(p.read_text())
                        if current['updated'] >= started_wall:active.append(current)
                elapsed=time.monotonic()-started
                report={'stage':'conversion','completed_archives':len(results),'total_archives':len(rows),
                    'failed_archives':len(failures), 'failed_tasks':[r['archive']['task'] for r in failures.values()],
                    'saved':sum(r['saved'] for r in results)+sum(r['saved'] for r in active),
                    'frames':sum(r['frames'] for r in results)+sum(r['frames'] for r in active),
                    'elapsed_seconds':elapsed,'active':active,'updated':time.time()}
                if args.mode=='full':
                    total_bytes=sum(r['bytes'] for r in rows)
                    processed=sum(r['archive']['bytes'] for r in results)+sum(r['compressed_bytes_read'] for r in active)
                    new_bytes=max(0,processed-baseline_bytes)
                    eta=(total_bytes-processed)/(new_bytes/elapsed) if new_bytes>0 else None
                    report.update(input_percent=100*processed/total_bytes,eta_seconds=eta,
                                  eta_basis='compressed input bytes including active archives; aggregation excluded')
                write_json(work/'progress.json',report)
                eta_text=f'; input {report["input_percent"]:.2f}%; ETA {report["eta_seconds"]/3600:.1f}h' if report.get('eta_seconds') is not None else ''
                print(f'PROGRESS {len(results)}/{len(rows)} archives; {report["saved"]} episodes; {report["frames"]} frames; '
                      f'{elapsed:.0f}s{eta_text}; repair_required={len(failures)}',flush=True)
        write_json(work/'conversion_results.json',results)
        if failures:
            write_json(work/'progress.json',{'stage':'blocked_source_repair','completed_archives':len(results),
                       'total_archives':len(rows),'failed_archives':len(failures),
                       'failed_tasks':[r['archive']['task'] for r in failures.values()],
                       'saved':sum(r['saved'] for r in results),'frames':sum(r['frames'] for r in results),
                       'updated':time.time()})
            first_failure=next(iter(failures.values()))
            write_json(work/'FAILED.json',{**first_failure,'failures':list(failures.values()),
                       'other_archives_continuing':False})
        require_all_archives(results, rows, failures)
        outputs=aggregate(results,args.output_base,work)
        write_json(work/'COMPLETED.json',{'outputs':outputs,'elapsed_seconds':time.monotonic()-started,
                   'saved':sum(r['saved'] for r in results),'frames':sum(r['frames'] for r in results)})
        write_json(work/'progress.json',{'stage':'completed','outputs':outputs,'updated':time.time()})
        print(f'COMPLETED {work}/COMPLETED.json',flush=True)


if __name__=='__main__':
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        os.environ[name]='1'
    os.environ['HDF5_USE_FILE_LOCKING']='FALSE'
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    main()
