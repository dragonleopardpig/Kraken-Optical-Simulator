#!/usr/bin/env python3
"""Display-free guard: the FOV / sensor popups prefill the LIVE sensor the 3D
canvas draws -- the registered camera's vendor sensor -- not a hardcoded 4:3
fold of the circular aperture (bugs/0153).

Symptom (flag_20260626_072642_619): with an hr25MCX (square 23.04x23.04 sensor)
registered, the Object-plane FOV popup defaulted to **26.07 x 19.55** -- a 4:3
rectangle folded from the Ø32.58 image circle -- while the canvas drew the real
**23.04 x 23.04** square. ``sensor_active_dimensions`` read only the terminal
row's explicit ``advanced['Detector']`` dims and, finding none, folded 4:3;
``_aspect_horizontal_fraction`` was a hardcoded 0.8. Both now track the live
sensor: the camera vendor sensor (``_camera_detector_active_dims_overrides``,
the same override the detector overlay blends to) -- with explicit rectangular
dims still winning, then the 4:3 fold ONLY when no sensor is known.

What it checks (pure ``QuickEstimationService`` on a tk-free fake editor):
  A  a registered square camera (23.04) -> sensor_active_dimensions == (23.04, 23.04),
     NOT the 4:3 fold of the Ø32.58 diameter.
  B  object_fov_dimensions == sensor / |m| (the popup default): (23.04, 23.04) at
     |m|=1 (the flag), and scales (|m|=2 -> 11.52) -- matching the canvas FOV rect.
  C  the live aspect is the sensor's: _aspect_horizontal_fraction ~ 1/sqrt2 for the
     square, so horizontal_to_diagonal(23.04)/2 ~ 16.29 (the popup's "semi" note).
  D  explicit rectangular detector dims WIN over the camera override (canvas
     precedence: scene_builder fills the override only when explicit is empty).
  E  REGRESSION GUARD -- no camera + no explicit dims still folds 4:3 from the
     diameter (Ø24 -> 19.2 x 14.4), aspect 0.8, horizontal_to_diagonal(8) == 10
     (the contract validate_open3d_fov_plane_solve pins).
  F  source contract: _live_sensor_active_dimensions exists and sensor_active_dimensions
     prefers it; the aspect derives from the live sensor.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_quick_estimation_live_sensor_prefill

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect
import types

from KrakenOS.UI.services.quick_estimation import QuickEstimationService


def _approx(a, b, tol=1e-3) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
    except (TypeError, ValueError):
        return False


def _row(**kw):
    r = types.SimpleNamespace(thickness=0.0, diameter=0.0, surface="", glass="AIR", advanced=None)
    r.__dict__.update(kw)
    return r


def _service(*, sensor_diameter, mag, camera_dims=None):
    """A tk-free editor: object + lens + Image(sensor). ``camera_dims`` (or None)
    is what ``_camera_detector_active_dims_overrides`` reports for the terminal row."""
    rows = [
        _row(surface="Object", thickness=200.0, diameter=sensor_diameter),
        _row(surface="Standard", thickness=8.0, diameter=25.0, glass="N-BK7"),
        _row(surface="Standard", thickness=100.0, diameter=25.0, glass="AIR"),
        _row(surface="Image", thickness=0.0, diameter=sensor_diameter),
    ]
    editor = types.SimpleNamespace(rows=rows)
    editor._current_finite_paraxial_magnification = lambda: mag
    editor._current_object_mode = lambda: "finite"
    editor._camera_detector_active_dims_overrides = (
        (lambda: {len(rows) - 1: tuple(camera_dims)}) if camera_dims else (lambda: None)
    )
    inspector = types.SimpleNamespace(
        editor=editor, quick_estimation_var=types.SimpleNamespace(get=lambda: True)
    )
    return QuickEstimationService(inspector), rows


def run_checks():
    failures = []

    # A: registered square camera -> the popup reads the camera sensor, not the 4:3 fold.
    svc, _rows = _service(sensor_diameter=32.583, mag=-1.0, camera_dims=(23.04, 23.04))
    sa = svc.sensor_active_dimensions()
    if not (sa and _approx(sa[0], 23.04) and _approx(sa[1], 23.04)):
        failures.append(f"A FAIL: camera sensor should prefill (23.04, 23.04), got {sa}")
    # the old bug: the 4:3 fold of Ø32.583 was (26.07, 19.55) -- must NOT be that now.
    if sa and (_approx(sa[0], 26.066) or _approx(sa[1], 19.55)):
        failures.append(f"A FAIL: still folding 4:3 from the diameter ({sa}) -- ignoring the camera")

    # B: object_fov_dimensions = sensor / |m| (the canvas FOV rect, and the popup default).
    of = svc.object_fov_dimensions()
    if not (of and _approx(of[0], 23.04) and _approx(of[1], 23.04)):
        failures.append(f"B FAIL: object FOV at |m|=1 should be (23.04, 23.04), got {of}")
    svc2, _ = _service(sensor_diameter=32.583, mag=-2.0, camera_dims=(23.04, 23.04))
    of2 = svc2.object_fov_dimensions()
    if not (of2 and _approx(of2[0], 11.52) and _approx(of2[1], 11.52)):
        failures.append(f"B FAIL: object FOV must scale as sensor/|m| (|m|=2 -> 11.52), got {of2}")

    # C: the live aspect is the sensor's (square -> 1/sqrt2), so the popup "semi" is right.
    frac = svc._aspect_horizontal_fraction()
    if not _approx(frac, 0.70710678, tol=1e-4):
        failures.append(f"C FAIL: square sensor aspect should be 1/sqrt2 (~0.7071), got {frac}")
    semi = svc.horizontal_to_diagonal(23.04) / 2.0
    if not _approx(semi, 16.29, tol=1e-3):
        failures.append(f"C FAIL: horizontal_to_diagonal(23.04)/2 should be ~16.29, got {semi}")

    # D: explicit rectangular detector dims WIN over the camera override (canvas precedence).
    svcD, rowsD = _service(sensor_diameter=32.583, mag=-1.0, camera_dims=(23.04, 23.04))
    rowsD[-1].advanced = {"Detector": {"active_width_mm": 10.0, "active_height_mm": 12.0}}
    sd = svcD.sensor_active_dimensions()
    if not (sd and _approx(sd[0], 10.0) and _approx(sd[1], 12.0)):
        failures.append(f"D FAIL: explicit detector dims must win over the camera, got {sd}")

    # E: REGRESSION GUARD -- no camera, no explicit dims -> 4:3 fold of the Ø24 diameter.
    svcE, _ = _service(sensor_diameter=24.0, mag=-0.5, camera_dims=None)
    se = svcE.sensor_active_dimensions()
    if not (se and _approx(se[0], 19.2) and _approx(se[1], 14.4)):
        failures.append(f"E FAIL: no-camera fold must stay 4:3 (Ø24 -> 19.2 x 14.4), got {se}")
    if not _approx(svcE._aspect_horizontal_fraction(), 0.8, tol=1e-4):
        failures.append(f"E FAIL: no-camera aspect must stay 0.8, got {svcE._aspect_horizontal_fraction()}")
    if not _approx(svcE.horizontal_to_diagonal(8.0), 10.0):
        failures.append(f"E FAIL: horizontal_to_diagonal(8) must stay 10, got {svcE.horizontal_to_diagonal(8.0)}")

    # F: source contract.
    if not hasattr(QuickEstimationService, "_live_sensor_active_dimensions"):
        failures.append("F FAIL: QuickEstimationService must expose _live_sensor_active_dimensions")
    try:
        src_sensor = inspect.getsource(QuickEstimationService.sensor_active_dimensions)
        if "_live_sensor_active_dimensions" not in src_sensor:
            failures.append("F FAIL: sensor_active_dimensions must prefer the live sensor")
        src_aspect = inspect.getsource(QuickEstimationService._aspect_horizontal_fraction)
        if "sensor_active_dimensions" not in src_aspect:
            failures.append("F FAIL: _aspect_horizontal_fraction must derive from the live sensor")
        src_live = inspect.getsource(QuickEstimationService._live_sensor_active_dimensions)
        if "_camera_detector_active_dims_overrides" not in src_live:
            failures.append("F FAIL: _live_sensor_active_dimensions must read the camera override")
    except (OSError, TypeError):
        failures.append("F FAIL: could not read QuickEstimationService source")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Quick Estimation FOV/sensor popup live-sensor prefill")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Quick Estimation FOV/sensor popup reads the live camera sensor (not a 4:3 fold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
