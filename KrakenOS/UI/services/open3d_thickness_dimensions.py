"""Open 3D editable Thickness dimension overlays.

The service owns row-to-row dimension geometry and the row-scoped edit action.
The embedded Tk/VTK inspector still owns renderer actor registration, picking,
and scene refresh.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import tkinter as tk
from tkinter import ttk


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
        self._inline_editor_window: tk.Toplevel | None = None
        self._inline_editor_row_index: int | None = None
        self._inline_editor_committing = False

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

    def _register_drag_actor(self, actor: Any, row_index: int, start: np.ndarray, end: np.ndarray) -> None:
        actor_key = self.inspector._actor_key(actor)
        if actor_key is None:
            return
        try:
            start_values = np.asarray(start, dtype=float).reshape(-1)[:3]
            end_values = np.asarray(end, dtype=float).reshape(-1)[:3]
        except Exception:
            return
        if start_values.size < 3 or end_values.size < 3:
            return
        if not (np.all(np.isfinite(start_values[:3])) and np.all(np.isfinite(end_values[:3]))):
            return
        try:
            initial = float(getattr(self.editor.rows[int(row_index)], "thickness", 0.0) or 0.0)
        except Exception:
            initial = 0.0
        self.inspector._thickness_dimension_drag_map[actor_key] = {
            "row_index": int(row_index),
            "start": tuple(float(value) for value in start_values[:3]),
            "end": tuple(float(value) for value in end_values[:3]),
            "initial_thickness": float(initial),
        }

    def add_label_actor(
        self,
        row_index: int,
        position: np.ndarray,
        text: str,
        *,
        drag_start: np.ndarray | None = None,
        drag_end: np.ndarray | None = None,
    ) -> bool:
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
            if drag_start is not None and drag_end is not None:
                self._register_drag_actor(actor, int(row_index), drag_start, drag_end)
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
            self._register_drag_actor(actor, row_index, p0, p1)
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
            if self.add_label_actor(row_index, label_position, label, drag_start=p0, drag_end=p1):
                count += 1
        return count

    def _display_direction_for_drag(self, start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, float]:
        try:
            start_display = self.inspector._world_to_display_2d(start)
            end_display = self.inspector._world_to_display_2d(end)
        except Exception:
            start_display = None
            end_display = None
        if start_display is not None and end_display is not None:
            delta = np.asarray(end_display, dtype=float).reshape(-1)[:2] - np.asarray(start_display, dtype=float).reshape(-1)[:2]
            display_length = float(np.linalg.norm(delta))
            if np.isfinite(display_length) and display_length > 1e-6:
                return delta / display_length, display_length
        segment = np.asarray(end, dtype=float).reshape(-1)[:3] - np.asarray(start, dtype=float).reshape(-1)[:3]
        axis = int(np.nanargmax(np.abs(segment[:3]))) if segment.size >= 3 else 2
        fallback = {
            0: np.asarray((1.0, 0.0), dtype=float),
            1: np.asarray((0.0, 1.0), dtype=float),
            2: np.asarray((1.0, 1.0), dtype=float) / np.sqrt(2.0),
        }.get(axis, np.asarray((1.0, 0.0), dtype=float))
        return fallback, 80.0

    def drag_state_from_current_pick(self) -> dict[str, object] | None:
        if self.inspector._picker is None or self.inspector._renderer is None or self.inspector._vtk_interactor is None:
            return None
        try:
            if int(self.inspector._vtk_interactor.GetControlKey()):
                return None
        except Exception:
            pass
        try:
            x, y = self.inspector._vtk_interactor.GetEventPosition()
            self.inspector._picker.Pick(x, y, 0.0, self.inspector._renderer)
            actor = self.inspector._picker.GetActor()
            if actor is None:
                get_view_prop = getattr(self.inspector._picker, "GetViewProp", None)
                if callable(get_view_prop):
                    actor = get_view_prop()
            actor_key = self.inspector._actor_key(actor)
        except Exception:
            return None
        if actor_key is None:
            return None
        record = self.inspector._thickness_dimension_drag_map.get(actor_key)
        if not isinstance(record, dict):
            return None
        try:
            row_index = int(record.get("row_index", -1))
        except Exception:
            return None
        if not (0 <= row_index < len(self.editor.rows) - 1):
            return None
        try:
            start = np.asarray(record.get("start"), dtype=float).reshape(-1)[:3]
            end = np.asarray(record.get("end"), dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if start.size < 3 or end.size < 3 or not (np.all(np.isfinite(start[:3])) and np.all(np.isfinite(end[:3]))):
            return None
        segment_length = float(np.linalg.norm(end[:3] - start[:3]))
        if not np.isfinite(segment_length) or segment_length <= 1e-12:
            return None
        display_direction, display_length = self._display_direction_for_drag(start[:3], end[:3])
        try:
            initial = float(getattr(self.editor.rows[row_index], "thickness", record.get("initial_thickness", 0.0)) or 0.0)
        except Exception:
            initial = 0.0
        mm_per_pixel = segment_length / max(float(display_length), 1.0)
        if not np.isfinite(mm_per_pixel) or mm_per_pixel <= 1e-12:
            mm_per_pixel = max(abs(float(initial)), 1.0) / 80.0
        self.inspector.status_var.set(
            f"Drag S{row_index} Thickness along the dimension arrow; release to apply, click to edit numerically."
        )
        return {
            "row_index": row_index,
            "initial_thickness": float(initial),
            "pending_thickness": float(initial),
            "display_direction": tuple(float(value) for value in display_direction[:2]),
            "mm_per_pixel": float(mm_per_pixel),
            "signed_pixels": 0.0,
            "moved": False,
        }

    def apply_drag_motion(self, state: dict[str, object] | None, dx: int | float, dy: int | float) -> None:
        if state is None:
            return
        try:
            cursor_delta = np.asarray((float(dx), -float(dy)), dtype=float)
            direction = np.asarray(state.get("display_direction"), dtype=float).reshape(-1)[:2]
            signed_pixels = float(np.dot(cursor_delta, direction))
            mm_per_pixel = float(state.get("mm_per_pixel", 0.0))
            initial = float(state.get("initial_thickness", 0.0))
        except Exception:
            return
        if not np.isfinite(signed_pixels) or not np.isfinite(mm_per_pixel) or mm_per_pixel <= 0.0:
            return
        total_pixels = float(state.get("signed_pixels", 0.0)) + signed_pixels
        pending = initial + total_pixels * mm_per_pixel
        if not np.isfinite(pending):
            return
        state["signed_pixels"] = float(total_pixels)
        state["pending_thickness"] = float(pending)
        state["moved"] = bool(abs(float(pending) - initial) > 1e-9)
        try:
            row_index = int(state.get("row_index", -1))
        except Exception:
            row_index = -1
        self.inspector.status_var.set(
            f"S{row_index} Thickness drag: {initial:.6g} -> {pending:.6g} mm. Release to apply."
        )

    def finish_drag(self, state: dict[str, object] | None) -> None:
        if state is None:
            return
        try:
            row_index = int(state.get("row_index", -1))
            pending = float(state.get("pending_thickness", state.get("initial_thickness", 0.0)))
            initial = float(state.get("initial_thickness", 0.0))
        except Exception:
            return
        if not bool(state.get("moved", False)) or abs(pending - initial) <= 1e-9:
            self.inspector.status_var.set(f"S{row_index} Thickness drag: no change.")
            return
        self.apply_dimension_value(row_index, pending)

    def _destroy_inline_editor(self) -> None:
        window = self._inline_editor_window
        self._inline_editor_window = None
        self._inline_editor_row_index = None
        self._inline_editor_committing = False
        if window is None:
            return
        try:
            if window.winfo_exists():
                window.destroy()
        except Exception:
            pass

    def has_inline_editor(self) -> bool:
        window = self._inline_editor_window
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except Exception:
            return False

    def cancel_inline_editor(self) -> None:
        self._destroy_inline_editor()
        try:
            self.inspector.status_var.set("Thickness edit cancelled.")
        except Exception:
            pass

    def _position_inline_editor(self, window: tk.Toplevel) -> None:
        try:
            window.update_idletasks()
            width = max(int(window.winfo_reqwidth()), 260)
            height = max(int(window.winfo_reqheight()), 80)
            pointer_x = int(self.inspector.winfo_pointerx())
            pointer_y = int(self.inspector.winfo_pointery())
            screen_w = max(int(window.winfo_screenwidth()), width)
            screen_h = max(int(window.winfo_screenheight()), height)
            x = min(max(pointer_x + 14, 8), max(screen_w - width - 12, 8))
            y = min(max(pointer_y + 14, 8), max(screen_h - height - 36, 8))
            window.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _row_label(self, row_index: int) -> str:
        if not (0 <= int(row_index) < len(self.editor.rows)):
            return f"S{int(row_index)}"
        row = self.editor.rows[int(row_index)]
        return f"S{int(row_index)}: {row.name or row.surface or 'Surface'}"

    def apply_dimension_value(self, row_index: int, next_value: float) -> bool:
        row_index = int(row_index)
        if not (0 <= row_index < len(self.editor.rows) - 1):
            self.inspector.status_var.set("Thickness dimension: choose a non-terminal table row.")
            return False
        try:
            next_value = float(next_value)
        except Exception:
            self.inspector.status_var.set("Thickness must be a finite number.")
            return False
        if not np.isfinite(next_value):
            self.inspector.status_var.set("Thickness must be a finite number.")
            return False
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
        return True

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
        self._destroy_inline_editor()
        value_var = tk.StringVar(value=f"{current:.6g}")
        window = tk.Toplevel(self.inspector)
        self._inline_editor_window = window
        self._inline_editor_row_index = row_index
        try:
            window.title("Edit Thickness")
            window.transient(self.inspector)
            window.resizable(False, False)
        except Exception:
            pass
        frame = ttk.Frame(window, padding=8)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=self._row_label(row_index)).grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(frame, text="Thickness [mm]").grid(row=1, column=0, sticky="w", pady=(6, 0))
        entry = ttk.Entry(frame, textvariable=value_var, width=16)
        entry.grid(row=1, column=1, sticky="ew", padx=(8, 6), pady=(6, 0))

        def commit(_event=None):
            if self._inline_editor_committing:
                return "break"
            self._inline_editor_committing = True
            try:
                next_value = float(value_var.get())
            except Exception:
                self._inline_editor_committing = False
                self.inspector.status_var.set("Thickness must be a finite number.")
                try:
                    entry.focus_set()
                    entry.selection_range(0, "end")
                except Exception:
                    pass
                return "break"
            if not np.isfinite(next_value):
                self._inline_editor_committing = False
                self.inspector.status_var.set("Thickness must be a finite number.")
                try:
                    entry.focus_set()
                    entry.selection_range(0, "end")
                except Exception:
                    pass
                return "break"
            self._destroy_inline_editor()
            self.apply_dimension_value(row_index, next_value)
            return "break"

        def cancel(_event=None):
            self.cancel_inline_editor()
            return "break"

        def commit_when_leaving_window(_event=None):
            try:
                focus = window.focus_get()
                if focus is not None and focus.winfo_toplevel() is window:
                    return None
            except Exception:
                pass
            return commit()

        ttk.Button(frame, text="OK", command=commit, width=6).grid(row=1, column=2, sticky="e", pady=(6, 0))
        window.bind("<Return>", commit, add="+")
        window.bind("<KP_Enter>", commit, add="+")
        window.bind("<Escape>", cancel, add="+")
        entry.bind("<FocusOut>", commit_when_leaving_window, add="+")
        try:
            window.protocol("WM_DELETE_WINDOW", cancel)
        except Exception:
            pass
        self._position_inline_editor(window)
        try:
            entry.focus_set()
            entry.selection_range(0, "end")
        except Exception:
            pass
        self.inspector.status_var.set(f"Editing {self._row_label(row_index)} Thickness. Press Enter to apply or Esc to cancel.")
