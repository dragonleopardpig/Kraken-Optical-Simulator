"""Display-free guard: the system inputs in Qt (bugs/0900,
docs/design_qt_migration.md phase 6).

0899 let the Qt shell pick plots and press Update; it still could not change WHAT was traced.
Object mode, wavelength, ray fan count, aperture and field were labels and value lists written
into two Tk panels' `build()`, and the commit each one ran -- resync, mark the plot stale -- was
a method on those panels rather than on the model.

`KrakenOS/UI/system_controls.py` names, for each input, the model variable it edits and the
model method to call after a change, so a view is layout and binding only. Binding is the trick
the status bar already uses: these variables carry `trace_add` whether a Tk panel or a UI host
made them, so the model writing a value repaints the widget and the widget writing one goes
through the model's own commit.

  C  the catalogue names 8 inputs, each against a variable the model registry declares, and the
     two Tk panels read their labels and choices from it
  F  the field-type tables live in ONE place now; the editor and the 3D inspector held a copy
     each and both import them
  S  the commits are the model's -- the Tk panels delegate
  B  in Qt the model writing a value repaints the form, and the form writing one reaches the
     model and marks the plot stale
  L  a control whose label depends on the system (the field value) shows the model's live label
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.system_controls import control_for

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    panel = window.system_panel
    rows: list[list] = []

    loaded = panel.values()

    # ---- B model -> view -----------------------------------------------------------------
    editor.wavelength_var.set("0.633")
    app.processEvents()
    repainted = panel.values()["wavelength_var"]

    # ---- B view -> model -----------------------------------------------------------------
    status_before = str(editor.status_var.get())
    panel.widgets["aperture_value_var"].setText("6.5")
    panel._commit(control_for("aperture_value_var"))
    app.processEvents()
    reached = str(editor.aperture_value_var.get())
    status_after = str(editor.status_var.get())

    rows.append(["B", repainted == "0.633" and reached == "6.5"
                 and status_after != status_before and "Update" in status_after,
                 f"the model writing 0.633 repainted the form ({repainted!r}) and the form "
                 f"writing 6.5 reached the model ({reached!r}), leaving the status line "
                 f"{status_after[:46]!r}"])

    rows.append(["L", panel.labels["field_value_var"].text() != control_for(
        "field_value_var").label and panel.labels["field_value_var"].text().strip() != "",
        f"the field value's label is the model's live one "
        f"({panel.labels['field_value_var'].text()!r}), not the catalogue's fallback"])

    rows.append(["loaded", True, loaded])
    window.close()
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
        "from KrakenOS.UI.validate_open3d_0900_system_controls import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["B", False, "the Qt subprocess timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["B", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["B", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI import open3d_inspector, system_controls
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.model_variables import MODEL_VARIABLES
    from KrakenOS.UI.panels import main_field_controls, main_trace_display_controls
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin
    from KrakenOS.UI.system_controls import SYSTEM_CONTROLS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    trace_source = inspect.getsource(main_trace_display_controls)
    field_source = inspect.getsource(main_field_controls)
    unregistered = [control.key for control in SYSTEM_CONTROLS
                    if control.key not in MODEL_VARIABLES]
    ok(len(SYSTEM_CONTROLS) == 8 and not unregistered
       and trace_source.count("control_for(") >= 8 and field_source.count("control_for(") >= 2
       and '"Aperture type"' not in trace_source and '"Field type"' not in field_source,
       f"C: {len(SYSTEM_CONTROLS)} inputs, every one against a variable the registry declares, "
       f"and both Tk panels read their labels and choices from the catalogue"
       + (f" -- unregistered: {unregistered}" if unregistered else ""))

    editor_source = (Path("KrakenOS/UI/layout_editor.py")).read_text(encoding="utf-8")
    inspector_source = inspect.getsource(open3d_inspector)
    ok('FIELD_TYPE_CANONICAL_VALUES = (' not in editor_source
       and 'FIELD_TYPE_CANONICAL_VALUES = (' not in inspector_source
       and system_controls.FIELD_TYPE_CANONICAL_VALUES
       == open3d_inspector.FIELD_TYPE_CANONICAL_VALUES
       and len(system_controls.FIELD_TYPE_DISPLAY_LABELS) == 4,
       f"F: the {len(system_controls.FIELD_TYPE_CANONICAL_VALUES)} field types are declared "
       f"once and imported by the editor and the 3D inspector, which held a copy each")

    commit_trace = inspect.getsource(LayoutShellControlsMixin.commit_trace_controls)
    commit_field = inspect.getsource(LayoutShellControlsMixin.commit_field_controls)
    panel_trace = inspect.getsource(
        main_trace_display_controls.MainTraceDisplayControlsPanel._commit_trace_controls)
    ok("_mark_plot_update_pending" in commit_trace and "_sync_left_mode_controls" in commit_trace
       and "_mark_plot_update_pending" in commit_field
       and "self.commit_trace_controls(" in panel_trace,
       "S: the commits are the model's, and the Tk panel is the callback shape that delegates")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        missing = [control.key for control in SYSTEM_CONTROLS
                   if getattr(editor, control.key, None) is None]
        label_var = getattr(editor, "field_value_label_var", None)
        live = system_controls.control_for("field_value_var").label_for(editor)
        ok(not missing and label_var is not None
           and live == str(label_var.get()).strip() and live != "Field value",
           f"L: a REAL editor has all {len(SYSTEM_CONTROLS)} variables, and the field value's "
           f"label is the model's live {live!r} rather than the catalogue's fallback"
           if not missing else f"L: the editor is missing {missing}")
    finally:
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP B/L: {qt_rows[0][2]}")
    else:
        for row in qt_rows:
            if row[0] == "loaded":
                values = row[2]
                ok(values.get("aperture_type_var") in system_controls.APERTURE_TYPES
                   and values.get("field_type_var") in system_controls.FIELD_TYPE_LABELS,
                   f"Q: the Qt form opened on the LOADED system -- {values}")
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
