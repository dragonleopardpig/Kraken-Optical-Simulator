# 0490 — Solve for Thickness never landed on the traced focus

> I think changes in WD and ID caused by dragging is natural, just let the user click Solve For
> Thickness will do, then the rays will re-trace correctly (or do they?)

They did not. And the cause is not the drag.

## The control that settled it

Clean scene, **nothing dragged**:

    as loaded                     ID 154.770   residual -7.3807
    after remove defocus          ID 162.151   residual -0.0000
    after Solve 23x23 (no drag)   ID 141.998   residual -5.5266     <-- the solve's own error
    + remove defocus again        ID 147.524   residual -0.0000

So the solve left ~5.5 mm of defocus from a focused start with nothing touched. The drag figures
decompose exactly against it: the mirror case's **−25.5266 = −5.5266 (the solve's own) + (−20.0)
(the drag's, passing straight through)**.

## What it actually is

Solving for the field the scene was **already at** took the residual −0.0000 → −7.3808 and put the
image distance back to **154.770 mm — the as-loaded value** — undoing a snap that had it at
162.151.

So the solve faithfully reproduces the prescription's **paraxial** image distance, and the traced
best focus is somewhere else. That gap is a real optical effect, not an arithmetic error: real-ray
aberration plus the glass paths through the BS cube and the prism. It varies with conjugate —
−7.38 mm at 1.15X, −5.53 at 23 × 23, −3.69 at 28 × 28.

**"Click Solve for Thickness" could therefore never focus, by construction.**

## Fix

Measured first: the snap costs **nothing** in field accuracy.

    cycle 1: after solve   residual -5.5266   achieved field 23.000
    cycle 1: after snap    residual -0.0000   achieved field 23.000
    cycle 2: after solve   residual -5.5266   achieved field 23.000     <-- the solve undoes it
    cycle 2: after snap    residual -0.0000   achieved field 23.000

One cycle lands both exactly, with no iteration — and a later solve undoes it again, which is why
the snap belongs INSIDE the solve rather than in the user's hands. `_finish_solve_on_traced_focus`
runs at the end of a successful conjugate solve.

Skipped when the sensor leg is pinned by hand (bugs/0489): the snap moves the detector along that
leg, so honouring the user's placement wins over auto-focusing, and the status line says so.

## Verified

The solve now lands in focus, idempotently, with the field exact:

    cycle 1..3: after solve   residual -0.0000   achieved field 23.000

and the workflow the user asked for works end to end:

    slide RA mirror -20 x   -0.0000 -> -20.0000 (drag) -> -0.0000 (solve), section 3 held at 83.270
    drag glued LED +20 z    -0.0000 -> +23.7662 (drag) -> -0.0000 (solve)

— focus recovered **and** the hand placement kept, bugs/0489's pin holding while the free section
absorbs.

## One guard generalised, not weakened

`validate_open3d_0470_remove_defocus_on_splitter` asserted that an explicit remove-defocus MOVES
the detector after a solve. It now legitimately has nothing to do, and refuses with "Detector
already at best focus". The defect 0470 was written for was a refusal saying *"best focus is not
computable for this layout"* on a splitter scene — so the invariant is that the snap is
**computable** and the scene ends at best focus, not that this particular call moves something.
The check now accepts "already at best focus" and still fails on "not computable"; the spot check
accepts "was already at the minimum".

0478, 0482, 0486, 0489, 0468 all PASS unchanged; 54/54 pytest.
