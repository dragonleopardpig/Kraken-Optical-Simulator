# 0829 -- the Object-plane FOV popup pre-fills from the FACE, not the sensor

User, showing `popup.png`: *"is this pop up correct?"*

## Every number in it was correct

| shown | is |
|---|---|
| Width = Height = 59.3284 | sensor 23.04 mm / \|m\| 0.38835 |
| "Object FOV (semi) = 41.95" | that square's semi-DIAGONAL: 59.3284 x sqrt(2) / 2 = 41.9515 |
| legs 9 + 6.85 | = 15.85, the stated total |

Both FOV numbers agree with each other -- one is the square's side, the other its
circumscribed radius. **This is not an arithmetic fix.**

## It was the wrong shape for the bench

The inspected faces on om05a are **20 x 1 mm edges**. The popup offered a square
**59.33 x 59.33** -- **3x the face length and 59x its thickness** -- and described the
field as a circle of semi-diameter 41.95. A centre prism and two RA mirrors fold sideways
into the lens, so each face receives a strip; a square field is not something the machine
can deliver.

And *"Fill just one box -- the other is derived from the sensor aspect"* actively FORCED
that square: it ties height to the **sensor** when the constraint that matters is the
**face**.

Same defect class as bugs/0828 -- a number with no stated parent, and no connection to the
part being inspected -- in the dialog that actually produced the user's original 59.3284
question. 0828 fixed the Inspection Part dialog; this popup never got the treatment.

## Fix

When a device is enabled, the object popup pre-fills from the inspected face + 5% --
**the same target `solve_fov_to_inspection_face` already uses**, so the popup and the
solve stop offering different fields. On the user's bench that is `21 x 1.05` rather than
`59.33 x 59.33`.

The grey note now states which parent is in force:

    device on   ->  "Pre-filled from the inspected face 20 x 1 mm + 5% margin."
    no device   ->  "pre-filled from sensor 23.04 x 23.04 mm / |m| 0.3883 = ... the field
                     that exactly fills the sensor as the scene stands"

With no device the previous behaviour is unchanged -- it just explains itself now.

## Note for the reader

The illustration added in bugs/0828 lives in the **Inspection Part** dialog (right-click
the Device -> "Device size / part settings..."), NOT in this popup. The user reasonably
expected to see it here after being told "the dialog" had gained a picture; they are two
different dialogs and the earlier write-up did not distinguish them.

## Guard

`KrakenOS/UI/validate_open3d_0829_fov_popup_prefills_from_the_face.py`, penta phase 608.
It asserts the popup's ORIGINAL numbers were self-consistent, so a later reader cannot
mistake this for an arithmetic correction.
