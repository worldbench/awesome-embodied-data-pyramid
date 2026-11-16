"""Legacy schema helpers and Arrow readers. New flows use embodiment adapters.

Original contract shared by the three reviewed converters.

The supported converters are:

* ``agibotworld2026_2lerobot``
* ``agibotworld_beta_2lerobot``
* ``abc130k2lerobot``

They write the same six feature names.  This module deliberately has no
fallback aliases: a missing or renamed feature is a schema error that must be
fixed at the converter/config boundary instead of being guessed here.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa


STATE_QPOS = "state.qpos"
STATE_EE = "state.ee"
STATE_EE_VALID = "state.ee_valid"
ACTION_QPOS = "action.qpos"
ACTION_EE = "action.ee"
ACTION_EE_VALID = "action.ee_valid"

ROBOT_FEATURES = (
    STATE_QPOS,
    STATE_EE,
    STATE_EE_VALID,
    ACTION_QPOS,
    ACTION_EE,
    ACTION_EE_VALID,
)
SIDES = ("left", "right")
EE_SIDE_SLICES = {"left": slice(0, 7), "right": slice(7, 14)}
EE_QUATERNION_SLICES = {"left": slice(3, 7), "right": slice(10, 14)}


def read_info(repo: Path) -> dict[str, Any]:
    path = repo / "meta" / "info.json"
    if not path.is_file():
        raise FileNotFoundError(f"LeRobot metadata does not exist: {path}")
    return json.loads(path.read_text())


def feature_width(info: dict[str, Any], key: str) -> int:
    feature = info.get("features", {}).get(key)
    if not isinstance(feature, dict):
        raise ValueError(f"meta/info.json does not declare required feature {key!r}")
    shape = feature.get("shape")
    if not isinstance(shape, (list, tuple)) or len(shape) != 1:
        raise ValueError(f"feature {key!r} must have a one-dimensional shape, got {shape!r}")
    width = int(shape[0])
    if width <= 0:
        raise ValueError(f"feature {key!r} has invalid width {width}")
    return width


def motor_names(info: dict[str, Any], key: str) -> list[str]:
    feature = info["features"][key]
    names = feature.get("names")
    if isinstance(names, dict):
        names = names.get("motors")
    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        raise ValueError(f"feature {key!r} must declare names.motors")
    width = feature_width(info, key)
    if len(names) != width:
        raise ValueError(f"feature {key!r} declares {len(names)} names for width {width}")
    return names


def arm_joint_indices(info: dict[str, Any], key: str, side: str) -> list[int]:
    """Resolve arm joints from the converter-emitted motor names.

    All three reviewed converters name arm entries as
    ``<state|action>/joint/position.<left|right>_joint_N``.  Effector entries
    use ``*_effector/position`` and are therefore excluded without relying on
    a fixed vector offset (important for Beta's 1-D and 6-D effectors).
    """

    if side not in SIDES:
        raise ValueError(f"unknown side {side!r}")
    marker = f"/joint/position.{side}_joint_"
    indices = [index for index, name in enumerate(motor_names(info, key)) if marker in name]
    if not indices:
        raise ValueError(f"feature {key!r} contains no {side} arm joints with marker {marker!r}")
    return indices


def fixed_list_numpy(
    column: pa.ChunkedArray,
    width: int,
    dtype: np.dtype | type = np.float64,
) -> np.ndarray:
    array = column.combine_chunks()
    if pa.types.is_fixed_size_list(array.type):
        if array.type.list_size != width:
            raise ValueError(f"expected list width {width}, got {array.type.list_size}")
        values = (
            array.values.slice(array.offset * width, len(array) * width)
            .to_numpy(zero_copy_only=False)
            .reshape(len(array), width)
        )
    elif width == 1 and not (pa.types.is_list(array.type) or pa.types.is_large_list(array.type)):
        # LeRobot writes shape=[1] features as either scalar or list Arrow columns.
        values = array.to_numpy(zero_copy_only=False).reshape(-1, 1)
    else:
        values = np.asarray(array.to_pylist())
    if values.shape != (len(column), width):
        raise ValueError(f"expected ({len(column)}, {width}), got {values.shape}")
    return values.astype(dtype, copy=False)


@dataclass(frozen=True)
class LeRobotSchema:
    qpos_width: int

    @classmethod
    def from_info(cls, info: dict[str, Any], require_ee: bool = True) -> "LeRobotSchema":
        required = (STATE_QPOS, ACTION_QPOS)
        if require_ee:
            required += (STATE_EE, STATE_EE_VALID, ACTION_EE, ACTION_EE_VALID)
        for key in required:
            feature_width(info, key)
        qpos_width = feature_width(info, STATE_QPOS)
        if feature_width(info, ACTION_QPOS) != qpos_width:
            raise ValueError("state.qpos and action.qpos widths differ")
        if require_ee:
            for key in (STATE_EE, ACTION_EE):
                if feature_width(info, key) != 14:
                    raise ValueError(f"{key} must be [left 7 + right 7], width 14")
            for key in (STATE_EE_VALID, ACTION_EE_VALID):
                if feature_width(info, key) != 2:
                    raise ValueError(f"{key} must be [left, right], width 2")
        return cls(qpos_width=qpos_width)

    def validate_config_width(self, expected: int | list[int] | None) -> None:
        if expected is None:
            return
        allowed = [int(expected)] if isinstance(expected, int) else [int(v) for v in expected]
        if self.qpos_width not in allowed:
            raise ValueError(
                f"dataset qpos width is {self.qpos_width}, config allows {sorted(set(allowed))}"
            )
