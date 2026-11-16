#!/usr/bin/env python3
"""Convert raw ABC-130k MCAP episodes to LeRobot v3.0.

The source tree is read-only. Robot and camera streams are aligned causally on a
fixed 30 Hz clock. The ABC YAM embodiment has two 6-DoF arms, therefore qpos is
14-D: left arm 6 + left gripper 1 + right arm 6 + right gripper 1.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Literal, cast

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Some LeRobot v3 checkouts do not re-export LeRobotDataset from the package.
# Populate the compatibility alias before generic_converter imports pipeline.py.
try:
    import lerobot.datasets as _lerobot_datasets

    if not hasattr(_lerobot_datasets, "LeRobotDataset"):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset as _LeRobotDataset

        _lerobot_datasets.LeRobotDataset = _LeRobotDataset
except ImportError:
    pass

from generic_converter import (  # noqa: E402
    BaseAdapter,
    ConversionTask,
    annotate_features,
    run_converter,
    validate_feature_descriptions,
)


FPS = 30
TICK_NS = int(1e9 / FPS)

# Full read-only audit of the ABC-130k source release on 2026-08-26.
# RobotState.pose is either a row-major 4x4 matrix (16 values) or an empty array.
EE_TOTAL_EPISODES = 130_919
EE_PRESENT_EPISODES = 69_720
EE_MISSING_EPISODES = 61_199
EE_PRESENT_PERCENT = 100.0 * EE_PRESENT_EPISODES / EE_TOTAL_EPISODES
EE_FILL_VALUE = 0.0
EE_VECTOR_SIZE = 7
MATRIX_POSE_SIZE = 16
MIN_EPISODE_FRAMES = 10

MissingEEPolicy = Literal["fill", "skip", "error"]

LEFT_ARM_STATE = "/left-arm-state"
RIGHT_ARM_STATE = "/right-arm-state"
LEFT_GRIPPER_STATE = "/left-ee-state"
RIGHT_GRIPPER_STATE = "/right-ee-state"
LEFT_ARM_ACTION = "/left-arm-action"
RIGHT_ARM_ACTION = "/right-arm-action"
LEFT_GRIPPER_ACTION = "/left-ee-action"
RIGHT_GRIPPER_ACTION = "/right-ee-action"

ARM_TOPICS = (
    LEFT_ARM_STATE,
    RIGHT_ARM_STATE,
    LEFT_ARM_ACTION,
    RIGHT_ARM_ACTION,
)
GRIPPER_TOPICS = (
    LEFT_GRIPPER_STATE,
    RIGHT_GRIPPER_STATE,
    LEFT_GRIPPER_ACTION,
    RIGHT_GRIPPER_ACTION,
)
SCALAR_TOPICS = ARM_TOPICS + GRIPPER_TOPICS
CAMERA_CANDIDATES = (
    "/top-camera",
    "/top-left-camera",
    "/top-right-camera",
    "/left-wrist-camera",
    "/right-wrist-camera",
)


QPOS_NAMES = [
    *[f"state/joint/position.left_joint_{i}" for i in range(6)],
    "state/left_effector/position",
    *[f"state/joint/position.right_joint_{i}" for i in range(6)],
    "state/right_effector/position",
]
ACTION_QPOS_NAMES = [name.replace("state/", "action/", 1) for name in QPOS_NAMES]
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


def build_features(
    height: int,
    width: int,
    qpos_only: bool,
) -> dict[str, dict[str, Any]]:
    """Build the fixed LeRobot schema embedded in ``meta/info.json``."""
    features: dict[str, dict[str, Any]] = {
        "observation.images.top": {
            "dtype": "video",
            "shape": (height, width, 3),
            "names": ["height", "width", "rgb"],
            "description": (
                "Fixed workspace camera. RealSense episodes use /top-camera; "
                "ZED-X episodes deterministically select one stereo eye. RGB uint8."
            ),
        },
        "observation.images.left_wrist": {
            "dtype": "video",
            "shape": (height, width, 3),
            "names": ["height", "width", "rgb"],
            "description": (
                "RGB image from the camera mounted on the robot's physical left arm wrist."
            ),
        },
        "observation.images.right_wrist": {
            "dtype": "video",
            "shape": (height, width, 3),
            "names": ["height", "width", "rgb"],
            "description": (
                "RGB image from the camera mounted on the robot's physical right arm wrist."
            ),
        },
        "state.qpos": {
            "dtype": "float32",
            "shape": (14,),
            "names": {"motors": QPOS_NAMES},
            "description": (
                "Observed absolute robot configuration: left YAM joints 1-6 [rad], left gripper "
                "aperture [0=closed, 1=open], right YAM joints 1-6 [rad], right gripper aperture "
                "[0=closed, 1=open]. This is 14-D because each YAM arm has 6, not 7, arm joints."
            ),
        },
        "action.qpos": {
            "dtype": "float32",
            "shape": (14,),
            "names": {"motors": ACTION_QPOS_NAMES},
            "description": (
                "Commanded absolute joint-position target at this timestamp: left 6 joint targets "
                "[rad] + left gripper target [0=closed, 1=open] + right 6 joint targets [rad] + "
                "right gripper target. It is an absolute position command, not a delta action."
            ),
        },
        "action.qpos_valid": {
            "dtype": "float32",
            "shape": (2,),
            "names": {"motors": ACTION_QPOS_VALID_NAMES},
            "description": (
                "Per-side validity mask [left,right] for action.qpos. 1 means all six arm "
                "targets and the gripper target are finite after causal alignment. 0 means "
                "that side is stored as seven finite zero placeholders and must be excluded "
                "from action losses and statistics."
            ),
        },
    }
    if not qpos_only:
        features.update(
            {
                "state.ee": {
                    "dtype": "float32",
                    "shape": (14,),
                    "names": {"motors": STATE_EE_NAMES},
                    "description": (
                        "Observed absolute end-effector poses from RobotState.pose: "
                        "left then right, "
                        "each [x,y,z,qx,qy,qz,qw]. Translation is metres, quaternion is xyzw, "
                        "frame is the right-handed Z-up YAM station world frame. In the audited "
                        "local release, raw EE is present in "
                        f"{EE_PRESENT_EPISODES}/{EE_TOTAL_EPISODES} episodes "
                        f"({EE_PRESENT_PERCENT:.4f}%). A missing side is filled with "
                        "seven "
                        "finite zeros; state.ee_valid must be used to distinguish placeholders."
                    ),
                },
                "state.ee_valid": {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {"motors": STATE_EE_VALID_NAMES},
                    "description": (
                        "Per-side validity mask [left,right] for state.ee. 1 means the raw state "
                        "RobotState.pose is a valid 16-value homogeneous matrix and "
                        "the corresponding "
                        "7-D state.ee is physical. 0 means that 7-D slot is a zero placeholder and "
                        "must be excluded from EE losses and EE statistics."
                    ),
                },
                "action.ee": {
                    "dtype": "float32",
                    "shape": (14,),
                    "names": {"motors": ACTION_EE_NAMES},
                    "description": (
                        "Commanded absolute end-effector pose target from action RobotState.pose: "
                        "left then right, each [x,y,z,qx,qy,qz,qw], metres and xyzw quaternion in "
                        "the YAM station world frame. It is an absolute pose target, not a delta. "
                        f"Raw EE is present in {EE_PRESENT_EPISODES}/{EE_TOTAL_EPISODES} episodes "
                        f"({EE_PRESENT_PERCENT:.4f}%); missing sides are seven finite "
                        "zeros and must "
                        "be masked with action.ee_valid."
                    ),
                },
                "action.ee_valid": {
                    "dtype": "float32",
                    "shape": (2,),
                    "names": {"motors": ACTION_EE_VALID_NAMES},
                    "description": (
                        "Per-side validity mask [left,right] for action.ee. 1 means the raw action "
                        "RobotState.pose is a valid 16-value homogeneous matrix and action.ee is a "
                        "physical target. 0 means that 7-D slot is a zero placeholder and must be "
                        "excluded from EE losses and EE statistics."
                    ),
                },
            }
        )
    origins = {
        "observation.images.top": (
            "MCAP topic /top-camera or selected /top-left-camera or /top-right-camera"
        ),
        "observation.images.left_wrist": "MCAP topic /left-wrist-camera",
        "observation.images.right_wrist": "MCAP topic /right-wrist-camera",
        "state.qpos": (
            "MCAP /left-arm-state.position + /left-ee-state.position + "
            "/right-arm-state.position + /right-ee-state.position"
        ),
        "action.qpos": (
            "MCAP /left-arm-action.position + /left-ee-action.position + "
            "/right-arm-action.position + /right-ee-action.position"
        ),
        "action.qpos_valid": (
            "derived from MCAP /left-arm-action.position + /left-ee-action.position + "
            "/right-arm-action.position + /right-ee-action.position"
        ),
        "state.ee": "MCAP /left-arm-state.pose + /right-arm-state.pose",
        "state.ee_valid": "derived from MCAP /left-arm-state.pose + /right-arm-state.pose",
        "action.ee": "MCAP /left-arm-action.pose + /right-arm-action.pose",
        "action.ee_valid": "derived from MCAP /left-arm-action.pose + /right-arm-action.pose",
    }
    return annotate_features(
        features,
        embodiment="YAM dual-arm",
        origins=origins,
    )


def floor_indices(source_ns: np.ndarray, target_ns: np.ndarray) -> np.ndarray:
    """Latest source sample at or before every target timestamp (causal hold)."""
    return np.clip(
        np.searchsorted(source_ns, target_ns, side="right") - 1,
        0,
        len(source_ns) - 1,
    )


def sanitize_bimanual_qpos_action(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Replace invalid left/right qpos targets with zeros and return a side mask."""
    action = np.asarray(values, dtype=np.float32).copy()
    if action.ndim != 2 or action.shape[1] != 14:
        raise ValueError(f"action.qpos must have shape (N,14), got {action.shape}")

    valid = np.zeros((len(action), 2), dtype=np.float32)
    for side, start in enumerate((0, 7)):
        side_values = action[:, start : start + 7]
        side_valid = np.isfinite(side_values).all(axis=1)
        side_values[~side_valid] = 0.0
        valid[:, side] = side_valid.astype(np.float32)
    return action, valid


