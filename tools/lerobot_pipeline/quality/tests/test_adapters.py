import copy
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from lerobot_quality.adapters import profiles, resolve_adapter
from lerobot_quality.signal_quality import validate_repo


def info_for_profile(name):
    p = profiles()[name]
    features = {k:{'shape':[width]} for k,width in p['feature_widths'].items()}
    for key,names in p['qpos_names'].items():
        features[key]['names'] = {'motors':names}
    return {'robot_type':p['robot_type'], 'fps':15 if name.startswith('galaxea') else 30,
            'features':features}


def fixture(tmp_path, name, update=None, split=False):
    info = info_for_profile(name)
    adapter = resolve_adapter(info)
    arrays = {k:np.zeros((4,width),np.float32) for k,width in adapter.profile['feature_widths'].items()}
    for key in arrays:
        if key.endswith('_valid'):
            arrays[key][:] = 1
    if adapter.profile['ee_representation'] == 'xyz_xyzw':
        for key in adapter.pose_keys:
            arrays[key][:,6::7] = 1
    if update:
        update(arrays)
    repo = tmp_path/'repo'
    (repo/'meta').mkdir(parents=True)
    (repo/'data').mkdir()
    (repo/'meta/info.json').write_text(json.dumps(info))
    table = pa.table({'episode_index':np.zeros(4,np.int64), 'frame_index':np.arange(4,dtype=np.int64),
                      **{k:pa.FixedSizeListArray.from_arrays(pa.array(v.flatten()),v.shape[1]) for k,v in arrays.items()}})
    if split:
        pq.write_table(table.slice(0,2),repo/'data/a.parquet')
        pq.write_table(table.slice(2),repo/'data/b.parquet')
    else:
        pq.write_table(table,repo/'data/a.parquet')
    return repo


@pytest.mark.parametrize('name', sorted(profiles()))
def test_registered_profiles_run_common_flow(tmp_path,name):
    repo=fixture(tmp_path,name)
    report=validate_repo(repo,tmp_path/'report',write_frames=True)
    assert report['adapter'] == name
    assert report['invalid_frames'] == 0
    assert report['retained_episodes_all_frames_valid'] == 1


def test_identity_and_order_are_not_guessed():
    info=info_for_profile('interndata_franka')
    info['robot_type']='unreviewed_robot'
    with pytest.raises(ValueError,match='no unique adapter'):
        resolve_adapter(info)
    info=info_for_profile('galaxea_r1lite')
    info['features']['state.qpos']['names']['motors'] = list(reversed(info['features']['state.qpos']['names']['motors']))
    with pytest.raises(ValueError,match='motor order'):
        resolve_adapter(info,'galaxea_r1lite')


def test_masked_action_placeholders_do_not_create_jumps(tmp_path):
    def update(a):
        a['action.qpos'][:] = 3
        a['action.qpos'][2] = 0
        a['action.qpos_valid'][2] = 0
    repo=fixture(tmp_path,'beta_a2d_gripper',update,split=True)
    report=validate_repo(repo,tmp_path/'report')
    assert report['sudden_change'] == 0
    assert report['mask_valid_frames_by_side']['action.qpos_valid'] == [3,3]
    strict=validate_repo(repo,tmp_path/'strict',require_action_targets=True)
    assert strict['target_policy_rejected'] == 1
    assert strict['rejected_episodes'] == 1


def test_single_arm_jump_across_parquet_boundary(tmp_path):
    def update(a):
        a['state.qpos'][2:,0]=2
    report=validate_repo(fixture(tmp_path,'interndata_franka',update,split=True),tmp_path/'report')
    assert report['sudden_change'] == 1
    assert report['rejected_episodes'] == 1


def test_waist_twist_is_checked_as_a_separate_signal(tmp_path):
    def update(a):
        a['action.waist_velocity'][1,5]=np.nan
        a['state.waist'][2,0]=np.inf
    report=validate_repo(fixture(tmp_path,'galaxea_r1lite',update),tmp_path/'report')
    assert report['extra_non_finite'] == 2
    assert report['sudden_change'] == 0
    assert set(report['coverage']['finite_only_signals']) == {'state.waist','action.waist_velocity'}




def test_missing_ee_coverage_and_target_policy(tmp_path):
    def update(a):
        a['state.ee'][:]=0
        a['state.ee_valid'][:]=0
    repo=fixture(tmp_path,'interndata_a2d',update)
    report=validate_repo(repo,tmp_path/'report')
    assert report['invalid_frames'] == 0
    assert report['mask_valid_frames_by_side']['state.ee_valid'] == [0,0]
    strict=validate_repo(repo,tmp_path/'strict',require_ee_targets=True)
    assert strict['target_policy_rejected'] == 4


def test_non_binary_masks_are_rejected(tmp_path):
    def update(a):
        a['action.qpos_valid'][1,0]=.5
        a['action.ee_valid'][2,0]=np.nan
    report=validate_repo(fixture(tmp_path,'interndata_franka',update),tmp_path/'report')
    assert report['invalid_mask'] == 2


def test_sampling_never_claims_full_episode_retention(tmp_path):
    repo=fixture(tmp_path,'abc_yam_bimanual_2x6dof')
    report=validate_repo(repo,tmp_path/'report',max_frames=2)
    assert report['frames'] == 2
    assert report['scope'] == 'sample'
    assert report['retained_episodes_all_frames_valid'] is None
    assert json.loads((tmp_path/'report/episodes.json').read_text())['0']['quality_valid'] is None
    with pytest.raises(ValueError,match='outside'):
        validate_repo(repo,repo/'report')
    with pytest.raises(FileExistsError):
        validate_repo(repo,tmp_path/'report')


