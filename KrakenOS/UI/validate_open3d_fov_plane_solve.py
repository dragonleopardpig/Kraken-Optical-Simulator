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

The popup takes a Width and a Height box; the user may fill just one (bugs/0071)
and the blank side is derived from the live sensor aspect (default 4:3), so
``fov_solve`` accepts a None width or height plus an explicit ``aspect``.

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
    # No explicit detector dims -> a 4:3 rectangle inscribed in the Ø24 image circle:
    # W = 24*4/5 = 19.2, H = 24*3/5 = 14.4.
    wh = qe.sensor_active_dimensions()
    if wh is None or abs(wh[0] - 19.2) > 1e-6 or abs(wh[1] - 14.4) > 1e-6:
        raise AssertionError(f"sensor_active_dimensions should be (19.2, 14.4), got {wh}")
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


def _test_object_solve_for_sensor_width_height() -> None:
    """Object plane, 'Solve for Image/Sensor Size' with an explicit Width x Height
    (bugs/0057): object W=40, H=30 imaged at |m|=0.5 -> sensor 20 x 15 mm, image
    circle Ø=sqrt(20^2+15^2)=25, with the rectangular detector dims stored. The
    diagonal must match the width-only path (which derives a 4:3 H=30), and no
    thickness may change."""
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    ok, msg = qe.fov_solve("object", "sensor", 40.0, 30.0)
    if not ok:
        raise AssertionError(f"object WxH sensor solve should succeed: {msg}")
    if abs(float(app.rows[-1].diameter) - 25.0) > 1e-6:
        raise AssertionError(f"sensor Ø should become 25, got {app.rows[-1].diameter}")
    det = (getattr(app.rows[-1], "advanced", {}) or {}).get("Detector", {})
    if abs(float(det.get("active_width_mm", 0.0)) - 20.0) > 1e-6 or \
            abs(float(det.get("active_height_mm", 0.0)) - 15.0) > 1e-6:
        raise AssertionError(f"explicit object W x H must map to sensor 20 x 15, got {det}")
    if [float(r.thickness) for r in app.rows] != gaps_before:
        raise AssertionError("object Solve for Sensor must NOT change any thickness")
    print("object plane Solve for Image/Sensor Size (W x H) OK")


def _test_object_solve_for_thickness_width_height() -> None:
    """Object plane, 'Solve for Thickness' with an explicit Width x Height
    (bugs/0057): object W=40, H=30 -> diagonal 50, semi 25 -> the conjugate pair
    moves so that field fills the current Ø24 sensor (identical to the width-only
    path that derives a 4:3 H). The sensor is left untouched."""
    app = _build_editor()
    qe = _service(app)
    sensor_before = float(app.rows[-1].diameter)
    ok, msg = qe.fov_solve("object", "thickness", 40.0, 30.0)
    if not ok:
        raise AssertionError(f"object WxH thickness solve should succeed: {msg}")
    mag = 12.0 / 25.0
    exp_obj = 50.0 * (1.0 + 1.0 / mag)
    exp_img = 50.0 * (1.0 + mag)
    if abs(float(app.rows[0].thickness) - exp_obj) > 1e-6:
        raise AssertionError(f"object gap should be {exp_obj:.6g}, got {app.rows[0].thickness}")
    if abs(float(app.rows[2].thickness) - exp_img) > 1e-6:
        raise AssertionError(f"image gap should be {exp_img:.6g}, got {app.rows[2].thickness}")
    if abs(float(app.rows[-1].diameter) - sensor_before) > 1e-9:
        raise AssertionError("object Solve for Thickness must NOT resize the sensor")
    print("object plane Solve for Thickness (W x H) OK")


def _test_object_fov_dimensions_prefill() -> None:
    """bugs/0057: the object popup prefills Width x Height from the sensor rectangle
    divided by the magnification. Sensor Ø24 (4:3 -> 19.2 x 14.4) at |m|=0.5 -> the
    object field that fills it is 38.4 x 28.8 mm."""
    qe = _service(_build_editor())
    wh = qe.object_fov_dimensions()
    if wh is None or abs(wh[0] - 38.4) > 1e-6 or abs(wh[1] - 28.8) > 1e-6:
        raise AssertionError(f"object_fov_dimensions should be (38.4, 28.8), got {wh}")
    print("object plane W x H prefill OK")


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


