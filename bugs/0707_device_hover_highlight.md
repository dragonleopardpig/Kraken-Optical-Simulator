# 0707 — "cursor on the device won't highlight; only the browser can pick it"

Half intended, half gap. Where the prism meshes cover the part, the frontmost
actor rightly wins the pick (physical z-order) and the 0705 browser row is
the handle. But where the Device IS the frontmost actor it never highlighted
-- its actors were tracked (0661) yet unknown to the hover system.

## Fix

- `Kraken3DInspector._set_inspection_part_hover(active)`: gold tint
  (1.0, 0.80, 0.20) over all part actors, original colours stashed and
  restored exactly on leave; actors rebuild per refresh so staleness
  self-heals.
- The plain-hover fallthrough in `open3d_interaction` now recognises a part
  actor pick: gold tint + floating label
  "Device W x H x D (inspect: face) / Right-click: size / faces / FOV".
  Leaving onto a STEP body releases the tint.
- Right-click on the exposed Device already worked (the 0661 canvas menu);
  the hover affordance now advertises it.

Live-verified on om05a_folded_80mm: all 7 part actors (box + 6 face
outlines) tint gold on activate and restore byte-exact. Guard: 0705 guard
gained E1 (hover branch source-pin) + E2 (tint/restore behavior) -- penta
phase 514.
