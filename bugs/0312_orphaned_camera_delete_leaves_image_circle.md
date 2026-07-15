# 0312 — After deleting an *orphaned* camera, the FOV / Max sensor / Image circle overlays remain

Recording `attachment/recorded_bug_repros/flag_20260715_092801_523/` — *"Camera deleted, clicked Trace,
still the same, FOV, Max Sensor and Image Circle remains."*

This is a **0311 resurface**. 0311 fixed the case where a camera-coupled layout is deleted, but gated the
field un-pin on `_camera_pinned_field` — a flag set **only** by `_apply_camera_coverage_autofill`. There is
a real path where the field is left at Real Image Height but that flag is never set, so 0311's reset was
skipped and the overlay lingered.

The companion recording `flag_20260715_092921_426` — *"the sensor and image plane successfully snap to the
correct location of the imported camera (after input 12 in the pop-up dialog)"* — is a **positive
confirmation that 0310 works** (camera body z=[645.09, 678.32], sensor row 8 at z=657.09 = 12 mm behind the
mount). Same recording session; 0310 good, 0312 the remaining defect.

## Root cause — an *orphaned* camera loads with the flag off but the field still pinned
Imported-camera registries are **per-machine** (`imported_cameras.json` is not synced; the cross-machine
workflow moves the scene `.py` + the git branch, not the JSON). So a layout saved on machine A with
`camera_model = "BC-OM25M"` coupled, reopened on machine B that never imported that camera, hits
`camera_record("BC-OM25M") is None` → `camera_is_valid = False` in `_apply_layout_settings`
(`services/layout_settings.py`). That path:

* forces `camera_model_var` → **None** (the model is dropped), and
* therefore the load-time coverage autofill (`layout_table_workbench.py:535-538`, which is the *only* thing
  that sets `_camera_pinned_field = True`) **never runs**,

**but** the saved **Real Image Height 16.2917** field (= the sensor half-diagonal) and the Manual image
aperture **Ø32.583** (= the sensor diagonal) are still restored from the row snapshot. So the still-shown
camera STEP is deleted → `_decouple_camera_model` takes the legacy (no-stash) branch with the flag **False**
→ 0311's reset is skipped → the field stays Real Image Height 16.29 → `_image_circle_radius` still reads
16.29 → the green object-FOV cone + "Max sensor" + "Image circle Ø32.6" stay on screen.

### Why the flag couldn't just be set on load
`LayoutTableWorkbenchMixin._apply_layout_settings` **delegates** to `LayoutSettingsService`
(`layout_table_workbench.py:1168`). That service's `__setattr__` routes any `_`-prefixed attribute to
`object.__setattr__(self, …)` — i.e. onto the **service instance**, not the editor. So setting
`self._camera_pinned_field = True` inside the service is dead: it never reaches the editor. (The same
delegation quietly defeats the 0306 stash-restore-on-load; the valid-camera reload only works because the
load-path autofill sets the flag on the *editor* directly.) Setting the flag from the load path is the wrong
layer.

## The fix — recognise the camera pin by its VALUE signature, editor-side, flag-independent
Per *"when a class recurs, guard the invariant, not the instance"* (this decouple class has now recurred
4×: 0296 / 0306 / 0311 / 0312), the reset is no longer gated on the fragile flag alone.
`_apply_camera_coverage_autofill` leaves a unique, camera-only fingerprint that `camera_image_coverage_mm`
makes exact — it returns `(diagonal, 0.5 · diagonal)`, so:

> **image aperture is Manual, field is Real Image Height `v`, and the Image-surface clear aperture `= 2·v`
> (the sensor diagonal).**

New editor-side helper `_field_matches_camera_autofill_signature()` tests exactly that (`|image_diameter −
2·field_value| ≤ max(0.05, 2e-3·image_diameter)`). `_decouple_camera_model`'s legacy branch now un-pins when
`_camera_pinned_field` **or** that signature holds. Because the 0306 Manual→Auto flip rewrites the aperture
mode that is *part* of the signature, the signature is **captured before the flip** (`pinned_by_signature`
local).

The signature stays **narrow**, preserving 0311's safety:

* a machine-vision **surrogate** that legitimately uses a Real Image Height field keeps its own image
  aperture (Auto, or a value ≠ 2·field), so the signature never matches — it is never wiped; and
* a user who **re-typed** the field away from Real Image Height is unaffected (the reset helper still
  early-returns unless the field is Real Image Height).

`_reset_camera_pinned_field_to_default` resets to the object-mode default (Angle 0 for infinity, Object
Height 0 for finite); the image radius then collapses and the overlay draws nothing — no camera, no coverage.

(An earlier attempt set `_camera_pinned_field = True` from `layout_settings.py`'s orphaned-load branch; it was
discarded once the `__setattr__` delegation above proved it dead — the fix belongs on the editor, hence the
value signature. `layout_settings.py` is therefore unchanged.)

## Together with 0296 / 0306 / 0311
**0296** decouples the sensor coverage when the camera STEP is deleted; **0306** unlocks the image aperture
Manual→Auto for a legacy (no-stash) file; **0311** un-pins the field for a *flagged* couple; **0312** un-pins
the field for an *orphaned* camera (flag never set) by detecting the camera-autofill value signature.

## Verified (display-free)
* `KrakenOS/UI/validate_open3d_camera_delete_field_unpin.py` — **PASS** (21 checks). Stub checks
  A/B/C/D/E (0311) unchanged; **F1/F2** orphaned finite/infinity (flag off) → reset via signature; **G**
  a Manual Real Image Height field with aperture ≠ 2·value is left untouched (signature is narrow);
  **E4** structural (decouple references the signature helper); **H1–H4** end-to-end on the real MV-150
  datasheet scene with BC-OM25M hermetically popped from `CAMERA_DATABASE`: orphaned load drops the model to
  None yet keeps Real Image Height (radius 16.29), delete collapses the image-circle radius to **0.0**.
* `bugs/diag_0312_camera_delete_withstash.py` — the diagnostic probe: scenario **A** (interactive couple,
  flag path) OK, **B1** (reload valid camera, flag path) OK, **B2** (reload orphaned camera, signature path)
  now **OK (overlay clears)** — was `BUG — image circle radius 16.2917 (draws Ø32.6)`.
* Penta **phase 274** (`phase_274_orphaned_camera_delete_field_unpin`) delegates to the end-to-end check;
  baseline updated (`"274": "pass"`). Phase 273 (0311) still PASS (it exercises the extended `run_checks`).

## Files
- `KrakenOS/UI/services/layout_table_workbench.py` — new `_field_matches_camera_autofill_signature`;
  `_decouple_camera_model` legacy branch captures `pinned_by_signature` before the 0306 flip and un-pins on
  flag **or** signature.
- `KrakenOS/UI/validate_open3d_camera_delete_field_unpin.py` — F/G/E4 stub checks + `run_orphaned_camera_check`
  end-to-end (H1–H4).
- `KrakenOS/UI/validate_open3d_penta_telescope_comprehensive.py` — `phase_274_orphaned_camera_delete_field_unpin`.
- `tools/penta_validator_baseline.json` — phase 274 baseline + title.

## Notes / remaining
- In-app eyeball owed (needs a GLX display): open (or sync) a layout saved with BC-OM25M coupled on a machine
  that has **not** imported that camera, delete the camera STEP, and confirm the green FOV cone + "Max sensor"
  + "Image circle" all disappear.
