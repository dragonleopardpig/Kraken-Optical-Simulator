# 0799 -- the outline is a CLOSED shape, computed not assembled

Follow-on from `bugs/0798`, which halved the DXF's fragmentation but left the item the user
actually asked for undone: *"they are supposed to be closed shape"*. Not one polyline carried
the DXF closed flag, and a body's profile still arrived as several chains.

## Why assembling edges could not get there

0798 left a measurement that decided this bug. The line art is a soup of silhouette and feature
edges whose graph has vertices of degree > 2 -- T-junctions, plus one contour per silhouette
pass -- so a greedy endpoint walk cannot know which incident edge continues a profile. Both
orders were measured on real captured buckets:

| route | chains | closed | total length |
|---|---|---|---|
| merge -> stitch (what 0798 shipped) | 120 | 0 | 46156 mm |
| stitch -> dedupe chains | 2 | 0 | 129386 mm |

The first fragments the graph; the second walks every duplicate into two giant scribbles
carrying 129386 mm of line for 46156 mm of unique geometry. Neither produces a loop, and the
stitched chains ended a median **1.38 mm** apart -- geometry away, not tolerance away.

## Fix: compute the outline, don't assemble it

A silhouette does not have to be reconstructed from edges. Project every triangle into the view
plane and take the **boolean union**: its boundary IS the outline, closed by construction, with
one exterior ring per connected body and one interior ring per through-hole.

`mesh_outline_polygons` does exactly that with shapely, then lifts the 2D result back along the
view direction at the mesh's own depth so the caller projects it like every other strip. On this
scene's own meshes:

| mesh | triangles | union | result |
|---|---|---|---|
| lens body | 11272 | 0.20 s | **1 closed ring**, 117 vertices |
| camera body | 231606 | 4.47 s | **1 closed ring**, 64 vertices |

Three supporting changes:

* the rings are emitted as closed polylines and **pass through `_postprocess_layer_polylines`
  untouched** -- decomposing a finished ring into segments and re-stitching it would hand it
  back to the very walk that could not close it;
* `write_dxf_r12` sets group 70 bit 1 and does not repeat the final vertex, so CAD offsets,
  hatches and area-measures the shape as a region. It does this for ANY polyline whose first
  vertex repeats as its last, so stitched interior loops (a flange circle) are flagged too;
* `_strips_not_already_drawn` now samples a SPARSE reference along its edges before testing
  coverage. An outline ring is a handful of long edges, so a fragment lying exactly on it can
  still be half a segment from the nearest reference vertex. It also works in 2D now, because
  the coverage test must run in the VIEW PLANE -- the ring sits at the mesh's mean depth, so a
  3D comparison measures depth rather than the drawing.

## Measured on the same scene and camera

| | 0798 | now |
|---|---|---|
| polylines carrying the DXF closed flag | **0** | **105** |
| closed outline rings from the union | 0 | 10 |

Rendered and looked at with closed shapes drawn in green: the barrel profile, the coaxial port,
the flange circles, the camera body and the object-plane rectangle and disc are all continuous
closed loops.

## What the remaining open lines are, measured rather than assumed

The bodies layer still holds ~7300 open polylines, and they are **not** duplicated outline: of
those, **0%** lie within 0.1 mm of a closed ring and only 1.6% within 0.3 mm. They are interior
detail -- creases, rims, the camera's connector work -- which is open line art in any drawing.
The outline dedupe therefore correctly removes almost nothing; it is in place so that a body
whose silhouette DOES retrace the union boundary is not drawn twice.

## Guard

`python -m KrakenOS.UI.validate_open3d_0799_the_outline_is_a_closed_shape` -- display-free,
synthetic meshes, no window. It pins that a box gives one closed ring whose area is its projected
footprint and that the footprint follows the view direction, that a drilled plate yields both an
exterior and an interior ring of the right areas, that empty or over-budget geometry is refused
quietly, that a closed ring survives the body post-process with its vertices untouched, that the
writer emits group 70 bit 1 for exactly the closed ring and drops its repeated vertex, and that
the coverage test samples a sparse reference along its edges. Penta phase 582.
