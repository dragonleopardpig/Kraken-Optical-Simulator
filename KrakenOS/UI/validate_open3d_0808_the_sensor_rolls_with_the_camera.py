"""bugs/0808 -- the sensor rolls with the camera.

flag_20260917_140152 (MV-CS050-60UM on the TCL4.0X): "Since this is a rectangular sensor, can you make
sure when I rotate the camera, the FOV length x width will become width x length?"

Measured on the user's scene after they rolled the camera body to 90 deg: the drawn body turned, the
FOV rectangle, the sensor rectangle and the launched 9-point field did not (+-1.056 x +-0.883 mm on
the object, +-4.223 x +-3.533 mm on the sensor, landscape). Nothing read the roll: every consumer asks
``_current_camera_sensor_active_mm`` for the WORLD horizontal x vertical extent.

The same flag's "FIELD REACHES THE SENSOR EDGE: 2166 ray(s) land up to 0.69 mm outside the active
area" was a second, older bug: the overflow check built its own in-plane frame with the sensor WIDTH
along Y, so a landscape field that exactly fills the sensor was judged transposed (0.69 = 4.223 -
3.533; 2166 = the 6 of 9 field points at |x| = 4.223, x 361 rays).

A-D display-free (a mixin double + pure geometry); E the user's saved scene (SKIPs when absent).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCENE = PROJECT_ROOT / "attachment" / "MV-CS050-60UM_V5_TCL4.0X-65DI-5M.py"
CAMERA = "MV-CS050-60UMUC（V5.0）"
W, H = 8.4456, 7.0656


def _editor(roll=0.0, tilt_y=0.0, with_step=True):
    import KrakenOS.UI.layout_editor  # noqa: F401 -- late-binds the service modules' globals
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    class _Double(LayoutPolylineDisplayMixin, LayoutTableWorkbenchMixin):
        pass

    ed = _Double.__new__(_Double)
    ed.camera_model_var = SimpleNamespace(get=lambda: CAMERA)
    ed.imported_camera_step_path = Path("camera.step") if with_step else None
    ed.camera_step_rotation_z_deg = float(roll)
    ed.camera_step_rotation_y_deg = float(tilt_y)
    ed.camera_step_rotation_x_deg = 180.0
    ed.append_debug = lambda *_a, **_k: None
    ed.layout_object_fov_bands = None
    ed.inspection_part_spec = {"enabled": False}
    return ed


def _bundle(points):
    paths = [SimpleNamespace(points_world=np.array([[0.0, 0.0, 0.0], [x, y, 225.0]]),
                             termination_reason="image") for x, y in points]
    return SimpleNamespace(ray_paths=paths)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the orientation follows the body's roll ---------------------------------------------
    for roll, swapped in ((0.0, False), (90.0, True), (180.0, False), (270.0, True), (-90.0, True)):
        o = _editor(roll)._camera_sensor_orientation()
        ok(o["swapped"] is swapped and abs(o["residual_deg"]) < 1e-9,
           f"A1: roll {roll:g} deg -> swapped={o['swapped']} (quarter turns {o['quarter_turns']})")
    o = _editor(90.0, tilt_y=180.0)._camera_sensor_orientation()
    ok(o["swapped"], f"A2: a 180 deg y-flip does not undo a 90 deg roll ({o})")
    o = _editor(30.0)._camera_sensor_orientation()
    ok(not o["swapped"] and abs(o["residual_deg"] - 30.0) < 1e-9,
       f"A3: a 30 deg roll is modelled at 0 with its residual kept ({o['residual_deg']:g})")
    o = _editor(90.0, with_step=False)._camera_sensor_orientation()
    ok(not o["swapped"], "A4: no camera STEP -> nothing rolls")

    # ---- B: the world-frame sensor pair --------------------------------------------------------
    dims0 = _editor(180.0)._current_camera_sensor_active_mm()
    dims90 = _editor(90.0)._current_camera_sensor_active_mm()
    ok(dims0 is not None and abs(dims0[0] - W) < 1e-6 and abs(dims0[1] - H) < 1e-6,
       f"B1: at 180 deg the sensor reads {dims0} (landscape)")
    ok(dims90 is not None and abs(dims90[0] - H) < 1e-6 and abs(dims90[1] - W) < 1e-6,
       f"B2: at 90 deg it reads {dims90} -- W x H became H x W")

    # ---- C: the HUD pairs pixels the same way and says so ---------------------------------------
    from KrakenOS.UI.services.system_info_hud import format_sensor_roll_lines

    ok(format_sensor_roll_lines(_editor(180.0)._camera_sensor_orientation()) == [],
       "C1: a landscape camera adds no HUD line")
    line = format_sensor_roll_lines(_editor(90.0)._camera_sensor_orientation())
    ok(bool(line) and "90" in line[0] and "portrait" in line[0], f"C2: rolled 90 deg: {line}")
    line = format_sensor_roll_lines(_editor(30.0)._camera_sensor_orientation())
    ok(bool(line) and "modelled at 0" in line[0], f"C3: a non-quarter roll is SAID, not hidden: {line}")

    # ---- D: the overflow check measures in the drawn frame ------------------------------------------
    corners = [(sx * W / 2.0, sy * H / 2.0) for sx in (-1, 0, 1) for sy in (-1, 0, 1)]
    for roll, pts, label in ((180.0, corners, "landscape field on a landscape sensor"),
                             (90.0, [(y, x) for x, y in corners], "portrait field on a rolled sensor")):
        ed = _editor(roll)
        info: dict = {}
        ed._annotate_sensor_overflow(info, _bundle(pts), (0.0, 0.0, 225.0), (0.0, 0.0, 1.0))
        record = info.get("sensor_overflow") or {}
        ok(record.get("outside") == 0 and record.get("landed") == len(pts),
           f"D1: a {label} that exactly fills it lands inside ({record.get('outside')} outside)")
    ed = _editor(180.0)
    info = {}
    ed._annotate_sensor_overflow(info, _bundle(corners + [(W / 2.0 + 0.5, 0.0)]),
                                 (0.0, 0.0, 225.0), (0.0, 0.0, 1.0))
    record = info.get("sensor_overflow") or {}
    ok(record.get("outside") == 1 and abs(record.get("overflow_mm", 0.0) - 0.5) < 1e-9,
       f"D2: a ray 0.5 mm past the width edge is still counted ({record.get('outside')}, "
       f"{record.get('overflow_mm')})")

    # ---- E: the user's scene --------------------------------------------------------------------
    if not SCENE.exists():
        notes.append("SKIP: E: the MV-CS050 + TCL4.0X scene is not in this checkout")
        return (not problems), notes
    live = None
    try:
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            live = KrakenLayoutEditor(headless=True)
            live._prompt_for_missing_cad_assets = lambda: None
            live.layout_files["scene"] = SCENE
            live.load_layout_by_name("scene")
        halves = {}
        for roll in (180.0, 90.0):
            live._set_step_rotation_deg_tuple(
                "camera", (live.camera_step_rotation_x_deg, live.camera_step_rotation_y_deg, roll))
            halves[roll] = live._camera_fov_object_half_extents()
        a, b = halves[180.0], halves[90.0]
        ok(a is not None and b is not None and a[0] > a[1] and b[0] < b[1]
           and abs(a[0] - b[1]) < 1e-9 and abs(a[1] - b[0]) < 1e-9,
           f"E1: the launched object field turns with the camera: 180 deg {a} -> 90 deg {b}")
    except Exception as exc:
        ok(False, f"E: the scene check raised {type(exc).__name__}: {exc}")
    finally:
        if live is not None:
            with contextlib.suppress(Exception):
                live.destroy()
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0808 sensor-rolls-with-the-camera validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
