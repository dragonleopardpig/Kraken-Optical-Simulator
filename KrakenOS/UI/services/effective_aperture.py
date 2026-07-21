"""General effective-aperture engine for the illumination path (bugs/0380).

The question "what limits the beam, and where do the dark edges come from" is a property
of ALL apertures on the path, not any one element. The non-sequential trace structurally
will not clip folded illumination (a split-branch ray never consults a downstream limiting
aperture -- bugs/0287/0289), which is exactly why the coaxial heatmap fell back to a
hard-coded synthetic. This module answers it GEOMETRICALLY instead:

  inventory every aperture (as a convex shape at a plane)
    -> project each onto a common reference plane along the beam (unfolding any folds)
    -> INTERSECT them
    -> the effective footprint, with each boundary edge attributed to the aperture that
       limits it (a "who clips" diagnostic).

General: the limiting edge can be the LED opening, the beam-splitter, the lens stop, a
mount, or a user-picked clear aperture -- and the engine reports which. Reduces to the old
foreshortened-LED answer when the LED is in fact the limiter, but no longer assumes it.

Pure + display-free (numpy only), so it is unit-testable without VTK.

v1 projection model: ORTHOGRAPHIC along the reference-plane normal, after unfolding each
aperture across the fold plane(s) between it and the reference. Foreshortening for a
tilted aperture is inherent (a 45deg-tilted aperture projects to cos45 of its extent).
Source-distance magnification and penumbra softening are documented refinements, not v1.
"""

from __future__ import annotations

import numpy as np

_EPS = 1e-9


# --------------------------------------------------------------------------- shapes
def rect_boundary(center, u_axis, v_axis, half_u, half_v) -> np.ndarray:
    """The four world corners of a rectangle (CCW in its own u,v frame)."""
    c = np.asarray(center, dtype=float).reshape(3)
    u = np.asarray(u_axis, dtype=float).reshape(3)
    v = np.asarray(v_axis, dtype=float).reshape(3)
    return np.array(
        [c - half_u * u - half_v * v, c + half_u * u - half_v * v,
         c + half_u * u + half_v * v, c - half_u * u + half_v * v],
        dtype=float,
    )


def circle_boundary(center, u_axis, v_axis, radius, n: int = 64) -> np.ndarray:
    """``n`` world points on a circle (a discretised convex aperture)."""
    c = np.asarray(center, dtype=float).reshape(3)
    u = np.asarray(u_axis, dtype=float).reshape(3)
    v = np.asarray(v_axis, dtype=float).reshape(3)
    ang = np.linspace(0.0, 2.0 * np.pi, int(max(8, n)), endpoint=False)
    return np.array([c + radius * (np.cos(a) * u + np.sin(a) * v) for a in ang], dtype=float)


# --------------------------------------------------------------------------- geometry
def reflect_points_across_plane(points, plane_point, plane_normal) -> np.ndarray:
    """Mirror ``points`` across the plane (unfold a fold: a mirror image is an isometry)."""
    p = np.asarray(points, dtype=float).reshape(-1, 3)
    o = np.asarray(plane_point, dtype=float).reshape(3)
    n = np.asarray(plane_normal, dtype=float).reshape(3)
    nn = float(np.linalg.norm(n))
    if nn < _EPS:
        return p.copy()
    n = n / nn
    d = (p - o) @ n
    return p - 2.0 * np.outer(d, n)


def project_onto_plane_2d(points_world, plane_center, plane_normal, u_axis, v_axis) -> np.ndarray:
    """Orthographic projection of world points onto the plane; return (u, v) coords."""
    p = np.asarray(points_world, dtype=float).reshape(-1, 3)
    c = np.asarray(plane_center, dtype=float).reshape(3)
    u = np.asarray(u_axis, dtype=float).reshape(3)
    v = np.asarray(v_axis, dtype=float).reshape(3)
    u = u / max(float(np.linalg.norm(u)), _EPS)
    v = v / max(float(np.linalg.norm(v)), _EPS)
    rel = p - c
    return np.column_stack([rel @ u, rel @ v])


