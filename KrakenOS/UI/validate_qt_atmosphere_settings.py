"""Guard for bugs/0954: Atmospheric Settings opens in the Qt shell.

It was the Tk editor's last menu-bar command without a Qt route (the parity guard's one known gap).
The Qt window is the model's own variables in the form the System / Source / Trace docks use, so
the claims are about the MODEL following the window, and the window following the model:

  A  the action sits in the ribbon's Analysis > More list; it opens ONE window that is not modal --
     asked for again, the same one comes back -- and the model's own command opens that window too
  F  its twelve inputs are the catalogue's, in order, showing the model's values
  O  an observatory preset fills temperature, pressure, humidity, CO2, latitude and altitude from
     the site's record: in the model's variables and in the window; the status line NAMES the
     preset (the plot-stale line used to replace it at once, in both shells)
  E  a typed zenith angle lands in the model's variable, and the summary under the form is the
     model's own summary line
  P  Apply marks the plot stale and leaves the analysis selection alone; "Apply + Atmos" switches
     the Atmos analysis on, once (a second press does not switch it off)
  N  none of it creates a Tk window
  T  in the Tk app the Tk window still opens, with the same title, note, twelve labels and three
     buttons, and its "Apply + Atmos" switches the Atmos analysis on
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTATMOS_RESULT "
SKIP_MARK = "QTATMOS_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
PRESET_FIELDS = {"T": "atmos_temperature_k_var", "p": "atmos_pressure_pa_var", "RH": "atmos_humidity_var",
                 "xc": "atmos_co2_ppm_var", "latitude": "atmos_latitude_deg_var", "altitude": "atmos_altitude_m_var"}


def qt_runtime_checks() -> dict:
    import time
    import tkinter as tk

    import KrakenOS as Kos
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from KrakenOS.UI import system_controls
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.ribbon import DROPDOWNS

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.0)
    editor = window.editor
    tk_windows: list = []
    real_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        tk_windows.append(self)

    tk.Toplevel.__init__ = counting_init
    rows: list = []

    # A -- one window, not modal, from the ribbon and from the model's own command
    in_more = "atmosphere_settings" in DROPDOWNS["menu:analysis_more"][1]
    listed = window.action_manager["atmosphere_settings"] in window.ribbon.dropdowns["menu:analysis_more"].menu().actions()
    window.action_manager["atmosphere_settings"].trigger()
    settle()
    dialog = window.atmosphere_dialog
    first = (dialog is not None and dialog.isVisible(), dialog.isModal() if dialog else None,
             dialog.windowTitle() if dialog else None)
    window.action_manager["atmosphere_settings"].trigger()
    editor.open_atmosphere_settings_dialog()            # the model's own command
    settle()
    same = window.atmosphere_dialog is dialog
    rows.append(["A", in_more and listed and first == (True, False, system_controls.ATMOSPHERE_TITLE) and same,
                 f"in Analysis > More: declared {in_more}, listed {listed}; the window shown/modal/title {first}; "
                 f"asked again (ribbon, then the model's command): the same window {same}"])

    # F -- the catalogue's inputs, showing the model
    panel = dialog.panel
    labels = [panel.labels[control.key].text() for control in system_controls.ATMOSPHERE_CONTROLS]
    shown = panel.values()
    model = {control.key: str(getattr(editor, control.key).get()) for control in system_controls.ATMOSPHERE_CONTROLS}
    rows.append(["F", len(labels) == 12 and labels[:2] == ["Observatory preset", "Atmos plot"]
                 and labels[2:] == [label for label, _var, _default in system_controls.ATMOSPHERE_CONTROL_SPECS]
                 and {key: str(value) for key, value in shown.items()} == model,
                 f"{len(labels)} inputs {labels}; showing the model's values: "
                 f"{ {key: str(value) for key, value in shown.items()} == model}"])

    # O -- an observatory preset
    site = sorted(getattr(Kos, "observatories", {}))[0]
    record = Kos.observatories[site]
    summary_before = dialog.summary.text()
    choices = [panel.widgets["atmos_observatory_var"].itemText(i)
               for i in range(panel.widgets["atmos_observatory_var"].count())]
    panel.widgets["atmos_observatory_var"].setCurrentText(site)
    settle()
    wanted = {variable: f"{float(record[key]):g}" for key, variable in PRESET_FIELDS.items()}
    in_model = {variable: str(getattr(editor, variable).get()) for variable in wanted}
    in_window = {variable: panel.widgets[variable].text() for variable in wanted}
    status = str(editor.status_var.get())
    rows.append(["O", choices[0] == "Manual" and site in choices and in_model == wanted and in_window == wanted
                 and status == f"Atmosphere preset set to {site}. Click Update."
                 and dialog.summary.text() != summary_before,
                 f"{len(choices)} presets; {site} -> model {in_model} (record {wanted}); the window shows them "
                 f"{in_window == wanted}; status {status!r}; the summary changed "
                 f"{dialog.summary.text() != summary_before}"])

    # E -- a typed value, and the model's summary
    field = panel.widgets["atmos_zenith_deg_var"]
    field.setFocus()
    field.selectAll()
    QTest.keyClicks(field, "30.5")
    QTest.keyClick(field, Qt.Key.Key_Return)
    settle()
    typed = str(editor.atmos_zenith_deg_var.get())
    rows.append(["E", typed == "30.5" and dialog.summary.text() == editor._format_atmosphere_summary()
                 and bool(dialog.summary.text()) and dialog.isVisible(),
                 f"typed 30.5 + Return -> the model's zenith angle {typed!r}; the summary is the model's own line "
                 f"{dialog.summary.text() == editor._format_atmosphere_summary()}: {dialog.summary.text()[:70]!r}; "
                 f"the window stayed open {dialog.isVisible()}"])

    # P -- Apply, and Apply + Atmos
    pending: list = []
    real_pending = editor._mark_plot_update_pending
    editor._mark_plot_update_pending = lambda *a, **k: (pending.append(1), real_pending(*a, **k))[1]
    modes_start = list(editor.selected_analysis_modes)
    QTest.mouseClick(dialog.apply_button, Qt.MouseButton.LeftButton)
    settle()
    after_apply = (len(pending), list(editor.selected_analysis_modes))
    QTest.mouseClick(dialog.apply_plot_button, Qt.MouseButton.LeftButton)
    settle()
    after_plot = (len(pending), list(editor.selected_analysis_modes))
    QTest.mouseClick(dialog.apply_plot_button, Qt.MouseButton.LeftButton)
    settle()
    after_again = list(editor.selected_analysis_modes)
    del editor._mark_plot_update_pending
    QTest.mouseClick(dialog.close_button, Qt.MouseButton.LeftButton)
    settle()
    rows.append(["P", "atmosphere" not in modes_start and after_apply[0] >= 1 and after_apply[1] == modes_start
                 and after_plot[0] > after_apply[0] and "atmosphere" in after_plot[1]
                 and after_again.count("atmosphere") == 1 and not dialog.isVisible(),
                 f"analyses selected at the start {modes_start}; Apply -> plot marked stale {after_apply[0]}x, "
                 f"selection {after_apply[1]}; Apply + Atmos -> {after_plot[1]}; again -> {after_again}; Close "
                 f"closed it {not dialog.isVisible()}"])

    rows.append(["N", not tk_windows, f"Tk windows created {len(tk_windows)}"])
    facts = {"title": first[2], "note": system_controls.ATMOSPHERE_NOTE, "labels": labels,
             "buttons": [dialog.apply_button.text(), dialog.apply_plot_button.text(), dialog.close_button.text()]}
    return {"rows": rows, "facts": facts}


def tk_runtime_checks() -> dict:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    made: list = []
    real_init = tk.Toplevel.__init__

    def recording_init(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        made.append(self)

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    editor = KrakenLayoutEditor()
    editor.layout_files[SCENE.stem] = SCENE
    editor.load_layout_by_name(SCENE.stem)
    for _ in range(4):
        editor.update()
    tk.Toplevel.__init__ = recording_init
    editor.open_atmosphere_settings_dialog()
    for _ in range(4):
        editor.update()
    if not made:
        return {"rows": [["T", False, "the Tk app opened no window"]], "facts": {}}
    window = made[-1]
    texts = [str(label.cget("text")) for label in widgets(window, ttk.Label)]
    buttons = [str(button.cget("text")) for button in widgets(window, ttk.Button)]
    combos = len(widgets(window, ttk.Combobox))
    entries = len(widgets(window, ttk.Entry)) - combos         # a ttk.Combobox is an Entry too
    # the note is the first label; the summary (a textvariable) the last; the rest are the inputs
    labels = [text for text in texts[1:] if text][:12]
    before = list(editor.selected_analysis_modes)
    next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == "Apply + Atmos").invoke()
    after = list(editor.selected_analysis_modes)
    again = made.count(window)
    editor.open_atmosphere_settings_dialog()             # asked again: the same window
    one_window = len(made) == again
    facts = {"title": str(window.title()), "note": texts[0] if texts else "", "labels": labels, "buttons": buttons}
    return {"rows": [["T", entries == 10 and combos == 2 and "atmosphere" not in before and "atmosphere" in after
                      and one_window,
                      f"Tk window {facts['title']!r}: {combos} lists + {entries} entries, buttons {buttons}; "
                      f"Apply + Atmos: analyses {before} -> {after}; asked again, no second window {one_window}"]],
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
        "from KrakenOS.UI.validate_qt_atmosphere_settings import qt_runtime_checks, tk_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
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


def run_checks() -> tuple[bool, list[str]]:
    qt = _run("qt_runtime_checks()")
    tk_side = _run("tk_runtime_checks()")
    rows = list(qt["rows"]) + list(tk_side["rows"])
    if qt["facts"] and tk_side["facts"]:
        differ = [f"{key}: Qt {str(qt['facts'].get(key))[:80]!r} vs Tk {str(tk_side['facts'].get(key))[:80]!r}"
                  for key in ("title", "note", "labels", "buttons") if qt["facts"].get(key) != tk_side["facts"].get(key)]
        # appended to T: the two windows say the same things
        for row in rows:
            if row[0] == "T":
                row[1] = bool(row[1]) and not differ
                row[2] += f"; title, note, labels and buttons differ from the Qt window's: {differ}"
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
