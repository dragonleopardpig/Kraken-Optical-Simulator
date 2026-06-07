# 0026 — Hiding a camera/lens STEP from the browser leaves residual

**Status:** Fixed (2026-06-07).
**Component:** Open 3D scene-component browser hide/unhide
(`KrakenOS/UI/open3d_inspector.py`).
**Reported via:** the in-app bug recorder —
`attachment/recorded_bug_repros/flag_20260607_200418_156/` ("Hiding the camera
STEP leaves residual."), and the user added "same goes to the lens".

## Symptom

Right-click → Hide on an imported camera or lens STEP overlay removed the body
mesh but left a residual in the scene: the feature-edge silhouette and (when the
element was selected) the rotation-handle gizmo stayed visible.

## Root cause

An imported STEP overlay's actors register across several maps, but the new
hide (bugs 0025 follow-up) only consulted `_step_actor_map[label]`:

* **body** mesh — added with `pick_step_label` → `_step_actor_map[label]` ✓ hidden.
* **feature edges** (two silhouette actors) — added with only
  `follow_step_label` → `_actor_step_follow_map` / `_step_follow_actor_map`, *not*
  `_step_actor_map` → missed.
* **rotation-handle gizmo** (when selected) — `_actor_step_rotate_map`
  (keyed `(label, axis, angle)`) → missed.

So the body vanished but the edges + gizmo remained. The same applied to any
imported STEP label (camera, lens, optical, led).

## Fix

`_all_actor_keys_for_step_label(label)` now unions every actor tied to the label
across all the maps — `_step_actor_map`, `_step_follow_actor_map`, the
`_actor_step_map` / `_actor_step_follow_map` reverse maps, and the
`_actor_step_rotate_map` gizmo handles (matched on the label element of the
tuple). `_all_actor_keys_for_row(row)` likewise unions `_row_actor_map` with the
`_actor_row_map` reverse. `set_step_label_hidden`, `set_scene_rows_hidden`, and
`_apply_scene_element_visibility` all use these, so hide/unhide and the
post-refresh re-apply cover the whole element. Labels are normalised to
lower-case to match how the overlays register.

## Result

On the measured machine-vision layout the camera/lens each had two edge actors
the old hide missed; selecting the camera added its gizmo handles. Hiding now
turns **all 15** of the selected camera's actors invisible — body, edges, and
gizmo. PNG-verified: hiding the camera leaves only the rays and the object-side
dimension arrow, no residual.

## Tests

`KrakenOS/UI/validate_open3d_scene_browser_hide_delete.py` (harness Phase 35)
gains source contracts that `_all_actor_keys_for_step_label` /
`_all_actor_keys_for_row` exist and that `set_step_label_hidden` +
`_apply_scene_element_visibility` use the comprehensive gather (not the
body-only `_step_actor_map`).
