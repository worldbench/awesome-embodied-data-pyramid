from dataclasses import asdict
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
import pytest

from lerobot_quality.four_rules import (FourRules, exact_bounds, derivative, acceleration_of,
    direction_check, smooth_valid)
from lerobot_quality.export import export_repo
from test_export import make_v3


def test_confirmed_exact_percentile_formula(tmp_path):
    values = np.r_[np.arange(1000,dtype=float), 1e6]
    path = tmp_path/'values.bin'; values.tofile(path)
    b = exact_bounds(path,5)
    lo,hi = np.quantile(values,[.01,.99])
    assert b['lower'] == lo-5*(hi-lo)
    assert b['upper'] == hi+5*(hi-lo)
    assert b['upper'] < 1e6
    assert b['count'] == len(values)


def test_constant_and_empty_bounds(tmp_path):
    p=tmp_path/'values.bin'
    np.ones(100).tofile(p)
    assert exact_bounds(p,5)['lower'] == exact_bounds(p,5)['upper'] == 1
    p.write_bytes(b'')
    assert exact_bounds(p,5)['count'] == 0


def test_timestamp_derivatives_and_gaps():
    time=np.array([0.,.1,.3,.6])
    x=(time**2)[:,None]
    v=derivative(x,np.ones_like(x,bool),time,np.arange(4))
    a=acceleration_of(v,time,np.arange(4))
    np.testing.assert_allclose(v[1:,0],[.1,.4,.9])
    np.testing.assert_allclose(a[2:,0],2.)
    assert np.isnan(a[:2]).all()
    v=derivative(x,np.ones_like(x,bool),time,np.array([0,1,3,4]))
    assert np.isnan(v[2]).all()


def test_masked_smoothing_and_short_episodes():
    x=np.arange(20,dtype=float)[:,None]; x[9]=np.nan
    out=smooth_valid(x,5)
    assert np.isnan(out[7:12]).all()
    assert out[5] == 5
    assert np.isnan(smooth_valid(x[:2],5)).all()


def test_direction_opposite_and_lag_and_missing():
    t=np.arange(150)/30; f=np.arange(150)
    state=np.tile(t[:,None],(1,3))
    good,checked,_=direction_check({'state.qpos':state,'action.qpos':-state},t,f,FourRules())
    assert checked.sum()>100
    assert not good[checked].any()
    # Nonperiodic delayed trajectory: lag search must find the true shift.
    rng=np.random.default_rng(123)
    state=np.cumsum(rng.normal(size=(150,3)),axis=0)
    action=np.vstack([state[7:],np.full((7,3),np.nan)])
    good,checked,detail=direction_check({'state.qpos':state,'action.qpos':action},t,f,FourRules())
    assert detail['lag_frames']==7
    assert good[checked].all()
    good,checked,detail=direction_check({'state.qpos':state},t,f,FourRules())
    assert good.all() and not checked.any() and 'reason' in detail


def test_export_four_rules_preserves_rows_videos_and_features(tmp_path):
    source=make_v3(tmp_path)
    out=tmp_path/'four-output'
    summary=export_repo(source,out,four_rules={})
    assert summary['four_rules']==asdict(FourRules())
    assert summary['frames']==4 and summary['rows_removed']==0
    assert (out/'videos').is_symlink()
    assert (out/'videos').resolve()==(source/'videos').resolve()
    for path in (source/'data').rglob('*.parquet'):
        a=pq.read_table(path); b=pq.read_table(out/path.relative_to(source))
        assert b.drop(['quality.valid']).equals(a,check_metadata=False)
    signal=pq.read_table(out/'quality/signal/frames.parquet')
    assert {'range_valid','velocity_valid','acceleration_valid','state_action_valid'} <= set(signal.column_names)
    assert not (out/'quality/signal/episodes.json').exists()
    assert not list(out.rglob('.calibration-*'))


@pytest.mark.parametrize('params',[{'alpha':-1},{'motion_alpha':float('nan')},
    {'smoothing_frames':4},{'max_lag_frames':-1},{'direction_min_agreement':2}])
def test_invalid_policy(params):
    with pytest.raises(ValueError): FourRules(**params)


def test_rotation_sign_invariance_and_timestamp_scaling(tmp_path):
    from lerobot_quality.four_rules import channels
    from lerobot_quality.adapters import resolve_adapter
    from lerobot_quality.schema import read_info
    source=make_v3(tmp_path)
    contract=resolve_adapter(read_info(source),'auto')
    table=pq.read_table(sorted((source/'data').rglob('*.parquet'))[0])
    raw,motion,arrays,time,frames=channels(table,contract)
    import pyarrow as pa
    poses=arrays['state.ee'].copy()
    poses[1,3:7]*=-1; poses[1,10:14]*=-1
    table=table.set_column(table.schema.get_field_index('state.ee'),'state.ee',pa.array(poses.tolist(),type=table['state.ee'].type))
    _,changed,*_=channels(table,contract)
    np.testing.assert_allclose(motion['state.ee.rotation0.velocity'],changed['state.ee.rotation0.velocity'],equal_nan=True,atol=1e-12)
    table=table.set_column(table.schema.get_field_index('timestamp'),'timestamp',pa.array(time*2))
    _,slower,*_=channels(table,contract)
    np.testing.assert_allclose(changed['state.qpos.velocity']/2,slower['state.qpos.velocity'],equal_nan=True)


def test_resume_rejects_other_policy(tmp_path):
    from lerobot_quality.batch_export import existing_result
    source=make_v3(tmp_path)
    out=tmp_path/'four-output'
    summary=export_repo(source,out,four_rules={})
    row={'source':str(source.resolve()),'output':str(out),'frames':4,'episodes':1,
         'adapter':summary['adapter'],'four_rules':summary['four_rules']}
    assert existing_result(row)['frames']==4
    row['four_rules']={**row['four_rules'],'alpha':6}
    with pytest.raises(ValueError,match='policy'):existing_result(row)

from lerobot_quality.adapters import profiles

@pytest.mark.parametrize('name',sorted(profiles()))
def test_four_rules_all_19_adapters(tmp_path,name):
    source=make_v3(tmp_path,name=name)
    result=export_repo(source,tmp_path/'out',four_rules={})
    assert result['frames']==4 and result['adapter']==name
    assert result['four_rules']['version']=='four_rules_v1'
