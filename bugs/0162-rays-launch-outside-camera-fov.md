# 0162 — finite-object rays launch outside the camera's field of view

User report (two flags): *"shr661MCX12 camera, the ray launch outside the FOV."*
and *"hr25MCX camera."* With a registered vendor camera, the launched display
rays fan out from object points well **beyond** the green object-plane FOV box —
the box the camera can actually image. The user wants rays to launch *within*
that FOV.

## Root cause

A registered camera's sensor defines an object-plane field of view: the green
overlay box has half-extent ``sensor_half / |m|`` (`detector_coverage_overlay.py`
``detector_coverage_metrics``). But the finite-object launch grid sizes itself
from ``_launch_field_radial_max()`` (`services/trace_preview_sampling.py`), which
clamped the configured field height **only** by the object aperture
(``rows[0].diameter / 2``) and never consulted the camera.

For a **magnifying** conjugate (``|m| > 1``) the object-plane FOV is *smaller*
than the object aperture, so the launch grid reached out to the object aperture —
well past the FOV box. The machine-vision fixtures the user flagged are exactly
this case:

* **hr25MCX** — 23.04×23.04 mm sensor (square), MV150 ``|m| ≈ 1.147`` →
  object-FOV half ``11.52 / 1.147 ≈ 10.05 mm``, but the object aperture (and
  field height) are ``≈ 14.21 mm``. Rays launched out to 14.21, the FOV is 10.05.
* **shr661MCX12** — 46.2×32.87 mm sensor (landscape) → same over-launch.

## Fix

`services/trace_preview_sampling.py` gains ``_camera_fov_inscribed_object_radius()``
and ``_launch_field_radial_max()`` clamps to it:

* ``_camera_fov_inscribed_object_radius()`` = ``min(sensor_half_w, sensor_half_h)
  / |m|`` when a camera is registered (``_current_camera_sensor_active_mm()``) and
  a finite paraxial magnification is available
  (``_current_finite_paraxial_magnification()``). It returns **None** when no
  camera is registered or the magnification is missing/degenerate, so plain
  scenes keep the object-aperture clamp alone and rays still launch (never
  vanish — per the standing "rays trace regardless of placement" rule; here the
  user explicitly wants the camera FOV to bound them).
* The radius is the FOV rectangle's **inscribed** radius (the largest disc that
  fits inside the box). The launch is radial, so bounding it by the inscribed
  radius guarantees every launched field point lands inside the FOV box
  regardless of the 3×3 grid layout — for a landscape sensor the binding term is
  the smaller (height) half-extent.
* ``_launch_field_radial_max()`` now returns ``min(field_height, object_radius,
  fov_inscribed)``. The 3D launch grid feeds off this in all five finite-object
  launch paths, so each one is now FOV-bounded. Paraxial metrics
  (``_field_metrics_summary`` samples ``_current_field_value()``) and detector
  overlays are untouched.

On MV150 the launch radial max drops from 14.207 → 10.046 (the hr25MCX FOV).

## Guard

* ``KrakenOS/UI/validate_open3d_launch_within_camera_fov.py`` (new, penta
  Phase 153) — display-free: binds the real ``_launch_field_radial_max`` /
  ``_camera_fov_inscribed_object_radius`` / ``_sample_field_grid_pairs`` onto a
  light fake editor and checks (a) a magnifying camera clamps the launch to the
  FOV inscribed radius (not the object aperture); (b) a landscape sensor uses the
  smaller half-extent; (c) **every** launched field point lands inside the FOV
  box; (d) no camera / missing / degenerate magnification disables the clamp and
  falls back to the object-aperture bound (rays never vanish); (e) a
  de-magnifying conjugate (``|m| < 1``) keeps the object aperture as the binding
  clamp (the camera clamp never expands the launch).
* Updated ``validate_launch_origin_within_object_aperture.py`` — MV150 stock now
  registers hr25MCX at a magnifying conjugate, so its binding limiter is the
  camera FOV; Case 1 became *camera-FOV-limited* (expects the FOV inscribed
  radius) and Case 2 shrinks the object below the FOV radius to keep exercising
  the aperture-limited path.

## Notes

* **In-app eyeball owed:** the felt result — object rays launching inside the
  green FOV box for a registered camera — must be eyeballed in the running app.
  Headless VTK (Xvfb llvmpipe) segfaults on paint for the freshly swapped
  machine-vision scene, so the live render can't be driven headless.
* Angle-field (infinite-object) launches use ``_current_field_angle_deg()`` and
  are unaffected; the FOV box is an object-plane (finite-object) concept.
