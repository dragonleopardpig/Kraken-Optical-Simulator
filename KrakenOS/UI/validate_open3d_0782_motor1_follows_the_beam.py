"""Guard for bugs/0782 -- MOTOR 1 moves the imaging group along the BEAM on any frame.

User: "the production one have exactly 2 motors same as the 80mm version."

bugs/0770 found MOTOR 1 on om05a_folded throwing the sensor (-10, +20, 0) for a -10 mm request and
made the move refuse, which left production with no image-side motor at all. Measured per write
(+1 mm, row math, no trace):

                        lens leg   seat desp_x: mirror / sensor    standoff: sensor   carry pair: filter
    om05a_folded_80mm   +x         (+1, 0, 0) / (+1, +1, 0)         (0, -1, 0)         +1 along the leg
    om05a_folded        -x         (+1, 0, 0) / (+1, -1, 0)         (0, -1, 0)         +1 along the leg

The standoff and the carry pair are chain THICKNESSES: they move along the beam the same way on
both frames. desp_x is a WORLD axis: on the production frame +1 moves the mirror TOWARD the object.
Writing all three with +delta doubled the fold-walk error and sent the filter the opposite way to
the group. The seat is now written with a MEASURED sign; with it the real production move carries
sensor, mirror and filter exactly -10.000 mm along the beam.

Checks (display-free; a kinematic stub reproduces the measured Jacobians of both frames):
  A  the sign is measured -- +1 on the 80 mm-like frame, -1 on the mirrored one -- and the probe
     nudge leaves the seat bit-for-bit as it was;
  B  on the mirrored frame the move APPLIES and carries sensor, mirror and filter exactly delta
     along the beam, where the pre-0782 writes put the sensor 2.236x off;
  C  on the 80 mm-like frame the writes are bit-identical to the pre-0782 ones;
  D  a sensor that travels the right DISTANCE the wrong WAY is refused and fully reverted;
  E  with no measurable world points the sign falls back to +1 -- the old writes, with the
     bugs/0770 distance check still in force;
  F  the solve's stage bound is computed with the same measured sign as the write.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0782_motor1_follows_the_beam
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np

FRONT, REAR, FILTER, PAIR, SEAT, PAD, IMAGE = 3, 7, 8, 9, 10, 12, 13


class _Row:
    def __init__(self, name, thickness=0.0, desp_x=0.0):
        self.name = name
        self.thickness = float(thickness)
        self.desp_x = float(desp_x)
        self.desp_y = 0.0
        self.desp_z = 0.0


def _rows(seat_x):
    return [
        _Row("Object"), _Row("fold"), _Row("prism exit gap (air)", 130.889),
        _Row("Front Optical Vertex Datum"), _Row("Blackbox 1", 9.7), _Row("Aperture Stop", 9.7),
        _Row("Blackbox 2", 11.9),
        _Row("Rear Optical Vertex Datum", 17.51),      # 7  C1 = the carry row
        _Row("Filter 48-926", 1.0),                    # 8
        _Row("to camera", 31.11),                      # 9  the carry pair (seat - 1)
        _Row("RA mirror 2 (40 mm)", 36.31, seat_x),    # 10 the seat
        _Row("placed", 0.0),
        _Row("sensor standoff", 9.67),                 # 12 the pad
        _Row("Image / Sensor"),                        # 13
    ]


def _editor(frame_sign, *, reversed_sensor=False, blind=False):
    """A frame whose lens leg runs along ``frame_sign * x``. Chain rows sit at x = sign * station;
    the seat is desp-placed at x = desp_x; the sensor rides the seat (x) and its fold walk puts
    y = y0 + sign * (desp_x - seat0) - (pad - pad0) -- the Jacobians measured on both om05a frames."""
    seat0 = 269.12 * frame_sign
    rows = _rows(seat0)
    pad0 = rows[PAD].thickness

    def station(i):
        return sum(float(r.thickness) for r in rows[:i])

    def point(i):
        i = int(i)
        if i == SEAT:
            return np.array([rows[SEAT].desp_x, 56.313, -25.0])
        if i == IMAGE:
            x = rows[SEAT].desp_x
            if reversed_sensor:
                x = 2.0 * seat0 - x            # the right distance, the wrong way
            y = 0.954 + frame_sign * (rows[SEAT].desp_x - seat0) - (rows[PAD].thickness - pad0)
            return np.array([x, y, -25.0])
        return np.array([frame_sign * station(i), 56.363, -25.0])

    ed = SimpleNamespace(rows=rows, append_debug=lambda m: None)
    if not blind:
        ed._imaging_lens_block_indices = lambda: (FRONT, REAR)
        ed._surface_reference_world_point = point
    return ed, point


def _service(editor):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    class _QE(QuickEstimationService):
        def _camera_focus_stage(self):
            return {"row": PAD, "min_mm": -1e9, "max_mm": 1e9,
                    "arm": {"row": SEAT, "carry_row": REAR, "min_mm": -1e9, "max_mm": 1e9}}

    return _QE(SimpleNamespace(editor=editor))


def _writes(rows):
    return (rows[SEAT].desp_x, rows[PAD].thickness, rows[REAR].thickness, rows[PAIR].thickness)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: the sign is measured, and the probe leaves no trace ---------------------------------
    for sign, label in ((+1, "80 mm-like (+x leg)"), (-1, "mirrored production-like (-x leg)")):
        ed, _ = _editor(sign)
        svc = _service(ed)
        seat_before = ed.rows[SEAT].desp_x
        measured, unit = svc._camera_arm_seat_axis(svc._camera_focus_stage())
        ok(measured == float(sign), f"A1: the seat sign on the {label} frame is {sign:+d} (got {measured:+.0f})")
        ok(unit is not None and abs(float(unit[0]) - sign) < 1e-9,
           f"A2: and the beam direction is {sign:+d}x (got {None if unit is None else np.round(unit, 6).tolist()})")
        ok(ed.rows[SEAT].desp_x == seat_before,
           "A3: the +1 mm probe nudge is restored bit-for-bit (saved, never subtracted)")

    # ---- B: the mirrored frame now moves the group along the beam --------------------------------
    ed, point = _editor(-1)
    svc = _service(ed)
    rows = ed.rows
    # the pre-0782 writes on this frame, for the record: seat +delta, pad +delta, carry pair
    legacy = _editor(-1)
    lrows = legacy[0].rows
    s0 = legacy[1](IMAGE)
    lrows[SEAT].desp_x += -10.0
    lrows[PAD].thickness += -10.0
    ok(abs(float(np.linalg.norm(legacy[1](IMAGE) - s0)) - 22.3607) < 1e-3,
       "B0: the stub reproduces the bug -- the old writes put the sensor 22.36 mm off for 10 mm")
    before = {k: point(i) for k, i in (("sensor", IMAGE), ("mirror", SEAT), ("filter", FILTER))}
    applied = svc._apply_camera_arm_move(-10.0)
    ok(applied is True, f"B1: MOTOR 1 applies on the mirrored frame (got {applied!r}, "
                        f"refusal {getattr(ed, '_camera_arm_move_refusal', '')!r})")
    beam = np.array([-1.0, 0.0, 0.0])
    for key, i in (("sensor", IMAGE), ("mirror", SEAT), ("filter", FILTER)):
        step = point(i) - before[key]
        ok(float(np.linalg.norm(step - (-10.0) * beam)) < 1e-9,
           f"B2: the {key} travels exactly -10 mm along the beam ({np.round(step, 6).tolist()})")

    # ---- C: the 80 mm-like frame writes exactly what it always did --------------------------------
    ed, _ = _editor(+1)
    svc = _service(ed)
    old = _writes(ed.rows)
    ok(svc._apply_camera_arm_move(-21.94) is True, "C1: MOTOR 1 applies on the 80 mm-like frame")
    expected = (old[0] + -21.94, old[1] + -21.94, old[2] + -21.94, old[3] - -21.94)
    ok(_writes(ed.rows) == expected,
       f"C2: seat, pad and carry pair are bit-identical to the pre-0782 writes ({_writes(ed.rows)} vs {expected})")

    # ---- D: the right distance the wrong way is refused -------------------------------------------
    ed, _ = _editor(+1, reversed_sensor=True)
    svc = _service(ed)
    snap = [(r.thickness, r.desp_x, r.desp_y, r.desp_z) for r in ed.rows]
    result = svc._apply_camera_arm_move(-10.0)
    ok(result is False, f"D1: a sensor moving 10 mm the WRONG way is refused (got {result!r}) -- "
                        f"a distance-only check passed it")
    ok([(r.thickness, r.desp_x, r.desp_y, r.desp_z) for r in ed.rows] == snap,
       "D2: and every field is reverted")
    ok(bool(str(getattr(ed, "_camera_arm_move_refusal", "") or "")), "D3: with a recorded reason")

    # ---- E: unmeasurable -> the old behaviour, still guarded by distance ---------------------------
    ed, _ = _editor(-1, blind=True)
    svc = _service(ed)
    ok(svc._camera_arm_seat_axis(svc._camera_focus_stage()) == (1.0, None),
       "E1: with no world points the sign falls back to +1 and no beam direction is claimed")
    old = _writes(ed.rows)
    ok(svc._apply_camera_arm_move(-5.0) is True and _writes(ed.rows) == (old[0] - 5.0, old[1] - 5.0, old[2] - 5.0, old[3] + 5.0),
       "E2: and the move writes exactly the pre-0782 values (the bugs/0770 check stands down when blind)")

    # ---- F: the stage bound and the write agree on direction ---------------------------------------
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok("travelled = float(rows[int(arm[\"row\"])].desp_x) + self._camera_arm_seat_axis(" in src,
       "F1: the solve bounds the seat at desp_x + (measured sign) * delta -- the write's own sign")
    move_src = inspect.getsource(QuickEstimationService._apply_camera_arm_move)
    ok("seat_sign * float(delta)" in move_src and "_camera_arm_seat_axis(stage)" in move_src,
       "F2: and the move writes the seat with that sign")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0782 motor1-follows-the-beam validation PASSED")
        return 0
    print("0782 motor1-follows-the-beam validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
