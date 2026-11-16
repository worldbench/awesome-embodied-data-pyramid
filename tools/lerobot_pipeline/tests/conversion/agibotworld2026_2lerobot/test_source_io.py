"""Release discovery and bounded archive-reading regression checks."""
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from agibotworld2026_2lerobot.source_io import JoinedParts, _relative_member, prepare_one_episode, split_parts
from agibotworld2026_2lerobot.convert_agibotworld2026 import discover_sources


class SourceIOTest(unittest.TestCase):
    def test_split_reader_and_missing_part(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, data in enumerate((b"abc", b"", b"defgh")):
                (root / f"data.tar.gz.{i:03d}").write_bytes(data)
            with io.BufferedReader(JoinedParts(split_parts(root, "data")), buffer_size=2) as stream:
                self.assertEqual(stream.read(), b"abcdefgh")
            (root / "data.tar.gz.001").unlink()
            with self.assertRaisesRegex(ValueError, "non-contiguous"):
                split_parts(root, "data")

    def test_traversal_rejected_and_wrapper_removed(self):
        for name in ("/etc/passwd", "data/../../escape", "../meta/info.json"):
            with self.assertRaises(ValueError):
                _relative_member(name)
        self.assertEqual(_relative_member("data/data/chunk-000/episode_000000.parquet"), Path("data/chunk-000/episode_000000.parquet"))

    def test_smoke_extracts_episode_zero_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            info = {"total_episodes": 2, "total_frames": 9, "chunks_size": 1000,
                    "data_path": "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet",
                    "video_path": "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4",
                    "features": {"observation.images.top_head": {"dtype": "video"}}}
            entries = {
                "data/data/chunk-000/episode_000000.parquet": b"selected",
                "data/data/chunk-000/episode_000001.parquet": b"skip",
                "data/meta/info.json": json.dumps(info).encode(),
                "data/meta/tasks.jsonl": b'{"task_index": 0, "task": "test"}\n',
                "data/meta/episodes.jsonl": b'{"episode_index":0,"length":4}\n{"episode_index":1,"length":5}\n',
                "data/meta/episodes_stats.jsonl": b'{"episode_index":0,"stats":{}}\n{"episode_index":1,"stats":{}}\n',
                "data/videos/chunk-000/observation.images.top_head/episode_000000.mp4": b"video",
            }
            archive = root / "source.tar.gz"
            with tarfile.open(archive, "w:gz") as output:
                for name, data in entries.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    output.addfile(member, io.BytesIO(data))
            fixture = root / "fixture"
            result = prepare_one_episode(archive, fixture)
            self.assertEqual(result["frames"], 4)
            self.assertFalse((fixture / "data/chunk-000/episode_000001.parquet").exists())
            self.assertEqual(json.loads((fixture / "meta/info.json").read_text())["total_episodes"], 1)

    def test_discovery_includes_rl_and_packed_simulation_not_depth_overlay(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path in ("ImitationLearning/task/a.tar.gz", "RichInteraction/task/b.tar.gz", "ReinforcementLearning/task/c.tar.gz", "simulation/task/g2/lite/meta.tar.gz.000", "simulation/task/g2/lite_depth_patch/meta.tar.gz.000"):
                file = root / path
                file.parent.mkdir(parents=True, exist_ok=True)
                file.touch()
            sources = discover_sources(root, "all", [], [])
            self.assertEqual(len(sources), 4)
            self.assertEqual(sum(s.kind == "packed_simulation" for s in sources), 1)


if __name__ == "__main__":
    unittest.main()
