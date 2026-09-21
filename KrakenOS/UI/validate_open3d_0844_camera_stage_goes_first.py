"""Display-free guard: a lens blocked by something the CAMERA STAGE carries is not a refusal --
the stage goes first, and the answer no longer depends on the path (bugs/0844).

The user: *"device size changed to 50x50x1, solver rejected. I think this is not correct,
contradict to actual production"*, and *"this sliding problem bound to minimum and maximum ...
the algorithm should be able to solve any values in between, thus eliminating false solve
refusal."*

Measured on the real om05a_folded (bugs/diag_0844_path_independence.py): after a 21 mm solve,
asking for the 52.5 mm field the file LOADS at was refused -- the lens needed +116.389 mm toward
the Filter with 74.47 mm of room, judged BEFORE the same solve moved the Filter's stage
+60.339 mm out of the way. Stage first: room 134.81 mm, the lens moves, and the result is the
fresh-load solve's to 0.01 mm.

This guard is a geometric MINIATURE of that bench. Nothing about the lens's room is scripted:
it is ``rows[rear].thickness - OVERHANG``, so it changes because the REAL stage motor
(``_apply_camera_arm_move``, bound here with the real stage reader, seat-axis measurement and
vendor lock) really moved the Filter. The REAL booking runs it, unwrapped and wrapped.

  Z  CONTROL -- with the rescue neutered the real booking refuses, as the user saw
  A  the fix -- the real booking succeeds; order of calls, final rows, honest message
  P  PATH INDEPENDENCE -- a zig-zag of fields lands each time where a direct solve lands
  R  a lens that does not fit the FINAL state still refuses: byte-identical, first numbers back
  T  a stage that cannot travel far enough: nothing attempted, the reason names the travel
  M  a lens that moved by another primitive is put back; the first refusal stands untouched
  V  the vendor-hardware lock gates the rescue exactly as it gates the normal image path
  F  a booking fake with no stage falls through instead of raising
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np

F_MM = 85.13
SENSOR_MM = 23.04
OVERHANG_MM = 5.212          # barrel past the rear datum + clearance: gap 79.681 vs room 74.469
M_AFTER_21 = SENSOR_MM / 21.0
FRONT, REAR, FILTER, PAIR, SEAT, PAD = 2, 6, 7, 8, 9, 10
A5_MM, C1_MM, SEAT_X_MM = 50.2344, 79.6812, -196.9827   # om05a after the 21 mm solve


def _expected(field_mm, overhang=OVERHANG_MM) -> dict:
    """What the PHYSICS says, derived here and not read back from the code under test:
    thin-lens conjugates s_o = f(1 + 1/m), s_i = f(1 + m), so going m1 -> m2 the lens moves
    d = f(1/m2 - 1/m1) and the sensor's stage d + f(m2 - m1)."""
    m1, m2 = M_AFTER_21, SENSOR_MM / float(field_mm)
    lens = F_MM * (1.0 / m2 - 1.0 / m1)
    stage = lens + F_MM * (m2 - m1)
    return {
        "lens": lens, "stage": stage,
        "room_before": C1_MM - overhang, "room_after": C1_MM + stage - overhang,
        "a5": A5_MM + lens, "c1": C1_MM - lens + stage, "seat": SEAT_X_MM - stage,
    }


def _near(calls, want) -> bool:
    return len(calls) == len(want) and all(
        abs(a - b) < 1.0e-3 for got, exp in zip(calls, want) for a, b in zip(got, exp)
    )


