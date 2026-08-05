"""Project a SceneBundle into 2-D display coordinates.

This module knows about numpy but has no dependency on matplotlib, VTK,
or tkinter.
"""

from __future__ import annotations

import numpy as np

from .scene_geometry import (
    BoundsRect,
    LabelSpec,
    PlaneMarker,
    PickRegion,
    ProjectedCurve2D,
    ProjectedRayEvent2D,
    ProjectedRay2D,
    ProjectedScene2D,
    SceneBundle,
    StyleHint,
    ray_path_reaches_image_from_events,
    ray_path_terminal_event,
    ray_path_terminal_metadata,
    ray_path_terminal_status_from_events,
    ray_paths_have_diffuse_scatter,
    scene_target_active_dimensions,
    scene_target_active_footprint_polylines,
    scene_target_detector_miss_crosshair_polylines,
)


PROJECTION_PLANES = ("YZ", "XZ", "XY")


def normalize_projection_plane(orientation: str) -> str:
    value = str(orientation or "Vertical").strip()
    if value in PROJECTION_PLANES:
        return value
    return "YZ"


def auxiliary_projection_planes(orientation: str) -> tuple[str, str]:
    selected = normalize_projection_plane(orientation)
    return tuple(plane for plane in PROJECTION_PLANES if plane != selected)


def projection_axis_labels(orientation: str) -> tuple[str, str, str]:
    value = str(orientation or "Vertical").strip()
    if value == "Horizontal":
        return "Y [mm]", "-Z [mm]", "YZ"
    plane = normalize_projection_plane(value)
    if plane == "XZ":
        return "Z [mm]", "X [mm]", "XZ"
    if plane == "XY":
        return "X [mm]", "Y [mm]", "XY"
    return "Z [mm]", "Y [mm]", "YZ"


def _target_is_scatter_branch_detector(target) -> bool:
    """True for a branch detector synthesised on a diffuse-scatter leaf.

    bugs/0182: such detectors are kept as is_detector targets so they still feed
    detector_planes_for_hard_stop (bounding the otherwise-escaping scatter rays in
    3-D), but their orange footprint / crosshair must NOT draw -- dozens of them
    plastered the 2-D 'full 3-D' projection with crisscrossing rectangles.
    """
    metadata = getattr(target, "metadata", None) or {}
    if metadata.get("target_source") != "branch_detector":
        return False
    from KrakenOS.UI.services.branch_detectors import _branch_path_has_scatter

    return _branch_path_has_scatter(metadata.get("branch_path", ""))


def _target_branch_detector_draw_suppressed(target, scene_has_diffuse_scatter: bool = False) -> bool:
    """True for a branch detector whose 2-D footprint/crosshair must NOT draw.

    Covers the bugs/0182 diffuse-scatter leaves and the bugs/0183 beam-splitter
    internal multi-bounce ghosts (per-path), PLUS bugs/0184: when the whole scene is
    a diffuse double-pass (``scene_has_diffuse_scatter``) EVERY branch detector is
    noise -- including a clean single-pass leak like ``S1:S1/transmit`` that carries
    neither a scatter token nor an internal-bounce signature -- so its draw is gated
    too. In all cases the detector target is kept (it still feeds
    detector_planes_for_hard_stop and bounds the rays in 3-D); only the DRAW is gated
    so the 2-D 'full 3-D' projection does not fill with orange clutter.
    """
    metadata = getattr(target, "metadata", None) or {}
    if metadata.get("target_source") != "branch_detector":
        return False
    # bugs/0285: build_scene_bundle stamps ``draw_suppressed`` on any branch detector whose
    # draw is gated (scatter / internal bounce / whole-scene scatter / illumination flood),
    # computed where the full scene context is known. Honour it as the authoritative signal.
    if metadata.get("draw_suppressed"):
        return True
    if scene_has_diffuse_scatter:
        return True
    from KrakenOS.UI.services.branch_detectors import _branch_path_draw_suppressed

    return _branch_path_draw_suppressed(metadata.get("branch_path", ""))


