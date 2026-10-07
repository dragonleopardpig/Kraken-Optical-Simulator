"""Guard for bugs/0987: what the Tk surface table draws over its rows is a panel; the table service lets go of tkinter.

Phase 7d of the Qt migration, the last module. `services/layout_table_workbench.py` held the Tk
table's drawing code -- the border round the active cell and round each block of selected rows,
the grid lines, the "V" marker of an optimization variable, the entry a cell is edited in, the
choice menu of a Surface or Material cell -- and the Tk Edit menu's Undo / Redo states. It named
tkinter sixteen times through globals the editor copies into it, and loaded it when imported.

The drawing is `panels/main_surface_table_overlays.py` now; the two menu methods joined
`panels/main_popup_helpers.py`; the Edit menu's states are `panels/main_window.py`'s. The model
keeps WHICH rows are selected, which cell is active, which cells are variables, what a committed
edit does, and whether there is anything to undo.

The panel forwards every attribute it sets to the editor, and the moved code read the editor's
`__dict__` in two places: a move that got either wrong would draw nothing, or never clear what it
drew. So the Tk claims are about what is ON the table, measured against the table's own cells.

  S  the service imports nothing from `widgets` and names no tkinter at run time; the mixin has
     none of the fifteen moved methods; the three panels define them; the editor delegates each;
     the one question that named `messagebox.NO` passes the same value, "no"
  L  asked of the interpreter, in a fresh process: importing the service loads no tkinter
  M  the model, no display: the undo state is told to the Tk view and to a shell's seam alike, as
     two booleans; a selection change is scheduled once through the host, and a host that cannot
     schedule leaves nothing pending and raises nothing
  G  a real Tk editor: a separator sits on the right edge of every visible column but the last, a
     line under every visible row; each variable cell carries a "V" inside its right edge, and a
     click on one makes that cell the active one; re-drawing replaces the overlays instead of
     piling them up
  B  each block of selected rows is outlined across the table's width, and deselecting destroys
     the outlines; the active cell is outlined exactly; a row that is gone is forgotten ON THE
     EDITOR and its outline hidden; a scheduled re-draw is pending on the editor, is not scheduled
     twice, and is cleared once it has run
  E  double-click editing: the entry sits exactly on the cell, inside the table, holding the
     cell's value; a typed value and Return reach the model's row and the table; Escape leaves both
     as they were
  C  the Surface and Material cells post a Tk menu owned by the editor, at the pointer, listing
     the model's choices; choosing a material changes the row; a poster installed on the editor
     receives the menu instead of Tk
  U  the Tk Edit menu's Undo and Redo follow the history, and a shell's seam is told the same
  X  scrolling: the handlers move the scrollbar and the view, the active cell's outline follows
     the cell, and a grid re-draw is scheduled
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "TABLEOVERLAYS_RESULT "
SKIP_MARK = "TABLEOVERLAYS_SKIP "
ROOT = Path("KrakenOS/UI")
SERVICE = ROOT / "services/layout_table_workbench.py"
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
OVERLAY_METHODS = ("_hide_active_cell_border", "_clear_selection_row_borders", "_update_selection_row_borders",
                   "_update_active_cell_border", "_schedule_active_cell_border_update", "_on_table_scroll", "_on_table_xview",
                   "_on_table_xscroll", "_clear_table_grid", "_table_grid_context", "_schedule_table_grid_update",
                   "_update_table_grid", "_draw_optimization_cell_markers")
MENU_METHODS = ("_show_choice_menu", "_post_popup_menu")
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog", "place_commit_cell_entry", "bind_entry_commit"}
GRID_COLOR, SELECTION_COLOR, ACTIVE_COLOR = "#e2e7ef", "#2563eb", "#4a89ff"


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def _fresh(code: str) -> str:
    """The last line a fresh interpreter prints for ``code``."""
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=300, cwd=str(Path.cwd()))
    return (done.stdout.strip().splitlines() or ["ERROR " + done.stderr.strip()[-300:]])[-1]


def runtime_tk_names(path: Path) -> list:
    """(line, name) of every tkinter name ``path`` uses at run time -- annotations are not run."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    annotations: set = set()
    for node in ast.walk(tree):
        parts = []
        if isinstance(node, (ast.arg, ast.AnnAssign)) and node.annotation is not None:
            parts.append(node.annotation)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            parts.append(node.returns)
        for part in parts:
            annotations |= {id(inner) for inner in ast.walk(part)}
    return sorted((node.lineno, node.id) for node in ast.walk(tree)
                  if isinstance(node, ast.Name) and node.id in TK_NAMES and id(node) not in annotations)


