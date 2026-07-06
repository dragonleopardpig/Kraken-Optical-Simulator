# 0237 — Typed FOV stays frozen at 23×23 because the split button never read the FOV boxes

## Symptom
flag_20260706_113107_413, on the promoted two-fold AZ85 periscope. The user typed a **55×55** FOV,
set the object-segment constraint to 50, and clicked the standalone bottom **"Apply split (move
mirror)"** button:

- "I can see the distance changed" — the split slid the fold mirror correctly.
- "…but the FOV text label remain 23×23mm" — the target FOV never moved off its old value.
- "I can't separately apply the FOV I have input, then click on split button next" — every
  FOV-consuming Solve button *closed* the dialog, so there was no "apply the FOV, then split" path.

## Root cause
The dialog had **two independent actions** that could not be composed:

- The FOV section's Solve buttons (`_apply_quick_estimation_fov_solve` → `qe.fov_solve`) filled the
  sensor **and** set the target FOV, then **closed the popup**.
- A separate standalone section at the bottom (`_add_folded_conjugate_split_section`) drove
  `_apply_folded_object_split`. Its handler read **only** the near/far leg spinboxes and never
  touched the FOV boxes.

So clicking *Apply split* moved the mirror (its own job) but left the FOV untouched — the label
stayed 23×23. And because the FOV Solve closed the dialog, the user could not run the FOV solve and
*then* the split in one sitting. The two operations were mutually exclusive by construction.

## Fix (user-directed)
"Merge the 3rd section [split] into the first [FOV], and introduce a checkbox for the segment
constraint. User then clicks *Solve for Thickness* and everything should be correct."

- The standalone split section is **removed** (`_add_folded_conjugate_split_section` is deleted, and
  its "Apply split (move mirror)" button along with it).
- The object-segment constraint becomes an **optional checkbox** — *"Constrain object → mirror
  distance"* — merged into the FOV section, with its leg spinbox.
- `_apply_quick_estimation_fov_solve` now threads a `segment` argument. It runs `qe.fov_solve`
  (fills the sensor **and** sets the target FOV) and, when the checkbox supplies a segment, then runs
  `_apply_folded_object_split` on the **post-solve** geometry (which recomputes the object→mirror
  total itself). One button, one action: the FOV moves *and* the fold mirror slides to the pinned
  leg, with the just-solved conjugate held fixed.

Because the split runs on the post-solve geometry and the trailing mirror is carried onto the beam
by `carry_free_placed_followers_after_fold` (bugs/0236), the merged op is a pure mechanical
repackaging: the solved total conjugate is preserved and the mirror stays on the beam.

## Verification
`KrakenOS/UI/validate_open3d_folded_fov_segment_merge.py` (penta **phase 214**) drives the exact
merged sequence on the two-fold fixture:

- **FOV CHANGES** — `fov_solve("object","thickness",55,55)` sets the target object semi to the 55×55
  diagonal semi (`hypot(55,55)/2 ≈ 38.89`); the label input moves off its old value.
- **SEGMENT PINS + TOTAL PRESERVED** — the follow-on `_apply_folded_object_split("near", …)` pins the
  object→mirror leg to the requested value on the post-solve geometry while the just-solved total is
  unchanged (Δtotal < 1e-4).
- **MIRROR ON BEAM** — across the merged op the trailing mirror moves (>1 mm) but keeps its axial
  beam offset (carried, not frozen off-axis).
- **STILL IMAGES** — after the merged op rays still reach the detector.
- **WIRED** — `_apply_quick_estimation_fov_solve` threads `segment` and calls
  `_apply_folded_object_split`; the popup adds the "Constrain object" checkbox and threads
  `segment=segment`; `_add_folded_conjugate_split_section` is gone.

Overlays/3D are a VTK render and can't be pixel-validated headless (llvmpipe SIGSEGV); this guard
checks the geometry and the wiring the dialog consumes. In-app visual confirm owed (restart the app
onto this build, re-type 55×55 with the checkbox, and confirm the label reads 55×55).
