# 0811 -- a line touching the outline is not on it

User, after 0809, on the re-exported `attachment/MV-CS050-60UM_V5_TCL4.0X-65DI-5M_view.dxf` (15:58, after
the 0809 commit): "still showing broken line shown in latest broken.png", then `correct.png` -- the
component six-view of the same spot: the SPO TCL4.0X's illumination-port flange plate drawn as a closed
rectangle.

## What broken.png shows

In the user's DXF (their frame; plate top y 5.967, plate bottom y 3.967):

| piece | length |
|---|---|
| plate top edge | drawn, -19.695 .. -3.772 |
| plate **bottom** edge | **missing** |
| plate end walls (outline notch) | drawn down to 3.967, with stubs `-20.283..-20.098` and `-3.326..-3.183` |
| four verticals under the top edge at x -19.733 / -17.333 / -6.133 / -3.733 | 0.105 mm each |

A headless export of the same view (`scratchpad dxf0810b/export_ab.py`, camera at -y) reproduces all of it.

## Why the bottom edge went missing

Traced through the collector stages:

| stage | edges on the plate bottom line |
|---|---|
| before hidden-line removal | 20 fragments |
| after hidden-line removal | 4 full-length (plate front -25.939..-8.939, pocket front -25.989..-8.889, two copies) |
| after the outline dedupe | **0** |

The front bottom edges PASSED the depth test and were then deleted by bugs/0799's outline dedupe:
"anything lying on a closed outline ring is that ring drawn again". `_strips_not_already_drawn` resamples
the RING along its segments (bugs/0799) but tested each CANDIDATE only at its vertices. The plate's bottom
edge is a 2-point line whose two ends sit on the ring at the 0.05 mm notch floors between plate and
pocket, so the 17 mm edge counted as already drawn. What remained of the pocket edge were the stubs.

The six-view collector has no outline dedupe, which is why it was clean.

## The four ticks

They are 0809's "one-pixel end pieces": the M3 hole walls, 1.7 mm behind the plate's front face, keep the
two samples at the plate rim that the 3x3 filter calls visible. 0809 left them because a pixel test cannot
tell them from a real short peek -- measured on the bugs/0803 D fixture, the 0.25 mm peek past a box is
the same two filter-visible samples with one raw-visible:

| | filter-visible samples | raw-visible | middle of the step |
|---|---|---|---|
| 0803 D right peek | 98, 99 | 99 | x 10.146 -- outside the box |
| port hole wall | 0, 1 | 0 or none | 0.05 mm inside the plate face |

The triangles can tell them apart.

## Fix (`dxf_viewport_export.py`)

* `_strips_not_already_drawn` samples the candidate along its segments at the same tolerance as the
  reference. A candidate is dropped only if its whole length lies on the ring.
* `_SceneDepthBuffer._exactly_hidden(point, tol)`: a point-in-triangle depth test on the rasterised
  triangles themselves (inclusive of edges, so a line on an occluder's own edge is not hidden by it).
* `visible_runs`: a CUT run of at most three samples that the raw buffer hides somewhere is kept only if
  the middle of at least one of its steps is not exactly hidden. Runs that are raw-visible throughout
  never reach the test, so it only runs next to a rim.

## Measured on the scene view (same process setup, committed module vs fix)

| | before | after |
|---|---|---|
| body polylines | 529 | 519 |
| closed rings | 5 | 6 |
| total drawn length | 1721.0 mm | 1738.0 mm |
| lines >= 5 mm | 48 (1541.1 mm) | 49 (1558.5 mm) |
| pieces < 0.2 mm | 310 | 300 |
| port | open at the bottom, stubs, four ticks | closed rectangle (bottom 17.1 mm, top 17.0 mm) |
| export time | 45.0 s | 47.8 s |

Every other change is at the camera: the same lines stitched differently (a 71.3 mm chain now 70.8 mm
with 7 vertices instead of 13, its 30.1 mm neighbour 29.8 mm, screw-rim fragments). Close-ups before and
after are the same drawing.

The plate's top edge now spans the whole plate (-25.939..-8.939), overlapping the ring for the 0.5 mm
between the plate end and the tube wall at each end, where before a 15.9 mm piece ran between the tube
walls. A line partly on the ring was always kept whole; that has not changed.

## Guard

`validate_open3d_0811_a_line_touching_the_outline_is_not_on_it` (penta phase 592):

* A: the dedupe on the port's ring. The bottom edge is kept, a line on the ring and a copy 0.02 mm off it
  are absorbed, and a chord across the port mouth is kept.
* B: a plate under a farther tube at 11 sub-pixel heights. Premise: the filter shows the wall's first
  two samples where the raw buffer hides one, at 6 of them. No hole wall leaves a tick, the plate's own
  top edge stays whole, and a line leaving the plate's bottom keeps its 0.35 mm.
* C: bugs/0803 D's two 0.25 mm peeks are kept.
* D: wiring.
* E (standalone): the user's scene. The plate's bottom edge is drawn and there is no piece under 0.3 mm
  around the plate.

On the committed code A1, A4, B2, B4 (a 0.052 mm tick at the top rim besides the 0.364 mm), D1 and D2 fail.
