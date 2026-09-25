"""Display-free guard: the results and debug panels are data, and Qt has them (bugs/0898,
docs/design_qt_migration.md phase 6).

Three more Tk widgets the MODEL wrote into directly, of the kind 0893 removed:

```python
self.results_table.insert("", "end", values=(key, value))   # 98 property/value pairs
self.debug_text.insert("end", line + "\\n")
self.progress_text.insert("end", message.rstrip() + "\\n")
```

None is view code -- what the analysis found and what it logged are results. They are now
`editor.results_items`, `editor.debug_lines` and `editor.progress_lines`, published through
`show_results` / `show_debug_line` / `show_progress_line`, which each shell implements and a
shell-less editor simply does not have. That is what gave the Qt shell its Results, Debug and
Progress docks, which it never had.

  S  no model function reaches for `results_table` or `debug_text` any more, and Copy Debug
     copies the model's own lines
  M  the REAL Tk results table holds exactly `results_items`, every entry a pair of strings
  D  a debug line lands in `debug_lines`, in the log FILE and in the widget, and Copy Debug
     puts the model's own text on the clipboard; a progress line lands in `progress_lines`
  H  an editor with no shell keeps publishing all three and raises nothing
  Q  the Qt shell's docks show the model's own rows, and its property list is the Tk one
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

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    editor.refresh_plot()
    app.processEvents()

    panel = window.results_panel
    shown = panel.rows()
    items = [[key, value] for key, value in editor.results_items]
    marker = "guard 0898: one line from the model"
    editor.append_debug(marker)
    editor.append_progress("guard 0898: a progress line")
    app.processEvents()
    log = panel.log.toPlainText()
    progress = panel.progress.toPlainText()
    docks = sorted(window.dock_manager.docks)
    rows = [["Q", shown == items and len(items) > 20 and marker in log
             and "guard 0898: a progress line" in progress
             and {"ResultsDock", "DebugDock", "ProgressDock"} <= set(docks),
             f"the Qt shell's docks {docks} show the model's own {len(items)} results rows, and "
             f"its debug and progress lines reached their logs"]]
    rows.append(["keys", True, [key for key, _value in editor.results_items]])
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
        "from KrakenOS.UI.validate_open3d_0898_results_and_debug_panels import qt_runtime_checks\n"
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
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.analysis_compute_workflow import (DEBUG_LOG_PATH,
                                                                AnalysisComputeWorkflowMixin)

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    set_results = inspect.getsource(AnalysisComputeWorkflowMixin._set_results)
    append_debug = inspect.getsource(AnalysisComputeWorkflowMixin.append_debug)
    copy_debug = inspect.getsource(AnalysisComputeWorkflowMixin.copy_debug_to_clipboard)
    append_progress = inspect.getsource(AnalysisComputeWorkflowMixin.append_progress)
    ok("results_table" not in set_results and "self.results_items" in set_results
       and 'getattr(self, "show_results", None)' in set_results
       and "debug_text" not in append_debug and "self.debug_lines.append" in append_debug
       and 'getattr(self, "show_debug_line", None)' in append_debug
       and "debug_text" not in copy_debug and "self.debug_lines" in copy_debug
       and "progress_text" not in append_progress
       and "self.progress_lines.append" in append_progress,
       "S: the model publishes results_items, debug_lines and progress_lines through a seam "
       "each shell implements -- no Treeview, no Text, and Copy Debug copies the model's own "
       "lines")

    keys_tk: list = []
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor.refresh_plot()

        items = list(editor.results_items)
        keys_tk = [key for key, _value in items]
        table = editor.results_table
        shown = [[str(value) for value in table.item(iid, "values")]
                 for iid in table.get_children("")]
        ok(shown == [[key, value] for key, value in items] and len(items) > 20
           and all(isinstance(key, str) and isinstance(value, str) for key, value in items),
           f"M: the Tk results table holds exactly the model's {len(items)} pairs, every one a "
           f"pair of strings"
           if shown == [[key, value] for key, value in items] else
           f"M: the table shows {len(shown)} rows for {len(items)} model items")

        # ---- D one line, three places -----------------------------------------------------
        before_lines = len(editor.debug_lines)
        marker = "guard 0898: one line from the model"
        editor.append_debug(marker)
        editor.append_progress("guard 0898: a progress line")
        widget_text = editor.debug_text.get("1.0", "end-1c")
        progress_text = editor.progress_text.get("1.0", "end-1c")
        logged = ""
        if DEBUG_LOG_PATH.exists():
            logged = DEBUG_LOG_PATH.read_text(encoding="utf-8", errors="replace")
        copied = {"text": None}
        editor._copy_text_to_clipboard = lambda text: (copied.update(text=text) or (True, "test"))
        editor.copy_debug_to_clipboard()
        ok(len(editor.debug_lines) == before_lines + 1 and editor.debug_lines[-1] == marker
           and marker in widget_text and marker in logged
           and editor.progress_lines[-1:] == ["guard 0898: a progress line"]
           and "guard 0898: a progress line" in progress_text
           and copied["text"] == "\n".join(editor.debug_lines),
           f"D: the line reached debug_lines ({len(editor.debug_lines)}), the widget and "
           f"{DEBUG_LOG_PATH.name}, a progress line reached progress_lines and its own widget, "
           f"and Copy Debug put the model's own {len(copied['text'] or '')} characters on the "
           f"clipboard"
           if editor.debug_lines[-1:] == [marker] else
           f"D: debug_lines ends {editor.debug_lines[-1:]!r}, widget has marker="
           f"{marker in widget_text}, copied={str(copied['text'])[:40]!r}")

        # ---- H no shell -------------------------------------------------------------------
        del editor.show_results
        del editor.show_debug_line
        del editor.show_progress_line
        editor.results_items = []
        editor._set_results([("Key", "Value"), ("Other", 2)])
        editor.append_debug("guard 0898: shell-less")
        editor.append_progress("guard 0898: shell-less progress")
        ok(editor.results_items == [("Key", "Value"), ("Other", "2")]
           and editor.debug_lines[-1] == "guard 0898: shell-less"
           and editor.progress_lines[-1] == "guard 0898: shell-less progress",
           "H: with no shell the model still publishes all three, coercing every results value "
           "to text, and raises nothing")
    finally:
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
    else:
        for row in qt_rows:
            if row[0] == "keys":
                ok(row[2] == keys_tk,
                   f"P: the Qt shell reports the same {len(keys_tk)} properties as Tk, in order"
                   if row[2] == keys_tk else
                   f"P: Qt reports {len(row[2])} properties, Tk {len(keys_tk)}; first difference "
                   f"{next((a, b) for a, b in zip(row[2], keys_tk) if a != b)}")
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
