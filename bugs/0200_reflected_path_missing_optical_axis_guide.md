# 0200 — BUG: the reflected (folded) path has no optical-axis line

**Status: RESOLVED. On a single promoted-mirror fold the 3D view now draws a dotted
optical-axis guide along the OUTGOING (reflected) branch, in addition to the incoming +Z
guide. Fix in `Kraken3DInspector._folded_reflected_axis_guide_record`, wired into
`_optical_axis_records_for_3d`; guard `validate_open3d_ra_mirror_reflected_axis_guide.py`.**

## Flag

`attachment/recorded_bug_repros/flag_20260701_201444_437` (and observed across the folded
AZ85 RA-mirror flags):

> "the reflected path missing optical axis line."

## Root cause — the incoming guide is clamped at the mirror, and the outgoing guide relied on traced rays

`_optical_axis_records_for_3d` draws the global dotted "Optical Axis" guide along +Z. On a
fold, bugs/0189 deliberately **clamps** that guide's far end to the fold point
(`z1 = min(z1, fold_point_z + margin)`) because past the mirror the axis turns onto +X — the
intent being that the **traced ray segments** ("Optical Axis 2", the promoted chief ray) draw
the reflected branch. But those segments only exist when rays are traced and a chief ray is
promoted; with rays off, or an untraced preview, the +X branch has **no axis line at all** —
the incoming guide stops dead at the mirror and nothing continues it.

## Fix — draw the outgoing guide from the fold point along the folded axis

`_folded_reflected_axis_guide_record(bounds, fold_point_z)` returns a second
`dotted_global_guide` record for the reflected branch:

- gated to a **single** promoted-mirror fold (`_folded_sequential_trace_rows` present with
  exactly one `Standard → Mirror` conversion); a CHAIN of folds zig-zags and is left to the
  traced segments, and an unfolded layout returns `None` (nothing changes);
- the folded axis direction is `R @ (0,0,1)` from the image row's fold transform
  (`_optical_axis_fold_world_transform_for_row`, the same rigid fold bugs/0185 uses for the
  lens/camera overlays), so it is exact and convention-free;
- it runs from the fold point `(0, 0, fold_point_z)` out to the scene extent (the farthest
  projection of the visible-bounds corners onto the folded axis).

For the AZ85 this draws a dotted guide from `(0, 0, 71.9)` along +X to `(361.7, 0, 71.9)` —
the reflected branch now always shows an optical-axis line, whether or not a chief ray is
traced. The incoming +Z guide and the traced chief-ray segments are unchanged.

## Verification (done)

`KrakenOS/UI/validate_open3d_ra_mirror_reflected_axis_guide.py` (standalone, display-free —
drives the real method against a stub inspector holding a headless editor):

1. the AZ85 single fold produces a dotted guide starting at the fold point, pointing along +X
   (folded axis), reaching the +X branch (far X ≈ 361.7);
2. a non-promoted-mirror layout (`flat_mirror_45_deg.py`) produces no guide;
3. a missing fold point produces no guide.

Standalone (NOT a penta phase). In-app eyeball still owed (headless cannot drive the VTK view).
