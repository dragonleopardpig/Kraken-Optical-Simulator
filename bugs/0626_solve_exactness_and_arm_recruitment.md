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

## What the first verification run uncovered (the real hazard)

Tightening the tolerance alone was NOT safe. Probe run 1 (tolerance 0.1%, no other
change) on the flagged scene: inside the ~1% band the book→focus-snap response is
oscillation/noise-dominated, two passes measure nearly the same delivered field, the
secant slope collapses, and the raw step explodes — a −0.9% residual produced +52.8 mm
then +267 mm lens-slide requests, the (correctly firing) arm recruitment amplified them
into 288 mm of fold-arm travel, the field became unmeasurable, and the old 0613
mid-loop exit then unlearned the correction and re-booked the RAW first order — leaving
the scene dislocated with 8 of 9 field pencils dead and a 77.8 mm readout. The old 1%
tolerance had been silently masking all of this.

## Final design (shipped) — five pieces, each forced by a measured failure

1. Tolerance 0.1%, pass ceiling 10.
2. Gap-exhaustion refusal reports its shortfall → arm recruitment fires there too
   (upstream exhaustion stays a plain refusal — the arm cannot make room in front of
   the lens).
3. **Step clamp**: a legitimate local slope near 1 needs a step ~error×target; the
   secant step is capped at 10× that — a larger demand means the slope is broken;
   take the multiplicative step (~error-sized by construction) instead.
4. **Geometry restore, not booking restore** (probe v2's lesson): the refinement
   explores by MUTATING the scene — lens/arm slides, focus snaps — with no undo, so a
   degraded exit that merely re-BOOKS the best request lands in a DIFFERENT machine
   than the one that measured it (measured: re-book after the arm slid 268 mm →
   +15.7%, 8 of 9 pencils dead; and v2's mystery "+267 mm slide" was exactly this
   re-book). The refinement snapshots row poses + STEP placement offsets at each
   best-improving pass and restores THAT on every degraded exit — mid-loop
   unmeasurable, refused re-book, oscillating loop end — then stores the pair's
   verified ratio. The bugs/0613 rule survives in spirit: nothing never-measured
   steers the scene; the pre-loop unmeasurable exit keeps the raw unlearn. Guards
   0613-B2 and 0625-A re-derived.
5. **An unvignetted ruler** (probes v4/v5's lesson): the delivered-field measurement
   probed at 0.7× the TYPED field — 27.2 mm object height on a machine that images
   ~14 — so the bundle mostly died and the surviving edge rays' centroid saturated
   near the image circle (~19.9 mm) REGARDLESS of conjugate: a flat response no
   iteration can converge on (and the source of the old ±1% "residual"). Worse, even
   near-axis full-acceptance cones lose ~43% to aperture clipping at some conjugates,
   biasing any centroid. The probe now (a) uses a NARROW pencil (acceptance × 0.1)
   about the chief ray — the chief's landing height IS the image height, immune to
   aperture clipping — and (b) shrinks the probe fraction until bundles keep ≥60% of
   their rays (genuine field-stop exclusion still reads as unmeasurable). Per-pass
   debug (`field-fill pass N: request → measured`) is permanent.

## Verified (diag_0626_solve_exact_55.py, probe v6 on the flagged scene)

Load → 55×55 solve: the refinement walked 19.3 → 15.64 → 20.17 → 18.51 → 16.56 →
16.37 → 16.33 → 16.18 → 16.5 → **16.29 = target exactly** (solve message:
"Delivered field measured 32.58 mm vs target 32.58 (+0.0%...)"), readout diagonal
77.78 = 55.00×√2, all 9 field pencils arrive, lens-to-fold margin 1.6 mm (the 0583
mechanical margin held — "almost hitting" the RA mirror is the solve legitimately
spending its room down to that margin). The residual band on any given solve is the
traced machine's ~±1% measurement noise; the step clamp keeps the walk stable inside
it and the best measured state is always what the scene lands on.

Guard: phase 470 (`validate_open3d_0626_solve_exactness_arm_recruitment`).
