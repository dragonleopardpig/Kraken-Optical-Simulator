"""Open 3D imported STEP rotation-handle helpers."""

from __future__ import annotations

from typing import Any

import numpy as np


class Open3DStepRotationHandleService:
    """Own imported STEP rotation-handle actors and hover styling."""

    def __init__(self, inspector: Any, *, pv_module: Any, valid_labels: set[str]) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.pv = pv_module
        self.valid_labels = {str(label).strip().lower() for label in valid_labels}

    def remove_actors(self) -> bool:
        inspector = self.inspector
        if inspector._renderer is None:
            return False
        removed = False
        actor_keys = set(inspector._actor_step_rotate_map)
        actor_keys.update(inspector._actor_step_rotate_visual_keys)
        for actor_key in list(actor_keys):
            actor = inspector._actor_by_key.pop(actor_key, None)
            inspector._actor_step_rotate_map.pop(actor_key, None)
            inspector._actor_step_rotate_visual_keys.discard(actor_key)
            inspector._actor_step_follow_map.pop(actor_key, None)
            for keys in list(inspector._step_follow_actor_map.values()):
                try:
                    while actor_key in keys:
                        keys.remove(actor_key)
                except Exception:
                    pass
            if actor_key == getattr(inspector, "_hover_rotation_handle_key", None):
                inspector._hover_rotation_handle_key = None
            if actor is None:
                continue
            try:
                inspector._renderer.RemoveActor(actor)
                removed = True
            except Exception:
                pass
        return removed

    def handle_count_for_label(self, label: str) -> int:
        label = str(label or "").strip().lower()
        if not label:
            return 0
        count = 0
        for step_label, _axis, _delta_deg in list(self.inspector._actor_step_rotate_map.values()):
            if str(step_label).strip().lower() == label:
                count += 1
        return count

    def ensure_for_label(self, label: str) -> int:
        inspector = self.inspector
        label = str(label or "").strip().lower()
        if (
            inspector._renderer is None
            or label not in self.valid_labels
            or self.editor._step_path_for_label(label) is None
            or not inspector._show_rotation_handles()
        ):
            return 0
        current_count = self.handle_count_for_label(label)
        if current_count > 0:
            return current_count
        try:
            mesh = self.editor._transformed_imported_step_mesh_for_label(label)
        except Exception as exc:
            self.editor.append_debug(f"STEP rotation handle rebuild failed for {label}: {exc}")
            return 0
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return 0
        return self.add_handles(label, mesh)

    @staticmethod
    def center_and_extent(mesh) -> tuple[np.ndarray, float] | None:
        try:
            bounds = np.asarray(mesh.bounds, dtype=float).reshape(6)
        except Exception:
            return None
        if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
            return None
        center = np.asarray(
            (
                0.5 * (bounds[0] + bounds[1]),
                0.5 * (bounds[2] + bounds[3]),
                0.5 * (bounds[4] + bounds[5]),
            ),
            dtype=float,
        )
        extent = max(bounds[1] - bounds[0], bounds[3] - bounds[2], bounds[5] - bounds[4], 1.0)
        return center, float(extent)

    def add_handles(self, label: str, mesh) -> int:
        inspector = self.inspector
        if self.pv is None or not inspector._show_rotation_handles():
            return 0
        label = str(label).strip().lower()
        if label not in self.valid_labels or self.editor._step_path_for_label(label) is None:
            return 0
        center_extent = self.center_and_extent(mesh)
        if center_extent is None:
            return 0
        center, extent = center_extent
        radius = max(float(extent) * 0.62, 3.0)
        tube_radius = max(radius * 0.014, 0.045)
        axes = (
            ("x", (0.88, 0.18, 0.18)),
            ("y", (0.12, 0.62, 0.24)),
            ("z", (0.18, 0.35, 0.88)),
        )
        step = inspector._rotation_handle_step_deg()
        count = 0
        for axis, color in axes:
            arc_mesh = inspector._scene_placement_rotation_arc_mesh(
                center=center,
                axis=axis,
                sign=1.0,
                radius=radius,
                tube_radius=tube_radius,
                include_arrowheads=False,
            )
            if arc_mesh is not None:
                arc_actor = inspector._add_mesh_actor(
                    arc_mesh,
                    color=color,
                    opacity=0.58,
                    follow_step_label=label,
                    flat_shading=True,
                    backface_culling=False,
                )
                arc_key = inspector._actor_key(arc_actor)
                if arc_key is not None:
                    inspector._actor_step_rotate_visual_keys.add(arc_key)
            for delta_deg in (-float(step), float(step)):
                arrow_mesh = inspector._scene_placement_rotation_arrowhead_mesh(
                    center=center,
                    axis=axis,
                    sign=1.0,
                    delta_sign=delta_deg,
                    radius=radius,
                    tube_radius=tube_radius,
                )
                if arrow_mesh is None:
                    continue
                actor = inspector._add_mesh_actor(
                    arrow_mesh,
                    color=color,
                    opacity=0.96,
                    pick_step_rotate=(label, axis, float(delta_deg)),
                    follow_step_label=label,
                    flat_shading=True,
                    backface_culling=False,
                )
                if actor is not None:
                    count += 1
        return count

    def apply_handle(self, label: str, axis: str, delta_deg: float) -> None:
        inspector = self.inspector
        label = str(label).strip().lower()
        axis = str(axis).strip().lower()
        if label not in self.valid_labels or axis not in {"x", "y", "z"}:
            inspector.status_var.set("STEP rotation handle: select a valid STEP component first.")
            return
        if self.editor._step_path_for_label(label) is None:
            inspector.status_var.set(f"STEP rotation handle: no {label.upper()} STEP is imported.")
            return
        inspector._step_rotation_active_label = label
        self.editor.select_step_component(label)
        try:
            physics_requested = bool(
                self.editor._open3d_trace_refresh_service().inspector_physics_requested(inspector)
            )
        except Exception:
            physics_requested = True
        next_angles = self.editor.rotate_step_world_axis(
            label,
            axis,
            float(delta_deg),
            refresh=physics_requested,
        )
        if next_angles is None:
            inspector.status_var.set(self.editor.status_var.get())
            return
        if not physics_requested:
            try:
                refreshed = bool(inspector.refresh_imported_step_overlay(label))
            except Exception as exc:
                refreshed = False
                self.editor.append_debug(f"STEP rotation partial refresh failed for {label}: {exc}")
            if not refreshed:
                try:
                    inspector.refresh_from_editor(force_retrace=False)
                except Exception as exc:
                    self.editor.append_debug(f"STEP rotation fallback refresh failed for {label}: {exc}")
        inspector.status_var.set(
            f"{label.upper()} STEP world {axis.upper()}{float(delta_deg):+.0f} deg -> "
            f"X={next_angles[0]:.0f}, "
            f"Y={next_angles[1]:.0f}, "
            f"Z={next_angles[2]:.0f} deg."
        )

    def set_hover(self, actor_key: str | None) -> None:
        inspector = self.inspector
        actor_key = str(actor_key or "").strip() or None
        if actor_key == inspector._hover_rotation_handle_key:
            return
        if inspector._renderer is None:
            inspector._hover_rotation_handle_key = actor_key
            return

        def restore(key: str | None) -> None:
            if not key:
                return
            actor = inspector._actor_by_key.get(str(key))
            if actor is None:
                return
            try:
                prop = actor.GetProperty()
            except Exception:
                prop = None
            if prop is None:
                return
            base = getattr(actor, "_kraken_rotation_hover_style", None)
            if not isinstance(base, dict):
                return
            try:
                color = tuple(base.get("color", (1.0, 1.0, 1.0)))
                if len(color) == 3:
                    prop.SetColor(*color)
                prop.SetOpacity(float(base.get("opacity", 1.0)))
                prop.SetAmbient(float(base.get("ambient", 0.0)))
                prop.SetDiffuse(float(base.get("diffuse", 1.0)))
                prop.SetLineWidth(float(base.get("line_width", 1.0)))
            except Exception:
                pass

        restore(inspector._hover_rotation_handle_key)
        inspector._hover_rotation_handle_key = actor_key
        actor = inspector._actor_by_key.get(actor_key) if actor_key is not None else None
        if actor is not None:
            try:
                prop = actor.GetProperty()
            except Exception:
                prop = None
            if prop is not None:
                base = getattr(actor, "_kraken_rotation_hover_style", None)
                if not isinstance(base, dict):
                    try:
                        base = {
                            "color": tuple(float(value) for value in prop.GetColor()),
                            "opacity": float(prop.GetOpacity()),
                            "ambient": float(prop.GetAmbient()),
                            "diffuse": float(prop.GetDiffuse()),
                            "line_width": float(prop.GetLineWidth()),
                        }
                        actor._kraken_rotation_hover_style = base
                    except Exception:
                        base = {}
                try:
                    prop.SetColor(1.0, 0.78, 0.08)
                    prop.SetOpacity(1.0)
                    prop.SetAmbient(max(float(base.get("ambient", 0.0)), 0.92))
                    prop.SetDiffuse(0.18)
                    prop.SetLineWidth(max(float(base.get("line_width", 1.0)), 4.0))
                except Exception:
                    pass
        inspector.render()
