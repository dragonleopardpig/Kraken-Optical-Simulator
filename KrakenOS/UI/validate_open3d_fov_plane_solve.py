#!/usr/bin/env python3
"""Display-free guard for bugs/0055: click-on-plane FOV solve.

Double-left-clicking the Object plane or Image plane in Open 3D opens a small box:
type a horizontal field width (NOT the image-circle diameter), then click one of
two buttons:

  * "Solve for Thickness" -- move the object/image conjugate pair so the typed
    field fills / maps to the sensor (in focus); or
  * "Solve for Image/Sensor Size" -- keep the conjugates (current magnification)
    and resize the terminal sensor so the typed field maps onto it.

The horizontal width is mapped to the model's circular image-circle diameter via
the working 4:3 sensor aspect (horizontal / diagonal = 0.8).

No X server needed. The solve math is exercised against a stubbed paraxial engine
(known focal length + magnification) so the conjugate numbers are deterministic;
the gesture/UI wiring is asserted against the installer/handler source.
"""
from __future__ import annotations

import inspect
import types

import numpy as np


def _build_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow

    app = KrakenLayoutEditor(headless=True)
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=275.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="L1", name="L1 front",
                   thickness=8.0, diameter=25.0, glass="N-BK7"),
        SurfaceRow(label="2", surface="Standard", element="", name="L1 back",
                   thickness=24.405, diameter=25.0, glass="AIR"),
        SurfaceRow(label="3", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=24.0, glass="AIR"),  # sensor Ø24 -> semi 12
    ]
    # Stub the paraxial engine: thin lens f=50 at the principal planes (ppa=ppp=0),
    # magnification -0.5. This makes the conjugate solve deterministic.
    app._exact_paraxial_solution_for_rows = lambda rows, wavelength=None: (0.0, 0.0, 0.0, 0.0, 50.0, 0.0, 0.0)
    app._current_finite_paraxial_magnification = lambda: -0.5
    app._current_object_mode = lambda: "finite"
    app._current_image_distance = lambda: 70.0
    try:
        app._sync_table()
    except Exception:
        pass
    # _sync_table couples the terminal diameter to the default field; pin the
    # sensor to Ø24 (semi 12) AFTER the sync so the FOV math is deterministic.
    app.rows[-1].diameter = 24.0
    return app


def _service(app):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    inspector = types.SimpleNamespace(editor=app)
    return QuickEstimationService(inspector)


def _test_horizontal_mapping() -> None:
    qe = _service(_build_editor())
    # 4:3 -> horizontal/diagonal = 0.8.
    if abs(qe.horizontal_to_diagonal(8.0) - 10.0) > 1e-9:
        raise AssertionError(f"horizontal_to_diagonal(8) should be 10, got {qe.horizontal_to_diagonal(8.0)}")
    if abs(qe.diagonal_to_horizontal(10.0) - 8.0) > 1e-9:
        raise AssertionError(f"diagonal_to_horizontal(10) should be 8, got {qe.diagonal_to_horizontal(10.0)}")
    # Sensor Ø24 -> 24 * 0.8 = 19.2 mm wide.
    if abs(qe.sensor_horizontal() - 19.2) > 1e-9:
        raise AssertionError(f"sensor_horizontal should be 19.2, got {qe.sensor_horizontal()}")
    # object FOV: |m|=0.5, sensor_semi=12 -> fov_semi=24, fov_full(diagonal)=48 -> 38.4 wide.
    if abs(qe.object_fov_horizontal() - 38.4) > 1e-6:
        raise AssertionError(f"object_fov_horizontal should be 38.4, got {qe.object_fov_horizontal()}")
    print("horizontal<->diagonal mapping + readouts OK")


def _test_object_solve_for_thickness() -> None:
    """Object plane, 'Solve for Thickness': type a 40 mm object width -> move the
    conjugate pair so that field fills the current sensor (Ø24), leaving the sensor
    untouched."""
    app = _build_editor()
    qe = _service(app)
    sensor_before = float(app.rows[-1].diameter)
    ok, msg = qe.fov_solve("object", "thickness", 40.0)
    if not ok:
        raise AssertionError(f"object thickness solve should succeed: {msg}")
    # diag=50, semi=25; |m| = sensor_semi/semi = 12/25 = 0.48.
    # object_distance = f*(1+1/mag) = 50*(1+1/0.48); image_distance = f*(1+mag).
    mag = 12.0 / 25.0
    exp_obj = 50.0 * (1.0 + 1.0 / mag)
    exp_img = 50.0 * (1.0 + mag)
    if abs(float(app.rows[0].thickness) - exp_obj) > 1e-6:
        raise AssertionError(f"object gap should be {exp_obj:.6g}, got {app.rows[0].thickness}")
    if abs(float(app.rows[2].thickness) - exp_img) > 1e-6:  # img_row = len-2 = 2
        raise AssertionError(f"image gap should be {exp_img:.6g}, got {app.rows[2].thickness}")
    if abs(float(app.rows[-1].diameter) - sensor_before) > 1e-9:
        raise AssertionError("Solve for Thickness must NOT resize the sensor")
    if abs((qe.target_object_semi() or 0.0) - 25.0) > 1e-9:
        raise AssertionError("the typed object field becomes the FOV target (semi=25)")
    print("object plane Solve for Thickness OK")


