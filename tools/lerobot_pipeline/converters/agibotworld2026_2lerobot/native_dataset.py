"""LeRobot 0.6.x reader preserving AgiBot's unquantized PNG16 depth values.

Only this dataset instance uses the adapter; no installed library is patched.
Unknown physical depth units stay unknown. Returned depth floats are exact
native uint16 codes, not an inferred metre/millimetre conversion.
"""
import av
import numpy as np
import torch
from lerobot.datasets.dataset_reader import DatasetReader
from lerobot.datasets.lerobot_dataset import LeRobotDataset

from agibotworld2026_2lerobot.video_compat import frame_at


class NativeDepthReader(DatasetReader):
    def _query_videos(self, query_timestamps, ep_idx):
        native_keys = {key for key, feature in self._meta.features.items()
                       if (feature.get("info") or {}).get("agibot_native_depth")}
        result = super()._query_videos({key: ts for key, ts in query_timestamps.items() if key not in native_keys}, ep_idx)
        episode = self._meta.episodes[ep_idx]
        for key in native_keys & query_timestamps.keys():
            offset = episode[f"videos/{key}/from_timestamp"]
            path = self.root / self._meta.get_video_file_path(ep_idx, key)
            with av.open(str(path)) as container:
                frames = [frame_at(container, offset + ts, depth=True, tolerance=self._tolerance_s)
                          for ts in query_timestamps[key]]
            result[key] = torch.from_numpy(np.stack(frames).astype(np.float32)).squeeze(0)
        return result


class AgiBotWorldDataset(LeRobotDataset):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not hasattr(self, "reader") or not isinstance(self.reader, DatasetReader):
            raise RuntimeError("Native PNG16 adapter requires LeRobot's DatasetReader API (tested with 0.6.1)")
        # Keep the already loaded HF dataset, index mappings, and user options.
        native = NativeDepthReader.__new__(NativeDepthReader)
        native.__dict__.update(self.reader.__dict__)
        self.reader = native
