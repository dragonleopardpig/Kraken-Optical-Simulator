#!/usr/bin/env python3
"""Display-free guard for bugs/0127: the LED<->beam-splitter two-body glue must stay
REACHABLE and HOLD after the beam splitter is promoted from its STEP overlay to a
promoted optical solid row.

Why it exists (user flagged it twice, flag_20260624_085546 / _085743):
  Promoting the beam splitter removes its "optical" STEP overlay (it becomes a
  promoted solid ROW).  The old glue gate (``set_optical_led_glue`` /
  ``_optical_led_glue_available``) required BOTH the "optical" AND "led" *overlays*,
  so after promotion the "Glue BS to LED" item vanished -- there was no way to glue
  the LED to the promoted splitter, and the user got funnelled into the misnamed
  "Glue STEP to Surrogate" reset (which just zeroes the overlay's drag offsets and
  retraces -- not a two-body glue).  Dragging the LED then proved they were not glued.

What it checks (binds the REAL ScenePlacementMixin methods onto a light fake editor):
  A. With the BS PROMOTED (a row labelled "optical") + the LED overlay present,
     ``_optical_bs_body_present`` is True, ``set_optical_led_glue(True)`` succeeds,
     and the menu-availability predicate ``_optical_led_glue_available`` is True.
  B. Glue is refused with no BS body at all (no overlay, no promoted row).
  C. Glue is refused with no LED.
  D. CARRY -- the user drags the promoted BS row: the glued LED overlay follows by
     exactly the same delta (one delta, never doubled).
  E. CARRY -- the user drags the LED: the glued promoted BS row follows by the same
     delta, and the re-entrancy guard stops the row primitive carrying back to the
     LED (so the LED is not double-moved).
  F. No carry happens when the two bodies are not glued.
  G. Source contract -- all three translate primitives route through
     ``_carry_glued_optical_led`` (the row primitives behind the ``_optical_led_carry_active``
     guard), the glue gate consults ``_optical_bs_body_present`` (not the old
     both-overlays form), and availability consults ``_promoted_optical_solid_row_index``.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_led_bs_glue_promoted

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
    """A tk-free stand-in carrying the REAL glue/carry methods so the test exercises
    production code, not a paraphrase of it."""

    # --- real methods under test (bound straight off the mixin) ---
    optical_led_glued = ScenePlacementMixin.optical_led_glued
    set_optical_led_glue = ScenePlacementMixin.set_optical_led_glue
    _optical_bs_body_present = ScenePlacementMixin._optical_bs_body_present
    _promoted_optical_solid_row_index = ScenePlacementMixin._promoted_optical_solid_row_index
    _carry_glued_optical_led = ScenePlacementMixin._carry_glued_optical_led
    translate_scene_row_pose_vector = ScenePlacementMixin.translate_scene_row_pose_vector

    def __init__(self, *, has_optical_overlay: bool, has_led: bool, promoted_bs: bool) -> None:
        self.rows = [_Row()] if promoted_bs else []
        self._promoted_bs = promoted_bs
        self._has_optical_overlay = has_optical_overlay
        self._has_led = has_led
        self._offsets = {"led": [0.0, 0.0, 0.0], "optical": [0.0, 0.0, 0.0]}
        self.status_var = SimpleNamespace(set=lambda *a, **k: None)

    # --- fake-only collaborators ---
    def _step_path_for_label(self, label):
        label = str(label or "").strip().lower()
        if label == "led":
            return "/tmp/led.step" if self._has_led else None
        if label == "optical":
            return "/tmp/optical.step" if self._has_optical_overlay else None
        return None

    def _open3d_step_label_for_optical_solid_row(self, row):
        return "optical" if self._promoted_bs else "lens"

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

    from KrakenOS.UI.services.open3d_face_assignment import Open3DFaceAssignmentService

    # A) BS promoted away (no 'optical' overlay) + LED overlay present -> glue reachable.
    ed = _FakeEditor(has_optical_overlay=False, has_led=True, promoted_bs=True)
    if not ed._optical_bs_body_present():
        failures.append("FAIL: a promoted 'optical' solid should count as a BS body present")
    if ed._promoted_optical_solid_row_index("optical") != 0:
        failures.append("FAIL: _promoted_optical_solid_row_index should find the promoted BS row")
    if not ed.set_optical_led_glue(True):
        failures.append("FAIL: glue must succeed with a promoted BS + LED overlay (the 0127 gap)")
    if not ed.optical_led_glued():
        failures.append("FAIL: glue flag not set after a successful glue")
    svc = Open3DFaceAssignmentService(
        SimpleNamespace(editor=ed, status_var=ed.status_var, append_debug=lambda *a, **k: None)
    )
    if not svc._optical_led_glue_available():
        failures.append("FAIL: menu availability must be True for a promoted BS + LED overlay")

    # B) No BS body at all -> glue refused.
    ed_nobs = _FakeEditor(has_optical_overlay=False, has_led=True, promoted_bs=False)
    if ed_nobs._optical_bs_body_present():
        failures.append("FAIL: no overlay + no promoted row must NOT report a BS body present")
    if ed_nobs.set_optical_led_glue(True):
        failures.append("FAIL: glue must be refused when there is no beam-splitter body")
    if ed_nobs.optical_led_glued():
        failures.append("FAIL: glue flag must stay False when glue was refused (no BS)")

    # C) No LED -> glue refused.
    ed_noled = _FakeEditor(has_optical_overlay=False, has_led=False, promoted_bs=True)
    if ed_noled.set_optical_led_glue(True):
        failures.append("FAIL: glue must be refused when the LED is not imported")

    # D) Carry (contract updated by bugs/0437, flag_20260726_110337 "old bug
    #    resurface"): dragging the promoted BS row positions it INSIDE the LED
    #    housing -- the glued LED must STAY PUT (a symmetric carry cancelled the
    #    relative move). The assembly direction lives in check E (LED-drag carries
    #    the BS).
    #    bugs/0508 B note: the USER gesture on a real editor now routes through the LED
    #    translate (the assembly move); this fake pins the INTERNAL layer, so the call
    #    passes record_history=False -- the delegation is explicitly a user-gesture-only
    #    behavior and internal deltas must keep the 0437 child-seat semantics.
    ed_d = _FakeEditor(has_optical_overlay=False, has_led=True, promoted_bs=True)
    ed_d._offsets["led"] = [1.0, 2.0, 3.0]
    ed_d.set_optical_led_glue(True)
    ed_d.translate_scene_row_pose_vector(0, (10.0, 0.0, -4.0), record_history=False)
    if not _approx(ed_d.rows[0].desp, (10.0, 0.0, -4.0)):
        failures.append(f"FAIL: BS row should move by the drag delta (got {ed_d.rows[0].desp})")
    if not _approx(ed_d._step_placement_offset_xyz("led"), (1.0, 2.0, 3.0)):
        failures.append(
            f"FAIL (0437): an internal BS delta must leave the glued LED where it is "
            f"(got {ed_d._step_placement_offset_xyz('led')}, expected unchanged (1,2,3))"
        )

    # E) Carry: user drags the LED -> the glued promoted BS row follows; the row
    #    primitive must NOT carry back to the LED (re-entrancy guard).
    ed_e = _FakeEditor(has_optical_overlay=False, has_led=True, promoted_bs=True)
    ed_e._offsets["led"] = [0.0, 0.0, 0.0]
    ed_e.set_optical_led_glue(True)
    ed_e._carry_glued_optical_led("led", (0.0, 5.0, 7.0))
    if not _approx(ed_e.rows[0].desp, (0.0, 5.0, 7.0)):
        failures.append(f"FAIL: glued BS row should follow the LED by one delta (got {ed_e.rows[0].desp})")
    if not _approx(ed_e._step_placement_offset_xyz("led"), (0.0, 0.0, 0.0)):
        failures.append(
            f"FAIL: carry-back guard failed -- the LED was moved again by the row primitive "
            f"(got {ed_e._step_placement_offset_xyz('led')}, expected unchanged (0,0,0))"
        )

    # F) Not glued -> no carry on either path.
    ed_f = _FakeEditor(has_optical_overlay=False, has_led=True, promoted_bs=True)
    ed_f._offsets["led"] = [1.0, 1.0, 1.0]
    ed_f._carry_glued_optical_led("led", (3.0, 3.0, 3.0))
    if not _approx(ed_f.rows[0].desp, (0.0, 0.0, 0.0)):
        failures.append("FAIL: unglued scene must not carry the BS row when the LED moves")
    ed_f.translate_scene_row_pose_vector(0, (2.0, 0.0, 0.0))
    if not _approx(ed_f._step_placement_offset_xyz("led"), (1.0, 1.0, 1.0)):
        failures.append("FAIL: unglued scene must not carry the LED when the BS row moves")

    # G) Source contract -- the wiring that makes the carry fire on EVERY drag path.
    overlay_src = inspect.getsource(ScenePlacementMixin.translate_step_overlay)
    if "_carry_glued_optical_led(" not in overlay_src:
        failures.append("FAIL: translate_step_overlay must route the BS<->LED carry through _carry_glued_optical_led")

    vec_src = inspect.getsource(ScenePlacementMixin.translate_scene_row_pose_vector)
    if "_carry_glued_optical_led(" not in vec_src or "_optical_led_carry_active" not in vec_src:
        failures.append("FAIL: translate_scene_row_pose_vector must carry the glued partner behind the re-entrancy guard")

    from KrakenOS.UI.services.optical_solid_workflow import LayoutOpticalSolidWorkflowMixin

    peraxis_src = inspect.getsource(LayoutOpticalSolidWorkflowMixin.translate_scene_row_pose)
    if "_carry_glued_optical_led(" not in peraxis_src or "_optical_led_carry_active" not in peraxis_src:
        failures.append("FAIL: translate_scene_row_pose must carry the glued partner behind the re-entrancy guard")

    gate_src = inspect.getsource(ScenePlacementMixin.set_optical_led_glue)
    if "_optical_bs_body_present(" not in gate_src:
        failures.append("FAIL: set_optical_led_glue must gate on _optical_bs_body_present (promoted BS counts)")

    avail_src = inspect.getsource(Open3DFaceAssignmentService._optical_led_glue_available)
    if "_promoted_optical_solid_row_index(" not in avail_src:
        failures.append("FAIL: _optical_led_glue_available must accept a promoted BS via _promoted_optical_solid_row_index")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0127 LED<->promoted-BS glue must stay reachable and hold")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] LED<->BS glue stays reachable after promotion and carries both bodies (bugs/0127)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
