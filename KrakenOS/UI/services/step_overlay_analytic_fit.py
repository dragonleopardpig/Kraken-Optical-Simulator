"""Geometry-only sphere/plane fitting for STEP-overlay → analytic-surface promotion.

User-drawn STEP files don't come with Zemax prescriptions. This module
fits a sphere or plane (least-squares) to each preserved face of an
imported STEP overlay, so the front/back optical surfaces of a self-
designed lens can be promoted to analytic ``Standard`` rows
(``Rc`` / ``thickness`` / ``diameter``) instead of an STL solid row.

The only thing geometry can't supply is the glass material; the user
types that at promote time.

Public API:

* ``fit_face(points)`` — return ``{'kind': 'sphere'|'plane', ...}``
  from a triangle-vertex point cloud.
* ``fit_step_overlay_analytic_surfaces(mesh, faces, *, source_axis)``
  — given the imported mesh and the preserved face metadata, return a
  list of ordered analytic-surface specs along ``source_axis``
  suitable for emitting Standard rows.

The fit results match Edmund Zemax CURV values to 0.0001 mm on the
DCV (-52.10) and Achromat front (+34.53). See
``validate_open3d_promotion_analytic_fit`` for the locked-in
regression numbers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np


@dataclass
class SphereFit:
    kind: str = "sphere"
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    radius: float = 0.0
    signed_rc: float = 0.0           # positive Rc = center of curvature on the +normal side
    residual_mm: float = 0.0


@dataclass
class PlaneFit:
    kind: str = "plane"
    point: tuple[float, float, float] = (0.0, 0.0, 0.0)
    normal: tuple[float, float, float] = (0.0, 0.0, 1.0)
    residual_mm: float = 0.0


@dataclass
class AnalyticSurfaceSpec:
    """One analytic Standard row's data, ordered along the optical axis."""

    face_id: str
    fit: Any                         # SphereFit | PlaneFit
    centroid: tuple[float, float, float]
    normal: tuple[float, float, float]
    axial_position: float            # signed projection onto source_axis
    radius_mm: float                 # lateral extent for the row's Diameter
    diameter_mm: float


@dataclass
class AnalyticSurfaceFitResult:
    """Ordered list of analytic surfaces extracted from a STEP overlay."""

    specs: list[AnalyticSurfaceSpec] = field(default_factory=list)
    source_axis: tuple[float, float, float] = (0.0, 0.0, 1.0)
    notes: list[str] = field(default_factory=list)


def _normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        return np.zeros_like(vec)
    return vec / norm


def fit_sphere(points: np.ndarray) -> SphereFit | None:
    """Least-squares sphere fit. Returns None when points are degenerate.

    Solves the linear system ``2(p·c) + d = ‖p‖²`` for ``c = (cx,cy,cz)``
    and ``d = -(‖c‖² - r²)``. Robust for any face with > ~6 points
    spanning a non-degenerate cap of the sphere; the planar case
    drops out as ``radius → ∞`` and is caught by the residual
    comparison.
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 6 or pts.shape[1] < 3:
        return None
    if not np.all(np.isfinite(pts[:, :3])):
        return None
    A = np.column_stack([2.0 * pts[:, 0], 2.0 * pts[:, 1], 2.0 * pts[:, 2], np.ones(pts.shape[0])])
    b = (pts[:, :3] ** 2).sum(axis=1)
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except Exception:
        return None
    cx, cy, cz, d = (float(v) for v in sol)
    r2 = d + cx * cx + cy * cy + cz * cz
    if r2 <= 0 or not np.isfinite(r2):
        return None
    radius = float(np.sqrt(r2))
    rads = np.sqrt(((pts[:, :3] - np.array([cx, cy, cz])) ** 2).sum(axis=1))
    residual = float(np.std(rads))
    return SphereFit(center=(cx, cy, cz), radius=radius, residual_mm=residual)


def fit_plane(points: np.ndarray) -> PlaneFit | None:
    """SVD plane fit. Normal is the smallest-variance principal axis."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 3 or pts.shape[1] < 3:
        return None
    if not np.all(np.isfinite(pts[:, :3])):
        return None
    centroid = pts[:, :3].mean(axis=0)
    centered = pts[:, :3] - centroid
    try:
        _, _, vh = np.linalg.svd(centered, full_matrices=False)
    except Exception:
        return None
    normal = _normalize(np.asarray(vh[-1], dtype=float))
    residual = float(np.std(centered @ normal))
    return PlaneFit(
        point=tuple(float(v) for v in centroid),
        normal=tuple(float(v) for v in normal),
        residual_mm=residual,
    )


def fit_face(points: np.ndarray) -> SphereFit | PlaneFit | None:
    """Pick sphere or plane based on residual.

    A sphere fit always succeeds for a curved cap. A plane fit also
    succeeds, but with a larger residual when the surface is curved.
    Pick sphere when its residual is at least 2× smaller than the
    plane's; otherwise the face is genuinely flat and the plane fit
    is the correct model.
    """
    sphere = fit_sphere(points)
    plane = fit_plane(points)
    if sphere is None:
        return plane
    if plane is None:
        return sphere
    # Curved surfaces fit sphere ~0 residual and plane several mm
    # residual; flat surfaces fit plane ~0 and sphere ~0 too (since
    # the sphere collapses to a huge radius). Resolve by picking the
    # smaller residual, with a margin to prefer plane when both
    # residuals are tiny (avoids spurious "Rc = 10^9" fits on flat
    # faces).
    if sphere.residual_mm <= 1e-4 and plane.residual_mm <= 1e-4:
        return plane
    if sphere.residual_mm < plane.residual_mm * 0.5:
        return sphere
    return plane


