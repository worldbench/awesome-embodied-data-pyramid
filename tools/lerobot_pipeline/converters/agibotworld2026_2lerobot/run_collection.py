#!/usr/bin/env python3
"""Run a bounded smoke review or an explicitly requested full collection conversion."""
from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import os
import shutil
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from agibotworld2026_2lerobot.convert_agibotworld2026 import (
    ConversionConfig, SourceUnit, convert_source, discover_sources,
)
from agibotworld2026_2lerobot.source_io import prepare_one_episode


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def source_size(unit):
    """Cheap archive weight for scheduling; do not scan extracted video trees."""
    path = Path(unit.source)
    if unit.kind == "archive":
        return path.stat().st_size
    if unit.kind == "packed_simulation":
        from agibotworld2026_2lerobot.source_io import split_parts
        return sum(p.stat().st_size for key in ("meta", "data", "videos") for p in split_parts(path, key))
    return 0


def largest_first(units):
    # Start longer jobs early so large archives do not form a serial tail.
    # Final aggregation still sorts by source path, preserving episode order.
    return sorted(units, key=lambda unit: (-source_size(unit), unit.output_relative))


def smoke_selection(units):
    """Cover real imitation, interaction, RL expert, RL feedback and simulation."""
    pools = defaultdict(list)
    for unit in units:
        path = Path(unit.source)
        if unit.kind == "packed_simulation":
            pools["simulation"].append(unit)
        elif unit.kind == "archive":
            group = Path(unit.output_relative).parts[0]
            if group == "ReinforcementLearning":
                group += "_feedback" if any(x in path.parts for x in ("HG-DAgger", "Rollout", "PolicyRollout")) else "_expert"
            pools[group].append(unit)
    required = {"ImitationLearning", "RichInteraction", "ReinforcementLearning_expert", "ReinforcementLearning_feedback", "simulation"}
    if required - pools.keys():
        raise ValueError(f"Missing smoke coverage groups: {required - pools.keys()}")
    def size(unit):
        path = Path(unit.source)
        return sum(p.stat().st_size for p in path.glob("*.tar.gz.*")) if path.is_dir() else path.stat().st_size
    return [min(pools[key], key=size) for key in sorted(pools)]


def dataset_name(info):
    # Do not remove or invent cameras/reward fields to force incompatible
    # leaves into one LeRobot repository. Hash its post-conversion contract.
    contract = {"fps": info["fps"], "robot_type": info["robot_type"], "features": {}}
    for key, value in sorted(info["features"].items()):
        feature = {k: value[k] for k in ("dtype", "shape", "names", "video_info", "info") if k in value}
        # LeRobot reader initialization adds encoder/runtime defaults to info.
        # They do not change the stored feature contract or dataset identity.
        runtime_options = {"video.crf", "video.extra_options", "video.video_backend", "video.g",
                           "video.fast_decode", "video.preset"}
        for metadata in ("video_info", "info"):
            if metadata in feature:
                feature[metadata] = {k: v for k, v in feature[metadata].items()
                                     if k not in runtime_options and v is not None}
        contract["features"][key] = feature
    label = "rl" if "reward" in info["features"] else "simulation" if "ts" in info["features"] else "real"
    digest = hashlib.sha256(json.dumps(contract, sort_keys=True).encode()).hexdigest()[:10]
    return f"AgiBotWorld2026_{label}_{digest}"


def aggregate_output(parts, output, engine="classic"):
    if engine == "fast":
        from agibotworld2026_2lerobot.fast_aggregate import aggregate_fast
        return aggregate_fast(parts, output)
    import inspect
    from lerobot.datasets.aggregate import aggregate_datasets
    from generic_converter.metadata import annotate_dataset_info

    if "concatenate_data" in inspect.signature(aggregate_datasets).parameters:
        # Current LeRobot already normalizes numeric arrays and offsets every
        # index statistic. Avoid the legacy project monkey patch on this API.
        aggregate_datasets(repo_ids=[p.name for p in parts], roots=parts,
                           aggr_repo_id=output.name, aggr_root=output)
        annotate_dataset_info(output)
    else:
        from generic_converter import aggregate_roots
        aggregate_roots(parts, output, aggr_repo_id=output.name)


def source_job(unit, effective, config, fixture, engine, settings, log_root):
    """One worker owns one leaf and its log; no shared writes between workers."""
    import contextlib
    import logging
    import traceback
    log = Path(log_root) / (unit.output_relative + ".log")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", buffering=1) as stream, contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
        root_logger = logging.getLogger()
        previous_handlers = root_logger.handlers[:]
        handler = logging.StreamHandler(stream)
        root_logger.handlers = [handler]
        job_started = time.monotonic()
        print(f"START pid={os.getpid()} source={unit.source} engine={engine}", flush=True)
        try:
            if engine == "fast":
                from agibotworld2026_2lerobot.fast_backend import convert_source_fast
                record = convert_source_fast(effective, config, **settings)
            else:
                record = convert_source(effective, config)
            part = Path(record["output"])
            if fixture:
                from agibotworld2026_2lerobot.validate_smoke import validate_part
                record["smoke_validation"] = validate_part(Path(fixture), part)
                write_json(part / "meta/smoke_validation.json", record["smoke_validation"])
            record["original_source"] = asdict(unit)
            record["log"] = str(log)
            record["wall_seconds"] = time.monotonic() - job_started
            print(f"DONE {record['status']}", flush=True)
            return record
        except Exception:
            traceback.print_exc()
            raise
        finally:
            root_logger.handlers = previous_handlers
            handler.close()


