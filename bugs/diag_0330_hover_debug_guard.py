"""bugs/0330 -- display-free guard for the opening-hover projection instrumentation.

The 0330 live miss (LED clear-aperture square resolves the whole panel F005 live,
yet the square F053 headless at the SAME camera + render size) can only be a
projection/size/DPI difference at the LIVE pick instant. A single before-flag
screenshot cannot carry that, so the opening-loop hover snap now stashes what it
SAW -- render/renderer/widget sizes, the cursor, and each mined opening's PROJECTED
centroid + its pixel distance to the cursor -- onto ``inspector._last_opening_hover_debug``,
which ``flag_bug`` persists into ``state.json`` (``opening_hover_debug``).

This guard locks that contract WITHOUT a display:
  A. ``_stash_opening_hover_debug`` records the three sizes, the cursor, the loop
     count, the chosen face, and per-loop projected centroid + distance -- a loop
     projecting ONTO the cursor gets ~0 px, a far loop gets a large distance.
  B. end-to-end through ``_opening_loop_hover_pick`` (with the loop miner + snap
     patched to fakes) the stash lands on the inspector with the chosen face -- so
     a real ``flag_bug`` will actually find it.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from KrakenOS.UI.services import open3d_round_lens_pick as pick_mod
from KrakenOS.UI.services.open3d_round_lens_pick import (
    _opening_loop_hover_pick,
    _stash_opening_hover_debug,
)


def _fake_loop(face_index: int, centroid, perimeter: float):
    return SimpleNamespace(
        face_index=int(face_index),
        centroid=np.asarray(centroid, dtype=float),
        perimeter=float(perimeter),
        area=float(perimeter) ** 2 / 16.0,
        points=np.zeros((4, 3), dtype=float),
    )


def _fake_inspector(rw_size=(1163, 904), viewport=(1163, 904), widget=(1163, 904)):
    render_window = SimpleNamespace(GetSize=lambda: tuple(rw_size))
    vtk_widget = SimpleNamespace(
        GetRenderWindow=lambda: render_window,
        winfo_width=lambda: int(widget[0]),
        winfo_height=lambda: int(widget[1]),
    )
    renderer = SimpleNamespace(GetSize=lambda: tuple(viewport))
    # Orthographic identity projector: world (x, y) -> screen (x, y).
    return SimpleNamespace(
        _vtk_widget=vtk_widget,
        _renderer=renderer,
        _world_to_display_2d=lambda p: np.asarray(p, dtype=float).reshape(-1)[:2],
        _last_opening_hover_debug=None,
    )


def _check_a() -> list[str]:
    fails: list[str] = []
    cursor = (432.0, 428.0)
    square = _fake_loop(53, (432.0, 428.0, 0.0), 176.6)   # projects ONTO the cursor
    far = _fake_loop(5, (900.0, 200.0, 0.0), 640.0)       # projects far away
    insp = _fake_inspector()
    project = insp._world_to_display_2d
    _stash_opening_hover_debug(insp, cursor, [square, far], project, square)
    dbg = insp._last_opening_hover_debug

    if not isinstance(dbg, dict):
        return ["FAIL(A): stash did not produce a dict"]
    if dbg.get("cursor_xy") != [432.0, 428.0]:
        fails.append(f"FAIL(A): cursor_xy={dbg.get('cursor_xy')!r} (want [432.0, 428.0])")
    if dbg.get("render_window_size") != [1163, 904]:
        fails.append(f"FAIL(A): render_window_size={dbg.get('render_window_size')!r} (want [1163, 904])")
    if dbg.get("renderer_viewport_size") != [1163, 904]:
        fails.append(f"FAIL(A): renderer_viewport_size={dbg.get('renderer_viewport_size')!r}")
    if dbg.get("widget_logical_size") != [1163, 904]:
        fails.append(f"FAIL(A): widget_logical_size={dbg.get('widget_logical_size')!r}")
    if dbg.get("n_loops") != 2:
        fails.append(f"FAIL(A): n_loops={dbg.get('n_loops')!r} (want 2)")
    if dbg.get("chosen_face_index") != 53:
        fails.append(f"FAIL(A): chosen_face_index={dbg.get('chosen_face_index')!r} (want 53)")

    rows = {int(r["face_index"]): r for r in dbg.get("loops", []) if "face_index" in r}
    sq = rows.get(53, {})
    fa = rows.get(5, {})
    if sq.get("centroid_dist_px") != 0.0:
        fails.append(f"FAIL(A): square centroid_dist_px={sq.get('centroid_dist_px')!r} (want 0.0)")
    if not (isinstance(fa.get("centroid_dist_px"), float) and fa["centroid_dist_px"] > 100.0):
        fails.append(f"FAIL(A): far centroid_dist_px={fa.get('centroid_dist_px')!r} (want > 100)")
    if sq.get("perimeter") != 176.6:
        fails.append(f"FAIL(A): square perimeter={sq.get('perimeter')!r} (want 176.6)")
    return fails


def _check_b(monkeypatched) -> list[str]:
    fails: list[str] = []
    cursor = (432.0, 428.0)
    square = _fake_loop(53, (432.0, 428.0, 0.0), 176.6)
    far = _fake_loop(5, (900.0, 200.0, 0.0), 640.0)

    insp = _fake_inspector()
    insp.editor = SimpleNamespace(
        _transformed_imported_step_mesh_for_label=lambda label: object()  # non-None mesh
    )
    insp._opening_loop_hover_feature = lambda label, loop: {"face_id": f"F{loop.face_index:03d}"}

    monkeypatched(lambda mesh: [square, far], lambda loops, xy, proj, **kw: square)

    feature = _opening_loop_hover_pick(insp, "led", cursor)
    dbg = insp._last_opening_hover_debug
    if not isinstance(dbg, dict):
        return ["FAIL(B): _opening_loop_hover_pick left no debug stash on the inspector"]
    if dbg.get("chosen_face_index") != 53:
        fails.append(f"FAIL(B): stashed chosen_face_index={dbg.get('chosen_face_index')!r} (want 53)")
    if not (isinstance(feature, dict) and feature.get("face_id") == "F053"):
        fails.append(f"FAIL(B): pick returned {feature!r} (want the square F053 feature)")
    return fails


def main() -> int:
    failures: list[str] = []
    failures += _check_a()

    # Patch the loop miner + snap that _opening_loop_hover_pick imports at call
    # time (from KrakenOS.UI.services.open3d_opening_loops import ...).
    import KrakenOS.UI.services.open3d_opening_loops as loops_mod

    orig_loops = loops_mod.opening_loops_for_mesh
    orig_nearest = loops_mod.nearest_opening_loop

    def _install(loops_fn, nearest_fn):
        loops_mod.opening_loops_for_mesh = loops_fn
        loops_mod.nearest_opening_loop = nearest_fn

    try:
        failures += _check_b(_install)
    finally:
        loops_mod.opening_loops_for_mesh = orig_loops
        loops_mod.nearest_opening_loop = orig_nearest

    if failures:
        print("RESULT: FAIL")
        for line in failures:
            print("  " + line)
        return 1
    print("RESULT: PASS")
    print("  A: _stash_opening_hover_debug records sizes + cursor + per-loop projected centroid/distance + chosen face")
    print("  B: _opening_loop_hover_pick lands the debug stash on the inspector (flag_bug will find it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
