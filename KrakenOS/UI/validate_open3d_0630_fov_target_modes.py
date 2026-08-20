"""Guard for bugs/0630 — FOV popup can target System Magnification / Resolution.

User request: in the object-plane FOV popup, drive the SAME thickness solve from the
HUD's System Magnification (m = sensor/FOV) or System Resolution (um/px) instead of
typing the object FOV. Each converts to the object field it implies and runs the solve.

Checks (display-free):
  A  CONVERSION — object_fov_for_magnification(m) = sensor/m; object_fov_for_resolution(r)
     = r*N/1000 per axis; both are the exact INVERSE of the bugs/0628 HUD formatter
     (round-trip returns the target).
  B  DEGRADATION — magnification needs a sensor size, resolution needs a camera pixel
     count; each returns None (row disabled in the dialog) when its datum is absent,
     and rejects non-positive / non-numeric targets.
  C  CONTRACT — the object FOV popup wires both modes into its solve (`_mode_target_wh`
     feeds `run`, superseding the Width/Height boxes) and bumps the grid past them.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0630_fov_target_modes
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace


def _qe(sensor, resolution):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = SimpleNamespace(
        _current_camera_record=lambda: ({"resolution_px": list(resolution)} if resolution else None)
    )
    qe = QuickEstimationService(SimpleNamespace(editor=editor))
    qe.sensor_active_dimensions = lambda: sensor
    return qe


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.system_info_hud import format_system_info_lines

    qe = _qe((23.04, 23.04), (5120, 5120))

    # ---------------------------------------------------------------- A: inverse of HUD
    mag_wh = qe.object_fov_for_magnification(0.818)
    res_wh = qe.object_fov_for_resolution(5.502)
    # round-trip through the HUD formatter: the derived FOV must report back the target.
    mag_lines = format_system_info_lines(mag_wh, (23.04, 23.04), (5120, 5120), (4.5, 4.5))
    res_lines = format_system_info_lines(res_wh, (23.04, 23.04), (5120, 5120), (4.5, 4.5))
    mag_line = next((l for l in mag_lines if l.startswith("Magnification")), "")
    res_line = next((l for l in res_lines if l.startswith("Resolution")), "")
    if mag_wh is None or abs(mag_wh[0] - 23.04 / 0.818) > 1e-6:
        ok = False
        notes.append(f"FAIL: A (bugs/0630): magnification->FOV {mag_wh} != sensor/m")
    elif "0.818x" not in mag_line:
        ok = False
        notes.append(f"FAIL: A (bugs/0630): FOV from mag 0.818 did not round-trip ({mag_line!r})")
    elif res_wh is None or abs(res_wh[0] - 5.502 * 5120 / 1000.0) > 1e-6:
        ok = False
        notes.append(f"FAIL: A (bugs/0630): resolution->FOV {res_wh} != r*N/1000")
    elif "5.502 um/px" not in res_line:
        ok = False
        notes.append(f"FAIL: A (bugs/0630): FOV from res 5.502 did not round-trip ({res_line!r})")
    else:
        notes.append("PASS: A: both target modes are exact inverses of the HUD (round-trip)")

    # ---------------------------------------------------------------- B: degradation
    no_cam = _qe((23.04, 23.04), None)
    no_sensor = _qe(None, (5120, 5120))
    if no_cam.object_fov_for_resolution(5.5) is not None:
        ok = False
        notes.append("FAIL: B (bugs/0630): resolution computed without a camera pixel count")
    elif no_sensor.object_fov_for_magnification(0.8) is not None:
        ok = False
        notes.append("FAIL: B (bugs/0630): magnification computed without a sensor size")
    elif qe.object_fov_for_magnification(0.0) is not None or qe.object_fov_for_magnification("x") is not None:
        ok = False
        notes.append("FAIL: B (bugs/0630): non-positive / non-numeric magnification accepted")
    elif qe.object_fov_for_resolution(-1) is not None or qe.object_fov_for_resolution(None) is not None:
        ok = False
        notes.append("FAIL: B (bugs/0630): non-positive / None resolution accepted")
    else:
        notes.append("PASS: B: each mode needs its datum and rejects bad targets")

    # ---------------------------------------------------------------- C: dialog contract
    from KrakenOS.UI import open3d_inspector as insp_module

    src = inspect.getsource(insp_module.Kraken3DInspector._open_quick_estimation_fov_popup)
    needles = [
        "object_fov_for_magnification",
        "object_fov_for_resolution",
        "_mode_target_wh",
        "next_row = 7",
    ]
    missing = [n for n in needles if n not in src]
    if missing:
        ok = False
        notes.append(
            f"FAIL: C (bugs/0630): the FOV popup lost its target-mode wiring ({missing}) -- "
            "the checkboxes no longer drive the solve"
        )
    else:
        notes.append("PASS: C: the object FOV popup wires both target modes into its solve")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("FOV-target-modes validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
