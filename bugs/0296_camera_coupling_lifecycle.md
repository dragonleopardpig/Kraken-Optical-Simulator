# 0296 — Camera STEP coupling lifecycle: decouple on delete + refresh the 2D on import

Two flags on the 0295 folder-import surrogate flow, both symptoms of an **asymmetric camera-coupling
lifecycle**. Importing a vendor camera STEP couples its sensor into the field / image-surface aperture
(0295 Stage 2a), but the two *other* edges of that lifecycle were never wired:

- Flag `attachment/recorded_bug_repros/flag_20260713_160023_003/` —
  > after BC-GM camera deleted, the sensor size remain on the screen.

  The state shows `step_actor_counts: {lens: 1}` (the camera body actor is gone) but the terminal
  **Image** row still carries the coupled sensor aperture (`row_actor_bounds["6"]` half = **9.050967** =
  the BC-GN25M12X4 sensor half-diagonal, `12.8·√2 / 2`). Deleting the camera cleared the body but left
  its sensor coverage on the layout.

- After importing the HR25M camera (flag `…_160249_590`, confirmed correct: `316.77 + 11.48 = 328.25`),
  the user:
  > Immediately after flag 2, click Done 2D, refer `attachment/2D.png`, it is not updated.

  The 2D layout still drew the datasheet FOV (±35.35 mm) instead of the coupled HR25M sensor FOV
  (±16.29 mm). The field **vars** were correctly coupled (the 3D scene proves it) — only the 2D re-plot
  never fired.

## Root cause

The camera coupling has three lifecycle edges; only one was fully wired.

1. **Couple** (`_apply_camera_coverage_autofill`) — fires on the dropdown (`_on_camera_model_changed`),
   on layout load, and on a vendor-STEP import (`_couple_camera_model_from_step`, 0295 Stage 2a). ✔

2. **2D refresh after couple** — the *dropdown* path calls `_mark_plot_update_pending()`, but the
   *STEP-import* path (`open3d_inspector.import_step_overlay`) never set `self._stl_placement_dirty =
   True`. So `finish_stl_placement` ("Done 2D") — which re-plots **only** when `_stl_placement_dirty` —
   skipped its `refresh_plot`, leaving the stale datasheet FOV. (The dropdown/load couple happens outside
   the STL-placement modal, so it was never affected.)

3. **Decouple** — happened **nowhere**. `clear_imported_step_overlay_state("camera")` cleared the STEP
   path / rotations / offsets / axis anchor but never reset `camera_model_var` nor reverted the coupled
   image-surface aperture / field. (The dropdown → `None` branch was the same latent gap: it marked the
   plot pending but never restored the field either.) So the sensor coverage outlived the camera.

## Fix

A symmetric **stash-on-couple / restore-on-decouple** lifecycle, plus the missing 2D-dirty marks. All in
the shared engine — no per-scene / hardcoded values, the display follows the model.

### Decouple (flag 160023) — `layout_table_workbench.py`

- `_stash_camera_precouple_field_state()` — remembers the field type / field value / image-diameter mode /
  image-surface aperture **before** the first couple overwrites them. Guarded by an existing stash, so
  re-coupling to a *different* camera keeps the *original* pre-camera state. Interactive-couple only
  (dropdown + STEP import), never on layout load (a loaded-with-camera layout has no meaningful "before").
- `_decouple_camera_model()` — resets `camera_model_var` → `CAMERA_NONE_LABEL` and restores the stash
  (aperture, field, mode), then clears it. Returns `True` when a stash was restored.
- Wired into: `_couple_camera_model_from_step` + `_on_camera_model_changed` (real-camera branch) **stash**
  before autofill; `_on_camera_model_changed` (None branch) **decouples** (symmetric with a delete);
  `step_overlay_import.clear_imported_step_overlay_state("camera")` **decouples** on delete — the reported
  path. (`clear_…` runs on `StepOverlayImportService`, whose `__getattr__`/`__setattr__` proxy to the
  editor, so `self._decouple_camera_model()` resolves to the editor method; guarded by `hasattr`.)

### 2D refresh (Done-2D-not-updated) — `open3d_inspector.py`

- `import_step_overlay` sets `self._stl_placement_dirty = True` after a successful import (matches the
  promote path at `_promote_step_overlay_to_optical_solid_row`), so "Done 2D" / close re-plots the 2D with
  the coupled camera field.
- `delete_selected_step` (import-overlay branch) sets `self._stl_placement_dirty = True` too, so a delete
  (which now decouples → restores the field/aperture) also re-plots the 2D.

## Guard + gate

`KrakenOS/UI/validate_open3d_camera_coupling_lifecycle.py` (`run_checks()`) — display-free, no Tk / no VTK:

- **B** runs the **real** couple (`_apply_camera_coverage_autofill("Japan Bopixel BC-GN25M12X4")` →
  aperture 18.1019, field 9.050967) then the new `_decouple_camera_model()` on a minimal stub, and asserts
  the aperture / field / image-diameter mode all restore to the pre-camera datasheet values and the model
  resets to `None`; a **second** couple (`Allied Vision hr25MCX`) must not overwrite the original stash;
  a second decouple is a no-op.
- **A** structurally asserts (via `inspect.getsource`) that `import_step_overlay` + `delete_selected_step`
  mark the 2D dirty (`bugs/0296`) and `clear_imported_step_overlay_state` decouples the camera — the
  Tk-only wirings that need a live app to *run* but not to *prove*.

Penta **phase 260** (`phase_260_camera_coupling_lifecycle`), baseline `260: pass` added. The full marathon
SIGSEGVs under Xvfb llvmpipe, so phase 260 was verified in isolation (`phase_260_camera_coupling_lifecycle(
None, None)` → PASS) and the baseline hand-edited, as the 0295 commit did for phase 259.

## Owed / limitation

The stash/restore + decouple logic and the dirty-flag wiring are headless-verified. The **rendered** 2D
re-plot (matplotlib) still owes an in-app NVIDIA GLX eyeball: import the vendor camera STEP → click
**Done 2D** → confirm the 2D FOV shrinks to the sensor; then **delete** the camera → confirm the sensor
coverage disappears from both the 3D image-surface disc and the 2D FOV.

Limitation: the stash is session state (not serialized), so a layout **saved** with a camera already
coupled and then deleted in a *fresh* session has no pre-camera state to restore — decouple resets the
model but leaves the authored aperture (there is no better "before" to return to). The reported flows
(interactive import → delete, dropdown couple → None) all carry a stash.