def _signed_rc_from_sphere(
    sphere: SphereFit,
    face_centroid: np.ndarray,
    source_axis: np.ndarray,
) -> float:
    """Convert raw sphere radius to KrakenOS signed Rc.

    KrakenOS convention: ``Rc > 0`` when the center of curvature sits
    on the ``+source_axis`` side of the surface (the side where light
    continues after refraction). The sign must come from the
    SHARED optical axis, not the per-face outward normal -- a DCV
    has anti-parallel normals on its two end faces and the
    previous "use the normal" rule collapsed both to the same sign,
    so the back surface fit ``-52.10`` instead of ``+52.10``.

    The sign rule recovers the Zemax CURV sign on every fixture:

      * DCV front: centroid @ z=-1.25, sphere center @ z=-53.35
        -> dot((center - centroid), +Z) = -52.10 < 0  ->  Rc = -52.10  (match)
      * DCV back : centroid @ z=+1.25, sphere center @ z=+53.35
        -> dot((center - centroid), +Z) = +52.10 > 0  ->  Rc = +52.10  (match)
    """
    center = np.asarray(sphere.center, dtype=float).reshape(3)
    centroid = np.asarray(face_centroid, dtype=float).reshape(3)
    axis = _normalize(np.asarray(source_axis, dtype=float).reshape(3))
    if np.linalg.norm(axis) < 1e-9:
        return float(sphere.radius)
    offset = float(np.dot(center - centroid, axis))
    return float(sphere.radius) if offset > 0 else -float(sphere.radius)


def fit_step_overlay_analytic_surfaces(
    mesh: Any,
    faces: Sequence[dict[str, Any]],
    *,
    source_axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    triangle_cap: int = 1500,
) -> AnalyticSurfaceFitResult:
    """Produce an ordered list of analytic surface specs along ``source_axis``.

    Steps:
      1. Read each preserved face's triangle indices, gather their
         vertex points from the mesh.
      2. Fit either a sphere or a plane to the vertex cloud
         (``fit_face`` picks the better model).
      3. Project the face centroid onto ``source_axis`` to obtain
         an axial position; this is used to ORDER the surfaces from
         front to back along the optical axis.
      4. Return one ``AnalyticSurfaceSpec`` per face, sorted by
         axial position.

    The caller decides which faces to include — typically the
    output of ``_auto_assign_lens_face_functions`` (the 2-3 faces
    flagged ``Transmit/Port``).
    """
    result = AnalyticSurfaceFitResult(source_axis=tuple(float(v) for v in source_axis))
    axis = _normalize(np.asarray(source_axis, dtype=float).reshape(3))
    specs: list[AnalyticSurfaceSpec] = []
    for face in faces:
        if not isinstance(face, dict):
            continue
        tri_ids = list(face.get("triangle_indices") or face.get("cell_indices") or [])
        if not tri_ids:
            continue
        verts: list[list[float]] = []
        for tid in tri_ids[: max(int(triangle_cap), 0) or len(tri_ids)]:
            try:
                cell = mesh.get_cell(int(tid))
            except Exception:
                cell = None
            if cell is None:
                continue
            try:
                n_points = int(cell.n_points)
            except Exception:
                continue
            for pid in range(n_points):
                try:
                    point = cell.points[pid]
                except Exception:
                    continue
                verts.append([float(point[0]), float(point[1]), float(point[2])])
        if not verts:
            continue
        pts = np.asarray(verts, dtype=float)
        fit = fit_face(pts)
        if fit is None:
            continue
        centroid = np.asarray(face.get("centroid") or pts.mean(axis=0), dtype=float).reshape(-1)[:3]
        normal = np.asarray(face.get("normal") or [0.0, 0.0, 1.0], dtype=float).reshape(-1)[:3]
        normal = _normalize(normal)
        if isinstance(fit, SphereFit):
            fit.signed_rc = _signed_rc_from_sphere(fit, centroid, axis)
        # Lateral extent for the row's diameter: from the points
        # perpendicular to source_axis.
        rel = pts - centroid
        perp = rel - np.outer(rel @ axis, axis)
        if perp.size:
            radial = float(np.linalg.norm(perp, axis=1).max())
        else:
            radial = 0.0
        axial_pos = float(np.dot(centroid - 0.0, axis))
        specs.append(
            AnalyticSurfaceSpec(
                face_id=str(face.get("face_id") or "?"),
                fit=fit,
                centroid=tuple(float(v) for v in centroid),
                normal=tuple(float(v) for v in normal),
                axial_position=axial_pos,
                radius_mm=radial,
                diameter_mm=2.0 * radial,
            )
        )
    specs.sort(key=lambda s: s.axial_position)
    result.specs = specs
    if not specs:
        result.notes.append("no usable faces to fit")
    return result
