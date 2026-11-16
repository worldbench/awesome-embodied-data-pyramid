"""Small, dependency-free URDF forward-kinematics implementation.

Only kinematic information is parsed. Meshes, inertials, transmissions and
Gazebo extensions are deliberately ignored so validation can run on a data
worker without ROS or Pinocchio.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np


def _values(text: str | None, size: int, default: tuple[float, ...]) -> np.ndarray:
    if text is None:
        return np.asarray(default, dtype=np.float64)
    result = np.fromstring(text, sep=" ", dtype=np.float64)
    if result.shape != (size,):
        raise ValueError(f"expected {size} values, got {text!r}")
    return result


def rotation_from_rpy(rpy: np.ndarray) -> np.ndarray:
    roll, pitch, yaw = rpy
    cr, sr = np.cos(roll), np.sin(roll)
    cp, sp = np.cos(pitch), np.sin(pitch)
    cy, sy = np.cos(yaw), np.sin(yaw)
    rx = np.array(((1, 0, 0), (0, cr, -sr), (0, sr, cr)))
    ry = np.array(((cp, 0, sp), (0, 1, 0), (-sp, 0, cp)))
    rz = np.array(((cy, -sy, 0), (sy, cy, 0), (0, 0, 1)))
    return rz @ ry @ rx


def transform(
    rotation: np.ndarray | None = None, translation: np.ndarray | None = None
) -> np.ndarray:
    result = np.eye(4, dtype=np.float64)
    if rotation is not None:
        result[:3, :3] = rotation
    if translation is not None:
        result[:3, 3] = translation
    return result


def axis_angle(axis: np.ndarray, angle: float) -> np.ndarray:
    norm = np.linalg.norm(axis)
    if norm < 1e-12:
        raise ValueError("joint axis has zero length")
    x, y, z = axis / norm
    c, s, one_c = np.cos(angle), np.sin(angle), 1.0 - np.cos(angle)
    return np.array(
        (
            (c + x * x * one_c, x * y * one_c - z * s, x * z * one_c + y * s),
            (y * x * one_c + z * s, c + y * y * one_c, y * z * one_c - x * s),
            (z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c),
        ),
        dtype=np.float64,
    )


@dataclass(frozen=True)
class Joint:
    name: str
    kind: str
    parent: str
    child: str
    origin: np.ndarray
    axis: np.ndarray

    def motion(self, position: float) -> np.ndarray:
        if self.kind in {"revolute", "continuous"}:
            return transform(rotation=axis_angle(self.axis, position))
        if self.kind == "prismatic":
            norm = np.linalg.norm(self.axis)
            if norm < 1e-12:
                raise ValueError(f"joint axis has zero length for {self.name}")
            return transform(translation=self.axis / norm * position)
        if self.kind == "fixed":
            return np.eye(4, dtype=np.float64)
        raise ValueError(f"unsupported URDF joint type {self.kind!r} for {self.name}")

    def motion_batch(self, positions: np.ndarray) -> np.ndarray:
        """Return one homogeneous joint-motion matrix per position."""
        positions = np.asarray(positions, dtype=np.float64)
        result = np.broadcast_to(np.eye(4), (len(positions), 4, 4)).copy()
        norm = np.linalg.norm(self.axis)
        if norm < 1e-12:
            raise ValueError(f"joint axis has zero length for {self.name}")
        axis = self.axis / norm
        if self.kind in {"revolute", "continuous"}:
            x, y, z = axis
            c, s, one_c = np.cos(positions), np.sin(positions), 1.0 - np.cos(positions)
            result[:, 0, 0] = c + x * x * one_c
            result[:, 0, 1] = x * y * one_c - z * s
            result[:, 0, 2] = x * z * one_c + y * s
            result[:, 1, 0] = y * x * one_c + z * s
            result[:, 1, 1] = c + y * y * one_c
            result[:, 1, 2] = y * z * one_c - x * s
            result[:, 2, 0] = z * x * one_c - y * s
            result[:, 2, 1] = z * y * one_c + x * s
            result[:, 2, 2] = c + z * z * one_c
            return result
        if self.kind == "prismatic":
            result[:, :3, 3] = positions[:, None] * axis
            return result
        if self.kind == "fixed":
            return result
        raise ValueError(f"unsupported URDF joint type {self.kind!r} for {self.name}")


class UrdfModel:
    def __init__(self, links: set[str], joints: list[Joint]):
        self.links = links
        self.joints = joints
        self.joint_by_name = {joint.name: joint for joint in joints}
        self.parent_joint_by_child = {joint.child: joint for joint in joints}
        if len(self.joint_by_name) != len(joints):
            raise ValueError("URDF contains duplicate joint names")
        if len(self.parent_joint_by_child) != len(joints):
            raise ValueError("URDF contains a link with multiple parent joints")

    @classmethod
    def load(cls, path: Path) -> "UrdfModel":
        root = ET.parse(path).getroot()
        links = {node.attrib["name"] for node in root.findall("link")}
        joints: list[Joint] = []
        for node in root.findall("joint"):
            origin_node = node.find("origin")
            xyz = _values(origin_node.get("xyz") if origin_node is not None else None, 3, (0, 0, 0))
            rpy = _values(origin_node.get("rpy") if origin_node is not None else None, 3, (0, 0, 0))
            axis_node = node.find("axis")
            axis = _values(axis_node.get("xyz") if axis_node is not None else None, 3, (1, 0, 0))
            parent_node, child_node = node.find("parent"), node.find("child")
            if parent_node is None or child_node is None:
                raise ValueError(f"joint {node.attrib.get('name')} lacks parent/child")
            joints.append(
                Joint(
                    name=node.attrib["name"],
                    kind=node.attrib["type"],
                    parent=parent_node.attrib["link"],
                    child=child_node.attrib["link"],
                    origin=transform(rotation_from_rpy(rpy), xyz),
                    axis=axis,
                )
            )
        return cls(links, joints)

    def chain(self, base_link: str, tip_link: str) -> list[Joint]:
        if base_link not in self.links or tip_link not in self.links:
            raise ValueError(f"unknown base/tip link: {base_link!r}, {tip_link!r}")
        result: list[Joint] = []
        current = tip_link
        visited: set[str] = set()
        while current != base_link:
            if current in visited:
                raise ValueError(f"cycle while resolving chain to {tip_link}")
            visited.add(current)
            joint = self.parent_joint_by_child.get(current)
            if joint is None:
                raise ValueError(f"{base_link!r} is not an ancestor of {tip_link!r}")
            result.append(joint)
            current = joint.parent
        result.reverse()
        return result

    def forward(self, base_link: str, tip_link: str, positions: dict[str, float]) -> np.ndarray:
        result = np.eye(4, dtype=np.float64)
        for joint in self.chain(base_link, tip_link):
            result = result @ joint.origin
            if joint.kind != "fixed":
                if joint.name not in positions:
                    raise ValueError(f"missing position for joint {joint.name!r}")
                result = result @ joint.motion(float(positions[joint.name]))
        return result

    def forward_batch(
        self, base_link: str, tip_link: str, positions: dict[str, np.ndarray]
    ) -> np.ndarray:
        lengths = {len(np.asarray(value)) for value in positions.values()}
        if len(lengths) != 1:
            raise ValueError("all batch joint-position arrays must have the same length")
        size = lengths.pop() if lengths else 0
        result = np.broadcast_to(np.eye(4), (size, 4, 4)).copy()
        for joint in self.chain(base_link, tip_link):
            result = result @ joint.origin
            if joint.kind != "fixed":
                if joint.name not in positions:
                    raise ValueError(f"missing position for joint {joint.name!r}")
                result = result @ joint.motion_batch(positions[joint.name])
        return result
