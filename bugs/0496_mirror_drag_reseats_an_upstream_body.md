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

## Fix (not yet written)

Re-seat a body only when the rows it is bolted to are in the carried set. `carried` is already
computed in `_fold_slide_carry_before` (`axis_tree.rows_on_emitted_leg`); what is missing is a
label → anchor-rows mapping. There is no helper for this today — `_step_body_world_center` reads a
body's bounds, and nothing maps "lens" back to rows 1,2,4,5,6.

The guard should assert the invariant both ways on one scene: sliding the SPLITTER carries the lens
body *and* its surrogate rows together, and sliding the MIRROR carries the camera and sensor while
leaving the lens body and its surrogate rows alone.
