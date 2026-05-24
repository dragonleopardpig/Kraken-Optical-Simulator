"""Open 3D STEP state-transition helpers.

This service is intentionally toolkit-light. It owns selection resolution for
STEP state transitions while the Tk/VTK inspector owns rendering and key/mouse
events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class StepDeleteSelection:
    """Resolved target for a targeted STEP delete operation."""

    import_label: str = ""
    row_indices: tuple[int, ...] = ()

    @property
    def has_target(self) -> bool:
        return bool(self.import_label or self.row_indices)


@dataclass(frozen=True, slots=True)
class StepFeatureSelection:
    """Selected imported STEP face/feature used by axis-alignment actions."""

    label: str = ""
    face_id: str = ""
    pick_point_world: tuple[float, float, float] = ()
    surface_center_world: tuple[float, float, float] = ()
    normal_world: tuple[float, float, float] = ()

    @property
    def has_pick_point(self) -> bool:
        return len(self.pick_point_world) == 3

    @property
    def has_surface_center(self) -> bool:
        return len(self.surface_center_world) == 3

    @property
    def has_normal(self) -> bool:
        return len(self.normal_world) == 3


@dataclass(frozen=True, slots=True)
class StepPromotionTransition:
    """Imported STEP overlay promotion result normalized for Open 3D callers."""

    label: str
    row_index: int
    mesh_path: str
    source_step_path: str = ""
    raw_result: dict[str, object] = field(default_factory=dict)


class Open3DStepStateService:
    """Resolve Open 3D STEP state transitions outside the widget layer."""

    def __init__(self, editor: Any, *, valid_labels: Iterable[str]) -> None:
        self.editor = editor
        self.valid_labels = {str(label).strip().lower() for label in valid_labels}

    def selected_import_label(self, candidates: Iterable[object]) -> str:
        """Return the first candidate label with a loaded STEP overlay."""
        for candidate in candidates:
            label = str(candidate or "").strip().lower()
            if label not in self.valid_labels:
                continue
            try:
                if self.editor._step_path_for_label(label) is not None:
                    return label
            except Exception:
                continue
        return ""

    def is_loaded_import_label(self, label: object) -> bool:
        """Return true when label names a currently loaded imported STEP overlay."""
        return bool(self.selected_import_label((label,)))

    @staticmethod
    def _finite_xyz(values: object) -> np.ndarray | None:
        try:
            array = np.asarray(values, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if array.size < 3 or not np.all(np.isfinite(array[:3])):
            return None
        return np.asarray(array[:3], dtype=float)

    def step_feature_selection(
        self,
        label: object,
        feature: object,
        *,
        surface_center_world: object = None,
        face_id: object = "",
    ) -> StepFeatureSelection | None:
        """Normalize a picked imported STEP face/feature into service-owned state."""
        label_text = self.selected_import_label((label,))
        if not label_text or feature is None:
            return None
        try:
            pick_point = self._finite_xyz(feature[0])
            normal = self._finite_xyz(feature[2])
        except Exception:
            return None
        if pick_point is None or normal is None:
            return None
        norm = float(np.linalg.norm(normal[:3]))
        if not np.isfinite(norm) or norm <= 1e-12:
            return None
        normal = normal[:3] / norm
        surface_center = self._finite_xyz(surface_center_world)
        if surface_center is None:
            surface_center = pick_point
        return StepFeatureSelection(
            label=label_text,
            face_id=str(face_id or "").strip(),
            pick_point_world=tuple(float(value) for value in pick_point[:3]),
            surface_center_world=tuple(float(value) for value in surface_center[:3]),
            normal_world=tuple(float(value) for value in normal[:3]),
        )

    def selected_feature_action(
        self,
        selection: StepFeatureSelection | None,
        *,
        label_candidates: Iterable[object],
        require_pick_point: bool = True,
        require_surface_center: bool = False,
        require_normal: bool = False,
    ) -> StepFeatureSelection | None:
        """Return the selected feature if it matches the active imported STEP label."""
        if selection is None or not selection.label:
            return None
        label = self.selected_import_label(label_candidates)
        if not label or label != selection.label:
            return None
        if require_pick_point and not selection.has_pick_point:
            return None
        if require_surface_center and not selection.has_surface_center:
            return None
        if require_normal and not selection.has_normal:
            return None
        return selection

    def promoted_step_row_indices(self, candidates: Iterable[object]) -> tuple[int, ...]:
        """Return unique promoted STEP optical-solid rows from candidate indices."""
        targets: set[int] = set()
        rows = list(getattr(self.editor, "rows", []) or [])
        for candidate in candidates:
            try:
                index = int(candidate)
            except Exception:
                continue
            if index < 0 or index >= len(rows):
                continue
            try:
                if self.editor._is_open3d_promoted_optical_solid_row(rows[index]):
                    targets.add(index)
            except Exception:
                continue
        return tuple(sorted(targets))

    def resolve_delete_selection(
        self,
        *,
        import_label_candidates: Iterable[object],
        row_index_candidates: Iterable[object],
    ) -> StepDeleteSelection:
        """Resolve a single imported overlay first, then promoted STEP rows."""
        label = self.selected_import_label(import_label_candidates)
        if label:
            return StepDeleteSelection(import_label=label)
        return StepDeleteSelection(row_indices=self.promoted_step_row_indices(row_index_candidates))

    def promote_imported_overlay_to_row(
        self,
        label: object,
        *,
        open_face_editor: bool,
        action_label: str = "Promote",
    ) -> StepPromotionTransition | None:
        """Promote a loaded imported STEP overlay into a persistent optical-solid row."""
        action = str(action_label or "Promote").strip() or "Promote"
        resolved_label = self.selected_import_label((label,))
        if not resolved_label:
            raise ValueError(f"{action} STEP: select or import a lens, optical, camera, or LED STEP first.")
        result = self.editor.promote_imported_step_to_optical_solid_row(
            resolved_label,
            open_face_editor=bool(open_face_editor),
            clear_overlay=True,
            refresh_open_3d=False,
        )
        if result is None:
            return None
        self.editor._live_step_overlay_trace_plan_cache = {}
        try:
            row_index = int(result.get("row_index", -1))
        except Exception:
            row_index = -1
        return StepPromotionTransition(
            label=resolved_label,
            row_index=row_index,
            mesh_path=str(result.get("mesh_path", "") or ""),
            source_step_path=str(result.get("source_step_path", "") or ""),
            raw_result=dict(result),
        )
