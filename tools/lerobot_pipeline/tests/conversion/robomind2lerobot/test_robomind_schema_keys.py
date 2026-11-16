import sys
import types
import unittest
from pathlib import Path

import numpy as np



sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "converters" / "robomind2lerobot"))

from robomind_uitls.configs import ROBOMIND_CONFIG  # noqa: E402
from robomind_uitls.lerobot_uitls import generate_features_from_config, remap_numeric_arrays  # noqa: E402


class RoboMINDSchemaKeyTest(unittest.TestCase):
    def test_fr3_dual_uses_unified_robot_keys(self) -> None:
        config = ROBOMIND_CONFIG["franka_fr3_dual"]
        features = generate_features_from_config(config, "franka_fr3_dual")
        self.assertEqual(features["state.ee"]["shape"], (12,))
        self.assertEqual(features["state.qpos"]["shape"], (16,))
        self.assertEqual(features["action.qpos_valid"]["shape"], (1,))
        self.assertFalse(any(key.startswith("observation.states.") for key in features))
        raw_states = {key: np.zeros((2, *feature["shape"]), dtype=np.float32)
                      for key, feature in config["states"].items()}
        remapped = remap_numeric_arrays(raw_states, config, "states", "state")
        self.assertEqual(remapped["state.ee"].shape, (2, 12))
        self.assertEqual(remapped["state.qpos"].shape, (2, 16))

    def test_non_pose_end_effector_stays_named_as_end_effector(self) -> None:
        config = ROBOMIND_CONFIG["tienkung_xsens_1rgb"]
        features = generate_features_from_config(config, "tienkung_xsens_1rgb")

        self.assertIn("state.qpos", features)
        self.assertIn("action.qpos", features)
        self.assertIn("state.end_effector", features)
        self.assertIn("action.end_effector", features)
        self.assertNotIn("state.ee", features)
        self.assertNotIn("action.ee", features)
        self.assertIn("action.end_effector_valid", features)

    def test_action_validity_is_computed_per_source_group(self) -> None:
        config = ROBOMIND_CONFIG["franka_fr3_dual"]
        raw_actions = {
            key: np.ones((2, *feature["shape"]), dtype=np.float32)
            for key, feature in config["actions"].items()
        }
        raw_actions["joint_position"][1, 0] = np.nan

        remapped = remap_numeric_arrays(
            raw_actions,
            config,
            "actions",
            "action",
            include_action_validity=True,
        )

        np.testing.assert_array_equal(remapped["action.qpos_valid"], [[1], [0]])
        np.testing.assert_array_equal(remapped["action.qpos"][1], 0)

    def test_every_embodiment_declares_metadata_for_every_action(self) -> None:
        for embodiment, config in ROBOMIND_CONFIG.items():
            if not isinstance(config, dict):
                continue
            features = generate_features_from_config(config, embodiment)
            action_keys = [
                key
                for key in features
                if key.startswith("action.") and not key.endswith("_valid")
            ]
            self.assertTrue(action_keys, embodiment)
            for key in action_keys:
                self.assertIn("description", features[key], f"{embodiment}: {key}")
                self.assertIn(f"{key}_valid", features, f"{embodiment}: {key}")
                self.assertIn(
                    "description",
                    features[f"{key}_valid"],
                    f"{embodiment}: {key}_valid",
                )
            for key, feature in features.items():
                self.assertIn(
                    f"Embodiment: {embodiment}.",
                    feature["description"],
                    f"{embodiment}: {key}",
                )
                self.assertIn(
                    "OriginData:",
                    feature["description"],
                    f"{embodiment}: {key}",
                )


if __name__ == "__main__":
    unittest.main()
