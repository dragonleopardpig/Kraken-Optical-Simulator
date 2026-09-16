# 0798 -- the DXF's shapes must close

The user, on their own export `attachment/MV-CH120-60UM_WWK10-110CP-111V3_view.dxf`:
*"the DXF output, there are many unclosed edges, they are supposed to be closed shape. I think
this is recurring bug as well."*

Recurring it is: `bugs/0650` item 3 was *"some boxes not closed, missing lines at one side, not
symmetry"*, and took eight rounds.

## What the file actually contained

| | |
|---|---|
| polylines | 3998 |
| carrying the DXF closed flag (70 & 1) | **0** |
| bare 2-vertex segments | 3206 (80%) |
| geometrically closed (first == last) | 386 |
| body polylines with a dangling end | 3610 of 3996 (**90.3%**) |

Rendered to PNG with every open end marked, the picture is unambiguous: the barrel, the port
and the camera are all drawn as loose lines with red open ends at **every corner of every box**.

## Two false starts, both recorded because they cost time

**The stitch tolerance is not the problem.** The first measurement -- median nearest-endpoint gap
0.0156 mm against `stitch_strips_2d`'s 1e-3 mm tolerance -- looked decisive and was an artifact.
Instrumenting the real pipeline showed the stitcher working correctly: one colour bucket went
416 strips in, 120 chains out, and the raw segments' median endpoint gap was **0.000000** with
66.5% of ends exactly coincident. After a CORRECT stitch, surviving endpoints are terminal by
construction, so "95% dangling" is the expected outcome, not a defect. Raising the tolerance to
0.08 mm changed nothing at all, and produced zero extra closed shapes at any value up to 0.4 mm.

**The perturbation union is not the whole story either.** Dropping the extra tilts entirely moved
the output only from 8050 polylines to 7748 and from 152 closed shapes to 145.

## Root cause

**1. The three silhouette passes TRIPLICATE every contour.** `mesh_outline_strips` unions
`vtkPolyDataSilhouette` at three perturbed view directions (bugs/0650 round 6, so a contour edge
lost at one direction's tangency knife-edge is caught by a neighbour). Each tilt puts the
silhouette on DIFFERENT mesh edges, so the copies land about 0.1 mm apart. Measured on the
user's scene: **129386 mm of raw line for 46156 mm of unique geometry**. Its own comment claims
"the fragment dedupe absorbs the overlap", but that dedupe is an EXACT one and cannot see copies
a tenth of a millimetre apart.

**2. The merge moved endpoints that were exactly coincident.**
`merge_collinear_segments_2d` emitted every result as

    d * t + normal * mean_offset

-- a line REBUILT on the cluster's reference direction at the group's mean offset. A segment was
therefore moved even when it had nothing to merge with, and the two arms of a corner, being in
different angle clusters, were moved independently. Measured on one real colour bucket: of
**2854** joinable (exactly coincident) endpoints among the raw segments, **13** survived the
merge. Two arms meeting exactly at (50, 0) come out ending at (50, 0.0125) and (50.0125, 0).

Together: every corner existed three times in three slightly different places, the merge had to
choose between the copies and chose inconsistently, so the arms of a corner ended up on
different copies. The stitched chains were left a median **1.38 mm** from closing -- not a
tolerance away, a geometry away.

## Fix

* `_strips_not_already_drawn` makes the perturbed passes ADDITIVE: the base silhouette is
  canonical and its connectivity is untouched, and a perturbed fragment is kept only where the
  base drew nothing near it. The tolerance is RELATIVE to the reference drawing's extent (0.05%)
  so it scales with the view instead of assuming millimetres. Round 6's purpose survives -- a
  contour the base pass misses entirely is still added.
* `merge_collinear_segments_2d` unions the parameter intervals as before but emits the REAL
  endpoints of the members that reach each end of a run. A group of one comes back untouched.
  Unioning overlaps was always the point; moving endpoints never was.

## Verified

Same scene, same camera, exported before and after:

| | before | after |
|---|---|---|
| polylines | 30975 | **7899** |
| bare 2-vertex fragments | 27486 | 4666 |
| geometrically closed shapes | 76 | **149** |
| open ends in the bodies layer | 59502 | **14294** |

3.9x fewer fragments, half the open ends, twice the closed shapes. Re-rendered to PNG and
looked: the barrel outlines and the flange circles are continuous where they were dotted with
open ends. The camera body, a dense vendor STEP, is still busy -- it genuinely has that many
edges.

Per colour bucket, joinable endpoints surviving the merge went 13 -> 101 and the chain count
halved (234 -> 120).

## Still open

The drawing does not yet carry the DXF **closed flag** (70 & 1) on any polyline, and a body's
outline is still delivered as several chains rather than one loop per profile. The measurements
that would drive that work are in this document: chains end a median 1.38 mm apart, which is
geometry the passes never produced, not a tolerance to widen.

## Guard

`python -m KrakenOS.UI.validate_open3d_0798_closed_shapes_in_the_dxf` -- display-free, synthetic
geometry, no app or VTK. It pins the causal invariant (**every endpoint the merge emits is one it
was given**, which the old averaging violates whenever a cluster holds more than one member),
that a near-parallel neighbour never drags a segment onto an averaged line, that a retrace is
dropped while a genuinely new edge is kept, that the dedupe tolerance scales with the drawing,
that a box retraced 0.025 mm away still stitches into ONE closed chain, and that a contour the
base pass missed is still added. Penta phase 581.
