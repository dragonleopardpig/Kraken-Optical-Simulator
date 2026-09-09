"""Guard for bugs/0759 -- the imaging group on one stage (MOTOR 1), the lens on another.

User, describing the production bench: "One Motor move the Lens + Filter + 40mm RA mirror +
Camera together, another Motor move the lens alone."

That is two genuinely independent knobs, and it is what the om05a needs:

    Motor 2  the lens alone      -> the existing thickness PAIR: s and s' trade off, K fixed
    Motor 1  the whole group     -> s changes, s' FIXED, K changes

bugs/0756 booked the image-side correction by sliding the SENSOR along its leg, which spends
camera-to-mirror clearance and capped the deliverable device at 48.4-56.1 mm. Moving the whole
group instead changes the track without spending any clearance -- measured, the mirror-to-sensor
distance stays 55.385 -> 55.412 mm across a 70.75 mm group travel.

The subtlety this guard pins: moving the fold mirror's SEAT alone does NOT work. Measured, a
5 mm seat move shortens the lens->mirror leg by 5 mm and lengthens mirror->sensor by exactly
5 mm, leaving the conjugate invariant to four decimals. The same delta must go on the standoff
so the assembly translates RIGIDLY.

Checks (display-free, pure):
  A  the stage spec parses an arm, and a bad arm row degrades to the base stage rather than
     disabling it;
  B  the arm primitive writes the SAME delta to both the seat and the standoff -- the rigid
     invariant -- and refuses without an arm;
  C  the solve books through the arm when one is declared, bounded, and refuses past the end
     with the number;
  D  a scene with no arm still uses the bugs/0756 sensor-only path.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0759_two_motor_imaging_group
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Row:
    def __init__(self, name, thickness=0.0, desp_x=0.0):
        self.name = name
        self.thickness = float(thickness)
        self.desp_x = float(desp_x)


def _service(stage, rows=None):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    rows = rows if rows is not None else [
        _Row(f"r{i}") for i in range(16)
    ] + [_Row("RA mirror 2 (40 mm)", 36.31, 272.6827)] + [
        _Row(f"s{i}") for i in range(7)
    ] + [_Row("sensor standoff", 9.67)]
    editor = SimpleNamespace(camera_focus_stage=stage, rows=rows)
    return QuickEstimationService(SimpleNamespace(editor=editor)), rows


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    SEAT, PAD = 16, 24
    good = {"enabled": True, "row": PAD, "min_mm": -60.0, "max_mm": 30.0,
            "arm_row": SEAT, "arm_min_mm": 192.68, "arm_max_mm": 292.68}

    # ---- A: the spec ------------------------------------------------------------------------
    svc, _rows = _service(good)
    stage = svc._camera_focus_stage()
    ok(isinstance(stage, dict) and isinstance(stage.get("arm"), dict),
       "A1: a stage declaring an arm parses one")
    ok(isinstance(stage, dict) and int(stage["arm"]["row"]) == SEAT
       and abs(float(stage["arm"]["max_mm"]) - 292.68) < 1e-9,
       "A2: the arm carries its own row and travel limits")
    svc, _ = _service({**good, "arm_row": 999})
    st = svc._camera_focus_stage()
    ok(isinstance(st, dict) and "arm" not in st,
       "A3: an out-of-range arm row degrades to the base stage, it does not disable it")
    svc, _ = _service({k: v for k, v in good.items() if not k.startswith("arm")})
    st = svc._camera_focus_stage()
    ok(isinstance(st, dict) and "arm" not in st,
       "A4: a scene with no arm is still a valid bugs/0756 sensor-only stage")

    # ---- B: the primitive is a RIGID translation ---------------------------------------------
    svc, rows = _service(good)
    seat0, pad0 = rows[SEAT].desp_x, rows[PAD].thickness
    ok(svc._apply_camera_arm_move(-21.94) is True, "B1: the arm move applies")
    dseat = rows[SEAT].desp_x - seat0
    dpad = rows[PAD].thickness - pad0
    ok(abs(dseat - (-21.94)) < 1e-9 and abs(dpad - (-21.94)) < 1e-9,
       f"B2: the SAME delta goes on the seat and the standoff ({dseat:+.4f} / {dpad:+.4f}) -- "
       f"a seat move alone leaves the conjugate invariant (the two legs trade off)")
    svc, rows = _service({k: v for k, v in good.items() if not k.startswith("arm")})
    before = (rows[SEAT].desp_x, rows[PAD].thickness)
    ok(svc._apply_camera_arm_move(-5.0) is False
       and (rows[SEAT].desp_x, rows[PAD].thickness) == before,
       "B3: without an arm it refuses and writes nothing")
    svc, _ = _service(None)
    ok(svc._apply_camera_arm_move(-5.0) is False, "B4: and with no stage at all")

    # ---- C: the solve routes through it -------------------------------------------------------
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok("self._apply_camera_arm_move(float(folded[\"image_delta\"]))" in src,
       "C1: the image-side correction is booked as a group move when an arm is declared")
    ok("image_handled = True" in src and src.find("_apply_camera_arm_move") < src.find(
           'if not image_locked_reason and not image_handled:'),
       "C2: and once booked, the sensor-only path is skipped")
    ok("the imaging group would have to travel to" in src,
       "C3: running past the stage end refuses naming where the group would have to sit")
    ok('arm["min_mm"] - 1.0e-9 <= travelled <= arm["max_mm"] + 1.0e-9' in src,
       "C4: bounded at BOTH ends, against the seat's resulting value")

    # ---- D: the bugs/0756 path survives for scenes without an arm --------------------------------
    ok('int(stage["row"]) == int(img_row_write)' in src,
       "D1: the sensor-only stage path is still there for scenes that declare no arm")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0759 two-motor-imaging-group validation PASSED")
        return 0
    print("0759 two-motor-imaging-group validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
