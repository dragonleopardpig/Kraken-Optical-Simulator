# 0734 — "some of them are not 90 degree after reflection": the axis was a ray

Flag `flag_20260907_102940_169`: *"check all optical axis (not rays), some of them are not 90
degree after after reflection?"* — measured from the flagged state's own recorded axis records:

| fold | face A | face B |
|---|---|---|
| first RA mirror | **94.49°** | **96.38°** |
| BS cube | **85.51°** | **85.80°** |
| centre mirror | **83.17°** | **83.62°** |
| big prism | 89.80° | 89.82° |
| RA mirror 2 | 89.80° | 89.82° |

## Why

bugs/0723 drew each device face's CHIEF RAY — aimed through the aperture stop so it would reach
the sensor (the face-normal ray dies on the Ø14.7 stop). A chief ray meets a 45° mirror
off-normal, so it turns by 90° ± 2·(its tilt): a 2.25° tilt gives 94.5° at one mirror and 85.5° at
the next. Correct for a ray, wrong for an axis — and the user asked for the beam AXIS in the first
place ("draw BOTH imaging beams at their own offsets, **parallel to the lens axis**").

## Fix

The traced ray stays the SOURCE of the geometry — it discovers which mirrors the arm uses and
where — but the drawn guide is now constructed:

* `folds_from_traced_path(points)` recovers each mirror as `(point, normal)`, using the identity
  that `d_before − d_after` is parallel to the mirror normal at ANY angle of incidence;
* `fold_axis_polyline(start, direction, folds, end_point, end_normal)` walks the axis from the
  face centre along its normal, intersects each mirror plane, reflects, and finishes on the
  sensor plane. A fold behind the start, a mirror the axis runs along, or a degenerate direction
  returns None rather than a guess.

Because the axis is parallel to the design axis between folds, a 45° mirror turns it by exactly
90°. Measured on om05a after the fix, both faces:

```
axis:beam:face-a: 7 vertices; FOLD angles [90.0, 90.0, 90.0, 90.0, 90.0]  worst dev 0.0000
axis:beam:face-b: 7 vertices; FOLD angles [90.0, 90.0, 90.0, 90.0, 90.0]  worst dev 0.0000
(0,0,0) -> (272.63, -1.76, -16.22)   and   (0,0,-50) -> (272.63, -1.76, -33.78)
```

— the two ±8.8 mm design offsets about the sensor centre at z −25.

## Guard

`validate_open3d_0734_beam_axis_folds_ninety` = penta phase 533: A the mirror normal is recovered
from an off-normal ray (and that ray's own turn is NOT 90°, which is what the user saw), while a
refraction-sized turn is not a fold; B every constructed fold is exactly 90° and the axis lands on
the sensor plane; C an off-axis beam still folds exactly 90° and stays parallel (8.8 mm apart end
to end); D the refusals; E the wiring.

bugs/0723's B section was re-scoped: the aiming still happens and still reaches the image (it is
what finds the fold train), but the DRAWN points are now the axis, checked here.

Note for future synthetic tests in this area: a fold train must include the LAST mirror onto the
sensor or the axis has no intersection with the detector plane, and an "offset" beam must be
offset PERPENDICULAR to travel — offsetting along the direction of travel is the same line.
