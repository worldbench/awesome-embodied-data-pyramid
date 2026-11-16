"""Single configurable entry point: plan, convert, clean, verify, and run both stages."""

from pathlib import Path
from datetime import datetime, timezone
from contextlib import contextmanager, ExitStack
import argparse
import fcntl
import json
import os
import shutil
import subprocess
import sys

from .release import ROOT, ENGINES, QUALITY_SRC, load_profile, load_manifest, selected_rows, verify
from .conversion import build_steps


def write_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def load_settings(path):
    path = Path(path).resolve()
    raw = json.loads(path.read_text())
    settings = {}
    for key in ("raw_root", "converted_root", "cleaned_root", "work_root"):
        if not raw.get(key):
            raise ValueError(f"Config requires {key}")
        p = Path(raw[key]).expanduser()
        settings[key] = (path.parent / p).resolve() if not p.is_absolute() else p.resolve()
    values = list(settings.values())
    for i, a in enumerate(values):
        for b in values[i + 1 :]:
            if a == b or a in b.parents or b in a.parents:
                raise ValueError(
                    "raw, converted, cleaned and work roots must be separate, non-overlapping directories"
                )
    for key, default in [
        ("conversion_workers", 8),
        ("cleaning_workers", 16),
        ("batch_size", 65536),
    ]:
        value = raw.get(key, default)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{key} must be a positive integer")
        settings[key] = value
    for key, default in [("ffmpeg", "ffmpeg"), ("python", sys.executable)]:
        value = raw.get(key, default)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Invalid {key}")
        settings[key] = (
            str((path.parent / value).resolve())
            if not Path(value).is_absolute() and len(Path(value).parts) > 1
            else value
        )
    settings["four_rules"] = raw.get("four_rules")
    if settings["four_rules"] is not None:
        from dataclasses import asdict

        sys.path.insert(0, str(QUALITY_SRC))
        from lerobot_quality.four_rules import FourRules

        settings["four_rules"] = asdict(FourRules(**settings["four_rules"]))
    return settings


