"""Fast unit checks for ABC-130k schema, alignment, and EE conversion."""

from __future__ import annotations

import unittest

import numpy as np

from abc130k2lerobot.abc_mcap import (
    EE_PRESENT_EPISODES,
    EE_TOTAL_EPISODES,
    ScalarStream,
    build_features,
    convert_pose_stream,
    floor_indices,
    matrix_to_pose7,
    sanitize_bimanual_qpos_action,
)


class AlignmentTest(unittest.TestCase):
    def test_floor_indices_use_causal_hold(self) -> None:
        source = np.asarray([10, 20, 40], dtype=np.int64)
        target = np.asarray([10, 19, 20, 39, 40, 50], dtype=np.int64)
        actual = floor_indices(source, target)
        np.testing.assert_array_equal(actual, [0, 0, 1, 1, 2, 2])


class PoseConversionTest(unittest.TestCase):
    def test_identity_matrix_to_pose7(self) -> None:
        actual = matrix_to_pose7(np.eye(4, dtype=np.float64).reshape(-1))
        np.testing.assert_allclose(actual, [0, 0, 0, 0, 0, 0, 1], atol=1e-6)

    def test_reflection_is_rejected(self) -> None:
        matrix = np.eye(4, dtype=np.float64)
        matrix[0, 0] = -1
        with self.assertRaisesRegex(ValueError, "determinant"):
            matrix_to_pose7(matrix.reshape(-1))

    def test_present_pose_stream_sets_valid_mask(self) -> None:
        identity = np.eye(4, dtype=np.float64).reshape(-1)
        stream = ScalarStream(
            timestamps=np.asarray([10, 20], dtype=np.int64),
            positions=np.zeros((2, 6), dtype=np.float64),
            poses=[identity, identity],
        )
        values, valid = convert_pose_stream(
            stream=stream,
            aligned_indices=np.asarray([0, 1], dtype=np.int64),
            frame_count=2,
            topic="/left-arm-state",
            missing_policy="fill",
        )
        self.assertEqual(values.shape, (2, 7))
        np.testing.assert_array_equal(valid, [1, 1])

    def test_missing_pose_stream_fills_finite_zeros(self) -> None:
        stream = ScalarStream(
            timestamps=np.asarray([10, 20], dtype=np.int64),
            positions=np.zeros((2, 6), dtype=np.float64),
            poses=[np.asarray([]), np.asarray([])],
        )
        values, valid = convert_pose_stream(
            stream=stream,
            aligned_indices=np.asarray([0, 1], dtype=np.int64),
            frame_count=2,
            topic="/left-arm-state",
            missing_policy="fill",
        )
        self.assertTrue(np.isfinite(values).all())
        np.testing.assert_array_equal(values, np.zeros((2, 7)))
        np.testing.assert_array_equal(valid, [0, 0])


class SchemaTest(unittest.TestCase):
    def test_ee_schema_is_fixed_and_documents_audit_ratio(self) -> None:
        features = build_features(height=480, width=640, qpos_only=False)
        self.assertEqual(features["state.ee"]["shape"], (14,))
        self.assertEqual(features["state.ee_valid"]["shape"], (2,))
        self.assertEqual(features["action.qpos_valid"]["shape"], (2,))
        self.assertIn("description", features["action.qpos"])
        self.assertIn("description", features["action.qpos_valid"])
        for feature in features.values():
            self.assertIn("Embodiment: YAM dual-arm.", feature["description"])
            self.assertIn("OriginData:", feature["description"])
        ratio = f"{EE_PRESENT_EPISODES}/{EE_TOTAL_EPISODES}"
        self.assertIn(ratio, features["state.ee"]["description"])

    def test_qpos_validity_is_per_side(self) -> None:
        action = np.ones((2, 14), dtype=np.float32)
        action[0, 2] = np.nan
        sanitized, valid = sanitize_bimanual_qpos_action(action)
        np.testing.assert_array_equal(valid, [[0, 1], [1, 1]])
        np.testing.assert_array_equal(sanitized[0, :7], 0)
        np.testing.assert_array_equal(sanitized[0, 7:], 1)


if __name__ == "__main__":
    unittest.main()
