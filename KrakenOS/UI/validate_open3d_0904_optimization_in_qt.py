"""Display-free guard: optimisation in Qt (bugs/0904, docs/design_qt_migration.md phase 6).

After 0903 the Qt shell could edit the lens but not optimise it. Three things stood in the way,
and all three were the model reaching into Tk widgets:

* WHICH OPERANDS are in use existed only as a Tk Listbox's selection -- `merit_mode_list.
  curselection()`, read by three model functions. It goes through a `selected_merit_operands`
  seam now (shell first, then the Tk Listbox, then the headless list), and all three ask it.
* START/STOP: the model configured the Tk button's text and command itself. It tells a shell
  through `show_optimization_state(running)` as well now.
* MARKING A VARIABLE, and its bounds, were Tk-menu verbs keyed on the Tk item under the mouse
  (`current_menu_row_id`). `toggle_optimization_cell`, `clear_bounds_for_cell` and
  `optimization_cell_state` take a row and a field; the Tk menu verbs delegate to them.

What each per-operand setting IS (label, variable, choices, default) is
`KrakenOS/UI/optimization_controls.py`; which settings an operand HAS was already data
(`OperandSpec.controls`).

  S  no model function reads the Tk Listbox outside the one fallback, Start/Stop has a seam, and
     the Tk menu verbs delegate to the row-and-field ones
  C  the settings follow `spec.controls` for all 8 operands; the MTF lists are shared with the Tk
     panel; the catalogue's defaults are exactly what the Tk panel creates; and
     `ensure_operand_variables` fills a shell-less owner and makes nothing where Tk already did
  T  Tk is unchanged: its Listbox drives the operands, a model-set choice shows in it, its menu
     toggle marks the cell, and its button follows the run state
  Q  in Qt the dock offers the 8 operands, a pick there is what the model reads, each operand
     shows exactly its settings, a typed weight reaches the model, the cell menu offers select /
     set bounds / clear bounds with the right enabled states, a marked cell carries the Tk
     marker colour -- and a REAL optimisation started from Qt finishes with the same merit as
     the same run in Tk, the button going Stop -> Start
"""
from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
#: a sequential lens whose Spot RMS merit is real (om05a_folded's is the 1e9 sentinel in both
#: shells -- recorded in bugs/0904, not this guard's business)
TRIPLET = Path("KrakenOS/common_optical_layouts/cooke_triplet_optimization_case_study.py")
MERIT = re.compile(r"Optimization finished: ([-+0-9.eE]+) -> ([-+0-9.eE]+)")


