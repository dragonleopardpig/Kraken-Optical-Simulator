# 0356 — Reflected imaging rays must not pass the opaque flat LED

**Status:** SHIPPED 2026-07-19 (guard `validate_open3d_led_ray_hard_stop`, penta phase 309).
**Ask (user, 2026-07-19):** "The reflected Imaging Ray launching from Object Plane should not go
beyond the Flat LED (not physically correct)."

## Root cause

On the vendor scene the LED module is display-only CAD — never a traced surface — so the imaging
rays reflected off the beam splitter toward the LED terminated at the generic display bound and
were DRAWN sailing through/past the plate. Same display-honesty class as the bugs/0088 "rays never
cross a detector plane" hard stop.

## Fix (rides the proven 0088 mechanism)

`_led_plate_planes_for_hard_stop()` (editor) appends one plane per enabled, physical, NON-marker
scene source (the 0282/0285 predicate) to the detector hard-stop planes in the refresh ray loop —
same `(center, normal, radial_limit)` contract, same `_clip_polyline_at_detector_planes` clip.
The normal points INTO the plate (−emit direction), so:

- a ray travelling toward the plate crosses forward and truncates AT the plate;
- the LED's own flood starts ON the plane heading away and is never clipped;
- rays outside the radial board (1.5 × window half-diagonal, ≥ 20 mm) pass free.

## Files

`services/led_ray_hard_stop.py` (pure plane builder),
`three_d_scene_tools._led_plate_planes_for_hard_stop`, one merge line in the
`open3d_scene_refresh` ray loop. Display-only truncation of the DRAWN polyline — trace records
untouched. In-app eyeball owed.
