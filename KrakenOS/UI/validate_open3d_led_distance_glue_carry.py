#!/usr/bin/env python3
"""Display-free guard for bugs/0133: editing the Object->LED *distance* must carry the
BS<->LED glue, so a glued beam splitter follows the LED (and the blue object->solid gap
keeps tracking it) instead of detaching.

Why it exists (flag_20260624_130423_829 + flag_20260624_130325_946):
  bugs/0132 made editing the Object->LED distance MOVE the LED. But the distance paths
  reposition the LED by rewriting ``led_object_edge_distance_mm`` /
  ``led_step_object_edge_local_z`` and letting ``_led_step_z_translation()`` recompute --
  they never hand a world delta to ``_carry_glued_optical_led`` the way the drag
  primitives do (bugs/0127). So a beam splitter glued to the LED was left behind: the user
  moved the Object->LED distance and the BS detached, and the blue "gap to solid" overlay
  (object->promoted-solid distance) stopped tracking the LED. The fix adds
  ``_carry_led_glue_over_translation_change`` -- derive the LED's net world z-shift from
  the translation change and shove the glued partner by it -- and calls it from every
  LED-distance write (the edge-distance dialog, the legacy object-edge pick, the dimension
  re-anchor value edit, and the zero-shift re-anchor).

What it checks (binds the REAL ScenePlacementMixin methods onto a light fake editor):
  A. Distance edit (200 -> 150) with a glued promoted BS: the BS row follows by exactly
     the LED's world z-shift (-50), and only in z; the LED's own offset is untouched.
  B. Reference edit (the apply_led_object_edge_pick knob: change
     led_step_object_edge_local_z) drives the same carry -- the helper is agnostic to
     which attribute moved the LED.
  C. A zero-shift change (the re-anchor case: translation unchanged) carries nothing.
  D. An UNGLUED scene carries nothing on a distance edit.
  E. Source contract -- the three LED-distance writers that actually MOVE the body
     (set_led_edge_distance, apply_led_object_edge_pick, _move_led_for_reanchored_value)
     all route through ``_carry_led_glue_over_translation_change``, which itself delegates
     to ``_carry_glued_optical_led``. (apply_led_object_edge_reanchor keeps the body put,
     so it carries nothing.)

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_distance_glue_carry

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
from types import SimpleNamespace

from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin


class _Row:
    def __init__(self) -> None:
        self.desp_x = 0.0
        self.desp_y = 0.0
        self.desp_z = 0.0
        self.advanced: dict = {}

    @property
    def desp(self) -> tuple:
        return (float(self.desp_x), float(self.desp_y), float(self.desp_z))


class _FakeEditor:
    """A tk-free stand-in carrying the REAL distance/glue/carry methods so the test
    exercises production code, not a paraphrase of it. The beam splitter is a PROMOTED
    optical solid row (the flagged scenario); the LED is an overlay."""

    # --- real methods under test (bound straight off the mixin) ---
    _led_step_z_translation = ScenePlacementMixin._led_step_z_translation
    _carry_led_glue_over_translation_change = ScenePlacementMixin._carry_led_glue_over_translation_change
    _carry_glued_optical_led = ScenePlacementMixin._carry_glued_optical_led
    translate_scene_row_pose_vector = ScenePlacementMixin.translate_scene_row_pose_vector
    optical_led_glued = ScenePlacementMixin.optical_led_glued
    set_optical_led_glue = ScenePlacementMixin.set_optical_led_glue
    _optical_bs_body_present = ScenePlacementMixin._optical_bs_body_present
    _promoted_optical_solid_row_index = ScenePlacementMixin._promoted_optical_solid_row_index

    def __init__(self, *, glued: bool, distance: float = 200.0, edge_local_z: float = 0.0) -> None:
        self.rows = [_Row()]  # one promoted "optical" (beam splitter) solid row
        self.led_object_edge_distance_mm = float(distance)
        self.led_step_object_edge_local_z = float(edge_local_z)
        self._offsets = {"led": [0.0, 0.0, 0.0], "optical": [0.0, 0.0, 0.0]}
        self.status_var = SimpleNamespace(set=lambda *a, **k: None)
        if glued:
            assert self.set_optical_led_glue(True), "test setup: glue should succeed"

    # --- fake-only collaborators ---
    def _step_path_for_label(self, label):
        label = str(label or "").strip().lower()
        if label == "led":
            return "/tmp/led.step"
        # the beam splitter is promoted (no 'optical' overlay) -> carry routes to the row
        return None

    def _open3d_step_label_for_optical_solid_row(self, row):
        return "optical"

    def _step_placement_offset_xyz(self, label):
        return tuple(self._offsets.get(str(label).strip().lower(), [0.0, 0.0, 0.0]))

    def _set_step_placement_offset_xyz(self, label, xyz):
        self._offsets[str(label).strip().lower()] = [float(v) for v in tuple(xyz)[:3]]

    def _invalidate_preview_scene_trace(self):
        pass

    def _mark_plot_update_pending(self):
        pass

    def append_debug(self, *_a, **_k):
        pass


def _approx(a, b, tol: float = 1e-6) -> bool:
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # A) Distance edit moves the LED; the glued promoted BS follows by the same z-shift.
    ed = _FakeEditor(glued=True, distance=200.0)
    before = ed._led_step_z_translation()
    ed.led_object_edge_distance_mm = 150.0  # what the edge-distance dialog writes
    ed._carry_led_glue_over_translation_change(before)
    if not _approx(ed.rows[0].desp, (0.0, 0.0, -50.0)):
        failures.append(
            f"A FAIL: a glued BS must follow the LED's -50 mm distance move "
            f"(got {ed.rows[0].desp}, expected (0,0,-50))"
        )
    if not _approx(ed._step_placement_offset_xyz("led"), (0.0, 0.0, 0.0)):
        failures.append(
            f"A FAIL: the carry must not move the LED's own offset (got {ed._step_placement_offset_xyz('led')})"
        )

    # B) The carry is driven by the TRANSLATION change, not a specific attribute -- moving
    #    the object-edge reference (apply_led_object_edge_pick) must carry the BS too.
    ed_b = _FakeEditor(glued=True, distance=200.0, edge_local_z=0.0)
    before_b = ed_b._led_step_z_translation()  # 200
    ed_b.led_step_object_edge_local_z = -30.0   # translation -> 200 - (-30) = 230 (+30)
    ed_b._carry_led_glue_over_translation_change(before_b)
    if not _approx(ed_b.rows[0].desp, (0.0, 0.0, 30.0)):
        failures.append(
            f"B FAIL: moving the LED via its object-edge reference must carry the BS by +30 "
            f"(got {ed_b.rows[0].desp})"
        )

    # C) A zero-shift change (the re-anchor case) carries nothing.
    ed_c = _FakeEditor(glued=True, distance=200.0)
    before_c = ed_c._led_step_z_translation()
    ed_c._carry_led_glue_over_translation_change(before_c)  # nothing changed in between
    if not _approx(ed_c.rows[0].desp, (0.0, 0.0, 0.0)):
        failures.append(f"C FAIL: a zero-shift LED move must not carry the BS (got {ed_c.rows[0].desp})")

    # D) Unglued -> no carry at all.
    ed_d = _FakeEditor(glued=False, distance=200.0)
    before_d = ed_d._led_step_z_translation()
    ed_d.led_object_edge_distance_mm = 80.0
    ed_d._carry_led_glue_over_translation_change(before_d)
    if not _approx(ed_d.rows[0].desp, (0.0, 0.0, 0.0)):
        failures.append(f"D FAIL: an unglued scene must not carry the BS on a distance edit (got {ed_d.rows[0].desp})")

    # E) Source contract -- every LED-distance write must route the glue carry.
    helper_name = "_carry_led_glue_over_translation_change"
    movers = {
        "set_led_edge_distance": ScenePlacementMixin.set_led_edge_distance,
        "apply_led_object_edge_pick": ScenePlacementMixin.apply_led_object_edge_pick,
        "_move_led_for_reanchored_value": ScenePlacementMixin._move_led_for_reanchored_value,
    }
    for name, fn in movers.items():
        if helper_name not in inspect.getsource(fn):
            failures.append(f"E FAIL: {name} must carry the BS<->LED glue via {helper_name}")
    helper_src = inspect.getsource(ScenePlacementMixin._carry_led_glue_over_translation_change)
    if "_carry_glued_optical_led(" not in helper_src:
        failures.append("E FAIL: the carry helper must delegate to _carry_glued_optical_led")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0133 LED object-edge distance edit must carry the BS<->LED glue")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] LED distance edit carries the glued beam splitter so it tracks the LED (bugs/0133)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