def _bench(*, overhang=OVERHANG_MM, lens_mode="thickness_pair", stage_row=PAD):
    from KrakenOS.UI.services import quick_estimation as qe_mod
    from KrakenOS.UI.surface_table_model import SurfaceRow

    Q = qe_mod.QuickEstimationService

    def _row(name, thickness, desp_x=0.0):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_x, row.axis_move = float(desp_x), 0.0
        return row

    s_o, s_i = F_MM * (1.0 + 1.0 / M_AFTER_21), F_MM * (1.0 + M_AFTER_21)
    a5, c1, carry_pair = A5_MM, C1_MM, 90.0

    class _Editor:
        def __init__(self):
            self.rows = [
                _row("Object", s_o - a5),
                _row("RA mirror 1", a5),
                _row("Front Optical Vertex Datum", 1.823),
                _row("Blackbox Group 1", 18.302),
                _row("Aperture Stop", 18.302),
                _row("Blackbox Group 2", 1.093),
                _row("Rear Optical Vertex Datum", c1),
                _row("Filter 48-926", 1.0),
                _row("to camera", carry_pair),
                _row("RA mirror 2", 0.0, desp_x=SEAT_X_MM),
                _row("camera standoff", s_i - c1 - 1.0 - carry_pair),
                _row("Image / Sensor", 0.0),
            ]
            self.camera_focus_stage = {
                "enabled": True, "row": stage_row, "min_mm": 0.0, "max_mm": 400.0,
                "arm_row": SEAT, "arm_carry_row": REAR,
                "arm_min_mm": -290.737, "arm_max_mm": -88.667,
            }
            self.lens_calls, self.debug = [], []

        # -- first order: station sums, exactly the frame the real conjugate books in ---------
        def _folded_conjugate_gaps_for_magnification(self, m):
            m = abs(float(m))
            so_now = sum(float(self.rows[i].thickness) for i in (0, 1))
            si_now = sum(float(self.rows[i].thickness) for i in range(REAR, PAD + 1))
            want_o, want_i = F_MM * (1.0 + 1.0 / m), F_MM * (1.0 + m)
            return {
                "object_gap_row": 1, "image_gap_row": PAD,
                "object_delta": want_o - so_now, "image_delta": want_i - si_now,
                "object_distance": want_o, "image_distance": want_i, "magnitude": m,
            }

        # -- the lens mover: the bugs/0719 thickness pair behind a GEOMETRIC room gate --------
        def translate_lens_block_along_leg(self, signed_delta, *, force=False):
            d = float(signed_delta)
            self._lens_move_refusal, self._lens_move_room_mm = "", None
            self._lens_move_refusal_info = None
            gap_row, body = (REAR, "Filter 48-926") if d > 0.0 else (FRONT - 1, "RA mirror 1")
            room = float(self.rows[gap_row].thickness) - float(overhang)
            self.lens_calls.append((round(d, 4), round(room, 4)))
            if abs(d) > room + 1.0e-9:
                self._lens_move_room_mm = room
                self._lens_move_refusal = (
                    f"that field needs the lens {d:+.4g} mm along its leg, but only {room:.4g} mm "
                    f"of physical room is left before its body reaches {body}"
                )
                return None
            self.rows[FRONT - 1].thickness = float(self.rows[FRONT - 1].thickness) + d
            self.rows[REAR].thickness = float(self.rows[REAR].thickness) - d
            return {"mode": lens_mode, "signed_mm": d, "distance": abs(d), "room_mm": room}

        # -- world: the lens leg runs along -x from RA mirror 1; the seat is ABSOLUTE ---------
        def _surface_reference_world_point(self, index):
            index = int(index)
            if index == SEAT:
                return np.array([float(self.rows[SEAT].desp_x), 0.0, 0.0])
            arc = sum(float(self.rows[i].thickness) for i in range(1, index))
            return np.array([-arc, 0.0, 0.0])

        def _imaging_lens_block_indices(self):
            return FRONT, REAR

        def _step_path_for_label(self, label):
            return "camera.step" if label == "camera" else None

        def shift_image_distance_frozen_aware(self, _delta):
            return False   # not a frozen fold: the stage books the image side (om05a)

        def _folded_image_conjugate_split(self):
            return None

        def _invalidate_preview_scene_trace(self):
            pass

        def append_debug(self, *args, **_kwargs):
            self.debug.append(" ".join(str(a) for a in args))

    class _QE:
        _apply_conjugate_pair = Q._apply_conjugate_pair
        _camera_focus_stage = Q._camera_focus_stage
        _motor_rail_from_lens_block = Q._motor_rail_from_lens_block
        _apply_camera_arm_move = Q._apply_camera_arm_move
        _camera_arm_seat_axis = Q._camera_arm_seat_axis
        _image_write_locked_by_vendor_hardware = Q._image_write_locked_by_vendor_hardware
        _ARM_MOVE_TOL_MM = Q._ARM_MOVE_TOL_MM

        def __init__(self, editor):
            self.editor = editor

        def _sensor_world_point(self):
            # the sensor rides the stage: along the beam it sits at the image-side station sum
            rows = self.editor.rows
            return np.array([-sum(float(rows[i].thickness) for i in range(1, PAD + 1)), 0.0, 0.0])

        def _gap_row_for_delta(self, _rows, index):
            return index

        def _folded_image_leg_write_row(self, _index):
            return PAD

        def _in_focus_fields_at_current_track(self):
            return []

        def _finish_solve_on_traced_focus(self):
            return ""

    editor = _Editor()
    return editor, _QE(editor), qe_mod


def _state(editor) -> dict:
    out = {i: float(editor.rows[i].thickness) for i in (1, REAR, PAIR, PAD)}
    out["seat"] = float(editor.rows[SEAT].desp_x)
    return out


def _fingerprint(editor) -> tuple:
    fields = ("thickness", "desp_x", "desp_y", "desp_z")
    return tuple(tuple(repr(getattr(r, f, None)) for f in fields) for r in editor.rows)


