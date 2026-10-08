"""Guard for bugs/0990: which rows are selected, and which has the focus, is the model's; no Tk table is asked.

Phase 7b of the Qt migration, second part. The Tk table shows a selection as borders, never as its
own highlight, so its `selection*` methods had been replaced by closures over a list the editor
holds -- model state, living in a widget's methods -- and the model asked the widget for it 57
times (`self.table.selection()`, `.selection_set(...)`, `.focus(...)`, `.see(...)`). The methods
are the model's now, the Tk table is pointed at them, and they work with no table at all.

That the selection behaves as before is recorded in bugs/0990: sixteen layouts on a real Tk editor,
537 steps of selects, clicks with and without Shift and Control, arrow keys, verbs, undo and redo
and path views, identical before and after. This guard holds what must stay true:

  S  no module of the toolkit-free layers asks the editor's Tk table for its selection, its focus
     item or to scroll -- counted, 0 (57 before); the model has the eight methods and no longer the
     two that touch the widget; the Tk panel has those and the three that mirror the focus
  M  the model alone, on a headless editor whose Tk table and overlays are removed: a selection
     keeps the order given, drops repeats and does not even store a row that is not shown; add,
     toggle and remove; a
     row that leaves the table is forgotten; three changes in a row announce themselves ONCE; the
     focus item is set, read, cleared, and lost when the rows are rebuilt; with nothing selected
     the focus row answers for the selected surface row; a source row answers with its source id
  N  with and without a Tk table, the same script -- selects, a commit, undo and redo, duplicate,
     move, group, ungroup, delete, a path view and back -- leaves the same selection, focus item,
     answers and rows after every step
  T  a real Tk editor: the widget's `selection*` ARE the model's -- a click, and a Tk panel calling
     the widget, both change what the model answers; nothing is ever selected natively, and
     what the widget selects on its own is cleared by the next change; the borders follow the
     selection; the focus item set through the model is the widget's, one set on
     the widget by a Tk panel is what the model answers; a row scrolled out of sight is brought
     into view
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "TABLESELECTION_RESULT "
SKIP_MARK = "TABLESELECTION_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
MODEL_METHODS = ("_table_selection", "_set_table_selection", "_remove_from_table_selection", "_add_to_table_selection",
                 "_toggle_table_selection", "_table_focus_item", "_set_table_focus_item", "_show_table_item")
VIEW_METHODS = ("_install_border_only_table_selection", "_clear_native_table_selection", "_tk_table_focus_item",
                "_show_tk_table_focus_item", "_show_tk_table_item")


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def pure_checks() -> list:
    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_surface_table_overlays import MainSurfaceTableOverlays
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as Model
        from KrakenOS.UI.validate_table_cells_model import tk_table_uses

        asked = tk_table_uses().get("selection", {})
        on_model = [name for name in MODEL_METHODS if name not in vars(Model)]
        widget_code = [name for name in VIEW_METHODS[:2] if name in vars(Model)]
        on_panel = [name for name in VIEW_METHODS if name not in vars(MainSurfaceTableOverlays)]
        delegated = [name for name in VIEW_METHODS if name in vars(KrakenLayoutEditor)]
        return (asked == {} and on_model == [] and widget_code == [] and on_panel == [] and len(delegated) == 5,
                f"the toolkit-free layers ask the editor's Tk table for its selection, focus item or to scroll: "
                f"{asked or 'nowhere'} (57 uses before bugs/0990); of the model's {len(MODEL_METHODS)} methods missing: "
                f"{on_model or 'none'}; widget code still on the model: {widget_code or 'none'}; missing from the Tk panel: "
                f"{on_panel or 'none'}; the editor delegates {len(delegated)} of {len(VIEW_METHODS)}")

    return _claims((("S", s),))


def _headless(without_table: bool):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.uihost import ScriptedUiHost

    editor = KrakenLayoutEditor(headless=True, ui=ScriptedUiHost(answers={}))
    editor.refresh_plot = lambda *a, **k: None
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    if without_table:                      # as an editor that never built a Tk table: no widget, no overlays
        editor.__dict__.pop("table").destroy()
        editor._cell_border_parts = []
        editor._grid_overlays = []
        editor._selection_border_overlays = []
    editor.ui.run_due(100)
    return editor


def _snapshot(editor) -> dict:
    return {"selection": list(editor._table_selection()), "focus": editor._table_focus_item(),
            "current": editor._current_selected_row_index(), "indices": editor._selected_table_indices(),
            "has": bool(editor._table_has_selection()), "surface_row": editor._selected_surface_row_index(),
            "source": editor._current_selected_scene_source_id(),
            "active": list(editor._active_cell) if editor._active_cell else None, "anchor": editor._selection_anchor_row,
            "rows": hashlib.sha1(repr([asdict(row) for row in editor.rows]).encode()).hexdigest()[:12]}


def _selection_script(editor) -> list:
    steps = []

    def step(label, call) -> None:
        call()
        editor.ui.run_due(100)                       # the selection announces itself when idle
        steps.append([label, _snapshot(editor)])

    source = next(item for item in editor._table_cells().items() if item.startswith("scene_source_"))
    step("select [1, 2], focus 2", lambda: editor._select_table_indices([1, 2], focus_index=2))
    step("select row 3", lambda: editor._select_table_row(3))
    step("add", lambda: editor._add_to_table_selection("row_5", "row_3", "nope"))
    step("toggle", lambda: editor._toggle_table_selection("row_3", "row_6"))
    step("remove", lambda: editor._remove_from_table_selection("row_5"))
    step("a source row", lambda: (editor._set_table_selection(source), editor._set_table_focus_item(source)))
    step("clear", editor._clear_table_selection)
    step("focus only", lambda: editor._set_table_focus_item("row_4"))
    step("select [2]", lambda: editor._select_table_indices([2]))
    step("commit", lambda: editor.commit_cell(2, "thickness", "4.5", quiet=True))
    step("undo", editor.undo)
    step("redo", editor.redo)
    step("select [2, 3]", lambda: editor._select_table_indices([2, 3], focus_index=3))
    step("duplicate", editor.duplicate_selected)
    step("move down", editor.move_down)
    step("move up", editor.move_up)
    step("group", editor.group_selected_as_element)
    step("ungroup", editor.ungroup_selected_elements)
    step("delete", editor.delete_selected)
    step("undo the delete", editor.undo)
    options = list(editor.arm_view_options())
    step("path view", lambda: (editor.arm_view_var.set(options[1]), editor.set_arm_view()))
    step("all paths", lambda: (editor.arm_view_var.set(options[0]), editor.set_arm_view()))
    return steps


def model_checks() -> list:
    bare = _headless(without_table=True)

    def m():
        editor = bare
        announced: list = []
        real = editor._on_table_selection_changed
        editor._on_table_selection_changed = lambda *a: (announced.append(len(editor._table_selection())), real(*a))[1]
        try:
            editor._set_table_selection(["row_2", "row_1"], "row_2", "nope", None, "")
            stored = list(editor._table_selected_items)      # what was KEPT, before a read prunes it: a row that is
            ordered = editor._table_selection()              # not shown must not wait there to be selected when it is
            editor._add_to_table_selection("row_3", "row_1")
            added = editor._table_selection()
            editor._toggle_table_selection("row_2", "row_4")
            toggled = editor._table_selection()
            editor._remove_from_table_selection("row_3")
            removed = editor._table_selection()
            before_idle = list(announced)
            editor.ui.run_due(100)
            after_idle = list(announced)
        finally:
            del editor._on_table_selection_changed

        cells = editor._table_cells()
        kept = {item: cells.values(item) for item in cells.items()}
        cells.clear()
        for item, values in kept.items():
            if item != "row_4":
                cells.add(item, values)
        forgotten = (editor._table_selection(), list(editor._table_selected_items))
        editor._sync_table()

        editor._set_table_focus_item("row_3")
        focus_set = editor._table_focus_item()
        editor._clear_table_selection()
        editor._set_table_focus_item("row_5")
        focus_row_answers = (editor._table_selection(), editor._selected_surface_row_index(), editor._current_selected_row_index())
        editor._sync_table()
        focus_after_rebuild = editor._table_focus_item()
        editor._set_table_focus_item("row_3")
        editor._set_table_focus_item("")
        focus_cleared = editor._table_focus_item()
        editor._show_table_item("row_3")                 # nothing to scroll: must simply do nothing

        source = next(item for item in cells.items() if item.startswith("scene_source_"))
        editor._set_table_selection(source)
        source_id = editor._current_selected_scene_source_id()
        source_answers = (bool(source_id), editor._current_selected_row_index(), editor._selected_table_indices())
        editor._clear_table_selection()
        editor.ui.run_due(100)
        return ("table" not in editor.__dict__ and stored == ["row_2", "row_1"]
                and ordered == ("row_2", "row_1") and added == ("row_2", "row_1", "row_3")
                and toggled == ("row_1", "row_3", "row_4") and removed == ("row_1", "row_4")
                and before_idle == [] and after_idle == [2] and forgotten == (("row_1",), ["row_1"])
                and focus_set == "row_3" and focus_row_answers == ((), 5, None) and focus_after_rebuild == ""
                and focus_cleared == "" and source_answers == (True, None, []),
                f"with no Tk table: selecting row 2, row 1, row 2 again, a row that is not shown, nothing -> {ordered} "
                f"(kept: {stored}); adding "
                f"row 3 and row 1 -> {added}; toggling rows 2 and 4 -> {toggled}; removing row 3 -> {removed}; announced before "
                f"idle {before_idle}, once idle {after_idle}; with row 4 gone from the table -> {forgotten}; the focus item set "
                f"{focus_set!r}; with nothing selected and the focus on row 5 (selection, selected surface row, current row) "
                f"{focus_row_answers}; after the rows are rebuilt {focus_after_rebuild!r}; cleared {focus_cleared!r}; a source "
                f"row selected (has a source id, current row, surface indices) {source_answers}")

    def n():
        with_table = _selection_script(_headless(without_table=False))
        without = _selection_script(_headless(without_table=True))
        differing = [a[0] for a, b in zip(with_table, without) if a != b]
        by_label = dict(without)
        return (len(with_table) == len(without) == 22 and differing == []
                and by_label["select [1, 2], focus 2"]["selection"] == ["row_1", "row_2"]
                and by_label["select [1, 2], focus 2"]["focus"] == "row_2"
                and by_label["commit"]["selection"] == ["row_2"] and by_label["commit"]["focus"] == ""
                and by_label["undo"]["focus"] != "" and by_label["duplicate"]["selection"] == ["row_4", "row_5"]
                and by_label["a source row"]["source"] and by_label["a source row"]["current"] is None
                and by_label["path view"]["selection"] and by_label["path view"]["rows"] == by_label["all paths"]["rows"]
                and by_label["delete"]["rows"] != by_label["undo the delete"]["rows"],
                f"{len(with_table)} steps with a Tk table and {len(without)} without: steps that differ {differing or 'none'}; "
                f"without a table -- selecting rows 1 and 2 leaves {by_label['select [1, 2], focus 2']['selection']} with the "
                f"focus on {by_label['select [1, 2], focus 2']['focus']!r}; a commit keeps the selection and loses the focus "
                f"item ({by_label['commit']['selection']}, {by_label['commit']['focus']!r}); undo gives one back "
                f"({by_label['undo']['focus']!r} -- WHICH row is bugs/0991's); duplicating rows 2 and 3 selects the copies "
                f"{by_label['duplicate']['selection']}; the path view selects {len(by_label['path view']['selection'])} rows")

    return _claims((("M", m), ("N", n)))


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import FIELDS, KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")
    editor.refresh_plot = lambda *a, **k: None
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    table = editor.table

    def settle(rounds: int = 8) -> None:
        for _ in range(rounds):
            editor.update()
            time.sleep(0.02)

    settle()

    def click(item: str, field: str, control: bool = False):
        x, y, w, h = table.bbox(item, f"#{FIELDS.index(field) + 1}")
        editor._on_table_click(SimpleNamespace(x=x + w // 2, y=y + h // 2, x_root=0, y_root=0, state=0x0004 if control else 0))
        settle()

    def claim_t():
        same_methods = (table.selection == editor._table_selection, table.selection_set == editor._set_table_selection,
                        table.selection_remove == editor._remove_from_table_selection)
        click("row_2", "thickness")
        click("row_4", "thickness", control=True)
        clicked = (table.selection(), editor._table_selection(), editor._table_focus_item(), table.focus())
        native_after_click = tuple(editor._native_table_selection())
        borders = len(editor._selection_border_overlays)

        table.selection_set("row_3")                     # as a Tk panel does (the context menu)
        table.focus("row_3")
        settle()
        through_widget = (editor._table_selection(), editor._table_focus_item(), editor._selected_table_indices(),
                          len(editor._selection_border_overlays), tuple(editor._native_table_selection()))

        editor._set_table_selection("row_5", "row_6")
        editor._set_table_focus_item("row_6")
        settle()
        through_model = (table.selection(), table.focus(), len(editor._selection_border_overlays),
                         tuple(editor._native_table_selection()))

        editor._native_table_selection_set("row_3")      # as the widget's own bindings would select a row
        settle()
        native_set = tuple(editor._native_table_selection())
        editor._set_table_selection("row_5")
        settle()
        native_cleared = (tuple(editor._native_table_selection()), table.selection())

        last = editor._table_cells().items()[-1]
        hidden = not table.bbox(last)
        editor._show_table_item(last)
        settle()
        shown = bool(table.bbox(last))
        editor._clear_table_selection()
        settle()
        cleared = (table.selection(), editor._table_focus_item(), len(editor._selection_border_overlays))
        return (same_methods == (True, True, True)
                and clicked == (("row_2", "row_4"), ("row_2", "row_4"), "row_4", "row_4") and native_after_click == ()
                and borders == 8 and through_widget == (("row_3",), "row_3", [3], 4, ())
                and through_model == (("row_5", "row_6"), "row_6", 4, ())
                and native_set == ("row_3",) and native_cleared == ((), ("row_5",))
                and hidden and shown and cleared == ((), "", 0),
                f"the Tk table's selection, selection_set and selection_remove are the model's: {same_methods}; a click and "
                f"a Control-click leave (the widget, the model, the model's focus item, the widget's) {clicked}, natively "
                f"selected {native_after_click}, {borders} border pieces; a Tk panel selecting and focusing row 3 on the WIDGET "
                f"leaves the model answering {through_widget[:3]} with {through_widget[3]} border pieces; rows 5 and 6 "
                f"selected through the MODEL leave the widget answering {through_model[:2]}, {through_model[2]} border "
                f"pieces, natively selected {through_model[3]}; a row the widget selects natively {native_set} is "
                f"un-selected there by the next change (natively, the selection) {native_cleared}; the last row was out of "
                f"sight ({hidden}) and is brought "
                f"into view ({shown}); cleared {cleared}")

    return _claims((("T", claim_t),))


def _run(call: str, claim: str, needs_display: bool) -> list:
    driver = (
        "import json, os\n"
        + ("if not os.environ.get('DISPLAY'):\n"
           f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
           "    raise SystemExit(0)\n" if needs_display else "")
        + "from KrakenOS.UI.validate_table_selection_model import model_checks, tk_checks\n"
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
    rows += _run("model_checks()", "M", False) + _run("tk_checks()", "T", True)
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
