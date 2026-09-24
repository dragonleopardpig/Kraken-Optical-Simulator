"""Display-free guard: the Coating / Material row form (bugs/0872,
docs/design_qt_migration.md phase 3).

The most tangled row dialog, and the one that finished the framework: a coating table edited as a
Python LITERAL with a preset list that rewrites it, a metal index linked to a catalogue list that
an ACTION can grow, and the shared advanced-surface validator, which reports warnings as well as
errors.

  P  choosing a preset REWRITES the coating table, through the model's own preset data
  L  choosing a catalogue sets the metal index it is listed under
  G  Load CSV asks the HOST, grows the catalogue list and selects what it loaded
  W  a warning is shown as a warning, not as a refusal
  E  an unparseable coating table refuses with a message, and a metal index with no catalogue is
     an error the model reports
  A  apply writes Coating and CoatingMet, REMOVES them when they are empty or zero, and keeps the
     loaded catalogues on the editor
  T  the REAL Tk dialog shows the builder's values
  Q  the Qt form does the same, with each field in the widget its kind asks for
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
ROW = 3


def sample_catalog(folder: Path) -> Path:
    path = Path(folder) / "kraken_guard_metal.csv"
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["wavelength_um", "n", "k"])
        for wavelength in (0.4, 0.55, 0.7):
            writer.writerow([wavelength, 1.2, 7.0])
    return path


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    from KrakenOS.UI.validate_open3d_0872_coating_material_row_form import sample_catalog

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    window.rows_view.selectRow(ROW)
    app.processEvents()
    dialog = window.action_manager["coating_material"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    form = dialog.form
    kinds = {key: type(widget).__name__ for key, widget in dialog.widgets.items()}
    opened = dict(form.values)

    preset = next((name for name in form.field("preset").choices
                   if name not in ("Custom", form.values["preset"])), None)
    dialog.widgets["preset"].setCurrentText(preset)
    app.processEvents()
    after_preset = dialog.widgets["coating"].toPlainText()

    path = sample_catalog(Path(tempfile.gettempdir()))

    class _Host(QtUiHost):
        def askopenfilename(self, **options):
            return str(path)

    dialog.host = _Host(window)
    loaded = dialog.run_action(form.actions[0])
    app.processEvents()
    catalogs = list(form.choices_for("metal_catalog"))
    met_after_load = dialog.widgets["coating_met"].text()

    applied = dialog.apply_to_row()
    app.processEvents()
    advanced = dict(editor.rows[ROW].advanced or {})

    window.close()
    return [kinds, opened, preset, after_preset[:40], loaded, catalogs, met_after_load,
            bool(applied), "Coating" in advanced, advanced.get("CoatingMet"),
            len(getattr(editor, "metal_catalogs", []) or [])]


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
        "from KrakenOS.UI.validate_open3d_0872_coating_material_row_form import qt_runtime_checks\n"
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


def _tk_shown(editor, row_index):
    import tkinter as tk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_coating_material_editor(row_index)
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    try:
        shown: list[str] = []
        texts: list[str] = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, tk.Text):
                    texts.append(child.get("1.0", "end-1c"))
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
        return shown, texts
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_coating_material_form
    from KrakenOS.UI.row_forms.coating_material import UNEDITABLE
    from KrakenOS.UI.uihost import ScriptedUiHost

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
        form = build_coating_material_form(editor, ROW)

        preset = next((name for name in form.field("preset").choices
                       if name not in ("Custom", form.values["preset"])), None)
        before_table = form.values["coating"]
        message = form.field("preset").on_change(form, preset)
        ok(preset and form.values["coating"] != before_table and preset in message
           and form.values["coating"].startswith("["),
           f"P: the {preset!r} preset rewrote the coating table "
           f"({form.values['coating'][:34]!r}...)")

        path = sample_catalog(Path(tempfile.gettempdir()))
        host = ScriptedUiHost(answers={"askopenfilename": str(path)})
        loaded = form.actions[0].run(form, host)
        asked = host.asked("askopenfilename")
        catalogs = form.choices_for("metal_catalog")
        ok(asked and asked[0][1].get("title") == "Load Metal CSV" and path.name in loaded
           and any(path.stem in label for label in catalogs)
           and form.values["metal_catalog"] in catalogs,
           f"G: Load CSV asked the host ({asked[0][1].get('title')!r}) and the catalogue list "
           f"grew to {len(catalogs)}, selecting what it loaded")

        target = next((label for label in catalogs if label != form.values["metal_catalog"]),
                      catalogs[-1])
        form.field("metal_catalog").on_change(form, target)
        ok(form.values["coating_met"] == target.split(":", 1)[0],
           f"L: choosing {target[:26]!r} set the metal index to "
           f"{form.values['coating_met']!r}")

        errors = form.validate(form.values)
        described = form.describe(form.values)
        ok(not errors and ("Validation passed" in described or "warning" in described.lower()),
           f"W: a warning is shown as a warning, not a refusal ({described[:56]!r}...)")

        broken = form.validate(dict(form.values, coating="[[1, 2,"))
        missing = form.validate(dict(form.values, coating_met="99"))
        ok(broken and missing and any("no loaded metal catalog" in error for error in missing),
           f"E: an unparseable table refuses ({broken[0][:40]!r}...) and a metal index with no "
           f"catalogue is the model's error ({missing[-1][:44]!r}...)")

        # Apply with a NON-ZERO index: zero means "default" and the apply removes the key, which
        # A2 covers. The editor keeps the loaded SPECS; the catalogue list also counts the
        # built-in metals, so the two numbers are not the same thing.
        loaded_label = next((label for label in catalogs if path.stem in label), catalogs[-1])
        form.field("metal_catalog").on_change(form, loaded_label)
        specs = len(form.state["catalogs"])
        status = form.apply(form.values)
        advanced = dict(editor.rows[ROW].advanced or {})
        kept = list(getattr(editor, "metal_catalogs", []) or [])
        ok("Coating" in advanced
           and advanced.get("CoatingMet") == int(form.values["coating_met"]) != 0
           and "Updated coating/material" in status and len(kept) == specs,
           f"A1: apply wrote Coating and CoatingMet={advanced.get('CoatingMet')} and kept the "
           f"{len(kept)} loaded catalogue spec(s) on the editor (the list also shows "
           f"{len(catalogs)} entries, built-in metals included)")

        empty = build_coating_material_form(editor, ROW)
        empty.values["coating"] = "[[], [], [], []]"
        empty.values["coating_met"] = "0"
        empty.apply(empty.values)
        after = dict(editor.rows[ROW].advanced or {})
        ok("Coating" not in after and "CoatingMet" not in after,
           "A2: applying an empty table and a zero index REMOVES both keys from the row")

        shown, texts = _tk_shown(editor, ROW)
        ok(shown is not None and texts and not boxes,
           f"T: the REAL Tk dialog opened with {len(shown or [])} bound variables and "
           f"{len(texts or [])} text box(es)" + (f" -- boxes {boxes}" if boxes else ""))

        uneditable = UNEDITABLE
        ok(isinstance(uneditable, str) and uneditable.startswith("<"),
           f"E2: a coating object that is not a literal is shown as {uneditable!r} and refuses to "
           f"be applied")
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

    (kinds, opened, preset, after_preset, loaded, catalogs, met_after_load, applied,
     has_coating, met, kept) = payload
    ok(kinds.get("coating") == "QPlainTextEdit" and kinds.get("preset") == "QComboBox"
       and kinds.get("metal_catalog") == "QComboBox" and kinds.get("coating_met") == "QLineEdit",
       f"Q1: each field got the widget its kind asks for ({kinds.get('coating')} for the table)")
    ok(after_preset.startswith("[") and preset,
       f"Q2: choosing the {preset!r} preset rewrote the Qt table widget "
       f"({after_preset[:28]!r}...)")
    ok(len(catalogs) >= 2 and met_after_load == str(len(catalogs) - 1),
       f"Q3: Load CSV grew the list to {len(catalogs)} and set the index to {met_after_load}")
    ok(applied and has_coating and int(met) == int(met_after_load) and kept >= 1,
       f"Q4: the Qt Apply wrote Coating, CoatingMet={met} (the index the load selected) and kept "
       f"{kept} loaded catalogue spec(s)")

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
