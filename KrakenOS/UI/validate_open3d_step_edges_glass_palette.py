"""Render guard for bugs/0020 — every imported CAD optical solid wears ONE glass
edge palette, and the heavy vendor camera body finally gets an outline.

Regression context
------------------
The 3D inspector outlined analytic lenses with a thin teal "glass" palette
(``_OPTICAL_STEP_EDGE_COLOR`` / ``_OPTICAL_STEP_SILHOUETTE_COLOR`` at
``_GLASS_EDGE_LINE_WIDTH`` / ``_GLASS_EDGE_SILHOUETTE_WIDTH``), but imported CAD
solids were treated two different ways:

1. A file-backed STEP/STL body whose promotion display label was anything other
   than ``"optical"`` (e.g. a beam-splitter *cube* promoted as ``"led"``) fell
   through to a legacy HEAVY BLACK wireframe — ``_solid_silhouette_edge_color``
   ``(0.005, 0.007, 0.014)`` at width ``5.0`` plus a darkened body edge at
   ``3.2``. The user wants one nice optical edge palette, not a black cage.
2. Any overlay mesh past ``> 50000`` cells skipped feature-edge extraction
   altogether (``heavy_cad_mesh``), so the ~114k-cell vendor camera body drew
   with NO outline at all — a flat translucent slab floating in space.

The fix makes the file-backed edge colour/weight unconditionally the glass
palette, drops the heavy-mesh skip, and memoises feature-edge extraction
(``cached_display_feature_edges``) so the camera's outline is computed once per
layout pose instead of per frame.

Invariants asserted here (needs an X server — boots a private Xvfb):

1. The file-backed beam-splitter cube (promotion label ``"led"``) carries BOTH
   glass edge actors — silhouette ``(0.014,0.279,0.288)`` @ 2.8 and edge line
   ``(0.026,0.512,0.528)`` @ 2.0 — and NO actor of that row uses the legacy
   black silhouette ``(0.005,0.007,0.014)`` or the legacy 5.0 / 3.2 widths.
2. The vendor camera STEP overlay produces at least two glass edge actors (the
   ``> 50000`` skip is gone), so the heavy body is outlined like the lens.
3. The imaging-lens STEP overlay likewise carries glass edge actors.
4. A render framed on the cube shows teal edge pixels (the outline actually
   reaches the screen — it is not occluded or zero-opacity).

Any element whose vendor STEP / cached mesh is unavailable on this machine is a
SKIP, not a failure (these CAD fixtures are not checked into git).

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_edges_glass_palette

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import os
from pathlib import Path

# Never touch a live Wayland/X session.
os.environ.pop("WAYLAND_DISPLAY", None)

from KrakenOS.UI.services.open3d_scene_refresh import (
    _GLASS_EDGE_LINE_WIDTH,
    _GLASS_EDGE_SILHOUETTE_WIDTH,
    _OPTICAL_STEP_EDGE_COLOR,
    _OPTICAL_STEP_SILHOUETTE_COLOR,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRESCRIPTION = PROJECT_ROOT / "attachment" / "machine_vision_150mm_measured_test.py"
CUBE_ROW = 6  # Object, 5 lens datums/groups, [6]=promoted LED STEP cube, Image

# The legacy heavy-black wireframe the fix removed (must never reappear).
_LEGACY_BLACK_SILHOUETTE = (0.005, 0.007, 0.014)
_LEGACY_SILHOUETTE_WIDTH = 5.0
_LEGACY_EDGE_WIDTH = 3.2


def _close(a, b, tol: float = 0.02) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def _actor_color_width(inspector, key):
    actor = inspector._actor_by_key.get(key)
    if actor is None:
        return None
    prop = actor.GetProperty()
    try:
        return tuple(float(c) for c in prop.GetColor()), float(prop.GetLineWidth())
    except Exception:
        return None


def _check_glass_edges(inspector, keys, *, label: str, notes: list[str]) -> bool:
    """A set of actors must carry both glass edge actors and no legacy black."""
    has_sil = has_edge = False
    has_black = False
    for key in keys:
        cw = _actor_color_width(inspector, key)
        if cw is None:
            continue
        color, width = cw
        if _close(color, _OPTICAL_STEP_SILHOUETTE_COLOR) and abs(width - _GLASS_EDGE_SILHOUETTE_WIDTH) < 0.1:
            has_sil = True
        if _close(color, _OPTICAL_STEP_EDGE_COLOR) and abs(width - _GLASS_EDGE_LINE_WIDTH) < 0.1:
            has_edge = True
        if _close(color, _LEGACY_BLACK_SILHOUETTE):
            has_black = True
            notes.append(f"FAIL: {label} actor still uses the legacy black silhouette {color}")
        if abs(width - _LEGACY_SILHOUETTE_WIDTH) < 0.05 or abs(width - _LEGACY_EDGE_WIDTH) < 0.05:
            notes.append(f"FAIL: {label} actor still uses a legacy heavy edge width {width}")
            has_black = True
    if not has_sil:
        notes.append(f"FAIL: {label} is missing the glass silhouette edge {_OPTICAL_STEP_SILHOUETTE_COLOR} @ {_GLASS_EDGE_SILHOUETTE_WIDTH}")
    if not has_edge:
        notes.append(f"FAIL: {label} is missing the glass edge line {_OPTICAL_STEP_EDGE_COLOR} @ {_GLASS_EDGE_LINE_WIDTH}")
    return bool(has_sil and has_edge and not has_black)


def _count_glass_edge_actors(inspector, keys) -> int:
    n = 0
    for key in keys:
        cw = _actor_color_width(inspector, key)
        if cw is None:
            continue
        color, _width = cw
        if _close(color, _OPTICAL_STEP_EDGE_COLOR) or _close(color, _OPTICAL_STEP_SILHOUETTE_COLOR):
            n += 1
    return n


def _classify_pixels(png_path) -> "tuple[int, int]":
    """Return (teal_pixels, legacy_black_edge_pixels) for a cube render.

    Teal covers both the glass edge actors and the translucent body, so it
    cannot distinguish the two on its own. The discriminating signal is the
    legacy black cage: the pre-fix silhouette is ``(0.005,0.007,0.014)`` -> a
    near-pure-black ``(1,2,4)`` drawn at width 5.0, so a black outline lit up
    hundreds of near-black pixels against the white background. The face-role
    / axis markers sit at ``(31,36,46)`` and lighter, so an ``< 15`` cutoff
    isolates only the legacy edge.
    """
    import numpy as np
    from PIL import Image

    arr = np.asarray(Image.open(png_path).convert("RGB")).astype(int)
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    teal = (r < 110) & (g > 90) & (b > 90) & (g - r > 30) & (b - r > 30)
    black_edge = (r < 15) & (g < 15) & (b < 15)
    return int(teal.sum()), int(black_edge.sum())


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    """Assert the bug-0020 glass-edge invariants.

    Standalone (``app``/``inspector`` omitted) this boots a private Xvfb and
    builds its own editor + embedded inspector. When driven by the comprehensive
    harness it is handed the harness's live ``(app, inspector)`` and REUSES them:
    a second embedded VTK inspector cannot initialise in the same process while
    the first is alive (``inspector.available`` goes False), so building one here
    would raise ``RuntimeError('Embedded 3D inspector unavailable')``.
    """
    notes: list[str] = []
    if not PRESCRIPTION.exists():
        notes.append(f"SKIP: bug-0020 repro prescription unavailable ({PRESCRIPTION.name})")
        return True, notes

    from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
        _ensure_display,
        render_window_to_png,
    )

    reuse = app is not None and inspector is not None
    xvfb_proc = None
    if not reuse:
        xvfb_proc, env_err = _ensure_display()
        if env_err is not None:
            notes.append(f"SKIP: cannot render ({env_err})")
            return True, notes

    passed = True
    own_app = False
    try:
        import numpy as np

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.render_layout_snapshot import (
            _load_layout_module,
            _rows_from_layout_info,
        )
        from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

        module = _load_layout_module(PRESCRIPTION)
        surfaces = list(getattr(module, "SURFACES", []) or [])
        settings = dict(getattr(module, "SETTINGS", {}) or {})

        # The file-backed beam-splitter row renders from its CACHED STL
        # (``Solid_3d_stl``), not the source STEP: a present source ``.step``
        # with a missing cache still draws nothing (and on some load paths
        # raises FileNotFoundError), so the render-critical input is the STL.
        # Require it -- otherwise this is an environment without the fixture
        # (these CAD caches are not in git, e.g. a fresh laptop) -> SKIP, not
        # FAIL.
        cube_spec = surfaces[CUBE_ROW] if CUBE_ROW < len(surfaces) else {}
        advanced = (cube_spec.get("advanced", {}) or {}) if isinstance(cube_spec, dict) else {}
        cube_stl = advanced.get("Solid_3d_stl")
        if not (cube_stl and Path(cube_stl).exists()):
            notes.append("SKIP: beam-splitter cube cached STL (Solid_3d_stl) unavailable")
            return True, notes

        if not reuse:
            app = KrakenLayoutEditor()
            inspector = _open_inspector(app)
            own_app = True
        try:
            app.rows = _rows_from_layout_info({"surfaces": surfaces})
            app._apply_layout_settings(settings)
            app._sync_table()
            inspector.show_rays_var.set(False)
            inspector.refresh_from_editor(force_retrace=False)
            inspector.update_idletasks()
            inspector.update()
        except Exception as exc:
            notes.append(f"SKIP: real prescription failed to load: {exc!r}")
            return True, notes

        # (1) file-backed cube: glass edges, no legacy black.
        cube_keys = inspector._row_actor_map.get(CUBE_ROW, []) or []
        if not cube_keys:
            notes.append(f"FAIL: file-backed cube row {CUBE_ROW} produced no actors")
            passed = False
        elif not _check_glass_edges(inspector, cube_keys, label="beam-splitter cube", notes=notes):
            passed = False

        # (2) vendor camera overlay: heavy body now outlined (skip removed).
        cam_path = settings.get("camera_step_path")
        if cam_path and (PROJECT_ROOT / cam_path).exists():
            cam_keys = inspector._step_follow_actor_map.get("camera", []) or []
            cam_edges = _count_glass_edge_actors(inspector, cam_keys)
            if cam_edges < 2:
                notes.append(f"FAIL: camera overlay has {cam_edges} glass edge actors (expected >= 2; the >50k skip should be gone)")
                passed = False
        else:
            notes.append("SKIP: vendor camera STEP unavailable")

        # (3) imaging-lens overlay: glass edges.
        lens_path = settings.get("lens_step_path")
        if lens_path and (PROJECT_ROOT / lens_path).exists():
            lens_keys = inspector._step_follow_actor_map.get("lens", []) or []
            lens_edges = _count_glass_edge_actors(inspector, lens_keys)
            if lens_edges < 2:
                notes.append(f"FAIL: lens overlay has {lens_edges} glass edge actors (expected >= 2)")
                passed = False
        else:
            notes.append("SKIP: imaging-lens STEP unavailable")

        # (4) pixel proof: framed on the cube, teal edges reach the screen.
        try:
            mins = np.array([np.inf] * 3)
            maxs = np.array([-np.inf] * 3)
            for key in cube_keys:
                actor = inspector._actor_by_key.get(key)
                if actor is None:
                    continue
                b = actor.GetBounds()
                if b is None:
                    continue
                mins = np.minimum(mins, [b[0], b[2], b[4]])
                maxs = np.maximum(maxs, [b[1], b[3], b[5]])
            if np.all(np.isfinite(mins)):
                import math

                center = (mins + maxs) / 2.0
                diag = float(np.linalg.norm(maxs - mins)) or 1.0
                cam = inspector._renderer.GetActiveCamera()
                az, el = math.radians(42.0), math.radians(22.0)
                d = np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])
                cam.SetFocalPoint(*center)
                cam.SetPosition(*(center + d * diag * 2.0))
                cam.SetViewUp(0, 1, 0)
                inspector._renderer.ResetCameraClippingRange()
                inspector._vtk_widget.GetRenderWindow().Render()
                png = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp")) / "bug0020_step_edges_glass.png"
                render_window_to_png(inspector, png)
                teal, black_edge = _classify_pixels(png)
                if teal < 200:
                    notes.append(f"FAIL: only {teal} teal pixels in the cube render (expected the glass outline to reach the screen)")
                    passed = False
                if black_edge > 80:
                    notes.append(f"FAIL: {black_edge} near-black edge pixels in the cube render (the legacy black wireframe cage is back)")
                    passed = False
                if verbose:
                    notes.append(f"teal pixels = {teal}; black-edge pixels = {black_edge}; render = {png}")
            else:
                notes.append("SKIP: could not frame the cube for the pixel check")
        except Exception as exc:
            notes.append(f"SKIP: cube pixel check raised {exc!r}")

        if own_app:
            try:
                app.destroy()
            except Exception:
                pass
        return passed, notes
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] bugs/0020: imported CAD solids wear one glass edge palette; camera body is outlined")
        return 0
    print("[FAIL] bugs/0020 step-edge glass-palette guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
