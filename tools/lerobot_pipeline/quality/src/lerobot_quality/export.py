"""Annotate every LeRobot v3 frame in a new repo, reusing the original videos.

No rows are removed. Source frame/episode indices and video timestamps stay intact.
quality.valid means all applicable configured checks passed; FK coverage is separate.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import shutil
import tempfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .adapters import resolve_adapter
from .fk_compare import _side_fk, joint_names, load_config, extra_joint_positions, fk_base_link
from .schema import LeRobotSchema, read_info
from .signal_quality import Thresholds, parquet_files, validate_repo
from .urdf_fk import UrdfModel

QUALITY_FEATURES = {
    "quality.valid": {
        "dtype": "bool",
        "shape": [1],
        "names": None,
        "description": "Per-frame pass flag for applicable configured quality checks. "
        "False marks only this frame. This is not a claim that unavailable "
        "checks passed. Original target masks must still gate training losses.",
    },
}

# Reject previous annotated outputs too; source robot columns are never rewritten.
ANNOTATION_COLUMNS = set(QUALITY_FEATURES) | {"quality.fk_checked"}


def bool_stats(count: int, true_count: int) -> dict:
    if not count or not 0 <= true_count <= count:
        raise ValueError("invalid boolean statistics counts")
    mean = true_count / count
    result = {
        "min": [float(true_count == count)],
        "max": [float(true_count > 0)],
        "mean": [mean],
        "std": [math.sqrt(mean * (1 - mean))],
        "count": [count],
    }
    zeros = count - true_count
    for key, q in (("q01", 0.01), ("q10", 0.1), ("q50", 0.5), ("q90", 0.9), ("q99", 0.99)):
        rank = (count - 1) * q
        low, high = math.floor(rank), math.ceil(rank)
        result[key] = [
            float(low >= zeros) + (rank - low) * (float(high >= zeros) - float(low >= zeros))
        ]
    return result


def append_columns(table: pa.Table, columns: dict[str, pa.Array]) -> pa.Table:
    """Preserve field types and custom metadata, invalidate stale pandas/HF schemas."""
    for key, values in columns.items():
        if key in table.column_names:
            raise ValueError(f"quality output column already exists: {key}")
        table = table.append_column(key, values)
    metadata = dict(table.schema.metadata or {})
    metadata.pop(b"pandas", None)
    metadata.pop(b"huggingface", None)
    return table.replace_schema_metadata(metadata or None)


class FrameReader:
    """Read report rows in order with bounded memory across independent batch boundaries."""

    def __init__(self, path: Path, batch_size: int):
        self.records = iter(pq.ParquetFile(path).iter_batches(batch_size=batch_size))
        self.current = None
        self.offset = 0

    def take(self, count: int) -> pa.Table:
        parts = []
        while count:
            if self.current is None or self.offset == len(self.current):
                self.current = next(self.records, None)
                self.offset = 0
                if self.current is None:
                    raise ValueError("signal report has fewer rows than source data")
            length = min(count, len(self.current) - self.offset)
            parts.append(self.current.slice(self.offset, length))
            self.offset += length
            count -= length
        return pa.Table.from_batches(parts)

    def assert_exhausted(self) -> None:
        if self.current is not None and self.offset != len(self.current):
            raise ValueError("signal report has extra rows")
        if next(self.records, None) is not None:
            raise ValueError("signal report has extra batches")


class BatchFK:
    """Bounded-memory wrapper around the exact same FK checker as fk_compare."""

    def __init__(
        self,
        contract,
        config_path: Path | None,
        require_fk: bool,
        position_threshold_m: float,
        rotation_threshold_deg: float,
    ):
        self.contract = contract
        self.position_threshold_m = position_threshold_m
        self.rotation_threshold_deg = rotation_threshold_deg
        explicit = config_path is not None
        self.unavailable_reason = contract.profile.get("fk_comparison_unavailable_reason")
        default = contract.profile.get("default_fk_config")
        if config_path is None and default:
            config_path = Path(__file__).resolve().parents[2] / "configs" / default
        if "state.qpos" not in contract.columns:
            self.unavailable_reason = (
                "no observed state.qpos; FK requires both joint positions and Cartesian EE"
            )
        elif "state.ee" not in contract.pose_keys:
            self.unavailable_reason = "no observed Cartesian state.ee; model mapping cannot independently validate absent targets"
        elif config_path is None and not self.unavailable_reason:
            self.unavailable_reason = "no executable FK mapping/frame calibration configured"
        self.config_path = config_path.resolve() if config_path else None
        if self.unavailable_reason:
            if require_fk or explicit:
                raise ValueError(f"FK required but unavailable: {self.unavailable_reason}")
            return
        self.config = load_config(self.config_path)
        LeRobotSchema(contract.qpos_width).validate_config_width(self.config.get("qpos_widths"))
        self.model = UrdfModel.load(self.config["urdf"])
        extra = self.config.get("extra_joints", {})
        for joint, mapping in extra.items():
            feature, index = mapping["feature"], mapping["index"]
            if joint not in self.model.joint_by_name:
                raise ValueError(f"{joint}: body joint absent from URDF")
            if (
                feature not in contract.columns
                or not 0 <= index < contract.profile["feature_widths"][feature]
            ):
                raise ValueError(
                    f"{joint}: missing or incompatible body feature {feature}[{index}]"
                )
        for side in self.config["active_sides"]:
            if side not in contract.arm_indices or side not in contract.ee_sides:
                raise ValueError(f"FK side {side} is absent from adapter")
            names = joint_names(self.config, side)
            if len(names) != len(contract.arm_indices[side]):
                raise ValueError(f"{side}: FK joint count does not match adapter")
            if set(names) - set(self.model.joint_by_name):
                raise ValueError(f"{side}: configured joints absent from URDF")
            required = {
                j.name
                for j in self.model.chain(
                    fk_base_link(self.config, side), self.config[f"{side}_ee_link"]
                )
                if j.kind != "fixed"
            }
            if required - set(names) - set(extra):
                raise ValueError(
                    f"{side}: FK chain joints are not mapped: {sorted(required-set(names)-set(extra))}"
                )

    def check(self, table: pa.Table) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
        checked, failed = np.zeros(len(table), bool), np.zeros(len(table), bool)
        detail = {}
        if self.unavailable_reason:
            return checked, failed, detail
        arrays = self.contract.arrays(table)
        qpos, ee = arrays["state.qpos"], arrays["state.ee"]
        masks = arrays["state.ee_valid"] == 1
        extra = extra_joint_positions(self.config, arrays)
        for side in self.config["active_sides"]:
            i = self.contract.ee_sides.index(side)
            result = _side_fk(
                self.model,
                self.config,
                side,
                qpos,
                self.contract.arm_indices[side],
                ee[:, i * 7 : (i + 1) * 7],
                masks[:, i],
                self.position_threshold_m,
                self.rotation_threshold_deg,
                extra,
            )
            checked |= result["fk_input_valid"]
            failed |= result["fk_input_valid"] & ~result["fk_ee_valid"]
            detail.update({f"{side}_{key}": value for key, value in result.items()})
        return checked, failed, detail


def snapshot(paths: list[Path]) -> dict[str, tuple[int, int]]:
    return {str(p): (s.st_size, s.st_mtime_ns) for p in paths for s in [p.stat()]}


def update_episode_metadata(stage: Path, counts: dict[int, list[int]]) -> None:
    seen = set()
    files = sorted((stage / "meta/episodes").rglob("*.parquet"))
    if not files:
        raise ValueError("LeRobot v3 episode metadata is missing")
    for path in files:
        table = pq.read_table(path)
        ids = table["episode_index"].to_pylist()
        lengths = table["length"].to_pylist()
        values = {
            key: []
            for feature in QUALITY_FEATURES
            for key in (f"stats/{feature}/{stat}" for stat in bool_stats(1, 1))
        }
        for episode, length in zip(ids, lengths, strict=True):
            if episode in seen or episode not in counts or counts[episode][0] != length:
                raise ValueError(f"episode metadata does not match data rows: episode {episode}")
            seen.add(episode)
            for i, feature in enumerate(QUALITY_FEATURES, start=1):
                for key, value in bool_stats(length, counts[episode][i]).items():
                    values[f"stats/{feature}/{key}"].append(value)
        table = append_columns(
            table,
            {
                k: pa.array(v, type=pa.list_(pa.int64() if k.endswith("/count") else pa.float64()))
                for k, v in values.items()
            },
        )
        pq.write_table(table, path, compression="zstd")
    if seen != set(counts):
        raise ValueError("episode metadata is missing data episodes")


def export_repo(
    repo: Path,
    output: Path,
    *,
    adapter: str = "auto",
    thresholds: Thresholds = Thresholds(),
    fk_config: Path | None = None,
    require_fk: bool = False,
    require_action_targets: bool = False,
    require_ee_targets: bool = False,
    position_threshold_m: float = 0.01,
    rotation_threshold_deg: float = 2.0,
    batch_size: int = 65536,
    progress=None,
    four_rules: dict | None = None,
) -> dict:
    repo, output = repo.resolve(), output.absolute()
    destination = output.resolve()
    if destination == repo or repo in destination.parents or destination in repo.parents:
        raise ValueError("output must be separate from the source repo and its parents")
    if output.exists() or output.is_symlink():
        raise FileExistsError(f"output already exists: {output}")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    if not all(np.isfinite(v) and v > 0 for v in (position_threshold_m, rotation_threshold_deg)):
        raise ValueError("FK thresholds must be finite and positive")
    info = read_info(repo)
    if info.get("codebase_version") != "v3.0":
        raise ValueError("annotation export currently requires LeRobot v3.0")
    if ANNOTATION_COLUMNS & set(info["features"]):
        raise ValueError("source already contains quality annotation columns")
    contract = resolve_adapter(info, adapter)
    fk = BatchFK(contract, fk_config, require_fk, position_threshold_m, rotation_threshold_deg)
    files = parquet_files(repo)
    for path in files:
        names = set(pq.ParquetFile(path).schema_arrow.names)
        if ANNOTATION_COLUMNS & names:
            raise ValueError(f"{path}: quality columns already exist")
        if not {"episode_index", "frame_index", "index"}.issubset(names):
            raise ValueError(f"{path}: v3 episode/frame/global indices are required")
    if (
        any(f.get("dtype") == "video" for f in info["features"].values())
        and not (repo / "videos").is_dir()
    ):
        raise ValueError("metadata declares video features but source videos directory is missing")
    source_paths = files + sorted(p for p in (repo / "meta").rglob("*") if p.is_file())
    original_snapshot = snapshot(source_paths)
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{output.name}.inprogress-", dir=output.parent))
    frame_writer = None
    try:
        report_root = stage / "quality"
        if four_rules is not None:
            from .four_rules import FourRules, validate_four

            if require_action_targets or require_ee_targets:
                raise ValueError("four-rules policy preserves optional target masks")
            four_rules = asdict(FourRules(**four_rules))
            signal = validate_four(
                repo,
                report_root / "signal",
                adapter=adapter,
                config=FourRules(**four_rules),
                progress=progress,
            )
        else:
            signal = validate_repo(
                repo,
                report_root / "signal",
                adapter=adapter,
                thresholds=thresholds,
                write_frames=True,
                require_action_targets=require_action_targets,
                require_ee_targets=require_ee_targets,
                progress=progress,
            )
        if progress:
            progress({"phase": "export", "frames": 0})
        reader = FrameReader(report_root / "signal/frames.parquet", batch_size)
        totals = [0, 0, 0]
        fk_failed_frames = 0
        episode_counts: dict[int, list[int]] = {}
        for path in files:
            target = stage / path.relative_to(repo)
            target.parent.mkdir(parents=True, exist_ok=True)
            writer = None
            try:
                for record in pq.ParquetFile(path).iter_batches(batch_size=batch_size):
                    table = pa.Table.from_batches([record])
                    report = reader.take(len(table))
                    for key in ("episode_index", "frame_index"):
                        if not np.array_equal(table[key].to_numpy(), report[key].to_numpy()):
                            raise ValueError(
                                f"signal report/source alignment mismatch: {path}, {key}"
                            )
                    checked, failed, details = fk.check(table)
                    fk_failed_frames += int(failed.sum())
                    valid = report["signal_quality_valid"].to_numpy() & ~failed
                    part = append_columns(table, {"quality.valid": pa.array(valid)})
                    if writer is None:
                        writer = pq.ParquetWriter(target, part.schema, compression="zstd")
                    writer.write_table(part)
                    combined = pa.table(
                        {
                            "episode_index": table["episode_index"],
                            "frame_index": table["frame_index"],
                            "index": table["index"],
                            "quality.valid": valid,
                            "fk_checked": checked,
                            "fk_failed": failed,
                            **details,
                        }
                    )
                    if frame_writer is None:
                        frame_writer = pq.ParquetWriter(
                            report_root / "frames.parquet", combined.schema, compression="zstd"
                        )
                    frame_writer.write_table(combined)
                    totals[0] += len(table)
                    totals[1] += int(valid.sum())
                    totals[2] += int(checked.sum())
                    episodes = table["episode_index"].to_numpy()
                    for episode in np.unique(episodes):
                        selected = episodes == episode
                        count = episode_counts.setdefault(int(episode), [0, 0, 0])
                        count[0] += int(selected.sum())
                        count[1] += int(valid[selected].sum())
                        count[2] += int(checked[selected].sum())
                    if progress:
                        progress(
                            {
                                "phase": "export",
                                "frames": totals[0],
                                "valid_frames": totals[1],
                                "fk_checked_frames": totals[2],
                            }
                        )
            finally:
                if writer is not None:
                    writer.close()
        reader.assert_exhausted()
        if frame_writer is not None:
            frame_writer.close()
            frame_writer = None
        if totals[0] != info["total_frames"] or len(episode_counts) != info["total_episodes"]:
            raise ValueError("source total_frames/total_episodes do not match parquet rows")
        if signal["frames"] != totals[0]:
            raise ValueError("signal report does not cover all source frames")
        if progress:
            progress({"phase": "metadata", "frames": totals[0]})
        shutil.copytree(repo / "meta", stage / "meta")
        update_episode_metadata(stage, episode_counts)
        stats_path = stage / "meta/stats.json"
        stats = json.loads(stats_path.read_text())
        for i, key in enumerate(QUALITY_FEATURES, start=1):
            stats[key] = bool_stats(totals[0], totals[i])
        stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n")
        info["features"].update(QUALITY_FEATURES)
        (stage / "meta/info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n")
        if (repo / "videos").is_dir():
            (stage / "videos").symlink_to((repo / "videos").resolve(), target_is_directory=True)
        # Preserve licenses and dataset cards; skip caches and other source directories.
        for path in repo.iterdir():
            if path.is_file() and not path.name.startswith("."):
                shutil.copy2(path, stage / path.name)
        summary = {
            "schema_version": "lerobot_quality_annotation_v1",
            "status": "complete",
            "source": str(repo),
            "output": str(output),
            "adapter": contract.name,
            "coverage": contract.coverage(),
            "policy": signal["policy"],
            "four_rules": four_rules,
            "fk_failed_frames": fk_failed_frames,
            "scope": "all_frames",
            "frame_policy": "independent_frame",
            "valid_rule": "signal_quality_valid AND no failure on any FK side with valid inputs",
            "frames": totals[0],
            "valid_frames": totals[1],
            "invalid_frames": totals[0] - totals[1],
            "fk_checked_frames": totals[2],
            "episodes": len(episode_counts),
            "fk_unavailable_reason": fk.unavailable_reason,
            "fk_config": str(fk.config_path) if fk.config_path else None,
            "thresholds": signal["thresholds"] if four_rules is not None else asdict(thresholds),
            "fk_thresholds": {
                "position_m": position_threshold_m,
                "rotation_deg": rotation_threshold_deg,
            },
            "rows_removed": 0,
            "videos": "absolute_symlink_to_source",
            "original_feature_stats": "unchanged; still describe all original frames, not valid-only rows",
            "training": "consume quality.valid explicitly; action/EE masks and temporal windows still need masking",
        }
        (report_root / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
        )
        (report_root / "episodes.json").write_text(
            json.dumps(
                {
                    str(k): {
                        "frames": v[0],
                        "valid_frames": v[1],
                        "invalid_frames": v[0] - v[1],
                        "fk_checked_frames": v[2],
                    }
                    for k, v in sorted(episode_counts.items())
                },
                indent=2,
            )
            + "\n"
        )
        if snapshot(source_paths) != original_snapshot or parquet_files(repo) != files:
            raise ValueError(
                "source changed while checking/exporting; annotated output was not published"
            )
        # Reserve destination exclusively, then replace only that empty directory.
        output.mkdir()
        try:
            os.rename(stage, output)
        except Exception:
            output.rmdir()
            raise
        if progress:
            progress(
                {
                    "phase": "complete",
                    "frames": totals[0],
                    "valid_frames": totals[1],
                    "fk_checked_frames": totals[2],
                }
            )
        return summary
    except Exception as error:
        if frame_writer is not None:
            frame_writer.close()
        (stage / "FAILED.json").write_text(
            json.dumps({"error": str(error), "source": str(repo)}, indent=2) + "\n"
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--adapter", default="auto")
    parser.add_argument(
        "--four-rules-config", type=Path, help="JSON FourRules policy; omitted retains legacy rules"
    )
    parser.add_argument("--fk-config", type=Path)
    parser.add_argument("--require-fk", action="store_true")
    parser.add_argument("--require-action-targets", action="store_true")
    parser.add_argument("--require-ee-targets", action="store_true")
    parser.add_argument("--batch-size", type=int, default=65536)
    parser.add_argument("--joint-step-rad", type=float, default=0.35)
    parser.add_argument("--ee-position-step-m", type=float, default=0.10)
    parser.add_argument("--ee-rotation-step-deg", type=float, default=30.0)
    parser.add_argument("--fk-position-threshold-m", type=float, default=0.01)
    parser.add_argument("--fk-rotation-threshold-deg", type=float, default=2.0)
    args = parser.parse_args()
    summary = export_repo(
        args.repo,
        args.output,
        adapter=args.adapter,
        fk_config=args.fk_config,
        require_fk=args.require_fk,
        require_action_targets=args.require_action_targets,
        require_ee_targets=args.require_ee_targets,
        batch_size=args.batch_size,
        thresholds=Thresholds(
            args.joint_step_rad, args.ee_position_step_m, args.ee_rotation_step_deg
        ),
        position_threshold_m=args.fk_position_threshold_m,
        rotation_threshold_deg=args.fk_rotation_threshold_deg,
        four_rules=(
            json.loads(args.four_rules_config.read_text()) if args.four_rules_config else None
        ),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
