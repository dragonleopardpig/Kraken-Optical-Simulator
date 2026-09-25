"""Display-free guard: the apply-tolerance-preset and resize-beam-splitter row forms
(bugs/0892, docs/design_qt_migration.md phase 3).

The last two tail dialogs. Both are small, and both had a decision worth keeping:

* the apply-preset dialog SKIPS ITSELF when the layout has exactly one preset -- there is
  nothing to choose -- and that shortcut now goes through the very same `apply_preset()` the
  dialog's Apply calls, so the two cannot drift;
* the resize dialog's FIELDS depend on the row: a cube takes one number, a plate takes four. The
  model reads `beam_splitter_resize_info` and builds the form to match, rather than a view
  branching on a kind it would have to understand.

  A  the preset chooser: refusal with none saved, its choices, and what Apply does
  S  the one-preset shortcut applies WITHOUT a dialog, through the shared path
  R  cube -> 1 field, plate -> 4, with the model's own wording on a bad entry
  T  the REAL Tk chooser opens on the saved names
  Q  the Qt chooser does the same
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


def _seed_presets(editor, names) -> list:
    from KrakenOS.UI.row_forms import build_save_tolerance_preset_form

    for name in names:
        form = build_save_tolerance_preset_form(editor)
        form.apply(dict(form.values, name=name))
    from KrakenOS.UI.row_forms.presets import saved_preset_names

    return saved_preset_names(editor)


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    seeded = _seed_presets(window.editor, ("Alpha", "Beta"))
    dialog = window.action_manager["apply_tolerance_preset"].trigger() \
        or window._open_dialogs[-1]
    app.processEvents()
    choices = [dialog.widgets["preset"].itemText(index)
               for index in range(dialog.widgets["preset"].count())]
    dialog.widgets["preset"].setCurrentText("Alpha")
    errors = list(dialog.validate())
    applied = dialog.apply_to_row()
    app.processEvents()
    active = str(getattr(window.editor, "active_tolerance_solve_preset_name", "") or "")
    dialog.close()
    app.processEvents()

    window.close()
    return [seeded, choices, errors, bool(applied), active]


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
        "from KrakenOS.UI.validate_open3d_0892_tail_forms import qt_runtime_checks\n"
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


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox
    from tkinter import ttk
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import (FormRefused, build_apply_tolerance_preset_form,
                                       build_resize_beam_splitter_form)
    from KrakenOS.UI.row_forms.resize_beam_splitter import CUBE_FIELDS, PLATE_FIELDS

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

        empty_refusal = ""
        try:
            build_apply_tolerance_preset_form(editor)
        except FormRefused as exc:
            empty_refusal = str(exc)
        names = _seed_presets(editor, ("Alpha", "Beta"))
        form = build_apply_tolerance_preset_form(editor)
        messages = [form.validate({"preset": "Nope"}), form.validate(dict(form.values))]
        status = form.apply(dict(form.values, preset="Alpha"))
        ok(empty_refusal.startswith("No saved tolerance solve presets")
           and names == ["Alpha", "Beta"]
           and list(form.choices_for("preset")) == names
           and messages[0] == ["Choose a preset to apply."] and messages[1] == []
           and "Applied tolerance solve preset 'Alpha'" in status,
           f"A: with none saved it refuses; with {names} it offers both and Apply reports "
           f"{status[:44]!r}")

        # the one-preset shortcut: the REAL panel applies without opening anything
        single = KrakenLayoutEditor(headless=True)
        try:
            single.layout_files[SCENE.stem] = SCENE
            single.load_layout_by_name(SCENE.stem)
            _seed_presets(single, ("Only",))
            before = {str(child) for child in single.root.winfo_children()}
            single._main_tolerance_report_dialogs().open_apply_tolerance_solve_preset_dialog()
            opened = [child for child in single.root.winfo_children()
                      if str(child) not in before and child.winfo_class() == "Toplevel"]
            shortcut_status = single.status_var.get()
        finally:
            single.destroy()
        ok(not opened and "Applied tolerance solve preset 'Only'" in shortcut_status,
           f"S: one saved preset applies with NO dialog, through the shared path "
           f"({shortcut_status[:48]!r})")

        real_refusal = ""
        try:
            build_resize_beam_splitter_form(editor, 1)
        except FormRefused as exc:
            real_refusal = str(exc)

        def stand_in(kind, params):
            return SimpleNamespace(
                rows=editor.rows,
                beam_splitter_resize_info=lambda _index: (kind, params),
                resize_beam_splitter=lambda _index, **_dimensions: None,
                status_var=SimpleNamespace(get=lambda: "stand-in refusal"),
                _selected_surface_row_index=lambda: 1,
            )

        cube = build_resize_beam_splitter_form(stand_in("cube", {"side_mm": 25.0}), 1)
        plate = build_resize_beam_splitter_form(
            stand_in("plate", {"width_mm": 30.0, "height_mm": 20.0, "thickness_mm": 2.0,
                               "tilt_deg": 45.0}), 1)
        cube_message = cube.validate(dict(cube.values, side_mm="x"))
        plate_keys = [field.key for field in plate.fields]
        ok(real_refusal.startswith("Resize Beam Splitter: this row is not")
           and [field.key for field in cube.fields] == [key for key, _ in CUBE_FIELDS]
           and plate_keys == [key for key, _ in PLATE_FIELDS]
           and cube_message == ["side: enter a number."]
           and "Cube" in cube.title and "Plate" in plate.title,
           f"R: a cube form has {len(cube.fields)} field and a plate {len(plate.fields)}; a "
           f"bad entry says {cube_message[0]!r}, and a non-parametric row refuses")

        before = {str(child) for child in editor.root.winfo_children()}
        editor._main_tolerance_report_dialogs().open_apply_tolerance_solve_preset_dialog()
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before and child.winfo_class() == "Toplevel"]
        combos = []
        if windows:
            window = windows[-1]

            def walk(widget):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Combobox):
                        combos.append((str(child.get()), list(child.cget("values"))))
                    walk(child)

            walk(window)
            try:
                window.grab_release()
            except Exception:
                pass
            window.destroy()
        ok(windows and combos and combos[0][1] == names and not boxes,
           f"T: the REAL Tk chooser opened on {combos[0][0]!r} with {combos[0][1]}"
           if combos else "T: the REAL Tk chooser did not open")
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

    seeded, choices, errors, applied, active = payload
    ok(choices == seeded == ["Alpha", "Beta"] and errors == [] and applied
       and active == "Alpha",
       f"Q: the Qt chooser offered {choices} and applying left {active!r} active")

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
