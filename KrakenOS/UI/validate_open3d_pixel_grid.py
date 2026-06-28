"""Display-free guard for the camera pixel-grid overlay (idea #1: the spot on real pixels).

When a vendor camera is registered the detector carries a pixel pitch (the Allied-Vision /
SVS 25 MP is 5120x5120 @ 4.50 um). The "Pixel grid" overlay draws that pixel lattice under
each spot -- true-aligned (lines on real k*pitch boundaries) and magnified about the chief
by the spot-map factor -- so the spot footprint reads in pixels.

This guard pins (headless, no VTK):

  * PURE GEOMETRY: span_px == 2*extent/pitch (factor cancels), the lattice is true-aligned
    (a chief on a pixel boundary sits ON a grid line; a chief mid-pixel sits half a
    magnified pixel away -> sub-pixel honesty), adjacent lines are pitch*factor apart,
    magnification preserved, degenerate / no-pitch input returns None.
  * INTEGRATION on the Zemax double gauss + the registered 25 MP camera: the spot spans a
    sane handful of pixels (4.5 um pitch), grids == spots, resolution carried; NO camera
    registered -> None.
  * RENDER-ONLY / TOGGLE: refresh_scene reads show_pixel_grid_var and calls
    _add_pixel_grid_overlays; that renderer never rebuilds the system, does not shadow the
    pv/np/vtkBillboardTextActor3D globals; the right-click menu offers it.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_pixel_grid

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""

from __future__ import annotations

import inspect
import io
from contextlib import redirect_stderr, redirect_stdout

import numpy as np

from KrakenOS.UI.camera_database import camera_names, camera_pixel_pitch_mm
from KrakenOS.UI.layout_editor import Kraken3DInspector
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService
from KrakenOS.UI.services.pixel_grid import build_pixel_grid_overlay
from KrakenOS.UI.validate_open3d_best_focus_surface import _build_scene_bundle_for_double_gauss


def _v_line_u_offsets(grid, center, u_axis: int) -> list[float]:
    return [float(np.asarray(seg, dtype=float)[0, u_axis]) - float(center[u_axis]) for seg in grid["v_lines"]]


def _check_pure_geometry(failures: list[str]) -> None:
    center = np.array([0.0, 0.0, 100.0])
    normal = np.array([0.0, 0.0, 1.0])
    tangent = np.array([1.0, 0.0, 0.0])  # -> u = +x, so display-u offset is the x coordinate
    px = 0.0045
    factor = 200.0
    extent = 4.0 * px  # spot radius 4 px -> diameter 8 px

    captured_du: list[float] = []
    for cu_frac, on_boundary in ((5.0, True), (5.5, False)):
        cu = cu_frac * px
        spec = build_pixel_grid_overlay(
            [[cu, 0.0]], [extent], center=center, normal=normal, tangent=tangent,
            pitch_mm=(px, px), magnification=factor, image_radius=10.0,
        )
        if not spec:
            failures.append(f"PURE: build returned None for a valid spot (cu={cu_frac}px)")
            return
        if not np.isclose(spec["span_px_max"], 2.0 * extent / px, rtol=1e-6):
            failures.append(f"PURE: span_px {spec['span_px_max']:.4g} != 2*extent/pitch {2*extent/px:.4g}")
        if not np.isclose(float(spec["magnification"]), factor):
            failures.append("PURE: magnification not preserved")
        du = _v_line_u_offsets(spec["grids"][0], center, 0)
        nearest = min(abs(cu - d) for d in du)
        if on_boundary and nearest > 1e-6:
            failures.append(f"PURE: a chief on a pixel boundary is not on a grid line (nearest {nearest:.3g})")
        if (not on_boundary) and not np.isclose(nearest, 0.5 * px * factor, rtol=1e-3):
            failures.append(f"PURE: a mid-pixel chief is not half a magnified pixel from a line ({nearest:.4g} vs {0.5*px*factor:.4g})")
        captured_du = du

    spacing = np.diff(np.sort(captured_du))
    if spacing.size and not np.allclose(spacing, px * factor, rtol=1e-5):
        failures.append(f"PURE: adjacent pixel lines are not pitch*factor apart ({float(spacing[0]):.4g} vs {px*factor:.4g})")

    if build_pixel_grid_overlay([[0.0, 0.0]], [extent], center=center, normal=normal, tangent=tangent, pitch_mm=(0.0, 0.0), magnification=factor) is not None:
        failures.append("PURE: a zero pixel pitch did not return None")
    if build_pixel_grid_overlay([], [], center=center, normal=normal, tangent=tangent, pitch_mm=(px, px), magnification=factor) is not None:
        failures.append("PURE: no spots did not return None")

    # Sub-pixel spots (focused system): the spot map's huge magnification makes one pixel
    # bigger than the image -> suppress the giant lattice, flag too_coarse, no grids.
    field = np.array([[0.0, 0.0], [5.0, 0.0], [-5.0, 0.0], [0.0, 5.0], [0.0, -5.0]])  # ~5 mm spread
    coarse = build_pixel_grid_overlay(field, [0.0003] * 5, center=center, normal=normal, tangent=tangent, pitch_mm=(px, px), magnification=1558.0)
    if not coarse or not coarse.get("too_coarse") or (coarse.get("grids") or []):
        failures.append("PURE: sub-pixel spots did not suppress the lattice (too_coarse)")
    normal_spots = build_pixel_grid_overlay(field, [0.18] * 5, center=center, normal=normal, tangent=tangent, pitch_mm=(px, px), magnification=25.0)
    if not normal_spots or normal_spots.get("too_coarse") or not (normal_spots.get("grids") or []):
        failures.append("PURE: multi-pixel spots were wrongly suppressed as too_coarse")

    # bugs/pixel-grid-beyond-detector-box: the magnified lattice must be CLIPPED to the sensor box
    # (the orange detector frame) so an edge spot's x-factor patch never spills past it.
    edge = np.array([[0.0, 0.0], [10.0, 10.0]])  # a corner-field spot near a 11.52 mm sensor edge
    half = 11.52

    def _grid_uv_max(spec):
        mu = mv = 0.0
        for g in (spec.get("grids") or []):
            for ln in (g.get("h_lines") or []) + (g.get("v_lines") or []):
                arr = np.asarray(ln, dtype=float)
                mu = max(mu, float(np.max(np.abs(arr[:, 0] - center[0]))))  # u = +x
                mv = max(mv, float(np.max(np.abs(arr[:, 1] - center[1]))))  # v = +y
        return mu, mv

    unclipped = build_pixel_grid_overlay(edge, [0.05, 0.05], center=center, normal=normal, tangent=tangent, pitch_mm=(px, px), magnification=210.0)
    clipped = build_pixel_grid_overlay(edge, [0.05, 0.05], center=center, normal=normal, tangent=tangent, pitch_mm=(px, px), magnification=210.0, sensor_half_uv=(half, half))
    if unclipped and clipped:
        umu, umv = _grid_uv_max(unclipped)
        cmu, cmv = _grid_uv_max(clipped)
        if not (umu > half + 1.0 and umv > half + 1.0):
            failures.append(f"PURE: the unclipped edge patch should spill past the sensor box ({umu:.3g},{umv:.3g} vs {half})")
        if cmu > half + 1e-6 or cmv > half + 1e-6:
            failures.append(f"PURE: clipped lattice spills past the sensor box ({cmu:.4g},{cmv:.4g} > {half})")
        if not any((g.get("h_lines") or g.get("v_lines")) for g in (clipped.get("grids") or [])):
            failures.append("PURE: clipping emptied the lattice (should keep the in-box lines)")
    else:
        failures.append("PURE: edge-spot clip build returned None")


def _camera_with_pitch() -> "str | None":
    preferred = [n for n in camera_names() if camera_pixel_pitch_mm(n) is not None and "25" in n]
    if preferred:
        return preferred[0]
    any_with_pitch = [n for n in camera_names() if camera_pixel_pitch_mm(n) is not None]
    return any_with_pitch[0] if any_with_pitch else None


def _check_integration(failures: list[str], notes: list[str]) -> None:
    editor, system, bundle = _build_scene_bundle_for_double_gauss()
    if editor is None:
        notes.append("SKIP integration: double-gauss layout/bundle unavailable")
        return

    # No camera registered -> nothing to draw.
    if editor.pixel_grid_overlay_spec(system, bundle) is not None:
        failures.append("INTEGRATION: pixel grid drew without a registered camera")

    camera = _camera_with_pitch()
    if camera is None:
        notes.append("SKIP integration: no camera with a pixel pitch in the DB")
        return
    editor.camera_model_var = type("_V", (), {"get": staticmethod(lambda: camera)})()

    capture = io.StringIO()
    with redirect_stdout(capture), redirect_stderr(capture):
        spec = editor.pixel_grid_overlay_spec(system, bundle)
    if spec is None:
        failures.append(f"INTEGRATION: pixel grid None with {camera} registered")
        return
    pitch = camera_pixel_pitch_mm(camera)
    if not np.isclose(spec["pitch_um"][0], pitch[0] * 1000.0, rtol=1e-6):
        failures.append("INTEGRATION: pitch_um does not match the camera record")
    span_lo = float(spec.get("span_px_min", 0.0))
    span_hi = float(spec.get("span_px_max", 0.0))
    if not (0.5 < span_lo <= span_hi < 1000.0):
        failures.append(f"INTEGRATION: implausible spot span ({span_lo:.2g}..{span_hi:.2g} px)")
    n_grids = len(spec.get("grids") or [])
    if n_grids < 5:
        failures.append(f"INTEGRATION: too few pixel grids ({n_grids})")
    notes.append(f"integration: {camera} {spec['pitch_um'][0]:.3g}µm -> spot ≈ {span_lo:.0f}-{span_hi:.0f} px over {n_grids} fields")


def _check_source_contracts(failures: list[str]) -> None:
    refresh_src = inspect.getsource(Open3DSceneRefreshService.refresh_scene)
    if "show_pixel_grid_var" not in refresh_src or "_add_pixel_grid_overlays" not in refresh_src:
        failures.append("CONTRACT: refresh_scene does not gate/call the pixel grid overlay")

    method = Kraken3DInspector._add_pixel_grid_overlays
    add_src = inspect.getsource(method)
    for forbidden in ("build_system(", "_build_preview_system_rays_bundle("):
        if forbidden in add_src:
            failures.append(f"CONTRACT: _add_pixel_grid_overlays references {forbidden!r} -- not render-only")
    shadowed = [g for g in ("pv", "np", "vtkBillboardTextActor3D") if g in method.__code__.co_varnames]
    if shadowed:
        failures.append(f"CONTRACT: _add_pixel_grid_overlays shadows module globals {shadowed}")

    analysis_src = inspect.getsource(Kraken3DInspector._add_image_plane_analysis_menu)
    if "show_pixel_grid_var" not in analysis_src:
        failures.append("CONTRACT: the right-click analyses menu does not offer the pixel grid")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    _check_pure_geometry(failures)
    _check_integration(failures, notes)
    _check_source_contracts(failures)
    return (not failures), (failures + notes)


def main() -> int:
    passed, messages = run_checks()
    for message in messages:
        print(f"  - {message}")
    if not passed:
        print("[FAIL] camera pixel grid (spot footprint on real pixels)")
        return 1
    print("[PASS] camera pixel grid shows the spot footprint on real pixels (idea #1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
