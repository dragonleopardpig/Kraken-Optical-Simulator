# 0311 — After the camera is deleted, the FOV / Max sensor / Image circle overlays remain

Recording `attachment/recorded_bug_repros/flag_20260715_084524_992/` — *"After camera deleted, FOV, Max
Sensor, Image circle remains."*

State snapshot: the camera STEP actor is gone (`step_actor_counts = {lens: 1, led: 1}`, no camera), yet the
green object-FOV cone (**"FOV 39.0×39.0"**), **"Max sensor 23.0×23.0"** and **"Image circle Ø32.6"** overlays
are still drawn. Row 8 (the Image row) still has half-width **16.2917** — the BC-OM25M sensor half-diagonal,
so `Ø32.6 = 2 × 16.29` and the inscribed max sensor `23.05 = 32.6/√2`.

The label reads **"Max sensor"** (not **"Sensor"**), which is the tell: the decouple *did* run and dropped
the detector's explicit vendor sensor — but the coverage overlay still had a non-zero image circle to draw.

## Root cause — the legacy decouple frees the aperture but not the pinned field
Coupling a camera pins the field to **Real Image Height = the sensor half-diagonal**
(`_apply_camera_coverage_autofill`), and *that field* is what drives the image circle / object-FOV overlay
(`detector_coverage_overlay._image_circle_radius` reads `_field_metrics_summary()['field_image_radius']`).

Deleting the camera STEP calls `_decouple_camera_model` (bugs/0296). When the layout **loaded** with a camera
coupled there is no pre-couple stash to restore (the stash is interactive-couple-only), so it takes the 0306
"legacy" branch — which flips the image **aperture** Manual → Auto but **never touches the pinned field**. So
the field stayed at Real Image Height 16.29, and the image circle Ø32.6 + FOV 39×39 lingered after the camera
was gone.

## The fix — un-pin the field on decouple, gated by a couple-set flag
* The couple now stamps `self._camera_pinned_field = True` when it pins the Real Image Height field.
* `_decouple_camera_model`'s legacy (no-stash) branch, **when that flag is set**, calls
  **`_reset_camera_pinned_field_to_default()`** — which resets the field to the object-mode default
  (**Angle 0** for an infinity object, **Object Height 0** for a finite one). With the field back to 0 the
  image radius collapses (`radius > 0` guard fails) and the coverage overlay draws nothing — no camera means
  no coverage.
* Both decouple paths clear the flag; the with-stash path already restores the exact pre-camera field.

The **flag** (not a bare `field_type == "Real Image Height"` test) is what makes this safe:

* a machine-vision **surrogate** that *legitimately* uses a Real Image Height field with **no camera** is
  never wiped (the flag was never set), and
* a user who **manually re-typed** the field while a camera was coupled keeps their choice (the reset helper
  also checks the field is still the camera-set Real Image Height before touching it).

## Together with 0296 / 0306
**0296** decouples the sensor coverage when the camera STEP is deleted; **0306** unlocks the image aperture
Manual → Auto for a legacy (no-stash) file; **0311** finishes the job by also un-pinning the *field* that
drives the image-circle / FOV overlay.

## Verified (display-free)
* `KrakenOS/UI/validate_open3d_camera_delete_field_unpin.py` — **PASS** (13 checks): a camera-pinned legacy
  decouple resets the field (Finite → Object Height 0; Infinity → Angle 0) and clears the flag while keeping
  0306's Manual → Auto; an unpinned surrogate field is untouched; a user override is respected; the real
  couple sets the flag and the with-stash decouple restores + clears it; and the couple/decouple/delete
  wiring is present.
* Existing `validate_open3d_camera_coupling_lifecycle.py` (0296) + `validate_open3d_camera_coupling_persistence.py`
  (0306) still **PASS** (no regression).
* Penta **phase 273** delegates to it; baseline updated (`"273": "pass"`).

## Files
- `KrakenOS/UI/services/layout_table_workbench.py` — `_camera_pinned_field` set in
  `_apply_camera_coverage_autofill`; `_decouple_camera_model` gates the reset on it (both paths clear it);
  new `_reset_camera_pinned_field_to_default`.
- `KrakenOS/UI/validate_open3d_camera_delete_field_unpin.py` — new display-free guard.
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_273_camera_delete_field_unpin`.
- `tools/penta_validator_baseline.json` — phase 273 baseline.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): open a layout that loaded with BC-OM25M coupled, delete the
  camera STEP, and confirm the green FOV cone + "Max sensor" + "Image circle" overlays all disappear.
