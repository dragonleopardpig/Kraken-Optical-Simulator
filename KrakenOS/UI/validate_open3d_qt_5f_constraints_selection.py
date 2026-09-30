"""Phase 5f, part 3a guard (docs/design_qt_migration.md): the design-constraint block and the System
Selection calculator reach the Qt shell, from ONE implementation each.

  S  System Selection: the Tk form's live result equals `system_selection_text` for the same typed
     inputs (the Tk builder now calls it) -- one parser, one answer for both shells
  D  design constraints: the Tk live panel's block, given two pins, shows exactly the message
     `design_constraints_model.evaluate` returns for them
  Q  in a real Qt shell on om05a_folded: the 3D Live dock's constraint block shows the service's
     answer for two pins, fills + disables the quantities they lock, and Apply moves the conjugate
     gaps; its System Selection button opens the calculator, whose result re-computes on input
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5F3_RESULT "
SKIP_MARK = "QT5F3_SKIP "
SCENE = Path("attachment/om05a_folded.py")
TYPED = {"fov_w": "56", "fov_h": "42", "resolution": "20", "wd_min": "100", "sensor_w": "23",
         "sensor_h": "17", "wavelength": "0.55"}


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI import design_constraints_model as model
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.system_selection import build_system_selection_form, system_selection_text
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor(headless=True)
    try:
        inspector = _open_inspector(app)
        # S -- a Tk System Selection form fed the typed inputs
        host = ttk.Frame(inspector)
        form = build_system_selection_form(host, app, compact=True, prefill=False)
        entries = [w for w in host.winfo_children() if isinstance(w, ttk.Entry)]
        for entry, key in zip(entries, ("fov_w", "fov_h", "resolution", "wd_min", "sensor_w", "sensor_h", "wavelength")):
            var_name = str(entry.cget("textvariable"))
            inspector.setvar(var_name, TYPED[key])
        form.recompute()
        tk_text = str(form.out_var.get())
        same = tk_text == system_selection_text(TYPED) and len(entries) == 7
        rows = [["S", same and "2800" in tk_text,
                 f"the Tk form's result equals system_selection_text for the same inputs: {same} "
                 f"({tk_text.splitlines()[0] if tk_text else ''})"]]
        # D -- the live panel's design-constraint block
        block = inspector._open3d_live_controls_panel()._design_constraint_controls
        q_mag, q_od = model.ROWS[0][0], model.ROWS[1][0]
        block._fix[q_mag].set(True)
        block._val[q_mag].set("0.5")
        block._fix[q_od].set(True)
        block._val[q_od].set("100")
        block.recompute()
        _states, result = model.evaluate(inspector, block._mode(), {q_mag: 0.5, q_od: 100.0})
        shown = str(block._result_var.get())
        rows.append(["D", shown == (result.get("message") or "") and "EFL" in shown,
                     f"the Tk block shows the model's message: {shown!r}"])
        return rows
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def qt_runtime_checks() -> list:
    from KrakenOS.UI import design_constraints_model as model
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    form, insp = window.live_controls, view.inspector
    q_mag, q_od = model.ROWS[0][0], model.ROWS[1][0]
    form.design_checks[q_mag].setChecked(True)
    form.design_values[q_mag].setText("0.5")
    form.design_checks[q_od].setChecked(True)
    form.design_values[q_od].setText("100")
    form.recompute_design()
    app.processEvents()
    states, result = model.evaluate(insp, "design", {q_mag: 0.5, q_od: 100.0})
    same = form.design_result.text() == (result.get("message") or "")
    locked = [q for q, s in states.items() if (s or {}).get("state") == "locked" and q in form.design_values]
    shown_locked = all(form.design_values[q].text() and not form.design_values[q].isEnabled() for q in locked)
    before = [float(r.thickness or 0.0) for r in insp.editor.rows]
    form.apply_design()
    for _ in range(10):
        app.processEvents()
    moved = [i for i, (a, b) in enumerate(zip(before, [float(r.thickness or 0.0) for r in insp.editor.rows])) if a != b]
    form.controls["System Selection Calculator…"].click()
    app.processEvents()
    dialog = window._open_dialogs[-1] if getattr(window, "_open_dialogs", None) else None
    computed = False
    if dialog is not None:
        for key in ("fov_w", "fov_h", "resolution", "wd_min"):
            dialog.on_field_changed(dialog.form.field(key), TYPED[key])
        computed = "2800" in str(dialog.form.values.get("result", ""))
    return [["Q", same and len(locked) >= 2 and shown_locked and bool(moved) and dialog is not None and computed,
             f"Qt block shows the service's answer: {same}; locked {len(locked)} shown+disabled: {shown_locked}; "
             f"Apply moved rows {moved}; calculator opened: {dialog is not None}, computed: {computed}"]]


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
        "from KrakenOS.UI.validate_open3d_qt_5f_constraints_selection import tk_checks, qt_runtime_checks\n"
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
    rows = _run("tk_checks()") + _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
