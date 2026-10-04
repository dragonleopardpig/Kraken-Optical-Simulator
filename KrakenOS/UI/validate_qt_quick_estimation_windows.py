"""Guard for bugs/0953: Quick Estimation's windows open in the running shell.

The inspector's last four hand-built Tk windows -- Target FOV, the object / image plane FOV solve,
the detector's design box and the configuration table -- were invisible in the Qt shell, and the
three that wait on themselves froze it. Under a shell they are now row forms and a report; the Tk
app keeps its own windows. On om05a_folded (a frozen folded scene with an object-side fold):

  Q1 Target FOV is a modal Qt form, prefilled; both boxes blank is refused; a width alone sets the
     target from the sensor aspect; Clear removes it; and Snap to FOV WAITS for it (it reads the
     target straight after the window closes)
  Q2 the object-plane FOV form: the prefill, the two fold-leg boxes locked until ticked, a ticked
     leg greying its sibling, the design block pinned by the typed field and following it; "Solve
     for Thickness" calls the inspector's solve with what was typed; a bad width and a ticked but
     empty leg are refused and call nothing
  Q3 the image-plane form: the sensor size prefilled, no design block, "Solve for Image/Sensor
     Size" calls the solve in sensor mode
  Q4 the detector's design box is NOT modal, opens in Placement mode and is pinned by the image
     distance
  Q5 the configuration table is the shell's report dialog: 16 conjugates, and the sweep leaves the
     scene's two thicknesses as they were
  N  none of that creates a Tk popup or waits on one
  T  in the Tk app the four still open their own Tk windows and take the typed values
  P  parity: both shells show the same titles, prefills, fold-leg labels and values, design rows
     and table cells, and send the SAME arguments to the solve for the same typed input
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTQE_RESULT "
SKIP_MARK = "QTQE_SKIP "
SCENE = Path("attachment/om05a_folded.py")
#: what both shells are asked to type into the object-plane form
TYPED_WIDTH = "40"
TYPED_LEG = "7.5"


def _solve_call(args, kwargs) -> list:
    """One spied `_apply_quick_estimation_fov_solve` call, as plain data."""
    plane, mode, width, height, aspect = (list(args) + [None] * 5)[:5]
    segment, image_segment = kwargs.get("segment"), kwargs.get("image_segment")
    return [plane, mode, width, height, [round(float(v), 6) for v in aspect] if aspect else None,
            list(segment) if segment else None, list(image_segment) if image_segment else None]


# ---- the Qt half ---------------------------------------------------------------------------------
def qt_runtime_checks() -> dict:
    import math
    import time
    import tkinter as tk

    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports import quick_estimation_config as config
    from KrakenOS.UI.uihost import host_of

    tk_windows: list = []
    tk_waits: list = []
    real_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        tk_windows.append(self)

    def no_wait(self, window=None):
        tk_waits.append(window)
        try:
            (window or self).destroy()
        except Exception:
            pass

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    view = window.build_scene()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.4) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(2.0)
    inspector = view.inspector
    editor = window.editor
    qe = inspector._quick_estimation_service()
    host = host_of(inspector)
    refused: list = []
    host.showerror = lambda *a, **k: refused.append(str(a[1] if len(a) > 1 else k.get("message")))
    tk.Toplevel.__init__ = counting_init        # from here on: the inspector itself is already built
    tk.Misc.wait_window = no_wait
    rows: list = []
    facts: dict = {}

    def in_form(drive):
        """Run ``drive(dialog)`` inside the modal form the next call opens, then make sure it closes."""
        def go():
            dialog = window.last_model_form_dialog
            try:
                drive(dialog)
            finally:
                if dialog.isVisible():
                    dialog.reject()
        QTimer.singleShot(0, go)

    def buttons_of(dialog) -> list:
        return sorted(button.text().replace("&", "") for button in dialog.buttons.buttons())

    # Q1 -- Target FOV
    width0, height0 = qe.object_fov_dimensions() or (0.0, 0.0)
    seen: dict = {}

    def drive_target(dialog):
        seen["title"], seen["modal"] = dialog.windowTitle(), dialog.isModal()
        seen["prefill"] = [dialog.widgets["width"].text(), dialog.widgets["height"].text()]
        seen["buttons"] = buttons_of(dialog)
        dialog.widgets["width"].setText("")
        dialog.widgets["height"].setText("")
        dialog.action_buttons["set_target"].click()
        seen["blank"] = (list(refused), dialog.isVisible(), qe.target_object_semi())
        dialog.widgets["width"].setText("30")
        dialog.action_buttons["set_target"].click()
        seen["set"] = (dialog.isVisible(), qe.target_object_semi(), str(inspector.status_var.get()))

    qe.set_target_fov(None)
    in_form(drive_target)
    inspector._quick_estimation_set_target_fov()
    expected_semi = math.hypot(30.0, 30.0 * height0 / width0) / 2.0 if width0 else None

    def drive_clear(dialog):
        dialog.action_buttons["clear_target"].click()
        seen["cleared"] = (dialog.isVisible(), qe.target_object_semi())

    in_form(drive_clear)
    inspector._quick_estimation_set_target_fov()
    # Snap to FOV opens the form when there is no target, and reads the target when it closes
    snaps: list = []
    qe.snap_to_fov = lambda *a, **k: (snaps.append(qe.target_object_semi()), (False, "spied"))[1]

    def drive_for_snap(dialog):
        dialog.widgets["width"].setText("30")
        dialog.widgets["height"].setText("")
        dialog.action_buttons["set_target"].click()

    in_form(drive_for_snap)
    inspector._quick_estimation_snap_to_fov()
    del qe.snap_to_fov
    qe.set_target_fov(None)
    facts["target"] = {"title": seen.get("title"), "prefill": seen.get("prefill")}
    rows.append(["Q1", seen.get("title") == "Target FOV — Object Field" and seen.get("modal") is True
                 and seen.get("buttons") == ["Clear (fill sensor)", "Close", "Set Target"]
                 and seen["blank"][0] and "Width or a Height" in seen["blank"][0][0] and seen["blank"][1]
                 and seen["blank"][2] is None and seen["set"][0] is False and expected_semi is not None
                 and abs(float(seen["set"][1]) - expected_semi) < 1e-6 and "Target FOV 30 x" in seen["set"][2]
                 and seen["cleared"] == (False, None) and len(snaps) == 1
                 and abs(float(snaps[0]) - expected_semi) < 1e-6,
                 f"form {seen.get('title')!r}, modal {seen.get('modal')}, prefilled {seen.get('prefill')}, buttons "
                 f"{seen.get('buttons')}; both blank refused ({seen['blank'][0][:1]}), still open "
                 f"{seen['blank'][1]}; width 30 -> target semi {seen['set'][1]} (expected {expected_semi}), "
                 f"closed {not seen['set'][0]}; Clear -> target {seen['cleared'][1]}; Snap to FOV ran after the "
                 f"form closed with target {snaps}"])

    # Q2 -- the object-plane FOV form
    calls: list = []
    inspector._apply_quick_estimation_fov_solve = lambda *a, **k: calls.append(_solve_call(a, k))
    split = editor._folded_object_conjugate_split() or {}
    seen = {}
    del refused[:]

    def drive_object(dialog):
        widgets = dialog.widgets
        block = dialog.panels.get("design_constraints")
        seen["title"], seen["modal"] = dialog.windowTitle(), dialog.isModal()
        seen["prefill"] = [widgets["width"].text(), widgets["height"].text()]
        seen["buttons"] = buttons_of(dialog)
        seen["leg_labels"] = [dialog.form.label_for(key) for key in ("pin_object_near", "pin_object_far")
                              if key in widgets]
        seen["leg_values"] = [widgets[key].text() for key in ("object_near", "object_far") if key in widgets]
        seen["locked_at_start"] = [widgets[key].isEnabled() for key in ("object_near", "object_far") if key in widgets]
        seen["design_rows"] = [check.text() for check in block.checks.values()] if block else None
        seen["design_mode"] = block.mode if block else None
        seen["context_start"] = block.context_note.text() if block else None
        # a ticked leg greys its sibling
        widgets["pin_object_far"].setChecked(True)
        seen["far_ticked"] = [widgets[key].isEnabled() for key in
                              ("pin_object_near", "object_near", "pin_object_far", "object_far")]
        widgets["pin_object_far"].setChecked(False)
        seen["unticked"] = [widgets[key].isEnabled() for key in
                            ("pin_object_near", "object_near", "pin_object_far", "object_far")]
        # refusals: a width that is not a number; a ticked leg with nothing in it
        widgets["width"].setText("abc")
        dialog.action_buttons["solve_thickness"].click()
        widgets["width"].setText(TYPED_WIDTH)
        widgets["height"].setText("")
        widgets["pin_object_far"].setChecked(True)
        widgets["object_far"].setText("")
        dialog.action_buttons["solve_thickness"].click()
        seen["refusals"] = (list(refused), list(calls), dialog.isVisible())
        # the design block follows what is typed (real key presses: only those say "edited")
        widgets["width"].selectAll()
        QTest.keyClicks(widgets["width"], TYPED_WIDTH)
        seen["context_typed"] = block.context_note.text() if block else None
        widgets["object_far"].setText(TYPED_LEG)
        dialog.action_buttons["solve_thickness"].click()
        seen["closed"] = not dialog.isVisible()

    in_form(drive_object)
    inspector._open_quick_estimation_fov_popup("object")
    object_calls = list(calls)
    aspect = [float(text) for text in seen.get("prefill") or ("0", "0")]     # the field the form offered
    semi_typed = float(qe.horizontal_to_diagonal(float(TYPED_WIDTH))) / 2.0
    facts["fov_object"] = {key: seen.get(key) for key in ("title", "prefill", "leg_labels", "leg_values",
                                                         "design_rows", "design_mode")}
    facts["solve"] = object_calls[-1] if object_calls else None
    wanted_call = ["object", "thickness", float(TYPED_WIDTH), None, [round(float(v), 6) for v in aspect],
                   ["far", float(TYPED_LEG)], None]
    rows.append(["Q2", seen.get("title") == "Object Plane — Field of View (FOV)" and seen.get("modal") is True
                 and seen.get("buttons") == ["Close", "Solve for Image/Sensor Size", "Solve for Thickness"]
                 and seen.get("leg_values") == [f"{float(split.get('near', 0)):.6g}", f"{float(split.get('far', 0)):.6g}"]
                 and seen.get("locked_at_start") == [False, False]
                 and seen.get("far_ticked") == [False, False, True, True]
                 and seen.get("unticked") == [True, False, True, False]
                 and seen.get("design_mode") == "design" and seen.get("design_rows") == ["Object distance",
                                                                                         "Image distance", "Total track"]
                 and len(seen["refusals"][0]) == 2 and "Width must be a number" in seen["refusals"][0][0]
                 and "or untick the box" in seen["refusals"][0][1] and seen["refusals"][1] == []
                 and seen["refusals"][2] and f"{semi_typed:.4g}" in str(seen.get("context_typed"))
                 and seen.get("context_typed") != seen.get("context_start")
                 and object_calls == [wanted_call] and seen.get("closed"),
                 f"form {seen.get('title')!r}, prefilled {seen.get('prefill')}; legs {seen.get('leg_labels')} = "
                 f"{seen.get('leg_values')}, enabled at the start {seen.get('locked_at_start')}; far ticked -> "
                 f"(near box, near, far box, far) enabled {seen.get('far_ticked')}; unticked {seen.get('unticked')}; "
                 f"design rows {seen.get('design_rows')}, {seen.get('context_start')!r} -> typed {TYPED_WIDTH}: "
                 f"{seen.get('context_typed')!r}; refused {seen['refusals'][0]} with {len(seen['refusals'][1])} "
                 f"solve calls; then the solve was called with {object_calls}"])

    # Q3 -- the image-plane form
    del calls[:]
    seen = {}

    def drive_image(dialog):
        seen["title"] = dialog.windowTitle()
        seen["prefill"] = [dialog.widgets["width"].text(), dialog.widgets["height"].text()]
        seen["panels"] = sorted(dialog.panels)
        seen["legs"] = sorted(key for key in dialog.widgets if key.startswith("pin_"))
        dialog.action_buttons["solve_sensor"].click()

    in_form(drive_image)
    inspector._open_quick_estimation_fov_popup("image")
    sensor = qe.sensor_active_dimensions() or (0.0, 0.0)
    wanted_image = ["image", "sensor", float(f"{sensor[0]:.6g}"), float(f"{sensor[1]:.6g}"),
                    [round(float(v), 6) for v in sensor], None, None]
    facts["fov_image"] = {"title": seen.get("title"), "prefill": seen.get("prefill"), "legs": seen.get("legs")}
    rows.append(["Q3", seen.get("title") == "Image Plane — Sensor Size"
                 and seen.get("prefill") == [f"{sensor[0]:.6g}", f"{sensor[1]:.6g}"] and seen.get("panels") == []
                 and calls == [wanted_image],
                 f"form {seen.get('title')!r}, prefilled {seen.get('prefill')} (sensor {sensor}); design block "
                 f"{seen.get('panels')}; the solve was called with {calls}"])
    del inspector._apply_quick_estimation_fov_solve

    # Q4 -- the detector's design box
    inspector._open_detector_design_popup("")
    settle(0.3)
    dialog = window.last_model_form_dialog
    block = dialog.panels.get("design_constraints")
    image_gap = float(editor.rows[qe.image_thickness_row()].thickness)
    detector = (dialog.windowTitle(), dialog.isVisible(), dialog.isModal(), block.mode if block else None,
                block.context_note.text() if block else None, sorted(dialog.widgets))
    dialog.reject()
    settle(0.2)
    facts["detector"] = {"title": detector[0], "mode": detector[3]}
    rows.append(["Q4", detector[:4] == ("Detector — Design Lens (Quick Estimation)", True, False, "placement")
                 and f"Image distance = {image_gap:.4g}" in str(detector[4]) and detector[5] == []
                 and not dialog.isVisible(),
                 f"form {detector[0]!r}: shown {detector[1]}, modal {detector[2]}, mode {detector[3]!r}, "
                 f"{detector[4]!r} (image gap {image_gap:.4g}); fields {detector[5]}"])

    # Q5 -- the configuration table
    thickness_before = [float(editor.rows[qe.object_thickness_row()].thickness),
                        float(editor.rows[qe.image_thickness_row()].thickness)]
    inspector._show_quick_estimation_config_table()
    settle(0.3)
    report_dialog = window.last_model_report_dialog
    report = report_dialog.report
    thickness_after = [float(editor.rows[qe.object_thickness_row()].thickness),
                       float(editor.rows[qe.image_thickness_row()].thickness)]
    cells = [list(row) for row in (report.display_rows or [])]
    shown_cells = []
    if report_dialog.table is not None:
        model = report_dialog.table.model()
        shown_cells = [[str(model.data(model.index(r, c))) for c in range(model.columnCount())]
                       for r in range(model.rowCount())]
    facts["config"] = {"title": report.title, "headings": [column.heading for column in report.columns],
                       "cells": cells, "summary": report.summary}
    rows.append(["Q5", report.title == config.TITLE and report_dialog.isVisible() and len(cells) == config.STEPS
                 and shown_cells == cells and thickness_after == thickness_before,
                 f"report {report.title!r}: {len(cells)} rows, the dialog shows them {shown_cells == cells}; first "
                 f"row {cells[0] if cells else None}; object / image thickness {thickness_before} -> "
                 f"{thickness_after}"])
    report_dialog.close()

    popups = [w for w in tk_windows if w is not inspector]
    rows.append(["N", not popups and not tk_waits,
                 f"Tk popups created {len(popups)}, waits on a Tk window {len(tk_waits)}"])
    return {"rows": rows, "facts": facts}


# ---- the Tk half ---------------------------------------------------------------------------------
def tk_runtime_checks() -> dict:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    made: list = []
    real_init = tk.Toplevel.__init__

    def recording_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        made.append(self)

    tk.Toplevel.__init__ = recording_init

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def press(window, text):
        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == text).invoke()

    plan: list = []          # what the next waited-on window is asked: a callable taking the window

    def scripted_wait(self, window=None):
        plan.pop(0)(window or self)

    tk.Misc.wait_window = scripted_wait

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    editor.open_3d_view()
    for _ in range(6):
        editor.update()
    inspector = getattr(editor, "_three_d_inspector", None)
    if inspector is None or not getattr(inspector, "available", False):
        return {"rows": [["T", True, "SKIP: the embedded 3D inspector is unavailable"]], "facts": {}}
    for _ in range(6):
        inspector.update()
        editor.update()
    qe = inspector._quick_estimation_service()
    facts: dict = {}
    notes: dict = {}

    # Target FOV
    def read_target(window):
        entries = widgets(window, ttk.Entry)
        facts["target"] = {"title": str(window.title()), "prefill": [entries[0].get(), entries[1].get()]}
        entries[0].delete(0, "end")
        entries[0].insert(0, "30")
        entries[1].delete(0, "end")
        press(window, "Set Target")

    qe.set_target_fov(None)
    plan.append(read_target)
    inspector._quick_estimation_set_target_fov()
    notes["Target FOV"] = qe.target_object_semi() is not None
    qe.set_target_fov(None)

    # the object-plane FOV popup
    calls: list = []
    inspector._apply_quick_estimation_fov_solve = lambda *a, **k: calls.append(_solve_call(a, k))

    def read_object(window):
        entries = widgets(window, ttk.Entry)
        checks = widgets(window, ttk.Checkbutton)
        leg_checks = [check for check in checks if "Constrain" in str(check.cget("text"))]
        design_checks = [str(check.cget("text")) for check in checks if check not in leg_checks]
        facts["fov_object"] = {
            "title": str(window.title()),
            "prefill": [entries[0].get(), entries[1].get()],
            "leg_labels": [str(check.cget("text")) for check in leg_checks],
            "leg_values": [entries[2].get(), entries[3].get()] if len(leg_checks) == 2 else [],
            "design_rows": design_checks,
            "design_mode": "design",
        }
        entries[0].delete(0, "end")
        entries[0].insert(0, TYPED_WIDTH)
        entries[1].delete(0, "end")
        leg_checks[1].invoke()                      # the far leg
        entries[3].delete(0, "end")
        entries[3].insert(0, TYPED_LEG)
        press(window, "Solve for Thickness")

    plan.append(read_object)
    inspector._open_quick_estimation_fov_popup("object")
    facts["solve"] = calls[-1] if calls else None
    notes["object FOV"] = len(calls) == 1

    def read_image(window):
        entries = widgets(window, ttk.Entry)
        facts["fov_image"] = {"title": str(window.title()), "prefill": [entries[0].get(), entries[1].get()],
                              "legs": [f"pin_{i}" for i, check in enumerate(widgets(window, ttk.Checkbutton))
                                       if "Constrain" in str(check.cget("text"))]}
        press(window, "Cancel")

    plan.append(read_image)
    inspector._open_quick_estimation_fov_popup("image")
    del inspector._apply_quick_estimation_fov_solve
    notes["image FOV"] = "fov_image" in facts

    # the detector's design box (it does not wait)
    del made[:]
    inspector._open_detector_design_popup("")
    if made:
        popup = made[-1]
        radios = widgets(popup, ttk.Radiobutton)
        facts["detector"] = {"title": str(popup.title()),
                             "mode": str(popup.getvar(str(radios[0].cget("variable")))) if radios else None}
        popup.destroy()
    notes["detector design"] = bool(made)

    # the configuration table (it does not wait)
    del made[:]
    inspector._show_quick_estimation_config_table()
    if made:
        popup = made[-1]
        tree = widgets(popup, ttk.Treeview)[0]
        labels = [str(label.cget("text")) for label in widgets(popup, ttk.Label)]
        facts["config"] = {"title": str(popup.title()),
                           "headings": [str(tree.heading(column, "text")) for column in tree["columns"]],
                           "cells": [[str(value) for value in tree.item(item, "values")] for item in tree.get_children()],
                           "summary": labels[0] if labels else ""}
        popup.destroy()
    notes["config table"] = bool(made)

    failed = sorted(name for name, good in notes.items() if not good)
    return {"rows": [["T", not failed and len(notes) == 5,
                      f"Tk windows still open and work: {sorted(notes)}; failed {failed}"]],
            "facts": facts}


def _run(call: str) -> dict:
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
        "from KrakenOS.UI.validate_qt_quick_estimation_windows import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1500,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return {"rows": [["X", False, f"{call} timed out"]], "facts": {}}
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return {"rows": [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]], "facts": {}, "skipped": True}
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-6:]
    return {"rows": [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]], "facts": {}}


def parity(qt_facts: dict, tk_facts: dict) -> list:
    """P: what the two shells show and send, compared."""
    differ = []
    for key in ("target", "fov_object", "fov_image", "detector", "config", "solve"):
        qt_value, tk_value = qt_facts.get(key), tk_facts.get(key)
        if isinstance(qt_value, dict) and isinstance(tk_value, dict):
            for name in sorted(set(qt_value) | set(tk_value)):
                a, b = qt_value.get(name), tk_value.get(name)
                if name == "leg_labels":
                    # the Tk box ends its label with a colon; the form's label is the same words
                    a, b = [str(x).rstrip(":") for x in a or []], [str(x).rstrip(":") for x in b or []]
                if name == "legs":
                    a, b = len(a or []), len(b or [])
                if a != b:
                    differ.append(f"{key}.{name}: Qt {str(a)[:70]!r} vs Tk {str(b)[:70]!r}")
        elif qt_value != tk_value:
            differ.append(f"{key}: Qt {str(qt_value)[:90]!r} vs Tk {str(tk_value)[:90]!r}")
    compared = sorted(set(qt_facts) & set(tk_facts))
    cells = len((qt_facts.get("config") or {}).get("cells") or [])
    return [["P", len(compared) == 6 and not differ,
             f"compared {compared}: {cells} table rows, the solve call {qt_facts.get('solve')}; differences "
             f"{differ}"]]


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    qt = _run("qt_runtime_checks()")
    tk_side = _run("tk_runtime_checks()")
    rows = list(qt["rows"]) + list(tk_side["rows"])
    if not qt.get("skipped") and not tk_side.get("skipped") and qt["facts"] and tk_side["facts"]:
        rows += parity(qt["facts"], tk_side["facts"])
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
