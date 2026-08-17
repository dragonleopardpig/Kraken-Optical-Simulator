"""Guard for bugs/0613 — unverified corrections cannot steer bookings.

The bugs/0608 one-shot swap re-measure recorded c=0.4731 (a 2x first-order
disagreement, never verified), the next solve over-booked by that factor, the
refinement aborted "unmeasurable" without unlearning, and the readout landed at -30%
(phases 447/448 flipped). Trust boundary: VERIFICATION, not factor size — the solve
refinement's converged factors stay unbounded within the 0591 sanity range.

Checks (display-free, stubbed editor):
  A  GATE — relearn_folded_m_correction refuses to store one-shot factors outside
     [0.5, 2.0] (both sides), stores sane ones.
  B  UNLEARN — both "unmeasurable" exits of _refine_folded_field_fill clear the
     standing correction and re-book the RAW target conjugate.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0613_unverified_relearn_gate
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np


def _service(measured, promised_raw=0.4189, correction=None):
    """QuickEstimationService over a stub editor, with the probe stubbed to `measured`."""
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = SimpleNamespace(
        _folded_m_correction_state=correction,
        append_debug=lambda *a, **k: None,
    )
    service = QuickEstimationService(SimpleNamespace(editor=editor))
    object_semi = 27.5
    service._measured_delivered_image_semi = lambda semi: measured
    service.current_state = lambda: {
        "magnification": promised_raw * (correction or 1.0),
        "fov_semi": object_semi,
    }
    booked = []
    service._apply_conjugate_pair = lambda o, i: (booked.append((o, i)) or (True, ""))
    return service, editor, booked


def run_checks():
    notes: list[str] = []
    ok = True

    # ---------------------------------------------------------------- A: the gate
    # measured/object_semi / promised_raw = factor. object_semi=27.5, promised 0.4189:
    # measured 5.45 -> factor ~0.4731 (the bugs/0613 poison) must NOT be stored.
    service, editor, _ = _service(measured=27.5 * 0.4189 * 0.4731)
    out = service.relearn_folded_m_correction()
    if out is not None or editor._folded_m_correction_state is not None:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0613): a 0.47x one-shot factor was stored ({out}) -- the next "
            "solve over-books its conjugate again"
        )
    else:
        notes.append("PASS: A1: a <0.5x one-shot factor is rejected (not stored)")
    service, editor, _ = _service(measured=27.5 * 0.4189 * 2.4)
    out = service.relearn_folded_m_correction()
    if out is not None or editor._folded_m_correction_state is not None:
        ok = False
        notes.append(f"FAIL: A (bugs/0613): a 2.4x one-shot factor was stored ({out})")
    else:
        notes.append("PASS: A2: a >2x one-shot factor is rejected")
    service, editor, _ = _service(measured=27.5 * 0.4189 * 0.906)
    out = service.relearn_folded_m_correction()
    if out is None or editor._folded_m_correction_state is None or abs(out - 0.906) > 1e-6:
        ok = False
        notes.append(f"FAIL: A (bugs/0613): a sane 0.906 factor was NOT stored ({out})")
    else:
        notes.append("PASS: A3: a sane one-shot factor still stores (the 0608 feature survives)")

    # ---------------------------------------------------------------- B: the unlearn
    # First-measurement blindness with a standing (unverified) correction:
    service, editor, booked = _service(measured=None, correction=0.4731)
    msg = service._refine_folded_field_fill(27.5, 11.5)
    if editor._folded_m_correction_state is not None:
        ok = False
        notes.append("FAIL: B (bugs/0613): first-probe blindness kept the unverified correction")
    elif not booked or abs(booked[-1][1] - 11.5) > 1e-9:
        ok = False
        notes.append(f"FAIL: B (bugs/0613): no raw re-book after unlearning (booked={booked})")
    else:
        notes.append("PASS: B1: first-probe blindness unlearns and re-books the raw target")
    # Mid-refinement blindness: first probe measures (off-target), second goes blind.
    # RE-DERIVED for bugs/0626: the old contract unlearned and re-booked the RAW target --
    # measured on the flagged Apo75, that raw re-book demanded a 267 mm lens slide and left
    # 8 of 9 field pencils dead. The refinement now restores its own best MEASURED pair
    # (request 24.31 -> measured 8.0, traced by this very solve), which still satisfies the
    # bugs/0613 spirit: no NEVER-verified number steers the booking or the readout.
    calls = {"n": 0}

    def flaky(semi):
        calls["n"] += 1
        return 8.0 if calls["n"] == 1 else None

    service, editor, booked = _service(measured=None, correction=0.4731)
    service._measured_delivered_image_semi = flaky
    msg = service._refine_folded_field_fill(27.5, 11.5)
    best_request = 11.5 / 0.4731
    want_correction = 8.0 / best_request
    stored = editor._folded_m_correction_state
    if stored is None or abs(float(stored) - want_correction) > 1e-9:
        ok = False
        notes.append(
            f"FAIL: B (bugs/0613/0626): mid-refinement blindness stored {stored} instead of "
            f"the best MEASURED pair's ratio {want_correction:.4f} -- either the unverified "
            "0.4731 survived or a blind booking is steering the readout"
        )
    elif "unmeasurable" not in msg or "best measured booking" not in msg:
        ok = False
        notes.append(f"FAIL: B: the unmeasurable exit lost its message ({msg!r})")
    else:
        notes.append("PASS: B2: mid-refinement blindness restores the best measured booking")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Unverified-relearn-gate validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
