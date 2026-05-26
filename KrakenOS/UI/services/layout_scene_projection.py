from __future__ import annotations

import copy
import math

import numpy as np


_PROTECTED_GLOBALS = {
    "LayoutSceneProjectionMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutSceneProjectionMixin:
    def _current_display_orientation(self) -> str:
        value = getattr(self, "display_orientation_var", None)
        if value is None:
            return "YZ"
        mode = value.get().strip() if hasattr(value, "get") else str(value).strip()
        return normalize_projection_plane(mode)

    def _current_display_slice_axis(self) -> str:
        return "x" if self._current_display_orientation() == "XZ" else "y"

    def _current_projection_display_mode(self) -> str:
        value = getattr(self, "projection_display_mode_var", None)
        if value is None:
            return PROJECTION_MODE_AXIS_FIELD
        mode = value.get() if hasattr(value, "get") else str(value)
        return normalize_projection_display_mode(mode)

    @staticmethod
    def _scene_bundle_launch_sampling_mode(bundle: SceneBundle | None) -> str:
        return scene_bundle_launch_sampling_mode(bundle)

    def _should_filter_projection_axis_fields(self, bundle: SceneBundle | None) -> bool:
        return (
            self._current_projection_display_mode() == PROJECTION_MODE_AXIS_FIELD
            and self._scene_bundle_launch_sampling_mode(bundle) == "world_envelope"
        )

    def _should_filter_projection_slice(self, bundle: SceneBundle | None) -> bool:
        return self._scene_bundle_launch_sampling_mode(bundle) == "world_sections"

    def _projection_display_title(self, orientation: str, bundle: SceneBundle | None = None) -> str:
        plane = normalize_projection_plane(orientation)
        _x_label, _y_label, title = projection_axis_labels(plane)
        if self._scene_bundle_launch_sampling_mode(bundle) != "world_envelope":
            return title
        mode = self._current_projection_display_mode()
        if mode == PROJECTION_MODE_FULL_3D:
            return f"{title} full 3D"
        if plane == "XY":
            return f"{title} full footprint"
        return f"{title} axis field"

    def _project_xy(self, z, y):
        z_arr = np.asarray(z, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        return z_arr, y_arr

    def _apply_display_orientation_to_lines(self, start_index: int = 0) -> None:
        if self._current_display_orientation() == "YZ":
            return
        for line in self.ax.lines[start_index:]:
            xdata = np.asarray(line.get_xdata(orig=False), dtype=float)
            ydata = np.asarray(line.get_ydata(orig=False), dtype=float)
            if xdata.size == 0 or ydata.size == 0:
                continue
            proj_x, proj_y = self._project_xy(xdata, ydata)
            line.set_xdata(proj_x)
            line.set_ydata(proj_y)

    def _has_off_axis_geometry(self) -> bool:
        # AxisMove=1 is the default for sequential surfaces and only takes effect
        # in the presence of a real tilt/decenter, so it is not by itself a sign
        # of off-axis geometry. Mirrors and explicit tilts/decenters are.
        for row in self.rows:
            if row.surface == "Mirror":
                return True
            if any(
                abs(value) > 1e-9
                for value in (row.tilt_x, row.tilt_y, row.tilt_z, row.desp_x, row.desp_y, row.desp_z)
            ):
                return True
        return False

    def _has_beam_splitter_surface(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if row.surface == BEAM_SPLITTER_SURFACE or BEAM_SPLITTER_ADVANCED_ATTR in advanced:
                return True
        return False

    def _has_diffuse_scatter_surface(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if row.surface == DIFFUSE_OBJECT_SURFACE or DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
                return True
        return False

    def _has_optical_stl_solid(self) -> bool:
        for row in self.rows:
            advanced = row.advanced or {}
            if isinstance(advanced, dict) and self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                return True
        return False

    def _can_build_folded_layout(self) -> bool:
        mirror_count = 0
        for row in self.rows:
            if row.surface == "Mirror":
                mirror_count += 1
            elif row.surface not in {"Object", "Image", "Standard", "Aperture"}:
                return False
        return mirror_count >= 1

    @staticmethod
    def _reflect_2d(direction: np.ndarray, line_angle_deg: float) -> np.ndarray:
        theta = np.deg2rad(float(line_angle_deg))
        tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
        tangent_norm = np.linalg.norm(tangent)
        if tangent_norm <= 1e-12:
            return direction
        tangent /= tangent_norm
        normal = np.array([-tangent[1], tangent[0]], dtype=float)
        reflected = direction - 2.0 * np.dot(direction, normal) * normal
        norm = np.linalg.norm(reflected)
        if norm <= 1e-12:
            return direction
        return reflected / norm

    @staticmethod
    def _display_mirror_angle_deg(row: SurfaceRow) -> float:
        # KrakenOS TiltX projects with the opposite sign in the Z-Y folded
        # cross-section used by the 2D layout preview.
        return -float(row.tilt_x)

    @staticmethod
    def _mirror_line_angle_deg(
        row: SurfaceRow,
        mirror_tangent: np.ndarray | None = None,
    ) -> float:
        if mirror_tangent is not None:
            tangent = np.asarray(mirror_tangent, dtype=float)
            if tangent.shape == (2,) and np.linalg.norm(tangent) > 1e-12:
                return float(np.rad2deg(np.arctan2(tangent[1], tangent[0])))
        return KrakenLayoutEditor._display_mirror_angle_deg(row)

    @staticmethod
    def _snap_display_direction(direction: np.ndarray, tolerance: float = 0.03) -> np.ndarray:
        d = np.asarray(direction, dtype=float)
        norm = np.linalg.norm(d)
        if norm <= 1e-12:
            return np.array([0.0, 1.0], dtype=float)
        d /= norm
        if abs(d[0]) <= tolerance:
            return np.array([0.0, 1.0 if d[1] >= 0.0 else -1.0], dtype=float)
        if abs(d[1]) <= tolerance:
            return np.array([1.0 if d[0] >= 0.0 else -1.0, 0.0], dtype=float)
        return d

    def _folded_initial_frame(self, orientation: str | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return display-space object point, chief direction, and transverse axis."""
        mode = orientation or self._current_display_orientation()
        point = np.array([0.0, 0.0], dtype=float)
        if mode == "Horizontal":
            direction = np.array([0.0, -1.0], dtype=float)
        else:
            direction = np.array([1.0, 0.0], dtype=float)
        tangent = np.array([-direction[1], direction[0]], dtype=float)
        return point, direction, tangent

    @classmethod
    def _folded_mirror_slant_deg_for_branch(
        cls,
        row: SurfaceRow,
        branch_dir: np.ndarray,
        *,
        orientation: str | None = None,
    ) -> float:
        branch = np.asarray(branch_dir, dtype=float)
        branch /= max(np.linalg.norm(branch), 1e-12)
        branch_angle = float(np.rad2deg(np.arctan2(branch[1], branch[0])))
        if orientation == "Horizontal":
            # Horizontal display is read left-to-right.  Flip the display slant
            # convention so a positive 45 deg mirror sends the folded path to
            # the right instead of back toward negative display X.
            return cls._normalize_mirror_slant_deg(branch_angle + 90.0 - float(row.tilt_x))
        return cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))

    @staticmethod
    def _intersect_ray_with_line(
        origin: np.ndarray,
        direction: np.ndarray,
        center: np.ndarray,
        line_angle_deg: float,
    ) -> tuple[np.ndarray | None, float | None]:
        theta = np.deg2rad(float(line_angle_deg))
        tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
        matrix = np.column_stack((direction, -tangent))
        try:
            t_ray, t_line = np.linalg.solve(matrix, center - origin)
        except np.linalg.LinAlgError:
            return None, None
        if t_ray < 0:
            return None, None
        point = origin + direction * t_ray
        return point, float(t_line)

    @staticmethod
    def _glass_index_for_preview(name: str) -> float:
        glass = str(name).strip()
        key = glass.upper()
        if key in _PREVIEW_GLASS_INDEX_CACHE:
            return _PREVIEW_GLASS_INDEX_CACHE[key]
        parts = [part.strip() for part in glass.split(",")]
        compact = parts[0].upper() if parts else key
        if glass in {"", "AIR", "NULL"}:
            return 1.0
        if compact in {"", "AIR", "NULL"}:
            return 1.0
        if compact == "MIRROR":
            return 1.0
        if compact == "NVK" and len(parts) >= 2:
            try:
                value = float(parts[1])
                _PREVIEW_GLASS_INDEX_CACHE[key] = value
                return value
            except Exception:
                pass
        if compact == "___BLANK" and len(parts) >= 4:
            try:
                value = float(parts[3])
                _PREVIEW_GLASS_INDEX_CACHE[key] = value
                return value
            except Exception:
                pass
        alias = {
            "BK7": "H-K9L",
            "K9": "H-K9L",
            "FS": "F_SILICA",
            "SILICA": "F_SILICA",
        }.get(compact, compact)
        catalog_value = _glass_nd_vd_from_setup(alias)
        if catalog_value is not None:
            value = float(catalog_value[0])
            _PREVIEW_GLASS_INDEX_CACHE[key] = value
            return value
        fallback = {
            "BK7": 1.5168,
            "H-K9L": 1.5168,
            "F2": 1.6200,
            "FS": 1.4585,
            "F_SILICA": 1.4585,
            "SILICA": 1.4585,
            "ZF13": 1.78472,
            "H-ZF13": 1.78472,
        }.get(alias, 1.5)
        _PREVIEW_GLASS_INDEX_CACHE[key] = float(fallback)
        return float(fallback)

    @staticmethod
    def _intersect_ray_with_spherical_surface(
        origin: np.ndarray,
        direction: np.ndarray,
        vertex: np.ndarray,
        axis_dir: np.ndarray,
        radius: float,
    ) -> tuple[np.ndarray | None, float | None]:
        if abs(radius) <= 1e-9:
            return None, None
        axis = np.asarray(axis_dir, dtype=float)
        axis /= max(np.linalg.norm(axis), 1e-12)
        tangent = np.array([-axis[1], axis[0]], dtype=float)
        center = vertex + axis * float(radius)
        oc = origin - center
        a = float(np.dot(direction, direction))
        b = 2.0 * float(np.dot(direction, oc))
        c = float(np.dot(oc, oc) - radius * radius)
        disc = b * b - 4.0 * a * c
        if disc < 0.0:
            return None, None
        root = np.sqrt(disc)
        candidates = [(-b - root) / (2.0 * a), (-b + root) / (2.0 * a)]
        candidates = [t for t in candidates if t >= 1e-9]
        if not candidates:
            return None, None
        t_ray = min(candidates)
        point = origin + direction * t_ray
        local = point - vertex
        return point, float(np.dot(local, tangent))

    @staticmethod
    def _intersect_ray_with_plane(
        origin: np.ndarray,
        direction: np.ndarray,
        center: np.ndarray,
        axis_dir: np.ndarray,
    ) -> tuple[np.ndarray | None, float | None]:
        axis = np.asarray(axis_dir, dtype=float)
        axis /= max(np.linalg.norm(axis), 1e-12)
        tangent = np.array([-axis[1], axis[0]], dtype=float)
        angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
        return KrakenLayoutEditor._intersect_ray_with_line(origin, direction, center, angle)

    @staticmethod
    def _refract_ray_2d(direction: np.ndarray, normal: np.ndarray, n_before: float, n_after: float) -> np.ndarray:
        d = np.asarray(direction, dtype=float)
        d /= max(np.linalg.norm(d), 1e-12)
        n = np.asarray(normal, dtype=float)
        n /= max(np.linalg.norm(n), 1e-12)
        if np.dot(d, n) > 0.0:
            n = -n
        eta = float(n_before) / float(n_after)
        cos_i = -float(np.dot(n, d))
        k = 1.0 - eta * eta * (1.0 - cos_i * cos_i)
        if k < 0.0:
            reflected = d + 2.0 * cos_i * n
            return reflected / max(np.linalg.norm(reflected), 1e-12)
        refracted = eta * d + (eta * cos_i - np.sqrt(k)) * n
        return refracted / max(np.linalg.norm(refracted), 1e-12)

    def _compute_folded_layout_geometry(self):
        return self._compute_folded_layout_geometry_for_rows(self.rows, orientation=self._current_display_orientation())

    def _compute_folded_layout_geometry_for_rows(
        self,
        rows: list[SurfaceRow],
        *,
        orientation: str | None = None,
    ):
        point, direction, tangent0 = self._folded_initial_frame(orientation)
        max_half = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
        extent_points = [point.copy()]
        elements: list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]] = []
        if not rows:
            return point, direction, max_half, extent_points, elements
        display_orientation = orientation or self._current_display_orientation()

        current_dir = direction.copy()
        current_point = point + current_dir * max(float(rows[0].thickness), 0.0)
        extent_points.append(current_point.copy())

        for row_index, row in enumerate(rows[1:], start=1):
            travel = max(float(row.thickness), 0.0)
            branch_dir = current_dir / max(np.linalg.norm(current_dir), 1e-12)
            branch_tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
            center_point = current_point + branch_dir * float(row.desp_z) + branch_tangent * float(row.desp_y)
            if row.surface == "Image" and travel > 0.0:
                center_point = center_point + branch_dir * travel
                travel = 0.0

            mirror_tangent = None
            if row.surface == "Mirror":
                slant_angle = self._folded_mirror_slant_deg_for_branch(
                    row,
                    branch_dir,
                    orientation=display_orientation,
                )
                mirror_tangent = np.array(
                    [np.cos(np.deg2rad(slant_angle)), np.sin(np.deg2rad(slant_angle))],
                    dtype=float,
                )

            elements.append((row.surface, center_point.copy(), row, branch_dir.copy(), mirror_tangent, False))
            extent_points.append(center_point.copy())

            if row.surface == "Mirror":
                slant_angle = self._folded_mirror_slant_deg_for_branch(
                    row,
                    branch_dir,
                    orientation=display_orientation,
                )
                current_dir = self._snap_display_direction(self._reflect_2d(branch_dir, slant_angle))
            else:
                current_dir = branch_dir
            current_point = center_point + current_dir * travel
            extent_points.append(current_point.copy())

        _unused = tangent0
        return point, direction, max_half, extent_points, elements

    def _compute_world_folded_layout_geometry(self, *, system=None):
        return self._compute_world_folded_layout_geometry_for_rows(self.rows, system=system)

    def _compute_world_folded_layout_geometry_for_rows(self, rows: list[SurfaceRow], *, system=None):
        _unused = system
        return self._compute_folded_layout_geometry_for_rows(rows, orientation=self._current_display_orientation())

    def _world_folded_geometry_from_transforms(
        self,
        rows: list[SurfaceRow],
        trans: list,
        max_half: float,
    ):
        """Build folded geometry using the system's actual TRANS_2A transforms."""
        point = np.array([0.0, 0.0], dtype=float)
        direction = np.array([1.0, 0.0], dtype=float)
        extent_points: list[np.ndarray] = [point.copy()]
        elements: list[tuple[str, np.ndarray, SurfaceRow, np.ndarray]] = []

        for row_index, row in enumerate(rows):
            t = np.asarray(trans[row_index], dtype=float)
            # TRANS_2A is a 4×4 matrix; translation is in the last column.
            # World-space position in (Z, Y) for Vertical display:
            z_world = float(t[2, 3])
            y_world = float(t[1, 3])
            center = np.array([z_world, y_world], dtype=float)
            extent_points.append(center.copy())
            if row_index == 0:
                # Object row — skip (not in elements list)
                continue

            # Always compute t_prev for row_index >= 1 (used for both
            # last-surface branch_dir and mirror tangent computation).
            t_prev = np.asarray(trans[row_index - 1], dtype=float)

            # Determine the local propagation direction from consecutive
            # surface positions (finite difference).
            if row_index + 1 < len(rows):
                t_next = np.asarray(trans[row_index + 1], dtype=float)
                dz = float(t_next[2, 3]) - z_world
                dy = float(t_next[1, 3]) - y_world
                branch_dir = np.array([dz, dy], dtype=float)
                norm = np.linalg.norm(branch_dir)
                if norm > 1e-9:
                    branch_dir /= norm
                else:
                    branch_dir = direction.copy()
            else:
                # Last surface — use direction from previous surface
                dz = z_world - float(t_prev[2, 3])
                dy = y_world - float(t_prev[1, 3])
                branch_dir = np.array([dz, dy], dtype=float)
                norm = np.linalg.norm(branch_dir)
                branch_dir = branch_dir / norm if norm > 1e-9 else direction.copy()
            branch_dir = self._snap_display_direction(branch_dir)

            mirror_tangent = None
            if row.surface == "Mirror":
                slant_angle = self._mirror_display_slant_deg_for_rows(rows, row_index)
                mirror_tangent = np.array(
                    [np.cos(np.deg2rad(slant_angle)), np.sin(np.deg2rad(slant_angle))],
                    dtype=float,
                )

            elements.append((row.surface, center.copy(), row, branch_dir.copy(), mirror_tangent, False))

        return point, direction, max_half, extent_points, elements

    def _world_folded_preview_ray_paths(self, max_half: float) -> list[np.ndarray]:
        return self._world_folded_preview_ray_paths_for_rows(self.rows, max_half)

    def _world_folded_preview_ray_paths_for_rows(self, rows: list[SurfaceRow], max_half: float) -> list[np.ndarray]:
        if not rows or not any(row.surface == "Mirror" for row in rows):
            return []
        point, direction, _max_half, _extent_points, elements = self._compute_world_folded_layout_geometry_for_rows(rows)
        tangent0 = np.array([-direction[1], direction[0]], dtype=float)
        paths: list[np.ndarray] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(self._resolved_preview_pupil_radius(max_half))
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    path, _reached_image = self._trace_folded_preview_ray(origin, d, elements)
                    paths.append(np.asarray(path, dtype=float))
        else:
            object_distance = max(float(rows[0].thickness), 1e-9) if rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin, d, elements)
                    paths.append(np.asarray(path, dtype=float))
        return paths

    def _folded_preview_spot_rms_for_rows(self, rows: list[SurfaceRow]) -> float:
        point, direction, max_half, _extent_points, elements = self._compute_world_folded_layout_geometry_for_rows(rows)
        _unused = (point, direction)
        if not elements or elements[-1][0] != "Image":
            raise RuntimeError("Folded best-focus solve requires an Image row after the mirror")
        _surface_type, image_center, image_row, branch_dir, *_rest = elements[-1]
        tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
        tangent /= max(np.linalg.norm(tangent), 1e-12)
        half = max(float(image_row.diameter) / 2.0, 0.5)
        hits: list[float] = []
        for path in self._world_folded_preview_ray_paths_for_rows(rows, max_half):
            if path.shape[0] < 2:
                continue
            hit = np.asarray(path[-1], dtype=float)
            along = float(np.dot(hit - image_center, tangent))
            if abs(along) <= half + 1e-9:
                hits.append(along)
        if not hits:
            raise RuntimeError("No folded image-plane ray hits")
        values = np.asarray(hits, dtype=float)
        centered = values - float(np.mean(values))
        return float(np.sqrt(np.mean(centered * centered)))

    def _folded_plane_overrides(self) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        if not self._can_build_folded_layout() or not self.rows:
            return {}
        point, direction, _max_half, _extent_points, elements = self._compute_folded_layout_geometry()
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {0: (point.copy(), direction.copy())}
        for index, (surface_type, center, _row, branch_dir, *_rest) in enumerate(elements, start=1):
            if surface_type in {"Image", "Aperture"}:
                overrides[index] = (np.asarray(center, dtype=float).copy(), np.asarray(branch_dir, dtype=float).copy())
        return overrides

    def _world_folded_plane_overrides(self, *, system=None) -> dict[int, tuple[np.ndarray, np.ndarray]]:
        if not self.rows:
            return {}
        if not any(row.surface == "Mirror" for row in self.rows):
            return {}
        # Reuse the folded geometry (which uses TRANS_2A when available)
        try:
            geom = self._compute_world_folded_layout_geometry(system=system)
        except Exception:
            return {}
        if geom is None:
            return {}
        point, direction, _mh, _ep, elements = geom
        overrides: dict[int, tuple[np.ndarray, np.ndarray]] = {0: (point.copy(), direction.copy())}
        for index, (surface_type, center, _row, branch_dir, *_rest) in enumerate(elements, start=1):
            if surface_type in {"Image", "Aperture"}:
                overrides[index] = (np.asarray(center, dtype=float).copy(), np.asarray(branch_dir, dtype=float).copy())
        return overrides

    def _trace_folded_preview_ray(
        self,
        origin: np.ndarray,
        initial_dir: np.ndarray,
        elements: list,
    ) -> tuple[list[np.ndarray], bool]:
        p = np.asarray(origin, dtype=float).copy()
        path = [p.copy()]
        current_dir = np.asarray(initial_dir, dtype=float).copy()
        current_medium = 1.0
        reached_image = False
        for surface_type, center, row, branch_dir, *_rest in elements:
            if surface_type == "Mirror":
                mirror_tangent = _rest[0] if _rest else None
                reverse_reflection = bool(_rest[1]) if len(_rest) > 1 else False
                mirror_angle = self._mirror_line_angle_deg(row, mirror_tangent)
                hit, along = self._intersect_ray_with_line(p, current_dir, center, mirror_angle)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                p = hit
                current_dir = self._reflect_2d(current_dir, mirror_angle)
                if reverse_reflection:
                    current_dir = -current_dir
            elif surface_type == "Standard":
                if abs(float(row.rc)) <= 1e-9:
                    hit, along = self._intersect_ray_with_plane(p, current_dir, center, branch_dir)
                    normal = np.asarray(branch_dir, dtype=float)
                else:
                    hit, along = self._intersect_ray_with_spherical_surface(
                        p, current_dir, center, branch_dir, float(row.rc)
                    )
                    if hit is not None:
                        axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
                        sphere_center = center + axis * float(row.rc)
                        normal = hit - sphere_center
                    else:
                        normal = np.asarray(branch_dir, dtype=float)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                next_medium = self._glass_index_for_preview(row.glass)
                current_dir = self._refract_ray_2d(current_dir, normal, current_medium, next_medium)
                current_medium = next_medium
                p = hit
            elif surface_type in {"Image", "Aperture"}:
                tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                hit, along = self._intersect_ray_with_line(p, current_dir, center, angle)
                if hit is None:
                    break
                half = max(row.diameter / 2.0, 0.5)
                if surface_type != "Image" and along is not None and abs(along) > half:
                    break
                if np.linalg.norm(hit - path[-1]) > 1e-9:
                    path.append(hit.copy())
                p = hit
                if surface_type == "Image":
                    reached_image = True
                    break
        return path, reached_image

    def _preview_ray_start_specs(self, max_half: float, *, system=None) -> list[tuple[np.ndarray, np.ndarray]]:
        point, direction, tangent0 = self._folded_initial_frame("Horizontal")
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(
            self._resolved_preview_pupil_radius(
                max_half,
                system=system,
            )
        )
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    starts.append((origin, d.copy()))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    starts.append((origin.copy(), d))
        return starts

    def _world_preview_ray_start_specs(self, max_half: float, *, system=None) -> list[tuple[np.ndarray, np.ndarray]]:
        point, direction, tangent0 = self._folded_initial_frame("Vertical")
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        pupil_samples = self._sample_ray_heights(
            self._resolved_preview_pupil_radius(
                max_half,
                system=system,
            )
        )
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                d = np.cos(angle) * direction + np.sin(angle) * tangent0
                d /= max(np.linalg.norm(d), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    starts.append((origin, d.copy()))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    d = target - origin
                    d /= max(np.linalg.norm(d), 1e-12)
                    starts.append((origin.copy(), d))
        return starts

    def _folded_display_ray_paths_for_elements(
        self,
        max_half: float,
        elements,
        *,
        orientation: str | None = None,
        system=None,
    ) -> list[np.ndarray]:
        if elements is None:
            return []
        point, direction, tangent0 = self._folded_initial_frame(orientation)
        source_starts = self._folded_source_display_start_specs(orientation=orientation)
        if source_starts is not None:
            paths = []
            for origin, ray_dir in source_starts:
                path, _reached_image = self._trace_folded_preview_ray(origin, ray_dir, elements)
                paths.append(np.asarray(path, dtype=float))
            return paths
        pupil_radius = self._resolved_preview_pupil_radius(max_half, system=system)
        pupil_samples = self._sample_ray_heights(pupil_radius)
        field_values = self._sample_field_values(
            self._current_field_angle_deg() if self._current_object_mode() == "Infinity" else self._current_field_height()
        )
        paths: list[np.ndarray] = []
        if self._current_object_mode() == "Infinity":
            for field_value in field_values:
                angle = np.deg2rad(float(field_value))
                chief_dir = np.cos(angle) * direction + np.sin(angle) * tangent0
                chief_dir /= max(np.linalg.norm(chief_dir), 1e-12)
                for pupil_y in pupil_samples:
                    origin = point + tangent0 * float(pupil_y)
                    path, _reached_image = self._trace_folded_preview_ray(origin, chief_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
                # Keep parity with the native off-axis preview, which traces a
                # second orthogonal fan.  In this 2-D section that fan projects
                # to the chief ray, so it intentionally overlays the center path.
                for _pupil_x in pupil_samples:
                    path, _reached_image = self._trace_folded_preview_ray(point.copy(), chief_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
        else:
            object_distance = max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0
            for field_value in field_values:
                origin_base = point + tangent0 * float(field_value)
                for pupil_y in pupil_samples:
                    target = point + direction * object_distance + tangent0 * float(pupil_y)
                    ray_dir = target - origin_base
                    ray_dir /= max(np.linalg.norm(ray_dir), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin_base, ray_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
                for _pupil_x in pupil_samples:
                    target = point + direction * object_distance
                    ray_dir = target - origin_base
                    ray_dir /= max(np.linalg.norm(ray_dir), 1e-12)
                    path, _reached_image = self._trace_folded_preview_ray(origin_base, ray_dir, elements)
                    paths.append(np.asarray(path, dtype=float))
        return paths

    def _build_element_display_paths(
        self,
        rays,
        elements,
        starts: list[tuple[np.ndarray, np.ndarray]],
    ) -> list[np.ndarray]:
        if elements is None:
            return []
        element_map = {index + 1: item for index, item in enumerate(elements)}
        paths: list[np.ndarray] = []
        for ray_index, surface_ids_raw in enumerate(rays.SURFACE):
            if ray_index >= len(starts):
                break
            origin, current_dir = starts[ray_index]
            current_point = np.asarray(origin, dtype=float).copy()
            current_medium = 1.0
            path = [current_point.copy()]
            surface_ids = [int(v) for v in np.asarray(surface_ids_raw, dtype=int).ravel().tolist()]
            last_id: int | None = None
            for surface_index in surface_ids:
                if surface_index == last_id:
                    continue
                element = element_map.get(surface_index)
                if element is None:
                    continue
                surface_type, center, row, branch_dir, *_rest = element
                success = False
                if surface_type == "Mirror":
                    mirror_tangent = _rest[0] if _rest else None
                    reverse_reflection = bool(_rest[1]) if len(_rest) > 1 else False
                    mirror_angle = self._mirror_line_angle_deg(row, mirror_tangent)
                    hit, along = self._intersect_ray_with_line(current_point, current_dir, center, mirror_angle)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    current_point = hit
                    current_dir = self._reflect_2d(current_dir, mirror_angle)
                    if reverse_reflection:
                        current_dir = -current_dir
                    success = True
                elif surface_type == "Standard":
                    if abs(float(row.rc)) <= 1e-9:
                        hit, along = self._intersect_ray_with_plane(current_point, current_dir, center, branch_dir)
                        normal = np.asarray(branch_dir, dtype=float)
                    else:
                        hit, along = self._intersect_ray_with_spherical_surface(
                            current_point, current_dir, center, branch_dir, float(row.rc)
                        )
                        if hit is not None:
                            axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
                            sphere_center = center + axis * float(row.rc)
                            normal = hit - sphere_center
                        else:
                            normal = np.asarray(branch_dir, dtype=float)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    next_medium = self._glass_index_for_preview(row.glass)
                    current_dir = self._refract_ray_2d(current_dir, normal, current_medium, next_medium)
                    current_medium = next_medium
                    current_point = hit
                    success = True
                elif surface_type in {"Image", "Aperture"}:
                    tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                    angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                    hit, along = self._intersect_ray_with_line(current_point, current_dir, center, angle)
                    if hit is None:
                        break
                    half = max(row.diameter / 2.0, 0.5)
                    if surface_type != "Image" and along is not None and abs(along) > half:
                        break
                    if np.linalg.norm(hit - path[-1]) > 1e-9:
                        path.append(hit.copy())
                    current_point = hit
                    success = True
                    if surface_type == "Image":
                        last_id = surface_index
                        break
                if not success:
                    break
                last_id = surface_index
            if last_id is not None and 0 < last_id < len(elements):
                trailing = list(range(last_id + 1, len(elements) + 1))
                if trailing and all(elements[idx - 1][0] in {"Image", "Aperture"} for idx in trailing):
                    for surface_index in trailing:
                        surface_type, center, row, branch_dir, *_rest = element_map[surface_index]
                        tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                        angle = np.rad2deg(np.arctan2(tangent[1], tangent[0]))
                        hit, along = self._intersect_ray_with_line(current_point, current_dir, center, angle)
                        if hit is None:
                            break
                        half = max(row.diameter / 2.0, 0.5)
                        if surface_type != "Image" and along is not None and abs(along) > half:
                            break
                        if np.linalg.norm(hit - path[-1]) > 1e-9:
                            path.append(hit.copy())
                        current_point = hit
                        if surface_type == "Image":
                            break
            paths.append(np.asarray(path, dtype=float))
        return paths

    def _folded_source_display_start_specs(
        self,
        *,
        orientation: str | None = None,
    ) -> list[tuple[np.ndarray, np.ndarray]] | None:
        if self._current_source_model() == SOURCE_MODEL_DEFAULT:
            return None
        try:
            source_bundle = self._build_random_source_bundle()
        except Exception as exc:
            self.append_debug(f"Folded source display fallback: {_short_error_message(exc)}")
            return None
        if source_bundle is None:
            return None
        _x_values, y_values, z_values, _l_values, m_values, n_values = (
            np.asarray(values, dtype=float).reshape(-1) for values in source_bundle
        )
        count = min(len(y_values), len(z_values), len(m_values), len(n_values))
        if count <= 0:
            return None
        mode = orientation or self._current_display_orientation()
        starts: list[tuple[np.ndarray, np.ndarray]] = []
        for index in range(count):
            if mode == "Horizontal":
                origin = np.array([-float(y_values[index]), -float(z_values[index])], dtype=float)
                direction = np.array([-float(m_values[index]), -float(n_values[index])], dtype=float)
            else:
                origin = np.array([float(z_values[index]), float(y_values[index])], dtype=float)
                direction = np.array([float(n_values[index]), float(m_values[index])], dtype=float)
            norm = float(np.linalg.norm(direction))
            if norm <= 1e-12:
                continue
            starts.append((origin, direction / norm))
        return starts or None

    def _build_mapped_display_paths_from_actual_hits(
        self,
        rays,
        elements,
        starts: list[tuple[np.ndarray, np.ndarray]],
        system,
    ) -> list[np.ndarray]:
        trans = getattr(system, "TRANS_2A", None)
        if trans is None:
            return self._build_element_display_paths(rays, elements, starts)
        element_map = {index + 1: item for index, item in enumerate(elements)}
        paths: list[np.ndarray] = []
        for ray_index, surface_ids_raw in enumerate(rays.SURFACE):
            if ray_index >= len(starts):
                break
            path = [np.asarray(starts[ray_index][0], dtype=float).copy()]
            previous_actual = path[-1].copy()
            surface_ids = [int(v) for v in np.asarray(surface_ids_raw, dtype=int).ravel().tolist()]
            hit_points = np.asarray(rays.CC[ray_index], dtype=float)
            if hit_points.ndim != 2 or hit_points.shape[0] < 2:
                paths.append(np.asarray(path, dtype=float))
                continue
            for surface_index, hit_world in zip(surface_ids, hit_points[1:]):
                element = element_map.get(surface_index)
                if element is None:
                    continue
                surface_type, center, _row, branch_dir, *_rest = element
                hit_actual = np.array([float(hit_world[2]), float(hit_world[1])], dtype=float)
                hit_display = hit_actual.copy()
                if surface_type in {"Mirror", "Image", "Aperture"} and surface_index < len(trans):
                    t = np.asarray(trans[surface_index], dtype=float)
                    actual_center = np.array([float(t[2, 3]), float(t[1, 3])], dtype=float)
                    actual_tangent = np.array([float(t[2, 1]), float(t[1, 1])], dtype=float)
                    actual_norm = np.linalg.norm(actual_tangent)
                    if actual_norm > 1e-12:
                        actual_tangent /= actual_norm
                        if surface_type == "Mirror" and _rest:
                            display_tangent = np.asarray(_rest[0], dtype=float).copy()
                        else:
                            display_tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
                        display_norm = np.linalg.norm(display_tangent)
                        if display_norm > 1e-12:
                            display_tangent /= display_norm
                            if np.dot(actual_tangent, display_tangent) < 0.0:
                                display_tangent = -display_tangent
                            along = float(np.dot(hit_display - actual_center, actual_tangent))
                            candidate_a = np.asarray(center, dtype=float) + display_tangent * along
                            candidate_b = np.asarray(center, dtype=float) - display_tangent * along
                            actual_dir = hit_actual - previous_actual
                            actual_dir_norm = np.linalg.norm(actual_dir)
                            if actual_dir_norm > 1e-12:
                                actual_dir /= actual_dir_norm
                                candidate_dirs = []
                                for candidate in (candidate_a, candidate_b):
                                    disp_dir = candidate - path[-1]
                                    disp_norm = np.linalg.norm(disp_dir)
                                    if disp_norm > 1e-12:
                                        disp_dir /= disp_norm
                                        candidate_dirs.append((float(np.dot(disp_dir, actual_dir)), candidate))
                                    else:
                                        candidate_dirs.append((-np.inf, candidate))
                                hit_display = max(candidate_dirs, key=lambda item: item[0])[1]
                            else:
                                hit_display = candidate_a
                if np.linalg.norm(hit_display - path[-1]) > 1e-9:
                    path.append(hit_display)
                previous_actual = hit_actual
                if surface_type == "Image":
                    break
            paths.append(np.asarray(path, dtype=float))
        return paths

    def _project_world_ray_paths_for_display(self, rays) -> list[np.ndarray]:
        paths: list[np.ndarray] = []
        for ray in getattr(rays, "CC", ()):
            pts = np.asarray(ray, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                paths.append(np.empty((0, 2), dtype=float))
                continue
            proj_x, proj_y = self._project_xy(pts[:, 2], pts[:, 1])
            paths.append(np.column_stack((proj_x, proj_y)))
        return paths

    def _display_path_overrides_for_current_layout(
        self,
        rays,
        max_half: float,
        *,
        folded_elements=None,
        folded_orientation: str | None = None,
        system=None,
    ) -> list[np.ndarray] | None:
        if folded_elements is not None:
            orientation = folded_orientation or self._current_display_orientation()
            return self._folded_display_ray_paths_for_elements(
                max_half,
                folded_elements,
                orientation=orientation,
                system=system,
            )
        if self._can_build_folded_layout():
            geom = self._compute_world_folded_layout_geometry(system=system)
            if geom is not None:
                return self._folded_display_ray_paths_for_elements(
                    max_half,
                    geom[-1],
                    orientation=self._current_display_orientation(),
                    system=system,
                )
        return None

    @staticmethod
    def _galvo_scan_overlay_values(row: SurfaceRow) -> list[float]:
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return []
        display_settings = advanced.get("Display2D", {})
        if not isinstance(display_settings, dict):
            return []
        raw_values = display_settings.get(GALVO_SCAN_OVERLAY_KEY)
        if raw_values in (None, "", "None"):
            return []
        try:
            if isinstance(raw_values, str):
                return _parse_float_sequence_text(raw_values)
            if isinstance(raw_values, (int, float)):
                return [float(raw_values)]
            return _dedupe_float_values([float(value) for value in raw_values])
        except Exception:
            return []

    def _pose_tolerance_entries(self) -> list[dict[str, object]]:
        entries: list[dict[str, object]] = []
        for row_index, row in enumerate(self.rows):
            if row.surface == "Object":
                continue
            enabled_fields = self._surface_type_enabled_fields(row.surface)
            for field in POSE_TOLERANCE_FIELDS:
                if field not in enabled_fields:
                    continue
                # Mirror TiltX keeps the dedicated galvo/folded-scan overlay.
                if field == "tilt_x" and row.surface == "Mirror":
                    continue
                values = self._pose_tolerance_overlay_values(row, field)
                if len(values) <= 1:
                    continue
                entries.append(
                    {
                        "row_index": int(row_index),
                        "field": field,
                        "values": values[:POSE_TOLERANCE_MAX_VARIANTS],
                        "nominal": float(getattr(row, field)),
                    }
                )
        return entries

    def _pose_tolerance_variant_assignments(self) -> list[list[tuple[int, str, float]]]:
        entries = self._pose_tolerance_entries()
        if not entries:
            return []
        lengths = [len(entry["values"]) for entry in entries]
        if len(set(lengths)) == 1:
            variants = [
                [
                    (int(entry["row_index"]), str(entry["field"]), float(entry["values"][value_index]))
                    for entry in entries
                ]
                for value_index in range(lengths[0])
            ]
        else:
            pools = [
                [
                    (int(entry["row_index"]), str(entry["field"]), float(value))
                    for value in entry["values"]
                ]
                for entry in entries
            ]
            variants = [list(combo) for combo in product(*pools)]
            if len(variants) > POSE_TOLERANCE_MAX_VARIANTS:
                self.append_debug(
                    f"Pose tolerance overlay truncated from {len(variants)} to {POSE_TOLERANCE_MAX_VARIANTS} variants."
                )
                variants = variants[:POSE_TOLERANCE_MAX_VARIANTS]

        nominal_by_key = {
            (int(entry["row_index"]), str(entry["field"])): float(entry["nominal"])
            for entry in entries
        }
        filtered: list[list[tuple[int, str, float]]] = []
        for variant in variants:
            if any(abs(float(value) - nominal_by_key.get((row_index, field), float("nan"))) > 1e-12 for row_index, field, value in variant):
                filtered.append(variant)
        return filtered[:POSE_TOLERANCE_MAX_VARIANTS]

    def _rows_with_pose_tolerance_assignment(self, assignment: list[tuple[int, str, float]]) -> list[SurfaceRow]:
        rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for row_index, field, value in assignment:
            if 0 <= row_index < len(rows) and field in POSE_TOLERANCE_FIELDS:
                setattr(rows[row_index], field, float(value))
        return rows

    @staticmethod
    def _pose_tolerance_assignment_label(assignment: list[tuple[int, str, float]]) -> str:
        labels = []
        for row_index, field, value in assignment:
            labels.append(f"S{row_index} {COLUMN_LABELS.get(field, field).split()[0]}={float(value):g}")
        return "; ".join(labels)

    def _project_pose_tolerance_rows(
        self,
        rows: list[SurfaceRow],
        *,
        max_radius: float,
        wavelength: float,
        orientation: str,
    ) -> ProjectedScene2D:
        original_rows = self.rows
        original_note = str(getattr(self, "_last_preview_trace_note", "") or "")
        original_backend = str(getattr(self, "_last_preview_trace_backend", "") or "")
        original_ray_count = int(getattr(self, "_preview_field_ray_count", 1) or 1)
        original_field_count = int(getattr(self, "_preview_field_bundle_count", 1) or 1)
        try:
            self.rows = rows
            system = _build_system_from_specs(self._serializable_specs_for_rows(rows), build=1)
            rays = Kos.raykeeper(system)
            self._trace_preview_rays(
                system,
                rays,
                wavelength,
                max_radius,
                allow_full_pupil=False,
                sampling_mode="display_slice",
            )
            bundle = self._build_scene_bundle(system, rays, max_radius)
            return project_scene_bundle(
                bundle,
                orientation,
                filter_arm_view=self._filter_projected_scene_for_arm_view,
            )
        finally:
            self.rows = original_rows
            self._last_preview_trace_note = original_note
            self._last_preview_trace_backend = original_backend
            self._preview_field_ray_count = original_ray_count
            self._preview_field_bundle_count = original_field_count

    def _draw_projected_pose_tolerance_overlay(
        self,
        projected: ProjectedScene2D,
        *,
        assignment: list[tuple[int, str, float]],
        color: str,
        alpha: float,
        linewidth: float,
    ) -> BoundsRect:
        bounds_points: list[np.ndarray] = []
        affected_rows = {row_index for row_index, _field, _value in assignment}
        for ray in projected.rays:
            if not self.show_clipped_rays_var.get() and not projected_ray_hits_detector(ray):
                continue
            pts = np.asarray(ray.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            bounds_points.append(pts)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color=color,
                linewidth=linewidth,
                alpha=alpha,
                linestyle=(0, (3, 2)),
                zorder=26.0,
            )
        for curve in projected.curves:
            if int(curve.row_index) not in affected_rows:
                continue
            pts = np.asarray(curve.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            bounds_points.append(pts)
            self.ax.plot(
                pts[:, 0],
                pts[:, 1],
                color=color,
                linewidth=max(linewidth * 1.35, 0.9),
                alpha=min(alpha + 0.18, 0.9),
                linestyle=(0, (5, 2)),
                zorder=52.0,
            )
        return BoundsRect.from_points(bounds_points)

    def _draw_pose_tolerance_overlay(self, max_radius: float, *, wavelength: float) -> BoundsRect:
        assignments = self._pose_tolerance_variant_assignments()
        if not assignments:
            return BoundsRect()
        orientation = self._current_display_orientation()
        palette = ("#f97316", "#0ea5e9", "#e11d48", "#8b5cf6", "#14b8a6", "#84cc16")
        ray_count_hint = max(1, int(getattr(self, "_preview_field_ray_count", 5) or 5))
        linewidth = 0.95 if ray_count_hint <= 9 else 0.58
        alpha = 0.52 if ray_count_hint <= 9 else 0.34
        bounds: list[BoundsRect] = []
        for variant_index, assignment in enumerate(assignments):
            rows = self._rows_with_pose_tolerance_assignment(assignment)
            try:
                projected = self._project_pose_tolerance_rows(
                    rows,
                    max_radius=max_radius,
                    wavelength=wavelength,
                    orientation=orientation,
                )
            except Exception as exc:
                self.append_debug(
                    f"Pose tolerance overlay failed for {self._pose_tolerance_assignment_label(assignment)}: {_short_error_message(exc)}"
                )
                continue
            color = palette[variant_index % len(palette)]
            bounds.append(
                self._draw_projected_pose_tolerance_overlay(
                    projected,
                    assignment=assignment,
                    color=color,
                    alpha=alpha,
                    linewidth=linewidth,
                )
            )
        if bounds:
            self.status_var.set(f"Pose tolerance overlay: {len(bounds)} variant ray trace(s).")
        return self._combined_plot_bounds(*bounds)

    @staticmethod
    def _combined_plot_bounds(*bounds_items: BoundsRect | None) -> BoundsRect:
        points: list[np.ndarray] = []
        for bounds in bounds_items:
            if bounds is None or bounds.is_empty:
                continue
            points.append(
                np.asarray(
                    [
                        [float(bounds.x_min), float(bounds.y_min)],
                        [float(bounds.x_max), float(bounds.y_max)],
                    ],
                    dtype=float,
                )
            )
        return BoundsRect.from_points(points)

    def _folded_scan_overlay_plans(self, max_half: float, *, system=None) -> list[dict[str, object]]:
        if not self.rows or not self._can_build_folded_layout():
            return []
        scan_rows = [
            (index, self._galvo_scan_overlay_values(row))
            for index, row in enumerate(self.rows)
            if row.surface == "Mirror"
        ]
        scan_rows = [(index, values) for index, values in scan_rows if values]
        if not scan_rows:
            return []
        orientation = self._current_display_orientation()
        palette = ("#f97316", "#0ea5e9", "#e11d48", "#8b5cf6", "#14b8a6")
        ray_count_hint = max(1, int(getattr(self, "_preview_field_ray_count", 5) or 5))
        plans: list[dict[str, object]] = []
        try:
            # A galvo scan changes the reflected ray direction, not the fixed
            # downstream F-theta lens and detector geometry.
            _point, _direction, _mh, _extent_points, fixed_elements = self._compute_folded_layout_geometry_for_rows(
                self.rows,
                orientation=orientation,
            )
        except Exception as exc:
            self.append_debug(f"Galvo scan overlay geometry failed: {_short_error_message(exc)}")
            return []
        for mirror_index, values in scan_rows:
            display_values = self._mirror_overlay_display_slants_for_rows(self.rows, mirror_index)
            nominal_display_tilt = self._mirror_display_slant_deg_for_rows(self.rows, mirror_index)
            if not (0 < mirror_index <= len(fixed_elements)):
                continue
            mirror_surface, mirror_center, mirror_row, _incoming_dir, *_mirror_rest = fixed_elements[mirror_index - 1]
            if mirror_surface != "Mirror":
                continue
            downstream_elements = fixed_elements[mirror_index:]
            upstream_elements = fixed_elements[:mirror_index]
            pupil_radius = self._resolved_preview_pupil_radius(max_half, system=system)
            pupil_samples = self._sample_ray_heights(pupil_radius)
            source_starts = self._folded_source_display_start_specs(orientation=orientation)
            if source_starts is None:
                point, direction, tangent0 = self._folded_initial_frame(orientation)
                field_values = self._sample_field_values(
                    self._current_field_angle_deg()
                    if self._current_object_mode() == "Infinity"
                    else self._current_field_height()
                )
                source_starts = folded_fallback_source_start_specs(
                    point,
                    direction,
                    tangent0,
                    field_values,
                    pupil_samples,
                    object_mode=self._current_object_mode(),
                    object_distance=max(float(self.rows[0].thickness), 1e-9) if self.rows else 1.0,
                )
            nominal_paths = []
            for start_point, start_dir in source_starts:
                nominal_path, _reached = self._trace_folded_preview_ray(start_point, start_dir, upstream_elements)
                nominal_paths.append(nominal_path)
            incoming_states = folded_scan_incoming_states(nominal_paths)
            for value_index, tilt_x in enumerate(values[:25]):
                display_tilt = display_values[value_index] if value_index < len(display_values) else float(tilt_x)
                field_theta = 2.0 * (float(display_tilt) - float(nominal_display_tilt))
                if abs(float(field_theta)) <= 1.0e-9:
                    # The nominal mirror pose is already covered by the traced
                    # folded preview. Drawing the same path again as a scan
                    # overlay makes the center bundle look like a special ray.
                    continue
                paths = []
                try:
                    for previous, ray_dir in incoming_states:
                        hit, along = self._intersect_ray_with_line(
                            previous,
                            ray_dir,
                            np.asarray(mirror_center, dtype=float),
                            float(display_tilt),
                        )
                        if hit is None:
                            continue
                        half = max(float(mirror_row.diameter) / 2.0, 0.5)
                        if along is not None and abs(along) > half:
                            continue
                        scan_dir = self._reflect_2d(ray_dir, float(display_tilt))
                        path, _reached_image = self._trace_folded_preview_ray(hit, scan_dir, downstream_elements)
                        paths.append(np.asarray(path, dtype=float))
                except Exception as exc:
                    self.append_debug(f"Galvo scan overlay failed for TiltX={tilt_x:g}: {_short_error_message(exc)}")
                    continue
                color = palette[value_index % len(palette)]
                plan = folded_scan_overlay_plan(
                    paths,
                    field_theta=float(field_theta),
                    display_tilt=float(display_tilt),
                    mirror_center=mirror_center,
                    mirror_diameter=float(mirror_row.diameter),
                    color=color,
                    ray_count_hint=ray_count_hint,
                )
                enriched_plan = dict(plan)
                enriched_plan.update(
                    {
                        "mirror_row_index": int(mirror_index),
                        "tilt_x": float(tilt_x),
                        "display_tilt": float(display_tilt),
                        "field_theta": float(field_theta),
                        "orientation": orientation,
                    }
                )
                plans.append(enriched_plan)
        return plans

    def _draw_folded_scan_overlay(self, max_half: float, *, system=None) -> BoundsRect:
        plans = self._folded_scan_overlay_plans(max_half, system=system)
        bounds_points: list[np.ndarray] = []
        for plan in plans:
            color = str(plan.get("color", "#f97316") or "#f97316")
            bounds_points.extend(np.asarray(points, dtype=float) for points in list(plan.get("bounds_points", []) or []))
            for path in list(plan.get("paths", []) or []):
                pts = np.asarray(path, dtype=float)
                self.ax.plot(
                    pts[:, 0],
                    pts[:, 1],
                    color=color,
                    linewidth=max(0.85, float(plan.get("linewidth", 1.1) or 1.1) * 0.9),
                    alpha=min(0.72, float(plan.get("alpha", 0.92) or 0.92)),
                    linestyle=(0, (4, 2)),
                    zorder=24.0,
                )
            line = plan.get("mirror_line")
            if line is not None:
                line = np.asarray(line, dtype=float)
                self.ax.plot(
                    line[:, 0],
                    line[:, 1],
                    color=color,
                    linewidth=1.5,
                    linestyle=(0, (4, 2)),
                    alpha=0.78,
                    zorder=58.0,
                )
            label_point = plan.get("label_point")
            if label_point is not None:
                label_point = np.asarray(label_point, dtype=float)
                self.ax.text(
                    float(label_point[0]),
                    float(label_point[1]),
                    str(plan.get("label", f"theta={float(plan.get('field_theta', 0.0)):g} deg")),
                    fontsize=7,
                    color=color,
                    ha="center",
                    va="center",
                    zorder=62.0,
                    bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.72, "pad": 0.25},
                )
        return BoundsRect.from_points(bounds_points)

    # _build_current_display_ray_paths removed — now in scene_builder + scene_projector
    # _draw_reference_plane_labels removed — now in scene_builder + scene_renderer_2d

    def _clear_cardinal_marker_artists(self) -> None:
        for artist in self._cardinal_marker_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._cardinal_marker_artists.clear()

    def _on_toggle_cardinal_markers(self) -> None:
        self._clear_cardinal_marker_artists()
        if not self.show_cardinals_var.get():
            self.canvas.draw_idle()
            self.status_var.set("PP / EP / XP hidden")
            return

        if self._last_optics_info is None and self.last_system is not None and self.last_rays is not None:
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    self._last_optics_info = self._collect_optics_info(
                        self.last_system,
                        self.last_rays,
                        self._current_wavelength(),
                    )
            except Exception:
                self._last_optics_info = None

        if self._last_optics_info is None:
            self.canvas.draw_idle()
            self.status_var.set("PP / EP / XP unavailable for current view")
            return

        self._draw_optics_markers(self._last_optics_info)
        self.canvas.draw_idle()
        self.status_var.set("PP / EP / XP updated")
        self._autosave_plot()

    def _current_show_path_labels(self) -> bool:
        var = getattr(self, "show_path_labels_var", None)
        if var is not None:
            try:
                return bool(var.get())
            except Exception:
                pass
        return bool(getattr(self, "show_path_labels", True))

    def _on_toggle_path_labels(self) -> None:
        self.show_path_labels = self._current_show_path_labels()
        if getattr(self, "last_system", None) is None or getattr(self, "last_rays", None) is None:
            self._mark_plot_update_pending()
            return
        try:
            self.refresh_plot(suppress_analysis=True)
            self.status_var.set("2D labels shown" if self.show_path_labels else "2D labels hidden")
        except Exception:
            self._mark_plot_update_pending()

    def _on_ray_display_mode_changed(self, _event=None) -> None:
        mode = self._current_ray_display_mode()
        self._set_optional_var("ray_display_mode_var", mode)
        if getattr(self, "last_system", None) is None or getattr(self, "last_rays", None) is None:
            self._mark_plot_update_pending()
            return
        try:
            self.refresh_plot(suppress_analysis=True)
            self.status_var.set(f"2D ray display: {mode}")
        except Exception:
            self._mark_plot_update_pending()

    def _draw_optics_markers(self, optics_info: dict) -> None:
        self._clear_cardinal_marker_artists()
        if not self.show_cardinals_var.get():
            return
        if bool(self._resolved_trace_mode().get("use_folded")) and self._draw_folded_optics_markers(optics_info):
            return
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        x_min, x_max = min(x0, x1), max(x0, x1)
        y_min, y_max = min(y0, y1), max(y0, y1)
        span_x = max(x_max - x_min, 1e-9)
        span_y = max(y_max - y_min, 1e-9)
        marker_specs = [
            ("Front PP", optics_info.get("h1_z"), None, "#ff9f1c"),
            ("Back PP", optics_info.get("h2_z"), None, "#ff9f1c"),
            ("EP", optics_info.get("ep_z"), optics_info.get("ep_radius"), "#00bcd4"),
            ("XP", optics_info.get("xp_z"), optics_info.get("xp_radius"), "#e91e63"),
        ]

        visible_markers = []
        for label, z_pos, half_length, color in marker_specs:
            if z_pos is None:
                continue
            z_val = float(z_pos)
            if z_val < x_min or z_val > x_max:
                continue
            visible_markers.append((label, z_val, half_length, color))

        cap_half = max(0.8, min(0.025 * span_x, 0.035 * span_y))
        for index, (label, marker_pos, half_length, color) in enumerate(visible_markers):
            use_extent = (
                label in {"EP", "XP"}
                and half_length is not None
                and np.isfinite(float(half_length))
                and float(half_length) > 1e-9
            )
            z_val = float(marker_pos)
            if use_extent:
                seg_x, seg_y = self._project_xy(
                    [z_val, z_val],
                    [-float(half_length), float(half_length)],
                )
                p0 = np.array([float(seg_x[0]), float(seg_y[0])], dtype=float)
                p1 = np.array([float(seg_x[1]), float(seg_y[1])], dtype=float)
                artists = self._draw_cardinal_extent_marker(
                    p0,
                    p1,
                    color,
                    cap_half=cap_half,
                )
            else:
                artists = [
                    self.ax.axvline(z_val, color=color, linewidth=1.0, linestyle=":", alpha=0.9, zorder=70.0)
                ]
            y_label = y_max - (0.10 + 0.065 * (index % 4)) * span_y
            text = self.ax.text(
                z_val,
                y_label,
                label,
                color=color,
                fontsize=8,
                ha="center",
                va="top",
                zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._cardinal_marker_artists.extend((*artists, text))

    def _draw_arm_labels(self, projected) -> None:
        if not self._current_show_path_labels():
            return
        if self._draw_physical_ray_segment_labels(projected):
            return
        catalog = self._arm_catalog()
        if not catalog:
            return
        view_key = self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))
        palette = ("#0f766e", "#b45309", "#2563eb", "#be123c", "#6d28d9", "#047857")
        labeled_keys = self._draw_arm_ray_labels(projected, catalog, view_key, palette)
        key_to_entry = {entry["key"]: entry for entry in catalog}
        row_to_key: dict[int, str] = {}
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            key = self._arm_key_from_metadata(self._element_metadata(self.rows[start]))
            if key in key_to_entry:
                for row_index in range(start, end + 1):
                    row_to_key[row_index] = key
            index = max(end + 1, index + 1)
        if not row_to_key:
            return

        y0, y1 = self.ax.get_ylim()
        span_y = max(abs(float(y1) - float(y0)), 1.0)
        arm_points: dict[str, list[np.ndarray]] = {entry["key"]: [] for entry in catalog}
        for curve in getattr(projected, "curves", []):
            key = row_to_key.get(int(curve.row_index))
            if not key:
                continue
            pts = np.asarray(curve.points_2d, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
            if np.any(finite):
                arm_points[key].append(np.mean(pts[finite], axis=0))

        for index, entry in enumerate(catalog):
            if view_key and entry["key"] != view_key:
                continue
            if entry["key"] in labeled_keys:
                continue
            points = arm_points.get(entry["key"]) or []
            if not points:
                continue
            center = np.mean(np.vstack(points), axis=0)
            detail = entry["detail"]
            label = entry["short_label"] if not detail else f"{entry['short_label']}\n{detail}"
            y_offset = (0.035 + 0.018 * (index % 3)) * span_y
            color = palette[index % len(palette)]
            self.ax.text(
                float(center[0]),
                float(center[1]) + y_offset,
                label,
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                zorder=72.0,
                clip_on=True,
                bbox={
                    "facecolor": "white",
                    "edgecolor": color,
                    "alpha": 0.78,
                    "boxstyle": "round,pad=0.25",
                    "linewidth": 0.8,
                },
            )

    def _projected_scene_for_layout_render(
        self,
        projected: ProjectedScene2D,
        *,
        suppress_scene_labels: bool | None = None,
    ) -> ProjectedScene2D:
        if suppress_scene_labels is None:
            suppress_scene_labels = self._uses_michelson_leg_workflow()
        return projected_scene_for_layout_render(
            projected,
            suppress_scene_labels=bool(suppress_scene_labels),
        )

    def _plot_leg_label_text(self, leg_id: str, short_label: str, detail: str) -> str:
        return leg_label_text(self._physical_leg_workflow(), leg_id, short_label, detail)

    def _projected_center_for_row(self, projected, row_index: int) -> np.ndarray | None:
        if 0 <= row_index < len(self.rows):
            display_settings = (self.rows[row_index].advanced or {}).get("Display2D", {})
            if isinstance(display_settings, dict):
                center_value = display_settings.get("plane_center")
                try:
                    center = np.asarray(center_value, dtype=float).ravel()
                except Exception:
                    center = np.empty(0, dtype=float)
                if center.size >= 2 and np.all(np.isfinite(center[:2])):
                    return np.asarray(center[:2], dtype=float)
        points: list[np.ndarray] = []
        for curve in getattr(projected, "curves", []) or []:
            if int(getattr(curve, "row_index", -1)) != int(row_index):
                continue
            curve_points = np.asarray(getattr(curve, "points_2d", []), dtype=float)
            if curve_points.ndim != 2 or curve_points.shape[0] < 1:
                continue
            finite = np.isfinite(curve_points[:, 0]) & np.isfinite(curve_points[:, 1])
            if np.any(finite):
                points.append(curve_points[finite])
        if points:
            return np.mean(np.vstack(points), axis=0)
        return None

    def _first_row_index_matching(self, predicate) -> int | None:
        for index, row in enumerate(self.rows):
            try:
                if predicate(index, row):
                    return index
            except Exception:
                continue
        return None

    @staticmethod
    def _leg_geometry_from_points(points: list[np.ndarray]) -> dict[str, object] | None:
        return leg_geometry_from_points(points)

    @staticmethod
    def _leg_geometry_point_at_fraction(leg: dict[str, object], fraction: float) -> np.ndarray | None:
        return leg_geometry_point_at_fraction(leg, fraction)

    def _first_beam_splitter_indices(self) -> list[int]:
        return [index for index, row in enumerate(self.rows) if row.surface == BEAM_SPLITTER_SURFACE]

    def _first_detector_index_matching(self, predicate) -> int | None:
        return self._first_row_index_matching(
            lambda index, row: row.surface in {"Aperture", "Image", "Standard"} and predicate(index, row)
        )

    def _auto_leg_geometry(self) -> dict[str, dict[str, object]]:
        geometry: dict[str, dict[str, object]] = {}
        for entry in self._auto_leg_entries():
            leg_id = str(entry.get("leg_id", "") or "").strip().lower()
            polyline = np.asarray(entry.get("polyline", []), dtype=float)
            if not leg_id or polyline.ndim != 2 or polyline.shape[0] < 2:
                continue
            leg = self._leg_geometry_from_points([point for point in polyline])
            if leg is not None:
                geometry[leg_id] = leg
        return geometry

    def _michelson_leg_geometry(self, projected) -> dict[str, dict[str, object]]:
        if not self._uses_michelson_leg_workflow() or not self.rows:
            return {}
        workflow = self._physical_leg_workflow()
        if workflow not in {"mach_zehnder", "michelson"}:
            return self._auto_leg_geometry()
        splitter_indices = self._first_beam_splitter_indices()
        splitter_index = splitter_indices[0] if splitter_indices else None
        if splitter_index is None:
            return {}
        hub = self._projected_center_for_row(projected, splitter_index)
        if hub is None:
            return {}

        def row_selector(row: SurfaceRow) -> str:
            return str(self._element_metadata(row).get("branch_selector", "") or "").strip().lower()

        def row_role(row: SurfaceRow) -> str:
            return str(self._element_metadata(row).get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)

        if workflow == "mach_zehnder":
            bs2_index = splitter_indices[1] if len(splitter_indices) >= 2 else None
            bs2 = self._projected_center_for_row(projected, bs2_index) if bs2_index is not None else None
            if bs2 is None:
                return {}
            transmit_mirror_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "transmit"
                    or "transmit" in str(getattr(row, "name", "") or "").lower()
                    or "transmit" in str(getattr(row, "element", "") or "").lower()
                )
            )
            reflect_mirror_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "reflect"
                    or "reflect" in str(getattr(row, "name", "") or "").lower()
                    or "reflect" in str(getattr(row, "element", "") or "").lower()
                )
            )
            cross_detector_index = self._first_detector_index_matching(
                lambda _index, row: (
                    "cross" in str(getattr(row, "name", "") or "").lower()
                    or (
                        row_role(row) == "Detector"
                        and row_selector(row) == "transmit"
                    )
                )
            )
            return_detector_index = self._first_detector_index_matching(
                lambda _index, row: (
                    "return" in str(getattr(row, "name", "") or "").lower()
                    or (
                        row_role(row) == "Detector"
                        and row_selector(row) == "reflect"
                    )
                )
            )
            target_points: dict[str, list[np.ndarray]] = {
                "input": [self._projected_center_for_row(projected, 0), hub],
                "transmit": [
                    hub,
                    self._projected_center_for_row(projected, transmit_mirror_index)
                    if transmit_mirror_index is not None
                    else None,
                    bs2,
                ],
                "reflect": [
                    hub,
                    self._projected_center_for_row(projected, reflect_mirror_index)
                    if reflect_mirror_index is not None
                    else None,
                    bs2,
                ],
                "cross": [
                    bs2,
                    self._projected_center_for_row(projected, cross_detector_index)
                    if cross_detector_index is not None
                    else None,
                ],
                "return": [
                    bs2,
                    self._projected_center_for_row(projected, return_detector_index)
                    if return_detector_index is not None
                    else None,
                ],
            }
            geometry: dict[str, dict[str, object]] = {}
            for leg_id, points in target_points.items():
                leg = self._leg_geometry_from_points([point for point in points if point is not None])
                if leg is not None:
                    geometry[leg_id] = leg
            return geometry

        detector_index = self._first_row_index_matching(
            lambda _index, row: row.surface == "Image" and row_role(row) == "Detector"
        )
        if detector_index is None:
            detector_index = self._first_row_index_matching(
                lambda _index, row: row_role(row) == "Detector"
            )
        if detector_index is None:
            detector_index = self._first_row_index_matching(
                lambda _index, row: row.surface == "Image" and self._row_has_detector_output_metadata(row)
            )

        target_indices: dict[str, int | None] = {
            "input": 0,
            "reflect": self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "reflect"
                    or "reflect" in str(getattr(row, "name", "") or "").lower()
                    or "reference" in str(getattr(row, "name", "") or "").lower()
                    or "reference" in str(getattr(row, "element", "") or "").lower()
                )
                and (row_role(row) in {"Reflect", "Return"} or row_selector(row) == "")
            ),
            "transmit": self._first_row_index_matching(
                lambda _index, row: row.surface == "Mirror"
                and (
                    row_selector(row) == "transmit"
                    or "transmit" in str(getattr(row, "name", "") or "").lower()
                    or "test optic" in str(getattr(row, "name", "") or "").lower()
                    or "test optic" in str(getattr(row, "element", "") or "").lower()
                )
                and (row_role(row) in {"Transmit", "Return"} or row_selector(row) == "")
            ),
            "detector": detector_index,
        }
        geometry: dict[str, dict[str, object]] = {}
        for leg_id, target_index in target_indices.items():
            if target_index is None:
                continue
            endpoint = self._projected_center_for_row(projected, target_index)
            if endpoint is None:
                continue
            leg = self._leg_geometry_from_points([hub, endpoint])
            if leg is not None:
                geometry[leg_id] = leg
        return geometry

    def _physical_ray_leg_segments(self, projected) -> tuple[dict[str, list[dict[str, object]]], np.ndarray] | None:
        if not self._uses_michelson_leg_workflow():
            return None
        rays = list(getattr(projected, "rays", []) or [])
        if not rays:
            return None
        geometry = self._michelson_leg_geometry(projected)
        if not geometry:
            return None

        finite_points: list[np.ndarray] = []
        for ray in rays:
            points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
            if points.ndim == 2 and points.shape[0] >= 2:
                finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
                if np.any(finite):
                    finite_points.append(points[finite])
        if not finite_points:
            return None
        all_points = np.vstack(finite_points)
        x_min, x_max = float(np.min(all_points[:, 0])), float(np.max(all_points[:, 0]))
        y_min, y_max = float(np.min(all_points[:, 1])), float(np.max(all_points[:, 1]))
        span_x = max(x_max - x_min, 1.0)
        span_y = max(y_max - y_min, 1.0)
        min_segment = max(0.25, 0.003 * min(span_x, span_y))
        raw_segments: list[dict[str, object]] = []
        for ray in rays:
            points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
            if not np.all(finite):
                original_indices = np.flatnonzero(finite)
                points = points[finite]
            else:
                original_indices = np.arange(points.shape[0], dtype=int)
            if points.shape[0] < 2:
                continue
            for index in range(points.shape[0] - 1):
                p0 = np.asarray(points[index], dtype=float)
                p1 = np.asarray(points[index + 1], dtype=float)
                length = float(np.linalg.norm(p1 - p0))
                if length <= min_segment:
                    continue
                raw_segments.append(
                    {
                        "ray": ray,
                        "p0": p0,
                        "p1": p1,
                        "start_index": int(original_indices[index]),
                        "end_index": int(original_indices[index + 1]),
                        "length": length,
                    }
                )
        if not raw_segments:
            return None

        groups: dict[str, list[dict[str, object]]] = {leg_id: [] for leg_id, _short, _detail in self._physical_leg_definitions()}
        for segment in raw_segments:
            p0 = np.asarray(segment["p0"], dtype=float)
            p1 = np.asarray(segment["p1"], dtype=float)
            tangent = p1 - p0
            tangent_norm = float(np.linalg.norm(tangent))
            if tangent_norm <= min_segment:
                continue
            tangent = tangent / tangent_norm
            midpoint = 0.5 * (p0 + p1)
            best: tuple[float, str] | None = None
            for leg_id, leg in geometry.items():
                for seg0, seg1 in list(leg.get("segments", []) or []):
                    seg0 = np.asarray(seg0, dtype=float)
                    seg1 = np.asarray(seg1, dtype=float)
                    axis = seg1 - seg0
                    length = float(np.linalg.norm(axis))
                    if length <= 1e-9:
                        continue
                    unit = axis / length
                    offset = midpoint - seg0
                    projection = float(np.dot(offset, unit))
                    t = projection / max(length, 1e-12)
                    if t < -0.10 or t > 1.12:
                        continue
                    alignment = abs(float(np.dot(tangent, unit)))
                    if alignment < 0.45:
                        continue
                    perpendicular = float(np.linalg.norm(offset - unit * projection))
                    tolerance = max(3.0, 0.24 * min(length, 90.0))
                    if perpendicular > tolerance:
                        continue
                    score = perpendicular / tolerance + 0.25 * (1.0 - alignment)
                    if best is None or score < best[0]:
                        best = (score, leg_id)
            if best is None:
                continue
            leg_id = best[1]
            segment_with_leg = dict(segment)
            segment_with_leg["leg_id"] = leg_id
            groups[leg_id].append(segment_with_leg)

        groups = {leg_id: segments for leg_id, segments in groups.items() if segments}
        if not groups:
            return None
        first_leg = next(iter(geometry.values()))
        return groups, np.asarray(first_leg["hub"], dtype=float)

    def _draw_physical_ray_segment_labels(self, projected) -> bool:
        geometry = self._michelson_leg_geometry(projected)
        if not geometry:
            return False
        definitions = self._physical_leg_definitions()
        workflow = self._physical_leg_workflow()
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        view_leg_id = self._leg_id_from_arm_key(self._current_arm_view_key())
        label_plan = physical_leg_label_plan(
            definitions=definitions,
            geometry=geometry,
            workflow=workflow,
            axis_limits=(x0, x1, y0, y1),
            view_leg_id=view_leg_id,
        )
        for item in label_plan:
            point = np.asarray(item["point"], dtype=float)
            text_point = np.asarray(item["text_point"], dtype=float)
            self.ax.annotate(
                str(item["label"]),
                xy=(float(point[0]), float(point[1])),
                xytext=(float(text_point[0]), float(text_point[1])),
                color="#334155",
                fontsize=7.8,
                ha="center",
                va="center",
                zorder=82.0,
                clip_on=True,
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": "#334155",
                    "linewidth": 0.85,
                    "alpha": 0.9,
                    "shrinkA": 3,
                    "shrinkB": 2,
                },
                bbox={
                    "facecolor": "white",
                    "edgecolor": "#334155",
                    "alpha": 0.86,
                    "boxstyle": "round,pad=0.22",
                    "linewidth": 0.75,
                },
            )
            self.ax.plot(
                [float(point[0])],
                [float(point[1])],
                marker="o",
                markersize=3.2,
                color="#111827",
                alpha=0.95,
                zorder=81.0,
            )
        return bool(label_plan)

    def _arm_ray_label_targets(self, projected, catalog: list[dict[str, str]], view_key: str = "") -> list[dict[str, object]]:
        return arm_ray_label_targets(
            projected,
            catalog,
            view_key,
            indices_for_arm_key=self._indices_for_arm_key,
            branch_path_for_arm_key=self._branch_path_for_arm_key,
            ray_matches_arm_key=self._ray_matches_arm_key,
            branch_path_selector_sequence=self._branch_path_selector_sequence,
        )

    def _draw_arm_ray_labels(
        self,
        projected,
        catalog: list[dict[str, str]],
        view_key: str,
        palette: tuple[str, ...],
    ) -> set[str]:
        targets = self._arm_ray_label_targets(projected, catalog, view_key)
        if not targets:
            return set()
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        labeled: set[str] = set()
        for item in arm_ray_label_plan(targets, axis_limits=(x0, x1, y0, y1), palette=palette):
            point = np.asarray(item["point"], dtype=float)
            text_point = np.asarray(item["text_point"], dtype=float)
            color = str(item["color"])
            self.ax.annotate(
                str(item["label"]),
                xy=(float(point[0]), float(point[1])),
                xytext=(float(text_point[0]), float(text_point[1])),
                color=color,
                fontsize=8,
                ha="center",
                va="center",
                zorder=82.0,
                clip_on=True,
                arrowprops={
                    "arrowstyle": "-|>",
                    "color": color,
                    "linewidth": 0.9,
                    "alpha": 0.9,
                    "shrinkA": 3,
                    "shrinkB": 2,
                },
                bbox={
                    "facecolor": "white",
                    "edgecolor": color,
                    "alpha": 0.86,
                    "boxstyle": "round,pad=0.25",
                    "linewidth": 0.8,
                },
            )
            for key in list(item.get("entry_keys", []) or []):
                labeled.add(str(key))
            self.ax.plot(
                [float(point[0])],
                [float(point[1])],
                marker="o",
                markersize=3.2,
                color=str(item.get("marker_color", color) or color),
                alpha=0.95,
                zorder=81.0,
            )
        return labeled

    def _common_arm_surface_indices(self) -> set[int]:
        indices = {0} if self.rows else set()
        if not self.rows:
            return indices
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            role = self._element_arm_role_for_index(self.rows, start)
            if role == "Common":
                indices.update(range(start, end + 1))
            index = max(end + 1, index + 1)
        return indices

    def _context_surface_indices_for_arm_key(self, arm_key: str) -> set[int]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id:
            return self._common_arm_surface_indices()
        indices = {0} if self.rows else set()
        auto_entry = self._auto_leg_entry_for_id(leg_id)
        if auto_entry is not None:
            return indices | {
                int(index)
                for index in set(auto_entry.get("context_indices", set()) or set())
                if 0 <= int(index) < len(self.rows)
            }
        if self._physical_leg_workflow() != "mach_zehnder":
            return indices | self._common_arm_surface_indices()
        splitters = self._first_beam_splitter_indices()
        bs1 = splitters[0] if len(splitters) >= 1 else None
        bs2 = splitters[1] if len(splitters) >= 2 else None
        if leg_id in {"input", "transmit", "reflect"} and bs1 is not None:
            indices.add(bs1)
        if leg_id in {"transmit", "reflect", "cross", "return"} and bs2 is not None:
            indices.add(bs2)
        return indices

    def _default_parent_splitter_id(self) -> str:
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            metadata = self._element_metadata(row)
            return (
                str(metadata.get("element_id", "") or "").strip()
                or self._element_key(row)
                or str(row.name or f"S{index}").strip()
            )
        return ""

    def _splitter_id_by_ordinal(self, ordinal: int) -> str:
        target = int(ordinal)
        seen = 0
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            if seen != target:
                seen += 1
                continue
            metadata = self._element_metadata(row)
            return (
                str(metadata.get("element_id", "") or "").strip()
                or self._element_key(row)
                or str(row.name or f"S{index}").strip()
            )
        return self._default_parent_splitter_id()

    def _branch_selector_for_arm_key(self, arm_key: str) -> str:
        path = self._branch_path_for_arm_key(arm_key)
        if path:
            return self._branch_path_leaf_selector(path)
        leg_id = self._leg_id_from_arm_key(arm_key)
        if leg_id:
            workflow = self._physical_leg_workflow()
            if workflow == "mach_zehnder":
                return {
                    "input": "primary",
                    "transmit": "transmit",
                    "reflect": "reflect",
                    "cross": "transmit",
                    "return": "reflect",
                }.get(leg_id, "")
            if leg_id == "input":
                return "primary"
            if leg_id in {"reflect", "transmit"}:
                return leg_id
            if leg_id == "detector":
                return "reflect"
        parts = str(arm_key or "").split("|")
        if len(parts) >= 3 and parts[0] == "branch":
            selector = parts[2].strip().lower()
            if selector in {"transmit", "reflect", "primary", "return"}:
                return selector
        return ""

    def _ray_matches_arm_key(self, ray, arm_key: str) -> bool:
        key = str(arm_key or "").strip()
        if not key:
            return False
        if self._leg_id_from_arm_key(key):
            return False
        branch_path = str(getattr(ray, "branch_path", "") or "").strip()
        target_path = self._branch_path_for_arm_key(key)
        if target_path:
            return branch_path == target_path
        if branch_path and self._metadata_arm_key_matches_branch_path(key, branch_path):
            return True
        selector = self._branch_selector_for_arm_key(key)
        branch_label = str(getattr(ray, "branch_label", "") or "").strip().lower()
        return bool(selector and branch_label == selector)

    def _apply_arm_key_metadata_to_row(self, row: SurfaceRow, arm_key: str) -> None:
        label = self._next_manual_element_label()
        metadata = self._element_metadata_for_arm_key(arm_key, label)
        if metadata is None:
            return
        row.element = label
        self._set_element_metadata(row, metadata)

    def _projected_rays_for_leg_view(self, projected: ProjectedScene2D, arm_key: str) -> list[ProjectedRay2D]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id:
            return []
        segment_data = self._physical_ray_leg_segments(projected)
        if segment_data is None:
            return []
        groups, _hub = segment_data
        rays: list[ProjectedRay2D] = []
        for segment_index, segment in enumerate(groups.get(leg_id, []) or []):
            ray = segment.get("ray")
            if ray is None:
                continue
            p0 = np.asarray(segment.get("p0"), dtype=float)
            p1 = np.asarray(segment.get("p1"), dtype=float)
            if p0.shape[0] < 2 or p1.shape[0] < 2:
                continue
            segment_points = np.vstack([p0[:2], p1[:2]])
            segment_events = projected_ray_events_for_segment(
                ray,
                int(segment.get("start_index", 0)),
                int(segment.get("end_index", 1)),
                segment_points,
            )
            segment_surface_ids = [
                int(getattr(event, "surface_id"))
                for event in segment_events
                if str(getattr(event, "event_kind", "") or "") == "surface"
                and getattr(event, "surface_id", None) is not None
            ]
            segment_terminal_surface_ids = [
                int(getattr(event, "surface_id"))
                for event in segment_events
                if str(getattr(event, "event_kind", "") or "") == "terminal"
                and getattr(event, "surface_id", None) is not None
            ]
            rays.append(
                ProjectedRay2D(
                    ray_index=int(getattr(ray, "ray_index", segment_index)),
                    field_index=int(getattr(ray, "field_index", 0)),
                    color=str(getattr(ray, "color", "#39FF14") or "#39FF14"),
                    points_2d=segment_points,
                    reaches_image=bool(getattr(ray, "reaches_image", False)),
                    terminal_status=str(getattr(ray, "terminal_status", "") or ""),
                    surface_ids=np.asarray(segment_surface_ids, dtype=int),
                    branch_label=str(getattr(ray, "branch_label", "") or ""),
                    branch_path=str(getattr(ray, "branch_path", "") or ""),
                    source_id=str(getattr(ray, "source_id", "") or ""),
                    source_name=str(getattr(ray, "source_name", "") or ""),
                    terminal_surface_ids=np.asarray(segment_terminal_surface_ids, dtype=int),
                    events_2d=segment_events,
                )
            )
        return rays

    def _filter_projected_scene_for_arm_view(self, projected: ProjectedScene2D) -> ProjectedScene2D:
        arm_key = self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))
        if not arm_key:
            return projected
        arm_indices = set(self._indices_for_arm_key(arm_key))
        allowed_indices = self._context_surface_indices_for_arm_key(arm_key) | self._surface_indices_for_arm_key(arm_key)

        curves = [
            curve
            for curve in projected.curves
            if int(curve.row_index) in allowed_indices
        ]
        pick_regions = [
            region
            for region in projected.pick_regions
            if int(region.row_index) in allowed_indices
        ]
        rays = self._projected_rays_for_leg_view(projected, arm_key)
        if not rays:
            for ray in projected.rays:
                surface_ids = set(np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel().tolist())
                if self._ray_matches_arm_key(ray, arm_key):
                    rays.append(ray)
                elif arm_indices and surface_ids & arm_indices:
                    rays.append(ray)
        visible_source_ids = {
            str(getattr(ray, "source_id", "") or "").strip()
            for ray in rays
            if str(getattr(ray, "source_id", "") or "").strip()
        }
        terminal_indices = projected_ray_terminal_surface_ids(rays)
        labels = filter_projected_labels_for_rows_and_sources(projected.labels, allowed_indices, visible_source_ids, terminal_indices)

        bound_points: list[np.ndarray] = []
        for curve in curves:
            points = np.asarray(curve.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        for ray in rays:
            points = np.asarray(ray.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        bounds = BoundsRect.from_points(bound_points)
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(projected.planes),
            labels=labels,
            pick_regions=pick_regions,
            bounds=bounds,
        )

    @staticmethod
    def _projected_ray_is_direct_source_path(ray) -> bool:
        branch_path = str(getattr(ray, "branch_path", "") or "").strip().lower()
        branch_label = str(getattr(ray, "branch_label", "") or "").strip().lower()
        return branch_path in {"", "primary"} and branch_label in {"", "primary"}

    @staticmethod
    def _representative_projected_rays_by_branch(rays: list[ProjectedRay2D]) -> list[ProjectedRay2D]:
        return representative_projected_rays_by_branch(rays)

    def _filter_projected_scene_for_ray_display(self, projected: ProjectedScene2D) -> ProjectedScene2D:
        mode = self._current_ray_display_mode()
        hide_stopped = not bool(self.show_clipped_rays_var.get())
        explicit_terminal_modes = {
            RAY_DISPLAY_MISSED_DETECTOR: "missed_detector",
            RAY_DISPLAY_ABSORBED: "absorbed",
            RAY_DISPLAY_ESCAPED: "escaped",
            RAY_DISPLAY_STOPPED: "stopped",
        }
        rays = []
        for ray in list(getattr(projected, "rays", []) or []):
            terminal_status = projected_ray_terminal_status(ray)
            if mode in explicit_terminal_modes:
                if terminal_status != explicit_terminal_modes[mode]:
                    continue
            elif hide_stopped and not projected_ray_hits_detector(ray):
                continue
            elif mode == RAY_DISPLAY_DETECTOR and not projected_ray_hits_detector(ray):
                continue
            elif mode == RAY_DISPLAY_SPLITTER and self._projected_ray_is_direct_source_path(ray):
                continue
            rays.append(ray)
        if mode == RAY_DISPLAY_SPLITTER:
            rays = self._representative_projected_rays_by_branch(rays)
        if mode == RAY_DISPLAY_ALL and not hide_stopped:
            return projected
        visible_source_ids = {
            str(getattr(ray, "source_id", "") or "").strip()
            for ray in rays
            if str(getattr(ray, "source_id", "") or "").strip()
        }
        visible_terminal_indices = projected_ray_terminal_surface_ids(rays)
        all_terminal_indices = projected_ray_terminal_surface_ids(getattr(projected, "rays", []) or [])
        labels = filter_projected_labels_for_visible_ray_set(
            projected.labels,
            visible_source_ids,
            visible_terminal_indices,
            all_terminal_indices,
        )

        bound_points: list[np.ndarray] = []
        for curve in projected.curves:
            points = np.asarray(curve.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        for ray in rays:
            points = np.asarray(ray.points_2d, dtype=float)
            if points.ndim == 2 and points.shape[0]:
                bound_points.append(points)
        bounds = BoundsRect.from_points(bound_points)
        return ProjectedScene2D(
            curves=list(projected.curves),
            rays=rays,
            planes=list(projected.planes),
            labels=labels,
            pick_regions=list(projected.pick_regions),
            bounds=bounds,
        )

    def _draw_cardinal_extent_marker(
        self,
        p0: np.ndarray,
        p1: np.ndarray,
        color: str,
        *,
        cap_half: float,
    ) -> list:
        tangent = np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)
        norm = np.linalg.norm(tangent)
        if norm <= 1e-12:
            return []
        tangent /= norm
        normal = np.array([-tangent[1], tangent[0]], dtype=float)
        normal /= max(np.linalg.norm(normal), 1e-12)
        artists = [
            self.ax.plot(
                [float(p0[0]), float(p1[0])],
                [float(p0[1]), float(p1[1])],
                color=color,
                linewidth=1.35,
                linestyle="-",
                alpha=0.95,
                zorder=70.0,
            )[0]
        ]
        for point in (np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)):
            c0 = point - normal * cap_half
            c1 = point + normal * cap_half
            artists.append(
                self.ax.plot(
                    [float(c0[0]), float(c1[0])],
                    [float(c0[1]), float(c1[1])],
                    color=color,
                    linewidth=1.1,
                    linestyle="-",
                    alpha=0.95,
                    zorder=70.0,
                )[0]
            )
        return artists

    def _folded_path_plane_at_distance(self, path_distance: float) -> tuple[np.ndarray, np.ndarray] | None:
        try:
            point, direction, _max_half, _extent_points, elements = self._compute_folded_layout_geometry()
        except Exception:
            return None
        if not elements:
            return None
        vertices: list[tuple[float, np.ndarray]] = [(0.0, np.asarray(point, dtype=float).copy())]
        distance = 0.0
        for row_index, element in enumerate(elements, start=1):
            center = np.asarray(element[1], dtype=float)
            distance += max(float(self.rows[row_index - 1].thickness), 0.0)
            vertices.append((float(distance), center.copy()))
        return folded_path_plane_at_distance(path_distance, vertices, direction)

    def _draw_folded_optics_markers(self, optics_info: dict) -> bool:
        marker_specs = [
            ("Front PP", optics_info.get("h1_z"), None, "#ff9f1c"),
            ("Back PP", optics_info.get("h2_z"), None, "#ff9f1c"),
            ("EP", optics_info.get("ep_z"), optics_info.get("ep_radius"), "#00bcd4"),
            ("XP", optics_info.get("xp_z"), optics_info.get("xp_radius"), "#e91e63"),
        ]
        drawn = 0
        x0, x1 = self.ax.get_xlim()
        y0, y1 = self.ax.get_ylim()
        plans = folded_optics_marker_plan(
            marker_specs,
            axis_limits=(x0, x1, y0, y1),
            path_plane_at_distance=self._folded_path_plane_at_distance,
        )
        for item in plans:
            p0 = np.asarray(item["p0"], dtype=float)
            p1 = np.asarray(item["p1"], dtype=float)
            color = str(item["color"])
            if bool(item["use_extent"]):
                artists = self._draw_cardinal_extent_marker(
                    p0,
                    p1,
                    color,
                    cap_half=float(item["cap_half"]),
                )
            else:
                artists = [
                    self.ax.plot(
                        [p0[0], p1[0]],
                        [p0[1], p1[1]],
                        color=color,
                        linewidth=1.15,
                        linestyle=":",
                        alpha=0.95,
                        zorder=70.0,
                    )[0]
                ]
            label_pos = np.asarray(item["label_pos"], dtype=float)
            text = self.ax.text(
                float(label_pos[0]),
                float(label_pos[1]),
                str(item["label"]),
                color=color,
                fontsize=8,
                ha="center",
                va="bottom",
                zorder=71.0,
                bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.65, "pad": 0.6},
            )
            self._cardinal_marker_artists.extend((*artists, text))
            drawn += 1
        return drawn > 0