def _signed_area(poly: np.ndarray) -> float:
    x, y = poly[:, 0], poly[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _as_ccw(poly: np.ndarray) -> np.ndarray:
    return poly if _signed_area(poly) >= 0.0 else poly[::-1].copy()


def clip_convex(subject_uv: np.ndarray, clip_uv: np.ndarray) -> np.ndarray:
    """Sutherland-Hodgman: clip convex ``subject`` by convex ``clip`` (both 2-D).

    Returns the intersection polygon (CCW), or an empty (0, 2) array if disjoint."""
    subject = _as_ccw(np.asarray(subject_uv, dtype=float).reshape(-1, 2))
    clip = _as_ccw(np.asarray(clip_uv, dtype=float).reshape(-1, 2))
    if subject.shape[0] < 3 or clip.shape[0] < 3:
        return np.empty((0, 2), dtype=float)
    output = subject
    for i in range(clip.shape[0]):
        a = clip[i]
        b = clip[(i + 1) % clip.shape[0]]
        edge = b - a
        if output.shape[0] == 0:
            break
        inp = output
        output = []

        def _inside(pt):
            return edge[0] * (pt[1] - a[1]) - edge[1] * (pt[0] - a[0]) >= -_EPS

        def _intersect(p0, p1):
            d = p1 - p0
            denom = edge[0] * d[1] - edge[1] * d[0]
            if abs(denom) < _EPS:
                return p1
            t = (edge[0] * (p0[1] - a[1]) - edge[1] * (p0[0] - a[0])) / -denom
            return p0 + t * d

        m = inp.shape[0]
        for j in range(m):
            cur = inp[j]
            prv = inp[(j - 1) % m]
            cur_in = _inside(cur)
            prv_in = _inside(prv)
            if cur_in:
                if not prv_in:
                    output.append(_intersect(prv, cur))
                output.append(cur)
            elif prv_in:
                output.append(_intersect(prv, cur))
        output = np.asarray(output, dtype=float).reshape(-1, 2) if output else np.empty((0, 2), float)
    return output


def _dedupe(poly: np.ndarray, tol: float = 1e-6) -> np.ndarray:
    if poly.shape[0] == 0:
        return poly
    keep = [poly[0]]
    for pt in poly[1:]:
        if np.linalg.norm(pt - keep[-1]) > tol:
            keep.append(pt)
    if len(keep) > 1 and np.linalg.norm(keep[0] - keep[-1]) <= tol:
        keep.pop()
    return np.asarray(keep, dtype=float)


# ----------------------------------------------------------------- attribution + engine
def _point_on_segment(pt, s0, s1, tol: float) -> bool:
    d = s1 - s0
    L = float(np.linalg.norm(d))
    if L < tol:
        return float(np.linalg.norm(pt - s0)) <= tol
    t = float(np.dot(pt - s0, d) / (L * L))
    if t < -tol / L or t > 1.0 + tol / L:
        return False
    perp = float(np.linalg.norm((pt - s0) - t * d))
    return perp <= tol


def _edge_on_polygon(p0, p1, poly: np.ndarray, tol: float) -> bool:
    """Is segment p0->p1 a sub-segment of one of ``poly``'s edges?"""
    m = poly.shape[0]
    for i in range(m):
        s0, s1 = poly[i], poly[(i + 1) % m]
        if _point_on_segment(p0, s0, s1, tol) and _point_on_segment(p1, s0, s1, tol):
            return True
    return False


def effective_footprint(apertures, object_frame, fold_planes=(), *, attribution_tol: float = 0.05) -> dict | None:
    """Intersect all apertures projected onto the reference plane; attribute each edge.

    ``apertures``: list of ``{"label": str, "boundary": (N,3) world points, "normal": (3,)}``.
    ``object_frame``: ``(center(3), normal(3), u_axis(3), v_axis(3))`` -- the reference
    plane and its in-plane axes (u along the fold axis, v perpendicular, by convention).
    ``fold_planes``: list of ``(point(3), normal(3))``; an aperture on the far side of a
    fold from the reference is reflected across it (unfolded) before projection.

    Returns ``{footprint_uv, bbox_uv, edge_labels, limiting_labels, per_aperture_uv}``, or
    None when the inventory is empty / the intersection is degenerate (nothing limits)."""
    if not apertures:
        return None
    center, normal, u_axis, v_axis = (np.asarray(a, dtype=float).reshape(3) for a in object_frame)

    projected: list[tuple[str, np.ndarray]] = []
    for ap in apertures:
        boundary = np.asarray(ap.get("boundary"), dtype=float).reshape(-1, 3)
        if boundary.shape[0] < 3:
            continue
        pts = boundary
        # Unfold across any fold plane that separates this aperture from the reference.
        for fp_pt, fp_n in fold_planes or ():
            fp_pt = np.asarray(fp_pt, dtype=float).reshape(3)
            fp_n = np.asarray(fp_n, dtype=float).reshape(3)
            ap_side = np.sign(np.dot(pts.mean(axis=0) - fp_pt, fp_n))
            ref_side = np.sign(np.dot(center - fp_pt, fp_n))
            if ap_side != 0 and ref_side != 0 and ap_side != ref_side:
                pts = reflect_points_across_plane(pts, fp_pt, fp_n)
        uv = _dedupe(project_onto_plane_2d(pts, center, normal, u_axis, v_axis))
        if uv.shape[0] >= 3:
            projected.append((str(ap.get("label", "?")), _as_ccw(uv)))
    if not projected:
        return None

    foot = projected[0][1]
    for _label, poly in projected[1:]:
        foot = _dedupe(clip_convex(foot, poly))
        if foot.shape[0] < 3:
            return {
                "footprint_uv": np.empty((0, 2), float), "bbox_uv": None,
                "edge_labels": [], "limiting_labels": sorted({l for l, _ in projected}),
                "per_aperture_uv": {l: p for l, p in projected}, "empty": True,
            }
    foot = _dedupe(foot)
    if foot.shape[0] < 3:
        return None

    # Attribute each footprint edge to the aperture(s) whose boundary it lies on.
    m = foot.shape[0]
    edge_labels: list[list[str]] = []
    for i in range(m):
        p0, p1 = foot[i], foot[(i + 1) % m]
        here = [label for label, poly in projected if _edge_on_polygon(p0, p1, poly, attribution_tol)]
        edge_labels.append(here or ["?"])
    limiting = sorted({l for labs in edge_labels for l in labs if l != "?"})
    bbox = np.array([[foot[:, 0].min(), foot[:, 1].min()], [foot[:, 0].max(), foot[:, 1].max()]])
    return {
        "footprint_uv": foot,
        "bbox_uv": bbox,
        "edge_labels": edge_labels,
        "limiting_labels": limiting,
        "per_aperture_uv": {l: p for l, p in projected},
        "empty": False,
    }