def _rotation_matrix_to_xyzw(rotation: np.ndarray) -> np.ndarray:
    """Convert a 3x3 rotation matrix to a normalized xyzw quaternion."""
    trace = float(np.trace(rotation))
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        qw = 0.25 * s
        qx = (rotation[2, 1] - rotation[1, 2]) / s
        qy = (rotation[0, 2] - rotation[2, 0]) / s
        qz = (rotation[1, 0] - rotation[0, 1]) / s
    else:
        axis = int(np.argmax(np.diag(rotation)))
        if axis == 0:
            s = math.sqrt(1.0 + rotation[0, 0] - rotation[1, 1] - rotation[2, 2]) * 2.0
            qw = (rotation[2, 1] - rotation[1, 2]) / s
            qx = 0.25 * s
            qy = (rotation[0, 1] + rotation[1, 0]) / s
            qz = (rotation[0, 2] + rotation[2, 0]) / s
        elif axis == 1:
            s = math.sqrt(1.0 + rotation[1, 1] - rotation[0, 0] - rotation[2, 2]) * 2.0
            qw = (rotation[0, 2] - rotation[2, 0]) / s
            qx = (rotation[0, 1] + rotation[1, 0]) / s
            qy = 0.25 * s
            qz = (rotation[1, 2] + rotation[2, 1]) / s
        else:
            s = math.sqrt(1.0 + rotation[2, 2] - rotation[0, 0] - rotation[1, 1]) * 2.0
            qw = (rotation[1, 0] - rotation[0, 1]) / s
            qx = (rotation[0, 2] + rotation[2, 0]) / s
            qy = (rotation[1, 2] + rotation[2, 1]) / s
            qz = 0.25 * s

    quaternion = np.asarray([qx, qy, qz, qw], dtype=np.float64)
    norm = float(np.linalg.norm(quaternion))
    if not np.isfinite(norm) or norm < 1e-12:
        raise ValueError("EE pose produced an invalid quaternion")
    return quaternion / norm


