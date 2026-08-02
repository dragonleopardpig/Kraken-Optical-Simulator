# 0513 — "is the 0508 C fix general enough?" No: the 3 mm gate is a CLIFF (+ an unmatched fingerprint)

Flag `flag_20260802_204748_649` ("after glue, dragging the lens STEP detached
from lens surrogate, is the previous fix general enough?"),
`machine_vision_150mm_test.py`, build `117f75dc`. The recording was NOT flushed
-- only the static end-state exists.

## Measured (bugs/probe_0513_lens_detach.py, glue-then-drag matrix)

| gesture | gap (body vs front datum) | offset after |
|---|---|---|
| M1: glue + 40-frame carry (+24 axial, one 0.2 mm jitter frame) | 28.153 -> 28.153 HELD | (0.2, 0, 0) |
| M2: glue + ONE 4 mm jitter frame + 39 axial frames | 28.153 -> **51.553 DETACHED (+23.4)** | (4.0, 0, 23.4) |
| M3: glue + single +42 commit | HELD | (0, 0, 0) |

**M2 is the general weakness**: 0508 C widened the on-axis gate 1e-3 -> 3 mm,
but ONE drag frame past 3 mm parks the body 4 mm off-axis and every later frame
then fails the gate -- the rest of the drag moves the body alone. A tolerance
can only move the cliff, not remove it.

## The flag's fingerprint does NOT match any row

Flag end-state: offset **[0,0,0]** with the body exactly +41.7 mm past the
datums (spans equal -- pure axial). M2 predicts a non-zero offset; M1/M3 stay
attached. Candidate explanations needing the RECORDING to decide: a re-glue /
undo after the detach, a solve moving the datums back, or a third drag path not
exercised here. **Ask the user to reproduce with the recorder flushed** (drag ->
close/stop recording -> flag) before coding.

## Fix directions (pending the recording)

1. Kill the cliff, not move it: during a glued axial slide, make the redirect
   verdict STICKY per gesture (evaluate on-axis-ness once at drag start), or
   project mostly-axial frames onto the axis (discard jitter) the way the 0503
   FOLDED row-carry always did -- while preserving the deliberate-park gesture
   (decisively lateral drags, the flag_20260621_142758 / C1 protection).
2. Whatever ships must add an M2-style jitter-cliff case to phase 409's guard.

## RESOLVED — the fingerprint was DISPLAY-STALE, not a model detach

Flag `flag_20260802_210224_063` (same scene, current build) reproduced the exact
fingerprint: body front = front datum + 41.5, offset [0,0,0], zero lateral
anywhere. Decoding: the MODEL was attached the whole time -- the body front sat
exactly ON the MODEL datum (which the axial redirect had slid) while the DRAWN
row actors stayed at the old station, because the unfolded thickness-redirect
branches never set `_fold_carry_pending_rebuild`, so the release flush stayed
scoped to the dragged STEP label (the exact bugs/0503 lesson, fixed on the
folded branches only). My M1/M3 probes measured the model -- which is why they
looked "held" while the user watched a detach.

Fix: `_fold_carry_pending_rebuild = True` on BOTH unfolded redirect branches
(lens axial + detector axial) in `translate_step_overlay`; phase 409's guard
gained B3 pinning the marker. The live-drag half (surrogate rows now TRACK the
barrel mid-drag instead of appearing at release) ships with bugs/0514.

The M2 jitter cliff (one >3 mm lateral frame poisons the rest of the drag)
remains REAL but was NOT the user's path (no lateral in either flag) -- kept
open as a hardening item; fix direction unchanged (sticky per-gesture verdict).
