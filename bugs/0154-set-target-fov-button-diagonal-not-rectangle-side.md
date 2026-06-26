# 0154 — "Set Target FOV" button uses the image-circle DIAGONAL, not the rectangle side the canvas shows

Flag: `attachment/recorded_bug_repros/flag_20260626_081217_118/`
Repro (description.txt): *"from Left Panel, Set Target FOV, enter 19.5, then Snap to FOV,
the object plane shows 13.8 x 13.8."*

## Symptom

With an hr25MCX (square **23.04 x 23.04** sensor) registered, the canvas object plane
read **13.8 x 13.8** at the flag geometry (|m| = 1.671: 23.04 / 1.671 = 13.79).
The user typed **19.5** into the left-panel *Set Target FOV* dialog and clicked
*Snap to FOV* expecting the object plane to become **19.5 x 19.5** — but it stayed
**13.8 x 13.8**. The snap appeared to do nothing.

Separately (attachment/QE.png) the *Rec. sensor* readout still advertised a
**26.1 x 19.6 mm (~APS-C)** 4:3 rectangle instead of the registered square sensor.

## Root cause

Two FOV representations that disagree once the sensor is non-4:3:

* The **canvas green FOV W×H** and the **double-click Object-plane FOV popup** work in
  sensor-RECTANGLE terms: the object field is `sensor_rect / |m|`. Entering a *side*
  (e.g. Height 19.5) sizes that rectangle directly. This path is **correct** (the user
  confirmed "the double-click one is correct").
* The **left-panel Set Target FOV / Snap to FOV button** worked in the image-circle
  DIAGONAL (disk) model. `_quick_estimation_set_target_fov` stored
  `set_target_fov(full / 2.0)` — treating the entered "full Object Height" as the
  image-circle **diameter** (semi = radius). `snap_to_fov` then solved
  `|m| = _sensor_semi() / target` where `_sensor_semi()` is the **half-diagonal**
  (16.29 for the Ø32.58 image circle).

At the flag geometry the current FOV image-circle diameter is already
`2 * sensor_semi / |m| = 2 * 16.29 / 1.671 = 19.5`. So entering "19.5" asked for a
diameter that was **already true** → `|m|` unchanged at 1.671 → object plane stayed at
the inscribed square **13.8 x 13.8**. The number the user typed (19.5) was the
**diagonal**; the number the canvas shows (13.8) is the **side** — geometrically
consistent (√(13.8² + 13.8²) = 19.5) but two different quantities.

`recommended_sensor()` independently hardcoded `aspect = SENSOR_ASPECT` (4:3),
producing the "26.1 x 19.6 ~APS-C" line for a square sensor.

## Fix

Sync the button path to the popup's rectangle-side semantics, gated on a genuine live
sensor so disk-model (no-camera) scenes are byte-identical:

* `_quick_estimation_set_target_fov` now interprets the entered Object Height as a
  rectangle **side**: `set_target_fov(height_to_diagonal(full) / 2.0)` — converting the
  side to the object-rectangle diagonal via the **live sensor aspect** (square → ×√2),
  exactly as the popup's `_sensor_wh` does. The dialog prefill round-trips back through
  `diagonal_to_height`. For the flag: 19.5 → diagonal 27.58 → semi 13.789 → snap
  `|m| = 16.29 / 13.789 = 1.181` → object plane **23.04 / 1.181 = 19.5 x 19.5**.
* New `_aspect_vertical_fraction` / `height_to_diagonal` / `diagonal_to_height`
  (mirror the existing horizontal helpers; derive from the live sensor).
* `recommended_sensor(aspect=None)` defaults to the **live** sensor aspect
  (`_live_sensor_active_dimensions()`), 4:3 only when no sensor shape is known.
* `format_readout` reports the Sensor / FOV / Target lines in sensor-rectangle (Height)
  terms whenever a live sensor is present — matching the canvas + popup — and keeps the
  diagonal strings verbatim for no-camera (penta) scenes. `snap_to_fov`'s status echoes
  the entered Height, not the diagonal.

`current_state()` numeric keys (`sensor_semi`, `fov_semi`, `fov_full` = image-circle
diagonal) are **unchanged** — the conjugate solver and the
`validate_open3d_quick_estimation_conjugate` / `validate_open3d_fov_plane_solve`
contracts still hold.

## Guard

`KrakenOS/UI/validate_open3d_target_fov_button_sync.py` (penta phase 145) — display-free
on a tk-free fake editor:

* entering Object Height 19.5 on the square-sensor flag scene maps to the diagonal-semi
  the popup would (≈13.789), so the implied snap `|m|` ≈ 1.181 and the resulting object
  plane is **19.5 x 19.5**, NOT the old 13.8;
* `height_to_diagonal` / `diagonal_to_height` round-trip on the live square aspect;
* `recommended_sensor()` is square (23.04 x 23.04) for the live square sensor;
* REGRESSION: no-camera scenes keep the 4:3 disk model (recommended 4:3,
  `height_to_diagonal` falls back to the 4:3 aspect).

## Follow-up — two-box dialog (UX half of the sync)

The first fix corrected the *number* the single-box dialog produced but left the box a
single "Object Height" field. The user flagged that it was *"still not sync with the
canvas double-click FOV, still showing one value instead of two inputs"* — the canvas
double-click Object-plane FOV popup is a **Width × Height** dialog. Now the left-panel
*Set Target FOV…* button opens the same two-box modal:

* `_quick_estimation_set_target_fov` is a `tk.Toplevel` modal modelled on
  `_open_quick_estimation_fov_popup` (Width / Height entries, "fill just one box — the
  other is derived from the sensor aspect" note), prefilled from
  `qe.object_fov_dimensions()`. Buttons: *Set Target* / *Clear (fill sensor)* / *Cancel*.
* New `QuickEstimationService.set_target_fov_rect(width, height, aspect=None)` reuses the
  popup's `_sensor_wh` to turn the rectangle into a **diagonal**, then
  `set_target_fov(diagonal / 2)` — exactly the popup's *Solve-for-Thickness* mapping. It
  only **stores** the target; the panel's *Snap to FOV* button still moves the
  conjugates (the two-step Set-then-Snap workflow is preserved). For a square sensor:
  19.5 × 19.5 (or width-only / height-only 19.5) → diagonal 27.58 → semi 13.789.
* If a future **rectangular** sensor is registered, both boxes prefill with the real
  W × H and either-box-derives-the-other follows the live aspect — answering the user's
  "what if the sensor is rectangular?" directly.

Guard extended with check **H** in the same validator (and phase 145): `set_target_fov_rect`
on the square flag scene (both / width-only / height-only) stores semi ≈ 13.789 and a
following snap reaches `|m|` ≈ 1.181; both-blank / non-positive are rejected; a no-camera
scene still folds 4:3 (width 6 → height 4.5 → semi 3.75).
