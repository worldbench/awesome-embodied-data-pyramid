#!/usr/bin/env python3
"""Convert extracted AgiBotWorld-Beta episodes to unified LeRobot v3.0."""

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
for import_path in (REPO_ROOT, REPO_ROOT / "agibot2lerobot"):
    import_path_string = str(import_path)
    if import_path_string not in sys.path:
        sys.path.insert(0, import_path_string)

from agibot2lerobot.agibot_h5 import AgiBotAdapter  # noqa: E402
from agibot2lerobot.agibot_utils.agibot_utils import (  # noqa: E402
    get_episode_videos,
    load_depths,
)
from agibotworld_beta_2lerobot.beta_utils import (  # noqa: E402
    EffectorType,
    build_features,
    load_unified_episode,
    qpos_dimension,
)
from generic_converter import run_converter  # noqa: E402


class UnifiedAgiBotBetaAdapter(AgiBotAdapter):
    """AgiBot adapter that emits the project-wide qpos/EE feature names."""

    dataset_type = "agibotworld-beta-unified"
    tags = ("agibot-world", "a2d", "unified-action-space")

    def __init__(
        self,
        src_path: Path,
        output_path: Path,
        eef_type: EffectorType,
        task_ids: list[str],
        save_depth: bool,
        episodes_per_task: int,
        invalid_episode_policy: str,
    ) -> None:
        super().__init__(
            src_path=src_path,
            output_path=output_path,
            eef_type=eef_type,
            task_ids=task_ids,
            save_depth=save_depth,
            episodes_per_task=episodes_per_task,
        )
        self.invalid_episode_policy = invalid_episode_policy
        self.features = build_features(
            raw_config=self.agibot_world_config,
            effector_type=eef_type,
            save_depth=save_depth,
        )

    def load_subset(self, task):
        json_file = task.input_path
        print(f"processing {json_file.stem}, saving to {task.output_path}")
        src_path, task_id, task_instruction, task_info = self._load_task_context(
            json_file
        )
        episode_ids = task.metadata.get("episode_ids")
        if episode_ids is None:
            episode_ids = sorted(task_info)

        for episode_id in episode_ids:
            if not self._is_convertible_episode(
                json_file.stem,
                src_path,
                task_id,
                episode_id,
                task_info,
            ):
                continue
            h5_path = (
                src_path
                / "proprio_stats"
                / task_id
                / str(episode_id)
                / "proprio_stats.h5"
            )
            if not h5_path.is_file():
                message = f"Missing {h5_path}"
                if self.invalid_episode_policy == "error":
                    raise FileNotFoundError(message)
                print(f"{message}; skipping")
                continue
            try:
                arrays = load_unified_episode(h5_path, self.eef_type)
                frame_count = len(arrays["state.qpos"])
                depth_images = None
                if self.save_depth:
                    depth_images = load_depths(
                        src_path
                        / "observations"
                        / task_id
                        / str(episode_id)
                        / "depth",
                        "head_depth",
                    )
                    if len(depth_images) != frame_count:
                        raise ValueError(
                            f"Depth/action length mismatch: {len(depth_images)} "
                            f"!= {frame_count}"
                        )
            except Exception as exception:
                if self.invalid_episode_policy == "error":
                    raise
                print(
                    f"{json_file.stem}, episode_{episode_id}: {exception}; skipping"
                )
                continue

            frames = []
            for frame_index in range(frame_count):
                frame: dict[str, Any] = {
                    key: value[frame_index] for key, value in arrays.items()
                }
                if depth_images is not None:
                    frame["observation.images.head_depth"] = depth_images[frame_index]
                frame["task"] = task_instruction
                frames.append(frame)

            yield {
                "episode_id": episode_id,
                "frames": frames,
                "videos": get_episode_videos(
                    src_path,
                    task_id,
                    episode_id,
                    self.agibot_world_config,
                ),
                "action_config": task_info[episode_id]["label_info"]["action_config"],
            }


def validate_source_root(source_root: Path) -> None:
    required_directories = ("observations", "parameters", "proprio_stats", "task_info")
    missing = [
        name for name in required_directories if not (source_root / name).is_dir()
    ]
    if missing:
        raise FileNotFoundError(
            f"Staged source is missing required directories: {missing}"
        )
    if not any((source_root / "observations").glob("*/*/videos")):
        raise ValueError(
            "observations contains archives rather than extracted episodes. Run "
            "prepare_raw.py into a staging root, then pass that root here."
        )
    if not any((source_root / "proprio_stats").glob("*/*/proprio_stats.h5")):
        raise ValueError(
            "proprio_stats contains archives rather than extracted HDF5 files. Run "
            "prepare_raw.py into a staging root first."
        )


