"""Guard for bugs/0992: the 3D inspector OWNS its Tk window instead of BEING one (docs/design_qt_migration.md step 1d).

`Kraken3DInspector(Open3DDebugToolsMixin, tk.Toplevel)` WAS a Tk window, so the 3D view could only
ever exist as one -- even in the Qt shell, where that window is withdrawn and never shown. It holds
`self.window` now and forwards to it whatever it does not define, the semantics a `tk.Toplevel`
subclass had -- exactly what bugs/0853 did for the editor and its root. So everything that treats
the inspector as a widget keeps working: `ttk.Frame(self)`, `self.after(...)`, `tk.Toplevel(self)`,
`transient(self)`, `parent=self`.

That the open inspector is the same Tk thing as before -- its 248 widgets with their layout and
bindings, its window, how it closes, and the picture on the screen -- is recorded in bugs/0992. This
guard holds what must stay true:

  A  the inspector is not a Tk widget; the window it owns is a Toplevel, child of the editor;
     `str(inspector)` is the window's path
  F  Tk calls through the inspector reach the window: `after` + `update` run a callback, the
     title, size and existence answer
  N  widgets parented to the inspector and to its window share ONE naming counter -- tkinter
     assigns a fresh counter to a master that has none, which would let both be named `.!frame`
  P  Tk takes the inspector where it takes a window: a dialog made with the inspector as its
     master, kept above it (`transient`), a variable whose master it is, and the inspector itself
     as an argument of a Tk command
  E  a callback of a widget inside the inspector that raises reaches the EDITOR's
     `report_callback_exception` -- tkinter finds the handler by walking `.master` up, through
     the inspector
  W  an inspector built with __new__ (guards build them) raises a clean AttributeError, honours
     getattr defaults, and a property whose own attribute is missing raises AttributeError too,
     not a recursion
  D  closing the inspector destroys its window and the editor forgets it
  Q  in the Qt shell the hosted inspector is the same kind of object: not a Tk widget, owning a
     window that is withdrawn, drawing into the Qt widget and scheduling on the shell's host
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

RESULT_MARK = "INSPECTORWINDOW_RESULT "
SKIP_MARK = "INSPECTORWINDOW_SKIP "
LAYOUT = Path("KrakenOS/common_optical_layouts/beam_splitter_two_arm_doublets.py")


def _claims(pairs) -> list:
    rows = []
    for key, claim in pairs:
        try:
            ok, detail = claim()
        except Exception as exc:        # a claim that raises is ITS failure, and the others still report
            ok, detail = False, f"raised {type(exc).__name__}: {exc}"
        rows.append([key, bool(ok), detail])
    return rows


def tk_checks() -> list:
    import tkinter as tk
    import tkinter.messagebox as tk_messagebox
    from tkinter import ttk

    for name in ("showinfo", "showwarning", "showerror"):
        setattr(tk_messagebox, name, lambda *a, **k: "ok")

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    editor = KrakenLayoutEditor()
    editor.geometry("1500x900+0+0")
    editor.layout_files[LAYOUT.stem] = LAYOUT
    editor.load_layout_by_name(LAYOUT.stem, refresh=False)

    def settle(seconds: float = 0.5) -> None:
        end = time.time() + seconds
        while time.time() < end:
            editor.update()
            time.sleep(0.02)

    settle()
    editor.open_3d_view()
    settle(3.0)
    inspector = editor._three_d_inspector

    def a():
        window = inspector.window
        mro = [cls.__name__ for cls in Kraken3DInspector.__mro__]
        return (not isinstance(inspector, tk.Misc) and isinstance(window, tk.Toplevel) and window.master is editor
                and str(inspector) == str(window) and str(window).startswith(".!") and tk.Toplevel not in Kraken3DInspector.__mro__
                and tk.Misc not in Kraken3DInspector.__mro__ and bool(inspector.available),
                f"the inspector is a {type(inspector).__name__} of {mro[1:]}; a Tk widget: {isinstance(inspector, tk.Misc)}; its "
                f"window is a {window.winfo_class()} at {window}, child of the editor: {window.master is editor}; "
                f"str(inspector) is {str(inspector)!r}; the 3D view is up: {bool(inspector.available)}")

    def f():
        fired: list = []
        inspector.after(1, lambda: fired.append("ran"))
        for _ in range(60):
            inspector.update()
            if fired:
                break
            time.sleep(0.01)
        answers = (inspector.title(), int(inspector.winfo_exists()), inspector.winfo_class(), inspector.state(),
                   inspector.winfo_toplevel() is inspector.window)
        return (fired == ["ran"] and answers == ("KrakenOS 3D Inspector", 1, "Toplevel", "normal", True),
                f"after + update through the inspector ran the callback {fired}; (title, exists, class, state, its toplevel is "
                f"the window) {answers}")

    def n():
        via_inspector, via_window = ttk.Frame(inspector), ttk.Frame(inspector.window)
        try:
            return (via_inspector.master is inspector and via_window.master is inspector.window
                    and str(via_inspector) != str(via_window)
                    and inspector._last_child_ids is inspector.window._last_child_ids
                    and str(via_inspector).startswith(str(inspector) + ".") and via_inspector.winfo_toplevel() is inspector.window,
                    f"one naming counter: {via_inspector} (inspector parent) and {via_window} (window parent); the counter is "
                    f"the window's: {inspector._last_child_ids is inspector.window._last_child_ids}")
        finally:
            via_inspector.destroy()
            via_window.destroy()

    def p():
        dialog = tk.Toplevel(inspector)
        try:
            dialog.transient(inspector)                          # "bad window path name" if the inspector is no path
            settle(0.2)
            above = str(dialog.tk.call("wm", "transient", dialog))
            variable = tk.StringVar(master=inspector, value="kept")
            as_argument = str(inspector.tk.call("winfo", "toplevel", inspector))
            menu = tk.Menu(inspector, tearoff=0)
            facts = (dialog.master is inspector, above == str(inspector.window), variable.get(), as_argument == str(inspector.window),
                     menu.master is inspector, str(dialog).startswith(str(inspector) + "."))
            menu.destroy()
        finally:
            dialog.destroy()
        return (facts == (True, True, "kept", True, True, True),
                f"a dialog whose master is the inspector, kept above it, a variable of it, the inspector as a Tk argument, a "
                f"menu of it, the dialog's path under the window: {facts}")

    def e():
        caught: list = []
        original = KrakenLayoutEditor.report_callback_exception
        KrakenLayoutEditor.report_callback_exception = lambda self, exc, val, tb: caught.append(type(val).__name__)
        frame = ttk.Frame(inspector)
        try:
            ttk.Button(frame, command=lambda: 1 / 0).invoke()
            root_of_child = frame._root()
        finally:
            KrakenLayoutEditor.report_callback_exception = original
            frame.destroy()
        return (caught == ["ZeroDivisionError"] and root_of_child is editor,
                f"a raising callback of a widget inside the inspector reached the editor's handler: {caught}; the top of "
                f"that widget's master chain is the editor: {root_of_child is editor}")

    def w():
        bare = Kraken3DInspector.__new__(Kraken3DInspector)
        outcomes = []
        for name in ("not_there", "after", "window", "_picked_row_index"):
            try:
                getattr(bare, name)
                outcomes.append("no error")
            except AttributeError:
                outcomes.append("AttributeError")
            except RecursionError:
                outcomes.append("RecursionError")
        bare._marker = 7
        return (outcomes == ["AttributeError"] * 4 and getattr(bare, "_optional", "default") == "default"
                and str(bare).startswith("<") and bare._last_child_ids is None and bare._marker == 7,
                f"an inspector built with __new__: a missing name, a Tk method, its window, a property whose own attribute "
                f"is missing -> {outcomes}; a getattr default is honoured; str() is the object's own")

    def d():
        window = inspector.window
        inspector._on_close()
        settle(0.5)
        try:
            gone = not window.winfo_exists()
        except tk.TclError:
            gone = True
        still_listed = [str(child) for child in editor.root.winfo_children() if child is window]
        return (gone and editor._three_d_inspector is None and still_listed == [],
                f"closing the inspector: its window is gone ({gone}), the editor forgot it "
                f"({editor._three_d_inspector is None}), the root still lists it: {still_listed or 'no'}")

    return _claims((("A", a), ("F", f), ("N", n), ("P", p), ("E", e), ("W", w), ("D", d)))


def qt_checks() -> list:
    def q():
        import tkinter as tk

        from KrakenOS.UI.qt.app import build
        from KrakenOS.UI.uihost import host_of

        app, window = build(["guard"])
        window.show()

        def settle(seconds: float = 0.5) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.5)
        editor = window.editor
        editor.layout_files[LAYOUT.stem] = LAYOUT
        editor.load_layout_by_name(LAYOUT.stem, refresh=False)
        settle(1.0)
        view = window.build_inspector_view()             # as the shell's own 3D scene is made
        settle(2.0)
        inspector = view.inspector
        owned = inspector.window
        facts = {"a Tk widget": isinstance(inspector, tk.Misc), "its window is a Toplevel": isinstance(owned, tk.Toplevel),
                 "the window's state": str(owned.state()), "draws into the Qt widget": inspector._shell_vtk_host is not None,
                 "schedules on the shell's host": inspector.ui is host_of(editor), "the 3D view is up": bool(inspector.available),
                 "it is the editor's inspector": editor._three_d_inspector is inspector}
        return (facts == {"a Tk widget": False, "its window is a Toplevel": True, "the window's state": "withdrawn",
                          "draws into the Qt widget": True, "schedules on the shell's host": True, "the 3D view is up": True,
                          "it is the editor's inspector": True},
                f"the inspector the Qt shell hosts: {facts}")

    return _claims((("Q", q),))


def _run(call: str, claim: str, needs: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        + needs
        + "from KrakenOS.UI.validate_inspector_owns_its_window import qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt/VTK teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
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
    rows = _run("tk_checks()", "A", "") + _run("qt_checks()", "Q", "import PySide6\n")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
