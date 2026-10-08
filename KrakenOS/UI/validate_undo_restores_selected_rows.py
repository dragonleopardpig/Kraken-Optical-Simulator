"""Guard for bugs/0991: Undo and Redo put the selection back on the ROWS that were selected.

The history keeps which rows were selected, as row numbers. Restoring them, the editor took each
number as a PLACE in the table. The two are the same only while every table line is a surface row
in order: a source row above shifts every place by one, and a path view hides rows. So in a scene
with an illumination source, Undo left the selection one row up -- and a Delete, Duplicate or Move
after it acted on the wrong rows. Measured in the Tk interface on the two-arm doublets: rows 2 and 3
selected, a cell committed, Undo -- rows 1 and 2 were selected, and Delete removed the beam
splitter's faces. (The Qt table keeps its own selection, so only the model's copy was wrong there.)

  M  the model, on a headless editor holding the two-arm doublets (a source row sits above row 1):
  M  the model, on a headless editor holding the two-arm doublets (a source row sits above row 1):
     rows 2 and 3 selected, a cell committed, another row selected instead, Undo -- rows 2 and 3
     are selected again, the focus on row 2; Redo, from yet another selection, brings back the
     selection Undo was pressed with; rows 2 and 3 deleted, another row selected, the delete
     undone -- rows 2 and 3 again, every row back. In a path view, where rows are hidden: an
     edited row comes back selected as that row. A scene with no source row behaves as it always did
  T  the Tk interface: after Undo the selection's outline is drawn on rows 2 and 3 -- measured
     against the table's own cells -- and Delete removes those rows
  Q  the Qt interface: after Undo the Qt table and the model name the same rows, 2 and 3
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

RESULT_MARK = "UNDOSELECTION_RESULT "
SKIP_MARK = "UNDOSELECTION_SKIP "
SCENE = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
PLAIN = Path("KrakenOS/common_optical_layouts/double_gauss_lens.py")
SELECTION_COLOR = "#2563eb"


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _load(editor, path: Path) -> None:
    editor.refresh_plot = lambda *a, **k: None
    editor.layout_files[path.stem] = path
    editor.load_layout_by_name(path.stem, refresh=False)


def model_checks() -> list:
    def m():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.uihost import ScriptedUiHost

        editor = KrakenLayoutEditor(headless=True, ui=ScriptedUiHost(answers={}))
        _load(editor, SCENE)
        idle = lambda: editor.ui.run_due(100)
        items = editor._table_cells().items()
        source_above = items[1].startswith("scene_source_") and items[2] == "row_1"
        names = [row.name for row in editor.rows]

        editor._select_table_indices([2, 3], focus_index=2)
        idle()
        editor.commit_cell(2, "thickness", "4.5", quiet=True)
        idle()
        editor._select_table_indices([5])            # elsewhere: Undo must bring the selection BACK, not leave it
        idle()
        elsewhere = editor._selected_table_indices()
        editor.undo()
        idle()
        after_undo = (editor._selected_table_indices(), list(editor._table_selection()), editor._table_focus_item(),
                      float(editor.rows[2].thickness))
        editor._select_table_indices([6])
        idle()
        editor.redo()                                # back to the state Undo left: row 5 was selected then
        idle()
        after_redo = (editor._selected_table_indices(), list(editor._table_selection()), float(editor.rows[2].thickness))

        editor._select_table_indices([2, 3], focus_index=2)
        idle()
        editor.delete_selected()
        idle()
        removed = [name for name in names if name not in [row.name for row in editor.rows]]
        editor._select_table_indices([1])
        idle()
        editor.undo()
        idle()
        after_delete_undone = (editor._selected_table_indices(), [row.name for row in editor.rows] == names)

        options = list(editor.arm_view_options())
        editor.arm_view_var.set(options[2])
        editor.set_arm_view()
        idle()
        shown = [index for index in (editor._table_item_row_index(item) for item in editor._table_cells().items())
                 if index is not None and 0 < index < len(editor.rows) - 1]
        far = max(shown)
        place = list(editor._table_cells().items()).index(f"row_{far}")
        editor._select_table_indices([far])
        idle()
        editor.commit_cell(far, "thickness", "2.5", quiet=True)
        idle()
        editor._select_table_indices([shown[0]])
        idle()
        editor.undo()
        idle()
        in_view = (editor._selected_table_indices(), far, place, shown[0])
        editor.arm_view_var.set(options[0])
        editor.set_arm_view()
        idle()

        _load(editor, PLAIN)
        plain_items = editor._table_cells().items()
        no_source = not any(item.startswith("scene_source_") for item in plain_items)
        editor._select_table_indices([2, 3], focus_index=2)
        idle()
        editor.commit_cell(2, "thickness", "4.5", quiet=True)
        idle()
        editor._select_table_indices([1])
        idle()
        editor.undo()
        idle()
        plain = editor._selected_table_indices()
        return (source_above and elsewhere == [5] and after_undo == ([2, 3], ["row_2", "row_3"], "row_2", float(after_undo[3]))
                and after_undo[3] != 4.5 and after_redo == ([5], ["row_5"], 4.5)
                and removed == [names[2], names[3]] and after_delete_undone == ([2, 3], True)
                and in_view[0] == [far] and far != place and far != in_view[3] and no_source and plain == [2, 3],
                f"a source row sits above row 1 ({source_above}); rows 2 and 3 selected, a cell committed, row 5 selected "
                f"instead, Undo -> (rows, items, focus item, the thickness) {after_undo}; row 6 selected, Redo -> "
                f"{after_redo}, the selection Undo was pressed with; rows 2 and 3 deleted: {removed}; another row selected "
                f"and the delete undone -> {after_delete_undone[0]} with every row back ({after_delete_undone[1]}); in a "
                f"path view, row {in_view[1]} -- at place {in_view[2]} of the table -- edited, row {in_view[3]} selected "
                f"instead, Undo -> {in_view[0]}; a scene with no source row ({no_source}) -> {plain}")

    return _claims((("M", m),))


def tk_checks() -> list:
    import tkinter.messagebox as tk_messagebox

    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: "ok")
    for name in ("askyesno", "askokcancel"):
        setattr(tk_messagebox, name, lambda *a, **k: True)

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")
    _load(editor, SCENE)
    table = editor.table

    def settle(rounds: int = 8) -> None:
        for _ in range(rounds):
            editor.update()
            time.sleep(0.02)

    settle()

    def claim_t():
        names = [row.name for row in editor.rows]
        editor._select_table_indices([2, 3], focus_index=2)
        settle()
        editor.commit_cell(2, "thickness", "4.5")
        settle()
        editor.undo()
        settle()
        pieces = [w for w in table.winfo_children() if w.winfo_class() == "Frame" and str(w.cget("bg")) == SELECTION_COLOR
                  and w.place_info()]
        top = min(int(w.winfo_y()) for w in pieces)
        bottom = max(int(w.winfo_y()) + int(w.winfo_height()) for w in pieces)
        row = lambda index: table.bbox(f"row_{index}", "#3")
        wanted = (row(2)[1], row(3)[1] + row(3)[3])
        one_up = (row(1)[1], row(2)[1] + row(2)[3])
        selected = (list(table.selection()), editor._selected_table_indices())
        editor.delete_selected()
        settle()
        removed = [name for name in names if name not in [row.name for row in editor.rows]]
        return (len(pieces) == 4 and (top, bottom) == wanted and wanted != one_up and selected == (["row_2", "row_3"], [2, 3])
                and removed == [names[2], names[3]],
                f"after Undo the Tk table has {selected[0]} selected and outlines y {top}..{bottom} -- rows 2 and 3 are at "
                f"{wanted[0]}..{wanted[1]}, one row up would be {one_up[0]}..{one_up[1]}; Delete then removes {removed}")

    return _claims((("T", claim_t),))


def qt_checks() -> list:
    def q():
        from PySide6.QtWidgets import QMessageBox

        from KrakenOS.UI.qt.app import build

        for name in ("information", "warning", "critical"):
            setattr(QMessageBox, name, staticmethod(lambda *a, **k: QMessageBox.StandardButton.Ok))
        setattr(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
        app, window = build(["guard"])
        window.show()

        def settle(seconds: float = 0.4) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.0)
        editor = window.editor
        _load(editor, SCENE)
        settle()
        editor._select_table_indices([2, 3], focus_index=2)
        settle()
        editor.commit_cell(2, "thickness", "4.5")
        settle()
        editor.undo()
        settle()
        qt_table = sorted(int(index) for index in editor.selected_row_indices())
        model = (editor._selected_table_indices(), list(editor._table_selection()))
        return (qt_table == [2, 3] and model == ([2, 3], ["row_2", "row_3"]),
                f"after Undo the Qt table has rows {qt_table} selected and the model names {model[1]} -- the same rows: "
                f"{model == ([2, 3], ['row_2', 'row_3'])}")

    return _claims((("Q", q),))


def _run(call: str, claim: str, needs: str, needs_display: bool) -> list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs_display else "")
        + needs
        + "from KrakenOS.UI.validate_undo_restores_selected_rows import model_checks, qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=600,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[claim, False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [[claim, False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = (_run("model_checks()", "M", "", False) + _run("tk_checks()", "T", "", True)
            + _run("qt_checks()", "Q", "import PySide6\n", True))
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
