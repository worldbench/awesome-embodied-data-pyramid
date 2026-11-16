"""Run a reviewed source/output manifest with bounded repository-level parallelism.

Outputs retain their repository boundaries. Completed outputs can be resumed;
failed jobs are reported and never silently treated as successful.
"""

from __future__ import annotations
import argparse
from collections import deque
from concurrent.futures import ProcessPoolExecutor, wait, FIRST_COMPLETED
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
import fcntl
import json
import multiprocessing
import os
from pathlib import Path
import time
import traceback


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def prepare(plan):
    if plan.get("four_rules") is not None:
        from dataclasses import asdict
        from .four_rules import FourRules

        plan = {**plan, "four_rules": asdict(FourRules(**plan["four_rules"]))}
    source_root, output_root = (
        Path(plan["input_root"]).resolve(),
        Path(plan["output_root"]).resolve(),
    )
    if (
        source_root == output_root
        or source_root in output_root.parents
        or output_root in source_root.parents
    ):
        raise ValueError("input and output roots must be separate")
    seen_source, jobs = set(), []
    for i, row in enumerate(plan["repositories"]):
        source, output = Path(row["source"]).resolve(), Path(row["output"]).resolve()
        expected = output_root / source.relative_to(source_root)
        if output != expected or source in seen_source:
            raise ValueError(f"duplicate or unexpected destination: {source} -> {output}")
        seen_source.add(source)
        info = json.loads((source / "meta/info.json").read_text())
        if (info["total_frames"], info["total_episodes"]) != (row["frames"], row["episodes"]):
            raise ValueError(f"source metadata changed since plan: {source}")
        jobs.append(
            {
                **row,
                "four_rules": plan.get("four_rules"),
                "source": str(source),
                "output": str(output),
                "job_id": f"{i:04d}",
            }
        )
    if len(jobs) != plan["selected_repositories"]:
        raise ValueError("manifest repository count mismatch")
    return sorted(jobs, key=lambda j: -j["frames"])


def worker_init():
    import pyarrow as pa

    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)


def existing_result(row):
    output = Path(row["output"])
    if not output.exists():
        return None
    summary = json.loads((output / "quality/summary.json").read_text())
    info = json.loads((output / "meta/info.json").read_text())
    expected_summary = {
        "status": "complete",
        "source": row["source"],
        "frames": row["frames"],
        "adapter": row["adapter"],
        "scope": "all_frames",
        "rows_removed": 0,
        "frame_policy": "independent_frame",
        "four_rules": row.get("four_rules"),
    }
    expected_counts = {"total_frames": row["frames"], "total_episodes": row["episodes"]}
    summary_matches = all(summary.get(key) == value for key, value in expected_summary.items())
    counts_match = all(info.get(key) == value for key, value in expected_counts.items())
    features = info["features"]
    if not (
        summary_matches
        and counts_match
        and "quality.valid" in features
        and "quality.fk_checked" not in features
    ):
        raise ValueError(f"existing output does not match the current plan/policy: {output}")
    return summary


