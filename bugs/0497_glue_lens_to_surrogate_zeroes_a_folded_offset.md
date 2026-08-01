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

## Fix — scoped, not yet written

`_seat_step_body_world_center(label, target)` is already the relative seater this needs: it reads
where the body actually sits and corrects by the **residual**, so it lands from any starting offset
(bugs/0456). The camera's fix used the same property. What is missing is the **target**.

"Front datum on the surrogate" is not literally the body's front face. Measured on this scene while
correctly glued:

```
lens STEP body      x[67.81, 127.00]   centre 97.405
front datum (row 1) x 71.66            rear datum (row 6) x 126.66   midpoint 99.16
```

so the body's centre sits **1.755 mm before** the datum midpoint, and its front face 3.85 mm before
the front datum. That asymmetry is a property of the CAD, not of the scene, so it is the same in any
orientation — which is what makes a general target computable:

1. Read the body's world centre at **zero offset** (set it, read, restore) → `C_zero`. That is what
   the existing nominal-axis auto-alignment produces, i.e. the designed pose expressed on the
   nominal axis.
2. Take the surrogate's datum midpoint **on the nominal axis** (`row_z_positions`) → `M_nom`, and
   the axial offset `k = (C_zero − M_nom) · ẑ`. For this lens `k` should come out ≈ −1.755. `k` is
   the CAD asymmetry, recovered at runtime rather than hardcoded.
3. Take the surrogate's datum midpoint **as it actually sits** (the world poses of the front and
   rear datum rows) → `M_now`, and the leg direction `d̂` between them.
4. `target = M_now + d̂ · k`, then `_seat_step_body_world_center("lens", target)`.

On an unfolded scene this reduces to the present behaviour (`M_now == M_nom`, `d̂ == ẑ`, so the
target is `C_zero` — exactly what zeroing gives), which is the check that the change is a
generalisation rather than a new rule. Orientation is untouched: the menu preserves user rotations,
and the flagged body was already correctly oriented along the leg before the glue.

The `already_glued` short-circuit must go too, or be re-expressed against the computed target
(`is the body already AT the target`) rather than against "is the offset zero" — otherwise the
stranding survives the fix.

The LED takes the identical destructive path and wants the same treatment on the same pass.

## Guard it needs

Drive the menu on the FOLDED scene and assert the body lands on its surrogate rather than the
origin; assert a second invocation is still able to move it (the stranding); and assert the
UNFOLDED case is byte-identical to today, which is what proves the generalisation.
