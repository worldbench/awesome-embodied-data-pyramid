"""Fast unit checks for AgiBotWorld2026 field mapping and unified schema."""

from __future__ import annotations

import unittest

import numpy as np

from agibotworld2026_2lerobot.convert_agibotworld2026 import (
    ACTION_EE_NAMES,
    ACTION_QPOS_NAMES,
    FieldMapping,
    STATE_EE_NAMES,
    STATE_QPOS_NAMES,
    _nonfinite_paths,
    build_unified_features,
    map_robot_vectors,
)


def make_info(state_width: int = 169, action_width: int = 40) -> dict:
    """Build one observed AgiBot schema variant with realistic source indices."""
    return {
        "features": {
            "observation.state": {
                "shape": [state_width],
                "field_descriptions": {
                    "state/left_effector/position": {"indices": [0]},
                    "state/right_effector/position": {"indices": [1]},
                    "state/end/arm_orientation": {
                        "indices": list(range(26, 34))
                    },
                    "state/end/arm_position": {"indices": list(range(34, 40))},
                    "state/joint/position": {"indices": list(range(40, 54))},
                    "state/waist/position": {"indices": list(range(85, 90))},
                },
            },
            "action": {
                "shape": [action_width],
                "field_descriptions": {
                    "action/left_effector/position": {"indices": [0]},
                    "action/right_effector/position": {"indices": [1]},
                    "action/end/position": {"indices": list(range(2, 8))},
                    "action/end/orientation": {"indices": list(range(8, 16))},
                    "action/joint/position": {"indices": list(range(16, 30))},
                    "action/waist/position": {"indices": list(range(33, 38))},
                },
            },
        }
    }


class MappingTest(unittest.TestCase):
    def test_waist_mapping_tracks_source_layout_and_preserves_values(self) -> None:
        for width, start in ((169, 85), (183, 99), (193, 109), (216, 127)):
            info = make_info(state_width=width, action_width=44)
            info["features"]["observation.state"]["field_descriptions"]["state/waist/position"]["indices"] = list(range(start, start + 5))
            mapping = FieldMapping.from_info(info)
            state = np.arange(3 * width, dtype=np.float32).reshape(3, width)
            action = np.arange(3 * 44, dtype=np.float32).reshape(3, 44)
            mapped = map_robot_vectors(state, action, mapping)
            np.testing.assert_array_equal(mapped["state.waist"], state[:, start:start + 5])
            np.testing.assert_array_equal(mapped["action.waist"], action[:, 33:38])

    def test_waist_missing_or_nonfinite_is_not_silently_filled(self) -> None:
        info = make_info()
        del info["features"]["action"]["field_descriptions"]["action/waist/position"]
        with self.assertRaisesRegex(ValueError, "action/waist/position"):
            FieldMapping.from_info(info)
        mapping = FieldMapping.from_info(make_info())
        for key in ("state", "action"):
            state, action = np.zeros((1, 169)), np.zeros((1, 40))
            (state if key == "state" else action)[0, getattr(mapping, f"{key}_waist")[0]] = np.nan
            with self.assertRaisesRegex(ValueError, f"{key}.waist"):
                map_robot_vectors(state, action, mapping)

    def test_mapping_uses_semantic_indices(self) -> None:
        mapping = FieldMapping.from_info(make_info())
        self.assertEqual(
            mapping.state_qpos,
            (*range(40, 47), 0, *range(47, 54), 1),
        )
        self.assertEqual(
            mapping.state_ee,
            (*range(34, 37), *range(26, 30), *range(37, 40), *range(30, 34)),
        )
        self.assertEqual(
            mapping.action_qpos,
            (*range(16, 23), 0, *range(23, 30), 1),
        )
        self.assertEqual(
            mapping.action_ee,
            (*range(2, 5), *range(8, 12), *range(5, 8), *range(12, 16)),
        )

    def test_required_mapping_is_stable_for_action_width_44(self) -> None:
        mapping_40 = FieldMapping.from_info(make_info(action_width=40))
        mapping_44 = FieldMapping.from_info(make_info(action_width=44))
        self.assertEqual(mapping_40.action_qpos, mapping_44.action_qpos)
        self.assertEqual(mapping_40.action_ee, mapping_44.action_ee)

    def test_map_normalizes_quaternions_and_masks_invalid_side(self) -> None:
        mapping = FieldMapping.from_info(make_info())
        state = np.arange(2 * 169, dtype=np.float32).reshape(2, 169)
        action = np.arange(2 * 40, dtype=np.float32).reshape(2, 40)

        # Both sides valid in row 0. Right state and left action invalid in row 1.
        state[0, 26:34] = [0, 0, 0, 2, 0, 0, 0, 4]
        action[0, 8:16] = [0, 0, 0, 3, 0, 0, 0, 5]
        state[1, 26:34] = [0, 0, 0, 1, 0, 0, 0, 0]
        action[1, 8:16] = [0, 0, 0, 0, 0, 0, 0, 1]

        mapped = map_robot_vectors(state, action, mapping)
        np.testing.assert_allclose(
            np.linalg.norm(mapped["state.ee"][0, [3, 4, 5, 6]]),
            1.0,
        )
        np.testing.assert_allclose(
            np.linalg.norm(mapped["action.ee"][0, [10, 11, 12, 13]]),
            1.0,
        )
        np.testing.assert_array_equal(mapped["state.ee_valid"][1], [1, 0])
        np.testing.assert_array_equal(mapped["action.ee_valid"][1], [0, 1])
        np.testing.assert_array_equal(mapped["state.ee"][1, 7:14], 0)
        np.testing.assert_array_equal(mapped["action.ee"][1, 0:7], 0)

    def test_nonfinite_qpos_is_rejected(self) -> None:
        mapping = FieldMapping.from_info(make_info())
        state = np.zeros((1, 169), dtype=np.float32)
        action = np.zeros((1, 40), dtype=np.float32)
        state[0, 40] = np.nan
        with self.assertRaisesRegex(ValueError, "state.qpos"):
            map_robot_vectors(state, action, mapping)

    def test_nonfinite_action_qpos_is_zeroed_and_masked_per_side(self) -> None:
        mapping = FieldMapping.from_info(make_info())
        state = np.zeros((1, 169), dtype=np.float32)
        action = np.zeros((1, 40), dtype=np.float32)
        action[0, mapping.action_qpos[0]] = np.nan
        mapped = map_robot_vectors(state, action, mapping)
        np.testing.assert_array_equal(mapped["action.qpos_valid"], [[0, 1]])
        np.testing.assert_array_equal(mapped["action.qpos"][0, :8], 0)


