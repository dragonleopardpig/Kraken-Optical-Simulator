"""Guard for bugs/0972: the Layouts / Machine Vision / Examples / Common Component menus are model data.

The Tk menu bar fills four menus from what is on disk: the common layouts by category, the
machine-vision layouts, the examples (with the Zemax prescriptions as a tree of folders), and the
common components that can be inserted. That was `tk.Menu` code inside a service -- and the Qt shell
had NONE of the four: 132 layouts, 23 machine-vision layouts and some 400 examples and Zemax files
could be opened there only through the file chooser. (Menu parity, phase 718, counts the menu bar's
fixed commands, so it never saw them.)

`editor.selector_menu(kind)` is the menu as data now; the Tk menu bar and four ribbon buttons both
show it.

  P  the model, no display, on a small made-up library:
       P1 layouts: a submenu per category in the declared order, a category not declared after
          them, an empty category left out; with no layouts ONE disabled line
       P2 examples: the categories, then a separator, then the Zemax prescriptions as a tree --
          folders before files, "Top Level" (the loose files) first, both alphabetical without
          regard to case; no separator without one side; with nothing at all ONE disabled line
       P3 machine vision and common components: a flat list, or ONE disabled line; an unknown menu
          is refused
       P4 an entry's command is the model's own loader, with the right argument, for each of the
          four kinds of entry
  T  a real Tk editor: each of its four menus shows exactly the model's menu; a name added to the
     library appears after a refresh, and an emptied list is one DISABLED line; a real menu entry
     loads its layout
  Q  a real Qt shell: the ribbon has the four buttons (three under File > Library, one under
     Surfaces > Catalogs), each with an icon; opened, each shows exactly the model's menu -- as it
     is NOW, so a name added since the last opening is there; a real entry loads its layout with the
     table and the title following and no Tk window; a common component is inserted into the rows;
     and the window is no wider than before
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SELECTORMENUS_RESULT "
SKIP_MARK = "SELECTORMENUS_SKIP "


def _count(outline) -> int:
    return sum(_count(row[3]) if row[0] == "cascade" else (0 if row[0] == "separator" else 1) for row in outline)


def pure_checks() -> list:
    from types import SimpleNamespace

    import KrakenOS.UI.layout_editor  # noqa: F401  (hands the service module its constants)
    from KrakenOS.UI.services import layout_shell_controls as module
    from KrakenOS.UI.services.layout_shell_controls import LayoutShellControlsMixin as Model

    order = list(module.LAYOUT_CATEGORY_ORDER)
    example_order = list(module.EXAMPLE_CATEGORY_ORDER)
    root = Path(module.ZEMAX_ATTACHMENT_DIR)
    ran: list = []

    def owner(**lists):
        fake = SimpleNamespace(
            layout_names=[], machine_vision_names=[], example_names=[], zemax_example_files={},
            _layout_menu_category=lambda name: name.split("/")[0],
            _example_menu_category=lambda name: name.split("/")[0],
            _insertable_common_layout_names=lambda: [],
            load_layout_by_name=lambda value: ran.append(("layout", value)),
            load_example_by_name=lambda value: ran.append(("example", value)),
            load_zemax_example_file=lambda value: ran.append(("zemax", value)),
            insert_layout_component_by_name=lambda value: ran.append(("insert", value)),
        )
        fake._fill_category_menu = Model._fill_category_menu
        fake._zemax_example_tree = lambda: Model._zemax_example_tree(fake)
        fake._fill_zemax_tree_menu = lambda menu, node: Model._fill_zemax_tree_menu(fake, menu, node)
        for key, value in lists.items():
            setattr(fake, key, value)
        return fake

    rows = []
    # ---- P1
    library = owner(layout_names=[f"{order[1]}/b", "Not Declared/z", f"{order[0]}/a", f"{order[1]}/c"])
    layouts = Model.selector_menu(library, "layouts").outline()
    empty = Model.selector_menu(owner(), "layouts").outline()
    rows.append(["P1", [row[:2] for row in layouts] == [("cascade", order[0]), ("cascade", order[1]), ("cascade", "Not Declared")]
                 and [entry[1] for entry in layouts[1][3]] == [f"{order[1]}/b", f"{order[1]}/c"]
                 and len(layouts) == 3 and empty == [("command", "No common layouts found", False)],
                 f"four layouts in three categories give submenus {[row[1] for row in layouts]} (declared order "
                 f"{order[:2]}..., the undeclared one last), the second holding {[entry[1] for entry in layouts[1][3]]}; no "
                 f"layouts: {empty}"])

    # ---- P2
    files = {"b.zmx": root / "b.zmx", "Zeta/x.zmx": root / "Zeta" / "x.zmx", "alpha/B.zmx": root / "alpha" / "B.zmx",
             "alpha/a.zmx": root / "alpha" / "a.zmx", "alpha/deep/q.zmx": root / "alpha" / "deep" / "q.zmx", "A.zmx": root / "A.zmx"}
    examples = Model.selector_menu(owner(example_names=[f"{example_order[0]}/e"], zemax_example_files=files), "examples").outline()
    tree = examples[2][3] if len(examples) == 3 else []
    only_examples = Model.selector_menu(owner(example_names=[f"{example_order[0]}/e"]), "examples").outline()
    only_zemax = Model.selector_menu(owner(zemax_example_files={"A.zmx": root / "A.zmx"}), "examples").outline()
    nothing = Model.selector_menu(owner(), "examples").outline()
    alpha = next((row for row in tree if row[1] == "alpha"), ("", "", True, []))
    rows.append(["P2", [row[0] for row in examples] == ["cascade", "separator", "cascade"]
                 and examples[2][1] == "Zemax Prescriptions (attachment)"
                 and [row[1] for row in tree] == ["Top Level", "alpha", "Zeta"]
                 and [entry[1] for entry in tree[0][3]] == ["A.zmx", "b.zmx"]
                 and [(entry[0], entry[1]) for entry in alpha[3]] == [("cascade", "deep"), ("command", "a.zmx"), ("command", "B.zmx")]
                 and [row[0] for row in only_examples] == ["cascade"] and [row[0] for row in only_zemax] == ["cascade"]
                 and nothing == [("command", "No examples found", False)],
                 f"examples then Zemax: {[row[0] for row in examples]}; the tree's folders {[row[1] for row in tree]}, "
                 f"Top Level holding {[entry[1] for entry in tree[0][3]] if tree else None}, 'alpha' holding "
                 f"{[(entry[0], entry[1]) for entry in alpha[3]]}; examples only {[row[0] for row in only_examples]}, Zemax "
                 f"only {[row[0] for row in only_zemax]}, nothing {nothing}"])

    # ---- P3
    vision = Model.selector_menu(owner(machine_vision_names=["MV one", "MV two"]), "machine_vision").outline()
    no_vision = Model.selector_menu(owner(), "machine_vision").outline()
    insertable = owner()
    insertable._insertable_common_layout_names = lambda: ["Single Lens", "Flat Mirror"]
    components = Model.selector_menu(insertable, "insert_component").outline()
    no_components = Model.selector_menu(owner(), "insert_component").outline()
    try:
        Model.selector_menu(owner(), "recent files")
        refused = ""
    except KeyError as exc:
        refused = str(exc)
    rows.append(["P3", vision == [("command", "MV one", True), ("command", "MV two", True)]
                 and no_vision == [("command", "No machine-vision layouts found", False)]
                 and components == [("command", "Single Lens", True), ("command", "Flat Mirror", True)]
                 and no_components == [("command", "No insertable common components found", False)]
                 and "recent files" in refused and Model.SELECTOR_MENUS == ("layouts", "machine_vision", "examples", "insert_component"),
                 f"machine vision {[row[1] for row in vision]} / {no_vision[0][1]!r}; components "
                 f"{[row[1] for row in components]} / {no_components[0][1]!r}; an unknown menu: {refused}"])

    # ---- P4
    del ran[:]
    full = owner(layout_names=[f"{order[0]}/a"], machine_vision_names=["MV one"], example_names=[f"{example_order[0]}/e"],
                 zemax_example_files={"alpha/a.zmx": root / "alpha" / "a.zmx"})
    full._insertable_common_layout_names = lambda: ["Single Lens"]
    menu = Model.selector_menu(full, "layouts")
    menu.entries[0].submenu.invoke(0)
    Model.selector_menu(full, "machine_vision").invoke(0)
    examples_menu = Model.selector_menu(full, "examples")
    examples_menu.entries[0].submenu.invoke(0)
    examples_menu.entries[2].submenu.entries[0].submenu.invoke(0)
    Model.selector_menu(full, "insert_component").invoke(0)
    rows.append(["P4", ran == [("layout", f"{order[0]}/a"), ("layout", "MV one"), ("example", f"{example_order[0]}/e"),
                               ("zemax", root / "alpha" / "a.zmx"), ("insert", "Single Lens")],
                 f"running a layout, a machine-vision layout, an example, a Zemax file and a component called "
                 f"{[(kind, Path(str(value)).name) for kind, value in ran]}"])
    return rows


def tk_checks() -> list:
    from KrakenOS.UI.context_menu import tk_menu_outline
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()
    targets = {"layouts": editor.layout_menu, "machine_vision": editor.machine_vision_menu,
               "examples": editor.example_menu, "insert_component": editor._insert_component_menu}
    same = {kind: tk_menu_outline(menu) == editor.selector_menu(kind).outline() for kind, menu in targets.items()}
    counts = {kind: _count(tk_menu_outline(menu)) for kind, menu in targets.items()}
    # the library grows: after a refresh the Tk menu has the new name
    editor.machine_vision_names = list(editor.machine_vision_names) + ["Machine Vision added by the guard"]
    editor._refresh_selector_menus()
    for _ in range(2):
        editor.update()
    grown = [row[1] for row in tk_menu_outline(editor.machine_vision_menu)]
    kept_names = editor.machine_vision_names[:-1]
    editor.machine_vision_names = []
    editor._refresh_selector_menus()
    for _ in range(2):
        editor.update()
    emptied = tk_menu_outline(editor.machine_vision_menu)
    editor.machine_vision_names = kept_names
    editor._refresh_selector_menus()
    # a real menu entry loads its layout
    category = editor.layout_menu.nametowidget(editor.layout_menu.entrycget(0, "menu"))
    label = category.entrycget(0, "label")
    rows_before = len(editor.rows)
    category.invoke(0)
    for _ in range(3):
        editor.update()
    loaded = (Path(str(editor.current_layout_file or "")).name, len(editor.rows))
    return [["T", all(same.values()) and counts["layouts"] >= 100 and counts["machine_vision"] >= 6
             and counts["examples"] >= 30 and counts["insert_component"] >= 1
             and grown[-1] == "Machine Vision added by the guard"
             and emptied == [("command", "No machine-vision layouts found", False)]
             and loaded[0].endswith(".py") and loaded[1] > 2 and loaded[1] != rows_before,
             f"each Tk menu shows the model's menu: {same}; entries {counts}; a name added to the library is the last "
             f"entry after a refresh: {grown[-1]!r}; with none, the menu is {emptied}; the real entry {label!r} "
             f"loaded {loaded[0]} ({rows_before} -> "
             f"{loaded[1]} rows)"]]


def qt_checks() -> list:
    import time
    import tkinter as tk

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.inspector_view import qmenu_outline
    from KrakenOS.UI.qt.ribbon import MODEL_MENUS, ribbon_entries

    app, window = build(["guard"])
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    window.build_scene()
    window.refresh_from_model()

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    settle(1.5)
    editor, ribbon = window.editor, window.ribbon
    placed = {name: (tab, group) for tab, group, name, _size, _label in ribbon_entries() if name in MODEL_MENUS}
    built = sorted(ribbon.model_menus)
    icons = {name: not button.icon().isNull() for name, button in ribbon.model_menus.items()}

    def opened(name):
        menu = ribbon.model_menus[name].menu()
        menu.aboutToShow.emit()                    # what opening the button's menu does
        return menu

    same = {kind: qmenu_outline(opened(name)) == editor.selector_menu(kind).outline() for name, (kind, _about) in MODEL_MENUS.items()}
    counts = {kind: _count(qmenu_outline(opened(name))) for name, (kind, _about) in MODEL_MENUS.items()}
    # never stale: a name added since the last opening is there at the next
    editor.machine_vision_names = list(editor.machine_vision_names) + ["Machine Vision added by the guard"]
    fresh = [action.text() for action in opened("model:machine_vision").actions()][-1]
    kept_names = editor.machine_vision_names[:-1]
    editor.machine_vision_names = []
    emptied = qmenu_outline(opened("model:machine_vision"))
    editor.machine_vision_names = kept_names

    tk_windows: list = []
    init = tk.Toplevel.__init__
    tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), tk_windows.append(type(self).__name__))[0]
    try:
        menu = opened("model:layouts")
        category = next(action for action in menu.actions() if action.menu() is not None)
        entry = category.menu().actions()[0]
        rows_before = len(editor.rows)
        entry.trigger()                            # the real menu entry
        settle(1.5)
        loaded = (Path(str(editor.current_layout_file or "")).name, len(editor.rows), window.rows_model.rowCount(),
                  window.windowTitle())
        component = opened("model:insert_component").actions()[0]
        rows_loaded = len(editor.rows)
        component.trigger()
        settle(1.5)
        inserted = (component.text(), len(editor.rows), window.rows_model.rowCount())
    finally:
        tk.Toplevel.__init__ = init
    width = window.minimumSizeHint().width()
    return [["Q", placed == {"model:layouts": ("File", "Library"), "model:machine_vision": ("File", "Library"),
                             "model:examples": ("File", "Library"), "model:insert_component": ("Surfaces", "Catalogs")}
             and built == sorted(MODEL_MENUS) and all(icons.values()) and all(same.values())
             and counts["layouts"] >= 100 and counts["machine_vision"] >= 6 and counts["examples"] >= 30
             and counts["insert_component"] >= 1 and fresh == "Machine Vision added by the guard"
             and emptied == [("command", "No machine-vision layouts found", False)]
             and loaded[0].endswith(".py") and loaded[1] > 2 and loaded[1] != rows_before and loaded[2] == loaded[1]
             and loaded[0] in loaded[3] and inserted[1] > rows_loaded and inserted[2] == inserted[1]
             and tk_windows == [] and width <= 1240,
             f"the ribbon places them {sorted(set(placed.values()))} and built {len(built)}, each with an icon: "
             f"{all(icons.values())}; opened, each shows the model's menu: {same}; entries {counts}; a name added since "
             f"the last opening is there: {fresh!r}; with none, the menu is {emptied}; the real entry "
             f"{category.text()!r} > {entry.text()!r} loaded "
             f"{loaded[0]} ({rows_before} -> {loaded[1]} rows, table {loaded[2]}, title {loaded[3]!r}); the component "
             f"{inserted[0]!r} took the rows {rows_loaded} -> {inserted[1]} (table {inserted[2]}); Tk windows "
             f"{tk_windows}; window minimum width {width} px"]]


def _run(call: str, needs: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_selector_menus import qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
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
    except Exception as exc:        # a claim that raises is a failed claim, not a lost run
        rows = [["P", False, f"raised {type(exc).__name__}: {exc}"]]
    rows += _run("tk_checks()", "", "T") + _run("qt_checks()", "import PySide6\n", "Q")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
