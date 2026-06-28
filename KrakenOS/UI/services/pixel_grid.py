"""Camera pixel-grid overlay geometry (idea #1: the spot footprint on real pixels).

When a vendor camera is registered on the detector it carries a pixel pitch (e.g. the SVS
/ Allied-Vision 25 MP is 5120x5120 @ 4.50 um). This module draws, at each spot in the
spot-field map, the camera's pixel LATTICE over the local region the spot covers -- so the
user sees the actual spot land on individual pixels (how many pixels the blur spans).

The lattice is true-aligned (lines fall on real pixel boundaries k*pitch from the sensor
centre, so the spot's sub-pixel position is honest) and magnified about each spot's chief
by the SAME factor the spot map uses, so the spot/pixel size RATIO is exact even though a
4.5 um pixel could never be seen at the sensor's true 23 mm scale.

Pure geometry only (numpy): the editor wrapper supplies the per-spot chief positions +
true extents (from the spot-map trace) and the camera pitch; the inspector renders the
returned line sets.
"""

from __future__ import annotations

import numpy as np

PIXEL_GRID_MARGIN_PX = 3       # pixels of lattice drawn beyond the spot on each side
PIXEL_GRID_MAX_CELLS = 80      # per-spot/per-axis cap (a pathological tiny pitch backstop)
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


def _clamp_span(lo: int, hi: int, max_cells: int) -> "tuple[int, int]":
    if (hi - lo) <= max_cells:
        return lo, hi
    mid = (hi + lo) // 2
    return mid - max_cells // 2, mid + max_cells // 2


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
    margin_px: int = PIXEL_GRID_MARGIN_PX,
    max_cells: int = PIXEL_GRID_MAX_CELLS,
) -> "dict | None":
    """Build per-spot pixel-lattice line sets on the detector.

    ``chief_uv`` (N,2) are the spot chief positions (mm, image-plane local); ``spot_extent_mm``
    (N,) their true (un-magnified) radii; ``pitch_mm`` the ``(px, py)`` true pixel pitch;
    ``magnification`` the spot-map factor. Each spot gets the pixel boundaries it straddles
    (k*pitch, plus ``margin_px`` either side), displayed at ``chief + (true - chief)*factor`` so
    the lattice aligns with the magnified scatter. Returns the line sets + the spot's span in
    pixels, or None when there is nothing/no pitch.
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
    margin = max(int(margin_px), 1)
    # Optional sensor box (half width/height in image-plane mm): the magnified lattice is CLIPPED
    # to it so an edge spot's x-factor patch never spills past the orange detector frame (bug: the
    # camera grid drew beyond the orange detector box). None -> no clip.
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

    grids: list[dict] = []
    spans_px: list[float] = []
    for i in range(n):
        cu = float(chief_uv[i, 0])
        cv = float(chief_uv[i, 1])
        r = float(spot_extent_mm[i])
        if not np.isfinite(r) or r <= 0.0:
            r = max(px, py)
        spans_px.append(max(2.0 * r / px, 2.0 * r / py))  # spot diameter in pixels (factor cancels)

        kx_lo, kx_hi = _clamp_span(int(np.floor((cu - r) / px)) - margin, int(np.ceil((cu + r) / px)) + margin, max_cells)
        ky_lo, ky_hi = _clamp_span(int(np.floor((cv - r) / py)) - margin, int(np.ceil((cv + r) / py)) + margin, max_cells)

        # display offset of a true image coord t from the chief: (t - chief) * factor
        dv_lo = cv + (ky_lo * py - cv) * factor
        dv_hi = cv + (ky_hi * py - cv) * factor
        du_lo = cu + (kx_lo * px - cu) * factor
        du_hi = cu + (kx_hi * px - cu) * factor

        v_lines: list[np.ndarray] = []
        for kx in range(kx_lo, kx_hi + 1):
            du = cu + (kx * px - cu) * factor
            if half_w is not None and abs(du) > half_w + 1e-9:
                continue  # column past the sensor edge -> drop the whole line
            a, b = dv_lo, dv_hi
            if half_h is not None:
                a, b = max(dv_lo, -half_h), min(dv_hi, half_h)
                if b <= a + 1e-9:
                    continue  # line fully outside the sensor box
            p0 = center + du * u + a * v
            p1 = center + du * u + b * v
            v_lines.append(np.vstack([p0, p1]))
        h_lines: list[np.ndarray] = []
        for ky in range(ky_lo, ky_hi + 1):
            dv = cv + (ky * py - cv) * factor
            if half_h is not None and abs(dv) > half_h + 1e-9:
                continue
            a, b = du_lo, du_hi
            if half_w is not None:
                a, b = max(du_lo, -half_w), min(du_hi, half_w)
                if b <= a + 1e-9:
                    continue
            p0 = center + a * u + dv * v
            p1 = center + b * u + dv * v
            h_lines.append(np.vstack([p0, p1]))
        grids.append({"h_lines": h_lines, "v_lines": v_lines})

    if not spans_px:
        return None
    return {
        "kind": "pixel_grid",
        "grids": grids,
        "too_coarse": False,
        "spans_px": spans_px,
        "span_px_min": float(np.min(spans_px)),
        "span_px_max": float(np.max(spans_px)),
        "pitch_um": (px * 1000.0, py * 1000.0),
        "magnification": factor,
        "color": PIXEL_GRID_LINE_COLOR,
        "n_spots": n,
        "center": center,
        "normal": n_hat,
    }