def merit_pair(status: str):
    match = MERIT.search(str(status))
    return (float(match.group(1)), float(match.group(2))) if match else None


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.layout_editor import OPERAND_REGISTRY
    from KrakenOS.UI.optimization_controls import controls_for
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.rows_table import marker_colour

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor, panel, model = window.editor, window.optimization_panel, window.rows_model
    rows: list[list] = []

    # ---- Q1 operands and their settings ---------------------------------------------------
    offered = [panel.operands.item(i).text() for i in range(panel.operands.count())]
    panel._select_labels(["EFFL", "MTF @ freq"])
    app.processEvents()
    read = editor._selected_operand_labels()
    specs = {spec.label: spec for spec in OPERAND_REGISTRY.values()}
    expected_fields = sorted((label, control.name) for label in ("EFFL", "MTF @ freq")
                             for control in controls_for(specs[label]))
    weight = panel.fields[("EFFL", "weight")]
    weight.setText("2.5")
    panel._commit(editor.operand_weight_vars["EFFL"], weight.text())
    rows.append(["Q1", offered == [spec.label for spec in OPERAND_REGISTRY.values()]
                 and read == ["EFFL", "MTF @ freq"] and sorted(panel.fields) == expected_fields
                 and editor._operand_weight("EFFL") == 2.5,
                 f"the dock offers {len(offered)} operands; a Qt pick is what the model reads "
                 f"({read}); each shows exactly its spec's settings ({len(expected_fields)}); a "
                 f"typed weight reached _operand_weight ({editor._operand_weight('EFFL')})"])

    # ---- Q2 the cell menu and the marker --------------------------------------------------
    fields = [model.field(c) for c in range(model.columnCount())]
    row = next(i for i in range(len(editor.rows))
               if editor.optimization_cell_state(i, "thickness")["supported"]
               and editor.rows[i].surface not in ("Object", "Image")
               and not editor.optimization_cell_state(i, "thickness")["marked"])
    before = [(label, enabled) for label, enabled, _run in window.cell_menu_actions(row, "thickness")]
    window.cell_menu_actions(row, "thickness")[0][2]()
    window.refresh_from_model()
    app.processEvents()
    after = [(label, enabled) for label, enabled, _run in window.cell_menu_actions(row, "thickness")]
    colour = model.data(model.index(row, fields.index("thickness")), Qt.ItemDataRole.BackgroundRole)
    rows.append(["Q2", before and before[0][0].startswith("Select") and before[2] == ("Clear bounds", False)
                 and after[0][0].startswith("Unselect")
                 and editor.optimization_cell_state(row, "thickness")["marked"]
                 and colour is not None and colour.name().lower() == marker_colour().lower()
                 and window.cell_menu_actions(row, "label") == [],
                 f"row {row} thickness: menu {[b[0] for b in before]}, then marked and offering "
                 f"{after[0][0]!r}; the cell carries the Tk marker colour {marker_colour()}; the # "
                 f"column has no menu"])
    window.close()

    # ---- Q3 a real run from the Qt dock ---------------------------------------------------
    app2, window2 = build(["kraken"])
    window2.show()
    app2.processEvents()
    window2.build_viewport()
    window2.load_layout_path(TRIPLET)
    app2.processEvents()
    editor2, panel2 = window2.editor, window2.optimization_panel
    panel2._select_labels(["Spot RMS"])
    panel2.start_or_stop()
    app2.processEvents()
    during = panel2.start_stop.text()
    deadline = time.time() + 400
    while getattr(editor2, "optimization_running", False) and time.time() < deadline:
        app2.processEvents()
        time.sleep(0.05)
    app2.processEvents()
    rows.append(["run", True, [str(editor2.status_var.get()), during, panel2.start_stop.text()]])
    window2.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0904_optimization_in_qt import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 1200 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, OPERAND_REGISTRY
    from KrakenOS.UI.optimization_controls import OPERAND_CONTROLS, controls_for, default_for
    from KrakenOS.UI.panels import main_optimization_panel
    from KrakenOS.UI.services import analysis_compute_workflow, layout_shell_controls
    from KrakenOS.UI.services.analysis_compute_workflow import AnalysisComputeWorkflowMixin
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as Workbench
    from KrakenOS.UI.uihost import ScriptedUiHost

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- S the seams ------------------------------------------------------------------------
    listbox_reads = {
        "analysis_compute_workflow": inspect.getsource(analysis_compute_workflow).count(
            "merit_mode_list.curselection()"),
        "layout_shell_controls": inspect.getsource(layout_shell_controls).count(
            "merit_mode_list.curselection()"),
        "_selected_operand_labels": inspect.getsource(
            Workbench._selected_operand_labels).count("merit_mode_list.curselection()"),
    }
    button = inspect.getsource(AnalysisComputeWorkflowMixin._update_optimization_button_state)
    toggle = inspect.getsource(Workbench.toggle_current_optimization_cell)
    clear = inspect.getsource(Workbench.clear_current_bounds)
    ok(listbox_reads == {"analysis_compute_workflow": 0, "layout_shell_controls": 0,
                         "_selected_operand_labels": 1}
       and 'getattr(self, "selected_merit_operands", None)' in inspect.getsource(
           Workbench._selected_operand_labels)
       and 'getattr(self, "show_optimization_state", None)' in button
       and "self.toggle_optimization_cell(" in toggle and "self.clear_bounds_for_cell(" in clear,
       f"S: the Tk Listbox is read in exactly one place, the fallback inside "
       f"_selected_operand_labels ({listbox_reads}); Start/Stop has a seam; the Tk menu verbs "
       f"delegate to the row-and-field ones")

    # ---- C the catalogue ---------------------------------------------------------------------
    panel_source = inspect.getsource(main_optimization_panel)
    names = {control.name for control in OPERAND_CONTROLS} | {"field_xy"}
    unknown = [(spec.label, name) for spec in OPERAND_REGISTRY.values() for name in spec.controls
               if name not in names]
    ok(not unknown and '"Average", "Tangential", "Sagittal"' not in panel_source
       and '"Diffraction FFT", "PSF FFT", "LSF FFT"' not in panel_source
       and "MTF_MODES" in panel_source and "MTF_ALGORITHMS" in panel_source,
       f"C1: every control the {len(OPERAND_REGISTRY)} operand specs name is in the catalogue, "
       f"and the Tk panel takes the MTF lists from it")

    stand_in = SimpleNamespace(ui=ScriptedUiHost(), wavelength_var=None,
                               **{control.variables: {} for control in OPERAND_CONTROLS},
                               operand_field_x_vars={}, operand_field_y_vars={})
    made = AnalysisComputeWorkflowMixin.ensure_operand_variables(stand_in)
    expected = sum(len(controls_for(spec)) for spec in OPERAND_REGISTRY.values())

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        mismatched = []
        for spec in OPERAND_REGISTRY.values():
            for control in controls_for(spec):
                variable = getattr(editor, control.variables).get(spec.label)
                if variable is None or str(variable.get()) != default_for(control, spec, editor):
                    mismatched.append((spec.label, control.name,
                                       None if variable is None else variable.get()))
        tk_made = editor.ensure_operand_variables()
        ok(made == expected and tk_made == 0 and not mismatched,
           f"C2: ensure_operand_variables made all {made} settings for a shell-less owner and none "
           f"where the Tk panel had; the catalogue's defaults are exactly the Tk panel's"
           + (f" -- differ: {mismatched}" if mismatched else ""))

        # ---- T Tk is unchanged ------------------------------------------------------------
        no_seams = all(getattr(editor, name, None) is None for name in
                       ("selected_merit_operands", "select_merit_operands", "show_optimization_state"))
        default = editor._selected_operand_labels()
        editor._set_selected_operand_labels(["EFFL", "Magnification"])
        listbox = [editor.merit_mode_list.get(i) for i in editor.merit_mode_list.curselection()]
        editor.current_menu_row_id = editor._table_iid_for_row_index(5)
        editor.current_menu_field = "thickness"
        editor.toggle_current_optimization_cell()
        marked = editor.optimization_cell_state(5, "thickness")["marked"]
        editor.optimization_running = True
        editor._update_optimization_button_state()
        running_text = editor.optimization_start_stop_button.cget("text")
        editor.optimization_running = False
        editor._update_optimization_button_state()
        idle_text = editor.optimization_start_stop_button.cget("text")
        ok(no_seams and default == ["Spot RMS"] and listbox == ["EFFL", "Magnification"] and marked
           and (running_text, idle_text) == ("Stop Optimization", "Start Optimization"),
           "T: a Tk-only editor has no seams; its Listbox shows the model's choice, its menu "
           "toggle marks the cell, and its button follows the run state")
    finally:
        editor.destroy()

    # ---- the same run in Tk, for Q3 -------------------------------------------------------
    tk_editor = KrakenLayoutEditor(headless=True)
    try:
        tk_editor.layout_files[TRIPLET.stem] = TRIPLET
        tk_editor.load_layout_by_name(TRIPLET.stem)
        tk_editor._set_selected_operand_labels(["Spot RMS"])
        tk_editor.start_optimization()
        deadline = time.time() + 400
        while getattr(tk_editor, "optimization_running", False) and time.time() < deadline:
            tk_editor.root.update()
            time.sleep(0.05)
        tk_merit = merit_pair(tk_editor.status_var.get())
    finally:
        tk_editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
        return state["ok"], notes
    for row in qt_rows:
        if row[0] == "run":
            qt_status, during, after = row[2]
            qt_merit = merit_pair(qt_status)
            ok(qt_merit is not None and tk_merit is not None and qt_merit[1] < qt_merit[0]
               and abs(qt_merit[0] - tk_merit[0]) <= 1e-9 * max(1.0, abs(tk_merit[0]))
               and abs(qt_merit[1] - tk_merit[1]) <= 1e-9 * max(1.0, abs(tk_merit[1]))
               and (during, after) == ("Stop Optimization", "Start Optimization"),
               f"Q3: a real optimisation started from the Qt dock took the Cooke triplet's merit "
               f"{qt_merit[0]:g} -> {qt_merit[1]:g}, the same as the same run in Tk "
               f"({tk_merit[0]:g} -> {tk_merit[1]:g}), the button going {during!r} -> {after!r}"
               if qt_merit and tk_merit else f"Q3: merits Qt {qt_status!r}, Tk {tk_merit}")
            continue
        ok(row[1], f"{row[0]}: {row[2]}")
    return state["ok"], notes


def run() -> int:
    passed, notes = run_checks()
    print()
    for note in notes:
        print(("  " + note[2:]) if note.startswith("= ") else ("! " + note))
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
