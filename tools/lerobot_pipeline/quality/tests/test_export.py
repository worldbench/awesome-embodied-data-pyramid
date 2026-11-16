import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lerobot_quality.adapters import profiles
from lerobot_quality.export import QUALITY_FEATURES, bool_stats, export_repo
from test_adapters import fixture as signal_fixture


def make_v3(tmp_path, name='beta_a2d_gripper', update=None):
    original_update = update
    def real_beta(arrays):
        if name == 'beta_a2d_gripper':
            rows = json.loads((Path(__file__).parent/'fixtures/current_release_fk.json').read_text())[name]['rows']
            for key in arrays:
                arrays[key][:] = rows[key]
        if original_update:
            original_update(arrays)
    repo = signal_fixture(tmp_path, name, update=real_beta, split=True)
    info = json.loads((repo/'meta/info.json').read_text())
    info.update(codebase_version='v3.0', total_frames=4, total_episodes=1,
                total_tasks=1, splits={'train':'0:1'},
                data_path='data/chunk-{chunk_index:03d}/file-{file_index:03d}.parquet',
                video_path='videos/{video_key}/chunk-{chunk_index:03d}/file-{file_index:03d}.mp4')
    info['features']['observation.images.test'] = {'dtype':'video', 'shape':[2,2,3], 'names':['height','width','channels']}
    (repo/'meta/info.json').write_text(json.dumps(info))
    (repo/'meta/stats.json').write_text(json.dumps({'state.qpos':{'count':[4], 'mean':[123]}}))
    (repo/'meta/episodes/chunk-000').mkdir(parents=True)
    pq.write_table(pa.table({'episode_index':[0], 'length':[4], 'dataset_from_index':[0],
                            'dataset_to_index':[4], 'videos/test/from_timestamp':[0.],
                            'videos/test/to_timestamp':[4/30.]}),repo/'meta/episodes/chunk-000/file-000.parquet')
    count=0
    for file in sorted((repo/'data').glob('*.parquet')):
        t=pq.read_table(file)
        t=t.append_column('index',pa.array(np.arange(count,count+len(t)),pa.int64()))
        t=t.append_column('timestamp',pa.array(np.arange(count,count+len(t))/30,pa.float32()))
        pq.write_table(t,file)
        count+=len(t)
    (repo/'videos').mkdir()
    (repo/'videos/unchanged.bin').write_bytes(b'video sentinel')
    return repo


@pytest.mark.parametrize('name',sorted(profiles()))
def test_all_adapters_export_without_removing_frames(tmp_path,name):
    repo=make_v3(tmp_path,name)
    out=tmp_path/'annotated'
    summary=export_repo(repo,out,batch_size=1)
    assert summary['rows_removed'] == 0
    assert summary['frames'] == 4
    assert summary['adapter'] == name
    for src in sorted((repo/'data').glob('*.parquet')):
        old=pq.read_table(src)
        new=pq.read_table(out/src.relative_to(repo))
        assert new.select(old.column_names).equals(old,check_metadata=False)
        assert new.schema.field('quality.valid').type == pa.bool_()
        assert set(new.column_names) - set(old.column_names) == {'quality.valid'}
        assert len(new) == len(old)
    assert (out/'videos').is_symlink()
    assert (out/'videos').resolve() == (repo/'videos').resolve()
    assert (out/'videos/unchanged.bin').read_bytes() == b'video sentinel'
    original_info=json.loads((repo/'meta/info.json').read_text())
    info=json.loads((out/'meta/info.json').read_text())
    assert not set(QUALITY_FEATURES)&set(original_info['features'])
    assert info['total_frames'] == original_info['total_frames']
    assert set(info['features']) - set(original_info['features']) == {'quality.valid'}
    original_stats=json.loads((repo/'meta/stats.json').read_text())
    stats=json.loads((out/'meta/stats.json').read_text())
    assert stats['state.qpos'] == original_stats['state.qpos']
    assert set(stats) - set(original_stats) == {'quality.valid'}
    assert stats['quality.valid']['count'] == [4]
    old_meta=pq.read_table(repo/'meta/episodes/chunk-000/file-000.parquet')
    new_meta=pq.read_table(out/'meta/episodes/chunk-000/file-000.parquet')
    assert new_meta.select(old_meta.column_names).equals(old_meta,check_metadata=False)
    assert new_meta['stats/quality.valid/count'].to_pylist() == [[4]]
    assert not any('quality.fk_checked' in key for key in new_meta.column_names)


