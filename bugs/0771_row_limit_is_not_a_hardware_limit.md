# 0771 -- a ROW that cannot absorb a move is not a MACHINE with no room

Flag `20260910_154535_461`:

> "FOV 20mm rejected. I see the image plane is in front of the sensor, and I think there is still
> adjustable distance available."

The user was right, and the simulator's own numbers agreed with them -- it just refused on the
wrong one.

## The measurement

`om05a_folded_80mm`, a 20 x 20 x 1 device (offset -15, correctly centred), FOV 20:

```
lens move needed        136.966 mm
leg gap (row 8)         130.889 mm   -> short by 6.077
mover's physical probe  155.793 mm   "room phys 155.7926 / station 130.8900"
```

And measuring the STEP bodies directly, with the lens slid as far as the row model permits:

```
lens at rest      min gap to the prism assembly  146.119 mm
lens moved -130   min gap to the prism assembly   19.851 mm
```

**19.85 mm of physical clearance remains** where the request needs 6.08. The machine can do it.

## What was wrong

The lens block moves as a THICKNESS PAIR, so row 8 would go to -6.08, and a negative row gap
slides every downstream row off the leg ([[reference_negative_gap_off_axis]]). Refusing is right.
Two things about HOW it refused were not:

1. **It said only "the gap would go negative"**, which reads as "there is no room" -- the exact
   opposite of what the user could see on screen. The message now names the shortfall, the
   physical room, and that the limit is the row partition rather than the hardware.
2. **It left `_lens_leg_slide_shortfall` unset.** bugs/0573 built a make-room path that slides
   the fold arm by the shortfall and retakes the move -- and it reads exactly that attribute. With
   it unset the path silently never ran. It is now recorded.

## What this does NOT yet fix

Recording the shortfall is necessary, not sufficient. Measured after the fix:
`slide_fold_arm_along_leg(7.077)` still returns `None`, because it needs a fold plan
(`_lens_leg_slide_plan()[2]`) and the om05a scenes are 0433-frozen -- the fold transform is None
on all of them ([[feedback_drag_is_thickness_constraint]]). So the make-room machinery is
unavailable across this whole scene family, and FOV 20 on a 20 mm device still refuses; it now
refuses with numbers that say the hardware has room, which is the honest state.

The real fix is to give the frozen family a way to re-partition the object leg -- the 6.08 mm has
to come from somewhere that is not a negative gap. That is scene-structure work and is NOT done.

## Guard

`KrakenOS/UI/validate_open3d_0771_row_limit_is_not_a_hardware_limit.py`, penta phase **555**:
the station-cap refusal records the shortfall, and it is the amount the ROW is short by (A); the
message names the shortfall and the physical room and says the limit is the partition (B); the
physical-room refusal above it is untouched, still structured and still naming the obstacle (C).
