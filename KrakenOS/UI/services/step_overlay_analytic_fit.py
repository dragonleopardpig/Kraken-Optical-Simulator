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
class ToroidFit:
    """Plano-cylindrical or toroidal surface fit.

    Encoded as a KrakenOS Standard row with:

      * ``Rc`` = the MERIDIONAL radius (the principal axis with
        higher curvature magnitude),
      * ``Cylinder_Rxy_Ratio = sqrt(R_meridional / R_sagittal)``,
        which the ``conic__surf`` math scales the Y coordinate by
        before computing sag. For a pure plano-cylindrical lens
        (curved in one direction, flat in the other) this ratio is
        ``0``; for a true torus it's a positive number != 1; for a
        sphere it would be ``1`` (and the dispatcher prefers
        ``SphereFit`` in that case).
      * ``tilt_z`` = rotation of the meridional axis about the
        optical axis, so the cylindrical "line of power" lands on
        the body's actual orientation in world coords.
    """

    kind: str = "toroid"
    radius_meridional: float = 0.0    # primary radius (highest curvature)
    radius_sagittal: float = float("inf")
    rotation_z_deg: float = 0.0       # angle of meridional axis vs local +X
    vertex_world: tuple[float, float, float] = (0.0, 0.0, 0.0)
    signed_rc: float = 0.0            # signed meridional radius (KrakenOS Rc)
    cylinder_rxy_ratio: float = 0.0   # sqrt(R_meridional / R_sagittal); 0 = pure cyl
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


def _rotation_to_align_axis_with_z(axis: np.ndarray) -> np.ndarray:
    """Rotation matrix that maps ``axis`` onto world +Z.

    Used by ``fit_torus`` so the quadratic-sag fit is performed in a
    frame where the optical axis is +Z. Rodrigues formula; degenerate
    case (axis already parallel or anti-parallel to +Z) handled
    explicitly.
    """
    axis = np.asarray(axis, dtype=float).reshape(3)
    norm = float(np.linalg.norm(axis))
    if norm < 1e-12:
        return np.eye(3)
    axis = axis / norm
    z = np.array([0.0, 0.0, 1.0])
    cross = np.cross(axis, z)
    sin_angle = float(np.linalg.norm(cross))
    cos_angle = float(np.dot(axis, z))
    if sin_angle < 1e-12:
        if cos_angle > 0.0:
            return np.eye(3)
        # axis points exactly -Z: rotate 180 deg about +X.
        return np.array([[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, -1.0]])
    k = cross / sin_angle
    K = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + K * sin_angle + K @ K * (1.0 - cos_angle)


