"""Distortion grid-warp geometry (3D field-distortion visualization, idea #2 / 2nd half).

A lens images a rectilinear object grid as a barrel- or pincushion-warped grid on the
detector. This module builds two coplanar grids on the image plane -- the IDEAL
(rectilinear, paraxial) grid and its REAL (radially warped) image -- from the per-field
real vs paraxial chief-ray heights the 2D Field Curvature / Distortion analysis already
computes. The divergence between the two grids is the distortion.

The radial warp comes from the meridional field scan: for a centered (rotationally
symmetric) system the distortion is a function of radius alone, so a 1-D real-vs-ideal
height mapping warps a full 2-D grid. The tiny residual distortion of a corrected lens
is auto-exaggerated (like the best-focus surface) so the barrel/pincushion reads, with
the TRUE max distortion % and the factor reported in the label; the ideal grid stays at
its true rectilinear position as the honest reference.

Pure geometry only (numpy) -- unit-testable without an editor or VTK.
"""

from __future__ import annotations

import numpy as np

DISTORTION_GRID_REAL_COLOR = (0.62, 0.18, 0.74)   # violet -- the warped real image grid
DISTORTION_GRID_IDEAL_COLOR = (0.60, 0.60, 0.62)  # grey -- the rectilinear reference grid
DISTORTION_GRID_LINES = 9
DISTORTION_GRID_SAMPLES = 25
# Exaggerate the radial displacement so a sub-percent warp is visible; target a peak
# displacement of this fraction of the image radius, clamped to [1, cap].
DISTORTION_DISPLACEMENT_TARGET_FRACTION = 0.06
DISTORTION_EXAGGERATION_CAP = 60.0


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


def build_distortion_grid(
    ideal_radii,
    real_radii,
    *,
    center,
    normal,
    tangent,
    n_lines: int = DISTORTION_GRID_LINES,
    samples: int = DISTORTION_GRID_SAMPLES,
    exaggeration: "float | None" = None,
    lift_radii=None,
    lift_dz=None,
    real_color=DISTORTION_GRID_REAL_COLOR,
    ideal_color=DISTORTION_GRID_IDEAL_COLOR,
) -> "dict | None":
    """Build the rectilinear ideal grid + its radially-warped real image.

    ``ideal_radii`` / ``real_radii`` are monotonic per-field paraxial and real chief-ray
    image heights (mm). The grid is an inscribed square (half-side = max ideal radius /
    sqrt(2)) of ``n_lines`` lines each way, each sampled at ``samples`` points so a warped
    line reads as a smooth curve.

    When ``lift_radii`` / ``lift_dz`` are given (the best-focus surface's ring radii and
    its already-exaggerated axial offsets), each grid vertex is lifted along the normal by
    ``interp(vertex_radius, lift_radii, lift_dz)`` -- i.e. the warped grid is laid onto the
    curved best-focus bowl (the "distorted bowl" when both overlays are on).

    Returns world-space polylines + the true max distortion % + the (auto) exaggeration
    factor, or None for degenerate input.
    """
    ideal_radii = np.asarray(ideal_radii, dtype=float).reshape(-1)
    real_radii = np.asarray(real_radii, dtype=float).reshape(-1)
    if ideal_radii.size < 2 or real_radii.size != ideal_radii.size:
        return None
    if not np.all(np.isfinite(ideal_radii)) or not np.all(np.isfinite(real_radii)):
        return None
    order = np.argsort(ideal_radii)
    ir = ideal_radii[order]
    rr = real_radii[order]
    image_radius = float(ir[-1])
    if not np.isfinite(image_radius) or image_radius <= 1e-6:
        return None

    with np.errstate(divide="ignore", invalid="ignore"):
        distortion_pct = np.where(ir > 1e-9, (rr - ir) / ir * 100.0, 0.0)
    max_distortion_pct = float(np.max(np.abs(distortion_pct)))
    max_displacement = float(np.max(np.abs(rr - ir)))

    if exaggeration is None:
        target = DISTORTION_DISPLACEMENT_TARGET_FRACTION * image_radius
        factor = (target / max_displacement) if max_displacement > 1e-9 else 1.0
        factor = float(min(max(factor, 1.0), DISTORTION_EXAGGERATION_CAP))
    else:
        factor = float(exaggeration)
        if not np.isfinite(factor) or factor <= 0.0:
            factor = 1.0

    center = np.asarray(center, dtype=float).reshape(3)
    n_hat = _unit(normal)
    tangent_vec = np.asarray(tangent, dtype=float).reshape(3)
    u = _unit(tangent_vec - n_hat * float(np.dot(tangent_vec, n_hat)), fallback=_any_perpendicular(n_hat))
    v = _unit(np.cross(n_hat, u))

    n_lines = max(int(n_lines), 2)
    samples = max(int(samples), 3)
    half = image_radius / np.sqrt(2.0)  # inscribed square -> corners ride the image circle
    line_coords = np.linspace(-half, half, n_lines)
    sample_coords = np.linspace(-half, half, samples)

    lifted = lift_radii is not None and lift_dz is not None
    if lifted:
        lr = np.asarray(lift_radii, dtype=float).reshape(-1)
        ld = np.asarray(lift_dz, dtype=float).reshape(-1)
        lifted = lr.size >= 2 and ld.size == lr.size and np.all(np.isfinite(lr)) and np.all(np.isfinite(ld))
        if lifted:
            order_l = np.argsort(lr)
            lr = lr[order_l]
            ld = ld[order_l]

    def _warp(a: np.ndarray, b: np.ndarray):
        rho = np.hypot(a, b)
        real_rho = np.interp(rho, ir, rr)
        disp = (real_rho - rho) * factor
        scale = np.where(rho > 1e-9, (rho + disp) / np.where(rho > 1e-9, rho, 1.0), 1.0)
        return a * scale, b * scale

    def _to_world(a: np.ndarray, b: np.ndarray) -> np.ndarray:
        pts = center[None, :] + a[:, None] * u[None, :] + b[:, None] * v[None, :]
        if lifted:
            dz = np.interp(np.hypot(a, b), lr, ld)
            pts = pts + dz[:, None] * n_hat[None, :]
        return pts

    ideal_polylines: list[np.ndarray] = []
    real_polylines: list[np.ndarray] = []
    for coord in line_coords:
        # horizontal line (b = coord, a sweeps) then vertical line (a = coord, b sweeps)
        for a, b in (
            (sample_coords, np.full(samples, float(coord))),
            (np.full(samples, float(coord)), sample_coords),
        ):
            ideal_polylines.append(_to_world(a, b))
            wa, wb = _warp(a, b)
            real_polylines.append(_to_world(wa, wb))

    return {
        "kind": "distortion_grid",
        "ideal_polylines": ideal_polylines,
        "real_polylines": real_polylines,
        "max_distortion_pct": max_distortion_pct,
        "exaggeration": float(factor),
        "lifted": bool(lifted),
        "image_radius": image_radius,
        "center": center,
        "normal": n_hat,
        "real_color": tuple(float(c) for c in real_color),
        "ideal_color": tuple(float(c) for c in ideal_color),
    }
