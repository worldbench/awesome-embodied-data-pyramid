"""Frame-only v2 policy: exact quantile bounds, motion, FK (export), direction agreement.

Calibration is repository-local. Finite, mask-valid samples are written to temporary
channel files and partitioned one channel at a time; no random sampling is used.
"""

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import shutil
import tempfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from .adapters import resolve_adapter
from .schema import read_info
from .signal_quality import Thresholds, validate_repo, parquet_files, _episode_segments


@dataclass(frozen=True)
class FourRules:
    version: str = "four_rules_v1"
    alpha: float = 10.0
    motion_alpha: float = 10.0
    smoothing_frames: int = 5
    max_lag_frames: int = 15
    direction_min_speed: float = 0.01
    direction_min_agreement: float = 0.5
    min_moving_joints: int = 2

    def __post_init__(self):
        if self.version != "four_rules_v1":
            raise ValueError("unsupported four-rules version")
        for key in ("alpha", "motion_alpha", "direction_min_speed"):
            if not np.isfinite(getattr(self, key)) or getattr(self, key) < 0:
                raise ValueError(f"{key} must be finite and nonnegative")
        for key in ("smoothing_frames", "max_lag_frames", "min_moving_joints"):
            value = getattr(self, key)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < (0 if key == "max_lag_frames" else 1)
            ):
                raise ValueError(f"invalid {key}")
        if self.smoothing_frames % 2 != 1 or not 0 <= self.direction_min_agreement <= 1:
            raise ValueError("odd smoothing window and agreement in [0,1] required")


def episodes(repo, contract):
    """Yield complete episodes across file and record-batch boundaries, in source order."""
    parts, current, seen, size = [], None, set(), 0
    columns = ["episode_index", "frame_index", "timestamp", *contract.columns]
    for path in parquet_files(repo):
        for batch in pq.ParquetFile(path).iter_batches(columns=columns, batch_size=65536):
            table = pa.Table.from_batches([batch])
            ids = table["episode_index"].to_numpy()
            for start, end in _episode_segments(ids):
                ep = int(ids[start])
                if current is not None and ep != current:
                    seen.add(current)
                    yield pa.concat_tables(parts)
                    parts, size = [], 0
                if ep in seen:
                    raise ValueError(f"noncontiguous episode {ep}")
                current = ep
                parts.append(table.slice(start, end - start))
                size += end - start
                if size > 2_000_000:
                    raise ValueError(
                        "episode exceeds bounded-memory safety limit of 2 million frames"
                    )
    if parts:
        yield pa.concat_tables(parts)


def derivative(x, active, time, frames):
    result = np.full_like(x, np.nan, dtype=np.float64)
    dt = np.diff(time)
    okay = np.isfinite(dt) & (dt > 0) & (np.diff(frames) == 1)
    valid = active[1:] & active[:-1] & okay[:, None]
    with np.errstate(invalid="ignore", divide="ignore", over="ignore"):
        delta = np.diff(x, axis=0) / dt[:, None]
    result[1:] = np.where(valid & np.isfinite(delta), delta, np.nan)
    return result


def acceleration_of(velocity, time, frames):
    midpoints = np.r_[np.nan, (time[1:] + time[:-1]) / 2]
    return derivative(velocity, np.isfinite(velocity), midpoints, frames)


