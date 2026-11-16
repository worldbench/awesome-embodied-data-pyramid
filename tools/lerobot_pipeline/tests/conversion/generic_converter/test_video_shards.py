import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from generic_converter.video_shards import VideoShardPlanner


class VideoShardPlannerTest(unittest.TestCase):
    def run_plan(self, concatenate=True):
        planner = VideoShardPlanner()
        idx = {'camera': {'chunk': 0, 'file': 0, 'latest_duration': 0}}
        dst = SimpleNamespace(root=Path('output'))
        mappings = []
        with patch('lerobot.datasets.aggregate.get_video_duration_in_s', return_value=2.0), \
             patch('lerobot.datasets.aggregate.get_file_size_in_mb', return_value=3.0):
            for i in range(5):
                src = SimpleNamespace(root=Path(f'source{i}'), episodes={
                    'videos/camera/chunk_index': [0, 0],
                    'videos/camera/file_index': [0, 0],
                })
                planner(src, dst, idx, 7, 2, concatenate)
                mappings.append((idx['camera']['src_to_dst'][(0, 0)],
                                 idx['camera']['src_to_offset'][(0, 0)]))
                self.assertEqual(idx['camera']['episode_duration'], 2.0)
        return planner, mappings

    def test_offsets_rotation_and_repeated_episode_references(self):
        planner, mappings = self.run_plan()
        self.assertEqual(mappings, [((0, 0), 0), ((0, 0), 2),
                                    ((0, 1), 0), ((0, 1), 2), ((1, 0), 0)])
        self.assertEqual([len(v) for v in planner.shards.values()], [2, 2, 1])

    def test_no_concatenation_rotates_each_file(self):
        planner, mappings = self.run_plan(False)
        self.assertEqual(mappings, [((0, 0), 0), ((0, 1), 0),
                                    ((1, 0), 0), ((1, 1), 0), ((2, 0), 0)])
        self.assertEqual(len(planner.shards), 5)

    def test_finish_propagates_merge_failure(self):
        planner = VideoShardPlanner()
        planner.shards[Path('output/x.mp4')] = [Path('source/x.mp4')]
        with patch('generic_converter.video_shards._write_shard', side_effect=RuntimeError('failed')):
            with self.assertRaisesRegex(RuntimeError, 'failed'):
                planner.finish()


if __name__ == '__main__':
    unittest.main()
