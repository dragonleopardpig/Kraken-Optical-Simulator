# 0920 -- a follower lens's edge walls stayed at the pre-fold pose in the non-sequential trace

**A real physics bug, and a regression from 2026-06-03.** Found by `validate_vendor_prism_42779`:
"vendor prism followed by a cemented doublet focuses the meridional fan" failed with
image_z_span 7.83 mm. It should be ~0.0015 mm.

## Bisected

- It passes at 2026-06-01 (span 0.00154) and fails at 07-01, 08-01 and 09-01 with the identical
  value.
- The first bad commit is **318040e9** (06-03), "bug 0003: mesh STEP optical solids in-process
  with OCC B-Rep".
- That commit did not introduce the bug. It moved the prism's mesh so that a latent bug became
  visible.

## Root cause

The y=+10 fan ray's events were 1, 1, 1, **3**, 1, 2, 3, 3, 4, 5. It registered a hit on surface 3
(the flint front, vertex at y=38.5) at (0, -13.5, 102.5), inside the prism. At that spurious hit
its direction reversed. Logging the mesh queries showed the hit came from `EEE[7]`. The tracer
has 8 meshes for 5 surfaces: `GlassOnSide = [0,1,2,3,4,5,2,3]`. Meshes 6 and 7 are the crown and
flint elements' **edge walls** (`Prerequisites3DSolids` appends each `Side3D` body to EEE after
the face meshes). Their bounds were y 10..40 in a thin z band, a barrel lying along the wrong
axis, reaching down into the prism's exit.

`_apply_optical_solid_output_port_system_overrides_built` moves each follower element to the
output-port pose. It transforms the face meshes `EEE[k]` and the side bodies `BBB[i]`, replacing
each with a transformed COPY. But `EEE` holds its own reference to every side body, and those
entries still pointed at the untransformed originals. The tracer intersects `EEE`, not `BBB`, so
every follower lens's edge wall stayed where the element was before the fold.

## Fix

When a side body is transformed, its `EEE` twin gets the same delta. `EEE` is the n face meshes
followed by `BBB` in order, so the twin's index is `len(EEE) - len(BBB) + body_index`.

## Verified

- The edge walls now sit with their elements: y 33.7..34.6 and 34.6..40.1 around z=112.5.
- All three rays take the clean path prism -> crown -> flint -> back -> image.
- The fan focuses to 0.00153 mm, the 06-01 value.

## Also in this batch (stale checks in the same validator)

- The mirror-labelled path and the boundary-index face order compare the two mirrors as a SET:
  the F003/F004 labels swapped relative to the physical fold order (0847 face records), as in
  0919.
- The reference-plane harness gains `_surrogate_blackbox_member_rows` (bugs/0627).
