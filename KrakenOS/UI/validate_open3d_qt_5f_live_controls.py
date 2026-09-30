"""Phase 5f, part 2 guard (docs/design_qt_migration.md): the 3D Live Controls reach the Qt shell.

  V  coverage: every editor variable the Tk Live Controls panel edits has a Qt home -- one of the
     main window's System / Source / Trace docks (the 0900-0902 catalogue) or the 3D Live dock's
     display choices. A variable added to the Tk panel without a Qt home fails here.
  R  the Quick Estimation readouts are MODEL values: the inspector owns one host variable per key,
     and the Tk panel's readout labels are bound to those very variables (not private ones)
  Q  in a real Qt shell on om05a_folded: the 3D Live dock is there; turning Quick Estimation on
     fills its readouts; Live Mode, the camera choice and an Obj Thk role choice reach the model;
     a Variable-thickness gap checkbox sets the solve service's flag to the value shown, and back
     (the Tk toggle would read the hidden Tk checkbox, which Qt never flips)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5F2_RESULT "
SKIP_MARK = "QT5F2_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def coverage() -> list:
    from KrakenOS.UI import open3d_live_panel
    from KrakenOS.UI import system_controls
    from KrakenOS.UI.panels import open3d_live_controls

    panel_vars = set(re.findall(r'"([a-z_]+_var)"', Path(open3d_live_controls.__file__).read_text(encoding="utf-8")))
    docked = set(re.findall(r'"([a-z_]+_var)"', Path(system_controls.__file__).read_text(encoding="utf-8")))
    live = {entry[0] for entry in open3d_live_panel.DISPLAY_CHOICES}
    homeless = sorted(panel_vars - docked - live)
    return [["V", len(panel_vars) >= 20 and not homeless,
             f"{len(panel_vars)} editor variables in the Tk panel; {len(panel_vars & docked)} in the Qt docks, "
             f"{len(panel_vars & live)} in the 3D Live dock; without a Qt home: {homeless}"]]


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_live_panel import READOUT_KEYS
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor(headless=True)
    try:
        inspector = _open_inspector(app)
        model = inspector._quick_estimation_readout_vars
        owned = sorted(model) == sorted(READOUT_KEYS)
        bound = set()

        def walk(widget) -> None:
            for child in widget.winfo_children():
                try:
                    name = str(child.cget("textvariable"))
                except Exception:
                    name = ""
                if name:
                    bound.add(name)
                walk(child)

        walk(inspector)
        model_names = {str(var) for var in model.values()}
        shown = model_names & bound
        return [["R", owned and len(shown) == len(model_names),
                 f"the inspector owns {len(model)} readout variables (keys match: {owned}); "
                 f"{len(shown)} of them are bound by the Tk panel's labels"]]
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def qt_runtime_checks() -> list:
    import time

    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    insp = view.inspector
    form = getattr(window, "live_controls", None)
    if form is None:
        return [["Q", False, "the Qt shell has no 3D Live form"]]
    notes = []
    form.controls["Quick Estimation"].setChecked(True)
    for _ in range(40):
        app.processEvents()
        time.sleep(0.05)
    filled = [k for k, w in form.readouts.items() if w.text().strip() not in ("", "--")]
    notes.append(f"readouts filled={len(filled)}")
    live = form.controls["Live Mode"]
    live.setChecked(True)
    app.processEvents()
    live_ok = bool(insp.live_mode_var.get())
    live.setChecked(False)
    app.processEvents()
    camera = form.controls["Camera"]
    items = [camera.itemText(i) for i in range(camera.count())]
    before = str(insp.editor.camera_model_var.get())
    target = next((i for i in items if i != before), before)
    camera.setCurrentText(target)
    app.processEvents()
    camera_ok = str(insp.editor.camera_model_var.get()) == target
    service = insp._quick_estimation_service()
    combo = form.controls["Obj Thk"]
    role_before = service.role("object_thickness")
    new_role = next(combo.itemText(i) for i in range(combo.count()) if combo.itemText(i) != role_before)
    combo.setCurrentText(new_role)
    app.processEvents()
    role_ok = service.role("object_thickness") == new_role
    gaps = list(form.gap_checks.items())
    gap_ok = False
    if gaps:
        row_index, box = gaps[0]
        solve = insp._open3d_solve_service()
        was = bool(solve.is_variable(row_index))
        box.setChecked(not was)
        app.processEvents()
        flipped = bool(solve.is_variable(row_index)) == (not was)
        box.setChecked(was)
        app.processEvents()
        gap_ok = flipped and bool(solve.is_variable(row_index)) == was
    notes += [f"live mode={live_ok}", f"camera={camera_ok}", f"role={role_ok}", f"gaps={len(gaps)} toggle={gap_ok}"]
    dock = "LiveControlsDock" in window.dock_manager.docks
    return [["Q", dock and len(filled) >= 8 and live_ok and camera_ok and role_ok and gap_ok,
             f"3D Live dock={dock}; " + ", ".join(notes)]]


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_qt_5f_live_controls import tk_checks, qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown: VTK/Qt objects can segfault while
        # being destroyed, and a crash there loses a buffered result line (0932)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    rows = coverage() + _run("tk_checks()") + _run("qt_runtime_checks()")
    notes = [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]
    return all(ok for _k, ok, _d in rows), notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