class SchemaTest(unittest.TestCase):
    def test_schema_matches_project_template(self) -> None:
        features = build_unified_features(fps=30)
        self.assertEqual(features["state.qpos"]["shape"], [16])
        self.assertEqual(features["action.qpos"]["shape"], [16])
        self.assertEqual(features["state.waist"]["shape"], [5])
        self.assertEqual(features["action.waist"]["shape"], [5])
        self.assertEqual(features["action.qpos_valid"]["shape"], [2])
        self.assertEqual(features["state.ee"]["shape"], [14])
        self.assertEqual(features["action.ee"]["shape"], [14])
        self.assertEqual(features["state.ee_valid"]["shape"], [2])
        self.assertEqual(features["action.ee_valid"]["shape"], [2])
        self.assertIn("description", features["action.qpos"])
        self.assertIn("description", features["action.qpos_valid"])
        self.assertEqual(features["state.qpos"]["names"]["motors"], STATE_QPOS_NAMES)
        self.assertEqual(features["action.qpos"]["names"]["motors"], ACTION_QPOS_NAMES)
        self.assertEqual(features["state.ee"]["names"]["motors"], STATE_EE_NAMES)
        self.assertEqual(features["action.ee"]["names"]["motors"], ACTION_EE_NAMES)
        for feature in features.values():
            self.assertIn("Embodiment: AgiBot G2 dual-arm.", feature["description"])
            self.assertIn("OriginData:", feature["description"])

        mapping = FieldMapping.from_info(make_info())
        mapped = map_robot_vectors(
            np.zeros((1, 169), dtype=np.float32),
            np.zeros((1, 40), dtype=np.float32),
            mapping,
        )
        np.testing.assert_array_equal(mapped["action.qpos_valid"], [[1, 1]])

    def test_nonfinite_stats_are_reported_by_path(self) -> None:
        payload = {
            "clean": np.asarray([1.0, 2.0]),
            "bad": {"mean": np.asarray([0.0, np.nan, np.inf])},
        }
        self.assertEqual(
            _nonfinite_paths(payload),
            ["/bad/mean[1]", "/bad/mean[2]"],
        )


if __name__ == "__main__":
    unittest.main()
