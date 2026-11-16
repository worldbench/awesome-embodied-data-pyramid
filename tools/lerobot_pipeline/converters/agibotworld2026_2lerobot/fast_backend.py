"""Bounded multi-process worker backend with single-storage, immutable videos.

Numeric schema transformation stays in the original converter. Only extraction
and video packaging change: raw videos are never re-encoded or concatenated.
"""
from __future__ import annotations

import gzip
import io
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
from contextlib import contextmanager
from contextlib import nullcontext
from dataclasses import asdict
from pathlib import Path

from agibotworld2026_2lerobot.convert_agibotworld2026 import (
    NEW_NUMERIC_KEYS, OLD_ACTION_KEY, OLD_STATE_KEY, ConversionConfig, SourceUnit,
    _ensure_part_compatibility, _result, _write_json_atomic, rewrite_unified_action_space,
)
from agibotworld2026_2lerobot.source_io import JoinedParts, _relative_member, extract_regular, split_parts


PIPELINE_VERSION = "fast-single-storage-v1"
EXTRACTION_LIMIT = None


def limit_worker_threads(extraction_limit=None):
    """Avoid workers x BLAS/Arrow/Torch automatic thread oversubscription."""
    global EXTRACTION_LIMIT
    EXTRACTION_LIMIT = extraction_limit
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    import pyarrow as pa
    import torch
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    # Initialize library loggers before redirecting per-source log streams.
    from lerobot.scripts import convert_dataset_v21_to_v30  # noqa: F401


