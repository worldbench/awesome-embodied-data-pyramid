"""Depth must retain the full uint16 range; fail on unsynchronized frames."""
import unittest
from fractions import Fraction
from types import SimpleNamespace

import numpy as np

from agibotworld2026_2lerobot.video_compat import frame_at


class FakeFrame:
    def __init__(self, pts):
        self.pts = pts
        self.formats = []

    def to_ndarray(self, format):
        self.formats.append(format)
        if format == "gray16le":
            return np.array([[0, 65535], [4096, 1234]], dtype=np.uint16)
        return np.zeros((2, 2, 3), dtype=np.uint8)


class FakeContainer:
    def __init__(self, pts):
        self.streams = SimpleNamespace(video=[SimpleNamespace(time_base=Fraction(1, 30))])
        self.frames = [FakeFrame(value) for value in pts]

    def seek(self, *args, **kwargs):
        pass

    def decode(self, stream):
        return iter(self.frames)


class VideoCompatTest(unittest.TestCase):
    def test_native_depth_does_not_truncate_16_bits(self):
        container = FakeContainer([0, 1, 2])
        values = frame_at(container, 1/30, depth=True)
        self.assertEqual(values.dtype, np.uint16)
        self.assertEqual(values.shape, (1, 2, 2))
        self.assertEqual(int(values[0, 0, 1]), 65535)
        self.assertEqual(container.frames[1].formats, ["gray16le"])

    def test_missing_timestamp_fails(self):
        with self.assertRaisesRegex(ValueError, "synchronized"):
            frame_at(FakeContainer([0, 1]), 1.0, depth=True)

    def test_rgb_is_channel_first_uint8(self):
        values = frame_at(FakeContainer([0]), 0)
        self.assertEqual(values.shape, (3, 2, 2))
        self.assertEqual(values.dtype, np.uint8)
