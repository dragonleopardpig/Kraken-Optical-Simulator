# 0302 — Import Vendor Camera from Folder (sensor auto-register + couple)

The user asked for the camera analogue of the imaging-lens folder importer:

> *the Imaging Lens already have import from folder and automatically extract datasheet and STEP file.
> Can you do the same to Camera? I need to import vendor camera in future.*

Point at one vendor **camera folder** (mechanical STEP + datasheet PDF, or a curated `.json` sidecar); the
sensor is scraped, registered as a `CAMERA_DATABASE` record, and the vendor STEP is imported as the camera
body — which couples the surrogate to that sensor (field → sensor half-diagonal, image circle → sensor)
exactly like picking the camera from the dropdown.

## Why this is small
The camera coupling already existed: `camera_model_for_step_path(step_path)` reverse-looks-up a STEP file to a
camera name, and `import_camera_step` → `_couple_camera_model_from_step` → `_apply_camera_coverage_autofill`
sets the detector size, FOV and image-plane snap. So the whole feature reduces to **getting a sensor record
into `CAMERA_DATABASE`** from a folder; the existing import+couple then "just works".

## The engine — `KrakenOS/UI/services/camera_folder_import.py` (NEW, pure/headless)
Mirrors `machine_vision_folder_import` for cameras. `scan_camera_folder` classifies `.step/.stp`, `.pdf`, and
a `.json` **sidecar** (honoured only when it carries a sensor size). Spec sources, in order:

* the vendor **datasheet PDF** spec table is scraped into a `CameraSpec` (~27 fields: sensor W/H/diagonal,
  pixel pitch, resolution, megapixels, spectral range, architecture, shutter, lens mount, body dims, weight,
  frame rate, chroma, bit depths, pixel formats, …);
* a curated **`.json` sidecar** wins when present — the escape hatch for a datasheet whose text cannot be
  extracted (see the ObjStm note below).

`build_camera_record_from_assets` assembles a `CAMERA_DATABASE`-shaped record (derives `sensor_diagonal_mm`,
`image_diameter_mm = max(W,H)`, stores `step_path`/`datasheet` project-relative), and **raises `ValueError`**
when neither source yields a sensor size (no fabricated camera). Best-effort `camera_front_to_sensor_mm` comes
from a mount-standard flange table or a datasheet "sensor distance/FFD" line, else `None` (it lives in the
mechanical drawing, not the spec text) — recorded as a note; sensor size + FOV coupling are unaffected.

### Persistence (Filen-synced, vendor `.py` untouched)
Records are written to `attachment/Cameras/imported_cameras.json` (next to the vendor assets, gitignored) —
**not** edited into the tracked `camera_database.py` literal. `camera_database` folds that registry into
`CAMERA_DATABASE` at import (`_merge_imported_cameras`) and on demand (`refresh_imported_cameras`, called by
the editor handler so a running session picks the camera up with no restart). List fields round-trip back to
tuples and project-relative paths to absolute `Path`s, so an imported record is indistinguishable from a
hand-authored one. **Hand-authored built-ins always win**: an imported camera only ever ADDS a new model.

## PDF extraction — hex-string ToUnicode shows (additive)
The 0293 stdlib extractor (`datasheet_prescription_import.extract_pdf_text`, `zlib` + regex, per-font
ToUnicode CMaps) recovered ~nothing from the Allied Vision hr25MCX datasheet: it uses **HEX-STRING shows**
(`<0031…>Tj` and hex elements inside `[ … ]TJ`) rather than the Schneider PDFs' literal `( … )Tj`. Added
`_decode_hex_show` + a generalized `/Fn Tf` font-resource regex to the existing per-font machinery — hr25 now
decodes its full spec table (1627 chars). The Schneider literal-show path is unchanged (no lens regression).

