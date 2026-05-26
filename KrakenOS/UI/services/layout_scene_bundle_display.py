from __future__ import annotations

import math
import sys

import numpy as np


_PROTECTED_GLOBALS = {
    "LayoutSceneBundleDisplayMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


def _current_pv_backend():
    value = globals().get("pv")
    if value is not None:
        return value
    layout_module = sys.modules.get("KrakenOS.UI.layout_editor")
    value = getattr(layout_module, "pv", None) if layout_module is not None else None
    if value is not None:
        globals()["pv"] = value
    return value


class LayoutSceneBundleDisplayMixin:
    def _current_field_value(self) -> float:
        try:
            return float(self.field_value_var.get())
        except ValueError:
            return 0.0

    def _current_field_angle_deg(self) -> float:
        return float(self._field_metrics().get("angle_deg", 0.0))

    def _current_field_height(self) -> float:
        return float(self._field_metrics().get("object_height", 0.0))

    def _field_metrics_for_value(self, field_type: str, raw_value: float) -> dict[str, float]:
        object_distance = self._current_object_distance()
        effl = self._current_effl_estimate()
        image_distance = self._current_image_distance()
        finite_magnification = self._current_finite_paraxial_magnification()

        with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
            if finite_magnification is not None:
                mag = max(abs(float(finite_magnification)), 1e-9)
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                else:
                    object_height = raw_value / mag
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                paraxial_image_height = mag * object_height
                real_image_height = paraxial_image_height
            else:
                if field_type == "Angle":
                    angle_deg = raw_value
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                elif field_type == "Object Height":
                    object_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(object_height, object_distance))
                elif field_type == "Paraxial Image Height":
                    paraxial_image_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(paraxial_image_height, max(effl, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))
                else:
                    real_image_height = raw_value
                    angle_deg = np.rad2deg(np.arctan2(real_image_height, max(image_distance, 1e-6)))
                    object_height = object_distance * np.tan(np.deg2rad(angle_deg))

                paraxial_image_height = effl * np.tan(np.deg2rad(angle_deg))
                real_image_height = image_distance * np.tan(np.deg2rad(angle_deg))

        if not np.isfinite(angle_deg):
            angle_deg = 0.0
        if not np.isfinite(object_height):
            object_height = 0.0
        if not np.isfinite(paraxial_image_height):
            paraxial_image_height = 0.0
        if not np.isfinite(real_image_height):
            real_image_height = 0.0
        return {
            "angle_deg": float(angle_deg),
            "object_height": float(object_height),
            "paraxial_image_height": float(paraxial_image_height),
            "real_image_height": float(real_image_height),
        }

    def _field_metrics(self) -> dict[str, float]:
        return self._field_metrics_for_value(self._current_field_type(), self._current_field_value())

    def _field_metrics_summary(self) -> dict[str, float]:
        field_type = self._current_field_type()
        sample_values = self._sample_field_values(self._current_field_value())
        if not sample_values:
            sample_values = [self._current_field_value()]
        metrics = [self._field_metrics_for_value(field_type, value) for value in sample_values]
        current_metrics = self._field_metrics()
        max_paraxial = max(abs(float(item.get("paraxial_image_height", 0.0))) for item in metrics) if metrics else 0.0
        max_real = max(abs(float(item.get("real_image_height", 0.0))) for item in metrics) if metrics else 0.0
        traced_image_diameter = self._traced_image_diameter_value()
        field_image_radius = max_paraxial if self._current_object_mode() == "Infinity" else max_real
        required_image_diameter = max(
            2.0 * field_image_radius,
            float(traced_image_diameter) if traced_image_diameter is not None else 0.0,
            1.0,
        )
        return {
            "current_angle_deg": float(current_metrics.get("angle_deg", 0.0)),
            "current_object_height": float(current_metrics.get("object_height", 0.0)),
            "current_paraxial_image_height": float(current_metrics.get("paraxial_image_height", 0.0)),
            "current_real_image_height": float(current_metrics.get("real_image_height", 0.0)),
            "max_paraxial_image_height": float(max_paraxial),
            "max_real_image_height": float(max_real),
            "image_diameter": float(required_image_diameter),
        }

    def _current_effl_estimate(self) -> float:
        try:
            effl, _ppa, _ppp = self._exact_paraxial_cardinals(self._current_wavelength())
            return max(abs(float(effl)), 1e-6)
        except Exception:
            pass
        if self.last_system is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    _a, _b, _c, _d, effl, *_rest = self.last_system.EFL(self._current_wavelength())  # type: ignore[misc]
                return max(abs(float(effl)), 1e-6)
            except Exception:
                pass
        return 100.0

    def _current_image_distance(self) -> float:
        if len(self.rows) >= 2:
            try:
                if any(row.surface == "Mirror" for row in self.rows):
                    distance, _last_source_index, _reference_rows = self._paraxial_total_image_gap(self.rows)
                else:
                    distance = float(self.rows[-2].thickness)
            except Exception:
                distance = float(self.rows[-2].thickness)
            return max(float(distance), 1e-6)
        return 100.0

    def _current_finite_paraxial_magnification(self) -> float | None:
        if self._current_object_mode() != "Finite" or len(self.rows) < 3:
            return None
        try:
            solve_rows = self.rows
            if any(row.surface == "Mirror" for row in self.rows):
                solve_rows, _last_source_index = self._paraxial_reference_rows_for_layout(self.rows)
            _a, _b, _c, _d, _effl, ppa, ppp = self._exact_paraxial_solution_for_rows(solve_rows)
            h1_vertex_z, h2_vertex_z = self._paraxial_vertex_zs(solve_rows)
            h1_z = h1_vertex_z + float(ppa)
            h2_z = h2_vertex_z + float(ppp)
            image_z = sum(float(row.thickness) for row in solve_rows[:-1])
            object_principal = float(h1_z)
            image_principal = float(image_z - h2_z)
            if (
                np.isfinite(object_principal)
                and np.isfinite(image_principal)
                and abs(object_principal) > 1e-9
            ):
                return float(image_principal / object_principal)
        except Exception:
            return None
        return None

    def _schedule_refresh_plot(self, *_args) -> None:
        if not self.winfo_exists():
            return
        if hasattr(self, "_refresh_after_id") and self._refresh_after_id is not None:
            self.after_cancel(self._refresh_after_id)
        self._refresh_after_id = self.after(120, self._refresh_plot_from_controls)

    def _refresh_plot_from_controls(self) -> None:
        self._refresh_after_id = None
        if self.optimization_running:
            return
        self.refresh_plot()

    # _style_embedded_plot removed — now in scene_renderer_2d._style_surface_lines

    def _field_colors(self, count: int) -> list[str]:
        if count <= 1:
            return ["#39FF14"]
        cmap = [
            "#39FF14",
            "#00E5FF",
            "#FF9F1C",
            "#FF4D6D",
            "#9B5DE5",
            "#FFD166",
            "#2EC4B6",
            "#E71D36",
        ]
        return [cmap[i % len(cmap)] for i in range(count)]

    # _build_world_ray_paths, _build_display_ray_paths, _render_display_surface_paths
    # removed — now in scene_builder and scene_renderer_2d

    def _current_folded_surface_geometry(
        self,
        *,
        system=None,
    ) -> tuple[np.ndarray, np.ndarray, float, list[np.ndarray], list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]]] | None:
        trace_state = self._resolved_trace_mode(system=system)
        if not bool(trace_state.get("use_folded")) or not self.rows:
            return None
        return self._compute_folded_layout_geometry()

    @staticmethod
    def _select_optical_solid_output_face(world_faces: list[dict[str, object]]) -> dict[str, object] | None:
        return select_optical_solid_output_face(world_faces)

    def _optical_solid_image_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        if len(self.rows) < 2:
            return overrides
        if system is not None:
            pose_overrides = optical_solid_output_port_pose_overrides(system, self.rows)
        else:
            pose_overrides = build_optical_solid_output_port_pose_overrides(self.rows)
        for row_index, row in enumerate(self.rows):
            if row.surface != "Image":
                continue
            pose = pose_overrides.get(row_index)
            if not isinstance(pose, dict):
                continue
            center_world = np.asarray(pose.get("center", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            normal_world = np.asarray(pose.get("normal", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
            if center_world.size < 3 or normal_world.size < 3:
                continue
            if not (np.all(np.isfinite(center_world[:3])) and np.all(np.isfinite(normal_world[:3]))):
                continue
            x0, y0 = self._project_xy([float(center_world[2])], [float(center_world[1])])
            x1, y1 = self._project_xy(
                [float(center_world[2] + normal_world[2])],
                [float(center_world[1] + normal_world[1])],
            )
            center = np.asarray((float(x0[0]), float(y0[0])), dtype=float)
            along = np.asarray((float(x1[0] - x0[0]), float(y1[0] - y0[0])), dtype=float)
            along_norm = float(np.linalg.norm(along))
            if along_norm <= 1e-12:
                along = np.asarray((0.0, 1.0), dtype=float)
                along_norm = 1.0
            overrides[row_index] = (center, along / max(along_norm, 1e-12))
        return overrides

    def _reference_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        trace_state = self._resolved_trace_mode(system=system)
        if bool(trace_state.get("use_folded")):
            return self._folded_plane_overrides()
        optical_solid_overrides = self._optical_solid_image_plane_overrides(system=system) if bool(trace_state.get("use_nonseq")) else {}
        if system is not None and self._has_off_axis_geometry():
            overrides = self._transform_reference_plane_overrides(system)
            if bool(trace_state.get("use_nonseq")):
                # KrakenOS TRANS_2A can place Object/Image reference rows at
                # internal solver stations for non-sequential scenes (notably
                # STL optical solids). The UI table still defines those
                # reference planes by row semantics instead. Preserve
                # transform-based aperture orientation only, and let Image use
                # the optical-solid output port pose when available.
                for row_index, row in enumerate(self.rows):
                    if row.surface in {"Object", "Image"}:
                        overrides.pop(row_index, None)
                overrides.update(optical_solid_overrides)
            if overrides:
                return overrides
        if optical_solid_overrides:
            return optical_solid_overrides
        return {}

    def _transform_reference_plane_overrides(self, system) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        transforms = self._system_transform_list(system)
        if transforms is None:
            return {}
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        for row_index, row in enumerate(self.rows):
            if row.surface not in {"Object", "Image", "Aperture"} or row_index >= len(transforms):
                continue
            try:
                transform = np.asarray(transforms[row_index], dtype=float)
                center_z = float(transform[2, 3])
                center_y = float(transform[1, 3])
                axis_z = float(transform[2, 2])
                axis_y = float(transform[1, 2])
                axis_norm = float(np.hypot(axis_z, axis_y))
                if axis_norm <= 1e-12:
                    continue
                x0, y0 = self._project_xy([center_z], [center_y])
                x1, y1 = self._project_xy([center_z + axis_z / axis_norm], [center_y + axis_y / axis_norm])
                center = np.array([float(x0[0]), float(y0[0])], dtype=float)
                along = np.array([float(x1[0] - x0[0]), float(y1[0] - y0[0])], dtype=float)
                along_norm = float(np.linalg.norm(along))
                if along_norm <= 1e-12:
                    continue
                overrides[row_index] = (center, along / along_norm)
            except Exception:
                continue
        return overrides

    # _reference_plane_display_points, _build_reference_plane_surface_paths
    # removed — now in scene_builder

    @staticmethod
    def _unit_display_vector(vector, fallback: np.ndarray | None = None) -> np.ndarray:
        try:
            arr = np.asarray(vector, dtype=float).ravel()
        except Exception:
            arr = np.empty(0, dtype=float)
        if arr.size >= 2 and np.all(np.isfinite(arr[:2])):
            candidate = np.asarray(arr[:2], dtype=float)
        elif fallback is not None:
            candidate = np.asarray(fallback, dtype=float).ravel()[:2]
        else:
            candidate = np.asarray((1.0, 0.0), dtype=float)
        norm = float(np.linalg.norm(candidate))
        if norm <= 1e-12:
            candidate = np.asarray((1.0, 0.0), dtype=float)
            norm = 1.0
        return candidate / norm

    def _source_display_frame(self) -> tuple[np.ndarray, np.ndarray, float]:
        try:
            source_x, source_y, source_z = self._current_source_origin()
            del source_x
        except Exception:
            source_y, source_z = 0.0, 0.0
        x_vals, y_vals = self._project_xy([source_z], [source_y])
        center = np.asarray((float(x_vals[0]), float(y_vals[0])), dtype=float)
        try:
            _source_l, source_m, source_n = self._current_source_direction()
        except Exception:
            source_m, source_n = 0.0, 1.0
        axis_x, axis_y = self._project_xy([source_n], [source_m])
        axis = np.asarray((float(axis_x[0]), float(axis_y[0])), dtype=float)
        axis = self._unit_display_vector(axis, np.asarray((1.0, 0.0), dtype=float))
        tangent = self._unit_display_vector(np.asarray((-axis[1], axis[0]), dtype=float), np.asarray((0.0, 1.0)))
        source_radius = self._current_source_radius()
        if getattr(self, "rows", None):
            try:
                source_radius = max(source_radius, 0.5 * abs(float(self.rows[0].diameter)))
            except Exception:
                pass
        return center, tangent, float(max(source_radius, 0.0))

    def _branch_output_display_targets(self) -> dict[str, np.ndarray]:
        targets: dict[str, np.ndarray] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                targets[code] = np.asarray(point[:2], dtype=float)
        return targets

    def _branch_output_display_target_frames(self) -> dict[str, tuple[np.ndarray, np.ndarray, float]]:
        source_center, source_tangent, source_radius = self._source_display_frame()
        frames: dict[str, tuple[np.ndarray, np.ndarray, float]] = {}
        for row in getattr(self, "rows", []) or []:
            advanced = getattr(row, "advanced", {}) or {}
            if not isinstance(advanced, dict):
                continue
            display_settings = advanced.get("Display2D", {})
            if not isinstance(display_settings, dict):
                continue
            raw_targets = display_settings.get("branch_output_targets")
            if not isinstance(raw_targets, dict):
                continue
            try:
                row_radius = 0.5 * abs(float(row.diameter))
            except Exception:
                row_radius = 0.0
            raw_tangent = display_settings.get("plane_tangent")
            for raw_code, raw_point in raw_targets.items():
                code = str(raw_code or "").strip().upper()
                if not code:
                    continue
                try:
                    point = np.asarray(raw_point, dtype=float).ravel()
                except Exception:
                    continue
                if point.size < 2 or not np.all(np.isfinite(point[:2])):
                    continue
                target = np.asarray(point[:2], dtype=float)
                if code in {"TT", "RR"}:
                    frames[code] = (target, source_tangent, source_radius)
                    continue
                fallback_axis = target - source_center
                fallback_tangent = np.asarray((-fallback_axis[1], fallback_axis[0]), dtype=float)
                tangent = self._unit_display_vector(raw_tangent, fallback_tangent)
                frames[code] = (target, tangent, max(row_radius, source_radius))
        return frames

    def _branch_output_display_path_overrides(self, rays) -> list[np.ndarray] | None:
        target_frames = self._branch_output_display_target_frames()
        if not target_frames or rays is None:
            return None
        source_center, source_tangent, _source_radius = self._source_display_frame()
        overrides: list[np.ndarray] = []
        used_override = False
        ray_paths = getattr(rays, "CC", ())
        if ray_paths is None:
            return None
        for ray_index, ray in enumerate(ray_paths):
            points_world = np.asarray(ray, dtype=float)
            if points_world.ndim != 2 or points_world.shape[0] < 2 or points_world.shape[1] < 3:
                overrides.append(np.empty((0, 2), dtype=float))
                continue
            x_vals, y_vals = self._project_xy(points_world[:, 2], points_world[:, 1])
            points_2d = np.column_stack((x_vals, y_vals)).astype(float)
            branch_path = str(self._raykeeper_value(rays, "BRANCH_PATH", ray_index, "") or "")
            code = "".join(self._branch_path_selector_sequence(branch_path))[-2:]
            target_frame = target_frames.get(code)
            if target_frame is not None and points_2d.shape[0] >= 2:
                target, target_tangent, max_offset = target_frame
                source_offset = float(np.dot(points_2d[0] - source_center, source_tangent))
                if abs(source_offset) <= 1e-12:
                    raw_offset = float(np.dot(points_2d[-1] - target, target_tangent))
                    if np.isfinite(raw_offset):
                        source_offset = raw_offset
                if np.isfinite(max_offset) and max_offset > 1e-9:
                    source_offset = float(np.clip(source_offset, -max_offset, max_offset))
                points_2d = np.asarray(points_2d, dtype=float).copy()
                points_2d[-1] = target + target_tangent * source_offset
                used_override = True
            overrides.append(points_2d)
        return overrides if used_override else None

    def _build_scene_bundle(self, system, rays, max_radius: float) -> SceneBundle:
        """Build a SceneBundle using the new Phase 3 pipeline."""
        orientation = self._current_display_orientation()
        trace_state = self._resolved_trace_mode(system=system)
        trace_note = str(trace_state.get("note", ""))
        trace_runtime_note = str(getattr(self, "_last_preview_trace_note", "") or "").strip()
        if trace_runtime_note:
            trace_note = f"{trace_note} {trace_runtime_note}".strip()
        folded_geometry = self._current_folded_surface_geometry(system=system)


        # Compute folded ray display overrides (pre-projected paths for folded layouts)
        folded_ray_display_paths = None
        folded_elements = None
        if folded_geometry is not None:
            _point, _direction, _mh, _ep, folded_elements = folded_geometry
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                folded_elements=folded_elements,
                folded_orientation=orientation,
                system=system,
            )
        elif bool(trace_state.get("use_folded")) and orientation == "YZ":
            folded_ray_display_paths = self._display_path_overrides_for_current_layout(
                rays, max_radius,
                system=system,
            )
        if folded_ray_display_paths is None and not bool(trace_state.get("use_nonseq")):
            folded_ray_display_paths = self._branch_output_display_path_overrides(rays)

        field_count = max(
            1,
            int(getattr(self, "_preview_field_bundle_count", self._current_field_count())),
        )

        return build_scene_bundle(
            rows=self.rows,
            system=system,
            rays=rays,
            sources=self._collect_scene_sources(wavelength=self._current_wavelength()),
            display_orientation=orientation,
            show_clipped_rays=self.show_clipped_rays_var.get(),
            field_count=field_count,
            ray_count_per_field=max(1, self._preview_field_ray_count),
            field_colors=self._field_colors(field_count),
            folded_geometry=folded_geometry,
            row_polylines_fn=self._row_layout_polylines,
            surface_meshes_fn=(
                (lambda current_system: self._iter_3d_surface_meshes(current_system, include_reference_surfaces=True))
                if _current_pv_backend() is not None
                else None
            ),
            project_fn=self._project_xy,
            reference_plane_overrides=self._reference_plane_overrides(system=system),
            folded_ray_display_paths=folded_ray_display_paths,
            folded_terminal_policy=self._current_folded_detector_policy(),
            trace_mode_requested=str(trace_state.get("requested", "Auto")),
            trace_mode_active=str(trace_state.get("active", "Sequential")),
            trace_mode_note=trace_note,
            target_surface=(
                self._current_nonseq_target_surface_index()
                if bool(trace_state.get("use_nonseq"))
                else None
            ),
            detector_surface_indices=self._scene_detector_surface_indices(trace_state),
            allow_target_plane_contact=True,
            source_row_order=normalize_source_row_order(getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)),
        )

    # _current_surface_scene, _render_current_layout_surfaces removed —
    # now in scene_builder.build_scene_bundle()

    # _build_folded_surface_paths, _surface_style_for_row, _polyline_vertical_extents,
    # _polyline_endpoints, _build_row_surface_groups, _build_curve_group_edge_paths,
    # _build_sequential_lens_edge_paths, _build_sequential_surface_paths
    # removed — now in scene_builder.py
    # _draw_colored_rays removed — now in scene_renderer_2d._draw_rays



    # --- Physical Distance overlay -------------------------------------------

    def _results_display_service(self) -> ResultsDisplayService:
        service = self.__dict__.get("_results_display_service_instance")
        if service is None:
            service = ResultsDisplayService(self)
            self._results_display_service_instance = service
        return service

    def _clear_physical_distance_artists(self) -> None:
        self._results_display_service()._clear_physical_distance_artists()

    def _on_toggle_physical_distances(self) -> None:
        self._results_display_service()._on_toggle_physical_distances()

    def _draw_physical_distances(self) -> None:
        self._results_display_service()._draw_physical_distances()

    def _update_results(self, system, rays, wavelength: float, optics_info: dict | None = None) -> None:
        self._results_display_service()._update_results(system, rays, wavelength, optics_info)

    # _set_plot_limits_from_layout removed — now in scene_renderer_2d.set_plot_limits

    def _set_plot_limits_from_drawn_data(self) -> None:
        x_values: list[float] = []
        y_values: list[float] = []
        for line in self.ax.lines:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            finite = np.isfinite(xdata) & np.isfinite(ydata)
            if np.any(finite):
                x_values.extend(xdata[finite].tolist())
                y_values.extend(ydata[finite].tolist())
        if not x_values or not y_values:
            return
        x_min = min(x_values)
        x_max = max(x_values)
        y_min = min(y_values)
        y_max = max(y_values)
        span_x = max(x_max - x_min, 1.0)
        span_y = max(y_max - y_min, 1.0)
        self.ax.set_xlim(x_min - 0.08 * span_x, x_max + 0.08 * span_x)
        self.ax.set_ylim(y_min - 0.12 * span_y, y_max + 0.12 * span_y)

    def _draw_input_ray_overlay(self, max_radius: float) -> None:
        if not self.rows:
            return
        if self._current_object_mode() == "Infinity":
            return
        object_distance = self._current_object_distance()
        if object_distance <= 1e-9:
            return
        field_samples = self._sample_field_values(self._current_field_height())
        angle_samples = self._sample_fan_angles_deg()
        colors = self._field_colors(len(field_samples))
        for field_index, field_height in enumerate(field_samples):
            color = colors[field_index]
            for angle_deg in angle_samples:
                angle_rad = np.deg2rad(angle_deg)
                pupil_y = float(field_height) + float(np.tan(angle_rad) * object_distance)
                x_vals, y_vals = self._project_xy([0.0, object_distance], [float(field_height), float(pupil_y)])
                self.ax.plot(
                    x_vals,
                    y_vals,
                    color=color,
                    linewidth=1.8,
                    alpha=0.95,
                )

    @staticmethod
    def _gaussian_radius_from_q(q_value: complex, wavelength_mm: float, m2: float, refractive_index: float) -> float:
        if not (np.isfinite(q_value.real) and np.isfinite(q_value.imag)) or abs(q_value) <= 1e-18:
            return np.nan
        inverse_q = 1.0 / q_value
        imag_inverse = float(np.imag(inverse_q))
        if imag_inverse >= 0.0:
            return np.nan
        return float(np.sqrt(-(wavelength_mm * m2) / (np.pi * max(float(refractive_index), 1e-12) * imag_inverse)))

    def _draw_gaussian_beam_overlay(self, system, wavelength: float) -> float | None:
        if self._current_source_model() != "Gaussian beam":
            return None
        source_direction = np.asarray(self._current_source_direction(), dtype=float)
        if np.linalg.norm(source_direction - np.asarray((0.0, 0.0, 1.0), dtype=float)) > 1e-9:
            self.append_debug(
                "Gaussian beam envelope skipped for non-+Z source direction; "
                "use traced source rays and Gaussian Beam Report data."
            )
            return None
        if any(row.surface == "Mirror" for row in self.rows) or self._has_off_axis_geometry():
            self.append_debug("Gaussian beam envelope skipped for folded/off-axis geometry; use Gaussian Beam Report for ABCD data.")
            return None
        try:
            paraxial_trace = system.ParaxMatrices(float(wavelength))
            input_beam = self._current_gaussian_beam_input(wavelength)
            beam_trace = Kos.propagate_gaussian_beam(paraxial_trace, input_beam)
        except Exception as exc:
            self.append_debug(f"Gaussian beam overlay unavailable: {_short_error_message(exc)}")
            return None

        wavelength_mm = float(beam_trace.wavelength_mm)
        m2 = float(input_beam.m2)
        current_z = 0.0
        source_x, source_y, source_z = self._current_source_origin()
        _unused_source_x = source_x
        q_before = complex(beam_trace.input_q)
        n_current = float(beam_trace.input_index)
        z_values: list[float] = [float(source_z)]
        radius_values: list[float] = [
            self._gaussian_radius_from_q(q_before, wavelength_mm, m2, n_current)
        ]

        for parax_step, beam_step in zip(paraxial_trace.steps, beam_trace.steps):
            q_after = complex(float(beam_step.q_real_mm), float(beam_step.q_imag_mm))
            n_after = max(float(beam_step.n_after), 1e-12)
            if str(getattr(parax_step, "kind", "")) == "translation":
                thickness = float(getattr(parax_step, "thickness", 0.0))
                sample_count = max(2, min(32, int(abs(thickness) / 5.0) + 2))
                for offset in np.linspace(0.0, thickness, sample_count)[1:]:
                    q_sample = q_before + float(offset)
                    z_values.append(float(source_z + current_z + float(offset)))
                    radius_values.append(self._gaussian_radius_from_q(q_sample, wavelength_mm, m2, n_after))
                current_z += thickness
            else:
                z_values.append(float(source_z + current_z))
                radius_values.append(self._gaussian_radius_from_q(q_after, wavelength_mm, m2, n_after))
            q_before = q_after
            n_current = n_after

        z_arr = np.asarray(z_values, dtype=float)
        r_arr = np.asarray(radius_values, dtype=float)
        finite = np.isfinite(z_arr) & np.isfinite(r_arr) & (r_arr >= 0.0)
        if np.count_nonzero(finite) < 2:
            return None
        z_arr = z_arr[finite]
        r_arr = r_arr[finite]
        y_center = float(source_y)
        upper_x, upper_y = self._project_xy(z_arr, y_center + r_arr)
        lower_x, lower_y = self._project_xy(z_arr, y_center - r_arr)
        center_x, center_y = self._project_xy(z_arr, np.full_like(z_arr, y_center))
        color = "#f59e0b"
        self.ax.plot(upper_x, upper_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(lower_x, lower_y, color=color, linewidth=1.8, linestyle="-", alpha=0.92, zorder=31.0)
        self.ax.plot(center_x, center_y, color=color, linewidth=0.85, linestyle=":", alpha=0.75, zorder=30.0)
        if self._current_display_orientation() == "YZ":
            self.ax.fill_between(
                z_arr,
                y_center - r_arr,
                y_center + r_arr,
                color=color,
                alpha=0.08,
                linewidth=0.0,
                zorder=29.0,
            )
        label_index = min(max(int(len(z_arr) * 0.12), 0), len(z_arr) - 1)
        self.ax.text(
            float(upper_x[label_index]),
            float(upper_y[label_index]),
            "Gaussian 1/e^2",
            color=color,
            fontsize=8,
            ha="left",
            va="bottom",
            zorder=61.0,
            bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.7, "pad": 0.4},
        )
        return float(np.max(np.abs(y_center) + r_arr))

    def _apply_example_display_defaults(self, path: Path) -> None:
        code = path.read_text(encoding="utf-8", errors="ignore")
        self._apply_interferometer_example_defaults(path)

        wavelength_match = re.search(r"\bW\s*=\s*([0-9]*\.?[0-9]+)", code)
        if wavelength_match:
            self.wavelength_var.set(wavelength_match.group(1))

        aperture_type_match = re.search(r"\b(?:AperType|ApType)\s*=\s*['\"](STOP|EPD|FNO)['\"]", code)
        if aperture_type_match:
            self.aperture_type_var.set(aperture_type_match.group(1))

        aperture_value_match = re.search(r"\b(?:AperVal|ApVal)\s*=\s*([0-9]*\.?[0-9]+)", code)
        if aperture_value_match:
            self.aperture_value_var.set(aperture_value_match.group(1))

        surf_match = re.search(r"\b(?:Surf|sup)\s*=\s*([0-9]+)", code)
        if surf_match:
            surf_index = surf_match.group(1)
            label = None
            for option in self.analysis_surface_menu["values"]:
                if option.startswith(f"{surf_index}:"):
                    label = option
                    break
            if label is not None:
                self.analysis_surface_var.set(label)
            else:
                self.analysis_surface_var.set("Auto")
        else:
            self.analysis_surface_var.set("Auto")

        if self._example_requests_nonsequential(code) and hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
            self.trace_mode = "Non-Sequential Preview"

    def _apply_interferometer_example_defaults(self, path: Path) -> None:
        stem = path.stem.lower()
        is_michelson = stem == "examp_michelson_interferometer"
        is_twyman = stem == "examp_twyman_green_interferometer"
        is_mach_zehnder = stem == "examp_mach_zehnder_interferometer"
        if not (is_michelson or is_twyman or is_mach_zehnder):
            return

        def _set_text_var(name: str, value: str) -> None:
            var = getattr(self, name, None)
            if var is not None:
                try:
                    var.set(value)
                except Exception:
                    pass

        _set_text_var("object_mode_var", "Infinity")
        _set_text_var("display_orientation_var", "YZ")
        _set_text_var("wavelength_var", "0.6328")
        _set_text_var("ray_count_var", "1")
        _set_text_var("source_model_var", "Collimated disk source")
        _set_text_var("source_radius_var", "0.5")
        _set_text_var("source_cone_angle_var", "0.0")
        _set_text_var("source_power_var", "1.0")
        _set_text_var("source_seed_var", "1")
        _set_text_var("source_x_var", "0.0")
        _set_text_var("source_y_var", "0.0")
        _set_text_var("source_z_var", "0.0")
        _set_text_var("source_l_var", "0.0")
        _set_text_var("source_m_var", "0.0")
        _set_text_var("source_n_var", "1.0")
        _set_text_var("field_type_var", "Angle")
        _set_text_var("field_value_var", "0.0")
        _set_text_var("field_count_var", "1")
        _set_text_var("aperture_type_var", "EPD")
        _set_text_var("aperture_value_var", "1.0")
        _set_text_var("trace_mode_var", "Non-Sequential Preview")
        _set_text_var("nonseq_ns_limit_var", "140" if is_mach_zehnder else "80")
        self.trace_mode = "Non-Sequential Preview"
        self.selected_analysis_modes = []
        self.analysis_mode = "none"
        self.secondary_analysis_mode = None
        try:
            self._sync_analysis_mode_buttons()
        except Exception:
            pass

        if is_mach_zehnder:
            return
        self._apply_michelson_family_example_metadata(is_twyman=is_twyman)

    def _apply_michelson_family_example_metadata(self, *, is_twyman: bool = False) -> None:
        title = "Twyman-Green" if is_twyman else "Michelson"
        splitter_name = "Twyman-Green splitter" if is_twyman else "Michelson splitter"
        interferogram_settings = {
            "analysis_title": f"{title} Interferogram",
            "detector_port": "cross",
            "detector_size_mm": 12.0,
            "pixels": 256,
            "fringe_tilt_x_mrad": 2.0 if is_twyman else 1.5,
            "fringe_tilt_y_mrad": 0.0,
            "opd_offset_um": 0.0,
            "visibility": 1.0,
            "coherence_mode": COHERENT_SUM_MODE_DEFAULT,
        }
        for row in self.rows:
            text = f"{getattr(row, 'name', '')} {getattr(row, 'element', '')}".strip().lower()
            advanced = dict(getattr(row, "advanced", {}) or {})
            if row.surface == BEAM_SPLITTER_SURFACE or "splitter" in text:
                row.surface = BEAM_SPLITTER_SURFACE
                row.element = splitter_name
                advanced[BEAM_SPLITTER_ADVANCED_ATTR] = _normalize_beam_splitter_settings(
                    advanced.get(BEAM_SPLITTER_ADVANCED_ATTR, BEAM_SPLITTER_DEFAULT_SETTINGS)
                )
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "BS1",
                        "element_name": splitter_name,
                        "arm_role": "Common",
                        "parent_splitter": "",
                    },
                )
                continue
            if row.surface == "Mirror" and ("transmit" in text or "test optic" in text):
                row.element = "Test optic" if is_twyman else "Transmit return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_TX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "transmit",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Mirror" and ("reflect" in text or "reference" in text):
                row.element = "Reference flat" if is_twyman else "Reflect return mirror"
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "M_RX",
                        "element_name": row.element,
                        "arm_role": "Return",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 80.0,
                    },
                )
                continue
            if row.surface == "Image" or "detector" in text or "output port" in text:
                row.element = "Detector path"
                advanced["Display2D"] = {
                    "plane_center": [50.0, -70.0],
                    "plane_tangent": [1.0, 0.0],
                    "branch_output_targets": {
                        "TT": [0.0, 0.0],
                        "TR": [50.0, -70.0],
                        "RT": [50.0, -70.0],
                        "RR": [0.0, 0.0],
                    },
                }
                advanced["Interferogram"] = interferogram_settings
                row.advanced = advanced
                self._set_element_metadata(
                    row,
                    {
                        "element_id": "DET_1",
                        "element_name": "Detector path",
                        "arm_role": "Detector",
                        "parent_splitter": "BS1",
                        "branch_selector": "reflect",
                        "arm_distance": 70.0,
                    },
                )

    @staticmethod
    def _example_requests_nonsequential(code: str) -> bool:
        return bool(re.search(r"\bNsTraceLoop\s*\(|\.\s*NsTrace\s*\(", code))




    def _plot_fallback_preview(self, max_radius: float) -> None:
        positions = []
        z = 0.0
        last_index = len(self.rows) - 1
        for row_index, row in enumerate(self.rows):
            positions.append(z)
            radius = max(row.diameter / 2.0, 0.5)
            color = "#4f81bd" if row.glass.upper() != "AIR" else "#7f8c8d"
            x_vals, y_vals = self._project_xy([z, z], [-radius, radius])
            self.ax.plot(x_vals, y_vals, color=color, linewidth=2)
            if row.surface in {"Object", "Image", "Aperture"} or row_index in {0, last_index}:
                self.ax.text(
                    float(x_vals[0]),
                    float(np.max(y_vals) + max_radius * 0.08),
                    row.name,
                    rotation=0,
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )
            z += row.thickness

        total_length = max(z, 1.0)
        margin = max(total_length * 0.05, 5.0)
        if self._current_display_orientation() in {"XZ", "XY"}:
            self._set_plot_limits_from_drawn_data()
        else:
            self.ax.set_xlim(-margin, total_length + margin)
            self.ax.set_ylim(-(max_radius * 1.4), max_radius * 1.4)
        axis_x, axis_y = self._project_xy([0.0, total_length], [0.0, 0.0])
        self.ax.plot(axis_x, axis_y, color="#2c3e50", linewidth=0.8)
        self.ax.text(
            0.01,
            0.99,
            "Fallback sequential preview",
            transform=self.ax.transAxes,
            ha="left",
            va="top",
            fontsize=8,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.75, "pad": 2.0},
        )

    def _plot_trace_failure_diagnostic(self, exc: NonSequentialTracePreviewError) -> None:
        trace_state = dict(getattr(exc, "trace_state", {}) or {})
        reasons = ", ".join(str(reason) for reason in trace_state.get("reasons", ()) or ())
        lines = [
            "Non-sequential trace failed",
            _short_error_message(exc, limit=320),
            "Sequential fallback was not drawn.",
        ]
        if reasons:
            lines.append(f"Scene trigger: {reasons}")
        self.ax.set_axis_off()
        self.ax.text(
            0.5,
            0.58,
            "\n".join(lines),
            transform=self.ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            color="#7f1d1d",
            bbox={"facecolor": "white", "edgecolor": "#7f1d1d", "alpha": 0.88, "pad": 8.0},
            wrap=True,
        )