def channels(table, contract):
    arrays = contract.arrays(table)
    time = table["timestamp"].to_numpy().astype(np.float64)
    frames = table["frame_index"].to_numpy()
    raw, motion = {}, {}
    indices = [i for group in contract.arm_indices.values() for i in group]
    for key in contract.joint_keys:
        values = arrays[key][:, indices].astype(np.float64)
        active = contract.active_dimensions(key, arrays)[:, indices]
        raw[key] = np.where(active, values, np.nan)
    for key in contract.pose_keys:
        active = contract.active_dimensions(key, arrays)
        xyz = [i * 7 + j for i in range(len(contract.ee_sides)) for j in range(3)]
        raw[key + ".xyz"] = np.where(active[:, xyz], arrays[key][:, xyz], np.nan).astype(np.float64)
        for side in range(len(contract.ee_sides)):
            quat = arrays[key][:, side * 7 + 3 : side * 7 + 7].astype(np.float64)
            norm = np.linalg.norm(quat, axis=1)
            okay = active[:, side * 7] & np.isfinite(quat).all(axis=1) & (np.abs(norm - 1) <= 1e-3)
            safe = quat.copy()
            safe[~okay] = [0, 0, 0, 1]
            safe /= np.linalg.norm(safe, axis=1)[:, None]
            previous, current = safe[:-1], safe[1:]
            xyz = (
                -current[:, 3:] * previous[:, :3]
                + previous[:, 3:] * current[:, :3]
                - np.cross(current[:, :3], previous[:, :3])
            )
            w = np.sum(current * previous, axis=1)
            xyz *= np.where(w < 0, -1.0, 1.0)[:, None]
            norm_xyz = np.linalg.norm(xyz, axis=1)
            scale = np.divide(
                2 * np.arctan2(norm_xyz, np.abs(w)),
                norm_xyz,
                out=np.full_like(norm_xyz, 2.0),
                where=norm_xyz > 1e-15,
            )
            increments = xyz * scale[:, None]
            dt = np.diff(time)
            valid = okay[1:] & okay[:-1] & np.isfinite(dt) & (dt > 0) & (np.diff(frames) == 1)
            velocity = np.full((len(time), 3), np.nan)
            with np.errstate(divide="ignore", invalid="ignore"):
                # Express angular velocity in the common EE observation frame.
                velocity[1:] = np.where(valid[:, None], increments / dt[:, None], np.nan)
            motion[key + f".rotation{side}.velocity"] = velocity
            motion[key + f".rotation{side}.acceleration"] = acceleration_of(velocity, time, frames)
    for key in contract.extra_keys:
        raw[key] = np.where(contract.active_dimensions(key, arrays), arrays[key], np.nan).astype(
            np.float64
        )
    for key, value in raw.items():
        if "velocity" in key:
            continue  # Native velocity fields get range checking; do not treat as positions.
        velocity = derivative(value, np.isfinite(value), time, frames)
        motion[key + ".velocity"] = velocity
        motion[key + ".acceleration"] = acceleration_of(velocity, time, frames)
    return raw, motion, arrays, time, frames


def exact_bounds(path, alpha, absolute=False):
    values = np.fromfile(path, dtype=np.float64)
    if not len(values):
        return {"count": 0, "q01": None, "q99": None, "lower": None, "upper": None}
    # overwrite_input partitions this single channel in place, bounding peak memory.
    q01, q99 = np.quantile(values, [0.01, 0.99], overwrite_input=True, method="linear")
    span = q99 - q01
    return {
        "count": len(values),
        "q01": float(q01),
        "q99": float(q99),
        "lower": 0.0 if absolute else float(q01 - alpha * span),
        "upper": float(q99 + alpha * span),
    }


def calibrate(repo, contract, scratch, config, progress):
    handles, paths = {}, {}
    count = 0
    try:
        for table in episodes(repo, contract):
            raw, motion, *_ = channels(table, contract)
            for group, data in (("range", raw), ("motion", motion)):
                for key, value in data.items():
                    for dim in range(value.shape[1]):
                        name = f"{group}:{key}:{dim}"
                        if name not in handles:
                            paths[name] = scratch / f"{len(paths):04d}.bin"
                            handles[name] = paths[name].open("wb")
                        sample = value[:, dim]
                        sample = sample[np.isfinite(sample)]
                        if group == "motion":
                            sample = np.abs(sample)
                        handles[name].write(
                            np.ascontiguousarray(sample, dtype=np.float64).tobytes()
                        )
            count += len(table)
            if progress:
                progress({"phase": "calibration", "frames": count})
    finally:
        for handle in handles.values():
            handle.close()
    result = {}
    for i, (name, path) in enumerate(paths.items()):
        motion = name.startswith("motion:")
        result[name] = exact_bounds(path, config.motion_alpha if motion else config.alpha, motion)
        path.unlink()
        if progress:
            progress({"phase": "quantiles", "frames": count, "channels_done": i + 1})
    return result


