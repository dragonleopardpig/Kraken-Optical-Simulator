"""Guard for bugs/0761 -- the filter travels with the group, and "already delivered" means the
image LANDS.

Flag 20260909_122103_567: "changed to 30x30 device size, the Edmund Filter misplaced. The image
plane is in front of the sensor." Two separate defects, both in the bugs/0759 two-motor work.

(a) MOTOR 1 left the filter behind. Measured on the flagged solve:

        Front/Rear Optical Vertex (lens)   [-80.842, 0, 0]     Motor 2
        RA mirror 2 + SENSOR               [-55.698, 0, 0]     Motor 1
        Filter 48-926                      [  0.000, 0, 0]     STAYED

    The user named the group precisely -- "lens + Filter + 40mm RA mirror + Camera" -- and the
    arm move wrote only the mirror seat and the sensor standoff. The filter rides the CHAIN, so
    it followed Motor 2 instead and ended 55.7 mm from the mirror it travels with.

    It must move as a PAIR, like the lens (bugs/0719): the gap before the filter takes +delta and
    the filter->mirror gap takes -delta. Writing only the first shifts the whole chain -- measured,
    the mirror picked up a 55.7 mm z component and the sensor went 259 mm out of place.

(b) The bugs/0727 idempotence test compared MAGNIFICATION only, so a scene at the right |m| with
    the image 6.276 mm off the sensor was declared finished: "the lens did not move -- the field
    was already delivered". Delivered now also requires the image to land.

Fixing (a) moved the whole range's residual by an order of magnitude (device 20: -0.3414 ->
+0.0035 mm), which retires the "first order vs trace at high magnification" explanation recorded
in bugs/0759 -- that residual was this bug.

Checks (display-free, pure):
  A  the arm move writes the carry PAIR, both gaps, opposite signs;
  B  it degrades safely when no carry is declared, and never writes one gap alone;
  C  idempotence refuses when the image does not land, and still short-circuits when it does;
  D  the focus tolerance is inside one pixel of depth of focus.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0761_filter_travels_and_focus_gates_idempotence
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


class _Row:
    def __init__(self, name, thickness=0.0, desp_x=0.0):
        self.name = name
        self.thickness = float(thickness)
        self.desp_x = float(desp_x)


def _rows():
    r = [_Row(f"r{i}") for i in range(13)]
    r.append(_Row("Rear Optical Vertex Datum", 17.51))    # 13 -- carry
    r.append(_Row("Filter 48-926", 1.0))                  # 14
    r.append(_Row("to camera", 31.11))                    # 15 -- carry pair
    r.append(_Row("RA mirror 2 (40 mm)", 36.31, 272.68))  # 16 -- seat
    r += [_Row(f"s{i}") for i in range(7)]                # 17..23
    r.append(_Row("sensor standoff", 9.67))               # 24 -- pad
    return r


def _svc(stage, rows):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService
    return QuickEstimationService(SimpleNamespace(editor=SimpleNamespace(
        camera_focus_stage=stage, rows=rows)))


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    SEAT, PAD, CARRY, PAIR = 16, 24, 13, 15
    base = {"enabled": True, "row": PAD, "min_mm": -80.0, "max_mm": 40.0,
            "arm_row": SEAT, "arm_min_mm": 100.0, "arm_max_mm": 400.0}

    # ---- A: the carry PAIR --------------------------------------------------------------------
    rows = _rows()
    svc = _svc({**base, "arm_carry_row": CARRY}, rows)
    before = (rows[CARRY].thickness, rows[PAIR].thickness, rows[SEAT].desp_x, rows[PAD].thickness)
    ok(svc._apply_camera_arm_move(-55.698) is True, "A1: the arm move applies")
    d_carry = rows[CARRY].thickness - before[0]
    d_pair = rows[PAIR].thickness - before[1]
    d_seat = rows[SEAT].desp_x - before[2]
    d_pad = rows[PAD].thickness - before[3]
    ok(abs(d_seat - (-55.698)) < 1e-9 and abs(d_pad - (-55.698)) < 1e-9,
       f"A2: the seat and the standoff still take the delta ({d_seat:+.3f} / {d_pad:+.3f})")
    ok(abs(d_carry - (-55.698)) < 1e-9,
       f"A3: the gap BEFORE the filter takes the same delta ({d_carry:+.3f}) -- the filter travels")
    ok(abs(d_pair - (+55.698)) < 1e-9,
       f"A4: and the filter->mirror gap takes the OPPOSITE delta ({d_pair:+.3f}), so the mirror's "
       f"station does not move -- writing only the first shifted the chain 259 mm")
    ok(abs((d_carry + d_pair)) < 1e-9,
       "A5: the pair sums to zero, which is what keeps everything downstream in place")

    # ---- B: safe without a carry ----------------------------------------------------------------
    rows = _rows()
    svc = _svc(base, rows)
    b0 = (rows[CARRY].thickness, rows[PAIR].thickness)
    ok(svc._apply_camera_arm_move(-10.0) is True, "B1: an arm with no carry still moves")
    ok((rows[CARRY].thickness, rows[PAIR].thickness) == b0,
       "B2: and touches neither carry gap -- a scene that declares none is unchanged")
    src = inspect.getsource(QuickEstimationService._apply_camera_arm_move)
    ok("rows[b_i].thickness = float(rows[b_i].thickness) - float(delta)" in src
       and "rows[a_i].thickness = float(rows[a_i].thickness) + float(delta)" in src,
       "B3: both halves of the pair are written in the production path")

    # ---- C: idempotence needs the image to land ---------------------------------------------------
    class Ed:
        def __init__(self, residual):
            self._res = residual
            self.rows = []
            self.camera_focus_stage = None

        def _current_finite_paraxial_magnification(self):
            return 0.7314

        def _folded_conjugate_gaps_for_magnification(self, m):
            return {"image_delta": self._res}

        def _current_camera_sensor_active_mm(self):
            return (23.04, 23.04)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService as Q
    landed = Q(SimpleNamespace(editor=Ed(0.02)))._fov_already_delivered(11.52, 15.75)
    missed = Q(SimpleNamespace(editor=Ed(6.276)))._fov_already_delivered(11.52, 15.75)
    ok(landed is not None,
       "C1: the SAME |m| with the image on the sensor is still 'already delivered'")
    ok(missed is None,
       "C2: the same |m| with the image 6.276 mm out is NOT delivered -- the flagged case, where "
       "the solve said 'the lens did not move' and left it there")
    idem = inspect.getsource(Q._fov_already_delivered)
    ok('_folded_conjugate_gaps_for_magnification' in idem and "image_delta" in idem,
       "C3: it asks the same first order the solve uses, so the two cannot disagree")

    # ---- D: the tolerance is optically meaningful ---------------------------------------------------
    ok(float(Q._DELIVERED_FOCUS_TOL_MM) <= 0.153,
       f"D1: the focus tolerance ({Q._DELIVERED_FOCUS_TOL_MM} mm) is inside one pixel of depth of "
       f"focus (0.153 mm)")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0761 filter-travels + focus-gated-idempotence validation PASSED")
        return 0
    print("0761 validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
