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
    ray_path_terminal_status_from_events,
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
        rays = self._project_rays(bundle)
        bounds = self._compute_bounds(curves, rays)
        pick_regions = _pick_regions_from_curves(curves)
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(bundle.planes),
            labels=list(bundle.labels) if self.plane == "YZ" else [],
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
            if pts.shape[1] >= 3:
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
            ))
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
            ))
        return projected

    def _project_rays(self, bundle: SceneBundle) -> list[ProjectedRay2D]:
        projected: list[ProjectedRay2D] = []
        folded_display = bundle.extra.get("folded_ray_display_paths")
        for path in bundle.ray_paths:
            folded_pts = None
            if folded_display is not None and path.ray_index < len(folded_display):
                candidate = np.asarray(folded_display[path.ray_index], dtype=float)
                if candidate.ndim == 2 and candidate.shape[0] >= 2:
                    folded_pts = candidate
            if folded_pts is not None and self.plane == "YZ":
                display_points = folded_pts
            else:
                pts = np.asarray(path.points_world, dtype=float)
                if pts.ndim != 2 or pts.shape[0] < 2:
                    continue
                display_points = self.project_xyz_points(pts)
            projected.append(ProjectedRay2D(
                ray_index=path.ray_index,
                field_index=path.field_index,
                color=path.color,
                points_2d=np.asarray(display_points, dtype=float),
                reaches_image=ray_path_reaches_image_from_events(path),
                terminal_status=ray_path_terminal_status_from_events(path),
                surface_ids=np.asarray(path.surface_ids, dtype=int),
                branch_label=str(path.branch_label or ""),
                branch_path=str(path.branch_path or path.branch_label or ""),
                events_2d=self._project_ray_events(path, np.asarray(display_points, dtype=float)),
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
