# 0309 — Ask for the camera flange-to-sensor distance when the datasheet hides it in a drawing

Recording `attachment/recorded_bug_repros/flag_20260715_075815_948/` — after importing the BC-OM25M
camera (via **0307**'s folder importer), *"the sensor location is not at the camera physical sensor
location. … the optical distance is 12 mm, the information is labelled in one of the picture, not the
table. **Is the PDF extraction able to read this information?**"*

## Answer: no — the 12 mm is unrecoverable from either source
* **Not in the PDF text.** The 12 mm flange-to-sensor (optical) distance appears only as a **dimension
  in the mechanical DRAWING** (a figure), not in the spec table. The extractor sees no "optical /
  distance / flange / back focal" words; the only "12" in the text is the model name (`BC-OM25M12X2`).
* **Not in the STEP.** The housing models the ~24 mm-deep **mount cavity** but not the sensor body — the
  sensor floats 12 mm behind the flange per the drawing, with no geometry to key on.

So `build_camera_record_from_assets` leaves `camera_front_to_sensor_mm` unset,
`_current_camera_front_to_sensor_mm` reads **0**, and `camera_front_z = image_plane_z − 0` seats the
sensor / image plane **on the mount face** instead of 12 mm behind it.

## The fix — ask the user at import time (user-approved)
`import_vendor_camera_from_folder` now prompts for the value **after building and before persisting**
the record, but only when it could not be scraped:

* **`_prompt_camera_flange_distance(imported, parent)`** — a `simpledialog.askfloat` dialog that explains
  the value lives only in the mechanical drawing (with the BC-OM25M = 12 mm example) and that Cancel /
  blank simply skips it (sensor size + FOV coupling are unaffected; only the axial image-plane snap is
  skipped). The `askfloat` call is guarded so a dialog hiccup can never abort the import.
* **`_apply_camera_flange_distance(imported, value_provider)`** — the **pure** decision (the provider is
  injected, so it is display-free-testable): it stamps `camera_front_to_sensor_mm` on the record only
  when the value is **missing** and a **positive finite** number is supplied, appends an audit note, and
  **never re-prompts or overwrites** a scraped value.

Because the value is stamped **before** `write_imported_camera` + `refresh_imported_cameras`, it
persists to `imported_cameras.json`, folds into the live `CAMERA_DATABASE`, and immediately drives
`_current_camera_front_to_sensor_mm` → `camera_front_z = image_plane_z − value` — so the sensor lands at
its true axial location.

## Together with 0308
**0308** faces the mount toward the beam; **0309** sets how far behind that mount face the sensor sits.
Both are needed for BC-OM25M's sensor to render at the real, datasheet-correct location.

## Verified (display-free)
* `KrakenOS/UI/validate_open3d_camera_flange_prompt.py` — **PASS** (11 checks): the apply decision
  (stamp-when-missing / never-overwrite / reject bad input / Cancel-safe), the value reaching the real
  `_current_camera_front_to_sensor_mm`, the build→prompt→persist ordering, and the **real BC-OM25M**
  scrape (genuinely missing → the prompt fires; entering 12 mm sticks).
* Penta **phase 271** delegates to it; baseline updated (`"271": "pass"`).

## Files
- `KrakenOS/UI/services/layout_table_workbench.py` — `_prompt_camera_flange_distance` +
  `_apply_camera_flange_distance`; `import_vendor_camera_from_folder` calls the prompt between building
  and persisting the record.
- `KrakenOS/UI/validate_open3d_camera_flange_prompt.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_271_camera_flange_prompt`.
- `tools/penta_validator_baseline.json` — phase 271 baseline.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): Open 3D → Import Camera from Folder →
  `attachment/Cameras/BC-OM25M`, enter **12** at the prompt, and confirm the sensor / image plane snaps
  12 mm behind the (now correctly-oriented, 0308) mount face.
