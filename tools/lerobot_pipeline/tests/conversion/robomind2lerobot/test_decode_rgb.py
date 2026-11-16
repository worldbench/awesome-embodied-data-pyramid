"""Regression coverage for native-resolution RGB in mixed RoboMIND archives."""
from pathlib import Path
import sys
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "converters" / "robomind2lerobot"))
from robomind_fast import decode_one


class DecodeRGBTests(unittest.TestCase):
    def test_legacy_raw_resolutions_override_config(self):
        for actual, configured in [((480, 640, 3), (720, 1280, 3)),
                                   ((720, 1280, 3), (480, 640, 3))]:
            source = np.arange(np.prod(actual), dtype=np.uint8).reshape(actual)
            for raw in [source.ravel(), source.tobytes()]:
                for flip in [False, True]:
                    with self.subTest(actual=actual, bytes=isinstance(raw, bytes), flip=flip):
                        decoded = decode_one(raw, flip, configured)
                        np.testing.assert_array_equal(decoded, source[..., ::-1] if flip else source)
                        self.assertTrue(decoded.flags.c_contiguous)

    def test_configured_raw_shape_and_hwc(self):
        source = np.arange(12 * 16 * 3, dtype=np.uint8).reshape(12, 16, 3)
        for raw in [source, source.ravel()]:
            np.testing.assert_array_equal(decode_one(raw, False, source.shape), source)

    def test_encoded_png_preserves_actual_resolution(self):
        source = np.arange(12 * 16 * 3, dtype=np.uint8).reshape(12, 16, 3)
        ok, encoded = cv2.imencode('.png', source)
        self.assertTrue(ok)
        np.testing.assert_array_equal(decode_one(encoded, False, (720, 1280, 3)), source)
        np.testing.assert_array_equal(decode_one(encoded.tobytes(), True, source.shape), source[..., ::-1])

    def test_unknown_raw_length_still_fails(self):
        with self.assertRaisesRegex(ValueError, 'Cannot decode RGB'):
            decode_one(np.zeros(101, dtype=np.uint8), False, (720, 1280, 3))


if __name__ == '__main__':
    unittest.main()
