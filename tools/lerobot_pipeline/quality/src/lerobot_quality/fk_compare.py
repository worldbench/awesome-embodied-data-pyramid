"""Compare ``state.qpos`` URDF FK with ``state.ee`` poses."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .schema import (
    SIDES,
    STATE_EE,
    STATE_EE_VALID,
    STATE_QPOS,
    LeRobotSchema,
    fixed_list_numpy,
    read_info,
)
from .urdf_fk import UrdfModel


CONFIG_SCHEMA = "lerobot_fk_config_v1"


def quaternion_xyzw_to_matrix(quaternion: np.ndarray) -> np.ndarray:
    value = np.asarray(quaternion, dtype=np.float64)
    norms = np.linalg.norm(value, axis=1, keepdims=True)
    q = np.divide(value, norms, out=np.full_like(value, np.nan), where=norms > 1e-12)
    x, y, z, w = q.T
    return np.stack(
        (
            1 - 2 * (y * y + z * z),
            2 * (x * y - z * w),
            2 * (x * z + y * w),
            2 * (x * y + z * w),
            1 - 2 * (x * x + z * z),
            2 * (y * z - x * w),
            2 * (x * z - y * w),
            2 * (y * z + x * w),
            1 - 2 * (x * x + y * y),
        ),
        axis=1,
    ).reshape(-1, 3, 3)


def rotation_error_deg(expected: np.ndarray, actual: np.ndarray) -> np.ndarray:
    relative = np.einsum("nij,njk->nik", np.transpose(expected, (0, 2, 1)), actual)
    cosine = np.clip(
        (np.trace(relative, axis1=1, axis2=2) - 1.0) / 2.0,
        -1.0,
        1.0,
    )
    return np.degrees(np.arccos(cosine))


def matrix4(value: Any | None) -> np.ndarray:
    if value is None:
        return np.eye(4, dtype=np.float64)
    result = np.asarray(value, dtype=np.float64)
    if result.shape != (4, 4):
        raise ValueError(f"expected a 4x4 transform, got {result.shape}")
    return result


def transform_candidates(config: dict, side: str, kind: str) -> list[np.ndarray]:
    if kind == "base":
        candidates_key = f"{side}_dataset_from_fk_base_candidates"
        single_key = f"{side}_dataset_from_fk_base"
        shared_key = "dataset_from_fk_base"
    else:
        candidates_key = f"{side}_ee_link_to_dataset_ee_candidates"
        single_key = f"{side}_ee_link_to_dataset_ee"
        shared_key = "ee_link_to_dataset_ee"
    if candidates_key in config:
        result = [matrix4(value) for value in config[candidates_key]]
        if not result:
            raise ValueError(f"{candidates_key} must not be empty")
        return result
    return [matrix4(config.get(single_key, config.get(shared_key)))]


def fk_base_link(config: dict, side: str) -> str:
    return config.get(f"{side}_base_link", config.get("base_link"))


def joint_names(config: dict, side: str) -> list[str]:
    return list(config.get(f"{side}_joint_names", config.get("joint_names", [])))


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if config.get("schema_version") != CONFIG_SCHEMA:
        raise ValueError(f"{path}: schema_version must be {CONFIG_SCHEMA!r}")
    active_sides = config.get("active_sides", ["left", "right"])
    if (
        not active_sides
        or len(set(active_sides)) != len(active_sides)
        or any(side not in SIDES for side in active_sides)
    ):
        raise ValueError("active_sides must be a non-empty unique subset of left/right")
    config["active_sides"] = active_sides
    required = {"urdf"} | {f"{side}_ee_link" for side in active_sides}
    missing = required - set(config)
    if missing:
        raise ValueError(f"config missing {sorted(missing)}")
    if "base_link" not in config and any(
        f"{side}_base_link" not in config for side in active_sides
    ):
        raise ValueError("config needs base_link or one base link per active side")
    shared_names = config.get("joint_names")
    side_names = [config.get(f"{side}_joint_names") for side in active_sides]
    if not shared_names and not all(side_names):
        raise ValueError("config needs joint_names or one joint-name list per active side")
    for side in active_sides:
        names = joint_names(config, side)
        if not names or len(names) != len(set(names)):
            raise ValueError(f"{side} joint names must be non-empty and unique")

    urdf = Path(config["urdf"])
    if not urdf.is_absolute():
        urdf = (path.parent / urdf).resolve()
    if not urdf.is_file():
        raise FileNotFoundError(f"URDF does not exist: {urdf}")
    expected_hash = config.get("urdf_sha256")
    if expected_hash:
        actual_hash = hashlib.sha256(urdf.read_bytes()).hexdigest()
        if actual_hash != expected_hash:
            raise ValueError(f"URDF SHA-256 mismatch: expected {expected_hash}, got {actual_hash}")
    config["urdf"] = urdf
    return config


def parquet_files(repo: Path) -> list[Path]:
    files = sorted((repo / "data").rglob("*.parquet")) if (repo / "data").is_dir() else []
    if not files and repo.suffix == ".parquet":
        files = [repo]
    if not files:
        raise FileNotFoundError(f"no parquet files under {repo}")
    return files


def statistics(values: np.ndarray) -> dict[str, float]:
    finite = values[np.isfinite(values)]
    if not len(finite):
        return {name: float("nan") for name in ("mean", "p50", "p95", "p99", "max")}
    return {
        "mean": float(finite.mean()),
        "p50": float(np.quantile(finite, 0.50)),
        "p95": float(np.quantile(finite, 0.95)),
        "p99": float(np.quantile(finite, 0.99)),
        "max": float(finite.max()),
    }


def _select_candidate(
    candidates: np.ndarray,
    source_position: np.ndarray,
    source_rotation: np.ndarray,
    rotation_weight: float,
) -> np.ndarray:
    position_error = np.linalg.norm(candidates[:, :, :3, 3] - source_position[None, :, :], axis=2)
    score = position_error
    if rotation_weight:
        rotation_error = np.stack(
            [rotation_error_deg(item[:, :3, :3], source_rotation) for item in candidates]
        )
        score = score + rotation_weight * rotation_error
    return np.argmin(np.where(np.isfinite(score), score, np.inf), axis=0)


def _side_fk(
    model: UrdfModel,
    config: dict,
    side: str,
    qpos: np.ndarray,
    qpos_indices: list[int],
    source_pose: np.ndarray,
    source_valid: np.ndarray,
    position_threshold_m: float,
    rotation_threshold_deg: float,
    extra_positions: dict[str, np.ndarray] | None = None,
) -> dict[str, np.ndarray]:
    names = joint_names(config, side)
    if len(names) != len(qpos_indices):
        raise ValueError(
            f"{side}: config has {len(names)} URDF joints but metadata exposes "
            f"{len(qpos_indices)} arm joints"
        )
    positions = {name: qpos[:, index] for name, index in zip(names, qpos_indices, strict=True)}
    positions.update(extra_positions or {})
    chain = model.chain(fk_base_link(config, side), config[f"{side}_ee_link"])
    required = {joint.name for joint in chain if joint.kind != "fixed"}
    missing = required - set(positions)
    if missing:
        raise ValueError(f"{side}: FK chain joints are not mapped: {sorted(missing)}")
    fk = model.forward_batch(
        fk_base_link(config, side),
        config[f"{side}_ee_link"],
        positions,
    )
    bases = transform_candidates(config, side, "base")
    tools = transform_candidates(config, side, "tool")
    candidates = np.stack([base @ fk @ tool for base in bases for tool in tools])
    source_rotation = quaternion_xyzw_to_matrix(source_pose[:, 3:7])
    indices = _select_candidate(
        candidates,
        source_pose[:, :3],
        source_rotation,
        float(config.get("candidate_rotation_weight_m_per_deg", 0.0)),
    )
    selected = candidates[indices, np.arange(len(qpos))]
    position_error = np.linalg.norm(selected[:, :3, 3] - source_pose[:, :3], axis=1)
    rotation_error = rotation_error_deg(selected[:, :3, :3], source_rotation)
    joint_valid = np.isfinite(qpos[:, qpos_indices]).all(axis=1)
    for name in required:
        joint_valid &= np.isfinite(positions[name])
    pose_valid = (
        source_valid
        & np.isfinite(source_pose).all(axis=1)
        & (np.linalg.norm(source_pose[:, 3:7], axis=1) > 1e-12)
    )
    input_valid = joint_valid & pose_valid
    passed = (
        input_valid
        & (position_error <= position_threshold_m)
        & (rotation_error <= rotation_threshold_deg)
    )
    return {
        "source_pose_valid": pose_valid,
        "fk_input_valid": input_valid,
        "position_error_m": position_error,
        "rotation_error_deg": rotation_error,
        "candidate_index": indices.astype(np.int32),
        "fk_ee_valid": passed,
    }


def extra_joint_positions(config: dict, arrays: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    result = {}
    for joint, mapping in config.get("extra_joints", {}).items():
        feature, index = mapping["feature"], mapping["index"]
        if feature not in arrays or not 0 <= index < arrays[feature].shape[1]:
            raise ValueError(f"{joint}: missing or incompatible body feature {feature}[{index}]")
        result[joint] = arrays[feature][:, index]
    return result


def compare_repo(
    repo: Path,
    config_path: Path,
    output: Path,
    *,
    stride: int = 1,
    max_frames: int | None = None,
    position_threshold_m: float = 0.01,
    rotation_threshold_deg: float = 2.0,
    write_frames: bool = False,
    adapter: str = "auto",
) -> dict:
    if stride < 1:
        raise ValueError("stride must be >= 1")
    if max_frames is not None and max_frames < 1:
        raise ValueError("max_frames must be positive")
    config = load_config(config_path)
    info = read_info(repo)
    from .adapters import resolve_adapter

    contract = resolve_adapter(info, adapter)
    if STATE_EE not in contract.pose_keys:
        raise ValueError(f"{contract.name}: FK requires an observed state.ee pose")
    if contract.profile.get("fk_comparison_unavailable_reason"):
        raise ValueError(contract.profile["fk_comparison_unavailable_reason"])
    schema = LeRobotSchema(qpos_width=contract.qpos_width)
    schema.validate_config_width(config.get("qpos_widths"))
    if set(config["active_sides"]) - set(contract.arm_indices):
        raise ValueError("FK config requests arm sides absent from adapter")
    model = UrdfModel.load(config["urdf"])
    indices = {side: contract.arm_indices[side] for side in config["active_sides"]}
    all_configured = {name for side in config["active_sides"] for name in joint_names(config, side)}
    unknown = all_configured - set(model.joint_by_name)
    if unknown:
        raise ValueError(f"configured joints absent from URDF: {sorted(unknown)}")

    frame_parts: dict[str, list[np.ndarray]] = {}
    metric_parts: dict[str, list[np.ndarray]] = {}
    valid_parts: list[np.ndarray] = []
    pass_parts: list[np.ndarray] = []
    total = 0
    for parquet in parquet_files(repo):
        available = set(pq.ParquetFile(parquet).schema_arrow.names)
        required = {STATE_QPOS, STATE_EE} | {
            m["feature"] for m in config.get("extra_joints", {}).values()
        }
        if STATE_EE_VALID in contract.columns:
            required.add(STATE_EE_VALID)
        missing = required - available
        if missing:
            raise ValueError(f"{parquet}: missing required columns {sorted(missing)}")
        optional = [name for name in ("episode_index", "frame_index", "index") if name in available]
        columns = sorted(required) + optional
        if max_frames is not None:
            # Smoke runs read at most the number of source rows needed for the cap.
            needed = (max_frames - total) * stride
            records = pq.ParquetFile(parquet).iter_batches(batch_size=needed, columns=columns)
            first = next(records, None)
            if first is None:
                continue
            table = pa.Table.from_batches([first])
        else:
            table = pq.read_table(parquet, columns=columns)
        take = np.arange(0, len(table), stride)
        if max_frames is not None:
            take = take[: max(0, max_frames - total)]
        if not len(take):
            break
        arrays = {key: value[take] for key, value in contract.arrays(table).items()}
        qpos, ee = arrays[STATE_QPOS], arrays[STATE_EE]
        ee_valid = arrays[STATE_EE_VALID] == 1
        extra = extra_joint_positions(config, arrays)
        batch: dict[str, np.ndarray] = {}
        side_results = {}
        for side in config["active_sides"]:
            side_index = contract.ee_sides.index(side)
            side_result = _side_fk(
                model,
                config,
                side,
                qpos,
                indices[side],
                ee[:, side_index * 7 : (side_index + 1) * 7],
                ee_valid[:, side_index],
                position_threshold_m,
                rotation_threshold_deg,
                extra,
            )
            side_results[side] = side_result
            for key, value in side_result.items():
                batch[f"{side}_{key}"] = value
                if key in {"position_error_m", "rotation_error_deg"}:
                    metric_parts.setdefault(f"{side}_{key}", []).append(
                        value[side_result["fk_input_valid"]]
                    )
        batch["fk_input_valid"] = np.logical_and.reduce(
            [side_results[side]["fk_input_valid"] for side in config["active_sides"]]
        )
        batch["fk_ee_valid"] = np.logical_and.reduce(
            [side_results[side]["fk_ee_valid"] for side in config["active_sides"]]
        )
        valid_parts.append(batch["fk_input_valid"])
        pass_parts.append(batch["fk_ee_valid"])
        if write_frames:
            for name in optional:
                values = np.asarray(table[name].to_numpy(zero_copy_only=False))[take]
                frame_parts.setdefault(name, []).append(values)
            for name, values in batch.items():
                frame_parts.setdefault(name, []).append(values)
        total += len(take)
        if max_frames is not None and total >= max_frames:
            break

    if not total:
        raise ValueError("no frames selected")
    valid = np.concatenate(valid_parts)
    passed = np.concatenate(pass_parts)
    summary = {
        "schema_version": "lerobot_fk_report_v1",
        "adapter": contract.name,
        "repo": str(repo.resolve()),
        "config": str(config_path.resolve()),
        "features": [STATE_QPOS, STATE_EE, STATE_EE_VALID],
        "qpos_width": schema.qpos_width,
        "arm_joint_indices": indices,
        "frames": total,
        "valid_frames": int(valid.sum()),
        "pass_frames": int(passed.sum()),
        "pass_rate": float(passed[valid].mean()) if valid.any() else float("nan"),
        "position_threshold_m": position_threshold_m,
        "rotation_threshold_deg": rotation_threshold_deg,
        "metrics": {
            name: statistics(np.concatenate(parts) if parts else np.array([]))
            for name, parts in metric_parts.items()
        },
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    if write_frames:
        table = pa.table(
            {name: pa.array(np.concatenate(parts)) for name, parts in frame_parts.items()}
        )
        pq.write_table(table, output / "frames.parquet", compression="zstd")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--adapter", default="auto")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--position-threshold-m", type=float, default=0.01)
    parser.add_argument("--rotation-threshold-deg", type=float, default=2.0)
    parser.add_argument("--write-frames", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = compare_repo(
        args.repo,
        args.config,
        args.output,
        stride=args.stride,
        max_frames=args.max_frames,
        position_threshold_m=args.position_threshold_m,
        rotation_threshold_deg=args.rotation_threshold_deg,
        write_frames=args.write_frames,
        adapter=args.adapter,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
