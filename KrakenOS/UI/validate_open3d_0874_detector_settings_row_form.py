"""Display-free guard: the Detector Settings row form (bugs/0874,
docs/design_qt_migration.md phase 3).

The fifth row form, and the first that needed NOTHING new: four fields, a Clear action and the
model's own normaliser. That is the point of having built the framework -- a dialog of this shape
is now a builder and a menu entry.

  R  refusals: no row selected, and an Object row, which cannot be a detector
  V  the model's own messages for a non-number, a negative size and bins out of range
  D  the description reports the size, the bins and the pitch
  A  apply writes the settings through the editor's own setter; Clear removes them
  T  the REAL Tk dialog shows the builder's values
  Q  the Qt form shows the same and applies the same
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
ROW = 24  # the image/sensor row


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.row_forms.detector_settings import model

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    parts = model(editor)

    row = min(ROW, len(editor.rows) - 1)
    window.rows_view.selectRow(row)
    app.processEvents()
    dialog = window.action_manager["detector_settings"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    values = dict(dialog.values())

    dialog.widgets["active_width_mm"].setText("12.5")
    dialog.widgets["bins"].setText("64")
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()
    stored = dict(parts.read(editor.rows[row]) or {})

    window.close()
    return [values, errors, bool(applied),
            {key: str(value) for key, value in stored.items()},
            [action.label for action in dialog.form.actions]]


def _run_qt_subprocess() -> tuple[str, object]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0874_detector_settings_row_form import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", ("the Qt subprocess timed out after 900 s -- a modal dialog with no one "
                         "to close it is the usual cause")
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_values(editor, row_index):
    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_detector_settings(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    try:
        shown: list[str] = []

        def walk(widget):
            for child in widget.winfo_children():
                try:
                    name = str(child.cget("textvariable"))
                except Exception:
                    name = ""
                if name:
                    try:
                        shown.append(str(window.getvar(name)))
                    except Exception:
                        pass
                walk(child)

        walk(window)
        return shown
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_detector_settings_form
    from KrakenOS.UI.row_forms.detector_settings import model

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"

    form_values = None
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        parts = model(editor)
        row = min(ROW, len(editor.rows) - 1)

        refusals = []
        object_row = next((index for index, item in enumerate(editor.rows)
                           if item.surface == "Object"), None)
        for bad_index, expected in ((len(editor.rows) + 5, "Select a surface row first."),
                                    (object_row, "Object rows cannot be detector planes.")):
            try:
                build_detector_settings_form(editor, bad_index)
                refusals.append(("no refusal", bad_index))
            except FormRefused as exc:
                if str(exc) != expected:
                    refusals.append((str(exc), expected))
        ok(object_row is not None and not refusals,
           "R: a row out of range and an Object row each refuse with their own message"
           + (f" -- wrong: {refusals}" if refusals else ""))

        form = build_detector_settings_form(editor, row)
        form_values = dict(form.values)
        messages = [form.validate(dict(form_values, active_width_mm="wide")),
                    form.validate(dict(form_values, active_height_mm="-3")),
                    form.validate(dict(form_values, bins="2")),
                    form.validate(dict(form_values, bins="Auto"))]
        ok(all(messages[:3]) and "numbers" in messages[0][0]
           and "non-negative" in messages[1][0] and "between 4 and 512" in messages[2][0]
           and messages[3] == [],
           f"V: the model's own messages -- {messages[0][0][:34]!r}, {messages[1][0][:34]!r}, "
           f"{messages[2][0][:34]!r}; Auto passes")

        described = form.describe(dict(form_values, active_width_mm="12.5", bins="64"))
        ok("12.5" in described and "bins=64" in described,
           f"D: the description reports size, bins and pitch ({described[:60]!r}...)")

        status = form.apply(dict(form_values, active_width_mm="12.5", bins="64"))
        stored = dict(parts.read(editor.rows[row]) or {})
        ok(abs(float(stored.get("active_width_mm", 0)) - 12.5) < 1e-12
           and str(stored.get("bins")) == "64" and "Updated detector settings" in status
           and editor.status_var.get() == status,
           f"A1: apply wrote {stored.get('active_width_mm')} mm and bins={stored.get('bins')} "
           f"through the editor's own setter")

        cleared_form = build_detector_settings_form(editor, row)
        cleared = cleared_form.actions[0].run(cleared_form, None)
        after = dict(parts.read(editor.rows[row]) or {})
        ok("Cleared detector settings" in cleared
           and not str(after.get("bins") or "")
           and float(after.get("active_width_mm", 0) or 0) == 0.0,
           f"A2: Clear removed them ({cleared[:40]!r}...)")

        shown = _tk_values(editor, row)
        rebuilt = build_detector_settings_form(editor, row).values
        missing = [key for key, value in rebuilt.items() if value and value not in (shown or [])]
        ok(shown is not None and not missing and not boxes,
           f"T: the REAL Tk dialog shows the builder's values ({len(shown or [])} bound "
           f"variables)" + (f" -- missing {missing}" if missing else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    values, errors, applied, stored, actions = payload
    ok(set(values) == set(form_values) and errors == [] and actions == ["Clear"],
       f"Q1: the Qt form opened with the builder's fields {sorted(values)} and its Clear action")
    ok(applied and abs(float(stored.get("active_width_mm", 0)) - 12.5) < 1e-12
       and str(stored.get("bins")) == "64",
       f"Q2: the Qt Apply wrote {stored.get('active_width_mm')} mm and bins={stored.get('bins')}")

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
