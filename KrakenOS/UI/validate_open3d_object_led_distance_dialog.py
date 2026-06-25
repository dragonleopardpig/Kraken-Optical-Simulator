#!/usr/bin/env python3
"""Display-free guard for bugs/0151: the Object->LED distance dialog must operate on the
LIVE distance (what the amber arrow shows and where the LED edge sits), not the raw
``led_object_edge_distance_mm`` knob, so editing it after a carry-drag puts the LED where
the user typed.

Why it exists (flag_20260624_203712_059 "changing the thickness of Object LED via dialog
pop up is not working"):
  The live "Object -> LED" dimension is ``led_object_edge_distance_mm + placement_offset_z``
  (a free carry-drag adds the axial offset on top of the typed knob WITHOUT rewriting it --
  see the live_distance derivation in open3d_thickness_dimensions, bugs/0125). The edge-
  distance dialog used to PREFILL and WRITE the raw knob, so after a drag of -71.34 it
  showed the stale knob (200) instead of the live 128.7, and typing V landed the LED's edge
  at V + offset_z (28.66 for V=100), not V. The fix prefills the live distance and writes
  ``knob = typed - offset_z`` so the live distance becomes the typed value, while leaving
  ``placement_offset`` untouched -- the bugs/0133 glue-carry tracks ``_led_step_z_translation``
  (which excludes offset_z), so the glued beam splitter is shoved by the SAME net z-shift as
  the LED edge.

What it checks (binds the REAL ScenePlacementMixin.set_led_edge_distance + collaborators
onto a tk-free fake editor; the Tk prompt is stubbed to return the typed value):
  A. After a drag (offset_z=-71.34, knob=200, live=128.7), typing V=100 makes the LIVE
     distance 100 (knob -> 171.34, offset untouched).
  B. The dialog PREFILL is the live distance (128.7), not the raw knob (200).
  C. Undragged (offset_z=0): the fix is a no-op -- typing 150 writes knob=150, live=150.
  D. A glued promoted BS follows the LED's NET edge move (128.7 -> 100 = -28.66) on the
     post-drag distance edit, not the raw knob delta.
  E. Source contract: set_led_edge_distance reconciles the LED placement offset_z AND still
     routes the glue carry.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_object_led_distance_dialog

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
    """tk-free stand-in carrying the REAL distance/glue/carry methods so the test exercises
    production code. The beam splitter is a PROMOTED optical solid row; the LED is an overlay.
    The Tk edge-distance prompt is stubbed to return ``typed`` and record the prefill it was
    handed."""

    # --- real methods under test (bound straight off the mixin) ---
    set_led_edge_distance = ScenePlacementMixin.set_led_edge_distance
    _led_step_z_translation = ScenePlacementMixin._led_step_z_translation
    _clear_led_edge_dimension_override = ScenePlacementMixin._clear_led_edge_dimension_override
    _carry_led_glue_over_translation_change = ScenePlacementMixin._carry_led_glue_over_translation_change
    _carry_glued_optical_led = ScenePlacementMixin._carry_glued_optical_led
    translate_scene_row_pose_vector = ScenePlacementMixin.translate_scene_row_pose_vector
    optical_led_glued = ScenePlacementMixin.optical_led_glued
    set_optical_led_glue = ScenePlacementMixin.set_optical_led_glue
    _optical_bs_body_present = ScenePlacementMixin._optical_bs_body_present
    _promoted_optical_solid_row_index = ScenePlacementMixin._promoted_optical_solid_row_index

    def __init__(
        self,
        *,
        glued: bool,
        knob: float = 200.0,
        offset_z: float = 0.0,
        typed: float = 100.0,
        edge_local_z: float = 0.0,
    ) -> None:
        self.rows = [_Row()]  # one promoted "optical" (beam splitter) solid row
        self.led_object_edge_distance_mm = float(knob)
        self.led_step_object_edge_local_z = float(edge_local_z)
        self._offsets = {"led": [22.8856, -0.0208, float(offset_z)], "optical": [0.0, 0.0, 0.0]}
        self._dimension_anchor_overrides: dict = {}
        self.status_var = SimpleNamespace(set=lambda *a, **k: None)
        self._typed = float(typed)
        self.prefill_seen: float | None = None
        if glued:
            assert self.set_optical_led_glue(True), "test setup: glue should succeed"

    # --- stubbed Tk prompt: capture the prefill, return the typed value ---
    def _ask_led_edge_distance(self, initial_value, *args, **kwargs):
        self.prefill_seen = float(initial_value)
        return self._typed

    # --- fake-only collaborators ---
    def _default_led_object_edge_distance(self) -> float:
        return 50.0

    def _begin_history_capture(self, *_a, **_k):
        pass

    def _commit_history_capture(self, *_a, **_k):
        pass

    def _refresh_open_3d_views(self, *_a, **_k):
        pass

    def _step_path_for_label(self, label):
        return "/tmp/led.step" if str(label or "").strip().lower() == "led" else None

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

    # --- test helper ---
    def live_distance(self) -> float:
        return float(self.led_object_edge_distance_mm) + float(self._step_placement_offset_xyz("led")[2])


def _approx(a, b, tol: float = 1e-4) -> bool:
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(float(a) - float(b)) <= tol
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(a, b))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    DRAG = -71.3406  # the recorded carry-drag axial offset (flag_20260624_203614_765)
    LIVE0 = 200.0 + DRAG          # the live distance the dimension shows after the drag (128.6594)
    NET_MOVE = 100.0 - LIVE0      # how far the LED edge moves when the user types 100 (-28.6594)

    # A) Post-drag edit lands the LED edge at the TYPED live distance.
    ed = _FakeEditor(glued=False, knob=200.0, offset_z=DRAG, typed=100.0)
    if not _approx(ed.live_distance(), LIVE0):
        failures.append(f"A SETUP: live distance should be 200+({DRAG})={LIVE0:.4g} (got {ed.live_distance():.4g})")
    ed.set_led_edge_distance()
    if not _approx(ed.live_distance(), 100.0):
        failures.append(
            f"A FAIL: after typing 100 the LIVE Object->LED distance must be 100 "
            f"(got {ed.live_distance():.4g}); the dialog still ignores the drag offset_z"
        )
    if not _approx(ed.led_object_edge_distance_mm, 100.0 - DRAG):
        failures.append(
            f"A FAIL: the knob must absorb the offset (expected {100.0 - DRAG:.4g}, got {ed.led_object_edge_distance_mm:.4g})"
        )
    if not _approx(ed._step_placement_offset_xyz("led"), (22.8856, -0.0208, DRAG)):
        failures.append(f"A FAIL: placement_offset must be left untouched (got {ed._step_placement_offset_xyz('led')})")

    # B) The dialog prefills the LIVE distance, not the raw knob.
    if ed.prefill_seen is None or not _approx(ed.prefill_seen, LIVE0):
        failures.append(
            f"B FAIL: the dialog must prefill the live distance {LIVE0:.4g}, not the raw knob 200 "
            f"(prefill was {ed.prefill_seen})"
        )

    # C) Undragged: the fix is a no-op -- typed value writes straight to the knob.
    ed_c = _FakeEditor(glued=False, knob=200.0, offset_z=0.0, typed=150.0)
    ed_c.set_led_edge_distance()
    if not (_approx(ed_c.led_object_edge_distance_mm, 150.0) and _approx(ed_c.live_distance(), 150.0)):
        failures.append(
            f"C FAIL: undragged edit must write knob=live=150 "
            f"(knob {ed_c.led_object_edge_distance_mm:.4g}, live {ed_c.live_distance():.4g})"
        )
    if not _approx(ed_c.prefill_seen, 200.0):
        failures.append(f"C FAIL: undragged prefill must be the knob 200 (got {ed_c.prefill_seen})")

    # D) Glued BS follows the LED's NET edge move (128.66 -> 100 = -28.66), not the raw knob delta.
    ed_d = _FakeEditor(glued=True, knob=200.0, offset_z=DRAG, typed=100.0)
    ed_d.set_led_edge_distance()
    if not _approx(ed_d.rows[0].desp, (0.0, 0.0, NET_MOVE)):
        failures.append(
            f"D FAIL: a glued BS must follow the LED edge's net -28.66 move on a post-drag "
            f"distance edit (got {ed_d.rows[0].desp}); the glue would drift if the carry used the raw knob"
        )
    if not _approx(ed_d.live_distance(), 100.0):
        failures.append(f"D FAIL: glued + dragged edit must still land live=100 (got {ed_d.live_distance():.4g})")

    # E) Source contract.
    src = inspect.getsource(ScenePlacementMixin.set_led_edge_distance)
    if '_step_placement_offset_xyz("led")' not in src or "offset_z" not in src:
        failures.append("E FAIL: set_led_edge_distance must reconcile the LED placement offset_z (bugs/0151)")
    if "_carry_led_glue_over_translation_change" not in src:
        failures.append("E FAIL: set_led_edge_distance must still route the BS<->LED glue carry (bugs/0133)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0151 Object->LED distance dialog must edit the LIVE distance")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Object->LED distance dialog edits the live distance after a drag, glue follows (bugs/0151)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
