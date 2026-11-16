"""Plan standard LeRobot video shards and materialize each shard only once."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import shutil
import subprocess
import tempfile


class VideoShardPlanner:
    """Drop-in aggregate_videos callback; metadata stays owned by LeRobot.

    Source files must remain present until finish() succeeds. Size rotation uses
    summed source sizes, avoiding repeated remuxing just to measure output size.
    """

    def __init__(self, workers: int = 8):
        if workers < 1:
            raise ValueError("Video merge workers must be positive")
        self.workers = workers
        self.shards = {}
        self.sizes = {}

    def __call__(self, src_meta, dst_meta, videos_idx, video_files_size_in_mb,
                 chunk_size, concatenate_videos=True):
        from lerobot.datasets import aggregate as api

        for key, idx in videos_idx.items():
            idx["episode_duration"] = 0
            idx["src_to_offset"] = {}
            idx["src_to_dst"] = {}
            durations = idx.setdefault("dst_file_durations", {})
            pairs = sorted(set(zip(
                src_meta.episodes[f"videos/{key}/chunk_index"],
                src_meta.episodes[f"videos/{key}/file_index"],
                strict=True,
            )))
            chunk, file = idx["chunk"], idx["file"]
            for src_chunk, src_file in pairs:
                src = src_meta.root / api.DEFAULT_VIDEO_PATH.format(
                    video_key=key, chunk_index=src_chunk, file_index=src_file)
                duration = api.get_video_duration_in_s(src)
                size = api.get_file_size_in_mb(src)
                dst = dst_meta.root / api.DEFAULT_VIDEO_PATH.format(
                    video_key=key, chunk_index=chunk, file_index=file)
                if dst in self.shards and (
                    not concatenate_videos or self.sizes[dst] + size >= video_files_size_in_mb
                ):
                    chunk, file = api.update_chunk_file_indices(chunk, file, chunk_size)
                    dst = dst_meta.root / api.DEFAULT_VIDEO_PATH.format(
                        video_key=key, chunk_index=chunk, file_index=file)
                dst_pair = (chunk, file)
                offset = durations.get(dst_pair, 0.0)
                idx["src_to_offset"][(src_chunk, src_file)] = offset
                idx["src_to_dst"][(src_chunk, src_file)] = dst_pair
                durations[dst_pair] = offset + duration
                idx["episode_duration"] += duration
                self.shards.setdefault(dst, []).append(src)
                self.sizes[dst] = self.sizes.get(dst, 0.0) + size
            idx["chunk"], idx["file"] = chunk, file
        return videos_idx

    def finish(self):
        # A separate FFmpeg process per shard avoids a Python packet-remux loop.
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            list(pool.map(_write_shard, self.shards.items()))


def _write_shard(item):
    dst, sources = item
    from lerobot.datasets.video_utils import get_video_info

    # Preserve the upstream compatibility checks before lossless stream copy.
    fields = ("video.height", "video.width", "video.fps", "video.codec", "video.pix_fmt")
    reference = None
    for src in sources:
        info = get_video_info(src)
        signature = tuple(info[k] for k in fields)
        if reference is not None and signature != reference:
            raise ValueError(f"Incompatible source video for shard {dst}: {src}")
        reference = signature
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        raise FileExistsError(f"Refusing to replace video shard: {dst}")
    with tempfile.TemporaryDirectory(prefix=".video-shard-", dir=dst.parent) as tmp:
        tmp = Path(tmp)
        output = tmp / "result.mp4"
        if len(sources) == 1:
            shutil.copyfile(sources[0], output)
        else:
            manifest = tmp / "inputs.ffconcat"
            lines = ["ffconcat version 1.0"]
            for src in sources:
                value = str(src.resolve())
                if "\n" in value or "\r" in value:
                    raise ValueError("Newlines are not supported in video paths")
                lines.append("file '" + value.replace("'", "'\\''") + "'")
            manifest.write_text("\n".join(lines) + "\n")
            result = subprocess.run([
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
                "-f", "concat", "-safe", "0", "-i", str(manifest),
                "-map", "0", "-c", "copy", "-movflags", "+faststart", str(output),
            ], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f"Video shard merge failed for {dst}: {result.stderr[-4000:]}")
        os.replace(output, dst)
