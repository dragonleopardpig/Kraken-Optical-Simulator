"""Zemax wavefront-map (OPD) ingest -> Zernike fit -> geometric spot.

The engine for the "wavefront-augmented surrogate" (option 2): a first-order Thin-Lens
surrogate has no aberrations, but the real (black-box) lens ships a Zemax wavefront-map
export. This module reads that OPD map, fits Zernike polynomials, and turns the wavefront
into the transverse ray aberration (the real geometric spot) -- so the surrogate can be
made to blur like the real lens instead of focusing to an unphysical point.

Pure numpy, no VTK / no KrakenOS system. The caller (next step) associates a map file with
the surrogate row and feeds the resulting spot into the Spot map.

Physics
-------
Transverse ray aberration at the image:  e = -R * grad(W)
  W   = wavefront error in length units (OPD_waves * lambda)
  R   = exit-pupil -> image distance
  grad= w.r.t. the PHYSICAL pupil coordinate (mm)
A near-diffraction-limited wavefront (~0.03 lambda RMS) therefore yields a small spot, of
the same order as the Airy radius -- not zero (ideal) and not hundreds of microns.
"""

from __future__ import annotations

import math
import re

import numpy as np

_FLOAT = re.compile(r"-?\d+\.\d+(?:[eE][-+]?\d+)?")
_INT = re.compile(r"-?\d+")


def _read_text(path) -> str:
    raw = open(path, "rb").read()
    for enc in ("utf-16", "utf-16-le", "utf-8-sig", "utf-8"):
        try:
            text = raw.decode(enc)
            # A good decode of these reports contains the ASCII header words.
            if "Wavefront" in text or "Pupil grid" in text or "Peak to valley" in text:
                return text
        except Exception:
            continue
    return raw.decode("utf-16", errors="ignore")