def run_job(row, run_dir, batch_size):
    from .export import export_repo

    run_dir = Path(run_dir)
    state_path = run_dir / "jobs" / f"{row['job_id']}.json"
    started = time.time()
    state = {
        **row,
        "pid": os.getpid(),
        "started_at": now(),
        "started_unix": started,
        "phase": "starting",
        "phase_frames": 0,
        "phase_started_unix": started,
        "phase_durations": {},
    }
    last_write = 0.0

    def progress(event):
        nonlocal last_write
        current = time.time()
        phase = event["phase"]
        changed = phase != state["phase"]
        if changed:
            state["phase_durations"][state["phase"]] = current - state["phase_started_unix"]
            state["phase_started_unix"] = current
        state.update(
            phase=phase,
            phase_frames=event["frames"],
            updated_at=now(),
            updated_unix=current,
            elapsed_seconds=current - started,
        )
        for key in ["valid_frames", "fk_checked_frames"]:
            if key in event:
                state[key] = event[key]
        if changed or current - last_write >= 5:
            save(state_path, state)
            last_write = current

    save(state_path, state)
    with (run_dir / "jobs" / f"{row['job_id']}.log").open("a", buffering=1) as log, redirect_stdout(
        log
    ), redirect_stderr(log):
        try:
            summary = existing_result(row)
            resumed = summary is not None
            if summary is None:
                summary = export_repo(
                    Path(row["source"]),
                    Path(row["output"]),
                    adapter=row["adapter"],
                    batch_size=batch_size,
                    progress=progress,
                    four_rules=row.get("four_rules"),
                )
            progress(
                {
                    "phase": "complete",
                    "frames": summary["frames"],
                    "valid_frames": summary["valid_frames"],
                    "fk_checked_frames": summary["fk_checked_frames"],
                }
            )
            state["resumed_existing"] = resumed
            save(state_path, state)
            return {
                "job_id": row["job_id"],
                "status": "complete",
                "frames": summary["frames"],
                "valid_frames": summary["valid_frames"],
                "invalid_frames": summary["invalid_frames"],
                "fk_checked_frames": summary["fk_checked_frames"],
                "elapsed_seconds": time.time() - started,
                "resumed_existing": resumed,
                "source": row["source"],
                "output": row["output"],
                "adapter": row["adapter"],
            }
        except Exception as error:
            traceback.print_exc()
            state.update(
                phase="failed", error=str(error), updated_at=now(), updated_unix=time.time()
            )
            save(state_path, state)
            return {
                "job_id": row["job_id"],
                "status": "failed",
                "source": row["source"],
                "output": row["output"],
                "error": str(error),
                "frames": row["frames"],
            }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=65536)
    args = parser.parse_args()
    if args.workers < 1 or args.batch_size < 1:
        raise ValueError("workers and batch-size must be positive")
    for name in [
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "VECLIB_MAXIMUM_THREADS",
    ]:
        os.environ[name] = "1"
    args.run_dir.mkdir(parents=True, exist_ok=True)
    (args.run_dir / "jobs").mkdir(exist_ok=True)
    lock = (args.run_dir / "batch.lock").open("a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("another batch coordinator already holds this run lock")
    plan = json.loads(args.plan.read_text())
    jobs = prepare(plan)
    pending = deque(jobs)
    results = []
    started = time.time()
    save(
        args.run_dir / "execution.json",
        {
            "started_at": now(),
            "started_unix": started,
            "pid": os.getpid(),
            "workers": args.workers,
            "batch_size": args.batch_size,
            "plan": str(args.plan.resolve()),
            "total_repositories": len(jobs),
            "total_frames": sum(j["frames"] for j in jobs),
            "order": "largest repositories first",
            "parallelism": "one process per active repository; one Arrow/BLAS thread per process",
        },
    )
    total_frames = sum(j["frames"] for j in jobs)

    def snapshot(active):
        running = []
        for job in active.values():
            path = args.run_dir / "jobs" / f"{job['job_id']}.json"
            if path.exists():
                try:
                    running.append(json.loads(path.read_text()))
                except (OSError, json.JSONDecodeError):
                    pass
        completed = [r for r in results if r["status"] == "complete"]
        failed = [r for r in results if r["status"] == "failed"]
        completed_frames = sum(r["frames"] for r in completed)
        signal = completed_frames + sum(
            (
                min(r.get("phase_frames", 0), r["frames"])
                if r["phase"] == "signal"
                else r["frames"] if r["phase"] in ["export", "metadata", "complete"] else 0
            )
            for r in running
        )
        written = completed_frames + sum(
            (
                min(r.get("phase_frames", 0), r["frames"])
                if r["phase"] == "export"
                else r["frames"] if r["phase"] in ["metadata", "complete"] else 0
            )
            for r in running
        )
        state = {
            "updated_at": now(),
            "updated_unix": time.time(),
            "elapsed_seconds": time.time() - started,
            "status": (
                "running"
                if active or pending
                else "completed_with_errors" if failed else "complete"
            ),
            "workers": args.workers,
            "total_repositories": len(jobs),
            "total_frames": total_frames,
            "completed_repositories": len(completed),
            "failed_repositories": len(failed),
            "pending_repositories": len(pending),
            "active_repositories": len(active),
            "completed_frames": completed_frames,
            "signal_frames_processed": signal,
            "export_frames_written": written,
            "two_pass_work_percent": (
                None
                if plan.get("four_rules") is not None
                else 100 * (signal + written) / (2 * total_frames)
            ),
            "invalid_frames_in_completed_repos": sum(r["invalid_frames"] for r in completed),
            "running": running,
            "failures": failed,
        }
        save(args.run_dir / "status.json", state)
        print(
            json.dumps(
                {k: v for k, v in state.items() if k not in ["running", "failures"]},
                ensure_ascii=False,
            ),
            flush=True,
        )

    with (args.run_dir / "results.jsonl").open("a", buffering=1) as records:
        with ProcessPoolExecutor(
            max_workers=args.workers,
            mp_context=multiprocessing.get_context("spawn"),
            initializer=worker_init,
        ) as pool:
            active = {}

            def fill():
                while pending and len(active) < args.workers:
                    job = pending.popleft()
                    active[pool.submit(run_job, job, str(args.run_dir), args.batch_size)] = job

            fill()
            snapshot(active)
            last_snapshot = time.time()
            while active:
                done, _ = wait(active, timeout=15, return_when=FIRST_COMPLETED)
                for future in done:
                    job = active.pop(future)
                    try:
                        result = future.result()
                    except Exception as error:
                        result = {
                            "job_id": job["job_id"],
                            "status": "failed",
                            "frames": job["frames"],
                            "source": job["source"],
                            "output": job["output"],
                            "error": repr(error),
                        }
                    results.append(result)
                    records.write(json.dumps(result, ensure_ascii=False) + "\n")
                fill()
                if done or time.time() - last_snapshot >= 15:
                    snapshot(active)
                    last_snapshot = time.time()
    snapshot({})
    if any(r["status"] == "failed" for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
