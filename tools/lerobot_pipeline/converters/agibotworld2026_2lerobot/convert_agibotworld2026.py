#!/usr/bin/env python3
"""Convert AgiBotWorld2026 v2.1 leaves into one unified LeRobot v3.0 dataset.

The official LeRobot converter performs the v2.1-to-v3.0 container conversion.
This script then replaces the source flat robot vectors with the project-wide
``state.qpos``, ``state.ee``, ``action.qpos`` and ``action.ee`` schema. Source
archives and extracted simulation leaves are always opened read-only. Converted
source parts are aggregated into the exact path supplied with ``--output-path``.
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

from generic_converter import annotate_features


SOURCE_VERSION = "v2.1"
TARGET_VERSION = "v3.0"
EXPECTED_REAL_ARCHIVES = 334
EXPECTED_SIMULATION_LEAVES = 6
EXPECTED_CANONICAL_LEAVES = 340

OLD_STATE_KEY = "observation.state"
OLD_ACTION_KEY = "action"
NEW_NUMERIC_KEYS = (
    "state.qpos",
    "state.waist",
    "state.ee",
    "state.ee_valid",
    "action.qpos",
    "action.waist",
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

STATE_QPOS_NAMES = [
    *[f"state/joint/position.left_joint_{index}" for index in range(7)],
    "state/left_effector/position",
    *[f"state/joint/position.right_joint_{index}" for index in range(7)],
    "state/right_effector/position",
]
ACTION_QPOS_NAMES = [name.replace("state/", "action/", 1) for name in STATE_QPOS_NAMES]
STATE_WAIST_NAMES = [f"state/waist/position.joint_{i}" for i in range(5)]
ACTION_WAIST_NAMES = [name.replace("state/", "action/", 1) for name in STATE_WAIST_NAMES]
ACTION_QPOS_VALID_NAMES = [
    "action/joint/position_valid.left",
    "action/joint/position_valid.right",
]
STATE_EE_NAMES = [
    "state/end/arm_position.left.x",
    "state/end/arm_position.left.y",
    "state/end/arm_position.left.z",
    "state/end/arm_orientation.left.qx",
    "state/end/arm_orientation.left.qy",
    "state/end/arm_orientation.left.qz",
    "state/end/arm_orientation.left.qw",
    "state/end/arm_position.right.x",
    "state/end/arm_position.right.y",
    "state/end/arm_position.right.z",
    "state/end/arm_orientation.right.qx",
    "state/end/arm_orientation.right.qy",
    "state/end/arm_orientation.right.qz",
    "state/end/arm_orientation.right.qw",
]
ACTION_EE_NAMES = [
    "action/end/position.left.x",
    "action/end/position.left.y",
    "action/end/position.left.z",
    "action/end/orientation.left.qx",
    "action/end/orientation.left.qy",
    "action/end/orientation.left.qz",
    "action/end/orientation.left.qw",
    "action/end/position.right.x",
    "action/end/position.right.y",
    "action/end/position.right.z",
    "action/end/orientation.right.qx",
    "action/end/orientation.right.qy",
    "action/end/orientation.right.qz",
    "action/end/orientation.right.qw",
]
STATE_EE_VALID_NAMES = [
    "state/end/pose_valid.left",
    "state/end/pose_valid.right",
]
ACTION_EE_VALID_NAMES = [
    "action/end/pose_valid.left",
    "action/end/pose_valid.right",
]

SourceKind = Literal["archive", "directory", "packed_simulation"]


@dataclass(frozen=True)
class SourceUnit:
    kind: SourceKind
    source: str
    output_relative: str


@dataclass(frozen=True)
class ConversionConfig:
    source_root: str
    output_root: str
    work_root: str
    overwrite: bool
    data_file_size_mb: int | None
    video_file_size_mb: int | None


@dataclass(frozen=True)
class FieldMapping:
    state_width: int
    action_width: int
    state_qpos: tuple[int, ...]
    state_ee: tuple[int, ...]
    action_qpos: tuple[int, ...]
    action_ee: tuple[int, ...]
    state_waist: tuple[int, ...]
    action_waist: tuple[int, ...]

    @classmethod
    def from_info(cls, info: dict[str, Any]) -> "FieldMapping":
        features = info.get("features", {})
        state_feature = features.get(OLD_STATE_KEY, {})
        action_feature = features.get(OLD_ACTION_KEY, {})
        state_fields = state_feature.get("field_descriptions", {})
        action_fields = action_feature.get("field_descriptions", {})

        state_width = _single_dimension(state_feature, OLD_STATE_KEY)
        action_width = _single_dimension(action_feature, OLD_ACTION_KEY)

        state_grippers = (
            _field_indices(state_fields, "state/left_effector/position", 1)[0],
            _field_indices(state_fields, "state/right_effector/position", 1)[0],
        )
        state_joints = _field_indices(state_fields, "state/joint/position", 14)
        state_position = _field_indices(state_fields, "state/end/arm_position", 6)
        state_orientation = _field_indices(
            state_fields,
            "state/end/arm_orientation",
            8,
        )

        action_grippers = (
            _field_indices(action_fields, "action/left_effector/position", 1)[0],
            _field_indices(action_fields, "action/right_effector/position", 1)[0],
        )
        action_joints = _field_indices(action_fields, "action/joint/position", 14)
        action_position = _field_indices(action_fields, "action/end/position", 6)
        action_orientation = _field_indices(
            action_fields,
            "action/end/orientation",
            8,
        )

        return cls(
            state_width=state_width,
            action_width=action_width,
            state_qpos=_qpos_indices(state_joints, state_grippers),
            state_ee=_ee_indices(state_position, state_orientation),
            action_qpos=_qpos_indices(action_joints, action_grippers),
            action_ee=_ee_indices(action_position, action_orientation),
            state_waist=_field_indices(state_fields, "state/waist/position", 5),
            action_waist=_field_indices(action_fields, "action/waist/position", 5),
        )


def _single_dimension(feature: dict[str, Any], feature_name: str) -> int:
    shape = feature.get("shape")
    if not isinstance(shape, list) or len(shape) != 1 or int(shape[0]) < 1:
        raise ValueError(f"{feature_name} has invalid shape: {shape}")
    return int(shape[0])


def _field_indices(
    field_descriptions: dict[str, Any],
    field_name: str,
    expected_size: int,
) -> tuple[int, ...]:
    indices = tuple(
        int(value)
        for value in field_descriptions.get(field_name, {}).get("indices", [])
    )
    if len(indices) != expected_size:
        raise ValueError(
            f"{field_name} has {len(indices)} indices, expected {expected_size}: {indices}"
        )
    return indices


def _qpos_indices(
    joints: tuple[int, ...],
    grippers: tuple[int, int],
) -> tuple[int, ...]:
    return (*joints[:7], grippers[0], *joints[7:], grippers[1])


def _ee_indices(
    position: tuple[int, ...],
    orientation: tuple[int, ...],
) -> tuple[int, ...]:
    return (
        *position[:3],
        *orientation[:4],
        *position[3:],
        *orientation[4:],
    )


def build_unified_features(fps: int) -> dict[str, dict[str, Any]]:
    features = {
        "state.qpos": {
            "dtype": "float32",
            "shape": [16],
            "names": {"motors": STATE_QPOS_NAMES},
            "fps": fps,
            "description": (
                "Observed absolute G2 configuration: left arm joints 1-7 [rad], "
                "left gripper position, right arm joints 1-7 [rad], right gripper "
                "position. The source fields are state/joint/position and the two "
                "state/*_effector/position scalars."
            ),
        },
        "state.ee": {
            "dtype": "float32",
            "shape": [14],
            "names": {"motors": STATE_EE_NAMES},
            "fps": fps,
            "description": (
                "Observed absolute left/right end-effector poses, each "
                "[x,y,z,qx,qy,qz,qw], from state/end/arm_position and "
                "state/end/arm_orientation. Quaternions are normalized xyzw."
            ),
        },
        "state.ee_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {"motors": STATE_EE_VALID_NAMES},
            "fps": fps,
            "description": (
                "Per-side [left,right] state.ee validity. Invalid or missing poses "
                "are finite zero placeholders and have mask value 0."
            ),
        },
        "action.qpos": {
            "dtype": "float32",
            "shape": [16],
            "names": {"motors": ACTION_QPOS_NAMES},
            "fps": fps,
            "description": (
                "Commanded absolute G2 joint-position target: left arm joints 1-7 "
                "+ left gripper + right arm joints 1-7 + right gripper. It is not "
                "a delta action."
            ),
        },
        "action.qpos_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {"motors": ACTION_QPOS_VALID_NAMES},
            "fps": fps,
            "description": (
                "Per-side [left,right] action.qpos validity. 1 means all seven arm "
                "targets and the effector target are finite; invalid sides are stored "
                "as finite zero placeholders with mask value 0."
            ),
        },
        "action.ee": {
            "dtype": "float32",
            "shape": [14],
            "names": {"motors": ACTION_EE_NAMES},
            "fps": fps,
            "description": (
                "Commanded absolute left/right end-effector pose target, each "
                "[x,y,z,qx,qy,qz,qw], from action/end/position and "
                "action/end/orientation. It is not a delta pose."
            ),
        },
        "action.ee_valid": {
            "dtype": "float32",
            "shape": [2],
            "names": {"motors": ACTION_EE_VALID_NAMES},
            "fps": fps,
            "description": (
                "Per-side [left,right] action.ee validity. Invalid or missing poses "
                "are finite zero placeholders and have mask value 0."
            ),
        },
    }
    for prefix, names in (("state", STATE_WAIST_NAMES), ("action", ACTION_WAIST_NAMES)):
        features[f"{prefix}.waist"] = {
            "dtype": "float32",
            "shape": [5],
            "names": {"motors": names},
            "fps": fps,
            "description": (
                f"{'Measured' if prefix == 'state' else 'Commanded absolute target'} "
                "G2 five-joint waist position. Native source order and units are "
                f"preserved from {prefix}/waist/position; no reordering or delta conversion."
            ),
        }
    origins = {
        "state.waist": "source LeRobot v2.1 observation.state field state/waist/position",
        "action.waist": "source LeRobot v2.1 action field action/waist/position",
        "state.qpos": (
            "source LeRobot v2.1 observation.state fields state/joint/position + "
            "state/left_effector/position + state/right_effector/position"
        ),
        "state.ee": (
            "source LeRobot v2.1 observation.state fields state/end/arm_position + "
            "state/end/arm_orientation"
        ),
        "state.ee_valid": (
            "derived from source LeRobot v2.1 observation.state fields "
            "state/end/arm_position + state/end/arm_orientation"
        ),
        "action.qpos": (
            "source LeRobot v2.1 action fields action/joint/position + "
            "action/left_effector/position + action/right_effector/position"
        ),
        "action.qpos_valid": (
            "derived from source LeRobot v2.1 action fields action/joint/position + "
            "action/left_effector/position + action/right_effector/position"
        ),
        "action.ee": (
            "source LeRobot v2.1 action fields action/end/position + action/end/orientation"
        ),
        "action.ee_valid": (
            "derived from source LeRobot v2.1 action fields "
            "action/end/position + action/end/orientation"
        ),
    }
    return annotate_features(
        features,
        embodiment="AgiBot G2 dual-arm",
        origins=origins,
    )


def map_robot_vectors(
    state: np.ndarray,
    action: np.ndarray,
    mapping: FieldMapping,
) -> dict[str, np.ndarray]:
    """Map source flat vectors to the shared qpos/EE schema."""
    state = np.asarray(state, dtype=np.float32)
    action = np.asarray(action, dtype=np.float32)
    if state.ndim != 2 or state.shape[1] != mapping.state_width:
        raise ValueError(
            f"{OLD_STATE_KEY} has shape {state.shape}, expected (*,{mapping.state_width})"
        )
    if action.ndim != 2 or action.shape[1] != mapping.action_width:
        raise ValueError(
            f"{OLD_ACTION_KEY} has shape {action.shape}, expected (*,{mapping.action_width})"
        )
    if len(state) != len(action):
        raise ValueError(f"state/action row mismatch: {len(state)} != {len(action)}")

    state_qpos = state[:, mapping.state_qpos]
    _require_finite(state_qpos, "state.qpos")
    state_waist = state[:, mapping.state_waist]
    action_waist = action[:, mapping.action_waist]
    _require_finite(state_waist, "state.waist")
    _require_finite(action_waist, "action.waist")
    action_qpos, action_qpos_valid = _sanitize_bimanual_qpos(
        action[:, mapping.action_qpos]
    )

    state_ee, state_valid = _normalize_ee(state[:, mapping.state_ee])
    action_ee, action_valid = _normalize_ee(action[:, mapping.action_ee])
    return {
        "state.qpos": state_qpos.astype(np.float32, copy=False),
        "state.waist": state_waist,
        "state.ee": state_ee,
        "state.ee_valid": state_valid,
        "action.qpos": action_qpos,
        "action.waist": action_waist,
        "action.qpos_valid": action_qpos_valid,
        "action.ee": action_ee,
        "action.ee_valid": action_valid,
    }


def _require_finite(values: np.ndarray, feature_name: str) -> None:
    invalid_rows = ~np.isfinite(values).all(axis=1)
    if invalid_rows.any():
        raise ValueError(
            f"{feature_name} contains non-finite values in {int(invalid_rows.sum())} rows"
        )


def _sanitize_bimanual_qpos(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    action = np.asarray(values, dtype=np.float32).copy()
    if action.ndim != 2 or action.shape[1] != 16:
        raise ValueError(f"action.qpos has shape {action.shape}, expected (*,16)")
    valid = np.zeros((len(action), 2), dtype=np.float32)
    for side, start in enumerate((0, 8)):
        group = action[:, start : start + 8]
        side_valid = np.isfinite(group).all(axis=1)
        group[~side_valid] = 0.0
        valid[:, side] = side_valid.astype(np.float32)
    return action, valid


def _normalize_ee(raw_ee: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(raw_ee, dtype=np.float32).copy()
    if values.ndim != 2 or values.shape[1] != 14:
        raise ValueError(f"EE values have shape {values.shape}, expected (*,14)")

    valid = np.zeros((len(values), 2), dtype=np.float32)
    for side, start in enumerate((0, 7)):
        pose = values[:, start : start + 7]
        quaternion = pose[:, 3:7]
        quaternion_norm = np.linalg.norm(quaternion, axis=1)
        side_valid = np.isfinite(pose).all(axis=1) & (quaternion_norm > 1e-8)
        pose[~side_valid] = 0.0
        pose[side_valid, 3:7] /= quaternion_norm[side_valid, None]
        valid[:, side] = side_valid.astype(np.float32)
    return values, valid


def discover_sources(
    source_root: Path,
    source_kind: Literal["all", "real", "simulation"],
    includes: list[str],
    excludes: list[str],
) -> list[SourceUnit]:
    source_root = source_root.resolve()
    units: list[SourceUnit] = []

    if source_kind in {"all", "real"}:
        for group in ("ImitationLearning", "RichInteraction", "ReinforcementLearning"):
            group_root = source_root / group
            for archive in sorted(group_root.glob("**/*.tar.gz")):
                relative = archive.relative_to(source_root).as_posix()
                output_relative = relative.removesuffix(".tar.gz")
                units.append(SourceUnit("archive", str(archive), output_relative))

    if source_kind in {"all", "simulation"}:
        simulation_root = source_root / "simulation_lerobot"
        for info_path in sorted(simulation_root.glob("**/meta/info.json")):
            leaf = info_path.parent.parent
            data_path = leaf / "data"
            if data_path.is_symlink():
                continue
            if not any(data_path.glob("chunk-*/episode_*.parquet")):
                continue
            relative = leaf.relative_to(source_root).as_posix()
            units.append(SourceUnit("directory", str(leaf), relative))
        extracted = {unit.output_relative.removeprefix("simulation_lerobot/") for unit in units if unit.kind == "directory"}
        for meta_part in sorted((source_root / "simulation").glob("**/lite/meta.tar.gz.000")):
            leaf = meta_part.parent
            relative = leaf.relative_to(source_root).as_posix()
            if relative.removeprefix("simulation/") not in extracted:
                units.append(SourceUnit("packed_simulation", str(leaf), relative))

    units = [
        unit
        for unit in units
        if _matches_filters(unit.output_relative, includes, excludes)
    ]
    return sorted(units, key=lambda unit: unit.output_relative)


def _matches_filters(relative: str, includes: list[str], excludes: list[str]) -> bool:
    name = Path(relative).name

    def matches(pattern: str) -> bool:
        return fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(name, pattern)

    if includes and not any(matches(pattern) for pattern in includes):
        return False
    return not any(matches(pattern) for pattern in excludes)


def convert_source(unit: SourceUnit, config: ConversionConfig) -> dict[str, Any]:
    output_root = Path(config.output_root)
    final_leaf = output_root / unit.output_relative
    marker_path = final_leaf / "meta" / "unified_action_space.json"
    if marker_path.is_file() and not config.overwrite:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
        if set(NEW_NUMERIC_KEYS).issubset(marker.get("added_features", [])):
            _ensure_part_compatibility(final_leaf, marker)
            return _result(unit, "skipped", final_leaf, "already complete", marker)
        raise ValueError(f"Stale converted part without waist fields: {final_leaf}")
    if final_leaf.exists() and not config.overwrite:
        raise FileExistsError(
            f"Incomplete output exists at {final_leaf}; inspect it or rerun with --overwrite"
        )
    if final_leaf.exists():
        shutil.rmtree(final_leaf)

    work_root = Path(config.work_root)
    work_root.mkdir(parents=True, exist_ok=True)
    job_dir = Path(tempfile.mkdtemp(prefix="agibot2026_", dir=work_root))
    try:
        old_root, old_repo_id = _prepare_v21_source(unit, job_dir)
        stage_root = job_dir / "v30"
        _official_v21_to_v30(
            old_root=old_root,
            old_repo_id=old_repo_id,
            new_root=stage_root,
            new_repo_id=unit.output_relative,
            data_file_size_mb=config.data_file_size_mb,
            video_file_size_mb=config.video_file_size_mb,
        )
        stage_leaf = stage_root / unit.output_relative
        summary = rewrite_unified_action_space(stage_leaf, unit)
        _ensure_part_compatibility(stage_leaf, summary)

        final_leaf.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(stage_leaf), str(final_leaf))
        return _result(unit, "converted", final_leaf, "ok", summary)
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)


def _prepare_v21_source(unit: SourceUnit, job_dir: Path) -> tuple[Path, str]:
    source = Path(unit.source)
    if unit.kind == "directory":
        return source.parent, source.name

    if unit.kind == "packed_simulation":
        from agibotworld2026_2lerobot.source_io import extract_simulation

        destination = job_dir / "extracted" / "dataset"
        extract_simulation(source, destination)
        return destination.parent, destination.name

    extract_root = job_dir / "extracted"
    extract_root.mkdir(parents=True)
    subprocess.run(
        [
            "tar",
            "--extract",
            "--gzip",
            "--file",
            str(source),
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
            f"Archive {source} contains {len(info_paths)} v2.1 info.json files, expected 1"
        )
    dataset_root = info_paths[0].parent.parent
    return dataset_root.parent, dataset_root.name


def _official_v21_to_v30(
    old_root: Path,
    old_repo_id: str,
    new_root: Path,
    new_repo_id: str,
    data_file_size_mb: int | None,
    video_file_size_mb: int | None,
) -> None:
    new_root.mkdir(parents=True, exist_ok=True)
    try:
        from lerobot.datasets.v30.convert_single_dataset_v21_to_v30 import convert_dataset
    except ModuleNotFoundError as exc:
        if exc.name not in {
            "lerobot.datasets.v30",
            "lerobot.datasets.v30.convert_single_dataset_v21_to_v30",
        }:
            raise
        # New LeRobot releases expose conversion stages, but their public entry
        # point moves the original dataset. Call only the read-only stages.
        from lerobot.scripts import convert_dataset_v21_to_v30 as converter

        source = old_root / old_repo_id
        destination = new_root / new_repo_id
        data_size = data_file_size_mb or converter.DEFAULT_DATA_FILE_SIZE_IN_MB
        video_size = video_file_size_mb or converter.DEFAULT_VIDEO_FILE_SIZE_IN_MB
        converter.validate_local_dataset_version(source)
        converter.convert_info(source, destination, data_size, video_size)
        converter.convert_tasks(source, destination)
        episodes = converter.convert_data(source, destination, data_size)
        videos = converter.convert_videos(source, destination, video_size)
        converter.convert_episodes_metadata(source, destination, episodes, videos)
        # Typed DatasetInfo can discard source-only field_descriptions. Keep
        # those until the semantic vector rewrite has consumed them.
        original = json.loads((source / "meta/info.json").read_text())
        _write_json_atomic(destination / "meta/source_info.json", original)
        info_path = destination / "meta/info.json"
        info = json.loads(info_path.read_text())
        for key in (OLD_STATE_KEY, OLD_ACTION_KEY):
            info["features"][key]["field_descriptions"] = original["features"][key]["field_descriptions"]
        _write_json_atomic(info_path, info)
        return
    convert_dataset(
        old_repo_id=old_repo_id,
        new_repo_id=new_repo_id,
        old_root=old_root,
        new_root=new_root,
        data_file_size_in_mb=data_file_size_mb,
        video_file_size_in_mb=video_file_size_mb,
        push_to_hub=False,
        force_conversion=True,
    )


def rewrite_unified_action_space(
    dataset_root: Path,
    source_unit: SourceUnit,
) -> dict[str, Any]:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from lerobot.datasets.compute_stats import aggregate_stats, compute_episode_stats
    try:
        from lerobot.datasets.io_utils import load_stats, write_stats
    except ImportError:
        from lerobot.datasets.utils import load_stats, write_stats

    info_path = dataset_root / "meta" / "info.json"
    info = json.loads(info_path.read_text(encoding="utf-8"))
    if info.get("codebase_version") != TARGET_VERSION:
        raise ValueError(
            f"Expected converted {TARGET_VERSION}, got {info.get('codebase_version')}"
        )
    mapping = FieldMapping.from_info(info)
    fps = int(info["fps"])
    new_features = build_unified_features(fps)

    episode_stats: dict[int, dict[str, dict[str, np.ndarray]]] = {}
    invalid_counts = {
        "state.ee.left": 0,
        "state.ee.right": 0,
        "action.ee.left": 0,
        "action.ee.right": 0,
    }
    total_rows = 0

    for parquet_path in sorted(dataset_root.glob("data/chunk-*/file-*.parquet")):
        table = pq.read_table(parquet_path)
        state = _fixed_list_to_numpy(table[OLD_STATE_KEY], mapping.state_width)
        action = _fixed_list_to_numpy(table[OLD_ACTION_KEY], mapping.action_width)
        mapped = map_robot_vectors(state, action, mapping)
        total_rows += len(state)

        invalid_counts["state.ee.left"] += int((mapped["state.ee_valid"][:, 0] == 0).sum())
        invalid_counts["state.ee.right"] += int((mapped["state.ee_valid"][:, 1] == 0).sum())
        invalid_counts["action.ee.left"] += int((mapped["action.ee_valid"][:, 0] == 0).sum())
        invalid_counts["action.ee.right"] += int((mapped["action.ee_valid"][:, 1] == 0).sum())

        episode_indices = table["episode_index"].combine_chunks().to_numpy(
            zero_copy_only=False
        )
        for episode_index in np.unique(episode_indices):
            index = int(episode_index)
            if index in episode_stats:
                raise ValueError(f"Episode {index} is split across data parquet files")
            row_mask = episode_indices == episode_index
            episode_data = {key: values[row_mask].astype(np.float64) for key, values in mapped.items()}
            episode_stats[index] = compute_episode_stats(
                episode_data,
                new_features,
            )

        rewritten = table.drop([OLD_STATE_KEY, OLD_ACTION_KEY])
        for feature_name in NEW_NUMERIC_KEYS:
            rewritten = rewritten.append_column(
                feature_name,
                _numpy_to_fixed_list(mapped[feature_name], pa),
            )
        _write_parquet_atomic(rewritten.replace_schema_metadata(None), parquet_path, pq)

    if not episode_stats:
        raise ValueError(f"No data parquet rows found below {dataset_root}")

    _rewrite_episode_metadata(dataset_root, episode_stats, pa, pq)
    global_stats = load_stats(dataset_root)
    if global_stats is None:
        raise FileNotFoundError(f"Missing meta/stats.json below {dataset_root}")
    global_stats.pop(OLD_STATE_KEY, None)
    global_stats.pop(OLD_ACTION_KEY, None)
    unified_stats = aggregate_stats(list(episode_stats.values()))
    invalid_unified_stats = _nonfinite_paths(unified_stats)
    if invalid_unified_stats:
        raise ValueError(
            "Unified action/state statistics contain non-finite values: "
            f"{invalid_unified_stats[:20]}"
        )
    global_stats.update(unified_stats)
    preserved_nonfinite_stats = _nonfinite_paths(
        {
            key: value
            for key, value in global_stats.items()
            if key not in NEW_NUMERIC_KEYS
        }
    )
    write_stats(global_stats, dataset_root)

    features = {
        key: value
        for key, value in info.get("features", {}).items()
        if key not in {OLD_STATE_KEY, OLD_ACTION_KEY}
    }
    features.update(new_features)
    info["features"] = annotate_features(
        features,
        embodiment="AgiBot G2 dual-arm",
        origins=lambda key: f"source LeRobot v2.1 feature {key}",
    )
    _write_json_atomic(info_path, info)

    summary = {
        "source": asdict(source_unit),
        "source_version": SOURCE_VERSION,
        "numeric_stats_version": "float64-v1",
        "target_version": TARGET_VERSION,
        "frames": total_rows,
        "episodes": len(episode_stats),
        "mapping": asdict(mapping),
        "invalid_ee_frames": invalid_counts,
        "removed_source_features": [OLD_STATE_KEY, OLD_ACTION_KEY],
        "added_features": list(NEW_NUMERIC_KEYS),
        "dropped_source_action_channels": [
            "action/head/position",
            "action/robot/velocity",
        ],
        "preserved_nonfinite_source_stats": preserved_nonfinite_stats,
    }
    _write_json_atomic(
        dataset_root / "meta" / "unified_action_space.json",
        summary,
    )
    return summary


def _ensure_part_compatibility(root: Path, summary: dict[str, Any], *, video_workers=1, decoder_threads=None) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq
    from lerobot.datasets.compute_stats import aggregate_stats, compute_episode_stats
    try:
        from lerobot.datasets.io_utils import load_stats, write_stats
    except ImportError:
        from lerobot.datasets.utils import load_stats, write_stats
    from agibotworld2026_2lerobot.video_compat import VIDEO_STATS_VERSION, repair_video_metadata_stats

    if summary.get("numeric_stats_version") != "float64-v1":
        info = json.loads((root / "meta/info.json").read_text())
        episode_stats = {}
        for path in sorted(root.glob("data/chunk-*/*.parquet")):
            table = pq.read_table(path)
            indices = table["episode_index"].to_numpy()
            arrays = {key: _fixed_list_to_numpy(table[key], info["features"][key]["shape"][0]).astype(np.float64)
                      for key in NEW_NUMERIC_KEYS}
            for index in np.unique(indices):
                if int(index) in episode_stats:
                    raise ValueError(f"Episode {index} spans parquet files")
                episode_stats[int(index)] = compute_episode_stats(
                    {key: value[indices == index] for key, value in arrays.items()}, info["features"])
        _rewrite_episode_metadata(root, episode_stats, pa, pq)
        stats = load_stats(root)
        stats.update(aggregate_stats(list(episode_stats.values())))
        write_stats(stats, root)
        summary["numeric_stats_version"] = "float64-v1"
    compat_path = root / "meta/video_compat.json"
    compatibility = json.loads(compat_path.read_text()) if compat_path.is_file() else {}
    if compatibility.get("version") != VIDEO_STATS_VERSION:
        updated = repair_video_metadata_stats(root, workers=video_workers, decoder_threads=decoder_threads)
        updated["repaired"] = {**compatibility.get("repaired", {}), **updated["repaired"]}
        _write_json_atomic(compat_path, updated)
        compatibility = updated
    summary["video_compat"] = compatibility
    summary.setdefault("original_nonfinite_source_stats", summary.get("preserved_nonfinite_source_stats", []))
    summary["preserved_nonfinite_source_stats"] = _nonfinite_paths(load_stats(root))
    _write_json_atomic(root / "meta/unified_action_space.json", summary)


def _fixed_list_to_numpy(column: Any, expected_width: int) -> np.ndarray:
    array = column.combine_chunks()
    if array.null_count:
        raise ValueError(f"Numeric source column contains {array.null_count} null rows")
    list_size = getattr(array.type, "list_size", None)
    if list_size is None and hasattr(array, "offsets"):
        lengths = np.diff(array.offsets.to_numpy(zero_copy_only=False))
        if not np.all(lengths == expected_width):
            raise ValueError(f"Numeric source column has inconsistent lengths, expected {expected_width}")
    elif list_size != expected_width:
        raise ValueError(
            f"Numeric source column has list size {list_size}, expected {expected_width}"
        )
    values = array.flatten().to_numpy(zero_copy_only=False).astype(
        np.float32,
        copy=False,
    )
    return values.reshape(len(array), expected_width)


def _numpy_to_fixed_list(values: np.ndarray, pa: Any) -> Any:
    values = np.asarray(values, dtype=np.float32)
    flat = pa.array(values.reshape(-1), type=pa.float32())
    return pa.FixedSizeListArray.from_arrays(flat, values.shape[1])


def _write_parquet_atomic(table: Any, path: Path, pq: Any) -> None:
    temporary_path = path.with_suffix(".parquet.tmp")
    pq.write_table(table, temporary_path, compression="zstd")
    temporary_path.replace(path)


def _rewrite_episode_metadata(
    dataset_root: Path,
    episode_stats: dict[int, dict[str, dict[str, np.ndarray]]],
    pa: Any,
    pq: Any,
) -> None:
    paths = sorted(dataset_root.glob("meta/episodes/chunk-*/file-*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No episode metadata parquet below {dataset_root}")

    seen: set[int] = set()
    for path in paths:
        table = pq.read_table(path)
        episode_indices = [int(value) for value in table["episode_index"].to_pylist()]
        stale_columns = [
            name
            for name in table.column_names
            if name.startswith(f"stats/{OLD_STATE_KEY}/")
            or name.startswith(f"stats/{OLD_ACTION_KEY}/")
            or any(name.startswith(f"stats/{key}/") for key in NEW_NUMERIC_KEYS)
        ]
        rewritten = table.drop(stale_columns)
        for feature_name in NEW_NUMERIC_KEYS:
            for statistic_name in STATISTIC_NAMES:
                column_name = f"stats/{feature_name}/{statistic_name}"
                column_values = []
                for episode_index in episode_indices:
                    if episode_index not in episode_stats:
                        raise KeyError(f"Missing computed stats for episode {episode_index}")
                    values = episode_stats[episode_index][feature_name][statistic_name]
                    column_values.append(np.asarray(values).tolist())
                rewritten = rewritten.append_column(column_name, pa.array(column_values))
        _write_parquet_atomic(rewritten.replace_schema_metadata(None), path, pq)
        seen.update(episode_indices)

    if seen != set(episode_stats):
        missing = sorted(set(episode_stats) - seen)
        raise ValueError(f"Episode metadata is missing episode indices: {missing[:20]}")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)


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
        invalid_indices = np.argwhere(~np.isfinite(payload))
        return [
            prefix + "[" + ",".join(str(int(index)) for index in indices) + "]"
            for indices in invalid_indices
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
    parser.add_argument(
        "--output-path",
        "--output-root",
        dest="output_path",
        type=Path,
        required=True,
        help=(
            "Final aggregated LeRobot root containing data/, meta/, and videos/. "
            "--output-root is retained as a compatibility alias."
        ),
    )
    parser.add_argument(
        "--work-root",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--source-kind",
        choices=["all", "real", "simulation"],
        default="all",
    )
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--max-sources", type=int)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--data-file-size-mb", type=int)
    parser.add_argument("--video-file-size-mb", type=int)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument(
        "--keep-parts",
        action="store_true",
        help="Keep per-source temporary LeRobot datasets after aggregation.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    if not args.source_root.is_dir():
        raise FileNotFoundError(f"Source root not found: {args.source_root}")
    if args.workers < 1:
        raise ValueError("--workers must be >= 1")
    if args.max_sources is not None and args.max_sources < 1:
        raise ValueError("--max-sources must be >= 1")
    for name in ("data_file_size_mb", "video_file_size_mb"):
        value = getattr(args, name)
        if value is not None and value < 1:
            raise ValueError(f"--{name.replace('_', '-')} must be >= 1")
    if args.output_path.resolve() == args.source_root.resolve():
        raise ValueError("--output-path must differ from the read-only --source-root")


def main() -> None:
    args = parse_args()
    validate_args(args)
    source_root = args.source_root.expanduser().resolve()
    units = discover_sources(
        source_root,
        source_kind=args.source_kind,
        includes=args.include,
        excludes=args.exclude,
    )
    if args.max_sources is not None:
        units = units[: args.max_sources]
    if not units:
        raise ValueError("No matching canonical AgiBotWorld2026 sources found")

    real_count = sum(unit.kind == "archive" for unit in units)
    simulation_count = sum(unit.kind == "directory" for unit in units)
    print(
        f"Discovered {len(units)} sources: real={real_count}, "
        f"simulation={simulation_count}",
        flush=True,
    )
    if not args.include and not args.exclude and args.source_kind == "all":
        if len(units) != EXPECTED_CANONICAL_LEAVES:
            print(
                f"[WARN] expected {EXPECTED_CANONICAL_LEAVES} canonical sources "
                f"({EXPECTED_REAL_ARCHIVES} real + {EXPECTED_SIMULATION_LEAVES} simulation)",
                flush=True,
            )
    if args.dry_run:
        for unit in units:
            print(f"{unit.kind}\t{unit.output_relative}\t{unit.source}")
        return

    output_path = args.output_path.expanduser().resolve()
    if output_path.exists() and not args.overwrite:
        raise FileExistsError(
            f"Final output already exists at {output_path}; rerun with --overwrite"
        )
    parts_root = output_path.with_name(f"{output_path.name}_parts")
    report_path = output_path.with_name(f"{output_path.name}_reports") / "conversion.jsonl"
    config = ConversionConfig(
        source_root=str(source_root),
        output_root=str(parts_root),
        work_root=str(args.work_root.expanduser().resolve()),
        overwrite=args.overwrite,
        data_file_size_mb=args.data_file_size_mb,
        video_file_size_mb=args.video_file_size_mb,
    )

    records: list[dict[str, Any]] = []
    if args.workers == 1:
        for index, unit in enumerate(units, start=1):
            print(f"[{index}/{len(units)}] {unit.output_relative}", flush=True)
            try:
                record = convert_source(unit, config)
            except Exception as exc:
                record = _result(
                    unit,
                    "failed",
                    parts_root / unit.output_relative,
                    f"{exc}\n{traceback.format_exc()}",
                )
            records.append(record)
            _append_report(report_path, record)
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
                        parts_root / unit.output_relative,
                        f"{exc}\n{traceback.format_exc()}",
                    )
                records.append(record)
                _append_report(report_path, record)
                print(
                    f"[{len(records)}/{len(units)}] {unit.output_relative}: "
                    f"{record['status']}",
                    flush=True,
                )

    converted = sum(record["status"] == "converted" for record in records)
    skipped = sum(record["status"] == "skipped" for record in records)
    failed = [record for record in records if record["status"] == "failed"]
    print(
        f"Finished: converted={converted}, skipped={skipped}, failed={len(failed)}; "
        f"report={report_path}",
        flush=True,
    )
    if failed:
        raise SystemExit(1)

    records_by_source = {
        record["source"]["output_relative"]: record for record in records
    }
    part_roots = [
        Path(records_by_source[unit.output_relative]["output"])
        for unit in units
    ]
    from generic_converter import aggregate_roots

    aggregate_roots(
        part_roots,
        output_path,
        aggr_repo_id=output_path.name,
    )
    if not args.keep_parts:
        shutil.rmtree(parts_root, ignore_errors=True)
    print(f"Final aggregated dataset: {output_path}", flush=True)


if __name__ == "__main__":
    main()
