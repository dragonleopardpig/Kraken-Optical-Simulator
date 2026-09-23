"""Display-free guard: the Ray Inspector, master and detail (bugs/0867,
docs/design_qt_migration.md phase 3).

The fourth dialog family: a master table (every traced ray) and a detail table (the hits of
whichever ray is selected). The detail side was already shared -- `_ray_hit_table_specs` and
`_ray_hit_table_values` on the editor -- while the master rows were formatted inline inside the Tk
refresh; they are now `KrakenOS/UI/reports/ray_tables.py`, which both toolkits fill from.

  C  the detail columns are the editor's own hit-table specs
  M  every master cell equals ray_table_values -- the tuple the Tk ray table inserts
  D  the detail follows the selection: each master row's hits are that record's, by
     _ray_hit_table_values, and selecting another row changes them
  S  the summary is the Tk ray inspector's own line
  T  the REAL Tk ray inspector shows the same master table -- one SHA-256 over every cell
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


def digest(cells) -> str:
    return hashlib.sha256(
        json.dumps(cells, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports.ray_tables import ray_table_values, summary_text

    from KrakenOS.UI.validate_open3d_0867_ray_inspector_master_detail import digest

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    dialog = window.action_manager["ray_inspector"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    report = dialog.report
    records = list(editor._collect_ray_analysis_records())

    # ---- C the detail columns are the editor's ------------------------------------------------
    specs = editor._ray_hit_table_specs()
    detail_columns = report.detail.columns
    row("C", len(detail_columns) == len(specs)
        and [c.key for c in detail_columns] == [str(s[0]) for s in specs]
        and [c.heading for c in detail_columns] == [str(s[1]) for s in specs],
        f"the detail table's {len(detail_columns)} columns are the editor's own hit-table specs")

    # ---- M every master cell ---------------------------------------------------------------------
    model = dialog.model
    mismatches = []
    for index, record in enumerate(records):
        for column_index, value in enumerate(ray_table_values(editor, record)):
            shown = model.data(model.index(index, column_index), Qt.ItemDataRole.DisplayRole)
            if shown != str(value):
                mismatches.append((index, column_index, shown, str(value)))
                break
        if mismatches:
            break
    master_cells = [[str(model.data(model.index(r, c), Qt.ItemDataRole.DisplayRole))
                     for c in range(model.columnCount())] for r in range(model.rowCount())]
    row("M", model.rowCount() == len(records) > 0 and not mismatches,
        f"{model.rowCount()}x{model.columnCount()} master cells equal ray_table_values -- the "
        f"tuple the Tk ray table inserts" + (f" -- MISMATCH {mismatches[:2]}" if mismatches else ""))

    # ---- D the detail follows the selection --------------------------------------------------------
    def expected_hits(index):
        return [[str(v) for v in editor._ray_hit_table_values(hit)]
                for hit in (records[index].get("hits", []) or [])]

    def shown_hits():
        detail = dialog.detail_model
        return [[str(detail.data(detail.index(r, c), Qt.ItemDataRole.DisplayRole))
                 for c in range(detail.columnCount())] for r in range(detail.rowCount())]

    dialog.select_master_row(0)
    app.processEvents()
    first = shown_hits()
    other = next((i for i in range(1, len(records))
                  if len(records[i].get("hits", []) or []) != len(first)), 1)
    dialog.select_master_row(other)
    app.processEvents()
    second = shown_hits()
    row("D", first == expected_hits(0) and second == expected_hits(other) and first != second,
        f"ray 0 shows its {len(first)} hits and ray {other} its {len(second)}, each by "
        f"_ray_hit_table_values, and the table changed with the selection")

    # ---- S the summary ---------------------------------------------------------------------------
    row("S", report.summary == summary_text(editor, len(records))
        and "image hits=" in report.summary and "stopped=" in report.summary,
        f"the summary is the Tk ray inspector's own line ({report.summary[:64]!r}...)")

    dialog.close()
    window.close()
    return [*rows, ["cells", True, digest(master_cells)]]


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
        "from KrakenOS.UI.validate_open3d_0867_ray_inspector_master_detail import qt_runtime_checks\n"
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


def _tk_master_cells(editor):
    """Open the REAL Tk ray inspector and read its master Treeview back."""
    import tkinter.ttk as ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_ray_inspector()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
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
            return None
        tree = trees[0]  # the master table is the first one built
        return [[str(value) for value in tree.item(item, "values")]
                for item in tree.get_children("")]
    finally:
        window.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

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

    tk_digest = None
    tk_rows = 0
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor._build_preview_system_rays_bundle(sampling_mode="world_envelope")
        cells = _tk_master_cells(editor)
        if cells is not None:
            tk_digest = digest(cells)
            tk_rows = len(cells)
        ok(cells is not None and tk_rows > 0 and not boxes,
           f"T1: the REAL Tk ray inspector opened with {tk_rows} master rows"
           + (f" -- boxes {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP C/M/D/S/T2: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    *checks, cells_row = payload
    for name, passed, detail in checks:
        ok(passed, f"{name}: {detail}")
    ok(cells_row[2] == tk_digest,
       f"T2: the Qt master table equals the Tk one -- one SHA-256 over all {tk_rows} rows "
       f"({str(tk_digest)[:16]}...)")

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
