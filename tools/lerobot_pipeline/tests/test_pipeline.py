"""Release orchestration and destination safety, independent of heavyweight engines."""
from pathlib import Path
import copy
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from pipeline import cli, conversion, release


def settings_file(tmp_path):
    cfg = tmp_path / 'settings.json'
    cfg.write_text(json.dumps({
        'raw_root': 'raw', 'converted_root': 'converted',
        'cleaned_root': 'cleaned', 'work_root': 'work',
        'python': sys.executable, 'ffmpeg': 'ffmpeg',
    }))
    return cfg


def test_manifest_is_exact_and_portable():
    d = release.load_manifest()
    rows = d['repositories']
    assert len(rows) == d['repository_count'] == 1721
    assert sum(r['episodes'] for r in rows) == 972324
    assert sum(r['frames'] for r in rows) == 1077451809
    assert len({r['relative_path'] for r in rows}) == 1721
    for row in rows:
        assert not Path(row['relative_path']).is_absolute()
        assert '..' not in Path(row['relative_path']).parts
        assert row['schema_id'] in d['schemas']
        assert row['adapter'] != 'robomind_agilex_3rgb'
    assert sum(r['adapter'].startswith('robomind_tienkung') or
               r['relative_path'].startswith('InternData_A1_v3/physical/') for r in rows) == 17


def test_plan_is_read_only_and_contains_only_requested_family(tmp_path, monkeypatch, capsys):
    cfg = settings_file(tmp_path)
    monkeypatch.setattr(cli, 'doctor', lambda *a, **k: pytest.fail('plan invoked doctor'))
    cli.main(['plan', '--config', str(cfg), '--dataset', 'robomind'])
    plan = json.loads(capsys.readouterr().out)
    assert set(plan['conversion']) == {'robomind'}
    assert plan['cleaning']['selected_repositories'] == 35
    assert plan['cleaning']['policy']['added_data_columns'] == ['quality.valid']
    assert set(p.name for p in tmp_path.iterdir()) == {'settings.json'}


def test_nonexecuting_run_is_read_only(tmp_path, capsys):
    cfg = settings_file(tmp_path)
    cli.main(['run', '--config', str(cfg)])
    plan = json.loads(capsys.readouterr().out)
    assert plan['cleaning']['selected_repositories'] == 1721
    assert set(p.name for p in tmp_path.iterdir()) == {'settings.json'}


def test_config_resolves_relative_roots_and_rejects_overlap(tmp_path):
    cfg = settings_file(tmp_path)
    settings = cli.load_settings(cfg)
    assert settings['raw_root'] == tmp_path / 'raw'
    values = json.loads(cfg.read_text()); values['cleaned_root'] = 'converted/cleaned'
    cfg.write_text(json.dumps(values))
    with pytest.raises(ValueError, match='overlapping'):
        cli.load_settings(cfg)


@pytest.mark.parametrize('value', [0, -1, True, 1.5])
def test_invalid_parallelism_rejected(tmp_path, value):
    cfg = settings_file(tmp_path); data = json.loads(cfg.read_text())
    data['cleaning_workers'] = value;cfg.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='positive integer'):
        cli.load_settings(cfg)


def test_released_exception_selection_is_in_conversion_plan(tmp_path):
    args = (tmp_path/'raw', tmp_path/'converted', tmp_path/'work', sys.executable)
    robo = conversion.build_steps('robomind', *args)[0]['command']
    assert '--embodiments' in robo and 'agilex_3rgb' not in robo
    assert 'place_yellow_banana_on_plastic_plate' in robo
    intern = conversion.build_steps('interndata', *args)[0]['command']
    assert intern.count('--exclude-job') == 2
    assert any(v.endswith('=basket,bowl,dish,flower_pot') for v in intern)
    lite, pro = conversion.build_steps('galaxea', *args)
    assert 'Boil_The_Water_20250714_006' in lite['command']
    assert '--include' in pro['command']
    assert 'Put_The_Items_Into_The_Storage_Box_20250929_002_007' in pro['command']
    beta = conversion.build_steps('beta', *args)
    assert beta[1]['env']['BETA_AGGREGATE_BY_TASK'] == '1'
    assert beta[2]['env']['BETA_AGGREGATE_BY_TASK'] == '1'


def test_owned_run_new_resume_and_changed_identity(tmp_path, monkeypatch):
    s = cli.load_settings(settings_file(tmp_path))
    expected = {'release': 'test-v1'}
    monkeypatch.setattr(cli, 'identity', lambda _: dict(expected))
    with cli.owned_run(s, ['converted', 'cleaned'], False):
        assert (s['work_root']/'.pipeline-owner.json').exists()
    with pytest.raises(ValueError, match='use --resume'):
        with cli.owned_run(s, ['converted', 'cleaned'], False):
            pass
    with cli.owned_run(s, ['converted', 'cleaned'], True):
        pass
    expected['release'] = 'test-v2'
    with pytest.raises(ValueError, match='identity/release changed'):
        with cli.owned_run(s, ['converted', 'cleaned'], True):
            pass


def test_unowned_output_rejected_before_work_created(tmp_path, monkeypatch):
    s = cli.load_settings(settings_file(tmp_path))
    s['cleaned_root'].mkdir(); (s['cleaned_root']/'keep.txt').write_text('preserve')
    monkeypatch.setattr(cli, 'identity', lambda _: {'release': 'test'})
    with pytest.raises(ValueError, match='unowned'):
        with cli.owned_run(s, ['cleaned'], False):
            pass
    assert not s['work_root'].exists()
    assert (s['cleaned_root']/'keep.txt').read_text() == 'preserve'


