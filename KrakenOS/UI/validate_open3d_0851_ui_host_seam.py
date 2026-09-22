"""Display-free guard: the Qt-migration seam -- model/controller code reaches the toolkit only
through the UI host, and the host is drivable without a display (bugs/0851,
docs/design_qt_migration.md step 1a/1b).

175 dialog and scheduling call sites in the services/mixins, the editor core and the 3D inspector
now go through `uihost.host_of(owner)`. `TkUiHost` is today's behaviour by pure delegation;
`ScriptedUiHost` answers dialogs from a script and runs timers on a deterministic clock; a Qt host
joins later behind the same interface.

  T  TkUiHost delegates scheduling to the widget it wraps and dialogs to the tkinter modules,
     resolved at CALL time
  S  ScriptedUiHost: timers in deadline order (including ones scheduled from a callback),
     cancellation, the jump-the-clock run; answers as a value / a list / a callable; unscripted
     questions answer "cancel"; every call is recorded
  H  host_of: the owner's own host, else its editor's, else the owner wrapped -- so a fake that
     stubbed `after` still gets its stub (why guards binding real methods keep working)
  L  the model/controller layer calls no tkinter dialog module and no `self.after*` directly --
     the only exceptions are the view-building closures step 1c moves out, listed by name
  E  a REAL headless editor built with a ScriptedUiHost opens File -> Open through it: the
     question asked is recorded, the scripted "cancel" leaves the layout untouched, and no
     toolkit dialog is raised
"""
from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

MODEL_LAYER = [*sorted(Path("KrakenOS/UI/services").glob("*.py")),
               Path("KrakenOS/UI/layout_editor.py"), Path("KrakenOS/UI/open3d_inspector.py")]
# view-building closures inside services -- they construct their own Tk windows and move to the
# view layer in step 1c; named here so a NEW direct call anywhere else fails this guard
VIEW_CODE_STILL_IN_SERVICES = {
    ("inspection_cell.py", "_browse_part_step"), ("inspection_cell.py", "_browse"),
    ("inspection_cell.py", "_export"), ("inspection_cell.py", "_save"),
    ("inspection_cell.py", "_load"), ("inspection_part.py", "_browse_step"),
}


def _direct_toolkit_calls(path: Path) -> list[tuple[str, int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
    found: list[tuple[str, int, str]] = []

    def walk(node, func_name):
        for child in ast.iter_child_nodes(node):
            name = child.name if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) else func_name
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute):
                f = child.func
                direct = (isinstance(f.value, ast.Name) and f.value.id in ("messagebox", "filedialog", "simpledialog")) or (
                    f.attr in ("after", "after_cancel", "after_idle", "update_idletasks")
                    and isinstance(f.value, ast.Name) and f.value.id == "self")
                if direct:
                    found.append((func_name or "<module>", child.lineno, ast.get_source_segment(path.read_text(encoding="utf-8"), f)))
            walk(child, name)

    walk(tree, None)
    return found


