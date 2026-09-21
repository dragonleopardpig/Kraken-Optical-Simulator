"""Display-free guard: after a solve the banner says where the focus landed and what the camera
stage did (bugs/0846).

The user, on flag_20260921_162154 -- the 50x50 solve bugs/0844 made possible: *"50x50x1mm works.
I notice the banner is less verbose."* It carried one line:

    SOLVE  delivering 52.5 x 52.5 mm (|m| 0.4389); the lens moved +131.4 mm along its leg

Two things were missing, and both went missing because the outcome was GOOD:

* the whole FOCUS block sat behind ``abs(offset) >= 0.05`` mm. The 52.5 mm solve landed
  0.023 mm off, so the best result said nothing -- indistinguishable from "not measured";
* the camera stage carried the Filter, RA mirror 2 and the camera +75.35 mm -- the largest
  visible move in the scene, and first, to clear the lens's way -- under a SOLVE line that named
  only the lens.

  F  the formatter: in-focus after a solve reports the landing with the SAME pixel verdict;
     with no solve an in-focus scene still says nothing (bugs/0728 D3); above the gate the text
     is byte-identical to before
  S  the stage line: signed, first-order note, the 0783 group move, unsigned when the seat's
     axis is unmeasured, nothing when there is no stage or no move
  B  the stage travel is MEASURED by the real stage motor on the bugs/0844 bench, and the
     stage-first claim is recorded only when the stage really went first
  W  fov_solve starts the measurement and writes it into the summary (executable lines)
"""
from __future__ import annotations

import inspect

