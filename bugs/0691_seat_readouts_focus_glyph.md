# 0691 — flag_20260902_094650: the three seated-scene regressions

## 1. "Only one launching point from each side" (+ hidden HUD, washed colours)
ONE root: the paraxial finite-m returned None on the seated scene. The 0440
centered-guard treats a Standard row with desp as a hand-tilted PRESCRIPTION and
raises -- the seated "Front Optical Vertex Datum" carries the frame-desp of the
vendor seat, which is PLACEMENT. The existing escape (ScenePlacement breadcrumbs)
could not be used as-is: `last_axis_to_axis_move` also makes the fold walk SKIP
the row (the v1 bake failure), and the walk's frame-desp pose IS the seat.
FIX: a new `ScenePlacement.frame_seat` breadcrumb -- honoured by
`_row_placement_is_baked_world_pose` (paraxial unfolds the placement desp) and
IGNORED by `_row_explicitly_axis_snapped` (the walk still poses the row).
m restored (0.4066): HUD Resolution/Magnification lines back, the 3x3 field grid
back (3 visible launch points per side), field colours back.

## 2. "One of the ray defocus at the sensor"
B2 measured a razor waist (0.1 um) at y=-9.90 vs the sensor row at -11.36 --
pure 1.46 mm defocus from the seat. FIX: mirror-2 row thickness 45.64 -> 44.18
(the final folded leg); best focus and row now coincide (B2: best y -9.90, row
-9.90, rms 0.1 um). Arm B rides the shared sensor at the compromise focus
(381 on-strip vs arm A 521 -- the vendor's split-field trade).

## 3. "The LED position and arrow is still wrong"
The glyph is the face-B EMITTER (not an LED) and its panel already hugs the
50x1 face -- but the direction arrow was 1.6 x max(rx, ry) = 40 mm, towering
over the assembly. FIX: arrow length also keyed to the smaller panel dimension
(min(1.6*max, 8*min+4)) -- slab emitters get a modest marker, ordinary LED
panels unchanged.

## Guard
0672: sensor-y pins moved to the focused plane (-9.9), counts re-pinned for the
restored grid (chain >=450 on-strip, faceB >=350). 15/15 PASS.