def parse_zemax_wavefront_map(path) -> "dict | None":
    """Parse a Zemax 'Listing of Wavefront Map Data' export.

    Returns ``{opd_waves (N,N with NaN outside the pupil), mask, wavelength_um, field_mm,
    exit_pupil_diameter_mm, rms_waves, pv_waves, grid_n, header_rms_waves}`` or None.
    """
    try:
        text = _read_text(path)
    except Exception:
        return None
    lines = text.splitlines()

    wavelength_um = None
    field_mm = None
    exit_pupil_diameter_mm = None
    header_rms = None
    header_pv = None
    grid_n = None
    center_row = None
    center_col = None

    for line in lines:
        if wavelength_um is None and "m at" in line and "mm" in line:
            # e.g. "0.5460 um at 0.00 mm"
            nums = _FLOAT.findall(line)
            if len(nums) >= 2:
                wavelength_um, field_mm = float(nums[0]), float(nums[1])
        if "Peak to valley" in line and "RMS" in line:
            nums = _FLOAT.findall(line)
            if len(nums) >= 2:
                header_pv, header_rms = float(nums[0]), float(nums[1])
        if "Exit Pupil Diameter" in line:
            nums = _FLOAT.findall(line)
            if nums:
                exit_pupil_diameter_mm = float(nums[0])
        if "Pupil grid size" in line:
            ints = _INT.findall(line)
            if ints:
                grid_n = int(ints[0])
        if "Center point" in line:
            ints = _INT.findall(line)
            if len(ints) >= 2:
                center_col, center_row = int(ints[0]), int(ints[1])

    # Data grid: the rows of N floats after the "Center point" line.
    try:
        data_start = next(i for i, l in enumerate(lines) if "Center point" in l) + 1
    except StopIteration:
        return None
    rows = []
    for line in lines[data_start:]:
        if not line.strip():
            continue
        vals = [float(t) for t in _FLOAT.findall(line)]
        if grid_n and len(vals) == grid_n:
            rows.append(vals)
        elif not grid_n and len(vals) >= 8:
            rows.append(vals)
    if not rows:
        return None
    width = grid_n or min(len(r) for r in rows)
    rows = [r for r in rows if len(r) == width]
    if len(rows) < width:  # need a square-ish grid
        return None
    grid = np.asarray(rows[:width], dtype=float)
    n = grid.shape[0]
    grid_n = n

    # Circular pupil mask centred on the reported centre (1-based -> 0-based).
    cy = (center_row - 1) if center_row else (n // 2)
    cx = (center_col - 1) if center_col else (n // 2)
    yy, xx = np.mgrid[0:n, 0:n]
    radius = (n / 2.0) - 0.5
    mask = np.hypot(yy - cy, xx - cx) <= radius

    opd = np.where(mask, grid, np.nan)
    inside = opd[mask]
    inside = inside - np.nanmean(inside)  # zero-mean over the pupil (Zemax RMS convention)
    rms_waves = float(np.sqrt(np.mean(inside ** 2)))
    pv_waves = float(np.nanmax(opd[mask]) - np.nanmin(opd[mask]))

    return {
        "opd_waves": opd,
        "mask": mask,
        "grid_n": int(grid_n),
        "wavelength_um": wavelength_um,
        "field_mm": field_mm,
        "exit_pupil_diameter_mm": exit_pupil_diameter_mm,
        "rms_waves": rms_waves,
        "pv_waves": pv_waves,
        "header_rms_waves": header_rms,
        "header_pv_waves": header_pv,
        "center_rc": (cy, cx),
    }


# ----------------------------------------------------------------------------
# Zernike basis (OSA/standard radial polynomials, orthonormal over the unit disk)

def _zernike_radial(n: int, m: int, rho: np.ndarray) -> np.ndarray:
    m = abs(m)
    out = np.zeros_like(rho)
    for k in range((n - m) // 2 + 1):
        num = ((-1) ** k) * math.factorial(n - k)
        den = (
            math.factorial(k)
            * math.factorial((n + m) // 2 - k)
            * math.factorial((n - m) // 2 - k)
        )
        out = out + (num / den) * rho ** (n - 2 * k)
    return out


def _zernike_term(n: int, m: int, rho: np.ndarray, theta: np.ndarray) -> np.ndarray:
    radial = _zernike_radial(n, m, rho)
    if m > 0:
        norm = np.sqrt(2.0 * (n + 1))
        return norm * radial * np.cos(m * theta)
    if m < 0:
        norm = np.sqrt(2.0 * (n + 1))
        return norm * radial * np.sin(abs(m) * theta)
    return np.sqrt(n + 1) * radial


_ZERNIKE_NAMES = {
    (0, 0): "piston",
    (1, 1): "tilt x", (1, -1): "tilt y",
    (2, 0): "defocus", (2, -2): "astig 45", (2, 2): "astig 0",
    (3, -1): "coma y", (3, 1): "coma x", (3, -3): "trefoil y", (3, 3): "trefoil x",
    (4, 0): "spherical", (4, 2): "sec astig 0", (4, -2): "sec astig 45",
    (4, 4): "tetrafoil x", (4, -4): "tetrafoil y",
}


def _zernike_nm_sequence(n_terms: int):
    """(n, m) pairs ordered by radial order then m (cos before sin), to n_terms."""
    seq = []
    order = 0
    while len(seq) < n_terms:
        for m in range(order, -order - 1, -2):  # n, n-2, ..., -n
            seq.append((order, m))
            if len(seq) >= n_terms:
                break
        order += 1
    return seq[:n_terms]


def _pupil_grid_coords(mask: np.ndarray):
    """Normalized pupil ``(rho, theta)`` over the FULL grid (rho>1 outside the pupil), from
    the mask's bounding circle, plus the pupil half-width in cells."""
    mask = np.asarray(mask, dtype=bool)
    n = mask.shape[0]
    ys, xs = np.where(mask)
    cy = (ys.min() + ys.max()) / 2.0
    cx = (xs.min() + xs.max()) / 2.0
    half = max((ys.max() - ys.min()) / 2.0, (xs.max() - xs.min()) / 2.0, 1.0)
    yy, xx = np.mgrid[0:n, 0:n]
    x = (xx - cx) / half
    y = (yy - cy) / half
    return np.hypot(x, y), np.arctan2(y, x), half


def reconstruct_wavefront(coeffs, terms, mask: np.ndarray) -> np.ndarray:
    """Smooth OPD (waves) over the FULL grid from the Zernike coeffs (continued smoothly
    just past rho=1, so a gradient at the pupil edge is two-sided and clean)."""
    rho, theta, _half = _pupil_grid_coords(mask)
    field = np.zeros(rho.shape, dtype=float)
    for c, (n, m) in zip(np.asarray(coeffs, dtype=float), terms):
        field = field + float(c) * _zernike_term(n, m, rho, theta)
    return field


def fit_zernike(opd_waves: np.ndarray, mask: np.ndarray, n_terms: int = 37, edge_keep: float = 0.92) -> dict:
    """Least-squares Zernike fit of the OPD (waves) over the masked pupil.

    The unreliable outermost ring of the mask (partial-pixel pupil edge) is excluded from the
    fit (``rho <= edge_keep``) so the fit is clean -- a real smooth Zemax wavefront then fits
    to ~0 residual. Returns ``{coeffs (waves), terms [(n,m)], names, residual_rms_waves,
    input_rms_waves}``; orthonormal Zernikes so coeffs are RMS contributions, piston removed.
    """
    mask = np.asarray(mask, dtype=bool)
    rho, theta, _half = _pupil_grid_coords(mask)
    seq = _zernike_nm_sequence(n_terms)
    basis = np.stack([_zernike_term(n, m, rho, theta)[mask] for (n, m) in seq], axis=1)
    w = np.asarray(opd_waves, dtype=float)[mask]
    w = w - np.mean(w)

    fit_sel = rho[mask] <= float(edge_keep)
    if int(fit_sel.sum()) < n_terms:
        fit_sel = np.ones_like(fit_sel)
    coeffs, _res, _rank, _sv = np.linalg.lstsq(basis[fit_sel], w[fit_sel], rcond=None)
    residual = w[fit_sel] - basis[fit_sel] @ coeffs
    return {
        "coeffs": coeffs,
        "terms": seq,
        "names": [_ZERNIKE_NAMES.get((n, m), f"Z(n={n},m={m})") for (n, m) in seq],
        "residual_rms_waves": float(np.sqrt(np.mean(residual ** 2))),
        "input_rms_waves": float(np.sqrt(np.mean(w[fit_sel] ** 2))),
    }


def wavefront_to_spot(
    opd_waves: np.ndarray,
    mask: np.ndarray,
    *,
    wavelength_um: float,
    exit_pupil_radius_mm: float,
    exit_pupil_to_image_mm: float,
    n_terms: int = 37,
) -> dict:
    """Transverse ray aberration (the real geometric spot) from the wavefront.

    ``e = -R * grad(W)``, W = wavefront (mm), R = exit-pupil->image distance, grad over the
    PHYSICAL pupil (mm). The gradient is taken on the smooth Zernike RECONSTRUCTION (so the
    unreliable mask-edge cells don't inflate the marginal-ray slopes). Returns
    ``{dx_mm, dy_mm, rms_mm, rms_um, zernike}`` -- per-pupil-sample landing offsets about the
    chief + geometric RMS radius.
    """
    mask = np.asarray(mask, dtype=bool)
    n = opd_waves.shape[0]
    fit = fit_zernike(opd_waves, mask, n_terms=n_terms)
    smooth_waves = reconstruct_wavefront(fit["coeffs"], fit["terms"], mask)

    lam_mm = float(wavelength_um) / 1000.0
    w_mm = smooth_waves * lam_mm
    mm_per_cell = float(exit_pupil_radius_mm) / ((n / 2.0) - 0.5)
    if mm_per_cell <= 0.0:
        return {"dx_mm": np.array([]), "dy_mm": np.array([]), "rms_mm": 0.0, "rms_um": 0.0, "zernike": fit}

    dW_dy, dW_dx = np.gradient(w_mm, mm_per_cell)  # mm/mm (dimensionless slopes)
    R = float(exit_pupil_to_image_mm)
    dx = (-R * dW_dx)[mask]
    dy = (-R * dW_dy)[mask]
    dx = dx - np.mean(dx)
    dy = dy - np.mean(dy)
    rms_mm = float(np.sqrt(np.mean(dx ** 2 + dy ** 2)))
    return {"dx_mm": dx, "dy_mm": dy, "rms_mm": rms_mm, "rms_um": rms_mm * 1000.0, "zernike": fit}
