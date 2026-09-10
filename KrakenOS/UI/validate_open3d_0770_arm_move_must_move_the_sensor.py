"""Guard for bugs/0770 -- MOTOR 1 must be shown to have moved the sensor, or not move at all.

bugs/0759 wrote: "the sensor moves in x only". That is true of the frame it was measured on and
not of every scene. The seat is written in ``desp_x`` while the pad is written as a THICKNESS,
which advances along whatever direction the chain points after the fold. Measured, for a -10 mm
request:

    om05a_folded_80mm   sensor moves (-10,  0, 0)   |d| 10.00   <- the two axes coincide
    om05a_folded        sensor moves (-10, +20, 0)  |d| 22.36   <- they do not

The second scene's mirror 2 carries ``tilt_y 90, tilt_z 180``; permuted x/y components are the
tell ([[reference_step_offset_frame]]). The first order cannot see any of it -- it books stations,
so it reported a clean 1.0000 gain while the traced focus moved by only 0.4142 of the request
(that wrong 3D motion projected onto the axis), and the solve wrote geometry that looked solved
and was not.

So the move measures the sensor before and after and reverts when it did not travel ``delta``.

Checks (display-free, pure):
  A  a frame where the sensor travels the requested distance is APPLIED and returns True;
  B  a frame where it travels the wrong distance is REVERTED, returns False, and records a
     reason naming both the request and the actual travel;
  C  the revert restores every field the move writes -- seat desp_x, pad thickness AND the
     bugs/0761 carry pair -- not just the two obvious ones;
  D  with no measurable sensor the move still applies (the guard stands down rather than
     blocking every scene that cannot report a world point), and the tolerance is sub-pixel.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0770_arm_move_must_move_the_sensor
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np


class _Row:
    def __init__(self, thickness=0.0, desp_x=0.0):
        self.thickness = float(thickness)
        self.desp_x = float(desp_x)
        self.desp_y = 0.0
        self.desp_z = 0.0

    def snap(self):
        return (self.thickness, self.desp_x, self.desp_y, self.desp_z)


def _service(mode):
    """mode: 'good' (sensor tracks delta), 'bad' (sensor travels 2.236x), 'blind' (no point)."""
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    rows = [_Row(10.0, 0.0) for _ in range(6)]
    rows[3].desp_x = 100.0          # seat
    rows[4].thickness = 8.82        # pad
    state = {"applied": 0.0}

    class _QE(QuickEstimationService):
        def _camera_focus_stage(self):
            return {"row": 4, "min_mm": -100.0, "max_mm": 100.0,
                    "arm": {"row": 3, "carry_row": 1, "carry_pair_row": 2,
                            "min_mm": -1e9, "max_mm": 1e9}}

        def _sensor_world_point(self):
            if mode == "blind":
                return None
            # the sensor's position is a function of what the pad currently holds
            travelled = rows[4].thickness - 8.82
            if mode == "good":
                return np.array([travelled, 0.0, 0.0])
            return np.array([travelled, 2.0 * travelled, 0.0])   # |d| = 2.236x

    editor = SimpleNamespace(rows=rows, append_debug=lambda m: None)
    return _QE(SimpleNamespace(editor=editor)), rows, editor


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: a well-behaved frame applies ----------------------------------------------------
    svc, rows, editor = _service("good")
    before = [r.snap() for r in rows]
    result = svc._apply_camera_arm_move(-10.0)
    ok(result is True, f"A1: a frame whose sensor travels the request applies (got {result!r})")
    ok(
        rows[3].desp_x == 90.0 and abs(rows[4].thickness - (-1.18)) < 1e-9,
        f"A2: and the seat and pad really moved (seat {rows[3].desp_x}, pad {rows[4].thickness})",
    )

    # ---- B: a mis-aligned frame reverts ------------------------------------------------------
    svc, rows, editor = _service("bad")
    before = [r.snap() for r in rows]
    result = svc._apply_camera_arm_move(-10.0)
    ok(result is False, f"B1: a frame whose sensor travels 2.236x is REFUSED (got {result!r})")
    reason = str(getattr(editor, "_camera_arm_move_refusal", "") or "")
    ok(bool(reason), "B2: and records a reason")
    ok(
        "10" in reason and "22.36" in reason.replace("22.4", "22.36"),
        f"B3: naming the request AND the actual travel (got {reason!r})",
    )

    # ---- C: the revert restores EVERY field the move writes ----------------------------------
    after = [r.snap() for r in rows]
    ok(
        after == before,
        "C1: the revert restores seat desp_x, pad thickness AND the bugs/0761 carry pair -- "
        f"a partial revert leaves the filter behind (before {before} after {after})",
    )

    # ---- D: stands down when blind; tolerance is sub-pixel -----------------------------------
    svc, rows, editor = _service("blind")
    result = svc._apply_camera_arm_move(-10.0)
    ok(
        result is True and rows[3].desp_x == 90.0,
        "D1: with no measurable sensor the move still applies -- the guard stands down rather "
        "than blocking every scene that cannot report a world point",
    )
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    tol = float(QuickEstimationService._ARM_MOVE_TOL_MM)
    ok(0.0 < tol < 0.153, f"D2: the tolerance ({tol} mm) is inside one pixel of depth of focus")
    src = inspect.getsource(QuickEstimationService._apply_camera_arm_move)
    ok(
        "_sensor_world_point()" in src and src.count("_sensor_world_point()") >= 2,
        "D3: the sensor is read BEFORE and AFTER -- one reading cannot tell you whether it moved",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0770 arm-move-must-move-the-sensor validation PASSED")
        return 0
    print("0770 arm-move-must-move-the-sensor validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
