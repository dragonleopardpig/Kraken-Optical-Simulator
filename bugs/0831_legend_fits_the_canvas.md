# 0831 -- the illustration legend fits inside its canvas

`new_dialog_illustration.png`. Two things in one screenshot: the bugs/0830 fixes working,
and a new layout defect.

## Working

    Width 52.5   Height 1.05
    "Pre-filled from the inspected face 50 x 1 mm + 5% margin."
    From this view: Object FOV (semi) = 26.26

`26.26` is the corrected semi-diagonal of the 52.5 x 1.05 rectangle -- bugs/0830's fix,
replacing the 37.12 that assumed a square. And the part illustration is present in the
post-swap popup, wafer-thin with its inspected edge green.

## The defect

The single-line legend `green = inspected   grey = unreachable` spilled past BOTH canvas
borders. Measured against real Tk font metrics: **196 px in a 190 px canvas**.

Split into two lines -- `green = inspected` (91 px) and `grey = not imageable` (108 px),
each colour-matched to the faces it names -- and the drawing area reduced from 120 to 96 px
so the part cannot collide with them. Measured: the drawing now ends at y=78, the legend
sits at y=100 and 111, the canvas is 120.

## Worth recording

This is the third time in this session that a layout defect survived every headless check
and was caught the moment something was actually drawn:

* bugs/0828 -- the derivation chain measured 1246 px wide until it was rendered to a PNG;
* bugs/0830 -- the picture was missing from the popup the user was actually looking at;
* this one -- a caption 6 px wider than its own box.

Pure logic guards cannot see any of them. The guard here measures against **live Tk font
metrics** rather than a hardcoded width, so it tracks the theme instead of asserting a
number that happened to hold on one machine.

## Guard

`KrakenOS/UI/validate_open3d_0831_legend_fits_the_canvas.py`, penta phase 610. It asserts
the OLD legend overflowed, so the fix cannot be silently reverted to "it looked fine".
