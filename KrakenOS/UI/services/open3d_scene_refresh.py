"""Open 3D scene refresh service."""

from __future__ import annotations

import time
from typing import Any

import numpy as np


_OPTICAL_STEP_BODY_COLOR = (0.10, 0.62, 0.72)
# Shared "glass" edge palette: deep-teal tones derived from the analytic
# glass body colour, used for BOTH imported file-backed STEP solids (the
# prisms) and analytic optic surfaces so every glass element outlines with
# the same colour and weight. The silhouette tone is the deepest; the edge
# tone is the brighter highlight line drawn on top.
_OPTICAL_STEP_EDGE_COLOR = (0.026, 0.512, 0.528)
_OPTICAL_STEP_SILHOUETTE_COLOR = (0.014, 0.279, 0.288)
# Shared outline weights (line widths) for glass elements.
_GLASS_EDGE_SILHOUETTE_WIDTH = 2.8
_GLASS_EDGE_LINE_WIDTH = 2.0


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class Open3DSceneRefreshService:
    """Render Open 3D scene bodies, rays, overlays, and status actors."""

    def __init__(self, inspector: Any) -> None:
        object.__setattr__(self, "_inspector", inspector)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inspector, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_inspector":
            object.__setattr__(self, name, value)
            return
        setattr(self._inspector, name, value)

    def refresh_scene(
        self,
        system,
        rays,
        row_names: list[str],
        *,
        scene_bundle: Any = None,
        reset_camera: bool = False,
    ) -> None:
        refresh_start = time.perf_counter()
        le = _layout_module()
        KrakenLayoutEditor = le.KrakenLayoutEditor
        STEP_OVERLAY_LABEL_SET = le.STEP_OVERLAY_LABEL_SET
        _VTK_TK_UNAVAILABLE_REASON = le._VTK_TK_UNAVAILABLE_REASON
        scene_display_center_radius = le.scene_display_center_radius
        if self._renderer is None:
            raise RuntimeError(_VTK_TK_UNAVAILABLE_REASON or "Embedded VTK/Tk viewer unavailable")
        self._current_scene_bundle = scene_bundle
        self._current_system = system
        self._current_rays = rays
        self._current_row_names = list(row_names or [])
        self._remember_refresh_sampling_mode(getattr(self.editor, "_active_preview_sampling_mode", None))

        show_reference_surfaces = bool(self.show_reference_surfaces_var.get())
        show_launch_reference_surface = bool(
            self.editor._should_show_open3d_launch_reference_surface(system=system)
        )
        mesh_collect_start = time.perf_counter()
        mesh_items = list(
            self.editor._scene_surface_meshes(
                system,
                scene_bundle,
                include_reference_surfaces=show_reference_surfaces or show_launch_reference_surface,
            )
        )
        mesh_collect_ms = (time.perf_counter() - mesh_collect_start) * 1000.0
        if show_launch_reference_surface and not show_reference_surfaces:
            mesh_items = [
                mesh_item
                for mesh_item in mesh_items
                if str(getattr(getattr(mesh_item, "row", None), "surface", "") or "") not in {"Object", "Image"}
                or (
                    int(getattr(mesh_item, "row_index", -1)) == 0
                    and str(getattr(getattr(mesh_item, "row", None), "surface", "") or "") == "Object"
                )
            ]
        rows = self.editor._preview_render_rows(scene_bundle)
        expected_physical_rows = {
            index
            for index, row in enumerate(rows)
            if str(getattr(row, "surface", "") or "") not in {"Object", "Image"}
        }
        mesh_rows = {
            int(getattr(mesh_item, "row_index", -1))
            for mesh_item in mesh_items
            if int(getattr(mesh_item, "row_index", -1)) >= 0
        }
        physical_mesh_rows = mesh_rows.intersection(expected_physical_rows)
        file_backed_rows = {
            index
            for index in expected_physical_rows
            if self._render_row_file_backed(rows, int(index))
        }
        previous_mesh_items = list(getattr(self, "_last_valid_surface_mesh_items", []) or [])
        previous_row_count = int(getattr(self, "_last_valid_surface_mesh_row_count", 0) or 0)
        can_reuse_previous_meshes = bool(previous_mesh_items) and previous_row_count == len(rows)
        previous_physical_rows = {
            int(getattr(mesh_item, "row_index", -1))
            for mesh_item in previous_mesh_items
            if int(getattr(mesh_item, "row_index", -1)) in expected_physical_rows
        }
        missing_file_backed_rows = file_backed_rows.difference(mesh_rows)
        suspicious_sparse_rebuild = (
            can_reuse_previous_meshes
            and bool(previous_physical_rows)
            and len(physical_mesh_rows) < max(1, int(np.ceil(len(previous_physical_rows) * 0.5)))
        )
        previous_actor_count = 0
        try:
            previous_actor_count = int(self._renderer.GetViewProps().GetNumberOfItems())
        except Exception:
            previous_actor_count = 0
        show_thickness_var = getattr(self.editor, "show_physical_distances_var", None)
        try:
            show_thickness_dimensions = bool(show_thickness_var.get()) if show_thickness_var is not None else False
        except Exception:
            show_thickness_dimensions = False
        self._debug_trace(
            "refresh_scene_start",
            mesh_collect_ms=round(float(mesh_collect_ms), 3),
            rows=len(rows),
            expected_physical_rows=sorted(expected_physical_rows),
            mesh_items=len(mesh_items),
            mesh_rows=sorted(mesh_rows),
            physical_mesh_rows=sorted(physical_mesh_rows),
            file_backed_rows=sorted(file_backed_rows),
            missing_file_backed_rows=sorted(missing_file_backed_rows),
            previous_physical_rows=sorted(previous_physical_rows),
            previous_actor_count=previous_actor_count,
            can_reuse_previous_meshes=can_reuse_previous_meshes,
            suspicious_sparse_rebuild=suspicious_sparse_rebuild,
            show_rays=bool(self.show_rays_var.get()),
            show_reference_surfaces=show_reference_surfaces,
            show_launch_reference_surface=show_launch_reference_surface,
            show_detector_overlays=bool(self.show_detector_overlays_var.get()),
            show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get()),
            show_placement_handles=bool(self.show_placement_handles_var.get()),
            show_thickness_dimensions=show_thickness_dimensions,
            reset_camera=bool(reset_camera),
        )
        if can_reuse_previous_meshes and (missing_file_backed_rows or suspicious_sparse_rebuild):
            detail = "missing file-backed rows" if missing_file_backed_rows else "sparse surface rebuild"
            message = f"3D refresh reused previous surface meshes: {detail} during trace refresh."
            self.status_var.set(message)
            self.editor.append_debug(message)
            self._debug_trace(
                "refresh_scene_reuse_previous_meshes",
                detail=detail,
                missing_file_backed_rows=sorted(missing_file_backed_rows),
                suspicious_sparse_rebuild=suspicious_sparse_rebuild,
            )
            mesh_items = previous_mesh_items
            mesh_rows = {
                int(getattr(mesh_item, "row_index", -1))
                for mesh_item in mesh_items
                if int(getattr(mesh_item, "row_index", -1)) >= 0
            }
            physical_mesh_rows = mesh_rows.intersection(expected_physical_rows)
        expects_surface_meshes = any(
            str(getattr(row, "surface", "") or "") not in {"Object", "Image"}
            for row in rows
        )
        if previous_actor_count > 0 and expects_surface_meshes and not mesh_items:
            message = "3D refresh kept previous scene: rebuilt trace produced no surface meshes."
            self.status_var.set(message)
            self.editor.append_debug(message)
            self._debug_trace(
                "refresh_scene_abort_no_meshes",
                previous_actor_count=previous_actor_count,
                duration_ms=round(float((time.perf_counter() - refresh_start) * 1000.0), 3),
            )
            self._timing_event(
                "refresh_scene_abort_no_meshes",
                previous_actor_count=previous_actor_count,
                duration_ms=round(float((time.perf_counter() - refresh_start) * 1000.0), 3),
            )
            return
        if physical_mesh_rows:
            self._last_valid_surface_mesh_items = list(mesh_items)
            self._last_valid_surface_mesh_row_count = len(rows)

        # CameraState capture via the Phase 8 helper so the dict shape
        # lives in one place; refresh_scene still owns the policy of
        # honouring reset_camera over a stored snapshot.
        camera_state = None
        selected_axis_id = self._picked_optical_axis_id
        if not bool(reset_camera):
            from KrakenOS.UI.services.open3d_camera_state import capture_camera_state

            camera_state = capture_camera_state(self._renderer)

        self._clear_galvo_scan_animation(cancel_timer=True, render=False)
        actor_clear_start = time.perf_counter()
        self._renderer.RemoveAllViewProps()
        self._actor_row_map.clear()
        self._row_actor_map.clear()
        self._actor_ray_map.clear()
        self._ray_actor_map.clear()
        self._actor_optical_axis_map.clear()
        self._optical_axis_actor_map.clear()
        self._optical_axis_pick_records.clear()
        self._optical_axis_highlight_actor = None
        self._actor_by_key.clear()
        self._actor_step_map.clear()
        self._step_actor_map.clear()
        self._actor_step_follow_map.clear()
        self._step_follow_actor_map.clear()
        self._actor_step_rotate_map.clear()
        self._actor_step_rotate_visual_keys.clear()
        self._actor_placement_move_map.clear()
        self._actor_placement_rotate_map.clear()
        self._actor_placement_rotate_visual_keys.clear()
        self._actor_placement_move_visual_keys.clear()
        self._actor_thickness_dimension_map.clear()
        self._thickness_dimension_actor_map.clear()
        self._thickness_dimension_drag_map.clear()
        self._thickness_drag_state = None
        self._step_feature_cache.clear()
        self._hover_rotation_handle_key = None
        self._hover_step_actor = None
        self._hover_step_outline_actor = None
        self._hover_step_cell_key = None
        self._ray_event_label_actors = []
        self._mode_badge_actor = None
        self._trace_summary_actor = None
        self._placement_grid_status_actor = None
        self._hover_status_actor = None
        self._step_carry_grip_actor = None
        actor_clear_ms = (time.perf_counter() - actor_clear_start) * 1000.0

        drew_surfaces = 0
        surface_actor_start = time.perf_counter()
        step_carry_label = self._step_carry_label()
        ray_visibility_requested = bool(self.show_rays_var.get())
        ray_surface_edge_overlays: list[tuple[object, tuple[float, float, float], float, int | None]] = []
        ray_surface_wire_overlays: list[tuple[object, tuple[float, float, float], float, int]] = []
        live_trace_step_labels_by_row = self._live_trace_step_overlay_label_by_row()
        mesh_row_indices: set[int] = set()
        for mesh_item in mesh_items:
            try:
                mesh_row_indices.add(int(getattr(mesh_item, "row_index", -1)))
            except Exception:
                continue
        current_live_trace_step_overlay_labels = {
            str(label).strip().lower()
            for row_index, label in live_trace_step_labels_by_row.items()
            if int(row_index) in mesh_row_indices and str(label).strip().lower()
        }
        live_trace_step_mesh_by_label: dict[str, object] = {}
        for mesh_item in mesh_items:
            mesh = mesh_item.mesh
            try:
                row_index = int(getattr(mesh_item, "row_index", -1))
            except Exception:
                row_index = -1
            # Missing-CAD placeholder rows render as a tinted red
            # wireframe box and short-circuit every other branch
            # (no glassy body, no rim outline, no file-backed edge
            # styling). The dedicated branch keeps the surrounding
            # logic free of "is_missing_placeholder" checks at every
            # step.
            if bool(getattr(mesh_item, "is_missing_placeholder", False)) and mesh is not None:
                self._add_missing_asset_placeholder_actors(mesh, row_index)
                drew_surfaces += 1
                continue
            transient_step_label = live_trace_step_labels_by_row.get(row_index)
            if transient_step_label is not None and bool(getattr(mesh_item, "is_body", False)):
                live_trace_step_mesh_by_label.setdefault(str(transient_step_label), mesh)
            row_step_label = transient_step_label
            if row_step_label is None:
                try:
                    row_step_label = KrakenLayoutEditor._open3d_step_label_for_optical_solid_row(getattr(mesh_item, "row", None)) or None
                except Exception:
                    row_step_label = None
            row_step_label = str(row_step_label or "").strip().lower()
            mesh_color = _OPTICAL_STEP_BODY_COLOR if row_step_label == "optical" and row_index in file_backed_rows else tuple(mesh_item.color)
            mesh_opacity = float(getattr(mesh_item, "opacity", 1.0))
            row_surface = str(getattr(getattr(mesh_item, "row", None), "surface", "") or "")
            row_surface_str = row_surface.lower()
            row_kind = str(getattr(mesh_item, "kind", "") or "").lower()
            row_is_body = bool(getattr(mesh_item, "is_body", False))
            row_advanced_attrs = getattr(getattr(mesh_item, "row", None), "advanced", None)
            row_advanced_attrs = row_advanced_attrs if isinstance(row_advanced_attrs, dict) else {}
            # Analytic STEP-promoted lens: the cached STEP body STL is the
            # real shape (rectangular plano-cyl plate, true sphere, etc.).
            # KrakenOS's auto-revolved BBB drum is redundant and would draw
            # a round shell/ring around it -- keep that drum invisible.
            analytic_promoted_step = bool(
                row_advanced_attrs.get("StepAnalyticBodyStlPath")
                or row_advanced_attrs.get("StepAnalyticBodyOmitMesh")
                or isinstance(row_advanced_attrs.get("StepAnalyticPromotion"), dict)
            )
            # Any analytic optic surface/body (Standard / thin-lens) that is
            # not a UI/reference/file-backed surface. These render as glassy
            # translucent glass like the file-backed STEP prisms -- never as
            # an opaque disc + wireframe overlay.
            analytic_optic_surface = (
                row_surface not in {"Object", "Image"}
                and row_surface_str not in {"aperture", "grating", "mirror"}
                and row_index not in file_backed_rows
                and (row_kind.startswith("standard") or row_kind.startswith("thin_lens"))
            )
            analytic_hidden_drum = analytic_promoted_step and row_is_body
            if analytic_hidden_drum:
                mesh_opacity = 0.0
            if row_index in file_backed_rows:
                mesh_opacity = min(max(mesh_opacity, 0.14), 0.28)
                if row_step_label == "optical":
                    mesh_opacity = min(max(mesh_opacity, 0.30), 0.36)
            # bugs/0020: every file-backed STEP/STL solid -- prisms,
            # beam-splitter cubes, mounts -- shares the glass edge colour
            # AND weight with the analytic lenses. A promotion display
            # label other than "optical" (e.g. a cube tagged "led") no
            # longer downgrades its outline to the legacy heavy black
            # wireframe; the user wants one nice optical edge palette.
            file_backed_edge_color = _OPTICAL_STEP_EDGE_COLOR
            file_backed_silhouette_color = _OPTICAL_STEP_SILHOUETTE_COLOR
            file_backed_silhouette_width = _GLASS_EDGE_SILHOUETTE_WIDTH
            file_backed_edge_width = _GLASS_EDGE_LINE_WIDTH
            if show_launch_reference_surface and not show_reference_surfaces and row_surface == "Object":
                mesh_opacity = min(mesh_opacity, 0.18)
            row_round_lens_like = False
            if row_index in file_backed_rows:
                try:
                    row_round_lens_like = bool(self._mesh_round_lens_axis(mesh) is not None)
                except Exception:
                    row_round_lens_like = False
            row_edge_feature_angle = 75 if row_round_lens_like else 24
            row_edge_boundary_edges = not row_round_lens_like
            if ray_visibility_requested and row_index >= 0:
                if row_surface in {"Object", "Image"}:
                    mesh_opacity = min(mesh_opacity, 0.22)
                elif row_index in file_backed_rows:
                    mesh_opacity = min(max(mesh_opacity, 0.14), 0.24)
                    if row_step_label == "optical":
                        mesh_opacity = min(max(mesh_opacity, 0.30), 0.36)
                elif analytic_hidden_drum:
                    # Redundant auto-revolved drum on a promoted STEP lens:
                    # stay invisible even with rays on (its actor is kept
                    # only for picking / centroid queries).
                    mesh_opacity = 0.0
                elif analytic_optic_surface:
                    # Glassy translucent lens body, matching the look of the
                    # file-backed STEP prisms. No opaque fill, no wireframe
                    # overlay -- the feature edges below outline the shape.
                    mesh_opacity = min(max(mesh_opacity, 0.26), 0.40)
                else:
                    mesh_opacity = max(mesh_opacity, 0.86)
                    wire_color = mesh_color
                    wire_width = 1.35
                    ray_surface_wire_overlays.append((mesh, wire_color, wire_width, row_index))
            # Glassy lens look for analytic lens surfaces. Applies to
            # Standard analytic caps, STEP-promoted lens body STLs
            # (StepAnalyticBodyStlPath) and ordinary revolved lens
            # bodies (e.g. the achromat). Skip object/image reference
            # planes, mirrors, apertures/grating UI surfaces, the
            # hidden auto-revolved STEP drum, and anything invisible.
            glassy_lens = analytic_optic_surface and mesh_opacity > 0.0
            body_actor = self._add_mesh_actor(
                mesh,
                color=mesh_color,
                opacity=mesh_opacity,
                pick_row_index=mesh_item.row_index,
                pick_step_label=transient_step_label,
                follow_step_label=transient_step_label,
                backface_culling=False,
                glassy=glassy_lens,
            )
            if body_actor is not None and row_index in file_backed_rows:
                try:
                    body_actor._kraken_file_backed_row_body = bool(mesh_item.is_body)
                except Exception:
                    pass
            # Glassy analytic lens bodies (revolved drums, Standard caps,
            # promoted-STEP body plates with no on-disk STL) are dense
            # solids that are NOT file-backed, so they miss the flag above.
            # Mark them so the selection highlight suppresses per-triangle
            # edges the same way -- otherwise selecting one paints a red
            # wireframe over every triangle and it reads as solid red
            # instead of pink translucent (bugs/0001).
            if body_actor is not None and glassy_lens:
                try:
                    body_actor._kraken_glassy_lens_body = True
                except Exception:
                    pass
            # Promoted-STEP analytic body owns multiple surface rows
            # (front + trailing). Trailing rows skip their own mesh
            # (StepAnalyticBodyOmitMesh) so the body STL doesn't get
            # double-drawn; register this single body actor under
            # each trailing row's _row_actor_map entry so picks,
            # centroid queries and selection still resolve.
            if body_actor is not None and isinstance(getattr(mesh_item, "row", None), object):
                try:
                    row_advanced = getattr(mesh_item.row, "advanced", None)
                    promotion = row_advanced.get("StepAnalyticPromotion") if isinstance(row_advanced, dict) else None
                    if (
                        isinstance(promotion, dict)
                        and row_advanced.get("StepAnalyticBodyStlPath")
                        and int(promotion.get("row_offset", -1)) == 0
                    ):
                        row_count = int(promotion.get("row_count", 1) or 1)
                        actor_key = self._actor_key(body_actor)
                        if actor_key is not None and row_count > 1:
                            for trailing_offset in range(1, row_count):
                                trailing_row = int(mesh_item.row_index) + trailing_offset
                                self._row_actor_map.setdefault(trailing_row, []).append(actor_key)
                except Exception:
                    pass
            # Analytic optic surfaces / bodies (Standard caps, STEP-
            # promoted body plates, revolved lens drums) get a deep
            # body-tone outline instead of a black wireframe: sharp
            # internal feature edges plus a live view-silhouette so
            # curved bodies (the achromat drum, the plano-cyl arc) read
            # as a continuous glass rim rather than a broken outline.
            if analytic_optic_surface and mesh_opacity > 0.0:
                # Identical glass-edge palette + weights as the file-backed
                # optical prisms (shared module constants), so lenses and
                # prisms outline the same way.
                outline_tone = _OPTICAL_STEP_SILHOUETTE_COLOR
                edge_tone = _OPTICAL_STEP_EDGE_COLOR
                # View-independent outline. A truly circular lens body (a
                # sphere, a revolved doublet drum) has no sharp feature
                # edges, so its rim is drawn as a real 3-D circle -- it
                # never disappears when the view tilts (a view-dependent
                # silhouette did). A square plano-cyl plate returns no
                # circle and falls back to feature edges below.
                rim = None
                try:
                    rim = self._lens_rim_circle_polyline(mesh)
                except Exception:
                    rim = None
                if rim is not None and int(getattr(rim, "n_points", 0)) > 0:
                    feature_angle = 75.0
                    boundary_edges = False
                    self._add_mesh_actor(rim, color=outline_tone, opacity=1.0, line_width=_GLASS_EDGE_SILHOUETTE_WIDTH, track_row_index=row_index, follow_step_label=transient_step_label)
                    self._add_mesh_actor(rim, color=edge_tone, opacity=1.0, line_width=_GLASS_EDGE_LINE_WIDTH, track_row_index=row_index, follow_step_label=transient_step_label)
                    if ray_visibility_requested:
                        ray_surface_edge_overlays.append((rim, outline_tone, _GLASS_EDGE_SILHOUETTE_WIDTH + 0.6, row_index))
                        ray_surface_edge_overlays.append((rim, edge_tone, _GLASS_EDGE_LINE_WIDTH + 0.4, row_index))
                else:
                    feature_angle = 24.0
                    boundary_edges = True
                # Sharp internal / plate edges (the plano-cyl rectangle and
                # its curved-face arcs). For a circular lens this adds
                # little; for the plano-cyl plate it is the whole outline.
                try:
                    edges = self._display_feature_edges(
                        mesh,
                        feature_angle=feature_angle,
                        boundary_edges=boundary_edges,
                    )
                    if edges is not None and int(getattr(edges, "n_points", 0)) > 0:
                        self._add_mesh_actor(edges, color=edge_tone, opacity=1.0, line_width=_GLASS_EDGE_LINE_WIDTH, track_row_index=row_index, follow_step_label=transient_step_label)
                        if ray_visibility_requested:
                            ray_surface_edge_overlays.append((edges, edge_tone, _GLASS_EDGE_LINE_WIDTH + 0.4, row_index))
                except Exception:
                    pass
                drew_surfaces += 1
                continue
            if not mesh_item.is_body:
                if row_index in file_backed_rows:
                    try:
                        edges = self._display_feature_edges(
                            mesh,
                            feature_angle=row_edge_feature_angle,
                            boundary_edges=row_edge_boundary_edges,
                        )
                        if edges is not None and int(getattr(edges, "n_points", 0)) > 0:
                            self._add_mesh_actor(edges, color=file_backed_silhouette_color, opacity=1.0, line_width=file_backed_silhouette_width, track_row_index=row_index, follow_step_label=transient_step_label)
                            self._add_mesh_actor(edges, color=file_backed_edge_color, opacity=1.0, line_width=file_backed_edge_width, track_row_index=row_index, follow_step_label=transient_step_label)
                            if ray_visibility_requested:
                                ray_surface_edge_overlays.append((edges, file_backed_silhouette_color, file_backed_silhouette_width + 0.8, row_index))
                                ray_surface_edge_overlays.append((edges, file_backed_edge_color, file_backed_edge_width + 0.6, row_index))
                    except Exception:
                        pass
                    drew_surfaces += 1
                    continue
                try:
                    edges = mesh.extract_feature_edges(
                        feature_angle=10,
                        boundary_edges=True,
                        feature_edges=False,
                        manifold_edges=False,
                    )
                    if int(getattr(edges, "n_points", 0)) > 0:
                        edge_color = file_backed_edge_color if row_index in file_backed_rows else (0.15, 0.15, 0.15)
                        edge_width = 3.2 if row_index in file_backed_rows else 1.0
                        if row_index in file_backed_rows:
                            self._add_mesh_actor(edges, color=file_backed_silhouette_color, opacity=1.0, line_width=5.0, track_row_index=row_index, follow_step_label=transient_step_label)
                        self._add_mesh_actor(edges, color=edge_color, opacity=1.0, line_width=edge_width, track_row_index=row_index if row_index in file_backed_rows else None, follow_step_label=transient_step_label)
                        if ray_visibility_requested and row_index >= 0:
                            ray_surface_edge_overlays.append(
                                (
                                    edges,
                                    file_backed_silhouette_color if row_index in file_backed_rows else (0.02, 0.03, 0.05),
                                    5.4 if row_index in file_backed_rows else 1.6,
                                    row_index if row_index in file_backed_rows else None,
                                )
                            )
                            if row_index in file_backed_rows:
                                ray_surface_edge_overlays.append(
                                    (
                                        edges,
                                        file_backed_edge_color,
                                        3.5,
                                        row_index,
                                    )
                                )
                except Exception:
                    pass
            elif row_index in file_backed_rows:
                try:
                    edges = self._display_feature_edges(
                        mesh,
                        feature_angle=row_edge_feature_angle,
                        boundary_edges=row_edge_boundary_edges,
                    )
                    if int(getattr(edges, "n_points", 0)) > 0:
                        if ray_visibility_requested:
                            ray_surface_edge_overlays.append((edges, file_backed_silhouette_color, file_backed_silhouette_width + 0.8, row_index))
                            ray_surface_edge_overlays.append((edges, file_backed_edge_color, file_backed_edge_width + 0.6, row_index))
                        self._add_mesh_actor(edges, color=file_backed_silhouette_color, opacity=1.0, line_width=file_backed_silhouette_width, track_row_index=row_index, follow_step_label=transient_step_label)
                        self._add_mesh_actor(edges, color=file_backed_edge_color, opacity=1.0, line_width=file_backed_edge_width, track_row_index=row_index, follow_step_label=transient_step_label)
                except Exception:
                    pass
            drew_surfaces += 1

        surface_actor_ms = (time.perf_counter() - surface_actor_start) * 1000.0
        overlay_start = time.perf_counter()
        assigned_face_overlays = self._add_optical_solid_assigned_face_overlays(system)
        face_role_markers = 0
        virtual_plane_markers = self._add_optical_solid_virtual_plane_overlays(system)
        # Suppress placement handles while a STEP carry is active OR the
        # user has just dropped a STEP overlay and not yet promoted it
        # (the `_selected_step_label` still names a loaded but
        # unpromoted import). Without the second check, dropping a
        # carry sets carry_label back to None and the previous
        # promoted row's placement handles re-appear underneath the
        # just-placed STEP -- captured in flag_20260531_094024_040
        # "this time carry seems OK, but once placed, handels for the
        # first element come back."
        selected_step_label = str(getattr(self.editor, "_selected_step_label", "") or "").strip().lower()
        unpromoted_step_selected = bool(
            selected_step_label
            and self.editor._step_path_for_label(selected_step_label) is not None
        )
        if (
            step_carry_label is not None
            or unpromoted_step_selected
            or not self._show_scene_placement_handles()
        ):
            placement_grid_lines, placement_grid_summary = 0, ""
        else:
            placement_grid_lines, placement_grid_summary = self._add_scene_placement_grid_overlays(scene_bundle)
        detector_overlay_lines = self._add_scene_detector_overlays(
            scene_bundle,
            include_footprints=bool(self.show_detector_overlays_var.get()),
            include_miss_crosshairs=bool(self.show_terminal_diagnostics_var.get()),
        )
        # bugs/0009: the thickness dimensions must be added *after* the imported
        # STEP overlay loop below registers the optical body into
        # ``_step_actor_map`` -- otherwise ``add_overlays`` measures against an
        # empty map and paints one row->row arrow straight through the lens
        # instead of splitting around it. Deferred to ``thickness_dimensions``
        # right after the step bodies exist (matching how the live drag readout
        # reads the same already-populated map).
        thickness_dimensions = 0
        overlay_ms = (time.perf_counter() - overlay_start) * 1000.0

        ray_actor_start = time.perf_counter()
        if self.show_rays_var.get():
            if scene_bundle is not None:
                center, radius = scene_display_center_radius(scene_bundle)
            else:
                center, radius = self._row_scene_bounds()
            paths_by_ray_index = KrakenLayoutEditor._scene_ray_path_by_index(scene_bundle)
            ray_radius = max(radius * 0.0015, 0.08)
            bounded_ray_count = 0
            suppressed_endpoint_count = 0
            terminal_counts: dict[str, int] = {}
            terminal_face_counts: dict[str, int] = {}
            terminal_sequence_counts: dict[str, int] = {}
            for ray_index, color, ray_pts, terminal_status in self.editor._iter_3d_scene_ray_records(rays, scene_bundle):
                terminal_key = str(terminal_status or "unknown").strip().lower() or "unknown"
                terminal_counts[terminal_key] = int(terminal_counts.get(terminal_key, 0)) + 1
                ray_path = paths_by_ray_index.get(int(ray_index))
                if ray_path is not None:
                    sequence_summary = self._ray_path_surface_sequence_summary(ray_path)
                    if sequence_summary:
                        terminal_sequence_counts[sequence_summary] = int(terminal_sequence_counts.get(sequence_summary, 0)) + 1
                    if terminal_key in {"escaped", "stopped", "terminated", "unknown"}:
                        face_summary = self._ray_path_terminal_face_summary(ray_path)
                        if face_summary:
                            terminal_face_counts[face_summary] = int(terminal_face_counts.get(face_summary, 0)) + 1
                terminal_target = KrakenLayoutEditor._missed_detector_target_for_path(scene_bundle, ray_path)
                terminal_direction = KrakenLayoutEditor._terminal_display_direction_for_path(ray_path)
                display_ray_pts, was_bounded = KrakenLayoutEditor._bounded_3d_ray_points_for_display(
                    ray_pts,
                    center,
                    radius,
                    terminal_status=terminal_status,
                    terminal_target=terminal_target,
                    terminal_direction=terminal_direction,
                )
                if was_bounded:
                    bounded_ray_count += 1
                ray_mesh = KrakenLayoutEditor._ray_segment_mesh_for_3d_display(
                    display_ray_pts,
                    vertex_inset=KrakenLayoutEditor._ray_vertex_display_inset(radius),
                )
                if ray_mesh is None:
                    continue
                if int(getattr(ray_mesh, "n_points", 0)) < 2:
                    continue
                style = KrakenLayoutEditor._ray_terminal_3d_style(color, terminal_status)
                self._add_ray_actor(
                    ray_mesh,
                    radius=ray_radius,
                    color=style["line_color"],
                    ray_index=ray_index,
                    opacity=float(style["line_opacity"]),
                    line_width=float(style["line_width"]),
                )
                if KrakenLayoutEditor._should_draw_3d_terminal_endpoint(
                    terminal_status,
                    show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get()),
                ):
                    self._add_ray_endpoint_actor(
                        display_ray_pts[-1],
                        radius=ray_radius * float(style["endpoint_scale"]),
                        color=style["endpoint_color"],
                        ray_index=ray_index,
                        terminal_status=terminal_status,
                    )
                else:
                    suppressed_endpoint_count += 1
            if bounded_ray_count:
                self._debug_trace("ray_display_bounded", rays=bounded_ray_count, radius=float(radius))
            if suppressed_endpoint_count:
                self._debug_trace("ray_display_suppressed_diagnostic_endpoints", rays=suppressed_endpoint_count)
            for edges, edge_color, edge_width, edge_row_index in ray_surface_edge_overlays:
                transient_step_label = live_trace_step_labels_by_row.get(int(edge_row_index)) if edge_row_index is not None else None
                self._add_mesh_actor(edges, color=edge_color, opacity=1.0, line_width=edge_width, backface_culling=False, track_row_index=edge_row_index, follow_step_label=transient_step_label)
            for mesh, wire_color, wire_width, row_index in ray_surface_wire_overlays:
                transient_step_label = live_trace_step_labels_by_row.get(int(row_index))
                self._add_mesh_actor(
                    mesh,
                    color=wire_color,
                    opacity=1.0,
                    pick_row_index=row_index,
                    pick_step_label=transient_step_label,
                    follow_step_label=transient_step_label,
                    line_width=wire_width,
                    wireframe=True,
                    backface_culling=False,
                )
        else:
            bounded_ray_count = 0
            suppressed_endpoint_count = 0
            terminal_counts = {}
            terminal_face_counts = {}
            terminal_sequence_counts = {}
        ray_actor_ms = (time.perf_counter() - ray_actor_start) * 1000.0

        axis_start = time.perf_counter()
        optical_axis_overlays = 0
        if self._should_draw_optical_axis_overlays():
            optical_axis_overlays = self._add_optical_axis_pick_overlays(scene_bundle)
            if selected_axis_id:
                self._set_optical_axis_highlight(selected_axis_id)
        axis_ms = (time.perf_counter() - axis_start) * 1000.0

        selected_step = getattr(self.editor, "_selected_step_label", None)
        step_rotation_handles = 0
        step_carry_active = 0
        step_carry_grid_summary = ""
        selected_step_label = str(selected_step or "").strip().lower()
        promoted_step_source_keys = self.editor._promoted_step_source_keys_for_rows(rows)
        carry_label = self._step_carry_label()
        if (
            selected_step_label
            and selected_step_label in STEP_OVERLAY_LABEL_SET
            and selected_step_label != carry_label
            and self.editor._step_overlay_matches_promoted_row(
                selected_step_label,
                promoted_step_source_keys,
            )
        ):
            self.editor._selected_step_label = None
            selected_step = None
            selected_step_label = ""
        transient_selected_mesh = live_trace_step_mesh_by_label.get(selected_step_label)
        if transient_selected_mesh is not None and int(getattr(transient_selected_mesh, "n_points", 0)) > 0:
            if carry_label == selected_step_label:
                step_carry_active, step_carry_grid_summary = self._add_step_carry_grid_overlay(selected_step_label, transient_selected_mesh)
            step_rotation_handles += self._add_step_rotation_handles(selected_step_label, transient_selected_mesh)
        for label, builder, color, opacity in (
            ("lens", self.editor._transformed_imported_lens_step_mesh, (0.30, 0.36, 0.46), 0.26),
            ("optical", self.editor._transformed_imported_optical_step_mesh, (0.10, 0.62, 0.72), 0.34),
            ("led", self.editor._transformed_imported_led_step_mesh, (0.95, 0.62, 0.16), 0.35),
            ("camera", self.editor._transformed_imported_camera_step_mesh, (0.28, 0.33, 0.42), 0.38),
        ):
            label_is_live_trace_row = label in current_live_trace_step_overlay_labels
            if (
                label != carry_label
                and self.editor._step_overlay_matches_promoted_row(label, promoted_step_source_keys)
            ):
                continue
            try:
                cad_mesh = builder()
            except Exception as exc:
                cad_mesh = None
                self.editor.append_debug(f"3D {label} STEP error: {exc}")
            if cad_mesh is not None and int(getattr(cad_mesh, "n_points", 0)) > 0:
                if label_is_live_trace_row:
                    if str(selected_step) == label and transient_selected_mesh is None:
                        if carry_label == label:
                            step_carry_active, step_carry_grid_summary = self._add_step_carry_grid_overlay(label, cad_mesh)
                        step_rotation_handles += self._add_step_rotation_handles(label, cad_mesh)
                    continue
                display_opacity = float(opacity)
                if ray_visibility_requested and label == "optical":
                    display_opacity = max(display_opacity, 0.46)
                self._add_mesh_actor(
                    cad_mesh,
                    color=color,
                    opacity=display_opacity,
                    pick_row_index=None,
                    pick_step_label=label,
                    follow_step_label=label,
                    flat_shading=True,
                    backface_culling=False,
                )
                try:
                    try:
                        round_lens_like = bool(self._mesh_round_lens_axis(cad_mesh) is not None)
                    except Exception:
                        round_lens_like = False
                    # bugs/0020: feature-edge extraction is memoised
                    # (cached_display_feature_edges), so even the heavy
                    # 114k-cell vendor camera body computes its outline once
                    # per layout pose -- no per-frame cost -- instead of
                    # rendering edge-less behind the old >50k-cell skip.
                    # Every imported CAD overlay now shares the analytic
                    # lens glass edge palette and weight.
                    cad_edges = self._display_feature_edges(
                        cad_mesh,
                        feature_angle=75 if round_lens_like else 55,
                        boundary_edges=not round_lens_like,
                    )
                    if int(getattr(cad_edges, "n_points", 0)) > 0:
                        self._add_mesh_actor(
                            cad_edges,
                            color=_OPTICAL_STEP_SILHOUETTE_COLOR,
                            opacity=0.98,
                            line_width=_GLASS_EDGE_SILHOUETTE_WIDTH,
                            follow_step_label=label,
                            backface_culling=False,
                        )
                        self._add_mesh_actor(
                            cad_edges,
                            color=_OPTICAL_STEP_EDGE_COLOR,
                            opacity=0.96,
                            line_width=_GLASS_EDGE_LINE_WIDTH,
                            follow_step_label=label,
                            backface_culling=False,
                        )
                except Exception:
                    pass
                if str(selected_step) == label:
                    if carry_label == label:
                        step_carry_active, step_carry_grid_summary = self._add_step_carry_grid_overlay(label, cad_mesh)
                    step_rotation_handles += self._add_step_rotation_handles(label, cad_mesh)

        try:
            external_mesh = self.editor._transformed_external_camera_mesh()
        except Exception as exc:
            external_mesh = None
            self.editor.append_debug(f"3D camera CAD error: {exc}")
        if external_mesh is not None and int(getattr(external_mesh, "n_points", 0)) > 0:
            spec = self.editor._current_external_camera_spec() or {}
            self._add_mesh_actor(
                external_mesh,
                color=tuple(spec.get("color", (0.62, 0.66, 0.72))),
                opacity=float(spec.get("opacity_3d", 1.0)),
                pick_row_index=None,
                flat_shading=True,
            )

        # bugs/0009: now that the imported STEP bodies are registered in
        # ``_step_actor_map``, draw the thickness dimensions so each row->row
        # span splits around any lens between its two surfaces.
        thickness_dimensions = self._add_thickness_dimension_overlays(system, scene_bundle)

        from KrakenOS.UI.services.open3d_camera_state import apply_camera_state

        if camera_state is not None:
            if apply_camera_state(self._renderer, camera_state):
                try:
                    self._reset_camera_clipping_range_for_scene()
                except Exception:
                    camera_state = None
            else:
                camera_state = None
        if camera_state is None:
            self._renderer.ResetCamera()
            self.set_camera_preset(self._camera_preset)
        try:
            selected_table_indices = [int(index) for index in self.editor._selected_table_indices()]
        except Exception:
            selected_table_indices = []
        if len(selected_table_indices) > 1:
            self.highlight_rows(selected_table_indices)
        else:
            self.highlight_row(self.editor._current_selected_row_index())
        if selected_step in STEP_OVERLAY_LABEL_SET and self.editor._step_path_for_label(str(selected_step)) is not None:
            self._step_rotation_active_label = str(selected_step)
            self._set_step_highlight(str(selected_step))
        else:
            self._close_step_rotation_handler()
        # SelectionModel survives RemoveAllViewProps; re-apply ray and
        # optical-axis highlights against the freshly built actors. Row
        # and step highlights are re-applied above via editor selection.
        # If the prior target no longer exists in the rebuilt scene
        # (e.g. a row was deleted or a new trace produced fewer rays),
        # drop the stale selection rather than keep it haunting the
        # model invisibly.
        ray_index = self._picked_ray_index
        if ray_index is not None:
            if int(ray_index) in self._ray_actor_map:
                try:
                    self._set_ray_highlight(int(ray_index))
                except Exception:
                    pass
            else:
                self._picked_ray_index = None
        axis_id = self._picked_optical_axis_id
        if axis_id:
            available_axis_ids = {
                str((info or {}).get("axis_id", "") or "").strip()
                for info in self._actor_optical_axis_map.values()
            }
            if str(axis_id) in available_axis_ids:
                try:
                    self._set_optical_axis_highlight(str(axis_id))
                except Exception:
                    pass
            else:
                self._picked_optical_axis_id = None
        self._update_step_rotation_handler_state()
        self._update_stl_placement_handler_state()
        self.refresh_step_admin_panel()
        ray_count = len(getattr(scene_bundle, "ray_paths", []) or []) if scene_bundle is not None else len(getattr(rays, "CC", []))
        self.status_var.set(
            f"3D scene ready | surfaces={drew_surfaces} | rays={ray_count} | optical axes={optical_axis_overlays} | assigned face overlays={assigned_face_overlays} | face roles={face_role_markers} | virtual planes={virtual_plane_markers} | detector overlays={detector_overlay_lines} | thickness dimensions={thickness_dimensions} | placement grid={placement_grid_lines} | STEP carry active={step_carry_active} | STEP rotation handles={step_rotation_handles}"
        )
        self._debug_trace(
            "refresh_scene_done",
            duration_ms=round(float((time.perf_counter() - refresh_start) * 1000.0), 3),
            mesh_collect_ms=round(float(mesh_collect_ms), 3),
            actor_clear_ms=round(float(actor_clear_ms), 3),
            surface_actor_ms=round(float(surface_actor_ms), 3),
            overlay_ms=round(float(overlay_ms), 3),
            ray_actor_ms=round(float(ray_actor_ms), 3),
            axis_ms=round(float(axis_ms), 3),
            surfaces=drew_surfaces,
            rays=ray_count,
            optical_axes=optical_axis_overlays,
            assigned_face_overlays=assigned_face_overlays,
            face_role_markers=face_role_markers,
            virtual_plane_markers=virtual_plane_markers,
            detector_overlays=detector_overlay_lines,
            thickness_dimensions=thickness_dimensions,
            placement_grid=placement_grid_lines,
            step_carry_active=step_carry_active,
            step_rotation_handles=step_rotation_handles,
            counts=self._debug_actor_counts(),
        )
        self._timing_event(
            "refresh_scene_timing",
            duration_ms=round(float((time.perf_counter() - refresh_start) * 1000.0), 3),
            mesh_collect_ms=round(float(mesh_collect_ms), 3),
            actor_clear_ms=round(float(actor_clear_ms), 3),
            surface_actor_ms=round(float(surface_actor_ms), 3),
            overlay_ms=round(float(overlay_ms), 3),
            ray_actor_ms=round(float(ray_actor_ms), 3),
            axis_ms=round(float(axis_ms), 3),
            surfaces=drew_surfaces,
            rays=ray_count,
            optical_axes=optical_axis_overlays,
            step_rotation_handles=step_rotation_handles,
        )
        grid_summary = " | ".join(part for part in (placement_grid_summary, step_carry_grid_summary) if part)
        self._update_placement_grid_status(grid_summary, render=False)
        self._update_mode_badge(render=False)
        self._update_trace_summary(
            terminal_counts,
            ray_count=ray_count if bool(self.show_rays_var.get()) else 0,
            bounded_ray_count=bounded_ray_count,
            suppressed_endpoint_count=suppressed_endpoint_count,
            terminal_face_counts=terminal_face_counts,
            terminal_sequence_counts=terminal_sequence_counts,
            render=False,
        )
        self.render()
