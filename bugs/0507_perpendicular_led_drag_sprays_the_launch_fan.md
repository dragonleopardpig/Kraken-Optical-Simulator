# 0507 — after a perpendicular (housing-seat) LED drag, the launch fan sprays: "broken rays"

`flag_20260802_112852` (build `0bce2ffe`) — *"dragged down LED, some broken rays are shown."*
No recording (flag pressed without one); REPRODUCED headlessly:
`translate_step_overlay("led", (0, 0, +14.25))` on the AZ85 scene, then a full refresh — the
snapshot shows the same broad scraggly fan between the box exit and the lens
(scratchpad probe `probe_perp_shot.py`, image `perp_after.png`).

## What is CORRECT in the flagged state (verified from state.json)

The perpendicular drag moved the BS housing +14.25 in z; the fold point slid +14.25 ALONG the
incoming axis (physics: the incoming ray meets the moved diagonal later), and the bugs/0485
fold-slide carry moved the WHOLE arm with it: split axis, lens rows/body, mirror, camera and
Image row all at +14.25, image still exactly on the sensor (row 8 cz 9.17 = -5.08 + 14.25).
Geometry, followers (0505 E2) and the object anchor (0505 E1) are all consistent.

## The defect

The imaging launcher aims its pupil disk at ``aim_z`` from
``_launch_reference_entrance_pupil_z`` -- the FIRST-ORDER reduced distance to the entrance
pupil. The fold point moving +14.25 ALONG the incoming axis lengthens the reduced path
object -> pupil by +14.25, but the first-order reference does not track the BS row's desp_z, so
the fan converges 14.25 too early and sprays after the fold: the flagged "broken rays"
(landed 67 vs the ~129 baseline; many strays at wild angles, plus bugs/diag_1x_cube-style
no-stop divergers made visible).

This is the REDUCED-DISTANCE half of the universal first-order reference
(bugs/0505 closed the LATERAL half with `axis_root_origin`): the launch aim must be computed
against the axis tree's actual reduced path (fold points from `axis_fold_emissions`), not the
nominal station arithmetic.

## Where to fix

`_launch_reference_entrance_pupil_z` (and whatever first-order station walk feeds it): measure
the object -> pupil distance along the ACTUAL root leg -- object anchor to the (moved) fold
point, then along the emitted leg -- i.e. consume the same emissions the axes use. The 0505
guard's E-section pattern (system rebuild per step) is the harness; assert landed-count parity
(~129-class, not 67) after a perpendicular housing drag, plus a tight-fan geometric check
(ray direction spread at the box exit).

## Status

Root-caused to the aim depth; NOT fixed yet. Repro script + snapshot exist; fix next session.
