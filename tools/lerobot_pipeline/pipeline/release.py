"""Release contract and path-safe inventory verification."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json
import os
import re

ROOT = Path(__file__).resolve().parents[1]
ENGINES = ROOT / "converters"
QUALITY_SRC = ROOT / "quality" / "src"


def load_profile():
    return json.loads((ROOT / "configs/release.json").read_text())


def load_manifest():
    return json.loads((ROOT / "manifests/repositories.json").read_text())


def dataset_infos(root):
    for current, dirs, _files in os.walk(root):
        current = Path(current)
        info = current / "meta/info.json"
        if info.is_file():
            yield info
            dirs.clear()
        else:
            dirs[:] = sorted(
                d
                for d in dirs
                if not d.startswith(".")
                and not any(x in d for x in (".partial", ".backup", ".inprogress"))
                and d not in ("data", "videos", "images", "meta")
            )


def relative_path(value):
    p = Path(value)
    if p.is_absolute() or ".." in p.parts or str(p) in ("", "."):
        raise ValueError(f"Unsafe manifest path: {value}")
    return p


def selected_rows(names):
    manifest = load_manifest()
    rows = [r for r in manifest["repositories"] if r["family"] in names]
    paths = [r["relative_path"] for r in rows]
    for p in paths:
        relative_path(p)
    if len(set(paths)) != len(paths):
        raise ValueError("Duplicate manifest repository")
    return rows


def feature_schema(features):
    return {k: {f: v.get(f) for f in ("dtype", "shape", "names")} for k, v in features.items()}


def discover(root, family):
    root = Path(root)
    cfg = load_profile()["datasets"][family]
    if family == "beta":
        return {
            str(p.parent.parent.relative_to(root))
            for name in cfg["outputs"]
            for p in (root / name).glob("task_*/meta/info.json")
            if re.fullmatch(r"task_\d+", p.parent.parent.name)
        }
    if family == "interndata":
        return {
            str(p.parent.parent.relative_to(root)) for p in dataset_infos(root / "InternData_A1_v3")
        }
    if family == "robomind":
        return {
            str(p.parent.parent.relative_to(root))
            for p in root.glob("RoboMIND_v12_*/meta/info.json")
        }
    if family == "agibot2026":
        return {
            str(p.parent.parent.relative_to(root))
            for p in root.glob("AgiBotWorld2026_*/meta/info.json")
        }
    return {name for name in cfg["outputs"] if (root / name / "meta/info.json").is_file()}


def verify(root, names, *, cleaned=False, source_root=None, check_inventory=True):
    """Check exact release paths/counts/schema; do not decode videos or rerun cleaning."""
    root = Path(root).resolve()
    manifest = load_manifest()
    rows = selected_rows(names)

    def one(r):
        p = root / relative_path(r["relative_path"])
        info = json.loads((p / "meta/info.json").read_text())
        for key in ("total_frames", "total_episodes", "fps", "robot_type"):
            expected = r[{"total_frames": "frames", "total_episodes": "episodes"}.get(key, key)]
            if info.get(key) != expected:
                raise ValueError(f"{p}: {key} differs: {info.get(key)!r} != {expected!r}")
        if info.get("codebase_version") != "v3.0":
            raise ValueError(f"{p}: requires LeRobot v3.0")
        fields = dict(info["features"])
        if cleaned:
            quality = fields.pop("quality.valid", None)
            if not quality or {k: quality.get(k) for k in ("dtype", "shape", "names")} != {
                "dtype": "bool",
                "shape": [1],
                "names": None,
            }:
                raise ValueError(f"{p}: quality.valid missing or wrong type")
            q = json.loads((p / "quality/summary.json").read_text())
            if (
                q.get("status") != "complete"
                or q.get("frames") != r["frames"]
                or q.get("rows_removed") != 0
                or q.get("adapter") != r["adapter"]
                or q.get("scope") != "all_frames"
                or q.get("frame_policy") != "independent_frame"
                or q.get("valid_frames", 0) + q.get("invalid_frames", 0) != r["frames"]
            ):
                raise ValueError(f"{p}: incomplete/incompatible quality result")
            if (
                source_root is not None
                and Path(q.get("source", "")).resolve()
                != (Path(source_root) / r["relative_path"]).resolve()
            ):
                raise ValueError(f"{p}: quality source identity differs")
            if not (p / "videos").is_symlink() or not (p / "videos").is_dir():
                raise ValueError(f"{p}: broken/non-symlink videos")
            if (
                source_root is not None
                and (p / "videos").resolve()
                != (Path(source_root) / r["relative_path"] / "videos").resolve()
            ):
                raise ValueError(f"{p}: wrong video symlink target")
        if feature_schema(fields) != manifest["schemas"][r["schema_id"]]:
            raise ValueError(f"{p}: schema differs from release")
        if not (p / "data").is_dir() or not (p / "meta/episodes").is_dir():
            raise ValueError(f"{p}: missing data/episode metadata")
        if not cleaned and r["family"] == "beta" and not (p / "TASK_COMPLETE.json").is_file():
            raise ValueError(f"{p}: unpublished Beta task")
        if r["family"] == "interndata" and not (p / "meta/conversion.json").is_file():
            raise ValueError(f"{p}: unpublished InternData task")
        return r

    with ThreadPoolExecutor(max_workers=8) as pool:
        checked = list(pool.map(one, rows))
    if check_inventory:
        for family in names:
            actual = discover(root, family)
            expected = {r["relative_path"] for r in rows if r["family"] == family}
            if actual != expected:
                raise ValueError(
                    f"{family}: release inventory differs; missing={sorted(expected-actual)[:8]}, extra={sorted(actual-expected)[:8]}"
                )
    return {
        "repositories": len(checked),
        "episodes": sum(r["episodes"] for r in checked),
        "frames": sum(r["frames"] for r in checked),
        "hours": sum(r["frames"] / r["fps"] / 3600 for r in checked),
        "kind": "cleaned" if cleaned else "converted",
        "validation": "exact release inventory, metadata schema/counts and publication markers; not full video decoding",
    }
