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


@dataclass(frozen=True, slots=True)
class StepCarryTransition:
    """Imported STEP carry transition resolved outside the widget layer."""

    label: str = ""
    status: str = ""

    @property
    def has_label(self) -> bool:
        return bool(self.label)


@dataclass(frozen=True, slots=True)
class StepCarryMotionDelta:
    """Computed imported STEP carry movement for the inspector to apply."""

    label: str = ""
    delta_xyz: tuple[float, float, float] = ()
    applied_steps: int = 0
    grid_spacing_mm: float | None = None
    force_refresh: bool = False
    live_refresh_message: str = ""
    debug_message: str = ""

    @property
    def has_delta(self) -> bool:
        return len(self.delta_xyz) == 3 and any(abs(value) > 1e-12 for value in self.delta_xyz)


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

    def resolve_active_carry_label(self, label: object) -> str:
        """Return an active imported STEP carry label if it is still loaded."""
        return self.selected_import_label((label,))

    def resolve_carry_start(self, label_candidates: Iterable[object]) -> StepCarryTransition:
        """Resolve the selected imported STEP overlay for press-hold carry."""
        label = self.selected_import_label(label_candidates)
        if not label:
            return StepCarryTransition(
                status="Carry STEP: select or import a lens, optical, camera, or LED STEP first.",
            )
        return StepCarryTransition(
            label=label,
            status=f"{label.upper()} STEP armed: hold on the STEP to lift; drag freely; release to drop.",
        )

    @staticmethod
    def carry_drop_status(label: object) -> str:
        """Return the user-facing status for an imported STEP carry stop."""
        label_text = str(label or "").strip().lower()
        return f"STEP carry dropped{f' for {label_text.upper()}' if label_text else ''}."

    @staticmethod
    def nice_grid_spacing(raw_spacing: float) -> float:
        """Round an arbitrary spacing to a 1/2/5 decade value."""
        raw = max(float(raw_spacing), 1e-6)
        exponent = float(np.floor(np.log10(raw)))
        base = 10.0 ** exponent
        for multiplier in (1.0, 2.0, 5.0, 10.0):
            candidate = base * multiplier
            if candidate >= raw:
                return float(candidate)
        return float(base * 10.0)

    @classmethod
    def carry_spacing_from_auto(cls, auto_spacing: float) -> float:
        """Return the free-carry spacing derived from the scene/object scale."""
        return cls.nice_grid_spacing(max(float(auto_spacing) * 0.25, 0.05))

    @classmethod
    def carry_spacing_for_scene(cls, *, scene_span: float, step_extent: float = 0.0) -> float:
        """Return the imported STEP carry spacing for the current scene scale."""
        raw_spacing = max(float(scene_span) / 18.0, float(step_extent) / 6.0, 0.5)
        return cls.carry_spacing_from_auto(cls.nice_grid_spacing(raw_spacing))

    @staticmethod
    def nearest_cardinal_axis(vector: object) -> np.ndarray:
        """Return the signed cardinal axis nearest a finite 3D vector."""
        try:
            values = np.asarray(vector, dtype=float).reshape(-1)[:3]
        except Exception:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        if values.size < 3 or not np.all(np.isfinite(values)):
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        index = int(np.argmax(np.abs(values)))
        result = np.zeros(3, dtype=float)
        result[index] = 1.0 if float(values[index]) >= 0.0 else -1.0
        return result

    def carry_motion_state(
        self,
        label: object,
        *,
        screen_axes: object,
        spacing: float,
    ) -> dict[str, object] | None:
        """Build the mutable imported STEP carry motion state used by the inspector."""
        label_text = self.resolve_active_carry_label(label)
        if not label_text:
            return None
        try:
            right_axis, up_axis = screen_axes
            spacing_value = float(spacing)
        except Exception:
            return None
        if not np.isfinite(spacing_value) or spacing_value <= 0.0:
            return None
        return {
            "label": label_text,
            "spacing": float(spacing_value),
            "snap_enabled": False,
            "ray_snap_enabled": False,
            "right_axis": self.nearest_cardinal_axis(right_axis),
            "up_axis": self.nearest_cardinal_axis(up_axis),
            "pixel_x": 0.0,
            "pixel_y": 0.0,
            "applied_steps": 0,
            "last_xy": None,
        }

    def carry_pixel_motion_delta(
        self,
        state: dict[str, object] | None,
        *,
        dx: int | float,
        dy: int | float,
        pixels_per_step: float,
    ) -> StepCarryMotionDelta | None:
        """Advance an imported STEP carry state from screen-pixel drag deltas."""
        if state is None:
            return None
        try:
            spacing = float(state.get("spacing", 0.0))
            pixel_x = float(state.get("pixel_x", 0.0)) + float(dx)
            pixel_y = float(state.get("pixel_y", 0.0)) - float(dy)
            pixels = float(pixels_per_step)
        except Exception:
            return None
        if not np.isfinite(spacing) or spacing <= 0.0 or not np.isfinite(pixels) or pixels <= 0.0:
            return None
        label = self.resolve_active_carry_label(state.get("label", ""))
        if not label:
            return StepCarryMotionDelta()
        if not bool(state.get("snap_enabled", True)):
            try:
                delta = (
                    np.asarray(state.get("right_axis"), dtype=float).reshape(3) * float(dx)
                    - np.asarray(state.get("up_axis"), dtype=float).reshape(3) * float(dy)
                ) * (spacing / pixels)
            except Exception:
                return None
            if not np.any(np.abs(delta[:3]) > 1e-12):
                return StepCarryMotionDelta(label=label)
            state["applied_steps"] = int(state.get("applied_steps", 0)) + 1
            return StepCarryMotionDelta(
                label=label,
                delta_xyz=tuple(float(value) for value in delta[:3]),
                applied_steps=1,
            )
        steps_x = int(pixel_x / pixels)
        steps_y = int(pixel_y / pixels)
        if steps_x == 0 and steps_y == 0:
            state["pixel_x"] = pixel_x
            state["pixel_y"] = pixel_y
            return StepCarryMotionDelta(label=label)
        state["pixel_x"] = pixel_x - float(steps_x) * pixels
        state["pixel_y"] = pixel_y - float(steps_y) * pixels
        delta = np.zeros(3, dtype=float)
        if steps_x:
            delta += np.asarray(state.get("right_axis"), dtype=float).reshape(3) * float(steps_x) * spacing
        if steps_y:
            delta += np.asarray(state.get("up_axis"), dtype=float).reshape(3) * float(steps_y) * spacing
        if not np.any(np.abs(delta[:3]) > 1e-12):
            return StepCarryMotionDelta(label=label)
        applied_steps = abs(int(steps_x)) + abs(int(steps_y))
        state["applied_steps"] = int(state.get("applied_steps", 0)) + applied_steps
        return StepCarryMotionDelta(
            label=label,
            delta_xyz=tuple(float(value) for value in delta[:3]),
            applied_steps=applied_steps,
            grid_spacing_mm=float(spacing),
        )

    def carry_plane_motion_delta(
        self,
        state: dict[str, object] | None,
        *,
        cursor_world: object,
        scene_span: float,
    ) -> StepCarryMotionDelta | None:
        """Advance an imported STEP carry state from a cursor point on its drag plane."""
        if state is None:
            return None
        try:
            spacing = float(state.get("spacing", 0.0))
            start_center = np.asarray(state.get("start_center_world"), dtype=float).reshape(-1)[:3]
            current_center = np.asarray(state.get("center_world"), dtype=float).reshape(-1)[:3]
            plane_origin = np.asarray(state.get("drag_plane_origin"), dtype=float).reshape(-1)[:3]
            plane_normal = np.asarray(state.get("drag_plane_normal"), dtype=float).reshape(-1)[:3]
            anchor_world = np.asarray(state.get("drag_anchor_world"), dtype=float).reshape(-1)[:3]
            cursor = np.asarray(cursor_world, dtype=float).reshape(-1)[:3]
            span = float(scene_span)
        except Exception:
            return None
        if (
            not np.isfinite(spacing)
            or spacing <= 0.0
            or not np.isfinite(span)
            or start_center.size < 3
            or current_center.size < 3
            or plane_origin.size < 3
            or plane_normal.size < 3
            or anchor_world.size < 3
            or cursor.size < 3
            or not np.all(np.isfinite(start_center[:3]))
            or not np.all(np.isfinite(current_center[:3]))
            or not np.all(np.isfinite(plane_origin[:3]))
            or not np.all(np.isfinite(plane_normal[:3]))
            or not np.all(np.isfinite(anchor_world[:3]))
            or not np.all(np.isfinite(cursor[:3]))
        ):
            return None
        raw_delta = np.asarray(cursor[:3] - anchor_world[:3], dtype=float)
        target_center = np.asarray(start_center[:3] + raw_delta[:3], dtype=float).reshape(-1)[:3]
        delta = target_center[:3] - current_center[:3]
        state["raw_drag_delta_world"] = tuple(float(value) for value in raw_delta[:3])
        label = self.resolve_active_carry_label(state.get("label", ""))
        if not label:
            return StepCarryMotionDelta()
        if not np.all(np.isfinite(delta[:3])) or not np.any(np.abs(delta[:3]) > 1e-12):
            return StepCarryMotionDelta(label=label)
        max_delta = max(float(span) * 4.0, float(spacing) * 40.0, 100.0)
        delta_norm = float(np.linalg.norm(delta[:3]))
        if not np.isfinite(delta_norm) or delta_norm > max_delta:
            state["drag_anchor_world"] = tuple(float(value) for value in cursor[:3])
            state["start_center_world"] = tuple(float(value) for value in current_center[:3])
            return StepCarryMotionDelta(
                label=label,
                debug_message=(
                    "STEP carry ignored implausible drag-plane jump: "
                    f"|delta|={delta_norm:.6g} mm, limit={max_delta:.6g} mm."
                ),
            )
        try:
            step_counts = np.abs(np.round(delta[:3] / spacing)).astype(int)
            applied_steps = int(np.sum(step_counts))
        except Exception:
            applied_steps = 1
        applied_steps = max(applied_steps, 1)
        state["applied_steps"] = int(state.get("applied_steps", 0)) + applied_steps
        return StepCarryMotionDelta(
            label=label,
            delta_xyz=tuple(float(value) for value in delta[:3]),
            applied_steps=applied_steps,
            force_refresh=True,
            live_refresh_message=f"{label} STEP carry moved",
        )

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