def pure_checks() -> list:
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin as Model

    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_popup_helpers import MainPopupHelpers
        from KrakenOS.UI.panels.main_surface_table_overlays import MainSurfaceTableOverlays
        from KrakenOS.UI.panels.main_window import MainWindowBuilder

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        from_widgets = sorted({node.lineno for node in ast.walk(tree)
                               if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("KrakenOS.UI.widgets")})
        named = runtime_tk_names(SERVICE)
        moved = OVERLAY_METHODS + MENU_METHODS
        still = [name for name in moved if name in vars(Model)]
        on_panel = [name for name in OVERLAY_METHODS + ("_place_cell_editor",) if name not in vars(MainSurfaceTableOverlays)]
        on_popup = [name for name in MENU_METHODS if name not in vars(MainPopupHelpers)]
        homes = {**{name: "_main_surface_table_overlays" for name in OVERLAY_METHODS + ("_place_cell_editor",)},
                 **{name: "_main_popup_helpers" for name in MENU_METHODS}, "_show_tk_undo_state": "_main_window_builder"}
        import tkinter.messagebox as tk_messagebox

        source = SERVICE.read_text(encoding="utf-8")
        same_default = (tk_messagebox.NO == "no", source.count('default="no",'))
        undelegated = [name for name, factory in homes.items()
                       if name not in vars(KrakenLayoutEditor)
                       or f"self.{factory}().{name}(" not in inspect.getsource(vars(KrakenLayoutEditor)[name])]
        return (from_widgets == [] and named == [] and still == [] and on_panel == [] and on_popup == []
                and "_show_tk_undo_state" in vars(MainWindowBuilder) and undelegated == [] and len(homes) == 17
                and same_default == (True, 1),
                f"{SERVICE.name}: imports from widgets at lines {from_widgets or 'none'}, tkinter names at run time "
                f"{named or 'none'}; of the {len(moved)} moved methods still on the model: {still or 'none'}; missing from the "
                f"overlays panel: {on_panel or 'none'}, from the popup helpers: {on_popup or 'none'}; the window builder shows "
                f"the undo state: {'_show_tk_undo_state' in vars(MainWindowBuilder)}; of {len(homes)} editor delegations "
                f"missing or pointing elsewhere: {undelegated or 'none'}; the question's default (tkinter's NO is \"no\", "
                f"times it is passed as that): {same_default}")

    def l():
        answer = _fresh("import sys\nimport KrakenOS.UI.services.layout_table_workbench\nprint('tkinter' in sys.modules)\n")
        return answer == "False", f"importing the table service in a fresh process loads tkinter: {answer}"

    def m():
        from KrakenOS.UI.uihost import UiHost

        told: dict = {}
        for name, (undo, redo) in {"none": ([], []), "undo": ([1], []), "both": ([1], [1]), "redo": ([], [1])}.items():
            tk_view, shell = [], []
            owner = SimpleNamespace(_undo_stack=undo, _redo_stack=redo, _show_tk_undo_state=lambda *a: tk_view.append(a),
                                    show_undo_state=lambda *a: shell.append(a))
            Model._update_undo_redo_buttons(owner)
            told[name] = (tk_view, shell)
        tk_only = []
        Model._update_undo_redo_buttons(SimpleNamespace(_undo_stack=[1], _redo_stack=[], _show_tk_undo_state=lambda *a: tk_only.append(a)))
        expected = {"none": (False, False), "undo": (True, False), "both": (True, True), "redo": (False, True)}
        undo_ok = all(told[name] == ([state], [state]) for name, state in expected.items()) and tk_only == [(True, False)]

        class Host(UiHost):
            def __init__(self, fail: bool = False) -> None:
                self.fail, self.scheduled = fail, []

            def after_idle(self, func, *args):
                if self.fail:
                    raise RuntimeError("the window is gone")
                self.scheduled.append(func)
                return f"idle#{len(self.scheduled)}"

        emit = lambda: None
        good = SimpleNamespace(ui=Host(), _table_selection_after_id=None, _emit_custom_table_selection_changed=emit)
        Model._schedule_custom_table_selection_changed(good)
        first = good._table_selection_after_id
        Model._schedule_custom_table_selection_changed(good)
        gone = SimpleNamespace(ui=Host(fail=True), _table_selection_after_id=None, _emit_custom_table_selection_changed=emit)
        Model._schedule_custom_table_selection_changed(gone)
        schedule_ok = (first == "idle#1" and good._table_selection_after_id == "idle#1" and good.ui.scheduled == [emit]
                       and gone._table_selection_after_id is None)
        return (undo_ok and schedule_ok,
                f"the undo state told to (the Tk view, the shell): {told}; with no shell the Tk view alone: {tk_only}; a "
                f"selection change is scheduled as {first!r}, {len(good.ui.scheduled)} time for two requests; a host that cannot "
                f"schedule leaves {gone._table_selection_after_id!r} pending")

    return _claims((("S", s), ("L", l), ("M", m)))


