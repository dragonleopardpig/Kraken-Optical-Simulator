# 0427 — Resize Beam Splitter must retain the gizmo orientation + placement

**User:**
> "after right click add BS plate to LED, I orient and place it using gizmo, then I resize it, my
> placement and orientation back to its original. It should retain my orientation and placement after
> resize."

## Root cause

The 0423 resize goes through `replace_promoted_optical_solid_step` →
`unpromote_optical_solid_to_overlay`. That restore reads the overlay rotation from the **promotion-time**
`StepOverlayPromotion["step_rotation_deg"]` — the rotation the BS had *when it was first added* — **not**
the row's current `tilt_x/y/z`, which is what the placement/rotate gizmo updates
(`rotate_scene_row_pose_world_axis`). So a manual gizmo re-orientation was thrown away on resize and the
BS snapped back to its original LED-matching orientation. (It did carry the current transverse `desp`, but
not the tilt.)

## Fix

`resize_beam_splitter` now **captures the current pose** (`tilt_x/y/z` + `desp_x/y`) from the promoted row
**before** the regenerate+replace, and **re-applies** it to the replacement row afterward (then
`_sync_table()`), so the resized BS keeps the orientation and placement the user set with the gizmo. The
parametric solid regenerates in template orientation, so re-applying the captured tilt restores the exact
displayed orientation.

## Verification (`validate_open3d_bs_resize`, penta phase 341 — extended)

Display-free; the RESIZE-WIRING check now also requires:

| token | asserts |
|---|---|
| `old_pose` / `tilt_x` capture | the current tilt + desp are captured before the replace |
| `setattr(new_row, attr, …)` | the captured pose is re-applied to the replacement row |

4/4 pass (phase 341 unchanged pass).

## Files

- `KrakenOS/UI/services/scene_placement_commands.py` — `resize_beam_splitter` captures + re-applies the pose.
- `KrakenOS/UI/validate_open3d_bs_resize.py` — guard extended.

## In-app eyeball still owed

Add a BS to the LED → orient + place it with the gizmo → Resize Beam Splitter… (change thickness/side) →
it must keep the orientation and placement, only the size changing. (If the *axial* along-axis position
still shifts — `unpromote` carries transverse `desp` but the axial re-place has a known "may need a nudge"
caveat — flag it and I'll capture the axial station too.)
