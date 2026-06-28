# Camera pixel grid was per-spot (overlapping patches), not a uniform sensor lattice

## Symptom
The camera "Pixel grid" overlay (idea #1: the spot footprint on real pixels) drew a SEPARATE
magnified pixel patch under each spot, each lattice magnified about its OWN chief. Cropped/zoomed
in, the patches sat at different offsets and overlapped at odd angles. User: "I thought the grid
for camera pixels should be uniform?" — a real camera sensor's pixels are an even, uniform grid.

## Root cause
`build_pixel_grid_overlay` (services/pixel_grid.py) looped over the N spots and, per spot, drew the
pixel boundaries it straddled at `du = cu + (k*px - cu)*factor` — i.e. magnified about THAT spot's
chief `cu`. The `cu*(1-factor)` term is per-spot, so every patch had a different sub-pixel origin
→ the patches did not tile into one continuous grid (they overlapped). This was deliberate (it kept
each spot's sub-pixel position honest), but it does not look like a camera's uniform pixel grid.

## Fix
Emit ONE uniform lattice. Pixel boundaries `k*pitch` are magnified about the SENSOR CENTRE (not per
spot): line k sits at `du = k*pitch*factor`, so cells are even (each `pitch*factor` wide) and the
grid is the same regardless of which spots are present. It is tiled only inside the sensor box
(`sensor_half_uv`, the orange frame) so it never spills past the edge, and capped at `max_cells` per
axis so a small magnification can't ask for thousands of lines. The spots (drawn by the spot map,
still magnified about their own chiefs) land on this shared grid; the count of pixels a spot spans is
exact because the factor cancels. Trade-off: the uniform grid no longer encodes each spot's exact
sub-pixel registration — it is a uniform pixel-size ruler, which is what the user wanted. The
too-coarse (sub-pixel spot) early-return is unchanged. The label drops "each grid = ×N zoom on one
spot" → "uniform lattice, ×N zoom so pixels are visible · spots span ≈ lo-hi px · full sensor … =
orange frame".

## Verified (display-free)
MV150 numbers (pitch 4.5 µm, factor ×210, 25 MP → ±11.52 mm box): one uniform 24×24 lattice, 25+25
lines spaced at EXACTLY 0.945 mm (= pitch*factor), a line on the sensor centre (k=0), max |u|,|v| =
11.34 mm ≤ 11.52 (inside the box, no spill). The lattice does NOT move when the spot chief changes
(chief-independent). guard `validate_open3d_pixel_grid` (pure-geometry uniformity + integration
"ONE uniform lattice inside the sensor box"). In-app eyeball owed (the render).
