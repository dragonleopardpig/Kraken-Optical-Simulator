"""bugs/0843 guard -- making room and using it are ONE transaction; "refused" means nothing moved.

Measured on the user's scene: the FOV solve's bugs/0573 rescue slid the fold arm 197.138 mm,
the lens move it made room FOR was refused anyway, and the solve reported the refusal with the
arm still slid -- row 12 at 276.819 mm where it had been 79.681, magnification None.

Display-free. The REAL ``slide_fold_arm_along_leg`` and the REAL offset setter (whose
``_clear_step_overlay_axis_anchor`` pops the camera anchor) are bound onto a probe, so what is
reverted here is what the production code actually writes -- not an imitation of it.

Sections:
  P  plain float arithmetic: an inverse slide is NOT bit-exact with this guard's own numbers,
     so an "undo by sliding back" cannot pass the byte-identity checks below.
  Z  CONTROL, no transaction: the real slide + a refused retry DOES strand the scene (gap row,
     camera offset, camera anchor). If this ever finds the scene intact the fixture no longer
     reproduces the bug and every other section proves nothing.
  T  the transaction: the slide demonstrably HAPPENED inside it (the vacuous-pass trap --
     "rows identical afterwards" is trivially true when the slide never fired) and the scene
     comes back byte-identical: same reprs, the SAME offset tuple object, the anchor restored.
  X  a body that RAISES after the slide: scene put back, exception still propagates.
  C  commit keeps the move -- the transaction is not just "always revert".
  R  awkward raw values (-0.0, an int thickness, a None desp, an attribute ABSENT at begin
     and created mid-way) come back as the same objects / absent again.
  S  a row list that changed identity: rollback writes NOTHING and says 'stuck'.
  N  a put-back that finds nothing to do writes nothing (no re-dirty, no flag).
  D  the booking-wide decorator: (False, why) and a raise put the scene back; (True, ...) keeps
     it; 'stuck' is appended to the message instead of claiming nothing moved.
  E  the explanation survives AND describes the restored scene: the first attempt's numbers
     are back in the channel, with structured facts for the refusal stash.
  W  the REAL booking, bound onto a fake (the validate_open3d_qe_object_locked precedent), with
     the real slide and a scripted refusing lens move. Driven UNWRAPPED as well, because the
     booking-wide net would otherwise mask a rescue that stopped using its own savepoint.
"""
from __future__ import annotations

import numpy as np

SLIDE_MM = 197.138
GAP_BEFORE = 79.681


def _fixture():
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin
    from KrakenOS.UI.surface_table_model import SurfaceRow

    def _row(name, *, thickness=0.0, desp_x=0.0, desp_z=0.0):
        row = SurfaceRow(name=name, thickness=float(thickness), diameter=25.0, glass="AIR")
        row.desp_x, row.desp_z, row.axis_move = float(desp_x), float(desp_z), 0.0
        return row

    class _Probe:
        slide_fold_arm_along_leg = ScenePlacementMixin.slide_fold_arm_along_leg
        _set_step_placement_offset_xyz = ScenePlacementMixin._set_step_placement_offset_xyz
        _step_placement_offset_xyz = ScenePlacementMixin._step_placement_offset_xyz
        _clear_step_overlay_axis_anchor = ScenePlacementMixin._clear_step_overlay_axis_anchor

        def __init__(self):
            self.rows = [
                _row("Object", thickness=118.970),
                _row("Front Optical Vertex Datum", thickness=1.823, desp_x=82.039, desp_z=-64.687),
                _row("Rear Optical Vertex Datum", thickness=GAP_BEFORE, desp_x=121.559,
                     desp_z=-104.207),
                _row("Filter", thickness=1.0, desp_x=150.0, desp_z=-150.0),
                _row("RA mirror 2", thickness=72.519, desp_x=179.788, desp_z=-198.034),
                _row("Image / Sensor", thickness=0.0, desp_x=179.788, desp_z=-328.223),
            ]
            self.camera_step_placement_offset_xyz = (-0.0597, 0.0581, -0.0006)
            self._step_overlay_axis_anchor_by_label = {
                "camera": {"face_id": "S1/F2", "source": "axis_snap"},
                "lens": {"face_id": "S9/F1", "source": "axis_snap"},
            }
            self.debug, self.invalidated, self.trace_invalidations = [], [], 0

        def _lens_leg_slide_plan(self):
            return ([1, 2], np.array([1.0, 0.0, 0.0]), True)

        def _promoted_mirror_fold_row_indices(self):
            return [4]

        def _step_path_for_label(self, label):
            return "camera.step" if label == "camera" else None

        def _step_overlay_mutation_signature(self, label):
            return None

        def _invalidate_step_overlay_after_mutation(self, label, before):
            self.invalidated.append(label)

        def _invalidate_preview_scene_trace(self):
            self.trace_invalidations += 1

        def append_debug(self, *args, **kwargs):
            self.debug.append(" ".join(str(a) for a in args))

    return _Probe()


