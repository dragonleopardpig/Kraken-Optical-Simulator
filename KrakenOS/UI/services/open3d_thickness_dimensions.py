"""Open 3D editable Thickness dimension overlays.

The service owns row-to-row dimension geometry and the row-scoped edit action.
The embedded Tk/VTK inspector still owns renderer actor registration, picking,
and scene refresh.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from tkinter import simpledialog


class Open3DThicknessDimensionService:
    """Render and edit Open 3D dimensions backed by table Thickness rows."""

    def __init__(
        self,
        inspector: Any,
        *,
        pv_module: Any,
        billboard_text_actor_cls: Any,
    ) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.pv = pv_module
        self.billboard_text_actor_cls = billboard_text_actor_cls

    def arrow_mesh(
        self,
        start: np.ndarray,
        end: np.ndarray,
        *,
        scene_span: float,
    ) -> Any | None:
        pv = self.pv
        if pv is None:
            return None
        start = np.asarray(start, dtype=float).reshape(3)
        end = np.asarray(end, dtype=float).reshape(3)
        delta = end - start
        length = float(np.linalg.norm(delta))
        if not np.isfinite(length) or length <= 1e-9:
            return None
        direction = delta / length
        head = min(max(float(scene_span) * 0.018, 0.75), max(length * 0.28, 0.75))
        radius = max(head * 0.20, 0.12)
        tube_radius = max(radius * 0.18, 0.025)
        parts: list[Any] = []
        try:
            line = pv.Line(tuple(float(value) for value in start), tuple(float(value) for value in end))
            try:
                parts.append(line.tube(radius=float(tube_radius), n_sides=10))
            except Exception:
                parts.append(line)
        except Exception:
            return None
        for tip, cone_direction in ((start, -direction), (end, direction)):
            try:
                center = np.asarray(tip, dtype=float) - np.asarray(cone_direction, dtype=float) * (head * 0.5)
                parts.append(
                    pv.Cone(
                        center=tuple(float(value) for value in center),
                        direction=tuple(float(value) for value in cone_direction),
                        height=float(head),
                        radius=float(radius),
                        resolution=24,
                    )
                )
            except Exception:
                pass
        merged = parts[0]
        for part in parts[1:]:
            try:
                merged = merged.merge(part)
            except Exception:
                pass
        return merged

    @staticmethod
    def offset_direction(segment_direction: np.ndarray) -> np.ndarray:
        direction = np.asarray(segment_direction, dtype=float).reshape(3)
        norm = float(np.linalg.norm(direction))
        if not np.isfinite(norm) or norm <= 1e-12:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        direction = direction / norm
        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(direction, reference))) > 0.90:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        side = np.cross(direction, reference)
        side_norm = float(np.linalg.norm(side))
        if not np.isfinite(side_norm) or side_norm <= 1e-12:
            return np.asarray((1.0, 0.0, 0.0), dtype=float)
        return side / side_norm

    def add_label_actor(self, row_index: int, position: np.ndarray, text: str) -> bool:
        actor_cls = self.billboard_text_actor_cls
        if self.inspector._renderer is None or actor_cls is None:
            return False
        try:
            actor = actor_cls()
            actor.SetInput(str(text))
            point = np.asarray(position, dtype=float).reshape(3)
            actor.SetPosition(float(point[0]), float(point[1]), float(point[2]))
            try:
                text_prop = actor.GetTextProperty()
                text_prop.SetFontSize(13)
                text_prop.SetColor(0.02, 0.16, 0.32)
                text_prop.SetBackgroundColor(1.0, 1.0, 1.0)
                text_prop.SetBackgroundOpacity(0.82)
                text_prop.SetFrame(1)
                text_prop.SetFrameColor(0.05, 0.42, 0.70)
            except Exception:
                pass
            self.inspector._register_thickness_dimension_actor(actor, int(row_index))
            self.inspector._add_renderer_view_prop(actor)
            return True
        except Exception as exc:
            self.editor.append_debug(f"3D thickness label skipped: {exc}")
            return False

    def add_overlays(self, system: Any, scene_bundle: Any = None) -> int:
        del scene_bundle
        pv = self.pv
        if pv is None:
            return 0
        show_var = getattr(self.editor, "show_physical_distances_var", None)
        if show_var is None or not bool(show_var.get()):
            return 0
        rows = list(getattr(self.editor, "rows", []) or [])
        if len(rows) < 2:
            return 0
        _center, scene_span = self.inspector._row_scene_bounds()
        base_offset = max(float(scene_span) * 0.045, 2.0)
        color = (0.05, 0.42, 0.70)
        count = 0
        for row_index, row in enumerate(rows[:-1]):
            try:
                thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            except Exception:
                continue
            if not np.isfinite(thickness) or abs(thickness) <= 1e-9:
                continue
            try:
                p0 = np.asarray(self.editor._surface_reference_world_point(row_index, system=system), dtype=float).reshape(3)
                p1 = np.asarray(self.editor._surface_reference_world_point(row_index + 1, system=system), dtype=float).reshape(3)
            except Exception as exc:
                self.editor.append_debug(f"3D thickness dimension skipped for S{row_index}: {exc}")
                continue
            if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))):
                continue
            segment = p1 - p0
            segment_length = float(np.linalg.norm(segment))
            if not np.isfinite(segment_length) or segment_length <= 1e-9:
                continue
            side = self.offset_direction(segment)
            row_band = 1.0 + 0.38 * float(row_index % 3)
            offset = side * base_offset * row_band
            start = p0 + offset
            end = p1 + offset
            mesh = self.arrow_mesh(start, end, scene_span=scene_span)
            if mesh is None:
                continue
            actor = self.inspector._add_mesh_actor(
                mesh,
                color=color,
                opacity=0.92,
                pick_thickness_dimension=row_index,
                flat_shading=True,
                backface_culling=False,
            )
            if actor is None:
                continue
            count += 1
            try:
                self.inspector._add_mesh_actor(
                    pv.Line(tuple(float(value) for value in p0), tuple(float(value) for value in start)),
                    color=(0.62, 0.72, 0.80),
                    opacity=0.52,
                    line_width=1.0,
                    backface_culling=False,
                )
                self.inspector._add_mesh_actor(
                    pv.Line(tuple(float(value) for value in p1), tuple(float(value) for value in end)),
                    color=(0.62, 0.72, 0.80),
                    opacity=0.52,
                    line_width=1.0,
                    backface_culling=False,
                )
            except Exception:
                pass
            label = f"S{row_index} Thickness = {thickness:.6g} mm"
            label_position = 0.5 * (start + end) + side * max(base_offset * 0.22, 0.8)
            if self.add_label_actor(row_index, label_position, label):
                count += 1
        return count

    def edit_dimension(self, row_index: int) -> None:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.editor.rows) - 1):
            self.inspector.status_var.set("Thickness dimension: choose a non-terminal table row.")
            return
        row = self.editor.rows[row_index]
        try:
            current = float(getattr(row, "thickness", 0.0) or 0.0)
        except Exception:
            current = 0.0
        label = f"S{row_index}: {row.name or row.surface or 'Surface'}"
        value = simpledialog.askfloat(
            "Edit Thickness",
            f"{label}\nThickness to next row [mm]:",
            initialvalue=current,
            parent=self.inspector,
        )
        if value is None:
            self.inspector.status_var.set("Thickness edit cancelled.")
            return
        try:
            next_value = float(value)
        except Exception:
            self.inspector.status_var.set("Thickness must be a finite number.")
            return
        if not np.isfinite(next_value):
            self.inspector.status_var.set("Thickness must be a finite number.")
            return
        self.editor._begin_history_capture()
        self.editor.rows[row_index].thickness = next_value
        self.editor._sync_table()
        self.editor._select_table_row(row_index)
        self.editor._commit_history_capture()
        self.editor._invalidate_preview_scene_trace()
        self.editor._sync_trace_state_badge()
        self.editor.status_var.set(f"S{row_index} Thickness set to {next_value:.6g} mm. Other table thickness values are unchanged.")
        self.inspector.status_var.set(f"S{row_index} Thickness set to {next_value:.6g} mm.")
        self.inspector.refresh_from_editor(force_retrace=True)
