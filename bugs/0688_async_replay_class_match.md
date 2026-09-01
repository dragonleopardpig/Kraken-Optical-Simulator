# 0688 — flag_20260901_210039: "B-side rays launched for a while then disappeared"

## Symptom
In the live app only arm A reached the sensor; the face-B arm showed briefly
(sync interactive refreshes) and vanished (once the ASYNC trace worker's result
was applied). Headless traces always showed both arms -- app-only.

## Root cause
The 0223 async capture/replay is POSITIONAL: the worker pops captured
`_trace_preview_bundles` records in call order. The world_cone sampler's
capture pass makes MORE imaging calls than its replay pass (the
envelope -> selected flow is data-dependent, and during capture nothing really
traces, so the branch differs). The worker's additive append call therefore
popped the ENVELOPE record: 147 envelope rays traced as the append pass
(1083 + 147 = the app's 1230 paths) and the captured face-B record was left
over -- the arm vanished. Reproduced in-process: capture 4 records, replay
consumed 2, chain 1230 / faceB 0 / leftover 2.

## Fix
Capture records now carry their class (`append: bool`); the replay pops the
first record OF THE SAME CLASS (imaging vs append). Within each class the
order is positional as before; the classes can no longer cross-contaminate.
The pre-existing world_cone imaging-count asymmetry still leaves surplus
imaging records (logged leftovers, harmless -- same as before 0680).
Verified: capture->replay now returns chain 1083 / faceB 1083, 20 reaching --
identical to the sync path.

## Also in this flag
"Is the golden arrow and the plate correspond to LED illuminator?" -- No: it is
the face-B SOURCE GLYPH (the mirrored imaging launch emitter) with its
direction arrow, standing at face B (z=-50) aiming -z into the B train. It was
drawn 55 x 10 mm (launch-bound leftovers in radius_x/y); the glyph is now sized
to the physical 50 x 1 face (radius 25 x 0.5) so it reads as the emitting face.
The LED illuminators are the two barrel assemblies on the housing sides; they
are not yet modelled as sources (the red-path backlog item).

## Guard
0672 scene guard: 15/15 PASS (specs unchanged where pinned; glyph radii are not
part of the launch contract).
