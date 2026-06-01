"""Targeted Open 3D refresh helpers for imported transient STEP overlays."""

from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.services.open3d_scene_refresh import (
    _OPTICAL_STEP_BODY_COLOR,
    _OPTICAL_STEP_EDGE_COLOR,
    _OPTICAL_STEP_SILHOUETTE_COLOR,
)
from KrakenOS.UI.services.open3d_timing import open3d_timing_event, open3d_timing_span
from KrakenOS.UI.services.step_overlay_labels import STEP_OVERLAY_LABEL_SET


class Open3DStepOverlayRefreshService:
    """Redraw one imported STEP overlay without rebuilding the whole 3D scene."""

    def __init__(self, inspector: Any) -> None:
        self.inspector = inspector
        self.editor = inspector.editor

    def _remove_actor_registration(self, actor_key: str) -> object | None:
        inspector = self.inspector
        actor_key = str(actor_key or "").strip()
        if not actor_key:
            return None
        actor = inspector._actor_by_key.pop(actor_key, None)
        inspector._actor_row_map.pop(actor_key, None)
        inspector._actor_ray_map.pop(actor_key, None)
        inspector._actor_step_map.pop(actor_key, None)
        inspector._actor_step_follow_map.pop(actor_key, None)
        inspector._actor_step_rotate_map.pop(actor_key, None)
        inspector._actor_step_rotate_visual_keys.discard(actor_key)
        inspector._actor_optical_axis_map.pop(actor_key, None)
        inspector._actor_placement_move_map.pop(actor_key, None)
        inspector._actor_placement_rotate_map.pop(actor_key, None)
        inspector._actor_thickness_dimension_map.pop(actor_key, None)
        for mapping in (
            inspector._row_actor_map,
            inspector._ray_actor_map,
            inspector._step_actor_map,
            inspector._step_follow_actor_map,
            inspector._optical_axis_actor_map,
            inspector._thickness_dimension_actor_map,
        ):
            for key, values in list(mapping.items()):
                if not isinstance(values, list):
                    continue
                try:
                    while actor_key in values:
                        values.remove(actor_key)
                except Exception:
                    continue
                if not values:
                    mapping.pop(key, None)
        if actor_key == getattr(inspector, "_hover_rotation_handle_key", None):
            inspector._hover_rotation_handle_key = None
        return actor

    def _remove_step_overlay_actors(self, label: str) -> int:
        inspector = self.inspector
        label = str(label or "").strip().lower()
        if inspector._renderer is None or label not in STEP_OVERLAY_LABEL_SET:
            return 0
        actor_keys = set(str(key) for key in inspector._step_follow_actor_map.get(label, []) or [])
        actor_keys.update(str(key) for key in inspector._step_actor_map.get(label, []) or [])
        actor_keys.update(
            str(actor_key)
            for actor_key, follow_label in list(inspector._actor_step_follow_map.items())
            if str(follow_label).strip().lower() == label
        )
        actor_keys.update(
            str(actor_key)
            for actor_key, step_label in list(inspector._actor_step_map.items())
            if str(step_label).strip().lower() == label
        )
        actor_keys.update(
            str(actor_key)
            for actor_key, rotate_info in list(inspector._actor_step_rotate_map.items())
            if rotate_info and str(rotate_info[0]).strip().lower() == label
        )
        removed = 0
        for actor_key in list(actor_keys):
            actor = self._remove_actor_registration(actor_key)
            if actor is None:
                continue
            try:
                inspector._remove_renderer_view_prop(actor)
                removed += 1
            except Exception:
                pass
        inspector._step_follow_actor_map.pop(label, None)
        inspector._step_actor_map.pop(label, None)
        if inspector._picked_step_label == label:
            inspector._picked_step_label = None
        if inspector._hover_step_actor is not None:
            hover_key = inspector._actor_key(inspector._hover_step_actor)
            if hover_key in actor_keys:
                inspector._hover_step_actor = None
        try:
            if str(inspector._selected_step_feature_label or "").strip().lower() == label:
                inspector._selected_step_feature = None
                inspector._selected_step_feature_label = None
                inspector._selected_step_feature_center_world = None
                inspector._selected_step_feature_surface_center_world = None
                inspector._selected_step_feature_normal_world = None
        except Exception:
            pass
        inspector._set_step_hover_outline(None, None, render=False)
        inspector._step_feature_cache.clear()
        return removed

    def _step_overlay_display_spec(self, label: str):
        label = str(label or "").strip().lower()
        specs = {
            "lens": (self.editor._transformed_imported_lens_step_mesh, (0.30, 0.36, 0.46), 0.26),
            "optical": (self.editor._transformed_imported_optical_step_mesh, _OPTICAL_STEP_BODY_COLOR, 0.34),
            "led": (self.editor._transformed_imported_led_step_mesh, (0.95, 0.62, 0.16), 0.35),
            "camera": (self.editor._transformed_imported_camera_step_mesh, (0.28, 0.33, 0.42), 0.38),
        }
        return specs.get(label)

    def refresh_imported_step_overlay(self, label: str, *, render: bool = True) -> bool:
        inspector = self.inspector
        label = str(label or "").strip().lower()
        if inspector._renderer is None or label not in STEP_OVERLAY_LABEL_SET:
            return False
        spec = self._step_overlay_display_spec(label)
        if spec is None or self.editor._step_path_for_label(label) is None:
            return False
        builder, color, opacity = spec
        with open3d_timing_span("refresh_imported_step_overlay", label=label):
            removed = self._remove_step_overlay_actors(label)
            if (
                inspector._step_carry_label() != label
                and self.editor._step_overlay_matches_promoted_row(label)
            ):
                if str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower() == label:
                    self.editor._selected_step_label = None
                open3d_timing_event("refresh_imported_step_overlay_promoted_suppressed", label=label, removed=removed)
                if render:
                    inspector.render()
                return bool(removed)
            try:
                cad_mesh = builder()
            except Exception as exc:
                self.editor.append_debug(f"3D {label} STEP partial refresh error: {exc}")
                cad_mesh = None
            if cad_mesh is None or int(getattr(cad_mesh, "n_points", 0)) <= 0:
                open3d_timing_event("refresh_imported_step_overlay_empty", label=label, removed=removed)
                if render:
                    inspector.render()
                return False
            display_opacity = float(opacity)
            try:
                if bool(inspector.show_rays_var.get()) and label == "optical":
                    display_opacity = max(display_opacity, 0.46)
            except Exception:
                pass
            try:
                round_lens_like = bool(inspector._mesh_round_lens_axis(cad_mesh) is not None)
            except Exception:
                round_lens_like = False
            heavy_cad_mesh = int(getattr(cad_mesh, "n_cells", 0)) > 50000
            inspector._add_mesh_actor(
                cad_mesh,
                color=tuple(color),
                opacity=display_opacity,
                pick_row_index=None,
                pick_step_label=label,
                follow_step_label=label,
                flat_shading=True,
                backface_culling=False,
            )
            try:
                cad_edges = None
                if not heavy_cad_mesh:
                    cad_edges = inspector._display_feature_edges(
                        cad_mesh,
                        feature_angle=75 if round_lens_like else 55,
                        boundary_edges=not round_lens_like,
                    )
                if int(getattr(cad_edges, "n_points", 0)) > 0:
                    edge_color = _OPTICAL_STEP_EDGE_COLOR if label == "optical" else inspector._solid_edge_color_from_body(color)
                    silhouette_color = _OPTICAL_STEP_SILHOUETTE_COLOR if label == "optical" else inspector._solid_silhouette_edge_color()
                    inspector._add_mesh_actor(
                        cad_edges,
                        color=silhouette_color,
                        opacity=0.98,
                        line_width=4.2 if bool(inspector.show_rays_var.get()) else 2.2,
                        follow_step_label=label,
                        backface_culling=False,
                    )
                    inspector._add_mesh_actor(
                        cad_edges,
                        color=edge_color,
                        opacity=0.96,
                        line_width=2.6 if bool(inspector.show_rays_var.get()) else 1.4,
                        follow_step_label=label,
                        backface_culling=False,
                    )
            except Exception:
                pass
            if str(self.editor._selected_step_label or "").strip().lower() == label:
                if inspector._step_carry_label() == label:
                    inspector._add_step_carry_grid_overlay(label, cad_mesh)
                if inspector._show_rotation_handles():
                    inspector._add_step_rotation_handles(label, cad_mesh)
                inspector._set_step_highlight(label, render=False)
            try:
                inspector._reset_camera_clipping_range_for_scene()
            except Exception:
                pass
            if render:
                inspector.render()
            open3d_timing_event(
                "refresh_imported_step_overlay_rebuilt",
                label=label,
                removed=removed,
                actor_count=len(inspector._step_follow_actor_map.get(label, []) or []),
            )
        return True
