"""Display-free guard: the analysis picker and Update in Qt (bugs/0899,
docs/design_qt_migration.md phase 6).

The Qt shell could open every dialog and, since 0898, show every result -- but it could not set
an analysis UP. The 24 plots a user can tick, their grouping in the picker and their tooltips
were literals inside the Tk toolbar's `build()`, and the model reached back into that toolbar to
write the button's caption:

```python
menubutton.configure(text="Plots: 3 ▾")
```

The plots are `KrakenOS/UI/analysis_modes.py` now, and the caption comes back through
`show_analysis_modes(modes, caption)`, which each shell implements. `selected_analysis_modes`
stays the one truth; a shell only ticks what it is handed.

  C  the catalogue is data -- 24 modes in 5 groups, a tooltip each -- and the Tk panel holds
     neither literal any more
  N  the toolbar CAPTIONS are deliberately not the long `ANALYSIS_MODE_LABELS`: five differ,
     because a button has room for "WFront" and the status line wants "Wavefront"
  S  the model no longer configures a Tk widget; it hands the selection to a seam
  T  the REAL Tk toolbar ticks the model's own variables and shows the model's own caption
  Q  the Qt menu offers the same 24; ticking and unticking drive the model, and the caption
     follows the model rather than the click
  U  Qt's Update runs the analysis the model was told to run
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
    from KrakenOS.UI.analysis_modes import MODES, selection_label
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    bar = window.analysis_toolbar
    rows: list[list] = []

    offered = sorted(bar.actions)
    start_caption = bar.button.text()
    bar.toggle("spot")
    bar.toggle("mtf")
    app.processEvents()
    ticked = bar.selected()
    model = list(editor.selected_analysis_modes)
    two_caption = bar.button.text()
    bar.toggle("spot")
    app.processEvents()
    one = bar.selected()
    one_model = list(editor.selected_analysis_modes)
    rows.append(["Q", offered == sorted(MODES) and ticked == ["mtf", "spot"]
                 and model == ["spot", "mtf"] and one == ["mtf"] and one_model == ["mtf"]
                 and two_caption == selection_label(2).replace("▾", "").strip()
                 and start_caption == selection_label(0).replace("▾", "").strip(),
                 f"the Qt menu offers all {len(offered)} plots; ticking gave the model "
                 f"{model} and unticking left {one_model}, with the caption reading "
                 f"{two_caption!r} then {bar.button.text()!r}"])

    before = len(editor.results_items)
    bar.run_update()
    app.processEvents()
    rows.append(["U", len(editor.results_items) > 20 and editor.analysis_mode == "mtf",
                 f"Update ran the analysis the model was told to run "
                 f"(analysis_mode={editor.analysis_mode!r}, {before} -> "
                 f"{len(editor.results_items)} results rows)"])
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
        "from KrakenOS.UI.validate_open3d_0899_analysis_toolbar import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.analysis_modes import (MODE_GROUPS, MODE_TOOLTIPS, MODES, mode_caption,
                                            selection_label)
    from KrakenOS.UI.layout_plot_controller import ANALYSIS_MODE_LABELS
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels import main_analysis_controls
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    panel_source = inspect.getsource(main_analysis_controls)
    ok(len(MODES) == 24 and len(MODE_GROUPS) == 5
       and all(mode in MODE_TOOLTIPS for mode in MODES)
       and "mode_button_groups = MODE_GROUPS" in panel_source
       and "Spot Diagram: traced ray intercepts" not in panel_source,
       f"C: the catalogue is data -- {len(MODES)} plots in {len(MODE_GROUPS)} groups with a "
       f"tooltip each -- and the Tk panel reads it instead of holding the literals")

    differ = [(mode, mode_caption(mode), ANALYSIS_MODE_LABELS.get(mode))
              for mode in MODES if mode_caption(mode) != ANALYSIS_MODE_LABELS.get(mode)]
    ok(len(differ) == 5 and ("wavefront", "WFront", "Wavefront") in differ,
       f"N: {len(differ)} captions are deliberately shorter than the long labels "
       f"({', '.join(f'{c}/{l}' for _m, c, l in differ)}) -- two tables, two jobs, neither a "
       f"copy of the other")

    sync = inspect.getsource(LayoutShellControlsMixin._sync_analysis_mode_buttons)
    ok("menubutton" not in sync and "configure(" not in sync
       and 'getattr(self, "show_analysis_modes", None)' in sync
       and "selection_label(" in sync,
       "S: the model hands its selection and its own caption to a seam -- it configures no "
       "widget")

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        button = getattr(editor, "analysis_mode_menubutton", None)
        editor.toggle_analysis_mode("spot")
        editor.toggle_analysis_mode("mtf")
        ticked = sorted(mode for mode, var in editor.analysis_mode_vars.items() if var.get())
        caption = button.cget("text") if button is not None else ""
        editor.toggle_analysis_mode("spot")
        one = sorted(mode for mode, var in editor.analysis_mode_vars.items() if var.get())
        ok(ticked == ["mtf", "spot"] and caption == selection_label(2) and one == ["mtf"]
           and button.cget("text") == selection_label(1)
           and set(editor.analysis_mode_vars) == set(MODES),
           f"T: the REAL Tk toolbar ticked {ticked} and read {caption!r}, then {one} and "
           f"{button.cget('text')!r} -- the model's own variables and the model's own caption"
           if button is not None else "T: the Tk toolbar has no picker button")
    finally:
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q/U: {qt_rows[0][2]}")
    else:
        for name, passed, detail in qt_rows:
            ok(passed, f"{name}: {detail}")

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