def _test_object_solve_for_sensor() -> None:
    """Object plane, 'Solve for Image/Sensor Size': keep the conjugates, resize the
    sensor so the typed 40 mm object width maps onto it at the current |m|=0.5."""
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    ok, msg = qe.fov_solve("object", "sensor", 40.0)
    if not ok:
        raise AssertionError(f"object sensor solve should succeed: {msg}")
    # diag=50; sensor diagonal = |m| * diag = 0.5 * 50 = 25.
    if abs(float(app.rows[-1].diameter) - 25.0) > 1e-6:
        raise AssertionError(f"sensor Ø should become 25, got {app.rows[-1].diameter}")
    if [float(r.thickness) for r in app.rows] != gaps_before:
        raise AssertionError("Solve for Sensor must NOT change any thickness")
    print("object plane Solve for Image/Sensor Size OK")


def _test_image_solve_for_sensor() -> None:
    """Image plane, 'Solve for Image/Sensor Size': resize the sensor to the typed
    16 mm width directly (Ø = 16 / 0.8 = 20)."""
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    ok, msg = qe.fov_solve("image", "sensor", 16.0)
    if not ok:
        raise AssertionError(f"image sensor solve should succeed: {msg}")
    if abs(float(app.rows[-1].diameter) - 20.0) > 1e-6:
        raise AssertionError(f"sensor Ø should become 20, got {app.rows[-1].diameter}")
    if [float(r.thickness) for r in app.rows] != gaps_before:
        raise AssertionError("image Solve for Sensor must NOT change any thickness")
    print("image plane Solve for Image/Sensor Size OK")


def _test_image_solve_for_thickness() -> None:
    """Image plane, 'Solve for Thickness': adjust the conjugates so the current
    object field images to the typed 16 mm width on the (unchanged) sensor."""
    app = _build_editor()
    qe = _service(app)
    qe.set_target_fov(25.0)  # current object field semi = 25
    sensor_before = float(app.rows[-1].diameter)
    ok, msg = qe.fov_solve("image", "thickness", 16.0)
    if not ok:
        raise AssertionError(f"image thickness solve should succeed: {msg}")
    # image semi = (16/0.8)/2 = 10; |m| = 10/25 = 0.4.
    mag = 10.0 / 25.0
    exp_obj = 50.0 * (1.0 + 1.0 / mag)
    exp_img = 50.0 * (1.0 + mag)
    if abs(float(app.rows[0].thickness) - exp_obj) > 1e-6:
        raise AssertionError(f"object gap should be {exp_obj:.6g}, got {app.rows[0].thickness}")
    if abs(float(app.rows[2].thickness) - exp_img) > 1e-6:
        raise AssertionError(f"image gap should be {exp_img:.6g}, got {app.rows[2].thickness}")
    if abs(float(app.rows[-1].diameter) - sensor_before) > 1e-9:
        raise AssertionError("image Solve for Thickness must NOT resize the sensor")
    print("image plane Solve for Thickness OK")


def _test_solve_refuses_bad_input() -> None:
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    sensor_before = float(app.rows[-1].diameter)
    for bad in (0.0, -5.0, float("nan")):
        if qe.fov_solve("object", "thickness", bad)[0] is not False:
            raise AssertionError(f"non-positive width {bad} must be refused")
    if [float(r.thickness) for r in app.rows] != gaps_before or float(app.rows[-1].diameter) != sensor_before:
        raise AssertionError("a refused solve must leave the model untouched")
    # Image thickness with no object target and no FOV available -> refuse cleanly.
    app2 = _build_editor()
    app2._current_finite_paraxial_magnification = lambda: None  # kills fov_semi
    qe2 = _service(app2)
    ok, _msg = qe2.fov_solve("image", "thickness", 16.0)
    if ok is not False:
        raise AssertionError("image thickness with no object field must refuse")
    print("solve refuses bad / under-specified input OK")


def _test_double_click_gesture_wiring() -> None:
    """The gesture is a Tk double-left-click that can't run without an X server, so
    assert the wiring against the source: the binding, the plane router, and the
    popup's two solve buttons."""
    from KrakenOS.UI.services.open3d_mouse_bindings import Open3DMouseBindingsService
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    binds = inspect.getsource(Open3DMouseBindingsService._install_pick_only_left_click_bindings)
    if "<Double-Button-1>" not in binds or "_maybe_open_fov_popup_from_double_click" not in binds:
        raise AssertionError("double-left-click must be bound and route to the FOV popup")

    router = inspect.getsource(Kraken3DInspector._maybe_open_fov_popup_from_double_click)
    if '"Object"' not in router or '"Image"' not in router:
        raise AssertionError("the double-click router must recognise the Object and Image planes")
    if "_open_quick_estimation_fov_popup" not in router:
        raise AssertionError("the router must open the FOV popup")

    popup = inspect.getsource(Kraken3DInspector._open_quick_estimation_fov_popup)
    if "Solve for Thickness" not in popup or "Solve for Image/Sensor Size" not in popup:
        raise AssertionError("the popup must offer both solve buttons")
    if 'fov_solve' not in inspect.getsource(Kraken3DInspector._apply_quick_estimation_fov_solve):
        raise AssertionError("the popup commit must call qe.fov_solve")
    print("double-click gesture + popup wiring OK")


def main() -> int:
    _test_horizontal_mapping()
    _test_object_solve_for_thickness()
    _test_object_solve_for_sensor()
    _test_image_solve_for_sensor()
    _test_image_solve_for_thickness()
    _test_solve_refuses_bad_input()
    _test_double_click_gesture_wiring()
    print("FOV plane-solve validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
