"""Camera pixel-grid overlay geometry (idea #1: the spot footprint on real pixels).

When a vendor camera is registered on the detector it carries a pixel pitch (e.g. the SVS
/ Allied-Vision 25 MP is 5120x5120 @ 4.50 um). This module draws ONE uniform pixel lattice
across the sensor -- every cell is a true pixel (4.5 um) -- so the user sees the camera's
real, even pixel grid with the spots landing on it (how many pixels the blur spans).

The lattice is uniform: lines fall on real pixel boundaries k*pitch from the sensor centre,
magnified about the sensor centre by the SAME factor the spot map uses, so the spot/pixel
size RATIO is exact even though a 4.5 um pixel could never be seen at the sensor's true
23 mm scale. (It was once built per-spot -- a magnified patch about each chief -- which made
the cells overlap at different offsets; a camera sensor's pixels are uniform, so it is now
a single even grid clipped to the orange detector frame.)

Pure geometry only (numpy): the editor wrapper supplies the spot chief positions + true
extents (from the spot-map trace, used only for the span-in-pixels label) and the camera
pitch + sensor box; the inspector renders the returned line set.
"""

from __future__ import annotations

import numpy as np

PIXEL_GRID_MAX_CELLS = 80      # per-axis line cap (a pathological tiny pitch / low mag backstop)
PIXEL_GRID_LINE_COLOR = (0.42, 0.47, 0.55)


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


