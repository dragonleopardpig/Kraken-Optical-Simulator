# 0727 — re-solving a delivered field is a no-op, and a folded bail says which side failed

User, after bugs/0726: *"make the solve idempotent. To clear my doubt, the FOV 20x20 solve
refusal is because the image location is outside the sensor?"* and *"what do you mean by No
Conjugate, is it because the WD is outside the lens WD range?"*

## The answer to both questions (measured, om05a)

No to both. The refusal has nothing to do with the field landing off the sensor, and nothing to
do with the working-distance range. Printing the folded solver's own terms:

| | before any solve | after solving 20 × 20 |
|---|---|---|
| lens rear principal `h2_z` | 296.68 | **158.07** (moved 138.6 mm toward the object) |
| sensor `image_z` | 433.36 | 433.36 (vendor camera, fixed) |
| object term for \|m\| 1.152 | −138.61 mm | **+0.0000 mm** — the WD is already exactly right |
| image term | +40.61 → image gap **+60.2** (feasible) | −98.00 → image gap **−78.4** (refused) |

"No real-image conjugate" means the solver could not find a *positive* object/image distance
pair for the requested magnification **from the current geometry**. On the second pass the
object side was already perfect (0.0000 mm of lens move needed) and the IMAGE side was the
blocker: for \|m\| 1.152 the focused image lands 98 mm in front of where the sensor sits, so the
image gap would have to be negative — the sensor would have to sit inside the optics.

The cause is that the lens sets magnification and focus together. Moving it 138.6 mm to reach
\|m\| 1.152 also moved where the focused image lands by the same amount, swinging the image term
from +40.6 to −98.0. With the camera fixed, the remedy is the device stage — which is exactly
what the first solve reported as "the exact conjugate needs the object/sensor track lengthened
by 40.61 mm".

## Fix 1 — idempotence

`QuickEstimationService._fov_already_delivered(sensor_semi, object_semi, tol=0.005)`: when the
current paraxial magnification is within 0.5% of the one the request needs, the field is already
delivered. `fov_solve` consults it **before** the conjugate move and returns a no-op success:

```
Already delivering 20.0021 x 20.0021 mm (|m| 1.152) -- nothing to move.
The focus residual from the solve that set it still applies: the exact conjugate needs
the object/sensor track lengthened by 40.61 mm.
```

The no-op still re-books the target FOV and the split-field band widths, restores the focus
residual (cleared at solve entry, and still true because nothing moved), and keeps a FORCED
banner when one describes the current geometry — a stale plain refusal is still cleared, since
each solve owns the banner. A forced repeat adds "(nothing to force)".

## Fix 2 — the bail says which side failed

`_folded_conjugate_gaps_for_magnification` returned `None` silently and the caller printed
"No real-image conjugate for that size (near the focal point?)", which reads as a
working-distance limit. It now stashes a measured reason at each bail (cleared on entry) and the
FOV solve prefers it:

```
No real-image conjugate for that size: the OBJECT side is reachable (+35.76 mm of lens move),
but the IMAGE side is not: for |m| 0.7679 the focused image lands 129.6 mm in front of the
sensor, so the image gap would be -110 mm -- the sensor would have to sit inside the optics.
The camera is fixed, so re-solve from the loaded geometry or move the device stage.
```

## Verified (om05a)

| step | before | after |
|---|---|---|
| solve 20 × 20 | moves lens −138.6 mm, ok | unchanged |
| solve 20 × 20 again | **refused**, "No real-image conjugate" | **no-op success**, gaps unchanged (41.8587 / 156.5413) |
| a third time, and forced | refused | no-op, "(nothing to force)" |
| solve 30 × 30 from the moved state | refused, generic text | still refused (correct) but now names the side, the 129.6 mm and the remedy |

## Guard

`validate_open3d_0727_fov_solve_idempotent` = penta phase 526 (display-free): A the pure gate
(inside/outside tolerance, unusable input, the reported field = sensor/|m|); B the gate runs
before the move and the no-op preserves the residual and a forced banner while still booking the
FOV and bands; C the forced repeat wording; D the folded solver clears and stashes its reason and
the solve prefers it. 0717 / 0719 / 0721 / 0726 still pass.

## Known limitation (not changed)

The reachable fields are path-dependent: once the lens has moved forward, other fields can refuse
on the image-side gate even though they solve from the as-loaded geometry (FOV 30 above). That is
the same fixed-camera coupling, not a new defect — but a "reset the lens to the loaded geometry
before solving" step would make the solve order-independent. Worth deciding with the user.
