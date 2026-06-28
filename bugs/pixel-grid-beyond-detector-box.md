# Camera pixel grid drew beyond the orange detector box

## Symptom (flag_20260628_161950_004)
The camera "Pixel grid" overlay (idea #1: the spot footprint on real pixels) drew a cross/plus of
magnified pixel-lattice patches that spilled WELL beyond the orange detector frame (the sensor).
MV-150 + the 25 MP Allied-Vision hr25MCX (5120x5120 @ 4.5 um = 23 mm sensor), spots ~1-6 px,
spot-map magnification x210.

## Root cause
`build_pixel_grid_overlay` (services/pixel_grid.py) draws, per spot, the pixel boundaries the spot
straddles, displayed at `chief + (true - chief) * factor` -- i.e. MAGNIFIED about each spot's chief
by the spot-map factor (x210). An EDGE spot sits near the sensor edge (~+/-11.5 mm); its magnified
patch (~16 mm wide) therefore extends several mm PAST the edge. The 0174 too-coarse guard
(`cell_size > 0.35*image_radius`) doesn't trip here (0.945 mm < 5.7 mm), so the grids draw -- and
spill out of the frame.

## Fix
Clip the magnified lattice to the SENSOR BOX. `pixel_grid_overlay_spec` computes
`sensor_half_uv = camera_resolution_px * pitch / 2` (= the orange frame; the 25 MP is 11.52 mm
half) and passes it to `build_pixel_grid_overlay`, which now drops/clamps each lattice line to
+/- sensor_half in (u, v). The lattice is axis-aligned with (u, v), so the clip is exact: a column
past the edge is dropped; a line crossing the edge is clamped to the edge. None -> no clip
(unchanged behaviour when the camera resolution is unknown).

## Verified (display-free)
A corner-field spot whose x210 patch reaches |u|,|v| = 23.96 mm is clamped to exactly 11.52 mm,
and the grid still has lines (not emptied). guard `validate_open3d_pixel_grid` (extended with a
clip assertion).
