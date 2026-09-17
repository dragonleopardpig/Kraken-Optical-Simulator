# 0804 -- an outline ring must enclose something

The user, on `attachment/Scene_DXF.png`: the camera and lens six-view sheets (`Camera_6_View.png`,
`Lens_6_View.png`) are clean, *"but why the Scene_DXF.png still show stray broken lines?"* -- short
stubs inside the lens taper, and one near the barrel's rear flange. Then: *"but why individual
export of the lens to 6 view DXF without those stray lines?"*

## Measured on the user's own file

`MV-CH120-60UM_WWK10-110CP-111V3_view.dxf` (09:40) held 302 body polylines and 24 closed rings.
The stubs are drawn by CLOSED-flagged polylines, which is why a search over short OPEN polylines
found nothing in the taper. Measuring every ring's mean width (2 x area / perimeter):

* **18 of 24 rings enclose exactly zero area** -- 3 or 4 collinear points, a line traced out and back
  (perimeters of 48, 10.28 and 6.10 mm are twice a segment length), two of them at the rear flange;
* the other 6 are real: widths from 0.098 mm to 27 mm.

## Reproduced and traced to its source

The earlier probes used a camera preset named `"left"`, which does not exist -- presets are `+yz`,
`-yz` and so on -- so they had silently measured a default projection. With `-yz` the export gave
**302 body polylines and 24 closed rings, matching the user's file**, and tagging each ring's origin:

| source | rings | zero-area |
|---|---|---|
| bugs/0799 outline union (`mesh_outline_polygons`) | 21 | **18** |
| writer ends-meet rule (bugs/0799) | 3 | 0 |

Seen from the side, the tapered flank's triangles are nearly edge-on, and simplifying their union at
`simplify_tol` (0.02 mm) collapses thin slivers into collinear points. Because they were flagged
closed, bugs/0802's hidden-line removal and the post-process both pass them through whole -- so they
drew as lines.

## Why the six-view sheets were clean

Parsed from the source, not assumed: only `collect_viewport_dxf_layers` calls
`mesh_outline_polygons`. `collect_component_six_view_layers` builds its line art from
`mesh_outline_strips` plus hidden-line removal alone, so it never produced these rings -- and the
user's lens six-view file has 0 zero-area rings. (A first check with `awk` reported 0 calls for BOTH
collectors because its line range ended on its own starting `def`; it was discarded.)

## Fix

A ring whose mean width is below the tolerance it was simplified to is below what that outline can
resolve, so `mesh_outline_polygons` no longer emits it.

## Verified, same -yz view

| | before | after |
|---|---|---|
| union rings emitted | 21 | **3** |
| zero-area rings | 18 | **0** |
| closed rings in the file | 24 | **6** (all real) |
| body polylines | 302 | 281 |

Rendered side by side: the taper is clean, and the port, flanges, camera, holes and axis are
unchanged.

## Residuals, not caused by this and not fixed by it

A short tick at the top of the barrel's rear flange and a partly drawn hole rim below it remain in
both renders. They are ordinary OPEN polylines, not zero-area rings.

## Guard

`python -m KrakenOS.UI.validate_open3d_0804_a_ring_must_enclose_something` -- display-free. It pins
that a 5 um sliver under a 20 um tolerance yields no ring, that a 1 mm strip is kept, that a body
beside a detached sliver keeps only the body's ring, and that a cone seen from the side emits only
rings wider than the tolerance. Penta phase 587.
