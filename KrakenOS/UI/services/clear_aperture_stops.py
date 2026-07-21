"""User-specified physical clear-aperture (CA) stops built from picked edges (bugs/0379).

A mechanical STEP overlay (LED coaxial illuminator, camera housing, a mount) carries
real Clear-Aperture openings that the ray trace ignores because the STEP is display
decoration. This module turns a set of PICKED EDGES into a rectangular aperture *at its
true 3-D location* -- the edges' shared plane is the stop plane, and the bounding box of
the edges in that plane is the opening -- and vignettes illumination rays that miss it.

Why edges, not a numeric size: the aperture's LOCATION along the light path matters (it is
a stop at a specific plane), and picking the geometry captures both the size AND the plane.
A closed window loop, three sides of an open opening, or two opposite mount edges all work:
the rectangle is whatever encloses the picked edges in their common plane.

Pure + display-free (numpy only), so it is unit-testable without VTK.
"""

from __future__ import annotations

import numpy as np


def rect_from_edges(edge_point_arrays) -> dict | None:
    """Build a rectangular CA spec from one or more picked edges.

    ``edge_point_arrays``: an iterable of (N_i, 3) point arrays (each a picked edge
    polyline -- a closed loop, or 3 sides, or 2 opposite sides).

    Returns ``{center, normal, u_axis, v_axis, half_u, half_v}`` (all lists / floats) --
    a rectangle centred at ``center``, spanning ``±half_u`` along ``u_axis`` and ``±half_v``
    along ``v_axis``, lying in the plane through ``center`` with the given ``normal``. The
    rectangle is the axis-aligned (in-plane) bounding box of ALL picked points, so 3 edges
    of a rectangle recover the full opening (the 4th side is the box closing itself) and 2
    opposite edges span it. Returns ``None`` for degenerate input (< 3 non-collinear points).
    """
    pts = []
    for arr in edge_point_arrays or []:
        a = np.asarray(arr, dtype=float)
        if a.ndim == 2 and a.shape[0] >= 1 and a.shape[1] >= 3:
            pts.append(a[:, :3])
    if not pts:
        return None
    points = np.concatenate(pts, axis=0)
    if points.shape[0] < 3 or not np.all(np.isfinite(points)):
        return None
    center = points.mean(axis=0)
    centered = points - center
    # Plane normal = the least-variance direction (SVD); the two in-plane axes are the
    # principal spread directions, so u/v align with the opening's own rectangle even when
    # it is tilted in world space.
    try:
        _u, _s, vt = np.linalg.svd(centered, full_matrices=False)
    except Exception:
        return None
    if vt.shape[0] < 3:
        return None
    u_axis = vt[0] / max(float(np.linalg.norm(vt[0])), 1e-12)
    v_axis = vt[1] / max(float(np.linalg.norm(vt[1])), 1e-12)
    normal = np.cross(u_axis, v_axis)
    nn = float(np.linalg.norm(normal))
    if nn < 1e-9:
        return None
    normal = normal / nn
    u = centered @ u_axis
    v = centered @ v_axis
    u_lo, u_hi = float(u.min()), float(u.max())
    v_lo, v_hi = float(v.min()), float(v.max())
    half_u = 0.5 * (u_hi - u_lo)
    half_v = 0.5 * (v_hi - v_lo)
    if half_u < 1e-6 or half_v < 1e-6:
        return None
    # Re-centre onto the bounding-box centre (the picked-point centroid is not the box
    # centre for a 3-sided/2-edge pick).
    box_center = center + (0.5 * (u_lo + u_hi)) * u_axis + (0.5 * (v_lo + v_hi)) * v_axis
    return {
        "center": [float(c) for c in box_center],
        "normal": [float(c) for c in normal],
        "u_axis": [float(c) for c in u_axis],
        "v_axis": [float(c) for c in v_axis],
        "half_u": half_u,
        "half_v": half_v,
    }


def _segment_hits_rect(p0, p1, ca) -> bool | None:
    """Does segment p0->p1 cross the CA plane INSIDE the rectangle?

    Returns True (passes the opening), False (crosses the plane outside the opening ->
    blocked), or None (segment does not reach the plane / is parallel -> not decided here).
    """
    center = np.asarray(ca["center"], dtype=float)
    normal = np.asarray(ca["normal"], dtype=float)
    d = p1 - p0
    denom = float(np.dot(d, normal))
    if abs(denom) < 1e-12:
        return None  # parallel to the plane
    t = float(np.dot(center - p0, normal) / denom)
    if t < -1e-9 or t > 1.0 + 1e-9:
        return None  # plane crossing not within this segment
    hit = p0 + t * d
    rel = hit - center
    u = float(np.dot(rel, np.asarray(ca["u_axis"], dtype=float)))
    v = float(np.dot(rel, np.asarray(ca["v_axis"], dtype=float)))
    return abs(u) <= ca["half_u"] + 1e-6 and abs(v) <= ca["half_v"] + 1e-6


def ray_passes_apertures(polyline, cas) -> bool:
    """A ray (its traced world polyline) passes iff, at EVERY CA plane its path crosses,
    the crossing is inside that CA's opening. A ray whose path never reaches a CA plane is
    not blocked by it (the aperture is elsewhere)."""
    p = np.asarray(polyline, dtype=float)
    if p.ndim != 2 or p.shape[0] < 2:
        return True
    for ca in cas or []:
        blocked = False
        for i in range(p.shape[0] - 1):
            hit = _segment_hits_rect(p[i], p[i + 1], ca)
            if hit is False:
                blocked = True
                break
            if hit is True:
                blocked = False
                break  # decided for this CA; move to the next
        if blocked:
            return False
    return True


def filter_illumination_records(records, cas) -> list:
    """Keep only illumination ray records whose traced polyline passes ALL CA openings
    (bugs/0379). A record with no traced polyline is kept (nothing to test)."""
    if not cas:
        return list(records or [])
    kept = []
    for rec in records or []:
        poly = rec.get("traced_polyline_world") if isinstance(rec, dict) else None
        if poly is None or ray_passes_apertures(poly, cas):
            kept.append(rec)
    return kept
