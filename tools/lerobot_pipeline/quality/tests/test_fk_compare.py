import json
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from lerobot_quality.fk_compare import compare_repo, load_config


def fixed(values: np.ndarray) -> pa.FixedSizeListArray:
    flat = pa.array(values.reshape(-1), type=pa.float32())
    return pa.FixedSizeListArray.from_arrays(flat, values.shape[1])


def test_fk_uses_state_qpos_and_state_ee(tmp_path: Path) -> None:
    urdf = tmp_path / "robot.urdf"
    joints = ['<robot name="test"><link name="base"/>']
    parent = 'base'
    for index in range(7):
        link=f'arm{index}'
        joints.append(f'<link name="{link}"/><joint name="joint{index}" type="revolute">'
                      f'<parent link="{parent}"/><child link="{link}"/><axis xyz="0 0 1"/></joint>')
        parent=link
    joints.append(f'<link name="tip"/><joint name="tool" type="fixed"><parent link="{parent}"/>'
                  '<child link="tip"/><origin xyz="1 0 0"/></joint></robot>')
    urdf.write_text(''.join(joints))
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_version": "lerobot_fk_config_v1",
                "urdf": str(urdf),
                "active_sides": ["left"],
                "base_link": "base",
                "left_ee_link": "tip",
                "left_joint_names": [f"joint{i}" for i in range(7)],
                "qpos_widths": [8],
            }
        )
    )
    repo = tmp_path / "repo"
    (repo / "meta").mkdir(parents=True)
    from test_adapters import info_for_profile
    info = info_for_profile('interndata_franka')
    (repo / "meta" / "info.json").write_text(json.dumps(info))
    (repo / "data").mkdir()
    qpos = np.asarray([[np.pi / 2, 0, 0, 0, 0, 0, 0, 0]], dtype=np.float32)
    ee = np.zeros((1, 7), dtype=np.float32)
    ee[0, :7] = [0, 1, 0, 0, 0, np.sqrt(0.5), np.sqrt(0.5)]
    valid = np.asarray([[1]], dtype=np.float32)
    pq.write_table(
        pa.table(
            {
                "episode_index": pa.array([0], pa.int64()),
                "frame_index": pa.array([0], pa.int64()),
                "state.qpos": fixed(qpos),
                "state.ee": fixed(ee),
                "state.ee_valid": fixed(valid),
            }
        ),
        repo / "data" / "part.parquet",
    )
    summary = compare_repo(
        repo,
        config,
        tmp_path / "report",
        position_threshold_m=1e-6,
        rotation_threshold_deg=1e-4,
        write_frames=True,
    )
    assert summary["valid_frames"] == 1
    assert summary["pass_frames"] == 1


def test_shipped_configs_and_urdfs_resolve() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("agibotworld2026_g2.json", "abc130k_yam.json"):
        config = load_config(root / "configs" / name)
        assert config["urdf"].is_file()


def test_incompatible_config_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "incompatible.json"
    path.write_text(json.dumps({"schema_version": "legacy_fk_config_v1"}))
    try:
        load_config(path)
    except ValueError as error:
        assert "schema_version must be" in str(error)
    else:
        raise AssertionError("old config unexpectedly accepted")
