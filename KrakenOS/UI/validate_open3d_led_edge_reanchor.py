#!/usr/bin/env python3
"""Display-free guard for bugs/0132: re-anchoring the amber "Object -> LED" arrow
must PERSIST and drive the LED's own object-edge reference -- editing the LED
edge-distance afterwards MOVES the LED with the arrow staying on the chosen face.

Why it exists (user flagged it, flag_20260624_115328_911 + flag_20260624_115350_660):
  "reanchor the Object LED distance." then -- after editing the dialog value --
  "the segment arrow ... point to the wrong location just like before anchor, and
   the LED is not moving."

Root cause (a regression I shipped in bugs/0130): the row -7 re-anchor stored a
MEASUREMENT-ONLY override that ``set_led_edge_distance`` cleared on any value-change,
so the arrow reverted to the typed endpoint (a cable extremum) and the body never
moved.

The fix routes the row -7 re-anchor to ``apply_led_object_edge_reanchor``, which sets
the LED's object-edge reference (``led_step_object_edge_local_z``) AND the typed edge
distance to the picked face's CURRENT object distance. So the LED does not jump on the
pick, the dialog now reads that face's distance, and a later edit slides the LED so the
chosen face tracks the value -- the arrow IS the LED's distance handle.

The placement model (see ``apply_led_object_edge_pick``): the edge stored in
``led_step_object_edge_local_z`` lands at world z ``led_object_edge_distance_mm``,
via ``_led_step_z_translation() = distance - reference``. So a picked face at native z
``L`` lands at world ``L + translation``.

What it checks:
  A. ``_led_reanchor_reference(face_z, T)`` == ``(face_z - T, face_z)`` (the pure math).
  B. NO-MOVE invariant: re-anchoring does not jump the body -- the LED's axial
     translation is identical before and after the pick (for ref=None and ref=set).
  C. MOVE-ON-EDIT invariant: after the re-anchor, setting the edge distance to V slides
     the LED so the picked face lands exactly at world z == V (for several V).
  D. Routing: ``apply_dimension_anchor_override(-7, ...)`` runs the re-anchor (sets the
     reference + distance) and stores NO measurement override; it never calls
     ``apply_led_object_edge_pick``. Row 0 'start' still IS the legacy LED placement edge.
  E. Source contracts -- the commit routes -7 to ``apply_led_object_edge_reanchor`` and
     no longer captures ``led_offset_z``; the overlay no longer honours a removed
     ``led_edge_override_endpoint`` but still registers a drag handle; the re-anchor sets
     both the reference and the distance; all LED re-placement paths clear a stale override.

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
_reference = ScenePlacementMixin._led_reanchor_reference


class _FakeStatus:
    def set(self, _text) -> None:
        pass


class _FakeEditor:
    """tk-free stand-in carrying the REAL re-anchor + placement commands so the test
    exercises production code, not a paraphrase of it. ``apply_led_object_edge_pick`` is
    overridden with a recorder so we can prove the -7 path does NOT move the LED via the
    legacy edge pick (and the row-0 path DOES route to it)."""

    apply_dimension_anchor_override = ScenePlacementMixin.apply_dimension_anchor_override
    apply_led_object_edge_reanchor = ScenePlacementMixin.apply_led_object_edge_reanchor
    _led_reanchor_reference = staticmethod(ScenePlacementMixin._led_reanchor_reference)
    _led_step_z_translation = ScenePlacementMixin._led_step_z_translation
    _clear_led_edge_dimension_override = ScenePlacementMixin._clear_led_edge_dimension_override
    _dimension_anchor_override_for_row = ScenePlacementMixin._dimension_anchor_override_for_row
    _dimension_row_is_object_led = ScenePlacementMixin._dimension_row_is_object_led
    _dimension_anchor_feature_label = ScenePlacementMixin._dimension_anchor_feature_label

    def __init__(self, *, distance: float = 0.0, ref=None) -> None:
        self.imported_led_step_path = "led.step"  # an LED IS imported
        self.led_object_edge_distance_mm = float(distance)
        self.led_step_object_edge_local_z = ref  # None or float
        self._dimension_anchor_overrides: dict[int, dict] = {}
        self._cad_led_object_edge_pick = False
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._selected_step_label = None
        self.status_var = _FakeStatus()
        self.led_pick_calls: list[np.ndarray] = []

    # stubs -----------------------------------------------------------------
    def _begin_history_capture(self) -> None:
        pass

    def _commit_history_capture(self) -> None:
        pass

    def _refresh_open_3d_views(self, *args, **kwargs) -> None:
        pass

    def apply_led_object_edge_pick(self, feature_center_xyz) -> None:
        # If this fires for row -7 the re-anchor wrongly used the JUMP path.
        self.led_pick_calls.append(np.asarray(feature_center_xyz, dtype=float))

    # helper ----------------------------------------------------------------
    def _picked_face_world_z(self) -> float:
        """Where the re-anchored face currently sits = native ref + translation."""
        return float(self.led_step_object_edge_local_z) + float(self._led_step_z_translation())


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []

    # --- A: the pure reference math -----------------------------------------
    for face_z, trans in ((213.2, 200.0), (60.0, 0.0), (190.0, 175.0), (-3.0, 10.0)):
        local_z, edge = _reference(face_z, trans)
        if abs(local_z - (face_z - trans)) > 1e-9:
            failures.append(f"A FAIL: local_z for face={face_z},T={trans} should be {face_z - trans}, got {local_z}")
        if abs(edge - face_z) > 1e-9:
            failures.append(f"A FAIL: edge distance should equal the face world z {face_z}, got {edge}")

    # --- B + C: no-move on pick, move-on-edit afterwards --------------------
    # Two starting poses: a fresh LED (no reference yet) and one already referenced.
    for distance, ref, face_z in ((200.0, None, 213.2), (180.0, 5.0, 190.0)):
        ed = _FakeEditor(distance=distance, ref=ref)
        translation_before = float(ed._led_step_z_translation())
        ed.apply_led_object_edge_reanchor(np.asarray([0.0, 0.0, face_z]))

        # B: the LED must NOT jump -- its axial translation is unchanged, so the
        # picked face still sits exactly where it was picked.
        translation_after = float(ed._led_step_z_translation())
        if abs(translation_after - translation_before) > 1e-6:
            failures.append(
                f"B FAIL: re-anchor jumped the LED (translation {translation_before} -> "
                f"{translation_after}) for distance={distance}, ref={ref}"
            )
        if abs(ed._picked_face_world_z() - face_z) > 1e-6:
            failures.append(
                f"B FAIL: picked face slid off its pick point (got {ed._picked_face_world_z()}, want {face_z})"
            )
        # the dialog now reflects the picked face's object distance.
        if abs(float(ed.led_object_edge_distance_mm) - face_z) > 1e-6:
            failures.append(
                f"B FAIL: edge distance should read the picked face {face_z}, got {ed.led_object_edge_distance_mm}"
            )
        if ed.led_step_object_edge_local_z is None:
            failures.append("B FAIL: re-anchor must set led_step_object_edge_local_z (the LED reference)")
        if ed.led_pick_calls:
            failures.append("B FAIL: re-anchor used the legacy JUMP path (apply_led_object_edge_pick)")

        # C: editing the edge distance to V slides the LED so the face lands at V.
        for v in (150.0, 240.0, 213.2):
            ed.led_object_edge_distance_mm = float(v)  # what set_led_edge_distance writes
            landed = ed._picked_face_world_z()
            if abs(landed - v) > 1e-6:
                failures.append(
                    f"C FAIL: after editing distance to {v}, the picked face landed at {landed} (want {v})"
                )

    # --- D: routing through apply_dimension_anchor_override ------------------
    ed = _FakeEditor(distance=200.0, ref=None)
    ed.apply_dimension_anchor_override(_ROW, "end", np.asarray([0.0, 0.0, 213.2]), fixed_z=0.0)
    if ed.led_step_object_edge_local_z is None:
        failures.append("D FAIL: routing row -7 must run the re-anchor (set the LED reference)")
    if abs(float(ed.led_object_edge_distance_mm) - 213.2) > 1e-6:
        failures.append(f"D FAIL: routing row -7 must set the edge distance to 213.2, got {ed.led_object_edge_distance_mm}")
    if ed._dimension_anchor_override_for_row(_ROW) is not None:
        failures.append("D FAIL: row -7 re-anchor must NOT store a measurement-only override anymore")
    if ed.led_pick_calls:
        failures.append("D FAIL: row -7 must not route to the legacy LED edge pick")
    # the S0 object-side endpoint IS the LED placement edge; row -7 is not.
    if not ed._dimension_row_is_object_led(0, "start"):
        failures.append("D FAIL: row 0 'start' should be the object/LED placement edge")
    if ed._dimension_row_is_object_led(_ROW, "end"):
        failures.append("D FAIL: sentinel row -7 must NOT be treated as the row-0 LED placement edge")
    ed_row0 = _FakeEditor(distance=200.0, ref=None)
    ed_row0.apply_dimension_anchor_override(0, "start", np.asarray([0.0, 0.0, 60.0]))
    if len(ed_row0.led_pick_calls) != 1:
        failures.append("D FAIL: row 0 'start' must still route to apply_led_object_edge_pick")

    # --- E: source contracts ------------------------------------------------
    commit_src = inspect.getsource(ScenePlacementMixin.apply_dimension_anchor_override)
    if "apply_led_object_edge_reanchor" not in commit_src:
        failures.append("E FAIL: the commit must route the sentinel row to apply_led_object_edge_reanchor")
    if "led_offset_z" in commit_src:
        failures.append("E FAIL: the commit must no longer capture led_offset_z (measurement-only path removed)")

    reanchor_src = inspect.getsource(ScenePlacementMixin.apply_led_object_edge_reanchor)
    if "led_step_object_edge_local_z" not in reanchor_src:
        failures.append("E FAIL: the re-anchor must set the LED object-edge reference")
    if "led_object_edge_distance_mm" not in reanchor_src:
        failures.append("E FAIL: the re-anchor must set the typed edge distance (so the LED does not jump)")
    if "_clear_led_edge_dimension_override" not in reanchor_src:
        failures.append("E FAIL: the re-anchor must clear any stale override")

    emit_src = inspect.getsource(Open3DThicknessDimensionService._emit_led_object_edge_dimension)
    if "led_edge_override_endpoint" in emit_src:
        failures.append("E FAIL: the overlay must no longer honour the removed measurement-only override")
    if "register_drag=True" not in emit_src:
        failures.append("E FAIL: the overlay must register a drag handle so re-anchor can begin")
    if hasattr(Open3DThicknessDimensionService, "led_edge_override_endpoint"):
        failures.append("E FAIL: the dead led_edge_override_endpoint helper should be removed")

    for name in ("set_led_edge_distance", "apply_led_object_edge_pick", "apply_led_object_edge_reanchor"):
        src = inspect.getsource(getattr(ScenePlacementMixin, name))
        if "_clear_led_edge_dimension_override" not in src:
            failures.append(f"E FAIL: {name} must clear a stale re-anchor override on LED re-placement")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0132 object->LED arrow re-anchor must persist + drive the LED")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] object->LED re-anchor persists; editing the distance moves the LED (bugs/0132)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
