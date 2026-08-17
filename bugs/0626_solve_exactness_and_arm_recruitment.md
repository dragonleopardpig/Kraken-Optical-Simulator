# 0626 — TRIAGE (OPEN): 55×55 solves to 54.5; recruit the fold arm when the lens leg floors

flag_20260817_131423 (build b967fa43, the 0625 fix confirmed working — census 558 paths,
**0 missed_image**, 172 arrivals): *"input 55x55, why become 54.5x54.5? can't it be
exact? Note the lens is almost hitting the RA mirror, the auto solve should adjust the
4th section distance if 3rd section can't meet."*

## Root causes (read from the code; marathon was running — no edits yet)

### a) 54.5 is the refinement's 1% tolerance, not a limit

`_FIELD_FILL_TOLERANCE = 0.01`, `_FIELD_FILL_MAX_PASSES = 5` (quick_estimation).
54.5/55 = −0.91% — inside tolerance, so the secant loop exits and the honest readout
shows the delivered 54.5. The machine was NOT out of room at that point (a room refusal
would have surfaced as "refinement stopped"). The user wants delivered == typed to
readout precision.

### b) The fold-arm recruitment has a dead branch

`slide_lens_block_along_its_leg` refuses in two ways:
- room refusal (`amount > _lens_leg_room_to_fold`) → sets `_lens_leg_slide_shortfall`
  → `_apply_conjugate_pair` recruits `slide_fold_arm_along_leg(shortfall + 1)` and
  retries ("Made room first: the fold mirror and the camera moved …"). WORKS.
- gap-positivity refusal (`up_new <= 0 or down_new <= 0`) → sets ONLY the refusal
  text, NO shortfall → recruitment never fires; the pass stops with a residual.
  This branch runs whenever `_lens_leg_room_to_fold` returns None (no promoted fold
  ahead / pose error) yet the section gap is exhausted — exactly "3rd section can't
  meet, adjust the 4th".

Note `_lens_leg_room_to_fold` already charges the mirror half-aperture + lens barrel
overhang + mechanical margin (bugs/0583) — "almost hitting the RA mirror" is the solve
spending room down to that margin, which is by design; the margin held.

## Fix plan

1. **Exactness**: `_FIELD_FILL_TOLERANCE` 0.01 → 0.001, `_FIELD_FILL_MAX_PASSES`
   5 → 10. The secant typically lands in 2–4 passes; extra passes only run while the
   error is still > 0.1%. Keep messages formatted from the constants (guards pin the
   TEXT patterns, 448 B2/B3 — do not alter the strings themselves). Convergence exit
   already learns c + centre (0625).
2. **Recruitment**: in the gap-positivity branch, set
   `_lens_leg_slide_shortfall = amount − max(room_left_in_gap − floor, 0)` so the
   existing QE recruitment path fires there too; the arm slide + the 0575 re-solve
   finisher then absorb it. The recruitment already re-runs per refinement pass.
3. Re-verify on the flagged scene: typed 55 → delivered 55.0 readout (±0.1%), lens
   keeps the 0583 margin off the mirror, arm recruitment message appears when room
   runs out, 9 pencils still arrive (0625 guard stays green). Also eyeball
   `ray_actor_count` — the flag shows 8 with all arrivals; confirm it is an actor
   grouping artifact, not a hidden pencil.
4. Guard: phase 470 — tolerance/pass constants contract + a stub behaviour check that
   the gap-branch refusal sets the shortfall channel (the 0572 stub arithmetic
   pattern), + convergence-to-0.1% on a synthetic linear machine.

## Status: OPEN — design ready; implement after the 2026-08-17 baseline re-cut
(marathon in flight when triaged; repo .py edits forbidden during a cut).
