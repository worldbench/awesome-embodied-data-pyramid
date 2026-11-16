import json
import pytest
from lerobot_quality.batch_export import existing_result, prepare


def completed_output(tmp_path):
    output = tmp_path / 'cleaned'
    (output / 'quality').mkdir(parents=True)
    (output / 'meta').mkdir()
    row = {'output': str(output), 'source': str(tmp_path / 'source'),
           'frames': 10, 'episodes': 1, 'adapter': 'example',
           'four_rules': {'alpha': 10}}
    summary = {'status': 'complete', 'source': row['source'], 'frames': 10,
               'adapter': 'example', 'scope': 'all_frames', 'rows_removed': 0,
               'frame_policy': 'independent_frame', 'four_rules': {'alpha': 10}}
    (output / 'quality/summary.json').write_text(json.dumps(summary))
    (output / 'meta/info.json').write_text(json.dumps(
        {'total_frames': 10, 'total_episodes': 1, 'features': {'quality.valid': {}}}))
    return row, summary


def test_resume_accepts_matching_output(tmp_path):
    row, summary = completed_output(tmp_path)
    assert existing_result(row) == summary


@pytest.mark.parametrize('key,value', [('four_rules', {'alpha': 5}), ('frames', 9),
                                      ('source', 'different-source'), ('status', 'partial')])
def test_resume_rejects_changed_identity_or_policy(tmp_path, key, value):
    row, summary = completed_output(tmp_path)
    summary[key] = value
    (tmp_path / 'cleaned/quality/summary.json').write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='current plan/policy'):
        existing_result(row)


def test_plan_rejects_duplicate_source_and_wrong_destination(tmp_path):
    source = tmp_path / 'source/repo'
    (source / 'meta').mkdir(parents=True)
    (source / 'meta/info.json').write_text(json.dumps({'total_frames': 10, 'total_episodes': 1}))
    row = {'source': str(source), 'output': str(tmp_path / 'cleaned/repo'),
           'frames': 10, 'episodes': 1}
    plan = {'input_root': str(tmp_path / 'source'), 'output_root': str(tmp_path / 'cleaned'),
            'repositories': [row, row], 'selected_repositories': 2}
    with pytest.raises(ValueError, match='duplicate or unexpected'):
        prepare(plan)
    plan.update(repositories=[{**row, 'output': str(tmp_path / 'cleaned/other')}], selected_repositories=1)
    with pytest.raises(ValueError, match='duplicate or unexpected'):
        prepare(plan)
