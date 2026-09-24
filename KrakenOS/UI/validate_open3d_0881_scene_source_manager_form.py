"""Display-free guard: the Scene Source Manager record-list form (bugs/0881,
docs/design_qt_migration.md phase 3).

The seventh dialog family and the first that edits a COLLECTION rather than one row, so the form
carries a `RecordList`: the master list is model data (`columns` + `rows(form)`), and the view
reports a pick by calling `select(form, index)`, which rewrites the form.

  B  the builder: the record list, the fields, the actions, the selected record
  V  the model's own refusals
  C  the collection verbs -- Add, Add From Source Panel, Duplicate, Delete
  M  the two choices that rewrite other fields: the model and the direction preset
  A  apply writes the whole list through _set_scene_source_specs
  T  the REAL Tk dialog opens with the record tree beside the fields
  Q  the Qt dialog shows the same rows, and picking one loads that record
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

    dialog = window.action_manager["scene_sources"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    columns = [dialog.records_view.horizontalHeaderItem(i).text()
               for i in range(dialog.records_view.columnCount())]
    first_rows = dialog.records_view.rowCount()
    first_id = dialog.widgets["source_id"].text()

    add = next(action for action in dialog.form.actions if action.key == "add")
    dialog.run_action(add)
    app.processEvents()
    after_rows = dialog.records_view.rowCount()
    added_id = dialog.widgets["source_id"].text()

    dialog.records_view.selectRow(0)
    app.processEvents()
    back_id = dialog.widgets["source_id"].text()

    applied = dialog.apply_to_row()
    app.processEvents()
    stored = [str(spec.get("source_id", ""))
              for spec in (window.editor.layout_scene_source_specs or [])]

    window.close()
    return [columns, first_rows, first_id, after_rows, added_id, back_id, bool(applied), stored,
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
        "from KrakenOS.UI.validate_open3d_0881_scene_source_manager_form import "
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
        return "error", ("the Qt subprocess timed out after 900 s -- a modal dialog with no one "
                         "to close it is the usual cause")
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def _tk_dialog_shape(editor):
    """Open the REAL Tk manager and report what it drew."""
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_scene_source_manager()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    shape = {"trees": [], "combos": 0, "entries": 0, "checks": 0, "buttons": []}
    try:
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    shape["trees"].append(
                        (tuple(child.cget("columns")), len(child.get_children()),
                         tuple(child.selection())))
                elif isinstance(child, ttk.Combobox):
                    shape["combos"] += 1
                elif isinstance(child, ttk.Entry):
                    shape["entries"] += 1
                elif isinstance(child, ttk.Checkbutton):
                    shape["checks"] += 1
                elif isinstance(child, ttk.Button):
                    shape["buttons"].append(str(child.cget("text")))
                walk(child)

        walk(window)
        return shape
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import build_scene_source_manager_form
    from KrakenOS.UI.row_forms.scene_sources import COLUMNS, model

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

        form = build_scene_source_manager_form(editor)
        rows = form.records.rows(form)
        labels = [action.label for action in form.actions]
        ok(form.records is not None and tuple(form.records.columns) == COLUMNS
           and len(rows) == len(form.state["specs"]) and len(rows[0]) == len(COLUMNS)
           and form.selected_index == 0 and len(form.fields) == 33
           and labels == ["Save Source", "Add", "Add From Source Panel", "Duplicate", "Delete",
                          "Aim Direction At Row", "Place Origin At Standoff",
                          "Use Source Panel Only"],
           f"B: {len(form.fields)} fields, a {len(COLUMNS)}-column record list of "
           f"{len(rows)} source(s), 8 collection verbs, editing #{form.selected_index}")

        messages = [form.validate(dict(form.values, source_id="   ")),
                    form.validate(dict(form.values, source_l="0", source_m="0", source_n="0")),
                    form.validate(dict(form.values, model="Not a model")),
                    form.validate(dict(form.values))]
        ok(messages[0] == ["Source ID cannot be empty."]
           and messages[1] == ["Direction vector cannot be zero."]
           and messages[2] == ["Choose a valid source model."] and messages[3] == [],
           f"V: {messages[0][0]!r}, {messages[1][0]!r}, {messages[2][0]!r}")

        by_key = {action.key: action for action in form.actions}
        start = len(form.state["specs"])
        by_key["add"].run(form, None)
        added_id = form.values["source_id"]
        by_key["duplicate"].run(form, None)
        duplicated_id = form.values["source_id"]
        by_key["add_panel"].run(form, None)
        panel_count = len(form.state["specs"])
        by_key["delete"].run(form, None)
        ok(panel_count == start + 3 and len(form.state["specs"]) == start + 2
           and duplicated_id.endswith("_copy") and added_id != duplicated_id,
           f"C: Add/Duplicate/Add From Source Panel grew {start} -> {panel_count} "
           f"(duplicate is {duplicated_id!r}), Delete took one back")

        form = build_scene_source_manager_form(editor)
        preset_field = form.field("direction_preset")
        model_field = form.field("model")
        before_dir = (form.values["source_l"], form.values["source_m"], form.values["source_n"])
        preset_label = next(label for label in parts.preset_values
                            if editor._source_direction_preset_vector(label) is not None
                            and label != form.values["direction_preset"])
        preset_message = preset_field.on_change(form, preset_label)
        after_dir = (form.values["source_l"], form.values["source_m"], form.values["source_n"])
        model_field.on_change(form, parts.model_default)
        ok(after_dir != before_dir and "Direction preset applied" in preset_message
           and form.values["physical"] == "false"
           and form.values["role"] == "pupil_field_reference",
           f"M: the preset rewrote LMN {before_dir} -> {after_dir}, and Pupil / field made the "
           f"record nonphysical")

        form = build_scene_source_manager_form(editor)
        by_key = {action.key: action for action in form.actions}
        by_key["add"].run(form, None)
        form.values["name"] = "Guard Source"
        status = form.apply(dict(form.values))
        stored = [str(spec.get("source_id", ""))
                  for spec in (editor.layout_scene_source_specs or [])]
        ok(len(stored) == len(form.state["specs"]) and "Applied" in status
           and any(str(spec.get("name", "")) == "Guard Source"
                   for spec in editor.layout_scene_source_specs),
           f"A: apply wrote {len(stored)} source(s) through _set_scene_source_specs ({stored})")

        shape = _tk_dialog_shape(editor)
        ok(shape is not None and len(shape["trees"]) == 1
           and shape["trees"][0][0] == COLUMNS
           and shape["trees"][0][1] == len(stored)
           and shape["trees"][0][2] == ("record_0",)
           and shape["combos"] == 8 and shape["checks"] == 2
           and "Add From Source Panel" in shape["buttons"] and not boxes,
           f"T: the REAL Tk manager drew a {len(shape['trees'][0][0])}-column tree of "
           f"{shape['trees'][0][1]} rows beside {shape['combos']} combos / "
           f"{shape['entries']} entries / {shape['checks']} checkbuttons"
           if shape else "T: the REAL Tk manager did not open")
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

    (columns, first_rows, first_id, after_rows, added_id, back_id, applied, stored,
     labels) = payload
    ok(tuple(columns) == COLUMNS and first_rows >= 1 and after_rows == first_rows + 1
       and added_id != first_id and len(labels) == 8,
       f"Q1: the Qt manager listed {first_rows} source(s) under {len(columns)} columns and Add "
       f"grew it to {after_rows}")
    ok(back_id == first_id and applied and len(stored) == after_rows,
       f"Q2: picking row 0 loaded {back_id!r} back, and Apply wrote {len(stored)} source(s)")

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
