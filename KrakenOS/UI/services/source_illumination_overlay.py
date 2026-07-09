"""Detector relative-illumination heatmap (3D on-detector irradiance overlay, viz idea #3).

Drape the source-illumination map (already binned by ``source_illumination_analysis``) onto the
DETECTOR plane as a smooth textured quad, so the coaxial-LED dark edges are visible directly on the
sensor -- what the Monitor shows -- instead of only in the separate 2-D report. The dark edges are an
ILLUMINATION-coverage effect: the flat area LED reflects off the 55x55x78 beam-splitter diagonal down
to the object; the 55x55 BS cross-section (foreshortened by the 45 deg fold) under-fills the 39x39 FOV
on the fold axis, so that axis reads dark while the long axis is uniform.

Pure geometry only (numpy): the editor wrapper traces the LED illumination arm and bins the
detector-plane hits with ``source_illumination_map_data_from_samples``; this module turns that map into
a structured grid of points + a per-point RELATIVE illumination scalar (normalised so the sensor CENTRE
= 1.0, the relative-illumination convention -- NOT the peak) and picks the colormap from the camera
sensor chroma (Mono/NIR -> grayscale, Color -> false colour). The inspector renders the returned grid
with a smooth (interpolated) scalar map.
"""

from __future__ import annotations

import numpy as np

# Colormaps keyed off the camera sensor chroma (camera_database "chroma"): a mono sensor shows a
# literal grey ramp (dark = low illumination), a colour sensor gets a false-colour ramp.
ILLUMINATION_MONO_CMAP = "gray"
ILLUMINATION_COLOR_CMAP = "turbo"

# Central fraction of the sensor whose mean defines relative illumination = 1.0 (the on-axis reference).
ILLUMINATION_CENTRE_FRACTION = 0.20

# Central fraction kept as "interior" when measuring an edge ratio: the outer (1 - this)/2 of bins on
# EACH end is the edge band. 0.70 -> edge = |pos| >= 0.7*half, matching phase 175's 13.5/19.5 ~ 0.69.
EDGE_BAND_FRACTION = 0.70

# Gaussian smoothing (in BIN units) applied to the binned density before draping. The true on-detector
# illumination field is smooth; per-bin Monte-Carlo counting noise (Poisson, ~1/sqrt(hits-per-bin) ->
# ~35% at the adaptive ~10 hits/bin) otherwise swamps the ~30% fold-edge dip and the quad renders as
# speckle. sigma averages neighbours to recover the underlying structure while leaving the many-bin-wide
# fold roll-off (and its edge-ratio) essentially untouched. bugs/0277 (flag_20260709_114618_526): a
# sparse coaxial scene lands only ~800 rays in the 39x39 sensor, so even the UNIFORM (over-filled) perp
# axis speckled DARK at sigma 1.0 -> the user read "4 dark edges" instead of 2. sigma 1.5 (with the
# lower bin floor in three_d_scene_tools) lifts the perp edge back over the 0.85 "uniform" bar (measured
# fold 0.77 < perp 0.91) while the fold stays dark.
ILLUMINATION_SMOOTH_SIGMA_BINS = 1.5


def _gaussian_smooth(grid: np.ndarray, sigma_bins: float) -> np.ndarray:
    """Separable Gaussian blur in bin units, edge-clamped. Prefers scipy, falls back to numpy."""
    sigma = float(sigma_bins)
    if not np.isfinite(sigma) or sigma <= 0.0 or grid.size == 0:
        return grid
    try:  # scipy is present in the app venv; the numpy path keeps the module import-safe elsewhere.
        from scipy.ndimage import gaussian_filter

        return gaussian_filter(grid, sigma=sigma, mode="nearest")
    except Exception:
        radius = max(1, int(round(sigma * 3.0)))
        xs = np.arange(-radius, radius + 1, dtype=float)
        kernel = np.exp(-(xs * xs) / (2.0 * sigma * sigma))
        kernel /= kernel.sum()
        out = grid.astype(float, copy=True)
        for axis in (0, 1):
            pad = [(0, 0), (0, 0)]
            pad[axis] = (radius, radius)
            padded = np.pad(out, pad, mode="edge")
            out = np.apply_along_axis(lambda m: np.convolve(m, kernel, mode="valid"), axis, padded)
        return out


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


