# 0809 -- a partly hidden edge is not a whole edge

User, on `attachment/MV-CS050-60UM_V5_TCL4.0X-65DI-5M_view.dxf` + `broken.jpg`: "the minor problematic
part highlighted" -- where the SPO TCL4.0X's illumination port meets the Ø31 barrel -- and "the
independent 6-view output: no such problem."

## Reproduced

Headless export of the saved scene looking along world +y (view-up -x, the user's frame): 415
polylines against the user's 413, the same 5 closed rings, the same pieces at the same offsets. Under
the port (drawing frame, barrel top at y 15.5):

| piece | what it is |
|---|---|
| verticals at x -25.44 / -23.04 / -11.84 / -9.44, y 12.8..14.8 | the M3 hole walls in the port's flange plate |
| horizontal y 14.8 | the plate's top edge (real, the six-view draws it) |
| outline notches to y 12.8 | the 0.5 mm slots between plate and the milled pocket (real geometry) |

The hole walls sit at depth 6.8 behind the plate's front face at 8.5.

## Why the viewport drew them and the six-view did not

Instrumented `visible_runs` on the same strips: the depth test HID the walls -- 20 samples along each,
the first 1-2 "visible" where the 3x3 min filter bleeds the port tube's depth past the plate rim. The
run it returned was two samples, 0.105 mm.

The viewport's hidden-line loop then kept the ORIGINAL entry when

    len(runs) == 1 and len(runs[0]) == len(world)

-- a point COUNT. A 2-point edge whose visible part is one 2-sample run passes, and the whole 2 mm edge
is drawn. The six-view collector draws the runs themselves, so it was clean.

## The long line far below the lens

`poly 259`, 545 mm at the object plane (user's file y -751..-206): the only prop projecting there is a
`vtkTextActor` -- the HUD text box. Its quad lives in SCREEN pixels; the collector walked it as a mesh
and flattened it through the view matrix.

## Fix

* `_remove_hidden_lines` (extracted from the collector so it runs without a display): an entry passes
  whole only when its single run IS the strip -- same count and the same end points.
* both collectors skip 2D props (`IsA("vtkActor2D")`).

## Measured on the scene view (before -> after)

| | before | after |
|---|---|---|
| body polylines | 413 | 529 |
| total drawn length | 2012.4 mm | 1724.8 mm |
| lines >= 5 mm | 60 (1816.8 mm) | 48 (1543.4 mm) |
| lowest point | -197.0 (the HUD line) | -17.0 (the lens) |
| port hole walls | four 2 mm ticks | 0.105 mm end pieces |

Overlay of everything removed: the port's four M3 hole walls, both ring screw holes' walls, a
camera-internal board edge seen through the housing (a 24 mm line), connector internals, and the HUD
line -- all hidden or not geometry. The count rises because edges that were drawn whole now draw as
their visible runs.

## Tried and reverted

Dropping one-pixel cut pieces (a 3-sample minimum, then trimming samples only the min filter made
visible) removed the 0.105 mm ends, but at one pixel a real peek cannot be told from bleed: bugs/0803 D
keeps a 0.25 mm end piece in a multi-body view and the raw grid rounded one of its two ends away. The
one-pixel ends stay; the defect was the whole edge.

## Guard

`validate_open3d_0809_a_partly_hidden_edge_is_not_whole` (penta phase 591): A the loop on a synthetic
buffer (premise: a partly hidden 2-point edge returns one 2-point run; kept entries are the visible
~10 mm, a clear edge passes as the same entry, a buried one goes), B at most a pixel survives at an
occluder rim and a 2 mm emergence survives, C a fake renderer with a cube and a HUD quad in pixels draws
only the cube, D the user's scene (standalone): nothing far below the lens, no hole wall under the port.
Fails on the old code. 0650, 0652, 0798, 0799, 0800, 0802 (E follows the helper), 0803, 0804 pass.
