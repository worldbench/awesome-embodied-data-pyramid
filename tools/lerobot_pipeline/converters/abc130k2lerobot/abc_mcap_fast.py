"""ABC converter with bounded streaming H.264 encoding; original action alignment unchanged.

Accepts all abc_mcap.py CLI arguments. Additional environment variables:
FFMPEG_BIN, ENCODER_THREADS (default 1), ENCODER_QUEUE (default 8).
Uses the existing task-level datatrove --resume-dir mechanism.
"""
import os
import queue
from pathlib import Path
import shutil
import subprocess
import sys
from types import MethodType

sys.path.insert(0, str(Path(__file__).resolve().parent))
import abc_mcap as original


def feed_frame_lossless(self, video_key, image):
    """Offline backpressure: never discard an aligned frame on a slow encoder."""
    if not self._episode_active:
        raise RuntimeError('No active streaming episode')
    copied = image.copy()
    while self._threads[video_key].is_alive():
        try:
            self._frame_queues[video_key].put(copied, timeout=0.25)
            return
        except queue.Full:
            continue
    raise RuntimeError(f'Encoder thread stopped for {video_key}; refusing to drop frames')


class BoundedVideoDecoder(original.AlignedVideoDecoder):
    def __init__(self, path, codec, width, height):
        executable = os.environ.get('FFMPEG_BIN', 'ffmpeg')
        input_format = 'hevc' if codec in {'h265', 'hevc'} else 'h264'
        vf = (f'scale={width}:{height}:force_original_aspect_ratio=decrease:flags=bicubic,'
              f'pad={width}:{height}:(ow-iw)/2:(oh-ih)/2')
        self.process = subprocess.Popen(
            [executable, '-loglevel', 'error', '-threads', '1', '-filter_threads', '1',
             '-f', input_format, '-i', str(path), '-vf', vf, '-threads', '1',
             '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        self.width, self.height = width, height
        self.index, self.frame = -1, None


class StreamingABC130KAdapter(original.ABC130KAdapter):
    def create_dataset(self, task):
        from lerobot.datasets.lerobot_dataset import LeRobotDataset
        from lerobot.configs.video import RGBEncoderConfig
        original.validate_feature_descriptions(self.features)
        dataset = LeRobotDataset.create(
            repo_id=task.local_repo_id, root=task.output_path, fps=self.fps,
            robot_type=self.robot_type, features=self.features,
            video_backend='pyav', streaming_encoding=True,
            encoder_queue_maxsize=int(os.environ.get('ENCODER_QUEUE', '8')),
            encoder_threads=int(os.environ.get('ENCODER_THREADS', '1')),
            rgb_encoder=RGBEncoderConfig(vcodec='h264', preset='veryfast', crf=23, g=2),
            metadata_buffer_size=1,
        )
        encoder = dataset.writer._streaming_encoder
        encoder.feed_frame = MethodType(feed_frame_lossless, encoder)
        return dataset


# Also apply in worker interpreters importing this module.
original.AlignedVideoDecoder = BoundedVideoDecoder

if __name__ == '__main__':
    executable = os.environ.get('FFMPEG_BIN', 'ffmpeg')
    if shutil.which(executable) is None:
        raise SystemExit('Set FFMPEG_BIN to an existing ffmpeg executable.')
    for name, default in [('ENCODER_THREADS', '1'), ('ENCODER_QUEUE', '8')]:
        if int(os.environ.get(name, default)) < 1:
            raise SystemExit(f'{name} must be positive')
    original.ABC130KAdapter = StreamingABC130KAdapter
    print('FAST: streaming H.264 veryfast CRF23 GOP2; bounded queues; no PNG intermediates', flush=True)
    original.main()
