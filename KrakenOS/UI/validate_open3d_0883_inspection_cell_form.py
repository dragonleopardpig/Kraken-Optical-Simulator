"""Display-free guard: the Inspection Cell record-list form (bugs/0883,
docs/design_qt_migration.md phase 3).

Six faces of one part, each slotted with its own station layout. The six faces ARE the record
list, which is what makes this a record-list form rather than twelve loose fields: select a face
and one "Browse Layout..." verb acts on it, replacing six per-face Browse buttons.

The embedded cell VIEW is a VTK plotter and stays in phase 5, so this guard never opens it -- it
only checks the form offers it.

  B  the builder: six faces, the part dims, the solve inputs, the eight verbs
  S  selecting a face loads that station, and edits fold back into the spec
  A  apply writes editor.inspection_cell_spec
  H  the file verbs ask through the UI HOST and honour a cancel
  T  the REAL Tk dialog opens on the six-face tree
  Q  the Qt dialog lists the same six faces
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

    dialog = window.action_manager["inspection_cell"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    columns = [dialog.records_view.horizontalHeaderItem(i).text()
               for i in range(dialog.records_view.columnCount())]
    rows = dialog.records_view.rowCount()
    first_face = dialog.widgets["face"].text()
    dialog.records_view.selectRow(4)
    app.processEvents()
    fifth_face = dialog.widgets["face"].text()
    labels = [action.label for action in dialog.form.actions]
    dialog.close()
    app.processEvents()

    window.close()
    return [columns, rows, first_face, fifth_face, labels]


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
        "from KrakenOS.UI.validate_open3d_0883_inspection_cell_form import qt_runtime_checks\n"
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


class _ScriptedFiles:
    """A UI host stand-in that answers the file choosers with a scripted path."""

    def __init__(self, answer):
        self.answer = answer
        self.asked: list = []

    def askopenfilename(self, **kwargs):
        self.asked.append(("open", kwargs.get("title", "")))
        return self.answer

    def asksaveasfilename(self, **kwargs):
        self.asked.append(("save", kwargs.get("title", "")))
        return self.answer


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import build_inspection_cell_form
    from KrakenOS.UI.row_forms import inspection_cell as cell_form

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

        form = build_inspection_cell_form(editor)
        faces = form.state["parts"].faces
        rows = form.records.rows(form)
        labels = [action.label for action in form.actions]
        ok(tuple(form.records.columns) == cell_form.COLUMNS and len(rows) == len(faces) == 6
           and [row[0] for row in rows] == [face.capitalize() for face in faces]
           and labels[0] == "Browse Layout..." and "Open Cell View" in labels
           and "Solve & Build Stations" in labels and len(labels) == 8
           and {"width_mm", "defect_mm", "out_dir"} <= {f.key for f in form.fields},
           f"B: the six faces {[row[0] for row in rows]} under {form.records.columns}, "
           f"with {len(labels)} verbs and the part/solve fields")

        first = form.values["face"]
        form.records.select(form, 3)
        picked = form.values["face"]
        form.values["enabled"] = "true"
        form.values["layout"] = str(SCENE)
        described = form.describe(dict(form.values))
        after = form.records.rows(form)
        ok(first == faces[0].capitalize() and picked == faces[3].capitalize()
           and after[3][1] == "yes" and after[3][2] == str(SCENE)
           and f"1 station(s) enabled: {faces[3]}" in described,
           f"S: the list opened on {first!r}, picking row 3 loaded {picked!r}, and the edit "
           f"folded back into that row ({after[3][1]!r}, {Path(after[3][2]).name})")

        status = form.apply(dict(form.values))
        stored = editor.inspection_cell_spec["stations"]
        ok(stored[faces[3]]["enabled"] and str(stored[faces[3]]["layout"]) == str(SCENE)
           and not any(stored[face]["enabled"] for face in faces if face != faces[3])
           and "1 of 6 stations enabled" in status,
           f"A: apply wrote editor.inspection_cell_spec -- only {faces[3]} is slotted "
           f"({status})")

        host = _ScriptedFiles(str(SCENE))
        browse = next(action for action in form.actions if action.key == "browse_layout")
        form.records.select(form, 5)
        message = browse.run(form, host)
        cancelled = browse.run(form, _ScriptedFiles(""))
        ok(host.asked and faces[5] in host.asked[0][1] and faces[5] in message
           and form.state["spec"]["stations"][faces[5]]["enabled"]
           and cancelled == "Browse cancelled.",
           f"H: Browse Layout asked the HOST for the {faces[5]} face and slotted it; "
           f"a cancel leaves the spec alone")

        before = {str(child) for child in editor.root.winfo_children()}
        editor.open_inspection_cell_dialog()
        windows = [child for child in editor.root.winfo_children()
                   if str(child) not in before and child.winfo_class() == "Toplevel"]
        tree = None
        if windows:
            found = []

            def walk(widget):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Treeview):
                        found.append((tuple(child.cget("columns")),
                                      len(child.get_children())))
                    walk(child)

            walk(windows[-1])
            tree = found[0] if found else None
            windows[-1].destroy()
        ok(tree is not None and tree[0] == cell_form.COLUMNS and tree[1] == 6 and not boxes,
           f"T: the REAL Tk dialog drew its {tree[1] if tree else 0}-face tree under "
           f"{tree[0] if tree else None}")
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

    columns, rows, first_face, fifth_face, labels = payload
    ok(tuple(columns) == cell_form.COLUMNS and rows == 6 and first_face == "Front"
       and fifth_face == "Top" and len(labels) == 8,
       f"Q: the Qt dialog listed {rows} faces, opened on {first_face!r} and loaded "
       f"{fifth_face!r} when row 4 was picked")

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
