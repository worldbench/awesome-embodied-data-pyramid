"""Schema definitions and HDF5 mapping for AgiBotWorld-Beta."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

import h5py
import numpy as np
from generic_converter import annotate_feature, annotate_features


EffectorType = Literal["gripper", "dexhand"]


def effector_dimension(effector_type: EffectorType) -> int:
    return 1 if effector_type == "gripper" else 6


def qpos_dimension(effector_type: EffectorType) -> int:
    return 14 + 2 * effector_dimension(effector_type)


def qpos_names(prefix: Literal["state", "action"], effector_type: EffectorType) -> list[str]:
    effector_dim = effector_dimension(effector_type)
    left_effector_names = (
        [f"{prefix}/left_effector/position"]
        if effector_dim == 1
        else [
            f"{prefix}/left_effector/position[{index}]"
            for index in range(effector_dim)
        ]
    )
    right_effector_names = (
        [f"{prefix}/right_effector/position"]
        if effector_dim == 1
        else [
            f"{prefix}/right_effector/position[{index}]"
            for index in range(effector_dim)
        ]
    )
    return [
        *[f"{prefix}/joint/position.left_joint_{index}" for index in range(7)],
        *left_effector_names,
        *[f"{prefix}/joint/position.right_joint_{index}" for index in range(7)],
        *right_effector_names,
    ]


def ee_names(prefix: Literal["state", "action"]) -> list[str]:
    end_position = "end/arm_position" if prefix == "state" else "end/position"
    end_orientation = (
        "end/arm_orientation" if prefix == "state" else "end/orientation"
    )
    return [
        f"{prefix}/{end_position}.left.x",
        f"{prefix}/{end_position}.left.y",
        f"{prefix}/{end_position}.left.z",
        f"{prefix}/{end_orientation}.left.qx",
        f"{prefix}/{end_orientation}.left.qy",
        f"{prefix}/{end_orientation}.left.qz",
        f"{prefix}/{end_orientation}.left.qw",
        f"{prefix}/{end_position}.right.x",
        f"{prefix}/{end_position}.right.y",
        f"{prefix}/{end_position}.right.z",
        f"{prefix}/{end_orientation}.right.qx",
        f"{prefix}/{end_orientation}.right.qy",
        f"{prefix}/{end_orientation}.right.qz",
        f"{prefix}/{end_orientation}.right.qw",
    ]


def _qpos_field_descriptions(
    prefix: Literal["state", "action"],
    effector_type: EffectorType,
) -> dict[str, dict[str, Any]]:
    effector_dim = effector_dimension(effector_type)
    right_arm_start = 7 + effector_dim
    right_effector_start = right_arm_start + 7
    target_or_measurement = "targets" if prefix == "action" else "measurements"
    if effector_type == "gripper":
        if prefix == "action":
            effector_description = (
                "Source-native binary gripper command; 0 means fully open and "
                "1 means fully closed."
            )
        else:
            effector_description = (
                "Unnormalized source-native measured gripper actuator position. "
                "The source metadata does not declare its physical unit; it is "
                "not the action's 0/1 binary convention."
            )
    else:
        effector_description = (
            f"Six dexterous-hand joint-position {target_or_measurement} in radians."
        )
    return {
        f"{prefix}/joint/position.left": {
            "dimensions": 7,
            "indices": list(range(7)),
            "description": (
                f"Left-arm absolute joint-position {target_or_measurement} in radians."
            ),
        },
        f"{prefix}/left_effector/position": {
            "dimensions": effector_dim,
            "indices": list(range(7, 7 + effector_dim)),
            "description": f"Left effector. {effector_description}",
        },
        f"{prefix}/joint/position.right": {
            "dimensions": 7,
            "indices": list(range(right_arm_start, right_arm_start + 7)),
            "description": (
                f"Right-arm absolute joint-position {target_or_measurement} in radians."
            ),
        },
        f"{prefix}/right_effector/position": {
            "dimensions": effector_dim,
            "indices": list(
                range(right_effector_start, right_effector_start + effector_dim)
            ),
            "description": f"Right effector. {effector_description}",
        },
    }


def _ee_field_descriptions(
    prefix: Literal["state", "action"],
) -> dict[str, dict[str, Any]]:
    position_name = "state/end/arm_position" if prefix == "state" else "action/end/position"
    orientation_name = (
        "state/end/arm_orientation"
        if prefix == "state"
        else "action/end/orientation"
    )
    target_or_measurement = "target" if prefix == "action" else "measurement"
    return {
        position_name: {
            "dimensions": 6,
            "indices": [0, 1, 2, 7, 8, 9],
            "description": (
                f"Absolute left/right flange xyz {target_or_measurement}s in meters."
            ),
        },
        orientation_name: {
            "dimensions": 8,
            "indices": [3, 4, 5, 6, 10, 11, 12, 13],
            "description": (
                f"Absolute left/right flange quaternion {target_or_measurement}s "
                "in normalized xyzw order."
            ),
        },
    }


def build_numeric_features(
    effector_type: EffectorType,
) -> dict[str, dict[str, Any]]:
    qpos_dim = qpos_dimension(effector_type)
    effector_text = (
        "one source-native gripper scalar per side"
        if effector_type == "gripper"
        else "six dexterous-hand joints per side"
    )
    features = {
        "state.qpos": {
            "dtype": "float32",
            "shape": (qpos_dim,),
            "names": {"motors": qpos_names("state", effector_type)},
            "field_descriptions": _qpos_field_descriptions("state", effector_type),
            "description": (
                "Observed absolute configuration ordered as left arm 7, left "
                f"effector ({effector_text}), right arm 7, right effector."
            ),
        },
        "state.ee": {
            "dtype": "float32",
            "shape": (14,),
            "names": {"motors": ee_names("state")},
            "field_descriptions": _ee_field_descriptions("state"),
            "description": (
                "Observed absolute left/right flange poses, each "
                "[x,y,z,qx,qy,qz,qw]. Position is meters and quaternion order is xyzw."
            ),
        },
        "state.ee_valid": {
            "dtype": "float32",
            "shape": (2,),
            "names": {"motors": ["state/end/pose_valid.left", "state/end/pose_valid.right"]},
            "description": (
                "Per-side [left,right] validity mask for state.ee. Invalid poses "
                "are finite zero placeholders and have mask value 0."
            ),
        },
        "action.qpos": {
            "dtype": "float32",
            "shape": (qpos_dim,),
            "names": {"motors": qpos_names("action", effector_type)},
            "field_descriptions": _qpos_field_descriptions("action", effector_type),
            "description": (
                "Commanded absolute configuration target ordered as left arm 7, "
                f"left effector ({effector_text}), right arm 7, right effector. "
                "This is not a delta action."
            ),
        },
        "action.qpos_valid": {
            "dtype": "float32",
            "shape": (2,),
            "names": {
                "motors": [
                    "action/joint/position_valid.left",
                    "action/joint/position_valid.right",
                ]
            },
            "description": (
                "Per-side [left,right] validity mask for action.qpos. Required joint "
                "and effector targets are finite when mask value is 1; an invalid side "
                "would be stored as finite zero placeholders with mask value 0."
            ),
        },
        "action.ee": {
            "dtype": "float32",
            "shape": (14,),
            "names": {"motors": ee_names("action")},
            "field_descriptions": _ee_field_descriptions("action"),
            "description": (
                "Commanded absolute left/right flange pose targets, each "
                "[x,y,z,qx,qy,qz,qw]. Position is meters; quaternion order is "
                "xyzw. This is not a delta pose."
            ),
        },
        "action.ee_valid": {
            "dtype": "float32",
            "shape": (2,),
            "names": {"motors": ["action/end/pose_valid.left", "action/end/pose_valid.right"]},
            "description": (
                "Per-side [left,right] validity mask for action.ee. Invalid poses "
                "are finite zero placeholders and have mask value 0."
            ),
        },
    }
    for prefix in ("state", "action"):
        features[f"{prefix}.waist"] = {
            "dtype": "float32",
            "shape": (2,),
            "names": {"motors": ["pitch", "lift"]},
            "description": (
                "Measured waist position" if prefix == "state" else "Commanded absolute waist position target"
            ) + " in source order [pitch, lift]. Source-native values are preserved without normalization or unit conversion.",
        }
    origins = {
        "state.waist": "proprio_stats.h5::state/waist/position",
        "action.waist": "proprio_stats.h5::action/waist/position",

        "state.qpos": "proprio_stats.h5::state/joint/position + state/effector/position",
        "state.ee": "proprio_stats.h5::state/end/position + state/end/orientation",
        "state.ee_valid": (
            "derived from proprio_stats.h5::state/end/position + state/end/orientation"
        ),
        "action.qpos": "proprio_stats.h5::action/joint/position + action/effector/position",
        "action.qpos_valid": (
            "derived from proprio_stats.h5::action/joint/position + action/effector/position"
        ),
        "action.ee": "proprio_stats.h5::action/end/position + action/end/orientation",
        "action.ee_valid": (
            "derived from proprio_stats.h5::action/end/position + action/end/orientation"
        ),
    }
    # Keep each waist feature with the corresponding state/action fields.
    features = {
        key: value
        for prefix in ("state.", "action.")
        for key, value in features.items()
        if key.startswith(prefix)
    }
    return annotate_features(
        features,
        embodiment=f"A2D {effector_type}",
        origins=origins,
    )


def build_features(
    raw_config: dict[str, Any],
    effector_type: EffectorType,
    save_depth: bool,
) -> dict[str, dict[str, Any]]:
    features = {}
    for key, value in raw_config["images"].items():
        feature_key = f"observation.images.{key}"
        origin = (
            f"observations/{{task_id}}/{{episode_id}}/depth/{key}*"
            if "depth" in key
            else f"observations/{{task_id}}/{{episode_id}}/videos/{key}_color.mp4"
        )
        features[feature_key] = annotate_feature(
            deepcopy(value),
            embodiment=f"A2D {effector_type}",
            origin_data=origin,
            default_description=f"AgiBotWorld Beta observation image stream {key}.",
        )
    if not save_depth:
        features.pop("observation.images.head_depth", None)
    features.update(build_numeric_features(effector_type))
    return features


def compose_qpos(
    joint_position: np.ndarray,
    effector_position: np.ndarray,
    effector_type: EffectorType,
    require_finite: bool = True,
) -> np.ndarray:
    joints = np.asarray(joint_position, dtype=np.float32)
    effectors = np.asarray(effector_position, dtype=np.float32)
    expected_effector_dim = 2 * effector_dimension(effector_type)
    if joints.ndim != 2 or joints.shape[1] != 14:
        raise ValueError(f"Joint position must have shape (N,14), got {joints.shape}")
    if effectors.ndim != 2 or effectors.shape != (len(joints), expected_effector_dim):
        raise ValueError(
            f"{effector_type} effector position must have shape "
            f"({len(joints)},{expected_effector_dim}), got {effectors.shape}"
        )
    effector_dim = effector_dimension(effector_type)
    result = np.concatenate(
        [
            joints[:, :7],
            effectors[:, :effector_dim],
            joints[:, 7:],
            effectors[:, effector_dim:],
        ],
        axis=1,
    )
    if require_finite:
        _require_finite(result, "qpos")
    return result.astype(np.float32, copy=False)


def sanitize_bimanual_qpos_action(
    values: np.ndarray,
    effector_type: EffectorType,
) -> tuple[np.ndarray, np.ndarray]:
    action = np.asarray(values, dtype=np.float32).copy()
    side_width = 7 + effector_dimension(effector_type)
    if action.ndim != 2 or action.shape[1] != 2 * side_width:
        raise ValueError(
            f"action.qpos must have shape (N,{2 * side_width}), got {action.shape}"
        )
    valid = np.zeros((len(action), 2), dtype=np.float32)
    for side, start in enumerate((0, side_width)):
        group = action[:, start : start + side_width]
        side_valid = np.isfinite(group).all(axis=1)
        group[~side_valid] = 0.0
        valid[:, side] = side_valid.astype(np.float32)
    return action, valid


def compose_ee(
    position: np.ndarray,
    orientation: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    position = np.asarray(position, dtype=np.float32)
    orientation = np.asarray(orientation, dtype=np.float32)
    frame_count = len(position)
    if position.shape != (frame_count, 2, 3):
        raise ValueError(f"EE position must have shape (N,2,3), got {position.shape}")
    if orientation.shape != (frame_count, 2, 4):
        raise ValueError(
            f"EE orientation must have shape (N,2,4), got {orientation.shape}"
        )

    values = np.concatenate([position, orientation], axis=2)
    valid = np.zeros((frame_count, 2), dtype=np.float32)
    for side in range(2):
        pose = values[:, side]
        quaternion = pose[:, 3:7]
        quaternion_norm = np.linalg.norm(quaternion, axis=1)
        side_valid = np.isfinite(pose).all(axis=1) & (quaternion_norm > 1e-8)
        pose[~side_valid] = 0
        pose[side_valid, 3:7] /= quaternion_norm[side_valid, None]
        valid[:, side] = side_valid.astype(np.float32)
    return values.reshape(frame_count, 14), valid


def _require_finite(values: np.ndarray, feature_name: str) -> None:
    invalid_rows = ~np.isfinite(values).all(axis=1)
    if invalid_rows.any():
        raise ValueError(
            f"{feature_name} contains non-finite values in "
            f"{int(invalid_rows.sum())} rows"
        )


def _has_nonempty_dataset(h5_file: h5py.File, key: str) -> bool:
    dataset = h5_file.get(key)
    return dataset is not None and dataset.size > 0


def _read_state(
    h5_file: h5py.File,
    key: str,
    frame_count: int,
    expected_tail: tuple[int, ...],
    required: bool,
) -> np.ndarray:
    dataset = h5_file.get(f"state/{key}")
    if dataset is None or dataset.size == 0:
        if required:
            raise ValueError(f"Missing required state/{key}")
        return np.zeros((frame_count, *expected_tail), dtype=np.float32)
    values = np.asarray(dataset, dtype=np.float32)
    if values.shape != (frame_count, *expected_tail):
        raise ValueError(
            f"state/{key} has shape {values.shape}, expected "
            f"{(frame_count, *expected_tail)}"
        )
    return values


def _read_aligned_action(
    h5_file: h5py.File,
    key: str,
    frame_count: int,
    expected_tail: tuple[int, ...],
    required: bool,
) -> np.ndarray:
    dataset = h5_file.get(f"action/{key}")
    if dataset is None or dataset.size == 0:
        if required:
            raise ValueError(f"Missing required action/{key}")
        return np.zeros((frame_count, *expected_tail), dtype=np.float32)

    values = np.asarray(dataset, dtype=np.float32)
    if values.shape[1:] != expected_tail:
        raise ValueError(
            f"action/{key} has shape {values.shape}; expected tail {expected_tail}"
        )
    if len(values) == frame_count:
        return values
    if len(values) > frame_count:
        raise ValueError(
            f"action/{key} has {len(values)} rows, more than {frame_count} states"
        )

    state_values = _read_state(
        h5_file,
        key,
        frame_count,
        expected_tail,
        required=required,
    )
    group_name = key.split("/", maxsplit=1)[0]
    index_dataset = h5_file.get(f"action/{group_name}/index")
    indices = (
        np.asarray(index_dataset, dtype=np.int64)
        if index_dataset is not None
        else np.asarray([], dtype=np.int64)
    )
    if len(indices) == 0 and group_name == "end":
        fallback = h5_file.get("action/joint/index")
        indices = (
            np.asarray(fallback, dtype=np.int64)
            if fallback is not None
            else np.asarray([], dtype=np.int64)
        )
    if len(indices) != len(values):
        raise ValueError(
            f"action/{key} has {len(values)} rows but its control index has "
            f"{len(indices)} rows"
        )
    if len(indices) and (indices.min() < 0 or indices.max() >= frame_count):
        raise ValueError(f"action/{key} contains out-of-range control indices")
    aligned = state_values.copy()
    aligned[indices] = values
    return aligned


def _is_malformed_empty_end_action(h5_file, frame_count):
    """Recognize only the confirmed invalid source placeholder, never real actions."""
    pos = h5_file.get('action/end/position')
    ori = h5_file.get('action/end/orientation')
    index = h5_file.get('action/end/index')
    if pos is None or ori is None or index is None or index.size != 0:
        return False
    if pos.ndim != 2 or ori.ndim != 2 or pos.shape[1:] != (3,) or ori.shape[1:] != (4,):
        return False
    if len(pos) != len(ori) or len(pos) <= frame_count:
        return False
    return bool(np.all(pos[:] == 0) and np.all(ori[:] == 0))


def load_unified_episode(
    h5_path: Path,
    effector_type: EffectorType,
) -> dict[str, np.ndarray]:
    effector_tail = (2 * effector_dimension(effector_type),)
    with h5py.File(h5_path, "r") as h5_file:
        frame_count = len(h5_file["timestamp"])
        state_joint = _read_state(
            h5_file, "joint/position", frame_count, (14,), required=True
        )
        state_effector = _read_state(
            h5_file,
            "effector/position",
            frame_count,
            effector_tail,
            required=True,
        )
        action_joint = _read_aligned_action(
            h5_file, "joint/position", frame_count, (14,), required=True
        )
        action_effector = _read_aligned_action(
            h5_file,
            "effector/position",
            frame_count,
            effector_tail,
            required=True,
        )

        state_waist = _read_state(
            h5_file, "waist/position", frame_count, (2,), required=True
        )
        action_waist = _read_aligned_action(
            h5_file, "waist/position", frame_count, (2,), required=True
        )
        _require_finite(state_waist, "state.waist")
        _require_finite(action_waist, "action.waist")

        state_pose_available = _has_nonempty_dataset(
            h5_file, "state/end/position"
        ) and _has_nonempty_dataset(h5_file, "state/end/orientation")
        action_pose_available = _has_nonempty_dataset(
            h5_file, "action/end/position"
        ) and _has_nonempty_dataset(h5_file, "action/end/orientation")

        state_position = _read_state(
            h5_file, "end/position", frame_count, (2, 3), required=False
        )
        state_orientation = _read_state(
            h5_file, "end/orientation", frame_count, (2, 4), required=False
        )
        if _is_malformed_empty_end_action(h5_file, frame_count):
            action_pose_available = False
            action_position = np.zeros((frame_count, 2, 3), dtype=np.float32)
            action_orientation = np.zeros((frame_count, 2, 4), dtype=np.float32)
            import os, json
            audit_dir = os.environ.get('AGIBOT_EMPTY_ACTION_AUDIT_DIR')
            if audit_dir:
                dest = Path(audit_dir)
                dest.mkdir(parents=True, exist_ok=True)
                record = {'source': str(h5_path), 'frames': frame_count,
                          'reason': 'malformed all-zero end action with empty index',
                          'position_shape': list(h5_file['action/end/position'].shape),
                          'orientation_shape': list(h5_file['action/end/orientation'].shape),
                          'action_ee_valid': [0, 0], 'episode_retained': True}
                target = dest / (h5_path.parent.parent.name + '_' + h5_path.parent.name + '.json')
                tmp = target.with_suffix('.tmp')
                tmp.write_text(json.dumps(record, indent=2))
                tmp.replace(target)
        else:
            action_position = _read_aligned_action(
                h5_file, "end/position", frame_count, (2, 3), required=False
            )
            action_orientation = _read_aligned_action(
                h5_file, "end/orientation", frame_count, (2, 4), required=False
            )

    state_ee, state_ee_valid = compose_ee(state_position, state_orientation)
    action_ee, action_ee_valid = compose_ee(action_position, action_orientation)
    if not state_pose_available:
        state_ee.fill(0)
        state_ee_valid.fill(0)
    if not action_pose_available:
        action_ee.fill(0)
        action_ee_valid.fill(0)
    action_qpos, action_qpos_valid = sanitize_bimanual_qpos_action(
        compose_qpos(
            action_joint,
            action_effector,
            effector_type,
            require_finite=False,
        ),
        effector_type,
    )
    return {
        "state.waist": state_waist,
        "action.waist": action_waist,
        "state.qpos": compose_qpos(state_joint, state_effector, effector_type),
        "state.ee": state_ee,
        "state.ee_valid": state_ee_valid,
        "action.qpos": action_qpos,
        "action.qpos_valid": action_qpos_valid,
        "action.ee": action_ee,
        "action.ee_valid": action_ee_valid,
    }
