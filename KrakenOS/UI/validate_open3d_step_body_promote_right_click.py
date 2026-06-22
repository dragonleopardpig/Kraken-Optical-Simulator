#!/usr/bin/env python3
"""Display-free guard for bugs/0110 -- a right-click that lands squarely on a
promotable imported-STEP body (e.g. a beam-splitter cube face) must keep its
direct per-face "Promote and set <face function>" menu, instead of being stolen
by the thickness-dimension arrow menu.

Regression history: bugs/0108 added a screen-space proximity fallback to
``_thickness_dimension_row_under_cursor`` so an arrow-less overlay's billboard
label/leader (which the cell picker can't hit) is still resolvable for hiding.
That fallback was too greedy: it fired even when the cell picker had landed
directly on a real optical body, so whenever a Thickness label/arrow happened to
sit within tolerance of the clicked face the thickness menu pre-empted the
face-promotion menu ("the direct promotion of each face is gone ... it is now
giving the Thickness arrow right click option").

Fix (``_thickness_dimension_row_under_cursor``): when the cell picker hit a
promotable body actor -- one registered in ``_actor_step_map`` (imported STEP
overlay) or ``_actor_row_map`` (optical / STL row) -- and it is NOT itself a
thickness-dimension actor, return ``None`` so the dispatcher falls through to the
face-promotion menu. The proximity fallback now only fires for clicks that
resolve to no promotable body (empty space or a non-body decoration).

What it checks (functional, by borrowing the real unbound method onto a fake):
  1. STEP-overlay body hit + a thickness overlay within tolerance -> None
     (defer to the promote menu), NOT the nearby thickness row.
  2. Optical / STL row hit + overlay within tolerance -> None.
  3. Direct hit on a thickness-dimension actor -> that row (unchanged).
  4. Empty space (no actor) near an overlay -> the proximity row (0108 intact).
  5. Non-body decoration hit near an overlay -> the proximity row (0108 intact).
And a source check that the gate is present.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_step_body_promote_right_click

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

from KrakenOS.UI.open3d_inspector import Kraken3DInspector


class _Event:
    x = 100
    y = 100


class _FakeInteractor:
    def SetEventInformationFlipY(self, *a, **k) -> None:
        return None

    def GetEventPosition(self):
        return (100, 100)


class _FakePicker:
    def __init__(self, actor) -> None:
        self._actor = actor

    def Pick(self, *a, **k) -> None:
        return None

    def GetActor(self):
        return self._actor


class _FakeInspector:
    """Minimal stand-in exercising only ``_thickness_dimension_row_under_cursor``.
    A thickness overlay is always "within tolerance" (the proximity fallback
    returns PROXIMITY_ROW) so the test proves the gate, not the geometry."""

    PROXIMITY_ROW = 7

    def __init__(self, *, actor_key, step_map=None, row_map=None, thick_map=None) -> None:
        self._actor = object() if actor_key is not None else None
        self._actor_key_value = actor_key
        self._renderer = object()
        self._vtk_interactor = _FakeInteractor()
        self._picker = _FakePicker(self._actor)
        self._actor_thickness_dimension_map = dict(thick_map or {})
        self._actor_step_map = dict(step_map or {})
        self._actor_row_map = dict(row_map or {})

    def _actor_key(self, actor):
        return self._actor_key_value

    def _thickness_dimension_row_near_display_xy(self, x, y, **k):
        return self.PROXIMITY_ROW


def _row_under_cursor(insp: _FakeInspector):
    method = types.MethodType(Kraken3DInspector._thickness_dimension_row_under_cursor, insp)
    return method(_Event())


def _hit_promotable_body(insp: _FakeInspector) -> bool:
    method = types.MethodType(Kraken3DInspector._right_click_hit_promotable_body, insp)
    return method(_Event())


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # 1) STEP-overlay body hit, with a thickness overlay within proximity.
    step_hit = _FakeInspector(actor_key="bs_cube", step_map={"bs_cube": "step:0"})
    got = _row_under_cursor(step_hit)
    if got is not None:
        failures.append(
            "FAIL: a right-click on an imported STEP body must defer to the face-promotion "
            f"menu (return None), got thickness row {got!r} -- the promote menu is lost")

    # 2) Optical / STL row body hit, with a thickness overlay within proximity.
    row_hit = _FakeInspector(actor_key="row3", row_map={"row3": 3})
    got = _row_under_cursor(row_hit)
    if got is not None:
        failures.append(
            "FAIL: a right-click on an optical/STL row body must defer to the face menu "
            f"(return None), got thickness row {got!r}")

    # 3) Direct hit on a real thickness-dimension actor -> that row (unchanged).
    thick_hit = _FakeInspector(actor_key="thick2", thick_map={"thick2": 2})
    got = _row_under_cursor(thick_hit)
    if got != 2:
        failures.append(
            f"FAIL: a direct hit on a thickness arrow must resolve its row (2), got {got!r}")

    # 3b) A body actor that is ALSO a thickness actor still resolves the arrow
    #     (the explicit-arrow branch wins before the body gate).
    both = _FakeInspector(
        actor_key="dual", step_map={"dual": "step:0"}, thick_map={"dual": 5}
    )
    got = _row_under_cursor(both)
    if got != 5:
        failures.append(
            f"FAIL: an actor that is a thickness arrow must resolve its row (5) even if "
            f"also body-mapped, got {got!r}")

    # 4) Empty space (no actor under cursor) near an overlay -> proximity fallback
    #    still resolves the row (bugs/0108 preserved).
    empty = _FakeInspector(actor_key=None)
    got = _row_under_cursor(empty)
    if got != _FakeInspector.PROXIMITY_ROW:
        failures.append(
            "FAIL: a click on empty space near an arrow-less overlay must still resolve via "
            f"the proximity fallback (row {_FakeInspector.PROXIMITY_ROW}), got {got!r} -- "
            "bugs/0108 broken")

    # 5) A non-body decoration hit (actor in no body map) near an overlay -> still
    #    the proximity fallback (the gate only blocks promotable bodies).
    deco = _FakeInspector(actor_key="axis_overlay")
    got = _row_under_cursor(deco)
    if got != _FakeInspector.PROXIMITY_ROW:
        failures.append(
            "FAIL: a click on a non-body decoration near an overlay must still resolve via "
            f"the proximity fallback (row {_FakeInspector.PROXIMITY_ROW}), got {got!r}")

    # 6) The shared body-hit helper: a STEP/optical-row hit is a promotable body;
    #    a thickness actor / empty space / non-body decoration is not.
    if not hasattr(Kraken3DInspector, "_right_click_hit_promotable_body"):
        failures.append("FAIL: Kraken3DInspector._right_click_hit_promotable_body helper is missing")
    else:
        cases = {
            "step body": (_FakeInspector(actor_key="bs_cube", step_map={"bs_cube": "step:0"}), True),
            "optical row": (_FakeInspector(actor_key="row3", row_map={"row3": 3}), True),
            "thickness arrow": (_FakeInspector(actor_key="thick2", thick_map={"thick2": 2}), False),
            "empty space": (_FakeInspector(actor_key=None), False),
            "decoration": (_FakeInspector(actor_key="axis_overlay"), False),
        }
        for label, (insp, expected) in cases.items():
            got = _hit_promotable_body(insp)
            if got != expected:
                failures.append(
                    f"FAIL: _right_click_hit_promotable_body({label}) -> {got!r}, expected {expected!r}")

    # 7) The measure menu's PickableOff proximity resolver must defer to the same
    #    body gate (the measure hook runs FIRST, so it could steal a body click too).
    measure_src = inspect.getsource(Kraken3DInspector._measure_segment_index_under_cursor)
    if "_right_click_hit_promotable_body" not in measure_src:
        failures.append(
            "FAIL: _measure_segment_index_under_cursor must defer to "
            "_right_click_hit_promotable_body so a click on a body opens the promote menu")

    # 8) Source: the thickness gate is present and returns None for a body hit.
    src = inspect.getsource(Kraken3DInspector._thickness_dimension_row_under_cursor)
    if "_actor_step_map" not in src or "_actor_row_map" not in src:
        failures.append(
            "FAIL: _thickness_dimension_row_under_cursor must gate the proximity fallback on "
            "the body actor maps (_actor_step_map / _actor_row_map)")
    if "bugs/0110" not in src:
        failures.append("FAIL: the bugs/0110 body-hit gate rationale is missing from the source")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] right-click on an imported STEP body keeps its direct per-face promote menu")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] right-click on an imported STEP body keeps its direct per-face promote menu "
          "(thickness-arrow proximity no longer steals it)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