def test_mock_fullflow_then_clean_resume_uses_same_owned_roots(tmp_path, monkeypatch):
    cfg = settings_file(tmp_path); s = cli.load_settings(cfg)
    for v in release.load_profile()['datasets'].values():
        (s['raw_root']/v['source']).mkdir(parents=True)
    calls = []
    monkeypatch.setattr(cli, 'doctor', lambda *a, **k: {})
    monkeypatch.setattr(cli, 'execute_conversion', lambda s,n,p,e: calls.append(('convert',n)))
    monkeypatch.setattr(cli, 'execute_cleaning', lambda s,n,p,e: calls.append(('clean',n)))
    monkeypatch.setattr(cli, 'verify', lambda *a, **k: {})
    cli.main(['run', '--config', str(cfg), '--dataset', 'abc', '--execute'])
    assert calls == [('convert',['abc']), ('clean',['abc'])]
    calls.clear()
    cli.main(['clean', '--config', str(cfg), '--dataset', 'abc', '--execute', '--resume'])
    assert calls == [('clean',['abc'])]


@pytest.fixture
def fake_repo(tmp_path, monkeypatch):
    features = {'state.qpos': {'dtype': 'float32', 'shape': [2], 'names': {'motors':['a','b']}}}
    row = {'family':'abc','adapter':'test_adapter','relative_path':'ABC-130k-train',
           'episodes':1,'frames':3,'fps':30,'robot_type':'test','schema_id':'schema_1'}
    manifest = {'repositories':[row],'schemas':{'schema_1':features}}
    monkeypatch.setattr(release, 'load_manifest', lambda: copy.deepcopy(manifest))
    monkeypatch.setattr(release, 'load_profile', lambda: {'datasets':{'abc':{'outputs':{'ABC-130k-train':{}}}}})
    root = tmp_path/'converted'; repo = root/row['relative_path']
    (repo/'meta/episodes').mkdir(parents=True); (repo/'data').mkdir(); (repo/'videos').mkdir()
    info = {'codebase_version':'v3.0','total_frames':3,'total_episodes':1,'fps':30,'robot_type':'test','features':copy.deepcopy(features)}
    (repo/'meta/info.json').write_text(json.dumps(info))
    return root,repo,row,info


def test_verify_exact_metadata_and_schema(fake_repo):
    root,repo,row,info = fake_repo
    assert release.verify(root,['abc'])['frames'] == 3
    info['features']['state.qpos']['shape'] = [3]
    (repo/'meta/info.json').write_text(json.dumps(info))
    with pytest.raises(ValueError, match='schema differs'):
        release.verify(root,['abc'])


def test_verify_rejects_counts_and_extra_columns(fake_repo):
    root,repo,row,info = fake_repo
    info['total_frames'] = 4;(repo/'meta/info.json').write_text(json.dumps(info))
    with pytest.raises(ValueError, match='total_frames differs'):
        release.verify(root,['abc'])
    info['total_frames'] = 3;info['features']['quality.fk_checked'] = {'dtype':'bool','shape':[1],'names':None}
    (repo/'meta/info.json').write_text(json.dumps(info))
    with pytest.raises(ValueError, match='schema differs'):
        release.verify(root,['abc'])


def test_clean_verify_accepts_fk_skip_and_rejects_wrong_video_target(fake_repo,tmp_path):
    root,source,row,info = fake_repo
    clean_root = tmp_path/'cleaned';repo = clean_root/row['relative_path']
    (repo/'meta/episodes').mkdir(parents=True); (repo/'data').mkdir();(repo/'quality').mkdir()
    info = copy.deepcopy(info);info['features']['quality.valid'] = {'dtype':'bool','shape':[1],'names':None}
    (repo/'meta/info.json').write_text(json.dumps(info))
    (repo/'quality/summary.json').write_text(json.dumps({'status':'complete','frames':3,'rows_removed':0,
        'adapter':'test_adapter','scope':'all_frames','frame_policy':'independent_frame','valid_frames':3,'invalid_frames':0,
        'source':str(source),'fk_checked_frames':0,'fk_unavailable_reason':'no observed EE'}))
    (repo/'videos').symlink_to(source/'videos',target_is_directory=True)
    assert release.verify(clean_root,['abc'],cleaned=True,source_root=root)['repositories'] == 1
    (repo/'videos').unlink();other=tmp_path/'other_videos';other.mkdir();(repo/'videos').symlink_to(other,target_is_directory=True)
    with pytest.raises(ValueError, match='wrong video symlink target'):
        release.verify(clean_root,['abc'],cleaned=True,source_root=root)


def test_two_work_roots_cannot_claim_same_output(tmp_path, monkeypatch):
    s = cli.load_settings(settings_file(tmp_path)); second = dict(s)
    second['work_root'] = tmp_path/'work_two'
    # Same synthetic identity lets the test reach the cross-work output lock.
    monkeypatch.setattr(cli, 'identity', lambda _: {'release':'test'})
    with cli.owned_run(s, ['converted'], False):
        with pytest.raises(BlockingIOError):
            with cli.owned_run(second, ['converted'], True):
                pass