def matrix_to_pose7(flat_matrix: np.ndarray) -> np.ndarray:
    """Convert a row-major homogeneous 4x4 matrix to xyz + xyzw."""
    values = np.asarray(flat_matrix, dtype=np.float64)
    if values.shape != (MATRIX_POSE_SIZE,):
        raise ValueError(
            f"EE pose has shape {values.shape}, expected ({MATRIX_POSE_SIZE},)"
        )
    if not np.isfinite(values).all():
        raise ValueError("non-finite EE pose")

    matrix = values.reshape(4, 4)
    if not np.allclose(matrix[3], [0.0, 0.0, 0.0, 1.0], atol=1e-3):
        raise ValueError("EE pose is not a homogeneous 4x4 matrix")

    rotation = matrix[:3, :3]
    if not np.allclose(rotation.T @ rotation, np.eye(3), atol=2e-2):
        raise ValueError("EE pose rotation is not orthonormal")
    if not np.isclose(np.linalg.det(rotation), 1.0, atol=2e-2):
        raise ValueError("EE pose rotation determinant is not +1")

    quaternion = _rotation_matrix_to_xyzw(rotation)
    return np.concatenate([matrix[:3, 3], quaternion]).astype(np.float32)


def convert_pose_stream(
    stream: "ScalarStream",
    aligned_indices: np.ndarray,
    frame_count: int,
    topic: str,
    missing_policy: MissingEEPolicy,
) -> tuple[np.ndarray, np.ndarray]:
    """Align one raw pose stream and return pose7 values plus a frame mask."""
    if len(stream.poses) != len(stream.timestamps):
        raise ValueError(
            f"{topic}.pose count {len(stream.poses)} does not match timestamp count "
            f"{len(stream.timestamps)}"
        )

    pose_shapes = {pose.shape for pose in stream.poses}
    if pose_shapes == {(MATRIX_POSE_SIZE,)}:
        aligned_poses = (stream.poses[index] for index in aligned_indices)
        pose_values = np.stack([matrix_to_pose7(pose) for pose in aligned_poses])
        valid = np.ones(frame_count, dtype=np.float32)
        return pose_values.astype(np.float32), valid

    if pose_shapes == {(0,)}:
        if missing_policy != "fill":
            raise ValueError(
                f"{topic}.pose is empty (missing EE policy: {missing_policy})"
            )
        pose_values = np.full(
            (frame_count, EE_VECTOR_SIZE),
            EE_FILL_VALUE,
            dtype=np.float32,
        )
        valid = np.zeros(frame_count, dtype=np.float32)
        return pose_values, valid

    shape_names = sorted(str(shape) for shape in pose_shapes)
    raise ValueError(f"{topic}.pose has mixed or invalid shapes: {shape_names}")


