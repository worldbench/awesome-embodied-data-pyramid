import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from lerobot_quality.adapters import resolve_adapter
from lerobot_quality.export import export_repo, BatchFK
from lerobot_quality.pipeline import run_pipeline
from test_export import make_v3


def drop_signals(repo, kind):
    info_path=repo/'meta/info.json';info=json.loads(info_path.read_text())
    remove=[k for k in info['features'] if k in (f'state.{kind}',f'action.{kind}',f'state.{kind}_valid',f'action.{kind}_valid')]
    for key in remove:del info['features'][key]
    info_path.write_text(json.dumps(info))
    for file in (repo/'data').glob('*.parquet'):
        table=pq.read_table(file);pq.write_table(table.drop([k for k in remove if k in table.column_names]),file)
    return remove


@pytest.mark.parametrize('missing', ['qpos','ee'])
def test_single_signal_exports_only_valid_flag_and_checks_present_signals(tmp_path, missing, monkeypatch):
    def update(arrays):
        key='state.ee' if missing=='qpos' else 'state.qpos'
        arrays[key][1,0]=np.nan
    repo=make_v3(tmp_path,'galaxea_r1lite',update)
    drop_signals(repo,missing)
    def forbidden_model(*args,**kwargs):raise AssertionError('FK must not load a model with incomplete inputs')
    monkeypatch.setattr('lerobot_quality.export.UrdfModel.load',forbidden_model)
    out=tmp_path/'annotated';report=export_repo(repo,out,batch_size=1)
    assert report['fk_checked_frames']==0
    assert report['fk_unavailable_reason']
    assert report['invalid_frames']>=1
    tables=[]
    for file in sorted((repo/'data').glob('*.parquet')):
        old=pq.read_table(file);new=pq.read_table(out/file.relative_to(repo))
        for key in old.column_names:
            assert new.schema.field(key).type == old.schema.field(key).type
            np.testing.assert_array_equal(np.asarray(new[key].to_pylist()), np.asarray(old[key].to_pylist()))
        assert set(new.column_names)-set(old.column_names)=={'quality.valid'}
        tables.append(new)
    assert pa.concat_tables(tables)['quality.valid'].to_pylist()[1] is False
    info=json.loads((out/'meta/info.json').read_text())
    assert 'quality.fk_checked' not in info['features']
    pipeline=run_pipeline(repo,tmp_path/'report')
    assert pipeline['stages']['fk']=='unavailable'
    signal=json.loads((tmp_path/'report/signal/summary.json').read_text())
    assert signal['qpos_checks']==('unavailable' if missing=='qpos' else 'performed')
    assert signal['ee_checks']==('unavailable' if missing=='ee' else 'performed')


def test_ee_only_still_checks_cross_file_pose_jump(tmp_path):
    def update(arrays):arrays['state.ee'][2:,0]=1.
    repo=make_v3(tmp_path,'galaxea_r1lite',update);drop_signals(repo,'qpos')
    report=export_repo(repo,tmp_path/'annotated',batch_size=1)
    assert report['valid_frames']==3
    assert report['fk_checked_frames']==0


def test_missing_both_observation_types_is_rejected(tmp_path):
    repo=make_v3(tmp_path,'galaxea_r1lite');drop_signals(repo,'qpos');drop_signals(repo,'ee')
    with pytest.raises(ValueError,match='requires observed'):
        export_repo(repo,tmp_path/'annotated')


def test_ee_only_ambiguous_robot_identity_requires_explicit_adapter(tmp_path):
    repo=make_v3(tmp_path);drop_signals(repo,'qpos')
    info=json.loads((repo/'meta/info.json').read_text())
    with pytest.raises(ValueError,match='no unique adapter'):
        resolve_adapter(info)
    assert resolve_adapter(info,'beta_a2d_gripper').joint_keys==[]
    report=export_repo(repo,tmp_path/'annotated',adapter='beta_a2d_gripper')
    assert report['fk_checked_frames']==0
    assert report['valid_frames']==4


def test_missing_joint_does_not_reinterpret_action_joint_as_observation(tmp_path):
    repo=make_v3(tmp_path,'galaxea_r1lite');info_path=repo/'meta/info.json';info=json.loads(info_path.read_text());del info['features']['state.qpos'];info_path.write_text(json.dumps(info))
    for f in (repo/'data').glob('*.parquet'):
        table=pq.read_table(f);pq.write_table(table.drop(['state.qpos']),f)
    report=export_repo(repo,tmp_path/'annotated')
    assert report['fk_checked_frames']==0
    assert 'no observed state.qpos' in report['fk_unavailable_reason']


@pytest.mark.parametrize('name', [
    'interndata_a2d', 'interndata_piper',
    'robomind_tienkung_gello_1rgb', 'robomind_tienkung_xsens_1rgb',
    'robomind_tienkung_prod1_gello_1rgb',
])
def test_unavailable_fk_never_loads_a_candidate_model(tmp_path, name, monkeypatch):
    from test_adapters import info_for_profile
    adapter=resolve_adapter(info_for_profile(name), name)
    def forbidden(*args, **kwargs):
        raise AssertionError('unavailable FK must not load a model')
    monkeypatch.setattr('lerobot_quality.export.UrdfModel.load', forbidden)
    runtime=BatchFK(adapter, None, False, .01, 2.)
    assert runtime.unavailable_reason
    assert runtime.config_path is None
    with pytest.raises(ValueError, match='FK required but unavailable'):
        BatchFK(adapter, None, True, .01, 2.)


def test_physical_zero_ee_masks_keep_other_checks_active(tmp_path):
    def update(arrays):
        arrays['state.ee'][:]=0
        arrays['action.ee'][:]=0
        arrays['state.ee_valid'][:]=0
        arrays['action.ee_valid'][:]=0
        arrays['state.waist'][1,0]=np.nan
    repo=make_v3(tmp_path, 'interndata_a2d', update)
    out=tmp_path/'annotated'
    report=export_repo(repo, out, adapter='interndata_a2d')
    assert report['fk_checked_frames']==0
    assert report['invalid_frames']==1
    result=pa.concat_tables([pq.read_table(f) for f in sorted((out/'data').glob('*.parquet'))])
    assert result['quality.valid'].to_pylist()==[True, False, True, True]
