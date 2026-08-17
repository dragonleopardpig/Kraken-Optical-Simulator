"""Guard for bugs/0626 — the FOV solve converges to readout precision and recruits the arm.

flag_20260817_131423: "input 55x55, why become 54.5x54.5? can't it be exact? Note the
lens is almost hitting the RA mirror, the auto solve should adjust the 4th section
distance if 3rd section can't meet." Two defects: the refinement's 1% tolerance let the
secant exit at -0.91% (the honest delivered readout then shows 54.5), and the lens-leg
slide's gap-positivity refusal set no shortfall, so the bugs/0573 fold-arm recruitment
("Made room first: the fold mirror and the camera moved ...") never fired on that branch.

Checks (display-free):
  A  CONTRACT — tolerance <= 0.1% (readout precision), pass ceiling >= 10; the
     _apply_conjugate_pair recruitment (slide_fold_arm_along_leg on shortfall) is wired.
  B  BEHAVIOUR — on a linear machine delivering +0.5% (inside the OLD tolerance), the
     refinement keeps going and converges VERIFIED to within 0.1%.
  C  BEHAVIOUR — a slide refused because the DOWNSTREAM gap runs out reports its
     shortfall through `_lens_leg_slide_shortfall` (the recruitment trigger); an
     UPSTREAM exhaustion stays a plain refusal (the arm cannot make room there).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0626_solve_exactness_arm_recruitment
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    from KrakenOS.UI.services import scene_placement_commands as placement_module

    # ---------------------------------------------------------------- A: contract
    tolerance = float(QuickEstimationService._FIELD_FILL_TOLERANCE)
    passes = int(QuickEstimationService._FIELD_FILL_MAX_PASSES)
    apply_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    if tolerance > 0.001 + 1e-12:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0626): field-fill tolerance {tolerance} > 0.1% -- a 55x55 "
            "solve may honestly deliver 54.5 and stop"
        )
    elif passes < 10:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0626): pass ceiling {passes} < 10 -- the tighter tolerance "
            "needs the extra secant passes"
        )
    elif "slide_fold_arm_along_leg(" not in apply_src:
        ok = False
        notes.append(
            "FAIL: A (bugs/0626): _apply_conjugate_pair no longer recruits the fold-arm "
            "slide on a shortfall"
        )
    else:
        notes.append(
            f"PASS: A: tolerance {tolerance:.4%}, {passes} passes, arm recruitment wired"
        )

    # ---------------------------------------------------------------- B: convergence
    class _Editor:
        def __init__(self):
            self._folded_m_correction_state = None
            self._folded_field_center_state = None

        def _world_placed_chain_rows(self):
            return []

        def append_debug(self, message):
            pass

    class _LinearMachine(QuickEstimationService):
        """Delivers k x the booked image semi -- +0.5% sat INSIDE the old 1% tolerance."""

        def __init__(self, editor, k, target):
            super().__init__(SimpleNamespace(editor=editor))
            self._k = float(k)
            self._booked = float(target)
            self.bookings = 0

        def _measured_delivered_image_semi(self, object_semi):
            return self._k * self._booked

        def _apply_conjugate_pair(self, object_semi, image_semi):
            self._booked = float(image_semi)
            self.bookings += 1
            return True, ""

    target = 16.29
    machine = _LinearMachine(_Editor(), 1.005, target)
    message = machine._refine_folded_field_fill(38.89, target)
    final_error = abs(machine._k * machine._booked / target - 1.0)
    if "VERIFIED" not in message:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0626): +0.5% machine did not converge VERIFIED "
            f"(message: {message.strip()!r}) -- the old tolerance would have accepted it"
        )
    elif final_error > 0.001:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0626): converged at {final_error:.3%} residual > 0.1%"
        )
    else:
        notes.append(
            f"PASS: B: +0.5% machine refined to {final_error:.4%} in "
            f"{machine.bookings} booking(s), VERIFIED"
        )

    # ---------------------------------------------------------------- C: shortfall channel
    mixin = None
    for name, cls in vars(placement_module).items():
        if isinstance(cls, type) and hasattr(cls, "slide_lens_block_along_its_leg"):
            mixin = cls
            break
    if mixin is None:
        return False, notes + ["FAIL: C: no mixin with slide_lens_block_along_its_leg"]

    class _Row:
        def __init__(self, thickness):
            self.thickness = float(thickness)
            self.desp_x = self.desp_y = self.desp_z = 0.0

    class _Slider(mixin):
        def __init__(self, down_gap, up_gap=50.0):
            self.rows = [_Row(10.0), _Row(up_gap), _Row(3.0), _Row(down_gap), _Row(10.0)]
            self.debug: list[str] = []

        def _lens_leg_slide_plan(self):
            return ([2, 3], np.array([1.0, 0.0, 0.0]), True)

        def _lens_leg_room_to_fold(self, direction, members):
            return None

        def _is_swap_preservable_block_row(self, row):
            return False

        def append_debug(self, message):
            self.debug.append(str(message))

    downstream_case = _Slider(down_gap=5.0)
    result = downstream_case.slide_lens_block_along_its_leg(20.0)
    want_shortfall = 20.0 - max(5.0 - 1.0, 0.0)
    upstream_case = _Slider(down_gap=50.0, up_gap=10.0)
    result_up = upstream_case.slide_lens_block_along_its_leg(-60.0)
    if result is not None or abs(float(downstream_case._lens_leg_slide_shortfall) - want_shortfall) > 1e-9:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0626): downstream-gap refusal reported shortfall "
            f"{getattr(downstream_case, '_lens_leg_slide_shortfall', None)} != {want_shortfall} "
            "-- the fold-arm recruitment never fires and the solve stops short (54.5)"
        )
    elif not str(downstream_case._lens_leg_slide_refusal or ""):
        ok = False
        notes.append("FAIL: C (bugs/0626): downstream-gap refusal lost its refusal text")
    elif result_up is not None or float(upstream_case._lens_leg_slide_shortfall) != 0.0:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0626): upstream exhaustion set shortfall "
            f"{upstream_case._lens_leg_slide_shortfall} -- the arm cannot make room "
            "in front of the lens; recruitment there would dislocate"
        )
    else:
        notes.append(
            f"PASS: C: downstream refusal reports shortfall {want_shortfall}, upstream stays plain"
        )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Solve-exactness-and-arm-recruitment validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
