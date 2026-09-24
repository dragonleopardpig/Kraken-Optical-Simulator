"""Display-free guard: the Error Map row form, and the host a dialog must message through
(bugs/0871, docs/design_qt_migration.md phase 3).

A row form with no editable fields: it carries a CANDIDATE error map, shows where it came from
and what it holds, and offers two ACTIONS -- Import (ask for a file, load it, validate it) and
Clear. `FormAction` is the framework's answer: a button whose model callable may rewrite the
form's values, summary and state, and which asks for anything it needs through the UI HOST, so
one implementation serves `filedialog` and `QFileDialog`.

  R  refusals: no row selected, and an Object/Image row
  I  Import asks through the HOST, loads the file and updates the source, summary and state
  C  Clear empties the candidate and says so
  P  apply stores Error_map as the model's own literal, and clears it when there is none
  S  the surface table's selection survives the refresh an apply triggers -- a row form opens on
     the selected row, and a model reset clears it
  H  a Qt dialog messages through ITS OWN host: host_of(dialog) would find no `ui` and fall back
     to a TkUiHost -- a modal TKINTER box inside the Qt app, which never returns
  T  the REAL Tk dialog shows the builder's source and summary
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
ROW = 3


def sample_map(folder: Path) -> Path:
    """A small measured map the loader accepts: a text file whose header names x, y and z."""
    import numpy as np

    path = Path(folder) / "kraken_guard_error_map.csv"
    x, y = np.meshgrid(np.linspace(-5.0, 5.0, 7), np.linspace(-5.0, 5.0, 7))
    z = 1e-4 * (x ** 2 + y ** 2)
    np.savetxt(path, np.column_stack([x.ravel(), y.ravel(), z.ravel()]), delimiter=",",
               header="x,y,z", comments="")
    return path


def qt_runtime_checks() -> list:
    import tempfile

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    from KrakenOS.UI.validate_open3d_0871_error_map_row_form import sample_map

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    window.rows_view.selectRow(ROW)
    app.processEvents()
    dialog = window.action_manager["error_map"].trigger() or window._open_dialogs[-1]
    app.processEvents()

    path = sample_map(Path(tempfile.gettempdir()))
    asked: dict = {}
    refused: dict = {}

    class _RecordingHost(QtUiHost):
        def askopenfilename(self, **options):
            asked.update(options)
            return str(path)

        def showerror(self, title=None, message=None, **options):
            refused.update(title=title, message=message)
            return "ok"

    dialog.host = _RecordingHost(window)
    imported = dialog.run_action(dialog.form.actions[0])
    app.processEvents()
    after_import = dict(dialog.form.values)
    applied = dialog.apply_to_row()
    app.processEvents()
    stored = dict(editor.rows[ROW].advanced or {}).get("Error_map")
    # the apply refreshed every view; the row form opens on the SELECTED row, so the selection
    # has to have survived the table's model reset
    still_selected = window.selected_row_index()

    # a refusal must reach THIS host, not a tkinter box
    dialog2 = window.action_manager["error_map"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    dialog2.host = _RecordingHost(window)

    def _boom(*_args, **_kwargs):
        from KrakenOS.UI.row_forms import FormRefused

        raise FormRefused("the guard's own refusal")

    from KrakenOS.UI.row_forms.base import FormAction

    dialog2.run_action(FormAction("boom", "Boom", _boom))
    app.processEvents()

    window.close()
    return [imported, after_import, bool(applied),
            (len(stored) if stored is not None else 0), dict(asked),
            dict(refused), str(path), still_selected]


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
        "from KrakenOS.UI.validate_open3d_0871_error_map_row_form import qt_runtime_checks\n"
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
    """Open the REAL Tk dialog and read back its source label and contents box."""
    import tkinter as tk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_error_map_editor(row_index)
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
    import tempfile
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import FormRefused, build_error_map_form
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

        refusals = []
        image_row = next((index for index, row in enumerate(editor.rows)
                          if row.surface in {"Object", "Image"}), 0)
        for bad_index, expected in ((len(editor.rows) + 5, "Select a surface row first."),
                                    (image_row, "Measured error maps apply to physical surfaces, "
                                                "not Object/Image rows.")):
            try:
                build_error_map_form(editor, bad_index)
                refusals.append(("no refusal", bad_index))
            except FormRefused as exc:
                if str(exc) != expected:
                    refusals.append((str(exc), expected))
        ok(not refusals,
           "R: no row selected and an Object/Image row each refuse with their own message"
           + (f" -- wrong: {refusals}" if refusals else ""))

        form = build_error_map_form(editor, ROW)
        path = sample_map(Path(tempfile.gettempdir()))
        host = ScriptedUiHost(answers={"askopenfilename": str(path)})
        message = form.actions[0].run(form, host)
        asked = host.asked("askopenfilename")
        ok(form.state.get("error_map") is not None and str(path) == form.values["source"]
           and "Validation passed" in message and asked
           and asked[0][1].get("title") == "Import Error Map",
           f"I: Import asked the host ({asked[0][1].get('title')!r}), loaded the file and set the "
           f"source and summary ({message!r})")

        cleared = form.actions[1].run(form, host)
        ok(form.state.get("error_map") is None and form.values["source"] == "None"
           and "cleared on Apply" in cleared and form.validate(form.values) == [],
           f"C: Clear emptied the candidate and said so ({cleared!r})")

        form.actions[0].run(form, host)
        status = form.apply(form.values)
        stored = dict(editor.rows[ROW].advanced or {}).get("Error_map")
        ok(stored is not None and len(stored) == 4 and "Updated error map" in status
           and editor.status_var.get() == status,
           f"P1: apply stored Error_map as the model's literal ({len(stored or [])} parts: "
           f"X, Y, Z, SPACE) -- {status[:56]!r}...")

        form2 = build_error_map_form(editor, ROW)
        form2.actions[1].run(form2, host)
        cleared_status = form2.apply(form2.values)
        ok("Error_map" not in dict(editor.rows[ROW].advanced or {})
           and "Cleared error map" in cleared_status,
           f"P2: applying an empty form removes Error_map from the row ({cleared_status[:44]!r}...)")

        shown, texts = _tk_shown(editor, ROW)
        ok(shown is not None and texts and any("No Error_map" in text or "samples" in text
                                               for text in texts) and not boxes,
           f"T: the REAL Tk dialog shows the builder's source and contents "
           f"({len(shown or [])} bound variables, {len(texts or [])} text boxes)"
           + (f" -- boxes {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q/H: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    imported, after_import, applied, parts, asked, refused, path, still_selected = payload
    ok("Validation passed" in str(imported) and after_import.get("source") == path
       and asked.get("title") == "Import Error Map",
       f"Q: the Qt Import asked the host ({asked.get('title')!r}) and set the source to the file")
    ok(applied and parts == 4,
       f"Q2: the Qt Apply stored the map as {parts} parts")
    ok(still_selected == ROW,
       f"S: the surface table's selection survived the apply's model reset (row "
       f"{still_selected}) -- otherwise the next row form opens on nothing and refuses")
    ok(refused.get("message") == "the guard's own refusal",
       f"H: a refusal reached the dialog's OWN host ({refused.get('message')!r}) -- had it used "
       f"host_of(dialog) it would have raised a modal tkinter box and hung the app")

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
