# 0221 — manual measurement can snap to the RA-mirror centre (axis ∩ hypotenuse)

**Status: FEATURE SHIPPED (the snap TARGET). The manual-measurement re-anchor tool can now snap a
dimension endpoint to the RA-mirror CENTRE — the point where the optical axis meets the mirror
hypotenuse (the fold vertex = the promoted RA-mirror centre) — so the user can measure e.g. object
plane → RA-mirror centre. Answers the `flag_20260704_195234` request. In-app CONFIRMED
(`flag_20260704_223026_841`, "Manual measurement of snapping optical axis works."): the manual
dimension snaps to the RA-mirror centre and reads 71.9 mm object-plane → RA-mirror-1 centre (the first
optical-axis segment), with a second 60.66 mm segment on the outgoing leg.**

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

## The "Z-only" limitation was a phantom — the measure tool is already 3D-correct (verified 2026-07-05)

An earlier draft of this doc claimed the manual measure tool is "Z-axis-centric" — that it keeps X/Y
on the optical axis, snaps only Z, and reports `abs(z1 − z0)`, so a MIDDLE-leg span (mirror-1 → lens,
which runs in +X) would read its Z-delta ≈ 0 instead of the real length. **That is wrong.** Direct
testing of the orange measure tool on the folded two-mirror scene shows it computes the true 3-D
distance:

- `_record_measure_point` stores the raw picked (optionally axis-snapped) world point; `dist` is
  `norm(p1 − p0)` (point-to-point) — a genuine 3-D length, not a Z-delta.
- `_anchor_measure_point` matches a pick's world-Z to the nearest row's cumulative-Z STATION and
  `_resolve_measure_point` re-derives only Z from that station, **keeping the pick's X/Y**. On the
  folded scene every middle-leg row sits at world-Z ≈ 71.9 (they run along +X), so a middle-leg pick
  anchors to the same row (mirror-1) — but its X is preserved, so the measured length is right.
- Verified span mirror-1-centre (0,0,71.9) → lens element (87.59,0,71.9): the tool returns **87.590
  mm** (the true +X extent), not 0. Object → mirror-1-centre still reads 71.90 mm; the outgoing-leg
  pick (181.37,0,−22.05) keeps its full 3-D position too.

So there is nothing to fix here: the tool the user drives measures folded distances correctly (matching
the in-app `flag_20260704_223026_841` "measurement works" — 71.9 mm + a 60.66 mm outgoing-leg span).
The only residual Z-collapse is the axis-snap FALLBACK (`_project_world_onto_optical_axis` → `(0,0,z)`)
used when NO axis polyline is rendered — an edge case that does not arise on a normal folded scene.
