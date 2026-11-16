import os
import numpy as np
from generic_converter import annotate_feature
from lerobot.datasets.compute_stats import (
    DEFAULT_QUANTILES,
    auto_downsample_height_width,
    get_feature_stats,
    sample_indices,
)
from torchcodec.decoders import VideoDecoder


ACTION_DESCRIPTIONS = {
    "effector.position": "Commanded source-native left/right end-effector actuator positions.",
    "end.orientation": "Commanded source-native left/right end-effector orientations.",
    "end.position": "Commanded source-native left/right end-effector Cartesian positions.",
    "head.position": "Commanded source-native head yaw and pitch positions.",
    "joint.position": "Commanded source-native absolute left/right arm joint positions.",
    "robot.velocity": "Commanded source-native planar base linear and yaw velocities.",
    "waist.position": "Commanded source-native waist pitch and lift positions.",
}


def _action_description(key: str) -> str:
    return ACTION_DESCRIPTIONS.get(
        key,
        f"Commanded source-native action signal from action/{key.replace('.', '/')}.",
    )


def generate_features_from_config(AgiBotWorld_CONFIG, embodiment: str):
    features = {}
    for key, value in AgiBotWorld_CONFIG["images"].items():
        feature_key = f"observation.images.{key}"
        origin = (
            f"observations/{{task_id}}/{{episode_id}}/depth/{key}*"
            if "depth" in key
            else f"observations/{{task_id}}/{{episode_id}}/videos/{key}_color.mp4"
        )
        features[feature_key] = annotate_feature(
            value,
            embodiment=embodiment,
            origin_data=origin,
            default_description=f"AgiBot observation image stream {key}.",
        )
    for key, value in AgiBotWorld_CONFIG["states"].items():
        feature_key = f"observation.states.{key}"
        features[feature_key] = annotate_feature(
            value,
            embodiment=embodiment,
            origin_data=f"proprio_stats.h5::state/{key.replace('.', '/')}",
            default_description=f"Observed source-native robot state {key}.",
        )
    for key, value in AgiBotWorld_CONFIG["actions"].items():
        action_key = f"actions.{key}"
        action_feature = dict(value)
        action_feature.setdefault("description", _action_description(key))
        action_origin = f"proprio_stats.h5::action/{key.replace('.', '/')}"
        features[action_key] = annotate_feature(
            action_feature,
            embodiment=embodiment,
            origin_data=action_origin,
            default_description=_action_description(key),
        )
        validity_feature = {
            "dtype": "float32",
            "shape": (1,),
            "names": {"motors": [f"action/{key.replace('.', '/')}_valid"]},
            "description": (
                f"Per-frame validity mask for {action_key}. 1 means the source action "
                "signal is present and finite after alignment. 0 means the action value "
                "is a finite zero placeholder and must be excluded from losses and statistics."
            ),
        }
        features[f"{action_key}_valid"] = annotate_feature(
            validity_feature,
            embodiment=embodiment,
            origin_data=f"derived from {action_origin}",
            default_description=f"Validity mask for {action_key}.",
        )
    return features


def sample_images(input):
    if type(input) is str:
        video_path = input
        decoder = VideoDecoder(
            video_path, num_ffmpeg_threads=int(os.environ.get("AGIBOT_VIDEO_DECODE_THREADS", "1"))
        )
        # Preserve the existing [0:-1] sampling timeline exactly, while decoding
        # only requested frames instead of materializing the full RGB video.
        sampled_indices = sample_indices(len(decoder) - 1)
        frames_array = decoder.get_frames_at(sampled_indices).data.numpy()
        images = None
        for i in range(len(sampled_indices)):
            img = frames_array[i]
            img = auto_downsample_height_width(img)

            if images is None:
                images = np.empty((len(sampled_indices), *img.shape), dtype=np.uint8)

            images[i] = img
    elif type(input) is np.ndarray:
        frames_array = input[:, None, :, :]  # Shape: [T, C, H, W]
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
