import gzip
import io
import os
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agibotworld2026_2lerobot.fast_backend import decompressed_tar, extract_source, link_immutable
from agibotworld2026_2lerobot.convert_agibotworld2026 import SourceUnit
from agibotworld2026_2lerobot.fast_aggregate import aggregate_video_links


def archive_bytes(entries):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, data in entries:
            item = tarfile.TarInfo(name)
            item.size = len(data)
            archive.addfile(item, io.BytesIO(data))
    return gzip.compress(buffer.getvalue())


class FastBackendTest(unittest.TestCase):
    def test_hardlinks_are_not_symlinks_and_survive_source_unlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src, dst = root / "a.mp4", root / "nested/b.mp4"
            src.write_bytes(b"immutable video bytes")
            link_immutable(src, dst)
            self.assertEqual(src.stat().st_ino, dst.stat().st_ino)
            self.assertFalse(dst.is_symlink())
            with self.assertRaises(OSError):
                link_immutable(src, dst)
            src.unlink()
            self.assertEqual(dst.read_bytes(), b"immutable video bytes")

    def test_linking_a_source_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").write_bytes(b"x")
            (root / "link").symlink_to(root / "src")
            with self.assertRaises(ValueError):
                link_immutable(root / "link", root / "destination")

    def test_split_gzip_stream_is_joined_before_inflate(self):
        content = archive_bytes([("meta/info.json", b"{}"), ("data/a", b"payload")])
        with tempfile.TemporaryDirectory() as tmp:
            parts = [Path(tmp) / str(i) for i in range(3)]
            cut = len(content)//3
            for index, part in enumerate(parts):
                part.write_bytes(content[index*cut:(index+1)*cut] if index < 2 else content[2*cut:])
            with decompressed_tar(parts) as archive:
                actual = {m.name: archive.extractfile(m).read() for m in archive}
            self.assertEqual(actual, {"meta/info.json": b"{}", "data/a": b"payload"})

    def test_private_extraction_preserves_source_archive(self):
        content = archive_bytes([("data/meta/info.json", b"{}"), ("data/videos/chunk-000/a/episode_000000.mp4", b"video")])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source.tar.gz"
            path.write_bytes(content)
            output, owned = extract_source(SourceUnit("archive", str(path), "unit"), root / "out")
            self.assertTrue(owned)
            self.assertEqual((output / "meta/info.json").read_bytes(), b"{}")
            self.assertEqual(path.read_bytes(), content)

    def test_gzip_crc_failure_is_not_accepted(self):
        content = bytearray(archive_bytes([("meta/info.json", b"{}")]))
        content[-8] ^= 0xFF
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.gz"
            path.write_bytes(content)
            with self.assertRaises((RuntimeError, OSError, EOFError)):
                with decompressed_tar([path]) as archive:
                    list(archive)

    def test_python_fallback_also_checks_gzip_crc(self):
        content = bytearray(archive_bytes([("meta/info.json", b"{}")]))
        content[-8] ^= 0xFF
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.gz"
            path.write_bytes(content)
            with patch("agibotworld2026_2lerobot.fast_backend.shutil.which", return_value=None):
                with self.assertRaises((OSError, EOFError)):
                    with decompressed_tar([path]) as archive:
                        list(archive)

    def test_extraction_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "source.tar.gz"
            path.write_bytes(archive_bytes([("data/../../outside", b"no")]))
            with self.assertRaises(ValueError):
                extract_source(SourceUnit("archive", str(path), "unit"), root / "out")
            self.assertFalse((root / "outside").exists())

    def test_video_mapping_rotates_chunks_without_copy_or_time_shift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key = "observation.images.top_head"
            src_root, dst_root = root / "src", root / "dst"
            for index in range(3):
                p = src_root / f"videos/{key}/chunk-000/file-{index:03d}.mp4"
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(bytes([index]))
            source = SimpleNamespace(root=src_root, episodes={
                f"videos/{key}/chunk_index": [0, 0, 0], f"videos/{key}/file_index": [0, 1, 2]})
            destination = SimpleNamespace(root=dst_root)
            state = {key: {"chunk": 0, "file": 0, "latest_duration": 0.0, "episode_duration": 0.0}}
            aggregate_video_links(source, destination, state, chunk_size=2)
            self.assertEqual(state[key]["src_to_dst"], {(0, 0): (0, 0), (0, 1): (0, 1), (0, 2): (1, 0)})
            self.assertEqual(set(state[key]["src_to_offset"].values()), {0.0})
            self.assertEqual((dst_root / f"videos/{key}/chunk-001/file-000.mp4").stat().st_ino,
                             (src_root / f"videos/{key}/chunk-000/file-002.mp4").stat().st_ino)
