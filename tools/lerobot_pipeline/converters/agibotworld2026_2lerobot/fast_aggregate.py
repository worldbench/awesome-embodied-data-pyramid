"""LeRobot index/task aggregation with hardlinked, non-concatenated videos.

Use the installed library for data reindexing and episode metadata; replace
only the video payload-copy stage. Final paths are real files, not symlinks.
"""
from __future__ import annotations

import json
from pathlib import Path

from agibotworld2026_2lerobot.fast_backend import link_immutable


def normalize_episode_task_aliases(df, source_tasks):
    """Resolve the verified simulation metadata spelling against its task table."""
    aliases = {"Freezer Food Organization-SIM-AW2": "Freezer Food Organization-AW2-SIM"}
    mapping = {old: new for old, new in aliases.items()
               if old not in source_tasks and new in source_tasks}
    if mapping and "tasks" in df.columns:
        df = df.copy()
        df["tasks"] = df["tasks"].map(lambda names: [mapping.get(name, name) for name in names])
    return df


def aggregate_video_links(src, dst, state, chunk_size):
    from lerobot.datasets.utils import DEFAULT_VIDEO_PATH, update_chunk_file_indices
    for key, item in state.items():
        item.update(episode_duration=0.0, src_to_dst={}, src_to_offset={})
        pairs = sorted(set(zip(src.episodes[f"videos/{key}/chunk_index"],
                               src.episodes[f"videos/{key}/file_index"], strict=True)))
        for src_chunk, src_file in pairs:
            destination = dst.root / DEFAULT_VIDEO_PATH.format(
                video_key=key, chunk_index=item["chunk"], file_index=item["file"])
            if destination.exists():
                item["chunk"], item["file"] = update_chunk_file_indices(item["chunk"], item["file"], chunk_size)
                destination = dst.root / DEFAULT_VIDEO_PATH.format(
                    video_key=key, chunk_index=item["chunk"], file_index=item["file"])
            source = src.root / DEFAULT_VIDEO_PATH.format(video_key=key, chunk_index=src_chunk, file_index=src_file)
            link_immutable(source, destination)
            pair = (src_chunk, src_file)
            item["src_to_dst"][pair] = (item["chunk"], item["file"])
            item["src_to_offset"][pair] = 0.0
        # Explicit zero per-file offsets are used; no global duration offset.
    return state


def aggregate_fast(parts: list[Path], output: Path):
    import pandas as pd
    from lerobot.datasets import aggregate as api
    from lerobot.datasets.dataset_metadata import LeRobotDatasetMetadata
    from generic_converter.metadata import annotate_dataset_info

    all_meta = [LeRobotDatasetMetadata(repo_id=p.name, root=p) for p in parts]
    fps, robot_type, _ = api.validate_all_metadata(all_meta)
    features = api.merge_video_feature_info_for_aggregate(all_meta)
    video_keys = [key for key, feature in features.items() if feature["dtype"] == "video"]
    chunk_size = api.DEFAULT_CHUNK_SIZE
    dst = LeRobotDatasetMetadata.create(
        repo_id=output.name, fps=fps, robot_type=robot_type, features=features,
        root=output, use_videos=bool(video_keys), chunks_size=chunk_size,
        data_files_size_in_mb=100, video_files_size_in_mb=500)
    tasks = pd.concat([meta.tasks for meta in all_meta]).index.unique()
    dst.tasks = pd.DataFrame({"task_index": range(len(tasks))}, index=pd.Index(tasks, name="task"))
    dst.episodes = {}
    meta_index, data_index = {"chunk": 0, "file": 0}, {"chunk": 0, "file": 0}
    videos_index = {key: {"chunk": 0, "file": 0, "latest_duration": 0.0, "episode_duration": 0.0}
                    for key in video_keys}
    for source in all_meta:
        videos_index = aggregate_video_links(source, dst, videos_index, chunk_size)
        data_index = api.aggregate_data(source, dst, data_index, 100, chunk_size, concatenate_data=False)
        original_update = api.update_meta_data
        def update_with_task_aliases(df, *args, **kwargs):
            return original_update(normalize_episode_task_aliases(df, source.tasks.index), *args, **kwargs)
        api.update_meta_data = update_with_task_aliases
        try:
            meta_index = api.aggregate_metadata(source, dst, meta_index, data_index, videos_index)
        finally:
            api.update_meta_data = original_update
        data_index.pop("src_to_dst", None)
        dst.info.total_episodes += source.total_episodes
        dst.info.total_frames += source.total_frames
    api.finalize_aggregation(dst, all_meta)
    annotate_dataset_info(output)
    audit = {"mode": "hardlink", "video_payload_copied_bytes": 0, "video_reencoded": False,
             "video_concatenated": False, "data_concatenated": False,
             "notice": "Videos are immutable hardlinks shared with conversion parts. Unlinking one path is safe; editing shared video contents is not."}
    (output / "meta/video_storage.json").write_text(json.dumps(audit, indent=2) + "\n")
