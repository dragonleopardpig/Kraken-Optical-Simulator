"""Spot RMS field map geometry (3D spot-quality visualization, idea #1/#3 foundation).

Trace the geometric spot at a grid of field points and draw, at each field's true
landing position on the detector, a circle whose radius is the (magnified) RMS spot
radius, coloured good->bad. The map shows how spot quality varies across the sensor in
3D -- the non-interactive precursor to the clickable detector-pixel -> PSF zoom.

Pure geometry only (numpy): the editor wrapper traces the spots and hands this module
``(chief_u, chief_v, rms)`` per field; the inspector renders the returned circles.
"""

from __future__ import annotations

import numpy as np

SPOT_FIELD_MAP_CIRCLE_SEGMENTS = 28
SPOT_FIELD_MAP_TARGET_FRACTION = 0.10  # peak circle radius as a fraction of the image radius
SPOT_FIELD_MAP_MAG_CAP = 1.0e6
SPOT_GOOD_COLOR = (0.15, 0.70, 0.25)  # small RMS
SPOT_BAD_COLOR = (0.90, 0.18, 0.12)   # large RMS


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


def _rms_color(t: float):
    t = float(min(max(t, 0.0), 1.0))
    good = np.asarray(SPOT_GOOD_COLOR, dtype=float)
    bad = np.asarray(SPOT_BAD_COLOR, dtype=float)
    mix = good + (bad - good) * t
    return tuple(float(c) for c in mix)


def build_spot_field_map(
    chief_u,
    chief_v,
    rms,
    *,
    center,
    normal,
    tangent,
    image_radius=None,
    magnification: "float | None" = None,
    n_circle: int = SPOT_FIELD_MAP_CIRCLE_SEGMENTS,
) -> "dict | None":
    """Build per-field RMS circles on the detector.

    ``chief_u`` / ``chief_v`` are each field's chief-ray (centroid) image-plane
    coordinates (mm); ``rms`` the geometric RMS spot radius there (mm). Each field gets a
    closed circle at ``center + cu*u + cv*v`` of radius ``rms * magnification`` (auto so
    the worst spot is a visible fraction of the image radius), coloured green (small) ->
    red (large). Returns None when there is nothing to show (no spots / a perfect lens).
    """
    chief_u = np.asarray(chief_u, dtype=float).reshape(-1)
    chief_v = np.asarray(chief_v, dtype=float).reshape(-1)
    rms = np.asarray(rms, dtype=float).reshape(-1)
    n = int(chief_u.size)
    if n < 2 or chief_v.size != n or rms.size != n:
        return None
    if not (np.all(np.isfinite(chief_u)) and np.all(np.isfinite(chief_v)) and np.all(np.isfinite(rms))):
        return None
    max_rms = float(np.max(rms))
    if max_rms <= 1e-12:
        return None  # diffraction-limited point lens -- no geometric spot to draw

    if image_radius is not None and float(image_radius) > 1e-6:
        radius_ref = float(image_radius)
    else:
        radius_ref = float(np.max(np.hypot(chief_u, chief_v)))
    if radius_ref <= 1e-6:
        radius_ref = 1.0

    if magnification is None:
        factor = (SPOT_FIELD_MAP_TARGET_FRACTION * radius_ref) / max_rms
        factor = float(min(max(factor, 1.0), SPOT_FIELD_MAP_MAG_CAP))
    else:
        factor = float(magnification)
        if not np.isfinite(factor) or factor <= 0.0:
            factor = 1.0

    center = np.asarray(center, dtype=float).reshape(3)
    n_hat = _unit(normal)
    tangent_vec = np.asarray(tangent, dtype=float).reshape(3)
    u = _unit(tangent_vec - n_hat * float(np.dot(tangent_vec, n_hat)), fallback=_any_perpendicular(n_hat))
    v = _unit(np.cross(n_hat, u))

    n_circle = max(int(n_circle), 6)
    thetas = np.linspace(0.0, 2.0 * np.pi, n_circle, endpoint=False)
    unit_ring = np.stack([np.cos(thetas), np.sin(thetas)], axis=1)  # (n_circle, 2)

    rms_min = float(np.min(rms))
    rms_span = max(max_rms - rms_min, 1e-12)
    circles: list[np.ndarray] = []
    colors: list[tuple] = []
    for i in range(n):
        radius = float(rms[i]) * factor
        ring2d = np.array([chief_u[i], chief_v[i]])[None, :] + radius * unit_ring
        world = center[None, :] + ring2d[:, 0:1] * u[None, :] + ring2d[:, 1:2] * v[None, :]
        circles.append(np.vstack([world, world[0]]))  # close the loop
        colors.append(_rms_color((float(rms[i]) - rms_min) / rms_span))

    return {
        "kind": "spot_field_map",
        "circles": circles,
        "colors": colors,
        "magnification": float(factor),
        "rms_min_mm": rms_min,
        "rms_max_mm": max_rms,
        "n_spots": n,
        "center": center,
        "normal": n_hat,
    }
