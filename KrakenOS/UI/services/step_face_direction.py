"""Imported STEP face-direction alignment helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import numpy as np


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


@dataclass(frozen=True, slots=True)
class StepFaceDirectionPlan:
    """Planned imported STEP pose after aligning a picked face normal."""

    label: str
    face_id: str
    direction_label: str
    surface_center: tuple[float, float, float]
    target_direction: tuple[float, float, float]
    rotation_deg: tuple[float, float, float]
    placement_offset_xyz: tuple[float, float, float]
    angle_error_deg: float

    def as_result(self) -> dict[str, object]:
        return {
            "label": self.label,
            "face_id": self.face_id,
            "direction_label": self.direction_label,
            "surface_center": self.surface_center,
            "target_direction": self.target_direction,
            "rotation_deg": self.rotation_deg,
            "placement_offset_xyz": self.placement_offset_xyz,
            "angle_error_deg": self.angle_error_deg,
        }


class StepFaceDirectionService:
    """Plan Right/Left/Up/Down/Front/Back alignment for imported STEP faces."""

    DIRECTION_VECTORS: dict[str, tuple[float, float, float]] = {
        "left": (0.0, 0.0, -1.0),
        "right": (0.0, 0.0, 1.0),
        "up": (0.0, 1.0, 0.0),
        "down": (0.0, -1.0, 0.0),
        "front": (1.0, 0.0, 0.0),
        "back": (-1.0, 0.0, 0.0),
    }

    def __init__(self, editor: Any, *, valid_labels: Iterable[str]) -> None:
        self.editor = editor
        self.valid_labels = {str(label).strip().lower() for label in valid_labels}

    @classmethod
    def direction_vector(cls, direction_label: object) -> np.ndarray | None:
        text = str(direction_label or "").strip().lower().replace("_", " ").replace("-", " ")
        value = cls.DIRECTION_VECTORS.get(text)
        return None if value is None else np.asarray(value, dtype=float)

    @staticmethod
    def _finite_xyz(values: object) -> np.ndarray | None:
        try:
            array = np.asarray(values, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if array.size < 3 or not np.all(np.isfinite(array[:3])):
            return None
        return np.asarray(array[:3], dtype=float)

    @staticmethod
    def _mesh_points(mesh: object) -> np.ndarray | None:
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        points = np.asarray(getattr(mesh, "points", np.empty((0, 3))), dtype=float)
        if points.ndim != 2 or points.shape[0] < 4 or points.shape[1] < 3:
            return None
        if not np.all(np.isfinite(points[:, :3])):
            return None
        return np.asarray(points[:, :3], dtype=float)

    @staticmethod
    def _direction_label_text(direction_label: object) -> str:
        return str(direction_label or "").strip().title()

    def plan_overlay_face_direction(
        self,
        label: str,
        feature_center_xyz: object,
        feature_normal_xyz: object,
        direction_label: str,
        *,
        face_id: str = "",
    ) -> StepFaceDirectionPlan | None:
        label = str(label).strip().lower()
        if label not in self.valid_labels:
            return None
        if self.editor._step_path_for_label(label) is None:
            raise ValueError(f"No {label} STEP is imported.")

        target_normal = self.direction_vector(direction_label)
        if target_normal is None:
            raise ValueError("STEP Face Direction must be Left, Right, Up, Down, Front, or Back.")
        feature_center = self._finite_xyz(feature_center_xyz)
        feature_normal = self._finite_xyz(feature_normal_xyz)
        if feature_center is None or feature_normal is None:
            raise ValueError("STEP Face Direction needs a finite picked STEP face center and normal.")

        feature_normal = self.editor._normalized_vector(feature_normal[:3])
        target_normal = self.editor._normalized_vector(target_normal[:3])

        current_mesh = self.editor._transformed_imported_step_mesh_for_label(label)
        current_points = self._mesh_points(current_mesh)
        if current_points is None:
            raise ValueError(f"{label.upper()} STEP mesh does not have enough points for face-direction alignment.")

        current_angles = self.editor._step_rotation_deg_tuple(label)
        current_offset = np.asarray(self.editor._step_placement_offset_xyz(label), dtype=float).reshape(3)
        current_matrix = self.editor._step_rotation_matrix_from_angles(*current_angles)
        delta_matrix = self.editor._rotation_matrix_between_vectors(feature_normal, target_normal)
        next_matrix = delta_matrix @ current_matrix
        next_angles = self.editor._step_angles_from_rotation_matrix(next_matrix)

        self.editor._set_step_rotation_deg_tuple(label, next_angles)
        try:
            rotated_mesh = self.editor._transformed_imported_step_mesh_for_label(label)
        finally:
            self.editor._set_step_rotation_deg_tuple(label, current_angles)
        rotated_points = self._mesh_points(rotated_mesh)
        if rotated_points is None:
            raise ValueError(f"{label.upper()} STEP rotated mesh unavailable for face-direction alignment.")

        affine = _layout_module()._affine_from_point_sets(current_points, rotated_points)
        if affine is not None:
            rotated_feature_center = (
                affine @ np.asarray((feature_center[0], feature_center[1], feature_center[2], 1.0), dtype=float)
            )[:3]
        else:
            rotated_feature_center = feature_center[:3]
        placement_delta = feature_center[:3] - np.asarray(rotated_feature_center, dtype=float).reshape(3)
        next_offset = current_offset[:3] + placement_delta[:3]

        rotated_normal = delta_matrix @ feature_normal
        angle_error = float(
            np.rad2deg(np.arccos(np.clip(float(np.dot(rotated_normal, target_normal)), -1.0, 1.0)))
        )
        return StepFaceDirectionPlan(
            label=label,
            face_id=str(face_id or "").strip(),
            direction_label=self._direction_label_text(direction_label),
            surface_center=tuple(float(value) for value in feature_center[:3]),
            target_direction=tuple(float(value) for value in target_normal[:3]),
            rotation_deg=tuple(float(value) for value in next_angles),
            placement_offset_xyz=tuple(float(value) for value in next_offset[:3]),
            angle_error_deg=angle_error,
        )
