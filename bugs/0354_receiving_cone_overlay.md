# 0354 — Receiving-angle cone from the imaging lens (translucent overlay)

**Status:** SHIPPED 2026-07-19 (guard `validate_open3d_receiving_cone_overlay`, penta phase 307).
**Ask (user, 2026-07-19):** "Receiving Angle Cone from the Imaging Lens, the cone should be some
kind of translucent faint color." Revives the earlier "(c) both cones" decision, whose lens-side
cone was reframed to the survivor aperture and never built as a volume.

## What ships

Overlays ▸ **"Accept cone"**: the acceptance volume the imaging lens RECEIVES from the object —
a faint steel-blue translucent skin (opacity 0.12, no caps) lofting the **imaged-FOV rectangle at
the Object plane** up to the **lens entrance pupil disc**. Every FOV point's accepted bundle
subtends the entrance pupil, so this loft is the union of the accepted cones — a point outside the
skin cannot contribute to the image.

## Anchors (no guessing — spec returns None when any is unavailable)

- Imaged FOV: `_camera_fov_object_half_extents()` (sensor dims / |m|, vendor override aware).
- Object plane: `_object_surface_plane_z(0)`.
- Entrance pupil: the first-order TRANSMISSIVE reference (bugs/0297 shared first order) via
  `_pupil_model_inputs(build_reference=True)` + `Kos.PupilCalc` — `PosPupInp` z and `RadPupInp`
  radius (EPD/2 fallback for the radius only).

## Files

`services/receiving_cone_overlay.py` (pure builder: twist-free rect→circle loft),
`three_d_scene_tools.receiving_cone_overlay_spec`, `_add_receiving_cone_overlays` (inspector),
refresh gate + `show_receiving_cone_var` + Overlays menu entry. Render-only toggle (0166 class).
In-app eyeball owed.
