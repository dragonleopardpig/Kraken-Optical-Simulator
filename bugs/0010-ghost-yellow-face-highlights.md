# 0010 — Hover edge highlights stranded after the Center-Row→Optical-Axis snap ("ghosts")

**Status:** Fixed (2026-06-04) — real root cause found and corrected in
`KrakenOS/UI/services/scene_placement_commands.py`. The earlier sign-off
(2026-06-03, commit `69fdf4d`) was a **false fix**: it flipped the status to
"Fixed" with **no code change**, so the ghost recurred ("supposed to be solved,
but now I see them come back"). The true cause was **two seams that stranded the
overlay's per-face metadata at the pre-move pose** (details below); both are now
fixed, covered by a display-free metadata test, an image-snapshot test, and
validator **Phase 20** (gate baseline regenerated).
**Component:** Open 3D inspector — the lens **hover edge highlight**
(`Kraken3DInspector._set_step_hover_outline` /
`_set_step_hover_outline_impl`, open3d_inspector.py ~10588; the cached actor
`_hover_step_outline_actor` keyed by `_hover_step_cell_key`) **vs** the
snap that repositions the lens without clearing it:
`_apply_center_row_to_optical_axis` (open3d_inspector.py ~10294), armed by
**Place → Center Row → Optical axis** (`start_center_row_to_ray`,
open3d_application_logic.py ~52).
**Reported via:** in-app recorder, flag `flag_20260603_171626_741`
(2026-06-03T17:16:26). **Repro bundles are gitignored**, so the evidence below
is transcribed here.

## Symptoms (user's words)

> still have ghost surfaces above the lens

Precise repro (user, at sign-off): the "ghosts" are actually the **highlighted
edges** that appear when the mouse hovers the **aspheric lens**.

1. Hover the aspheric lens → its edges highlight (the hover outline).
2. **Place → Center Row → Optical axis** → the lens **snaps** onto the optical
   axis (it moves).
3. But the highlighted edges **stay where they were** (the lens's pre-snap
   position). They sit there **invisible until the mouse hovers that — now
   empty — region again**, where they light up again.

So stale hover highlight / pick geometry is left behind at the lens's former
location after the snap; "a few elsewhere too" → several such ghosts accumulate
as the lens is repositioned more than once.

## State evidence

`flag_20260603_171626_741/state.json` (recording active, nothing selected):

* `selected_step_label = null`, `picked_step_label = null`,
  `picked_row_index = null` — nothing is selected; this is a passive hover.
* `step_actor_bounds["optical"]` = x[-12.50, 12.50] y[**-12.54, 12.46**]
  z[12.11, 23.69] — the imported lens body tops out at y ≈ +12.46.
* `scene_visible_bounds` y-max = **29.706** — a visible prop sits ~17 mm
  **above** the top of the lens body. That extra prop is the ghost.
* `cursor.png_xy = [546, 329]` — the cursor (and the floating gold rounded-rect
  + green/magenta hover crosshair + `OPTICAL STEP S002/F002 face` tooltip) are
  near the top-centre of the frame, well above the lens.
* `thickness_dimension_count = 0`, all handle counts `0` — no gizmo/overlay; the
  only "extra" geometry is the hover highlight itself.
* Lens is parked near the Object end (z ≈ 12.1–23.7); optical axis z = -65..165.

The screenshot shows the lens (side view, on-axis) with a small gold rounded
rectangle floating high above it, the hover crosshair, and the
`OPTICAL STEP S002/F002 face` tooltip — i.e. the face-hover highlight for face
F002 is being drawn as a tiny box up in empty space instead of on the face.

## Root cause (confirmed 2026-06-04, headless)

The snap moves the body, but the **per-face overlay metadata** the hover/pick
read stayed frozen at the pre-move pose. The hover/pick path reads
`_step_overlay_face_metadata(label)` (in
`KrakenOS/UI/services/scene_placement_commands.py`), which memoises analytic
face records carrying world-space `centroid_world` / `normal_world`. **Two
independent seams** stranded those records:

1. **Pose-blind cache key.** `_step_overlay_face_metadata` keyed its cache on
   `(label, source-file stat)` only — *not* the placement offset / rotation. So
   the first hover computed the records at the original pose and cached them; a
   later move re-read the **same cache entry** and got the original world coords
   back. (The hover path re-reads **without** clearing the cache, which is why
   this is the dominant seam.)
2. **Affine-transformed cap centroid that silently degenerates.** Grouped
   axisymmetric **cap** faces (the round-lens front/back caps) derived their
   centroid by affine-transforming the *source-frame* analytic centroid:
   `affine @ source_centroid`, where `affine = _affine_from_point_sets(source_tris,
   display_tris)`. That fit returns `None` whenever the source and display
   triangle counts differ (they routinely do), and the code then **fell back to
   the raw source coords** — so even on a forced recompute the caps never moved.
   Commit `69fdf4d` had already renamed `assignment_source` to
   `…_group_transformed` but still affine-transformed the centre, so the fix was
   only cosmetic — hence the recurrence.

**Why the ghost is the cap pick / marker, not the outline.** The hover *outline*
geometry is rebuilt from the record's stored `triangle_indices` →
`face_indices_for_record` → all triangles of that face-id selected from the
**moved** display mesh, so the outline always tracks the body. The stale-able
consumers are: (a) the **cap pick decision** —
`_metadata_round_lens_cap_pick` ray-tests the stale `centroid_world`/`normal`
plane, so a pick at the cap's *new* screen position misses while a pick at the
*vacated old* region hits the stale plane; and (b) the **centre-anchored marker
/ tooltip** (`surface_center`, from `centroid_world`/`centroid`), which is the
gold rounded-rect + crosshair the user saw floating ~17 mm above the body
(`scene_visible_bounds` y-max 29.71 vs body top 12.46 in
`flag_20260603_171626_741`). Re-hovering the now-empty old region re-picks the
stale-plane face and redraws its marker/outline there — the "ghost".

## Fix

`KrakenOS/UI/services/scene_placement_commands.py`:

1. **Seam 1 — pose-aware cache key.** New
   `_step_overlay_pose_cache_signature(label)` returns the rounded live pose
   `(rot_z, rot_x, rot_y, axis_offset_xy, placement_offset_xyz)`.
   `_step_overlay_face_metadata` now folds it into the cache key, so a move
   invalidates the entry and recomputes world coords at the new pose. Labels in
   `_DISPLAY_ONLY_STEP_LABELS_NO_ANALYTIC = {"camera", "led", "lens"}` keep the
   stat-only key (they have no analytic metadata to strand, and re-keying them
   triggered a ~35 s recompute on every pose nudge).
2. **Seam 2 — derive the cap record from the display-transformed triangles.**
   Dropped the `_affine_from_point_sets` / `affine @ source_centroid` path. The
   grouped cap record is now built straight from the moved display triangles via
   `_analytic_step_face_record_from_triangles(...)`, so **both** the centre and
   the normal come from the current pose. `assignment_source` stays
   `step_analytic_axisymmetric_group_transformed`.

## Tests

* **Display-free metadata test** —
  `KrakenOS/UI/validate_open3d_step_overlay_metadata_tracks_pose.py`. Imports an
  optical STEP, reads the metadata, moves the overlay +20 mm in z **with no cache
  clear between reads** (exactly what the hover path does), and asserts every
  face centroid — including the grouped caps — tracks the move. The tracked
  prism always runs (guards seam 1); a round lens with grouped caps additionally
  exercises seam 2. Teeth verified: reverting either fix flips it to FAIL
  (`worst_track_err_mm = 20`).
* **Image-snapshot test** (visual bug, mandatory) —
  `KrakenOS/UI/validate_open3d_step_overlay_hover_tracks_move_snapshot.py`. Uses
  an **oblique** camera (a side-on view makes the cap-plane ray test degenerate,
  `|ray·normal|≈0`, so the pick never fires) on a round-lens-like fixture. It
  picks the cap at its projected screen-xy before a 25 mm move, then picks again
  at both the **vacated old** and the **new** screen positions, and anchors a
  marker sphere on the pick's `surface_center` so the rendered PNGs show
  ghost-vs-tracked by eye. The discriminator with teeth is
  `ghost_stale = (old-region pick returns a `surface_center.z` still at the old
  z)`; a whole-frame outline diff has **no** teeth because the outline always
  tracks. With the fix: the new pick tracks (same cap, z follows) and the
  old-region pick returns nothing or a correctly-moved cap.
* **Validator Phase 20** —
  `phase_20_overlay_metadata_tracks_pose` in
  `validate_open3d_penta_telescope_comprehensive.py` imports the display-free
  validator's core (`_evaluate_fixture` / `_first_lens_with_grouped_caps`) so the
  two stay in lockstep, and source-couples seam 1 (asserts the cache key still
  folds in `_step_overlay_pose_cache_signature`). Gate baseline regenerated
  (`tools/penta_validator_baseline.json`).
