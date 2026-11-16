"""Run FK validation over one LeRobot repo or a tree of repos."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .fk_compare import compare_repo
from .schema import STATE_EE, STATE_EE_VALID, STATE_QPOS, read_info


def discover_repos(root: Path) -> list[Path]:
    candidates = (
        [root]
        if (root / "meta" / "info.json").is_file()
        else [path.parent.parent for path in sorted(root.rglob("meta/info.json"))]
    )
    result = []
    for repo in candidates:
        features = set(read_info(repo).get("features", {}))
        if {STATE_QPOS, STATE_EE}.issubset(features):
            result.append(repo)
    return result


def run(args: argparse.Namespace) -> dict:
    repos = discover_repos(args.root)
    if args.max_repos is not None:
        repos = repos[: args.max_repos]
    if not repos:
        raise ValueError("no repos with state.qpos/state.ee found")
    reports = []
    args.output.mkdir(parents=True, exist_ok=True)
    for index, repo in enumerate(repos):
        relative = repo.relative_to(args.root) if repo != args.root else Path(repo.name)
        report_output = (
            args.output / "repos" / f"{index:05d}_{relative.as_posix().replace('/', '__')}"
        )
        report = compare_repo(
            repo,
            args.config,
            report_output,
            stride=args.stride,
            max_frames=args.max_frames_per_repo,
            position_threshold_m=args.position_threshold_m,
            rotation_threshold_deg=args.rotation_threshold_deg,
            write_frames=False,
        )
        report["repo_id"] = relative.as_posix()
        reports.append(report)
    valid_frames = sum(item["valid_frames"] for item in reports)
    pass_frames = sum(item["pass_frames"] for item in reports)
    summary = {
        "schema_version": "lerobot_fk_dataset_report_v1",
        "root": str(args.root.resolve()),
        "config": str(args.config.resolve()),
        "repos": len(reports),
        "frames": sum(item["frames"] for item in reports),
        "valid_frames": valid_frames,
        "pass_frames": pass_frames,
        "pass_rate": pass_frames / valid_frames if valid_frames else float("nan"),
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    (args.output / "repos.json").write_text(
        json.dumps(reports, ensure_ascii=False, indent=2) + "\n"
    )
    with (args.output / "repos.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "repo_id",
                "frames",
                "valid_frames",
                "pass_frames",
                "pass_rate",
                "qpos_width",
            ),
        )
        writer.writeheader()
        for item in reports:
            writer.writerow({key: item[key] for key in writer.fieldnames})
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stride", type=int, default=1)
    parser.add_argument("--max-frames-per-repo", type=int)
    parser.add_argument("--max-repos", type=int)
    parser.add_argument("--position-threshold-m", type=float, default=0.01)
    parser.add_argument("--rotation-threshold-deg", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(json.dumps(run(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
