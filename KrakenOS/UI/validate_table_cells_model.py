"""Guard for bugs/0989: the surface table's cells are the model's; the cell parser no longer reads a Tk widget.

Phase 7b of the Qt migration, first part. A cell of the surface table is text: what the model
formats, then whatever was typed or chosen over it, and the parser reads the rows back from those
texts. The texts lived in the Tk table widget -- `_read_rows_from_table` asked a `ttk.Treeview`
for its items and their values -- so the Qt shell and a headless editor kept a hidden Tk table to
parse a typed number. They are `services/table_cells.py` now; the Tk table is a view of them.

That every shipped layout parses to the same rows, and takes the same edits the same way, as before
the change is recorded in bugs/0989 (164 layouts, 5 857 steps, identical). This guard holds what
must stay true:

  S  no module of the toolkit-free layers asks the editor's Tk table about its CELLS -- which rows
     it has, what they say -- counted, 0 (26 before); what they still ask it about, the selection
     and the pointer, is counted exactly too and may only shrink; the cell store names no tkinter
  C  the cell store on its own: rows in the order added, their texts and tags; one text set, a
     short row padded; a row that is not there takes nothing; an id added twice is there once
  N  with NO Tk table: a headless editor whose Tk table is destroyed and removed takes the same
     thirty cell edits and path-view changes as one that has it -- the same answers, the same rows
     -- and knows it is in a path view, where the pose columns are path-local
  P  the parser reads the model, not the widget: a text written straight into the Tk widget is NOT
     parsed; a text given to the model is, and the Tk table shows it; the two builder scripts'
     rename, which used to write into the widget, survives a parse
  V  the Tk table shows exactly the model's cells -- same rows, same order, same texts, same tags
     -- after a load, a committed cell, a chosen material, a path view and back; in a path view
     the headings are the path-local ones, and the model knows the mode
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

RESULT_MARK = "TABLECELLS_RESULT "
SKIP_MARK = "TABLECELLS_SKIP "
ROOT = Path("KrakenOS/UI")
LAYERS = ("services", "reports", "row_forms", "uihost")
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
CELL_METHODS = {"get_children", "item", "set", "insert", "delete", "exists", "index", "heading"}
SELECTION_METHODS = {"selection", "selection_set", "selection_remove", "selection_add", "selection_toggle", "focus", "see"}
#: what the toolkit-free layers still ask the editor's Tk table, by kind. EXACT: a count that falls
#: must be lowered here, so it can only shrink (bugs/0989 took "cells" from 26 to 0).
#: selection: the table workbench 53, the import/export service 3, the scene placement commands 2
TK_TABLE_USES = {"selection": 58, "geometry and events": 16}
TK_TABLE_USE = re.compile(r"\b(?:self|self\.editor|editor)\.table\.(\w+)"
                          r"|\btable\.(get_children|item|set|insert|delete|exists|index|heading|selection\w*|focus|see)\(")
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog"}
EDITS = (("thickness", "7.25"), ("rc", "-33.5"), ("name", "Edited 007"), ("tilt_x", "1, 2, 3"), ("desp_y", "0.5"),
         ("diameter", "12.5"), ("glass", "F2"), ("k", "abc"), ("surface", "Mirror"), ("tilt_x", "44, 45, 46"))


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def tk_table_uses() -> dict:
    """kind -> {module: count} of what the toolkit-free layers ask the editor's Tk table."""
    found: dict = {}
    for layer in LAYERS:
        for path in sorted((ROOT / layer).rglob("*.py")):
            for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
                if line.strip().startswith("#"):
                    continue
                for first, second in TK_TABLE_USE.findall(line):
                    name = first or second
                    kind = "cells" if name in CELL_METHODS else "selection" if name in SELECTION_METHODS else "geometry and events"
                    per_module = found.setdefault(kind, {})
                    key = path.relative_to(ROOT).as_posix()
                    per_module[key] = per_module.get(key, 0) + 1
    return found


