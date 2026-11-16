"""Only executable, in-scope kinematic resources ship with the release."""
import json
from pathlib import Path

from lerobot_quality.adapters import profiles
from lerobot_quality.fk_compare import load_config
from lerobot_quality.urdf_fk import UrdfModel

ROOT = Path(__file__).resolve().parents[1]


def test_only_release_profiles_and_models_are_shipped():
    assert len(profiles()) == 19
    assert 'robomind_agilex_3rgb' not in profiles()
    names = {p.get('default_fk_config') for p in profiles().values()} - {None}
    assert {p.name for p in (ROOT/'configs').glob('*.json')} == names
    referenced = set()
    for name in names:
        path = ROOT/'configs'/name
        assert not Path(json.loads(path.read_text())['urdf']).is_absolute()
        config = load_config(path)
        referenced.add(config['urdf'])
        model = UrdfModel.load(config['urdf'])
        for side in config['active_sides']:
            model.chain(config.get(side+'_base_link', config.get('base_link')), config[side+'_ee_link'])
    assert referenced == {p.resolve() for p in (ROOT/'robot_models').rglob('*.urdf')}


def test_recorded_samples_use_relative_provenance():
    samples=json.loads((ROOT/'tests/fixtures/current_release_fk.json').read_text())
    assert set(samples)==set(profiles())
    assert all(not Path(s['source']).is_absolute() for s in samples.values())
