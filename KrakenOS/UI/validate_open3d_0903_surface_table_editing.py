"""Display-free guard: the surface table is editable in Qt (bugs/0903,
docs/design_qt_migration.md phase 4).

Since 0900-0902 the Qt shell could set up and run everything EXCEPT the lens itself: its surface
table was read-only, and the six table verbs could not be offered, because each one read its
selection straight from the Tk Treeview -- `self.table.selection()`. The Qt shell keeps a hidden
Tk table, so from Qt every verb would always have seen "nothing selected".

* The selection belongs to whichever shell shows the table: `_selected_table_indices` asks a
  shell's `selected_row_indices` first, `_select_table_indices` tells its `select_rows`, and
  `_sync_table` tells its `show_rows`. A Tk-only editor installs none of them and behaves as
  before.
* An edit has ONE commit, `commit_cell`, which Tk's `_finish_edit` and choice menu now call and
  the Qt model's `setData` calls too. It still parses through the Tk table, exactly as a Tk edit
  always has -- one parser rather than a second that could disagree -- and that is also what
  keeps the hidden table from reverting a Qt edit on the next `_read_rows_from_table`.
* The Qt cells show the text the Tk table shows (the model's `_table_values_for_surface_row`),
  all 15 fields, instead of a private seven-column formatter.

  S  no verb reads the Tk selection; the selection, the rebuild and the commit all go through
     seams or the one shared method
  T  Tk is unchanged: its selection drives duplicate/delete, its cell edit and choice menu commit
     through commit_cell, and a bad value still raises its own error box
  Q  in Qt every cell of every row is the Tk text; an edit commits, a bad one is refused with
     the model's message and changes nothing, a cell the surface type disallows is not editable;
     each of the six verbs acts on the Qt selection; and an edit survives a later verb AND a
     forced re-read from the hidden Tk table
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")
VERBS = ("add_surface", "delete_selected", "duplicate_selected", "flip_selected", "move_up",
         "move_down")


def qt_runtime_checks() -> list[list]:
    from PySide6.QtCore import Qt

    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    app.processEvents()
    editor, model = window.editor, window.rows_model
    fields = [model.field(column) for column in range(model.columnCount())]
    rows: list[list] = []

    # ---- Q1 every cell is the Tk text -----------------------------------------------------
    mismatched = []
    for row_index, row in enumerate(editor.rows):
        expected = [str(value) for value in editor._table_values_for_surface_row(row_index, row)]
        shown = [model.data(model.index(row_index, column)) for column in range(len(fields))]
        if shown != expected:
            mismatched.append(row_index)
    rows.append(["Q1", len(fields) == 15 and not mismatched and model.rowCount() == len(editor.rows),
                 f"all {model.rowCount()} rows x {len(fields)} cells show the Tk table's own text"
                 + (f" -- mismatched rows {mismatched}" if mismatched else "")])

    # ---- Q2 an edit, a refusal, a disallowed cell -----------------------------------------
    thickness = fields.index("thickness")
    before = editor.rows[5].thickness
    committed = model.setData(model.index(5, thickness), f"{before + 1.5:.4f}")
    after = editor.rows[5].thickness
    refused = not model.setData(model.index(5, thickness), "abc")
    message = model.last_refusal
    unchanged = editor.rows[5].thickness == after
    disallowed = next(((r, f) for r in range(len(editor.rows)) for f in fields
                       if f != "label" and not editor._table_cell_enabled(r, f)), None)
    not_editable = True
    if disallowed is not None:
        index = model.index(disallowed[0], fields.index(disallowed[1]))
        not_editable = not bool(model.flags(index) & Qt.ItemFlag.ItemIsEditable)
    label_locked = not bool(model.flags(model.index(0, fields.index("label")))
                            & Qt.ItemFlag.ItemIsEditable)
    rows.append(["Q2", committed and abs(after - (before + 1.5)) < 1e-9 and refused and unchanged
                 and "expects a number" in message and not_editable and label_locked
                 and disallowed is not None,
                 f"thickness {before} -> {after} committed; 'abc' refused ({message!r}) and "
                 f"changed nothing; {disallowed} -- a cell its surface type disallows -- and the "
                 f"# column are not editable"])

    # ---- Q3 the six verbs act on the Qt selection -----------------------------------------
    results = {}
    n = len(editor.rows)
    window.select_rows([4], 4)
    window.run_table_verb("add_surface")
    results["add_surface"] = (len(editor.rows) == n + 1 and window.selected_row_indices() == [5])
    window.run_table_verb("delete_selected")
    results["delete_selected"] = len(editor.rows) == n
    window.select_rows([3, 4], 3)
    window.run_table_verb("duplicate_selected")
    results["duplicate_selected"] = (len(editor.rows) == n + 2
                                     and window.selected_row_indices() == [5, 6])
    window.run_table_verb("delete_selected")
    # Flip on any two adjacent ordinary rows: om05a_folded has NO curved Standard surface (its
    # lens is a surrogate), so the radius negation cannot be seen here -- what CAN be seen, and
    # is the claim, is that the verb reversed exactly the rows selected in Qt
    ordinary = [i for i, r in enumerate(editor.rows) if r.surface not in ("Object", "Image")]
    pair = next((a, b) for a, b in zip(ordinary, ordinary[1:]) if b == a + 1)
    names_before = [row.name for row in editor.rows]
    window.select_rows(list(pair), pair[0])
    window.run_table_verb("flip_selected")
    names_after = [row.name for row in editor.rows]
    reversed_pair = (names_after[pair[0]] == editor._flipped_name(names_before[pair[1]])
                     and names_after[pair[1]] == editor._flipped_name(names_before[pair[0]]))
    others_kept = all(names_after[i] == names_before[i]
                      for i in range(len(names_before)) if i not in pair)
    results["flip_selected"] = reversed_pair and others_kept
    names = [row.name for row in editor.rows]
    movable = next((i for i in range(2, len(editor.rows) - 2)
                    if editor.rows[i].surface not in ("Object", "Image")), None)
    window.select_rows([movable], movable)
    window.run_table_verb("move_down")
    moved_down = [row.name for row in editor.rows] != names
    names_after = [row.name for row in editor.rows]
    window.run_table_verb("move_up")
    results["move_down"] = moved_down
    results["move_up"] = [row.name for row in editor.rows] != names_after
    rows.append(["Q3", all(results.values()) and set(results) == set(VERBS),
                 f"each verb acted on the Qt selection: {results}"])

    # ---- Q4 an edit survives a verb and a forced re-read ----------------------------------
    model.setData(model.index(5, thickness), "21.25")
    window.select_rows([8], 8)
    window.run_table_verb("move_down")
    editor._read_rows_from_table()
    survived = next((row.thickness for row in editor.rows if abs(row.thickness - 21.25) < 1e-9),
                    None)
    rows.append(["Q4", survived is not None,
                 "a Qt edit survived a later verb AND a forced re-read from the hidden Tk table "
                 "-- the commit writes through it, so there is nothing stale to revert to"])
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
        "from KrakenOS.UI.validate_open3d_0903_surface_table_editing import qt_runtime_checks\n"
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


class _FakeEntry:
    """What the Tk cell editor hands `_finish_edit`: the typed text."""

    def __init__(self, text: str) -> None:
        self.text = text

    def get(self) -> str:
        return self.text

    def destroy(self) -> None:
        pass


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.qt import rows_table
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as Workbench

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- S the seams ------------------------------------------------------------------------
    verb_sources = {name: inspect.getsource(getattr(Workbench, name)) for name in VERBS}
    reading_tk = [name for name, source in verb_sources.items() if "self.table.selection()" in source]
    selected = inspect.getsource(Workbench._selected_table_indices)
    finish = inspect.getsource(Workbench._finish_edit)
    set_data = inspect.getsource(rows_table)
    ok(not reading_tk and 'getattr(self, "selected_row_indices", None)' in selected
       and "self.commit_cell(" in finish and "self.editor.commit_cell(" in set_data
       and 'getattr(self, "show_rows", None)' in inspect.getsource(Workbench._sync_table)
       and 'getattr(self, "select_rows", None)' in inspect.getsource(Workbench._select_table_indices),
       "S: no verb reads the Tk selection; the model asks the shell for it, tells the shell what "
       "to select and when the rows were rebuilt, and both shells' edits go through commit_cell"
       + (f" -- still reading Tk: {reading_tk}" if reading_tk else ""))

    # ---- T Tk is unchanged ------------------------------------------------------------------
    boxes: list = []
    saved = tk_messagebox.showerror
    tk_messagebox.showerror = lambda *a, **k: boxes.append(a) or "ok"
    editor = KrakenLayoutEditor(headless=True)
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        no_seam = getattr(editor, "selected_row_indices", None) is None
        editor._select_table_indices([3, 4], focus_index=3)
        n = len(editor.rows)
        editor.duplicate_selected()
        duplicated = len(editor.rows) == n + 2 and editor._selected_table_indices() == [5, 6]
        editor.delete_selected()
        deleted = len(editor.rows) == n
        iid = editor._table_iid_for_row_index(5)
        editor.editor, editor._editor_row_id, editor._editor_field = _FakeEntry("33.5"), iid, "thickness"
        editor._finish_edit(iid, "thickness")
        typed = editor.rows[5].thickness == 33.5
        editor.editor = _FakeEntry("xyz")
        editor._finish_edit(iid, "thickness")
        boxed = len(boxes) == 1 and "expects a number" in str(boxes[-1])
        editor._apply_choice(editor._table_iid_for_row_index(6), "glass", "F2")
        chosen = editor.rows[6].glass == "F2"
        ok(no_seam and duplicated and deleted and typed and boxed and chosen,
           "T: a Tk-only editor has no shell seam, its Tk selection drives duplicate and delete, "
           "its typed edit and glass choice commit, and a bad value still raises its own error box"
           if no_seam else "T: a Tk-only editor unexpectedly has a shell selection seam")
    finally:
        tk_messagebox.showerror = saved
        editor.destroy()

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {qt_rows[0][2]}")
    else:
        for name, passed, detail in qt_rows:
            ok(passed, f"{name}: {detail}")

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
