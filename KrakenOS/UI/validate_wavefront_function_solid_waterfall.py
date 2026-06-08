"""Guard: the Wavefront Function plot renders as an opaque hidden-line surface.

Zemax draws the Wavefront Function as a solid waterfall sitting on a flat base
plane -- nearer slices occlude farther ones (see attachment/wavefront_zemax.png).
KrakenOS used to draw a see-through wireframe (every row line drawn translucent,
no fills, no floor), so the back of the surface bled through the front
(attachment/wavefront.png). This guards bug 0036: the waterfall must be drawn
with opaque white curtains (hidden-line removal) and a visible base-plane apron.

All checks are display-free (Agg backend, no Xvfb / GPU needed) and use a
synthetic circular-pupil wavefront, so they do not depend on a ray trace:

A. ``_wavefront_projected_axes_coordinates`` returns the surface grid, a
   finite-everywhere per-point z=0 floor line, and a 4-corner base parallelogram.
B. The relief rests on the floor: every surface sample is at or above its floor.
C. Drawing produces opaque curtains (fill collections) -- the old wireframe had
   none -- plus the row line curves and the base-plane parallelogram patch.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_wavefront_function_solid_waterfall

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib.figure import Figure

# Importing layout_editor syncs Rectangle/textwrap into the mixin's globals.
import KrakenOS.UI.layout_editor  # noqa: F401
from KrakenOS.UI.services.layout_analysis_display import LayoutAnalysisDisplayMixin


class _WavefrontProbe(LayoutAnalysisDisplayMixin):
    """Minimal carrier for the wavefront-plot mixin methods."""


def _synthetic_pupil() -> "tuple[np.ndarray, np.ndarray, np.ndarray, float, float]":
    n = 45
    lin = np.linspace(-1.0, 1.0, n)
    grid_x, grid_y = np.meshgrid(lin, lin)
    inside = (grid_x**2 + grid_y**2) <= 1.0
    x_pupil = grid_x[inside]
    y_pupil = grid_y[inside]
    radius = np.sqrt(x_pupil**2 + y_pupil**2)
    angle = np.arctan2(y_pupil, x_pupil)
    phase = -(
        1.4 * (6 * radius**4 - 6 * radius**2 + 1)        # spherical
        + 0.9 * (3 * radius**3 - 2 * radius) * np.cos(angle)  # coma
        + 0.6 * radius**2 * np.cos(2 * angle)            # astigmatism
    )
    phase_centered = phase - float(np.mean(phase))
    pv = float(np.nanmax(phase_centered) - np.nanmin(phase_centered))
    rms = float(np.sqrt(np.mean(phase_centered**2)))
    return x_pupil, y_pupil, phase_centered, pv, rms


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    probe = _WavefrontProbe()
    x_pupil, y_pupil, phase_centered, pv, rms = _synthetic_pupil()

    xx, yy, zz = probe._wavefront_function_grid(x_pupil, y_pupil, phase_centered)
    xx, yy, zz = probe._orient_wavefront_waterfall_grid(xx, yy, zz)
    projected = probe._wavefront_projected_axes_coordinates(xx, yy, zz)

    # A. Projection yields surface grid + finite floor line + 4 base corners.
    if len(projected) != 4:
        notes.append(f"FAIL: projection returned {len(projected)} values, expected 4")
        return False, notes
    axis_x, axis_y, base_axis_y, base_corners = projected
    if len(base_corners) != 4:
        notes.append(f"FAIL: base parallelogram has {len(base_corners)} corners, expected 4")
        passed = False
    if not np.all(np.isfinite(base_axis_y)):
        notes.append("FAIL: per-point floor line has non-finite samples")
        passed = False

    # B. The relief rests on the floor (every surface sample >= its floor).
    finite = np.isfinite(axis_x) & np.isfinite(axis_y)
    below_floor = axis_y[finite] < (base_axis_y[finite] - 1e-6)
    if np.any(below_floor):
        notes.append(
            f"FAIL: {int(np.count_nonzero(below_floor))} surface samples dip below the z=0 floor"
        )
        passed = False

    # C. Drawing produces opaque curtains + row lines + base-plane patch.
    figure = Figure(figsize=(4.2, 3.3))
    analysis_ax = figure.add_subplot(111)
    probe._plot_wavefront_function_analysis(
        analysis_ax,
        x_pupil,
        y_pupil,
        phase_centered,
        phase_pv=pv,
        phase_rms=rms,
        phase_method="Synthetic Zernike",
        reference_note="",
    )

    fill_collections = len(list(analysis_ax.collections))
    row_lines = len(list(analysis_ax.lines))
    # A genuinely filled patch (the base parallelogram) has a non-zero face
    # alpha; the outer frame Rectangle is fill=False (alpha 0) and is ignored.
    base_patches = [
        patch for patch in analysis_ax.patches
        if float(patch.get_facecolor()[3]) > 0.0
    ]

    if fill_collections == 0:
        notes.append("FAIL: no opaque curtains drawn -- still a see-through wireframe (bug 0036)")
        passed = False
    if row_lines < 5:
        notes.append(f"FAIL: only {row_lines} row line segments drawn, expected the waterfall slices")
        passed = False
    if not base_patches:
        notes.append("FAIL: no filled base-plane parallelogram drawn under the relief")
        passed = False

    if verbose:
        notes.append(
            f"curtains={fill_collections}, row_lines={row_lines}, "
            f"base_patches={len(base_patches)}, PV={pv:.3f}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Wavefront Function renders an opaque hidden-line waterfall on a base plane")
        return 0
    print("[FAIL] Wavefront Function solid-waterfall guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
