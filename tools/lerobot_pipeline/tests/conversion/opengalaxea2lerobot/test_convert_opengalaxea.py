"""Unit checks for OpenGalaxea schema mapping and validity masks."""

from __future__ import annotations

import unittest

import numpy as np

from opengalaxea2lerobot.convert_opengalaxea import (
    GalaxeaSchema,
    build_unified_features,
    map_robot_arrays,
)


def make_info(robot_type: str, include_action_ee: bool) -> dict:
    arm_width = 6 if robot_type == "r1lite" else 7
    features = {
        "observation.state.left_arm": {"shape": [arm_width]},
        "observation.state.right_arm": {"shape": [arm_width]},
        "observation.state.left_gripper": {"shape": [1]},
        "observation.state.right_gripper": {"shape": [1]},
        "observation.state.left_ee_pose": {"shape": [7]},
        "observation.state.right_ee_pose": {"shape": [7]},
        "action.left_arm": {"shape": [arm_width]},
        "action.right_arm": {"shape": [arm_width]},
        "action.left_gripper": {"shape": [1]},
        "action.right_gripper": {"shape": [1]},
    }
    features["observation.state.torso"] = {"shape": [4]}
    if robot_type == "r1lite":
        features["action.torso.velocities"] = {"shape": [6]}
    if include_action_ee:
        features["action.left_ee_pose"] = {"shape": [7]}
        features["action.right_ee_pose"] = {"shape": [7]}
    return {"robot_type": robot_type, "features": features}


def make_arrays(schema: GalaxeaSchema, rows: int = 2) -> dict[str, np.ndarray]:
    arrays = {
        "observation.state.left_arm": np.ones(
            (rows, schema.arm_width), dtype=np.float32
        ),
        "observation.state.right_arm": np.full(
            (rows, schema.arm_width), 2, dtype=np.float32
        ),
        "observation.state.left_gripper": np.full(rows, 3, dtype=np.float32),
        "observation.state.right_gripper": np.full(rows, 4, dtype=np.float32),
        "observation.state.left_ee_pose": np.tile(
            [1, 2, 3, 0, 0, 0, 2], (rows, 1)
        ).astype(np.float32),
        "observation.state.right_ee_pose": np.tile(
            [4, 5, 6, 0, 0, 0, 4], (rows, 1)
        ).astype(np.float32),
        "action.left_arm": np.full(
            (rows, schema.arm_width), 5, dtype=np.float32
        ),
        "action.right_arm": np.full(
            (rows, schema.arm_width), 6, dtype=np.float32
        ),
        "action.left_gripper": np.full(rows, 7, dtype=np.float32),
        "action.right_gripper": np.full(rows, 8, dtype=np.float32),
    }
    arrays["observation.state.torso"] = np.tile([0.1, -0.2, 0.3, 0.4], (rows, 1))
    if schema.robot_type == "r1lite":
        arrays["action.torso.velocities"] = np.tile([0.15, 0, -0.1, 0, 0.2, 0], (rows, 1))
    if schema.has_action_ee:
        arrays["action.left_ee_pose"] = np.tile(
            [1, 2, 3, 0, 0, 0, 3], (rows, 1)
        ).astype(np.float32)
        arrays["action.right_ee_pose"] = np.tile(
            [4, 5, 6, 0, 0, 0, 5], (rows, 1)
        ).astype(np.float32)
    return arrays


class GalaxeaMappingTest(unittest.TestCase):
    def test_waist_preserves_source_values_and_pro_omits_action(self):
        for robot in ['r1lite', 'r1pro']:
            schema = GalaxeaSchema.from_info(make_info(robot, robot == 'r1pro'))
            arrays = make_arrays(schema)
            mapped = map_robot_arrays(arrays, schema)
            np.testing.assert_array_equal(mapped['state.waist'], arrays['observation.state.torso'].astype(np.float32))
            if robot == 'r1lite':
                np.testing.assert_array_equal(mapped['action.waist_velocity'], arrays['action.torso.velocities'].astype(np.float32))
            else:
                self.assertNotIn('action.waist_velocity', mapped)
                self.assertNotIn('action.waist_velocity', build_unified_features(schema))

    def test_missing_or_invalid_waist_fails_explicitly(self):
        info = make_info('r1lite', False)
        del info['features']['action.torso.velocities']
        with self.assertRaises(KeyError): GalaxeaSchema.from_info(info)
        schema = GalaxeaSchema.from_info(make_info('r1lite', False))
        for key in ['observation.state.torso', 'action.torso.velocities']:
            arrays = make_arrays(schema); arrays[key][0, 0] = np.nan
            with self.assertRaises(ValueError): map_robot_arrays(arrays, schema)

    def test_r1lite_uses_14d_qpos_and_invalid_ee_placeholder(self) -> None:
        schema = GalaxeaSchema.from_info(make_info("r1lite", False))
        mapped = map_robot_arrays(make_arrays(schema), schema)

        self.assertEqual(mapped["state.qpos"].shape, (2, 14))
        self.assertEqual(mapped["action.qpos"].shape, (2, 14))
        np.testing.assert_array_equal(mapped["action.ee"], 0)
        np.testing.assert_array_equal(mapped["action.ee_valid"], 0)
        np.testing.assert_array_equal(mapped["action.qpos_valid"], 1)
        np.testing.assert_array_equal(mapped["state.qpos"][0, :7], [1] * 6 + [3])
        np.testing.assert_array_equal(mapped["state.qpos"][0, 7:], [2] * 6 + [4])

    def test_r1pro_uses_source_action_ee_and_normalizes_quaternions(self) -> None:
        schema = GalaxeaSchema.from_info(make_info("r1pro", True))
        mapped = map_robot_arrays(make_arrays(schema), schema)

        self.assertEqual(mapped["state.qpos"].shape, (2, 16))
        self.assertEqual(mapped["action.qpos"].shape, (2, 16))
        np.testing.assert_array_equal(mapped["action.ee_valid"], 1)
        np.testing.assert_allclose(mapped["action.ee"][:, 6], 1)
        np.testing.assert_allclose(mapped["action.ee"][:, 13], 1)

    def test_nonfinite_action_group_is_zeroed_and_masked(self) -> None:
        schema = GalaxeaSchema.from_info(make_info("r1lite", False))
        arrays = make_arrays(schema)
        arrays["action.left_arm"][1, 0] = np.nan
        mapped = map_robot_arrays(arrays, schema)

        np.testing.assert_array_equal(mapped["action.qpos_valid"], [[1, 1], [0, 1]])
        np.testing.assert_array_equal(mapped["action.qpos"][1, :7], 0)

    def test_every_feature_has_embodiment_and_origin(self) -> None:
        for robot_type, has_action_ee in (("r1lite", False), ("r1pro", True)):
            schema = GalaxeaSchema.from_info(make_info(robot_type, has_action_ee))
            features = build_unified_features(schema)
            expected = "R1-Lite" if robot_type == "r1lite" else "R1-Pro"
            for feature in features.values():
                self.assertIn(f"Embodiment: Galaxea {expected}.", feature["description"])
                self.assertIn("OriginData:", feature["description"])


if __name__ == "__main__":
    unittest.main()