@contextmanager
def decompressed_tar(paths, threads=2):
    """pigz supplies buffered inflate; split parts form ONE gzip stream."""
    pigz = shutil.which("pigz")
    if pigz is None:
        with io.BufferedReader(JoinedParts(paths), buffer_size=1024*1024) as raw:
            with gzip.GzipFile(fileobj=raw) as decoded:
                with tarfile.open(fileobj=decoded, mode="r|", bufsize=1024*1024) as archive:
                    yield archive
                # tar's end-of-archive marker may precede the gzip trailer.
                while decoded.read(1024*1024):
                    pass
        return
    feeder = None
    errors = []
    args = [pigz, "-dc", "-p", str(threads)]
    if len(paths) == 1:
        args += ["--", str(paths[0])]
    process = subprocess.Popen(args, stdin=subprocess.PIPE if len(paths) > 1 else subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if len(paths) > 1:
        def feed():
            try:
                with JoinedParts(paths) as stream:
                    shutil.copyfileobj(stream, process.stdin, length=1024*1024)
            except Exception as exc:
                errors.append(exc)
            finally:
                process.stdin.close()
        feeder = threading.Thread(target=feed, daemon=True)
        feeder.start()
    completed = False
    try:
        with tarfile.open(fileobj=process.stdout, mode="r|", bufsize=1024*1024) as archive:
            yield archive
        # Read the trailer as well: don't accept a truncated gzip/CRC failure.
        while process.stdout.read(1024*1024):
            pass
        stderr = process.stderr.read().decode(errors="replace")
        returncode = process.wait()
        if feeder is not None:
            feeder.join()
        if returncode or errors:
            raise RuntimeError(f"gzip extraction failed ({returncode}): {stderr}; {errors}")
        completed = True
    finally:
        if not completed and process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stdout.close()
        process.stderr.close()
        if feeder is not None:
            feeder.join(timeout=5)


def extract_source(unit: SourceUnit, destination: Path, threads=2):
    source = Path(unit.source)
    if unit.kind == "directory":
        return source, False
    components = ([split_parts(source, key) for key in ("meta", "data", "videos")]
                  if unit.kind == "packed_simulation" else [[source]])
    for paths in components:
        with decompressed_tar(paths, threads) as archive:
            for member in archive:
                if member.isdir():
                    continue
                relative = _relative_member(member.name)
                if not relative.parts or relative.parts[0] not in {"data", "meta", "videos"}:
                    continue
                target = destination / relative
                if target.exists():
                    raise ValueError(f"Duplicate archive member: {relative}")
                extract_regular(archive, member, target)
    if not (destination / "meta/info.json").is_file():
        raise ValueError(f"No canonical meta/info.json in {source}")
    return destination, True


def link_immutable(source: Path, destination: Path):
    """Hard link, never silently copy TBs or link a source symlink."""
    if source.is_symlink() or not source.is_file():
        raise ValueError(f"Expected a regular immutable video: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(source, destination)
    except OSError as exc:
        raise OSError(f"Fast mode requires hardlink-capable source/output on one filesystem: {source} -> {destination}: {exc}") from exc


def package_native_videos(source, destination, info, episodes, *, move_owned):
    import av
    from lerobot.datasets.utils import DEFAULT_CHUNK_SIZE, DEFAULT_VIDEO_PATH

    video_rows = [{"episode_index": int(ep["episode_index"])} for ep in episodes]
    count = byte_count = 0
    for key, feature in info["features"].items():
        if feature["dtype"] != "video":
            continue
        for ep, record in zip(episodes, video_rows, strict=True):
            index = int(ep["episode_index"])
            relative = Path(info["video_path"].format(
                episode_chunk=index // int(info.get("chunks_size", 1000)), episode_index=index, video_key=key)
            )
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe source video path: {relative}")
            src = source / relative
            if not src.resolve().is_relative_to(source.resolve()):
                raise ValueError(f"Video path escapes source root: {src}")
            if src.is_symlink() or not src.is_file():
                raise ValueError(f"Missing/non-regular video: {src}")
            with av.open(str(src)) as container:
                stream = container.streams.video[0]
                expected_frames = int(ep["dataset_to_index"] - ep["dataset_from_index"])
                if stream.frames and stream.frames != expected_frames:
                    raise ValueError(f"Video/data frame mismatch: {src}: {stream.frames} != {expected_frames}")
                if [stream.height, stream.width] != feature["shape"][:2]:
                    raise ValueError(f"Video dimensions disagree with info.json: {src}")
                if stream.duration is None:
                    raise ValueError(f"Missing video duration: {src}")
                duration = float(stream.duration * stream.time_base)
                if abs(duration - expected_frames / info["fps"]) > 1.0 / info["fps"]:
                    raise ValueError(f"Video duration/data mismatch: {src}")
            chunk, file = divmod(index, DEFAULT_CHUNK_SIZE)
            dst = destination / DEFAULT_VIDEO_PATH.format(video_key=key, chunk_index=chunk, file_index=file)
            byte_count += src.stat().st_size
            dst.parent.mkdir(parents=True, exist_ok=True)
            if move_owned:
                if dst.exists():
                    raise FileExistsError(dst)
                src.rename(dst)
            else:
                link_immutable(src, dst)
            record.update({f"videos/{key}/chunk_index": chunk, f"videos/{key}/file_index": file,
                           f"videos/{key}/from_timestamp": 0.0, f"videos/{key}/to_timestamp": duration})
            count += 1
    return video_rows, {"video_files": count, "video_bytes": byte_count,
                        "video_operation": "rename private extracted videos" if move_owned else "hardlink immutable videos",
                        "video_payload_copied_bytes": 0}


def convert_source_fast(unit: SourceUnit, config: ConversionConfig, *, camera_workers=1,
                        decoder_threads=1, extraction_threads=2):
    started = time.monotonic()
    target = Path(config.output_root) / unit.output_relative
    marker = target / "meta/unified_action_space.json"
    if target.exists():
        if marker.is_file() and not config.overwrite:
            summary = json.loads(marker.read_text())
            if (summary.get("fast_pipeline") == PIPELINE_VERSION
                    and summary.get("source") == asdict(unit)
                    and set(NEW_NUMERIC_KEYS).issubset(summary.get("added_features", []))):
                _ensure_part_compatibility(target, summary)
                return _result(unit, "skipped", target, "validated completion marker", summary)
        raise FileExistsError(f"Will not overwrite an unrecognized/incomplete part: {target}")
    Path(config.work_root).mkdir(parents=True, exist_ok=True)
    Path(config.output_root).mkdir(parents=True, exist_ok=True)
    if Path(config.work_root).stat().st_dev != Path(config.output_root).stat().st_dev:
        raise ValueError("Fast work and part output roots must be on the same filesystem")
    job = Path(tempfile.mkdtemp(prefix="fast_", dir=config.work_root))
    stages = {}
    try:
        print(f"EXTRACT {unit.source}", flush=True)
        t = time.monotonic()
        with EXTRACTION_LIMIT if EXTRACTION_LIMIT is not None else nullcontext():
            stages["extract_wait_seconds"] = time.monotonic() - t
            t = time.monotonic()
            source, owned = extract_source(unit, job / "extracted", extraction_threads)
        stages["extract_seconds"] = time.monotonic() - t
        print(f"EXTRACT done in {stages['extract_seconds']:.2f}s; packaging native videos", flush=True)
        from lerobot.scripts import convert_dataset_v21_to_v30 as converter
        info = json.loads((source / "meta/info.json").read_text())
        converter.validate_local_dataset_version(source)
        stage = job / "converted"
        t = time.monotonic()
        converter.convert_info(source, stage, config.data_file_size_mb or 100, config.video_file_size_mb or 500)
        converter.convert_tasks(source, stage)
        episodes = converter.convert_data(source, stage, config.data_file_size_mb or 100)
        if (len(episodes) != info["total_episodes"] or
                sum(ep["dataset_to_index"] - ep["dataset_from_index"] for ep in episodes) != info["total_frames"]):
            raise ValueError(f"Source frame/episode totals disagree with actual parquet data: {source}")
        videos, video_audit = package_native_videos(source, stage, info, episodes, move_owned=owned)
        converter.convert_episodes_metadata(source, stage, episodes, videos)
        _write_json_atomic(stage / "meta/source_info.json", info)
        converted_info = json.loads((stage / "meta/info.json").read_text())
        for key in (OLD_STATE_KEY, OLD_ACTION_KEY):
            converted_info["features"][key]["field_descriptions"] = info["features"][key]["field_descriptions"]
        _write_json_atomic(stage / "meta/info.json", converted_info)
        stages["container_seconds"] = time.monotonic() - t
        print(f"CONTAINER done in {stages['container_seconds']:.2f}s; mapping numeric fields", flush=True)
        t = time.monotonic()
        summary = rewrite_unified_action_space(stage, unit)
        stages["numeric_seconds"] = time.monotonic() - t
        t = time.monotonic()
        _ensure_part_compatibility(stage, summary, video_workers=camera_workers, decoder_threads=decoder_threads)
        stages["video_stats_seconds"] = time.monotonic() - t
        print(f"STATS done in {stages['video_stats_seconds']:.2f}s", flush=True)
        summary.update(fast_pipeline=PIPELINE_VERSION, video_storage=video_audit,
                       timing={**stages, "total_seconds": time.monotonic() - started})
        _write_json_atomic(stage / "meta/unified_action_space.json", summary)
        target.parent.mkdir(parents=True, exist_ok=True)
        stage.rename(target)
        return _result(unit, "converted", target, "native videos, no remux/copy", summary)
    finally:
        # job is a freshly-created, private directory, never a source/work root.
        shutil.rmtree(job, ignore_errors=True)
