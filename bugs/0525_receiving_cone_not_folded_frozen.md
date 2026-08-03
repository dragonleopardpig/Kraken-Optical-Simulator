# 0525 — the acceptance cone did not fold on a frozen scene

## Flag

`flag_20260803_154133` "acceptance cone is not folded" (frozen AZ85 at 55×55 — the cone ran
straight down the nominal axis through the splitter instead of creasing toward the lens).

## Root cause

The receiving-cone crease (0416–0421) reads
`_optical_axis_fold_world_transform_for_row(_lens_front_datum_row_index())` — the
pose-override transform, which the 0433 freeze bakes away (the same gate class as 0517's
camera frame and 0519's folded-solve gate). No transform → no crease → straight cone.

## Fix

`_emission_fold_transform_for_receiving_cone()` (layout_polyline_display): synthesize the
crease transform from the axis fold EMISSIONS (the same source the axes/launcher use) —
the FIRST fold from the object gives the hinge (its world origin on the nominal axis) and
the emitted leg; `R` maps the straight +Z onto that leg with `t = (I−R)·origin`, so the
crease's fixed-point recovery lands exactly on the fold origin (a least-norm shift along
the rotation axis is ⊥ the mirror-plane normal and cannot move the plane). No row-order
gate against the lens: on the AZ85 the BS fold ROW (3) sorts after the front-datum row (1)
even though it physically precedes the lens, and a fold the cone never reaches is a no-op
in the crease anyway. The inspector falls back to this transform when the pose-override
one is None; plain scenes keep the straight cone byte-identical.

Verified: the transform maps +Z → the +X lens leg with the hinge at the BS fold (z=53.8),
and the creased cone stops at the fold plane and extends onto the lens leg.

## Guard

`validate_open3d_0525_receiving_cone_folds_frozen.py` (penta phase 422).
