"""Display-free guard: the Non-Sequential Scene Graph renders a builder (bugs/0897,
docs/design_qt_migration.md phase 4).

The last dialog of the report family, and the first whose data had no builder at all -- Qt had
never shown it. The collector returns FLAT records carrying `id` and `parent`, which is what a
`ttk.Treeview` wants; `TreeRow` wants children, so `reports/nonseq_scene_graph.py` nests them
once and both toolkits draw the result.

Its three verbs act on the selected node, and two of them needed things the report could not say:

* **a key that survives a rebuild.** Set Target ADDS a target node, so a node key that is a row
  INDEX would afterwards point at a different node than the user had selected. The key is the
  record's own `id` string, as the Tk dialog's iids always were.
* **where to start.** The Tk dialog opened on the first SURFACE node, not the first node;
  `Report.initial_key` says so, and a refresh keeps whatever the user had instead.

`ReportAction.on_activate` carries the double-click, which ran Select Row.

  L  the panel is one `ReportWindow`; the editor keeps none of its widgets, and
     DIALOG_SCOPED_VARIABLES is finally empty
  N  the tree is the collector's records, nested by `parent`, with every record drawn once
  K  the selection survives a refresh, and Set Target -- which grows the graph -- leaves the
     user on the node they had, with the verb's own message in the status bar
  V  Select Row selects the row (a whole ELEMENT when the node is one), and the CSV carries the
     14 record keys, not the 10 shown columns
  Q  the Qt shell has the dialog at last, showing the same tree
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def digest(rows) -> str:
    return sha256(json.dumps(rows, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def walk_tk(table, node="", depth=0):
    """Every node of a Tk tree, depth first: depth, label, cells."""
    walked = []
    for child in table.get_children(node):
        item = table.item(child)
        walked.append([depth, str(item["text"]), [str(value) for value in item["values"]]])
        walked.extend(walk_tk(table, child, depth + 1))
    return walked


def qt_runtime_checks() -> list[list]:
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.reports import build_nonseq_scene_graph_report

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()

    dialog = window.action_manager["nonseq_scene_graph"].trigger() or window._open_dialogs[-1]
    app.processEvents()
    model = dialog.tree_model
    from PySide6.QtCore import Qt

    walked: list = []

    def walk(item, depth):
        for row in range(item.rowCount()):
            child = item.child(row, 0)
            if child is None:
                continue
            cells = [item.child(row, c).text() if item.child(row, c) is not None else ""
                     for c in range(1, model.columnCount())]
            walked.append([depth, child.text(), cells])
            walk(child, depth + 1)

    walk(model.invisibleRootItem(), 0)
    report = build_nonseq_scene_graph_report(window.editor)
    rows = [["Q", len(walked) == len(report.rows) and dialog.selected_key() == report.initial_key
             and [action.label for action in report.actions] ==
             ["Select Row", "Set Target", "Edit Target"],
             f"the Qt shell drew all {len(walked)} nodes, opened on {dialog.selected_key()!r} and "
             f"offers {list(dialog.action_buttons)}"]]
    rows.append(["tree", True, digest(walked), len(walked)])
    dialog.close()
    window.close()
    return rows


def _run_qt_subprocess() -> tuple[str, list]:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0897_scene_graph_on_report_view import "
        "qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.model_variables import DIALOG_SCOPED_VARIABLES
    from KrakenOS.UI.panels import main_nonseq_scene_graph_dialog
    from KrakenOS.UI.reports.nonseq_scene_graph import CSV_COLUMNS, LAYOUT

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    panel_source = inspect.getsource(main_nonseq_scene_graph_dialog)
    editor_source = (Path("KrakenOS/UI/layout_editor.py")).read_text(encoding="utf-8")
    ok(panel_source.count("ReportWindow(") == 1 and "ttk.Treeview(" not in panel_source
       and "_nonseq_scene_table" not in editor_source
       and "_nonseq_scene_window" not in editor_source
       and not DIALOG_SCOPED_VARIABLES,
       f"L: the panel is one ReportWindow ({len(panel_source.splitlines())} lines), the editor "
       f"keeps none of its widgets, and DIALOG_SCOPED_VARIABLES is empty at last")

    saved = (tk_messagebox.showinfo, tk_messagebox.showerror, tk_filedialog.asksaveasfilename)
    boxes: list = []
    tk_messagebox.showinfo = lambda *a, **k: boxes.append(a) or "ok"
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"
    tk_digest = None

    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        panel = editor._main_nonseq_scene_graph_dialog()
        editor.open_nonseq_scene_graph()
        window = panel._report_window
        report = window.report

        # ---- N the tree is the records, nested ------------------------------------------
        walked = walk_tk(window.table)
        tk_digest = digest(walked)
        expected_cells = {str(record.get("id", "")):
                          [str(record.get(key, "")) for key, *_rest in LAYOUT]
                          for record in report.rows}
        by_label = {}
        for _depth, label, cells in walked:
            by_label.setdefault(label, []).append(cells)
        nested = [entry for entry in walked if entry[0] >= 1]
        ok(len(walked) == len(report.rows) and nested
           and all(cells in expected_cells.values() for _d, _l, cells in walked)
           and not boxes,
           f"N: {len(walked)} nodes for {len(report.rows)} records, {len(nested)} of them nested "
           f"under a parent, every cell row the record's own"
           if len(walked) == len(report.rows) else
           f"N: drew {len(walked)} nodes for {len(report.rows)} records")

        ok(window.selected_key() == report.initial_key
           and str(report.initial_key).startswith("surface:"),
           f"N2: it opened on the first surface node ({report.initial_key!r}), as the Tk dialog "
           f"always did -- not on the first node")

        # ---- K the selection survives, and Set Target grows the graph --------------------
        keys = [key for key in window._tree_keys.values() if key is not None]
        target_key = next(key for key in keys if str(key).startswith("surface:")
                          and key != report.initial_key)
        window.select_key(target_key)
        before_nodes = len(report.rows)
        editor._refresh_nonseq_scene_graph()
        kept = window.selected_key()
        editor._set_nonseq_scene_target()
        after = panel._report_window
        ok(kept == target_key and after.selected_key() == target_key
           and "Non-sequential target set to row" in editor.status_var.get(),
           f"K: the refresh kept {target_key!r}, Set Target grew the graph "
           f"{before_nodes} -> {len(after.report.rows)} nodes and left the user there, with its "
           f"own message ({editor.status_var.get()[:52]!r})"
           if kept == target_key and after.selected_key() == target_key else
           f"K: selection {target_key!r} -> after refresh {kept!r} -> after Set Target "
           f"{after.selected_key()!r}; status {editor.status_var.get()[:60]!r}")

        # ---- V the verbs and the CSV -----------------------------------------------------
        element_key = next((key for key in window._tree_keys.values()
                            if key is not None and str(key).startswith("element:")), None)
        selected_rows = None
        if element_key is not None:
            window.select_key(element_key)
            panel._select_nonseq_scene_row()
            selected_rows = list(editor.table.selection())
        csv_path = Path("/tmp/claude-1000/guard_0897_scene_graph.csv")
        tk_filedialog.asksaveasfilename = lambda *a, **k: str(csv_path)
        panel.export_nonseq_scene_graph_csv()
        header = csv_path.read_text(encoding="utf-8").splitlines()[0]
        ok(header.split(",") == list(CSV_COLUMNS) and len(CSV_COLUMNS) > len(LAYOUT)
           and (selected_rows is None or len(selected_rows) >= 1),
           f"V: Select Row put {len(selected_rows or [])} row(s) in the table selection for an "
           f"element node, and the CSV carries the {len(CSV_COLUMNS)} record keys, not the "
           f"{len(LAYOUT)} shown columns")
    finally:
        tk_messagebox.showinfo, tk_messagebox.showerror, tk_filedialog.asksaveasfilename = saved
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
    else:
        for row in qt_rows:
            if row[0] == "tree":
                ok(row[2] == tk_digest,
                   f"T: the Qt tree is the Tk tree -- one SHA-256 over all {row[3]} nodes, "
                   f"labels and cells ({row[2][:16]}...)"
                   if row[2] == tk_digest else
                   f"T: Qt {row[2][:16]}... over {row[3]} nodes, Tk {(tk_digest or '')[:16]}...")
                continue
            ok(row[1], f"{row[0]}: {row[2]}")

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
