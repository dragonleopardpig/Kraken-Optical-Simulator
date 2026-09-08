# 0749 -- changing the lens gap SUM drags every row after it (arm B included)

Flags `20260908_094631_423` ("image plane is still detached ... still shifted side way from
centre") and `20260908_094814_180` ("seems like the previous flag is caused by this hay wired prism
assembly. Both big RA mirror is not aligned as well"). The user was right on both counts, and the
cause was bugs/0748 -- my own change.

## What happened

bugs/0748 set the lens sliding-gap sum from 148.4000 to 156.9400 mm to put the Gaussian focus on a
54 mm device. Rows 8 and 13 are the two gaps bracketing the lens block. **Every row after them in
the list inherits the change through its station** -- and rows 17-23 are the arm-B block (First RA
mirror B, BS cube B, Centre RA mirror B, both far halves, both LED panels), which must stay a mirror
image of arm A about the split plane z = -25.

| pair | before (sum 148.4000) | after (sum 156.9400) |
|---|---|---|
| BS cube A / B, z_a + z_b | **-50.000** | **-41.460** |
| BS cube B | -57.25 | -48.71 (+8.54) |
| LED panel A / B | 4.95 / -54.95 | 13.49 / -46.41 (both +8.54) |

Arm A stayed put, arm B slid 8.54 mm. That is the "haywire prism assembly", and the misaligned
mirrors, and the sideways-shifted image plane -- one cause, three symptoms.

The bugs/0745 self-check caught it in the user's own screenshot before I did:

    MODEL MISMATCH: the first order says -73.39 mm and the traced rays say -68.51 mm
    (+4.874 mm apart) -- the drawn image plane is the measured one

## The rule

**The gap SUM must stay invariant.** That is exactly why the bugs/0719 FOV solve moves a thickness
PAIR -- `rows[front-1] += d` and `rows[rear] -= d` -- rather than a single gap: the pair changes
where the lens sits while leaving every downstream station, and therefore the whole camera side and
arm B, exactly where it was. My manual edit changed the sum and broke that invariant.

So a genuine TRACK change on this scene is not a two-row edit. It needs the arm-B block's `desp_z`
compensated by the same amount (or a restructure so arm B is not downstream of the lens in row
order). Not attempted -- it should be designed, not patched.

## Reverted

`om05a_folded_80mm.py` restored to the 148.4000 mm sum. Verified after:

* BS cube, centre mirror and LED pairs all back to **z_a + z_b = -50.000** exactly
* 30 mm device: paraxial -54.848 vs traced -54.898, **0.049 mm** apart (no MODEL MISMATCH)
* station sum 413.760 vs traced path 414.026, **0.266 mm**

The deliverable range is 17-56 mm and the Gaussian focus sits at 51.26 mm, as it did before 0748.

## What bugs/0748 still gets right

The physics in that document stands: the required track spans 71.5 mm over a 20-54 mm range against
a ~0.15 mm depth of focus, the focusing sizes come as a reciprocal pair d1*d2 = 481.5 mm^2, and a
full-range in-focus system needs a ~71.5 mm focus axis on the camera or stage. Only the two-row
implementation of the track change was wrong.