def check_bounds(data, bounds, group, length):
    good, checked = np.ones(length, bool), np.zeros(length, bool)
    for key, value in data.items():
        for dim in range(value.shape[1]):
            bound = bounds[f"{group}:{key}:{dim}"]
            if not bound["count"]:
                continue
            x = np.abs(value[:, dim]) if group == "motion" else value[:, dim]
            finite = np.isfinite(x)
            checked |= finite
            good &= ~finite | ((x >= bound["lower"]) & (x <= bound["upper"]))
    return good, checked


def smooth_valid(x, window):
    radius = window // 2
    if len(x) < window:
        return np.full_like(x, np.nan)
    finite = np.isfinite(x)
    sums = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(np.where(finite, x, 0), axis=0)])
    counts = np.vstack([np.zeros((1, x.shape[1])), np.cumsum(finite, axis=0)])
    out = np.full_like(x, np.nan)
    stop = len(x) - radius if radius else len(x)
    out[radius:stop] = np.where(
        counts[window:] - counts[:-window] == window,
        (sums[window:] - sums[:-window]) / window,
        np.nan,
    )
    return out


def direction_check(raw, time, frames, config):
    n = len(time)
    good, checked = np.ones(n, bool), np.zeros(n, bool)
    if not {"state.qpos", "action.qpos"} <= raw.keys():
        return good, checked, {"reason": "missing comparable state/action joint positions"}
    state, action = (
        smooth_valid(raw[key], config.smoothing_frames) for key in ("state.qpos", "action.qpos")
    )
    # Split at index/time gaps before smoothing so no window bridges corrupt boundaries.
    boundary = np.r_[
        False, (np.diff(frames) != 1) | ~np.isfinite(np.diff(time)) | (np.diff(time) <= 0)
    ]
    for i in np.flatnonzero(boundary):
        lo, hi = max(0, i - config.smoothing_frames), min(n, i + config.smoothing_frames)
        state[lo:hi] = np.nan
        action[lo:hi] = np.nan
    sv = derivative(state, np.isfinite(state), time, frames)
    av = derivative(action, np.isfinite(action), time, frames)
    segments = np.cumsum(boundary)
    candidates = []
    for lag in range(-config.max_lag_frames, config.max_lag_frames + 1):
        ids = np.arange(max(0, -lag), min(n, n - lag))
        a, s = av[ids], sv[ids + lag]
        eligible = (
            np.isfinite(a)
            & np.isfinite(s)
            & (np.abs(a) > config.direction_min_speed)
            & (np.abs(s) > config.direction_min_speed)
        )
        eligible &= (segments[ids] == segments[ids + lag])[:, None]
        counts = eligible.sum(axis=1)
        enough = counts >= config.min_moving_joints
        agree = ((np.sign(a) == np.sign(s)) & eligible).sum(axis=1)
        total = int(counts[enough].sum())
        if total:
            score = float(agree[enough].sum() / total)
            candidates.append((score, -abs(lag), lag, ids, enough, agree, counts))
    if not candidates:
        return good, checked, {"reason": "no jointly moving mask-valid joint pairs"}
    _, _, lag, ids, eligible, agree, counts = max(candidates, key=lambda x: (x[0], x[1], -x[2]))
    checked[ids[eligible]] = True
    good[ids[eligible]] = agree[eligible] / counts[eligible] >= config.direction_min_agreement
    return (
        good,
        checked,
        {
            "lag_frames": lag,
            "agreement": float(agree[eligible].sum() / counts[eligible].sum()),
            "checked_frames": int(checked.sum()),
        },
    )