def pure_checks() -> list:
    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.services import editable_table_rows

        uses = tk_table_uses()
        totals = {kind: sum(per_module.values()) for kind, per_module in uses.items()}
        cells = uses.get("cells", {})
        store = ast.parse((ROOT / "services/table_cells.py").read_text(encoding="utf-8"))
        store_tk = sorted({node.id for node in ast.walk(store) if isinstance(node, ast.Name) and node.id in TK_NAMES}
                          | {alias.name for node in ast.walk(store) if isinstance(node, (ast.Import, ast.ImportFrom))
                             for alias in node.names if "tkinter" in alias.name or "tkinter" in (getattr(node, "module", "") or "")})
        parser = Path(editable_table_rows.__file__).read_text(encoding="utf-8")
        view = [name for name in ("_show_tk_table_rows", "_show_tk_table_cell", "_show_tk_table_headings")
                if name in vars(KrakenLayoutEditor)]
        return (cells == {} and {kind: count for kind, count in totals.items() if kind != "cells"} == TK_TABLE_USES
                and store_tk == [] and "self._table_cells()" in parser and "self.table" not in parser and len(view) == 3,
                f"what the toolkit-free layers ask the editor's Tk table: about its cells {cells or 'nothing'} (26 uses before "
                f"bugs/0989); otherwise {totals} (listed: {TK_TABLE_USES}; a count that falls must be lowered in the list); the "
                f"cell store names tkinter {store_tk or 'nowhere'}; the parser reads the model's cells and no widget: "
                f"{'self._table_cells()' in parser and 'self.table' not in parser}; the editor delegates {len(view)} view calls")

    def c():
        from KrakenOS.UI.services.table_cells import TableCells

        cells = TableCells()
        cells.add("row_0", ["0", "Object", 45], ("blue",))
        cells.add("scene_source_1", ("Src1", "Illumination Source"), ("scene_source",))
        cells.add("row_1", ["1"])
        listed = (cells.items(), cells.values("row_0"), cells.tags("scene_source_1"), cells.tags("row_1"), cells.index("row_1"),
                  cells.exists("row_1"), cells.exists("row_9"), cells.text("row_0", 1), cells.text("row_0", 7), cells.text("row_9", 0))
        cells.set_text("row_1", 3, 2.5)
        cells.set_text("row_0", 1, "Standard")
        cells.set_text("row_9", 0, "nobody")
        edited = (cells.values("row_1"), cells.values("row_0"), cells.exists("row_9"), cells.values("row_9"))
        cells.add("row_0", ["again"])
        again = (cells.items(), cells.values("row_0"), cells.tags("row_0"))
        try:
            cells.index("row_9")
            missing = "no error"
        except ValueError:
            missing = "ValueError"
        cells.clear()
        return (listed == (("row_0", "scene_source_1", "row_1"), ("0", "Object", "45"), ("scene_source",), (), 2, True, False,
                           "Object", "", "")
                and edited == (("1", "", "", "2.5"), ("0", "Standard", "45"), False, ())
                and again == (("scene_source_1", "row_1", "row_0"), ("again",), ()) and missing == "ValueError"
                and cells.items() == (),
                f"rows in the order added with their texts and tags: {listed[:4]}; position, there, not there, a text, past "
                f"the end, of nobody: {listed[4:]}; one text set and a short row padded: {edited[:2]}; a row that is not "
                f"there takes nothing: {edited[2:]}; an id added twice is there once, last: {again}; the position of a row "
                f"that is not there: {missing}; cleared: {cells.items()}")

    return _claims((("S", s), ("C", c)))


