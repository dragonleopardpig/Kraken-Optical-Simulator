"""Legacy PyVista 3D scene assembly service."""

from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.scene_geometry import SceneBundle
from KrakenOS.UI.scene_projector import scene_display_center_radius


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class Legacy3DSceneService:
    """Populate legacy PyVista 3D scenes while delegating editor state."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _populate_legacy_3d_plotter_scene(
        self,
        plotter,
        system,
        rays,
        *,
        scene_bundle: SceneBundle | None = None,
        add_clip_plane: bool,
        add_labels: bool,
    ) -> dict[str, list]:
        le = _layout_module()
        Kraken3DInspector = le.Kraken3DInspector
        KrakenLayoutEditor = le.KrakenLayoutEditor
        _dotted_optical_axis_mesh = le._dotted_optical_axis_mesh
        pv = le.pv
        label_points: list[np.ndarray] = []
        label_text: list[str] = []
        merged_shell = None
        merged_bodies = None
        ray_actors = []
        mirror_actors = []
        lens_actors = []
        helper_actors = []
        actor_ray_map: dict[str, int] = {}
        ray_actor_map: dict[int, list] = {}
        cad_step_actors: dict[str, list[tuple[str, object]]] = {}
        cad_step_actor_map: dict[str, str] = {}
        actor_row_map: dict[str, int] = {}
        row_actor_map: dict[int, list] = {}
        file_backed_rows = {
            index
            for index, _row in enumerate(self.rows)
            if self._file_backed_stl_row_at(int(index)) is not None
        }

        def register_actor(actor, row_index: int | None = None, *, pickable: bool = False):
            if actor is None:
                return None
            try:
                actor.SetPickable(bool(pickable))
            except Exception:
                pass
            if row_index is None:
                return actor
            actor_key = Kraken3DInspector._actor_key(actor)
            if actor_key is None:
                return actor
            actor_row_map[actor_key] = row_index
            row_actor_map.setdefault(row_index, []).append(actor)
            try:
                actor._kraken_row_index = row_index
                prop = actor.GetProperty()
                if prop is not None:
                    actor._kraken_base_style = {
                        "edge_visibility": int(prop.GetEdgeVisibility()),
                        "line_width": float(prop.GetLineWidth()),
                        "edge_color": tuple(float(v) for v in prop.GetEdgeColor()),
                        "opacity": float(prop.GetOpacity()),
                        "ambient": float(prop.GetAmbient()),
                        "diffuse": float(prop.GetDiffuse()),
                    }
            except Exception:
                pass
            return actor

        def register_ray_actor(actor, ray_index: int | None):
            if actor is None:
                return None
            try:
                actor.SetPickable(ray_index is not None)
            except Exception:
                pass
            if ray_index is None:
                return actor
            actor_key = Kraken3DInspector._actor_key(actor)
            if actor_key is None:
                return actor
            ray_index = int(ray_index)
            actor_ray_map[actor_key] = ray_index
            ray_actor_map.setdefault(ray_index, []).append(actor)
            try:
                prop = actor.GetProperty()
                if prop is not None:
                    actor._kraken_ray_select_style = {
                        "color": tuple(float(v) for v in prop.GetColor()),
                        "line_width": float(prop.GetLineWidth()),
                        "opacity": float(prop.GetOpacity()),
                        "ambient": float(prop.GetAmbient()),
                        "diffuse": float(prop.GetDiffuse()),
                    }
            except Exception:
                pass
            return actor

        for mesh_item in self._scene_surface_meshes(system, scene_bundle, include_reference_surfaces=False):
            index = int(mesh_item.row_index)
            row = mesh_item.row
            mesh = mesh_item.mesh
            if mesh_item.is_stop and not mesh_item.is_body:
                ring_mesh = self._legacy_3d_stop_ring_mesh(mesh, row)
                if ring_mesh is not None and int(getattr(ring_mesh, "n_points", 0)) > 0:
                    actor = register_actor(
                        plotter.add_mesh(
                            ring_mesh,
                            color="#f59e0b",
                            opacity=0.95,
                            smooth_shading=False,
                            show_edges=False,
                            pickable=True,
                        ),
                        index,
                        pickable=True,
                    )
                    if actor is not None:
                        helper_actors.append(actor)
                if add_labels:
                    try:
                        label_points.append(np.mean(np.asarray(mesh.points, dtype=float), axis=0))
                        label_text.append(f"{index}: {row.name}")
                    except Exception:
                        pass
                continue
            actor = register_actor(
                plotter.add_mesh(
                    mesh,
                    color=mesh_item.color,
                    opacity=min(max(float(mesh_item.opacity), 0.14), 0.28)
                    if index in file_backed_rows
                    else float(mesh_item.opacity),
                    smooth_shading=not bool(mesh_item.is_body),
                    show_edges=False,
                    pickable=True,
                ),
                index,
                pickable=True,
            )
            if row.surface == "Mirror":
                mirror_actors.append(actor)
            else:
                lens_actors.append(actor)
            if not mesh_item.is_body:
                try:
                    edges = mesh.extract_feature_edges(
                        feature_angle=10,
                        boundary_edges=True,
                        feature_edges=False,
                        manifold_edges=False,
                    )
                    if int(getattr(edges, "n_points", 0)) > 0:
                        edge_actor = register_actor(
                            plotter.add_mesh(
                                edges,
                                color="#030712" if index in file_backed_rows else "#1f2937",
                                line_width=3.0 if index in file_backed_rows else 1.0,
                                pickable=False,
                            ),
                            index,
                            pickable=False,
                        )
                        if row.surface == "Mirror":
                            mirror_actors.append(edge_actor)
                        else:
                            lens_actors.append(edge_actor)
                except Exception:
                    pass
                try:
                    merged_shell = mesh.copy(deep=True) if merged_shell is None else merged_shell.merge(mesh)
                except Exception:
                    pass
            else:
                if index in file_backed_rows:
                    try:
                        edges = mesh.extract_feature_edges(
                            feature_angle=20,
                            boundary_edges=True,
                            feature_edges=True,
                            manifold_edges=False,
                        )
                        if int(getattr(edges, "n_points", 0)) > 0:
                            edge_actor = register_actor(
                                plotter.add_mesh(
                                    edges,
                                    color="#030712",
                                    line_width=3.4,
                                    pickable=False,
                                ),
                                index,
                                pickable=False,
                            )
                            lens_actors.append(edge_actor)
                    except Exception:
                        pass
                try:
                    merged_bodies = mesh.copy(deep=True) if merged_bodies is None else merged_bodies.merge(mesh)
                except Exception:
                    pass
            if add_labels and not mesh_item.is_body:
                try:
                    label_points.append(np.mean(np.asarray(mesh.points, dtype=float), axis=0))
                    label_text.append(f"{index}: {row.name}")
                except Exception:
                    pass

        try:
            external_mesh = self._transformed_external_camera_mesh()
        except Exception as exc:
            external_mesh = None
            self.append_debug(f"Legacy 3D camera CAD error: {exc}")
        if external_mesh is not None and int(getattr(external_mesh, "n_points", 0)) > 0:
            spec = self._current_external_camera_spec() or {}
            try:
                actor = plotter.add_mesh(
                    external_mesh,
                    color=tuple(spec.get("color", (0.62, 0.66, 0.72))),
                    opacity=float(spec.get("opacity_3d", 1.0)),
                    smooth_shading=False,
                    show_edges=False,
                    pickable=False,
                )
                helper_actors.append(actor)
            except Exception:
                pass

        for label, builder, color, opacity in (
            ("lens", self._transformed_imported_lens_step_mesh, "#4b5563", 0.22),
            ("optical", self._transformed_imported_optical_step_mesh, "#0891b2", 0.30),
            ("led", self._transformed_imported_led_step_mesh, "#f59e0b", 0.35),
            ("camera", self._transformed_imported_camera_step_mesh, "#6b7280", 0.32),
        ):
            try:
                cad_mesh = builder()
            except Exception as exc:
                cad_mesh = None
                self.append_debug(f"Legacy 3D {label} STEP error: {exc}")
            if cad_mesh is None or int(getattr(cad_mesh, "n_points", 0)) <= 0:
                continue
            try:
                cad_step_actors.setdefault(label, [])
                actor = plotter.add_mesh(
                    cad_mesh,
                    color=color,
                    opacity=opacity,
                    smooth_shading=False,
                    show_edges=False,
                    pickable=True,
                )
                try:
                    actor.SetPickable(True)
                except Exception:
                    pass
                actor_key = Kraken3DInspector._actor_key(actor)
                if actor_key is not None:
                    cad_step_actor_map[actor_key] = label
                cad_step_actors[label].append(("mesh", actor))
                try:
                    edges = cad_mesh.extract_feature_edges(
                        feature_angle=20,
                        boundary_edges=True,
                        feature_edges=True,
                        manifold_edges=False,
                    )
                    if int(getattr(edges, "n_points", 0)) > 0:
                        edge_actor = plotter.add_mesh(edges, color="#111827", line_width=0.8, pickable=False)
                        cad_step_actors[label].append(("edges", edge_actor))
                except Exception:
                    pass
            except Exception as exc:
                self.append_debug(f"Legacy 3D {label} STEP render error: {exc}")

        detector_display_center, detector_display_radius = self._scene_center_radius_from_bounds(plotter.bounds)
        for spec in self._scene_detector_overlay_specs(
            scene_bundle,
            cap_miss_crosshairs_to_scene=True,
            display_center=detector_display_center,
            display_radius=detector_display_radius,
        ):
            try:
                points = np.asarray(spec["points"], dtype=float)
                if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                    continue
                mesh = pv.lines_from_points(points[:, :3])
                if int(getattr(mesh, "n_points", 0)) < 2:
                    continue
                actor = plotter.add_mesh(
                    mesh,
                    color=tuple(spec["color"]),
                    opacity=float(spec["opacity"]),
                    line_width=float(spec["line_width"]),
                    pickable=False,
                    lighting=False,
                )
                helper_actors.append(actor)
            except Exception:
                continue

        merged_scene = merged_shell
        if merged_bodies is not None:
            try:
                merged_scene = merged_bodies.copy(deep=True) if merged_scene is None else merged_scene.merge(merged_bodies)
            except Exception:
                pass

        try:
            axis_mesh = _dotted_optical_axis_mesh(plotter.bounds)
            if axis_mesh is not None and int(getattr(axis_mesh, "n_points", 0)) > 0:
                axis_actor = plotter.add_mesh(
                    axis_mesh,
                    color="#0070d9",
                    opacity=0.95,
                    line_width=2.2,
                    pickable=False,
                    lighting=False,
                )
                helper_actors.append(axis_actor)
        except Exception as exc:
            self.append_debug(f"Legacy 3D optical-axis guide failed: {exc}")

        ray_radius = self._legacy_3d_ray_radius(system, rays)
        if scene_bundle is not None:
            ray_center, ray_scene_radius = scene_display_center_radius(scene_bundle)
        else:
            ray_center, ray_scene_radius = self._scene_center_radius_from_bounds(plotter.bounds)
        paths_by_ray_index = self._scene_ray_path_by_index(scene_bundle)
        suppressed_endpoint_count = 0
        for ray_index, color, ray_pts, terminal_status in self._iter_3d_scene_ray_records(rays, scene_bundle):
            ray_path = paths_by_ray_index.get(int(ray_index))
            terminal_target = self._missed_detector_target_for_path(scene_bundle, ray_path)
            terminal_direction = self._terminal_display_direction_for_path(ray_path)
            display_ray_pts, _was_bounded = self._bounded_3d_ray_points_for_display(
                ray_pts,
                ray_center,
                ray_scene_radius,
                terminal_status=terminal_status,
                terminal_target=terminal_target,
                terminal_direction=terminal_direction,
            )
            line = self._ray_segment_mesh_for_3d_display(
                display_ray_pts,
                vertex_inset=self._ray_vertex_display_inset(ray_scene_radius),
            )
            if line is None:
                continue
            if int(getattr(line, "n_points", 0)) < 2:
                continue
            style = KrakenLayoutEditor._ray_terminal_3d_style(color, terminal_status)
            actor = register_ray_actor(
                plotter.add_mesh(
                    line,
                    color=style["line_color"],
                    opacity=float(style["line_opacity"]),
                    line_width=float(style["line_width"]),
                    pickable=True,
                ),
                ray_index,
            )
            ray_actors.append(actor)
            if not self._should_draw_3d_terminal_endpoint(
                terminal_status,
                show_terminal_diagnostics=bool(self.show_terminal_diagnostics_var.get()),
            ):
                suppressed_endpoint_count += 1
                continue
            try:
                endpoint = np.asarray(display_ray_pts[-1], dtype=float).reshape(-1)[:3]
                if endpoint.size >= 3 and np.all(np.isfinite(endpoint)):
                    marker = pv.Sphere(
                        radius=max(float(ray_radius) * float(style["endpoint_scale"]), 0.08),
                        center=tuple(endpoint[:3]),
                        theta_resolution=16 if terminal_status == "missed_detector" else 12,
                        phi_resolution=10 if terminal_status == "missed_detector" else 8,
                    )
                    marker_actor = register_ray_actor(
                        plotter.add_mesh(
                            marker,
                            color=style["endpoint_color"],
                            opacity=0.96,
                            smooth_shading=False,
                            pickable=True,
                        ),
                        ray_index,
                    )
                    ray_actors.append(marker_actor)
            except Exception:
                pass
        if suppressed_endpoint_count:
            self.append_debug(f"Legacy 3D suppressed {suppressed_endpoint_count} non-physical escaped/missed terminal endpoint markers.")

        self._add_legacy_3d_physical_dimensions(plotter, helper_actors)

        if merged_scene is not None and int(getattr(merged_scene, "n_points", 0)) > 0:
            if add_clip_plane:
                try:
                    actor = plotter.add_mesh_clip_plane(
                        merged_scene,
                        normal=(1.0, 0.0, 0.0),
                        normal_rotation=True,
                        color="#f59e0b",
                        opacity=0.45,
                        name="folded_clip",
                    )
                    try:
                        actor.SetPickable(False)
                    except Exception:
                        pass
                    helper_actors.append(actor)
                except Exception as exc:
                    self.append_debug(f"Legacy 3D clip-plane setup failed: {exc}")
                try:
                    slice_mesh = merged_scene.slice(normal=(1.0, 0.0, 0.0), origin=np.asarray(merged_scene.center))
                    if int(getattr(slice_mesh, "n_points", 0)) > 0:
                        actor = plotter.add_mesh(
                            slice_mesh,
                            color="#dc2626",
                            line_width=3,
                            name="folded_section",
                            pickable=False,
                        )
                        try:
                            actor.SetPickable(False)
                        except Exception:
                            pass
                        helper_actors.append(actor)
                except Exception as exc:
                    self.append_debug(f"Legacy 3D section setup failed: {exc}")

        if add_labels and label_points and hasattr(plotter, "add_point_labels"):
            try:
                plotter.add_point_labels(
                    np.asarray(label_points, dtype=float),
                    label_text,
                    font_size=10,
                    point_size=0,
                    text_color="black",
                    fill_shape=False,
                    shape_opacity=0.0,
                    margin=2,
                    always_visible=True,
                )
            except Exception:
                pass

        return {
            "ray_actors": ray_actors,
            "actor_ray_map": actor_ray_map,
            "ray_actor_map": ray_actor_map,
            "mirror_actors": mirror_actors,
            "lens_actors": lens_actors,
            "helper_actors": helper_actors,
            "cad_step_actors": cad_step_actors,
            "cad_step_actor_map": cad_step_actor_map,
            "actor_row_map": actor_row_map,
            "row_actor_map": row_actor_map,
        }


    def _add_legacy_3d_physical_dimensions(self, plotter, helper_actors: list) -> None:
        pv = _layout_module().pv
        show_var = self.editor.__dict__.get("show_physical_distances_var")
        if show_var is None or not show_var.get():
            return
        values = self._physical_dimension_values()
        if values is None:
            return
        object_z, housing_front_z, camera_front_z, dist_object, dist_camera = values
        try:
            bounds = np.asarray(plotter.bounds, dtype=float)
            if bounds.size != 6 or not np.all(np.isfinite(bounds)) or bounds[0] > bounds[1]:
                return
        except Exception:
            return

        span_x = max(float(bounds[1] - bounds[0]), 1.0)
        span_y = max(float(bounds[3] - bounds[2]), 1.0)
        span_z = max(float(bounds[5] - bounds[4]), 1.0)
        x_dim = float(bounds[0] + 0.08 * span_x)
        y_dim = float(bounds[2] + 0.08 * span_y)
        x_low = float(bounds[0] + 0.04 * span_x)
        x_high = float(bounds[1] - 0.04 * span_x)
        y_low = float(bounds[2] + 0.04 * span_y)
        y_high = float(bounds[3] - 0.04 * span_y)
        head = max(min(span_z * 0.015, max(span_x, span_y) * 0.12), 2.0)

        def _add_actor(actor):
            if actor is not None:
                helper_actors.append(actor)
            return actor

        def _add_double_arrow(
            z1: float,
            z2: float,
            color: str,
            label: str,
            *,
            x_pos: float | None = None,
            y_pos: float | None = None,
        ) -> None:
            if abs(z2 - z1) <= 1e-9:
                return
            arrow_x = x_dim if x_pos is None else float(x_pos)
            arrow_y = y_dim if y_pos is None else float(y_pos)
            try:
                _add_actor(
                    plotter.add_mesh(
                        pv.Line((arrow_x, arrow_y, z1), (arrow_x, arrow_y, z2)),
                        color=color,
                        line_width=2.0,
                        pickable=False,
                    )
                )
                cone_radius = max(head * 0.28, 0.8)
                _add_actor(
                    plotter.add_mesh(
                        pv.Cone(center=(arrow_x, arrow_y, z1 + head * 0.5), direction=(0.0, 0.0, -1.0), height=head, radius=cone_radius),
                        color=color,
                        pickable=False,
                    )
                )
                _add_actor(
                    plotter.add_mesh(
                        pv.Cone(center=(arrow_x, arrow_y, z2 - head * 0.5), direction=(0.0, 0.0, 1.0), height=head, radius=cone_radius),
                        color=color,
                        pickable=False,
                    )
                )
                if hasattr(plotter, "add_point_labels"):
                    _add_actor(
                        plotter.add_point_labels(
                            np.asarray([(arrow_x, arrow_y, 0.5 * (z1 + z2))], dtype=float),
                            [label],
                            font_size=12,
                            point_size=0,
                            text_color=color,
                            shape_color="white",
                            shape_opacity=0.72,
                            margin=3,
                            always_visible=True,
                        )
                    )
            except Exception as exc:
                self.append_debug(f"3D dimension arrow failed: {exc}")

        _add_double_arrow(object_z, housing_front_z, "#2196f3", f"{dist_object:.1f} mm")
        _add_double_arrow(housing_front_z, camera_front_z, "#4caf50", f"{dist_camera:.1f} mm")
        led_edge_z = None
        if self.editor.__dict__.get("imported_led_step_path") is not None:
            try:
                led_edge_z = object_z + max(float(getattr(self, "led_object_edge_distance_mm", 0.0)), 0.0)
            except Exception:
                led_edge_z = None
        if led_edge_z is not None and np.isfinite(led_edge_z) and abs(led_edge_z - object_z) > 1e-9:
            led_color = "#f59e0b"
            _add_double_arrow(
                object_z,
                float(led_edge_z),
                led_color,
                f"LED {abs(float(led_edge_z - object_z)):.1f} mm",
                x_pos=x_dim + 0.08 * span_x,
                y_pos=y_dim + 0.10 * span_y,
            )
            try:
                for p1, p2 in (
                    ((x_dim + 0.08 * span_x, y_low, led_edge_z), (x_dim + 0.08 * span_x, y_high, led_edge_z)),
                    ((x_low, y_dim + 0.10 * span_y, led_edge_z), (x_high, y_dim + 0.10 * span_y, led_edge_z)),
                ):
                    _add_actor(plotter.add_mesh(pv.Line(p1, p2), color=led_color, line_width=1.5, pickable=False))
                if hasattr(plotter, "add_point_labels"):
                    _add_actor(
                        plotter.add_point_labels(
                            np.asarray([(x_dim + 0.08 * span_x, y_dim + 0.10 * span_y, led_edge_z)], dtype=float),
                            ["LED Edge"],
                            font_size=11,
                            point_size=0,
                            text_color=led_color,
                            shape_color="white",
                            shape_opacity=0.68,
                            margin=3,
                            always_visible=True,
                        )
                    )
            except Exception as exc:
                self.append_debug(f"3D LED-edge dimension failed: {exc}")

        # One Y segment and one X segment make the camera-edge marker readable
        # from both exact YZ and XZ orthographic views.
        try:
            for p1, p2 in (
                ((x_dim, y_low, camera_front_z), (x_dim, y_high, camera_front_z)),
                ((x_low, y_dim, camera_front_z), (x_high, y_dim, camera_front_z)),
            ):
                _add_actor(plotter.add_mesh(pv.Line(p1, p2), color="#ff5722", line_width=1.5, pickable=False))
            if hasattr(plotter, "add_point_labels"):
                _add_actor(
                    plotter.add_point_labels(
                        np.asarray([(x_dim, y_dim, camera_front_z)], dtype=float),
                        ["Camera Edge"],
                        font_size=11,
                        point_size=0,
                        text_color="#ff5722",
                        shape_color="white",
                        shape_opacity=0.68,
                        margin=3,
                        always_visible=True,
                    )
                )
        except Exception as exc:
            self.append_debug(f"3D camera-edge dimension failed: {exc}")

    def _configure_legacy_3d_plotter(
        self,
        plotter,
        *,
        ray_actors=None,
        mirror_actors=None,
        lens_actors=None,
        helper_actors=None,
    ) -> None:
        help_lines = [
            "KrakenOS 3D",
            "Click a surface to select its row, or a ray to inspect it",
            "Keys: I Iso  Y YZ  T Top  B Bottom  X XZ  H Home  K Save PNG  Q Close",
            "CAD/STL row selected: use bottom placement buttons, CenterRay, then Done2D or close.",
        ]
        plotter.add_text("\n".join(help_lines), position="upper_left", font_size=12, color="royalblue")
        self._set_legacy_3d_camera(
            plotter,
            self._legacy_3d_camera_preset_from_display_orientation(self._current_display_orientation()),
        )
        plotter.add_key_event("i", lambda: self._set_legacy_3d_camera(plotter, "iso"))
        plotter.add_key_event("I", lambda: self._set_legacy_3d_camera(plotter, "iso"))
        plotter.add_key_event("y", lambda: self._set_legacy_3d_camera(plotter, "yz"))
        plotter.add_key_event("Y", lambda: self._set_legacy_3d_camera(plotter, "yz"))
        plotter.add_key_event("t", lambda: self._set_legacy_3d_camera(plotter, "top"))
        plotter.add_key_event("T", lambda: self._set_legacy_3d_camera(plotter, "top"))
        plotter.add_key_event("b", lambda: self._set_legacy_3d_camera(plotter, "bottom"))
        plotter.add_key_event("B", lambda: self._set_legacy_3d_camera(plotter, "bottom"))
        plotter.add_key_event("x", lambda: self._set_legacy_3d_camera(plotter, "xz"))
        plotter.add_key_event("X", lambda: self._set_legacy_3d_camera(plotter, "xz"))
        plotter.add_key_event("h", lambda: self._set_legacy_3d_camera(plotter, "reset"))
        plotter.add_key_event("H", lambda: self._set_legacy_3d_camera(plotter, "reset"))
        plotter.add_key_event("k", lambda: self._save_legacy_3d_screenshot(plotter))
        plotter.add_key_event("K", lambda: self._save_legacy_3d_screenshot(plotter))
        plotter.add_key_event("q", self._close_legacy_3d_plotter)
        plotter.add_key_event("Q", self._close_legacy_3d_plotter)

        ray_actors = list(ray_actors or [])
        mirror_actors = list(mirror_actors or [])
        lens_actors = list(lens_actors or [])
        helper_actors = list(helper_actors or [])
        setattr(
            plotter,
            "_kraken_visibility",
            {
                "rays": True,
                "mirrors": True,
                "lenses": True,
                "helpers": True,
                "step_lens": True,
                "step_led": True,
                "step_camera": True,
            },
        )
        positions = self._legacy_3d_control_positions(plotter)
        for category_label, category_position, category_color in positions.get("__categories__", []):
            try:
                plotter.add_text(
                    category_label,
                    position=category_position,
                    font_size=10,
                    color=category_color,
                )
            except Exception:
                pass
        self._add_legacy_3d_action_button(
            plotter,
            label="Save",
            position=positions["Save"],
            callback=lambda _state: self._save_legacy_3d_screenshot(plotter),
            color="#0f766e",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Close",
            position=positions["Close"],
            callback=lambda _state: self._close_legacy_3d_plotter(),
            color="#991b1b",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Iso",
            position=positions["Iso"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "iso"),
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="YZ",
            position=positions["YZ"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "yz"),
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Top",
            position=positions["Top"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "top"),
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="XZ",
            position=positions["XZ"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "xz"),
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Bottom",
            position=positions["Bottom"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "bottom"),
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Home",
            position=positions["Home"],
            callback=lambda _state: self._set_legacy_3d_camera(plotter, "reset"),
            color="#475569",
        )
        for label, axis, delta in (
            ("X -90", "x", -90.0),
            ("X +90", "x", 90.0),
            ("Y -90", "y", -90.0),
            ("Y +90", "y", 90.0),
            ("Z -90", "z", -90.0),
            ("Z +90", "z", 90.0),
        ):
            self._add_legacy_3d_action_button(
                plotter,
                label=label,
                position=positions[label],
                callback=lambda _state, a=axis, d=delta: self.rotate_selected_step_axis(a, d),
                color="#7c3aed",
            )
        self._add_legacy_3d_action_button(
            plotter,
            label="CenterRay",
            position=positions["CenterRay"],
            callback=lambda _state: self._legacy_3d_start_center_row_to_ray(plotter),
            color="#0f766e",
        )
        self._add_legacy_stl_placement_controls(plotter, positions)
        self._add_legacy_3d_action_button(
            plotter,
            label="Center STEP",
            position=positions["Center STEP"],
            callback=lambda _state: self.start_any_step_axis_pick(),
            color="#d97706",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Obj->LED",
            position=positions["Obj-LED"],
            callback=lambda _state: self.start_led_object_edge_pick(),
            color="#d97706",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Clear Axis",
            position=positions["Clear Axis"],
            callback=lambda _state: self.clear_step_axis_offsets(),
            color="#64748b",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Rays",
            position=positions["Rays"],
            callback=lambda state: self._legacy_3d_set_scene_actor_visibility(plotter, "ray_actors", state, "rays"),
            value=True,
            color="#2563eb",
        )
        if mirror_actors:
            self._add_legacy_3d_action_button(
                plotter,
                label="Mirrors",
                position=positions["Mirrors"],
                callback=lambda state: self._legacy_3d_set_actor_visibility(mirror_actors, state, plotter, "mirrors"),
                value=True,
                color="#6b7280",
            )
        self._add_legacy_3d_action_button(
            plotter,
            label="Lenses",
            position=positions["Lenses"],
            callback=lambda state: self._legacy_3d_set_actor_visibility(lens_actors, state, plotter, "lenses"),
            value=True,
            color="#0284c7",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Helpers",
            position=positions["Helpers"],
            callback=lambda state: self._legacy_3d_set_actor_visibility(helper_actors, state, plotter, "helpers"),
            value=True,
            color="#f59e0b",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Full Pupil",
            position=positions["Full Pupil"],
            callback=lambda state: self._legacy_3d_toggle_full_pupil(plotter, state),
            value=self._is_full_pupil_mode(),
            color="#059669",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Lens CAD",
            position=positions["Lens CAD"],
            callback=lambda state: self._legacy_3d_set_step_visibility(plotter, "lens", state),
            value=True,
            color="#475569",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="LED CAD",
            position=positions["LED CAD"],
            callback=lambda state: self._legacy_3d_set_step_visibility(plotter, "led", state),
            value=True,
            color="#d97706",
        )
        self._add_legacy_3d_action_button(
            plotter,
            label="Cam CAD",
            position=positions["Cam CAD"],
            callback=lambda state: self._legacy_3d_set_step_visibility(plotter, "camera", state),
            value=True,
            color="#7c3aed",
        )
        self._enable_legacy_3d_picking(plotter)
