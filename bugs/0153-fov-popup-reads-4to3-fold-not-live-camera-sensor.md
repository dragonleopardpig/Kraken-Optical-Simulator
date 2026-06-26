# 0153 — the FOV / sensor popup must prefill the LIVE camera sensor, not a 4:3 fold

## Symptom

`flag_20260626_072642_619` — "The layout a bit not organized, and why the default value is
**26.0668 x 19.5501**? It should read the current FOV value. (The FOV shown in the canvas is
**23x23**.)" (screenshot replaced with a printscreen because Flag 's' can't capture a popup.)

Double-clicking the Object plane opens the Field-of-View popup. With an **hr25MCX** camera
(square **23.04 × 23.04 mm** sensor) registered, the Width/Height boxes defaulted to
**26.0668 × 19.5501** — a 4:3 rectangle — while the 3D canvas drew the real **23.04 × 23.04**
square. Two complaints: the wrong default value, and a crowded popup layout.

## Root cause

The popup prefill and the canvas read the sensor from **different sources**.

* **Canvas** (`detector_coverage_overlay` → `scene_geometry.scene_target_active_dimensions`):
  the scene-bundle detector *target* carries `active_width_mm`/`active_height_mm` populated by
  `_camera_detector_active_dims_overrides()` — the **registered camera's vendor sensor**
  (hr25MCX = 23.04 × 23.04). The object-FOV rectangle is `sensor / |m|`.
* **Popup** (`quick_estimation.object_fov_dimensions` → `sensor_active_dimensions`): read only
  the terminal row's explicit `advanced['Detector']` dims. The user never set those, so it fell
  through to a hardcoded **4:3 fold** of the circular image-circle diameter:

  ```
  Ø32.583  →  W = Ø·4/5 = 26.07,  H = Ø·3/5 = 19.55     # SENSOR_ASPECT = (4, 3)
  ```

  `object_fov_dimensions = sensor / |m|`, and at |m| ≈ 1 that is the same 26.07 × 19.55.

So the camera was invisible to the popup. `_aspect_horizontal_fraction()` was *also* hardcoded
4:3 (→ 0.8), so even the "From this view: Object FOV (semi) = 16.29" note was just the 26.07 box
folded back by 0.8, not an independent reading. (The 4:3 fold of Ø32.583 has the **same diagonal
32.583** as the 23.04 square — semi-diagonal 16.29 — which is why the disc looked right but the
W×H didn't.)

## Fix

`sensor_active_dimensions()` now reads the **same live sensor the canvas draws**, via a new
`_live_sensor_active_dimensions()` that mirrors `scene_builder`'s precedence exactly:

1. explicit rectangular `advanced['Detector']` dims on the terminal row (these win — the canvas
   only fills the camera override when they are empty);
2. else the registered camera's vendor sensor (`_camera_detector_active_dims_overrides()`);
3. else (no sensor known) the existing 4:3 fold of the image-circle diameter — unchanged.

`_aspect_horizontal_fraction()` now derives from `sensor_active_dimensions()` (square → 1/√2 ≈
0.7071; the 4:3 fold → 0.8, identical to the old constant), so `horizontal_to_diagonal`, the FOV
"semi" note, and the W/H box derivation all track the live sensor. `object_fov_dimensions()` is
unchanged (`sensor / |m|`) and therefore corrected for free.

Net for the flagged scene: object popup prefills **23.04 × 23.04**, semi **16.29** — matching the
canvas. Undragged/no-camera scenes are a no-op (the 4:3 fold and 0.8 aspect are preserved).

**Layout:** the embedded "design a lens" block in `_open_quick_estimation_fov_popup` now sits
under a horizontal separator + a bold **"Design a lens for this field"** section header, so it
reads as a distinct tool below the FOV-sizing boxes/buttons instead of crowding them.

## Guard

`KrakenOS/UI/validate_open3d_quick_estimation_live_sensor_prefill.py` (display-free; pure
`QuickEstimationService` on a tk-free fake editor). Checks: **A** a registered square camera
prefills (23.04, 23.04), not the 4:3 fold; **B** `object_fov_dimensions = sensor/|m|` (23.04 at
|m|=1, scales to 11.52 at |m|=2); **C** live square aspect → 1/√2 so the popup semi = 16.29;
**D** explicit detector dims win over the camera override (canvas precedence); **E** REGRESSION
GUARD — no camera + no explicit dims keeps the 4:3 fold (Ø24 → 19.2 × 14.4), aspect 0.8,
`horizontal_to_diagonal(8) == 10` (the contract `validate_open3d_fov_plane_solve` pins); **F**
source contract. Non-vacuity verified: reverting `_live_sensor_active_dimensions` to the old
ignore-the-camera behaviour reproduces (26.0664, 19.5498) and fails A/B. The existing
`validate_open3d_fov_plane_solve` still passes (no camera → 4:3 preserved). Penta phase **144**;
baseline regenerated. In-app eyeball owed (the embedded-VTK double-click + Tk popup can't be
driven headless — confirm the box opens on 23.04 × 23.04 and the layout reads cleanly).
