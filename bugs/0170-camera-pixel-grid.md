# 0170 — FEATURE: camera pixel-grid overlay (the spot footprint on real pixels, idea #1)

## Request (user)

> Let's say now I add a camera so that the detector has pixel size, can you draw for
> example 5120x5120 grid with 4.5um? This is an example of the SVS 25MP camera. You might
> want to generalize it. The idea here is when enable the spot diagram overlay, we can see
> how the actual spot overlay onto each pixels of the camera.

## What it does

A new **"Pixel grid"** overlay (Overlays dropdown + the right-click image-plane menu). When
a vendor camera is registered on the detector, the camera record carries a pixel pitch
(the Allied-Vision / SVS 25 MP `hr25MCX` is 5120x5120 @ 4.50 um). The overlay draws that
pixel LATTICE under each spot of the Spot map, so the user sees the real spot land on
individual pixels -- and the label reports how many pixels the blur spans (the double gauss
on the 25 MP: spot ≈ 6-9 px).

Drawing a literal 5120x5120 grid is impossible (and a 4.5 um pixel is invisible at the
sensor's true 23 mm scale), so the overlay draws only the LOCAL lattice each spot straddles:

- **true-aligned** — lines fall on real pixel boundaries `k*pitch` from the sensor centre,
  so the spot's sub-pixel position is honest;
- **magnified about each chief by the same factor the Spot map uses**, so the spot/pixel
  size RATIO is exact (a 34 um spot over 4.5 um pixels really reads as ≈ 7.5 px).

Best used with **Spot map** on (the scatter overlays the pixels). Generalized: any camera
in `camera_database.py` with a `pixel_size_um` works; no camera -> the overlay is inert.

## Pieces

- `camera_database.camera_pixel_pitch_mm` / `camera_resolution_px` — vendor pitch + size.
- `services/pixel_grid.py` (pure) — `build_pixel_grid_overlay(chief_uv, spot_extent_mm,
  pitch_mm, magnification, ...)` -> per-spot `{h_lines, v_lines}` world segments + the
  pixel span. The spot-map spec now exports `chief_uv` / `tangent` / `spot_extent_mm`.
- `three_d_scene_tools.pixel_grid_overlay_spec` (+ `_camera_pixel_pitch_mm`) — reuses the
  cached Spot map; needs a registered camera.
- `open3d_inspector._add_pixel_grid_overlays` — one merged line mesh + a label; render-only
  per bugs/0166, behind `show_pixel_grid_var`.

## Guard

`validate_open3d_pixel_grid` (display-free): lattice geometry (span = 2*extent/pitch, true
alignment + sub-pixel honesty, pitch*factor spacing), a real double-gauss + 25 MP camera
spanning a few pixels, no-camera -> None, render-only/no-shadowing. Penta phase 164.
In-app eyeball owed (register the 25 MP camera, enable Spot map + Pixel grid).
