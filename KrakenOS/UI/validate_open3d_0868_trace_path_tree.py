"""Display-free guard: the Trace Path Inspector's tree (bugs/0868,
docs/design_qt_migration.md phase 3).

The fifth dialog family: a HIERARCHY. Every traced ray is a node and the paths it split into hang
underneath it -- nested again when one path branched from another. bugs/0867 deliberately left
this dialog alone because a table cannot show that; `Report` now carries `TreeRow`s and the Qt
dialog renders them in a QTreeView, with the selected path's hits in the detail view.

  C  the columns are the Tk branch tree's own layout, under its "Ray / Path" heading
  N  the nesting is the model's: one node per ray, every path under its ray or its PARENT path,
     and exactly one detail-carrying node per record
  D  the detail follows the selected NODE, by the record key the node carries
  S  the summary is the Tk trace-path inspector's own line
  T  the REAL Tk branch tree, walked depth first, gives the same labels and cells as the Qt tree
     -- one SHA-256 over the whole hierarchy
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


def digest(rows) -> str:
    return hashlib.sha256(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def qt_runtime_checks() -> list:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports.branch_tree_tables import COLUMNS, TREE_HEADING, summary_text

    from KrakenOS.UI.validate_open3d_0868_trace_path_tree import digest

    rows: list = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor = window.editor

    dialog = window.action_manager["trace_paths"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    report = dialog.report
    model = dialog.tree_model
    records = list(report.rows)

    # ---- C the columns --------------------------------------------------------------------------
    headings = [model.headerData(c, Qt.Orientation.Horizontal)
                for c in range(model.columnCount())]
    row("C", headings == [TREE_HEADING, *[column.heading for column in COLUMNS]],
        f"the tree's {len(headings)} headings are the Tk layout under {TREE_HEADING!r}")

    # ---- N the nesting --------------------------------------------------------------------------
    walked: list = []

    def walk(item, depth):
        for index in range(item.rowCount()):
            child = item.child(index, 0)
            if child is None:
                continue
            cells = [item.child(index, c).text() if item.child(index, c) is not None else ""
                     for c in range(1, model.columnCount())]
            walked.append([depth, child.text(), cells,
                           child.data(Qt.ItemDataRole.UserRole) is not None])
            walk(child, depth + 1)

    walk(model.invisibleRootItem(), 0)
    ray_nodes = [entry for entry in walked if entry[0] == 0]
    detail_nodes = [entry for entry in walked if entry[3]]
    nested = [entry for entry in walked if entry[0] >= 1]
    expected_rays = len({int(record["ray_index"]) for record in records})
    row("N", len(ray_nodes) == expected_rays and len(detail_nodes) == len(records)
        and all(entry[1].startswith("Ray ") for entry in ray_nodes)
        and all(entry[1].startswith("Path ") for entry in nested),
        f"{len(ray_nodes)} ray nodes for {expected_rays} rays, {len(detail_nodes)} path nodes for "
        f"{len(records)} records, every nested node a Path")

    # ---- D the detail follows the node -----------------------------------------------------------
    def shown_hits():
        detail = dialog.detail_model
        return [[str(detail.data(detail.index(r, c), Qt.ItemDataRole.DisplayRole))
                 for c in range(detail.columnCount())] for r in range(detail.rowCount())]

    def expected_hits(key):
        hits = records[int(key)].get("hits", []) or []
        return [[str(v) for v in editor._ray_hit_table_values(hit)] for hit in hits]

    nodes = dialog.detail_nodes()
    dialog.select_master_row(0)
    app.processEvents()
    first_key = nodes[0].data(Qt.ItemDataRole.UserRole)
    first = shown_hits()
    other = next((i for i, node in enumerate(nodes)
                  if len(records[int(node.data(Qt.ItemDataRole.UserRole))].get("hits", []) or [])
                  != len(first)), min(3, len(nodes) - 1))
    dialog.select_master_row(other)
    app.processEvents()
    other_key = nodes[other].data(Qt.ItemDataRole.UserRole)
    second = shown_hits()
    row("D", first == expected_hits(first_key) and second == expected_hits(other_key)
        and len(nodes) == len(records),
        f"the detail follows the node: record {first_key} shows {len(first)} hits and record "
        f"{other_key} shows {len(second)}, each by _ray_hit_table_values")

    # ---- S the summary ---------------------------------------------------------------------------
    row("S", report.summary == summary_text(editor, len(records)) and "paths=" in report.summary,
        f"the summary is the Tk trace-path line ({report.summary[:64]!r}...)")

    flat = [[entry[0], entry[1], entry[2]] for entry in walked]
    dialog.close()
    window.close()
    return [*rows, ["tree", True, digest(flat), len(flat)]]


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
        "from KrakenOS.UI.validate_open3d_0868_trace_path_tree import qt_runtime_checks\n"
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


def _tk_tree(editor):
    """Open the REAL Tk trace-path inspector and walk its tree depth first."""
    import tkinter.ttk as ttk

    before = {str(child) for child in editor.root.winfo_children()}
    editor.open_branch_tree_inspector()
    windows = [child for child in editor.root.winfo_children()
               if str(child) not in before and child.winfo_class() == "Toplevel"]
    if not windows:
        return None
    window = windows[-1]
    try:
        trees: list = []

        def find(widget):
            for child in widget.winfo_children():
                if isinstance(child, ttk.Treeview):
                    trees.append(child)
                find(child)

        find(window)
        # the branch tree is the one that shows a tree column, not a flat table
        tree = next((t for t in trees if "tree" in str(t.cget("show"))), None)
        if tree is None:
            return None
        walked: list = []

        def walk(node, depth):
            for child in tree.get_children(node):
                item = tree.item(child)
                walked.append([depth, str(item["text"]),
                               [str(value) for value in item["values"]]])
                walk(child, depth + 1)

        walk("", 0)
        return walked
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
    tk_nodes = 0
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor._build_preview_system_rays_bundle(sampling_mode="world_envelope")
        walked = _tk_tree(editor)
        if walked is not None:
            tk_digest = digest(walked)
            tk_nodes = len(walked)
        ok(walked is not None and tk_nodes > 0 and not boxes,
           f"T1: the REAL Tk trace-path inspector opened with {tk_nodes} tree nodes"
           + (f" -- boxes {boxes}" if boxes else ""))
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror = saved
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP C/N/D/S/T2: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    *checks, tree_row = payload
    for name, passed, detail in checks:
        ok(passed, f"{name}: {detail}")
    ok(tree_row[2] == tk_digest and tree_row[3] == tk_nodes,
       f"T2: the Qt tree is the Tk tree -- one SHA-256 over all {tk_nodes} nodes, labels, cells "
       f"and depth ({str(tk_digest)[:16]}...)")

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
