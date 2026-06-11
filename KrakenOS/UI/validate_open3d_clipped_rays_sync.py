"""Guard for the synced Open 3D "Show clipped rays" toggle (bugs/0061).

The embedded Open 3D inspector had no "Show clipped rays" control even though
its ray-line filter already honours the editor's ``show_clipped_rays_var`` -- the
same ``tk.BooleanVar`` the 2D editor binds. With no 3D toggle, escaped/stray rays
(e.g. an LED fan that misses the lens entirely) always rendered in 3D, and the
"Miss" overlay toggle (terminal diagnostics) only gates endpoint disks +
missed-detector crosshairs, never the ray lines -- so toggling it left the stray
lines on screen.

The fix adds a "Clipped" checkbutton to the 3D Overlays menu bound to the shared
``show_clipped_rays_var`` (via ``_editor_var``), so the 3D filter and the 2D
"Show clipped rays" checkbox stay in sync both ways (the bug-0059 pattern).

Checks
------
Source contracts (always run, no display):
A. the 3D Overlays menu wires a "Clipped" ``MenuCheckbutton`` to
   ``_editor_var("show_clipped_rays_var")`` with command ``_on_clipped_rays_changed``.
B. the inspector defines ``_on_clipped_rays_changed`` and it both marks the 2D
   plot pending and refreshes the 3D scene.
C. the 2D trace-display panel still binds the same ``show_clipped_rays_var``.

Behaviour (display-free):
D. ``_on_clipped_rays_changed`` calls ``editor._mark_plot_update_pending`` and the
   scene refresh exactly once each.
E. ``Open3DLiveControlsPanel.editor_var("show_clipped_rays_var")`` returns the very
   object the editor holds (shared var -> bidirectional sync).
F. the 3D ray-line filter honours the var: with escaped-non-folded strays present,
   OFF hides them while keeping detector hits / misses / stops / folded branches,
   and ON keeps everything.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_clipped_rays_sync

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT_DIR = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts"
_FILTER_LAYOUT = "machine_vision_150mm_datasheet_1x.py"


def _snapshot_editor_for(fname: str):
    from KrakenOS.UI.render_layout_snapshot import (
        _load_layout_module,
        _rows_from_layout_info,
        _snapshot_editor,
    )

    path = LAYOUT_DIR / fname
    module = _load_layout_module(path)
    surfaces = list(getattr(module, "SURFACES", []) or [])
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    rows = _rows_from_layout_info({"surfaces": surfaces})
    editor = _snapshot_editor(rows, settings)
    editor._normalize_special_rows()
    return editor


def _synthetic_paths():
    """Build five RayPath3D records, one per terminal class.

    The escaped-non-folded path is the only one the clipped filter hides; the
    folded escape (beam-splitter style second branch), the detector miss, the
    detector hit, and the aperture stop must all survive (bugs 0016/0018/0022).
    """
    from KrakenOS.UI.scene_geometry import RayEvent3D, RayPath3D

    def _terminal(reason: str) -> RayEvent3D:
        return RayEvent3D(event_kind="terminal", termination_reason=reason)

    def _fold() -> RayEvent3D:
        return RayEvent3D(event_kind="surface", event_type="reflect", surface_name="beam_splitter")

    pts = np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 10.0]], dtype=float)

    def _path(index: int, events) -> RayPath3D:
        return RayPath3D(ray_index=index, wavelength=0.55, color="#39FF14",
                         points_world=pts.copy(), events=list(events))

    return {
        "escaped_nofold": _path(0, [_terminal("no_hit")]),
        "escaped_folded": _path(1, [_fold(), _terminal("no_hit")]),
        "missed_detector": _path(2, [_terminal("missed_detector")]),
        "hit_detector": _path(3, [_terminal("detector")]),
        "stopped": _path(4, [_terminal("aperture_stop")]),
    }


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    def _fail(msg: str) -> None:
        nonlocal passed
        notes.append(f"FAIL: {msg}")
        passed = False

    # --- A: Overlays-menu wiring -----------------------------------------
    from KrakenOS.UI.panels.open3d_top_controls import Open3DTopControlsPanel
    try:
        toolbar_src = inspect.getsource(Open3DTopControlsPanel.build_view_toolbar)
    except Exception as exc:
        toolbar_src = ""
        _fail(f"cannot read build_view_toolbar: {exc!r}")
    if 'MenuCheckbutton("Clipped"' not in toolbar_src:
        _fail("Overlays menu has no \"Clipped\" MenuCheckbutton")
    if '_editor_var("show_clipped_rays_var")' not in toolbar_src:
        _fail("Clipped toggle is not bound to the shared show_clipped_rays_var via _editor_var")
    if "_on_clipped_rays_changed" not in toolbar_src:
        _fail("Clipped toggle is not wired to _on_clipped_rays_changed")

    # --- B: inspector handler exists + marks 2D + refreshes 3D -----------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    if not hasattr(Kraken3DInspector, "_on_clipped_rays_changed"):
        _fail("inspector missing _on_clipped_rays_changed")
        handler_src = ""
    else:
        try:
            handler_src = inspect.getsource(Kraken3DInspector._on_clipped_rays_changed)
        except Exception as exc:
            handler_src = ""
            _fail(f"cannot read _on_clipped_rays_changed: {exc!r}")
    if "_mark_plot_update_pending" not in handler_src:
        _fail("_on_clipped_rays_changed does not mark the 2D plot pending")
    if "_on_scene_visibility_changed" not in handler_src and "refresh_from_editor" not in handler_src:
        _fail("_on_clipped_rays_changed does not refresh the 3D scene")

    # --- C: 2D panel still binds the same var ----------------------------
    from KrakenOS.UI.panels.main_trace_display_controls import MainTraceDisplayControlsPanel
    try:
        panel_2d_src = inspect.getsource(MainTraceDisplayControlsPanel.build)
    except Exception as exc:
        panel_2d_src = ""
        _fail(f"cannot read 2D trace-display build: {exc!r}")
    if "show_clipped_rays_var" not in panel_2d_src:
        _fail("2D trace-display panel no longer binds show_clipped_rays_var")

    # --- D: handler behaviour (display-free stub) ------------------------
    calls = {"mark": 0, "refresh": 0}
    editor_stub = types.SimpleNamespace(
        _mark_plot_update_pending=lambda: calls.__setitem__("mark", calls["mark"] + 1),
        append_debug=lambda _m: None,
    )
    insp_stub = types.SimpleNamespace(
        editor=editor_stub,
        _on_scene_visibility_changed=lambda: calls.__setitem__("refresh", calls["refresh"] + 1),
    )
    try:
        Kraken3DInspector._on_clipped_rays_changed(insp_stub)
    except Exception as exc:
        _fail(f"_on_clipped_rays_changed raised on call: {exc!r}")
    if calls != {"mark": 1, "refresh": 1}:
        _fail(f"_on_clipped_rays_changed call counts wrong: {calls}")

    # --- E: shared-var identity (3D toggle == 2D var) --------------------
    from KrakenOS.UI.panels.open3d_live_controls import Open3DLiveControlsPanel
    sentinel = object()
    panel_stub = types.SimpleNamespace(
        editor=types.SimpleNamespace(show_clipped_rays_var=sentinel)
    )
    got = Open3DLiveControlsPanel.editor_var(panel_stub, "show_clipped_rays_var")
    if got is not sentinel:
        _fail("editor_var('show_clipped_rays_var') did not return the editor's own var (sync broken)")

    # --- F: the 3D ray-line filter honours the var -----------------------
    from KrakenOS.UI.scene_geometry import SceneBundle
    if not (LAYOUT_DIR / _FILTER_LAYOUT).exists():
        notes.append(f"SKIP: {_FILTER_LAYOUT} missing -- filter behaviour not exercised")
    else:
        try:
            editor = _snapshot_editor_for(_FILTER_LAYOUT)
            paths = _synthetic_paths()
            bundle = SceneBundle(ray_paths=list(paths.values()))
            editor.show_clipped_rays_var.set(True)
            on = editor._iter_3d_scene_ray_records(scene_bundle=bundle)
            editor.show_clipped_rays_var.set(False)
            off = editor._iter_3d_scene_ray_records(scene_bundle=bundle)
        except Exception as exc:
            _fail(f"filter exercise raised: {exc!r}")
            on = off = None
        if on is not None and off is not None:
            on_idx = {int(r[0]) for r in on}
            off_idx = {int(r[0]) for r in off}
            expected_on = {0, 1, 2, 3, 4}
            expected_off = {1, 2, 3, 4}  # escaped-non-folded (index 0) dropped
            if on_idx != expected_on:
                _fail(f"clipped ON should render all 5 rays, got indices {sorted(on_idx)}")
            if off_idx != expected_off:
                _fail(
                    "clipped OFF should hide only the escaped-non-folded stray, "
                    f"got indices {sorted(off_idx)} (expected {sorted(expected_off)})"
                )

    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        if not note.startswith("FAIL") and not note.startswith("SKIP"):
            print(note)
    if passed:
        print("[PASS] Open 3D synced clipped-rays toggle")
        return 0
    print("[FAIL] Open 3D clipped-rays sync guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
