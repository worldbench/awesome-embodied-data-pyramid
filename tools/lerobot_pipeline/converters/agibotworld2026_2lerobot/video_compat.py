"""Native PNG16 depth reads and bounded, real-video statistics for this release.

LeRobot 0.6.1 assumes its own 12-bit quantized depth encoder. AgiBot uses
unquantized 16-bit PNG. Never run that stream through the 12-bit dequantizer.
"""
from __future__ import annotations

import json
from pathlib import Path

import av
import numpy as np


VIDEO_STATS_VERSION = "native_video_stats_v2"
MAX_STATS_FRAMES = 32


def frame_at(container, timestamp, *, depth=False, tolerance=1e-4):
    stream = container.streams.video[0]
    container.seek(max(0, round(timestamp / stream.time_base) - 1), stream=stream,
                   backward=True, any_frame=False)
    closest = None
    distance = float("inf")
    for frame in container.decode(stream):
        if frame.pts is None:
            continue
        actual = float(frame.pts * stream.time_base)
        error = abs(actual - timestamp)
        if error < distance:
            closest, distance = frame, error
        if actual >= timestamp - tolerance:
            break
    if closest is None or distance > tolerance:
        raise ValueError(f"No synchronized video frame at {timestamp}; error={distance}")
    if depth:
        # gray16be -> native uint16 changes endianness only, not bit depth.
        return closest.to_ndarray(format="gray16le").astype(np.uint16)[None]
    return closest.to_ndarray(format="rgb24").transpose(2, 0, 1)


def sample_video_episodes(root, info, episodes, key, depth, *, workers=1, decoder_threads=None):
    from concurrent.futures import ThreadPoolExecutor
    from lerobot.datasets.compute_stats import auto_downsample_height_width, get_feature_stats

    def sample(episode):
        index = int(episode["episode_index"])
        length = int(episode["length"])
        indices = np.unique(np.round(np.linspace(0, length - 1, min(MAX_STATS_FRAMES, length))).astype(int))
        path = root / info["video_path"].format(
            video_key=key, chunk_index=episode[f"videos/{key}/chunk_index"],
            file_index=episode[f"videos/{key}/file_index"])
        start = episode[f"videos/{key}/from_timestamp"]
        with av.open(str(path)) as container:
            if decoder_threads is not None:
                container.streams.video[0].thread_count = decoder_threads
            images = np.stack([auto_downsample_height_width(frame_at(
                container, start + int(i) / info["fps"], depth=depth)) for i in indices])
        values = get_feature_stats(images, axis=(0, 2, 3), keepdims=True)
        factor = 1.0 if depth else 255.0
        return index, {k: v if k == "count" else np.squeeze(v / factor, axis=0) for k, v in values.items()}

    if workers == 1:
        return dict(map(sample, episodes))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return dict(pool.map(sample, episodes))


def repair_video_metadata_stats(root: Path, *, workers=1, decoder_threads=None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from lerobot.datasets.compute_stats import aggregate_stats, auto_downsample_height_width, get_feature_stats
    try:
        from lerobot.datasets.io_utils import load_stats, write_stats
    except ImportError:
        from lerobot.datasets.utils import load_stats, write_stats
    from agibotworld2026_2lerobot.convert_agibotworld2026 import _write_json_atomic, _write_parquet_atomic

    info_path = root / "meta/info.json"
    info = json.loads(info_path.read_text())
    stats = load_stats(root)
    episode_paths = sorted(root.glob("meta/episodes/chunk-*/*.parquet"))
    tables = {path: pq.read_table(path) for path in episode_paths}
    episodes = [row for table in tables.values() for row in table.to_pylist()]
    repairs, missing_units = {}, []
    for key, feature in info["features"].items():
        if feature["dtype"] != "video":
            continue
        video_info = {**feature.get("video_info", {}), **feature.get("info", {})}
        depth = bool(video_info.get("is_depth_map", video_info.get("video.is_depth_map", False)))
        if depth:
            if video_info.get("video.pix_fmt") not in ("gray16be", "gray16le"):
                raise ValueError(f"Unsupported native depth encoding: {key}: {video_info}")
            video_info["is_depth_map"] = True
            video_info["agibot_native_depth"] = True
            feature["shape"][-1] = 1
            if not video_info.get("depth_unit"):
                missing_units.append(key)
        if depth:
            # 0.6.1 constructs its DepthEncoderConfig even for a read-only
            # dataset and rejects PNG as an encoder. Keep true source codec
            # details in legacy video_info, away from that encoder parser.
            feature["video_info"] = video_info
            feature["info"] = {"is_depth_map": True, "agibot_native_depth": True}
            if "depth_unit" in video_info:
                feature["info"]["depth_unit"] = video_info["depth_unit"]
        else:
            feature["info"] = video_info
            feature.pop("video_info", None)
        count = stats.get(key, {}).get("count", [0])
        bad = (not np.all(np.asarray(count) > 0)
               or any(not np.isfinite(value).all() for value in stats.get(key, {}).values())
               or np.asarray(stats.get(key, {}).get("mean", [])).shape != (feature["shape"][-1], 1, 1))
        if not bad:
            continue
        print(f"Sampling video statistics ({MAX_STATS_FRAMES}/episode max): {key}", flush=True)
        sampled = sample_video_episodes(root, info, episodes, key, depth,
                                        workers=workers, decoder_threads=decoder_threads)
        for path, table in tables.items():
            replaced = table.drop([name for name in table.column_names if name.startswith(f"stats/{key}/")])
            for statistic in next(iter(sampled.values())):
                values = [sampled[int(i)][statistic].tolist() for i in table["episode_index"].to_pylist()]
                replaced = replaced.append_column(f"stats/{key}/{statistic}", pa.array(values))
            tables[path] = replaced
        stats[key] = aggregate_stats([{key: value} for value in sampled.values()])[key]
        repairs[key] = {"episodes": len(sampled), "sampled_frames": sum(int(v["count"][0]) for v in sampled.values()),
                        "value_scale": "native depth codes" if depth else "RGB / 255"}
    for path, table in tables.items():
        _write_parquet_atomic(table.replace_schema_metadata(None), path, pq)
    write_stats(stats, root)
    _write_json_atomic(info_path, info)
    result = {"version": VIDEO_STATS_VERSION, "method": "uniformly sampled frames, spatially subsampled using LeRobot auto_downsample_height_width",
              "episode_workers": workers, "decoder_threads": decoder_threads,
              "max_frames_per_episode": MAX_STATS_FRAMES, "repaired": repairs,
              "depth_units_unspecified": missing_units,
              "native_depth_reader": "agibotworld2026_2lerobot.native_dataset.AgiBotWorldDataset" if missing_units else None}
    _write_json_atomic(root / "meta/video_compat.json", result)
    return result