def write_conversion_marker(
    output_path: Path,
    source_root: Path,
    eef_type: EffectorType,
) -> None:
    marker = {
        "source_dataset": "AgiBotWorld-Beta",
        "source_root": str(source_root),
        "target_version": "v3.0",
        "effector_type": eef_type,
        "qpos_dimension": qpos_dimension(eef_type),
        "ee_dimension": 14,
        "waist_dimension": 2,
        "waist_order": ["pitch", "lift"],
        "effector_rule": (
            "action/left_effector/position and "
            "action/right_effector/position keep the same semantic field names; "
            f"each side has {1 if eef_type == 'gripper' else 6} value(s)."
        ),
        "dropped_source_action_channels": [
            "action/head/position",
            "action/robot/velocity",
        ],
        "source_components": [
            "observations",
            "parameters",
            "proprio_stats",
            "task_info",
        ],
    }
    marker_path = output_path / "meta" / "unified_action_space.json"
    marker_path.write_text(
        json.dumps(marker, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--src-path", type=Path, required=True)
    parser.add_argument("--output-path", type=Path, required=True)
    parser.add_argument(
        "--eef-type",
        choices=["gripper", "dexhand"],
        required=True,
    )
    parser.add_argument("--task-ids", nargs="+", default=[])
    parser.add_argument("--executor", choices=["local", "ray"], default="local")
    parser.add_argument("--cpus-per-task", type=int, default=1)
    parser.add_argument("--tasks-per-job", type=int, default=1)
    parser.add_argument("--episodes-per-task", type=int, default=10)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--resume-dir", type=Path)
    parser.add_argument("--save-depth", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--repo-id")
    parser.add_argument("--push-to-hub", action="store_true")
    parser.add_argument(
        "--invalid-episode-policy",
        choices=["error", "skip"],
        default="error",
    )
    parser.add_argument("--resume", action="store_true", help="Resume task-grouped outputs using the same task checkpoints")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_root = args.src_path.expanduser().resolve()
    output_path = args.output_path.expanduser().resolve()
    validate_source_root(source_root)
    grouped = os.environ.get("BETA_AGGREGATE_BY_TASK") == "1"
    if grouped and args.push_to_hub:
        raise ValueError("Grouped outputs must be uploaded separately after verification")
    complete = output_path / "ALL_TASKS_COMPLETE.json"
    if args.resume and grouped and complete.exists():
        marker = json.loads(complete.read_text())
        parts = [p for p in output_path.glob("task_*") if re.fullmatch(r"task_\d+", p.name)
                 and (p / "TASK_COMPLETE.json").exists()]
        if len(parts) != marker['tasks']:
            raise ValueError("Completed task count mismatch")
        total = sum(json.loads((p/'meta/info.json').read_text())['total_episodes'] for p in parts)
        if total != marker['episodes']: raise ValueError("Completed episode count mismatch")
        for p in parts: write_conversion_marker(p, source_root, args.eef_type)
        print(f"Already complete: {output_path}")
        return
    if output_path.exists() and not (args.resume and grouped and args.resume_dir):
        raise FileExistsError(
            f"Refusing to replace existing output: {output_path}. Use a new path."
        )
    if args.episodes_per_task < 1:
        raise ValueError("--episodes-per-task must be >= 1")
    if args.workers == 0 or args.workers < -1:
        raise ValueError("--workers must be -1 or >= 1")

    adapter = UnifiedAgiBotBetaAdapter(
        src_path=source_root,
        output_path=output_path,
        eef_type=args.eef_type,
        task_ids=args.task_ids,
        save_depth=args.save_depth,
        episodes_per_task=args.episodes_per_task,
        invalid_episode_policy=args.invalid_episode_policy,
    )
    run_converter(
        adapter=adapter,
        cleanup_temp=False,
        executor=args.executor,
        cpus_per_task=args.cpus_per_task,
        tasks_per_job=args.tasks_per_job,
        workers=args.workers,
        resume_dir=args.resume_dir,
        debug=args.debug,
        local_repo_id=args.repo_id,
        hub_repo_id=args.repo_id,
        push_to_hub=args.push_to_hub,
        extra_tags=[args.eef_type],
    )
    if __import__("os").environ.get("BETA_AGGREGATE_BY_TASK") == "1":
        for root in output_path.glob("task_*"):
            if re.fullmatch(r"task_\d+", root.name) and (root / "TASK_COMPLETE.json").exists():
                write_conversion_marker(root, source_root, args.eef_type)
    else:
        write_conversion_marker(output_path, source_root, args.eef_type)


def cli() -> None:
    module = importlib.import_module(
        "agibotworld_beta_2lerobot.convert_agibotworld_beta"
    )
    module.main()


if __name__ == "__main__":
    cli()