PIXEL = (4.5, 4.5)
SOLVE_52 = {"delivered_fov_wh": (52.5, 52.5), "delivered_m": 0.4389, "lens_move_mm": 131.4}
SOLVE_21 = {"delivered_fov_wh": (21.0, 21.0), "delivered_m": 1.097, "lens_move_mm": -131.4}
IN_FOCUS = {"offset_mm": 0.02263, "side": "in front of", "rms_waist_mm": 0.0005, "rms_plane_mm": 0.0012}
OFF_FOCUS = {
    "offset_mm": -0.1155, "side": "in front of", "rms_waist_mm": 0.000489, "rms_plane_mm": 0.00306,
    "images": [
        {"name": "Face A field", "offset_mm": -0.1155, "side": "in front of"},
        {"name": "Face B field", "offset_mm": -0.1155, "side": "in front of"},
    ],
}
# What the banner printed for OFF_FOCUS + SOLVE_21 before bugs/0846 (captured from the parent
# commit's formatter): above the gate nothing may change.
OFF_FOCUS_TEXT_BEFORE = [
    "SOLVE: delivering 21 x 21 mm (|m| 1.097); the lens moved -131.4 mm along its leg",
    "FOCUS: the image forms 0.1155 mm in front of the sensor -- spot 0.489 um there vs 3.06 um on the sensor",
    "  Face A field: 0.1155 mm in front of the sensor",
    "  Face B field: 0.1155 mm in front of the sensor",
    "Landed: the blur on the sensor (3.06 um) is inside one pixel (4.5 um) -- nothing to move",
]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines as fmt

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- F: the formatter ----------------------------------------------------------------------
    landed = fmt(IN_FOCUS, SOLVE_52, pixel_size_um=PIXEL)
    ok(len(landed) == 3 and landed[0].startswith("SOLVE: delivering 52.5")
       and landed[1] == "FOCUS: the image forms on the sensor (0.023 mm in front of it) -- spot 1.2 um on the sensor"
       and landed[2].startswith("Landed: the blur on the sensor (1.2 um) is inside one pixel (4.5 um)"),
       f"F1: the solve that landed 0.023 mm off now SAYS so, with the pixel verdict -- {landed[1:]}")
    ok(fmt(IN_FOCUS, None, pixel_size_um=PIXEL) == [] and fmt(None, SOLVE_52, pixel_size_um=PIXEL) == landed[:1],
       "F2: with NO solve an in-focus scene says nothing (bugs/0728 D3); with no measurement "
       "nothing about focus is invented")
    blurry = dict(IN_FOCUS, rms_waist_mm=0.0199, rms_plane_mm=0.020)
    defocus = dict(IN_FOCUS, rms_waist_mm=0.001, rms_plane_mm=0.020)
    ok(any(line.startswith("THE BLUR IS NOT DEFOCUS") for line in fmt(blurry, SOLVE_52, pixel_size_um=PIXEL))
       and any(line.startswith("Move the device stage") for line in fmt(defocus, SOLVE_52, pixel_size_um=PIXEL)),
       "F3: in focus by distance but blurred beyond a pixel gets the SAME bugs/0767/0777 verdicts "
       "as an off-focus image -- aberration vs defocus -- never a blanket 'landed'")
    ok(fmt(OFF_FOCUS, SOLVE_21, pixel_size_um=PIXEL) == OFF_FOCUS_TEXT_BEFORE,
       "F4: above the 0.05 mm gate the banner is byte-identical to before (the user's 20x20 flag text)")

    # ---- S: the stage line ---------------------------------------------------------------------
    def stage_lines(info):
        return [line for line in fmt(None, info, pixel_size_um=PIXEL) if line.startswith("Camera stage:")]

    first = stage_lines(dict(SOLVE_52, stage_move_mm=75.3488, stage_first=True))
    ok(first == ["Camera stage: moved +75.35 mm along the beam, carrying everything on it -- first, "
                 "to clear the lens's way"],
       f"S1: the stage move is named, signed like the lens move, with the order it happened in -- {first}")
    ok(stage_lines(dict(SOLVE_21, stage_move_mm=-75.3502))
       == ["Camera stage: moved -75.35 mm along the beam, carrying everything on it"],
       "S2: a stage that did NOT have to go first says only how far it moved")
    ok(stage_lines({"delivered_m": 0.43, "lens_move_mm": 3.2, "group_move_mm": 3.2, "wd_restored": True})
       == ["Camera stage: moved +3.2 mm along the beam, carrying everything on it"],
       "S3: the bugs/0783 working-distance restore's rigid group move is reported too")
    unsigned = stage_lines(dict(SOLVE_52, stage_move_abs_mm=75.35))
    ok(unsigned == ["Camera stage: moved 75.35 mm, carrying everything on it"],
       f"S4: when the seat's axis could not be measured the distance is given and NO direction "
       f"is claimed -- {unsigned}")
    ok(stage_lines(SOLVE_52) == [] and stage_lines(dict(SOLVE_52, stage_move_mm=0.001)) == [],
       "S5: no stage, or a stage that did not move, adds no line -- a lens-only scene reads as before")

    # ---- B: measured by the real stage motor on the bugs/0844 bench -----------------------------
    from KrakenOS.UI import validate_open3d_0844_camera_stage_goes_first as bench_mod

    def _bench(**kwargs):
        editor, service, qe_mod = bench_mod._bench(**kwargs)
        Q = qe_mod.QuickEstimationService
        type(service)._camera_stage_seat = Q._camera_stage_seat        # the REAL readers
        type(service)._camera_stage_travel = Q._camera_stage_travel
        return editor, service, qe_mod

    editor, service, _ = _bench()
    start = service._camera_stage_seat()
    sensor_before = service._sensor_world_point()
    moved = service._apply_camera_arm_move(60.339)
    travel = service._camera_stage_travel(start)
    along = float(sensor_before[0] - service._sensor_world_point()[0])   # the leg runs along -x
    ok(start == (bench_mod.SEAT, bench_mod.SEAT_X_MM) and moved
       and abs(travel.get("stage_move_mm", 0.0) - 60.339) < 1e-9 and abs(along - 60.339) < 1e-9,
       f"B1: the real stage motor moved the sensor {along:+.4f} mm along the beam and the reported "
       f"travel is {travel} -- same sign as the lens move (away from the object)")
    ok(service._camera_stage_travel(service._camera_stage_seat()) == {}
       and service._camera_stage_travel(None) == {},
       "B2: no travel since the start, or no start, reports nothing")

    for tag, overhang, want in (("stage went first", bench_mod.OVERHANG_MM, True),
                                ("refused, put back", 30.0, False)):
        editor, service, _ = _bench(overhang=overhang)
        verdict = bench_mod._solve(service, 52.5)
        claim = editor.__dict__.get("_fov_solve_stage_first_mm")
        expected = bench_mod._expected(52.5, overhang)["stage"]
        ok((claim is not None and abs(claim - expected) < 1e-6) if want else claim is None,
           f"B3[{tag}]: the stage-first claim is {claim!r} (booking ok={verdict[0]}) -- recorded "
           f"only when the stage really went first, never when the rescue was put back")

    # B4: the rescue COMMITTED, and the booking is refused LATER ("the object or image leg would
    # go negative"). The booking-wide net (bugs/0843) must take the claim back with the geometry.
    editor, service, qe_mod = _bench()

    @qe_mod._refused_booking_moves_nothing
    def _refused_after_the_stage_went_first(self):
        self.editor._fov_solve_stage_first_mm = 60.339
        return False, "FOV out of range on the folded arms (the object or image leg would go negative)"

    verdict = _refused_after_the_stage_went_first(service)
    ok(verdict[0] is False and "_fov_solve_stage_first_mm" not in editor.__dict__,
       "B4: a booking refused AFTER the stage went first leaves no stage-first claim behind -- "
       "the refusal banner cannot say the stage moved when the net put it back")
    # ... and B4 is not vacuous: strip the net's `also=` list and the claim survives the refusal.
    real_transaction = qe_mod.GeometryTransaction

    class _NoAlso(real_transaction):
        def __init__(self, editor_, label, *, also=()):
            super().__init__(editor_, label, also=())

    editor, service, qe_mod = _bench()
    qe_mod.GeometryTransaction = _NoAlso
    try:
        _refused_after_the_stage_went_first(service)
    finally:
        qe_mod.GeometryTransaction = real_transaction
    ok(editor.__dict__.get("_fov_solve_stage_first_mm") == 60.339,
       "B4-Z: CONTROL -- without the net's `also=` the stage-first claim outlives the refusal")

    # ---- W: fov_solve measures the stage over the WHOLE solve ------------------------------------
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    code = [ln.split("#", 1)[0] for ln in inspect.getsource(QuickEstimationService.fov_solve).splitlines()]
    starts = any("_fov_solve_stage_start = self._camera_stage_seat()" in ln for ln in code)
    writes = any("self._camera_stage_travel(" in ln for ln in code)
    ok(starts and writes,
       "W: fov_solve records the seat when it starts and writes the measured travel into the "
       "summary -- net over every booking and refinement pass, not the last booking's share")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
