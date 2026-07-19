# 0351 — Normal-to-Sensor hidden geometry remains hover-pickable

**Status:** Fixed (2026-07-19).
**Reported via:** `recording_20260719_081955.json`, flags
`flag_20260719_081736_555` and `flag_20260719_081909_365`.

## Symptom

**Overlays ▸ Normal to Sensor** correctly removed the camera, LED, lens, rays, and other off-plane
geometry from the detector view. Their projected locations nevertheless remained interactive:
hovering showed a crosshair and tooltip and reconstructed a gold translucent face from an invisible
body. The first flag described the hidden camera; its saved hover state was LED face `F009` after a
prior camera `F038` hit. The second flag captured LED face `F002`. Both gold outlines were near the
LED (`z≈200`), far from the detector (`z≈657`).

## Root cause

Sensor isolation changed only each VTK actor's `Visibility`. Passive hover deliberately falls back
to camera-ray tests against cached STEP and CAD/STL face geometry when the normal VTK picker has no
actor. Those cached pickers knew about the browser's persistent hidden sets, but not actors hidden
temporarily by Normal-to-Sensor. They therefore returned an invisible face, and hover created a new
visible gold overlay after isolation had finished.

## Fix

- A registered STEP or CAD-row body whose live actors are all invisible is now inert to cached
  face-ray picking. Unknown/no-actor cases remain eligible, preserving the intentional transparent
  and transient-body fallbacks.
- Off-plane actors become non-pickable for the isolation lifetime. Their original pickability is
  recorded and restored exactly, including props that were non-pickable before entering the view.
- Off-plane move/rotate handles in the always-on-top gizmo layer are isolated too, and selecting an
  invisible component in the scene tree cannot rebuild its body or handles over the detector.
- Entering or reapplying Normal-to-Sensor clears any stale face outline, tooltip, and pick cursor.
- Persistent browser-hidden state is untouched; temporary isolation does not leak into the saved
  `_hidden_step_labels` or `_hidden_scene_rows` sets, and restore cannot override those saved hides.

## Verification

`validate_open3d_normal_to_sensor_isolation` (comprehensive phase 245) now covers the recorded LED
and camera STEP cases plus the promoted CAD-row fall-through. It verifies hide/non-pickability,
cached-pick rejection, stale-hover cleanup, exact restoration, idempotent reinvocation, and
post-rebuild reapplication. The existing browser hide/unhide/delete regression also passes under
Xvfb.