def _run_probe(path: Path, input_format: str) -> int | None:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-f",
            input_format,
            "-count_frames",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=nb_read_frames",
            "-of",
            "csv=p=0",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip()
    return int(value) if value.isdigit() else None


def _read_exact(stream: Any, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            break
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class AlignedVideoDecoder:
    def __init__(self, path: Path, codec: str, width: int, height: int):
        input_format = "hevc" if codec in {"h265", "hevc"} else "h264"
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease:flags=bicubic,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        )
        self.process = subprocess.Popen(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                input_format,
                "-i",
                str(path),
                "-vf",
                vf,
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.width = width
        self.height = height
        self.index = -1
        self.frame: np.ndarray | None = None

    def get(self, wanted_index: int) -> np.ndarray:
        if wanted_index < self.index:
            raise ValueError("camera indices must be monotonic")
        frame_size = self.width * self.height * 3
        while self.index < wanted_index:
            assert self.process.stdout is not None
            raw = _read_exact(self.process.stdout, frame_size)
            if len(raw) != frame_size:
                stderr = b""
                if self.process.stderr is not None:
                    stderr = self.process.stderr.read()
                raise RuntimeError(
                    f"ffmpeg ended at frame {self.index}; wanted {wanted_index}: "
                    f"{stderr.decode(errors='replace')[-500:]}"
                )
            self.index += 1
            self.frame = (
                np.frombuffer(raw, dtype=np.uint8)
                .reshape(self.height, self.width, 3)
                .copy()
            )
        if self.frame is None:
            raise RuntimeError("video decoder produced no frame")
        return self.frame

    def close(self) -> None:
        if self.process.stdout is not None:
            self.process.stdout.close()
        if self.process.poll() is not None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=10)


@dataclass
class ScalarStream:
    timestamps: np.ndarray
    positions: np.ndarray
    poses: list[np.ndarray]


@dataclass
class CameraStream:
    timestamps: np.ndarray
    path: Path
    codec: str


@dataclass
class PreparedEpisode:
    source: Path
    instruction: str
    ticks: np.ndarray
    arrays: dict[str, np.ndarray]
    camera_indices: dict[str, np.ndarray]
    cameras: dict[str, CameraStream]
    width: int
    height: int
    temp_dir: Path

    def __len__(self) -> int:
        return len(self.ticks)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        decoders = {
            key: AlignedVideoDecoder(stream.path, stream.codec, self.width, self.height)
            for key, stream in self.cameras.items()
        }
        try:
            for index in range(len(self)):
                frame: dict[str, Any] = {
                    key: values[index] for key, values in self.arrays.items()
                }
                for key, decoder in decoders.items():
                    frame[f"observation.images.{key}"] = decoder.get(
                        int(self.camera_indices[key][index])
                    )
                frame["task"] = self.instruction
                yield frame
        finally:
            for decoder in decoders.values():
                decoder.close()

    def cleanup(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)


