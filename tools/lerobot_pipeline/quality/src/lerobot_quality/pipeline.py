"""Run one embodiment adapter through shared signal and configured FK checks.

Produces auditable episode decisions, without rewriting the source LeRobot repo.
Unavailable checks are explicitly listed; a sampled run never produces keep decisions.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
import pyarrow.parquet as pq

from .adapters import resolve_adapter
from .fk_compare import compare_repo
from .schema import read_info
from .signal_quality import Thresholds, _check_output, validate_repo


def run_pipeline(
    repo: Path,
    output: Path,
    *,
    adapter: str = "auto",
    max_frames: int | None = None,
    fk_config: Path | None = None,
    require_fk: bool = False,
    require_action_targets: bool = False,
    require_ee_targets: bool = False,
    thresholds: Thresholds = Thresholds(),
    write_frames: bool = False,
) -> dict:
    _check_output(repo, output)
    contract = resolve_adapter(read_info(repo), adapter)
    from .export import BatchFK

    runtime = BatchFK(contract, fk_config, require_fk, 0.01, 2.0)
    fk_config, reason = runtime.config_path, runtime.unavailable_reason
    output.mkdir(parents=True, exist_ok=True)
    signal = validate_repo(
        repo,
        output / "signal",
        adapter=adapter,
        max_frames=max_frames,
        require_action_targets=require_action_targets,
        require_ee_targets=require_ee_targets,
        thresholds=thresholds,
        write_frames=write_frames,
    )
    fk = None
    fk_failures: set[int] = set()
    fk_checked: dict[int, int] = {}
    if reason is None:
        fk = compare_repo(
            repo,
            fk_config,
            output / "fk",
            adapter=adapter,
            max_frames=max_frames,
            write_frames=True,
        )
        file = pq.ParquetFile(output / "fk/frames.parquet")
        sides = [
            side
            for side in contract.arm_indices
            if f"{side}_fk_input_valid" in file.schema_arrow.names
        ]
        columns = [
            "episode_index",
            *[f"{s}_{key}" for s in sides for key in ("fk_input_valid", "fk_ee_valid")],
        ]
        for record in file.iter_batches(columns=columns):
            values = record.to_pydict()
            for row, episode in enumerate(values["episode_index"]):
                valid_sides = [s for s in sides if values[f"{s}_fk_input_valid"][row]]
                if valid_sides:
                    fk_checked[episode] = fk_checked.get(episode, 0) + 1
                    if any(not values[f"{s}_fk_ee_valid"][row] for s in valid_sides):
                        fk_failures.add(episode)
    decisions = json.loads((output / "signal/episodes.json").read_text())
    sampled = max_frames is not None
    for episode, decision in decisions.items():
        okay = decision["observed_frames_valid"] and int(episode) not in fk_failures
        decision.update(
            {
                "quality_valid": None if sampled else okay,
                "observed_checks_passed": okay,
                "fk_checked_frames": fk_checked.get(int(episode), 0),
                "fk_failed": int(episode) in fk_failures,
            }
        )
    summary = {
        "schema_version": "lerobot_quality_pipeline_v1",
        "repo": str(repo.resolve()),
        "adapter": contract.name,
        "coverage": contract.coverage(),
        "scope": "sample" if sampled else "full",
        "stages": {"signal": "completed", "fk": "unavailable" if reason else "completed"},
        "fk_unavailable_reason": reason,
        "decision_rule": "all observed signal checks and all FK frames with valid inputs pass; unavailable checks do not vote",
        "frames": signal["frames"],
        "episodes": len(decisions),
        "retained_episodes": (
            None if sampled else sum(d["quality_valid"] for d in decisions.values())
        ),
        "fk_checked_frames": sum(fk_checked.values()),
        "policy": {"require_fk": require_fk, **signal["policy"]},
        "source_modified": False,
    }
    (output / "episodes.json").write_text(
        json.dumps(decisions, ensure_ascii=False, indent=2) + "\n"
    )
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", default="auto")
    parser.add_argument("--max-frames", type=int)
    parser.add_argument("--fk-config", type=Path)
    parser.add_argument("--require-fk", action="store_true")
    parser.add_argument("--require-action-targets", action="store_true")
    parser.add_argument("--require-ee-targets", action="store_true")
    parser.add_argument("--write-frames", action="store_true")
    parser.add_argument("--joint-step-rad", type=float, default=0.35)
    parser.add_argument("--ee-position-step-m", type=float, default=0.10)
    parser.add_argument("--ee-rotation-step-deg", type=float, default=30.0)
    args = parser.parse_args()
    result = run_pipeline(
        args.repo,
        args.output,
        adapter=args.adapter,
        max_frames=args.max_frames,
        fk_config=args.fk_config,
        require_fk=args.require_fk,
        require_action_targets=args.require_action_targets,
        require_ee_targets=args.require_ee_targets,
        write_frames=args.write_frames,
        thresholds=Thresholds(
            args.joint_step_rad, args.ee_position_step_m, args.ee_rotation_step_deg
        ),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
