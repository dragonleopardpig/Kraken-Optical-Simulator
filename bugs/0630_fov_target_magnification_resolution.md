# 0630 — FOV popup can target System Magnification or Resolution (FEATURE, user request)

User: *"for the FOV popup dialog box, add (1) checkbox to set System Magnification -> auto
solve for FOV and thickness, (2) checkbox to set System Resolution -> auto solve for FOV
and thickness. Both parameters as defined in the HUD."*

## What shipped

Two checkbox rows in the object-plane FOV popup (`_open_quick_estimation_fov_popup`),
below Width/Height:

- **Set Magnification (sensor/FOV):** target |m| -> object field = `sensor / m`.
- **Set Resolution (µm/px):** target r -> object field = `r * N / 1000` per axis (N =
  camera pixel count).

Both are the exact INVERSE of the bugs/0628 HUD formulas, so the derived field round-trips
back to the typed target. Ticking one greys Width/Height and drives the SAME thickness
solve (`_apply_quick_estimation_fov_solve(..., "thickness", ...)`, the bugs/0626-verified
path) -- so the DELIVERED field lands at exactly that magnification / resolution. Each row
is prefilled with the current HUD value, the two are mutually exclusive, and each disables
itself with a hint when its camera datum is absent (magnification needs a sensor size,
resolution needs a registered camera's pixel count). Unticked, the dialog is unchanged.

Conversions live on `QuickEstimationService`: `object_fov_for_magnification`,
`object_fov_for_resolution`, `_camera_pixel_count` -- display-free and guarded.

## Verified

- Guard phase 473 (`validate_open3d_0630_fov_target_modes`): conversions are exact HUD
  inverses (round-trip), degrade without their datum, reject bad targets, and the popup
  wires both modes into its solve.
- Integration (diag_0630_fov_target_dialog.py): through the REAL modal dialog, ticking
  Magnification=0.5 solved for object width 46.08 mm (= sensor 23.04 / 0.5), mode=thickness
  -- the mode superseded the FOV boxes.
- Screenshot: bugs/_0630_fov_target_modes_dialog.png (prefilled 0.8179x / 5.502 µm/px).

## Follow-up: which button (user asked)

A target mode is realised by ONE action -- "Solve for Thickness". "Solve for Image/Sensor
Size" resizes the sensor, which is meaningless when the target is defined BY the fixed
sensor + pixel count, so it is grayed out whenever a magnification/resolution box is
ticked (bugs/_0630_fov_resolution_ticked.png). Width/Height and the other mode gray too,
leaving Solve for Thickness as the single clear action.
