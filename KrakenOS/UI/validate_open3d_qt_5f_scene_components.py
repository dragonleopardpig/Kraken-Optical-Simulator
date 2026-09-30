"""Phase 5f, part 3b guard (docs/design_qt_migration.md): the Scene Components browser reaches the
Qt shell from the Tk browser's own data, selection and menus.

  T  the Tk tree renders `tree_nodes()` exactly: every item's iid, parent and text, in order
  M  the browser's right-click menus are built through `new_context_menu` (a MenuModel under a
     shell) -- none is a direct tk.Menu, which a Qt shell could not show
  Q  in a real Qt shell on om05a_folded: the Scene Components dock shows the same nodes (iids and
     texts); a click on a surface row selects it in the browser AND the editor; its right-click
     opens a Qt menu built from the browser's own builder; Hide there tags the node hidden and the
     Qt item greys -- the browser's own refresh reaches the shell
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5F3B_RESULT "
SKIP_MARK = "QT5F3B_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def static_checks() -> list:
    from KrakenOS.UI.panels import open3d_step_admin

    source = inspect.getsource(open3d_step_admin)
    direct = source.count("tk.Menu(")
    routed = source.count("new_context_menu(")
    return [["M", direct == 0 and routed >= 4,
             f"browser menus through new_context_menu: {routed}; direct tk.Menu: {direct}"]]


def tk_checks() -> list:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor(headless=True)
    try:
        app.load_layout_by_name(SCENE.stem)
        inspector = _open_inspector(app)
        panel = inspector._open3d_step_admin_panel()
        panel.refresh()
        tree = panel._tree
        built = []

        def walk(parent: str) -> None:
            for iid in tree.get_children(parent):
                built.append((str(iid), parent, str(tree.item(iid, "text"))))
                walk(iid)

        walk("")
        nodes = [(n["iid"], n["parent"], n["text"]) for n in panel.tree_nodes()]
        return [["T", len(nodes) >= 10 and sorted(built) == sorted(nodes),
                 f"Tk tree items {len(built)} == tree_nodes {len(nodes)}: {sorted(built) == sorted(nodes)}"]]
    finally:
        try:
            app.destroy()
        except Exception:
            pass


def qt_runtime_checks() -> list:
    from KrakenOS.UI.qt.app import build

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    tree, insp = window.scene_components, view.inspector
    panel = tree.panel()
    nodes = panel.tree_nodes()
    same = [n["iid"] for n in nodes] == list(tree.items) and all(
        tree.items[n["iid"]].text(0) == n["text"] for n in nodes)
    target = next((iid for iid in tree.items if iid.startswith("scene-row:")), None)
    selected = editor_row = False
    labels, hidden, grey = [], False, ""
    if target is not None:
        tree.items[target].setSelected(True)
        tree.widget.setCurrentItem(tree.items[target])
        app.processEvents()
        row = int(target.split(":", 1)[1])
        selected = panel._selected_item_id == target
        editor_row = row in list(insp.editor._selected_table_indices())
        tree._context_menu(tree.widget.visualItemRect(tree.items[target]).center())
        app.processEvents()
        menu = view.last_menu
        labels = [a.text() for a in menu.actions() if a.text()] if menu is not None else []
        hide = next((a for a in menu.actions() if a.text().lower().startswith("hide")), None) if menu else None
        if hide is not None:
            hide.trigger()
            for _ in range(10):
                app.processEvents()
            hidden = "hidden" in next(n for n in panel.tree_nodes() if n["iid"] == target)["tags"]
            grey = tree.items[target].foreground(0).color().name()
        if menu is not None:
            menu.close()
    return [["Q", same and selected and editor_row and bool(labels) and hidden and grey == "#9a9a9a",
             f"Qt nodes == browser nodes ({len(nodes)}): {same}; click selects {target} in the browser "
             f"({selected}) and the editor ({editor_row}); menu {labels[:4]}; Hide tags hidden ({hidden}), "
             f"Qt item colour {grey}"]]


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
        "from KrakenOS.UI.validate_open3d_qt_5f_scene_components import tk_checks, qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown: VTK/Qt objects can segfault while
        # being destroyed, and a crash there loses a buffered result line (0932)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
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
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    rows = static_checks() + _run("tk_checks()") + _run("qt_runtime_checks()")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
