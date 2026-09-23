"""Display-free guard: the Beam Splitter row form (bugs/0869,
docs/design_qt_migration.md phase 3).

The sixth dialog family, and the shape most of the remaining dialogs take: pick a surface row,
show its settings, validate them, write them back. `KrakenOS/UI/row_forms/` declares the fields
and hands over the three things the model owns -- read, validate, apply -- so the Tk dialog and
the Qt dialog agree by construction.

  F  the form's fields are exactly the settings the model normalises
  R  a refusal carries its message: no row selected, and a row that is not a beam splitter
  V  validation returns the MODEL's own errors, not the view's opinion
  A  apply writes the normalised settings, regenerates the Coating, sets the surface, and sets
     the status line
  T  the REAL Tk dialog opens on the same values the builder reports
  Q  the Qt dialog shows the same fields and values, its Validate returns the same errors, and
     its Apply leaves the row in the same state
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
NEW_REFLECTANCE = "0.42"


def beam_splitter_row(editor) -> int:
    """A Beam Splitter row to edit -- this scene has none, so the guard makes one."""
    from KrakenOS.UI.row_forms.beam_splitter import model

    parts = model(editor)
    existing = [index for index, row in enumerate(editor.rows) if row.surface == parts.surface]
    if existing:
        return existing[0]
    index = min(3, len(editor.rows) - 1)
    editor.rows[index].surface = parts.surface
    return index


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.row_forms.beam_splitter import model

    from KrakenOS.UI.validate_open3d_0869_beam_splitter_row_form import beam_splitter_row

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor
    parts = model(editor)

    index = beam_splitter_row(editor)
    window.rows_view.selectRow(index)
    app.processEvents()
    dialog = window.action_manager["beam_splitter"].trigger() or window._open_dialogs[-1]
    app.processEvents()

    values = dict(dialog.values())
    title = dialog.windowTitle()
    selected = window.selected_row_index()

    dialog.widgets["reflectance"].setText("5")
    bad_errors = list(dialog.validate())
    dialog.widgets["reflectance"].setText(NEW_REFLECTANCE)
    good_errors = list(dialog.validate())

    applied = dialog.apply_to_row()
    app.processEvents()
    advanced = dict(editor.rows[index].advanced or {})
    settings = dict(advanced.get(parts.attr, {}))

    window.close()
    return [title, selected, values, bad_errors, good_errors, bool(applied),
            {key: str(value) for key, value in settings.items()},
            str(editor.rows[index].surface), advanced.get("Coating") is not None]


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
        "from KrakenOS.UI.validate_open3d_0869_beam_splitter_row_form import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
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


def _tk_form_values(editor, row_index):
    """Open the REAL Tk dialog and read back what its entries show."""
    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_beam_splitter_settings(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    try:
        shown: list[str] = []

        def walk(widget):
            for child in widget.winfo_children():
                name = ""
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
    from KrakenOS.UI.row_forms import FormRefused, build_beam_splitter_form
    from KrakenOS.UI.row_forms.beam_splitter import model

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

    tk_values = None
    form_values = None
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        parts = model(editor)
        index = beam_splitter_row(editor)
        form = build_beam_splitter_form(editor, index)
        form_values = dict(form.values)

        settings_keys = set(parts.normalize(None))
        ok(set(form_values) == settings_keys and len(form.fields) == len(settings_keys),
           f"F: the form's {len(form.fields)} fields are exactly the settings the model "
           f"normalises ({sorted(settings_keys)[:3]}...)")

        refusals = []
        for bad_index, expected in ((len(editor.rows) + 5, "Select a Beam Splitter row first."),
                                    (0, "Beam splitter settings apply only to Beam Splitter rows.")):
            try:
                build_beam_splitter_form(editor, bad_index)
                refusals.append(("no refusal", bad_index))
            except FormRefused as exc:
                if str(exc) != expected:
                    refusals.append((str(exc), expected))
        ok(not refusals,
           "R: a row out of range and a non-beam-splitter row each refuse with their own message"
           + (f" -- wrong: {refusals}" if refusals else ""))

        bad = dict(form_values, reflectance="5")
        errors = form.validate(bad)
        ok(errors and "reflectance" in errors[0].lower() and not form.validate(form_values),
           f"V: validation is the model's own ({errors[0]!r}), and the row's current values pass")

        good = dict(form_values, reflectance=NEW_REFLECTANCE)
        status = form.apply(good)
        advanced = dict(editor.rows[index].advanced or {})
        settings = dict(advanced.get(parts.attr, {}))
        ok(abs(float(settings.get("reflectance", 0)) - float(NEW_REFLECTANCE)) < 1e-12
           and advanced.get("Coating") is not None
           and str(editor.rows[index].surface) == str(parts.surface)
           and "Updated beam splitter" in status
           and editor.status_var.get() == status,
           f"A: apply wrote reflectance {settings.get('reflectance')}, regenerated the Coating, "
           f"kept the surface {editor.rows[index].surface!r}, and set the status line")

        tk_values = _tk_form_values(editor, index)
        ok(tk_values is not None and all(value in tk_values
                                         for value in build_beam_splitter_form(
                                             editor, index).values.values()),
           f"T: the REAL Tk dialog shows the builder's values -- {len(tk_values or [])} bound "
           f"variables, every form value among them")
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

    (title, selected, values, bad_errors, good_errors, applied, settings, surface,
     has_coating) = payload
    ok(values == form_values and selected is not None and "Beam Splitter - S" in title,
       f"Q1: the Qt form opened on the selected row ({title!r}) with the builder's own values")
    ok(bad_errors and "reflectance" in bad_errors[0].lower() and good_errors == [],
       f"Q2: the Qt Validate returns the model's errors ({bad_errors[0]!r}) and none for a good "
       f"value")
    ok(applied and abs(float(settings.get("reflectance", 0)) - float(NEW_REFLECTANCE)) < 1e-12
       and has_coating,
       f"Q3: the Qt Apply left the row in the same state -- reflectance "
       f"{settings.get('reflectance')}, coating regenerated, surface {surface!r}")

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
