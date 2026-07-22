# 0407 — Replace overlay must be per-label (camera sensor location; lens surrogate)

**User's catch on 0406:** "Camera replacement involves sensor location, which means camera location
should be identical to Camera Import, otherwise sensor location will be wrong… two steps: first through
the Camera Import flow, then place it to the current camera location with minor adjustment. The same go
for Imaging Lens where lens surrogate needs to be created."

0406 replaced every imported STEP overlay with one behaviour — a pose-preserving path swap. That is
**correct only for LED / BS**. It is **wrong for a camera** and **wrong for a lens**.

## Why a raw pose swap is wrong for camera + lens

- **Camera:** the sensor sits `camera_front_to_sensor_mm` BEHIND the body's front, and the
  camera↔detector glue places the body so the **sensor** lands on the image plane
  (`_step_overlay_alignment_target_z` = `image_plane_z − front_to_sensor`). A different camera has a
  different `front_to_sensor`, so keeping the OLD pose puts the NEW camera's sensor at the wrong axial
  location. The placement must be re-established the way **Camera Import** does it.
- **Lens:** an imaging lens is an optical **surrogate**, not just CAD — replacing it needs the surrogate
  rebuilt. That is exactly **Swap Imaging Lens from Folder** (which takes a lens *folder*, not a single
  STEP). A raw STEP path swap would leave the surrogate prescription stale.

## Fix — `replace_imported_step_overlay` branches per label

- **LED / BS (optical):** unchanged — a pose-preserving path swap (no sensor-location dependency).
- **camera:** the **two steps** the user described — (1) run the full `import_camera_step` flow so the
  sensor re-locates correctly (`front_to_sensor` + coupling + the image-plane glue), then (2) restore
  the old **transverse** position (x/y) as the minor adjustment. The **axial** position is auto-driven
  by `image_plane_z − front_to_sensor`, so only x/y carry the user's placement.
- **lens:** rejected with a status pointing at **Swap Imaging Lens from Folder**. The overlay right-click
  "Replace … STEP…" entry is also **hidden for a lens**.

## Verification (`validate_open3d_replace_step_overlay`, penta phase 333 — updated)

Behavioural stubs drive the real service:

| check | asserts |
|---|---|
| PRESERVE | a LED/BS replace swaps the path, KEEPS the pose, invalidates/refreshes |
| CAMERA | a camera replace runs `import_camera_step`, restores the old transverse x/y, takes axial z from the import glue (not the old pose) |
| LENS | a lens replace is rejected → status points at Swap Imaging Lens |
| NO-OP | nothing imported → None, path untouched |
| WRAPPER / MENU | editor wrapper delegates; menu offers "Replace … STEP…" **excluding lens** |

6/6 pass; baseline phase 333 stays pass.

## Files

- `KrakenOS/UI/services/step_overlay_import.py` — per-label branch (camera import-flow + transverse
  restore; lens rejection; LED/BS pose-preserve).
- `KrakenOS/UI/services/open3d_face_assignment.py` — hide "Replace … STEP…" for a lens.
- `KrakenOS/UI/validate_open3d_replace_step_overlay.py` — updated guard (phase 333).

## In-app eyeball still owed

Right-click the **camera** → "Replace Camera STEP…" → pick a different camera STEP → the sensor lands at
the correct image-plane location (as if freshly imported), the camera keeping its lateral position. A
lens overlay shows no "Replace … STEP…" (use Swap Imaging Lens from Folder). BS/LED still swap in place
keeping their pose.
