"""Regression against recorded source observations, not FK-generated expectations."""
import json
from pathlib import Path
import numpy as np
import pyarrow as pa
import pytest
from lerobot_quality.adapters import profiles, resolve_adapter
from lerobot_quality.export import BatchFK
from lerobot_quality.fk_compare import extra_joint_positions, _side_fk, quaternion_xyzw_to_matrix
from lerobot_quality.urdf_fk import rotation_from_rpy

SAMPLES = json.loads((Path(__file__).parent/'fixtures/current_release_fk.json').read_text())
CHECKED = set(SAMPLES) - {'abc_yam_bimanual_2x6dof','interndata_a2d','interndata_piper',
    'robomind_tienkung_gello_1rgb','robomind_tienkung_prod1_gello_1rgb','robomind_tienkung_xsens_1rgb'}

@pytest.mark.parametrize('name', sorted(SAMPLES))
def test_all_current_models_and_observed_poses(name):
    sample = SAMPLES[name]
    adapter = resolve_adapter(sample['info'])
    runtime = BatchFK(adapter, None, False, .01, 2.)
    if runtime.unavailable_reason is None:
        assert runtime.config_path.is_file()
        assert runtime.model
    else:
        assert not hasattr(runtime, 'model')
    checked, failed, detail = runtime.check(pa.table(sample['rows']))
    assert not failed.any()
    assert checked.all() if name in CHECKED else not checked.any()
    if name.startswith('robomind_tienkung'):
        assert 'no observed Cartesian' in runtime.unavailable_reason


def test_beta_waist_order_and_nonfinite_input():
    sample = SAMPLES['beta_a2d_gripper'];adapter=resolve_adapter(sample['info'])
    runtime = BatchFK(adapter,None,False,.01,2.)
    rows = {k:np.array(v) for k,v in sample['rows'].items()}
    rows['state.waist'] = rows['state.waist'][:,::-1]
    checked,failed,_ = runtime.check(pa.table({k:v.tolist() for k,v in rows.items()}))
    assert checked.all() and failed.all()
    rows['state.waist'][:] = np.nan
    checked,failed,_=runtime.check(pa.table({k:v.tolist() for k,v in rows.items()}))
    assert not checked.any() and not failed.any()

@pytest.mark.parametrize('name', sorted(CHECKED))
def test_wrong_observed_position_fails_fk(name):
    sample=SAMPLES[name];adapter=resolve_adapter(sample['info']);rows=dict(sample['rows'])
    ee=np.array(rows['state.ee']);ee[:,0]+=1.;rows['state.ee']=ee.tolist()
    checked,failed,_=BatchFK(adapter,None,False,.01,2.).check(pa.table(rows))
    assert checked.all() and failed.all()


def test_native_rotation_and_masks_are_converted_without_modifying_source():
    sample=SAMPLES['robomind_franka_1rgb'];adapter=resolve_adapter(sample['info'])
    table=pa.table(sample['rows']);native=np.array(sample['rows']['state.ee'])
    arrays=adapter.arrays(table);rotation=quaternion_xyzw_to_matrix(arrays['state.ee'][:,3:7])
    np.testing.assert_allclose(rotation[0],rotation_from_rpy(native[0,3:6]),atol=1e-7)
    assert arrays['state.ee_valid'].all()
    assert table['state.ee'].to_pylist()==sample['rows']['state.ee']


def test_unknown_body_mapping_is_rejected(tmp_path):
    sample=SAMPLES['beta_a2d_gripper'];adapter=resolve_adapter(sample['info'])
    runtime=BatchFK(adapter,None,False,.01,2.);cfg=dict(runtime.config)
    cfg['urdf']=str(cfg['urdf']);cfg['extra_joints']['idx01_body_joint1']['index']=2
    file=tmp_path/'bad.json';file.write_text(json.dumps(cfg))
    with pytest.raises(ValueError,match='body feature'):
        BatchFK(adapter,file,False,.01,2.)


def test_native_rotvec_zero_and_quarter_turn():
    sample=SAMPLES['robomind_ur_1rgb'];a=resolve_adapter(sample['info'])
    t=pa.table({'state.ee':[[0.,0.,0.,0.,0.,0.],[0.,0.,0.,0.,0.,np.pi/2]]})
    values=a.arrays(t)['state.ee']
    np.testing.assert_allclose(values[0,3:],[0,0,0,1],atol=1e-12)
    np.testing.assert_allclose(values[1,3:],[0,0,np.sqrt(.5),np.sqrt(.5)],atol=1e-12)




def test_native_pose_is_discovered_without_explicit_mask(tmp_path):
    from lerobot_quality.fk_dataset_stats import discover_repos
    repo=tmp_path/'native';(repo/'meta').mkdir(parents=True)
    (repo/'meta/info.json').write_text(json.dumps(SAMPLES['robomind_franka_1rgb']['info']))
    assert discover_repos(tmp_path)==[repo]
