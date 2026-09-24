"""Display-free guard: the Scene Target row form (bugs/0875,
docs/design_qt_migration.md phase 3).

The role choice turns the four detector fields on and off WHILE the dialog is open, which
`FormField.enabled` -- fixed when the form is built -- cannot express. `RowForm.locked` holds the
live answer and both views ask `form.is_enabled(key)`.

  R  refusals: nothing selected; an Object row cannot take the Detector role
  L  the lock follows the role, in the form and in both views
  V  the model's own messages for a non-number, a negative size and bins out of range
  A  apply writes the role, the name and the active TargSurf; Clear Target removes them
  T  the REAL Tk dialog shows the values AND disables the detector entries under Auto
  Q  the Qt form does the same, and its combo unlocks them live
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
DETECTOR_KEYS = ("active_width_mm", "active_height_mm", "bins", "pixel_pitch_um")


def pick_row(editor) -> int:
    """A row the editor is not already treating as a detector -- so the lock starts ON."""
    for index, row in enumerate(editor.rows):
        if row.surface in ("Object", "Image"):
            continue
        if editor._scene_target_editor_kind_for_row(index) != "detector":
            return index
    return max(len(editor.rows) - 2, 0)


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    row = pick_row(editor)
    window.rows_view.selectRow(row)
    app.processEvents()
    dialog = window.action_manager["scene_target"].trigger() or window._open_dialogs[-1]
    app.processEvents()

    locked_at_open = [key for key in DETECTOR_KEYS if not dialog.widgets[key].isEnabled()]
    dialog.widgets["role"].setCurrentText("Detector")
    app.processEvents()
    unlocked = [key for key in DETECTOR_KEYS if dialog.widgets[key].isEnabled()]

    dialog.widgets["active_width_mm"].setText("9.75")
    dialog.widgets["name"].setText("QtTarget")
    dialog.widgets["active"].setChecked(True)
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()
    state = {"kind": editor._scene_target_editor_kind_for_row(row),
             "name": str(editor.rows[row].name),
             "active": editor._current_nonseq_target_surface_index() == row,
             "width": float(editor._detector_settings(editor.rows[row])
                            .get("active_width_mm", 0.0))}

    window.close()
    return [sorted(locked_at_open), sorted(unlocked), errors, bool(applied), state,
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
        "from KrakenOS.UI.validate_open3d_0875_scene_target_row_form import qt_runtime_checks\n"
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


def _tk_dialog_state(editor, row_index):
    """Open the REAL Tk dialog and read back what it shows and what it lets you edit."""
    import tkinter as tk
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_scene_target_editor(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    shown: list[str] = []
    disabled: list[str] = []
    try:
        def walk(widget):
            for child in widget.winfo_children():
                name = ""
                try:
                    name = str(child.cget("textvariable"))
                except Exception:
                    try:
                        name = str(child.cget("variable"))
                    except Exception:
                        name = ""
                if name:
                    try:
                        shown.append(str(window.getvar(name)))
                    except Exception:
                        pass
                if isinstance(child, ttk.Entry) and child.instate(["disabled"]):
                    try:
                        disabled.append(str(window.getvar(str(child.cget("textvariable")))))
                    except Exception:
                        disabled.append("?")
                walk(child)

        walk(window)
        return shown, disabled
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_scene_target_form
    from KrakenOS.UI.row_forms.scene_target import model

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

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        parts = model(editor)
        row = pick_row(editor)

        refused = ""
        try:
            build_scene_target_form(editor, len(editor.rows) + 5)
        except FormRefused as exc:
            refused = str(exc)
        object_row = next((index for index, item in enumerate(editor.rows)
                           if item.surface == "Object"), None)
        object_form = build_scene_target_form(editor, object_row)
        object_errors = object_form.validate(
            dict(object_form.values, role=parts.kind_labels["detector"]))
        ok(refused == "Select a surface row or scene target first."
           and object_errors == ["Object rows cannot be detector planes."],
           f"R: an out-of-range row refuses ({refused!r}) and an Object row refuses the "
           f"Detector role")

        form = build_scene_target_form(editor, row)
        opened_locked = [key for key in DETECTOR_KEYS if not form.is_enabled(key)]
        form.field("role").on_change(form, parts.kind_labels["detector"])
        after_detector = [key for key in DETECTOR_KEYS if form.is_enabled(key)]
        form.field("role").on_change(form, parts.kind_labels["auto"])
        back_locked = [key for key in DETECTOR_KEYS if not form.is_enabled(key)]
        ok(sorted(opened_locked) == sorted(DETECTOR_KEYS)
           and sorted(after_detector) == sorted(DETECTOR_KEYS)
           and sorted(back_locked) == sorted(DETECTOR_KEYS)
           and form.field("name").enabled and form.is_enabled("name"),
           f"L: S{row} opens with the 4 detector fields locked, Detector unlocks all 4, and "
           f"Auto locks them again -- while FormField.enabled stays True")

        detector_values = dict(form.values, role=parts.kind_labels["detector"])
        messages = [form.validate(dict(detector_values, active_width_mm="wide")),
                    form.validate(dict(detector_values, pixel_pitch_um="-2")),
                    form.validate(dict(detector_values, bins="900")),
                    form.validate(dict(detector_values, bins="Auto"))]
        ok(all(messages[:3]) and "must be numbers" in messages[0][0]
           and "non-negative" in messages[1][0] and "between 4 and 512" in messages[2][0]
           and messages[3] == [],
           f"V: {messages[0][0][:38]!r}, {messages[1][0][:38]!r}, {messages[2][0][:38]!r}; "
           f"Auto passes")

        described = form.describe(dict(detector_values, active="true"))
        status = form.apply(dict(detector_values, active_width_mm="9.5", active="true",
                                 name="GuardTarget"))
        ok("role=Detector" in described and "active=yes" in described
           and editor._scene_target_editor_kind_for_row(row) == "detector"
           and str(editor.rows[row].name) == "GuardTarget"
           and editor._current_nonseq_target_surface_index() == row
           and abs(float(editor._detector_settings(editor.rows[row])
                         .get("active_width_mm", 0.0)) - 9.5) < 1e-12
           and editor.status_var.get() == status,
           f"A1: apply set the role, the name and the active TargSurf ({described!r})")

        cleared_form = build_scene_target_form(editor, row)
        cleared = cleared_form.actions[0].run(cleared_form, None)
        ok(cleared_form.actions[0].label == "Clear Target"
           and editor._scene_target_editor_kind_for_row(row) != "detector"
           and editor._current_nonseq_target_surface_index() != row
           and "Cleared scene-target metadata" in cleared,
           f"A2: Clear Target removed the role and the active TargSurf ({cleared[:44]!r}...)")

        rebuilt = build_scene_target_form(editor, row)
        shown, disabled = _tk_dialog_state(editor, row)
        wanted = [value for key, value in rebuilt.values.items()
                  if key not in ("surface", "active") and value]
        missing = [value for value in wanted if value not in (shown or [])]
        ok(shown is not None and not missing and sorted(disabled or []) == sorted(
               rebuilt.values[key] for key in DETECTOR_KEYS)
           and not boxes,
           f"T: the REAL Tk dialog shows the builder's values and DISABLES the 4 detector "
           f"entries under Auto ({len(shown or [])} variables, {len(disabled or [])} disabled)"
           + (f" -- missing {missing}" if missing else ""))
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

    locked_at_open, unlocked, errors, applied, qt_state, actions = payload
    ok(locked_at_open == sorted(DETECTOR_KEYS) and unlocked == sorted(DETECTOR_KEYS)
       and actions == ["Clear Target"],
       f"Q1: the Qt widgets open DISABLED and the Detector choice enables all four live")
    ok(applied and errors == [] and qt_state["kind"] == "detector"
       and qt_state["name"] == "QtTarget" and qt_state["active"] is True
       and abs(float(qt_state["width"]) - 9.75) < 1e-12,
       f"Q2: the Qt Apply wrote role={qt_state['kind']}, name={qt_state['name']!r}, "
       f"active={qt_state['active']}, width={qt_state['width']}")

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
