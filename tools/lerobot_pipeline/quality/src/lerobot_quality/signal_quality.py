"""Validate robot signals through embodiment adapters and shared quality rules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .schema import read_info


def parquet_files(repo: Path) -> list[Path]:
    result = sorted((repo / "data").rglob("*.parquet"))
    if not result:
        raise FileNotFoundError(f"no parquet files under {repo / 'data'}")
    return result


def quaternion_step_deg(previous: np.ndarray, current: np.ndarray) -> np.ndarray:
    previous_norm = np.linalg.norm(previous, axis=1)
    current_norm = np.linalg.norm(current, axis=1)
    valid = (previous_norm > 1e-12) & (current_norm > 1e-12)
    dot = np.zeros(len(previous), dtype=np.float64)
    dot[valid] = np.abs(
        np.sum(previous[valid] * current[valid], axis=1)
        / (previous_norm[valid] * current_norm[valid])
    )
    result = np.full(len(previous), np.nan)
    result[valid] = np.degrees(2.0 * np.arccos(np.clip(dot[valid], 0.0, 1.0)))
    return result


@dataclass(frozen=True)
class Thresholds:
    joint_step_rad: float = 0.35
    ee_position_step_m: float = 0.10
    ee_rotation_step_deg: float = 30.0


def _episode_segments(episodes: np.ndarray) -> list[tuple[int, int]]:
    if not len(episodes):
        return []
    starts = np.r_[0, np.flatnonzero(episodes[1:] != episodes[:-1]) + 1]
    ends = np.r_[starts[1:], len(episodes)]
    return [(int(start), int(end)) for start, end in zip(starts, ends, strict=True)]


def _check_output(repo: Path, output: Path) -> None:
    source, destination = repo.resolve(), output.resolve()
    if destination == source or source in destination.parents or destination in source.parents:
        raise ValueError("report output must be outside the source repository and its parents")
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"report directory is not empty: {output}")


def validate_repo(
    repo: Path,
    output: Path,
    *,
    thresholds: Thresholds = Thresholds(),
    write_frames: bool = False,
    adapter: str = "auto",
    max_frames: int | None = None,
    require_action_targets: bool = False,
    require_ee_targets: bool = False,
    progress=None,
) -> dict:
    from .adapters import resolve_adapter

    _check_output(repo, output)
    if max_frames is not None and max_frames < 1:
        raise ValueError("max_frames must be positive")
    limits = (
        thresholds.joint_step_rad,
        thresholds.ee_position_step_m,
        thresholds.ee_rotation_step_deg,
    )
    if not all(np.isfinite(v) and v > 0 for v in limits):
        raise ValueError("thresholds must be finite and positive")
    info = read_info(repo)
    contract = resolve_adapter(info, adapter)
    if require_action_targets and "action.qpos_valid" not in contract.columns:
        raise ValueError("action-target policy requires an explicit action.qpos_valid mask")
    if require_ee_targets and set(contract.pose_keys) != {"state.ee", "action.ee"}:
        raise ValueError("EE-target policy requires verified state/action xyz_xyzw poses and masks")
    if progress:
        progress({"phase": "signal", "frames": 0})
    counts = dict.fromkeys(
        (
            "frames",
            "qpos_non_finite",
            "ee_invalid_numeric",
            "invalid_mask",
            "extra_non_finite",
            "non_contiguous_frame",
            "sudden_change",
            "target_policy_rejected",
            "invalid_frames",
        ),
        0,
    )
    mask_coverage = {
        k: [0] * contract.profile["feature_widths"][k]
        for k in contract.columns
        if k.endswith("_valid")
    }
    episode_outcomes: dict[int, bool] = {}
    last: dict[int, dict] = {}
    writer = None
    output.mkdir(parents=True, exist_ok=True)

    def steps(previous: dict, current: dict) -> np.ndarray:
        n = len(next(iter(current.values())))
        good = np.ones(n, dtype=bool)
        joint_indices = [i for group in contract.arm_indices.values() for i in group]
        for key in contract.joint_keys:
            active = contract.active_dimensions(key, previous) & contract.active_dimensions(
                key, current
            )
            delta_ok = np.abs(current[key] - previous[key]) <= thresholds.joint_step_rad
            good &= (~active[:, joint_indices] | delta_ok[:, joint_indices]).all(axis=1)
        for key in contract.pose_keys:
            for i, _side in enumerate(contract.ee_sides):
                active = (previous[key + "_valid"][:, i] == 1) & (
                    current[key + "_valid"][:, i] == 1
                )
                a, b = previous[key][:, i * 7 : (i + 1) * 7], current[key][:, i * 7 : (i + 1) * 7]
                okay = np.linalg.norm(b[:, :3] - a[:, :3], axis=1) <= thresholds.ee_position_step_m
                okay &= quaternion_step_deg(a[:, 3:7], b[:, 3:7]) <= thresholds.ee_rotation_step_deg
                good &= ~active | okay
        return good

    try:
        for parquet in parquet_files(repo):
            file = pq.ParquetFile(parquet)
            available = set(file.schema_arrow.names)
            index_key = (
                "frame_index"
                if "frame_index" in available
                else "index" if "index" in available else None
            )
            if index_key is None:
                raise ValueError(
                    f"{parquet}: frame_index or index is required for continuity checks"
                )
            columns = ["episode_index", index_key, *contract.columns]
            missing = set(columns) - available
            if missing:
                raise ValueError(f"{parquet}: missing declared columns {sorted(missing)}")
            for record in file.iter_batches(batch_size=65536, columns=columns):
                table = pa.Table.from_batches([record])
                if max_frames is not None:
                    table = table.slice(0, max(0, max_frames - counts["frames"]))
                if not len(table):
                    break
                arrays = contract.arrays(table)
                episodes = np.asarray(table["episode_index"].to_numpy(), dtype=np.int64)
                frames = np.asarray(table[index_key].to_numpy(), dtype=np.int64)
                n = len(table)
                qpos_ok = np.ones(n, dtype=bool)
                for key in contract.joint_keys:
                    qpos_ok &= np.isfinite(arrays[key]).all(axis=1)
                mask_ok, ee_ok, extra_ok, target_ok = [np.ones(n, dtype=bool) for _ in range(4)]
                for key in mask_coverage:
                    raw = arrays[key]
                    mask_ok &= np.isin(raw, (0, 1)).all(axis=1)
                    for i in range(raw.shape[1]):
                        mask_coverage[key][i] += int((raw[:, i] == 1).sum())
                for key in contract.pose_keys:
                    for i, _side in enumerate(contract.ee_sides):
                        pose = arrays[key][:, i * 7 : (i + 1) * 7]
                        active = arrays[key + "_valid"][:, i] == 1
                        numeric = np.isfinite(pose).all(axis=1)
                        numeric &= np.abs(np.linalg.norm(pose[:, 3:7], axis=1) - 1.0) <= 1e-3
                        ee_ok &= ~active | numeric
                for key in contract.extra_keys:
                    active = contract.active_dimensions(key, arrays)
                    extra_ok &= (~active | np.isfinite(arrays[key])).all(axis=1)
                if require_action_targets:
                    target_ok &= (arrays["action.qpos_valid"] == 1).all(axis=1)
                if require_ee_targets:
                    for key in contract.pose_keys:
                        target_ok &= (arrays[key + "_valid"] == 1).all(axis=1)
                contiguous, smooth = np.ones(n, dtype=bool), np.ones(n, dtype=bool)
                for start, end in _episode_segments(episodes):
                    episode = int(episodes[start])
                    contiguous[start + 1 : end] = np.diff(frames[start:end]) == 1
                    previous = last.get(episode)
                    if previous is not None:
                        contiguous[start] = frames[start] == previous["frame"] + 1
                        smooth[start] = steps(
                            previous["arrays"], {k: v[start : start + 1] for k, v in arrays.items()}
                        )[0]
                    if end - start > 1:
                        smooth[start + 1 : end] = steps(
                            {k: v[start : end - 1] for k, v in arrays.items()},
                            {k: v[start + 1 : end] for k, v in arrays.items()},
                        )
                    last[episode] = {
                        "frame": int(frames[end - 1]),
                        "arrays": {k: v[end - 1 : end].copy() for k, v in arrays.items()},
                    }
                quality = qpos_ok & mask_ok & ee_ok & extra_ok & contiguous & smooth & target_ok
                flags = {
                    "qpos_non_finite": qpos_ok,
                    "invalid_mask": mask_ok,
                    "ee_invalid_numeric": ee_ok,
                    "extra_non_finite": extra_ok,
                    "non_contiguous_frame": contiguous,
                    "sudden_change": smooth,
                    "target_policy_rejected": target_ok,
                    "invalid_frames": quality,
                }
                counts["frames"] += n
                for key, values in flags.items():
                    counts[key] += int((~values).sum())
                for episode in np.unique(episodes):
                    episode = int(episode)
                    episode_outcomes[episode] = episode_outcomes.get(episode, True) and bool(
                        quality[episodes == episode].all()
                    )
                if write_frames:
                    part = pa.table(
                        {
                            "episode_index": episodes,
                            "frame_index": frames,
                            "qpos_finite_valid": qpos_ok,
                            "ee_numeric_valid": ee_ok,
                            "ee_mask_valid": mask_ok,
                            "extra_numeric_valid": extra_ok,
                            "frame_contiguous_valid": contiguous,
                            "sudden_change_valid": smooth,
                            "target_policy_valid": target_ok,
                            "signal_quality_valid": quality,
                        }
                    )
                    if writer is None:
                        writer = pq.ParquetWriter(
                            output / "frames.parquet", part.schema, compression="zstd"
                        )
                    writer.write_table(part)
                if progress:
                    progress({"phase": "signal", "frames": counts["frames"]})
                if max_frames is not None and counts["frames"] >= max_frames:
                    break
            if max_frames is not None and counts["frames"] >= max_frames:
                break
    finally:
        if writer is not None:
            writer.close()
    if not counts["frames"]:
        raise ValueError("no frames found")
    retained = sum(episode_outcomes.values())
    # A capped run is always a sample, even if the cap happened to equal the data size.
    sampled = max_frames is not None
    summary = {
        "schema_version": "lerobot_signal_quality_report_v2",
        "repo": str(repo.resolve()),
        "adapter": contract.name,
        "coverage": contract.coverage(),
        "features": contract.columns,
        "qpos_width": contract.qpos_width,
        "qpos_checks": "performed" if contract.joint_keys else "unavailable",
        "ee_checks": "performed" if contract.pose_keys else "unavailable",
        "arm_joint_indices": {
            k: [i for group in contract.arm_indices.values() for i in group]
            for k in contract.joint_keys
        },
        "thresholds": {
            "joint_step_rad": thresholds.joint_step_rad,
            "ee_position_step_m": thresholds.ee_position_step_m,
            "ee_rotation_step_deg": thresholds.ee_rotation_step_deg,
        },
        "threshold_semantics": "per adjacent frame; source units retained; no FPS rescaling",
        "mask_valid_frames_by_side": mask_coverage,
        "policy": {
            "require_action_targets": require_action_targets,
            "require_ee_targets": require_ee_targets,
        },
        "scope": "sample" if sampled else "full",
        "max_frames": max_frames,
        **counts,
        "episodes": len(episode_outcomes),
        "retained_episodes_all_frames_valid": None if sampled else retained,
        "rejected_episodes": None if sampled else len(episode_outcomes) - retained,
        "sample_episodes_all_observed_frames_valid": retained if sampled else None,
    }
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    (output / "episodes.json").write_text(
        json.dumps(
            {
                str(k): {
                    "quality_valid": v if not sampled else None,
                    "observed_frames_valid": v,
                    "scope": summary["scope"],
                }
                for k, v in sorted(episode_outcomes.items())
            },
            indent=2,
        )
        + "\n"
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", default="auto")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--joint-step-rad", type=float, default=0.35)
    parser.add_argument("--ee-position-step-m", type=float, default=0.10)
    parser.add_argument("--ee-rotation-step-deg", type=float, default=30.0)
    parser.add_argument("--write-frames", action="store_true")
    parser.add_argument("--require-action-targets", action="store_true")
    parser.add_argument("--require-ee-targets", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = validate_repo(
        args.repo,
        args.output,
        thresholds=Thresholds(
            args.joint_step_rad, args.ee_position_step_m, args.ee_rotation_step_deg
        ),
        adapter=args.adapter,
        max_frames=args.max_frames,
        write_frames=args.write_frames,
        require_action_targets=args.require_action_targets,
        require_ee_targets=args.require_ee_targets,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
