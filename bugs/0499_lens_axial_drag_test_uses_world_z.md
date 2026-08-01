# 0499 — a lens drag along a FOLDED optical axis is treated as lateral, so the optics stay behind

`flag_20260801_210453` (build `e78c7c59`) — *"clicked glue STEP to surrogate, drag right, it is
still detached."*

## The glue worked; the drag undid it

The recorded state is the as-loaded scene in every respect **except** the lens: rows 1/6/7/8, both
axis records, the LED and camera overlays are all at their original values. Only the lens differs —
overlay offset x **119.26** against the reference **97.406**, body at x[89.66, 148.85].

Read in the order the user wrote it — glue, *then* drag right — that is 97.406 restored by the glue
(bugs/0497 working) plus a 21.85 mm drag. The complaint is that the drag detaches it again: the body
moves and its optical surrogate does not follow.

## Root cause

`translate_step_overlay` decides axial-vs-lateral for a lens with

```python
if label == "lens" and overlay_on_axis and abs(float(delta[2])) > 1e-9:
```

`delta[2]` is the **world Z** component. The intent is documented right there: an AXIAL drag
redirects into the gap before the front datum so "every lens row and the glued rear datum move
together ... the optics respond to the new lens position", while "lateral drag still only centres
the body".

That test is only the optical axis on an **unfolded** scene. Here the lens sits on the beam
splitter's +X leg, so dragging along its own optical axis produces `delta = (21.85, 0, 0)` and
`delta[2] == 0`. The drag is classified lateral, the optics are left behind, and the body slides off
its surrogate — exactly "still detached".

The same world-axis assumption is what bugs/0475 fixed for the camera and bugs/0497 for the lens
placement. This is the third instance, in the drag classifier.

## Attempted, and REVERTED — there is a second, deeper blocker

Both world-axis assumptions were generalised and measured, and the result was worse than the bug:

* the inner test `abs(delta[2]) > 1e-9` → project onto the surrogate's leg direction;
* the outer gate `overlay_on_axis`, which requires the placement offset's X/Y ≈ 0 — i.e. "on the
  nominal +Z line". The AZ85 lens offset is [97.41, 0, -106.43] **because** it rides the +X leg, so
  that gate was False and the axial branch had never run at all on this scene. Replaced with a
  geometric test: is the body's centre on the line through its own datums?

With both fixed the redirect fires and the optics do follow — **in the wrong direction**. Dragging
+X 20 moved the body *and* both datums +Z 20:

```
before   body [97.41, 0, 53.8]   front datum [71.66, 0, 53.8]
+X 20 -> body [97.41, 0, 73.8]   front datum [71.66, 0, 73.8]
```

Because the redirect rewrites `rows[lens_front_idx - 1].thickness`, and on this layout the row
order is `0 Object, 1 Front datum, 2 BB1, 3 BS, 4 Aperture, 5 BB2, 6 Rear datum, 7 mirror, 8 Image`
— the lens datums **bracket the beam splitter in index order**. So "the row before the front datum"
is the Object gap: section 1, the object→BS distance, which moves the fold point and therefore the
whole leg vertically. Dragging the lens right must change section 2 (BS→lens), not section 1.

Index order does not follow optical order along the legs once a scene is folded — the same family
as bugs/0448's backwards frozen gaps. Reverted: a drag that silently changes the working distance
is worse than one that does nothing.

## Fix — still not written

Project the drag onto the lens's ACTUAL optical axis instead of testing world Z: the surrogate's
front and rear datum rows already give that direction (`_lens_datum_row_index("front"/"rear")` plus
`_fold_carry_row_world_pose`, both used by bugs/0497), so

```
axial   = dot(delta, leg_dir)      # redirect into the gap before the front datum, as today
lateral = delta - axial * leg_dir  # centre the body, as today
```

On an unfolded scene `leg_dir` is +Z and this reduces to the present behaviour exactly — the same
reduction test bugs/0497 used, and the check that it is a generalisation rather than a new rule.

### The missing primitive — BUILT

`optical_axis_tree.leg_upstream_neighbour(tree, snaps, row)` and `rows_along_leg(snaps, segment)`,
from the same tree the rest of the fold work uses, so a caller cannot disagree with
`rows_on_emitted_leg` (bugs/0485) or `point_on_emitted_leg` (bugs/0496) about what is on a leg.

Measured on this scene — the three that differ from `rows[i-1]` are the whole point:

```
leg axis:root      optical order [0, 3]            row 1 -> upstream 3 (the SPLITTER), index says 0
leg axis:fold:3    optical order [1, 2, 4, 5, 6]   row 3 -> upstream 0,                index says 2
leg axis:fold:7    optical order [7, 8]            row 4 -> upstream 2,                index says 3
```

Two traps it had to handle: a folder sits at `s = 0` on the leg **it emits**, so the naive
"return the segment's `source_row`" fallback made row 7 its own upstream neighbour; the lookup now
walks to the parent leg and takes the last row before the branch point. And on an unfolded scene it
collapses to plain index order, which is the reduction test that it generalises rather than replaces.

Guard: `validate_open3d_0499_leg_neighbour_lookup.py`, penta phase 403 (display-free).

### Fixed

Repointing the redirect at the leg neighbour turned out NOT to be the answer, and the lookup is what
showed why. On a folded leg no thickness controls position along that leg:

```
+10 on rows[3].thickness (the true leg-upstream neighbour) -> lens moves [0, 0,   0]
+10 on rows[0].thickness (what the old code picked)        -> lens moves [0, 0, +10]
```

Positions along a fold leg live in `desp`. So the redirect now slides a folded leg the way the fold
carry does — it translates the surrogate's own rows (`rows_along_leg` between the two datums, so the
set cannot disagree with `rows_on_emitted_leg`). The thickness redirect stays for the unfolded case,
where it works and is the existing behaviour.

One more trap on the way: having moved the rows, subtracting the axial part from the body's own
placement left the optics sliding +20 while the barrel stood still — detached the other way round. A
STEP body is anchored to its row's z-STATION, not to `desp` (bugs/0456, which is why the fold carry
re-seats bodies explicitly), so the body needs the FULL delta.

Measured after, dragging +X 20:

```
body +20   front datum +20   rear datum +20     together -- still attached
object, splitter, mirror, image  unchanged
section 1 (obj->BS)   54.459 -> 54.459          the working distance holds
section 2 (BS->lens)  71.785 -> 91.784          +20
section 3 (lens->mir) 103.270 -> 83.270         -20
```

Guard: `validate_open3d_0499_lens_slides_along_its_leg.py`, penta phase 404.

The two helpers written for the attempt — `_lens_surrogate_axis_direction` and
`_lens_body_centred_on_surrogate_axis` — were reverted with it, but both are correct and should be
restored alongside the redirect change.

## Guard it needs

Drag the lens along its leg on the FOLDED scene and assert the surrogate rows follow, so body and
optics stay together; drag perpendicular and assert only the body centres; and assert the unfolded
scene is unchanged.

## Recurrence, resolved elsewhere

`flag_20260801_220951` / `flag_20260801_221613` re-reported "detached after dragging right" on a
build that CONTAINS this fix. Event replay proved the redirect fired and carried the rows both
times — what failed was the DRAWING (the leg-slide branch never set the bugs/0493 rebuild marker,
so nothing repainted the carried rows) and the GLUE (which restored an absolute pose onto the slid
surrogate). Both are bugs/0503.