def _test_image_solve_for_sensor_width_height() -> None:
    """Image plane, 'Solve for Image/Sensor Size' with an explicit Width x Height
    (bugs/0055 follow-up): W=16, H=12 -> image-circle Ø = sqrt(16^2+12^2) = 20, and
    the rectangular detector dims are written so the overlay reads the real sensor.
    No thickness changes."""
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    ok, msg = qe.fov_solve("image", "sensor", 16.0, 12.0)
    if not ok:
        raise AssertionError(f"image WxH sensor solve should succeed: {msg}")
    if abs(float(app.rows[-1].diameter) - 20.0) > 1e-6:
        raise AssertionError(f"sensor Ø should become 20, got {app.rows[-1].diameter}")
    det = (getattr(app.rows[-1], "advanced", {}) or {}).get("Detector", {})
    if abs(float(det.get("active_width_mm", 0.0)) - 16.0) > 1e-6 or \
            abs(float(det.get("active_height_mm", 0.0)) - 12.0) > 1e-6:
        raise AssertionError(f"explicit W x H must be stored on the detector, got {det}")
    if [float(r.thickness) for r in app.rows] != gaps_before:
        raise AssertionError("image Solve for Sensor must NOT change any thickness")
    print("image plane Solve for Image/Sensor Size (W x H) OK")


