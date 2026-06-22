#!/usr/bin/env python3
"""Display-free guard for the per-dimension Thickness overlay controls
(feature: "each Thickness measurement overlay can be turned off; each blue arrow
can be dragged to point to a desired measured edge/face").

Two capabilities:

  1. Per-row on/off. The blue Thickness dimension arrows are individually
     hideable. `editor._hidden_thickness_dimension_rows` is a persisted set of row
     indices; `add_overlays` skips any hidden row (model thickness untouched). A
     right-click on the arrow toggles it ("Hide this thickness dimension" /
     "Show all thickness dimensions").

  2. Drag-to-point re-anchor. The bugs/0053 re-anchor backend (point a dimension
     endpoint at a picked surface/edge -- MEASUREMENT only, the model is never
     moved) is exposed as a natural gesture: a right-click "Re-anchor to a
     surface/edge…" enters the modal, and a drag of the endpoint onto a face/edge
     commits on release (in addition to the click-move-click path).

What it checks:
  A. Editor toggle semantics: set/toggle/show-all and `_thickness_dimension_is_hidden`
     add, flip, and clear the hidden set correctly.
  B. `add_overlays` consults `_thickness_dimension_is_hidden` (source) so a hidden
     row's arrow is skipped.
  C. Persistence (source): `_collect_layout_settings` serialises
     `hidden_thickness_dimension_rows`; `_apply_layout_settings` restores it onto
     `self.editor._hidden_thickness_dimension_rows`.
  D. Right-click menu (source): the context menu calls
     `_maybe_show_thickness_dimension_menu`, and the menu offers both "Hide this
     thickness dimension" and "Re-anchor to a surface/edge…".
  E. Drag-to-point (source): the left-button release commits the re-anchor on a
     drag (`dimension_anchor_was_drag`), and `_begin_dimension_anchor_pick_for_row`
     enters the modal for a menu-chosen row.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_dimension_visibility

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import contextlib
import inspect
import io

from KrakenOS.UI.validate_open3d_object_plane_after_promote import _editor, _plain_specs


def _toggle_test_editor():
    """A snapshot editor with the visibility set + the side-effecting infra
    (history capture / 3D refresh) stubbed -- the snapshot harness skips __init__,
    so those collaborators are absent. The real app initialises them; here we only
    exercise the hidden-set logic itself."""
    ed = _editor(_plain_specs())
    ed._hidden_thickness_dimension_rows = set()
    ed._begin_history_capture = lambda *a, **k: None
    ed._commit_history_capture = lambda *a, **k: None
    ed._refresh_open_3d_views = lambda *a, **k: None
    return ed


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # A) Editor toggle semantics.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        ed = _toggle_test_editor()
        initial = ed._thickness_dimension_is_hidden(1)
        ed.set_thickness_dimension_hidden(1, True)
        after_hide = ed._thickness_dimension_is_hidden(1)
        other_row = ed._thickness_dimension_is_hidden(2)
        ed.toggle_thickness_dimension_hidden(1)
        after_toggle = ed._thickness_dimension_is_hidden(1)
        ed.set_thickness_dimension_hidden(1, True)
        ed.set_thickness_dimension_hidden(3, True)
        hidden_count = len(ed._hidden_thickness_dimension_rows)
        ed.show_all_thickness_dimensions()
        after_show_all = len(ed._hidden_thickness_dimension_rows)
    if initial:
        failures.append("FAIL: a fresh row should not be hidden")
    if not after_hide:
        failures.append("FAIL: set_thickness_dimension_hidden(row, True) must hide that row")
    if other_row:
        failures.append("FAIL: hiding one row must not hide a different row")
    if after_toggle:
        failures.append("FAIL: toggle_thickness_dimension_hidden must un-hide a hidden row")
    if hidden_count != 2:
        failures.append(f"FAIL: two hidden rows expected, got {hidden_count}")
    if after_show_all != 0:
        failures.append(f"FAIL: show_all_thickness_dimensions must clear the hidden set, {after_show_all} left")

    # B) add_overlays skips hidden rows.
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    add_src = inspect.getsource(Open3DThicknessDimensionService.add_overlays)
    if "_thickness_dimension_is_hidden" not in add_src:
        failures.append(
            "FAIL: add_overlays must skip rows in the hidden set "
            "(_thickness_dimension_is_hidden) so a turned-off dimension is not drawn")

    # C) Persistence round-trips the hidden set.
    from KrakenOS.UI.services.layout_settings import LayoutSettingsService

    save_src = inspect.getsource(LayoutSettingsService._collect_layout_settings)
    load_src = inspect.getsource(LayoutSettingsService._apply_layout_settings)
    if "hidden_thickness_dimension_rows" not in save_src:
        failures.append("FAIL: _collect_layout_settings must serialise hidden_thickness_dimension_rows")
    if "hidden_thickness_dimension_rows" not in load_src or "_hidden_thickness_dimension_rows" not in load_src:
        failures.append(
            "FAIL: _apply_layout_settings must restore hidden_thickness_dimension_rows "
            "onto editor._hidden_thickness_dimension_rows")

    # D) Right-click menu wiring.
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    ctx_src = inspect.getsource(Open3DFaceAssignmentService._show_surface_function_context_menu)
    if "_maybe_show_thickness_dimension_menu" not in ctx_src:
        failures.append(
            "FAIL: the right-click context menu must offer the thickness-dimension menu "
            "(_maybe_show_thickness_dimension_menu)")
    if not hasattr(Kraken3DInspector, "_maybe_show_thickness_dimension_menu"):
        failures.append("FAIL: Kraken3DInspector._maybe_show_thickness_dimension_menu is missing")
    menu_src = inspect.getsource(Kraken3DInspector._show_thickness_dimension_menu)
    if "Hide this thickness dimension" not in menu_src:
        failures.append("FAIL: the dimension menu must offer 'Hide this thickness dimension'")
    if "Re-anchor to a surface/edge" not in menu_src:
        failures.append("FAIL: the dimension menu must offer 'Re-anchor to a surface/edge…'")

    # E) Drag-to-point re-anchor commit.
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService

    release_src = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    if "dimension_anchor_was_drag" not in release_src:
        failures.append(
            "FAIL: a drag of the dimension endpoint onto a surface/edge must commit the "
            "re-anchor on release (dimension_anchor_was_drag)")
    if not hasattr(Kraken3DInspector, "_begin_dimension_anchor_pick_for_row"):
        failures.append("FAIL: Kraken3DInspector._begin_dimension_anchor_pick_for_row is missing")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] per-dimension Thickness visibility / drag-to-point re-anchor")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] each Thickness dimension can be turned off + dragged to re-anchor to a "
          "surface/edge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
