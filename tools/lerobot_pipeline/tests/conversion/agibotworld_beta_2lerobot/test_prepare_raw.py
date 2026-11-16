"""Exercise archive preparation and missing-payload policy on tiny raw fixtures."""
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from agibotworld_beta_2lerobot import prepare_raw as prep


class RawPreparationTest(unittest.TestCase):
    def test_missing_payload_is_audited_and_resume_keeps_available_episodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, work = Path(tmp)/'raw', Path(tmp)/'work'
            for name in ('parameters', 'task_info', 'proprio_stats', 'observations/1'):
                (src/name).mkdir(parents=True)
            work.mkdir()
            records = [{'episode_id': n} for n in (10, 11, 12)]
            (src/'task_info/task_1.json').write_text(json.dumps(records))
            def archive(path, members):
                with tarfile.open(path, 'w') as tf:
                    for name, data in members.items():
                        info = tarfile.TarInfo(name);info.size = len(data)
                        tf.addfile(info, io.BytesIO(data))
            archive(src/'proprio_stats/1.tar', {
                '1/10/proprio_stats.h5': b'fixture-h5',
                '1/11/proprio_stats.h5': b'fixture-h5',
                '1/12/proprio_stats.h5': b'',
            })
            archive(src/'observations/1/available.tar', {
                '10/videos/head_color.mp4': b'fixture-video',
                '12/videos/head_color.mp4': b'fixture-video',
                '10/videos/ignored_depth.mp4': b'not-selected',
            })
            (src/'observations/1/missing.tar').write_bytes(b'version https://git-lfs.github.com/spec/v1\noid sha256:fixture\nsize 1024\n')
            cfg = {'dexhand': {'task_ids': []},
                   'gripper': {'task_config': {'images': {'head': {'dtype': 'video'}}}}}
            with patch.multiple(prep, BASE=work, SRC=src, DST=work/'staged', CFG=cfg, WORKERS=2, EXCLUDED_TASK_IDS=set()):
                for _ in range(2):
                    prep.main()
                    self.assertEqual(json.loads((work/'expected_counts.json').read_text()), {'gripper': 1, 'dexhand': 0})
                    self.assertEqual(json.loads((work/'staged/task_info/task_1.json').read_text()), [{'episode_id': 10}])
                    audit = json.loads((work/'preparation_audit.json').read_text())
                    self.assertEqual(audit['excluded_episodes'], 2)
                    self.assertEqual(audit['missing_files'], 2)
                    excluded = json.loads((work/'excluded_episodes.json').read_text())
                    self.assertEqual({e['episode_id'] for e in excluded}, {'11', '12'})
            self.assertEqual(json.loads((src/'task_info/task_1.json').read_text()), records)
            self.assertFalse((work/'staged/observations/1/10/videos/ignored_depth.mp4').exists())


if __name__ == '__main__':
    unittest.main()
