"""Display-free guard: the Qt reports show what the Tk dialogs show (bugs/0862,
docs/design_qt_migration.md phase 3).

The user, having opened all five: *"they pop up dialog with table and values in it (although I
can't verify they are correct)."* Fair -- the earlier guards compared the Qt tables against the
FORMATTERS the Tk dialogs use, which is an argument, not a demonstration. This one opens the real
Tk dialog and the real Qt dialog on the same scene and compares every cell.

  T  each Tk dialog opens and yields its headings and cells
  Q  each Qt dialog opens and yields its headings and cells
  P* per report: same headings, same shape, and the same SHA-256 over every cell -- so the two
     applications display the identical table, cell for cell
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")

#: report name -> the editor method that opens its Tk dialog
REPORTS = {
    "paraxial_matrix": "open_paraxial_matrix_report",
    "branch_gaussian_q": "open_branch_gaussian_q_report",
    "detector_aperture": "open_detector_aperture_report",
    "branch_throughput": "open_branch_throughput_report",
    "source_illumination": "open_source_illumination_report",
}


def digest(cells) -> str:
    return hashlib.sha256(
        json.dumps(cells, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def _tk_table(editor, opener: str):
    """Open one Tk dialog and read its main table back. Returns (headings, cells)."""
    import tkinter.ttk as ttk

    before = {str(child) for child in editor.root.winfo_children()}
    getattr(editor, opener)()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None, None
    window = windows[-1]
    try:
        trees: list = []

        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    trees.append(child)
                walk(child)

        walk(window)
        if not trees:
            return None, None
        tree = trees[0]
        headings = [str(tree.heading(column)["text"]) for column in tree["columns"]]
        cells = [[str(value) for value in tree.item(item, "values")]
                 for item in tree.get_children("")]
        return headings, cells
    finally:
        window.destroy()


def qt_runtime_checks() -> list[list]:
    """Open every Qt report and return [name, headings, cells-digest, shape]."""
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    out: list[list] = []
    for name in REPORTS:
        dialog = window.action_manager[name].trigger() or window._open_dialogs[-1]
        app.processEvents()
        model = dialog.model
        headings = [str(model.headerData(c, Qt.Orientation.Horizontal))
                    for c in range(model.columnCount())]
        cells = [[str(model.data(model.index(r, c), Qt.ItemDataRole.DisplayRole))
                  for c in range(model.columnCount())]
                 for r in range(model.rowCount())]
        out.append([name, headings, digest(cells), [len(cells), len(headings)],
                    cells[0] if cells else []])
        dialog.close()
    window.close()
    return out


def _run_qt_subprocess() -> tuple[str, list]:
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
        "from KrakenOS.UI.validate_open3d_0862_qt_tk_report_parity import qt_runtime_checks\n"
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


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # A dialog with nothing to show raises a MODAL info box, which would block this process.
    saved = (tk_messagebox.showinfo, tk_messagebox.showerror, tk_messagebox.showwarning)
    boxes: list[tuple] = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(("info", a)) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(("error", a)) or "ok"
    tk_messagebox.showwarning = lambda *a, **k: boxes.append(("warning", a)) or "ok"

    tk_tables: dict[str, tuple] = {}
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        # the same trace the Qt shell's redraw runs, so the analyses have their live state
        editor._build_preview_system_rays_bundle(sampling_mode="world_envelope")
        for name, opener in REPORTS.items():
            headings, cells = _tk_table(editor, opener)
            tk_tables[name] = (headings, cells)
        opened = [name for name, (headings, _cells) in tk_tables.items() if headings]
        ok(len(opened) == len(REPORTS) and not boxes,
           f"T: all {len(opened)} Tk report dialogs opened with a table"
           + (f" -- message boxes: {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror, tk_messagebox.showwarning = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q/P: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    qt_tables = {row[0]: (row[1], row[2], row[3], row[4]) for row in payload}
    ok(sorted(qt_tables) == sorted(REPORTS),
       f"Q: all {len(qt_tables)} Qt report dialogs opened with a table")

    for name in REPORTS:
        tk_headings, tk_cells = tk_tables.get(name, (None, None))
        qt_headings, qt_digest, qt_shape, qt_first = qt_tables.get(name, (None, None, None, None))
        if tk_cells is None or qt_headings is None:
            ok(False, f"P:{name}: one side produced no table (Tk={tk_cells is not None}, "
                      f"Qt={qt_headings is not None})")
            continue
        tk_digest = digest(tk_cells)
        same_shape = [len(tk_cells), len(tk_headings)] == qt_shape
        first_diff = next((index for index, (a, b) in enumerate(zip(tk_cells[0] if tk_cells else [],
                                                                   qt_first)) if a != b), None)
        ok(tk_headings == qt_headings and same_shape and tk_digest == qt_digest,
           f"P:{name}: Tk and Qt show the same {qt_shape[0]}x{qt_shape[1]} table -- identical "
           f"headings and one SHA-256 over every cell ({tk_digest[:16]}...)"
           + ("" if tk_digest == qt_digest else
              f" -- DIFFER: row 0 column {first_diff}: Tk {tk_cells[0][first_diff]!r} vs Qt "
              f"{qt_first[first_diff]!r}" if first_diff is not None else " -- DIFFER"))

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