class ABC130KAdapter(BaseAdapter):
    dataset_type = "abc130k"
    fps = FPS
    robot_type = "yam_bimanual_2x6dof"
    tags = ["abc130k", "yam", "bimanual", "real-world", "mcap"]

    def __init__(
        self,
        src_root: Path,
        output_path: Path,
        split: str,
        episodes_per_task: int,
        max_episodes: int | None,
        episode_list: Path | None,
        work_dir: Path,
        width: int,
        height: int,
        max_gap_ms: float,
        qpos_only: bool,
        missing_ee_policy: MissingEEPolicy,
        image_writer_threads: int,
        verify_video_frame_count: bool,
    ):
        super().__init__(output_path)
        self.src_root = src_root.expanduser().resolve()
        self.split = split
        self.episodes_per_task = episodes_per_task
        self.max_episodes = max_episodes
        self.episode_list = episode_list.expanduser().resolve() if episode_list else None
        self.work_dir = work_dir.expanduser().resolve()
        self.width = width
        self.height = height
        self.max_gap_ns = int(max_gap_ms * 1e6)
        self.qpos_only = qpos_only
        self.missing_ee_policy = missing_ee_policy
        self.image_writer_threads = image_writer_threads
        self.verify_video_frame_count = verify_video_frame_count
        self.features = build_features(height, width, qpos_only)
        self.report_dir = self.output_path.with_name(f"{self.output_path.name}_reports")

    def create_dataset(self, task: ConversionTask):
        from lerobot.datasets import LeRobotDataset

        validate_feature_descriptions(self.features)
        return LeRobotDataset.create(
            repo_id=task.local_repo_id,
            root=task.output_path,
            fps=self.fps,
            robot_type=self.robot_type,
            features=self.features,
            image_writer_threads=self.image_writer_threads,
        )

    def load_tasks(self) -> list[ConversionTask]:
        split_root = self.src_root / "data" / self.split
        if self.episode_list is None:
            paths = sorted(split_root.glob("*/episode_*/episode.mcap"))
        else:
            paths = []
            for line in self.episode_list.read_text(encoding="utf-8").splitlines():
                value = line.strip()
                if not value or value.startswith("#"):
                    continue
                path = Path(value).expanduser().resolve()
                try:
                    path.relative_to((self.src_root / "data").resolve())
                except ValueError as exc:
                    raise ValueError(
                        f"Episode from --episode-list is outside dataset data root: {path}"
                    ) from exc
                try:
                    path.relative_to(split_root.resolve())
                except ValueError:
                    # A shared audit manifest may contain both train and val.
                    # Keep only paths belonging to the requested --split.
                    continue
                if path.name != "episode.mcap" or not path.is_file():
                    raise FileNotFoundError(f"Invalid episode path in --episode-list: {path}")
                paths.append(path)
            paths = sorted(set(paths))
        if self.max_episodes is not None:
            paths = paths[: self.max_episodes]
        if not paths:
            raise FileNotFoundError(f"No episode.mcap found below {split_root}")

        tasks: list[ConversionTask] = []
        for chunk_index, start in enumerate(range(0, len(paths), self.episodes_per_task)):
            chunk = paths[start : start + self.episodes_per_task]
            chunk_name = f"{self.split}-chunk-{chunk_index:06d}"
            tasks.append(
                ConversionTask(
                    input_path=chunk[0].parent.parent,
                    output_path=self.temp_output_path / self.split / chunk_name,
                    local_repo_id=f"abc130k/{chunk_name}",
                    metadata={"episodes": [str(path) for path in chunk], "chunk": chunk_name},
                )
            )
        return tasks

    def load_subset(self, task: ConversionTask) -> Iterable[PreparedEpisode]:
        self.work_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)
        for raw_path in task.metadata["episodes"]:
            source = Path(raw_path)
            try:
                yield self._prepare_episode(source)
            except Exception as exc:
                self._write_report(task, source, "skipped", str(exc))
                if self.missing_ee_policy == "error" and "pose" in str(exc).lower():
                    raise
                print(f"[SKIP] {source}: {exc}", flush=True)

    def save_episode(
        self,
        dataset: Any,
        episode_data: PreparedEpisode,
        task: ConversionTask,
    ) -> bool:
        try:
            for frame in episode_data:
                dataset.add_frame(frame)
            dataset.save_episode()
            self._write_report(task, episode_data.source, "saved", "", len(episode_data))
            return True
        except Exception as exc:
            self._write_report(task, episode_data.source, "failed", str(exc), len(episode_data))
            raise
        finally:
            episode_data.cleanup()

    def get_episode_length(self, episode_data: PreparedEpisode) -> int:
        return len(episode_data)

    def _write_report(
        self,
        task: ConversionTask,
        source: Path,
        status: str,
        reason: str,
        frames: int = 0,
    ) -> None:
        report_path = self.report_dir / f"{task.metadata['chunk']}.jsonl"
        record = {
            "source": str(source),
            "status": status,
            "reason": reason,
            "frames": frames,
        }
        with report_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _prepare_episode(self, source: Path) -> PreparedEpisode:
        try:
            from mcap.reader import make_reader
            from mcap_protobuf.decoder import DecoderFactory
        except ImportError as exc:
            raise RuntimeError("Install mcap and mcap-protobuf-support first") from exc

        episode_temp = Path(tempfile.mkdtemp(prefix=f"{source.parent.name}_", dir=self.work_dir))
        camera_files: dict[str, Any] = {}
        camera_paths: dict[str, Path] = {}
        camera_times: dict[str, list[int]] = {topic: [] for topic in CAMERA_CANDIDATES}
        camera_codecs: dict[str, str] = {}
        scalar_times: dict[str, list[int]] = {topic: [] for topic in SCALAR_TOPICS}
        scalar_positions: dict[str, list[np.ndarray]] = {topic: [] for topic in SCALAR_TOPICS}
        scalar_poses: dict[str, list[np.ndarray]] = {topic: [] for topic in ARM_TOPICS}
        instruction: str | None = None

        topics = [*SCALAR_TOPICS, *CAMERA_CANDIDATES, "/instruction"]
        try:
            with source.open("rb") as stream:
                reader = make_reader(stream, decoder_factories=[DecoderFactory()])
                for _, channel, message, decoded in reader.iter_decoded_messages(topics=topics):
                    topic = channel.topic
                    if topic in CAMERA_CANDIDATES:
                        if topic not in camera_files:
                            camera_name = topic.strip("/").replace("/", "_")
                            path = episode_temp / f"camera_{camera_name}.bin"
                            camera_paths[topic] = path
                            camera_files[topic] = path.open("wb")
                        camera_files[topic].write(bytes(decoded.data))
                        camera_times[topic].append(int(message.log_time))
                        camera_codecs[topic] = str(decoded.format).lower()
                    elif topic in SCALAR_TOPICS:
                        expected = 6 if topic in ARM_TOPICS else 1
                        position = np.asarray(decoded.position, dtype=np.float64)
                        if position.shape != (expected,):
                            raise ValueError(
                                f"{topic}.position has shape {position.shape}, "
                                f"expected ({expected},)"
                            )
                        scalar_times[topic].append(int(message.log_time))
                        scalar_positions[topic].append(position)
                        if topic in ARM_TOPICS:
                            scalar_poses[topic].append(np.asarray(decoded.pose, dtype=np.float64))
                    elif topic == "/instruction":
                        instruction = str(decoded.data).strip()
        except Exception:
            shutil.rmtree(episode_temp, ignore_errors=True)
            raise
        finally:
            for file_obj in camera_files.values():
                file_obj.close()

        try:
            missing = [topic for topic in SCALAR_TOPICS if not scalar_times[topic]]
            if missing:
                raise ValueError(f"missing required robot streams: {missing}")

            if "/top-left-camera" in camera_paths and "/top-right-camera" in camera_paths:
                digest = hashlib.sha1(source.parent.name.encode()).digest()[0]
                top_topic = "/top-left-camera" if digest % 2 == 0 else "/top-right-camera"
            elif "/top-camera" in camera_paths:
                top_topic = "/top-camera"
            else:
                raise ValueError("missing top camera")

            camera_topics = {
                "top": top_topic,
                "left_wrist": "/left-wrist-camera",
                "right_wrist": "/right-wrist-camera",
            }
            absent_cameras = [
                topic for topic in camera_topics.values() if topic not in camera_paths
            ]
            if absent_cameras:
                raise ValueError(f"missing required cameras: {absent_cameras}")

            scalars = {
                topic: ScalarStream(
                    timestamps=np.asarray(scalar_times[topic], dtype=np.int64),
                    positions=np.stack(scalar_positions[topic]),
                    poses=scalar_poses.get(topic, []),
                )
                for topic in SCALAR_TOPICS
            }
            cameras: dict[str, CameraStream] = {}
            for key, topic in camera_topics.items():
                timestamps = np.asarray(camera_times[topic], dtype=np.int64)
                codec = camera_codecs[topic]
                input_format = "hevc" if codec in {"h265", "hevc"} else "h264"
                decoded_count = (
                    _run_probe(camera_paths[topic], input_format)
                    if self.verify_video_frame_count
                    else None
                )
                if decoded_count and decoded_count != len(timestamps):
                    timestamps = np.linspace(
                        timestamps[0], timestamps[-1], decoded_count, dtype=np.int64
                    )
                cameras[key] = CameraStream(timestamps, camera_paths[topic], codec)

            all_times = [stream.timestamps for stream in scalars.values()] + [
                stream.timestamps for stream in cameras.values()
            ]
            start_ns = max(int(values[0]) for values in all_times)
            end_ns = min(int(values[-1]) for values in all_times)
            ticks = np.arange(start_ns + TICK_NS, end_ns + 1, TICK_NS, dtype=np.int64)
            if len(ticks) < MIN_EPISODE_FRAMES:
                raise ValueError(f"episode overlap is too short: {len(ticks)} frames")

            scalar_indices = {
                topic: floor_indices(stream.timestamps, ticks)
                for topic, stream in scalars.items()
            }
            camera_indices = {
                key: floor_indices(stream.timestamps, ticks) for key, stream in cameras.items()
            }
            for topic, indices in scalar_indices.items():
                max_gap = int(np.max(ticks - scalars[topic].timestamps[indices]))
                if max_gap > self.max_gap_ns:
                    raise ValueError(f"{topic} causal alignment gap {max_gap / 1e6:.1f} ms")
            for key, indices in camera_indices.items():
                max_gap = int(np.max(ticks - cameras[key].timestamps[indices]))
                if max_gap > self.max_gap_ns:
                    raise ValueError(f"camera {key} causal alignment gap {max_gap / 1e6:.1f} ms")

            def aligned_position(topic: str) -> np.ndarray:
                return scalars[topic].positions[scalar_indices[topic]]

            state_qpos = np.concatenate(
                [
                    aligned_position(LEFT_ARM_STATE),
                    aligned_position(LEFT_GRIPPER_STATE),
                    aligned_position(RIGHT_ARM_STATE),
                    aligned_position(RIGHT_GRIPPER_STATE),
                ],
                axis=1,
            ).astype(np.float32)
            action_qpos, action_qpos_valid = sanitize_bimanual_qpos_action(np.concatenate(
                [
                    aligned_position(LEFT_ARM_ACTION),
                    aligned_position(LEFT_GRIPPER_ACTION),
                    aligned_position(RIGHT_ARM_ACTION),
                    aligned_position(RIGHT_GRIPPER_ACTION),
                ],
                axis=1,
            ))
            arrays: dict[str, np.ndarray] = {
                "state.qpos": state_qpos,
                "action.qpos": action_qpos,
                "action.qpos_valid": action_qpos_valid,
            }

            if not self.qpos_only:
                pose_arrays: dict[str, np.ndarray] = {}
                pose_valid: dict[str, np.ndarray] = {}
                for topic in ARM_TOPICS:
                    pose_arrays[topic], pose_valid[topic] = convert_pose_stream(
                        stream=scalars[topic],
                        aligned_indices=scalar_indices[topic],
                        frame_count=len(ticks),
                        topic=topic,
                        missing_policy=self.missing_ee_policy,
                    )
                arrays["state.ee"] = np.concatenate(
                    [pose_arrays[LEFT_ARM_STATE], pose_arrays[RIGHT_ARM_STATE]], axis=1
                ).astype(np.float32)
                arrays["state.ee_valid"] = np.stack(
                    [pose_valid[LEFT_ARM_STATE], pose_valid[RIGHT_ARM_STATE]], axis=1
                ).astype(np.float32)
                arrays["action.ee"] = np.concatenate(
                    [pose_arrays[LEFT_ARM_ACTION], pose_arrays[RIGHT_ARM_ACTION]], axis=1
                ).astype(np.float32)
                arrays["action.ee_valid"] = np.stack(
                    [pose_valid[LEFT_ARM_ACTION], pose_valid[RIGHT_ARM_ACTION]], axis=1
                ).astype(np.float32)

            if instruction is None:
                instruction = source.parent.parent.name.replace("_", " ")
            return PreparedEpisode(
                source=source,
                instruction=instruction,
                ticks=ticks,
                arrays=arrays,
                camera_indices=camera_indices,
                cameras=cameras,
                width=self.width,
                height=self.height,
                temp_dir=episode_temp,
            )
        except Exception:
            shutil.rmtree(episode_temp, ignore_errors=True)
            raise


