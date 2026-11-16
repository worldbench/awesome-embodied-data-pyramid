"""Numerical, metadata and real LeRobot reader checks for conversion review."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from agibotworld2026_2lerobot.convert_agibotworld2026 import (
    FieldMapping, NEW_NUMERIC_KEYS, map_robot_vectors,
)


def array(column):
    return np.asarray(column.to_pylist(), dtype=np.float32)


def validate_part(source: Path, output: Path):
    info = json.loads((source / "meta/info.json").read_text())
    mapping = FieldMapping.from_info(info)
    original = pq.read_table(source / info["data_path"].format(episode_chunk=0, episode_index=0))
    converted = pq.read_table(sorted(output.glob("data/chunk-*/*.parquet")))
    if len(original) != len(converted):
        raise AssertionError("Smoke conversion changed frame count")
    expected = map_robot_vectors(array(original["observation.state"]), array(original["action"]), mapping)
    errors = {}
    for key, values in expected.items():
        actual = array(converted[key])
        np.testing.assert_array_equal(actual, values, err_msg=key)
        errors[key] = float(np.max(np.abs(actual - values)))
    # Independent assertion against native waist columns, not just mapper output.
    for prefix, source_key in (("state", "observation.state"), ("action", "action")):
        indices = info["features"][source_key]["field_descriptions"][f"{prefix}/waist/position"]["indices"]
        np.testing.assert_array_equal(array(converted[f"{prefix}.waist"]), array(original[source_key])[:, indices])
    retained = [key for key in original.column_names if key not in ("observation.state", "action") and not key.startswith("observation.images.")]
    for key in retained:
        np.testing.assert_equal(original[key].to_pylist(), converted[key].to_pylist(), err_msg=key)
    return {"status": "passed", "frames": len(original), "max_absolute_errors": errors,
            "native_waist_indices": {"state": list(mapping.state_waist), "action": list(mapping.action_waist)},
            "retained_columns_checked": retained}


def validate_dataset(root: Path):
    import av
    from agibotworld2026_2lerobot.native_dataset import AgiBotWorldDataset
    from agibotworld2026_2lerobot.video_compat import frame_at
    from torch.utils.data import DataLoader

    info = json.loads((root / "meta/info.json").read_text())
    stats = json.loads((root / "meta/stats.json").read_text())
    table = pq.read_table(sorted(root.glob("data/chunk-*/*.parquet")))
    episodes = pq.read_table(sorted(root.glob("meta/episodes/chunk-*/*.parquet")))
    assert info["codebase_version"] == "v3.0"
    assert len(table) == info["total_frames"]
    assert len(episodes) == info["total_episodes"]
    np.testing.assert_array_equal(table["index"].to_numpy(), np.arange(len(table)))
    waist_ranges = {}
    numeric_arrays = {key: array(table[key]) for key in NEW_NUMERIC_KEYS}
    for key in NEW_NUMERIC_KEYS:
        values = numeric_arrays[key]
        assert values.shape == (len(table), info["features"][key]["shape"][0]), key
        assert np.isfinite(values).all(), key
        # Reference reductions need float64 too: long float32 sequences can
        # accumulate enough rounding error to reject correct stored statistics.
        for statistic, expected in (("min", values.min(axis=0)), ("max", values.max(axis=0)), ("mean", values.mean(axis=0, dtype=np.float64)), ("std", values.std(axis=0, dtype=np.float64))):
            np.testing.assert_allclose(stats[key][statistic], expected, atol=2e-5, rtol=2e-4, err_msg=f"{key}/{statistic}")
        for stat_values in stats[key].values():
            assert np.isfinite(stat_values).all(), f"nonfinite stats {key}"
        assert f"stats/{key}/mean" in episodes.column_names, key
        if key.endswith(".waist"):
            waist_ranges[key] = {"min": values.min(axis=0).tolist(), "max": values.max(axis=0).tolist()}
    videos = []
    camera_frames = {}
    for path in sorted(root.glob("videos/**/*.mp4")):
        probe = json.loads(subprocess.check_output([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
            "stream=codec_name,width,height,nb_frames,duration", "-of", "json", str(path)
        ], text=True))
        assert probe["streams"], path
        stream = probe["streams"][0]
        camera = path.relative_to(root).parts[1]
        feature = info["features"][camera]
        assert [stream["height"], stream["width"]] == feature["shape"][:2], camera
        camera_frames[camera] = camera_frames.get(camera, 0) + int(stream["nb_frames"])
        videos.append({"file": str(path.relative_to(root)), **stream})
    assert len(videos) >= sum(f["dtype"] == "video" for f in info["features"].values())
    for key, frames in camera_frames.items():
        assert frames == len(table), f"{key}: {frames} video frames vs {len(table)} data rows"
        assert np.asarray(stats[key]["mean"]).shape == (info["features"][key]["shape"][-1], 1, 1)
        assert np.all(np.asarray(stats[key]["count"]) > 0), key
        assert all(np.isfinite(value).all() for value in stats[key].values()), key
    dataset = AgiBotWorldDataset(repo_id=root.name, root=root, video_backend="pyav")
    indices = sorted({0, len(dataset) // 2, len(dataset) - 1,
                      *[int(x) for x in episodes["dataset_from_index"].to_pylist()],
                      *[int(x) - 1 for x in episodes["dataset_to_index"].to_pylist()]})
    samples = []
    for index in indices:
        sample = dataset[index]
        assert tuple(sample["state.waist"].shape) == (5,)
        assert tuple(sample["action.waist"].shape) == (5,)
        for key in NEW_NUMERIC_KEYS:
            np.testing.assert_array_equal(sample[key].numpy(), numeric_arrays[key][index], err_msg=f"reader {key}")
        cameras = {key: list(value.shape) for key, value in sample.items() if key.startswith("observation.images.")}
        assert len(cameras) == sum(f["dtype"] == "video" for f in info["features"].values())
        for key, shape in cameras.items():
            height, width, channels = info["features"][key]["shape"]
            assert shape == [channels, height, width], key
            assert np.isfinite(sample[key].numpy()).all(), key
            if (info["features"][key].get("info") or {}).get("agibot_native_depth"):
                episode_index = int(sample["episode_index"].item())
                episode = dataset.meta.episodes[episode_index]
                timestamp = float(sample["timestamp"].item()) + episode[f"videos/{key}/from_timestamp"]
                with av.open(str(root / dataset.meta.get_video_file_path(episode_index, key))) as container:
                    raw = frame_at(container, timestamp, depth=True)
                np.testing.assert_array_equal(sample[key].numpy(), raw, err_msg="native PNG16 depth")
        samples.append({"index": index, "cameras": cameras})
    batch = next(iter(DataLoader(dataset, batch_size=2, num_workers=0)))
    assert tuple(batch["state.waist"].shape) == (2, 5)
    return {"status": "passed", "episodes": len(episodes), "frames": len(table),
            "features": list(NEW_NUMERIC_KEYS), "waist_ranges": waist_ranges,
            "videos": videos, "reader_samples": samples, "dataloader_waist_shape": [2, 5],
            "video_stats": "finite, positive sample counts; image stats are sampled estimates",
            "reader": "agibotworld2026_2lerobot.native_dataset.AgiBotWorldDataset",
            "native_depth": "PNG16 codes checked exactly; physical depth unit not inferred"}