def _scripted_edits(editor) -> list:
    """Thirty cell edits on three rows, the image value, a path view -- a thickness and a pose typed
    there, and a row that is hidden -- and back."""
    steps = []
    editor._sync_table()
    editor._read_rows_from_table()
    for index in (1, 3, 4):
        for field, text in EDITS:
            steps.append([index, field, editor.commit_cell(index, field, text, quiet=True)])
    editor._sync_image_row_table_value()
    options = list(editor.arm_view_options())
    editor.arm_view_var.set(options[1])
    editor.set_arm_view()
    shown = [index for index in (editor._table_item_row_index(item) for item in editor._table_cells().items())
             if index is not None and 0 < index < len(editor.rows) - 1]
    # the pose columns mean something else in a path view (path-local): the MODEL must know the mode
    steps.append(["path-local mode", bool(editor.__dict__.get("_table_path_local_mode_active")), ""])
    steps.append([shown[0], "thickness", editor.commit_cell(shown[0], "thickness", "3.5", quiet=True)])
    steps.append([shown[-1], "desp_x", editor.commit_cell(shown[-1], "desp_x", "0.25", quiet=True)])
    steps.append(["path view", len(editor._table_cells().items()), editor.commit_cell(7, "thickness", "9", quiet=True)])
    editor.arm_view_var.set(options[0])
    editor.set_arm_view()
    steps.append(["all paths", len(editor._table_cells().items()), ""])
    return steps


def model_checks() -> list:
    def n():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.uihost import ScriptedUiHost

        outcome = {}
        for label in ("with", "without"):
            editor = KrakenLayoutEditor(headless=True, ui=ScriptedUiHost(answers={}))
            editor.refresh_plot = lambda *a, **k: None
            editor.layout_files[LAYOUT.stem] = LAYOUT
            editor.load_layout_by_name(LAYOUT.stem, refresh=False)
            if label == "without":
                editor.__dict__.pop("table").destroy()
            steps = _scripted_edits(editor)
            outcome[label] = (steps, [asdict(row) for row in editor.rows], "table" in editor.__dict__)
        (steps, rows, has), (steps_bare, rows_bare, has_bare) = outcome["with"], outcome["without"]
        refused = sum(1 for step in steps if step[2])
        changed = sum(1 for row in rows if row["name"] == "Edited 007")
        local = [step for step in steps if step[0] == "path-local mode"]
        return (has and not has_bare and steps == steps_bare and rows == rows_bare and len(steps) == 35 and refused == 4
                and changed == 3 and local == [["path-local mode", True, ""]]
                and steps[-2][:2] == ["path view", 8] and "not in the current path view" in steps[-2][2],
                f"a headless editor with its Tk table ({has}) and one with it destroyed and removed ({has_bare}) take the same "
                f"{len(steps)} steps -- same answers: {steps == steps_bare}, same {len(rows)} rows: {rows == rows_bare}; "
                f"{refused} of the steps were refusals, {changed} rows took the typed name, and in the path view of "
                f"{steps[-2][1]} rows a hidden row answers {steps[-2][2][:44]!r}")

    return _claims((("N", n),))


