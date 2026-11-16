import sys
from pathlib import Path

import numpy as np
from lerobot.datasets.compute_stats import (
    DEFAULT_QUANTILES,
    auto_downsample_height_width,
    get_feature_stats,
    sample_indices,
)
from lerobot.datasets.io_utils import load_image_as_numpy

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from generic_converter import annotate_features  # noqa: E402


POSE_NAME_MARKERS = {"x", "y", "z", "rx", "ry", "rz", "rw", "r", "p", "roll", "pitch", "yaw"}

ACTION_DESCRIPTIONS = {
    "ee": (
        "Commanded source-native end-effector pose target. Component order, side, and "
        "rotation representation are declared by names.motors."
    ),
    "qpos": (
        "Commanded source-native joint-position target. Component and gripper order are "
        "declared by names.motors."
    ),
    "joint_effort": "Commanded source-native joint-effort target ordered by names.motors.",
    "joint_velocity": "Commanded source-native joint-velocity target ordered by names.motors.",
    "end_effector": (
        "Commanded source-native end-effector actuator target ordered by names.motors; "
        "this field is not a Cartesian pose."
    ),
}


def _motor_names(feature: dict) -> list[str]:
    names = feature.get("names", {}).get("motors", [])
    return list(names) if isinstance(names, list) else []


def _feature_with_motor_names(feature: dict, names: list[str]) -> dict:
    output = dict(feature)
    output["names"] = dict(output.get("names", {}))
    output["names"]["motors"] = names
    return output


def _combine_features(left_feature: dict, right_feature: dict, prefix: str, base_key: str) -> dict:
    left_shape = tuple(left_feature["shape"])
    right_shape = tuple(right_feature["shape"])
    if len(left_shape) != 1 or len(right_shape) != 1:
        raise ValueError(f"{base_key} features must be 1-D, got {left_shape} and {right_shape}")

    left_names = _motor_names(left_feature) or [f"motor_{index}" for index in range(left_shape[0])]
    right_names = _motor_names(right_feature) or [f"motor_{index}" for index in range(right_shape[0])]
    return {
        "dtype": left_feature["dtype"],
        "shape": (left_shape[0] + right_shape[0],),
        "names": {
            "motors": [
                *[f"{prefix}/{base_key}.left.{name}" for name in left_names],
                *[f"{prefix}/{base_key}.right.{name}" for name in right_names],
            ]
        },
    }


def _looks_like_pose_feature(raw_key: str, feature: dict) -> bool:
    if not raw_key.startswith("end_effector"):
        return False
    names = {name.lower() for name in _motor_names(feature)}
    if any("finger" in name or "thumb" in name for name in names):
        return False
    return bool(names & POSE_NAME_MARKERS) or any("xyz" in name.lower() for name in names)


def _canonical_base_key(raw_key: str, feature: dict) -> str:
    if raw_key == "joint_position":
        return "qpos"
    if raw_key in {"joint_position_left", "joint_position_right"}:
        return "qpos"
    if _looks_like_pose_feature(raw_key, feature):
        return "ee"
    if raw_key.endswith("_left") or raw_key.endswith("_right"):
        return raw_key.rsplit("_", 1)[0]
    return raw_key


def _canonical_feature_key(prefix: str, raw_key: str, feature: dict) -> str:
    return f"{prefix}.{_canonical_base_key(raw_key, feature)}"


def _copy_single_feature(prefix: str, raw_key: str, feature: dict) -> dict:
    names = _motor_names(feature)
    if not names:
        return dict(feature)
    base_key = _canonical_base_key(raw_key, feature)
    return _feature_with_motor_names(feature, [f"{prefix}/{base_key}.{name}" for name in names])


