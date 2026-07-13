# 0295 — "Import Lens from Folder" builds an incomplete machine-vision surrogate

Flag `attachment/recorded_bug_repros/flag_20260713_134717_389/`. After importing the PYRITE
`5.6/80/1.0x` lens folder (datasheet-only, the 0293 Path C) **and** a camera STEP, the scene is only
*partly* set up. The user:

> the Object Plane not showing FOV, just a big circular plane even camera is imported. The image plane is
> not located at the camera sensor. The Field parameters are not set (Finite Conjugate, F-number, etc)
> according to the lens. Rays launching parameters are not set as well (only center ray). The whole import
> from folder --> create lens surrogate seems not complete, only done partially. We need to establish
> complete process flow. Meaning after lens imported, surrogate created, it must synchronize with the
> subsequent camera imported, etc. Final look should be same as those found in other machine vision lens.

## Root cause
The datasheet path `machine_vision_folder_import._core_from_datasheet_cardinals` built its settings as a bare
`{"object_mode", "wavelength"}` dict (was line ~900) — **no field**. Every hand-authored `machine_vision_*`
preset (compare `machine_vision_150mm_datasheet_1x.py:3-21`) carries `field_type` / `field_value` /
`field_count` **and** the `camera_*` keys. Without a field:

- `DetectorCoverageOverlayService._image_circle_radius()` reads `editor._field_metrics_summary()`, which
  returns no image radius → `detector_coverage_overlay` line ~583 `sys_image_radius is None` → the
  object-FOV-rectangle loop `continue`s → the object plane falls back to a plain **disc** (complaint #1).
- the trace has one field point → only the **on-axis** ray fan launches (complaint #4).
- "Field parameters not set" is literally that dict (complaint #3).

The image plane / camera-sensor coupling (complaints #2, #5) is a *second* gap: Path C never writes the
`camera_model` / `camera_step_path` keys, and the image plane is placed only by the finite-conjugate
`image_gap`, with `image_diameter` from the datasheet **image circle** (the lens's *max* sensor capability =
100 mm here, not the actual sensor) — so nothing sizes/moves it to the real camera sensor.

## Fix — staged

### Stage 1 (this change) — complete the surrogate itself
`_core_from_datasheet_cardinals` now sets, when an image radius is known:

- `field_type = "Real Image Height"`
- `field_value = image_diameter / 2` — i.e. the datasheet **max real image height** (image-circle/2 = 50 mm
  for PYRITE; the honest datasheet default, since the datasheet lists a 100 mm max sensor). When no image
  circle is on the datasheet it falls back to the lens-aperture radius, so no datasheet lens is field-less.
- `field_count = 3` — on-axis + 2 off-axis fans, matching the presets.

Result: the object plane draws a real **FOV rectangle** (bare-lens inscribed square of the image circle,
`70.7 × 70.7 mm` for PYRITE) and off-axis rays launch — the "final look" of the hand-authored presets. F#
and finite-conjugate object gap were already set.

### Stage 2 (next) — synchronize with the imported camera
When a camera is present/glued, drive `image_diameter_mode = "Auto"` + the camera sensor so the **image plane
lands on / sizes to the sensor** and `field_value` is overridden by the true sensor half-height (the FOV then
shrinks from the 100 mm datasheet capability to the real sensor). This is the "complete process flow …
synchronize with the subsequent camera" the user asked for. Needs an in-app (NVIDIA GLX) eyeball.

## Guard + gate
`KrakenOS/UI/validate_open3d_folder_import_completeness.py` (`run_checks()`) — display-free + portable (drives
`_core_from_datasheet_cardinals` + the coverage-overlay geometry; no VTK, no vendor PDF/STEP):

- **A** the surrogate core sets `field_type` / `field_value` (== image-circle/2) / `field_count` ≥ 2;
- **B** fed that field, `detector_coverage_overlay_specs` emits an `object_fov_rect` with a positive extent;
- **C** a datasheet lens with no image circle still gets a field (from the aperture).

Confirmed FAIL against the pre-fix engine (A/B/C fail: `field_value None`, object FOV `0.0×0.0`) and PASS
after. Penta **phase 259** (`phase_259_folder_import_completeness`), baseline updated (+"259").

## Owed / limitation
Stage 1 is verified headless (field settings + FOV-rect geometry). The **rendered** FOV rectangle + off-axis
rays and the **Stage 2** camera-sensor sync need the in-app NVIDIA GLX eyeball (re-import the lens folder;
the persisted `common_optical_layouts/machine_vision_pyrite_56_80_…py` was regenerated with the field, but a
fresh import is the real path). The image-plane-at-sensor coupling is Stage 2, not yet shipped.
