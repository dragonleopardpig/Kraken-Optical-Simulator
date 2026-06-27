# 0174 — Pixel grid: suppress the giant mesh when spots are sub-pixel (focused)

## Symptom (user, "grid on" after focusing the MV-150)

Once the detector was snapped to focus, the spots became sub-pixel (0.1–1 µm). The Spot map
magnifies hugely (×1568) to draw such tiny spots — which blew each 4.5 µm pixel up to ~7 mm,
so the **pixel grid became a giant mesh swamping the whole scene** (a wall of lines, not a
local per-spot lattice).

## Root cause

The pixel grid shares the Spot-map magnification (so the spot/pixel ratio is exact). For a
focused / ideal system the spots are sub-pixel, the magnification is enormous, and one pixel
cell ends up larger than the whole image — the per-spot patches overlap into one mesh. A
pixel grid simply has nothing to resolve when the spot is smaller than a pixel.

## Fix

`build_pixel_grid_overlay` now detects the degenerate case: `cell_size = pitch ×
magnification`; if one pixel is bigger than ~a third of the image radius (`image_radius`,
passed from `_image_circle_radius_value`, falling back to the chief spread), it returns
`too_coarse=True` with **no grids**. The inspector then draws a single plain note instead of
the mesh:

> Camera pixel grid · <camera> — spots ≈ 0.08–1.2 px — sub-pixel; one 4.5 µm pixel ≫ the
> spot, nothing to resolve

When the spots genuinely cover multiple pixels (a defocused / soft system), the normal local
per-spot lattice is drawn as before.

Verified on the MV-150: defocused (RMS ~50 µm, ×25) -> 13 grids, span 37–39 px; focused
(RMS ~0.1–1 µm, ×1558) -> too_coarse, 0 grids, span 0.08–1.2 px. Guard
`validate_open3d_pixel_grid` extended (sub-pixel suppresses; multi-pixel still draws); the
penta phase 164 guard covers it. In-app eyeball owed.
