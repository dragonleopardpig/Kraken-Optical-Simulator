# 0738 -- a bare "air" spacer row is not an optical surface

Flag `20260907_112030_381` (build 08f0acb9), zoomed in on the sensor:

> "zoom view showing left and right side of the rays, left shows focus rays, right shows defocus
> rays, although they are not landed on sensor, but **symmetry should applies**."

The user is right, and it was a real defect -- not a sampling artefact.

## What was measured

om05a images two faces of the same device down two arms that are meant to be mirror images. One
axis ray per face, printing `SURFACE` / `GLASS` / `DISTANCE`:

| | arm A (face A) | arm B (face B) |
|---|---|---|
| geometric path | 114.907 mm | 114.907 mm |
| legs to the centre mirror | 8.58, 5.77, **1.50**, 3.92, 8.08, 4.0, 12.72 | 8.58, 5.77, **5.42**, 8.08, 16.72 |
| medium of that middle slice | **AIR** | BK7 |
| path the trace tags as glass | **17.770 mm** | **19.270 mm** |

The two arms were symmetric to the micron geometrically, and arm A carried **1.5 mm less glass** --
one extra hit, on a surface named `air`, splitting a 5.42 mm glass leg into 3.92 mm of glass plus
1.50 mm of air. (The last row sums the trace's own per-segment medium tags; what matters is the
DIFFERENCE between two arms read the same way, and the extra hit that causes it.) Downstream
(surfaces 7, 8, 9, 10) the two hit lists were already identical leg for leg.

## Root cause

The scene's rows:

| arm A | arm B |
|---|---|
| 1 `First RA mirror A` (Solid) | 16 `First RA mirror B` (Solid) |
| 2 `air` -- bare spacer, Ø80, no element | -- |
| 3 `BS cube A` (Solid, BK7) | 17 `BS cube B` (Solid, BK7) |
| 4 `air` -- bare spacer, Ø80, no element | -- |
| 5 `Centre RA mirror A` (Solid) | 18 `Centre RA mirror B` (Solid) |

Arm A carries two bare spacer rows that arm B does not. A spacer is flat, AIR, uncoated, unmasked,
no stop, and carries no body -- in a **sequential** trace it contributes nothing but its thickness.

Non-sequential mode meshes *every* row, so that spacer becomes a real Ø80 disc the chooser can hit,
and the medium bookkeeping is row-**order** based, not geometry based: crossing the disc reports the
glass that *follows* the spacer row. Row 2's disc falls **inside BS cube A**, so the ray was declared
to be in AIR for 1.5 mm of the cube's interior, and the cube silently lost that optical path -- on
arm A only.

The observable is exactly what the user photographed: two bundles at the same plane, one converged
and one not.

## Fix

`system._ns_phantom_spacer_surfaces()` (KrakenSys.py) marks the rows a non-sequential trace must
never interact with, and `__NonSequentialChooser` skips them as candidates.

A row is a **bare spacer** when it has no CAD/STL body, is a Standard flat surface, is AIR, and has
no optical behaviour of its own -- no curvature, conic, axicon, thin lens, grating, annulus, mask,
UDA, coating, error map, sub-aperture, cylinder ratio, or diffuse scatter -- is neither a designated
aperture stop (bugs/0179), a surrogate barrel wall (bugs/0623), nor a detector, **and is not
drawn**.

The drawn/undrawn line is the second safety clause, and penta 185/186 found it. Those phases assert
that "every folded downstream row's drawn X coincides with the ray's crossing" -- so skipping a row
the scene DRAWS leaves a disc on screen that no ray meets, which is the 0207 defect seen from the
other side. It is also where the harm is and is not: an UNDRAWN spacer is scaffolding that can sit
anywhere, including inside a glass body (om05a row 2, inside BS cube A); a DRAWN one marks a real
station -- a promoted solid's own rear face -- met in air, where keeping it costs one vertex and
changes nothing.

A bare spacer is only **phantom** when the medium in front of it is owned by an optical **SOLID**
(walking back over any run of spacers). That clause is what keeps the fix safe:

* A solid meshes its own entry, internal and exit faces, so it performs every refraction of that
  element itself -- no bare row placed after it can be one of its interfaces.
* Where the medium comes from a classical glass row instead, the bare AIR row **is** that element's
  exit face. om05a row 13 `Filter 48-926` (N-BK7) hands off to row 14 `to camera`, and every plano
  lens's flat back works the same way. Skipping those would trap the ray in glass forever.

The image/target row is never phantom, however bare it looks.

On om05a the rule marks rows 2, 4 and 6 phantom, and leaves 14 (the Filter's exit face) and 23
(the sensor) alone.

## Result

The two arms now trace identically, hit for hit:

```
arm A  SURFACE [ 1,  3,  3,  3,  5, 7, 7, 8, 7, 9, 10]
arm B  SURFACE [16, 17, 17, 17, 18, 7, 7, 8, 7, 9, 10]
both   DISTANCE [8.58, 5.77, 5.42, 8.08, 16.72, 16.61, 25.0, 16.866, 8.134, 3.727, 0.0]
both   geometric 114.907 mm | glass 19.270 mm
```

Full-bundle waist measurement at the sensor, before and after:

| | face A | face B | split |
|---|---|---|---|
| before -- landing rays | 4 | 7 | |
| before -- waist offset | -72.67 mm | -79.47 mm | **6.80 mm** |
| before -- spot on the sensor | 1.68 mm | 1.95 mm | |
| after -- landing rays | 7 | 7 | |
| after -- waist offset | -79.474 mm | -79.474 mm | **0.000 mm** |
| after -- spot on the sensor | 1.9537 mm | 1.9537 mm | |

The phantom disc was the whole cause: it not only drained the glass, it perturbed *which* rays got
through, so arm A was also being measured from a smaller, biased sample (4 rays against 7).

Dropping three phantom surfaces from the candidate set also shortens every non-sequential step.

## Checked against the other scene families

Statically, across all 34 scenes in `attachment/`, the rule skips a row in only six files, and in
every case it is a gap row that follows a solid -- never a row whose medium comes from a classical
glass row.

The promoted-STEP surrogate family (`machine_vision_150mm_*`, `machine_vision_AZ85_RA_Mirror`)
writes a promoted solid as the solid row plus a `-> next gap (AIR)` row. Those gap rows are DRAWN,
so the final rule keeps them. Before the drawn clause was added they were skipped, and tracing the
scene both ways gave identical results -- same path (614.549 / 614.611 / 614.986 mm at three
heights), same glass, every ray still reaching the image -- confirming that gap row sits in air
OUTSIDE the solid and never did any harm. om05a's spacers sit INSIDE the glass and are undrawn,
which is where the damage was. The surrogate's `Lens Front Datum` rows are barrel walls (bugs/0623)
and are never spacers.

## Not fixed here

`stopped_at_surface_10` still dominates in this scene -- most rays are stopped by the aperture stop
at this conjugate, so few reach the sensor. That is the stop doing its job at a demanding
magnification, not an asymmetry; both arms now lose rays equally.

## Regression check

The first cut of this fix (without the drawn clause) failed the penta gate. Isolating it by running
the flagged phases at HEAD with the change parked showed that 8 of the 11 -- 25, 31, 39, 60, 282,
477, 492, 505 -- were already failing at HEAD, unchanged by this work and unchanged by the scene
repair. This change was responsible for exactly three: 185, 186 (the drawn-row contract above) and
518 (which passes once the scene itself is repaired). With the drawn clause all three pass.

## Guard

`KrakenOS/UI/validate_open3d_0738_phantom_spacer_surfaces.py` (penta phase 536).
