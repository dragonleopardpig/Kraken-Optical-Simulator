# 0221 — manual measurement can snap to the RA-mirror centre (axis ∩ hypotenuse)

**Status: FEATURE SHIPPED (the snap TARGET). The manual-measurement re-anchor tool can now snap a
dimension endpoint to the RA-mirror CENTRE — the point where the optical axis meets the mirror
hypotenuse (the fold vertex = the promoted RA-mirror centre) — so the user can measure e.g. object
plane → RA-mirror centre. Answers the `flag_20260704_195234` request. In-app drag verification is
owed (the pick/drag is interactive; headless proves the snap target + measurement, not the mouse
gesture).**

## The request

`flag_20260704_195234`: "For manual measurement overlay, can we have option to snap from object
plane to the RA mirror center (snap to the intersection of optical axis and RA mirror hypotenuse
surface)?"

## What it did before

The re-anchor tool (`_apply_dimension_anchor_pick_motion`, `open3d_inspector.py`) snapped a dragged
endpoint to the arbitrary surface point under the cursor on whatever body was hit — so dragging onto
the RA mirror gave an imprecise point that wandered over the prism face. (The COMMITTED anchor did
re-derive the row's centre z via `_surface_reference_world_point`, but the live snap did not, so the
centre snap was neither precise nor discoverable.)

## The fix

- `_ra_mirror_fold_vertex_world(row_index)` (`services/paraxial_tools.py`): returns the fold vertex
  for a promoted RA-mirror row — `_surface_reference_world_point` returns the folded element centre,
  which for a promoted RA mirror IS the axis ∩ hypotenuse point (verified == `promoted_mirror_world_
  center`: mirror-1 (0,0,71.9), mirror-2 (182.67,−1.53,70.6)). Returns None for any non-RA-mirror row.
- `_apply_dimension_anchor_pick_motion`: when the cursor is over a promoted RA mirror, the moving
  endpoint snaps PRECISELY to that vertex (labelled "RA MIRROR CENTRE") instead of the surface point.
  The committed anchor already re-derives the same centre, so the live snap now matches the commit.

Object plane → mirror-1 centre (both on the incoming +Z axis) then measures 71.90 mm = the object →
fold-vertex distance, i.e. the FIRST optical-axis segment the user asked about.

## Verification

Display-free guard `validate_open3d_ra_mirror_centre_snap` (4/4): the vertex resolves + equals the
promoted-mirror centre for both RA mirrors, is gated to RA mirrors (None for Object/Image/lens/
aperture/datum rows), the object→mirror-1-centre measurement, and wiring. Penta **phase 197**,
baseline `pass`.

## Known limitation (not this feature — a bigger, separate refactor)

The dimension tool is Z-AXIS-CENTRIC: a re-anchored endpoint keeps its X/Y on the optical axis and
snaps only Z, and the measured value is `abs(z1 − z0)` (the global-Z component). This is exact for a
measurement ALONG the incoming/outgoing legs (which run in Z) — including object → mirror-1 centre —
but it DROPS the transverse component of the MIDDLE leg (mirror-1 → lens runs in +X, so a middle-leg
span reads its Z-delta ≈ 0, not the real length). Making the tool measure the true folded path (or
snap the full-3D vertex for the off-axis mirror-2) is a larger change to the Z-centric dimension
model, tracked separately. The reported object working / image distance are already correct end-to-end
(bugs/0219); this snap is a manual cross-check aid for the first axis segment.
