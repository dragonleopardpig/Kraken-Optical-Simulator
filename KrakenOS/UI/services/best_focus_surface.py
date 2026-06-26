"""Curved best-focus surface geometry (3D field-curvature visualization, idea #2).

The real best-focus surface of a lens is CURVED (Petzval / field curvature); the
detector is flat. This module lofts the per-field best-focus offsets (the tangential
and sagittal foci that the 2D Field Curvature analysis already computes, referenced
to the on-axis focus) into a surface of revolution sitting at the image plane, so the
field curvature -- and the field-dependent gap to the flat detector -- reads in 3D.

Pure geometry only (numpy), so it is unit-testable without an editor or VTK. The
editor wrapper feeds it the field-curvature scan + the image-plane frame; the Open 3D
inspector turns the returned point grid + faces into a translucent VTK actor.

The returned spec is a surface-of-revolution grid: ``n_rings`` concentric rings of
``n_az`` points each (ring 0 = the on-axis apex), row-major (ring-major) so point
(ring i, azimuth j) is at index ``i * n_az + j``.
"""

from __future__ import annotations

import numpy as np

# Cyan, translucent -- distinct from the orange detector footprint it floats over.
BEST_FOCUS_SURFACE_COLOR = (0.30, 0.85, 0.95)
BEST_FOCUS_SURFACE_OPACITY = 0.22
BEST_FOCUS_SURFACE_AZIMUTHS = 48


def _unit(vector, fallback=None) -> np.ndarray:
    vec = np.asarray(vector, dtype=float).reshape(3)
    norm = float(np.linalg.norm(vec))
    if norm < 1e-12:
        if fallback is not None:
            return np.asarray(fallback, dtype=float).reshape(3)
        return np.array([0.0, 0.0, 1.0])
    return vec / norm


def _any_perpendicular(n_hat: np.ndarray) -> np.ndarray:
    seed = np.array([1.0, 0.0, 0.0]) if abs(float(n_hat[0])) < 0.9 else np.array([0.0, 1.0, 0.0])
    return _unit(np.cross(n_hat, seed))


def build_best_focus_surface(
    fields,
    focus_tangential,
    focus_sagittal,
    field_limit: float,
    *,
    center,
    normal,
    tangent,
    radius: float,
    n_az: int = BEST_FOCUS_SURFACE_AZIMUTHS,
    color=BEST_FOCUS_SURFACE_COLOR,
    opacity: float = BEST_FOCUS_SURFACE_OPACITY,
) -> "dict | None":
    """Loft the medial best-focus surface as a grid of revolved rings.

    ``fields`` are the absolute field samples ``[0 .. field_limit]``;
    ``focus_tangential`` / ``focus_sagittal`` are the on-axis-referenced longitudinal
    best-focus offsets (mm) at each field (the Y/X ``focus`` arrays from
    ``_sample_field_curvature_distortion``). The medial surface is their mean. The
    in-plane radius of ring i maps the field linearly onto the image-plane radius so
    the rim ring (``field_limit``) sits at ``radius`` (the detector / image edge).

    Returns the surface spec dict, or None when the inputs cannot make a surface
    (too few fields, zero field span, zero radius, non-finite focus).
    """
    fields = np.asarray(fields, dtype=float).reshape(-1)
    focus_t = np.asarray(focus_tangential, dtype=float).reshape(-1)
    focus_s = np.asarray(focus_sagittal, dtype=float).reshape(-1)
    n_rings = int(fields.size)
    if n_rings < 2 or focus_t.size != n_rings or focus_s.size != n_rings:
        return None
    if not np.isfinite(field_limit) or float(field_limit) <= 1e-9:
        return None
    if not np.isfinite(radius) or float(radius) <= 1e-6:
        return None
    n_az = int(n_az)
    if n_az < 8:
        n_az = 8

    medial = 0.5 * (focus_t + focus_s)
    if not np.all(np.isfinite(medial)):
        return None
    ring_radii = (np.abs(fields) / float(field_limit)) * float(radius)

    center = np.asarray(center, dtype=float).reshape(3)
    n_hat = _unit(normal)
    tangent_vec = np.asarray(tangent, dtype=float).reshape(3)
    u = _unit(tangent_vec - n_hat * float(np.dot(tangent_vec, n_hat)), fallback=_any_perpendicular(n_hat))
    v = _unit(np.cross(n_hat, u))

    thetas = np.linspace(0.0, 2.0 * np.pi, n_az, endpoint=False)
    cos_t = np.cos(thetas)
    sin_t = np.sin(thetas)
    rings = []
    for i in range(n_rings):
        ring = (
            center[None, :]
            + ring_radii[i] * (np.outer(cos_t, u) + np.outer(sin_t, v))
            + medial[i] * n_hat[None, :]
        )
        rings.append(ring)
    points = np.concatenate(rings, axis=0)

    return {
        "kind": "best_focus_surface",
        "points": points,
        "n_rings": n_rings,
        "n_az": n_az,
        "ring_radii": ring_radii,
        "ring_dz": medial,
        "center": center,
        "normal": n_hat,
        "color": tuple(float(c) for c in color),
        "opacity": float(opacity),
    }


def best_focus_surface_faces(n_rings: int, n_az: int) -> np.ndarray:
    """VTK/pyvista quad faces (``[4, p0, p1, p2, p3, ...]``) for the ring grid.

    Quads wrap in azimuth (j -> j+1 mod n_az) and span consecutive rings. The apex
    ring (radius 0) yields degenerate quads VTK renders harmlessly.
    """
    n_rings = int(n_rings)
    n_az = int(n_az)
    faces: list[int] = []
    for i in range(n_rings - 1):
        for j in range(n_az):
            j2 = (j + 1) % n_az
            p0 = i * n_az + j
            p1 = i * n_az + j2
            p2 = (i + 1) * n_az + j2
            p3 = (i + 1) * n_az + j
            faces.extend((4, p0, p1, p2, p3))
    return np.asarray(faces, dtype=np.int64)


def best_focus_surface_ring_polylines(spec: "dict") -> "list[np.ndarray]":
    """Closed latitude-ring polylines (for drawing edge lines over the translucent
    fill so the bowl shape reads). One polyline per non-degenerate ring."""
    points = np.asarray(spec.get("points"), dtype=float)
    n_rings = int(spec.get("n_rings", 0))
    n_az = int(spec.get("n_az", 0))
    ring_radii = np.asarray(spec.get("ring_radii", []), dtype=float)
    out: list[np.ndarray] = []
    if points.size == 0 or n_rings <= 0 or n_az <= 0:
        return out
    for i in range(n_rings):
        if i < ring_radii.size and float(ring_radii[i]) <= 1e-6:
            continue  # apex ring is a point
        ring = points[i * n_az:(i + 1) * n_az]
        if ring.shape[0] < 3:
            continue
        out.append(np.vstack([ring, ring[0]]))  # close the loop
    return out