def run_checks() -> tuple[bool, list[str]]:
    import tkinter.messagebox as tk_messagebox

    from KrakenOS.UI.uihost import ScriptedUiHost, TkUiHost, UiHost, host_of

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- T: Tk delegation ----------------------------------------------------------------------
    log = []
    root = SimpleNamespace(
        after=lambda ms, func=None, *a: log.append(("after", ms, func, a)) or "id-1",
        after_cancel=lambda h: log.append(("cancel", h)),
        after_idle=lambda func, *a: log.append(("idle", func, a)) or "id-2",
        update_idletasks=lambda: log.append(("flush",)),
    )
    host = TkUiHost(root)
    cb = lambda: None
    got = (host.after(40, cb, 1), host.after_idle(cb), host.after_cancel("id-1"), host.update_idletasks())
    ok(got[:2] == ("id-1", "id-2") and log == [("after", 40, cb, (1,)), ("idle", cb, ()), ("cancel", "id-1"), ("flush",)],
       "T1: scheduling is delegated to the wrapped widget, arguments and handles untouched")
    saved = tk_messagebox.askyesno
    tk_messagebox.askyesno = lambda title, message, **k: ("patched", title, message, k.get("parent"))
    try:
        answer = host.askyesno("Q", "sure?", parent="w")
    finally:
        tk_messagebox.askyesno = saved
    ok(answer == ("patched", "Q", "sure?", "w"),
       "T2: dialogs go to tkinter.messagebox resolved at call time (so patching it still works)")

    # ---- S: the scripted host ------------------------------------------------------------------
    ui = ScriptedUiHost(answers={"askyesno": [True, False], "askopenfilename": "/tmp/a.py",
                                 "askstring": lambda title, prompt, **k: f"{title}:{prompt}"})
    order = []
    ui.after(30, order.append, "late")
    ui.after(10, lambda: (order.append("early"), ui.after(5, order.append, "nested")))
    doomed = ui.after(20, order.append, "cancelled")
    ui.after_cancel(doomed)
    first = ui.run_due(12)
    rest = ui.run_all()
    ok(order == ["early", "nested", "late"] and (first, rest) == (1, 2) and ui.pending() == 0,
       f"S1: timers run in deadline order, a callback's own timer included, a cancelled one never ({order})")
    answers = (ui.askyesno("a", "b"), ui.askyesno("a", "b"), ui.askyesno("a", "b"),
               ui.askopenfilename(title="Open"), ui.askstring("T", "P"), ui.askdirectory(), ui.askyesnocancel())
    ok(answers == (True, False, False, "/tmp/a.py", "T:P", "", None),
       f"S2: a list is consumed in order then falls back to cancel; values and callables answer; "
       f"unscripted questions cancel {answers}")
    ok([name for name, *_ in ui.calls if name.startswith("ask")] == ["askyesno"] * 3 + ["askopenfilename", "askstring", "askdirectory", "askyesnocancel"]
       and ui.asked("askopenfilename") == [((), {"title": "Open"})],
       "S3: every question is recorded with its arguments")

    # ---- H: host resolution --------------------------------------------------------------------
    own = SimpleNamespace(ui=ui)
    via_editor = SimpleNamespace(editor=SimpleNamespace(ui=ui))
    stubbed = SimpleNamespace(after=lambda ms, func=None, *a: ("stub", ms))
    wrapped = host_of(stubbed)
    ok(host_of(own) is ui and host_of(via_editor) is ui and isinstance(wrapped, TkUiHost)
       and wrapped.after(7, cb) == ("stub", 7) and isinstance(wrapped, UiHost),
       "H: the owner's host, else its editor's, else the owner wrapped -- a fake's own `after` stub "
       "still answers")

    # ---- L: the model layer's purity -----------------------------------------------------------
    stray = []
    for path in MODEL_LAYER:
        for func, line, text in _direct_toolkit_calls(path):
            if (path.name, func) not in VIEW_CODE_STILL_IN_SERVICES:
                stray.append(f"{path.name}:{line} {func}: {text}")
    ok(not stray, f"L: no direct tkinter dialog / self.after* call left in the model/controller layer "
                  f"outside the {len(VIEW_CODE_STILL_IN_SERVICES)} named view closures ({stray or 'none'})")

    # ---- E: a real editor on a scripted host ----------------------------------------------------
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    scripted = ScriptedUiHost()                               # unscripted -> the user cancels
    raised = []
    saved_open = tk_messagebox.showerror
    import tkinter.filedialog as tk_filedialog
    saved_ask = tk_filedialog.askopenfilename
    tk_filedialog.askopenfilename = lambda **k: raised.append("tk dialog") or ""
    try:
        editor = KrakenLayoutEditor(headless=True, ui=scripted)
        try:
            rows_before = list(editor.rows)
            file_before = editor.current_layout_file
            editor.open_layout()
            asked = scripted.asked("askopenfilename")
            ok(editor.ui is scripted and len(asked) == 1 and asked[0][1].get("title") == "Open Kraken layout"
               and editor.rows == rows_before and editor.current_layout_file == file_before and not raised,
               f"E: a REAL headless editor asked File -> Open through its scripted host "
               f"({asked[0][1].get('title') if asked else None!r}); the scripted cancel left the layout "
               f"untouched and no toolkit dialog was raised")
        finally:
            editor.destroy()
    finally:
        tk_filedialog.askopenfilename = saved_ask
        tk_messagebox.showerror = saved_open
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
