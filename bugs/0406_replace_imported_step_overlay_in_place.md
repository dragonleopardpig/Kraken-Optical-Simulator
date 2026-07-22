# 0406 — Replace an imported STEP overlay (camera / BS / LED) in place

**Feature:** the second half of the user's "delete/import the RA mirror / camera / BS on the spot" ask.
0404 did the **promoted optical solid** (RA mirror). 0406 does the **imported STEP overlays** — camera,
BS (LED-glued), LED, and a non-promoted optical STEP.

## Why the overlay case is a clean path swap

An imported STEP overlay carries its geometry in `imported_<label>_step_path` plus a pose
(`<label>_step_rotation_*`, `_axis_offset_xy`, `_placement_offset_xyz`). A **fresh import** RESETS that
pose to zero. So replacing an overlay in place is just a **pose-preserving path swap** — exactly the
principle behind Swap Imaging Lens (`_apply_swapped_lens_step_settings`): swap the STEP, keep where the
user put it. No unpromote/promote round trip (unlike the promoted-solid 0404 path).

## Fix

**`replace_imported_step_overlay(label, new_step_path)`** (service, with an editor mixin wrapper):

1. No-op when no STEP of that label is imported (nothing to replace).
2. Set `imported_<label>_step_path` = the new file.
3. **Preserve** the pose (rotation / axis offset / placement offset) and glue — do NOT reset them.
4. A **camera** replacement additionally re-couples the surrogate sensor when the new STEP is a
   recognised vendor camera (that's the point of swapping a vendor camera — field + image circle follow
   its sensor), reported in the status.
5. Mirror the import-time invalidation (`clear_step_overlay_physics_preview`,
   `_live_step_overlay_trace_plan_cache = {}`, `_invalidate_preview_scene_trace`), one history step, and
   refresh (camera-only for a camera, else per-label).

**Menu:** right-click an imported STEP overlay → **"Replace {Camera/BS/LED/Optical} STEP…"** (in the
overlay's face-pick context menu, for both decoration overlays and a pickable optical overlay); the
handler prompts for a STEP file and calls the editor's replace method.

### The mixin-wrapper trap (again)

Like 0404, the service method needed an explicit editor wrapper delegating to the service, or the
right-click would silently no-op through tkinter `__getattr__`
(`reference_editor_mixin_service_wrappers`).

## Verification (`validate_open3d_replace_step_overlay`, penta phase 333)

Display-free — a **behavioural stub** drives the real service method (no live editor / renderer):

| check | asserts |
|---|---|
| PRESERVE | replace swaps the path, KEEPS a pre-set pose attr (rotation + offset), invalidates/refreshes, returns the new path |
| NO-OP | nothing imported → returns None, path untouched |
| NO-RESET | the service source never zeroes the pose |
| WRAPPER | the editor exposes the method and delegates to the service (mixin-wrapper trap) |
| MENU | "Replace … STEP…" → `_replace_step_overlay_from_context` → editor's replace method |

5/5 pass; baseline records phase 333 = pass.

## Files

- `KrakenOS/UI/services/step_overlay_import.py` — `replace_imported_step_overlay` (service).
- `KrakenOS/UI/services/scene_placement_commands.py` — editor mixin wrapper.
- `KrakenOS/UI/services/open3d_face_assignment.py` — "Replace … STEP…" menu entry + handler.
- `KrakenOS/UI/validate_open3d_replace_step_overlay.py` — guard (phase 333).

## Scope / next

Replace-in-place is now complete for both element kinds: promoted optical solids (0404) and imported
STEP overlays (0406). A camera replacement re-couples the sensor by design; if a user wants to swap only
the CAD body and keep the current sensor, that's a possible option/flag later. Face flags / clear-aperture
picks on an overlay are tied to face ids, so a very different replacement STEP may need re-picking (the
pose + glue survive regardless).

## In-app eyeball still owed

Right-click the camera (or the BS) in the 3D scene → "Replace … STEP…" → pick another STEP → the body
swaps in at the same pose (a recognised vendor camera also re-syncs the sensor).