def test_only_failed_frame_is_masked_not_entire_episode(tmp_path):
    def update(arrays):
        arrays['state.waist'][1,0]=np.nan
    repo=make_v3(tmp_path,update=update)
    out=tmp_path/'annotated'
    summary=export_repo(repo,out,batch_size=3)
    table=pa.concat_tables([pq.read_table(p) for p in sorted((out/'data').glob('*.parquet'))])
    assert table['quality.valid'].to_pylist() == [True,False,True,True]
    assert 'quality.fk_checked' not in table.column_names
    assert pq.read_table(out/'quality/frames.parquet')['fk_checked'].to_pylist() == [True,False,True,True]
    assert summary['invalid_frames'] == 1
    assert summary['fk_unavailable_reason'] is None
    stats=json.loads((out/'meta/stats.json').read_text())['quality.valid']
    assert stats['mean'] == [.75]
    assert stats['count'] == [4]
    assert not (repo/'quality').exists()


def test_existing_or_nested_destinations_are_rejected(tmp_path):
    repo=make_v3(tmp_path)
    out=tmp_path/'annotated'
    out.mkdir()
    (out/'keep').write_text('keep')
    with pytest.raises(FileExistsError):
        export_repo(repo,out)
    with pytest.raises(ValueError,match='separate'):
        export_repo(repo,repo/'annotated')
    assert (out/'keep').read_text() == 'keep'


def test_metadata_mismatch_does_not_publish_output(tmp_path):
    repo=make_v3(tmp_path)
    info=json.loads((repo/'meta/info.json').read_text())
    info['total_frames']=99
    (repo/'meta/info.json').write_text(json.dumps(info))
    with pytest.raises(ValueError,match='total_frames'):
        export_repo(repo,tmp_path/'annotated')
    assert not (tmp_path/'annotated').exists()
    assert len(list(tmp_path.glob('.annotated.inprogress-*/FAILED.json'))) == 1


def test_action_target_mask_policy_is_preserved(tmp_path):
    def update(a):
        a['action.qpos_valid'][2,0]=0
    repo=make_v3(tmp_path,update=update)
    normal=export_repo(repo,tmp_path/'normal')
    strict=export_repo(repo,tmp_path/'strict',require_action_targets=True)
    assert normal['valid_frames'] == 4
    assert strict['valid_frames'] == 3


def test_partial_fk_coverage_cannot_hide_valid_side_failure(tmp_path,monkeypatch):
    import lerobot_quality.export as module
    repo=make_v3(tmp_path,'abc_yam_bimanual_2x6dof')
    def fake_side(model,config,side,qpos,*args):
        size=len(qpos)
        active=np.full(size,side=='left',dtype=bool)
        return {'fk_input_valid':active, 'fk_ee_valid':np.zeros(size,dtype=bool)}
    monkeypatch.setattr(module,'_side_fk',fake_side)
    summary=export_repo(repo,tmp_path/'annotated')
    assert summary['fk_checked_frames'] == 4
    assert summary['valid_frames'] == 0


def test_report_alignment_failure_is_not_published(tmp_path,monkeypatch):
    import lerobot_quality.export as module
    original=module.validate_repo
    repo=make_v3(tmp_path)
    def corrupt(*args,**kwargs):
        summary=original(*args,**kwargs)
        path=args[1]/'frames.parquet'
        table=pq.read_table(path)
        table=table.set_column(table.schema.get_field_index('frame_index'),'frame_index',pa.array([1,0,2,3]))
        pq.write_table(table,path)
        return summary
    monkeypatch.setattr(module,'validate_repo',corrupt)
    with pytest.raises(ValueError,match='alignment mismatch'):
        export_repo(repo,tmp_path/'annotated')
    assert not (tmp_path/'annotated').exists()


@pytest.mark.parametrize('count,true_count',[(1,0),(1,1),(4,1),(5,3),(100,99)])
def test_binary_statistics_match_numpy(count,true_count):
    data=np.array([0]*(count-true_count)+[1]*true_count)
    stats=bool_stats(count,true_count)
    assert stats['mean'][0] == pytest.approx(data.mean())
    assert stats['std'][0] == pytest.approx(data.std())
    for key,q in [('q01',.01),('q10',.1),('q50',.5),('q90',.9),('q99',.99)]:
        assert stats[key][0] == pytest.approx(np.quantile(data,q))


def test_progress_callback_covers_both_passes_and_preserves_export(tmp_path):
    repo=make_v3(tmp_path);events=[]
    summary=export_repo(repo,tmp_path/'annotated',batch_size=2,progress=events.append)
    assert summary['valid_frames']==4
    assert [e['phase'] for e in events if e['frames']==0]==['signal','export']
    assert any(e['phase']=='signal' and e['frames']==4 for e in events)
    assert any(e['phase']=='export' and e['frames']==4 for e in events)
    assert events[-1]['phase']=='complete' and events[-1]['frames']==4
