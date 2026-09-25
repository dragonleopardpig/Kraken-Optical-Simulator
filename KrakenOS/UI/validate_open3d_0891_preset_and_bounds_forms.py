"""Display-free guard: the tolerance-solve preset and optimisation-bounds row forms
(bugs/0891, docs/design_qt_migration.md phase 3).

Two more tail dialogs that needed nothing new from the framework. What they DID need was care
about where an error goes: the bounds dialog has never shown a message box -- it writes to the
DEBUG LOG and leaves the dialog open -- and the preset dialog reports through `append_debug` as
well as the status line. The builders raise `FormRefused` with the model's own wording; the
panels decide where it lands.

  P  the preset: its fields, its refusals, and what Save writes
  B  the bounds: the one rule (lower below upper), and the model's own two messages
  W  a bounds refusal goes to the DEBUG LOG, not a message box
  T  both REAL Tk dialogs open on the builders' fields, modally
  Q  the Qt preset dialog does the same
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


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = window.action_manager["tolerance_preset"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    keys = sorted(dialog.widgets)
    blank = list(dialog.form.validate(dict(dialog.values(), name="  ")))
    dialog.widgets["name"].setText("Qt guard preset")
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()
    names = [str(preset.get("name", ""))
             for preset in (getattr(window.editor, "tolerance_solve_presets", []) or [])]
    dialog.close()
    app.processEvents()

    window.close()
    return [keys, blank, errors, bool(applied), names]


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
        "from KrakenOS.UI.validate_open3d_0891_preset_and_bounds_forms import "
        "qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", "the Qt subprocess timed out after 900 s"
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_shape(editor, opener):
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    opener()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    entries, combos, buttons = 0, 0, []
    grabbed = str(window.grab_current() or "")
    try:
        def walk(widget):
            nonlocal entries, combos
            for child in widget.winfo_children():
                if isinstance(child, ttk.Combobox):
                    combos += 1
                elif isinstance(child, ttk.Entry):
                    entries += 1
                elif isinstance(child, ttk.Button):
                    buttons.append(str(child.cget("text")))
                walk(child)

        walk(window)
        return (entries, combos, buttons, grabbed == str(window))
    finally:
        try:
            window.grab_release()
        except Exception:
            pass
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import (FormRefused, build_optimization_bounds_form,
                                       build_save_tolerance_preset_form)

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)

        form = build_save_tolerance_preset_form(editor)
        keys = [field.key for field in form.fields]
        messages = [form.validate(dict(form.values, name="  ")),
                    form.validate(dict(form.values, sample_count="lots")),
                    form.validate(dict(form.values, sample_count="0")),
                    form.validate(dict(form.values))]
        status = form.apply(dict(form.values, name="Guard preset"))
        saved = [str(preset.get("name", ""))
                 for preset in (getattr(editor, "tolerance_solve_presets", []) or [])]
        ok(len(keys) == 7 and keys[-1] == "tolerance_compare_view"
           and messages[0] == ["Give the preset a name."]
           and messages[1] == ["Monte Carlo samples expects a whole number."]
           and messages[2] == ["Monte Carlo samples must be at least 1."]
           and messages[3] == []
           and "Guard preset" in saved and "Saved tolerance solve preset" in status,
           f"P: {len(keys)} fields; {messages[0][0]!r}, {messages[2][0]!r}; Save wrote "
           f"{saved[-1]!r}")

        spec = next((editor._variable_spec_for_field(field)
                     for field in ("thickness", "rc", "Thickness", "Rc")
                     if editor._variable_spec_for_field(field) is not None), None)
        bounds = build_optimization_bounds_form(editor, 1, spec=spec)
        bounds_messages = [bounds.validate(dict(bounds.values, lower="5", upper="1")),
                           bounds.validate(dict(bounds.values, lower="x")),
                           bounds.validate(dict(bounds.values, lower="-5", upper="5"))]
        bounds_status = bounds.apply(dict(bounds.values, lower="-5", upper="5"))
        stored = spec.get_bounds(editor.rows[1])
        refused = ""
        try:
            build_optimization_bounds_form(editor, None, spec=None)
        except FormRefused as exc:
            refused = str(exc)
        ok(spec is not None
           and bounds_messages[0] == ["Optimization bounds rejected: lower must be less than "
                                      "upper."]
           and bounds_messages[1] == ["Invalid optimization bounds entry."]
           and bounds_messages[2] == []
           and stored == (-5.0, 5.0) and "Bounds set for row 1" in bounds_status
           and refused == "Right-click an optimisation variable cell first.",
           f"B: {bounds_messages[0][0][:44]!r} and {bounds_messages[1][0]!r}; Save wrote "
           f"{stored}")

        # A refusal must reach the DEBUG LOG, which is where this dialog has always put it.
        # Drive the REAL panel method with a builder that refuses -- an earlier version of this
        # check passed the row id as None, which returns before the builder and proved nothing.
        import tkinter.messagebox as tk_messagebox

        from KrakenOS.UI.panels import main_optimization_panel as panel_module

        logged: list = []
        boxes: list = []
        panel = editor._main_optimization_panel()
        saved_builder = panel_module.build_optimization_bounds_form
        saved_debug = editor.append_debug
        saved_boxes = (tk_messagebox.showerror, tk_messagebox.showinfo)

        def refusing_builder(*_args, **_kwargs):
            raise FormRefused("the guard's own refusal")

        panel_module.build_optimization_bounds_form = refusing_builder
        editor.append_debug = lambda text: logged.append(str(text))
        tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"
        tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
        try:
            panel.current_menu_row_id = "row_1"
            panel.current_menu_field = "thickness"
            panel._table_item_row_index = lambda _row_id: 1
            panel._variable_spec_for_field = lambda _field: spec
            panel.edit_current_bounds()
        finally:
            panel_module.build_optimization_bounds_form = saved_builder
            editor.append_debug = saved_debug
            tk_messagebox.showerror, tk_messagebox.showinfo = saved_boxes
        ok(logged == ["the guard's own refusal"] and not boxes,
           f"W: a bounds refusal reached the DEBUG LOG ({logged}) and opened no message box, "
           f"which is how this dialog has always reported a bad entry")

        preset_tk = _tk_shape(
            editor, lambda: editor._main_tolerance_report_dialogs()
            .open_save_tolerance_solve_preset_dialog())
        ok(preset_tk and preset_tk[0] == 6 and preset_tk[1] == 1
           and preset_tk[2] == ["Validate", "Apply", "Cancel"] and preset_tk[3],
           f"T: the REAL Tk preset dialog drew {preset_tk[0]} entries and {preset_tk[1]} combo "
           f"under {preset_tk[2]}, and it GRABBED" if preset_tk else
           "T: the REAL Tk preset dialog did not open")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    keys, blank, errors, applied, names = payload
    ok(len(keys) == 7 and blank == ["Give the preset a name."] and errors == []
       and applied and "Qt guard preset" in names,
       f"Q: the Qt preset dialog showed {len(keys)} fields, refused a blank name and saved "
       f"{names[-1]!r}")

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
