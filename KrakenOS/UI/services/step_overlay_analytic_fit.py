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


def _triangle_centroid(mesh, triangle_id: int) -> np.ndarray | None:
    try:
        cell = mesh.get_cell(int(triangle_id))
    except Exception:
        return None
    if cell is None:
        return None
    try:
        n = int(cell.n_points)
    except Exception:
        return None
    if n <= 0:
        return None
    pts = []
    for pid in range(n):
        try:
            pts.append(cell.points[pid])
        except Exception:
            continue
    if not pts:
        return None
    return np.asarray(pts, dtype=float).mean(axis=0)


def _face_vertex_cloud(mesh, triangle_ids: list[int], cap: int = 1500) -> np.ndarray:
    out: list[list[float]] = []
    for tid in triangle_ids[: max(int(cap), 0) or len(triangle_ids)]:
        try:
            cell = mesh.get_cell(int(tid))
        except Exception:
            continue
        if cell is None:
            continue
        try:
            n = int(cell.n_points)
        except Exception:
            continue
        for pid in range(n):
            try:
                pt = cell.points[pid]
            except Exception:
                continue
            out.append([float(pt[0]), float(pt[1]), float(pt[2])])
    if not out:
        return np.empty((0, 3), dtype=float)
    return np.asarray(out, dtype=float)


def maybe_split_full_sphere_face(
    mesh: Any,
    face: dict[str, Any],
    *,
    source_axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
    residual_tolerance_mm: float = 0.05,
    coverage_threshold: float = 0.80,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Detect a face that IS the entire sphere and split it.

    Ball-lens STEPs often arrive as a SINGLE face group that wraps
    both hemispheres -- the importer area-weighted-normals the whole
    sphere and only the centroid normal sticks. The auto-assignment
    heuristic looks for two anti-parallel faces, so it can't find a
    front/back pair on a one-face sphere and the analytic-promote
    path bails.

    This helper:
      1. Fits a sphere to the face's triangle vertices.
      2. Verifies the fit is tight (residual < ``residual_tolerance_mm``)
         AND the face area is ``>= coverage_threshold`` of the full
         sphere area ``4 pi R^2``.
      3. Splits the triangle list along the sphere-center plane
         perpendicular to ``source_axis`` and returns two synthesized
         face records (front + back) that the rest of the pipeline can
         treat like any other anti-parallel face pair.

    Returns ``None`` when the face isn't a clean full sphere.
    """
    tri_ids = list(face.get("triangle_indices") or [])
    if len(tri_ids) < 20:
        return None
    sampling_step = max(1, len(tri_ids) // 300)
    pts = _face_vertex_cloud(mesh, tri_ids[::sampling_step])
    if pts.shape[0] < 6:
        return None
    sphere = fit_sphere(pts)
    if sphere is None:
        return None
    if not np.isfinite(sphere.residual_mm) or sphere.residual_mm > float(residual_tolerance_mm):
        return None
    if not np.isfinite(sphere.radius) or sphere.radius <= 0:
        return None
    full_area = 4.0 * np.pi * sphere.radius * sphere.radius
    face_area = float(face.get("area_mm2", 0.0) or 0.0)
    if full_area <= 0 or face_area < float(coverage_threshold) * full_area:
        return None
    center = np.asarray(sphere.center, dtype=float)
    axis = np.asarray(source_axis, dtype=float)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-9:
        return None
    axis = axis / norm

    front_tids: list[int] = []
    back_tids: list[int] = []
    for tid in tri_ids:
        tri_c = _triangle_centroid(mesh, tid)
        if tri_c is None:
            continue
        if float(np.dot(tri_c - center, axis)) < 0:
            front_tids.append(int(tid))
        else:
            back_tids.append(int(tid))
    if len(front_tids) < 10 or len(back_tids) < 10:
        return None

    # KrakenOS Standard surfaces position themselves at the surface
    # VERTEX (the extreme point of the cap along the optical axis),
    # NOT at the geometric centroid of the spherical patch. For a
    # full ball lens with R = 4.7625 mm centered at z = 0, the
    # vertex of the front hemisphere is at z = -R, the back vertex
    # is at z = +R, and the "thickness" between them is 2R =
    # 9.525 mm -- the physical diameter of the ball, matching the
    # Zemax DISZ for surface 1. Using triangle-centroid averages
    # would instead give ~R/2 which makes the analytic body half
    # the right thickness, with the back surface ending up INSIDE
    # the front sphere.
    front_centroid = center - sphere.radius * axis
    back_centroid = center + sphere.radius * axis

    base = {k: v for k, v in face.items() if k not in {"triangle_indices", "centroid", "normal", "area_mm2"}}
    half_area = float(face_area) * 0.5
    front_face = dict(base)
    front_face.update(
        {
            "face_id": f"{str(face.get('face_id') or 'sphere')}/front",
            "triangle_indices": front_tids,
            "centroid": [float(front_centroid[0]), float(front_centroid[1]), float(front_centroid[2])],
            # Outward normal of the front hemisphere = -axis (it points
            # back toward the incoming light direction).
            "normal": [-float(axis[0]), -float(axis[1]), -float(axis[2])],
            "area_mm2": half_area,
            "split_origin": "auto_sphere_split",
        }
    )
    back_face = dict(base)
    back_face.update(
        {
            "face_id": f"{str(face.get('face_id') or 'sphere')}/back",
            "triangle_indices": back_tids,
            "centroid": [float(back_centroid[0]), float(back_centroid[1]), float(back_centroid[2])],
            "normal": [float(axis[0]), float(axis[1]), float(axis[2])],
            "area_mm2": half_area,
            "split_origin": "auto_sphere_split",
        }
    )
    return front_face, back_face


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