def fit_torus(
    points: np.ndarray,
    *,
    source_axis: tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> ToroidFit | None:
    """Least-squares fit of a toroidal/cylindrical sag surface.

    The model assumes the optical axis is ``source_axis`` and the
    surface is well approximated by the conic sag

        z = c · s² / (1 + sqrt(1 - (k+1) c² s²)),  s² = u² + (gamma · v)²

    with ``k = 0`` and ``(u, v)`` the principal-curvature axes of
    the face. For paraxial caps this reduces to

        z = u²/(2 R_meridional) + v²/(2 R_sagittal)

    so we fit a general quadratic ``z = a x² + b y² + c xy + d x +
    e y + f`` in the source-axis-aligned frame and diagonalise the
    Hessian to recover the two principal curvatures plus their
    rotation angle.

    Returns ``None`` when the points are degenerate, when both
    principal curvatures vanish (use ``fit_plane``), or when the
    surface is a saddle (positive × negative curvature — not a lens
    surface in any standard catalog).
    """
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 10 or pts.shape[1] < 3:
        return None
    if not np.all(np.isfinite(pts[:, :3])):
        return None
    axis = np.asarray(source_axis, dtype=float).reshape(3)
    if float(np.linalg.norm(axis)) < 1e-12:
        return None

    rotation = _rotation_to_align_axis_with_z(axis)
    rotated = pts[:, :3] @ rotation.T
    # Translate so the lateral (X/Y) centroid sits at the origin --
    # the quadratic fit's constant term f then represents the vertex
    # offset along Z (in the rotated frame).
    lateral_centroid = np.array([rotated[:, 0].mean(), rotated[:, 1].mean(), 0.0])
    rotated = rotated - lateral_centroid
    x = rotated[:, 0]
    y = rotated[:, 1]
    z = rotated[:, 2]
    basis = np.column_stack([x * x, y * y, x * y, x, y, np.ones_like(x)])
    try:
        coeffs, *_ = np.linalg.lstsq(basis, z, rcond=None)
    except Exception:
        return None
    a, b, cxy, d, e, f = (float(v) for v in coeffs)

    # z = a x² + b y² + cxy x y + linear + offset
    # After diagonalising the symmetric Hessian H/2 = [[a, cxy/2],[cxy/2, b]],
    # the principal curvatures are lambda_i (such that in the rotated
    # principal frame z ≈ lam_1 u² + lam_2 v²) and the principal axes
    # are the eigenvectors.
    H = np.array([[a, 0.5 * cxy], [0.5 * cxy, b]])
    try:
        eigvals, eigvecs = np.linalg.eigh(H)
    except Exception:
        return None
    # Order by |curvature| descending: largest curvature is the
    # meridional (most-curved) axis.
    order = np.argsort(np.abs(eigvals))[::-1]
    lam_m, lam_s = float(eigvals[order[0]]), float(eigvals[order[1]])
    if abs(lam_m) < 1e-12:
        # truly flat -- caller should use fit_plane.
        return None
    if lam_m * lam_s < -1e-9:
        # Saddle: not a lens surface. Bail.
        return None

    # In the principal frame z ≈ lam_m u² + lam_s v², so the
    # paraxial sag z = u² / (2R_m) + v² / (2R_s) gives
    #   R_m = 1 / (2 lam_m)
    #   R_s = 1 / (2 lam_s)  (infinite when lam_s == 0)
    radius_meridional = 1.0 / (2.0 * lam_m)
    if abs(lam_s) < 1e-9:
        radius_sagittal = float("inf")
        gamma = 0.0
    else:
        radius_sagittal = 1.0 / (2.0 * lam_s)
        ratio = radius_meridional / radius_sagittal
        if ratio < 0:
            return None
        gamma = float(np.sqrt(ratio))

    # Meridional axis direction in the rotated frame. The eigenvector
    # is an unsigned axis -- flipping its sign is the same axis -- so
    # normalise the rotation angle to (-90, +90] to avoid spurious
    # 180-deg flips.
    v_m = np.asarray(eigvecs[:, order[0]], dtype=float).reshape(2)
    rotation_z_rad = float(np.arctan2(v_m[1], v_m[0]))
    if rotation_z_rad > 0.5 * np.pi:
        rotation_z_rad -= np.pi
    elif rotation_z_rad <= -0.5 * np.pi:
        rotation_z_rad += np.pi

    # Predict and compute residual in the rotated frame.
    predicted = basis @ coeffs
    residual = float(np.std(z - predicted))

    # Recover the vertex's world position. In the rotated frame the
    # vertex sits at (0, 0, f) (the constant term of the quadratic);
    # undo the lateral shift and the alignment rotation.
    vertex_rotated = np.array([0.0, 0.0, f]) + lateral_centroid
    vertex_world = rotation.T @ vertex_rotated

    return ToroidFit(
        radius_meridional=float(radius_meridional),
        radius_sagittal=float(radius_sagittal),
        rotation_z_deg=float(np.degrees(rotation_z_rad)),
        vertex_world=tuple(float(v) for v in vertex_world),
        cylinder_rxy_ratio=float(gamma),
        residual_mm=float(residual),
    )


def fit_face(
    points: np.ndarray,
    *,
    source_axis: tuple[float, float, float] | None = None,
) -> SphereFit | PlaneFit | ToroidFit | None:
    """Pick sphere, plane, or torus based on residual.

    Sphere and plane fits are tried first. If both have large
    residuals (which happens when the face has DIFFERENT principal
    curvatures -- a cylindrical or toroidal lens), the torus fit
    runs to capture the two principal radii. We pick the model with
    the smallest residual, with two tie-break preferences:
      * prefer plane over sphere when both fit a flat face well
        (avoids spurious "Rc = 1e9" sphere fits on flat surfaces);
      * prefer sphere over torus when the torus's two principal
        radii are within 5 percent of each other (no real
        astigmatism, just numerical drift in the principal-axis
        diagonalisation).

    ``source_axis`` is the body's optical axis, used by ``fit_torus``
    to project points into the right sag frame. Defaults to ``+Z``
    (matching the legacy fit_sphere / fit_plane behaviour).
    """
    sphere = fit_sphere(points)
    plane = fit_plane(points)
    torus: ToroidFit | None = None
    # Only bother fitting a torus when both simpler models are
    # genuinely poor (residual > 0.05 mm) -- the torus fit is more
    # expensive and pulls in a 6-DOF quadratic where 2-4 DOF was
    # enough for a sphere or plane.
    needs_torus = True
    if sphere is not None and float(sphere.residual_mm) < 0.05:
        needs_torus = False
    if plane is not None and float(plane.residual_mm) < 0.05:
        needs_torus = False
    if needs_torus:
        axis_arg = (0.0, 0.0, 1.0) if source_axis is None else tuple(float(v) for v in source_axis)
        torus = fit_torus(points, source_axis=axis_arg)
    candidates: list[SphereFit | PlaneFit | ToroidFit] = []
    if sphere is not None:
        candidates.append(sphere)
    if plane is not None:
        candidates.append(plane)
    if torus is not None:
        candidates.append(torus)
    if not candidates:
        return None
    # Tie-break preferences.
    if sphere is not None and plane is not None:
        if sphere.residual_mm <= 1e-4 and plane.residual_mm <= 1e-4:
            # Both fit a flat face perfectly -> the sphere fit's huge
            # Rc is misleading; pick plane.
            candidates = [c for c in candidates if not isinstance(c, SphereFit)]
    if torus is not None and sphere is not None:
        # Torus that reduces to a sphere -> drop it in favour of sphere.
        if abs(torus.cylinder_rxy_ratio - 1.0) < 0.05 and sphere.residual_mm <= torus.residual_mm * 1.05:
            candidates = [c for c in candidates if not isinstance(c, ToroidFit)]
    return min(candidates, key=lambda c: float(getattr(c, "residual_mm", float("inf"))))


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


def _fit_from_analytic_parameters(
    face: dict[str, Any],
    points: np.ndarray,
    *,
    axis: np.ndarray,
) -> SphereFit | PlaneFit | ToroidFit | None:
    """Build a fit directly from OCC's preserved analytic parameters.

    The STEP importer (see ``step_overlay_face_metadata`` upstream)
    stores ``surface_type`` and ``analytic_parameters`` on each
    face when the underlying B-rep surface is one of the standard
    analytic kinds. For ``cylinder`` faces in particular this
    bypasses a tessellation-dependent mesh fit -- vendor STEPs
    often subdivide developable surfaces (cylinders, cones) only
    along the curved direction and leave the straight extrusion
    direction with two layers of triangles, which is too sparse to
    distinguish a cylinder from a sphere.

    Returns ``None`` when the face's analytic data is missing or
    when the surface type isn't one we model as a Standard row;
    the caller then falls back to the mesh-based fit_face.
    """
    if not isinstance(face, dict):
        return None
    surface_type = str(face.get("surface_type") or "").strip().lower()
    params = face.get("analytic_parameters") or {}
    if not surface_type:
        return None
    axis_arr = np.asarray(axis, dtype=float).reshape(3)
    axis_norm = float(np.linalg.norm(axis_arr))
    if axis_norm < 1e-9:
        return None
    axis_arr = axis_arr / axis_norm

    if surface_type == "cylinder":
        radius_mm = params.get("radius_mm")
        if radius_mm is None or float(radius_mm) <= 0:
            return None
        cyl_axis = np.asarray(params.get("axis_direction") or (0.0, 0.0, 1.0), dtype=float).reshape(3)
        cyl_norm = float(np.linalg.norm(cyl_axis))
        if cyl_norm < 1e-9:
            return None
        cyl_axis = cyl_axis / cyl_norm
        # The cylinder's central axis is perpendicular to the optical
        # axis for a plano-cylindrical optical face. Reject when the
        # cylinder axis is nearly parallel to the optical axis -- that
        # geometry is a "rim cylinder" (the side wall of a lens body),
        # not an optical surface.
        if abs(float(np.dot(cyl_axis, axis_arr))) > 0.5:
            return None
        # KrakenOS encodes plano-cylindrical surfaces as Standard rows
        # with Cylinder_Rxy_Ratio=0 and Rc=meridional radius. The
        # signed Rc follows the usual convention -- positive when the
        # centre of curvature sits on the +optical_axis side of the
        # vertex.
        centroid = np.asarray(face.get("centroid") or points.mean(axis=0), dtype=float).reshape(3)
        cyl_origin = np.asarray(params.get("axis_origin") or (0.0, 0.0, 0.0), dtype=float).reshape(3)
        # Project cyl_origin onto the plane perpendicular to cyl_axis
        # that contains the centroid: that gives the point on the
        # cylinder's central axis nearest the face centroid, i.e. the
        # centre of curvature of the meridional arc.
        offset_to_origin = cyl_origin - centroid
        center_of_curvature = centroid + offset_to_origin - cyl_axis * float(np.dot(offset_to_origin, cyl_axis))
        # Signed Rc: +R when centre is on +axis_arr side of vertex.
        sign = +1.0 if float(np.dot(center_of_curvature - centroid, axis_arr)) > 0.0 else -1.0
        signed_rc = sign * float(radius_mm)
        # Meridional axis direction within the local X-Y plane
        # (perpendicular to the optical axis). Computed by projecting
        # the cylinder axis onto the optical axis's perpendicular
        # plane, then rotating 90 deg about the optical axis -- the
        # meridional axis is perpendicular to the cylinder axis.
        perp_to_axis = cyl_axis - axis_arr * float(np.dot(cyl_axis, axis_arr))
        perp_norm = float(np.linalg.norm(perp_to_axis))
        if perp_norm < 1e-9:
            rotation_z_deg = 0.0
        else:
            sag_dir = perp_to_axis / perp_norm  # cyl extrusion within perp plane
            # Meridional direction is perpendicular to sag_dir within
            # the perp-to-axis plane. Build local X = world projection
            # of a global +X onto the perp plane to define "0 deg".
            ref = np.array([1.0, 0.0, 0.0])
            ref = ref - axis_arr * float(np.dot(ref, axis_arr))
            ref_norm = float(np.linalg.norm(ref))
            if ref_norm < 1e-9:
                ref = np.array([0.0, 1.0, 0.0])
                ref = ref - axis_arr * float(np.dot(ref, axis_arr))
                ref_norm = float(np.linalg.norm(ref))
            ref = ref / max(ref_norm, 1e-9)
            # Meridional axis is the cross product axis_arr x sag_dir
            # (perpendicular to both, lying in the perp plane).
            meridional = np.cross(axis_arr, sag_dir)
            mer_norm = float(np.linalg.norm(meridional))
            if mer_norm < 1e-9:
                rotation_z_deg = 0.0
            else:
                meridional = meridional / mer_norm
                cos_t = float(np.dot(meridional, ref))
                sin_t = float(np.dot(np.cross(ref, meridional), axis_arr))
                rotation_z_deg = float(np.degrees(np.arctan2(sin_t, cos_t)))
                if rotation_z_deg > 90.0:
                    rotation_z_deg -= 180.0
                elif rotation_z_deg <= -90.0:
                    rotation_z_deg += 180.0
        return ToroidFit(
            radius_meridional=float(radius_mm) * sign,
            radius_sagittal=float("inf"),
            rotation_z_deg=rotation_z_deg,
            vertex_world=tuple(float(v) for v in centroid),
            signed_rc=signed_rc,
            cylinder_rxy_ratio=0.0,
            residual_mm=0.0,
        )
    # plane_exact / sphere_exact: let mesh fit handle them -- their
    # analytic_parameters don't include the numeric quantities
    # (radius, plane offset) we'd need.
    return None


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
        # Fast-path: if the STEP importer preserved an analytic
        # surface type (sphere_exact, cylinder, plane_exact, ...)
        # with numeric parameters, build the fit from those instead
        # of mesh-fitting. Vendor STEP files often tessellate curved
        # faces sparsely -- e.g. the Edmund 34754 plano-cylindrical
        # has only 4 unique Z values on a 25 mm-long face, so the
        # mesh fit incorrectly picks a sphere that interpolates the
        # two edge arcs. The analytic parameters from OCC are exact.
        analytic_fit = _fit_from_analytic_parameters(
            face, pts, axis=axis,
        )
        if analytic_fit is not None:
            fit = analytic_fit
        else:
            fit = fit_face(pts, source_axis=tuple(float(v) for v in axis))
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
