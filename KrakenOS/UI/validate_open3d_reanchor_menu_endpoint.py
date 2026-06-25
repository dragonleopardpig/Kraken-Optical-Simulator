#!/usr/bin/env python3
"""Display-free guard for bugs/0150: the right-click "Re-anchor to a surface/edge..."
menu must move the dimension endpoint the user clicked NEAREST, not always the right
("end") endpoint.

Why it exists (user, in-app: "I point to the Left Arrow, right click, select reanchor --
the right arrow repositions to the left arrow (zero length) then slides; Ctrl-left click
works as expected"): `_show_thickness_dimension_menu` wired the re-anchor command as
`_begin_dimension_anchor_pick_for_row(idx)` with NO endpoint, so it defaulted to "end"
and the left arrowhead could never be re-anchored from the menu. The Ctrl-click path picks
the nearer endpoint by display-space proximity (`_dimension_anchor_state_from_current_pick`,
default "start"). The fix adds `_nearer_dimension_endpoint_for_event`, which mirrors that
proximity test, and the menu forwards its result as `endpoint=`.

What it checks (binds the REAL `_nearer_dimension_endpoint_for_event` onto a fake inspector
with a stubbed interactor + projection):
  A. A click near the START projection returns "start".
  B. A click near the END projection returns "end".
  C. An equidistant click returns "start" (tie -> start, matching the Ctrl-click default).
  D. A row with no drag record falls back to "start".
  E. An unavailable endpoint projection (world_to_display None) falls back to "start".
  F. An interactor that can't report the cursor falls back to "start".
  G. Source contract: `_show_thickness_dimension_menu` derives the endpoint via
     `_nearer_dimension_endpoint_for_event` and forwards `endpoint=` into
     `_begin_dimension_anchor_pick_for_row` (no longer the bare `(idx)` form).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_reanchor_menu_endpoint

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import re
import types

import numpy as np

from KrakenOS.UI.layout_editor import Kraken3DInspector


class _FakeInteractor:
    """Stub VTK interactor: GetEventPosition returns a preset display cursor."""

    def __init__(self, cursor, *, raises=False):
        self._cursor = cursor
        self._raises = raises

    def SetEventInformationFlipY(self, *args):  # noqa: N802 (VTK name)
        if self._raises:
            raise RuntimeError("no interactor")

    def GetEventPosition(self):  # noqa: N802 (VTK name)
        if self._raises:
            raise RuntimeError("no interactor")
        return self._cursor


class _FakeInspector:
    # bind the REAL method under test
    _nearer_dimension_endpoint_for_event = (
        Kraken3DInspector._nearer_dimension_endpoint_for_event
    )

    def __init__(self, cursor, *, w2d_none=False, interactor_raises=False, has_record=True):
        self._vtk_interactor = _FakeInteractor(cursor, raises=interactor_raises)
        self._w2d_none = w2d_none
        if has_record:
            self._thickness_dimension_actor_map = {0: ["k0"]}
            # start projects to (0,0), end to (100,0) via _world_to_display_2d below
            self._thickness_dimension_drag_map = {
                "k0": {"start": (0.0, 0.0, 0.0), "end": (100.0, 0.0, 0.0)}
            }
        else:
            self._thickness_dimension_actor_map = {0: []}
            self._thickness_dimension_drag_map = {}

    def _world_to_display_2d(self, point):
        if self._w2d_none:
            return None
        return np.asarray(point, dtype=float).reshape(-1)[:2]


def _endpoint(cursor, **kw):
    insp = _FakeInspector(cursor, **kw)
    event = types.SimpleNamespace(x=int(cursor[0]), y=int(cursor[1]))
    return insp._nearer_dimension_endpoint_for_event(event, 0)


def run_checks():
    failures = []

    # A: click near the START projection (0,0)
    if _endpoint((5, 0)) != "start":
        failures.append("A FAIL: a click near the start arrowhead must re-anchor 'start'")
    # B: click near the END projection (100,0)
    if _endpoint((95, 0)) != "end":
        failures.append("B FAIL: a click near the end arrowhead must re-anchor 'end'")
    # C: equidistant -> start (tie -> start)
    if _endpoint((50, 0)) != "start":
        failures.append("C FAIL: an equidistant click must default to 'start' (tie -> start)")
    # D: no drag record -> start
    if _endpoint((95, 0), has_record=False) != "start":
        failures.append("D FAIL: a row with no drag record must fall back to 'start'")
    # E: projection unavailable -> start
    if _endpoint((95, 0), w2d_none=True) != "start":
        failures.append("E FAIL: an unavailable endpoint projection must fall back to 'start'")
    # F: interactor cannot report the cursor -> start
    if _endpoint((95, 0), interactor_raises=True) != "start":
        failures.append("F FAIL: an unavailable cursor must fall back to 'start'")

    # G: source contract on the real menu builder
    menu_src = inspect.getsource(Kraken3DInspector._show_thickness_dimension_menu)
    if "_nearer_dimension_endpoint_for_event" not in menu_src:
        failures.append(
            "G FAIL: the menu must derive the endpoint via _nearer_dimension_endpoint_for_event"
        )
    if "endpoint=" not in menu_src:
        failures.append(
            "G FAIL: the menu must forward the chosen endpoint to _begin_dimension_anchor_pick_for_row"
        )
    # require the `self.` prefix so the explanatory COMMENT (which quotes the old
    # `_begin_dimension_anchor_pick_for_row(idx)` signature) is not mistaken for a live call
    if re.search(r"self\._begin_dimension_anchor_pick_for_row\(\s*idx\s*\)", menu_src):
        failures.append(
            "G FAIL: the menu still calls self._begin_dimension_anchor_pick_for_row(idx) with no endpoint (bug 0150)"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0150 right-click re-anchor menu must move the endpoint nearest the click")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] right-click re-anchor menu moves the endpoint nearest the click (bugs/0150)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
