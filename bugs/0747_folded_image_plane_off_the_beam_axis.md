# 0747 -- the folded image plane sat off the beam axis inside its leg

Flag `20260908_073125_158`: "30mm device size still defocus at sensor." and, on the same render,
"the image plane still shifted in Y-direction, off center."

Two separate things, and only one of them was a defect.

## Not a defect: 30 mm does not focus on this build

Measured on `om05a_folded_80mm.py` after bugs/0745:

| long side | residual |
|---|---|
| 30 mm | -54.85 mm |
| 46 mm | -15.73 mm |
| 50 mm | -3.86 mm |
| 54 mm | +8.48 mm |

The track focuses at about **51 mm**. A 30 mm field leaves the image ~55 mm in front of the sensor,
and no lens move changes that -- the conjugates are fixed once the magnification is chosen. The
banner says so, and after bugs/0745 the paraxial and traced readouts finally agree (the user's
screenshot: HUD 64.85 mm, image plane 64.9 mm).

## The defect: off the axis INSIDE the folded leg

bugs/0742 re-centred the drawn plane on the beam, but only when the walk crossed NO fold. At a
-54.9 mm offset the walk-back crosses RA mirror 2, so the plane is placed around the corner up the
incoming leg (bugs/0729, which the user asked for). In that branch the raw walked point was kept --
and it carries the axial ray's own landing error:

| | before | after |
|---|---|---|
| focus centre | `[272.294, 52.661, -32.517]` | `[271.933, 52.661, -25.024]` |
| off the sensor's z | **7.517 mm** | **0.024 mm** |
| off the sensor's x | 0.339 mm | 0.700 mm |

Fix: translate the axial ray's polyline so it LANDS on the sensor centre before walking it back.
A rigid translation preserves the polyline's shape, so the fold handling of bugs/0729 is untouched,
but the ray's landing error (3.335 mm here) no longer propagates into the plane's position.

Verified: the unfolded case still centres exactly (om05a_folded_80mm at a -3.826 mm offset gives
lateral 0.000 mm, tilt 0.0000 deg), and penta 527, 528, 532, 538, 540 all pass.

## Still open

The remaining ~54 mm of Y displacement is the FOLD, not an error: the waist is 54.9 mm back along
the beam and the last straight leg into the sensor is shorter than that, so it genuinely sits up
the incoming leg. That is bugs/0729's behaviour, requested by the user ("I think it skip the fold.
It should be located somewhere near the Filter"). Whether a waist that lies BEYOND a fold would
read better drawn on the sensor's own axis -- unfolded, with a note -- is a product question, not
a correctness one.