class SceneProjector2D:
    """Project a :class:`SceneBundle` into a :class:`ProjectedScene2D`."""

    def __init__(self, orientation: str = "Vertical") -> None:
        self.orientation = str(orientation or "Vertical")
        self.plane = normalize_projection_plane(self.orientation)

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def project_bundle(self, bundle: SceneBundle) -> ProjectedScene2D:
        """Project all geometry in *bundle* to 2-D display coordinates."""
        curves = self._project_curves(bundle)
        curves.extend(self._project_mesh_outlines(bundle))
        if not _bundle_uses_folded_display_projection(bundle, self.plane):
            curves.extend(self._project_detector_footprints(bundle))
            curves.extend(self._project_detector_miss_crosshairs(bundle))
        rays = self._project_rays(bundle)
        bounds = self._compute_bounds(curves, rays)
        pick_regions = _pick_regions_from_curves(curves)
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(bundle.planes),
            labels=self._project_labels(bundle),
            pick_regions=pick_regions,
            bounds=bounds,
        )

    def project_point(self, z: float, y: float) -> tuple[float, float]:
        if self.orientation == "Horizontal":
            return -y, -z
        return z, y

    def project_points(self, z: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        z_arr = np.asarray(z, dtype=float)
        y_arr = np.asarray(y, dtype=float)
        if self.orientation == "Horizontal":
            return -y_arr, -z_arr
        return z_arr, y_arr

    def project_xyz_points(self, points: np.ndarray) -> np.ndarray:
        pts = np.asarray(points, dtype=float)
        if pts.ndim != 2 or pts.shape[1] < 3:
            return np.empty((0, 2), dtype=float)
        x_vals = pts[:, 0]
        y_vals = pts[:, 1]
        z_vals = pts[:, 2]
        if self.orientation == "Horizontal":
            return np.column_stack((-y_vals, -z_vals))
        if self.plane == "XZ":
            return np.column_stack((z_vals, x_vals))
        if self.plane == "XY":
            return np.column_stack((x_vals, y_vals))
        return np.column_stack((z_vals, y_vals))

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _project_curves(self, bundle: SceneBundle) -> list[ProjectedCurve2D]:
        projected: list[ProjectedCurve2D] = []
        for curve in bundle.surface_curves:
            pts = np.asarray(curve.points_world, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            coordinate_space = str(getattr(curve, "coordinate_space", "world") or "world")
            if coordinate_space == "folded_yz_display":
                if self.plane != "YZ":
                    continue
                points_2d = pts[:, :2]
            elif pts.shape[1] >= 3:
                points_2d = self.project_xyz_points(pts)
            elif self.plane == "YZ":
                # Legacy display-only curves are already in YZ display
                # coordinates.  New scene geometry should arrive as (N, 3).
                points_2d = pts[:, :2]
            elif self.plane == "XZ":
                # Most table-driven reference curves still arrive as axial
                # (Z, transverse) cross-sections.  Reuse that section for XZ
                # until each surface curve carries native 3-D coordinates.
                points_2d = pts[:, :2]
            elif self.plane == "XY":
                # Without a native 3-D curve, draw its transverse footprint at
                # X=0.  Traced rays and mesh outlines remain true 3-D
                # projections in this view.
                points_2d = np.column_stack((np.zeros(pts.shape[0], dtype=float), pts[:, 1]))
            else:
                continue
            projected.append(ProjectedCurve2D(
                row_index=curve.row_index,
                kind=curve.kind,
                points_2d=np.asarray(points_2d, dtype=float),
                style=curve.style,
                coordinate_space=coordinate_space,
            ))
        return projected

    def _project_labels(self, bundle: SceneBundle) -> list[LabelSpec]:
        projected: list[LabelSpec] = []
        for label in list(getattr(bundle, "labels", []) or []):
            coordinate_space = str(getattr(label, "coordinate_space", "yz_display") or "yz_display")
            if coordinate_space == "world":
                point_world = np.asarray(getattr(label, "point_world", np.full(3, np.nan)), dtype=float).reshape(-1)
                if point_world.size < 3 or not np.all(np.isfinite(point_world[:3])):
                    continue
                point_2d = self.project_xyz_points(point_world[:3].reshape(1, 3))
                if point_2d.shape != (1, 2):
                    continue
                offset = np.asarray(getattr(label, "offset_2d", np.zeros(2)), dtype=float).reshape(-1)
                if offset.size < 2 or not np.all(np.isfinite(offset[:2])):
                    offset = np.zeros(2, dtype=float)
                x_value = float(point_2d[0, 0] + offset[0])
                y_value = float(point_2d[0, 1] + offset[1])
                projected.append(LabelSpec(
                    text=str(getattr(label, "text", "") or ""),
                    x=x_value,
                    y=y_value,
                    row_index=getattr(label, "row_index", None),
                    fontsize=float(getattr(label, "fontsize", 9.0) or 9.0),
                    color=str(getattr(label, "color", "#202020") or "#202020"),
                    ha=str(getattr(label, "ha", "center") or "center"),
                    va=str(getattr(label, "va", "bottom") or "bottom"),
                    point_world=np.asarray(point_world[:3], dtype=float),
                    offset_2d=np.asarray(offset[:2], dtype=float),
                    coordinate_space="world",
                    source_id=str(getattr(label, "source_id", "") or ""),
                ))
                continue
            if self.plane != "YZ":
                continue
            projected.append(label)
        return projected

    def _project_mesh_outlines(self, bundle: SceneBundle) -> list[ProjectedCurve2D]:
        if self.plane == "YZ":
            return []
        projected: list[ProjectedCurve2D] = []
        for mesh_item in list(getattr(bundle, "surface_meshes", []) or []):
            mesh = getattr(mesh_item, "mesh", None)
            points = getattr(mesh, "points", None)
            if points is None:
                continue
            pts2 = self.project_xyz_points(np.asarray(points, dtype=float))
            hull = _convex_hull_2d(pts2)
            if hull.shape[0] < 3:
                continue
            closed = np.vstack((hull, hull[0]))
            style = StyleHint(color="#8b95a5", linewidth=1.2, alpha=0.78, zorder=32.0)
            projected.append(ProjectedCurve2D(
                row_index=int(getattr(mesh_item, "row_index", -1)),
                kind=f"{getattr(mesh_item, 'kind', 'mesh')}_outline",
                points_2d=closed,
                style=style,
                coordinate_space="world",
            ))
        return projected

    def _project_detector_footprints(self, bundle: SceneBundle) -> list[ProjectedCurve2D]:
        projected: list[ProjectedCurve2D] = []
        scene_scatter = ray_paths_have_diffuse_scatter(getattr(bundle, "ray_paths", []))
        for target in list(getattr(bundle, "targets", []) or []):
            if _target_branch_detector_draw_suppressed(target, scene_scatter):
                continue
            polylines = scene_target_active_footprint_polylines(target)
            if not polylines:
                continue
            try:
                row_index = int(getattr(target, "row_index", -1))
            except Exception:
                row_index = -1
            for index, points_world in enumerate(polylines):
                pts2 = self.project_xyz_points(np.asarray(points_world, dtype=float))
                if pts2.shape[0] < 2:
                    continue
                projected.append(
                    ProjectedCurve2D(
                        row_index=row_index,
                        kind="detector_active_footprint" if index == 0 else "detector_active_center",
                        points_2d=pts2,
                        style=StyleHint(
                            color="#f97316",
                            linewidth=1.7 if index == 0 else 1.0,
                            alpha=0.92 if index == 0 else 0.72,
                            zorder=72.0,
                            linestyle="-" if index == 0 else ":",
                        ),
                        coordinate_space="world",
                    )
                )
        return projected

    def _project_detector_miss_crosshairs(self, bundle: SceneBundle) -> list[ProjectedCurve2D]:
        scene_scatter = ray_paths_have_diffuse_scatter(getattr(bundle, "ray_paths", []))
        targets_by_surface = {
            int(getattr(target, "trace_surface")): target
            for target in list(getattr(bundle, "targets", []) or [])
            if getattr(target, "trace_surface", None) is not None
            and not _target_branch_detector_draw_suppressed(target, scene_scatter)
        }
        projected: list[ProjectedCurve2D] = []
        for path in list(getattr(bundle, "ray_paths", []) or []):
            metadata = ray_path_terminal_metadata(path)
            surface = metadata.get("detector_miss_surface")
            event = ray_path_terminal_event(path)
            if surface in (None, "") and event is not None:
                surface = getattr(event, "surface_id", None)
            try:
                target = targets_by_surface.get(int(surface))
            except Exception:
                target = None
            if target is None:
                continue
            for points_world in scene_target_detector_miss_crosshair_polylines(path, target):
                pts2 = self.project_xyz_points(np.asarray(points_world, dtype=float))
                if pts2.shape[0] < 2:
                    continue
                projected.append(
                    ProjectedCurve2D(
                        row_index=int(getattr(target, "row_index", -1)),
                        kind="detector_miss_crosshair",
                        points_2d=pts2,
                        style=StyleHint(
                            color="#ea580c",
                            linewidth=1.45,
                            alpha=0.98,
                            zorder=88.0,
                            linestyle="-",
                        ),
                        coordinate_space="world",
                    )
                )
        return projected

    def _project_rays(self, bundle: SceneBundle) -> list[ProjectedRay2D]:
        projected: list[ProjectedRay2D] = []
        folded_display = None
        if not _bundle_uses_native_nonsequential_projection(bundle):
            folded_display = bundle.extra.get("folded_ray_display_paths")
        scene_center, scene_radius = scene_display_center_radius(bundle)
        targets_by_surface = _targets_by_trace_surface(bundle)
        detector_planes = detector_planes_for_hard_stop(bundle, scene_radius)
        scene_has_diffuse_scatter = ray_paths_have_diffuse_scatter(bundle.ray_paths)
        for path in bundle.ray_paths:
            folded_pts = None
            if folded_display is not None and path.ray_index < len(folded_display):
                candidate = np.asarray(folded_display[path.ray_index], dtype=float)
                if candidate.ndim == 2 and candidate.shape[0] >= 2:
                    folded_pts = candidate
            if folded_pts is not None and self.plane == "YZ":
                display_points = folded_pts
                draw_behind_surfaces = True
            else:
                pts = np.asarray(path.points_world, dtype=float)
                if pts.ndim != 2 or pts.shape[0] < 2:
                    continue
                terminal_status = ray_path_terminal_status_from_events(path)
                terminal_target = _missed_detector_target_for_path(path, targets_by_surface)
                pts, _was_capped = bounded_ray_points_for_scene_display(
                    pts,
                    scene_center,
                    scene_radius,
                    terminal_status=terminal_status,
                    terminal_target=terminal_target,
                    terminal_direction=_terminal_display_direction_from_path(path),
                    detector_planes=detector_planes,
                    branch_path=str(getattr(path, "branch_path", "") or ""),
                    scene_has_diffuse_scatter=scene_has_diffuse_scatter,
                )
                if pts.shape[0] < 2:
                    continue
                display_points = self.project_xyz_points(pts)
                # Two-arm display-fold rays ARE a fold (like folded_ray_display_paths) -- draw
                # them BEHIND the surfaces (zorder ~18-22) so the optical elements stay visible,
                # instead of on top (~42-52) where the dense beam hides the lenses.
                draw_behind_surfaces = str(getattr(path, "branch_path", "") or "").startswith("twoarm/")
            events_2d = self._project_ray_events(path, np.asarray(display_points, dtype=float))
            projected.append(ProjectedRay2D(
                ray_index=path.ray_index,
                field_index=path.field_index,
                color=path.color,
                points_2d=np.asarray(display_points, dtype=float),
                draw_behind_surfaces=draw_behind_surfaces,
                reaches_image=ray_path_reaches_image_from_events(path),
                terminal_status=ray_path_terminal_status_from_events(path),
                surface_ids=np.asarray(path.surface_ids, dtype=int),
                branch_label=str(path.branch_label or ""),
                branch_path=str(path.branch_path or path.branch_label or ""),
                source_id=str(getattr(path, "source_id", "") or ""),
                source_name=str(getattr(path, "source_name", "") or ""),
                terminal_surface_ids=_terminal_surface_ids_from_projected_events(events_2d),
                events_2d=events_2d,
            ))
        return projected

    def _project_ray_events(self, path: object, display_points: np.ndarray) -> list[ProjectedRayEvent2D]:
        events = list(getattr(path, "events", []) or [])
        if not events:
            return []
        pts = np.asarray(display_points, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 2:
            return []
        surface_ordinal = 0
        terminal_status = ray_path_terminal_status_from_events(path)
        projected: list[ProjectedRayEvent2D] = []
        for event in events:
            event_kind = str(getattr(event, "event_kind", "") or "")
            if event_kind == "surface":
                point_index = min(max(surface_ordinal + 1, 0), pts.shape[0] - 1)
                surface_ordinal += 1
            elif event_kind == "terminal":
                point_index = pts.shape[0] - 1
            else:
                continue
            point_2d = np.asarray(pts[point_index, :2], dtype=float)
            if not np.all(np.isfinite(point_2d)):
                point_world = np.asarray(getattr(event, "point_world", np.full(3, np.nan)), dtype=float).reshape(-1)
                if point_world.size >= 3:
                    fallback = self.project_xyz_points(point_world[:3].reshape(1, 3))
                    if fallback.shape == (1, 2):
                        point_2d = fallback[0]
            surface_id = getattr(event, "surface_id", None)
            projected.append(ProjectedRayEvent2D(
                event_id=str(getattr(event, "event_id", "") or ""),
                event_kind=event_kind,
                event_type=str(getattr(event, "event_type", "") or ""),
                step=int(getattr(event, "step", 0) or 0),
                surface_id=None if surface_id is None else int(surface_id),
                mesh_face_id=str(getattr(event, "mesh_face_id", "") or ""),
                surface_name=str(getattr(event, "surface_name", "") or ""),
                interaction_model=str(getattr(event, "interaction_model", "") or ""),
                point_index=int(point_index),
                point_2d=np.asarray(point_2d, dtype=float),
                terminal_status=terminal_status if event_kind == "terminal" else "",
            ))
        return projected

    @staticmethod
    def _compute_bounds(
        curves: list[ProjectedCurve2D],
        rays: list[ProjectedRay2D],
    ) -> BoundsRect:
        all_points: list[np.ndarray] = []
        for c in curves:
            if c.points_2d.shape[0] >= 2:
                all_points.append(c.points_2d)
        for r in rays:
            if r.points_2d.shape[0] >= 2:
                all_points.append(r.points_2d)
        return BoundsRect.from_points(all_points)


def _bundle_uses_native_nonsequential_projection(bundle: SceneBundle) -> bool:
    extra = dict(getattr(bundle, "extra", {}) or {})
    mode_text = " ".join(
        str(extra.get(key, "") or "").strip().lower()
        for key in ("trace_mode_requested", "trace_mode_active", "trace_mode_note")
    )
    if "non-sequential" in mode_text or "nonseq" in mode_text:
        return True
    if list(getattr(bundle, "optical_volumes", []) or []):
        return True
    if list(getattr(bundle, "boundary_faces", []) or []):
        return True
    return False


def _bundle_uses_folded_display_projection(bundle: SceneBundle, plane: str) -> bool:
    if normalize_projection_plane(plane) != "YZ":
        return False
    if _bundle_uses_native_nonsequential_projection(bundle):
        return False
    extra = dict(getattr(bundle, "extra", {}) or {})
    folded_paths = list(extra.get("folded_ray_display_paths") or [])
    if not folded_paths:
        return False
    mode_text = " ".join(
        str(extra.get(key, "") or "").strip().lower()
        for key in ("trace_mode_requested", "trace_mode_active", "trace_mode_note")
    )
    return "folded" in mode_text


def _terminal_display_direction_from_path(path: object) -> np.ndarray | None:
    event = ray_path_terminal_event(path)
    if event is not None:
        for attribute in ("outgoing_direction", "incoming_direction"):
            direction = _unit_vector_or_none(getattr(event, attribute, None))
            if direction is not None:
                return direction
    try:
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
    except Exception:
        return None
    if points.ndim == 2 and points.shape[0] >= 2 and points.shape[1] >= 3:
        return _unit_vector_or_none(points[-1, :3] - points[-2, :3])
    return None


def _unit_vector_or_none(value: object) -> np.ndarray | None:
    try:
        vector = np.asarray(value, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return None
    norm = float(np.linalg.norm(vector[:3]))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return None
    return vector[:3] / norm


def scene_display_center_radius(bundle: SceneBundle) -> tuple[np.ndarray, float]:
    """Return the scene envelope used by both 2-D and 3-D ray display capping."""
    points: list[np.ndarray] = []
    for mesh_item in list(getattr(bundle, "surface_meshes", []) or []):
        mesh = getattr(mesh_item, "mesh", None)
        mesh_points = getattr(mesh, "points", None)
        if mesh_points is None:
            continue
        pts = np.asarray(mesh_points, dtype=float)
        if pts.ndim == 2 and pts.shape[0] and pts.shape[1] >= 3:
            finite = np.all(np.isfinite(pts[:, :3]), axis=1)
            if np.any(finite):
                points.append(pts[finite, :3])
    for curve in list(getattr(bundle, "surface_curves", []) or []):
        pts = np.asarray(getattr(curve, "points_world", []), dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 1:
            continue
        if pts.shape[1] >= 3:
            finite = np.all(np.isfinite(pts[:, :3]), axis=1)
            if np.any(finite):
                points.append(pts[finite, :3])
        elif pts.shape[1] >= 2:
            finite = np.all(np.isfinite(pts[:, :2]), axis=1)
            if np.any(finite):
                yz = pts[finite, :2]
                points.append(np.column_stack((np.zeros(yz.shape[0], dtype=float), yz[:, 1], yz[:, 0])))
    for target in list(getattr(bundle, "targets", []) or []):
        footprints = scene_target_active_footprint_polylines(target)
        if footprints:
            for pts in footprints:
                pts = np.asarray(pts, dtype=float)
                if pts.ndim == 2 and pts.shape[0] and pts.shape[1] >= 3:
                    finite = np.all(np.isfinite(pts[:, :3]), axis=1)
                    if np.any(finite):
                        points.append(pts[finite, :3])
            continue
        center = np.asarray(getattr(target, "center_world", []), dtype=float).reshape(-1)[:3]
        if center.size >= 3 and np.all(np.isfinite(center[:3])):
            points.append(center[:3].reshape(1, 3))
    if not points:
        bounds = getattr(bundle, "bounds", BoundsRect())
        if not bool(getattr(bounds, "is_empty", True)):
            pts2 = np.asarray(
                (
                    (float(bounds.x_min), float(bounds.y_min)),
                    (float(bounds.x_max), float(bounds.y_max)),
                ),
                dtype=float,
            )
            points.append(np.column_stack((np.zeros(pts2.shape[0], dtype=float), pts2[:, 1], pts2[:, 0])))
    if not points:
        return np.zeros(3, dtype=float), max(float(getattr(bundle, "max_half", 1.0) or 1.0) * 2.0, 1.0)
    all_points = np.vstack(points)
    mins = np.min(all_points, axis=0)
    maxs = np.max(all_points, axis=0)
    center = 0.5 * (mins + maxs)
    radius = max(float(maxs[0] - mins[0]), float(maxs[1] - mins[1]), float(maxs[2] - mins[2]), 1.0)
    return center, float(radius)


def _scene_center_radius_for_projection(bundle: SceneBundle) -> tuple[np.ndarray, float]:
    return scene_display_center_radius(bundle)


def _targets_by_trace_surface(bundle: SceneBundle) -> dict[int, object]:
    targets: dict[int, object] = {}
    for target in list(getattr(bundle, "targets", []) or []):
        surface = getattr(target, "trace_surface", None)
        try:
            targets[int(surface)] = target
        except Exception:
            continue
    return targets


def _missed_detector_target_for_path(path: object, targets_by_surface: dict[int, object]) -> object | None:
    if ray_path_terminal_status_from_events(path) != "missed_detector":
        return None
    metadata = ray_path_terminal_metadata(path)
    surface = metadata.get("detector_miss_surface")
    if surface in (None, ""):
        event = ray_path_terminal_event(path)
        if event is not None:
            surface = getattr(event, "surface_id", None)
    try:
        return targets_by_surface.get(int(surface))
    except Exception:
        return None


def _target_frame_axes_for_projection(target: object | None) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    if target is None:
        return None
    try:
        center = np.asarray(getattr(target, "center_world", ()), dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if center.size < 3 or not np.all(np.isfinite(center[:3])):
        return None
    normal = _unit_vector_or_none(getattr(target, "normal_world", None))
    if normal is None:
        return None
    tangent = _unit_vector_or_none(getattr(target, "tangent_world", None))
    if tangent is None:
        tangent = np.asarray((1.0, 0.0, 0.0), dtype=float)
        if abs(float(np.dot(tangent, normal))) > 0.95:
            tangent = np.asarray((0.0, 1.0, 0.0), dtype=float)
    tangent = tangent - normal * float(np.dot(tangent, normal))
    tangent = _unit_vector_or_none(tangent)
    if tangent is None:
        return None
    bitangent = _unit_vector_or_none(np.cross(normal, tangent))
    if bitangent is None:
        return None
    return center[:3], tangent, bitangent


def _display_detector_miss_limit(target: object | None, radius: float) -> float:
    try:
        scene_radius = float(radius)
    except Exception:
        scene_radius = 1.0
    if not np.isfinite(scene_radius) or scene_radius <= 0.0:
        scene_radius = 1.0
    dimensions = scene_target_active_dimensions(target) if target is not None else None
    aperture_span = max(dimensions) if dimensions is not None else 1.0
    scene_limit = max(25.0, min(scene_radius * 0.35, 250.0))
    return float(max(aperture_span * 1.25, scene_limit))


def _display_detector_miss_point_on_plane(
    point: object,
    target: object | None,
    radius: float,
) -> tuple[np.ndarray | None, bool]:
    try:
        terminal = np.asarray(point, dtype=float).reshape(-1)[:3]
    except Exception:
        return None, False
    if terminal.size < 3 or not np.all(np.isfinite(terminal[:3])):
        return None, False
    axes = _target_frame_axes_for_projection(target)
    if axes is None:
        return terminal[:3], False
    center, tangent, bitangent = axes
    rel = terminal[:3] - center
    u = float(np.dot(rel, tangent))
    v = float(np.dot(rel, bitangent))
    limit = _display_detector_miss_limit(target, radius)
    radial = float(np.hypot(u, v))
    capped = False
    if np.isfinite(radial) and radial > limit > 0.0:
        scale = limit / radial
        u *= scale
        v *= scale
        capped = True
    display_point = center + tangent * u + bitangent * v
    if not np.allclose(display_point, terminal[:3], rtol=0.0, atol=1.0e-9):
        capped = True
    return display_point, capped


def detector_planes_for_hard_stop(bundle: object, radius: float) -> list[tuple[np.ndarray, np.ndarray, float]]:
    """Detector/Image planes that hard-stop the DRAWN ray polyline (display-only).

    Returns ``(center_world, normal_unit, radial_limit)`` for every
    ``is_detector`` scene target. A ray polyline that crosses one of these planes
    within ``radial_limit`` of its centre is truncated there by
    ``bounded_ray_points_for_scene_display`` so no ray (incl. an escaped/missed
    one shown via the Miss toggle) is drawn past a detector. The limit reuses
    ``_display_detector_miss_limit`` so the hard stop matches the existing
    missed-detector cap (a generous radial board, NOT a tight active-area rect).
    """
    planes: list[tuple[np.ndarray, np.ndarray, float]] = []
    for target in list(getattr(bundle, "targets", []) or []):
        if not bool(getattr(target, "is_detector", False)):
            continue
        axes = _target_frame_axes_for_projection(target)
        if axes is None:
            continue
        center = axes[0]
        normal = _unit_vector_or_none(getattr(target, "normal_world", None))
        if normal is None:
            continue
        limit = float(_display_detector_miss_limit(target, radius))
        if not np.isfinite(limit) or limit <= 0.0:
            continue
        planes.append((np.asarray(center, dtype=float)[:3], np.asarray(normal, dtype=float)[:3], limit))
    return planes


def _clip_polyline_at_detector_planes(
    pts: np.ndarray,
    detector_planes: list[tuple[np.ndarray, np.ndarray, float]] | None,
) -> tuple[np.ndarray, bool]:
    """Truncate ``pts`` at the FIRST detector plane the ray reaches within extent.

    Finds the first point along the polyline where it crosses FORWARD into a
    detector plane (``(p-centre)·normal`` goes from <0 to >=0) within the plane's
    radial limit, and truncates there. This now includes a ray PASSING THROUGH the
    plane at an interior vertex (bugs/0093: a transmit beam whose polyline has a
    vertex exactly on the image/detector plane and continues past it -- the
    diverging tail beyond was still drawn). A ray that TERMINATES on the plane (its
    last vertex is on it) keeps its cap (not re-clipped to zero); a ray that crosses
    outside the radial board (a genuine miss) is left alone.
    """
    if detector_planes is None or len(detector_planes) == 0:
        return pts, False
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return pts, False
    p = pts[:, :3]
    n = p.shape[0]
    best_param: float | None = None
    best_cross: np.ndarray | None = None
    best_i: int | None = None
    for center, normal, limit in detector_planes:
        center = np.asarray(center, dtype=float)[:3]
        normal = np.asarray(normal, dtype=float)[:3]
        d = (p - center) @ normal  # signed distance of every vertex to this plane
        for i in range(1, n):
            if not (d[i - 1] < -1.0e-6 and d[i] >= -1.0e-6):
                continue  # the ray does not cross FORWARD into the plane here
            if i == n - 1 and abs(d[i]) <= 1.0e-6:
                break  # the ray ENDS on the plane (hit_detector) -> keep its cap
            denom = d[i - 1] - d[i]
            t = (d[i - 1] / denom) if abs(denom) > 1.0e-12 else 1.0
            t = min(max(t, 0.0), 1.0)
            cross = p[i - 1] + t * (p[i] - p[i - 1])
            if float(np.linalg.norm(cross - center)) > limit:
                break  # crosses outside the radial board -> a genuine miss
            param = float(i - 1) + t
            if best_param is None or param < best_param:
                best_param = param
                best_cross = cross
                best_i = i
            break  # first forward crossing for this plane
    if best_cross is None or best_i is None:
        return pts, False
    truncated = np.vstack((p[:best_i], best_cross.reshape(1, 3)))
    if truncated.shape[0] >= 2:
        return truncated, True
    return pts, False


#: bugs/0551: how far an ESCAPED ray's DISPLAY tail may run, as a fraction of the scene
#: envelope radius. Scene-RELATIVE by construction -- there is no absolute millimetre bound
#: here, so a 10 mm micro-objective and a 2 m telescope both get a tail proportionate to
#: themselves, and the 75 mm floor below still protects small scenes (0.40 only starts to
#: bind above a ~188 mm radius, i.e. exactly the large scenes where 1.25 ran off the frame).
_ESCAPED_TAIL_SCENE_RADIUS_FACTOR = 0.40


def bounded_ray_points_for_scene_display(
    points: object,
    center: np.ndarray,
    radius: float,
    *,
    terminal_status: str = "",
    terminal_target: object | None = None,
    terminal_direction: object | None = None,
    detector_planes: list[tuple[np.ndarray, np.ndarray, float]] | None = None,
    branch_path: str = "",
    scene_has_diffuse_scatter: bool = False,
) -> tuple[np.ndarray, bool]:
    try:
        pts = np.asarray(points, dtype=float)
    except Exception:
        return np.empty((0, 3), dtype=float), False
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return np.empty((0, 3), dtype=float), False
    pts = np.array(pts[:, :3], dtype=float, copy=True)
    finite = np.all(np.isfinite(pts), axis=1)
    if not np.all(finite):
        pts = pts[finite]
    if pts.shape[0] < 2:
        return np.empty((0, 3), dtype=float), True
    scene_center = np.asarray(center, dtype=float).reshape(-1)[:3]
    if scene_center.size != 3 or not np.all(np.isfinite(scene_center)):
        scene_center = np.zeros(3, dtype=float)
    try:
        scene_radius = float(radius)
    except Exception:
        scene_radius = 1.0
    if not np.isfinite(scene_radius) or scene_radius <= 0.0:
        scene_radius = 1.0
    status = str(terminal_status or "").strip().lower()
    # bugs/0506: is this ray on a branch whose synthesized detector is display-noise?
    # (per-path diffuse-scatter / internal-bounce, or ANY non-primary branch once the
    # scene has diffuse scatter -- the bugs/0184 rule). Such a branch is drawn BOUNDED:
    # its hit_detector rays keep the hard-stop clip (no 0459 exemption) and its escaped
    # rays keep only a short diagnostic stub instead of the full scene-radius tail
    # (measured: the 15-ray leak escape tail ran to 318 mm past every plane's shrunken
    # radial capture once 0464 sized the planes to their beams).
    _bp = str(branch_path or "").strip()
    _suppressed_branch = False
    if _bp:
        if scene_has_diffuse_scatter and _bp.lower() not in ("", "primary"):
            _suppressed_branch = True
        else:
            try:
                from KrakenOS.UI.services.branch_detectors import _branch_path_draw_suppressed

                _suppressed_branch = _branch_path_draw_suppressed(_bp)
            except Exception:
                _suppressed_branch = False
    terminal_was_capped = False
    if status == "missed_detector" and terminal_target is not None and pts.shape[0] >= 2:
        display_point, terminal_was_capped = _display_detector_miss_point_on_plane(
            pts[-1],
            terminal_target,
            scene_radius,
        )
        if display_point is not None:
            pts[-1] = display_point[:3]
    elif status == "escaped" and pts.shape[0] >= 2:
        terminal_segment = pts[-1] - pts[-2]
        terminal_length = float(np.linalg.norm(terminal_segment))
        # Escaped rays are display diagnostics.  Keep the full trace metadata,
        # but draw a scene-envelope tail long enough to show the output
        # direction without letting one distant miss dominate autoscale.
        #
        # bugs/0551 (flag_20260805_081647 / _081811, "still have unbounded rays"): the factor
        # was 1.25, which on the swapped AZ85 scene drew every escape ~375 mm -- past the
        # prism, past the camera and clean off the frame, while the TRACE stopped at 237 mm.
        # That tail is EXTENDED beyond the traced stub (see below), so what the user was
        # judging as stray light was display scaffolding, not physics. Measured on that scene
        # from the flag's own camera: 1.25 -> drawn max x 375.1; 0.40 -> 233.6, with the beam,
        # the fold and the camera bundle pixel-identical. Anything at or below ~0.40 gives the
        # same picture there (the drawn extent falls back to the scene geometry), so 0.40 is
        # the largest value that fixes it -- the direction cue survives, the starburst does not.
        max_terminal_length = max(75.0, min(scene_radius * _ESCAPED_TAIL_SCENE_RADIUS_FACTOR, 600.0))
        if _suppressed_branch:
            # bugs/0506: a suppressed branch's escape is bounded -- a 75 mm stub shows
            # the direction without the starburst (the 0182 bounding contract).
            max_terminal_length = 75.0
        geometry_direction = _unit_vector_or_none(terminal_segment)
        direction = _unit_vector_or_none(terminal_direction)
        if direction is None:
            direction = geometry_direction
        elif geometry_direction is not None and float(np.dot(direction, geometry_direction)) < 0.0:
            # ``terminal_direction`` is sourced from the trace event's R_LMN
            # (and LMN) fields, which carry the raw KrakenOS ``ResVec`` without
            # the cumulative ``SIGN`` flip.  After an odd number of reflections
            # ``ResVec`` points backwards.  The traced polyline is built from
            # ``ResVec * SIGN`` (see KrakenSys.__AppendNsTerminalSegment) and is
            # the authoritative physical direction, so reconcile the tail
            # against it instead of drawing the escaped ray 180 deg reversed.
            direction = -direction
        if direction is not None and np.isfinite(terminal_length) and max_terminal_length > 0.0:
            if terminal_length > max_terminal_length:
                pts[-1] = pts[-2] + direction * max_terminal_length
            else:
                remaining_length = max_terminal_length - terminal_length
                if remaining_length > 1.0e-9:
                    pts = np.vstack((pts, pts[-1] + direction * remaining_length))
            terminal_was_capped = True
    # Hard stop: a detector/Image plane terminates the DRAWN ray (display-only;
    # the trace is unchanged). Applied after the escaped tail / missed cap so a
    # tail that would shoot past a detector is truncated at the plane instead.
    #
    # bugs/0459: NOT for a ray that already terminated ON a detector. The hard stop
    # exists to bound rays that would otherwise run past one -- escaped and missed ones,
    # per the docstring above. A ray with ``hit_detector`` has already stopped where the
    # physics put it, and clipping it again can only cut it SHORT at some OTHER arm's
    # plane: ``detector_planes_for_hard_stop`` returns a plane for EVERY is_detector
    # target, including the synthesized detectors on non-imaging beam-splitter arms.
    # Measured on the user's BS scene: all 166 hit_detector rays entered this function
    # reaching x=230.4 (median) and left it at x=81.7, clipped by the mid-scene arm's
    # plane at x=74.4 -- the beam visibly stopped just past the lens and never reached
    # the sensor, while the trace itself was correct the whole time
    # (flag_20260729_094555: traced_ray_max_x 243.04 vs drawn 85.4).
    # bugs/0506 (phase 178/180 regression): the 0459 exemption must not extend to a
    # DRAW-SUPPRESSED branch (diffuse scatter / internal bounce). Those leaves' synthesized
    # detectors exist PRECISELY to bound the starburst (bugs/0182/0183) -- they draw no
    # footprint, and their rays also terminate ``hit_detector`` (on their own far-parked
    # plane), so the blanket exemption let the scatter spray run to its full flight
    # (measured max|x,y| 318 vs the 150 bound). A suppressed branch clips at the FIRST
    # plane crossed, exactly as before 0459; a clean imaging arm keeps the 0459 behaviour
    # and draws all the way to its sensor.
    detector_clip_applied = False
    if detector_planes and (status != "hit_detector" or _suppressed_branch):
        pts, detector_clip_applied = _clip_polyline_at_detector_planes(pts, detector_planes)
        if detector_clip_applied:
            terminal_was_capped = True
    display_radius = max(scene_radius * 3.0, 250.0)
    offsets = pts - scene_center
    distances = np.linalg.norm(offsets, axis=1)
    too_far = distances > display_radius
    if np.any(too_far):
        safe_distances = np.maximum(distances[too_far], 1.0e-12)
        pts[too_far] = scene_center + offsets[too_far] * (display_radius / safe_distances)[:, None]
    bounded = bool(terminal_was_capped or (not np.all(finite)) or np.any(too_far))
    if pts.shape[0] < 2:
        return np.empty((0, 3), dtype=float), True
    return pts, bounded


_bounded_ray_points_for_projection = bounded_ray_points_for_scene_display


def _convex_hull_2d(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 2:
        return np.empty((0, 2), dtype=float)
    finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
    pts = pts[finite, :2]
    if pts.shape[0] < 3:
        return np.empty((0, 2), dtype=float)
    order = np.lexsort((pts[:, 1], pts[:, 0]))
    pts = pts[order]
    unique = [pts[0]]
    for point in pts[1:]:
        if np.linalg.norm(point - unique[-1]) > 1e-9:
            unique.append(point)
    pts = np.asarray(unique, dtype=float)
    if pts.shape[0] < 3:
        return np.empty((0, 2), dtype=float)

    def cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    lower: list[np.ndarray] = []
    for point in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 1e-12:
            lower.pop()
        lower.append(point)
    upper: list[np.ndarray] = []
    for point in pts[::-1]:
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 1e-12:
            upper.pop()
        upper.append(point)
    hull = lower[:-1] + upper[:-1]
    return np.asarray(hull, dtype=float)


def _pick_regions_from_curves(curves: list[ProjectedCurve2D]) -> list[PickRegion]:
    grouped: dict[int, list[np.ndarray]] = {}
    for curve in curves:
        try:
            row_index = int(curve.row_index)
        except Exception:
            continue
        if row_index < 0:
            continue
        if str(getattr(curve, "kind", "") or "") == "lens_edge":
            continue
        points = np.asarray(curve.points_2d, dtype=float)
        if points.ndim != 2 or points.shape[0] < 2:
            continue
        grouped.setdefault(row_index, []).append(points)
    return [
        PickRegion(row_index=row_index, polylines=polylines)
        for row_index, polylines in sorted(grouped.items())
    ]


def _terminal_surface_ids_from_projected_events(events: list[ProjectedRayEvent2D]) -> np.ndarray:
    surface_ids: list[int] = []
    for event in list(events or []):
        if str(getattr(event, "event_kind", "") or "") != "terminal":
            continue
        surface_id = getattr(event, "surface_id", None)
        if surface_id is None:
            continue
        try:
            surface_ids.append(int(surface_id))
        except Exception:
            continue
    return np.asarray(surface_ids, dtype=int)
