"""Guard: the Wavefront Function plot renders as an opaque hidden-surface MESH.

Zemax draws the Wavefront Function as a solid relief on a base plane with the
surface mesh visible (cross-sections in both directions), nearer cells occluding
farther ones. KrakenOS first drew a see-through wireframe (bug 0036), then a
stylized waterfall whose hand-built "wall" kept breaking on folded wavefronts.
It now draws the real thing: the structured pupil grid's rows (constant-y) and
columns (constant-x) are both genuine slices, rendered as depth-sorted opaque
white quads with dark edges (``_draw_wavefront_mesh``) -- a true cross-section
mesh with hidden-surface removal, every visible line a real cut.

All checks are display-free (Agg backend, no Xvfb / GPU needed) and use a
synthetic circular-pupil wavefront, so they do not depend on a ray trace:

A. A wavefront-mesh ``PolyCollection`` (gid "wavefront-mesh") is drawn with many
   cells -- a real mesh from both grid directions, not a few stray polygons.
B. Its faces are OPAQUE WHITE -- hidden-surface removal (the back is occluded),
   not the see-through wireframe of the original bug 0036.
C. Its edges are dark -- the visible mesh lines (the real cross-sections).
D. A base-plane diamond patch is drawn under the mesh for grounding.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_wavefront_function_solid_waterfall

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib.figure import Figure

# Importing layout_editor syncs Rectangle/textwrap into the mixin's globals.
import KrakenOS.UI.layout_editor  # noqa: F401
from KrakenOS.UI.services.layout_analysis_display import LayoutAnalysisDisplayMixin

# A real disk mesh has hundreds of cells; require clearly more than a handful.
MIN_MESH_QUADS = 100


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

    # The wavefront is drawn as a real cross-section MESH: the structured grid's
    # rows (constant-y) and columns (constant-x) are both genuine slices, drawn as
    # depth-sorted opaque white quads with dark edges (hidden-surface removal).
    xx, yy, zz = probe._wavefront_function_grid(x_pupil, y_pupil, phase_centered)
    xx, yy, zz = probe._orient_wavefront_waterfall_grid(xx, yy, zz)
    if xx.ndim != 2 or min(xx.shape) < 2:
        notes.append(f"FAIL: wavefront grid is {xx.shape}, not a 2-D mesh grid")
        return False, notes

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

    mesh_collections = [
        c for c in analysis_ax.collections
        if isinstance(c, PolyCollection) and c.get_gid() == "wavefront-mesh"
    ]
    base_patches = [
        patch for patch in analysis_ax.patches
        if float(patch.get_facecolor()[3]) > 0.0
    ]

    n_quads = 0
    if not mesh_collections:
        notes.append("FAIL: no wavefront mesh PolyCollection drawn (gid 'wavefront-mesh')")
        passed = False
    else:
        mesh = mesh_collections[0]
        # A. A real cross-section mesh -- many cells from both grid directions.
        n_quads = len(mesh.get_paths())
        if n_quads < MIN_MESH_QUADS:
            notes.append(f"FAIL: mesh has {n_quads} cells (< {MIN_MESH_QUADS}) -- not a real mesh")
            passed = False
        # B. Opaque white faces => hidden-surface removal (the back of the surface
        # is occluded), NOT the see-through wireframe of the original bug 0036.
        face = np.atleast_2d(np.asarray(mesh.get_facecolor(), dtype=float))
        if face.size == 0 or float(np.min(face[:, 3])) < 0.999:
            notes.append("FAIL: mesh faces not opaque -- back of surface bleeds through (bug 0036)")
            passed = False
        elif not np.all(face[:, :3] > 0.95):
            notes.append("FAIL: mesh faces are not white (occluding fill expected)")
            passed = False
        # C. Dark edges => the visible mesh lines (the real cross-sections).
        edge = np.atleast_2d(np.asarray(mesh.get_edgecolor(), dtype=float))
        if edge.size == 0 or float(np.max(edge[:, :3])) > 0.5:
            notes.append("FAIL: mesh edges not drawn dark -- the slice lines are missing")
            passed = False

    # D. Base-plane diamond drawn under the mesh (grounding).
    if not base_patches:
        notes.append("FAIL: no base-plane patch drawn under the mesh")
        passed = False

    if verbose:
        notes.append(
            f"mesh_collections={len(mesh_collections)}, quads={n_quads}, "
            f"base_patches={len(base_patches)}, PV={pv:.3f}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Wavefront Function renders an opaque hidden-surface cross-section mesh")
        return 0
    print("[FAIL] Wavefront Function mesh guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
