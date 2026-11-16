"""Fast unit checks for the reviewed AgiBotWorld-Beta action template."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from agibotworld_beta_2lerobot.beta_utils import (
    build_numeric_features,
    compose_ee,
    compose_qpos,
    load_unified_episode,
    sanitize_bimanual_qpos_action,
)


class SchemaTest(unittest.TestCase):
    def test_gripper_schema_keeps_one_value_per_effector(self) -> None:
        features = build_numeric_features("gripper")
        self.assertEqual(features["action.qpos"]["shape"], (16,))
        self.assertEqual(features["action.qpos_valid"]["shape"], (2,))
        self.assertIn("description", features["action.qpos"])
        self.assertIn("description", features["action.qpos_valid"])
        for feature in features.values():
            self.assertIn("Embodiment: A2D gripper.", feature["description"])
            self.assertIn("OriginData:", feature["description"])
        self.assertEqual(
            features["action.qpos"]["names"]["motors"][7],
            "action/left_effector/position",
        )
        fields = features["action.qpos"]["field_descriptions"]
        self.assertEqual(fields["action/left_effector/position"]["dimensions"], 1)
        self.assertEqual(fields["action/left_effector/position"]["indices"], [7])
        self.assertEqual(fields["action/right_effector/position"]["indices"], [15])
        self.assertIn("0 means fully open", fields["action/left_effector/position"]["description"])
        state_fields = features["state.qpos"]["field_descriptions"]
        self.assertIn(
            "not the action's 0/1",
            state_fields["state/left_effector/position"]["description"],
        )

    def test_dexhand_replaces_each_gripper_slot_with_six_values(self) -> None:
        features = build_numeric_features("dexhand")
        self.assertEqual(features["action.qpos"]["shape"], (26,))
        fields = features["action.qpos"]["field_descriptions"]
        self.assertEqual(fields["action/left_effector/position"]["dimensions"], 6)
        self.assertEqual(
            fields["action/left_effector/position"]["indices"],
            list(range(7, 13)),
        )
        self.assertEqual(
            fields["action/right_effector/position"]["indices"],
            list(range(20, 26)),
        )


class MappingTest(unittest.TestCase):
    def test_gripper_qpos_order(self) -> None:
        joints = np.arange(14, dtype=np.float32)[None]
        effectors = np.asarray([[100, 200]], dtype=np.float32)
        actual = compose_qpos(joints, effectors, "gripper")
        np.testing.assert_array_equal(
            actual[0],
            [0, 1, 2, 3, 4, 5, 6, 100, 7, 8, 9, 10, 11, 12, 13, 200],
        )

    def test_dexhand_qpos_order(self) -> None:
        joints = np.arange(14, dtype=np.float32)[None]
        effectors = np.arange(100, 112, dtype=np.float32)[None]
        actual = compose_qpos(joints, effectors, "dexhand")
        np.testing.assert_array_equal(
            actual[0],
            [
                0, 1, 2, 3, 4, 5, 6,
                100, 101, 102, 103, 104, 105,
                7, 8, 9, 10, 11, 12, 13,
                106, 107, 108, 109, 110, 111,
            ],
        )

    def test_qpos_action_validity_is_per_side(self) -> None:
        action = np.ones((1, 16), dtype=np.float32)
        action[0, 9] = np.nan
        sanitized, valid = sanitize_bimanual_qpos_action(action, "gripper")
        np.testing.assert_array_equal(valid, [[1, 0]])
        np.testing.assert_array_equal(sanitized[0, :8], 1)
        np.testing.assert_array_equal(sanitized[0, 8:], 0)

    def test_ee_order_and_quaternion_normalization(self) -> None:
        position = np.asarray([[[1, 2, 3], [4, 5, 6]]], dtype=np.float32)
        orientation = np.asarray([[[0, 0, 0, 2], [0, 0, 0, 4]]], dtype=np.float32)
        values, valid = compose_ee(position, orientation)
        np.testing.assert_array_equal(values[0], [1, 2, 3, 0, 0, 0, 1, 4, 5, 6, 0, 0, 0, 1])
        np.testing.assert_array_equal(valid[0], [1, 1])

    def test_sparse_action_is_scattered_over_state_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "episode.h5"
            with h5py.File(path, "w") as h5_file:
                h5_file["state/waist/position"] = np.arange(8).reshape(4, 2)
                h5_file["action/waist/position"] = [[10, 11], [12, 13]]
                h5_file["action/waist/index"] = [1, 3]
                h5_file["timestamp"] = np.arange(4)
                h5_file["state/joint/position"] = np.zeros((4, 14))
                h5_file["state/effector/position"] = np.zeros((4, 2))
                h5_file["state/end/position"] = np.zeros((4, 2, 3))
                orientation = np.zeros((4, 2, 4))
                orientation[..., 3] = 1
                h5_file["state/end/orientation"] = orientation
                h5_file["action/joint/position"] = np.ones((2, 14))
                h5_file["action/joint/index"] = [1, 3]
                h5_file["action/effector/position"] = np.ones((2, 2))
                h5_file["action/effector/index"] = [1, 3]
                h5_file["action/end/position"] = np.zeros((2, 2, 3))
                h5_file["action/end/orientation"] = np.asarray(
                    [orientation[1], orientation[3]]
                )
                h5_file["action/end/index"] = [1, 3]

            arrays = load_unified_episode(path, "gripper")
            np.testing.assert_array_equal(arrays["state.waist"], np.arange(8).reshape(4, 2))
            np.testing.assert_array_equal(arrays["action.waist"], [[0, 1], [10, 11], [4, 5], [12, 13]])
            self.assertEqual(arrays["action.waist"].dtype, np.dtype("float32"))
            np.testing.assert_array_equal(arrays["action.qpos"][[0, 2]], 0)
            np.testing.assert_array_equal(arrays["action.qpos"][[1, 3]], 1)
            np.testing.assert_array_equal(arrays["action.qpos_valid"], 1)

    def test_missing_ee_group_is_zero_and_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "episode.h5"
            with h5py.File(path, "w") as h5_file:
                h5_file["state/waist/position"] = np.zeros((2, 2))
                h5_file["action/waist/position"] = np.ones((2, 2))
                h5_file["timestamp"] = np.arange(2)
                h5_file["state/joint/position"] = np.zeros((2, 14))
                h5_file["state/effector/position"] = np.zeros((2, 2))
                h5_file["action/joint/position"] = np.zeros((2, 14))
                h5_file["action/effector/position"] = np.zeros((2, 2))

                # Quaternion alone is insufficient: EE position is absent.
                orientation = np.zeros((2, 2, 4))
                orientation[..., 3] = 1
                h5_file["state/end/orientation"] = orientation
                h5_file["action/end/orientation"] = orientation

            arrays = load_unified_episode(path, "gripper")
            np.testing.assert_array_equal(arrays["action.waist"], 1)
            np.testing.assert_array_equal(arrays["state.ee"], 0)
            np.testing.assert_array_equal(arrays["state.ee_valid"], 0)
            np.testing.assert_array_equal(arrays["action.ee"], 0)
            np.testing.assert_array_equal(arrays["action.ee_valid"], 0)


if __name__ == "__main__":
    unittest.main()
