#!/usr/bin/env python3
"""Display-free guard for bugs/0132 -- the exact flag_20260624_115350_660 repro:
after re-anchoring the amber object->LED arrow onto a body face, editing the LED
edge-distance MUST move the LED (the chosen face tracks the typed value).

User's words:
  flag_115328: "reanchor the Object LED distance."   (arrow snapped to the face at 213.2)
  flag_115350: "changed the value of the Object LED distance by input in the pop up
                dialog. The segment arrow shorten but the arrow point to the wrong
                location just like before anchor, and the LED is not moving."

Regression (bugs/0130, now reversed): the re-anchor stored a measurement-only override
that ``set_led_edge_distance`` cleared on edit, so the body sat frozen and the arrow
reverted to the typed front extremum (the "cable").

This pins the literal scenario: an LED whose typed object distance is 200 (its front
extremum) is re-anchored onto a body face currently at z=213.2; the re-anchor must NOT
move the body, and a later dialog edit MUST translate the body so the chosen face lands
exactly at the new value. Exercises the REAL re-anchor + placement commands; no display.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_reanchor_moves

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin


class _FakeStatus:
    def set(self, _text) -> None:
        pass


class _FakeEditor:
    """tk-free stand-in carrying the REAL LED re-anchor + axial-placement methods."""

    apply_led_object_edge_reanchor = ScenePlacementMixin.apply_led_object_edge_reanchor
    _led_reanchor_reference = staticmethod(ScenePlacementMixin._led_reanchor_reference)
    _led_step_z_translation = ScenePlacementMixin._led_step_z_translation
    _clear_led_edge_dimension_override = ScenePlacementMixin._clear_led_edge_dimension_override

    def __init__(self, *, distance: float, ref=None) -> None:
        self.imported_led_step_path = "led.step"
        self.led_object_edge_distance_mm = float(distance)
        self.led_step_object_edge_local_z = ref
        self._dimension_anchor_overrides: dict[int, dict] = {}
        self._cad_led_object_edge_pick = False
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._selected_step_label = None
        self.status_var = _FakeStatus()

    def _begin_history_capture(self) -> None:
        pass

    def _commit_history_capture(self) -> None:
        pass

    def _refresh_open_3d_views(self, *args, **kwargs) -> None:
        pass


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # The flagged pose: typed distance 200 (front extremum), no LED reference yet.
    ed = _FakeEditor(distance=200.0, ref=None)
    translation_initial = float(ed._led_step_z_translation())

    # flag_115328: pick the body face currently at z=213.2.
    ed.apply_led_object_edge_reanchor(np.asarray([0.0, 0.0, 213.2]))
    if ed.led_step_object_edge_local_z is None:
        failures.append("re-anchor did not record the LED object-edge reference")
        return (not failures), failures
    face_native = float(ed.led_step_object_edge_local_z)

    # The pick must NOT move the body (flag_115328 showed 213.2 with the LED parked).
    translation_after_pick = float(ed._led_step_z_translation())
    if abs(translation_after_pick - translation_initial) > 1e-6:
        failures.append(
            f"re-anchor moved the LED (translation {translation_initial} -> "
            f"{translation_after_pick}); it must stay put on the pick"
        )
    if abs((face_native + translation_after_pick) - 213.2) > 1e-6:
        failures.append("the picked face must still sit at z=213.2 right after the pick")

    # flag_115350: now edit the dialog value. The LED MUST move and the chosen face
    # must land exactly at the typed value -- not stay frozen at the old extremum.
    for value in (200.0, 160.0, 250.0):
        translation_before = float(ed._led_step_z_translation())
        ed.led_object_edge_distance_mm = float(value)  # what set_led_edge_distance writes
        translation_after = float(ed._led_step_z_translation())
        face_world = face_native + translation_after
        expected_shift = value - (face_native + translation_before)
        if abs(expected_shift) > 1e-6 and abs(translation_after - translation_before) < 1e-6:
            failures.append(
                f"editing distance to {value} did NOT move the LED (flag_115350 'not moving' regression)"
            )
        if abs(face_world - value) > 1e-6:
            failures.append(
                f"after editing to {value} the picked face is at {face_world}, not {value}"
            )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0132 editing the LED edge-distance must move the LED after re-anchor")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] re-anchor keeps the LED put; editing the distance moves it, face tracks (bugs/0132)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
