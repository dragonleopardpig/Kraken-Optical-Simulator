# 0769 -- a camera stage on the wrong row fails silently; and production gets its stage

`attachment/om05a_folded.py` carried `camera_focus_stage: None` and could not book any
image-side correction, so every solve on the production build reported a large focus residual.
Fixing that turned out to need one scene change and one code change.

## Why declaring a stage was not enough

`_image_write_locked_by_vendor_hardware` exempts the glued camera body **only when the stage's
row IS the row the solve writes** (`_folded_image_leg_write_row`). On production that write row
is the last row before Image; a stage declared on the RA mirror row therefore fell through to:

> the sensor carries the vendor camera body (glued camera STEP)

which is the identical message a scene with **no stage at all** gets. Motor 1 was skipped, 7.31 mm
of residual was reported, and nothing in the output pointed at the mismatch. That cost an
afternoon.

The reason now names both rows:

> ... -- this scene's camera stage is declared on row 15, but the image side is written on row
> 22, so the stage cannot book it

## Why the code does NOT just use the write row

Tempting, and wrong. Measured: pointing the stage at om05a_folded's actual write row -- a
zero-thickness, **desp-placed vendor LED panel** -- satisfied the first order beautifully
(`image_delta -> -5e-13`, the solve returning at -0.0014 mm) while the **trace stayed 7.31 mm
out**. A desp-placed body's thickness moves the station sum without moving the sensor in the
folded world geometry. Silently re-pointing the stage would have written a vendor body and
produced a scene that looks solved and is not.

## The scene change

`om05a_folded.py` needed a real `sensor standoff` row, exactly as the 80 mm scene has, so that
the write row and the stage row coincide by construction:

```
RA mirror 2 (40 mm)  45.13  ->  36.31  +  sensor standoff 8.82      (sum preserved: 45.13)
camera_focus_stage: row=23 (the new standoff), arm_row=15 (mirror 2), arm_carry_row=12 (C1)
```

Nothing moves -- both halves stay `AIR`, the mirror is a single reflecting face either way
(external reflection on this build, confirmed by the user), so no glass and no phantom surface
are introduced. Backup: `attachment/om05a_folded.py.pre-standoff.bak`.

Two earlier proposals for this scene were **withdrawn** after the user corrected me: restoring
BK7 to `RA mirror 1 (50 mm)` (it is external reflection here -- AIR is right, and adding glass
would have injected ~17 mm of focus shift the hardware does not have), and splitting row 7 (for
an external mirror there is no body to traverse; the split would have inserted a phantom surface
into a non-sequential trace, the bugs/0738 trap).

## Guard

`KrakenOS/UI/validate_open3d_0769_stage_row_must_be_the_write_row.py`, penta phase **553**:
a wrong-row stage is refused with a reason naming both rows (A); a right-row stage is still
exempted, bugs/0756 intact (B); a scene with no stage keeps the original message, and the two
cases are now distinguishable (C); the lock does not silently substitute the write row (D).
