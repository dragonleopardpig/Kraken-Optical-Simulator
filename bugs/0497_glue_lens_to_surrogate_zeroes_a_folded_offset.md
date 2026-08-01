# 0497 — "glue surrogate to LED" zeroes the lens offset, which is only right on an unfolded scene

`flag_20260801_195042` — *"glue surrogate to LED misplaced the Lens STEP."* (build `865d3afc`).
This is the recurrence of the earlier backlog item `flag_20260726_192720` ("clicking glue-surrogate
misplaces the lens"), now with an exact signature.

## Measured

```
lens placement_offset_xyz   [97.41, 0, -105.10]  ->  [0.0, 0.0, 0.0]
STEP lens bounds            x[67.81, 127.00] z[27.63, 82.63]
                        ->  x[-29.60,  29.60] z[132.73, 187.73]
```

The offset is zeroed and the body lands on the nominal +Z axis near the origin.

## Root cause

`glue_step_overlay_to_surrogate` clears the offsets outright:

```python
self._set_step_axis_offset_xy(label, (0.0, 0.0))
self._set_step_placement_offset_xyz(label, (0.0, 0.0, 0.0))
```

on the stated assumption that *"for a lens or an LED the zero-offset default IS the auto-aligned
station"*. That holds on an **unfolded** scene, where the surrogate sits on the nominal +Z axis. On
this folded scene the lens sits on the splitter's SPLIT axis (along +X at z ≈ 55), so its correct
offset is `[97.41, 0, -105.10]` and zero is nowhere near it.

bugs/0475 already met exactly this failure — for the **camera** — and its comment says so: *"with a
zero offset the body seats on the NOMINAL axis, which on a folded scene is nowhere near the sensor
... Clearing the offset here therefore did the opposite of the menu's promise"*. The fix there was
to delegate to `seat_camera_on_sensor`, *"a RELATIVE correction computed from the body's current
bounds, so it lands from ANY starting offset and never needs the destructive zeroing step."*

That carve-out was written for one label. The lens (and the LED) still take the destructive path,
and on a folded scene they hit the identical bug.

Note the second-order trap 0475 also documented: once the offset is all-zero, the `already_glued`
short-circuit refuses every retry, so the body is **stranded** — a second click cannot recover it.
Ctrl-Z is the only way back.

## Fix (not yet written)

Give the lens the same treatment: a relative seater that lands its front datum on the surrogate's
front vertex and centres it on the surrogate's axis, computed from the body's current bounds, and
call that instead of zeroing. No such helper exists yet (`seat_camera_on_sensor` is the camera's;
there is no lens equivalent). The LED wants the same audit.

The guard should drive the menu on a FOLDED scene and assert the body ends up on its surrogate, not
at the origin — and that a second invocation is still able to move it.
