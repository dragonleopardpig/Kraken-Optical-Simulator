# Image-plane analysis overlay text labels overlapped each other

## Symptom
From flag_20260629_085625_442: "Turning on more analysis overlay, the texts labels overlap."
With one image-plane analysis overlay on, its billboard label sat near the detector top and read
fine. With two or more on (e.g. Spot map + Pixel grid + Astigmatism), each overlay drew its OWN
billboard at roughly the SAME spot (the top rim of the image plane) → the labels stacked on top of
one another into an unreadable pile. User: "I think just group them in one label, expand it if more
analysis are shown."

## Root cause
Five image-plane analysis overlays each owned a `vtkBillboardTextActor3D` and each computed its
anchor independently from its own geometry's top rim point
(`rim[argmax(y)] + normal*clearance`):

  * `_add_best_focus_surface_overlays`  (Focus surf)
  * `_add_distortion_grid_overlays`     (Distortion)
  * `_add_astigmatism_surfaces_overlays`(Astigmatism)
  * `_add_spot_field_map_overlays`      (Spot RMS map)
  * `_add_pixel_grid_overlays`          (Camera pixel grid)

Because every overlay lives on the SAME image plane, those anchors land within a few mm of each
other — so the more overlays you enable, the more billboards pile onto the same corner. There was
no shared placement; each was unaware of the others.

## Fix
Route every overlay's label through ONE shared, expanding legend instead of each drawing its own
billboard:

  * `_reset_analysis_overlay_labels()` — clears the shared collector (sections + anchor basis) at
    the start of each scene refresh.
  * `_queue_analysis_overlay_label(text, center, normal)` — each overlay APPENDS its label text
    (unchanged wording) and the FIRST overlay fixes the shared anchor basis (all overlays sit on
    the same image plane, so any one's center/normal works).
  * `_add_grouped_analysis_overlay_label()` — draws a SINGLE `vtkBillboardTextActor3D` whose text is
    the queued sections joined by a blank line, anchored at the image-plane TOP-RIGHT corner (via
    the camera screen axes, like the old pixel-grid corner anchor) and growing downward. Left/top
    justified so it reads as a stacked list. Out of the way of the spots/grid in the image circle.

`Open3DSceneRefreshService.refresh_scene` resets the collector before the five overlays are added
and draws the one combined legend after. Each section still starts with its own self-describing
title ("Spot RMS map · …", "Camera pixel grid · …", "Astigmatism · tangential (amber) vs sagittal
(blue)", …) and the colour cues are spelled out in words, so a single-colour combined billboard
loses no information. The per-overlay billboard creation + per-overlay anchor math (and the now-dead
pixel-grid top-corner scoring loop) are removed.

Trade-off: the legend is one taller block in a fixed corner rather than labels hugging each
overlay's own geometry — which is exactly what the user asked for (one label, expanding).

## Verified (display-free)
guard `validate_open3d_analysis_overlay_labels` (penta phase 174):
  * FUNCTIONAL — reset clears the collector; queue accumulates in order, locks the anchor to the
    FIRST overlay, skips empty/None text, auto-initialises if reset was skipped; the combined drawer
    is a safe no-op (returns 0, never raises) with no renderer even when sections are queued.
  * SOURCE CONTRACT — the combined drawer joins the sections (`"\n\n".join`) into exactly ONE
    billboard and corner-anchors via `_camera_screen_world_axes`; each of the five overlay methods
    queues its label and NO LONGER references `vtkBillboardTextActor3D`; `refresh_scene` resets
    before and draws the combined label after.
The four affected overlay guards (`validate_open3d_{spot_field_map,pixel_grid,best_focus_surface,
field_resolved_surrogate}`) still PASS (the specs/geometry are unchanged; only label drawing moved).
In-app eyeball owed (the render): enable several overlays and confirm one stacked legend.
