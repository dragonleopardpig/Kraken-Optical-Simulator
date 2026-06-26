#!/usr/bin/env python3
"""Display-free guard: the left-panel "Set Target FOV" / "Snap to FOV" button path
treats the typed Object Height as a sensor-RECTANGLE side (like the canvas + the
double-click Object-plane FOV popup), not as the image-circle DIAGONAL (bugs/0154).

Symptom (flag_20260626_081217_118): with an hr25MCX (square 23.04x23.04) registered
at |m|=1.671 the canvas object plane read 13.8 x 13.8. Typing 19.5 into Set Target
FOV + Snap left it at 13.8 -- the disk model stored set_target_fov(19.5/2)=9.75 (the
image-circle radius), and snap solved |m| = _sensor_semi()/9.75 = 16.29/9.75 = 1.671
(= the current mag, so snap was a no-op). 19.5 was the DIAGONAL; 13.8 is the SIDE.

Fix: the typed Object Height is a rectangle side. height_to_diagonal() converts it to
the object diagonal via the LIVE sensor aspect (square -> x sqrt2); set_target_fov gets
the diagonal-semi the popup would. 19.5 -> diagonal 27.58 -> semi 13.789 -> snap
|m| = 16.29/13.789 = 1.181 -> object plane 23.04/1.181 = 19.5 x 19.5.
recommended_sensor() also follows the live (square) aspect, not 4:3 APS-C.

What it checks (pure QuickEstimationService on a tk-free fake editor):
  A  mapping: Object Height 19.5 on the square flag scene -> target diagonal-semi
     ~13.789 (NOT the old 9.75); the implied snap |m| = _sensor_semi()/target ~1.181
     (NOT the no-op 1.671).
  B  end-to-end snap (stubbed thin lens f=100): snap_to_fov sets gaps whose ratio is
     |m| ~1.181; the status echoes the Height 19.5 (not the diagonal 27.58).
  C  canvas result: at the snapped |m|=1.181 the object FOV rect is 19.5 x 19.5; the
     old disk |m|=1.671 would have been 13.79 (the bug shape) -- we no longer land there.
  D  round-trip: height_to_diagonal(19.5) ~27.58 and diagonal_to_height back ~19.5
     on the live square aspect.
  E  recommended_sensor is SQUARE (23.04 x 23.04) for the live square sensor, NOT the
     4:3 fold (26.07 x 19.55).
  F  REGRESSION -- no live sensor keeps the 4:3 disk model: _aspect_vertical_fraction
     0.6, height_to_diagonal(6)=10, diagonal_to_height(10)=6, recommended_sensor 4:3.
  G  source contract: recommended_sensor + format_readout gate on the live sensor;
     height_to_diagonal / diagonal_to_height / set_target_fov_rect exist.
  H  two-box dialog: set_target_fov_rect(W, H) stores the rectangle DIAGONAL-semi the
     same way the popup's Solve-for-Thickness does -- square 19.5x19.5 / width-only /
     height-only all -> semi ~13.789 and a following snap reaches |m| ~1.181; both-blank
     / non-positive are rejected; no live sensor still folds 4:3 (width 6 -> semi 3.75).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_target_fov_button_sync

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


def _service(*, sensor_diameter, mag, camera_dims=None, f=100.0):
    """Object + thin lens + air + Image(sensor). A stubbed thin-lens paraxial
    solution (f, ppa=ppp=0) lets snap_to_fov solve real conjugate distances."""
    rows = [
        _row(surface="Object", thickness=200.0, diameter=sensor_diameter),
        _row(surface="Standard", thickness=8.0, diameter=25.0, glass="N-BK7"),
        _row(surface="Standard", thickness=100.0, diameter=25.0, glass="AIR"),
        _row(surface="Image", thickness=0.0, diameter=sensor_diameter),
    ]
    sol = (None, None, None, None, float(f), 0.0, 0.0)
    editor = types.SimpleNamespace(rows=rows)
    editor._current_finite_paraxial_magnification = lambda: mag
    editor._current_object_mode = lambda: "finite"
    editor._current_image_distance = lambda: float(rows[2].thickness)
    editor._layout_needs_paraxial_reference = lambda _rows: False
    editor._exact_paraxial_solution_for_rows = lambda _rows: sol
    editor._camera_detector_active_dims_overrides = (
        (lambda: {len(rows) - 1: tuple(camera_dims)}) if camera_dims else (lambda: None)
    )
    inspector = types.SimpleNamespace(
        editor=editor, quick_estimation_var=types.SimpleNamespace(get=lambda: True)
    )
    return QuickEstimationService(inspector), rows


# the flag scene: square 23.04 sensor, image circle Ø32.583 (semi 16.2915), |m|=1.671.
FLAG_DIAM = 32.583
FLAG_SQUARE = (23.04, 23.04)


def run_checks():
    failures = []

    # A: typed Object Height 19.5 -> the rectangle-side mapping, not the disk radius.
    svc, _ = _service(sensor_diameter=FLAG_DIAM, mag=1.671, camera_dims=FLAG_SQUARE)
    target_semi = svc.height_to_diagonal(19.5) / 2.0
    if not _approx(target_semi, 13.789, tol=2e-3):
        failures.append(f"A FAIL: Object Height 19.5 should map to diagonal-semi ~13.789, got {target_semi}")
    if _approx(target_semi, 9.75, tol=2e-3):
        failures.append("A FAIL: still the disk model (19.5/2=9.75) -- ignoring the rectangle side")
    sensor_semi = svc._sensor_semi()
    snap_mag = sensor_semi / target_semi
    if not _approx(snap_mag, 1.181, tol=3e-3):
        failures.append(f"A FAIL: implied snap |m| should be ~1.181, got {snap_mag}")
    if _approx(snap_mag, 1.671, tol=3e-3):
        failures.append("A FAIL: snap |m| unchanged at the current 1.671 -- snap is a no-op (the bug)")

    # B: end-to-end snap with a stubbed thin lens -> gaps whose ratio is |m|, Height echoed.
    svcB, rowsB = _service(sensor_diameter=FLAG_DIAM, mag=1.671, camera_dims=FLAG_SQUARE, f=100.0)
    svcB.set_target_fov(svcB.height_to_diagonal(19.5) / 2.0)
    ok, msg = svcB.snap_to_fov()
    if not ok:
        failures.append(f"B FAIL: snap_to_fov should succeed, got {msg!r}")
    else:
        obj_d = rowsB[0].thickness
        img_d = rowsB[2].thickness
        implied = img_d / obj_d if obj_d else None
        if not _approx(implied, 1.181, tol=4e-3):
            failures.append(f"B FAIL: snapped gaps imply |m| ~1.181, got {implied} (obj {obj_d}, img {img_d})")
        if "19.5" not in msg:
            failures.append(f"B FAIL: status should echo the Height 19.5, got {msg!r}")
        if "27.5" in msg or "27.6" in msg:
            failures.append(f"B FAIL: status leaks the diagonal 27.58 instead of the Height, got {msg!r}")

    # C: the canvas object FOV at the snapped |m| is 19.5 x 19.5; the old disk |m| was 13.79.
    svcC, _ = _service(sensor_diameter=FLAG_DIAM, mag=1.1815, camera_dims=FLAG_SQUARE)
    of = svcC.object_fov_dimensions()
    if not (of and _approx(of[0], 19.5, tol=3e-3) and _approx(of[1], 19.5, tol=3e-3)):
        failures.append(f"C FAIL: object FOV at the snapped |m| should be ~19.5 x 19.5, got {of}")
    svcC0, _ = _service(sensor_diameter=FLAG_DIAM, mag=1.671, camera_dims=FLAG_SQUARE)
    of0 = svcC0.object_fov_dimensions()
    if not (of0 and _approx(of0[0], 13.79, tol=3e-3)):
        failures.append(f"C FAIL: the current-|m| object FOV (the bug shape) should be ~13.8, got {of0}")

    # D: height/diagonal round-trip on the live square aspect.
    if not _approx(svc.height_to_diagonal(19.5), 27.577, tol=2e-3):
        failures.append(f"D FAIL: square height_to_diagonal(19.5) should be ~27.58, got {svc.height_to_diagonal(19.5)}")
    if not _approx(svc.diagonal_to_height(svc.height_to_diagonal(19.5)), 19.5):
        failures.append("D FAIL: diagonal_to_height(height_to_diagonal(x)) must round-trip")

    # E: recommended sensor follows the LIVE square aspect, not 4:3 APS-C.
    svcE, _ = _service(sensor_diameter=FLAG_DIAM, mag=1.1815, camera_dims=FLAG_SQUARE)
    svcE.set_target_fov(svcE.height_to_diagonal(19.5) / 2.0)
    rec = svcE.recommended_sensor()
    if not rec:
        failures.append("E FAIL: recommended_sensor returned None for the live square sensor")
    else:
        if not _approx(rec["width"], rec["height"], tol=2e-3):
            failures.append(
                f"E FAIL: live square sensor recommendation must be square, "
                f"got {rec['width']} x {rec['height']}"
            )
        if _approx(rec["width"], 26.07, tol=5e-3) or _approx(rec["height"], 19.55, tol=5e-3):
            failures.append(f"E FAIL: still folding 4:3 APS-C ({rec['width']} x {rec['height']})")

    # F: REGRESSION -- no live sensor keeps the 4:3 disk model intact.
    svcF, _ = _service(sensor_diameter=24.0, mag=1.0, camera_dims=None)
    if not _approx(svcF._aspect_vertical_fraction(), 0.6, tol=1e-4):
        failures.append(f"F FAIL: no-camera vertical aspect must stay 0.6, got {svcF._aspect_vertical_fraction()}")
    if not _approx(svcF.height_to_diagonal(6.0), 10.0):
        failures.append(f"F FAIL: 4:3 height_to_diagonal(6) must be 10, got {svcF.height_to_diagonal(6.0)}")
    if not _approx(svcF.diagonal_to_height(10.0), 6.0):
        failures.append(f"F FAIL: 4:3 diagonal_to_height(10) must be 6, got {svcF.diagonal_to_height(10.0)}")
    svcF.set_target_fov(5.0)
    recF = svcF.recommended_sensor()
    if not recF or not _approx(recF["width"] / recF["height"], 4.0 / 3.0, tol=2e-3):
        failures.append(f"F FAIL: no-camera recommendation must stay 4:3, got {recF}")

    # H: two-box dialog path -- set_target_fov_rect (Width x Height) stores the same
    # diagonal-semi the single-box height path did, but accepts two sides like the
    # canvas popup. Square 23.04: width-only / height-only / both -> semi ~13.789.
    svcH, _ = _service(sensor_diameter=FLAG_DIAM, mag=1.671, camera_dims=FLAG_SQUARE)
    for label, w, h in (("both", 19.5, 19.5), ("width-only", 19.5, None), ("height-only", None, 19.5)):
        ok, msg, fw, fh = svcH.set_target_fov_rect(w, h)
        if not ok:
            failures.append(f"H FAIL: set_target_fov_rect({label}) should succeed, got {msg!r}")
            continue
        if not (_approx(fw, 19.5, tol=2e-3) and _approx(fh, 19.5, tol=2e-3)):
            failures.append(f"H FAIL: set_target_fov_rect({label}) should fill 19.5 x 19.5, got {fw} x {fh}")
        if not _approx(svcH.target_object_semi(), 13.789, tol=2e-3):
            failures.append(
                f"H FAIL: set_target_fov_rect({label}) target semi should be ~13.789, "
                f"got {svcH.target_object_semi()}"
            )

    # snap after a rect target reaches |m| ~1.181 (not the 1.671 no-op), like check B/C.
    svcH2, rowsH2 = _service(sensor_diameter=FLAG_DIAM, mag=1.671, camera_dims=FLAG_SQUARE, f=100.0)
    svcH2.set_target_fov_rect(19.5, 19.5)
    okH, msgH = svcH2.snap_to_fov()
    if not okH:
        failures.append(f"H FAIL: snap after set_target_fov_rect should succeed, got {msgH!r}")
    else:
        obj_d = rowsH2[0].thickness
        implied = rowsH2[2].thickness / obj_d if obj_d else None
        if not _approx(implied, 1.181, tol=4e-3):
            failures.append(f"H FAIL: rect-target snap |m| should be ~1.181, got {implied}")

    # invalid input is rejected (both blank / non-positive) and leaves the target alone.
    if svcH.set_target_fov_rect(None, None)[0]:
        failures.append("H FAIL: set_target_fov_rect(None, None) must be rejected")
    if svcH.set_target_fov_rect(0.0, None)[0]:
        failures.append("H FAIL: set_target_fov_rect(0, None) must be rejected")

    # REGRESSION -- no live sensor folds 4:3: width-only 6 -> height 4.5 -> diag 7.5 -> semi 3.75.
    svcH4, _ = _service(sensor_diameter=24.0, mag=1.0, camera_dims=None)
    okH4, _m4, fw4, fh4 = svcH4.set_target_fov_rect(6.0, None)
    if not okH4 or not (_approx(fw4, 6.0) and _approx(fh4, 4.5)):
        failures.append(f"H FAIL: 4:3 fallback width-only 6 should derive 4.5 height, got {fw4} x {fh4}")
    if not _approx(svcH4.target_object_semi(), 3.75, tol=2e-3):
        failures.append(f"H FAIL: 4:3 fallback rect target semi should be ~3.75, got {svcH4.target_object_semi()}")

    # G: source contract.
    for name in ("height_to_diagonal", "diagonal_to_height", "_aspect_vertical_fraction", "set_target_fov_rect"):
        if not hasattr(QuickEstimationService, name):
            failures.append(f"G FAIL: QuickEstimationService must expose {name}")
    try:
        src_rec = inspect.getsource(QuickEstimationService.recommended_sensor)
        if "_live_sensor_active_dimensions" not in src_rec:
            failures.append("G FAIL: recommended_sensor must default to the live sensor aspect")
        src_fmt = inspect.getsource(QuickEstimationService.format_readout)
        if "_live_sensor_active_dimensions" not in src_fmt:
            failures.append("G FAIL: format_readout must report the live-sensor rectangle terms")
    except (OSError, TypeError):
        failures.append("G FAIL: could not read QuickEstimationService source")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] Set Target FOV button rectangle-side sync")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] Set Target FOV / Snap to FOV treats Object Height as a rectangle side (bugs/0154)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
