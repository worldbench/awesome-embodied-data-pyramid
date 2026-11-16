"""Read packed release leaves without changing the downloaded source tree."""
from __future__ import annotations

import io
import json
import shutil
import tarfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


class JoinedParts(io.RawIOBase):
    """Sequential reader for the numbered chunks of one gzip stream."""

    def __init__(self, paths):
        self.paths = iter(paths)
        self.current = None

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            if self.current is None:
                path = next(self.paths, None)
                if path is None:
                    return 0
                self.current = path.open("rb")
            size = self.current.readinto(buffer)
            if size:
                return size
            self.current.close()
            self.current = None

    def close(self):
        if self.current:
            self.current.close()
        super().close()


def split_parts(leaf: Path, component: str) -> list[Path]:
    paths = sorted(leaf.glob(f"{component}.tar.gz.[0-9][0-9][0-9]"))
    if not paths or [int(p.suffix[1:]) for p in paths] != list(range(len(paths))):
        raise ValueError(f"Missing or non-contiguous {component} archive parts in {leaf}")
    return paths


@contextmanager
def open_tar(paths):
    with io.BufferedReader(JoinedParts(paths), buffer_size=1024 * 1024) as stream:
        with tarfile.open(fileobj=stream, mode="r|gz") as archive:
            yield archive


def _relative_member(name: str) -> Path:
    parts = PurePosixPath(name).parts
    if PurePosixPath(name).is_absolute() or ".." in parts:
        raise ValueError(f"Unsafe archive path: {name}")
    # Real archives wrap the v2.1 root in data/; simulation components do not.
    for index, item in enumerate(parts):
        if item == "meta" or item == "videos" or (
            item == "data" and index + 1 < len(parts) and parts[index + 1].startswith("chunk-")
        ):
            return Path(*parts[index:])
    return Path(*parts)


def extract_regular(archive, member, destination):
    if not member.isfile():
        raise ValueError(f"Only regular archive members are accepted: {member.name}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with archive.extractfile(member) as source, destination.open("wb") as output:
        shutil.copyfileobj(source, output, length=1024 * 1024)


def extract_simulation(leaf: Path, destination: Path):
    for component in ("meta", "data", "videos"):
        with open_tar(split_parts(leaf, component)) as archive:
            for member in archive:
                if member.isdir():
                    continue
                relative = _relative_member(member.name)
                extract_regular(archive, member, destination / relative)


def prepare_one_episode(source: Path, destination: Path) -> dict:
    """Stream only metadata and episode zero out of a real or split sim archive.

    Gzip still requires reading past unselected members, but only one episode
    occupies output storage. Stop once all selected cameras have been read.
    """
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True)
    components = [split_parts(source, kind) for kind in ("meta", "data", "videos")] if source.is_dir() else [[source]]
    required_meta = {"info.json", "tasks.jsonl", "episodes.jsonl", "episodes_stats.jsonl"}
    expected = None
    seen = set()
    info = None
    for paths in components:
        with open_tar(paths) as archive:
            for member in archive:
                if not member.isfile():
                    if member.issym() or member.islnk():
                        raise ValueError(f"Unexpected source link: {member.name}")
                    continue
                rel = _relative_member(member.name)
                selected = (
                    rel.parent == Path("meta") and rel.name in required_meta
                ) or (
                    rel.parts[0] in {"data", "videos"}
                    and rel.name in {"episode_000000.parquet", "episode_000000.mp4"}
                )
                if selected:
                    extract_regular(archive, member, destination / rel)
                    seen.add(rel.as_posix())
                    if rel == Path("meta/info.json"):
                        info = json.loads((destination / rel).read_text())
                        expected = {f"meta/{n}" for n in required_meta}
                        expected.add(info["data_path"].format(episode_chunk=0, episode_index=0))
                        for key, feature in info["features"].items():
                            if feature["dtype"] == "video":
                                expected.add(info["video_path"].format(episode_chunk=0, episode_index=0, video_key=key))
                if expected and expected.issubset(seen):
                    break
        if expected and expected.issubset(seen):
            break
    if not expected or not expected.issubset(seen):
        raise ValueError(f"Incomplete smoke fixture from {source}: {sorted((expected or set()) - seen)}")
    episode = None
    for name in ("episodes.jsonl", "episodes_stats.jsonl"):
        path = destination / "meta" / name
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        selected = [row for row in records if row["episode_index"] == 0]
        if len(selected) != 1:
            raise ValueError(f"Expected exactly one episode zero in {path}")
        path.write_text(json.dumps(selected[0], ensure_ascii=False) + "\n")
        if name == "episodes.jsonl":
            episode = selected[0]
    source_counts = {k: info[k] for k in ("total_episodes", "total_frames")}
    info.update(total_episodes=1, total_frames=episode["length"], total_chunks=1,
                total_videos=sum(f["dtype"] == "video" for f in info["features"].values()),
                splits={"train": "0:1"})
    (destination / "meta/info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
    record = {"source": str(source), "episode_index": 0, "frames": episode["length"],
              "source_counts": source_counts, "extracted_files": sorted(seen)}
    (destination / "smoke_source.json").write_text(json.dumps(record, indent=2) + "\n")
    return record
