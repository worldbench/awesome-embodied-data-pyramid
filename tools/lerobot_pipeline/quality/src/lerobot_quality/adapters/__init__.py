"""Embodiment and release-specific contracts feeding the shared quality checks.

Adapters describe source semantics; they do not repair, normalize or rewrite data.
Selection requires robot identity AND exact qpos motor names, never vector width alone.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
import pyarrow as pa

from ..schema import feature_width, fixed_list_numpy, motor_names


@lru_cache(maxsize=1)
def profiles() -> dict[str, dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(
        (Path(__file__).parent / "profiles").glob("*.json")) if not p.name.startswith(".")}


@dataclass(frozen=True)
class RobotAdapter:
    profile: dict
    info: dict

    @property
    def name(self) -> str:
        return self.profile['id']

    @property
    def qpos_width(self) -> int:
        return self.profile['qpos_width']

    @property
    def arm_indices(self) -> dict[str, list[int]]:
        return self.profile['arm_indices']

    @property
    def ee_sides(self) -> list[str]:
        return self.profile['ee_sides']

    @property
    def columns(self) -> list[str]:
        return [k for k in self.profile['feature_widths'] if k in self.info['features']]

    @property
    def joint_keys(self) -> list[str]:
        return [k for k in ('state.qpos', 'action.qpos') if k in self.columns]

    @property
    def pose_keys(self) -> list[str]:
        if self.profile['ee_representation'] not in ('xyz_xyzw', 'xyz_euler_xyz', 'xyz_rotvec'):
            return []
        return [k for k in ('state.ee', 'action.ee') if k in self.columns]

    @property
    def extra_keys(self) -> list[str]:
        return [k for k in self.columns if k not in ('state.qpos', 'action.qpos')
                and k not in self.pose_keys and not k.endswith('_valid')]

    def validate(self) -> None:
        if not {'state.qpos', 'state.ee'} & set(self.columns):
            raise ValueError(f'{self.name}: requires observed joint positions or EE')
        for key in self.joint_keys:
            if feature_width(self.info, key) != self.qpos_width:
                raise ValueError(f'{self.name}: incompatible {key} width')
            if motor_names(self.info, key) != self.profile['qpos_names'][key]:
                raise ValueError(f'{self.name}: {key} motor order differs from adapter contract')
        for key in self.columns:
            if feature_width(self.info, key) != self.profile['feature_widths'][key]:
                raise ValueError(f'{self.name}: incompatible {key} width')
        # Unknown robot signals must be mapped explicitly, not silently ignored.
        unknown = {k for k in self.info['features'] if k.startswith(('state.', 'action.'))} - set(self.columns)
        if unknown:
            raise ValueError(f'{self.name}: unmapped robot features {sorted(unknown)}')
        if self.profile['ee_representation'] == 'xyz_xyzw':
            for key in ('state.ee', 'action.ee'):
                if (key in self.columns) != (key+'_valid' in self.columns):
                    raise ValueError(f'{self.name}: partial EE schema; expected {key} and {key}_valid together')
        if 'action.qpos_valid' in self.columns and 'action.qpos' not in self.columns:
            raise ValueError(f'{self.name}: action.qpos_valid requires action.qpos')

    def arrays(self, table: pa.Table) -> dict[str, np.ndarray]:
        arrays = {k: fixed_list_numpy(table[k], self.profile['feature_widths'][k])
                  for k in self.columns if k in table.column_names}
        representation = self.profile['ee_representation']
        for key in self.pose_keys:
            if key not in arrays:
                continue
            if representation != 'xyz_xyzw':
                native = arrays[key].reshape(len(table), len(self.ee_sides), -1)
                rotation = native[:, :, 3:6]
                if representation == 'xyz_rotvec':
                    theta = np.linalg.norm(rotation, axis=2, keepdims=True)
                    quaternion = np.concatenate((rotation * np.sinc(theta / (2*np.pi)) / 2,
                                                 np.cos(theta/2)), axis=2)
                else:
                    r, pitch, y = np.moveaxis(rotation / 2, -1, 0)
                    cr, sr = np.cos(r), np.sin(r)
                    cp, sp = np.cos(pitch), np.sin(pitch)
                    cy, sy = np.cos(y), np.sin(y)
                    quaternion = np.stack((sr*cp*cy-cr*sp*sy, cr*sp*cy+sr*cp*sy,
                                           cr*cp*sy-sr*sp*cy, cr*cp*cy+sr*sp*sy), axis=2)
                arrays[key] = np.concatenate((native[:, :, :3], quaternion), axis=2).reshape(len(table), -1)
            # Native RoboMIND poses have no measured-pose mask. Nonfinite values
            # remain active so signal checks flag them instead of hiding them.
            arrays.setdefault(key + '_valid', np.ones((len(table), len(self.ee_sides))))
        return arrays

    def active_dimensions(self, key: str, arrays: dict[str, np.ndarray]) -> np.ndarray:
        width = self.profile['feature_widths'][key]
        active = np.ones_like(arrays[key], dtype=bool)
        mask = arrays.get(key + '_valid')
        if mask is None:
            return active
        if key == 'action.qpos':
            groups = self.profile['action_mask_groups']
        elif key in self.pose_keys:
            groups = [list(range(i*7, (i+1)*7)) for i in range(len(self.ee_sides))]
        else:
            if width % mask.shape[1]:
                raise ValueError(f'{self.name}: cannot map {key} mask to dimensions')
            groups = np.array_split(np.arange(width), mask.shape[1])
        if len(groups) != mask.shape[1]:
            raise ValueError(f'{self.name}: {key} mask group count mismatch')
        for i, group in enumerate(groups):
            active[:, group] = (mask[:, i] == 1)[:, None]
        return active

    def coverage(self) -> dict:
        return {
            'adapter': self.name,
            'source_family': self.profile['source_family'],
            'format_version': self.profile['format_version'],
            'ee_representation': self.profile['ee_representation'],
            'joint_checks': self.joint_keys,
            'ee_pose_checks': self.pose_keys,
            'implicit_pose_masks': [key+'_valid' for key in self.pose_keys if key+'_valid' not in self.columns],
            'fk_calibration_status': self.profile.get('fk_calibration_status'),
            'finite_only_signals': self.extra_keys,
            'masks': [k for k in self.columns if k.endswith('_valid')],
            'missing_optional_signals': sorted(set(self.profile['feature_widths']) - set(self.columns)),
            'default_fk_config': self.profile.get('default_fk_config'),
            'fk_comparison_unavailable_reason': self.profile.get('fk_comparison_unavailable_reason'),
            'notes': self.profile.get('notes', []),
        }


def resolve_adapter(info: dict, name: str = 'auto') -> RobotAdapter:
    robot = info.get('robot_type')
    if name != 'auto':
        if name not in profiles():
            raise ValueError(f'unknown adapter {name!r}; available: {sorted(profiles())}')
        profile = profiles()[name]
        if robot and robot != profile['robot_type']:
            raise ValueError(f'adapter {name} expects robot_type={profile["robot_type"]!r}, got {robot!r}')
    elif not robot:
        raise ValueError('robot_type is required; choose a manifest adapter explicitly')
    else:
        candidates = [p for p in profiles().values() if p['robot_type'] == robot
                      and all(motor_names(info,k) == p['qpos_names'][k]
                              for k in ('state.qpos','action.qpos') if k in info['features'])]
        if len(candidates) != 1:
            raise ValueError(f'no unique adapter for robot_type={robot!r} and qpos names; select or add an explicit profile')
        profile = candidates[0]
    adapter = RobotAdapter(profile, info)
    adapter.validate()
    return adapter
