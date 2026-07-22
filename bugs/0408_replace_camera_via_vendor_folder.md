# 0408 — Replace Camera must use the vendor FOLDER flow (flange prompt + front_to_sensor)

**User's catch on 0407:** "When I click Replace Camera, it should let the user select a folder (same as
camera import). Now it is still asking for a STEP file. I imported BC-OM25 camera — by right it should
prompt me for the camera flange distance, but it does not (after selecting the camera STEP file)."

## Root cause

0407 wired the camera Replace to `import_camera_step` (a single-STEP import). But the user's actual
"Camera Import" is `import_vendor_camera_from_folder` — the FOLDER flow that:

1. Prompts for a camera **folder** (STEP + datasheet).
2. Scrapes the sensor size.
3. **Prompts for the flange-to-sensor optical distance** when the datasheet lacks it (bugs/0309 —
   BC-OM25M = 12 mm, carried only in the mechanical drawing) → sets `camera_front_to_sensor_mm`.
4. Registers the sensor, then imports the STEP body, which reverse-resolves `front_to_sensor` so the
   sensor snaps to its true axial location (`image_plane_z − front_to_sensor`).

`import_camera_step` alone does **none** of steps 1–3 — so Replace asked for a STEP file and never
prompted for the flange, leaving `front_to_sensor` unset and the sensor mislocated.

## Fix

**`replace_camera_from_folder(folder=None)`** (new, on `LayoutTableWorkbenchMixin`, next to
`import_vendor_camera_from_folder`) — the camera analogue of Swap Imaging Lens from Folder:

1. Capture the old **transverse** placement (x/y).
2. Run `import_vendor_camera_from_folder` (folder chooser + flange prompt + `front_to_sensor` +
   sensor coupling) — the sensor now locates correctly.
3. Restore the old transverse x/y as the minor adjustment (axial z stays auto-driven by
   `image_plane_z − front_to_sensor`).

**Routing:** the right-click handler sends a **camera** to `replace_camera_from_folder` (no STEP dialog);
LED / BS / optical still swap a single STEP keeping the pose. The menu label for a camera now reads
**"Replace Camera from Folder…"**. `replace_imported_step_overlay` **rejects** a stray STEP-path camera
call (points at the folder flow).

## Verification (`validate_open3d_replace_step_overlay`, penta phase 333 — updated)

Behavioural stubs drive the real service methods:

| check | asserts |
|---|---|
| PRESERVE | LED/BS replace swaps path, keeps pose, invalidates/refreshes |
| CAMERA-REJECT | a STEP-path camera replace is rejected → status points at Replace Camera from Folder |
| CAMERA-FOLDER | `replace_camera_from_folder` runs the vendor FOLDER import (flange + `front_to_sensor`) then restores the old transverse x/y (axial z from the import) |
| LENS | rejected → Swap Imaging Lens from Folder |
| NO-OP / WRAPPER / MENU | nothing-imported no-op; editor wrapper delegates; menu = camera "from Folder", LED/BS STEP, lens excluded |

7/7 pass; baseline phase 333 stays pass.

## Files

- `KrakenOS/UI/services/layout_table_workbench.py` — `replace_camera_from_folder` (folder flow + transverse restore).
- `KrakenOS/UI/services/step_overlay_import.py` — reject a STEP-path camera replace (route to the folder flow).
- `KrakenOS/UI/services/open3d_face_assignment.py` — handler routes camera → folder flow; menu label "Replace Camera from Folder…".
- `KrakenOS/UI/validate_open3d_replace_step_overlay.py` — updated guard (phase 333).

## In-app eyeball still owed

Right-click the **camera** → **"Replace Camera from Folder…"** → pick a camera **folder** (e.g. BC-OM25):
it prompts for the flange distance (if the datasheet lacks it), registers the sensor, and the sensor
lands at the correct image-plane location, keeping the camera's lateral position.
