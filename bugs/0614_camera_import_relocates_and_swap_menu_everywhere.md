# 0614 — Camera IMPORT still relocates the body; swap offered on every STEP right-click (FIXED)

Flag `flag_20260812_114828_832`, build `51ac2022`: *"camera still relocate after
importing camera. Actually, I want to swap camera, can make right click to each STEP
component and offer swapping option?"* The screenshot shows the fold leg's sensor
overlays with NO camera body anywhere near them.

## Part 1 — the import flow was the remaining dislocation door

bugs/0612 seated the REPLACE flow only. The user used the plain toolbar import
("Import Camera from Folder..."), which is `import_vendor_camera_from_folder` →
`import_camera_step` — and `import_camera_step` **zeroes every placement offset**
(rotations, axis offset, `camera_step_placement_offset_xyz`). Measured with the
same-camera no-op probe: body-to-sensor vector went (0, 0, −25.3) → (−179.8, 0, +25.3)
— **186.8 mm**: the transverse glue offset (x = 179.8, holding the body on the fold
leg) wiped, AND the axial sign flipped to the 0220 straight-axis default. That run
also recorded the 0608 re-measure at **+81.6%** — a dislocated body poisons the
real-ray probe (clear-aperture stops vignette), so seat order matters.

**Fix:** the bugs/0612 seat (traced-beam, fold-aware, transverse-keep fallback on
refusal) moved INTO `import_vendor_camera_from_folder` — after `import_camera_step`,
BEFORE the 0608 re-measure. `replace_camera_from_folder` now simply delegates; one
flow owns seating for both the toolbar import and the right-click replace.

Verified: same-camera IMPORT and same-camera REPLACE are both placement no-ops
(drift < 2 mm, same side) on the frozen Apo75 — guard phase 464 runs both flows.

## Part 2 — "right click each STEP component → swap" (feature)

The swap/replace entries moved from the canvas-only menu block into
`append_element_context_actions` — the branch SHARED by the 3D-canvas right-click and
the Scene Components tree, so both surfaces now offer, per label:

- **camera** → "Replace Camera from Folder..." (the vendor-folder flow; flange prompt
  + front_to_sensor + seat — bugs/0408/0612/0614);
- **led / optical (BS)** → "Replace {NAME} STEP..." (single-STEP swap, pose kept);
- **lens** → NEW "Swap Imaging Lens from Folder (keeps scene)..." — the lens was
  deliberately excluded from the plain replace (it must rebuild the optical surrogate,
  bugs/0378); it now routes to `swap_imaging_lens_from_folder` via the inspector
  wrapper. Direct commands, no cascades (the bugs/0320 VTK-menu lesson).

Guard re-derivations: phase 333 (`validate_open3d_replace_step_overlay`) — the menu
contract now inspects the shared branch (both surfaces), asserts the lens swap entry
and its routing, and the camera-folder check pins DELEGATION (replace keeps the
import's seated placement instead of restoring stale transverse numbers). Phase 464
extended with the import-flow leg.
