import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from lerobot_quality.signal_quality import validate_repo
from lerobot_quality.adapters import profiles


def fixed(values: np.ndarray) -> pa.FixedSizeListArray:
    return pa.FixedSizeListArray.from_arrays(
        pa.array(values.reshape(-1), type=pa.float32()), values.shape[1]
    )


def write_beta_repo(root: Path, effector_dof: int) -> None:
    arm_dof = 7
    width = 2 * (arm_dof + effector_dof)
    profile = profiles()['beta_a2d_gripper' if effector_dof == 1 else 'beta_a2d_dexhand']
    def names(prefix: str) -> list[str]:
        return profile['qpos_names'][prefix+'.qpos']
    features = {
        "state.qpos": {"shape": [width], "names": {"motors": names("state")}},
        "action.qpos": {"shape": [width], "names": {"motors": names("action")}},
        "state.ee": {"shape": [14]},
        "action.ee": {"shape": [14]},
        "state.ee_valid": {"shape": [2]},
        "action.ee_valid": {"shape": [2]},
    }
    (root / "meta").mkdir(parents=True)
    (root / "meta" / "info.json").write_text(json.dumps({"robot_type":profile["robot_type"], "features": features}))
    (root / "data").mkdir()
    frames = 4
    qpos = np.zeros((frames, width), dtype=np.float32)
    qpos[:, 0] = np.arange(frames) * 0.01
    ee = np.zeros((frames, 14), dtype=np.float32)
    ee[:, [6, 13]] = 1.0
    valid = np.ones((frames, 2), dtype=np.float32)
    pq.write_table(
        pa.table(
            {
                "episode_index": pa.array([0] * frames, pa.int64()),
                "frame_index": pa.array(range(frames), pa.int64()),
                "state.qpos": fixed(qpos),
                "action.qpos": fixed(qpos),
                "state.ee": fixed(ee),
                "action.ee": fixed(ee),
                "state.ee_valid": fixed(valid),
                "action.ee_valid": fixed(valid),
            }
        ),
        root / "data" / "part.parquet",
    )


def test_beta_gripper_and_dexhand_layouts(tmp_path: Path) -> None:
    for effector_dof, width, right_start in ((1, 16, 8), (6, 26, 13)):
        repo = tmp_path / f"beta_{width}"
        write_beta_repo(repo, effector_dof)
        summary = validate_repo(repo, tmp_path / f"report_{width}", write_frames=True)
        assert summary["qpos_width"] == width
        assert summary["arm_joint_indices"]["state.qpos"][7] == right_start
        assert summary["invalid_frames"] == 0