def _solve(service, field_mm, *, unwrapped=False):
    booking = type(service)._apply_conjugate_pair
    if unwrapped:
        booking = booking.__wrapped__
    return booking(service, float(field_mm) / 2.0, SENSOR_MM / 2.0)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        if cond:
            notes.append("= " + text)
        else:
            state["ok"] = False
            notes.append("FAIL " + text)

    # ---- Z: CONTROL -- the old order, reproduced through the real booking ----------------------
    editor, service, qe_mod = _bench()
    start = _fingerprint(editor)
    real_rescue = qe_mod._lens_move_with_camera_stage_first
    qe_mod._lens_move_with_camera_stage_first = lambda *_a, **_k: (None, {})
    try:
        verdict = _solve(service, 52.5)
    finally:
        qe_mod._lens_move_with_camera_stage_first = real_rescue
    want = _expected(52.5)
    ok(verdict[0] is False and _near(editor.lens_calls, [(want["lens"], want["room_before"])])
       and abs(want["lens"] - 116.389) < 1e-3 and abs(want["room_before"] - 74.469) < 1e-3
       and _fingerprint(editor) == start,
       f"Z: CONTROL -- lens first, the 52.5 mm field is REFUSED on the intermediate state "
       f"(needs +116.389, room 74.469: the numbers on the user's banner) -- {editor.lens_calls}")

    # ---- A: the fix, through the real booking, with and without the booking-wide net ----------
    for tag in ("unwrapped", "wrapped"):
        editor, service, qe_mod = _bench()
        verdict = _solve(service, 52.5, unwrapped=(tag == "unwrapped"))
        now = _state(editor)
        ok(verdict[0] is True and want["room_after"] > want["lens"] > want["room_before"]
           and _near(editor.lens_calls, [(want["lens"], want["room_before"]),
                                         (want["lens"], want["room_after"])]),
           f"A1[{tag}]: refused lens-first, then the REAL stage motor moved the Filter and the "
           f"same lens move had room -- {editor.lens_calls}")
        ok(abs(now[1] - want["a5"]) < 1e-6 and abs(now[REAR] - want["c1"]) < 1e-6
           and abs(now["seat"] - want["seat"]) < 1e-6
           # ... and the miniature is the real bench: the REAL fresh-load 52.5 solve measured
           # 166.6231 / 23.6414 / -257.3315 (bugs/diag_0844_path_independence.py)
           and abs(now[1] - 166.6231) < 1e-3 and abs(now[REAR] - 23.6414) < 1e-3
           and abs(now["seat"] - (-257.3315)) < 1e-3,
           f"A2[{tag}]: lens gap {now[1]:.4f}, lens->Filter {now[REAR]:.4f}, seat "
           f"{now['seat']:.4f} -- what the physics says, and what the REAL scene's fresh-load "
           f"solve measured (166.6231 / 23.6414 / -257.3315)")
        left = editor._folded_conjugate_gaps_for_magnification(SENSOR_MM / 52.5)
        ok(abs(left["object_delta"]) < 1e-9 and abs(left["image_delta"]) < 1e-9,
           f"A3[{tag}]: the conjugate re-measured afterwards leaves nothing to book "
           f"({left['object_delta']:+.2e}, {left['image_delta']:+.2e}) -- the stage-first amount "
           f"was the ORDER of the solve's own two moves, not a second answer")
        text = str(verdict[1])
        ok(f"sensor moved {want['stage']:+.4g} mm" in text and "sensor moved +0 mm" not in text
           and "camera stage moved first" in text,
           f"A4[{tag}]: the message quotes what the sensor TRAVELLED ({want['stage']:+.4g} mm), "
           f"not the ~0 left after re-measuring, and says the stage went first")
        ok(abs(float(editor.__dict__.get("_fov_solve_lens_move_mm", 0.0)) - want["lens"]) < 1e-6
           and not editor.__dict__.get("_fov_solve_refusal_info"),
           f"A5[{tag}]: the lens move is recorded ({editor.__dict__.get('_fov_solve_lens_move_mm')}) "
           f"and no refusal is stashed")

    # ---- P: path independence -- the user's min/max insight ------------------------------------
    path = (52.5, 21.0, 60.0, 12.0, 45.0, 30.0, 52.5)
    editor, service, _ = _bench()
    worst, refused = 0.0, []
    for field in path:
        if not _solve(service, field)[0]:
            refused.append(field)
            continue
        direct_editor, direct_service, _ = _bench()
        _solve(direct_service, field)
        here, there = _state(editor), _state(direct_editor)
        worst = max(worst, max(abs(here[k] - there[k]) for k in here))
    rescued = sum("FIRST, then the lens" in line for line in editor.debug)
    ok(not refused and worst < 1e-6 and rescued >= 1,
       f"P1: a zig-zag {path} lands every field where a DIRECT solve of it lands (worst row "
       f"difference {worst:.2e} mm, refused: {refused}; {rescued} step(s) needed the stage to go "
       f"first) -- inside the travel, the answer does not depend on the path")
    # ... and the zig-zag is a real test: the SAME path with the rescue neutered gets refused.
    editor, service, qe_mod = _bench()
    qe_mod._lens_move_with_camera_stage_first = lambda *_a, **_k: (None, {})
    try:
        old_refused = [field for field in path if not _solve(service, field)[0]]
    finally:
        qe_mod._lens_move_with_camera_stage_first = real_rescue
    ok(len(old_refused) >= 1,
       f"P2: CONTROL -- lens-first only, the same zig-zag REFUSES {old_refused}: fields this "
       f"machine solves from a fresh load")

    # ---- R: the FINAL state does not fit -> refuse, byte-identical, first numbers back ----------
    for tag in ("unwrapped", "wrapped"):
        editor, service, _ = _bench(overhang=30.0)   # a fat barrel
        start = _fingerprint(editor)
        verdict = _solve(service, 52.5, unwrapped=(tag == "unwrapped"))
        info = editor.__dict__.get("_fov_solve_refusal_info") or {}
        fat = _expected(52.5, overhang=30.0)
        ok(verdict[0] is False and fat["room_after"] < fat["lens"]
           and _near(editor.lens_calls, [(fat["lens"], fat["room_before"]),
                                         (fat["lens"], fat["room_after"])])
           and _fingerprint(editor) == start,
           f"R1[{tag}]: the stage really moved and the lens STILL did not fit the final state "
           f"{editor.lens_calls} -- refused, and the scene is byte-identical")
        ok(info.get("stage_first_put_back") is True
           and abs(float(info.get("stage_first_tried_mm") or 0.0) - fat["stage"]) < 1e-6
           and abs(float(info.get("leg_room_mm") or 0.0) - fat["room_before"]) < 1e-6,
           f"R2[{tag}]: the stash carries VALUES -- tried {info.get('stage_first_tried_mm')}, put "
           f"back {info.get('stage_first_put_back')}, room {info.get('leg_room_mm')} (the scene "
           f"on screen, not the 110 mm of the put-back one)")
        text = str(verdict[1])
        ok(text.index("49.68") < text.index("Moving the camera stage") < text.index("110")
           and "put back -- nothing was moved" in text,
           f"R3[{tag}]: the reason leads with the first refusal, then says what was tried and "
           f"that it was put back")

    # ---- T: the stage cannot travel that far ----------------------------------------------------
    editor, service, _ = _bench()
    start = _fingerprint(editor)
    verdict = _solve(service, 70.0)
    info = editor.__dict__.get("_fov_solve_refusal_info") or {}
    ok(verdict[0] is False and len(editor.lens_calls) == 1 and _fingerprint(editor) == start
       and info.get("stage_first_outside_travel") is True
       and "outside its -290.7 to -88.67 mm travel" in str(verdict[1]),
       f"T: a 70 mm field needs the stage past its travel -- nothing is attempted "
       f"({len(editor.lens_calls)} lens call), and the reason NAMES the limit of the machine")

    # ---- M: moved, but not by the primitive this order is measured on ---------------------------
    editor, service, _ = _bench(lens_mode="slide")
    start = _fingerprint(editor)
    verdict = _solve(service, 52.5, unwrapped=True)
    ok(verdict[0] is False and len(editor.lens_calls) == 2 and _fingerprint(editor) == start
       and "Moving the camera stage" not in str(verdict[1]) and "74.47" in str(verdict[1]),
       "M: a lens that moved as a desp-leg 'slide' is put back with the stage, and the first "
       "refusal stands UNTOUCHED -- 'still refused' would be untrue")

    # ---- V: the vendor lock gates the rescue as it gates the normal image path ------------------
    editor, service, _ = _bench(stage_row=PAIR)   # stage declared on a row the image is not written on
    start = _fingerprint(editor)
    verdict = _solve(service, 52.5)
    ok(verdict[0] is False and len(editor.lens_calls) == 1 and _fingerprint(editor) == start,
       "V: with the image write locked by vendor hardware the stage is NOT moved first -- one "
       "lens call, scene untouched")

    # ---- F: a partial fake must fall through, not raise -----------------------------------------
    editor, _service, qe_mod = _bench()
    bare = SimpleNamespace(editor=editor)
    folded = editor._folded_conjugate_gaps_for_magnification(SENSOR_MM / 52.5)
    ok(qe_mod._lens_move_with_camera_stage_first(bare, folded, editor.rows, PAD) == (None, {})
       and not editor.lens_calls,
       "F: a booking fake with no stage methods falls through -- (None, {}), nothing called")

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
