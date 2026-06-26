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


# The true best-focus sag of a corrected lens is tiny (often << 1% of the image
# radius) -- edge-on it reads as a flat line. Auto-exaggerate the axial deviation so
# the bowl is visible, targeting a peak sag of this fraction of the rim radius, and
# report the magnification so the surface is honest (the gap is NOT the literal
# defocus once exaggerated). The factor is clamped to [1, cap].
BEST_FOCUS_SAG_TARGET_FRACTION = 0.12
BEST_FOCUS_EXAGGERATION_CAP = 5000.0


def build_best_focus_surface(
    image_heights,
    focus_tangential,
    focus_sagittal,
    *,
    center,
    normal,
    tangent,
    n_az: int = BEST_FOCUS_SURFACE_AZIMUTHS,
    exaggeration: "float | None" = None,
    color=BEST_FOCUS_SURFACE_COLOR,
    opacity: float = BEST_FOCUS_SURFACE_OPACITY,
) -> "dict | None":
    """Loft the medial best-focus surface as a grid of revolved rings.

    ``image_heights`` are the real chief-ray image heights per field (mm) -- the
    radial position where each field actually lands on the detector, so the rim ring
    sits on the real image circle (NOT the lens clear-aperture diameter).
    ``focus_tangential`` / ``focus_sagittal`` are the on-axis-referenced longitudinal
    best-focus offsets (mm) at each field (the Y/X ``focus`` arrays from
    ``_sample_field_curvature_distortion``); the medial surface is their mean.

    The axial sag is auto-exaggerated (``exaggeration=None``) so the curvature reads
    edge-on; ``ring_dz`` keeps the TRUE medial offsets while ``points`` use the
    exaggerated sag, and the returned ``exaggeration`` / ``true_max_sag_mm`` let the
    overlay label the magnification.

    Returns None when the inputs cannot make a surface (too few fields, zero image
    radius, non-finite focus).
    """
    image_heights = np.asarray(image_heights, dtype=float).reshape(-1)
    focus_t = np.asarray(focus_tangential, dtype=float).reshape(-1)
    focus_s = np.asarray(focus_sagittal, dtype=float).reshape(-1)
    n_rings = int(image_heights.size)
    if n_rings < 2 or focus_t.size != n_rings or focus_s.size != n_rings:
        return None
    ring_radii = np.abs(image_heights)
    rim = float(np.max(ring_radii)) if ring_radii.size else 0.0
    if not np.isfinite(rim) or rim <= 1e-6:
        return None
    n_az = int(n_az)
    if n_az < 8:
        n_az = 8

    medial = 0.5 * (focus_t + focus_s)
    if not np.all(np.isfinite(medial)):
        return None
    true_max_sag = float(np.max(np.abs(medial)))

    if exaggeration is None:
        target_sag = BEST_FOCUS_SAG_TARGET_FRACTION * rim
        factor = (target_sag / true_max_sag) if true_max_sag > 1e-9 else 1.0
        factor = float(min(max(factor, 1.0), BEST_FOCUS_EXAGGERATION_CAP))
    else:
        factor = float(exaggeration)
        if not np.isfinite(factor) or factor <= 0.0:
            factor = 1.0
    display_dz = medial * factor

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
            + display_dz[i] * n_hat[None, :]
        )
        rings.append(ring)
    points = np.concatenate(rings, axis=0)

    return {
        "kind": "best_focus_surface",
        "points": points,
        "n_rings": n_rings,
        "n_az": n_az,
        "ring_radii": ring_radii,
        "ring_dz": medial,           # TRUE medial offsets (mm), on-axis referenced
        "display_dz": display_dz,    # exaggerated offsets actually drawn
        "radius": rim,               # rim = max real image height (the image circle)
        "exaggeration": float(factor),
        "true_max_sag_mm": true_max_sag,
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