def _numeric_output_specs(config: dict, section: str, prefix: str) -> list[tuple[str, tuple[str, ...]]]:
    specs: list[tuple[str, tuple[str, ...]]] = []
    used: set[str] = set()
    section_config = config[section]

    for raw_key, feature in section_config.items():
        if raw_key in used:
            continue
        if raw_key.endswith("_left"):
            base = raw_key[:-5]
            right_key = f"{base}_right"
            if right_key in section_config:
                used.update({raw_key, right_key})
                output_base = _canonical_base_key(raw_key, feature)
                specs.append((f"{prefix}.{output_base}", (raw_key, right_key)))
                continue
        if raw_key.endswith("_right") and f"{raw_key[:-6]}_left" in section_config:
            continue
        used.add(raw_key)
        specs.append((_canonical_feature_key(prefix, raw_key, feature), (raw_key,)))
    return specs


def _action_validity_feature(output_key: str, input_keys: tuple[str, ...]) -> dict:
    base_key = output_key.removeprefix("action.")
    sides = ["left", "right"] if len(input_keys) == 2 else ["signal"]
    return {
        "dtype": "float32",
        "shape": (len(sides),),
        "names": {
            "motors": [f"action/{base_key}_valid.{side}" for side in sides]
        },
        "description": (
            f"Per-frame validity mask for {output_key}, ordered {sides}. 1 means the "
            "corresponding source action group is present and finite; Cartesian quaternion "
            "groups must also have non-zero norm. Invalid groups are stored as finite zero "
            "placeholders with mask value 0."
        ),
    }


def _sanitize_action_group(
    values: np.ndarray,
    output_key: str,
    feature: dict,
) -> tuple[np.ndarray, np.ndarray]:
    sanitized = np.asarray(values, dtype=np.float32).copy()
    if sanitized.ndim < 2:
        raise ValueError(f"{output_key} source action must have a frame dimension")
    valid = np.isfinite(sanitized.reshape(len(sanitized), -1)).all(axis=1)

    names = [name.lower() for name in _motor_names(feature)]
    if output_key == "action.ee" and sanitized.shape[-1] == 7 and any(
        name in {"rw", "qw", "w"} for name in names
    ):
        quaternion_norm = np.linalg.norm(sanitized[..., 3:7], axis=-1)
        valid &= np.isfinite(quaternion_norm) & (quaternion_norm > 1e-8)

    sanitized[~valid] = 0.0
    return sanitized, valid.astype(np.float32)


def remap_numeric_arrays(
    arrays: dict[str, np.ndarray],
    config: dict,
    section: str,
    prefix: str,
    include_action_validity: bool = False,
) -> dict[str, np.ndarray]:
    remapped = {}
    for output_key, input_keys in _numeric_output_specs(config, section, prefix):
        values = [np.asarray(arrays[key]) for key in input_keys]
        if include_action_validity:
            sanitized_and_valid = [
                _sanitize_action_group(values[index], output_key, config[section][key])
                for index, key in enumerate(input_keys)
            ]
            values = [item[0] for item in sanitized_and_valid]
            remapped[f"{output_key}_valid"] = np.stack(
                [item[1] for item in sanitized_and_valid], axis=1
            )
        remapped[output_key] = values[0] if len(values) == 1 else np.concatenate(values, axis=-1)
    return remapped


