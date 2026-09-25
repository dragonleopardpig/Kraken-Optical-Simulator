"""Display-free guard: the source inputs in Qt (bugs/0901,
docs/design_qt_migration.md phase 6).

0900 gave the Qt shell the inputs that decide what the light goes THROUGH. This is the other
half: the 23 that decide what launches it -- source model and pupil pattern, radius and cone
angle, the seven Gaussian-beam fields, pupil r/theta, power, seed, position, direction and its
preset, and the random-source angular weight.

No new mechanism. `system_controls.SOURCE_CONTROLS` is a second group of the same
`SystemControl`, `CONTROL_GROUPS` names both, and one Qt `SystemPanel` renders either -- so the
Source dock is the System dock's class over a different tuple. The six value lists already lived
in `source_trace_helpers.py`, and `commit_source_controls` joined its two siblings on the model.

  C  23 source controls, each against a variable the model registry declares, and the Tk panel
     reads every one of their labels from the catalogue
  V  the six choice lists are `source_trace_helpers`' own, not a copy
  S  the commit is the model's; the Tk panel delegates
  G  one Qt class renders both groups, and the shell has both docks
  B  in Qt a model write repaints the source form, and a form write reaches the model and
     marks the plot stale
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
    from KrakenOS.UI.system_controls import SOURCE_CONTROLS, SYSTEM_CONTROLS, control_for

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    panel = window.source_panel
    rows: list[list] = []

    docks = sorted(window.dock_manager.docks)
    same_class = type(window.source_panel) is type(window.system_panel)
    rows.append(["G", same_class and {"SystemDock", "SourceDock"} <= set(docks)
                 and len(panel.values()) == len(SOURCE_CONTROLS)
                 and len(window.system_panel.values()) == len(SYSTEM_CONTROLS),
                 f"one class renders both groups -- {len(window.system_panel.values())} system "
                 f"and {len(panel.values())} source inputs, in docks {docks}"])

    editor.source_power_var.set("2.5")
    app.processEvents()
    repainted = panel.values()["source_power_var"]
    status_before = str(editor.status_var.get())
    panel.widgets["source_radius_var"].setText("7.25")
    panel._commit(control_for("source_radius_var"))
    app.processEvents()
    reached = str(editor.source_radius_var.get())
    status_after = str(editor.status_var.get())
    rows.append(["B", repainted == "2.5" and reached == "7.25"
                 and status_after != status_before and "Update" in status_after,
                 f"the model writing 2.5 repainted the form ({repainted!r}) and the form writing "
                 f"7.25 reached the model ({reached!r}), leaving {status_after[:44]!r}"])
    rows.append(["loaded", True, panel.values()])
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
        "from KrakenOS.UI.validate_open3d_0901_source_controls import qt_runtime_checks\n"
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
    from KrakenOS.UI import source_trace_helpers
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.model_variables import MODEL_VARIABLES
    from KrakenOS.UI.panels import main_source_controls
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin
    from KrakenOS.UI.system_controls import CONTROL_GROUPS, SOURCE_CONTROLS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    panel_source = inspect.getsource(main_source_controls)
    unregistered = [control.key for control in SOURCE_CONTROLS
                    if control.key not in MODEL_VARIABLES]
    literals = [control.label for control in SOURCE_CONTROLS
                if f'"{control.label}"' in panel_source]
    ok(len(SOURCE_CONTROLS) == 23 and not unregistered and not literals
       and panel_source.count("control_for(") >= 23
       and dict(CONTROL_GROUPS).keys() == {"System", "Source"},
       f"C: {len(SOURCE_CONTROLS)} source inputs, every one against a registry-declared "
       f"variable, and the Tk panel reads all their labels from the catalogue"
       + (f" -- unregistered {unregistered}, still literal {literals}"
          if unregistered or literals else ""))

    lists = {"source_model_var": source_trace_helpers.SOURCE_MODEL_VALUES,
             "pupil_pattern_var": source_trace_helpers.PUPIL_PATTERN_VALUES,
             "gaussian_input_mode_var": source_trace_helpers.GAUSSIAN_INPUT_MODE_VALUES,
             "gaussian_waist_side_var": source_trace_helpers.GAUSSIAN_WAIST_SIDE_VALUES,
             "source_direction_preset_var": source_trace_helpers.SOURCE_DIRECTION_PRESET_VALUES,
             "source_angular_weight_var": source_trace_helpers.SOURCE_ANGULAR_WEIGHT_VALUES}
    by_key = {control.key: control for control in SOURCE_CONTROLS}
    wrong = [key for key, values in lists.items() if by_key[key].choices != tuple(values)]
    ok(not wrong and all(by_key[key].kind == "choice" for key in lists),
       f"V: the {len(lists)} choice lists ARE source_trace_helpers' own "
       f"({sum(len(v) for v in lists.values())} options in total), not a copy"
       + (f" -- differ: {wrong}" if wrong else ""))

    commit = inspect.getsource(LayoutShellControlsMixin.commit_source_controls)
    panel_commit = inspect.getsource(
        main_source_controls.MainSourceControlsPanel._commit_source_controls)
    ok("_mark_plot_update_pending" in commit and "_sync_left_mode_controls" in commit
       and "self.commit_source_controls(" in panel_commit,
       "S: the commit is the model's, and the Tk panel is the callback shape that delegates")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        missing = [control.key for control in SOURCE_CONTROLS
                   if getattr(editor, control.key, None) is None]
        offered = {key: str(getattr(editor, key).get()) for key in lists}
        unknown = [key for key, value in offered.items()
                   if value and value not in by_key[key].choices]
        ok(not missing and not unknown,
           f"T: a REAL editor has all {len(SOURCE_CONTROLS)} source variables, and every choice "
           f"it holds is in the catalogue's own list ({offered})"
           if not missing else f"T: the editor is missing {missing}")
    finally:
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP G/B: {qt_rows[0][2]}")
    else:
        for row in qt_rows:
            if row[0] == "loaded":
                values = row[2]
                ok(values.get("source_model_var") in source_trace_helpers.SOURCE_MODEL_VALUES,
                   f"Q: the Qt source form opened on the loaded source "
                   f"({values.get('source_model_var')!r}, pattern "
                   f"{values.get('pupil_pattern_var')!r})")
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