## Wiring
* `layout_table_workbench.import_vendor_camera_from_folder(folder=None, *, dialog_parent=None,
  refresh_open_3d=True)` — scan → build → persist → `refresh_imported_cameras()` → `import_camera_step(
  path=assets.primary_step, …)`; returns the `ImportedCamera` (or `None` on cancel/failure).
* `import_camera_step` grew an explicit `path=` (skips the file chooser) so the folder handler reuses the full
  overlay-setup + couple without a second dialog (`step_overlay_import.py`, delegate in
  `scene_placement_commands.py`).
* `open3d_inspector.import_vendor_camera_from_folder` — mirrors the camera STEP-overlay scene wiring (marks
  `_stl_placement_dirty` per the 0296 stale-2D invariant, selects the camera component, shows the rotation
  handler, refreshes). Unlike the lens importer this does NOT replace the working layout — it only adds a
  camera overlay — so no layout-swap keep-alive guard is needed.
* Menus: *"Import Vendor Camera from Folder…"* in the 2D right-click **Insert** menu
  (`main_context_menu.py`); *"Import Camera from Folder…"* in the Open 3D **CAD** menu
  (`open3d_top_controls.py`), beside the existing lens folder importer.

## Files
- `KrakenOS/UI/services/camera_folder_import.py` — **NEW**, engine.
- `KrakenOS/UI/services/datasheet_prescription_import.py` — hex-string show support (shared with the lens Path-C importer).
- `KrakenOS/UI/camera_database.py` — `_merge_imported_cameras` / `refresh_imported_cameras` registry hook (`import json`).
- `KrakenOS/UI/services/step_overlay_import.py` + `services/scene_placement_commands.py` — `import_camera_step(path=…)`.
- `KrakenOS/UI/services/layout_table_workbench.py` — `import_vendor_camera_from_folder`.
- `KrakenOS/UI/open3d_inspector.py` — inspector handler.
- `KrakenOS/UI/panels/main_context_menu.py` + `panels/open3d_top_controls.py` — menu commands.

## Verified end-to-end (real Allied Vision hr25MCX assets, no display)
`bugs/diag_camera_folder_import.py` builds the record from the real datasheet+STEP and matches the
hand-authored `CAMERA_DATABASE` entry field-for-field (23 ground-truth checks + registry round-trip, all
PASS): sensor 23.04×23.04, diagonal 32.58, pixel 4.5/4.5, resolution 5120×5120, 25.0 MP, spectral 400–1000,
CMOS global-shutter, mount `M58x0.75`, body 56×70×70, 420 g, mono8/mono10. `bugs/diag_camera_db_merge.py`
confirms the merge (tuple/Path parity, `camera_model_for_step_path` reverse-resolve, built-ins-win).

## Guard + gate
`KrakenOS/UI/validate_camera_folder_import.py` (`run_checks()`) — display-free: a synthetic **sidecar folder**
(deterministic, no vendor asset) exercises classify → build → persist → fold-into-reloaded-`camera_database`
→ `camera_names()` + tuple/absolute-Path parity + `camera_model_for_step_path` reverse-resolve +
built-ins-win + source-less-folder rejection; the **real hr25MCX datasheet** scrape is asserted when the asset
is checked out (skipped, not failed, when absent); plus editor/inspector/menu wiring via source-text asserts.
Penta **phase 265**, baseline updated.

## Notes / remaining
- **ObjStm datasheets** (e.g. the Bopixel BC-Gx25M12X4 spec: compressed object streams + XRef streams) are
  not parseable by the classic extractor and are out of automatic scope; the `.json` **sidecar** beside the
  STEP is the deterministic escape hatch (`build_camera_record_from_assets` prefers it over the PDF).
- `camera_front_to_sensor_mm` is best-effort (mount-standard FFD or a datasheet line); when unknown the
  image-plane axial auto-snap is skipped until the user sets it — sensor size + FOV coupling still apply.
- In-app eyeball owed (the folder-chooser → couple → 3D-render path needs a GLX display; headless VTK
  segfaults under Xvfb llvmpipe).