def runtime_env(settings, *, check_binaries=True):
    binary = shutil.which(settings["ffmpeg"])
    if check_binaries and not binary:
        raise ValueError("ffmpeg is unavailable; set ffmpeg in config or put it on PATH")
    env = {
        **os.environ,
        "PYTHONPATH": os.pathsep.join(map(str, [ENGINES, QUALITY_SRC, ROOT])),
        "HF_HUB_OFFLINE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    if binary:
        env["FFMPEG_BIN"] = binary
        env["PATH"] = str(Path(binary).parent) + os.pathsep + env.get("PATH", "")
    if check_binaries and not shutil.which("ffprobe", path=env["PATH"]):
        raise ValueError("ffprobe is required on PATH alongside ffmpeg")
    return env


def doctor(settings, names, *, conversion=True):
    env = runtime_env(settings, check_binaries=conversion)
    entrypoints = {
        "beta": "agibotworld_beta_2lerobot/convert_agibotworld_beta.py",
        "abc": "abc130k2lerobot/abc_mcap_fast.py",
        "agibot2026": "agibotworld2026_2lerobot/run_collection.py",
        "robomind": "robomind2lerobot/robomind_fast.py",
        "galaxea": "opengalaxea2lerobot/convert_opengalaxea.py",
        "interndata": "interndata_a1_2lerobot/run_full.py",
    }
    commands = []
    if conversion:
        commands.extend(
            (name, [settings["python"], str(ENGINES / entrypoints[name]), "--help"])
            for name in names
        )
        commands.append(("ffmpeg", [env["FFMPEG_BIN"], "-version"]))
        commands.append(("ffprobe", ["ffprobe", "-version"]))
    commands.append(("quality", [settings["python"], "-m", "lerobot_quality.export", "--help"]))
    for name, command in commands:
        r = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(f"{name} environment check failed:\n{r.stdout}\n{r.stderr}")
        print(f"Environment OK: {name}", flush=True)
    return env


def create_plan(settings, names):
    raw, converted, cleaned, work = (
        settings[k] for k in ("raw_root", "converted_root", "cleaned_root", "work_root")
    )
    conversion = {
        name: build_steps(
            name,
            raw,
            converted,
            work / "conversion",
            settings["python"],
            settings["conversion_workers"],
        )
        for name in names
    }
    rows = selected_rows(names)
    cleaning = {
        "four_rules": settings.get("four_rules"),
        "input_root": str(converted),
        "output_root": str(cleaned),
        "selected_repositories": len(rows),
        "repositories": [
            {
                **r,
                "source": str(converted / r["relative_path"]),
                "output": str(cleaned / r["relative_path"]),
            }
            for r in rows
        ],
        "policy": {
            "retain_all_frames": True,
            "added_data_columns": ["quality.valid"],
            "videos": "symlink_to_source",
            "fk_missing_observations": "skip; record reason in reports, not as failure",
            "require_action_targets": False,
            "require_ee_targets": False,
        },
    }
    return {
        "release": load_profile()["version"],
        "roots": {
            k: str(settings[k]) for k in ("raw_root", "converted_root", "cleaned_root", "work_root")
        },
        "datasets": names,
        "conversion": conversion,
        "cleaning": cleaning,
    }


def identity(settings):
    return {
        "release": load_profile()["version"],
        "roots": {
            k: str(settings[k]) for k in ("raw_root", "converted_root", "cleaned_root", "work_root")
        },
        "policies": load_profile(),
        "manifest": load_manifest(),
        "four_rules": settings.get("four_rules"),
    }


def check_owner(root, expected, resume, *, ignore_lock=False):
    root = Path(root)
    marker = root / ".pipeline-owner.json"
    if marker.exists():
        if not resume:
            raise ValueError(f"{root}: already owned; use --resume")
        if json.loads(marker.read_text()) != expected:
            raise ValueError(f"{root}: run identity/release changed; use new roots")
    elif root.exists() and any(
        p.name != ".pipeline.lock" or not ignore_lock for p in root.iterdir()
    ):
        raise ValueError(f"{root}: refusing nonempty unowned destination")


@contextmanager
def owned_run(settings, stages, resume):
    expected = identity(settings)
    work = settings["work_root"]
    roots = [work] + [settings[f"{stage}_root"] for stage in stages]
    # Validate every root before creating or changing any destination.
    for root in roots:
        check_owner(root, expected, resume, ignore_lock=root == work)
    # Lock every destination before rechecking ownership. Separate work roots
    # cannot concurrently claim the same converted/cleaned destination.
    with ExitStack() as stack:
        for root in sorted(roots):
            root.parent.mkdir(parents=True, exist_ok=True)
            lock = stack.enter_context((root.parent / f".{root.name}.pipeline.lock").open("a"))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        for root in roots:
            check_owner(root, expected, resume, ignore_lock=root == work)
        for root in roots:
            root.mkdir(parents=True, exist_ok=True)
            write_json(root / ".pipeline-owner.json", expected)
        yield


def execute_conversion(settings, names, plan, env):
    work = settings["work_root"] / "conversion"
    work.mkdir(exist_ok=True)
    for name in names:
        done = work / f"{name}.complete.json"
        if done.exists():
            result = verify(settings["converted_root"], [name])
            print("Already verified:", name, flush=True)
            continue
        for idx, step in enumerate(plan["conversion"][name]):
            if name == "galaxea":
                target = settings["converted_root"] / (
                    "Galaxea_r1lite_v3" if idx == 0 else "Galaxea_r1pro_v3"
                )
                if (target / "meta/unified_action_space.json").exists():
                    continue
            print(f"RUN conversion {name} step {idx+1}", flush=True)
            with (work / f"{name}-{idx}.log").open("a") as log:
                subprocess.run(
                    step["command"],
                    cwd=ENGINES,
                    env={**env, **step["env"]},
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            if name == "beta" and idx == 0:
                counts = json.loads((work / "beta/expected_counts.json").read_text())
                audit = json.loads((work / "beta/preparation_audit.json").read_text())
                if (
                    counts != {"gripper": 147838, "dexhand": 5851}
                    or audit["excluded_episodes"] != 12707
                ):
                    raise ValueError(
                        "Beta raw inventory differs from accepted release; inspect preparation audit"
                    )
        result = verify(settings["converted_root"], [name])
        write_json(done, {"completed_at": datetime.now(timezone.utc).isoformat(), **result})
        print("VERIFIED conversion", name, result["repositories"], flush=True)


def execute_cleaning(settings, names, plan, env):
    # Do not require skipped FK to succeed; availability is decided by the adapter and masks.
    verify(settings["converted_root"], names)
    work = settings["work_root"] / "cleaning" / ("_".join(sorted(names)))
    work.mkdir(parents=True, exist_ok=True)
    write_json(work / "plan.json", plan["cleaning"])
    command = [
        settings["python"],
        "-u",
        "-m",
        "lerobot_quality.batch_export",
        "--plan",
        str(work / "plan.json"),
        "--run-dir",
        str(work),
        "--workers",
        str(settings["cleaning_workers"]),
        "--batch-size",
        str(settings["batch_size"]),
    ]
    print("RUN cleaning", len(plan["cleaning"]["repositories"]), "repositories", flush=True)
    with (work / "coordinator.log").open("a") as log:
        subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = verify(
        settings["cleaned_root"], names, cleaned=True, source_root=settings["converted_root"]
    )
    write_json(
        work / "verified.json", {"completed_at": datetime.now(timezone.utc).isoformat(), **result}
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)


def main(argv=None):
    if not __debug__:
        raise SystemExit("Do not use python -O: engine integrity assertions must be enabled")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["plan", "doctor", "convert", "clean", "run", "verify"])
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--dataset", choices=["all", *load_profile()["datasets"]], default="all")
    p.add_argument(
        "--execute",
        action="store_true",
        help="Launch conversion/cleaning; otherwise show plan only",
    )
    p.add_argument(
        "--resume", action="store_true", help="Resume only matching pipeline-owned destinations"
    )
    p.add_argument(
        "--kind", choices=["converted", "cleaned"], default="cleaned", help="verify stage"
    )
    p.add_argument(
        "--allow-extra",
        action="store_true",
        help="verify only: permit unrelated repositories alongside selected release paths",
    )
    a = p.parse_args(argv)
    if a.allow_extra and a.command != "verify":
        p.error("--allow-extra is only for read-only verification")
    s = load_settings(a.config)
    names = list(load_profile()["datasets"]) if a.dataset == "all" else [a.dataset]
    if a.command == "doctor":
        doctor(s, names)
        return
    if a.command == "verify":
        print(
            json.dumps(
                verify(
                    s[a.kind + "_root"],
                    names,
                    cleaned=a.kind == "cleaned",
                    source_root=s["converted_root"],
                    check_inventory=not a.allow_extra,
                ),
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    plan = create_plan(s, names)
    if a.command == "plan" or not a.execute:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return
    conversion = a.command in ("convert", "run")
    cleaning = a.command in ("clean", "run")
    if conversion:
        for name in names:
            if not (s["raw_root"] / load_profile()["datasets"][name]["source"]).is_dir():
                raise ValueError(f"Missing raw directory for {name}")
    else:
        verify(s["converted_root"], names)
    stages = (["converted"] if conversion else []) + (["cleaned"] if cleaning else [])
    # Ownership checks precede environment checks and all writes.
    for root in [s["work_root"]] + [s[x + "_root"] for x in stages]:
        check_owner(root, identity(s), a.resume, ignore_lock=root == s["work_root"])
    env = doctor(s, names, conversion=conversion)
    with owned_run(s, stages, a.resume):
        write_json(s["work_root"] / "plan.json", plan)
        if conversion:
            execute_conversion(s, names, plan, env)
        if cleaning:
            execute_cleaning(s, names, plan, env)


if __name__ == "__main__":
    main()
