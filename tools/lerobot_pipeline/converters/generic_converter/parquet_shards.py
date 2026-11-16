"""Append standard episode row groups without rereading an existing shard."""
from pathlib import Path
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq


class StreamingDataShards:
    def __init__(self, fallback):
        self.fallback = fallback
        self.writer = None
        self.path = None
        self.size = 0.0
        self.pending = None

    def _flush_pending(self):
        if self.pending is not None:
            self.writer.write_table(self.pending)
            self.pending = None

    def close(self):
        if self.writer is not None:
            try:
                self._flush_pending()
            finally:
                self.writer.close()
                self.writer = None

    def __call__(self, df, src_path, idx, max_mb, chunk_size, default_path,
                 contains_images=False, aggr_root=None, hf_features=None,
                 concatenate=True, one_row_group_per_episode=False):
        from lerobot.datasets import aggregate as api
        if contains_images or not one_row_group_per_episode:
            return self.fallback(df, src_path, idx, max_mb, chunk_size, default_path,
                                 contains_images=contains_images, aggr_root=aggr_root,
                                 hf_features=hf_features, concatenate=concatenate,
                                 one_row_group_per_episode=one_row_group_per_episode)
        if aggr_root is None:
            raise ValueError('aggr_root is required')
        size = api.get_parquet_file_size_in_mb(src_path)
        if self.writer is not None and (not concatenate or self.size + size >= max_mb):
            self.close()
            idx['chunk'], idx['file'] = api.update_chunk_file_indices(idx['chunk'], idx['file'], chunk_size)
        path = Path(aggr_root) / default_path.format(chunk_index=idx['chunk'], file_index=idx['file'])
        table = pa.Table.from_pandas(df, preserve_index=False)
        if self.writer is None:
            if path.exists():
                raise FileExistsError(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            self.writer = pq.ParquetWriter(path, table.schema, compression='snappy', use_dictionary=True)
            self.path, self.size = path, 0.0
        if path != self.path:
            raise ValueError('Unexpected data shard index change')
        episode = table['episode_index'].to_numpy(zero_copy_only=False)
        starts = np.concatenate(([0], np.nonzero(np.diff(episode))[0] + 1))
        for start, stop in zip(starts, np.append(starts[1:], len(episode)), strict=True):
            part = table.slice(int(start), int(stop-start))
            if not len(part):
                continue
            if self.pending is not None and self.pending['episode_index'][0].as_py() == part['episode_index'][0].as_py():
                self.pending = pa.concat_tables([self.pending, part])
            else:
                self._flush_pending()
                self.pending = part
        self.size += size
        return idx, (idx['chunk'], idx['file'])
