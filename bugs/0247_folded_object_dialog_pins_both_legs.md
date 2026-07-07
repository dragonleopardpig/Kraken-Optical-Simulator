# 0247 — Object FOV dialog pins BOTH fold legs in one solve (feature)

## Request
Double-clicking the OBJECT-plane FOV gizmo on a folded scene opened a dialog with **two**
checkboxes that pin one leg of the OBJECT fold (object → mirror / mirror → first surface). The
IMAGE-plane dialog separately offered two checkboxes for the IMAGE fold (last surface → mirror /
mirror → sensor). The user asked: *"the current 2 boxes for input of constraint of object side
splitting, can I have another 2 boxes with the same function for Image side?"* — i.e. put the
image-side pair **into the object dialog too**, so one "Solve for Thickness" can pin one object
leg AND one image leg together (four boxes in the object dialog on a two-fold).

## Why this is well-posed
The object fold and the image fold are **independent mechanical freedoms**:
- the OBJECT mirror is a SEQUENTIAL fold (its along-axis `desp_z` places the vertex); its split
  slides gap rows `0` (object gap) and the trailing spacer row;
- the IMAGE mirror is a FREE-PLACED promoted solid (bugs/0213/0218); its split slides the two
  gap rows straddling the mirror (`mirror_row-1`, `mirror_row`).

They touch **disjoint** gap rows, so pinning one object leg and one image leg in the same solve
does not over-constrain anything (within one conjugate near+far are still mutually determined, so
only one leg per fold is pinnable — that invariant is unchanged). Each split preserves its
conjugate TOTAL (the focus) and carries the free-placed trailing mirror onto the beam with the
bugs/0244 leg-walk carry.

## What shipped (one commit)
`KrakenOS/UI/open3d_inspector.py`:
- `_open_quick_estimation_fov_popup` — the split-box block is refactored into a reusable inner
  helper `_build_split_group(seg_split, kind, start_row, header)` that renders one conjugate's
  near/far checkbox pair with its OWN sibling gray-out and returns `(segment_getter, next_row)`.
  The OBJECT dialog now builds the object group AND (on a two-fold, gated on
  `_folded_image_conjugate_split()`) the image group below it, with bold "Object-side fold" /
  "Image-side fold" headers when both are shown. The IMAGE dialog still builds only the image
  group (single group, no header — byte-identical layout to before). Grid rows and `button_row`
  are computed dynamically from the helper's returned `next_row` (single-group dialogs land on
  the same rows as before, so the design block below is unmoved).
- `run(mode)` reads a second getter (`image_segment_getter`) and threads `image_segment` into
  the solve.
- `_apply_quick_estimation_fov_solve(..., segment, image_segment=None)` — after the plane's own
  split, when `image_segment is not None and plane == "object"` it applies
  `_apply_folded_image_split(image_leg, value)` and appends its message (surfaced-but-non-fatal,
  like the object split). `image_segment` is recorded in the `fov_solve` dialog command for
  replay. Backward compatible: the IMAGE dialog and any old recording pass `image_segment=None`.

No new editor/service code — the feature is pure UI plumbing over the existing
`_apply_folded_object_split` / `_apply_folded_image_split` (bugs/0242) and their bugs/0244 carry.

## Result (AZ85 two-fold, headless)
`fov_solve('object','thickness',30,21)` then object split near=60 then image split near=100:

    object conjugate: total 170.018 -> 170.018 (held), near -> 60.000 (pinned)
    image  conjugate: total 150.120 -> 150.120 (held), near -> 100.000 (pinned)
    image mirror along-beam 265.018 == last-lens 165.018 + image near 100.0  (rides the beam)
    both mirrors ordered: object -> M1 -> lens block -> M2 (265.018) -> sensor

Both conjugates (both foci) preserved, both legs exact, the free-placed image mirror re-seated at
its pinned prescription distance past the lens (bugs/0244), not frozen at its stale authored
offset. Applying the image split does not disturb the pinned object leg and vice versa.

## Verification
`validate_open3d_folded_object_plus_image_split` (display-free, AZ85 two-fold) pins four checks:
  1. BOTH CONJUGATES HELD — one solve + both pins keeps both totals and hits both legs exactly;
  2. IMAGE MIRROR RIDES THE BEAM — the free-placed mirror re-seats at last-lens + image near
     (265.018), ordered after the lens (bugs/0244 re-seat);
  3. INDEPENDENT FREEDOMS — the image split leaves the object leg + totals untouched, the object
     split leaves the image total untouched;
  4. WIRED — the object popup builds both split groups, threads `image_segment` into the solve,
     which applies it via `_apply_folded_image_split` (object plane only) and records it.
Added as penta phase 223. The bugs/0242 image-segment-split (phase 219), bugs/0236 two-fold
arm-follow (phase 213), bugs/0244 free-mirror re-seat (phase 222) and the recorder-captures-
dialogs guard all still pass unchanged (the `segment` payload/contract is untouched; the extra
`image_segment` key is additive).

## Owed
In-app eyeball: a Tk dialog + embedded-VTK trace cannot be driven headless, so the four-box
layout and the live combined solve need the user's visual confirmation in the running app.
General N+n (several folds per conjugate) remains future work; this is "2+2" on a two-fold.
