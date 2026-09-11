# 0783 -- a device-size change at a fixed FOV restores the working distance; the banner says what moved

User:

> I sometimes see Lens did not move kind of banner message while changing device size. How can a
> lens don't move when the device size changed? the WD cannot be right without lens moving.

> the production has only 3 FOVs, meaning only 3 WD + 3 image distance. So when the device change
> size, one motor move to "Restore" the WD. Thus, the entire production setup is simple.

> As a result, we shouldn't have long ray tracing wait, or chasing FOV or verifying wheater image
> land on sensor every time device size change. Everything is invariant for a fixed FOV, the motor
> just restore the WD, everything else not changing.

The user is right on the physics, and the simulator's own numbers agree.

## The physics: a fixed FOV fixes both conjugates

A FOV fixes |m|, and |m| fixes the working distance and the image distance. A device-size change
moves only the device face -- by half the size change on the split field -- so the whole correction
is one rigid move of the imaging group. The first order says exactly that (chain mm, device face ->
lens front datum and lens rear datum -> sensor), identical for a 15 mm and a 50 mm device:

| FOV | \|m\| | 80 mm WD / image | production WD / image |
|---|---|---|---|
| 20 | 1.152 | 153.85 / 155.40 | 141.47 / 161.59 |
| 34 | 0.678 | 203.92 / 116.31 | 193.20 / 121.21 |
| 54 | 0.427 | 275.44 / 95.64 | 267.10 / 99.84 |

## Two defects said "the lens did not move"

**1. The banner could not see most lens moves.** `format_focus_summary_lines` prints "the lens did
not move -- the field was already delivered" when the solve summary has no `lens_move_mm`. The
summary read it only from `_fov_solve_focus_residual_info`, which only the vendor-lock branch writes.
Every solve whose image side MOTOR 1 booked cleanly -- all of them on om05a_folded_80mm, whose sweep
records carry `residual: null` -- therefore reported no lens move after moving it (86.9 mm at
20x20 @ FOV 34).

**2. The idempotence gate ignored the working distance.** bugs/0727's `_fov_already_delivered`
compares |m| to 0.5 %, the first-order image residual, and the stored traced focus. It never asks the
object side. First order only, om05a_folded_80mm at FOV 54, from the authored 50 mm device:

| device | lens move the first order asks | \|m\| off | gate |
|---|---|---|---|
| 50 | -0.383 | -0.198 % | delivered, nothing moves |
| 49.5 | -0.633 | -0.327 % | delivered, nothing moves |
| **49** | **-0.883** | -0.455 % | **delivered, nothing moves** |
| 48 | -1.383 | -0.711 % | solves |
| 40 | -5.383 | -2.712 % | solves |

The image-side residual stays at 0.0345 mm for every size because it is computed for the target |m|
as if the object side were already corrected; the stored traced focus predates the size change. So
a small size change passed all three checks with the lens out of place -- the user's "sometimes".

## Fix

`QuickEstimationService._restore_working_distance` runs in `fov_solve` before the idempotence gate
(never on a forced request). When the scene has a MOTOR 1 group stage, the image distance already
sits at the requested FOV's operating point (|image_delta| within the delivered focus tolerance, at
the magnification the solve would book), a traced focus -- if measured -- agrees, and the working
distance is off by more than 1 um, it:

1. checks the MOTOR 1 stage bound with the measured seat sign (bugs/0782) before anything moves;
2. moves the lens pair by `object_delta` (bugs/0719, with its rail and physical-room gates);
3. moves MOTOR 1 by `object_delta + image_delta` (bugs/0759/0782, with its sensor check), putting
   every row back if it refuses;
4. records the lens move for the banner, keeps the prior focus readouts, and defers the trace --
   nothing optical changed, so the scene draws bodies and Trace Now draws the rays.

Anything else returns None and the full solve runs, which also reports every refusal with its numbers.

`_apply_conjugate_pair` now records `_fov_solve_lens_move_mm` wherever the lens move is booked, and the
success summary falls back to it when there is no residual, so the SOLVE line reads "the lens moved".

## Result -- the real 80 mm scene, first order only

`restore_probe.py`: load `om05a_folded_80mm.py` (authored device 50 at FOV 54), change the device,
call `fov_solve("object", "thickness", 54, 54)`.

| change | lens | MOTOR 1 | afterwards | banner | time |
|---|---|---|---|---|---|
| 50 -> 40 | -5.383 | -5.349 | A5 125.5068, standoff 4.3213 = the TRACED full solve's 125.507 / 4.3213 | "the lens moved -5.383 mm" | 15.7 s |
| 40 -> 30 | -5.000 | -5.000 | object/image delta 0.00000 / 0.00000 | "the lens moved -5 mm" | 18.3 s |
| 30 -> 30.5 | +0.250 | +0.250 | 0.00000 / 0.00000 | "the lens moved +0.25 mm" | 19.7 s |

The 50 -> 40 restore lands on the geometry the full traced solve reached (which measured 0.68 um on the
sensor), without its ~150 s of solve and traces. The 15-20 s left is world-point geometry recomputed
per call (the seat-sign probe, the sensor check, the lens room measure) -- not optimised here.

## Not changed

- Scenes with no MOTOR 1 group stage still take the full solve, and there bugs/0727's gate is still
  blind to the object side.
- Production's traced image does not yet form where its first order says (bugs/0782 doc); the restore
  moves it correctly, it does not make that model image.

## Guard

`KrakenOS/UI/validate_open3d_0783_device_change_restores_wd.py`, penta phase **566**, 21 checks on a stub
bench whose first order is the rows' own bookkeeping: a device change at an operating point is one
rigid move after which the conjugate asks for nothing, with no full solve and no trace, and asking
again restores nothing (A); a FOV change is solved, not restored (B); no MOTOR 1 stage, already at WD,
or a traced image that does not land is not a restore (C); a lens refusal writes nothing and a MOTOR 1
refusal after the lens moved restores every row bit-for-bit (D); the banner reads "the lens moved" from
the restore and from the full solve (E); the restore runs before the gate and never when forced (F).
Related guards on this change: 0727, 0735, 0741, 0759, 0761, 0762, 0767, 0770, 0773, 0781, 0782 pass.