def parallel_jobs(jobs, workers, io_workers):
    from agibotworld2026_2lerobot.fast_backend import limit_worker_threads
    # Spawn avoids inherited decoder/BLAS locks and honors child thread limits.
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    ctx = multiprocessing.get_context("spawn")
    slot = ctx.BoundedSemaphore(io_workers)
    iterator = iter(jobs)
    with ProcessPoolExecutor(max_workers=workers, mp_context=ctx, initializer=limit_worker_threads,
                             initargs=(slot,)) as pool:
        pending = set()
        for _ in range(workers):
            job = next(iterator, None)
            if job is not None:
                pending.add(pool.submit(source_job, *job))
        try:
            while pending:
                done, pending = wait(pending, return_when=FIRST_COMPLETED)
                # Resolve failures before scheduling further work.
                results = [future.result() for future in done]
                for record in results:
                    yield record
                    job = next(iterator, None)
                    if job is not None:
                        pending.add(pool.submit(source_job, *job))
        finally:
            for future in pending:
                future.cancel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("smoke", "full", "plan"), default="plan")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-base", type=Path, required=True)
    parser.add_argument("--work-root", type=Path)
    parser.add_argument("--prepare-workers", type=int, default=2)
    parser.add_argument("--engine", choices=("classic", "fast"), default="classic")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--io-workers", type=int, default=4)
    parser.add_argument("--camera-workers", type=int, default=1, help="Concurrent episodes within each camera")
    parser.add_argument("--decoder-threads", type=int, default=1)
    parser.add_argument("--extraction-threads", type=int, default=2)
    parser.add_argument("--fixture-root", type=Path, help="Optional existing v2.1 smoke fixture cache")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--max-sources", type=int, help="Bounded FULL-ARCHIVE test only; omitted for full collection")
    args = parser.parse_args()
    if min(args.prepare_workers, args.workers, args.io_workers, args.camera_workers, args.decoder_threads, args.extraction_threads) < 1:
        parser.error("All worker/thread counts must be positive")
    if args.max_sources is not None and args.max_sources < 1:
        parser.error("--max-sources must be positive")
    units = discover_sources(args.source_root, "all", args.include, [])
    if not units:
        raise ValueError("No sources")
    counts = defaultdict(int)
    for unit in units:
        counts[Path(unit.output_relative).parts[0]] += 1
    selected = smoke_selection(units) if args.mode == "smoke" else units
    if args.max_sources is not None:
        selected = selected[:args.max_sources]
    if args.engine == "fast" and args.mode != "smoke":
        selected = largest_first(selected)
    base = args.output_base / "smoke_test" if args.mode == "smoke" else args.output_base
    work = args.work_root or base / (".agibotworld2026_fast" if args.engine == "fast" else ".agibotworld2026_work")
    report = {"mode": args.mode, "source_root": str(args.source_root), "source_counts": dict(counts),
              "canonical_sources": len(units), "selected_sources": [asdict(u) for u in selected],
              "excluded": {"simulation_lite_depth_patch": "Overlay without independent trajectories; original adapter excludes these additional depth cameras."},
              "status": "planned", "outputs": [], "engine": args.engine, "workers": args.workers,
              "io_workers": args.io_workers, "camera_workers": args.camera_workers,
              "subset": bool(args.include) or len(selected) != len(units), "source_filters": args.include,
              "scheduling": "largest-archive-first" if args.engine == "fast" and args.mode != "smoke" else "source-order",
              "completed_sources": 0}
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
    if args.mode == "plan":
        return
    report_path = base / "AgiBotWorld2026_review.json"
    work.mkdir(parents=True, exist_ok=True)
    # A local process lock also guards runs targeting this shared output root.
    import fcntl
    lock = (work / "conversion.lock").open("a")
    fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    output_lock = (base / ".agibotworld2026_output.lock").open("a")
    fcntl.flock(output_lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    started = time.monotonic()
    report["status"] = "running"
    write_json(report_path, report)
    try:
        fixtures = {}
        if args.mode == "smoke":
            def prepare(unit):
                path = (args.fixture_root or work / "fixtures") / unit.output_relative
                marker = path / "smoke_source.json"
                if marker.is_file():
                    if json.loads(marker.read_text()).get("source") != unit.source:
                        raise ValueError(f"Fixture belongs to a different source: {path}")
                    return unit.output_relative, path
                print(f"Extracting episode 0: {unit.output_relative}", flush=True)
                prepare_one_episode(Path(unit.source), path)
                print(f"Fixture ready: {unit.output_relative}", flush=True)
                return unit.output_relative, path
            with ThreadPoolExecutor(max_workers=args.prepare_workers) as executor:
                futures = [executor.submit(prepare, unit) for unit in selected]
                for future in as_completed(futures):
                    key, path = future.result()
                    fixtures[key] = path
        config = ConversionConfig(str(args.source_root), str(work / "parts"), str(work / "staging"), False, None, None)
        groups = defaultdict(list)
        settings = {"camera_workers": args.camera_workers, "decoder_threads": args.decoder_threads,
                    "extraction_threads": args.extraction_threads}
        jobs = []
        for unit in selected:
            effective = SourceUnit("directory", str(fixtures[unit.output_relative]), unit.output_relative) if fixtures else unit
            jobs.append((unit, effective, config, str(fixtures[unit.output_relative]) if fixtures else None,
                         args.engine, settings, str(work / "logs")))
        results = parallel_jobs(jobs, args.workers, args.io_workers)
        for index, record in enumerate(results):
            part = Path(record["output"])
            name = dataset_name(json.loads((part / "meta/info.json").read_text()))
            groups[name].append(record)
            checkpoint = work / "completed" / (record["original_source"]["output_relative"] + ".json")
            write_json(checkpoint, record)
            report.update(completed_sources=index + 1, elapsed_seconds=time.monotonic() - started)
            write_json(report_path, report)
            print(f"Completed [{index + 1}/{len(selected)}] {record['original_source']['output_relative']} ({record['status']})", flush=True)
        report["conversion_seconds"] = time.monotonic() - started
        for name, records in sorted(groups.items()):
            # Worker completion order must not alter episode/task indices.
            records.sort(key=lambda r: r["original_source"]["output_relative"])
            output = base / name
            if output.exists():
                audit_path = output / "meta/unified_action_space.json"
                if not audit_path.is_file():
                    raise FileExistsError(f"Unrecognized final dataset; inspect before replacing: {output}")
                audit = json.loads(audit_path.read_text())
                previous = audit.get("sources", [])
                expected = [r["original_source"] for r in records]
                existing = [r.get("original_source") for r in previous]
                versions_match = all(
                    a.get("summary", {}).get("numeric_stats_version") == b["summary"]["numeric_stats_version"]
                    and a.get("summary", {}).get("video_compat", {}).get("version") == b["summary"]["video_compat"]["version"]
                    for a, b in zip(previous, records)
                )
                info = json.loads((output / "meta/info.json").read_text())
                if (audit.get("schema_version") != "agibotworld2026_waist_v1" or audit.get("mode") != args.mode
                        or existing != expected or not versions_match or dataset_name(info) != name
                        or info["total_frames"] != sum(r["summary"]["frames"] for r in records)):
                    raise FileExistsError(f"Final dataset has different provenance/schema; will not overwrite: {output}")
                result = {"dataset_name": name, "path": str(output), "sources": len(records), "reused": True}
                if fixtures:
                    from agibotworld2026_2lerobot.validate_smoke import validate_dataset
                    result["validation"] = validate_dataset(output)
                    write_json(output / "meta/smoke_validation.json", result["validation"])
                report["outputs"].append(result)
                write_json(report_path, report)
                print(f"Reused completed dataset: {output}", flush=True)
                continue
            stage = work / "aggregate" / name
            if stage.exists():
                backup = work / "failed_attempts" / f"{name}-{time.time_ns()}"
                backup.parent.mkdir(parents=True, exist_ok=True)
                stage.rename(backup)
                print(f"Previous incomplete aggregate retained at {backup}", flush=True)
            aggregate_started = time.monotonic()
            aggregate_output([Path(record["output"]) for record in records], stage, args.engine)
            for number, record in enumerate(records):
                source_info = Path(record["output"]) / "meta/source_info.json"
                if source_info.exists():
                    destination = stage / "meta/source_metadata" / f"source-{number:05d}.json"
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source_info, destination)
                    record["source_metadata"] = str(destination.relative_to(stage))
            audit = {"schema_version": "agibotworld2026_waist_v1", "mode": args.mode, "engine": args.engine, "sources": records}
            write_json(stage / "meta/unified_action_space.json", audit)
            result = {"dataset_name": name, "path": str(output), "sources": len(records),
                      "aggregate_seconds": time.monotonic() - aggregate_started}
            if fixtures:
                from agibotworld2026_2lerobot.validate_smoke import validate_dataset
                result["validation"] = validate_dataset(stage)
                write_json(stage / "meta/smoke_validation.json", result["validation"])
            stage.rename(output)
            report["outputs"].append(result)
            write_json(report_path, report)
        report["status"] = "passed" if fixtures else "completed"
        report["elapsed_seconds"] = time.monotonic() - started
        write_json(report_path, report)
        print(f"{report['status']}: {report_path}", flush=True)
    except Exception as exc:
        report.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        write_json(report_path, report)
        raise


if __name__ == "__main__":
    main()
