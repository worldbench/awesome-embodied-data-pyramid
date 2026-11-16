#!/usr/bin/env python3
"""Convert OpenGalaxea LeRobot v2.1 archives to the unified v3 schema.

The source release contains incompatible R1-Lite and R1-Pro robot schemas, so
one invocation converts exactly one ``--robot-type``. Source archives and
directories are opened read-only; all extraction and conversion happens below
the configured work directory.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import shutil
import subprocess
import sys
import tempfile
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generic_converter import annotate_features, validate_feature_descriptions


SOURCE_VERSION = "v2.1"
TARGET_VERSION = "v3.0"
FPS = 15
ROBOT_ARM_WIDTHS = {"r1lite": 6, "r1pro": 7}
EMBODIMENT_NAMES = {
    "r1lite": "Galaxea R1-Lite",
    "r1pro": "Galaxea R1-Pro",
}

NEW_NUMERIC_KEYS = (
    "state.qpos",
    "state.ee",
    "state.ee_valid",
    "action.qpos",
    "action.qpos_valid",
    "action.ee",
    "action.ee_valid",
)
STATISTIC_NAMES = (
    "min",
    "max",
    "mean",
    "std",
    "count",
    "q01",
    "q10",
    "q50",
    "q90",
    "q99",
)

SourceKind = Literal["archive", "directory"]


@dataclass(frozen=True)
class SourceUnit:
    kind: SourceKind
    source: str
    name: str


@dataclass(frozen=True)
class ConversionConfig:
    output_parts_root: str
    work_root: str
    robot_type: str
    overwrite: bool
    data_file_size_mb: int | None
    video_file_size_mb: int | None
    resume_incomplete: bool = False


@dataclass(frozen=True)
class GalaxeaSchema:
    robot_type: str
    arm_width: int
    has_action_ee: bool

    @classmethod
    def from_info(cls, info: dict[str, Any]) -> "GalaxeaSchema":
        robot_type = str(info.get("robot_type", "")).lower()
        if robot_type not in ROBOT_ARM_WIDTHS:
            raise ValueError(f"Unsupported Galaxea robot_type: {robot_type!r}")

        features = info.get("features", {})
        expected_arm_width = ROBOT_ARM_WIDTHS[robot_type]
        required_widths = {
            "observation.state.torso": 4,
            "observation.state.left_arm": expected_arm_width,
            "observation.state.right_arm": expected_arm_width,
            "observation.state.left_gripper": 1,
            "observation.state.right_gripper": 1,
            "observation.state.left_ee_pose": 7,
            "observation.state.right_ee_pose": 7,
            "action.left_arm": expected_arm_width,
            "action.right_arm": expected_arm_width,
            "action.left_gripper": 1,
            "action.right_gripper": 1,
        }
        if robot_type == "r1lite":
            required_widths["action.torso.velocities"] = 6
        for key, expected_width in required_widths.items():
            width = _feature_width(features.get(key), key)
            if width != expected_width:
                raise ValueError(
                    f"{key} has width {width}, expected {expected_width} for {robot_type}"
                )

        action_ee_keys = {"action.left_ee_pose", "action.right_ee_pose"}
        present_action_ee = action_ee_keys.intersection(features)
        if present_action_ee and present_action_ee != action_ee_keys:
            raise ValueError("Only one side of the source action EE pose is present")
        for key in present_action_ee:
            if _feature_width(features[key], key) != 7:
                raise ValueError(f"{key} must have width 7")

        return cls(
            robot_type=robot_type,
            arm_width=expected_arm_width,
            has_action_ee=bool(present_action_ee),
        )


def _feature_width(feature: Any, key: str) -> int:
    if not isinstance(feature, dict):
        raise KeyError(f"Missing required source feature {key}")
    shape = feature.get("shape")
    if not isinstance(shape, list) or len(shape) != 1:
        raise ValueError(f"{key} has invalid shape {shape}")
    return int(shape[0])


def build_unified_features(
    schema: GalaxeaSchema,
    fps: int = FPS,
) -> dict[str, dict[str, Any]]:
    arm_width = schema.arm_width
    state_qpos_names = [
        *[f"state/qpos.left_joint_{index}" for index in range(arm_width)],
        "state/qpos.left_gripper",
        *[f"state/qpos.right_joint_{index}" for index in range(arm_width)],
        "state/qpos.right_gripper",
    ]
    action_qpos_names = [
        name.replace("state/", "action/", 1) for name in state_qpos_names
    ]
    ee_components = ("x", "y", "z", "qx", "qy", "qz", "qw")
    state_ee_names = [
        *[f"state/ee.left.{component}" for component in ee_components],
        *[f"state/ee.right.{component}" for component in ee_components],
    ]
    action_ee_names = [
        name.replace("state/", "action/", 1) for name in state_ee_names
    ]
    qpos_width = 2 * (arm_width + 1)
    action_ee_description = (
        "Commanded absolute left/right end-effector poses, each ordered "
        "[x,y,z,qx,qy,qz,qw]."
        if schema.has_action_ee
        else "Finite zero placeholder for unavailable source end-effector actions; "
        "action.ee_valid is always zero."
    )
    features = {
        "state.qpos": {
            "dtype": "float32",
            "shape": [qpos_width],
            "names": {"motors": state_qpos_names},
            "fps": fps,
            "description": (
                "Measured joint positions ordered left arm, left gripper, right arm, "
                "right gripper. Gripper values retain the source 0=closed, 100=open scale."
            ),
        },
        "state.ee": {
            "dtype": "float32",
            "shape": [14],
            "names": {"motors": state_ee_names},
            "fps": fps,
            "description": (
                "Measured left/right end-effector poses, each ordered "
                "[x,y,z,qx,qy,qz,qw]; valid quaternions are normalized."
            ),
        },
        "state.ee_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {"motors": ["state/ee_valid.left", "state/ee_valid.right"]},
            "fps": fps,
            "description": (
                "Per-side [left,right] state.ee validity. Invalid poses are finite "
                "zero placeholders with mask value 0."
            ),
        },
        "action.qpos": {
            "dtype": "float32",
            "shape": [qpos_width],
            "names": {"motors": action_qpos_names},
            "fps": fps,
            "description": (
                "Commanded absolute joint-position targets ordered left arm, left "
                "gripper, right arm, right gripper; this is not a delta action."
            ),
        },
        "action.qpos_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {
                "motors": ["action/qpos_valid.left", "action/qpos_valid.right"]
            },
            "fps": fps,
            "description": (
                "Per-side [left,right] action.qpos validity. Invalid command groups "
                "are finite zero placeholders with mask value 0."
            ),
        },
        "action.ee": {
            "dtype": "float32",
            "shape": [14],
            "names": {"motors": action_ee_names},
            "fps": fps,
            "description": action_ee_description,
        },
        "action.ee_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {"motors": ["action/ee_valid.left", "action/ee_valid.right"]},
            "fps": fps,
            "description": (
                "Per-side [left,right] action.ee validity. Invalid or unavailable "
                "poses are finite zero placeholders with mask value 0."
            ),
        },
    }
    state_qpos_origin = (
        "source LeRobot v2.1 observation.state.left_arm + "
        "observation.state.left_gripper + observation.state.right_arm + "
        "observation.state.right_gripper"
    )
    state_ee_origin = (
        "source LeRobot v2.1 observation.state.left_ee_pose + "
        "observation.state.right_ee_pose"
    )
    action_qpos_origin = (
        "source LeRobot v2.1 action.left_arm + action.left_gripper + "
        "action.right_arm + action.right_gripper"
    )
    action_ee_origin = (
        "source LeRobot v2.1 action.left_ee_pose + action.right_ee_pose"
        if schema.has_action_ee
        else "not present in R1-Lite source; converter-generated finite-zero placeholder"
    )
    origins = {
        "state.qpos": state_qpos_origin,
        "state.ee": state_ee_origin,
        "state.ee_valid": f"derived from {state_ee_origin}",
        "action.qpos": action_qpos_origin,
        "action.qpos_valid": f"derived from {action_qpos_origin}",
        "action.ee": action_ee_origin,
        "action.ee_valid": f"derived from {action_ee_origin}",
    }
    features['state.waist'] = {
        'dtype': 'float32', 'shape': [4], 'fps': fps,
        'names': {'motors': [f'torso.position[{i}]' for i in range(4)]},
        'description': 'Measured torso joint positions in source index order [0,1,2,3]. Source-native values retained without normalization or unit conversion; physical axis names are not specified by source metadata.',
    }
    origins['state.waist'] = 'source LeRobot v2.1 observation.state.torso (/hdas/feedback_torso.position[0:4])'
    if schema.robot_type == 'r1lite':
        features['action.waist_velocity'] = {
            'dtype': 'float32', 'shape': [6], 'fps': fps,
            'names': {'motors': ['vx','vy','vz','wx','wy','wz']},
            'description': 'Commanded torso spatial velocity [linear.x,linear.y,linear.z,angular.x,angular.y,angular.z]. Not joint velocities or position targets. Source-native values retained without normalization or unit conversion; reference frame and units are not asserted beyond source metadata.',
        }
        origins['action.waist_velocity'] = 'source LeRobot v2.1 action.torso.velocities (/motion_target/target_speed_torso.twist)'
    order = ['state.qpos','state.waist','state.ee','state.ee_valid','action.qpos','action.qpos_valid','action.waist_velocity','action.ee','action.ee_valid']
    features = {key: features[key] for key in order if key in features}
    return annotate_features(
        features,
        embodiment=EMBODIMENT_NAMES[schema.robot_type],
        origins=origins,
    )


def map_robot_arrays(
    arrays: dict[str, np.ndarray],
    schema: GalaxeaSchema,
) -> dict[str, np.ndarray]:
    left_state = _matrix(arrays["observation.state.left_arm"], schema.arm_width)
    right_state = _matrix(arrays["observation.state.right_arm"], schema.arm_width)
    left_state_gripper = _matrix(arrays["observation.state.left_gripper"], 1)
    right_state_gripper = _matrix(arrays["observation.state.right_gripper"], 1)
    left_action = _matrix(arrays["action.left_arm"], schema.arm_width)
    right_action = _matrix(arrays["action.right_arm"], schema.arm_width)
    left_action_gripper = _matrix(arrays["action.left_gripper"], 1)
    right_action_gripper = _matrix(arrays["action.right_gripper"], 1)

    lengths = {
        len(value)
        for value in (
            left_state,
            right_state,
            left_state_gripper,
            right_state_gripper,
            left_action,
            right_action,
            left_action_gripper,
            right_action_gripper,
        )
    }
    if len(lengths) != 1:
        raise ValueError(f"Source robot feature row counts differ: {sorted(lengths)}")

    state_qpos = np.concatenate(
        [left_state, left_state_gripper, right_state, right_state_gripper], axis=1
    )
    _require_finite(state_qpos, "state.qpos")

    left_qpos_action, left_qpos_valid = _sanitize_group(
        np.concatenate([left_action, left_action_gripper], axis=1)
    )
    right_qpos_action, right_qpos_valid = _sanitize_group(
        np.concatenate([right_action, right_action_gripper], axis=1)
    )
    action_qpos = np.concatenate([left_qpos_action, right_qpos_action], axis=1)
    action_qpos_valid = np.stack(
        [left_qpos_valid, right_qpos_valid], axis=1
    )

    state_ee, state_ee_valid = _normalize_pose_pair(
        arrays["observation.state.left_ee_pose"],
        arrays["observation.state.right_ee_pose"],
    )
    if schema.has_action_ee:
        action_ee, action_ee_valid = _normalize_pose_pair(
            arrays["action.left_ee_pose"],
            arrays["action.right_ee_pose"],
        )
    else:
        action_ee = np.zeros((len(state_qpos), 14), dtype=np.float32)
        action_ee_valid = np.zeros((len(state_qpos), 2), dtype=np.float32)

    mapped = {
        "state.qpos": state_qpos.astype(np.float32, copy=False),
        "state.ee": state_ee,
        "state.ee_valid": state_ee_valid,
        "action.qpos": action_qpos,
        "action.qpos_valid": action_qpos_valid,
        "action.ee": action_ee,
        "action.ee_valid": action_ee_valid,
    }

    waist = _matrix(arrays['observation.state.torso'], 4)
    _require_finite(waist, 'state.waist')
    if len(waist) != len(state_qpos):
        raise ValueError('state.waist row count mismatch')
    mapped['state.waist'] = waist
    if schema.robot_type == 'r1lite':
        velocity = _matrix(arrays['action.torso.velocities'], 6)
        _require_finite(velocity, 'action.waist_velocity')
        if len(velocity) != len(state_qpos):
            raise ValueError('action.waist_velocity row count mismatch')
        mapped['action.waist_velocity'] = velocity
    return mapped


def _matrix(values: np.ndarray, width: int) -> np.ndarray:
    result = np.asarray(values, dtype=np.float32)
    if result.ndim == 1 and width == 1:
        result = result[:, None]
    if result.ndim != 2 or result.shape[1] != width:
        raise ValueError(f"Expected (*,{width}) values, got {result.shape}")
    return result


def _require_finite(values: np.ndarray, feature_name: str) -> None:
    invalid = ~np.isfinite(values).all(axis=1)
    if invalid.any():
        raise ValueError(
            f"{feature_name} contains non-finite values in {int(invalid.sum())} rows"
        )


def _sanitize_group(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(values, dtype=np.float32).copy()
    valid = np.isfinite(values).all(axis=1)
    values[~valid] = 0.0
    return values, valid.astype(np.float32)


def _normalize_pose_pair(
    left_values: np.ndarray,
    right_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    poses = np.concatenate(
        [_matrix(left_values, 7), _matrix(right_values, 7)], axis=1
    ).astype(np.float32, copy=True)
    valid = np.zeros((len(poses), 2), dtype=np.float32)
    for side, start in enumerate((0, 7)):
        pose = poses[:, start : start + 7]
        quaternion = pose[:, 3:7]
        norm = np.linalg.norm(quaternion, axis=1)
        side_valid = np.isfinite(pose).all(axis=1) & np.isfinite(norm) & (norm > 1e-8)
        pose[~side_valid] = 0.0
        pose[side_valid, 3:7] /= norm[side_valid, None]
        valid[:, side] = side_valid.astype(np.float32)
    return poses, valid


def discover_sources(
    source_root: Path,
    source_kind: Literal["archive", "directory"],
    archive_subdir: str,
    includes: list[str],
    excludes: list[str],
) -> list[SourceUnit]:
    source_root = source_root.expanduser().resolve()
    units: list[SourceUnit] = []
    if source_kind == "archive":
        archive_root = source_root / archive_subdir
        if not archive_root.is_dir():
            archive_root = source_root
        units = [
            SourceUnit("archive", str(path), path.name.removesuffix(".tar.gz"))
            for path in sorted(archive_root.glob("*.tar.gz"))
        ]
    else:
        if (source_root / "meta" / "info.json").is_file():
            leaves = [source_root]
        else:
            leaves = sorted(
                path.parent.parent
                for path in source_root.glob("**/meta/info.json")
                if not path.parent.parent.name.endswith("_old")
            )
        units = [SourceUnit("directory", str(path), path.name) for path in leaves]

    filtered = [
        unit
        for unit in units
        if _matches_filters(unit.name, includes, excludes)
    ]
    names = [unit.name for unit in filtered]
    if len(names) != len(set(names)):
        raise ValueError("Discovered duplicate source names; narrow --source-root")
    return filtered


def _matches_filters(name: str, includes: list[str], excludes: list[str]) -> bool:
    if includes and not any(fnmatch.fnmatch(name, pattern) for pattern in includes):
        return False
    return not any(fnmatch.fnmatch(name, pattern) for pattern in excludes)


def convert_source(unit: SourceUnit, config: ConversionConfig) -> dict[str, Any]:
    output_root = Path(config.output_parts_root) / unit.name
    marker_path = output_root / "meta" / "unified_action_space.json"
    if marker_path.is_file() and not config.overwrite:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if marker.get("robot_type") == config.robot_type:
            return _result(unit, "skipped", output_root, "already complete")
        raise ValueError(f"Existing part has incompatible robot_type: {output_root}")
    if output_root.exists() and config.resume_incomplete:
        import time
        output_root.rename(output_root.with_name(output_root.name + f".backup_{time.time_ns()}"))
    if output_root.exists() and not config.overwrite:
        raise FileExistsError(
            f"Incomplete output exists at {output_root}; inspect it or use --overwrite"
        )
    if output_root.exists():
        shutil.rmtree(output_root)

    work_root = Path(config.work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    job_root = Path(tempfile.mkdtemp(prefix="opengalaxea_", dir=work_root))
    try:
        source_dataset = _prepare_source(unit, job_root)
        source_info = json.loads(
            (source_dataset / "meta" / "info.json").read_text(encoding="utf-8")
        )
        source_robot_type = str(source_info.get("robot_type", "")).lower()
        if source_robot_type != config.robot_type:
            return _result(
                unit,
                "filtered",
                output_root,
                f"source robot_type={source_robot_type}",
            )

        _convert_v21_to_v30_in_place(
            source_dataset,
            data_file_size_mb=config.data_file_size_mb,
            video_file_size_mb=config.video_file_size_mb,
        )
        summary = rewrite_unified_action_space(source_dataset, unit)
        output_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_dataset), str(output_root))
        return _result(unit, "converted", output_root, "ok", summary)
    finally:
        shutil.rmtree(job_root, ignore_errors=True)


def _prepare_source(unit: SourceUnit, job_root: Path) -> Path:
    if unit.kind == "archive":
        extract_root = job_root / "extracted"
        extract_root.mkdir()
        subprocess.run(
            [
                "tar",
                "--extract",
                "--gzip",
                "--file",
                unit.source,
                "--directory",
                str(extract_root),
                "--no-same-owner",
                "--no-same-permissions",
            ],
            check=True,
        )
        info_paths = sorted(extract_root.glob("**/meta/info.json"))
        if len(info_paths) != 1:
            raise ValueError(
                f"{unit.source} contains {len(info_paths)} datasets, expected one"
            )
        return info_paths[0].parent.parent

    source = Path(unit.source).resolve()
    destination = job_root / "source" / source.name
    _symlink_copy_tree(source, destination)
    return destination


def _symlink_copy_tree(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True)
    for path in source.rglob("*"):
        relative = path.relative_to(source)
        target = destination / relative
        if path.is_dir():
            target.mkdir(exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.symlink_to(path.resolve())


def _convert_v21_to_v30_in_place(
    dataset_root: Path,
    *,
    data_file_size_mb: int | None,
    video_file_size_mb: int | None,
) -> None:
    from lerobot.scripts.convert_dataset_v21_to_v30 import convert_dataset

    convert_dataset(
        repo_id=dataset_root.name,
        root=dataset_root,
        push_to_hub=False,
        force_conversion=True,
        data_file_size_in_mb=data_file_size_mb,
        video_file_size_in_mb=video_file_size_mb,
    )


def rewrite_unified_action_space(
    dataset_root: Path,
    source_unit: SourceUnit,
) -> dict[str, Any]:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from lerobot.datasets.compute_stats import aggregate_stats, compute_episode_stats
    from lerobot.datasets.io_utils import load_stats, write_stats

    info_path = dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("codebase_version") != TARGET_VERSION:
        raise ValueError(
            f"Expected {TARGET_VERSION}, got {info.get('codebase_version')}"
        )
    schema = GalaxeaSchema.from_info(info)
    new_features = build_unified_features(schema, int(info["fps"]))
    validate_feature_descriptions(new_features)
    source_numeric_keys = {
        key
        for key in info["features"]
        if key.startswith("observation.state.") or key.startswith("action.")
    }
    required_source_keys = {
        "observation.state.left_arm",
        "observation.state.right_arm",
        "observation.state.left_gripper",
        "observation.state.right_gripper",
        "observation.state.left_ee_pose",
        "observation.state.right_ee_pose",
        "action.left_arm",
        "action.right_arm",
        "action.left_gripper",
        "action.right_gripper",
    }
    required_source_keys.add("observation.state.torso")
    if schema.robot_type == "r1lite":
        required_source_keys.add("action.torso.velocities")
    if schema.has_action_ee:
        required_source_keys.update({"action.left_ee_pose", "action.right_ee_pose"})

    episode_stats: dict[int, dict[str, dict[str, np.ndarray]]] = {}
    invalid_counts = {
        "state.ee.left": 0,
        "state.ee.right": 0,
        "action.qpos.left": 0,
        "action.qpos.right": 0,
        "action.ee.left": 0,
        "action.ee.right": 0,
    }
    total_rows = 0
    for parquet_path in sorted(dataset_root.glob("data/chunk-*/*.parquet")):
        table = pq.read_table(parquet_path)
        arrays = {
            key: _column_to_numpy(
                table[key], _feature_width(info["features"][key], key), pa
            )
            for key in required_source_keys
        }
        mapped = map_robot_arrays(arrays, schema)
        total_rows += len(mapped["state.qpos"])
        for prefix, mask_key in (
            ("state.ee", "state.ee_valid"),
            ("action.qpos", "action.qpos_valid"),
            ("action.ee", "action.ee_valid"),
        ):
            invalid_counts[f"{prefix}.left"] += int(
                (mapped[mask_key][:, 0] == 0).sum()
            )
            invalid_counts[f"{prefix}.right"] += int(
                (mapped[mask_key][:, 1] == 0).sum()
            )

        episode_indices = table["episode_index"].combine_chunks().to_numpy(
            zero_copy_only=False
        )
        for episode_index in np.unique(episode_indices):
            index = int(episode_index)
            if index in episode_stats:
                raise ValueError(f"Episode {index} is split across data files")
            row_mask = episode_indices == episode_index
            episode_stats[index] = compute_episode_stats(
                {key: values[row_mask] for key, values in mapped.items()},
                new_features,
            )

        stale_columns = [key for key in source_numeric_keys if key in table.column_names]
        rewritten = table.drop(stale_columns)
        for key in new_features:
            rewritten = rewritten.append_column(
                key, _numpy_to_fixed_list(mapped[key], pa)
            )
        _write_parquet_atomic(rewritten.replace_schema_metadata(None), parquet_path, pq)

    if not episode_stats:
        raise ValueError(f"No data rows found below {dataset_root}")

    _rewrite_episode_metadata(
        dataset_root,
        episode_stats,
        source_numeric_keys,
        pa,
        pq,
    )
    global_stats = load_stats(dataset_root)
    if global_stats is None:
        raise FileNotFoundError(f"Missing meta/stats.json below {dataset_root}")
    for key in source_numeric_keys:
        global_stats.pop(key, None)
    unified_stats = aggregate_stats(list(episode_stats.values()))
    invalid_stats = _nonfinite_paths(unified_stats)
    if invalid_stats:
        raise ValueError(
            f"Unified statistics contain non-finite values: {invalid_stats[:20]}"
        )
    global_stats.update(unified_stats)
    write_stats(global_stats, dataset_root)

    preserved_features = {
        key: value
        for key, value in info["features"].items()
        if key not in source_numeric_keys
    }
    preserved_features.update(new_features)
    info["features"] = annotate_features(
        preserved_features,
        embodiment=EMBODIMENT_NAMES[schema.robot_type],
        origins=lambda key: f"source LeRobot v2.1 feature {key}",
        default_description=lambda key: f"Preserved OpenGalaxea feature {key}.",
    )
    validate_feature_descriptions(info["features"])
    _write_json_atomic(info_path, info)

    summary = {
        "source": asdict(source_unit),
        "source_version": SOURCE_VERSION,
        "target_version": TARGET_VERSION,
        "robot_type": schema.robot_type,
        "arm_width": schema.arm_width,
        "source_has_action_ee": schema.has_action_ee,
        "episodes": len(episode_stats),
        "frames": total_rows,
        "invalid_frames": invalid_counts,
        "removed_source_numeric_features": sorted(source_numeric_keys),
        "added_features": list(new_features),
    }
    _write_json_atomic(
        dataset_root / "meta" / "unified_action_space.json", summary
    )
    return summary


def _column_to_numpy(column: Any, expected_width: int, pa: Any) -> np.ndarray:
    array = column.combine_chunks()
    if array.null_count:
        raise ValueError(f"Source column contains {array.null_count} null rows")
    if pa.types.is_fixed_size_list(array.type):
        values = array.values.to_numpy(zero_copy_only=False)
        result = np.asarray(values, dtype=np.float32).reshape(len(array), -1)
    elif pa.types.is_list(array.type) or pa.types.is_large_list(array.type):
        result = np.asarray(array.to_pylist(), dtype=np.float32)
    else:
        result = np.asarray(array.to_numpy(zero_copy_only=False), dtype=np.float32)
        if expected_width == 1:
            result = result[:, None]
    if result.shape != (len(array), expected_width):
        raise ValueError(
            f"Source column has shape {result.shape}, expected ({len(array)},{expected_width})"
        )
    return result


def _numpy_to_fixed_list(values: np.ndarray, pa: Any) -> Any:
    values = np.asarray(values, dtype=np.float32)
    flat = pa.array(values.reshape(-1), type=pa.float32())
    return pa.FixedSizeListArray.from_arrays(flat, values.shape[1])


def _rewrite_episode_metadata(
    dataset_root: Path,
    episode_stats: dict[int, dict[str, dict[str, np.ndarray]]],
    source_numeric_keys: set[str],
    pa: Any,
    pq: Any,
) -> None:
    paths = sorted(dataset_root.glob("meta/episodes/chunk-*/*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No episode metadata parquet below {dataset_root}")
    seen: set[int] = set()
    for path in paths:
        table = pq.read_table(path)
        episode_indices = [int(value) for value in table["episode_index"].to_pylist()]
        stale_columns = [
            name
            for name in table.column_names
            if any(name.startswith(f"stats/{key}/") for key in source_numeric_keys)
        ]
        rewritten = table.drop(stale_columns)
        for feature_name in next(iter(episode_stats.values())):
            for statistic_name in STATISTIC_NAMES:
                column_name = f"stats/{feature_name}/{statistic_name}"
                values = [
                    np.asarray(
                        episode_stats[index][feature_name][statistic_name]
                    ).tolist()
                    for index in episode_indices
                ]
                rewritten = rewritten.append_column(column_name, pa.array(values))
        _write_parquet_atomic(rewritten.replace_schema_metadata(None), path, pq)
        seen.update(episode_indices)
    if seen != set(episode_stats):
        missing = sorted(set(episode_stats) - seen)
        raise ValueError(f"Episode metadata is missing indices: {missing[:20]}")


def _write_parquet_atomic(table: Any, path: Path, pq: Any) -> None:
    temporary = path.with_suffix(".parquet.tmp")
    pq.write_table(table, temporary, compression="zstd")
    temporary.replace(path)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(f"{path.suffix}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _nonfinite_paths(payload: Any, prefix: str = "") -> list[str]:
    if isinstance(payload, dict):
        paths: list[str] = []
        for key, value in payload.items():
            paths.extend(_nonfinite_paths(value, f"{prefix}/{key}"))
        return paths
    if isinstance(payload, (list, tuple)):
        paths = []
        for index, value in enumerate(payload):
            paths.extend(_nonfinite_paths(value, f"{prefix}/{index}"))
        return paths
    if isinstance(payload, np.ndarray):
        return [
            prefix + "[" + ",".join(str(int(i)) for i in indices) + "]"
            for indices in np.argwhere(~np.isfinite(payload))
        ]
    if isinstance(payload, (float, np.floating)) and not np.isfinite(payload):
        return [prefix]
    return []


def _result(
    unit: SourceUnit,
    status: str,
    output: Path,
    message: str,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": asdict(unit),
        "status": status,
        "output": str(output),
        "message": message,
        "summary": summary,
    }


def _append_report(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    parser.add_argument("--robot-type", choices=sorted(ROBOT_ARM_WIDTHS), required=True)
    parser.add_argument(
        "--source-kind", choices=["archive", "directory"], default="archive"
    )
    parser.add_argument("--archive-subdir", default="lerobot_opensource")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--max-sources", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--data-file-size-mb", type=int)
    parser.add_argument("--video-file-size-mb", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--resume-incomplete", action="store_true", help="Rename incomplete outputs and reuse completed parts")
    parser.add_argument("--keep-parts", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.source_root.is_dir():
        raise FileNotFoundError(f"Source root not found: {args.source_root}")
    if args.output_path.resolve() == args.source_root.resolve():
        raise ValueError("--output-path must differ from --source-root")
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    if args.max_sources is not None and args.max_sources < 1:
        raise ValueError("--max-sources must be >= 1")
    for name in ("data_file_size_mb", "video_file_size_mb"):
        value = getattr(args, name)
        if value is not None and value < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be >= 1")


def main() -> None:
    args = parse_args()
    validate_args(args)
    units = discover_sources(
        args.source_root,
        args.source_kind,
        args.archive_subdir,
        args.include,
        args.exclude,
    )
    if args.max_sources is not None:
        units = units[: args.max_sources]
    if not units:
        raise ValueError("No matching OpenGalaxea sources found")
    print(f"Discovered {len(units)} source(s)", flush=True)
    if args.dry_run:
        for unit in units:
            print(f"{unit.kind}\t{unit.name}\t{unit.source}")
        return

    output_path = args.output_path.expanduser().resolve()
    if output_path.exists() and args.resume_incomplete:
        if (output_path / "meta/unified_action_space.json").exists():
            raise FileExistsError(f"Completed output exists: {output_path}")
        import time
        output_path.rename(output_path.with_name(output_path.name + f".backup_{time.time_ns()}"))
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Final output exists at {output_path}; rerun with --overwrite"
        )
    parts_root = output_path.with_name(f"{output_path.name}_parts")
    report_path = output_path.with_name(f"{output_path.name}_reports") / "conversion.jsonl"
    config = ConversionConfig(
        output_parts_root=str(parts_root),
        work_root=str(args.work_root.expanduser().resolve()),
        robot_type=args.robot_type,
        overwrite=args.overwrite,
        data_file_size_mb=args.data_file_size_mb,
        video_file_size_mb=args.video_file_size_mb,
        resume_incomplete=args.resume_incomplete,
    )

    records: list[dict[str, Any]] = []
    if args.workers == 1:
        for index, unit in enumerate(units, start=1):
            print(f"[{index}/{len(units)}] {unit.name}", flush=True)
            try:
                record = convert_source(unit, config)
            except Exception as exc:
                record = _result(
                    unit,
                    "failed",
                    parts_root / unit.name,
                    f"{exc}\n{traceback.format_exc()}",
                )
            records.append(record)
            _append_report(report_path, record)
            print(f"  {record['status']}: {record['message']}", flush=True)
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(convert_source, unit, config): unit for unit in units
            }
            for future in as_completed(futures):
                unit = futures[future]
                try:
                    record = future.result()
                except Exception as exc:
                    record = _result(
                        unit,
                        "failed",
                        parts_root / unit.name,
                        f"{exc}\n{traceback.format_exc()}",
                    )
                records.append(record)
                _append_report(report_path, record)
                print(f"[{len(records)}/{len(units)}] {unit.name}: {record['status']}")

    failed = [record for record in records if record["status"] == "failed"]
    if failed:
        print(f"Failed sources: {len(failed)}; report={report_path}", flush=True)
        raise SystemExit(1)
    selected = {
        record["source"]["name"]: record
        for record in records
        if record["status"] in {"converted", "skipped"}
    }
    part_roots = [
        Path(selected[unit.name]["output"])
        for unit in units
        if unit.name in selected
    ]
    if not part_roots:
        raise ValueError(f"No sources matched --robot-type {args.robot_type}")

    from generic_converter import aggregate_roots

    aggregate_roots(part_roots, output_path, aggr_repo_id=output_path.name)
    _write_json_atomic(
        output_path / "meta" / "unified_action_space.json",
        {
            "source_dataset": "OpenGalaxea/Galaxea-Open-World-Dataset",
            "source_version": SOURCE_VERSION,
            "target_version": TARGET_VERSION,
            "robot_type": args.robot_type,
            "embodiment": EMBODIMENT_NAMES[args.robot_type],
            "source_count": len(part_roots),
            "source_names": [root.name for root in part_roots],
            "features": list(build_unified_features(GalaxeaSchema(args.robot_type, ROBOT_ARM_WIDTHS[args.robot_type], args.robot_type == "r1pro"))),
        },
    )
    if not args.keep_parts:
        shutil.rmtree(parts_root, ignore_errors=True)
    print(f"Final aggregated dataset: {output_path}", flush=True)


if __name__ == "__main__":
    main()