def generate_features_from_config(AgiBotWorld_CONFIG, embodiment: str):
    features = {}
    for key, value in AgiBotWorld_CONFIG["images"].items():
        features[f"observation.images.{key}"] = value
    for output_key, input_keys in _numeric_output_specs(AgiBotWorld_CONFIG, "states", "state"):
        if len(input_keys) == 1:
            raw_key = input_keys[0]
            features[output_key] = _copy_single_feature("state", raw_key, AgiBotWorld_CONFIG["states"][raw_key])
        else:
            left_key, right_key = input_keys
            base_key = output_key.removeprefix("state.")
            features[output_key] = _combine_features(
                AgiBotWorld_CONFIG["states"][left_key],
                AgiBotWorld_CONFIG["states"][right_key],
                "state",
                base_key,
            )
    for output_key, input_keys in _numeric_output_specs(AgiBotWorld_CONFIG, "actions", "action"):
        if len(input_keys) == 1:
            raw_key = input_keys[0]
            features[output_key] = _copy_single_feature("action", raw_key, AgiBotWorld_CONFIG["actions"][raw_key])
        else:
            left_key, right_key = input_keys
            base_key = output_key.removeprefix("action.")
            features[output_key] = _combine_features(
                AgiBotWorld_CONFIG["actions"][left_key],
                AgiBotWorld_CONFIG["actions"][right_key],
                "action",
                base_key,
            )
        base_key = output_key.removeprefix("action.")
        features[output_key].setdefault(
            "description",
            ACTION_DESCRIPTIONS.get(
                base_key,
                f"Commanded source-native {base_key} target ordered by names.motors.",
            ),
        )
        features[f"{output_key}_valid"] = _action_validity_feature(output_key, input_keys)

    origins = {}
    for key in AgiBotWorld_CONFIG["images"]:
        output_key = f"observation.images.{key}"
        if key.endswith("_depth"):
            origins[output_key] = f"HDF5 observations/depth_images/{key[:-6]}"
        else:
            origins[output_key] = f"HDF5 observations/rgb_images/{key}"
    for output_key, input_keys in _numeric_output_specs(
        AgiBotWorld_CONFIG, "states", "state"
    ):
        origins[output_key] = " + ".join(
            f"HDF5 puppet/{input_key}" for input_key in input_keys
        )
    for output_key, input_keys in _numeric_output_specs(
        AgiBotWorld_CONFIG, "actions", "action"
    ):
        raw_origin = " + ".join(
            f"HDF5 master/{input_key}" for input_key in input_keys
        )
        origins[output_key] = raw_origin
        origins[f"{output_key}_valid"] = f"derived from {raw_origin}"

    return annotate_features(
        features,
        embodiment=embodiment,
        origins=origins,
        default_description=lambda key: f"RoboMIND converted feature {key}.",
    )


def sample_images(input):
    if type(input) is list:
        image_paths = input

        sampled_indices = sample_indices(len(image_paths))
        images = None
        for i, idx in enumerate(sampled_indices):
            path = image_paths[idx]

            img = load_image_as_numpy(path, dtype=np.uint8, channel_first=True)
            img = auto_downsample_height_width(img)

            if images is None:
                images = np.empty((len(sampled_indices), *img.shape), dtype=np.uint8)

            images[i] = img
    elif type(input) is np.ndarray:
        frames_array = input[:, None, :, :]  # Shape: [T, 1, H, W]
        sampled_indices = sample_indices(len(frames_array))
        images = None
        for i, idx in enumerate(sampled_indices):
            img = frames_array[idx]
            img = auto_downsample_height_width(img)

            if images is None:
                images = np.empty((len(sampled_indices), *img.shape), dtype=np.uint8)

            images[i] = img

    return images


def compute_episode_stats(
    episode_data: dict[str, list[str] | np.ndarray],
    features: dict,
    quantile_list: list[float] | None = None,
) -> dict:
    if quantile_list is None:
        quantile_list = DEFAULT_QUANTILES

    ep_stats = {}
    for key, data in episode_data.items():
        if features[key]["dtype"] == "string":
            continue

        elif features[key]["dtype"] in ["image", "video"]:
            ep_ft_array = sample_images(data)
            axes_to_reduce = (0, 2, 3)
            keepdims = True
        else:
            ep_ft_array = data
            axes_to_reduce = 0
            keepdims = data.ndim == 1

        ep_stats[key] = get_feature_stats(
            ep_ft_array, axis=axes_to_reduce, keepdims=keepdims, quantile_list=quantile_list
        )

        if features[key]["dtype"] in ["image", "video"]:
            value_norm = 1.0 if "depth" in key else 255.0
            ep_stats[key] = {
                k: v if k == "count" else np.squeeze(v / value_norm, axis=0) for k, v in ep_stats[key].items()
            }

    return ep_stats
