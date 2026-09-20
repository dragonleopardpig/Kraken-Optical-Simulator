# 0836 -- the lens room is measured where the bodies are drawn

Found while surveying for Scene IR Phase D, not from a flag. It is a live hole in the
crash-avoidance path.

## The defect

`_lens_leg_room_to_fold` read both endpoints through `scene_ir.world_frame` and projected them
on the slide plan's direction. On `om05a_folded` that is three frames in one subtraction:

    block_end   (row 12, rear datum)    [   0.000,  0.000, 314.920]   straight-equivalent
    fold_centre (row 15, RA mirror 2)   [-269.137, 56.313, -25.000]   already its folded centre
    leg unit    (the slide plan)        [0, 0, 1]                     pre-fold; drawn leg is -x

    -> "room" = -378.42 mm

Both rows tag `sequential`. The space tag agreed on both and settled nothing.

The barrel-overhang term -- bugs/0583 added it precisely to stop the lens entering the prism --
then took a folded-world bound away from a pre-fold coordinate, `2.366 - 314.920`, and
`max(0, ...)` reported the barrel as not overhanging at all.

And the quieter half: handed the plan's leg direction, `_lens_block_physical_room_mm` found
**no obstacle at all** -- `method: 'none'`, `room_phys: None` -- on a bench whose Filter 48-926
is 16 mm away. Called without that argument the same function names the Filter correctly. So
the physical-room measure was inert on exactly the path the frozen-leg scenes use. That is the
third safety check in one day that silently did not run (`"0 mm: missing obstacle"`,
`method: 'none'`, and this).

It does not wrongly REFUSE: `translate_lens_block_along_leg` only consults the -378 number when
`amount > 0`, and the solves that matter move the lens negative, so `room` stays `None`.
Inert, not wrong -- which is why nothing ever surfaced it.

## The rule is measured, and two derivations were wrong first

Printed for all 25 rows against the pose audit's DRAWN column:

* **The placement SPACE does not decide it.** Every row tags `sequential`, RA mirror 2
  included, whose `desp` is already its folded centre.
* **Applying `_optical_axis_fold_world_transform_for_row` does not either.** That transform is
  `F(v) = C + R (v - S)` with `S` the row's straight-axis STATION, so it is valid only where
  the prescription IS `[0, 0, z]`. Rows 3, 5, 7, 8, 15 and 16-22 carry a decentre and it
  mis-places every one: RA mirror 2 lands at `[124.49, 0, 244.14]` instead of
  `[-269.14, 56.31, -25.0]`, and the front datum's `desp_x = -8.78` (bugs/0832's inert marker)
  arrives in world as a Z offset, `-33.78` where the scene draws `-25.0`.
* **The OUTPUT-PORT pose override reproduces DRAWN on every row that has one** -- all 23 on
  that bench, to the 0.08 mm an actor's bbox centre differs from its surface.

So a row with an override is drawn AT that override; a row without one is drawn where its own
numbers put it. No fold is applied at all, which is how both derivations above could disagree
with the display without anything noticing.

I shipped derivation 1 inside bugs/0833 yesterday and it worked only because the single row it
touches happens to be a plain sequential one. Derivation 2 was written today, was a no-op
(`world_frame` returns `placement_space`, not the `frame` tag), and REGRESSED 0833 --
`_element_row_world_aabb` started returning an unfolded AABB. The probe caught it; reasoning
did not. What made the difference was printing all 25 rows instead of thinking about two.

## The fix

`scene_ir.drawn_world_frame()` and `drawn_leg_unit()`: one place that answers "where is this
row drawn" and "which way does its leg run on screen", both resolving the output-port override.
Read by `_lens_leg_room_to_fold`, `_lens_block_physical_room_mm` (for a caller-supplied leg
unit) and `_element_row_world_aabb`, whose hand-written fold branch is deleted in favour of it.

`except Exception: return None` in the room measure meant "no fold ahead, unbounded leg" to
every caller -- an exception read as physics on the crash-avoidance path. It now records what
it swallowed in `_lens_leg_room_unmeasured`.

## Measured result

    drawn_world_frame(RA mirror 2)          [124.49, 0, 244.14]  ->  [-269.14, 56.31, -25.00]
    drawn_leg_unit(rear datum, (0,0,1))              [0, 0, 1]   ->  [-1, 0, 0]
    _lens_leg_room_to_fold                          -378.42 mm   ->  +0.6366 mm
    room with the plan's leg_unit            None, method none   ->  Filter 48-926, 16.388 mm
    room without leg_unit                    Filter, 16.388 mm   ->  unchanged (they agree now)
    _element_row_world_aabb(Filter)                              ->  unchanged from bugs/0833

The `+0.6366 mm` has an independent check: with the override rule the rear datum draws at
`-224.79` and the lens mesh spans `-228.00 .. -180.20`, so the barrel overhangs its datum by
`3.21 mm` -- the same 3.212 mm measured hours earlier by a completely different route (seating
the STEP through `_cad_mesh_aligned_to_optical_axis` and projecting on the surrogate axis).

## What this changes about Phase D

Phase D is not "move `_optical_axis_fold_world_transform_for_row` into `lower()`" -- that
transform is the wrong mechanism for 8 of the 23 override rows. Phase D is **`lower()` resolves
the output-port pose override**, which is a different and more contained change. `world_frame`
then returns what `drawn_world_frame` returns and every caller drops back to it.

## Guard

`KrakenOS/UI/validate_open3d_0836_room_measured_in_the_drawn_frame.py`, penta phase 615. It
pins BOTH rejected derivations as well as the fix: that the override centre reproduces DRAWN on
all 23 rows, that re-folding the prescription really does fling RA mirror 2 to `[124.5, 0, 244.1]`,
that the old arithmetic really did read -378.42, and that bugs/0833's AABB is untouched.