def _test_pick_disk_registers_row() -> None:
    """bugs/0055 follow-up: the Object/Image planes need a *pickable* disk actor so
    they hover-highlight and accept the double-click. Without it only the detector
    footprint (image side) was pickable, so the Object plane never lit up on hover
    and could not be double-clicked."""
    import pyvista as pv

    from KrakenOS.UI.services.quick_estimation_overlay import QuickEstimationOverlayService

    captured: list[dict] = []

    class _FakeInspector:
        def __init__(self, editor):
            self.editor = editor

        def _add_mesh_actor(self, mesh, **kw):
            captured.append(kw)

    app = _build_editor()
    svc = QuickEstimationOverlayService(_FakeInspector(app), pv_module=pv)
    svc._pick_disk_actor((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 12.0, (0.2, 0.9, 0.35), 0)
    if not captured:
        raise AssertionError("the pick disk must add a mesh actor")
    if captured[-1].get("pick_row_index") != 0:
        raise AssertionError(f"the pick disk must register pick_row_index, got {captured[-1]}")
    # The overlay must place a pickable disk on BOTH the Object (row 0) and the
    # terminal (image) plane.
    src = inspect.getsource(QuickEstimationOverlayService.add_overlays)
    if src.count("_pick_disk_actor") < 2:
        raise AssertionError("add_overlays must place pickable disks on both planes")
    print("pickable plane disk registration OK")


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


def _test_solve_single_dimension() -> None:
    """bugs/0071: the popup lets the user fill JUST one box -- the blank side is
    derived from the live sensor aspect (default 4:3). ``fov_solve`` accepts a None
    width or height and an explicit ``aspect``."""
    # Image 'sensor', height only (default 4:3): H=12 -> W=16, Ø=sqrt(16^2+12^2)=20.
    app = _build_editor()
    qe = _service(app)
    gaps_before = [float(r.thickness) for r in app.rows]
    ok, msg = qe.fov_solve("image", "sensor", None, 12.0)
    if not ok:
        raise AssertionError(f"image sensor solve with height only should succeed: {msg}")
    if abs(float(app.rows[-1].diameter) - 20.0) > 1e-6:
        raise AssertionError(f"height-only sensor Ø should be 20, got {app.rows[-1].diameter}")
    det = (getattr(app.rows[-1], "advanced", {}) or {}).get("Detector", {})
    if abs(float(det.get("active_width_mm", 0.0)) - 16.0) > 1e-6 or \
            abs(float(det.get("active_height_mm", 0.0)) - 12.0) > 1e-6:
        raise AssertionError(f"height-only must derive W=16 (4:3 of H=12), got {det}")
    if [float(r.thickness) for r in app.rows] != gaps_before:
        raise AssertionError("a sensor solve must not change any thickness")

    # The width-only path must reach the identical sensor (symmetry).
    app2 = _build_editor()
    qe2 = _service(app2)
    qe2.fov_solve("image", "sensor", 16.0, None)
    if abs(float(app2.rows[-1].diameter) - 20.0) > 1e-6:
        raise AssertionError("width-only and height-only must reach the same Ø20 sensor")

    # Object 'thickness', height only: H=30 -> W=40, diag 50 (== the width-only path).
    app3 = _build_editor()
    qe3 = _service(app3)
    ok, msg = qe3.fov_solve("object", "thickness", None, 30.0)
    if not ok:
        raise AssertionError(f"object thickness solve with height only should succeed: {msg}")
    mag = 12.0 / 25.0
    if abs(float(app3.rows[0].thickness) - 50.0 * (1.0 + 1.0 / mag)) > 1e-6 or \
            abs(float(app3.rows[2].thickness) - 50.0 * (1.0 + mag)) > 1e-6:
        raise AssertionError("height-only object thickness must match the width-only conjugate solve")

    # A custom aspect (the live sensor's W:H, e.g. the 65MP Bopixel 29.9:22.4) fills
    # the blank box at that ratio: H=22.4 -> W=29.9, Ø=sqrt(29.9^2+22.4^2)=37.36.
    app4 = _build_editor()
    qe4 = _service(app4)
    ok, msg = qe4.fov_solve("image", "sensor", None, 22.4, aspect=(29.9, 22.4))
    if not ok:
        raise AssertionError(f"aspect-driven sensor solve should succeed: {msg}")
    det4 = (getattr(app4.rows[-1], "advanced", {}) or {}).get("Detector", {})
    if abs(float(det4.get("active_width_mm", 0.0)) - 29.9) > 1e-6 or \
            abs(float(det4.get("active_height_mm", 0.0)) - 22.4) > 1e-6:
        raise AssertionError(f"the blank width must derive from the 29.9:22.4 aspect, got {det4}")
    if abs(float(app4.rows[-1].diameter) - 37.36000535331867) > 1e-4:
        raise AssertionError(f"aspect-driven image circle Ø should be 37.36, got {app4.rows[-1].diameter}")

    # Both boxes blank -> refuse cleanly, model untouched.
    app5 = _build_editor()
    qe5 = _service(app5)
    gaps5 = [float(r.thickness) for r in app5.rows]
    sensor5 = float(app5.rows[-1].diameter)
    if qe5.fov_solve("object", "sensor", None, None)[0] is not False:
        raise AssertionError("both-blank object sensor solve must be refused")
    if qe5.fov_solve("image", "sensor", None, None)[0] is not False:
        raise AssertionError("both-blank image sensor solve must be refused")
    if [float(r.thickness) for r in app5.rows] != gaps5 or float(app5.rows[-1].diameter) != sensor5:
        raise AssertionError("a refused (both-blank) solve must leave the model untouched")
    print("one-box solve (fill just Width or just Height, aspect-derived) OK")


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
    if "height_var" not in popup or "Height" not in popup:
        raise AssertionError("both popups must offer a Height field (W x H)")
    if "object_fov_dimensions" not in popup:
        raise AssertionError("the object popup must prefill W x H from object_fov_dimensions")
    apply_src = inspect.getsource(Kraken3DInspector._apply_quick_estimation_fov_solve)
    if 'fov_solve' not in apply_src:
        raise AssertionError("the popup commit must call qe.fov_solve")
    # bugs/0071: fill just one box -- the popup parses each box independently (blank
    # is allowed) and threads the live sensor aspect so the blank side is derived.
    if "_read_dim" not in popup:
        raise AssertionError("the popup must parse each box independently so one can be left blank")
    if "aspect" not in popup or "aspect" not in apply_src:
        raise AssertionError("the popup must thread the live sensor aspect to fill the blank box")
    print("double-click gesture + popup wiring OK")


def main() -> int:
    _test_horizontal_mapping()
    _test_object_solve_for_thickness()
    _test_object_solve_for_sensor()
    _test_object_solve_for_sensor_width_height()
    _test_object_solve_for_thickness_width_height()
    _test_object_fov_dimensions_prefill()
    _test_image_solve_for_sensor()
    _test_image_solve_for_sensor_width_height()
    _test_pick_disk_registers_row()
    _test_image_solve_for_thickness()
    _test_solve_refuses_bad_input()
    _test_solve_single_dimension()
    _test_double_click_gesture_wiring()
    print("FOV plane-solve validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
