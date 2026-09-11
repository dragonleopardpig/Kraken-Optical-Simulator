"""Guard for bugs/0783 -- a device-size change at a fixed FOV restores the working distance.

User: "I sometimes see Lens did not move kind of banner message while changing device size. How
can a lens don't move when the device size changed? the WD cannot be right without lens moving."
Then: "the production has only 3 FOVs, meaning only 3 WD + 3 image distance. So when the device
change size, one motor move to 'Restore' the WD" and "Everything is invariant for a fixed FOV, the
motor just restore the WD, everything else not changing".

Two defects said "the lens did not move":
  * the solve summary read ``lens_move_mm`` only from the vendor-lock residual, so every solve whose
    image side MOTOR 1 booked cleanly reported no lens move after moving the lens 86.9 mm;
  * bugs/0727's already-delivered gate compared |m| to 0.5 % and never the object side -- measured on
    om05a_folded_80mm at FOV 54, a 50 -> 49 mm device left the first order asking for a -0.883 mm
    lens move while the gate said "nothing to move".

And the size change itself ran the whole conjugate solve plus the traced finisher and snap (~150 s)
although a fixed FOV fixes both conjugates: the first order's WD and image distance are identical for
a 15 mm and a 50 mm device, only the lens position changes, by dL/2.

Checks (display-free; a stub bench whose first order is the thickness bookkeeping the real rows use):
  A  at an operating point, a device change is ONE rigid move -- lens pair and MOTOR 1 by the same
     object delta -- after which the conjugate asks for nothing more; no full solve, no trace;
  B  a FOV change (the image distance is not this FOV's) is not a restore;
  C  no MOTOR 1 stage, already at WD, or a traced focus that does not land: not a restore;
  D  a lens-pair refusal (rail / physical room) writes nothing; a MOTOR 1 refusal after the lens
     moved puts every row back bit-for-bit;
  E  the banner says what moved: the restore records the lens move, the full solve records it from
     whichever branch booked it, and the SOLVE line reads "the lens moved";
  F  wiring: the restore runs before the idempotence gate and never on a forced request.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0783_device_change_restores_wd
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import numpy as np

A5, FRONT, REAR, FILTER, PAIR, SEAT, PAD, IMAGE = 2, 3, 7, 8, 9, 10, 12, 13


class _Row:
    def __init__(self, name, thickness=0.0, desp_x=0.0):
        self.name = name
        self.thickness = float(thickness)
        self.desp_x = float(desp_x)
        self.desp_y = 0.0
        self.desp_z = 0.0


def _wd_target(m):
    return 200.0 + 20.0 / m


def _img_target(m):
    return 80.0 + 30.0 * m


class _Bench:
    """Stub editor. First order = the row bookkeeping: WD = A5 + 60 - face_offset, image distance
    = C1 + pair + pad + 20. The lens pair trades A5 against C1 (so the image distance drops by the
    move, the bugs/0575 coupling); MOTOR 1 moves the pad and the carry pair. World points follow the
    om05a 80 mm Jacobians (bugs/0782) so the MOTOR 1 sensor check really runs."""

    def __init__(self, m, *, refuse_lens=False, reversed_sensor=False):
        self.rows = [
            _Row("Object"), _Row("fold"), _Row("prism exit gap (air)", 0.0),
            _Row("Front Optical Vertex Datum"), _Row("g1", 9.7), _Row("stop", 9.7), _Row("g2", 11.9),
            _Row("Rear Optical Vertex Datum", 0.0), _Row("Filter", 1.0), _Row("to camera", 31.11),
            _Row("RA mirror 2", 36.31, 269.12), _Row("placed"), _Row("sensor standoff", 0.0),
            _Row("Image / Sensor"),
        ]
        self.face_offset = 0.0
        self.refuse_lens = refuse_lens
        self.reversed_sensor = reversed_sensor
        self._seat0 = self.rows[SEAT].desp_x
        # put the bench exactly at the operating point for m
        self.rows[A5].thickness = _wd_target(m) - 60.0
        self.rows[REAR].thickness = 40.0
        self.rows[PAD].thickness = _img_target(m) - 20.0 - 40.0 - 31.11
        self._pad0 = self.rows[PAD].thickness
        self.pair_calls = 0
        self.trace_deferred = False
        self.m = m

    # -- first order ------------------------------------------------------------------------
    def _folded_conjugate_gaps_for_magnification(self, m):
        wd = self.rows[A5].thickness + 60.0 - self.face_offset
        img = self.rows[REAR].thickness + self.rows[PAIR].thickness + self.rows[PAD].thickness + 20.0
        return {"object_delta": _wd_target(m) - wd, "image_delta": _img_target(m) - img,
                "object_gap_row": 0, "image_gap_row": PAD, "magnitude": m}

    def _current_finite_paraxial_magnification(self):
        return self.m

    def _current_camera_sensor_active_mm(self):
        return (23.04, 23.04)

    # -- motors ------------------------------------------------------------------------------
    def translate_lens_block_along_leg(self, d):
        if self.refuse_lens:
            self._lens_move_refusal = "that field needs the lens past the end of its travel"
            return None
        self.rows[A5].thickness += d
        self.rows[REAR].thickness -= d
        return {"mode": "thickness_pair", "signed_mm": float(d), "distance": abs(float(d))}

    def _imaging_lens_block_indices(self):
        return (FRONT, REAR)

    def _surface_reference_world_point(self, i):
        station = sum(r.thickness for r in self.rows[: int(i)])
        if int(i) == SEAT:
            return np.array([self.rows[SEAT].desp_x, 56.3, -25.0])
        if int(i) == IMAGE:
            x = self.rows[SEAT].desp_x
            if self.reversed_sensor:
                x = 2.0 * self._seat0 - x
            y = 1.0 + (self.rows[SEAT].desp_x - self._seat0) - (self.rows[PAD].thickness - self._pad0)
            return np.array([x, y, -25.0])
        return np.array([station, 56.4, -25.0])

    def _invalidate_preview_scene_trace(self):
        pass

    def append_debug(self, message):
        pass


def _service(bench, *, with_arm=True):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    class _QE(QuickEstimationService):
        full_solves = 0

        def _camera_focus_stage(self):
            stage = {"row": PAD, "min_mm": -1e9, "max_mm": 1e9}
            if with_arm:
                stage["arm"] = {"row": SEAT, "carry_row": REAR, "min_mm": -1e9, "max_mm": 1e9}
            return stage

        def _folded_m_correction(self):
            return 1.0

        def set_target_fov(self, semi):
            self.editor.target_semi = semi

        def _update_split_field_band_widths(self, width):
            self.editor.band_width = width

        def _apply_conjugate_pair(self, *args, **kwargs):
            type(self).full_solves += 1
            raise AssertionError("the restore must not run the full conjugate solve")

    return _QE(SimpleNamespace(editor=bench))


def _snap(rows):
    return [(r.thickness, r.desp_x, r.desp_y, r.desp_z) for r in rows]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    m = 0.4267
    semi, image_semi = 27.0, 27.0 * m

    # ---- A: a device change at an operating point is one rigid move ---------------------------------
    bench = _Bench(m)
    svc = _service(bench)
    fo = bench._folded_conjugate_gaps_for_magnification(m)
    ok(abs(fo["object_delta"]) < 1e-9 and abs(fo["image_delta"]) < 1e-9,
       "A0: the stub bench starts exactly at the FOV's operating point")
    bench.face_offset = -5.0                                  # the device shrank by 10 mm
    a5_0, c1_0, pad_0, seat_0 = (bench.rows[A5].thickness, bench.rows[REAR].thickness,
                                 bench.rows[PAD].thickness, bench.rows[SEAT].desp_x)
    result = svc._restore_working_distance(54.0, 54.0, semi, image_semi)
    ok(isinstance(result, tuple) and result[0] is True, f"A1: the size change is a restore ({result!r})")
    ok(abs((bench.rows[A5].thickness - a5_0) - (-5.0)) < 1e-9,
       f"A2: the lens moves the object delta, -5 mm (moved {bench.rows[A5].thickness - a5_0:+.4f})")
    ok(abs((bench.rows[PAD].thickness - pad_0) - (-5.0)) < 1e-9 and abs((bench.rows[SEAT].desp_x - seat_0) - (-5.0)) < 1e-9,
       "A3: and MOTOR 1 carries the group the same -5 mm (standoff and seat)")
    ok(abs(bench.rows[REAR].thickness - c1_0) < 1e-9,
       "A4: the lens-to-filter gap is unchanged -- lens and filter travel together")
    after = bench._folded_conjugate_gaps_for_magnification(m)
    ok(abs(after["object_delta"]) < 1e-9 and abs(after["image_delta"]) < 1e-9,
       f"A5: afterwards the conjugate asks for nothing: WD and image distance are this FOV's "
       f"({after['object_delta']:+.2e} / {after['image_delta']:+.2e})")
    ok(type(svc).full_solves == 0, "A6: the full conjugate solve never ran")
    ok(getattr(bench, "_preview_trace_deferred_until_requested", False) is True,
       "A7: nothing optical changed, so the scene is not re-traced (Trace Now draws the rays)")
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None,
       "A8: asking again restores nothing -- idempotent")

    # ---- B: a FOV change is not a restore ------------------------------------------------------------
    bench = _Bench(m)
    svc = _service(bench)
    before = _snap(bench.rows)
    m34 = 0.6776
    ok(svc._restore_working_distance(34.0, 34.0, 17.0, 17.0 * m34) is None and _snap(bench.rows) == before,
       "B1: a different FOV (its image distance is not this one's) is solved, not restored")

    # ---- C: the other ways out ---------------------------------------------------------------------------
    bench = _Bench(m)
    bench.face_offset = -5.0
    svc = _service(bench, with_arm=False)
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None,
       "C1: without a MOTOR 1 group stage there is no one-motor restore")
    bench = _Bench(m)
    svc = _service(bench)
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None,
       "C2: already at WD -> not a restore (the idempotence gate answers)")
    bench = _Bench(m)
    bench.face_offset = -5.0
    bench.__dict__["_focused_image_plane_info"] = {"images": [{"offset_mm": 0.02}, {"offset_mm": 3.0}]}
    svc = _service(bench)
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None,
       "C3: a traced image that does not land (worst arm 3 mm) is not an operating point to restore")

    # ---- D: refusals write nothing / put everything back ------------------------------------------------
    bench = _Bench(m, refuse_lens=True)
    bench.face_offset = -5.0
    svc = _service(bench)
    before = _snap(bench.rows)
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None and _snap(bench.rows) == before,
       "D1: a lens-pair refusal (rail end / physical room) writes nothing and hands over to the full "
       "solve, which reports it with its numbers")
    bench = _Bench(m, reversed_sensor=True)
    bench.face_offset = -5.0
    svc = _service(bench)
    before = _snap(bench.rows)
    ok(svc._restore_working_distance(54.0, 54.0, semi, image_semi) is None and _snap(bench.rows) == before,
       "D2: a MOTOR 1 refusal AFTER the lens moved puts every row back bit-for-bit")

    # ---- E: the banner says what moved ------------------------------------------------------------------
    bench = _Bench(m)
    bench.face_offset = -5.0
    svc = _service(bench)
    svc._restore_working_distance(54.0, 54.0, semi, image_semi)
    summary = getattr(bench, "_solve_summary_info", None) or {}
    ok(abs(float(summary.get("lens_move_mm", 0.0)) - (-5.0)) < 1e-9 and summary.get("wd_restored") is True,
       f"E1: the restore records the lens move for the banner ({summary})")
    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    lines = format_focus_summary_lines(None, solve_info=summary) if "solve_info" in inspect.signature(
        format_focus_summary_lines).parameters else []
    text = " ".join(lines)
    ok("the lens moved -5 mm" in text and "did not move" not in text,
       f"E2: the SOLVE line reads 'the lens moved' ({text!r})")
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    pair_src = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok("self.editor._fov_solve_lens_move_mm =" in pair_src,
       "E3: the full solve records the lens move from whichever branch booked it, not only the "
       "vendor-lock residual")
    solve_src = inspect.getsource(QuickEstimationService.fov_solve)
    ok('self.editor.__dict__.get("_fov_solve_lens_move_mm")' in solve_src
       and "self.editor._fov_solve_lens_move_mm = None" in solve_src,
       "E4: fov_solve clears it on entry and the success summary falls back to it")

    # ---- F: wiring -------------------------------------------------------------------------------------------
    restore_at = solve_src.find("self._restore_working_distance(")
    gate_at = solve_src.find("_fov_already_delivered(")
    ok(0 < restore_at < gate_at, "F1: the restore runs before the idempotence gate")
    ok("if not force:" in solve_src[max(0, restore_at - 400):restore_at],
       "F2: and never on a forced request -- force exists to show a collision")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0783 device-change-restores-wd validation PASSED")
        return 0
    print("0783 device-change-restores-wd validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
