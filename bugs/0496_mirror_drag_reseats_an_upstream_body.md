# 0496 — dragging the RA mirror re-seats the lens body, which is upstream of it

`flag_20260801_194857` — *"drag RA mirror to the left: Lens detached from surrogate."* (build
`865d3afc`). Its sibling `flag_20260801_194741` — *"LED drag up, down, left, right: all working
fine"* — confirms bugs/0494 and bugs/0495 in all four directions.

## Measured

Dragging the mirror left, against the preceding good state:

```
row 7 (RA mirror)          x -22.60          the drag
STEP camera                x -22.99          correct: the camera is on the mirror's arm
STEP lens                  x -22.99          WRONG
rows 1,2,4,5,6 (the lens surrogate)   +0.00  did not move
```

So the drawn lens barrel slid 23 mm off its own optical surfaces — "detached from surrogate". The
sensor and the branch detector followed the mirror correctly (both at x[190.6, 223.2]).

## Root cause

`_fold_slide_carry_before` captures body centres unconditionally:

```python
bodies = {}
for label in ("camera", "lens"):
    centre = self._step_body_world_center(label)
```

and `_fold_slide_carry_apply` then transforms **both** by the fold delta. That list was widened to
include the lens by the bugs/0456 / flag_20260731_192318 work, and rightly so *for a beam-splitter
slide*: there the lens genuinely is on the carried leg.

The mirror is different. Its emitted leg runs from the mirror to the sensor, so the carried set is
the sensor and the camera. The lens sits **upstream**, on the splitter's leg, and is not in
`carried` — yet it is re-seated anyway, because the body list never consults `carried`.

## Fix

A body rides the carry only when its world centre sits on the leg being moved. No label →
anchor-rows mapping was needed after all: `optical_axis_tree.point_on_emitted_leg` classifies a
world POINT with the SAME two primitives that pick the carried ROWS — `_active_segment_for_point`
for "which leg is this on" and `descendant_segment_ids` for "which legs does this fold carry" — so a
body and a row cannot disagree about whether they ride a given carry. A classification failure falls
back to carrying the body, so an error can never silently strand one.

Measured after, sliding the mirror −22.60 in x: rows 1,2,4,5,6 and the lens body all +0.00, while
row 7 −22.59, row 8 −22.60 and the camera −22.60.

## Guard

`validate_open3d_0496_carry_reseats_only_bodies_on_the_leg.py`, penta phase 401. The invariant is
asserted BOTH ways, because either half alone is satisfiable by cheating: a MIRROR slide must leave
the lens body and its surrogate rows alone *while* the mirror, sensor and camera all move (so B1 is
not "nothing happened"), and a SPLITTER slide must still carry the lens body and its rows together
— the bugs/0456 + bugs/0491 case that put the lens on the list, which this fix must not undo.
