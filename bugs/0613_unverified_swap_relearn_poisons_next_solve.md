# 0613 — The one-shot swap re-measure poisons the next solve (FIXED)

Found by the 2026-08-11 baseline re-cut: phases 447/448 (0572/0573 solve-refusal /
make-room family) flipped PASS→FAIL after the bugs/0608–0610 swap arc landed. The
standalone reproduces deterministically.

## Measured chain (Apo75 → PYRITE 4.5/85 swap, then 55×55 solve)

1. `relearn_folded_m_correction` (bugs/0608) takes a ONE-SHOT real-ray measurement at
   the swap's transitional state and records **c = 0.4731** — a claimed 2× disagreement
   with the first order. Unlike the solve refinement, nothing ever verifies this value.
2. The next 55×55 solve books its conjugate at `sensor/c` — over-booked ~2× (paraxial
   |m| 0.8854 vs the 0.4189 target).
3. The refinement probe cannot measure at that state ("the delivered field became
   unmeasurable") and aborted WITHOUT unlearning — booking and readout both kept the
   poisoned factor. Readout landed at −30% (marathon: diag 50.5, want 77.8); at 35×35
   the wrong arithmetic happened to skip the make-room step the guard expects.

The Apo75's own converged factor (c = 2.0318, typed = delivered verified exact) shows
large factors are legal WHEN VERIFIED — the trust boundary is verification, not size.

## Fix

- `relearn_folded_m_correction` stores only factors within **[0.5, 2.0]**; outside
  that, a single unverified probe is a broken measurement, not physics — log and leave
  the correction unset (the next solve's secant refinement learns the real factor with
  verification).
- Both "unmeasurable" exits of `_refine_folded_field_fill` now **unlearn** the standing
  correction and re-book the RAW target conjugate, so typed == booked == readout even
  when verification is impossible (refusals from the raw re-book surface verbatim).

Verified: the 0573 standalone (both the 35×35 and 55×55 post-swap cases) restored to
green; phase 447's premise (35×35 needs room under raw arithmetic) restored with it.

Guard: phase 465 (`validate_open3d_0613_unverified_relearn_gate`) — the relearn gate
and both unlearn-and-rebook exits, display-free.

## Cross-machine note

bugs/0608–0610 came from the M90aPro session; this keeps their readout-after-swap
feature for sane measurements (|factor−1| ≤ …×2) and only rejects the unverifiable
tail. If a future scene legitimately needs a >2× one-shot factor, the answer is a
verified measurement (run the solve refinement), not widening the gate.
