# 0833 -- the clearance walks see all real matter, and never report an absence

`flag_20260920_175110_525` asked *"is the lens hit the Edmund filter?"* It did, and nothing
warned. bugs/0832 fixed what pushed it there. This fixes why no one noticed.

## Two walks, one blind spot

Every obstacle walk in the swap/solve path counted only rows carrying a promoted
`advanced['Solid_3d_stl']`. The Filter 48-926 is an ordinary surrogate row:

    row 13  Filter 48-926   Standard   N-BK7   O50.8   1.0 mm   drawing on

Real glass, drawn as a solid plate, physically in the barrel's way -- and invisible to the
walk, which looked straight past it to RA mirror 2 forty millimetres further down the leg and
reported room the lens did not have.

The camera layer had the mirror image of the same fault. `_swap_camera_body_clearance_deficit`
assumed the obstacle was `rows[-2]`. On om05a that is `sensor standoff`, a plain air gap with
no body, so `_promoted_solid_world_bounds` returned None and the layer ended at

    "obstacle_bounds": null,
    "result": "0 mm: missing obstacle"

on **every** swap, for as long as the flags go back -- an absence dressed as a measurement,
returned as `0.0` to a caller that reads 0 as "already clear". The thing the camera can
actually hit, RA mirror 2, sat eight rows back and was never examined.

## Row order is not the repair

The first draft of this walked back from the sensor looking for the first row with a body. It
landed on `LED panel B` -- a promoted solid belonging to the illumination arm, at x -37.5..37.5
while the camera spans x -304..-234. om05a's row order is not spatial.

Measured, every candidate against the camera (leg `(0, -1, 0)`):

    row  1 First RA mirror A      sep -24.38   transverse overlap [False, True]
    row  5 Centre RA mirror A     sep -11.80   transverse overlap [False, True]
    row  7 RA mirror 1 (50 mm)    sep  11.49   transverse overlap [False, True]
    row 13 Filter 48-926          sep  11.09   transverse overlap [True,  True]   <- nearest
    row 15 RA mirror 2 (40 mm)    sep  16.44   transverse overlap [True,  True]
    row 21 LED panel A            sep   6.40   transverse overlap [False, True]
    row 22 LED panel B            sep   6.40   transverse overlap [False, True]

The illumination rows have the *smallest* separations along the leg and the camera can never
touch them. Only the transverse-overlap test tells them apart. That is exactly the recipe
bugs/0719 settled on for the lens, so both walks now use it: overlap on BOTH axes
perpendicular to the leg (0.5 mm tolerance), nearest face-to-face separation wins.

## What changed

* `_element_row_world_aabb` (new) -- the world AABB of an ordinary drawn element.
  **Glass is the discriminator**, not "is it drawn": a datum row draws a disc too, and
  bugs/0806 is explicit that the rear vertex datum's disc is a mount face the camera seats on,
  not matter. Air is not matter; N-BK7 is. Posed exactly as the DISPLAY poses it -- a
  SEQUENTIAL row gets its leg's fold, a WORLD row must not be folded twice. Measured while
  building it: folding om05a's WORLD-placed RA mirror 2 again put it at +124.5 instead of
  -269.1. Validated against the user's own capture: the Filter's transverse AABB comes out
  `(30.96, 81.76, -50.40, 0.40)`, the drawn actor bounds to 0.01 mm.
* `_lens_block_physical_room_mm` counts element rows as candidates.
* `_nearest_body_row_along_leg` / `_row_world_body_aabb` (new) -- the geometric picker, STL
  bounds first (bugs/0719: matches the RA-mirror-1 actor to 0.16 mm), then promotion
  metadata, then the element AABB.
* A clearance layer that could not run now says so in `_swap_clearance_note`, next to the ones
  that did. Silence there reads as "checked, and clear".

## Measured result

The lens's room toward the sensor, which the refusal banner quotes:

    PYRITE 45-85   obstacle RA mirror 2  ->  Filter 48-926   room 16.388 mm
    ELS-85 4.5V16K obstacle RA mirror 2  ->  Filter 48-926   room  0.271 mm

The camera layer reaches `result: "ok"` with `obstacle_center_source: "nearest_body_along_leg"`
instead of `"0 mm: missing obstacle"`.

## The physics question this answers

*"Is it correct that the PYRITE 85 mm won't hit the Edmund filter while the ELS-85 will, under
the same FOV?"* No -- not for the reason it looks like. Measured on a clean swap:

    lens             barrel   datum span   front over   REAR over   datum->filter   verdict
    PYRITE 45-85     47.800      39.909        4.680       3.212        21.600      clears 18.388
    ELS-85 4.5V16K   59.191      55.389       -0.046       3.849         6.120      clears  2.271

Their rear overhangs differ by 0.64 mm. What differs is the GAP, which the swap re-fits from
each lens's back focal distance: 21.600 mm against 6.120 mm. The ELS-85 starts with 3.5x less
room and still clears -- by 2.271 mm, of which only 0.271 mm is usable once the 2 mm mechanical
clearance is charged. It took bugs/0832's 0.99 mm axial creep plus the FOV solve sliding the
lens down its leg to consume that. The ELS-85 is not too long; it is operating on a quarter of
a millimetre of margin, which is now measured and reported instead of invisible.

## Guard

`KrakenOS/UI/validate_open3d_0833_clearance_sees_all_real_matter.py`, penta phase 612. It
asserts the STL-only rule really did name RA mirror 2 here, and that a row-order walk really
does land on LED panel B, so neither regression can pass unnoticed.
