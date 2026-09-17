"""bugs/0331 -- display-free guard for the trailing-edge hover re-pick contract.

Root cause of the CA-not-highlighting family (flags 978/798/718/630/408): the
mouse-move throttle (``_mouse_move_due``, 35 ms) drops the motion events that
arrive closer than the interval, and there was NO trailing re-pick. A mouse
coming to REST fires its last reports inside one throttle window, so the FINAL
resting cursor never got a hover pick -- the highlight froze 300-590 px behind
the cursor, even though the pick logic resolves the opening correctly AT the
resting cursor (proven live in bugs/diag_0330f_flag408_live.py: [420,635]->F164).

The fix adds a debounced, one-shot trailing re-pick. This guard binds the REAL
inspector methods (no VTK/Tk display) onto a fake ``self`` with a fake Tk widget
and asserts the timer CONTRACT:
  A. a throttled move SCHEDULES exactly one trailing timer (~interval+5 ms),
  B. a second throttled move DEBOUNCES (cancels the prior, schedules one fresh),
  C. the timer firing at rest RE-PICKS once (idle) ...
  D. ... but NOT while a carry drag/follow owns the mouse,
  E. an explicit cancel drops the pending timer,
  F. with no widget it is an inert no-op (never raises).
"""
from __future__ import annotations
import types

from KrakenOS.UI.open3d_inspector import Kraken3DInspector as K


class FakeWidget:
    def __init__(self):
        self.scheduled: dict[str, tuple[int, object]] = {}
        self.cancelled: list[str] = []
        self._n = 0

    def after(self, delay_ms, cb):
        self._n += 1
        tok = f"after#{self._n}"
        self.scheduled[tok] = (int(delay_ms), cb)
        return tok

    def after_cancel(self, tok):
        self.cancelled.append(tok)
        self.scheduled.pop(tok, None)


def _make(widget):
    """A minimal object carrying only what the three methods touch, with the
    REAL methods bound so the guard exercises production code, not a copy."""
    self = types.SimpleNamespace()
    self._vtk_widget = widget
    self._mouse_move_min_interval_s = 0.035
    self._trailing_hover_repick_after_id = None
    self._step_carry_drag_state = None
    self._step_carry_follow_state = None
    self._refires = 0

    def _refire():
        self._refires += 1

    self._refire_scene_hover_pick = _refire
    for name in (
        "_schedule_trailing_hover_repick",
        "_cancel_trailing_hover_repick",
        "_on_trailing_hover_repick",
    ):
        setattr(self, name, types.MethodType(getattr(K, name), self))
    return self


def main() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  ok  " if cond else "  FAIL") + "  " + msg)
        ok = ok and bool(cond)

    # A. schedule once
    w = FakeWidget()
    s = _make(w)
    s._schedule_trailing_hover_repick()
    tok1 = s._trailing_hover_repick_after_id
    check(tok1 in w.scheduled, "A: one trailing timer scheduled")
    delay, cb = w.scheduled[tok1]
    check(35 <= delay <= 60, f"A: delay ~= interval+5 ({delay} ms)")
    check(cb == s._on_trailing_hover_repick, "A: callback is the trailing re-pick")

    # B. debounce: a second throttled move cancels the first, keeps one
    s._schedule_trailing_hover_repick()
    tok2 = s._trailing_hover_repick_after_id
    check(tok1 in w.cancelled, "B: prior timer cancelled (debounced)")
    check(tok2 != tok1 and tok2 in w.scheduled, "B: exactly one fresh timer pending")
    check(len(w.scheduled) == 1, "B: never more than one pending timer")

    # C. fire at rest -> exactly one re-pick, id cleared
    _, cb2 = w.scheduled[tok2]
    cb2()
    check(s._refires == 1, "C: resting timer re-picked once")
    check(s._trailing_hover_repick_after_id is None, "C: id cleared after firing")

    # D. carry drag active -> timer must NOT re-pick
    w2 = FakeWidget()
    s2 = _make(w2)
    s2._step_carry_drag_state = {"dragging": True}
    s2._schedule_trailing_hover_repick()
    _, cbd = w2.scheduled[s2._trailing_hover_repick_after_id]
    cbd()
    check(s2._refires == 0, "D: no re-pick while a carry drag owns the mouse")
    s2._step_carry_drag_state = None
    s2._step_carry_follow_state = {"following": True}
    s2._schedule_trailing_hover_repick()
    _, cbf = w2.scheduled[s2._trailing_hover_repick_after_id]
    cbf()
    check(s2._refires == 0, "D: no re-pick while a carry follow owns the mouse")

    # E. explicit cancel drops the pending timer
    w3 = FakeWidget()
    s3 = _make(w3)
    s3._schedule_trailing_hover_repick()
    tok3 = s3._trailing_hover_repick_after_id
    s3._cancel_trailing_hover_repick()
    check(tok3 in w3.cancelled, "E: cancel calls after_cancel")
    check(s3._trailing_hover_repick_after_id is None, "E: id cleared on cancel")

    # F. no widget -> schedule/cancel are inert and never raise (the re-pick
    # itself is gated downstream in _refire_scene_hover_pick, not here).
    s4 = _make(None)
    try:
        s4._schedule_trailing_hover_repick()
        s4._cancel_trailing_hover_repick()
        inert = s4._trailing_hover_repick_after_id is None
    except Exception as exc:  # noqa: BLE001
        inert = False
        print("  FAIL  F raised:", exc)
    check(inert, "F: no-widget schedule/cancel is an inert no-op")

    print("\nRESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
