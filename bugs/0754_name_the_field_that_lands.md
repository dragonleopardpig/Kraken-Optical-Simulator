# 0754 -- when the solve leaves a focus residual, NAME the field that lands

Flag `20260908_133248_992`:

> Device size 30mm. Two seperate image planes shown, they are deteched from the sensor. Why the
> image is not landed on the sensor? I need a configuration to land the image on the sensor.

## Why the image was not on the sensor

The scene's own banner in the screenshot:

```
SOLVE: delivering 31.5 x 31.5 mm (|m| 0.7314); the lens moved -90.84 mm along its leg
FOCUS: the image forms 65.75 mm in front of the sensor -- spot 0.226 um there vs 1.94 mm on the sensor
  Face A field: 65.75 mm in front of the sensor
  Face B field: 65.75 mm in front of the sensor
```

Setting the device to 30 mm ran the FOV solve, which re-magnified so a 30 mm part would FILL the
sensor: |m| 0.4260 -> **0.7314**, by moving the lens -90.84 mm. A fixed track focuses exactly two
magnifications -- the reciprocal pair of `f(2 + m + 1/m) = K` -- and 0.7314 is not one of them, so
the image detached by 65.75 mm.

Nothing was broken. The solve delivered the requested field and reported the consequence, which is
bugs/0719 working as designed. Both faces reading exactly 65.75 mm also confirms bugs/0752 and
bugs/0753 are behaving -- the arms agree.

## What was missing

The scene said the request had failed and gave no way out. The user had to ask. A fixed track
focuses a specific field, the tool knows the model that determines it, and it never said so.

## Fix

`QuickEstimationService._in_focus_fields_at_current_track()` inverts the SAME first-order model
the solve uses (`_folded_conjugate_gaps_for_magnification`), so the two readouts cannot disagree:
scan |m| for sign changes of `image_delta` and bisect each root, then convert to object fields
with the live sensor dimensions. Pure and display-free -- no trace, no geometry written.

The result is stashed beside the residual in `_fov_solve_focus_residual_info`, and the HUD adds:

```
This track DOES focus a 54.05 x 54.05 mm object field (|m| 0.4262)
  -- ask for that and the image lands on the sensor
```

Degrades to nothing rather than guessing: an unavailable model, an unavailable sensor, or a track
shorter than 4f all yield `[]`, and a malformed entry is skipped rather than half-rendered.

## Verified against the trace

On `om05a_folded_80mm.py` at the shipped leg-45.98 configuration:

| | |m| | object field |
|---|---|---|
| inverse solve (first order) | 0.426248 | **54.053 mm** |
| measured, real folded trace | 0.4259532 | **54.090 mm** |

0.07% apart, which is the same agreement bugs/0745 requires between the first order and the trace.

## The configuration the user asked for

At the shipped setting a 30 mm part is **already in focus** -- it just does not fill the frame,
spanning 2840 of 5120 px (55.5%) at 10.564 um/px. Full sensor fill for a 30 mm part would need an
in-focus field of 31.5 mm, which needs the sensor leg at **-13.7 mm** -- physically impossible.
The most a 30 mm part can get on this bench is the shortest reachable leg, 7.54 mm, giving a
39.87 mm field: 3853 px (75.3%) at 7.786 um/px.

## Guard

`validate_open3d_0754_name_the_field_that_lands.py` (penta phase 544), display-free, against a
stub whose first-order model is the textbook conjugate law so the recovered roots can be checked
analytically:

* A: both roots are found and are the analytic reciprocal pair (product 1.0000000);
* B: converted with the real sensor dimensions, largest field first; [] for a broken model, a
  missing sensor, or a track shorter than 4f;
* C: stashed in the same dict as the residual, by the conjugate solve every `fov_solve` path
  routes through, and rendered by the HUD alongside the residual;
* D: no residual, a missing field list, or a malformed entry all render no claim.
