"""Real 3D wavefront surface (PyVista/VTK) -- a true z-buffered relief.

The Wavefront Function *analysis panel* draws an oblique 2D "waterfall" that
mirrors the Zemax printout (see ``layout_analysis_display`` + bug 0036). That is
the right representation for the static/export chart, but it is painter's-algorithm
fake-3D: hard saddle/twisted wavefronts force hand-tuned hidden-line tricks.

This module is the honest counterpart: it warps the pupil OPD samples into a real
3D surface mesh and renders it with PyVista/VTK, which has a genuine GPU z-buffer
(true hidden-surface removal -- no saddle artifacts) and free interactive
rotate/zoom. PyVista/VTK are already KrakenOS dependencies, so this adds none.

Design notes:
* PyVista is imported **lazily** inside each function so importing this module
  (and collecting its guard) never hard-fails if VTK is unavailable on a clone.
* ``build_wavefront_surface`` is pure (mesh in, mesh out -- no display), so it is
  unit-testable headless.
* ``render_wavefront_surface_to_png`` renders off-screen (works headless here with
  VTK's software GL -- no Xvfb needed) for export and display-free regression.
* ``show_wavefront_surface`` opens the interactive window; ``main`` makes the
  module launchable as a subprocess so the Tk UI can pop the 3D view without
  blocking its event loop or fighting VTK over the GIL.

The pupil samples come straight from ``editor._last_wavefront_samples`` (the same
dicts the analysis panel already fills): ``x_pupil``, ``y_pupil``, ``phase_waves``.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Sequence

import numpy as np

SCALAR_NAME = "Wavefront [waves]"
# Relief height as a fraction of the pupil footprint width -- a low Zemax-style
# dome rather than a tall spike. Matches the 2D waterfall's shallow aspect.
_RELIEF_ASPECT = 0.33


def wavefront_xyz_from_samples(
    samples: Sequence[dict] | None,
) -> "tuple[np.ndarray, np.ndarray, np.ndarray]":
    """Pull ``(x, y, opd_waves)`` arrays out of ``_last_wavefront_samples`` dicts,
    dropping any row that is missing a key or non-finite."""
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for row in samples or []:
        try:
            x = float(row["x_pupil"])
            y = float(row["y_pupil"])
            z = float(row["phase_waves"])
        except (KeyError, TypeError, ValueError):
            continue
        if np.isfinite(x) and np.isfinite(y) and np.isfinite(z):
            xs.append(x)
            ys.append(y)
            zs.append(z)
    return np.asarray(xs, dtype=float), np.asarray(ys, dtype=float), np.asarray(zs, dtype=float)


def auto_warp_factor(x: np.ndarray, y: np.ndarray, opd: np.ndarray) -> float:
    """Warp factor giving a relief ~``_RELIEF_ASPECT`` of the footprint width, so
    the surface reads as a shallow dome regardless of pupil units (mm) or OPD
    magnitude (waves)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    span = max(float(np.ptp(x)) if x.size else 0.0, float(np.ptp(y)) if y.size else 0.0)
    opd_range = float(np.ptp(opd)) if np.asarray(opd).size else 0.0
    if opd_range <= 1e-12 or span <= 0.0:
        return 1.0
    return float(_RELIEF_ASPECT * span / opd_range)


def write_wavefront_payload_npz(
    samples: Sequence[dict] | None,
    *,
    title: str | None = None,
    directory: "str | Path | None" = None,
) -> "Path | None":
    """Serialise the pupil samples to a temp ``.npz`` for the interactive
    subprocess (``main``). Returns the path, or ``None`` if there are fewer than
    3 finite samples (nothing to show -- run the Wavefront analysis first)."""
    x, y, opd = wavefront_xyz_from_samples(samples)
    if x.size < 3:
        return None
    base = Path(directory) if directory is not None else Path(tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix="kraken_wavefront3d_", suffix=".npz", dir=str(base))
    os.close(handle)
    path = Path(name)
    arrays: dict[str, np.ndarray] = {"x": x, "y": y, "opd": opd}
    if title:
        arrays["title"] = np.asarray(str(title))
    np.savez(path, **arrays)
    return path


