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


class SceneProjector2D:
    """Project a :class:`SceneBundle` into a :class:`ProjectedScene2D`."""

    def __init__(self, orientation: str = "Vertical") -> None:
        self.orientation = orientation

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------

    def project_bundle(self, bundle: SceneBundle) -> ProjectedScene2D:
        """Project all geometry in *bundle* to 2-D display coordinates."""
        curves = self._project_curves(bundle)
        rays = self._project_rays(bundle)
        bounds = self._compute_bounds(curves, rays)
        return ProjectedScene2D(
            curves=curves,
            rays=rays,
            planes=list(bundle.planes),
            labels=list(bundle.labels),
            pick_regions=list(bundle.pick_regions),
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

    # ------------------------------------------------------------------
    # private
    # ------------------------------------------------------------------

    def _project_curves(self, bundle: SceneBundle) -> list[ProjectedCurve2D]:
        projected: list[ProjectedCurve2D] = []
        for curve in bundle.surface_curves:
            pts = np.asarray(curve.points_world, dtype=float)
            if pts.ndim != 2 or pts.shape[0] < 2:
                continue
            # Surface curves are already in display coordinates from the
            # builder (Phase 2 convention).  Pass them through unchanged.
            projected.append(ProjectedCurve2D(
                row_index=curve.row_index,
                kind=curve.kind,
                points_2d=pts,
                style=curve.style,
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
            if folded_pts is not None:
                display_points = folded_pts
            else:
                pts = np.asarray(path.points_world, dtype=float)
                if pts.ndim != 2 or pts.shape[0] < 2:
                    continue
                x_vals, y_vals = self.project_points(pts[:, 2], pts[:, 1])
                display_points = np.column_stack((x_vals, y_vals))
            projected.append(ProjectedRay2D(
                ray_index=path.ray_index,
                field_index=path.field_index,
                color=path.color,
                points_2d=np.asarray(display_points, dtype=float),
                reaches_image=path.reaches_image,
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
