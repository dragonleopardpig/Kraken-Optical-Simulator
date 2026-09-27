"""Guard: the 3D view's right-click menus, in the Qt shell (bugs/0907, docs/design_qt_migration.md
phase 5c).

Every CAD / Place / Orient command in the 3D view is a right-click verb (bugs/0619). The Tk menus
are built imperatively by 16 builders in the inspector and its face-assignment service, and
measured, those builders use only `add_command`, `add_separator`, `add_checkbutton`,
`add_cascade`, `invoke`, `unpost` and a post. So they are not rewritten:
`context_menu.new_context_menu` hands them a real `tk.Menu` exactly as before, unless a shell
hosting the inspector installed `show_context_menu`; then it hands them a `MenuModel`, which records
the same calls. The Qt shell renders that record as a QMenu whose actions run the builders' own
callables.

Static:
  S  no viewport menu is created by `tk.Menu(...)` directly, and nothing but the two posters
     (`_popup_context_menu`, `_post_viewport_menu`) posts one; every call the builders make on
     a menu is one `MenuModel` takes
  M  `MenuModel.run` does what a Tk entry click does: a check entry toggles its variable and a
     radio entry sets its own BEFORE the command; a disabled entry, a separator and a cascade run
     nothing; `new_context_menu` gives a `tk.Menu` with no shell and a model with one

In the Tk shell, on om05a_folded (same process, same pixel, same state):
  T  at every pixel of a grid, the REAL `tk.Menu` the Tk inspector posts and the `MenuModel` the
     SAME builder fills when a shell hook is installed have the identical outline -- kind, label,
     enabled, submenus -- for every kind of menu the grid reaches (at least four kinds, a
     face-assignment menu among them)

In a real Qt shell (subprocess, xcb):
  Q  a right click on the Qt widget shows a QMenu whose outline is its model's, for every kind
     the grid reaches (at least four, a face menu among them)
  A  triggering a QMenu action runs the builder's verb: "Select Elements" on the empty-space menu
     arms the box select; the menu is then no longer the live one
  D  a left click in the scene dismisses a shown menu, as it does in Tk (bugs/0341)
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")
RESULT_MARK = "GUARD0907:"
SKIP_MARK = "GUARD0907-SKIP:"
MENU_MODULES = ("KrakenOS/UI/open3d_inspector.py", "KrakenOS/UI/services/open3d_face_assignment.py")
POSTERS = ("_popup_context_menu", "_post_viewport_menu")


def _kind(outline) -> str:
    """A menu's kind: its title entry's first word ("S15", "OPTICAL", "Optical", "—", ...)."""
    if not outline or len(outline[0]) < 2:
        return "?"
    return (str(outline[0][1]).split() or ["?"])[0]


def _is_face_menu(outline) -> bool:
    return any(len(row) > 1 and str(row[1]).startswith("Set ") for row in outline)


# ---- the Qt half -----------------------------------------------------------------------------
def qt_runtime_checks() -> list:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.context_menu import MenuModel
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.inspector_view import qmenu_outline

    rows: list = []
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(20):
        app.processEvents()
    widget, inspector = view.widget, view.inspector
    NONE = Qt.MouseButton.NoButton

    def settle(turns=2):
        for _ in range(turns):
            app.processEvents()

    def mouse(kind, x, y, button=NONE, buttons=NONE):
        event = QMouseEvent(kind, QPointF(x, y), QPointF(widget.mapToGlobal(QPoint(x, y))),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, event)
        settle(1)

    def right_click(x, y):
        view.last_menu = None
        rb = Qt.MouseButton.RightButton
        mouse(QEvent.Type.MouseMove, x, y)
        mouse(QEvent.Type.MouseButtonPress, x, y, rb, rb)
        mouse(QEvent.Type.MouseButtonRelease, x, y, rb, NONE)
        return view.last_menu, getattr(inspector, "_active_context_menu", None)

    # ---- Q ---------------------------------------------------------------------------------
    seen: dict = {}
    mismatched = []
    empty_space = None
    width, height = widget.width(), widget.height()
    for gy in range(1, 10):
        for gx in range(1, 12):
            x, y = width * gx // 12, height * gy // 10
            shown, model = right_click(x, y)
            if shown is None:
                continue
            if not isinstance(model, MenuModel):
                mismatched.append((x, y, "no live model"))
            else:
                qt_outline, model_outline = qmenu_outline(shown), model.outline()
                kind = _kind(model_outline)
                seen.setdefault(kind, (x, y, len(model_outline), _is_face_menu(model_outline)))
                if qt_outline != model_outline:
                    mismatched.append((x, y, kind))
                if kind == "—" and empty_space is None:
                    empty_space = (x, y)
            shown.close()
            settle()
    faces = [kind for kind, info in seen.items() if info[3]]
    rows.append(["Q", len(seen) >= 4 and faces and not mismatched,
                 f"right clicks showed {len(seen)} kinds of QMenu, each exactly its model "
                 f"(kind: x, y, entries, face-menu) {seen}"
                 + (f"; MISMATCHED {mismatched}" if mismatched else "")])

    # ---- A ---------------------------------------------------------------------------------
    armed_before = bool(getattr(inspector, "_rubber_band_select_mode", False))
    ran, released = False, False
    if empty_space is not None:
        shown, model = right_click(*empty_space)
        for action in shown.actions():
            if action.text().startswith("Select Elements"):
                action.trigger()
                ran = True
                break
        shown.close()
        settle()
        released = getattr(inspector, "_active_context_menu", None) is None
    armed = bool(getattr(inspector, "_rubber_band_select_mode", False))
    rows.append(["A", ran and armed and not armed_before and released,
                 f"'Select Elements' triggered from the empty-space QMenu at {empty_space} armed "
                 f"the box select ({armed_before} -> {armed}); the menu is no longer live "
                 f"({released})"])
    try:
        inspector.dispatch_viewport_key("Escape")
    except Exception:
        pass
    settle()

    # ---- D ---------------------------------------------------------------------------------
    visible_before = visible_after = None
    if empty_space is not None:
        shown, model = right_click(*empty_space)
        visible_before = shown.isVisible()
        lb = Qt.MouseButton.LeftButton
        x, y = empty_space
        mouse(QEvent.Type.MouseButtonPress, x + 3, y + 3, lb, lb)
        mouse(QEvent.Type.MouseButtonRelease, x + 3, y + 3, lb, NONE)
        visible_after = shown.isVisible()
    live = getattr(inspector, "_active_context_menu", None)
    rows.append(["D", visible_before is True and visible_after is False and live is None,
                 f"a left click in the scene closed the shown menu (visible {visible_before} -> "
                 f"{visible_after}); live menu now {live}"])
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
        "from KrakenOS.UI.validate_open3d_0907_context_menus_in_qt import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1500, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 1500 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


# ---- the static half -------------------------------------------------------------------------
def _menu_calls() -> tuple[list, list, set]:
    """(direct tk.Menu constructions, tk_popup calls outside the posters, attrs called on menus)."""
    direct, stray_posts, attrs = [], [], set()
    for path in MENU_MODULES:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        for func in ast.walk(tree):
            if not isinstance(func, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            menu_names = {"menu", "parent_menu"}
            for node in ast.walk(func):
                if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
                        and getattr(node.value.func, "id", "") == "new_context_menu"):
                    menu_names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
            for node in ast.walk(func):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                owner = node.func.value
                if (node.func.attr == "Menu" and isinstance(owner, ast.Name)
                        and owner.id == "tk"):
                    direct.append(f"{Path(path).name}:{node.lineno}")
                if isinstance(owner, ast.Name) and owner.id in menu_names:
                    if func.name in POSTERS:
                        # a poster's Tk branch (grab, <Unmap>, settle timer) runs only for a
                        # tk.Menu: its shell branch returns first
                        continue
                    if node.func.attr == "tk_popup":
                        stray_posts.append(f"{Path(path).name}:{func.name}:{node.lineno}")
                    else:
                        attrs.add(node.func.attr)
    return direct, stray_posts, attrs


class _Var:
    def __init__(self, value):
        self.value = value

    def get(self):
        return self.value

    def set(self, value):
        self.value = value


def _tk_parity(notes, ok) -> None:
    """T: the real Tk menu and the recorded model, from the same builder at the same pixel."""
    import tkinter

    from KrakenOS.UI.context_menu import MenuModel, tk_menu_outline
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.viewport_events import ViewportEvent

    posted: list = []
    real_popup = tkinter.Menu.tk_popup

    def record_popup(menu, x, y, entry=""):
        # record the posted menu instead of grabbing the pointer (no mainloop runs here)
        posted.append(menu)

    editor = KrakenLayoutEditor()
    tkinter.Menu.tk_popup = record_popup
    try:
        editor.layout_files[SCENE.stem] = SCENE
        editor.load_layout_by_name(SCENE.stem)
        editor.open_3d_view()
        for _ in range(6):
            editor.update()
        inspector = getattr(editor, "_three_d_inspector", None)
        if inspector is None or not getattr(inspector, "available", False):
            notes.append("SKIP T: the embedded 3D inspector is unavailable")
            return
        for _ in range(6):
            inspector.update()
            editor.update()
        interactor = inspector._vtk_interactor
        width, height = inspector._vtk_widget.GetRenderWindow().GetSize()

        def right_press(x, y):
            inspector._mouse_move_last_ts = 0.0
            interactor.SetEventInformationFlipY(x, y, 0, 0, chr(0), 0, None)
            interactor.MouseMoveEvent()
            event = ViewportEvent(x, y, 0, "", 100 + x, 100 + y)
            inspector.dispatch_viewport_event("hover", event)
            inspector.dispatch_viewport_event("right_press", event)
            inspector.dispatch_viewport_event("right_release", event)
            inspector.update()

        seen: dict = {}
        differ = []
        for gy in range(1, 10):
            for gx in range(1, 12):
                x, y = width * gx // 12, height * gy // 10
                # a right-click can itself change what the next menu reads (measured: a menu
                # built right after the previous pixel's differed from one built after its own
                # click), so settle the state with one click here before the compared two
                posted.clear()
                right_press(x, y)
                inspector._face_assignment_service()._dismiss_active_context_menu()
                if not posted:
                    continue
                posted.clear()
                right_press(x, y)
                if not posted:
                    differ.append((x, y, "no Tk menu on the second click"))
                    continue
                tk_outline = tk_menu_outline(posted[-1])
                inspector._face_assignment_service()._dismiss_active_context_menu()
                try:
                    posted[-1].destroy()
                except Exception:
                    pass
                captured: list = []
                inspector.show_context_menu = lambda model, _event: captured.append(model)
                try:
                    right_press(x, y)
                finally:
                    del inspector.show_context_menu
                inspector._face_assignment_service()._dismiss_active_context_menu()
                model = captured[-1] if captured else None
                model_outline = model.outline() if isinstance(model, MenuModel) else None
                kind = _kind(tk_outline)
                seen.setdefault(kind, (x, y, len(tk_outline), _is_face_menu(tk_outline)))
                if model_outline != tk_outline:
                    first = next((i for i, (a, b) in enumerate(zip(tk_outline, model_outline or []))
                                  if a != b), min(len(tk_outline), len(model_outline or [])))
                    differ.append((x, y, kind, first,
                                   tk_outline[first] if first < len(tk_outline) else None,
                                   (model_outline or [None] * (first + 1))[first]
                                   if model_outline and first < len(model_outline) else None))
        faces = [kind for kind, info in seen.items() if info[3]]
        ok(len(seen) >= 4 and faces and not differ,
           f"T: at every grid pixel the REAL Tk menu and the model the same builder filled have "
           f"the identical outline -- {len(seen)} kinds (kind: x, y, entries, face-menu) {seen}"
           + (f"; DIFFER at {differ}" if differ else ""))
    finally:
        tkinter.Menu.tk_popup = real_popup
        editor.destroy()


def run_checks() -> tuple[bool, list[str]]:
    import tkinter

    from KrakenOS.UI.context_menu import MenuModel, new_context_menu

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- S ---------------------------------------------------------------------------------
    direct, stray_posts, attrs = _menu_calls()
    unmodelled = sorted(attr for attr in attrs if not hasattr(MenuModel, attr))
    ok(not direct and not stray_posts and not unmodelled and {"add_command", "add_cascade"} <= attrs,
       f"S: no viewport menu is a direct tk.Menu, only {POSTERS} post one, and every call the "
       f"builders make on a menu {sorted(attrs)} is one MenuModel takes"
       + (f" -- direct {direct}" if direct else "") + (f" -- posts {stray_posts}" if stray_posts else "")
       + (f" -- unmodelled {unmodelled}" if unmodelled else ""))

    # ---- M ---------------------------------------------------------------------------------
    calls: list = []
    model = MenuModel()
    check, radio = _Var(False), _Var("a")
    model.add_checkbutton(label="c", variable=check,
                          command=lambda: calls.append(("check", check.get())))
    model.add_radiobutton(label="r", variable=radio, value="b",
                          command=lambda: calls.append(("radio", radio.get())))
    model.add_command(label="off", state="disabled", command=lambda: calls.append("disabled"))
    model.add_separator()
    sub = MenuModel(model)
    model.add_cascade(label="more", menu=sub)
    for index in range(len(model.entries)):
        model.invoke(index)
    model.invoke(0)
    no_shell = new_context_menu(object(), None)
    shell_owner = type("Shell", (), {"show_context_menu": lambda *a: None})()
    with_shell = new_context_menu(shell_owner, None)
    nested = new_context_menu(object(), with_shell)
    ok(calls == [("check", True), ("radio", "b"), ("check", False)]
       and isinstance(no_shell, tkinter.Menu) and isinstance(with_shell, MenuModel)
       and isinstance(nested, MenuModel),
       f"M: a click toggles/sets the variable BEFORE the command, disabled/separator/cascade run "
       f"nothing ({calls}); no shell -> {type(no_shell).__name__}, a shell -> "
       f"{type(with_shell).__name__}, a model's submenu -> {type(nested).__name__}")
    try:
        no_shell.destroy()
    except Exception:
        pass

    # ---- T ---------------------------------------------------------------------------------
    _tk_parity(notes, ok)

    status, qt_rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Qt half: {qt_rows[0][2]}")
        return state["ok"], notes
    for row in qt_rows:
        ok(bool(row[1]), f"{row[0]}: {row[2]}")
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
