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
    ProjectedCurve2D,
    ProjectedRay2D,
    ProjectedScene2D,
    SceneBundle,
    StyleHint,
)


def normalize_projection_plane(orientation: str) -> str:
    value = str(orientation or "Vertical").strip()
    if value in {"XZ", "XY", "YZ"}:
        return value
    return "YZ"


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
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(bundle.planes),
            labels=list(bundle.labels) if self.plane == "YZ" else [],
            pick_regions=list(bundle.pick_regions) if self.plane == "YZ" else [],
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
                # Surface curves are already in YZ display coordinates from
                # the builder.  Pass them through unchanged for the primary
                # layout projection until surface curves become fully 3-D.
                points_2d = pts[:, :2]
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
                reaches_image=path.reaches_image,
                surface_ids=np.asarray(path.surface_ids, dtype=int),
                branch_label=str(path.branch_label or ""),
                branch_path=str(path.branch_path or path.branch_label or ""),
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
