"""Guard for bugs/0631 — the System Selection sizing calculator.

User: "given FOV + resolution requirement + minimum working distance, determine a
matching lens and camera." Pure first-order optics -> camera pixel count, magnification,
lens focal length (for WD_min) and image circle.

Checks (display-free):
  A  RELATIONS — required_pixel_count = ceil(FOV*1000/r); magnification = sensor/FOV;
     min focal length for WD_min round-trips (WD at that f == WD_min).
  B  COMPUTE — the full compute_system_selection on a worked example; degrades to the
     pixel count alone without a sensor; flags an aspect mismatch; rejects bad inputs.
  C  CONTRACT — the editor exposes open_system_selection_calculator and the Actions menu
     wires it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0631_system_selection
"""

from __future__ import annotations

import inspect
import math


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services import system_selection as ss

    # ---------------------------------------------------------------- A: relations
    if ss.required_pixel_count(100.0, 50.0) != 2000:
        ok = False
        notes.append("FAIL: A (bugs/0631): pixel count 100mm@50um/px != 2000")
    elif ss.required_pixel_count(100.0, 51.0) != math.ceil(100000 / 51.0):
        ok = False
        notes.append("FAIL: A (bugs/0631): pixel count is not rounded UP (under-samples)")
    elif abs(ss.system_magnification(12.8, 100.0) - 0.128) > 1e-9:
        ok = False
        notes.append("FAIL: A (bugs/0631): magnification 12.8/100 != 0.128")
    else:
        f = ss.min_focal_length_for_working_distance(200.0, 0.128)
        wd = ss.working_distance_for_focal_length(f, 0.128)
        if abs(wd - 200.0) > 1e-6:
            ok = False
            notes.append(f"FAIL: A (bugs/0631): WD at min EFL {wd} != WD_min 200 (no round-trip)")
        else:
            notes.append(f"PASS: A: pixel/mag/WD relations exact (EFL≥{f:.3f} → WD 200)")

    # ---------------------------------------------------------------- B: compute
    full = ss.compute_system_selection((100.0, 100.0), 50.0, wd_min_mm=200.0, sensor_wh_mm=(12.8, 12.8))
    pixels_only = ss.compute_system_selection((55.0, 55.0), 10.0)
    aspect = ss.compute_system_selection((100.0, 60.0), 50.0, wd_min_mm=200.0, sensor_wh_mm=(12.8, 12.8))
    if (full.required_pixels_w != 2000 or abs(full.magnification - 0.128) > 1e-9
            or abs(full.min_focal_length_mm - 200.0 * 0.128 / 1.128) > 1e-6
            or abs(full.image_circle_min_mm - math.hypot(12.8, 12.8)) > 1e-6):
        ok = False
        notes.append(f"FAIL: B (bugs/0631): worked example wrong ({full})")
    elif pixels_only.magnification is not None or pixels_only.min_focal_length_mm is not None:
        ok = False
        notes.append("FAIL: B (bugs/0631): no-sensor case still produced a lens/magnification")
    elif not any("aspect" in n.lower() for n in aspect.notes):
        ok = False
        notes.append("FAIL: B (bugs/0631): FOV/sensor aspect mismatch was not flagged")
    else:
        bad = False
        for args in [((0.0, 100.0), 50.0), ((100.0, 100.0), 0.0), ((100.0, 100.0), -1.0)]:
            try:
                ss.compute_system_selection(*args)
                bad = True
            except Exception:
                pass
        if bad:
            ok = False
            notes.append("FAIL: B (bugs/0631): a non-positive FOV/resolution was accepted")
        else:
            notes.append("PASS: B: worked example, no-sensor degrade, aspect flag, bad-input reject")

    # ---------------------------------------------------------------- C: contract
    from KrakenOS.UI.services import layout_table_workbench as wb
    from KrakenOS.UI.panels import main_window as mw

    editor_has = any(
        isinstance(cls, type) and "open_system_selection_calculator" in vars(cls)
        for cls in vars(wb).values()
    )
    menu_src = inspect.getsource(mw)
    if not editor_has:
        ok = False
        notes.append("FAIL: C (bugs/0631): editor lost open_system_selection_calculator")
    elif "open_system_selection_calculator" not in menu_src:
        ok = False
        notes.append("FAIL: C (bugs/0631): the Actions menu no longer opens the calculator")
    else:
        notes.append("PASS: C: editor method + Actions-menu entry wired")

    # ---------------------------------------------------------------- D: shared form + panel
    # bugs/0632: the form is shared by the dialog AND the 3D left panel; the dialog self-fits.
    from KrakenOS.UI.panels import open3d_live_controls as lc

    has_form = hasattr(ss, "build_system_selection_form")
    panel_src = inspect.getsource(lc.Open3DLiveControlsPanel)
    dialog_src = inspect.getsource(ss.open_system_selection_dialog)
    if not has_form:
        ok = False
        notes.append("FAIL: D (bugs/0632): the shared build_system_selection_form is gone")
    elif "build_system_selection_controls" not in panel_src or "System Selection" not in panel_src:
        ok = False
        notes.append("FAIL: D (bugs/0632): the 3D left panel lost its System Selection section")
    elif "resizable(True, True)" not in dialog_src or "_fit_to_content" not in dialog_src:
        ok = False
        notes.append("FAIL: D (bugs/0632): the dialog no longer self-fits -- the result clips")
    else:
        notes.append("PASS: D: shared form + left-panel section + self-fitting dialog")

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("System-selection-calculator validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
