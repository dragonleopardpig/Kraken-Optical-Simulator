# 0214 — a re-imported RA mirror auto-inherits its Mirror face (fold DOWN, not UP)

**Status: FIXED. Re-importing the SAME right-angle-mirror part a second time (the user's "add
another mirror" workflow) now auto-assigns that part's authored Mirror face, so the new mirror folds
DOWN by its own orientation with NO manual right-click. Fixes the 0213 regression the user flagged as
"the image plane and detector wrong direction".**

## What the user flagged

Right after 0213 shipped, the user promoted a 2nd RA mirror on the AZ85 (ELS-85 surrogate) scene and
flagged the result WRONG via `flag_20260703_122209_873` — *"the image plane and detector wrong
direction"* — paired with the `before`-promotion reference `flag_20260703_122046_143`. After promoting
the free-placed, oriented 2nd mirror, the image plane / detector / rays folded **UP (+Z)** when they
should fold **DOWN (−Z)**. The flag's `state.json`: row 8 mirror-2 centre `(182.67, −1.53, 70.6)`
tilt 0; row 9 image z **83…123** — well ABOVE the placed mirror centre `z = 70.6` (the wrong side).

## Root cause — the promoted mirror had NO Mirror face

0213 (Fix B) folds a free-placed 2nd mirror by physics off its own orientation, **but only once the
row carries a `function == "Mirror"` face** — every fold path (`mirror_fold_face_normal`,
`free_placed_mirror_world_planes`, the detector re-frame) keys on that. The user's real session
(recording `122301`) had **ZERO right-clicks** (no button-3 events at all), so the 2nd mirror was
never given a "Full Reflecting" face.

A clean promote auto-roles **every** face `Transmit`/`Port`. With no Mirror face,
`select_optical_solid_output_face` picks the **+Z straight-through** face (the bugs/0084 output-port
side-priority) as the output port, and `build_optical_solid_output_port_pose_overrides` seats the
downstream image/detector along **+Z (UP)** at `z = 123.098` — an exact match for the flagged
`state.json` (image z 83…123). So the "wrong direction" was not a fold-direction error in the 0213
mechanism at all; it was the 2nd mirror silently **not being a mirror**.

Reproduced end-to-end in `bugs/probe_0214_seating.py`: a clean promote (no Mirror face) → image UP at
`z = 123.098`; the same scene WITH the Mirror face assigned → image DOWN at `z = −62`.

**Hypothesis explicitly ruled out:** the stored face normal is **not** stale. `bugs/probe_0214_
metadata_stale.py` shows the promoted overlay's stored Mirror-face normal tracks the placement
rotation exactly ("AGREE" at every rotation); at `(90, 45, 0)` the hypotenuse normal is
`(−0.707, 0, −0.707)`, which reflects `+X` DOWN correctly. The normal was always right — there simply
was no `function == "Mirror"` face for the fold to read.

## The product decision

The fold could be fixed two ways: keep manual face assignment (user must right-click "Full
Reflecting" every time) or auto-assign it on a same-part re-import. The user chose (via
AskUserQuestion) **"Auto-fold same-part re-import"**: when promoting a part that is already a Mirror
elsewhere in the scene, auto-assign the Mirror face to the same hypotenuse so it folds by its
orientation with no manual click. Scoped to same-part re-imports — it will not turn a promoted lens
into a mirror. This matches the natural "import the same mirror twice" workflow.

## The fix — same-part Mirror carry-over on promote

`KrakenOS/UI/services/step_overlay_promotion.py`, new
`StepOverlayPromotionService._carry_over_same_part_mirror_face`, called at the end of
`promote_imported_step_to_optical_solid_row` (right after `_mark_plot_update_pending`):

- **Same part** is matched by **resolved source STEP path** (`_promoted_source_step_key`, reads
  `StepOverlayPromotion`/`StepNativePromotion` → `source_step_path`, `Path(...).resolve()`). The AZ85
  mirror-1 (row 1) and the re-imported mirror-2 share
  `attachment/prisms/Right_Angle_Mirror/87931/step_87391.step`.
- The reflecting face is matched by **`face_id`** (same part → same face topology; both use
  `S001/F002`, area ≈ 884) with an **area cross-check** (reject if it differs by > max(1 mm², 2 %)),
  so a coincidental id collision across DIFFERENT parts cannot mis-assign.
- The carry runs the standard `assign_optical_solid_face_function(row, face_id, "Full Reflecting")`
  path, so the fold + the detector/image seating see exactly a **user-authored Mirror face** (0213).

**Strictly scoped:** only a face the user already authored `Mirror` on the identical part is carried
over — a promoted lens/prism (no mirror donor) is never turned into a reflector; a row the user
already marked keeps its own authoring (idempotent, no re-assign).

## Why penta-safe

The carry-over runs **only inside `promote_imported_step_to_optical_solid_row`**. Loading a saved
layout (penta cascade, stock AZ85) never calls it, so those scenes are untouched. And even on a
promote it will not misfire: a different part, a non-mirror donor, an already-authored target, and a
same-id/mismatched-area face are all left inert (proven by the guard's five scoping cases).

## Verification

Display-free guard `validate_open3d_second_mirror_same_part_mirror_carryover` (10/10):

1. a clean AZ85 promote of the same-part RA mirror **auto-carries** `S001/F002` → fold normal
   `(−0.707, 0, −0.707)` (folds `+X` DOWN);
2. the detector/image **seats DOWN** at `z = −62.05` (below the placed mirror `z = 70.6`);
3. the free-placed **display-ray fold** reflects the `+X` beam DOWN (`+X → (0, 0, −1)`), 1 plane;
4. **CAUSAL:** strip the carried Mirror face and re-seat → the detector flips back **UP** to
   `z = 123.098` — exactly the flagged bug, proving the carried face is what folds it DOWN;
5–9. **scoping:** a same-part donor carries the exact face (one assign call); a DIFFERENT part with a
   colliding id is inert; a same-part **lens** is inert (never mirrored); an already-authored target is
   inert; a same-id face whose **area disagrees** is rejected;
10. the carry-over is **defined AND called** inside the promote path (guard not vestigial).

Regression: `validate_open3d_second_mirror_orientation_driven_fold` (0213) still PASS — its synthetic
mirror-2 is a `deepcopy` that already carries a Mirror face, so the carry-over is inert there and the
0213 fold mechanism is exercised unchanged.

Registered as penta **phase 190** (`phase_190_second_mirror_same_part_mirror_carryover`), baseline
`pass`. The full validator marathon still SIGSEGVs on llvmpipe, so phases 0–189 are carried forward.

Scratch probes (untracked): `bugs/probe_0214_seating.py` (reproduces UP vs DOWN),
`bugs/probe_0214_verify.py` (the fix folds DOWN), `bugs/probe_0214_metadata_stale.py` (normal is not
stale), `bugs/probe_0214_fold_planes.py`.

**In-app eyeball owed:** the headless guard proves the seating + ray fold go DOWN; the final rendered
image plane / detector / rays through the full VTK draw should be confirmed in-app on the user's
two-mirror AZ85 scene.

## What's next (deferred, per the user)

The **FOV shrinks per added RA mirror** (~23 mm → ~20 mm → ~16 mm; the `before`-promotion screenshot
confirmed "FOV 20.2×20.2" with one mirror). The user asked to investigate this **only after** the
fold fix is confirmed, so it is out of scope here.
