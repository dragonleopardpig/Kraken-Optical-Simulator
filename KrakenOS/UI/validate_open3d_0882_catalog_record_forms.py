"""Display-free guard: the Glass Catalog Browser and Stock Lens Importer record-list forms
(bugs/0882, docs/design_qt_migration.md phase 3).

Both are catalogue browsers -- a list you search and pick from -- so `RecordList` absorbed them
with one addition: an `on_change` on a TEXT field, so a filter is live, and the view re-asks the
model for its rows after any on_change. The glass browser edits nothing at all; the importer
carries the placement options and inserts a rigid block of rows.

  G  the glass browser: 3000+ records, a live filter, apply writes the row's glass
  S  the importer: a catalogue choice that LOADS, a live search, apply inserts the rows
  P  path mode adds the distance and the local decenter/tilt fields, and refuses a bad one
  T  both REAL Tk dialogs open on their record trees
  Q  both Qt dialogs list the same rows
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

    glass = window.action_manager["glass_catalog"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    glass_columns = [glass.records_view.horizontalHeaderItem(i).text()
                     for i in range(glass.records_view.columnCount())]
    glass_all = glass.records_view.rowCount()
    glass.widgets["filter"].setText("bk7")
    glass.on_field_changed(glass.form.field("filter"), "bk7")
    app.processEvents()
    glass_filtered = glass.records_view.rowCount()
    glass_pick = glass.form.values["glass"]
    glass.close()
    app.processEvents()

    stock = window.action_manager["stock_lens"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    stock_columns = [stock.records_view.horizontalHeaderItem(i).text()
                     for i in range(stock.records_view.columnCount())]
    stock_rows = stock.records_view.rowCount()
    stock_part = stock.form.values["part"]
    stock.close()
    app.processEvents()

    window.close()
    return [glass_columns, glass_all, glass_filtered, glass_pick,
            stock_columns, stock_rows, stock_part]


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
        "from KrakenOS.UI.validate_open3d_0882_catalog_record_forms import qt_runtime_checks\n"
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


def _tk_tree(editor, opener):
    from tkinter import ttk

    before = {str(child) for child in editor.root.winfo_children()}
    opener()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    trees = []
    try:
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    trees.append((tuple(child.cget("columns")), len(child.get_children())))
                walk(child)

        walk(window)
        return trees[0] if trees else None
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.row_forms import (FormRefused, build_glass_catalog_form,
                                       build_stock_lens_form)
    from KrakenOS.UI.row_forms import glass_catalog, stock_lens

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

        form = build_glass_catalog_form(editor)
        every = form.records.rows(form)
        no_row = form.validate(dict(form.values))
        form.values["filter"] = "bk7"
        message = form.field("filter").on_change(form, "bk7")
        filtered = form.records.rows(form)
        editor._select_table_row(2)
        status = form.apply(dict(form.values))
        ok(tuple(form.records.columns) == glass_catalog.COLUMNS and len(every) > 1000
           and 0 < len(filtered) < len(every)
           and form.values["glass"].lower().find("bk7") >= 0
           and no_row == ["Select a surface row first, then apply the glass."]
           and editor.rows[2].glass == form.values["glass"]
           and "Applied glass" in status and str(len(filtered)) in message,
           f"G: {len(every)} catalogue glasses, the live filter cut it to {len(filtered)}, "
           f"and apply wrote {editor.rows[2].glass!r} onto row 2 "
           f"(with no row selected it refuses)")

        form = build_stock_lens_form(editor)
        catalogs = list(form.choices_for("catalog"))
        loaded = form.records.rows(form)
        form.values["search"] = "achromat"
        search_message = form.field("search").on_change(form, "achromat")
        searched = form.records.rows(form)
        before_rows = len(editor.rows)
        status = form.apply(dict(form.values))
        ok(tuple(form.records.columns) == stock_lens.COLUMNS and len(catalogs) >= 2
           and len(loaded) == stock_lens.SHOWN_LIMIT and searched
           and "match(es)" in search_message
           and len(editor.rows) > before_rows and "Imported stock lens" in status,
           f"S: {len(catalogs)} catalogs, the loaded one drew {len(loaded)} rows (the "
           f"{stock_lens.SHOWN_LIMIT}-row cap), the search matched, and apply inserted "
           f"{len(editor.rows) - before_rows} surface rows")

        path_form = build_stock_lens_form(
            editor, path_placement={"splitter_index": 1, "arm_role": "Transmit"})
        path_keys = [field.key for field in path_form.fields]
        refusals = [path_form.validate(dict(path_form.values, distance="-5")),
                    path_form.validate(dict(path_form.values, local_tilt_x="sideways"))]
        ok(path_form.title == stock_lens.PATH_TITLE and "distance" in path_keys
           and all(key in path_keys for key in stock_lens.PATH_KEYS)
           and refusals[0] == ["Path distance must be positive."]
           and refusals[1] == ["Local offset and tilt values must be numeric."],
           f"P: path mode is titled {path_form.title!r} and adds "
           f"{1 + len(stock_lens.PATH_KEYS)} placement fields; "
           f"{refusals[0][0]!r} / {refusals[1][0]!r}")

        glass_tree = _tk_tree(editor, editor.open_glass_catalog_browser)
        stock_tree = _tk_tree(editor, editor.open_stock_lens_importer)
        ok(glass_tree is not None and glass_tree[0] == glass_catalog.COLUMNS
           and glass_tree[1] == len(every)
           and stock_tree is not None and stock_tree[0] == stock_lens.COLUMNS
           and stock_tree[1] == stock_lens.SHOWN_LIMIT and not boxes,
           f"T: the REAL Tk browser drew {glass_tree[1]} glasses and the REAL Tk importer "
           f"{stock_tree[1]} parts, each under the builder's columns")
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

    (glass_columns, glass_all, glass_filtered, glass_pick, stock_columns, stock_rows,
     stock_part) = payload
    ok(tuple(glass_columns) == glass_catalog.COLUMNS and glass_all > 1000
       and 0 < glass_filtered < glass_all and "bk7" in str(glass_pick).lower(),
       f"Q1: the Qt browser listed {glass_all} glasses and the live filter cut it to "
       f"{glass_filtered}, selecting {glass_pick!r}")
    ok(tuple(stock_columns) == stock_lens.COLUMNS and stock_rows > 0 and str(stock_part),
       f"Q2: the Qt importer listed {stock_rows} parts and selected {stock_part!r}")

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
