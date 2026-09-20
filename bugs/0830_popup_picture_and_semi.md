# 0830 -- the post-swap popup shows the part, and its semi-FOV follows the rectangle

User, twice: *"I am looking at the swap lens pop up now, I don't see device illustration."*

## The picture belongs here

That popup IS the post-swap prompt: `_prompt_fov_solve_after_swap` calls
`_open_quick_estimation_fov_popup("object")`. So it is where the FOV decision is actually
made -- and therefore where a picture of what is being inspected belongs. bugs/0828 gave
the illustration only to the Inspection Part dialog, and the earlier write-up said "the
dialog" without distinguishing the three that exist:

    Inspection Part dialog    device size / part settings   <- 0828 put the picture here
    Object-plane FOV popup    the field entry               <- 0829 fixed its prefill
    post-swap prompt          ...is the SAME popup          <- so this is where it was needed

The popup now draws the part at true proportions when a device is enabled, inspected faces
green and unreachable ones grey, beside the Width/Height boxes.

## A regression I introduced in 0829, caught by the user's screenshot

`new_dialog.png` shows the 0829 prefill working -- `52.5 x 1.05`, *"Pre-filled from the
inspected face 50 x 1 mm + 5% margin."* -- and, three lines down:

    From this view: Object FOV (semi) = 37.12

**Wrong.** 52.5 x 1.05 has semi-diagonal **26.255**. 37.12 is 52.5 x sqrt(2) / 2, the answer
for a 52.5 SQUARE.

`_fov_context` computed `semi = qe.horizontal_to_diagonal(w) / 2`, deriving the diagonal
from the WIDTH alone via the sensor aspect. That was correct while the two boxes were locked
to that aspect -- before 0829 the field was always square. Making the height face-derived
left this reading the width and inventing the height, and it said so 1.41x too large.

Fixed to measure the rectangle actually in the boxes (`hypot(w, h) / 2`), falling back to
the aspect conversion only when the height box is empty. For a square field the two agree
exactly, so the no-device path is unchanged -- 59.3284 square still reads 41.95.

## Worth recording

0829 changed what the boxes MEAN without checking what else read them. The guard now pins
both: the rectangle-derived semi, and that a square field still gives the old answer.
