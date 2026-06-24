#!/usr/bin/env python3
"""Display-free guard for bugs/0130: the amber "Object -> LED" arrow must be
re-anchorable to a picked LED face/edge -- measurement only, the LED stays put.

Why it exists (user flagged it, flag_20260624_083930_719):
  "dragging the LED does change the value, but I can't reposition the arrow to point
   to the LED correct edge ... it is measuring the cable, not the LED edge, I need to
   be able to drag the arrow to point to the correct LED edge/face."

Root cause: the overlay drew its LED-side endpoint at the typed dialog distance and
ignored any stored re-anchor override, so a right-click "Re-anchor to a surface/edge"
pick had no visible effect (the arrow snapped back to the typed point, which could
land on a cable instead of the body face).

The fix honours ``_dimension_anchor_override_for_row(-7)`` inside
``_emit_led_object_edge_dimension`` via the pure ``led_edge_override_endpoint``
helper. The pick is measurement-only (row -7 is NOT the object/LED placement row, so
``apply_dimension_anchor_override`` does not move the LED), and the picked face rides
the LED's later axial carry-drag through the captured pick-time offset.

What it checks:
  A. ``led_edge_override_endpoint`` returns None for a missing / malformed override.
  B. A re-anchor override repoints the endpoint onto the picked face (ref_z), NOT the
     typed distance -- with the LED undragged the endpoint sits exactly at ref_z.
  C. After the LED is carry-dragged axially, the endpoint TRACKS the moving face
     (effective_z = ref_z + (current_offset - pick_offset)).
  D. Measurement-only invariant: re-anchoring row -7 stores ref_z + the pick-time LED
     offset and NEVER calls ``apply_led_object_edge_pick`` (which would move the LED),
     whereas the S0 object-side endpoint (row 0 start) IS the LED placement edge.
  E. Source contract -- the overlay honours the override + registers a drag handle;
     the commit captures ``led_offset_z``; both LED re-placement paths clear it.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_edge_reanchor

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService
from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

_ROW = Open3DThicknessDimensionService.LED_OBJECT_EDGE_DIM_ROW  # sentinel -7
_endpoint = Open3DThicknessDimensionService.led_edge_override_endpoint


class _FakeStatus:
    def set(self, _text) -> None:
        pass


class _FakeEditor:
    """tk-free stand-in carrying the REAL re-anchor commands so the test exercises
    production code, not a paraphrase of it."""

    apply_dimension_anchor_override = ScenePlacementMixin.apply_dimension_anchor_override
    _dimension_anchor_override_for_row = ScenePlacementMixin._dimension_anchor_override_for_row
    _dimension_row_is_object_led = ScenePlacementMixin._dimension_row_is_object_led
    _dimension_anchor_feature_label = ScenePlacementMixin._dimension_anchor_feature_label
    _clear_led_edge_dimension_override = ScenePlacementMixin._clear_led_edge_dimension_override

    def __init__(self, led_offset_z: float = 0.0) -> None:
        self.imported_led_step_path = "led.step"  # an LED IS imported
        self._dimension_anchor_overrides: dict[int, dict] = {}
        self._led_offset_z = float(led_offset_z)
        self.led_pick_calls: list[np.ndarray] = []
        self.status_var = _FakeStatus()

    # stubs -----------------------------------------------------------------
    def _begin_history_capture(self) -> None:
        pass

    def _commit_history_capture(self) -> None:
        pass

    def _refresh_open_3d_views(self, *args, **kwargs) -> None:
        pass

    def _step_placement_offset_xyz(self, _label):
        return (0.0, 0.0, self._led_offset_z)

    def apply_led_object_edge_pick(self, feature_center_xyz) -> None:
        # If this ever fires for row -7 the "measurement only" contract is broken.
        self.led_pick_calls.append(np.asarray(feature_center_xyz, dtype=float))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    p0 = np.zeros(3, dtype=float)  # object reference on the axis

    # --- A: no / malformed override -> None ---------------------------------
    if _endpoint(p0, 0.0, None) is not None:
        failures.append("A FAIL: a missing override should yield no endpoint")
    if _endpoint(p0, 0.0, {}) is not None:
        failures.append("A FAIL: an override without ref_z should yield no endpoint")
    if _endpoint(p0, 0.0, {"ref_z": float("nan")}) is not None:
        failures.append("A FAIL: a non-finite ref_z should yield no endpoint")

    # --- B: re-anchor repoints to the picked face (not the typed distance) ---
    # The dialog distance is 50 (the "cable"); the user picks the body face at 60.
    override = {"ref_z": 60.0, "led_offset_z": 0.0}
    result = _endpoint(p0, 0.0, override)
    if result is None:
        failures.append("B FAIL: a valid override produced no endpoint")
    else:
        p1, live = result
        if abs(float(p1[2]) - 60.0) > 1e-9:
            failures.append(f"B FAIL: endpoint z should sit on the picked face 60, got {p1[2]}")
        if abs(live - 60.0) > 1e-9:
            failures.append(f"B FAIL: measured distance should be 60 (object->face), got {live}")
        if abs(live - 50.0) < 1e-9:
            failures.append("B FAIL: arrow still measures the typed distance 50, not the picked face")
        if abs(float(p1[0])) > 1e-9 or abs(float(p1[1])) > 1e-9:
            failures.append("B FAIL: re-anchored endpoint must stay on the optical axis")

    # --- C: the picked face tracks the LED's later axial carry-drag ----------
    # pick captured offset 0; the LED is then dragged +12 along the axis.
    dragged = _endpoint(p0, 12.0, {"ref_z": 60.0, "led_offset_z": 0.0})
    if dragged is None:
        failures.append("C FAIL: tracking override produced no endpoint")
    else:
        p1d, lived = dragged
        if abs(float(p1d[2]) - 72.0) > 1e-9:
            failures.append(f"C FAIL: dragged face should ride to 60+12=72, got {p1d[2]}")
        if abs(lived - 72.0) > 1e-9:
            failures.append(f"C FAIL: tracked distance should be 72, got {lived}")
    # and with the captured offset == current offset, no spurious shift.
    held = _endpoint(p0, 9.0, {"ref_z": 60.0, "led_offset_z": 9.0})
    if held is None:
        failures.append("C FAIL: held-offset override produced no endpoint")
    elif abs(float(held[1]) - 60.0) > 1e-9:
        failures.append(f"C FAIL: equal pick/current offset must stay at ref_z=60, got {held[1]}")

    # --- D: measurement-only invariant; the LED does NOT move ----------------
    ed = _FakeEditor(led_offset_z=7.0)
    ed.apply_dimension_anchor_override(_ROW, "end", np.asarray([0.0, 0.0, 60.0]), fixed_z=0.0)
    spec = ed._dimension_anchor_override_for_row(_ROW)
    if not isinstance(spec, dict):
        failures.append("D FAIL: re-anchoring row -7 stored no override")
    else:
        if abs(float(spec.get("ref_z", -1)) - 60.0) > 1e-9:
            failures.append(f"D FAIL: stored ref_z should be 60, got {spec.get('ref_z')}")
        if abs(float(spec.get("led_offset_z", -1)) - 7.0) > 1e-9:
            failures.append(f"D FAIL: should capture the pick-time LED offset 7, got {spec.get('led_offset_z')}")
        if str(spec.get("endpoint")) != "end":
            failures.append(f"D FAIL: re-anchored endpoint should be 'end', got {spec.get('endpoint')}")
    if ed.led_pick_calls:
        failures.append("D FAIL: re-anchoring the amber arrow (row -7) MOVED the LED (measurement-only broken)")
    # the S0 object-side endpoint IS the LED placement edge, but row -7 is not.
    if not ed._dimension_row_is_object_led(0, "start"):
        failures.append("D FAIL: row 0 'start' should be the object/LED placement edge")
    if ed._dimension_row_is_object_led(_ROW, "end"):
        failures.append("D FAIL: sentinel row -7 must NOT be treated as the LED placement edge")

    # clearing on re-placement drops the override.
    ed._clear_led_edge_dimension_override()
    if ed._dimension_anchor_override_for_row(_ROW) is not None:
        failures.append("D FAIL: _clear_led_edge_dimension_override left the override in place")

    # --- E: source contracts ------------------------------------------------
    emit_src = inspect.getsource(Open3DThicknessDimensionService._emit_led_object_edge_dimension)
    if "led_edge_override_endpoint" not in emit_src:
        failures.append("E FAIL: the overlay must honour the override via led_edge_override_endpoint")
    if "_dimension_anchor_override_for_row" not in emit_src:
        failures.append("E FAIL: the overlay must look up _dimension_anchor_override_for_row")
    if "register_drag=True" not in emit_src:
        failures.append("E FAIL: the overlay must register a drag handle so re-anchor can begin")
    commit_src = inspect.getsource(ScenePlacementMixin.apply_dimension_anchor_override)
    if "led_offset_z" not in commit_src:
        failures.append("E FAIL: the commit must capture led_offset_z for the sentinel row")
    for name in ("set_led_edge_distance", "apply_led_object_edge_pick"):
        src = inspect.getsource(getattr(ScenePlacementMixin, name))
        if "_clear_led_edge_dimension_override" not in src:
            failures.append(f"E FAIL: {name} must clear a stale re-anchor override on LED re-placement")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0130 object->LED arrow must re-anchor to the picked LED face")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] object->LED arrow re-anchors to a picked LED face, LED unmoved (bugs/0130)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
