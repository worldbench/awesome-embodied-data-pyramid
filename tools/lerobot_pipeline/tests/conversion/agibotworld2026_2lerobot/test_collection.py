import copy
import tempfile
import unittest
from pathlib import Path

from agibotworld2026_2lerobot.convert_agibotworld2026 import SourceUnit
from agibotworld2026_2lerobot.run_collection import dataset_name, largest_first, source_size


class CollectionContractTest(unittest.TestCase):
    def test_largest_first_is_deterministic_without_mutating_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            units = []
            for name, size in (("a", 1), ("c", 3), ("b", 3)):
                path = Path(tmp) / name
                path.write_bytes(b"x" * size)
                units.append(SourceUnit("archive", str(path), name))
            self.assertEqual([u.output_relative for u in largest_first(units)], ["b", "c", "a"])
            self.assertEqual([u.output_relative for u in units], ["a", "c", "b"])

    def test_packed_weight_only_counts_contiguous_canonical_components(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for component in ("meta", "data", "videos"):
                (root / f"{component}.tar.gz.000").write_bytes(b"123")
            (root / "unrelated.tar.gz.000").write_bytes(b"ignore")
            self.assertEqual(source_size(SourceUnit("packed_simulation", str(root), "sim")), 9)
            (root / "videos.tar.gz.002").write_bytes(b"gap")
            with self.assertRaises(ValueError):
                source_size(SourceUnit("packed_simulation", str(root), "sim"))

    def fixture(self):
        return {"fps": 30, "robot_type": "g2a", "features": {
            "observation.images.top_head": {"dtype": "video", "shape": [400, 640, 3],
                                             "info": {"video.codec": "libdav1d"}},
            "state.waist": {"dtype": "float32", "shape": [5]},
        }}

    def test_reader_encoder_defaults_do_not_change_identity(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after["features"]["observation.images.top_head"]["info"].update({
            "video.crf": None, "video.video_backend": "pyav", "video.g": None,
            "video.fast_decode": None, "video.extra_options": None, "video.preset": None})
        self.assertEqual(dataset_name(before), dataset_name(after))

    def test_incompatible_camera_shape_splits_dataset(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after["features"]["observation.images.top_head"]["shape"] = [800, 1280, 3]
        self.assertNotEqual(dataset_name(before), dataset_name(after))

    def test_extra_rl_columns_are_not_silently_merged(self):
        before = self.fixture()
        after = copy.deepcopy(before)
        after["features"]["reward"] = {"dtype": "float32", "shape": [1]}
        self.assertNotEqual(dataset_name(before), dataset_name(after))
        self.assertIn("_rl_", dataset_name(after))
