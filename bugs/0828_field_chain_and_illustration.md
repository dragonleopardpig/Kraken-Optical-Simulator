# 0828 -- the device dialog shows the derivation, and a picture of the part

Three numbers confused the user inside one session, and **every one was arithmetically
correct**:

* the device stayed 20 mm after they typed `50x50` -- they had edited **Required FOV**,
  and the dialog never said which of its two numbers they were changing;
* the scene drew `FOV 21.0x8.3` while the banner said `delivering 21 x 21` -- the
  per-FACE field and the whole-sensor field, two quantities wearing one word;
* a swap pre-filled `59.3284` -- sensor 23.04 mm / |m| 0.3883, the object field that
  would exactly fill the sensor at the magnification in force right then. Stated nowhere.

None is an error. Each is **a number shown without its parent**. So the fix is not another
field: every line now names what it was derived from.

    Part               20 x 20 x 1 mm       (L x W x T, as you set it)
    Inspected faces    2 x (L x T) = 20 x 1 (front + its mirror on the back, W apart)
    Required FOV       21 x 21 mm           (your number -- authoritative, no margin)
    Across the sensor  21.0027 x 21.0027    (sensor 23.04 / |m| 1.097; the WHOLE sensor)
    Reaching one face  21 x 8.3 mm          (MEASURED from traced coverage)

The 8.3 stops being mysterious: the inspected face is a **1 mm edge**.

## The illustration (the user's request)

A canvas beside the chain draws the part at **true proportions** with the two inspected
faces green and the unreachable ones grey. A 20 x 20 x 1 device renders as a 100 px edge
against a 5 px thickness -- a wafer -- so the thin field explains itself before any number
is read. A cube draws as a cube: the picture follows the real shape rather than being an
icon.

## No face selector, and it stays gone

bugs/0768 removed that dropdown at the user's request: *"even the Inspected Face
dropdown, I don't think we need this"*. The split field images the front face and its
mirror on the back, so it was never a choice. This bug **re-proposed** a greyed-out
selector before checking, and the user had to be asked to confirm it stay removed. The
guard now pins the absence of the widget.

The user also supplied the physics the dialog should have encoded all along: *"as you see
from the prism + RA mirror + lens + another RA mirror setup, it can never image the top
face 20x20 (and the bottom face as well). The ray tracing physics should have told you all
this."* The fold turns sideways into the lens, so only edge faces are reachable -- which is
why the picture greys top and bottom rather than offering them.

## Three mistakes made while building this, all caught

1. **The module reproduced the bug it exists to prevent.** The first draft computed the
   per-face row from `sensor / |m|` and labelled it "per face" -- exactly the
   `21 x 21` vs `21 x 8.3` conflation. The per-face field CANNOT be computed there; it is
   measured and passed in, now enforced by the signature. With nothing measured the row is
   absent rather than invented.
2. **The rendered dialog measured 1246 px wide** and would have been unusable. Caught only
   by rendering it to a PNG and looking; shortened and wrapped to 624 px.
3. **Two guard checks were wrong, not the code.** `F2` measured the bounding box of an
   isometric face -- a sheared parallelogram, whose bbox height is the projection's skew,
   not the part's thickness (it read 55 px of "thickness" on a 1 mm wafer). Measuring the
   EDGES gives 20:1 for the wafer and 1:1 for a cube. `G2` failed on its own explanatory
   comment, since the source mentions "Inspected Face" only in the note recording its
   removal -- a guard that fails on its explanation invites deleting the explanation.

## Guard

`KrakenOS/UI/validate_open3d_0828_field_chain_and_illustration.py`, penta phase 607.
