"""Guard: the editor OWNS its Tk root instead of BEING one (bugs/0853,
docs/design_qt_migration.md step 1d).

`KrakenLayoutEditor(18 mixins, tk.Tk)` WAS the Tk root, so the model could only ever live inside a
Tk application. It now holds `self.root = tk.Tk()` and forwards to it whatever it does not define --
the semantics a tk.Tk subclass had -- so the panels that parent widgets to it, `editor.update()` /
`editor.after(...)`, and the 171 validators that do both keep working unchanged. A Qt shell can
later hold the same model with no Tk root at all.

  A  the editor is not a Tk; its root is; `str(editor)` is still the root path "."
  F  Tk calls through the editor reach the root: `after` + `update` run a callback, `winfo_exists`
  N  widgets parented to the editor and to the root share ONE naming counter -- tkinter assigns a
     fresh counter to a master that has none, which would have let both be named `.!frame`
  E  a widget callback that raises reaches the EDITOR's report_callback_exception (tkinter finds
     the handler by walking `.master` up, which now ends at the editor), and the root's own
     handler is the editor's too
  W  an editor built with __new__ (the off-thread trace worker, render_layout_snapshot) gets a
     clean AttributeError / getattr default -- the bugs/0223 recursion class is gone by
     construction
  D  destroy() runs the editor's cleanup and takes the root with it
"""
from __future__ import annotations

import time


def run_checks() -> tuple[bool, list[str]]:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    app = KrakenLayoutEditor(headless=True)
    destroyed_root = None
    try:
        ok(not isinstance(app, tk.Misc) and isinstance(app.root, tk.Tk) and str(app) == "."
           and tk.Tk not in KrakenLayoutEditor.__mro__,
           "A: the editor is not a Tk widget; the root it owns is; str(editor) is still '.'")

        fired = []
        app.after(1, lambda: fired.append("ran"))
        for _ in range(50):
            app.update()
            if fired:
                break
            time.sleep(0.01)
        ok(fired == ["ran"] and app.winfo_exists() == 1,
           "F: after + update through the editor run the callback on the root; winfo_* answers")

        via_editor, via_root = ttk.Frame(app), ttk.Frame(app.root)
        ok(via_editor.master is app and str(via_editor) != str(via_root)
           and app._last_child_ids is app.root._last_child_ids,
           f"N: one naming counter -- {via_editor} (editor parent) vs {via_root} (root parent)")

        caught = []
        original = KrakenLayoutEditor.report_callback_exception
        KrakenLayoutEditor.report_callback_exception = lambda self, exc, val, tb: caught.append(type(val).__name__)
        try:
            ttk.Button(via_editor, command=lambda: 1 / 0).invoke()
        finally:
            KrakenLayoutEditor.report_callback_exception = original
        root_handler = app.root.report_callback_exception
        ok(caught == ["ZeroDivisionError"] and getattr(root_handler, "__self__", None) is app,
           f"E: a raising widget callback reaches the editor's handler ({caught}); the root's handler "
           f"is the editor's too")

        bare = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
        try:
            bare.not_there
            clean = False
        except AttributeError:
            clean = True
        except RecursionError:
            clean = False
        ok(clean and getattr(bare, "_optional", "default") == "default" and str(bare).startswith("<"),
           "W: an editor built with __new__ raises a clean AttributeError and honours getattr defaults")

        cleaned = []
        original_shutdown = app._shutdown_analysis_executor
        app._shutdown_analysis_executor = lambda: cleaned.append("executor")
        destroyed_root = app.root
    finally:
        app.destroy()
    try:
        destroyed_root.winfo_exists()
        gone = False
    except tk.TclError:
        gone = True
    ok(gone and cleaned == ["executor"], "D: destroy() ran the editor's cleanup and destroyed the root")
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
