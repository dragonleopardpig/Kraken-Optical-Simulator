#!/usr/bin/env python3
"""Display-free guard for the manual Measure-tool overlay controls
(bugs/0108: "the manual measurement, can't delete or hide by selection" and
"manual measurement, mouse hover over edge or surface is not highlighting").

Two capabilities:

  1. Per-measurement delete / hide. Each recorded measurement carries a stable
     ``id``; ``_hidden_measure_segments`` is a set of those ids. A right-click on
     a measurement opens a menu ("Delete this measurement" / "Hide this
     measurement" / "Show all measurements"). ``_refresh_measure_overlays`` skips
     hidden ids. Because the hidden set keys on the stable id (not the list
     index), hiding survives a delete that shifts indices.

  2. Hover highlight. While the Measure tool is armed, the edge/surface under the
     cursor is highlighted (the gold STEP-face outline / row highlight) via a
     ``_measure_pick_mode`` branch in the interaction service's ``_on_mouse_move``
     that calls ``_update_measure_hover_highlight``.

What it checks:
  A. Functional id-based delete/hide: toggle/delete/show-all manipulate
     ``_measure_segments`` + ``_hidden_measure_segments`` correctly, and a hide
     survives a delete that shifts list indices.
  B. Draw loop (source): ``_refresh_measure_overlays`` skips hidden ids.
  C. Right-click menu (source): ``_show_surface_function_context_menu`` calls
     ``_maybe_show_measure_menu``; the menu offers Delete / Hide / Show all.
  D. Stable id (source): ``_record_measure_point`` assigns ``seg["id"]``.
  E. Hover (source): the interaction ``_on_mouse_move`` has a ``_measure_pick_mode``
     branch that calls ``_update_measure_hover_highlight``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_measure_overlay_visibility

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types


def _fake_inspector(segments):
    """A bare object that borrows the unbound Measure methods. The real methods
    only touch ``_measure_segments`` / ``_hidden_measure_segments`` plus a couple
    of side-effecting collaborators (overlay refresh / status / badge), which we
    stub so the pure hide/delete logic runs without a Tk/VTK inspector."""
    fake = types.SimpleNamespace()
    fake._measure_segments = segments
    fake._hidden_measure_segments = set()
    fake.status_var = types.SimpleNamespace(set=lambda *_a, **_k: None)
    fake._refresh_measure_overlays = lambda *a, **k: None
    fake._update_mode_badge = lambda *a, **k: None
    return fake


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService
    from KrakenOS.UI.services.open3d_interaction import Open3DInteractionService

    failures: list[str] = []

    # A) Functional id-based delete/hide.
    for name in (
        "delete_measure_segment",
        "toggle_measure_segment_hidden",
        "show_all_measure_segments",
        "hide_all_measure_segments",
        "_measure_segment_index_near_display_xy",
        "_measure_segment_offset_endpoints",
        "_update_measure_hover_highlight",
        "_maybe_show_measure_menu",
        "_show_measure_menu",
    ):
        if not hasattr(Kraken3DInspector, name):
            failures.append(f"FAIL: Kraken3DInspector.{name} is missing")

    if not failures:
        toggle = Kraken3DInspector.toggle_measure_segment_hidden
        delete = Kraken3DInspector.delete_measure_segment
        show_all = Kraken3DInspector.show_all_measure_segments
        hide_all = Kraken3DInspector.hide_all_measure_segments

        fake = _fake_inspector([{"id": 0}, {"id": 1}, {"id": 2}])
        toggle(fake, 1)  # hide id 1 (the middle row)
        if fake._hidden_measure_segments != {1}:
            failures.append(f"FAIL: hiding row 1 should hide id 1, got {fake._hidden_measure_segments}")
        # Deleting row 0 shifts list indices (id 1 moves to index 0). The hidden
        # set keys on the stable id, so id 1 must STAY hidden.
        delete(fake, 0)
        if [s["id"] for s in fake._measure_segments] != [1, 2]:
            failures.append(f"FAIL: delete row 0 should leave ids [1, 2], got {[s['id'] for s in fake._measure_segments]}")
        if fake._hidden_measure_segments != {1}:
            failures.append(
                "FAIL: a hidden measurement must stay hidden after a delete shifts "
                f"indices, got {fake._hidden_measure_segments}")
        # id 1 is now at list index 0 -- un-hiding it must clear the set.
        toggle(fake, 0)
        if fake._hidden_measure_segments:
            failures.append(f"FAIL: un-hiding id 1 should empty the hidden set, got {fake._hidden_measure_segments}")
        toggle(fake, 1)  # hide id 2
        show_all(fake)
        if fake._hidden_measure_segments:
            failures.append(f"FAIL: show_all_measure_segments must clear the hidden set, got {fake._hidden_measure_segments}")

        # Hide-all in one go: every stable id lands in the hidden set; show-all clears.
        fake_all = _fake_inspector([{"id": 3}, {"id": 7}, {"id": 9}])
        hide_all(fake_all)
        if fake_all._hidden_measure_segments != {3, 7, 9}:
            failures.append(f"FAIL: hide_all_measure_segments must hide every id, got {fake_all._hidden_measure_segments}")
        show_all(fake_all)
        if fake_all._hidden_measure_segments:
            failures.append(f"FAIL: show_all after hide_all must clear the hidden set, got {fake_all._hidden_measure_segments}")

        # Deleting the last visible measurement must also drop its id from hidden.
        fake2 = _fake_inspector([{"id": 5}])
        toggle(fake2, 0)
        delete(fake2, 0)
        if fake2._measure_segments or fake2._hidden_measure_segments:
            failures.append("FAIL: deleting a hidden measurement must drop it from both lists")

    # B) Draw loop skips hidden ids.
    refresh_src = inspect.getsource(Kraken3DInspector._refresh_measure_overlays)
    if "_hidden_measure_segments" not in refresh_src:
        failures.append(
            "FAIL: _refresh_measure_overlays must skip hidden measurements "
            "(_hidden_measure_segments) so a hidden one is not drawn")

    # C) Right-click menu wiring.
    ctx_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "_maybe_show_measure_menu" not in ctx_src:
        failures.append(
            "FAIL: the right-click context menu must offer the measure menu "
            "(_maybe_show_measure_menu)")
    menu_src = inspect.getsource(Kraken3DInspector._show_measure_menu)
    for label in ("Delete this measurement", "Hide this measurement", "Hide all measurements", "Show all measurements"):
        if label not in menu_src:
            failures.append(f"FAIL: the measure menu must offer '{label}'")

    # D) Stable id assigned at record time.
    record_src = inspect.getsource(Kraken3DInspector._record_measure_point)
    if '"id"' not in record_src:
        failures.append("FAIL: _record_measure_point must assign a stable seg['id']")

    # E) Hover highlight branch.
    move_src = inspect.getsource(Open3DInteractionService._on_mouse_move)
    if "_measure_pick_mode" not in move_src or "_update_measure_hover_highlight" not in move_src:
        failures.append(
            "FAIL: _on_mouse_move must hover-highlight in measure mode "
            "(_measure_pick_mode -> _update_measure_hover_highlight)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] manual Measure overlay delete/hide + hover highlight")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] each manual measurement can be deleted/hidden by selection + "
          "edge/surface hover highlights while measuring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
