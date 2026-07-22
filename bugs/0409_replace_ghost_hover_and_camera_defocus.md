# 0409 — Replace ghost hover outline + "remove defocus" on the camera menu

Two items from `flag_20260722_153216` (build 96f2e2b6, AZ85 scene — the camera path is now BC-OM25M, so
the 0408 folder replace worked):

## 1. Ghost hover outline on the replaced RA mirror

**Flag:** "There are ghost highlight when mouse hover the 2nd RA mirror, same size but offset from the
body." The screenshot shows the gold "OPTICAL STEP F003 face" outline offset below the pink prism body.

**Root cause (two contributing):**
- The `replace_promoted_optical_solid_step` re-promote used `clear_overlay=False` (default), so the
  **source overlay was left behind**. An original promoted solid has NO overlay (AZ85's
  `optical_step_path` is empty — promotion consumed it), so the leftover overlay's face was what
  hovered — offset from the promoted body. (The "OPTICAL STEP" label is the overlay hover, not the
  promoted solid's.)
- 0405 applied the transverse re-centering with a **raw `desp_x`/`desp_y` set**, which bypasses the
  scene-placement sync + plot-dirty mark, so the promoted solid's own hover could desync too.

**Fix:**
- Re-promote with **`clear_overlay=True`** — the replacement ends with no leftover overlay (matching the
  original promoted state), so there's nothing to ghost.
- Apply the transverse decenter through **`translate_scene_row_pose_vector`** (the sanctioned drag path
  the interactive move uses — syncs scene-placement metadata + marks the plot) instead of a raw `desp`
  set, computing the delta from the current post-promote `desp`.

## 2. "Reset Camera to Image Plane" doesn't remove defocus

**Flag:** "Right click Camera STEP → reset camera to image plane not removing defocus."

"Reset Camera to Image Plane" is the surrogate reset — it clears the camera's drag offsets so the body's
sensor returns to the **current** image plane. It does **not** move the DETECTOR to best focus, so a
defocus gap (detector ≠ best-focus image plane) remains. The user right-clicks the camera (glued to the
detector) expecting to remove defocus.

**Fix:** the camera element menu now also offers **"Snap detector to image plane (remove defocus)"** (the
`snap_detector_to_image_plane` action, same as the detector browser row from 0405), right below "Reset
Camera to Image Plane".

## Verification (`validate_open3d_replace_axis_and_defocus_menu`, penta phase 332 — updated)

| check | asserts |
|---|---|
| REPLACE-AXIS | decenter re-applied via `translate_scene_row_pose_vector` after re-promote; **`clear_overlay=True`** (no ghost) |
| DEFOCUS-MENU | the detector browser row offers "remove defocus" (0405) |
| CAMERA-DEFOCUS | the **camera** menu offers "remove defocus", gated on camera, wired to `_snap_detector_to_image_plane` |

3/3 pass; 0404 replace guard still green; baseline phase 332 stays pass.

## Files

- `KrakenOS/UI/services/step_overlay_promotion.py` — re-promote `clear_overlay=True`; decenter via the
  drag path.
- `KrakenOS/UI/services/open3d_face_assignment.py` — "remove defocus" on the camera element menu.
- `KrakenOS/UI/validate_open3d_replace_axis_and_defocus_menu.py` — updated guard (phase 332).

## In-app eyeball still owed

Replace the RA mirror again → hover it: the gold face outline sits ON the body (no offset ghost).
Right-click the camera → "Snap detector to image plane (remove defocus)" closes the defocus gap.
