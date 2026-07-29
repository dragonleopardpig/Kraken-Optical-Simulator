# 0475 — "Reset Camera to Image Plane" zeroes the offset, so the camera lands on the LED

Flag `flag_20260729_184224_343` on build `94f336db`, scene
`attachment/machine_vision_AZ85_RA_Mirror_BS.py`:

> right click reset camera to image plane: endup camera misplaced to LED position.

with the follow-up that **the camera and sensor were already detached on load**, before
the right-click.

## Measured

Saved in the scene file:

    camera_step_placement_offset_xyz = [229.930, -0.0, -25.335]
    camera_step_axis_offset_xy       = [0.0, 0.0]

Captured in `state.json` AFTER the right-click:

    step_overlay_poses.camera.placement_offset_xyz = [0.0, 0.0, 0.0]
    step_actor_bounds.camera = [-35.0,  35.0, -35.0, 35.0,  -9.18, 64.45]
    step_actor_bounds.led    = [-88.0,  70.13, -70.89, 70.89,  5.60, 143.21]
    step_actor_bounds.lens   = [ 67.81, 127.0, -27.50, 27.50, 26.30, 81.30]

The action wiped x = 229.93 and left the body centred on x = 0 — inside the LED's
x = [-88, 70], with the lens (x = 67.8..127) and the sensor beyond it. That is the
reported "misplaced to LED position", and the 229.93 is exactly the sensor x quoted
in `seat_camera_on_sensor`'s own comment.

## Cause — a shared implementation that is wrong for one label

`glue_step_overlay_to_surrogate` was the whole action:

    self._set_step_axis_offset_xy(label, (0.0, 0.0))
    self._set_step_placement_offset_xyz(label, (0.0, 0.0, 0.0))

For a **lens** or an **LED** the zero-offset default *is* the auto-aligned station, so
clearing the drags is the entire job. A **camera** is different, and `seat_camera_on_sensor`
(bugs/0471, extended to 3-D by bugs/0473) says so in as many words:

> Registering or REPLACING a camera **resets its placement offset**, and the default seats
> the body on the nominal axis — on a folded scene that is nowhere near the sensor: the user
> replaced the camera and it landed at x = [-40, 40], **on top of the LED**, while the sensor
> sits at x = 229.9.

bugs/0473 fixed the *registration* and *replace* paths by seating afterwards. The right-click
menu item was never wired to it, so the identical "reset to a zero offset" hazard survived
behind a third door — and behind a label that promises the opposite.

### It also stranded the user there

After the reset the offsets are all zero, so the `already_glued` short-circuit

    already_glued = (all offsets within 1e-9 of zero)
    -> status "CAMERA STEP is already glued to its optical surrogate."; return False

refuses every retry. The one menu item named for the job reports success-by-no-op while the
camera sits on the LED. Recovery required the separate "Seat camera on the sensor" action.

## The detached-on-load half is a different, pre-existing thing

The saved z offset is **-25.335** — the exact value bugs/0471 measured and diagnosed:

> the body carries a PERSISTED `placement_offset_xyz` of z = -25.335 in the saved scene, which
> lands its centre on the sensor plane instead of its front face at -9.177

So the scene still carries the original 0471 mis-seating; the file was never re-seated after
that fix shipped. That is why the camera reads as detached from the sensor the moment it
loads. **Not** auto-corrected on load, deliberately: bugs/0471 established that the offset is
the user's own placement state and recomputing it silently would discard deliberate
positioning, which is why seating is an explicit action. bugs/0473 auto-seats on
*registration* (a fresh camera has no deliberate placement to lose); a saved scene does.
Fixing the action is what makes the scene recoverable — right-click ▸ Reset Camera to Image
Plane now actually seats it.

## Fix

`glue_step_overlay_to_surrogate("camera")` delegates to `_reset_camera_to_image_plane`, which
calls `seat_camera_on_sensor` inside one history capture (one undo step, bugs/0449).

The offsets are deliberately **not** cleared first. The seating is a RELATIVE correction
computed from the body's current bounds, so it lands the sensor on the image plane from any
starting offset; zeroing buys nothing and opens the window where a refusal (no traced
detector) leaves the body stranded at the origin — the bug itself. A refused seating now
leaves the camera exactly where it was.

Lens and LED are untouched: they still clear their drag offsets, and the `already_glued`
no-op still applies to them.

## Verified

Phase 77's guard (`validate_open3d_glue_step_to_surrogate`, display-free) covers this action
already and was strengthened rather than duplicated into a new phase:

    PASS A1-A3  a dragged lens still clears its offsets
    PASS B1-B2  a clean lens is still a no-op ("already glued")
    PASS C1     resetting the camera reports it moved
    PASS C2     it delegates to seat_camera_on_sensor (calls=['camera'])
    PASS C3     the offset is NOT zeroed (229.93, 0.0, -25.335 preserved for the seating)
    PASS C4     the untouched LED overlay keeps its offset (per-label)
    PASS C5     a refused seating reports no move
    PASS C6     a refused seating leaves the camera where it was, never at the origin

C3 and C5/C6 are the regression: section C previously asserted the camera's offsets were
cleared, i.e. the old guard encoded the bug.
