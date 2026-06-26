"""Display-free guard for bugs/0162: finite-object rays launch WITHIN the camera FOV.

When a vendor camera is registered, its sensor defines a field of view on the
object plane (the green overlay box) of half-extent ``sensor_half / |m|``. The
finite-object launch grid, however, only clamped its radial extent by the object
aperture (``rows[0].diameter / 2``) and never consulted the camera -- so for a
magnifying conjugate (``|m| > 1``) the FOV is *smaller* than the object aperture
and rays launched well outside the box the camera can actually image.

The fix clamps ``_launch_field_radial_max()`` to the FOV's inscribed object
radius ``min(half_w, half_h) / |m|`` whenever a camera is registered and a finite
magnification is available. No camera (or no magnification) -> no extra clamp, so
plain scenes keep the object-aperture behaviour and rays never vanish.

This guard binds the real ``TracePreviewSamplingMixin`` methods onto a light fake
editor (no display) and checks the clamp value, the landscape vs. square sensor
handling, the no-camera / unavailable-magnification fall-through, and -- the
user-facing guarantee -- that every launched field point lands inside the FOV box.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_launch_within_camera_fov

Exit: 0 = pass, 1 = regression.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.trace_preview_sampling import TracePreviewSamplingMixin

# Real vendor sensors (KrakenOS/UI/camera_database.py) -- the two the user flagged.
_HR25MCX = (23.04, 23.04)      # square
_SHR661 = (46.2, 32.87)        # landscape (height is the binding inscribed dim)


class _Row:
    def __init__(self, diameter: float) -> None:
        self.diameter = float(diameter)


class _FovEditor:
    """Fake editor binding the REAL launch clamp + FOV helper (production code)."""

    _launch_field_radial_max = TracePreviewSamplingMixin._launch_field_radial_max
    _camera_fov_inscribed_object_radius = TracePreviewSamplingMixin._camera_fov_inscribed_object_radius
    _sample_field_grid_pairs = TracePreviewSamplingMixin._sample_field_grid_pairs
    _sample_field_values = TracePreviewSamplingMixin._sample_field_values

    def __init__(
        self,
        *,
        field_height: float,
        object_diameter: float,
        sensor: "tuple[float, float] | None",
        magnification: "float | None",
        field_count: int = 3,
    ) -> None:
        self._field_height = float(field_height)
        self.rows = [_Row(object_diameter)] if object_diameter is not None else []
        self._sensor = sensor
        self._mag = magnification
        self._field_count = int(field_count)

    def _current_field_height(self) -> float:
        return self._field_height

    def _current_field_count(self) -> int:
        return self._field_count

    def _current_camera_sensor_active_mm(self) -> "tuple[float, float] | None":
        return self._sensor

    def _current_finite_paraxial_magnification(self) -> "float | None":
        return self._mag


def _fov_half_extents(sensor, mag):
    return (sensor[0] * 0.5 / abs(mag), sensor[1] * 0.5 / abs(mag))


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []

    # 1) Magnifying camera conjugate (|m| > 1): the FOV is SMALLER than the object
    #    aperture, so the launch must clamp to the FOV's inscribed radius, NOT the
    #    object aperture. Square hr25MCX, m = 2 -> inscribed = 11.52 / 2 = 5.76.
    ed = _FovEditor(field_height=50.0, object_diameter=56.7, sensor=_HR25MCX, magnification=2.0)
    expect = min(_HR25MCX) * 0.5 / 2.0
    got = float(ed._launch_field_radial_max())
    if not np.isclose(got, expect, atol=1e-6):
        failures.append(f"FAIL: hr25MCX m=2 launch_max={got:.4f}, expected FOV-inscribed {expect:.4f}")
    if got >= 56.7 * 0.5:
        failures.append("FAIL: hr25MCX launch still reaches the object aperture (FOV clamp not applied)")

    # 2) Landscape sensor (shr661MCX12 46.2x32.87): the inscribed radius is the
    #    SMALLER half-dimension (height 16.435), not the width 23.1.
    ed = _FovEditor(field_height=50.0, object_diameter=56.7, sensor=_SHR661, magnification=2.0)
    expect = min(_SHR661) * 0.5 / 2.0          # 32.87/2/2 = 8.2175
    got = float(ed._launch_field_radial_max())
    if not np.isclose(got, expect, atol=1e-6):
        failures.append(f"FAIL: shr661 landscape launch_max={got:.4f}, expected inscribed(min) {expect:.4f}")
    if np.isclose(got, _SHR661[0] * 0.5 / 2.0, atol=1e-6):
        failures.append("FAIL: shr661 used the WIDTH half-extent (rays exceed the FOV top/bottom)")

    # 3) The user-facing guarantee: every launched field point lands INSIDE the
    #    FOV box (|x| <= half_w and |y| <= half_h), for both sensors.
    for sensor, mag, label in ((_HR25MCX, 2.0, "hr25MCX"), (_SHR661, 1.5, "shr661MCX12")):
        ed = _FovEditor(field_height=80.0, object_diameter=70.0, sensor=sensor, magnification=mag)
        half_w, half_h = _fov_half_extents(sensor, mag)
        pairs = ed._sample_field_grid_pairs(ed._launch_field_radial_max())
        for fx, fy in pairs:
            if abs(fx) > half_w + 1e-6 or abs(fy) > half_h + 1e-6:
                failures.append(
                    f"FAIL: {label} launched field point ({fx:.3f},{fy:.3f}) outside FOV "
                    f"box (+/-{half_w:.3f}, +/-{half_h:.3f})"
                )
                break

    # 4) No camera registered -> no FOV clamp; falls back to the object-aperture
    #    clamp and rays still launch (never vanish).
    ed = _FovEditor(field_height=50.0, object_diameter=20.0, sensor=None, magnification=2.0)
    if ed._camera_fov_inscribed_object_radius() is not None:
        failures.append("FAIL: no-camera scene reported a FOV radius (should be None)")
    got = float(ed._launch_field_radial_max())
    if not np.isclose(got, 10.0, atol=1e-6):
        failures.append(f"FAIL: no-camera launch_max={got:.4f}, expected object aperture 10.0")

    # 5) Camera registered but magnification unavailable / degenerate -> no clamp
    #    (None), object-aperture fallback (rays must not vanish).
    for bad_mag in (None, 0.0, float("nan")):
        ed = _FovEditor(field_height=50.0, object_diameter=20.0, sensor=_HR25MCX, magnification=bad_mag)
        if ed._camera_fov_inscribed_object_radius() is not None:
            failures.append(f"FAIL: magnification {bad_mag!r} should disable the FOV clamp (got a radius)")
        got = float(ed._launch_field_radial_max())
        if not np.isclose(got, 10.0, atol=1e-6):
            failures.append(f"FAIL: mag {bad_mag!r} launch_max={got:.4f}, expected object aperture 10.0")

    # 6) De-magnifying conjugate (|m| < 1): the FOV is LARGER than the object
    #    aperture, so the object aperture stays the binding clamp -- rays fill the
    #    object and stay within the (larger) FOV; the camera clamp must not expand.
    ed = _FovEditor(field_height=50.0, object_diameter=20.0, sensor=_HR25MCX, magnification=0.5)
    fov_radius = ed._camera_fov_inscribed_object_radius()
    if fov_radius is None or fov_radius <= 10.0:
        failures.append(f"FAIL: m=0.5 FOV radius should exceed object aperture, got {fov_radius}")
    got = float(ed._launch_field_radial_max())
    if not np.isclose(got, 10.0, atol=1e-6):
        failures.append(f"FAIL: m=0.5 launch_max={got:.4f}, expected object aperture 10.0 (FOV larger)")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0162 finite-object rays launch within the camera FOV")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] registered-camera launch is clamped to the object FOV box; no-camera scenes unchanged (bugs/0162)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