def build_wavefront_surface(
    x: np.ndarray,
    y: np.ndarray,
    opd: np.ndarray,
    *,
    warp_factor: float | None = None,
    center_opd: bool = True,
) -> "tuple[Any, float]":
    """Triangulate the pupil samples and warp them into a real 3D surface mesh.

    Returns ``(warped_mesh, warp_factor)``. Pure: no display, no global state."""
    import pyvista as pv  # lazy: keep module import safe without VTK

    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    opd = np.asarray(opd, dtype=float).ravel()
    finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(opd)
    x, y, opd = x[finite], y[finite], opd[finite]
    if x.size < 3:
        raise ValueError("need >= 3 finite wavefront samples to build a 3D surface")

    relief = opd - float(np.mean(opd)) if center_opd else opd
    if warp_factor is None:
        warp_factor = auto_warp_factor(x, y, relief)

    cloud = pv.PolyData(np.column_stack([x, y, np.zeros_like(x)]))
    cloud[SCALAR_NAME] = relief
    surface = cloud.delaunay_2d()
    if surface.n_cells == 0:
        raise RuntimeError("delaunay_2d produced no cells -- degenerate pupil sampling")
    warped = surface.warp_by_scalar(SCALAR_NAME, factor=warp_factor)
    return warped, float(warp_factor)




def _populate_plotter(
    pv: Any,
    warped: Any,
    title: str | None,
    *,
    off_screen: bool,
    window_size: "tuple[int, int]",
) -> Any:
    plotter = pv.Plotter(off_screen=off_screen, window_size=list(window_size))
    plotter.set_background("white")
    plotter.add_mesh(
        warped,
        scalars=SCALAR_NAME,
        cmap="RdBu_r",
        smooth_shading=True,
        scalar_bar_args={"title": SCALAR_NAME, "color": "black"},
    )
    # Outline the pupil rim so the footprint reads cleanly.
    try:
        edges = warped.extract_feature_edges(
            boundary_edges=True,
            feature_edges=False,
            non_manifold_edges=False,
            manifold_edges=False,
        )
        if edges.n_points:
            plotter.add_mesh(edges, color="black", line_width=1.5)
    except Exception:
        pass
    plotter.add_axes(color="black")
    plotter.camera_position = "iso"
    if title:
        plotter.add_text(str(title), font_size=10, color="black")
    return plotter


def render_wavefront_surface_to_png(
    x: np.ndarray,
    y: np.ndarray,
    opd: np.ndarray,
    path: "str | Path",
    *,
    title: str | None = None,
    window_size: "tuple[int, int]" = (960, 720),
    warp_factor: float | None = None,
) -> "tuple[Path, float]":
    """Off-screen render of the 3D surface to a PNG (export + regression)."""
    import pyvista as pv

    pv.OFF_SCREEN = True
    warped, factor = build_wavefront_surface(x, y, opd, warp_factor=warp_factor)
    plotter = _populate_plotter(pv, warped, title, off_screen=True, window_size=window_size)
    out = Path(path)
    plotter.screenshot(str(out))
    plotter.close()
    return out, factor


def show_wavefront_surface(
    x: np.ndarray,
    y: np.ndarray,
    opd: np.ndarray,
    *,
    title: str | None = None,
    window_size: "tuple[int, int]" = (960, 720),
    warp_factor: float | None = None,
) -> float:
    """Open the interactive 3D window (blocking). The Tk UI launches this in a
    subprocess via ``main`` so it never blocks the GUI event loop."""
    import pyvista as pv

    warped, factor = build_wavefront_surface(x, y, opd, warp_factor=warp_factor)
    plotter = _populate_plotter(pv, warped, title, off_screen=False, window_size=window_size)
    plotter.show(title=str(title) if title else "Wavefront 3D")
    return factor


def main(argv: "list[str] | None" = None) -> int:
    """Subprocess entry point: ``python -m KrakenOS.UI.services.wavefront_3d_view DATA.npz``
    where DATA.npz holds ``x``, ``y``, ``opd`` and optional ``title``."""
    import argparse

    parser = argparse.ArgumentParser(description="Interactive 3D wavefront surface")
    parser.add_argument("data", help="path to an .npz with x, y, opd (and optional title)")
    args = parser.parse_args(argv)

    payload = np.load(args.data, allow_pickle=True)
    title = str(payload["title"]) if "title" in payload.files else None
    show_wavefront_surface(payload["x"], payload["y"], payload["opd"], title=title)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
