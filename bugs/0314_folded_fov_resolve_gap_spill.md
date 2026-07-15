# 0314 — A second Solve-for-Thickness on a two-fold periscope silently no-ops

## Flag
`attachment/recorded_bug_repros/flag_20260715_105226_165/` (AZ85 / ELS-85 two-fold RA-mirror
periscope + imported camera):

> *"first time change FOV to 55x55, and make 2 constraint, it works. But second time change to FOV
> 20x20, same constraints, not working. It seems not doing any processing at all after clicking Solve
> for Thickness the second time."*

The recorded screenshot confirms it: after the second solve the object disc is still Ø38.9 mm
(FOV **55×55**), i.e. the FOV never changed — the solve did nothing.

## Root cause — the object-distance correction is dumped on ONE gap row
A folded conjugate solve (`QuickEstimationService._apply_conjugate_pair` → the folded branch, using
`_folded_conjugate_gaps_for_magnification`) computes the correction needed to bring the object /
image **totals** to `f·(1+1/m)` / `f·(1+m)` and writes each correction onto a single gap row:
`object_gap_row = 0` (object → mirror) and `image_gap_row` (last lens surface → mirror). It then
guards `if new_obj_gap < 0 or new_img_gap < 0: return False` and bails.

That row is not the only object-side leg. On a fold, the object distance spans **two** legs around
the mirror (object→mirror + mirror→first-surface). The user's two constraints pin one leg of each
fold:

1. **Solve 1 (FOV 55×55):** conjugate sets object total 259.8 mm (row 0 = 177.3 mm). The
   `object → mirror = 50 mm` constraint (`_apply_folded_object_split`) then slides 139.8 mm **out of
   row 0** into the far spacer → row 0 = **37.5 mm**. Works, retraces, FOV = 55. The user sees it work.
2. **Solve 2 (FOV 20×20):** larger magnification (|m| 0.42 → 1.15) needs the object ~129 mm **nearer**,
   so `object_delta ≈ −129 mm`. It's dumped entirely on row 0: `37.5 − 129 < 0` → guard returns
   **False**: *"FOV out of range on the folded arms — slide the fold mirrors first."* `ok=False` →
   `_apply_quick_estimation_fov_solve` skips the retrace → **"nothing happens."**

The object total (259.8 mm) has ample room for the reduction — the **far spacer holds 209.8 mm** —
but the solve only ever touched the one drained row. The status bar did carry the error, but a user
watching the 3D view (waiting for the ~69 s folded retrace) reads it as a dead button.

Reproduced headless (pure paraxial row math, no VTK/trace) in
`bugs/probe_0314_double_fov_solve.py`: solve 1 + short object pin, then solve 2 → `conjugate ok=False`.

## Fix — spill the overflow onto the fold's other leg (slide the mirror)
The correction is a change to a leg **total**; how it splits across the fold's near/far legs is a
mechanical DOF (and the constraint split re-pins it right afterward). So instead of failing when one
leg can't hold the whole delta, distribute it:

- **`_distribute_folded_gap_delta(rows, primary_row, delta, spill_row)`** — applies `delta` to the
  primary row; if that underflows below 0, the primary gives up all it has (→ 0) and the negative
  remainder lands on `spill_row`, **preserving the total**. Returns the `(row, applied_delta)` list,
  or `None` only when even the two legs together can't absorb it (truly out of range). Both legs are
  floored at 0 — the collision floor is enforced by the constraint split that runs after.
- **`_folded_conjugate_spill_row(primary_row, side)`** — the sibling leg to spill onto: the fold
  split's **far** leg, and only when that split's *near* leg IS the primary row (else `None`, so an
  unrelated row is never trusted as the sibling).

`_apply_conjugate_pair` now routes both the object and image corrections through the distributor and
carries the **actual per-row changes** into `carry_free_placed_followers_after_fold` (previously it
passed the whole delta on row 0 — a pre-fold row the carry ignores anyway, so the non-spill path is
byte-for-byte unchanged). When the primary row has room, the distributor returns `[(row, delta)]` —
exactly the old single-row write, zero behavioural change.

After the fix, Solve 2 succeeds: row 0 drains to 0, 91.5 mm spills to the far spacer, object total =
130.6 mm, and the subsequent `object → mirror = 50 mm` re-pin is honoured (near 50 / far 80.6). The
system retraces to the requested FOV 20×20 — exactly what the old error told the user to do by hand.

## Why the shared solver, not a special case
Per *"guard the invariant, not the instance"*: the invariant is **a folded conjugate solve must reach
the target leg total whenever the total geometry allows it, regardless of how the current near/far
split happens to be arranged.** The old code violated it by hard-binding the delta to one row. The
fix restores the invariant in the shared `_apply_conjugate_pair`, so it holds for every folded
Solve-for-Thickness (single- or two-fold, object- or image-side underflow), not just this scene.

## Verified (display-free)
`KrakenOS/UI/validate_open3d_folded_fov_solve_gap_spill.py` — **PASS (13 checks)**:
- **A** the distributor: in-range delta → single primary write; underflow spills to the sibling with
  the **total preserved**; `None` when there is no sibling or both legs can't hold it.
- **B** the sibling is the split's far leg, and only when its near leg is the primary row (else `None`,
  incl. no-fold scenes).
- **C** the real two-solve sequence (FOV55 + short object pin, then FOV20 + same pin) — the second
  solve **succeeds** (object 130.6 mm, |m|=1.152) where the pre-fix path returned False, and the
  pinned `object → mirror = 50 mm` is honoured at the new total.
- **D** plain (no-constraint) two-solve sequence still both succeed and the primary row absorbs the
  delta directly (no spill — the old single-row write).
- **E** structural wiring: `_apply_conjugate_pair` routes through the distributor + sibling picker and
  carries the per-row changes.

The three existing folded guards still PASS unchanged
(`validate_open3d_two_fold_image_arm_follow`, `validate_open3d_folded_fov_solve`,
`validate_open3d_folded_fov_free_mirror_reseat`). Penta **phase 276**
(`phase_276_folded_fov_solve_gap_spill`) delegates to the new guard; baseline updated (`"276": "pass"`).

## Files
- `KrakenOS/UI/services/quick_estimation.py` — `_distribute_folded_gap_delta`,
  `_folded_conjugate_spill_row`; `_apply_conjugate_pair` folded branch distributes both corrections
  and carries the per-row changes.
- `KrakenOS/UI/validate_open3d_folded_fov_solve_gap_spill.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_276_folded_fov_solve_gap_spill`.
- `tools/penta_validator_baseline.json` — phase 276 baseline + title.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): open the AZ85 two-fold periscope, Solve-for-Thickness at
  FOV 55×55 with an object→mirror leg pinned short, then re-solve at FOV 20×20 with the same pin —
  confirm the second solve retraces to the smaller FOV (mirror slid) instead of silently doing
  nothing. The display-free guard proves the distributor, the sibling pick, the end-to-end
  two-solve success with the pin honoured, and the plain-path non-regression.
