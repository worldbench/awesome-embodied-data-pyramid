import unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from agibot2lerobot.agibot_utils import lerobot_utils as mod

class SampleImagesTest(unittest.TestCase):
    def test_exact_legacy_samples_without_full_decode(self):
        frames=np.arange(240*3*4*5,dtype=np.uint8).reshape(240,3,4,5)
        class Decoder:
            def __len__(self): return len(frames)
            def __getitem__(self,key): raise AssertionError('Full decode is forbidden')
            def get_frames_at(self,indices):
                return SimpleNamespace(data=SimpleNamespace(numpy=lambda:frames[indices]))
        with patch.object(mod,'VideoDecoder',return_value=Decoder()):
            actual=mod.sample_images('test.mp4')
        expected=frames[mod.sample_indices(len(frames)-1)]
        np.testing.assert_array_equal(actual,expected)

    def test_depth_array_path_unchanged(self):
        data=np.arange(240*4*5,dtype=np.uint8).reshape(240,4,5)
        np.testing.assert_array_equal(mod.sample_images(data),data[mod.sample_indices(240),None])