def _fingerprint(probe) -> tuple:
    """repr, not ==: 79.68100000000001, -0.0 and int-vs-float must all count as different."""
    fields = ("thickness", "desp_x", "desp_y", "desp_z", "tilt_x", "tilt_y", "tilt_z", "axis_move")
    rows = tuple(tuple(repr(getattr(r, f, None)) for f in fields) for r in probe.rows)
    held = probe.__dict__
    return (
        rows,
        repr(held.get("camera_step_placement_offset_xyz", "<absent>")),
        repr(sorted((held.get("_step_overlay_axis_anchor_by_label") or {}).items())),
    )


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    state = {"ok": True}

    def ok(condition, text):
        notes.append(("= " if condition else "") + text)
        if not condition:
            state["ok"] = False

    from KrakenOS.UI.services.geometry_transaction import GeometryTransaction

    # ---- P ---------------------------------------------------------------------------------
    drifted = (GAP_BEFORE + SLIDE_MM) - SLIDE_MM
    ok(repr(drifted) != repr(GAP_BEFORE),
       f"P: an inverse slide is not bit-exact here ({GAP_BEFORE!r} -> {drifted!r}), so sliding "
       f"back cannot satisfy the byte-identity checks")

    # ---- Z: control, NO transaction ---------------------------------------------------------
    control = _fixture()
    before_z = _fingerprint(control)
    slid = control.slide_fold_arm_along_leg(SLIDE_MM)
    stranded = _fingerprint(control)
    gap_now = float(control.rows[2].thickness)
    anchor_gone = "camera" not in (control.__dict__.get("_step_overlay_axis_anchor_by_label") or {})
    ok(slid is not None and abs(gap_now - (GAP_BEFORE + SLIDE_MM)) < 1e-9 and stranded != before_z
       and anchor_gone,
       f"Z: CONTROL -- without a transaction the real slide strands the scene (gap row "
       f"{GAP_BEFORE} -> {gap_now:.3f}, camera anchor popped: {anchor_gone}); the fixture "
       f"reproduces the bug")

    # ---- T: the transaction ------------------------------------------------------------------
    probe = _fixture()
    before = _fingerprint(probe)
    offset_object = probe.camera_step_placement_offset_xyz
    seen = {}
    with GeometryTransaction(probe, "make room at the fold") as tx:
        result = probe.slide_fold_arm_along_leg(SLIDE_MM)
        seen["gap_mid"] = float(probe.rows[2].thickness)
        seen["mid"] = _fingerprint(probe)
        seen["anchor_mid"] = "camera" in probe._step_overlay_axis_anchor_by_label
        # The slide ITSELF sets the rebuild flag, so merely finding it set afterwards proves
        # nothing about rollback (the first draft of T6 did exactly that -- always true).
        # Model the production hazard instead: append_debug pumps idle tasks, a refresh runs
        # mid-slide and CONSUMES the flag. Rollback must set it again.
        seen["flag_was_set"] = bool(probe.__dict__.pop("_fold_carry_pending_rebuild", False))
        # the scripted REFUSED retry: no commit
    ok(result is not None and abs(seen["gap_mid"] - (GAP_BEFORE + SLIDE_MM)) < 1e-9
       and seen["mid"] != before,
       f"T1: the slide really HAPPENED inside the transaction (gap row read "
       f"{seen['gap_mid']:.3f} mid-way) -- not a vacuous pass")
    ok(_fingerprint(probe) == before,
       "T2: after the refused retry the scene is BYTE-IDENTICAL (every row field by repr, the "
       "camera offset, the anchor table)")
    ok(probe.camera_step_placement_offset_xyz is offset_object,
       "T3: the camera offset is the SAME tuple object again, not a re-packed equal")
    ok("camera" in probe._step_overlay_axis_anchor_by_label,
       "T4: the camera axis anchor the real setter popped is back")
    ok(tx.state == "rolled_back" and tx.restored > 0,
       f"T5: the transaction reports what it did (state {tx.state}, {tx.restored} restored)")
    ok(seen["flag_was_set"] and probe.__dict__.get("_fold_carry_pending_rebuild") is True
       and probe.trace_invalidations >= 1,
       "T6: with the rebuild flag CONSUMED mid-slide (a refresh ran), the put-back sets it "
       "again and re-dirties the trace, so a frame drawn mid-slide cannot linger")
    ok(probe.invalidated == ["camera", "camera"] and seen["anchor_mid"] is False,
       f"T7: the real setter ran to completion twice -- the forward carry and the put-back "
       f"({probe.invalidated}) -- so the overlay caches describing the slid pose are dropped, "
       f"and the anchor really was gone mid-way")

    # ---- X: the body raises ------------------------------------------------------------------
    probe_x = _fixture()
    before_x = _fingerprint(probe_x)
    raised = False
    try:
        with GeometryTransaction(probe_x, "make room at the fold"):
            probe_x.slide_fold_arm_along_leg(SLIDE_MM)
            raise RuntimeError("retry blew up")
    except RuntimeError:
        raised = True
    ok(raised and _fingerprint(probe_x) == before_x,
       "X: a body that raises after the slide still leaves the scene byte-identical, and the "
       "exception propagates")

    # ---- C: commit keeps the move --------------------------------------------------------------
    probe_c = _fixture()
    before_c = _fingerprint(probe_c)
    with GeometryTransaction(probe_c, "make room at the fold") as tx_c:
        probe_c.slide_fold_arm_along_leg(SLIDE_MM)
        tx_c.commit()
    ok(_fingerprint(probe_c) != before_c and tx_c.state == "committed"
       and abs(float(probe_c.rows[2].thickness) - (GAP_BEFORE + SLIDE_MM)) < 1e-9,
       "C: a committed transaction KEEPS the slide -- it is not 'always revert'")

    # ---- R: awkward raw values -------------------------------------------------------------------
    probe_r = _fixture()
    neg_zero, int_thickness = -0.0, 7
    probe_r.rows[3].desp_x = neg_zero
    probe_r.rows[3].thickness = int_thickness
    probe_r.rows[3].desp_y = None
    probe_r.__dict__.pop("lens_step_placement_offset_xyz", None)
    with GeometryTransaction(probe_r, "raw values"):
        # 0.0, not some other number: the ONLY thing that may make rollback write here is the
        # sign bit. A value-based compare (-0.0 == 0.0) would skip it and leave 0.0 behind.
        probe_r.rows[3].desp_x = 0.0
        probe_r.rows[3].thickness = 7.0
        probe_r.rows[3].desp_y = 1.25
        probe_r.lens_step_placement_offset_xyz = (1.0, 2.0, 3.0)
    ok(repr(probe_r.rows[3].desp_x) == "-0.0" and probe_r.rows[3].thickness is int_thickness
       and probe_r.rows[3].desp_y is None
       and "lens_step_placement_offset_xyz" not in probe_r.__dict__,
       "R: -0.0, an int thickness and a None desp come back as themselves, and an attribute "
       "ABSENT at begin is absent again")

    # ---- S: stuck -----------------------------------------------------------------------------------
    probe_s = _fixture()
    tx_s = GeometryTransaction(probe_s, "stuck case").begin()
    probe_s.slide_fold_arm_along_leg(SLIDE_MM)
    slid_print = _fingerprint(probe_s)
    import copy as _copy

    probe_s.rows[3] = _copy.copy(probe_s.rows[3])  # same values, DIFFERENT object
    put_back = tx_s.rollback()
    ok(put_back is False and tx_s.state == "stuck" and _fingerprint(probe_s) == slid_print,
       "S: when the row list changed identity NOTHING is written and the state is 'stuck' -- "
       "restoring onto rows that are not the captured ones would be a guess")

    # ---- N: a no-op put-back writes nothing ------------------------------------------------------
    probe_n = _fixture()
    with GeometryTransaction(probe_n, "no-op") as tx_n:
        pass
    ok(tx_n.state == "rolled_back" and tx_n.restored == 0
       and "_fold_carry_pending_rebuild" not in probe_n.__dict__
       and probe_n.trace_invalidations == 0 and not probe_n.debug
       and probe_n.invalidated == [],
       "N: a put-back that finds nothing to do writes nothing -- no re-dirty, no flag, no log")

    # ---- D: the booking-wide decorator -------------------------------------------------------------
    from types import SimpleNamespace

    from KrakenOS.UI.services import quick_estimation as qe_mod

    def _booking(outcome):
        def body(self):
            self.editor.slide_fold_arm_along_leg(SLIDE_MM)
            # what a booking records once its lens move succeeded -- the `also=` channel
            self.editor._fov_solve_lens_move_mm = 12.5
            if outcome == "raise":
                raise ValueError("past the slide")
            if outcome == "stuck":
                import copy as _c

                self.editor.rows[3] = _c.copy(self.editor.rows[3])
                return False, "refused."
            return (outcome == "ok"), ("fine" if outcome == "ok" else "refused.")
        return qe_mod._refused_booking_moves_nothing(body)

    for outcome, want_intact in (("refuse", True), ("ok", False), ("raise", True)):
        editor = _fixture()
        start = _fingerprint(editor)
        service = SimpleNamespace(editor=editor)
        propagated = False
        try:
            _booking(outcome)(service)
        except ValueError:
            propagated = True
        intact = _fingerprint(editor) == start
        move_claim = editor.__dict__.get("_fov_solve_lens_move_mm", "<absent>")
        claim_right = (move_claim == "<absent>") if want_intact else (move_claim == 12.5)
        ok(intact == want_intact and (propagated == (outcome == "raise")) and claim_right,
           f"D[{outcome}]: a booking that ends '{outcome}' leaves the scene "
           f"{'byte-identical' if want_intact else 'moved (success keeps its work)'}, and the "
           f"recorded lens move is {move_claim!r} -- a put-back scene must not claim a move")
    editor = _fixture()
    verdict, message = _booking("stuck")(SimpleNamespace(editor=editor))
    ok(verdict is False and "could NOT be put back" in str(message),
       "D[stuck]: when the put-back is impossible the message SAYS so instead of implying "
       "nothing moved")
    ok(hasattr(qe_mod.QuickEstimationService._apply_conjugate_pair, "__wrapped__"),
       "D[wired]: the real booking is wrapped by the net")

    # ---- E: the explanation -------------------------------------------------------------------------
    editor = _fixture()
    first = {
        "_lens_move_refusal": "only 74.47 mm of physical room is left before Filter 48-926.",
        "_lens_move_room_mm": 74.47, "_lens_move_refusal_info": {"kind": "physical_room"},
        "_lens_leg_slide_refusal": "", "_lens_leg_slide_shortfall": 56.92,
    }
    # what the RETRY left behind, measured on the slid scene that no longer exists
    editor._lens_move_refusal = "only 275.1 mm of physical room is left before RA mirror 2."
    editor._lens_move_room_mm, editor._lens_leg_slide_shortfall = 275.1, 0.0
    facts = qe_mod._restate_refusal_after_put_back(editor, first, {"distance": SLIDE_MM})
    ok(editor._lens_move_room_mm == 74.47 and editor._lens_leg_slide_shortfall == 56.92,
       "E1: the channel carries the FIRST attempt's numbers again -- measured on the scene "
       "that exists, not the ~275 mm of a slid scene that does not")
    ok(facts == {"make_room_tried_mm": SLIDE_MM, "make_room_put_back": True},
       f"E2: structured facts for the refusal stash ({facts})")
    text = str(editor._lens_move_refusal)
    lead = first["_lens_move_refusal"].rstrip(".")
    ok(text.startswith(lead) and "put back" in text
       and text.index("275.1") > text.index("Making room"),
       "E3: the reason LEADS with the first refusal, says the arm was put back, and keeps the "
       "retry's reason after it as the bracketed detail")
    untouched = _fixture()
    for name, value in first.items():
        setattr(untouched, name, value)
    facts_none = qe_mod._restate_refusal_after_put_back(untouched, first, None)
    ok(facts_none == {} and untouched._lens_move_refusal == first["_lens_move_refusal"]
       and untouched._lens_move_room_mm == 74.47,
       "E4: when the arm never moved the first refusal stands UNTOUCHED on the editor and no "
       "facts are claimed")

    # ---- W: the REAL booking, real slide, scripted refusing lens move ------------------------
    Q = qe_mod.QuickEstimationService
    first_text = "only 74.47 mm of physical room is left before its body reaches Filter 48-926"

    def _booking_case(function):
        editor = _fixture()
        calls = []

        def translate(_delta, **_kwargs):
            calls.append(float(editor.rows[2].thickness))
            if len(calls) == 1:   # measured on the scene the user is looking at
                editor._lens_move_refusal = first_text
                editor._lens_move_room_mm, editor._lens_leg_slide_shortfall = 74.47, 56.92
            else:                 # the retry: measured on the SLID scene
                editor._lens_move_refusal = "only 275.1 mm is left before RA mirror 2"
                editor._lens_move_room_mm, editor._lens_leg_slide_shortfall = 275.1, 0.0
            return None

        editor.translate_lens_block_along_leg = translate
        editor._folded_conjugate_gaps_for_magnification = lambda _m: {
            "object_gap_row": 0, "image_gap_row": 4, "object_delta": 131.4, "image_delta": 0.0,
        }
        editor._imaging_lens_block_indices = lambda: (1, 2)

        class _QE:
            _apply_conjugate_pair = function

            def __init__(self, ed):
                self.editor = ed

            def _gap_row_for_delta(self, rows, index):
                return index

            def _folded_image_leg_write_row(self, index):
                return index

        start = _fingerprint(editor)
        verdict = _QE(editor)._apply_conjugate_pair(10.0, 4.0)
        return editor, calls, start, verdict

    # W0 CONTROL: neuter ONLY the rescue's savepoint and the unwrapped booking must strand the
    # scene. Without this, W2[unwrapped] could pass because the fixture never really slid.
    real_transaction = qe_mod.GeometryTransaction

    class _Neutered(real_transaction):
        def rollback(self):
            if self.label != "make room at the fold":
                return super().rollback()
            self.state = "rolled_back"   # claims it put things back; writes nothing
            return 0

    qe_mod.GeometryTransaction = _Neutered
    try:
        editor, calls, start, verdict = _booking_case(Q._apply_conjugate_pair.__wrapped__)
    finally:
        qe_mod.GeometryTransaction = real_transaction
    ok(verdict[0] is False and _fingerprint(editor) != start
       and abs(float(editor.rows[2].thickness) - (GAP_BEFORE + 57.92)) < 1e-9,
       f"W0: CONTROL -- with the rescue's savepoint neutered the refused booking STRANDS the "
       f"scene (gap row {GAP_BEFORE} -> {float(editor.rows[2].thickness):.3f}); W2 is not vacuous")

    for tag, function in (("unwrapped", Q._apply_conjugate_pair.__wrapped__),
                          ("wrapped", Q._apply_conjugate_pair)):
        editor, calls, start, verdict = _booking_case(function)
        slide = 56.92 + 1.0
        ok(len(calls) == 2 and abs(calls[0] - GAP_BEFORE) < 1e-9
           and abs(calls[1] - (GAP_BEFORE + slide)) < 1e-9,
           f"W1[{tag}]: the real rescue slid the real arm INSIDE the real booking -- the retry "
           f"saw the gap row at {calls[1] if len(calls) > 1 else '?'} (was {GAP_BEFORE})")
        ok(verdict[0] is False and _fingerprint(editor) == start,
           f"W2[{tag}]: the booking refuses AND the scene is byte-identical"
           + (" -- by the rescue's OWN savepoint, the net is not in play" if tag == "unwrapped"
              else ""))
        info = editor.__dict__.get("_fov_solve_refusal_info") or {}
        ok(info.get("make_room_put_back") is True
           and abs(float(info.get("make_room_tried_mm") or 0.0) - slide) < 1e-9
           and info.get("leg_room_mm") == 74.47,
           f"W3[{tag}]: the refusal stash carries VALUES -- tried {info.get('make_room_tried_mm')}"
           f" mm, put back {info.get('make_room_put_back')}, room {info.get('leg_room_mm')} mm "
           f"(the first attempt's, not the slid scene's 275.1)")
        ok(str(verdict[1]).startswith("FOV out of range on this fold: " + first_text)
           and "put back" in str(verdict[1]),
           f"W4[{tag}]: the message leads with the first refusal and says the arm was put back")

    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
