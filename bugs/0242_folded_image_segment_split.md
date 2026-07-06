# 0242 — Per-segment constraint for the IMAGE conjugate (the "2+2" completion)

## Intent
The object-side per-segment constraint (bugs/0234–0237) lets the user pin one leg of the OBJECT
conjugate at the 1st periscope fold — object→mirror or mirror→first-surface — and slides that fold
mirror while the optics hold the conjugate. On the two-fold AZ85 periscope the user asked to pin the
IMAGE conjugate too, at the 2nd fold. That is the **"2+2"** freedom: 2 legs × 2 conjugates. (The
general **N+n** — several folds per conjugate — is future work; this ships the two-fold case the user
runs today.)

In a two-fold relay the image distance is bent by the image-side RA mirror:
`image_total = near + far` (last lens surface → mirror → sensor, along the folded beam). The optics
fix `image_total` (the conjugate / focus); the split is the mechanical freedom. Pinning one leg
slides the mirror and carries the detector onto the end of the repositioned arm, focus untouched.

## The object/image asymmetry (why the object arithmetic does not port)
The **object** mirror is a SEQUENTIAL fold — its `desp_z` is an along-axis decenter, so its vertex is
`station + desp_z` and `near = station + desp_z` (bugs/0234). The **image** mirror is a FREE-PLACED
promoted solid (bugs/0213/0218) pinned in global +Z, so its `desp_z` is a **WORLD offset**, not an
along-axis decenter — the object formula gives a nonsense negative split (≈ −126 mm here).

So the image legs are read straight off the **straight-equivalent gap ROWS**, which sum to
`_paraxial_total_image_gap` (and match the row-editor prescription the user edits):

- `near = sum(thickness[gap_start : mirror_row])` — last lens surface → mirror station.
- `far  = sum(thickness[mirror_row : image_row])` — mirror station → sensor.

`gap_start` walks back from the last optical reference through any trailing fold the beam passes
THROUGH (matching `_paraxial_total_image_gap`); `mirror_row` is the fold strictly between them.

## The slide (`_apply_folded_image_split`)
Pin `near` (or `far`); `delta = near_new − near`. Add `delta` to the leg INTO the mirror
(`near_gap_row = mirror_row − 1`) and subtract it from the mirror's own gap to the sensor
(`far_gap_row = mirror_row`) — `near + far` (the total, the focus) is unchanged. Then
`carry_free_placed_followers_after_fold` redirects the post-fold walk onto the reflected leg so the
free-placed trailing mirror rides the beam instead of advancing in +Z (bugs/0236). A single fold can
pin only ONE image leg: the two legs are perpendicular, so with the total fixed the fold point is
geometrically determined — the DETECTOR moves onto the end of the repositioned arm; the camera body
stays put.

## Collision floor (the subtle part)
Each leg gets a collision floor so the mirror cannot slide into the lens (near) or the detector
(far). The object side uses `0.5 × thickness[mirror_row]`, which is stable there because its
`far_gap_row` is a SEPARATE trailing spacer — the mirror row is never slid. On the **image** side
`far_gap_row == mirror_row`, so `thickness[mirror_row]` **is the far leg being slid**: a
`0.5 × thickness[mirror_row]` floor would shrink to `0.5 × far` and never stop the mirror (an unsafe
`far` always clears half of itself). The floor is instead the mirror's **aperture half-diameter**
(`0.5 × row.diameter`) — a STABLE, geometry-only along-axis half-extent that does not move with the
slide. (A body STEP overlay could extend it further; the aperture radius is the read-from-rows floor.)

## Dialog
The FOV popup (`_open_quick_estimation_fov_popup`) offers this plane's near/far constraint as two
checkboxes + entries, gated on a fold for that plane (`_folded_object_conjugate_split()` for the
object popup, `_folded_image_conjugate_split()` for the image popup). The image labels read
*"Constrain last surface → mirror distance"* and *"Constrain mirror → sensor distance"*. Ticking one
leg grays out its sibling (`_sync_seg`) — `near + far` are mutually determined, so only one may be
pinned. `_apply_quick_estimation_fov_solve` threads the checked leg as `segment` and, after the FOV
solve, dispatches by plane: object → `_apply_folded_object_split`, image →
`_apply_folded_image_split`, on the post-solve geometry. One button ("Solve for Thickness"): the FOV
moves *and* the fold mirror slides to the pinned leg with the just-solved conjugate held fixed.

## Verification
`KrakenOS/UI/validate_open3d_folded_image_segment_split.py` (penta **phase 219**), on the two-fold
fixture:

- **SPLIT** — `near + far == image_total`, and `near`/`far` match the straight-equivalent fold legs
  reconstructed independently from the gap rows (`near = 150.37`, `far = 40.0`, total `190.37`).
- **SLIDE** — pinning `near` slides the mirror there (`> 1 mm`), the image total is unchanged
  (Δtotal `< 1e-4`), and the free-placed trailing mirror keeps its axial beam offset (carried, not
  frozen off-axis).
- **RANGE** — a constraint needing a negative gap is rejected, not applied.
- **SAFE GAP** — `far_min = 0.5 × diameter = 12.5 mm` is stable: a valid `far` (`far_min + 8`)
  applies, an unsafe one (`far_min − 3`) is rejected with a "Safe gap" message. (Fail-before: the old
  `0.5 × thickness[mirror_row]` floor moved with the far leg and never rejected the unsafe case.)
- **TRACE** — after the slide the scene still images: rays reach the relocated detector.
- **WIRED** — the image FOV popup offers the near/far checkboxes (`_folded_image_conjugate_split()`,
  *"Constrain last surface"*, *"mirror → sensor"*) and the solve calls `_apply_folded_image_split`.

The object-side guards (`validate_open3d_folded_conjugate_split`,
`validate_open3d_folded_fov_segment_merge`, `validate_open3d_two_fold_image_arm_follow`) still pass —
the object plane is untouched. The dialog is a Tk popup and can't be driven headless; this guard
checks the split geometry and the wiring the popup consumes. In-app visual confirm owed (restart the
app onto this build, open the IMAGE FOV popup on the two-fold, tick a leg, Solve for Thickness, and
confirm the 2nd fold mirror + detector slide while the image stays in focus).