def validate_four(repo, output, *, adapter="auto", config=FourRules(), progress=None):
    output = Path(output)
    # Reuse numeric/mask/index safety checks, with the legacy per-frame jump rule disabled.
    base = validate_repo(
        repo,
        output,
        adapter=adapter,
        write_frames=True,
        thresholds=Thresholds(1e300, 1e300, 1e300),
        progress=progress,
    )
    contract = resolve_adapter(read_info(repo), adapter)
    scratch = Path(tempfile.mkdtemp(prefix=".calibration-", dir=output))
    try:
        bounds = calibrate(repo, contract, scratch, config, progress)
    finally:
        shutil.rmtree(scratch)
    from .export import FrameReader

    reader = FrameReader(output / "frames.parquet", 65536)
    temporary = output / "four-frames.parquet"
    writer = None
    counts = {
        k: 0
        for k in (
            "frames",
            "range_failed",
            "range_checked",
            "velocity_failed",
            "acceleration_failed",
            "motion_checked",
            "state_action_failed",
            "state_action_checked",
            "invalid_frames",
        )
    }
    details = {}
    try:
        for table in episodes(repo, contract):
            raw, motion, arrays, time, frames = channels(table, contract)
            baseline = reader.take(len(table))
            for key in ("episode_index", "frame_index"):
                if not np.array_equal(table[key].to_numpy(), baseline[key].to_numpy()):
                    raise ValueError("source and basic safety report are misaligned")
            ranges, rc = check_bounds(raw, bounds, "range", len(table))
            velocity, vc = check_bounds(
                {k: v for k, v in motion.items() if k.endswith(".velocity")},
                bounds,
                "motion",
                len(table),
            )
            acceleration, ac = check_bounds(
                {k: v for k, v in motion.items() if k.endswith(".acceleration")},
                bounds,
                "motion",
                len(table),
            )
            direction, dc, detail = direction_check(raw, time, frames, config)
            details[str(table["episode_index"][0].as_py())] = detail
            timestamp_ok = np.isfinite(time) & np.r_[True, np.diff(time) > 0]
            valid = (
                baseline["signal_quality_valid"].to_numpy()
                & timestamp_ok
                & ranges
                & velocity
                & acceleration
                & direction
            )
            columns = {
                name: baseline[name]
                for name in baseline.column_names
                if name not in ("sudden_change_valid", "signal_quality_valid")
            }
            columns.update(
                timestamp_valid=timestamp_ok,
                range_valid=ranges,
                range_checked=rc,
                velocity_valid=velocity,
                acceleration_valid=acceleration,
                motion_checked=vc | ac,
                state_action_valid=direction,
                state_action_checked=dc,
                signal_quality_valid=valid,
            )
            part = pa.table(columns)
            if writer is None:
                writer = pq.ParquetWriter(temporary, part.schema, compression="zstd")
            writer.write_table(part)
            counts["frames"] += len(table)
            for name, mask in [
                ("range_failed", ~ranges),
                ("range_checked", rc),
                ("velocity_failed", ~velocity),
                ("acceleration_failed", ~acceleration),
                ("motion_checked", vc | ac),
                ("state_action_failed", ~direction),
                ("state_action_checked", dc),
                ("invalid_frames", ~valid),
            ]:
                counts[name] += int(mask.sum())
            if progress:
                progress({"phase": "signal", "frames": counts["frames"]})
        reader.assert_exhausted()
    finally:
        if writer:
            writer.close()
    temporary.replace(output / "frames.parquet")
    summary = {
        **base,
        **counts,
        "schema_version": "lerobot_four_rules_signal_v1",
        "four_rules": asdict(config),
        "thresholds": {"calibrated_bounds": "bounds.json"},
        "threshold_semantics": "source units per second and per second squared; repository exact finite valid quantiles",
        "sudden_change": None,
        "retained_episodes_all_frames_valid": None,
        "rejected_episodes": None,
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (output / "bounds.json").write_text(json.dumps(bounds, indent=2, allow_nan=False) + "\n")
    (output / "state_action_episodes.json").write_text(json.dumps(details, indent=2) + "\n")
    # The legacy episodes file describes only safety checks, so name it accordingly.
    (output / "episodes.json").rename(output / "basic_safety_episodes.json")
    return summary