def build_pixel_grid_overlay(
    chief_uv,
    spot_extent_mm,
    *,
    center,
    normal,
    tangent,
    pitch_mm,
    magnification,
    image_radius=None,
    sensor_half_uv=None,
    max_cells: int = PIXEL_GRID_MAX_CELLS,
) -> "dict | None":
    """Build ONE uniform pixel-lattice line set across the detector.

    ``chief_uv`` (N,2) are the spot chief positions (mm, image-plane local); ``spot_extent_mm``
    (N,) their true (un-magnified) radii (used only for the span-in-pixels label); ``pitch_mm``
    the ``(px, py)`` true pixel pitch; ``magnification`` the spot-map factor. The lattice is a
    single even grid -- lines on real pixel boundaries ``k*pitch`` magnified about the sensor
    centre by ``factor`` (so cell size == ``pitch*factor``) -- clipped to ``sensor_half_uv`` (the
    orange detector frame). Returns the line set + the spots' span in pixels, or None when there
    is nothing/no pitch.
    """
    chief_uv = np.asarray(chief_uv, dtype=float).reshape(-1, 2)
    spot_extent_mm = np.asarray(spot_extent_mm, dtype=float).reshape(-1)
    n = int(chief_uv.shape[0])
    if n < 1 or spot_extent_mm.size != n:
        return None
    try:
        px = float(pitch_mm[0])
        py = float(pitch_mm[1])
    except (TypeError, ValueError, IndexError):
        return None
    if not (px > 0.0 and py > 0.0):
        return None
    factor = float(magnification)
    if not np.isfinite(factor) or factor <= 0.0:
        factor = 1.0

    center = np.asarray(center, dtype=float).reshape(3)
    n_hat = _unit(normal)
    tangent_vec = np.asarray(tangent, dtype=float).reshape(3)
    u = _unit(tangent_vec - n_hat * float(np.dot(tangent_vec, n_hat)), fallback=_any_perpendicular(n_hat))
    v = _unit(np.cross(n_hat, u))
    # Optional sensor box (half width/height in image-plane mm): the uniform lattice is tiled only
    # inside it so it never spills past the orange detector frame (bug: the camera grid drew beyond
    # the orange detector box). None -> tile the spots' own footprint instead.
    half_w = half_h = None
    if sensor_half_uv is not None:
        try:
            hw = float(sensor_half_uv[0])
            hh = float(sensor_half_uv[1])
            if np.isfinite(hw) and hw > 0.0 and np.isfinite(hh) and hh > 0.0:
                half_w, half_h = hw, hh
        except (TypeError, ValueError, IndexError):
            half_w = half_h = None

    # When the spots are sub-pixel (a focused / ideal system), the spot map magnifies hugely
    # to show them -- which would blow one pixel up LARGER than the whole image, drowning the
    # scene in a useless giant mesh. Detect that ("one pixel >> the spot spread") and skip the
    # lattice; the caller shows a plain "spots are sub-pixel" note instead.
    spot_radii = np.where(np.isfinite(spot_extent_mm) & (spot_extent_mm > 0.0), spot_extent_mm, max(px, py))
    spans_all = np.maximum(2.0 * spot_radii / px, 2.0 * spot_radii / py)
    if image_radius is not None and float(image_radius) > 1e-6:
        image_ref = float(image_radius)  # the real sensor/image radius (robust)
    else:
        image_ref = float(np.max(np.hypot(chief_uv[:, 0], chief_uv[:, 1]))) if n else 0.0
    cell_size = px * factor  # on-screen size of one pixel at the spot-map magnification
    if image_ref > 1e-6 and cell_size > 0.35 * image_ref:
        return {
            "kind": "pixel_grid",
            "grids": [],
            "too_coarse": True,
            "spans_px": [float(s) for s in spans_all],
            "span_px_min": float(np.min(spans_all)),
            "span_px_max": float(np.max(spans_all)),
            "pitch_um": (px * 1000.0, py * 1000.0),
            "magnification": factor,
            "color": PIXEL_GRID_LINE_COLOR,
            "n_spots": n,
            "center": center,
            "normal": n_hat,
        }

    # ONE uniform lattice: pixel boundaries k*pitch magnified about the sensor CENTRE (not per
    # spot), so the cells are even -- a camera sensor's pixels are uniform. Cell size on screen
    # is pitch*factor; the spots (drawn by the spot map, each magnified about its own chief) land
    # on this shared grid, and the count of pixels a spot spans is exact (the factor cancels).
    cell_u = px * factor
    cell_v = py * factor
    spans_px = [float(s) for s in spans_all]  # spot diameter in pixels (factor cancels)

    # Half-extent to tile (image-plane mm): the sensor box (orange frame) when known, else the
    # spots' own on-screen footprint (chief +/- magnified radius) so the grid underlies them.
    if half_w is not None and half_h is not None:
        reach_u, reach_v = half_w, half_h
    elif n:
        spot_reach = float(np.max(spot_radii)) * factor
        reach_u = float(np.max(np.abs(chief_uv[:, 0]))) + spot_reach + cell_u
        reach_v = float(np.max(np.abs(chief_uv[:, 1]))) + spot_reach + cell_v
    else:
        reach_u = reach_v = 0.0

    # Pixel-boundary indices whose magnified position k*cell stays inside the reach -> the lattice
    # never spills past the box (clip is exact: the lattice is axis-aligned with (u, v)). Capped so
    # a tiny magnification can't ask for thousands of lines.
    kmax_u = max(min(int(np.floor(reach_u / cell_u + 1e-9)) if cell_u > 0.0 else 0, max_cells // 2), 0)
    kmax_v = max(min(int(np.floor(reach_v / cell_v + 1e-9)) if cell_v > 0.0 else 0, max_cells // 2), 0)
    us = [k * cell_u for k in range(-kmax_u, kmax_u + 1)]
    vs = [k * cell_v for k in range(-kmax_v, kmax_v + 1)]

    v_lines: list[np.ndarray] = []
    if len(vs) >= 2:
        v0, v1 = vs[0], vs[-1]
        for du in us:
            v_lines.append(np.vstack([center + du * u + v0 * v, center + du * u + v1 * v]))
    h_lines: list[np.ndarray] = []
    if len(us) >= 2:
        u0, u1 = us[0], us[-1]
        for dv in vs:
            h_lines.append(np.vstack([center + u0 * u + dv * v, center + u1 * u + dv * v]))

    return {
        "kind": "pixel_grid",
        "grids": [{"h_lines": h_lines, "v_lines": v_lines}],
        "uniform": True,
        "too_coarse": False,
        "n_cells_uv": (max(len(us) - 1, 0), max(len(vs) - 1, 0)),
        "spans_px": spans_px,
        "span_px_min": float(np.min(spans_all)),
        "span_px_max": float(np.max(spans_all)),
        "pitch_um": (px * 1000.0, py * 1000.0),
        "magnification": factor,
        "color": PIXEL_GRID_LINE_COLOR,
        "n_spots": n,
        "center": center,
        "normal": n_hat,
    }
