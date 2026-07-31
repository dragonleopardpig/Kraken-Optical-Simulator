# 0489 — a hand-placed folder is a constraint, and the solve was discarding it

> dragging any of the components will at least fix one of the 4 section thickness constraints
> (dragging lens will fix 2), so the solver should take into account of the constraint introduce
> by the user by dragging. It is equivalent to changing the FOV in the pop up dialog and click
> thickness constraint.

## Measured

Slide the RA mirror 20 mm along its leg — setting section 3 to 83.270 mm — then Solve for
Thickness 23 × 23:

    without the pin   section 3  83.270 -> 76.884 mm   drift -6.386   the solve moved it back
    with the pin      section 3  83.270 -> 83.270 mm   drift +0.000   section 4 absorbs (45.114 -> 38.728)

The solve was re-running its own default distribution — bugs/0482's 50:50 image share, bugs/0484's
hold of section 1 — which overwrites exactly what the drag just set.

## Which section a drag pins

It falls out of the split the folder belongs to. The object split's `near` is object → beam
splitter (section 1); the image split's `near` is lens rear → mirror (section 3). Pinning `near` —
the distance from the upstream element to the folder — is what makes *"it stays where I put it"*
true whatever the solve does to the total, because the sibling `far` absorbs the change. That is
the same policy bugs/0484 already chose for the object side.

A pure **rotation** pins nothing: it leaves the fold point, so no section length changed.

Pins are **session state**, cleared when a layout loads: a pin records "I put this here", which
belongs to the editing session rather than the prescription, and a scene must never arrive
silently over-constrained. Both sections of a split pinned is reported as over-constrained rather
than silently resolved.

## Scope — stated because it is easy to over-read

The pin governs **where things sit, not whether the system is in focus.** Residual defocus is a
property of the image TOTAL, which a pin does not change.

And the total is separately wrong. Control measurement, clean scene, **nothing dragged**:

    as loaded                     ID 154.770   residual -7.3807
    after remove defocus          ID 162.151   residual -0.0000
    after Solve 23x23 (no drag)   ID 141.998   residual -5.5266     <-- the solve's own error
    + remove defocus again        ID 147.524   residual -0.0000

So Solve for Thickness leaves ≈ −5.53 mm of defocus from a focused start with nothing touched.
The drag figures decompose exactly against it:

    slide RA mirror -20 x    -25.5266 = -5.5266 (the solve's own) + (-20.0) (the drag's, untouched)

Two distinct defects, and this bug fixes neither of them:

1. the solve does not land on the traced focus even on a clean scene (**open**);
2. the solve does not absorb a drag's change to the conjugate — the −20 passes straight through
   (**open**).

So *"drag, then click Solve for Thickness"* still does not return to focus. What this bug fixes is
narrower and worth having on its own: the solve no longer **moves the thing you just placed**.

## Verification

`KrakenOS/UI/validate_open3d_0489_drag_pins_a_section.py`, penta **phase 395**. Sections A (pin
beats the default; a far-pin honoured through the total; both pinned reported) and B (cleared on
load) are display-free; C drives the real scene both ways and asserts the drift is 0.000 with the
pin and −6.386 without.
