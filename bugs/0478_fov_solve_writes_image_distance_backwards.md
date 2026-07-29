# 0478 — the FOV solve moved the sensor the wrong way, so a solved field arrived defocused

Flag `flag_20260729_185356_727` on build `69426d5b`, scene
`attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

> changed to FOV 30x30, ray defocus at sensor.

The user confirmed they entered **no thickness constraint** in the FOV dialog, so this is the
plain unconstrained conjugate path.

## Measured

Reproduced bit-for-bit against the flag bundles:

    remove defocus   -> row 7 thickness 44.1193   residual  -0.0000 mm
    FOV 30 x 30      -> row 7 thickness 18.8600   residual +62.0798 mm
    remove defocus   -> row 7 thickness 80.9398   residual  +0.0002 mm

Row 7 is the promoted RA-mirror row; its thickness is the **mirror -> sensor** gap. The solve
is *designed* to leave the model in focus (`fov_solve` docstring: "The optical model is left
in focus and the caller owns the retrace"), so a 62 mm residual is a solver defect, not a
missing user step.

## Cause — the gap row's sign is inverted on a frozen folded scene

Two steps get there.

**1. The folded-aware branch is skipped.** `_apply_conjugate_pair` first tries
`_folded_conjugate_gaps_for_magnification`, which returns `None` because
`_folded_optical_solid_straight_equivalent_rows()` is `None` on a beam-splitter scene — the
same gate bugs/0470 documented. Control falls through to the plain branch, which writes
absolute prescription thicknesses:

    rows[obj_row].thickness = object_distance
    rows[img_row].thickness = image_distance          # img_row = len(rows)-2 = 7

**2. On this FROZEN scene that write is backwards.** Every row carries absolute `desp_*` with
`axis_move = 0` and `ScenePlacement.stay_put_freeze`; the beam after the RA mirror travels
global **-Z** while the station axis advances **+Z**. Sweeping the row confirms it exactly:

    rows[7].thickness   18.86    44.1193   51.50     80.9398
    WORLD mirror->sensor 84.14    58.8807   51.50     22.0602      == 103.0 - thickness

Derivative **-1**. The two frames agree only at the baked 51.5. So the solve asked for
-25.26 mm and the sensor moved +25.26 mm — and ~95% of the 62 mm residual is that sign, not
paraxial-vs-real error. (Setting the WORLD leg to the solved 18.86 gives a -2.35 mm residual,
the genuine BS-plate/prism residual bugs/0470 accepted.)

The object side is fine: its prescription delta equals its world delta, because the whole
downstream chain rides the station in +Z and the object row sits at world z = 0.

This is the same frame inversion already recorded at `paraxial_tools.py:2378-2384`: the scan
measures along the detector NORMAL while the consumer works in the cumulative-z / gap frame,
"which runs the other way".

## Fix

`_apply_frozen_image_split` (bugs/0447) already places an image-side leg **correctly** on a
frozen scene: it re-bakes the mirror and sensor world centres along the measured `out_dir` and
carries the camera body. It was only reachable when the user ticked a leg-pin checkbox — never
from an unconstrained solve, which is exactly the case the user hit.

New `ParaxialToolsMixin.apply_image_distance_frozen_aware(image_distance)` routes the write
through it with `delta = 0` (the mirror stays put; only the sensor re-seats, which is what an
unconstrained conjugate solve wants). `_apply_conjugate_pair` calls it and falls back to the
original prescription write whenever it returns False — no image-side fold, not frozen, or
unreadable geometry — so straight and unfrozen scenes are untouched.

Ordering matters and is preserved: the object write runs FIRST, because prescription writes
shift stations and the frozen path re-bakes world centres, which must come last (bugs/0447).

## Verified

Same drive as the flag, after the fix:

    remove defocus   -> row 7 = 44.1193   world far leg 58.8807   residual  -0.0000 mm
    FOV 30 x 30      -> row 7 = 44.1193   world far leg 18.8600   residual  -2.3505 mm

The world leg now *is* the solved 18.86 mm, and the residual is the predicted -2.35 mm instead
of +62.08 mm. Row 7's thickness stays put because a frozen row is placed by `desp`, not by the
gap — correct for this scene.

Guard `KrakenOS/UI/validate_open3d_0478_fov_solve_frozen_image.py`, penta phase **386**:
A1-A4 the fallback contract (straight/unfrozen/degenerate inputs are refused, so those scenes
keep the original write), B1-B4 the frozen write puts the solved distance on the FAR leg with
`delta = 0`, C1-C3 the applier consults it and keeps the object write first, D1-D4 the real
scene — residual well inside the broken +62.08, and the world far leg equal to 18.86.

Solve/frozen phases 363, 364, 368, 379, 380, 381, 382, 385 all pass the gate.