def colormap_for_chroma(chroma: object) -> str:
    """Grayscale for a monochrome (or NIR) sensor, false colour for a colour sensor."""
    text = str(chroma or "").strip().lower()
    return ILLUMINATION_COLOR_CMAP if text.startswith("colo") else ILLUMINATION_MONO_CMAP


def _centre_reference(relative_grid: np.ndarray, centre_fraction: float) -> float:
    ny, nx = relative_grid.shape
    fx = max(1, int(round(nx * centre_fraction)))
    fy = max(1, int(round(ny * centre_fraction)))
    cx0 = max(0, (nx - fx) // 2)
    cy0 = max(0, (ny - fy) // 2)
    block = relative_grid[cy0:cy0 + fy, cx0:cx0 + fx]
    positive = block[block > 0.0]
    if positive.size:
        return float(np.mean(positive))
    return float(np.max(relative_grid)) if np.any(relative_grid > 0.0) else 0.0


def build_source_illumination_overlay(
    map_data: "dict | None",
    *,
    center,
    normal,
    tangent,
    chroma: object = "Mono",
    centre_fraction: float = ILLUMINATION_CENTRE_FRACTION,
    gamma: float = 1.0,
    opacity: float = 0.85,
    smooth_sigma_bins: float = ILLUMINATION_SMOOTH_SIGMA_BINS,
) -> "dict | None":
    """Build the detector-plane illumination heatmap grid (pure geometry, no pyvista).

    ``map_data`` is the dict from ``source_illumination_map_data_from_samples`` (its ``density`` is
    peak-normalised; we re-normalise to the sensor CENTRE). The detector plane frame is ``center`` +
    ``normal`` (out-of-plane) + ``tangent`` (the sensor local +x / horizontal); local +y = normal x u.
    Returns a grid of ``dims = (nx, ny)`` bin-centre points with a per-point relative-illumination
    scalar, the chroma-chosen ``cmap``, and edge/centre metrics; None when there is nothing to draw.
    """
    if not isinstance(map_data, dict):
        return None
    density = np.asarray(map_data.get("density"), dtype=float)
    x_edges = np.asarray(map_data.get("x_edges"), dtype=float)
    y_edges = np.asarray(map_data.get("y_edges"), dtype=float)
    if density.ndim != 2 or density.size == 0:
        return None
    ny, nx = density.shape
    if x_edges.size != nx + 1 or y_edges.size != ny + 1:
        return None
    if not np.any(density > 0.0):
        return None

    # Smooth the Monte-Carlo counting noise out of the binned density BEFORE normalising, so the
    # centre reference and the draped scalars come from the same de-speckled field the user sees.
    density = _gaussian_smooth(density, float(smooth_sigma_bins))

    centre_value = _centre_reference(density, float(centre_fraction))
    if centre_value <= 0.0:
        return None
    relative = density / centre_value  # centre ~ 1.0, dark edges < 1.0

    gamma = float(gamma) if np.isfinite(gamma) and gamma > 0.0 else 1.0
    scalar_grid = np.clip(relative, 0.0, None) ** gamma

    xc = 0.5 * (x_edges[:-1] + x_edges[1:])  # (nx,)
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])  # (ny,)
    # bugs/0277 (flag_20260709_114618_526): the draped quad is a point grid at bin CENTRES, so it
    # stops half a bin short of the window on every side -- a ~1.2 mm dark gap to the orange sensor
    # square (the user: "still not fully covered the sensor"). Pin the OUTER vertices to the window
    # edges so the quad spans the full sensor; the edge cell just holds its outermost bin's value out
    # to the rim. Only the vertex POSITIONS move -- the density/relative grid and edge ratios are
    # untouched (they read the bins, not the point coords).
    if xc.size >= 2:
        xc[0] = float(x_edges[0])
        xc[-1] = float(x_edges[-1])
    if yc.size >= 2:
        yc[0] = float(y_edges[0])
        yc[-1] = float(y_edges[-1])

    center = np.asarray(center, dtype=float).reshape(3)
    n_hat = _unit(normal)
    tangent_vec = np.asarray(tangent, dtype=float).reshape(3)
    u = _unit(tangent_vec - n_hat * float(np.dot(tangent_vec, n_hat)), fallback=_any_perpendicular(n_hat))
    v = _unit(np.cross(n_hat, u))

    # point[j, i] = center + xc[i]*u + yc[j]*v ; row-major reshape keeps points aligned with scalars.
    gx = xc[None, :, None]  # (1, nx, 1)
    gy = yc[:, None, None]  # (ny, 1, 1)
    grid = (center[None, None, :]
            + gx * u[None, None, :]
            + gy * v[None, None, :])  # (ny, nx, 3)
    points = grid.reshape(-1, 3)
    scalars = scalar_grid.reshape(-1)

    # Edge/centre ratios per in-plane axis, measured along a CENTRAL strip so each axis is isolated
    # (a whole edge row crosses the other axis' dip at the corners and would blur the two), and
    # averaged over an OUTER BAND (both ends) rather than the single outermost bin -- the extreme
    # bin sits deep in the penumbra roll-off and is too noisy. This mirrors phase 175's
    # _strip_edge_over_centre exactly (edge = mean of |pos| >= ~0.7*half over both ends; centre by
    # construction == 1.0). The fold axis is whichever ratio is smaller -- this module stays
    # axis-agnostic and lets the guard/labels decide.
    bw_x = max(1, int(round(nx * float(centre_fraction))))
    bw_y = max(1, int(round(ny * float(centre_fraction))))
    row0 = max(0, (ny - bw_y) // 2)
    col0 = max(0, (nx - bw_x) // 2)
    central_rows = relative[row0:row0 + bw_y, :]  # spans x at mid-y -> fold(x) edge vs centre
    central_cols = relative[:, col0:col0 + bw_x]  # spans y at mid-x -> perp(y) edge vs centre
    eb_x = max(1, int(round(nx * (1.0 - EDGE_BAND_FRACTION) / 2.0)))  # bins per end
    eb_y = max(1, int(round(ny * (1.0 - EDGE_BAND_FRACTION) / 2.0)))
    x_edge_band = np.concatenate([central_rows[:, :eb_x].ravel(), central_rows[:, -eb_x:].ravel()])
    y_edge_band = np.concatenate([central_cols[:eb_y, :].ravel(), central_cols[-eb_y:, :].ravel()])
    x_edge_ratio = float(np.mean(x_edge_band)) if x_edge_band.size else 0.0
    y_edge_ratio = float(np.mean(y_edge_band)) if y_edge_band.size else 0.0

    return {
        "kind": "source_illumination_overlay",
        "points": points,
        "scalars": scalars,
        "dims": (int(nx), int(ny)),
        "relative": relative,
        "cmap": colormap_for_chroma(chroma),
        # Display range in RELATIVE illumination: 0 -> black, the sensor CENTRE reference (1.0) ->
        # full white/hot. Edges (< 1) read progressively darker; the rare hot bin (> 1, sampling
        # noise) clips at the top. This is what makes the fold-axis dark edges legible on the quad.
        "clim": [0.0, 1.0],
        "opacity": float(min(max(opacity, 0.0), 1.0)),
        "centre_value": float(centre_value),
        "min_relative": float(np.min(relative)),
        "max_relative": float(np.max(relative)),
        "x_edge_ratio": x_edge_ratio,
        "y_edge_ratio": y_edge_ratio,
        "gamma": gamma,
        "center": center,
        "normal": n_hat,
        "tangent": u,
        "bitangent": v,
    }
