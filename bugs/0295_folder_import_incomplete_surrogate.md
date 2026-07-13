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

### Stage 2 (this change) — synchronize with the imported camera sensor
**Root cause of the "no sync":** the app already has a sensor-sync engine —
`layout_table_workbench._apply_camera_coverage_autofill()` sets the image-surface aperture to the sensor
**diagonal** and overrides `field_type='Real Image Height'` / `field_value` = sensor **half-diagonal**
(`camera_image_coverage_mm`), and it fires on both the camera dropdown (`_on_camera_model_changed`) and layout
load. But `step_overlay_import.import_camera_step()` only stashed `imported_camera_step_path`; it never
associated a camera **model**, so the autofill never ran on a raw STEP import → the surrogate kept the
datasheet field and the FOV never followed the sensor.

Fix (general, all four DB cameras): `camera_database.camera_model_for_step_path()` matches an imported STEP
back to its vendor camera (resolved path, then case-insensitive filename — the stable vendor id). New
`_couple_camera_model_from_step()` sets `camera_model_var` + runs the existing autofill.
`import_camera_step()` calls it, so importing the vendor camera STEP now behaves exactly like picking that
model from the dropdown: the field **shrinks from the datasheet max (image-circle/2 = 50 mm for PYRITE) to the
real sensor half-diagonal (hr25MCX = 16.29 mm)** and the object FOV follows the sensor (70.7 → 23.0 mm).

### Stage 2b (this change) — snap the image/detector plane onto the camera sensor
**Not new placement code — an *unblocking*.** The axial snap already lives in the display layer:
`layout_polyline_display._transformed_imported_camera_step_mesh` places the body at
`camera_front_z = _camera_track_image_plane_z() - _current_camera_front_to_sensor_mm()  # bugs/0220`, so the
sensor (front face + the body's physical flange) lands **on** the image plane. It was dormant on a raw STEP
import for exactly the same reason as Stage 2a: with no camera **model** coupled, `_current_camera_record()`
is `None` → `_current_camera_front_to_sensor_mm()` returns **0.0** → the body is placed with its *front face*
on the image plane, leaving the real sensor its full flange (hr25MCX = **11.48 mm**) *behind* the plane
(complaint #2). Stage 2a's model coupling now feeds the real flange in, so the same bugs/0220 formula snaps the
sensor onto the plane automatically (`delta 11.48 → 0.00 mm`). No hand-tuned
`camera_step_placement_offset_xyz`, no new nudge — the physics/placement was already correct; it just needed
the model. (The presets' explicit offset is for hand-authored scenes that never run the STEP-import coupling.)

## Guard + gate
`KrakenOS/UI/validate_open3d_folder_import_completeness.py` (`run_checks()`) — display-free + portable (drives
`_core_from_datasheet_cardinals` + the coverage-overlay geometry + the camera model/coverage lookups; no VTK,
no vendor PDF/STEP):

- **A** the surrogate core sets `field_type` / `field_value` (== image-circle/2) / `field_count` ≥ 2;
- **B** fed that field, `detector_coverage_overlay_specs` emits an `object_fov_rect` with a positive extent;
- **C** a datasheet lens with no image circle still gets a field (from the aperture);
- **D** (Stage 2a) the vendor camera STEP filename resolves back to its model, an unknown STEP does not
  falsely couple, and coupling shrinks the field (50 → 16.29 mm) so the object FOV follows the sensor
  (70.7 → 23.0 mm).
- **E** (Stage 2b) drives the **real** `LayoutPolylineDisplayMixin._current_camera_front_to_sensor_mm` on a
  minimal stub (only `camera_model_var`): uncoupled reads flange **0** and leaves the sensor its full flange
  *behind* the image plane (`11.48 mm off`); coupling feeds the body's real flange (**11.48 mm**) so the
  bugs/0220 placement snaps the sensor onto the plane (`delta 0.00 mm`).

Confirmed FAIL against the pre-fix engine (A/B/C fail: `field_value None`, object FOV `0.0×0.0`) and PASS
after (all A–E). Penta **phase 259** (`phase_259_folder_import_completeness`, title broadened to cover the
camera sync + image-plane snap), baseline title updated.

## Owed / limitation
Stage 1 (field settings + FOV-rect geometry), Stage 2a (STEP→model coupling → FOV-follows-sensor) and Stage 2b
(model coupling → image-plane-snaps-onto-sensor via the pre-existing bugs/0220 placement) are verified headless.
The **rendered** FOV rectangle + off-axis rays and the **rendered** axial snap still need the in-app NVIDIA GLX
eyeball — re-import the lens folder, then import the vendor camera STEP, and confirm the FOV rectangle shrinks to
the sensor and the sensor sits on the image plane. The persisted
`common_optical_layouts/machine_vision_pyrite_56_80_…py` was regenerated with the field, but a fresh import is
the real path.