def tk_checks() -> list:
    from KrakenOS.UI import build_penta_analytic_telescope_layout, build_penta_telescope_layout
    from KrakenOS.UI.layout_editor import COLUMN_LABELS, FIELDS, PATH_LOCAL_COLUMN_LABELS, KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.refresh_plot = lambda *a, **k: None
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    for _ in range(4):
        editor.update()
    table = editor.table

    def shown() -> list:
        return [[item, [str(value) for value in table.item(item, "values")], [str(tag) for tag in table.item(item, "tags")]]
                for item in table.get_children()]

    def model() -> list:
        cells = editor._table_cells()
        return [[item, list(cells.values(item)), list(cells.tags(item))] for item in cells.items()]

    def claim_p():
        item = editor._table_item_for_row_index(3)
        before = float(editor.rows[3].thickness)
        table.set(item, "thickness", "999")                       # into the WIDGET, behind the model's back
        editor._read_rows_from_table()
        widget_only = (float(editor.rows[3].thickness), str(table.set(item, "thickness")),
                       editor._table_cells().text(item, FIELDS.index("thickness")))
        editor._set_table_cell_text(item, "thickness", "8.5")      # to the MODEL
        told = str(table.set(item, "thickness"))
        editor._read_rows_from_table()
        through_model = float(editor.rows[3].thickness)

        renamed = {}
        for index, module in ((4, build_penta_telescope_layout), (5, build_penta_analytic_telescope_layout)):
            name = f"Renamed by {module.__name__.rsplit('.', 1)[-1][6:22]}"
            module._rename_row(editor, index, name)
            editor.rows[index].name = "what the parser must put back"        # only the cell holds the name now
            editor._read_rows_from_table()
            renamed[index] = (editor.rows[index].name == name,
                              str(table.set(editor._table_item_for_row_index(index), "name")) == name)
        editor.commit_cell(3, "thickness", repr(before))
        return (before not in (999.0, 8.5) and widget_only == (before, "999", repr(before).rstrip("0").rstrip("."))
                and told == "8.5" and through_model == 8.5 and renamed == {4: (True, True), 5: (True, True)},
                f"a thickness of {before}: with 999 written into the Tk widget only, a parse leaves (the row, the widget, "
                f"the model's cell) {widget_only}; given to the model as 8.5 the Tk table shows {told!r} and a parse makes it "
                f"{through_model}; the two builders' rename (kept by a parse, shown by the Tk table): {renamed}")

    def claim_v():
        states = {"after the load": (shown(), model())}
        editor.commit_cell(3, "rc", "-41.5")
        states["after a committed cell"] = (shown(), model())
        editor.commit_cell(4, "glass", "F2")
        states["after a chosen material"] = (shown(), model())
        rc_shown = str(table.set(editor._table_item_for_row_index(3), "rc"))
        plain_headings = {field: str(table.heading(field, "text")) for field in FIELDS}
        options = list(editor.arm_view_options())
        editor.arm_view_var.set(options[1])
        editor.set_arm_view()
        for _ in range(3):
            editor.update()
        states["in a path view"] = (shown(), model())
        local = bool(editor.__dict__.get("_table_path_local_mode_active"))
        path_headings = {field: str(table.heading(field, "text")) for field in FIELDS}
        in_view = len(table.get_children())
        editor.arm_view_var.set(options[0])
        editor.set_arm_view()
        for _ in range(3):
            editor.update()
        states["back to all paths"] = (shown(), model())
        same = {name: view == cells for name, (view, cells) in states.items()}
        sizes = {name: len(view) for name, (view, _cells) in states.items()}
        tagged = sum(1 for _item, _values, tags in states["after the load"][0] if tags)
        expected_local = {field: PATH_LOCAL_COLUMN_LABELS.get(field, COLUMN_LABELS[field]) for field in FIELDS}
        return (all(same.values()) and len(same) == 5 and sizes["after the load"] == 13 and in_view == 8 and tagged >= 8
                and rc_shown == "-41.5" and plain_headings == {field: COLUMN_LABELS[field] for field in FIELDS}
                and local and path_headings == expected_local and path_headings != plain_headings
                and not editor.__dict__.get("_table_path_local_mode_active"),
                f"the Tk table shows exactly the model's cells {same} (rows {sizes}, {tagged} of them tagged); the committed "
                f"Rc reads {rc_shown!r}; in the path view the model knows the mode ({local}), the table has {in_view} rows and "
                f"its headings are the path-local ones: {path_headings == expected_local} "
                f"({sum(1 for f in FIELDS if path_headings[f] != plain_headings[f])} differ from the plain ones)")

    return _claims((("P", claim_p), ("V", claim_v)))


def _run(call: str, claim: str, needs_display: bool) -> list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs_display else "")
        + "from KrakenOS.UI.validate_table_cells_model import model_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
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
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["S", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("model_checks()", "N", False) + _run("tk_checks()", "P", True)
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
