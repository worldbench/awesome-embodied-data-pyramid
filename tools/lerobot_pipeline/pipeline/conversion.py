"""Conversion plans preserve the released engines and explicit recovery policies."""

import os
from pathlib import Path
from .release import ENGINES, QUALITY_SRC, load_profile


def build_steps(dataset, raw, output, work, python, workers=None):
    cfg = load_profile()["datasets"][dataset]
    src = Path(raw) / cfg["source"]
    output, work = Path(output), Path(work)
    env = {
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "PYTHONPATH": os.pathsep.join([str(ENGINES), str(QUALITY_SRC)]),
        "HF_HUB_OFFLINE": "1",
        "BETA_AGGREGATE_BY_TASK": "0",
    }
    steps = []

    def py(rel, args, extra=None):
        steps.append(
            {
                "command": [str(python), str(ENGINES / rel), *map(str, args)],
                "env": {**env, **(extra or {})},
            }
        )

    if dataset == "beta":
        w = work / "beta"
        py(
            "agibotworld_beta_2lerobot/prepare_raw.py",
            ["--source", src, "--work", w, "--workers", "4"],
        )
        for kind in ("gripper", "dexhand"):
            py(
                "agibotworld_beta_2lerobot/convert_agibotworld_beta.py",
                [
                    "--src-path",
                    w / "staged",
                    "--output-path",
                    output / "AgiBotWorld_Beta_v3" / kind,
                    "--resume-dir",
                    w / kind / "logs",
                    "--eef-type",
                    kind,
                    "--workers",
                    workers or 16,
                    "--episodes-per-task",
                    1,
                    "--invalid-episode-policy",
                    "error",
                    "--resume",
                ],
                {
                    "BETA_AGGREGATE_BY_TASK": "1",
                    "BETA_AGGREGATE_WORKERS": "4",
                    "LEROBOT_VIDEO_MERGE_WORKERS": "2",
                    "AGIBOT_VIDEO_DECODE_THREADS": "1",
                    "LEROBOT_TASK_CACHE": str(w / "task-cache"),
                    "AGIBOT_EMPTY_ACTION_AUDIT_DIR": str(w / "empty_action_audit"),
                },
            )
    elif dataset == "abc":
        steps.append(
            {
                "command": ["bash", str(ENGINES / "abc130k2lerobot/convert_fast.sh")],
                "env": {
                    **env,
                    "MODE": "full",
                    "PYTHON_BIN": str(python),
                    "SRC_ROOT": str(src),
                    "OUTPUT_BASE": str(output),
                    "WORK_ROOT": str(work / "abc"),
                    "WORKERS": str(workers or 8),
                    "EPISODES_PER_TASK": "16",
                    "RESUME_AGGREGATION": "1",
                },
            }
        )
    elif dataset == "agibot2026":
        py(
            "agibotworld2026_2lerobot/run_collection.py",
            [
                "--engine",
                "fast",
                "--mode",
                "full",
                "--source-root",
                src,
                "--output-base",
                output,
                "--work-root",
                work / "agibot2026",
                "--workers",
                workers or 8,
                "--io-workers",
                4,
                "--camera-workers",
                2,
                "--decoder-threads",
                1,
                "--extraction-threads",
                2,
            ],
        )
    elif dataset == "robomind":
        args = [
            "--mode",
            "full",
            "--source",
            src,
            "--output-base",
            output,
            "--work",
            work / "robomind",
            "--scratch",
            work / "robomind-scratch",
            "--workers",
            workers or 12,
            "--decode-threads",
            2,
            "--encoder-threads",
            1,
            "--shard-episodes",
            16,
        ]
        args += ["--embodiments", *cfg["embodiments"]]
        for name in cfg["exclude_tasks"]:
            args += ["--exclude-task", name]
        py("robomind2lerobot/robomind_fast.py", args, {"HDF5_USE_FILE_LOCKING": "FALSE"})
    elif dataset == "galaxea":
        for kind in ("r1lite", "r1pro"):
            args = [
                "--source-root",
                src,
                "--source-kind",
                "archive",
                "--archive-subdir",
                "lerobot_opensource",
                "--robot-type",
                kind,
                "--output-path",
                output / f"Galaxea_{kind}_v3",
                "--work-root",
                work / "galaxea" / kind,
                "--workers",
                workers or 8,
                "--keep-parts",
                "--resume-incomplete",
            ]
            if kind == "r1lite":
                for name in cfg["exclude_lite"] + cfg["pro_sources"]:
                    args += ["--exclude", name]
            else:
                for name in cfg["pro_sources"]:
                    args += ["--include", name]
            py(
                "opengalaxea2lerobot/convert_opengalaxea.py",
                args,
                {"LEROBOT_VIDEO_MERGE_WORKERS": "4"},
            )
    elif dataset == "interndata":
        args = [
            "--source",
            src,
            "--output",
            output / "InternData_A1_v3",
            "--work",
            work / "interndata",
            "--workers",
            workers or 4,
        ]
        for name in cfg["exclude_jobs"]:
            args += ["--exclude-job", name]
        for job, roots in cfg.get("job_roots", {}).items():
            args += ["--job-roots", job + "=" + ",".join(roots)]
        py("interndata_a1_2lerobot/run_full.py", args)
    return steps
