"""Guard for bugs/0981: popup-menu dismissal and dialog centring are a Tk panel; the last service lets go of tkinter.

Phase 7d of the Qt migration, the last service that imported tkinter for view code.
`services/paraxial_tools.py` held four small pieces of Tk -- a click elsewhere or Escape dismisses
the surface table's popup menu, and two ways of centring a dialog -- plus the clean-up of that menu,
which caught `tk.TclError`. The four are `panels/main_popup_helpers.py` now. The clean-up stays in
the service, because it is the model that forgets which cell the menu was on, and it asks whatever
made the menu to take it down.

  S  the service imports and names no tkinter; the panel class defines the four and the editor
     delegates the three that are called from outside; the clean-up is still the service's
  M  the clean-up, no display: a menu is released and destroyed, in that order, and forgotten with
     the cell it was on; a menu whose calls RAISE is forgotten all the same and nothing is passed
     on; with no menu only the cell is forgotten; the recording menu a shell renders is taken down
     the same way
  T  a real Tk editor: the window binds the click, the release and Escape; with a real popup menu
     up, a click ON the menu leaves it, a click elsewhere takes it down, so does a dismissal with
     no event, and with no menu up nothing happens; a dialog is centred over the main window, and
     on the screen, to the pixel
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

RESULT_MARK = "POPUPHELPERS_RESULT "
SKIP_MARK = "POPUPHELPERS_SKIP "
SERVICE = Path("KrakenOS/UI/services/paraxial_tools.py")
PANEL_METHODS = ("_event_inside_widget_root_bounds", "_dismiss_popup_menu_event", "_center_dialog_over_main_window",
                 "_center_dialog_on_screen")
DELEGATED = PANEL_METHODS[1:]
TK_NAMES = {"tk", "ttk", "tkfont", "messagebox", "filedialog", "simpledialog"}


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
    from KrakenOS.UI.services.paraxial_tools import ParaxialToolsMixin as Model

    def s():
        from KrakenOS.UI.layout_editor import KrakenLayoutEditor
        from KrakenOS.UI.panels.main_popup_helpers import MainPopupHelpers

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        still_there = [name for name in PANEL_METHODS if name in vars(Model)]
        panel_defines = [name for name in PANEL_METHODS if name in vars(MainPopupHelpers)]
        delegations = [name for name in DELEGATED if name in vars(KrakenLayoutEditor)
                       and f"self._main_popup_helpers().{name}(" in inspect.getsource(vars(KrakenLayoutEditor)[name])]
        return (imports == [] and named == [] and still_there == [] and panel_defines == list(PANEL_METHODS)
                and delegations == list(DELEGATED) and "_cleanup_current_popup_menu" in vars(Model),
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, view methods "
                f"still defined there {still_there or 'none'}; the panel defines {len(panel_defines)} of {len(PANEL_METHODS)} and "
                f"the editor delegates {len(delegations)} of {len(DELEGATED)}; the clean-up is the service's: "
                f"{'_cleanup_current_popup_menu' in vars(Model)}")

    def m():
        from KrakenOS.UI.context_menu import MenuModel

        def owner(menu):
            return SimpleNamespace(popup_menu=menu, current_menu_row_id="I003", current_menu_field="thickness")

        calls: list = []
        tidy = SimpleNamespace(grab_release=lambda: calls.append("grab_release"), destroy=lambda: calls.append("destroy"))
        first = owner(tidy)
        Model._cleanup_current_popup_menu(first)

        attempts: list = []

        def failing(name):
            def call():
                attempts.append(name)
                raise RuntimeError(f"{name} failed")
            return call

        broken = owner(SimpleNamespace(grab_release=failing("grab_release"), destroy=failing("destroy")))
        Model._cleanup_current_popup_menu(broken)
        none = owner(None)
        Model._cleanup_current_popup_menu(none)
        recorded = owner(MenuModel())
        Model._cleanup_current_popup_menu(recorded)
        forgotten = lambda o: (o.popup_menu, o.current_menu_row_id, o.current_menu_field) == (None, None, None)
        return (calls == ["grab_release", "destroy"] and forgotten(first) and attempts == ["grab_release", "destroy"]
                and forgotten(broken) and forgotten(none) and forgotten(recorded),
                f"a menu is taken down by {calls} and forgotten with its cell: {forgotten(first)}; a menu whose calls raise "
                f"is still asked both ({attempts}) and forgotten: {forgotten(broken)}; with no menu the cell is forgotten: "
                f"{forgotten(none)}; a shell's recording menu the same: {forgotten(recorded)}")

    return _claims((("S", s), ("M", m)))


def tk_checks() -> list:
    import tkinter as tk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    for _ in range(4):
        editor.update()

    def pump() -> None:
        for _ in range(4):
            editor.update()

    def claim_t():
        notes, ok = [], True

        def check(condition, note) -> None:
            nonlocal ok
            ok = ok and bool(condition)
            notes.append(f"{note}: {bool(condition)}")

        bound = [bool(editor.root.bind_all(sequence)) for sequence in ("<Button-1>", "<ButtonRelease-1>", "<Escape>")]
        check(bound == [True, True, True], f"the window binds the click, the release and Escape {bound}")

        posted: list = []
        popup, tk.Menu.tk_popup = tk.Menu.tk_popup, lambda self, x, y, entry="": posted.append((x, y))
        try:
            def post():
                editor._show_choice_menu("I001", "surface", ("Standard", "Mirror"), 300, 200)
                pump()
                return editor.popup_menu

            menu = post()
            is_menu = isinstance(menu, tk.Menu) and posted[-1:] == [(300, 200)]
            x, y = int(menu.winfo_rootx()), int(menu.winfo_rooty())
            width = max(int(menu.winfo_width()), 1)
            editor._dismiss_popup_menu_event(SimpleNamespace(widget=menu, x_root=x, y_root=y))
            on_menu = (editor.popup_menu is menu, bool(menu.winfo_exists()))
            editor._dismiss_popup_menu_event(SimpleNamespace(widget=menu, x_root=x + width + 60, y_root=y))
            beside = (editor.popup_menu is None, not bool(menu.winfo_exists()))

            menu = post()
            editor._dismiss_popup_menu_event(SimpleNamespace(widget=editor.root, x_root=x, y_root=y))
            other_widget = (editor.popup_menu is None, not bool(menu.winfo_exists()))
            menu = post()
            editor._dismiss_popup_menu_event()
            no_event = (editor.popup_menu is None, not bool(menu.winfo_exists()))
            editor.current_menu_row_id = "kept"
            editor._dismiss_popup_menu_event()
            nothing_up = editor.current_menu_row_id
        finally:
            tk.Menu.tk_popup = popup
        check(is_menu and on_menu == (True, True), f"a real popup menu is up; a click ON it leaves it {on_menu}")
        check(beside == (True, True) and other_widget == (True, True),
              f"a click beside it takes it down {beside}, and so does a click on another widget {other_widget}")
        check(no_event == (True, True) and nothing_up == "kept",
              f"a dismissal with no event takes it down {no_event}; with no menu up nothing is touched ({nothing_up!r})")

        # centring, to the pixel
        editor.root.geometry("900x600+120+80")
        pump()
        dialog = tk.Toplevel(editor)
        dialog.geometry("300x200+0+0")
        pump()
        editor._center_dialog_over_main_window(dialog)
        pump()
        over = (int(dialog.winfo_x()), int(dialog.winfo_y()))
        root = (int(editor.winfo_rootx()), int(editor.winfo_rooty()), int(editor.winfo_width()), int(editor.winfo_height()))
        size = (int(dialog.winfo_width()), int(dialog.winfo_height()))
        expected_over = (root[0] + max((root[2] - size[0]) // 2, 0), root[1] + max((root[3] - size[1]) // 2, 0))
        editor._center_dialog_on_screen(dialog)
        for _ in range(6):                                   # it places at once, when idle, and 80 ms later
            pump()
            editor.after(30, lambda: None)
        pump()
        on_screen = (int(dialog.winfo_x()), int(dialog.winfo_y()))
        screen = (int(dialog.winfo_screenwidth()), int(dialog.winfo_screenheight()))
        expected_screen = (max((screen[0] - size[0]) // 2, 0), max((screen[1] - size[1]) // 2, 0))
        dialog.destroy()
        check(size == (300, 200) and over == expected_over and expected_over != (0, 0),
              f"a 300 x 200 dialog over the main window (at {root[:2]}, {root[2]} x {root[3]}) lands at {over}, expected "
              f"{expected_over}")
        check(on_screen == expected_screen and expected_screen != expected_over,
              f"on the {screen[0]} x {screen[1]} screen it lands at {on_screen}, expected {expected_screen}")
        return ok, "; ".join(notes)

    return _claims((("T", claim_t),))


def _run(call: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_popup_helpers_view import tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=300,
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
    rows += _run("tk_checks()", "T")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
