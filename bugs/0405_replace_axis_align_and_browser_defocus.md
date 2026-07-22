# 0405 — Replace axis-alignment + browser defocus snap (two 0404 follow-ups)

Two flags on the AZ85 RA-mirror scene (build `7a4bedb9`) confirming 0404 Replace **and** the defocus
snap **work**, each with a usability note.

## 1. Resized replacement drifted off the optical axis

**Flag `flag_20260722_142908`:** "Replace the second RA mirror with a bigger one works, but need to
manually align it to the optical axis."

The 0404 Replace preserves the overlay placement offset. A bigger/smaller replacement has a different
intrinsic mesh center, so the same offset lands its center — and its reflecting face — off the axis,
forcing a manual nudge.

**Fix:** `replace_promoted_optical_solid_step` now captures the old solid's **transverse decenter**
(`desp_x`/`desp_y`) BEFORE unpromote (which deletes the row), and re-applies it to the replacement row
AFTER the re-promote. A resized mirror keeps the optical-axis alignment the user set — its center stays
where the aligned old one was, instead of drifting by the mesh-center difference. (Axial position still
follows the new geometry, the small along-axis nudge the Swap philosophy already accepts; fine
reflecting-face alignment on a very different mirror may still want a touch-up — center-matching is the
robust general improvement.)

## 2. Removing defocus required hiding the camera first

**Flag `flag_20260722_143106`:** "Remove defocus works. One thing not convenient, I need to hide the
camera → right click the detector to select defocus."

"Snap detector to image plane (remove defocus)" lived only on the **3D** detector (Image-plane)
right-click, and the camera STEP body occludes the detector in the 3D view — so the user had to hide
the camera to reach it.

**Fix:** the detector (final `Image` row) now offers **"Snap detector to image plane (remove defocus)"**
in the right-hand **Scene Components browser** menu (gated on the `Image` surface row), wired to the
inspector's `_snap_detector_to_image_plane`. No 3D occlusion, no camera-hide — right-click the detector
in the tree.

## Verification (`validate_open3d_replace_axis_and_defocus_menu`, penta phase 332)

Display-free:

| check | asserts |
|---|---|
| REPLACE-AXIS | `old_desp_xy` captured BEFORE unpromote; both `desp_x`/`desp_y` re-applied AFTER re-promote |
| DEFOCUS-MENU | the browser element menu offers "remove defocus" gated on the `Image` row, wired to `_snap_detector_to_image_plane` |

2/2 pass; the 0404 replace guard still passes (capture-before-unpromote ordering intact). Baseline
records phase 332 = pass.

## Files

- `KrakenOS/UI/services/step_overlay_promotion.py` — capture + re-apply the transverse decenter on Replace.
- `KrakenOS/UI/panels/open3d_step_admin.py` — "remove defocus" on the detector browser row.
- `KrakenOS/UI/validate_open3d_replace_axis_and_defocus_menu.py` — guard (phase 332).

## In-app eyeball still owed

Replace the RA mirror with a **different-size** RA-mirror STEP → it lands on the optical axis (no manual
transverse nudge). Right-click the **detector row in the Scene Components tree** (camera still visible) →
"Snap detector to image plane (remove defocus)" is there.
