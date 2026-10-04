"""Guard for bugs/0948: the surface table's right-click menu is the model's own, in both shells.

The Tk table's menu has over a hundred commands in thirteen submenus (convert type, insert
component, shape, material, coating, geometry, element, diagnostics, advanced, solves); the Qt
table's had three. The Tk builder now fills whatever menu it is handed -- a `tk.Menu`, or a
recording `MenuModel` for a shell -- so the Qt table shows the same menu without a second
implementation. On the two-arm doublets example, for seven cells:

  B  the menu the REAL Tk right-click builds and the model a shell is handed have identical
     outlines (labels, enabled states, nesting): 100+ commands in 13 submenus each
  Q  a right-click on the Qt table shows a QMenu with exactly that outline -- the model's, and
     the Tk shell's for the same cell
  R  entries RUN from the Qt menu: Convert Type -> Mirror changes the row in the model and in
     the Qt table (Undo restores it); Coating / Material Editor opens a QT dialog; Select ... for
     optimization marks the cell; Set bounds opens its dialog and waits for it
  N  none of it creates a Tk window or calls a tkinter dialog
  E  EVERY entry: each distinct command of those menus (about 118), run once in a throwaway Qt
     shell with the layout reloaded before it and every question cancelled, raises nothing, calls no
     tkinter dialog and creates no Tk window -- reports included, which open in the Qt report
     dialog through the `show_report` seam -- except the entries in `KNOWN_TK_ENTRIES`, a list that
     may only shrink
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QTTABLEMENU_RESULT "
SKIP_MARK = "QTTABLEMENU_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")
#: (row, field): a lens thickness, the splitter's # column, the Object, the Image, a detector, a
#: glass cell, a lens's # column
CELLS = ((2, "thickness"), (1, "label"), (0, "thickness"), (11, "rc"), (6, "thickness"), (3, "glass"), (2, "label"))
LENS = 2
#: menu entries that still end in a Tk window -> why. An entry that stops doing so fails the guard
#: until it is deleted here, so this can only shrink.
KNOWN_TK_ENTRIES: dict = {}          # bugs/0955 gave the solve review windows a Qt dialog: none left


def _counts(outline) -> tuple[int, int]:
    commands = submenus = 0
    for entry in outline:
        if entry[0] == "cascade":
            inner = _counts(entry[3])
            commands, submenus = commands + inner[0], submenus + inner[1] + 1
        elif entry[0] != "separator":
            commands += 1
    return commands, submenus


def tk_runtime_checks() -> list:
    from KrakenOS.UI.context_menu import tk_menu_outline
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem)
    editor.refresh_plot()
    editor.update()
    captured: list = []
    editor._post_popup_menu = lambda menu, x, y: captured.append(menu)   # build it, do not post it
    builder = editor._main_context_menu()
    fields = list(builder.fields)
    shown: dict = {}
    differ: list = []
    for row_index, field in CELLS:
        row_id = editor._table_item_for_row_index(row_index)
        editor.table.see(row_id)
        editor.update()
        x, y, width, height = editor.table.bbox(row_id, f"#{fields.index(field) + 1}")
        event = type("Event", (), {"x": x + width // 2, "y": y + height // 2, "x_root": 100, "y_root": 100})()
        captured.clear()
        editor.table.selection_set(row_id)
        builder.show_context_menu(event)
        tk_outline = json.loads(json.dumps(tk_menu_outline(captured[0]))) if captured else None
        editor.table.selection_set(row_id)
        model = editor.table_cell_menu(row_index, field)
        model_outline = json.loads(json.dumps(model.outline())) if model is not None else None
        key = f"{row_index}:{field}"
        shown[key] = tk_outline
        if tk_outline is None or tk_outline != model_outline:
            differ.append(key)
    sizes = {key: _counts(outline or []) for key, outline in shown.items()}
    return [["B", not differ and all(commands >= 100 and submenus == 13 for commands, submenus in sizes.values()),
             f"{len(CELLS)} cells: the Tk menu and the shell's model differ for {differ}; (commands, submenus) "
             f"{sizes}"],
            ["_tk", True, json.dumps(shown)]]


def qt_runtime_checks() -> list:
    import tkinter as tk
    import tkinter.messagebox as tk_messagebox

    from PySide6.QtCore import QTimer

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.inspector_view import qmenu_outline

    tk_windows: list = []
    tk_dialogs: list = []
    tk_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        tk_init(self, *args, **kwargs)
        tk_windows.append(self)

    tk.Toplevel.__init__ = counting_init
    for name in ("showinfo", "showwarning", "showerror", "askyesno"):
        setattr(tk_messagebox, name, (lambda n: lambda *a, **_k: tk_dialogs.append(n))(name))
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(LAYOUT)
    window.action_manager["refresh_plot"].trigger()
    app.processEvents()
    editor, model, view = window.editor, window.rows_model, window.rows_view
    fields = [model.field(column) for column in range(model.columnCount())]

    def right_click(row: int, field: str):
        """What a right-click on that cell does: the view asks for its context menu there."""
        window.select_rows([row], row)
        rect = view.visualRect(model.index(row, fields.index(field)))
        view.customContextMenuRequested.emit(rect.center())
        app.processEvents()
        return window.last_cell_menu

    def entry(menu, *path):
        for depth, label in enumerate(path):
            action = next((a for a in menu.actions() if a.text().split("\t")[0].replace("&&", "&") == label), None)
            if action is None:
                return None
            if depth == len(path) - 1:
                return action
            menu = action.menu()
        return None

    rows: list = []
    shown: dict = {}
    differ: list = []
    for row, field in CELLS:
        menu = right_click(row, field)
        outline = json.loads(json.dumps(qmenu_outline(menu)))
        expected = json.loads(json.dumps(window.last_cell_menu_model.outline()))
        shown[f"{row}:{field}"] = outline
        if outline != expected:
            differ.append(f"{row}:{field}")
        menu.close()
    rows.append(["Q", not differ and all(_counts(o)[0] >= 100 for o in shown.values()),
                 f"{len(CELLS)} Qt right-clicks: menus differing from the model's {differ}; commands "
                 f"{[_counts(o)[0] for o in shown.values()]}"])

    # R -- entries run
    before = editor.rows[LENS].surface
    entry(right_click(LENS, "thickness"), "Convert Type", "Mirror").trigger()
    app.processEvents()
    converted = (editor.rows[LENS].surface, str(model.data(model.index(LENS, fields.index("surface")))))
    window.action_manager["undo"].trigger()
    app.processEvents()
    restored = editor.rows[LENS].surface

    previous = window.last_model_form_dialog
    entry(right_click(LENS, "thickness"), "Coating / Polarization", "Coating / Material Editor...").trigger()
    app.processEvents()
    coating = window.last_model_form_dialog
    coating_opened = coating is not None and coating is not previous and coating.isVisible()
    coating_title = coating.windowTitle() if coating_opened else ""
    if coating_opened:
        coating.close()

    solves = next(a.text() for a in entry(right_click(LENS, "thickness"), "Optimization / Solves").menu().actions()
                  if a.text().startswith("Select "))
    entry(window.last_cell_menu, "Optimization / Solves", solves).trigger()
    app.processEvents()
    marked = bool(editor.optimization_cell_state(LENS, "thickness")["marked"])

    state: dict = {"open": None}
    before_bounds = window.last_model_form_dialog

    def close_bounds() -> None:
        dialog = window.last_model_form_dialog
        state["open"] = dialog is not None and dialog is not before_bounds and dialog.isVisible()
        if state["open"]:
            dialog.reject()

    bounds_action = entry(right_click(LENS, "thickness"), "Optimization / Solves", "Set bounds...")
    QTimer.singleShot(0, close_bounds)
    bounds_action.trigger()
    app.processEvents()
    after_bounds = window.last_model_form_dialog
    waited = state["open"] is True and after_bounds is not before_bounds and not after_bounds.isVisible()
    rows.append(["R", before == "Standard" and converted == ("Mirror", "Mirror") and restored == before
                 and coating_opened and "coating" in coating_title.lower() and marked and waited,
                 f"Convert Type -> Mirror: row {LENS} {before!r} -> model/table {converted}, Undo -> {restored!r}; "
                 f"Coating editor opened a Qt dialog {coating_title!r}; {solves!r} marked the cell: {marked}; "
                 f"Set bounds was open during the command and closed after: {waited}"])
    rows.append(["N", not tk_windows and not tk_dialogs,
                 f"Tk windows {len(tk_windows)}, tkinter dialog calls {tk_dialogs}"])
    return rows + [["_qt", True, json.dumps(shown)]]


def _leaves(model, prefix=()):
    for entry in model.entries:
        if entry.kind == "cascade" and entry.submenu is not None:
            yield from _leaves(entry.submenu, prefix + (entry.label,))
        elif entry.kind != "separator" and entry.command is not None:
            yield prefix + (entry.label,), entry


def qt_every_entry_checks() -> list:
    import tkinter as tk
    import tkinter.filedialog as tk_filedialog
    import tkinter.messagebox as tk_messagebox
    import tkinter.simpledialog as tk_simpledialog
    import webbrowser

    from PySide6.QtWidgets import QApplication, QDialog

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of

    events: list = []
    tk_init = tk.Toplevel.__init__

    def counting_init(self, *args, **kwargs):
        tk_init(self, *args, **kwargs)
        events.append("TK-WINDOW")

    tk.Toplevel.__init__ = counting_init
    for module, names in ((tk_messagebox, ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel")),
                          (tk_simpledialog, ("askstring", "askinteger", "askfloat")),
                          (tk_filedialog, ("askopenfilename", "asksaveasfilename", "askdirectory"))):
        for name in names:
            setattr(module, name, lambda *a, **_k: events.append("TK-DIALOG"))
    webbrowser.open = lambda *a, **_k: True
    QDialog.exec = lambda self: 0                      # a form that waits returns at once
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    host = host_of(window)
    for name in ("showinfo", "showwarning", "showerror"):
        setattr(host, name, lambda *a, **_k: None)
    for name, cancel in (("askyesno", False), ("askokcancel", False), ("askyesnocancel", None), ("askstring", None),
                         ("askinteger", None), ("askfloat", None), ("askopenfilename", ""),
                         ("asksaveasfilename", ""), ("askdirectory", ""), ("askopenfilenames", ())):
        setattr(host, name, (lambda value: lambda *a, **_k: value)(cancel))
    editor = window.editor
    editor.wait_window = lambda _window: events.append("TK-WINDOW")
    window.load_layout_path(LAYOUT)
    window.action_manager["refresh_plot"].trigger()
    app.processEvents()
    # every distinct entry once, on a cell where it is enabled when there is one
    todo: dict = {}
    for row, field in CELLS:
        window.select_rows([row], row)
        for path, entry in _leaves(editor.table_cell_menu(row, field)):
            if path not in todo or (entry.enabled and not todo[path][2]):
                todo[path] = (row, field, entry.enabled)
    tk_ending: list = []
    raised: list = []
    ran = 0
    for path, (row, field, _enabled) in todo.items():
        window.load_layout_path(LAYOUT)
        window.select_rows([row], row)
        model = editor.table_cell_menu(row, field)
        owner = model
        for label in path[:-1]:
            owner = next(e.submenu for e in owner.entries if e.kind == "cascade" and e.label == label)
        entry = next((e for e in owner.entries if e.kind != "separator" and e.label == path[-1]), None)
        if entry is None or not entry.enabled:
            continue
        events.clear()
        before = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
        try:
            owner.run(entry)
        except Exception as exc:
            raised.append((" > ".join(path), f"{type(exc).__name__}: {str(exc)[:60]}"))
        app.processEvents()
        ran += 1
        for widget in QApplication.topLevelWidgets():
            if widget.isVisible() and id(widget) not in before and widget is not window:
                widget.close()
        if events:
            tk_ending.append(" > ".join(path))
    unexpected = sorted(set(tk_ending) - set(KNOWN_TK_ENTRIES))
    fixed = sorted(set(KNOWN_TK_ENTRIES) - set(tk_ending))
    return [["E", ran >= 100 and not unexpected and not fixed and not raised,
             f"{len(todo)} distinct entries, {ran} run (the rest disabled on this scene); ending in Tk and not "
             f"listed: {unexpected}; listed but no longer Tk (delete them): {fixed}; raised: {raised}; known Tk "
             f"entries: {sorted(KNOWN_TK_ENTRIES)}"]]


def _run(call: str) -> list:
    driver = (
        "import json, os\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_qt_table_context_menu import (qt_every_entry_checks, qt_runtime_checks,\n"
        "    tk_runtime_checks)\n"
        # flushed, then exit WITHOUT interpreter teardown (a Qt/Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return [["X", False, f"{call}: exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    tk_rows = _run("tk_runtime_checks()")
    qt_rows = _run("qt_runtime_checks()") + _run("qt_every_entry_checks()")
    tk_shown = next((json.loads(d) for k, _o, d in tk_rows if k == "_tk"), None)
    qt_shown = next((json.loads(d) for k, _o, d in qt_rows if k == "_qt"), None)
    rows = [r for r in tk_rows + qt_rows if not r[0].startswith("_")]
    if tk_shown is not None and qt_shown is not None:
        across = [key for key in tk_shown if tk_shown[key] != qt_shown.get(key)]
        for row in rows:
            if row[0] == "Q":
                row[1] = bool(row[1]) and not across
                row[2] += f"; cells where the Qt menu differs from the Tk shell's: {across}"
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
