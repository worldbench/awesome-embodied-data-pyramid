from lerobot_quality.schema import ACTION_QPOS, STATE_QPOS, LeRobotSchema, arm_joint_indices


def info_for(arm_dof: int, effector_dof: int) -> dict:
    def names(prefix: str) -> list[str]:
        return [
            *[f"{prefix}/joint/position.left_joint_{i}" for i in range(arm_dof)],
            *[f"{prefix}/left_effector/position[{i}]" for i in range(effector_dof)],
            *[f"{prefix}/joint/position.right_joint_{i}" for i in range(arm_dof)],
            *[f"{prefix}/right_effector/position[{i}]" for i in range(effector_dof)],
        ]

    width = 2 * (arm_dof + effector_dof)
    return {
        "features": {
            STATE_QPOS: {"shape": [width], "names": {"motors": names("state")}},
            ACTION_QPOS: {"shape": [width], "names": {"motors": names("action")}},
        }
    }


def test_abc_14d_joint_indices() -> None:
    info = info_for(arm_dof=6, effector_dof=1)
    assert LeRobotSchema.from_info(info, require_ee=False).qpos_width == 14
    assert arm_joint_indices(info, STATE_QPOS, "left") == list(range(0, 6))
    assert arm_joint_indices(info, STATE_QPOS, "right") == list(range(7, 13))


def test_agibot_16d_joint_indices() -> None:
    info = info_for(arm_dof=7, effector_dof=1)
    assert LeRobotSchema.from_info(info, require_ee=False).qpos_width == 16
    assert arm_joint_indices(info, STATE_QPOS, "left") == list(range(0, 7))
    assert arm_joint_indices(info, STATE_QPOS, "right") == list(range(8, 15))


def test_beta_dexhand_26d_joint_indices() -> None:
    info = info_for(arm_dof=7, effector_dof=6)
    assert LeRobotSchema.from_info(info, require_ee=False).qpos_width == 26
    assert arm_joint_indices(info, STATE_QPOS, "left") == list(range(0, 7))
    assert arm_joint_indices(info, STATE_QPOS, "right") == list(range(13, 20))
