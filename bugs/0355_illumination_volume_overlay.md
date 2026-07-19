# 0355 — Flat-LED illumination volume, LED → BS fold → FOV (translucent overlay)

**Status:** SHIPPED 2026-07-19 (guard `validate_open3d_illumination_volume_overlay`, penta phase 308).
**Ask (user, 2026-07-19):** "Illumination ray from the Flat LED at the side of the BS Cube.
Launch as a 3D Volume, faint translucent, all the way to the FOV."

## What ships

Overlays ▸ **"Illum volume"**: each physical (enabled, non-marker) scene source drawn as one
faint cyan translucent envelope (opacity 0.10): the emitting rectangle — in the SAME
(origin, direction, u, v) frame as the 0283 source glyph, so volume and glyph coincide — extrudes
along the emit direction, **folds at the optical axis by the mirror law**, and continues to the
Object/FOV plane.

## Physics (the corrected coaxial_led_dark_edges model)

Reflection is an ISOMETRY: the folded legs stay CONGRUENT to the emitting rectangle — the guard
asserts the Object-plane footprint of a 74×55 side emitter is exactly 74×55, never a cos-squashed
38.9. The fold is derived from the scene's optical axis (closest point on the axis to the emit
ray; exit aims at the Object-plane axis point; fold-plane normal = the mirror-law bisector) — no
dependency on any BS pose, and an emitter already aiming down the axis (the unfolded teaching
scene) draws a single straight leg.

## Files

`services/illumination_volume_overlay.py` (pure folded-tube builder),
`_add_illumination_volume_overlays` (inspector, rides `_drawable_scene_source_descriptors` +
`_scene_source_glyph_basis`), refresh gate + `show_illumination_volume_var` + Overlays menu entry.
Render-only toggle. In-app eyeball owed.
