"""Checks for action descriptions and validity masks in the shared Beta converter."""

from __future__ import annotations

import unittest

import numpy as np

from agibot2lerobot.agibot_utils.agibot_utils import sanitize_action_array
from agibot2lerobot.agibot_utils.config import AgiBotWorld_TASK_TYPE
from agibot2lerobot.agibot_utils.lerobot_utils import generate_features_from_config


class ActionMetadataTest(unittest.TestCase):
    def test_every_action_has_description_and_validity_feature(self) -> None:
        for task_type in AgiBotWorld_TASK_TYPE.values():
            features = generate_features_from_config(
                task_type["task_config"],
                embodiment="A2D test",
            )
            action_keys = [
                key
                for key in features
                if key.startswith("actions.") and not key.endswith("_valid")
            ]
            self.assertTrue(action_keys)
            for key in action_keys:
                self.assertIn("description", features[key])
                self.assertEqual(features[f"{key}_valid"]["shape"], (1,))
                self.assertIn("description", features[f"{key}_valid"])
            for feature in features.values():
                self.assertIn("Embodiment: A2D test.", feature["description"])
                self.assertIn("OriginData:", feature["description"])

    def test_missing_and_nonfinite_actions_are_masked(self) -> None:
        missing, missing_valid = sanitize_action_array(
            np.empty((0, 2), dtype=np.float32), 2, (2,), "float32"
        )
        np.testing.assert_array_equal(missing, 0)
        np.testing.assert_array_equal(missing_valid, 0)

        values = np.asarray([[1, 2], [np.nan, 3]], dtype=np.float32)
        sanitized, valid = sanitize_action_array(values, 2, (2,), "float32")
        np.testing.assert_array_equal(valid[:, 0], [1, 0])
        np.testing.assert_array_equal(sanitized[1], 0)


if __name__ == "__main__":
    unittest.main()