def tk_checks() -> list:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import (FIELDS, OPTIMIZATION_CELL_MARKER_BG, OPTIMIZATION_CELL_MARKER_TEXT, SURFACE_TYPES,
                                           KrakenLayoutEditor)
    from KrakenOS.UI.services.layout_table_workbench import TABLE_GLASS_CHOICES

    editor = KrakenLayoutEditor()
    editor.geometry("1700x950+0+0")
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)
    editor.refresh_plot = lambda *a, **k: None          # a committed cell asks for a re-plot: not this guard's subject
    table = editor.table

    def settle(rounds: int = 10) -> None:
        for _ in range(rounds):
            editor.update()
            time.sleep(0.03)

    settle()
    marked = {id(editor.rows[3]): ("rc", "thickness"), id(editor.rows[5]): ("thickness",)}
    editor._optimization_marker_fields_for_row = lambda row: marked.get(id(row), ())

    def column(field: str) -> str:
        return f"#{FIELDS.index(field) + 1}"

    def item_of(row_index: int) -> str:
        return editor._table_item_for_row_index(row_index)

    def box(widget) -> tuple:
        return (int(widget.winfo_x()), int(widget.winfo_y()), int(widget.winfo_x()) + int(widget.winfo_width()),
                int(widget.winfo_y()) + int(widget.winfo_height()))

    def outline(widgets) -> tuple:
        boxes = [box(widget) for widget in widgets]
        return (min(b[0] for b in boxes), min(b[1] for b in boxes), max(b[2] for b in boxes), max(b[3] for b in boxes))

    def cell(item: str, field: str) -> tuple:
        x, y, w, h = table.bbox(item, column(field))
        return (x, y, x + w, y + h)

    def overlays(kind: str, color: str) -> list:
        return [w for w in table.winfo_children() if w.winfo_class() == kind and str(w.cget("bg")) == color and w.place_info()]

    def cell_event(item: str, field: str):
        x0, y0, x1, y1 = cell(item, field)
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        return SimpleNamespace(x=cx, y=cy, x_root=table.winfo_rootx() + cx, y_root=table.winfo_rooty() + cy)

    def claim_g():
        editor._update_table_grid()
        settle()
        names = list(table["columns"])
        items = list(table.get_children())
        visible = [item for item in items if any(table.bbox(item, f"#{i}") for i in range(1, len(names) + 1))]
        first = visible[0]
        edges = sorted(table.bbox(first, f"#{i}")[0] + table.bbox(first, f"#{i}")[2] - 1
                       for i in range(1, len(names)) if table.bbox(first, f"#{i}"))
        row_bottoms = sorted(next(table.bbox(item, f"#{i}") for i in range(1, len(names) + 1) if table.bbox(item, f"#{i}"))
                             for item in visible)
        bottoms = sorted(b[1] + b[3] - 1 for b in row_bottoms)
        data_top, data_bottom = min(b[1] for b in row_bottoms), max(b[1] + b[3] for b in row_bottoms)
        grid = overlays("Frame", GRID_COLOR)
        separators = [w for w in grid if int(w.winfo_width()) == 1]
        lines = [w for w in grid if int(w.winfo_height()) == 1 and w not in separators]
        sep_ok = (sorted(int(w.winfo_x()) for w in separators) == edges and len(edges) >= 5
                  and all((int(w.winfo_y()), int(w.winfo_y()) + int(w.winfo_height())) == (data_top, data_bottom) for w in separators))
        line_ok = (sorted(int(w.winfo_y()) for w in lines) == bottoms and len(bottoms) >= 8
                   and all(int(w.winfo_width()) == int(table.winfo_width()) for w in lines))

        markers = overlays("Label", OPTIMIZATION_CELL_MARKER_BG)
        wanted = {(item_of(3), "rc"), (item_of(3), "thickness"), (item_of(5), "thickness")}
        placed = set()
        for marker in markers:
            mx0, my0, mx1, my1 = box(marker)
            for item, field in wanted:
                cx0, cy0, cx1, cy1 = cell(item, field)
                if cx0 < mx0 and mx1 == cx1 - 1 and cy0 <= my0 and my1 <= cy1 and 16 <= mx1 - mx0 <= 24:
                    placed.add((item, field))
        texts = sorted({str(marker.cget("text")) for marker in markers})
        marker_ok = len(markers) == 3 and placed == wanted and texts == [OPTIMIZATION_CELL_MARKER_TEXT]

        target = next(marker for marker in markers if cell(item_of(5), "thickness")[0] < box(marker)[0] < cell(item_of(5), "thickness")[2]
                      and cell(item_of(5), "thickness")[1] <= box(marker)[1] < cell(item_of(5), "thickness")[3])
        editor._active_cell = None
        target.event_generate("<Button-1>")
        settle(4)
        clicked = editor._active_cell

        old = list(editor._grid_overlays)
        editor._update_table_grid()
        settle()
        replaced = (len(old) == len(grid) + len(markers), len(editor._grid_overlays) == len(old),
                    not any(bool(widget.winfo_exists()) for widget in old))
        return (sep_ok and line_ok and marker_ok and clicked == (item_of(5), column("thickness")) and replaced == (True, True, True),
                f"{len(separators)} separators on the right edges of the {len(edges)} visible columns but the last: {sep_ok}; "
                f"{len(lines)} lines under the {len(bottoms)} visible rows, across the table: {line_ok}; {len(markers)} markers "
                f"{texts} inside the right edge of their cells {sorted(field for _i, field in placed)}: {marker_ok}; a click on "
                f"one makes its cell active: {clicked == (item_of(5), column('thickness'))}; re-drawing (the editor's list held "
                f"all {len(old)}, holds as many again, the old widgets are gone): {replaced}")

    def claim_b():
        editor._select_tk_table_indices([2, 3, 6])
        settle()
        width = int(table.winfo_width())
        frames = overlays("Frame", SELECTION_COLOR)
        blocks = [(item_of(2), item_of(3)), (item_of(6), item_of(6))]
        outlined = []
        for first, last in blocks:
            top, bottom = table.bbox(first, column("thickness"))[1], sum(table.bbox(last, column("thickness"))[i] for i in (1, 3))
            mine = [w for w in frames if top <= int(w.winfo_y()) < bottom]
            outlined.append(len(mine) == 4 and outline(mine) == (0, top, width, bottom)
                            and all(min(int(w.winfo_width()), int(w.winfo_height())) == 2 for w in mine))
        on_editor = len(editor._selection_border_overlays)
        editor._clear_table_selection()
        settle()
        cleared = (len(overlays("Frame", SELECTION_COLOR)), len(editor._selection_border_overlays),
                   any(bool(w.winfo_exists()) for w in frames))

        item = item_of(3)
        editor._active_cell = (item, column("thickness"))
        editor._update_active_cell_border()
        settle(4)
        active = outline(editor._cell_border_parts) == cell(item, "thickness") and len(overlays("Frame", ACTIVE_COLOR)) == 4

        editor._active_cell = ("no-such-row", "#3")
        editor._update_active_cell_border()
        forgotten = (editor._active_cell, [bool(part.place_info()) for part in editor._cell_border_parts])

        settle()
        editor._active_cell_border_after_id = None
        editor._schedule_active_cell_border_update()
        pending = editor._active_cell_border_after_id
        editor._schedule_active_cell_border_update()
        same = editor._active_cell_border_after_id
        editor._grid_after_id = None
        editor._schedule_table_grid_update()
        grid_pending = editor._grid_after_id
        settle()
        ran = (editor._active_cell_border_after_id, editor._grid_after_id)
        return (len(frames) == 8 and outlined == [True, True] and on_editor == 8 and cleared == (0, 0, False) and active
                and forgotten == (None, [False, False, False, False]) and pending is not None and same == pending
                and grid_pending is not None and ran == (None, None),
                f"{len(frames)} outline pieces for 2 blocks of selected rows, each block outlined across the table: {outlined}; "
                f"the editor held {on_editor}; after deselecting (pieces on the table, on the editor, any still alive): "
                f"{cleared}; the active cell is outlined exactly: {active}; a row that is gone leaves the editor's active cell "
                f"{forgotten[0]} and the outline placed {forgotten[1]}; a scheduled outline is pending on the editor "
                f"({pending is not None}), not scheduled twice ({same == pending}), a grid re-draw too "
                f"({grid_pending is not None}), and both are cleared once run: {ran}")

    def claim_e():
        item = item_of(3)
        row = editor.rows[3]
        before = float(row.thickness)
        shown = str(table.set(item, "thickness"))
        editor.begin_edit(cell_event(item, "thickness"))
        settle(4)
        entry = editor.editor
        placed = (entry.master is table, box(entry) == cell(item, "thickness"), str(entry.get()) == shown,
                  editor._editor_row_id == item, editor._editor_field)
        entry.delete(0, "end")
        entry.insert(0, "7.25")
        entry.focus_force()
        settle(4)
        entry.event_generate("<Return>")
        settle()
        item = item_of(3)
        committed = (float(editor.rows[3].thickness), str(table.set(item, "thickness")), editor.editor is None)

        editor.begin_edit(cell_event(item, "thickness"))
        settle(4)
        entry = editor.editor
        entry.delete(0, "end")
        entry.insert(0, "99")
        entry.focus_force()
        settle(4)
        entry.event_generate("<Escape>")
        settle()
        cancelled = (float(editor.rows[3].thickness), str(table.set(item_of(3), "thickness")), editor.editor is None,
                     editor._editor_row_id, editor._editor_field)
        editor.commit_cell(3, "thickness", repr(before))
        settle(4)
        restored = float(editor.rows[3].thickness) == before
        return (placed == (True, True, True, True, "thickness") and before != 7.25 and committed == (7.25, "7.25", True)
                and cancelled == (7.25, "7.25", True, None, None) and restored,
                f"the entry (inside the table, exactly on the cell, holding {shown!r}, for that row, field): {placed}; typing "
                f"7.25 and Return leaves (the model's row, the table, the entry gone) {committed}, from {before}; typing 99 and "
                f"Escape leaves {cancelled}; put back: {restored}")

    def claim_c():
        item = item_of(3)
        posted: list = []
        popup, tk.Menu.tk_popup = tk.Menu.tk_popup, lambda self, x, y, entry="": posted.append((int(x), int(y)))
        try:
            event = cell_event(item, "surface")
            editor.begin_edit(event)
            menu = editor.popup_menu
            labels = [str(menu.entrycget(index, "label")) for index in range((menu.index("end") or 0) + 1)]
            surface = (isinstance(menu, tk.Menu), menu.master is editor, int(menu.cget("tearoff")), labels == list(SURFACE_TYPES),
                       posted[-1:] == [(event.x_root, event.y_root)])
            editor._cleanup_current_popup_menu()

            before = str(editor.rows[3].glass)
            other = next(glass for glass in TABLE_GLASS_CHOICES if glass not in (before, "AIR", "NA", "MIRROR"))
            editor.begin_edit(cell_event(item, "glass"))
            menu = editor.popup_menu
            glasses = [str(menu.entrycget(index, "label")) for index in range((menu.index("end") or 0) + 1)]
            menu.invoke(list(TABLE_GLASS_CHOICES).index(other))
            settle(4)
            chosen = str(editor.rows[3].glass)
            editor.commit_cell(3, "glass", before)
            settle(4)
            restored = str(editor.rows[3].glass) == before

            received: list = []
            count = len(posted)
            editor._post_popup_menu = lambda menu, x, y: received.append((type(menu).__name__, int(x), int(y)))
            try:
                event = cell_event(item_of(3), "surface")
                editor.begin_edit(event)
            finally:
                del editor._post_popup_menu
            through_editor = (received == [("Menu", event.x_root, event.y_root)], len(posted) == count)
            editor._cleanup_current_popup_menu()
        finally:
            tk.Menu.tk_popup = popup
        return (surface == (True, True, 0, True, True) and glasses == list(TABLE_GLASS_CHOICES) and chosen == other != before
                and restored and through_editor == (True, True),
                f"the Surface cell posts (a Tk menu, owned by the editor, tearoff, the {len(SURFACE_TYPES)} surface types, at "
                f"the pointer) {surface}; the Material cell lists the {len(glasses)} glass choices: "
                f"{glasses == list(TABLE_GLASS_CHOICES)}; choosing {other!r} leaves the row's material {chosen!r} (was "
                f"{before!r}, put back: {restored}); a poster installed on the editor (received the menu, Tk posted nothing): "
                f"{through_editor}")

    def claim_u():
        def states() -> list:
            return [str(editor._edit_menu.entrycget(label, "state")) for label in ("Undo", "Redo")]

        saved = list(editor._undo_stack), list(editor._redo_stack)
        told: list = []
        editor.show_undo_state = lambda *a: told.append(a)
        shown = {}
        try:
            for name, (undo, redo) in {"none": ([], []), "undo": ([object()], []), "both": ([object()], [object()])}.items():
                editor._undo_stack[:], editor._redo_stack[:] = undo, redo
                editor._update_undo_redo_buttons()
                shown[name] = states()
        finally:
            del editor.show_undo_state
            editor._undo_stack[:], editor._redo_stack[:] = saved
            editor._update_undo_redo_buttons()
        return (shown == {"none": ["disabled", "disabled"], "undo": ["normal", "disabled"], "both": ["normal", "normal"]}
                and told == [(False, False), (True, False), (True, True)],
                f"the Tk Edit menu's (Undo, Redo) with nothing, one step to undo, and one each way: {shown}; a shell's seam was "
                f"told {told}")

    def claim_x():
        item = item_of(3)
        editor._active_cell = (item, column("thickness"))
        editor._update_active_cell_border()
        settle(4)
        before = cell(item, "thickness")
        editor._on_table_xview("moveto", 0.15)
        settle()
        view = float(table.xview()[0])
        after = cell(item, "thickness")
        followed = outline(editor._cell_border_parts) == after
        calls: list = []
        bar = SimpleNamespace(set=lambda first, last: calls.append((first, last)))
        editor._grid_after_id = None
        editor._on_table_scroll(bar, "0.0", "0.5")
        scheduled = editor._grid_after_id is not None
        editor._on_table_xview("moveto", 0.0)
        editor._on_table_xscroll(bar, "0.1", "0.6")
        settle()
        back = outline(editor._cell_border_parts) == cell(item, "thickness") == before
        return (abs(view - 0.15) < 0.01 and after[0] < before[0] - 50 and followed and calls == [("0.0", "0.5"), ("0.1", "0.6")]
                and scheduled and back,
                f"moving the view to 0.15 leaves it at {view:.3f}; the cell went from x {before[0]} to {after[0]} and its outline "
                f"followed: {followed}; the scrollbar was set {calls}; a grid re-draw was scheduled: {scheduled}; back at 0 the "
                f"outline is on the cell again: {back}")

    return _claims((("G", claim_g), ("B", claim_b), ("E", claim_e), ("C", claim_c), ("U", claim_u), ("X", claim_x)))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_surface_table_overlays_view import tk_checks\n"
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
    rows += _run("tk_checks()", "G")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