def rewrite_masked_ee_stats(output_path: Path, batch_size: int = 2048) -> None:
    """Replace zero-biased EE stats with stats from ee_valid==1 episodes only.

    The audited ABC release has episode-level EE availability: both sides are
    present or both are empty for every episode. Reading the compact episode
    metadata is therefore sufficient; the large frame parquet files do not
    need to be scanned a second time.
    """
    try:
        import pyarrow.parquet as pq
        from lerobot.datasets.compute_stats import aggregate_feature_stats
        from lerobot.datasets.io_utils import load_stats, write_stats
    except ImportError as exc:
        raise RuntimeError("Mask-aware EE stats require pyarrow and LeRobot v3") from exc

    feature_to_mask = {
        "state.ee": "state.ee_valid",
        "action.ee": "action.ee_valid",
    }
    statistic_names = (
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
    pending: dict[str, list[dict[str, np.ndarray]]] = {
        key: [] for key in feature_to_mask
    }
    partial: dict[str, list[dict[str, np.ndarray]]] = {
        key: [] for key in feature_to_mask
    }
    valid_episode_counts = {key: 0 for key in feature_to_mask}

    columns = []
    for feature, mask in feature_to_mask.items():
        columns.append(f"stats/{mask}/mean")
        columns.extend(f"stats/{feature}/{name}" for name in statistic_names)

    def flush(feature: str) -> None:
        if pending[feature]:
            partial[feature].append(aggregate_feature_stats(pending[feature]))
            pending[feature].clear()

    episode_meta_files = sorted(output_path.glob("meta/episodes/chunk-*/file-*.parquet"))
    if not episode_meta_files:
        raise FileNotFoundError(f"No episode metadata parquet found below {output_path}")

    for parquet_path in episode_meta_files:
        values = pq.read_table(parquet_path, columns=columns).to_pydict()
        row_count = len(next(iter(values.values())))
        for row_index in range(row_count):
            for feature, mask in feature_to_mask.items():
                validity = np.asarray(
                    values[f"stats/{mask}/mean"][row_index], dtype=np.float64
                )
                if validity.shape != (2,):
                    raise ValueError(
                        f"{mask} episode mean has shape {validity.shape}, expected (2,)"
                    )
                if not np.allclose(validity, 1.0):
                    continue
                pending[feature].append(
                    {
                        name: np.asarray(
                            values[f"stats/{feature}/{name}"][row_index]
                        )
                        for name in statistic_names
                    }
                )
                valid_episode_counts[feature] += 1
                if len(pending[feature]) >= batch_size:
                    flush(feature)

    dataset_stats = load_stats(output_path)
    if dataset_stats is None:
        raise FileNotFoundError(f"Missing meta/stats.json below {output_path}")
    for feature in feature_to_mask:
        flush(feature)
        if partial[feature]:
            dataset_stats[feature] = aggregate_feature_stats(partial[feature])
        else:
            print(
                f"[EE STATS] no valid {feature} episodes; leaving placeholder-only stats unchanged",
                flush=True,
            )
    write_stats(dataset_stats, output_path)
    print(
        "[EE STATS] valid-only episode counts: "
        + ", ".join(f"{key}={value}" for key, value in valid_episode_counts.items()),
        flush=True,
    )


def push_converted_dataset(
    output_path: Path,
    repo_id: str,
    adapter: ABC130KAdapter,
) -> None:
    """Push only after mask-aware statistics have been written locally."""
    from lerobot.datasets import LeRobotDataset

    tags = list(
        dict.fromkeys(
            [
                "LeRobot",
                adapter.dataset_type,
                adapter.robot_type,
                *adapter.tags,
            ]
        )
    )
    LeRobotDataset(repo_id=repo_id, root=output_path).push_to_hub(
        tags=tags,
        private=False,
        push_videos=True,
        license="apache-2.0",
        upload_large_folder=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-root", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument("--split", choices=["train", "val"], default="train")
    parser.add_argument("--episodes-per-task", type=int, default=32)
    parser.add_argument("--max-episodes", type=int)
    parser.add_argument(
        "--episode-list",
        type=Path,
        help="optional text file containing one absolute episode.mcap path per line",
    )
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--resize-width", type=int, default=640)
    parser.add_argument("--resize-height", type=int, default=480)
    parser.add_argument("--max-gap-ms", type=float, default=100.0)
    parser.add_argument(
        "--qpos-only",
        action="store_true",
        help="omit state.ee/action.ee and their validity masks",
    )
    parser.add_argument(
        "--missing-ee-policy",
        choices=["fill", "skip", "error"],
        default="fill",
        help="fill uses finite zeros plus ee_valid=0; skip/error reject missing raw pose",
    )
    parser.add_argument("--executor", choices=["local", "ray"], default="local")
    parser.add_argument("--cpus-per-task", type=int, default=2)
    parser.add_argument("--tasks-per-job", type=int, default=1)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument(
        "--image-writer-threads",
        type=int,
        default=8,
        help="background PNG writers per conversion task",
    )
    parser.add_argument(
        "--verify-video-frame-count",
        action="store_true",
        help="fully decode each camera once with ffprobe before conversion; safer but much slower",
    )
    parser.add_argument("--resume-dir", type=Path)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--repo-id", type=str)
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument("--keep-temp", action="store_true")
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    """Fail fast before creating temporary or output directories."""
    if args.episodes_per_task < 1:
        raise ValueError("--episodes-per-task must be >= 1")
    if args.max_episodes is not None and args.max_episodes < 1:
        raise ValueError("--max-episodes must be >= 1")
    if args.resize_width < 1 or args.resize_height < 1:
        raise ValueError("--resize-width and --resize-height must be >= 1")
    if args.max_gap_ms <= 0:
        raise ValueError("--max-gap-ms must be > 0")
    if args.workers == 0 or args.workers < -1:
        raise ValueError("--workers must be -1 or >= 1")
    if args.image_writer_threads < 1:
        raise ValueError("--image-writer-threads must be >= 1")
    if args.push_to_hub and not args.repo_id:
        raise ValueError("--repo-id is required with --push-to-hub")


def main() -> None:
    args = parse_args()
    validate_args(args)
    missing_ee_policy = cast(MissingEEPolicy, args.missing_ee_policy)
    adapter = ABC130KAdapter(
        src_root=args.src_root,
        output_path=args.output_path,
        split=args.split,
        episodes_per_task=args.episodes_per_task,
        max_episodes=args.max_episodes,
        episode_list=args.episode_list,
        work_dir=args.work_dir,
        width=args.resize_width,
        height=args.resize_height,
        max_gap_ms=args.max_gap_ms,
        qpos_only=args.qpos_only,
        missing_ee_policy=missing_ee_policy,
        image_writer_threads=args.image_writer_threads,
        verify_video_frame_count=args.verify_video_frame_count,
    )
    converted_path = run_converter(
        adapter=adapter,
        executor=args.executor,
        cpus_per_task=args.cpus_per_task,
        tasks_per_job=args.tasks_per_job,
        workers=args.workers,
        resume_dir=args.resume_dir,
        debug=args.debug,
        local_repo_id=args.repo_id,
        hub_repo_id=args.repo_id,
        # EE stats must be rewritten before any upload.
        push_to_hub=False,
        cleanup_temp=not args.keep_temp,
    )
    if not args.qpos_only:
        rewrite_masked_ee_stats(converted_path)
    if args.push_to_hub:
        assert args.repo_id is not None  # Enforced by validate_args.
        push_converted_dataset(converted_path, args.repo_id, adapter)


if __name__ == "__main__":
    main()