def test_unmapped_signals_and_partial_ee_fail_closed():
    info=copy.deepcopy(info_for_profile('galaxea_r1pro'))
    info['features']['action.new_signal']={'shape':[2]}
    with pytest.raises(ValueError,match='unmapped'):
        resolve_adapter(info)
    del info['features']['action.new_signal']
    del info['features']['action.ee_valid']
    with pytest.raises(ValueError,match='partial EE'):
        resolve_adapter(info)


def test_pipeline_reports_unavailable_fk_and_no_sample_retention(tmp_path):
    from lerobot_quality.pipeline import run_pipeline
    repo=fixture(tmp_path,'robomind_tienkung_gello_1rgb')
    report=run_pipeline(repo,tmp_path/'pipeline',max_frames=2)
    assert report['stages'] == {'signal':'completed','fk':'unavailable'}
    assert report['retained_episodes'] is None
    with pytest.raises(ValueError,match='FK required'):
        run_pipeline(repo,tmp_path/'required',require_fk=True)


def test_single_arm_adapter_works_with_fk_and_pipeline(tmp_path):
    from lerobot_quality.pipeline import run_pipeline
    def update(a):
        a['state.ee'][:,0]=1
    repo=fixture(tmp_path,'interndata_franka',update)
    urdf=tmp_path/'robot.urdf'
    xml=['<robot name="test"><link name="base"/>']
    parent='base'
    for i in range(7):
        link=f'link{i}'
        xml.append(f'<link name="{link}"/><joint name="j{i}" type="revolute">'
                   f'<parent link="{parent}"/><child link="{link}"/><axis xyz="0 0 1"/></joint>')
        parent=link
    xml.append(f'<link name="tip"/><joint name="tool" type="fixed"><parent link="{parent}"/>'
               '<child link="tip"/><origin xyz="1 0 0"/></joint></robot>')
    urdf.write_text(''.join(xml))
    cfg=tmp_path/'fk.json'
    cfg.write_text(json.dumps({'schema_version':'lerobot_fk_config_v1','urdf':str(urdf),
        'active_sides':['left'],'base_link':'base','left_ee_link':'tip',
        'left_joint_names':[f'j{i}' for i in range(7)],'qpos_widths':[8]}))
    report=run_pipeline(repo,tmp_path/'pipeline',fk_config=cfg,require_fk=True)
    assert report['stages']['fk'] == 'completed'
    assert report['fk_checked_frames'] == 4
    assert report['retained_episodes'] == 1


def test_scalar_one_dimensional_masks_from_lerobot(tmp_path):
    repo=fixture(tmp_path,'interndata_franka')
    path=repo/'data/a.parquet'
    table=pq.read_table(path)
    for key in ('state.ee_valid','action.ee_valid','action.qpos_valid'):
        table=table.set_column(table.schema.get_field_index(key),key,pa.array([1.,1.,1.,1.],pa.float32()))
    pq.write_table(table,path)
    report=validate_repo(repo,tmp_path/'report')
    assert report['invalid_frames'] == 0
    assert report['mask_valid_frames_by_side']['action.qpos_valid'] == [4]


def test_fk_failure_on_one_valid_side_is_not_hidden_by_other_side(tmp_path,monkeypatch):
    import lerobot_quality.pipeline as pipeline
    repo=fixture(tmp_path,'abc_yam_bimanual_2x6dof')
    def fake_compare(_repo,_config,output,**kwargs):
        output.mkdir(parents=True)
        pq.write_table(pa.table({'episode_index':[0],
            'left_fk_input_valid':[True], 'left_fk_ee_valid':[False],
            'right_fk_input_valid':[False], 'right_fk_ee_valid':[False]}),output/'frames.parquet')
        return {'valid_frames':0}
    monkeypatch.setattr(pipeline,'compare_repo',fake_compare)
    summary=pipeline.run_pipeline(repo,tmp_path/'pipeline')
    assert summary['retained_episodes'] == 0
    assert summary['fk_checked_frames'] == 1


def test_qpos_only_abc_keeps_signal_stage(tmp_path):
    from lerobot_quality.pipeline import run_pipeline
    repo=fixture(tmp_path,'abc_yam_bimanual_2x6dof')
    info=json.loads((repo/'meta/info.json').read_text())
    info['features']={k:v for k,v in info['features'].items() if '.ee' not in k}
    (repo/'meta/info.json').write_text(json.dumps(info))
    summary=run_pipeline(repo,tmp_path/'pipeline')
    assert summary['stages'] == {'signal':'completed','fk':'unavailable'}
    assert summary['retained_episodes'] == 1


def test_profile_discovery_ignores_hidden_metadata_files(tmp_path, monkeypatch):
    import lerobot_quality.adapters as adapters
    directory=tmp_path/'profiles'
    directory.mkdir()
    (directory/'selected.json').write_text(json.dumps({'id':'selected'}))
    (directory/'._selected.json').write_bytes(b'\x00\xffAppleDouble')
    monkeypatch.setattr(adapters, '__file__', str(tmp_path/'__init__.py'))
    adapters.profiles.cache_clear()
    try:
        assert adapters.profiles()=={'selected':{'id':'selected'}}
    finally:
        adapters.profiles.cache_clear()
