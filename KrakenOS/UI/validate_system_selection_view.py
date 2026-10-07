"""Guard for bugs/0980: the System Selection Calculator's Tk form is a panel module; the command picks the view.

Phase 7d of the Qt migration, the sixth service. `services/system_selection.py` is the calculator's
first-order core -- and carried, at its end, the Tk form (seven inputs, a result that recomputes as
you type) and the Tk window that holds it. Both are `panels/system_selection_view.py` now.

The model's command, `open_system_selection_calculator`, used to build the Tk window whatever the
shell. It asks first whether another shell draws the editor, and shows the calculator's row form
there -- the same one that shell's own action opens.

  S  the core imports and names no tkinter, at module level or inside a function, and no longer
     has the two view functions; the panel module defines both; the command checks for a shell
     BEFORE it reaches for the Tk window; the 3D view's left panel takes the form from the panel
     module
  T  the Tk app: the command opens ONE window, "System Selection Calculator", resizable, with
     seven entries and Close; the form shows exactly what the model computes for what is typed,
     and recomputes on every keystroke -- a value that is no number included; Close closes it
  Q  the Qt shell: the same command opens the calculator's Qt form, makes no Tk window and never
     asks for the Tk view
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "SYSSELVIEW_RESULT "
SKIP_MARK = "SYSSELVIEW_SKIP "
SERVICE = Path("KrakenOS/UI/services/system_selection.py")
VIEW_FUNCTIONS = ("build_system_selection_form", "open_system_selection_dialog")
INPUTS = ("fov_w", "fov_h", "resolution", "wd_min", "sensor_w", "sensor_h", "wavelength")
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
    def s():
        from KrakenOS.UI.panels import open3d_live_controls, system_selection_view
        from KrakenOS.UI.services import system_selection as core
        from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

        tree = ast.parse(SERVICE.read_text(encoding="utf-8"))
        imports = sorted({node.lineno for node in ast.walk(tree)
                          if (node.__class__ is ast.Import and any(a.name.split(".")[0] == "tkinter" for a in node.names))
                          or (isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] == "tkinter")})
        named = sorted({node.id for node in ast.walk(tree) if isinstance(node, ast.Name) and node.id in TK_NAMES})
        still_there = [name for name in VIEW_FUNCTIONS if hasattr(core, name)]
        defined = [name for name in VIEW_FUNCTIONS if callable(getattr(system_selection_view, name, None))]
        command = inspect.getsource(LayoutTableWorkbenchMixin.open_system_selection_calculator)
        shell_at, view_at = command.find('"show_row_form"'), command.find("system_selection_view import open_system_selection_dialog")
        left_panel = inspect.getsource(open3d_live_controls.Open3DLiveControlsPanel.build_system_selection_controls)
        return (imports == [] and named == [] and still_there == [] and defined == list(VIEW_FUNCTIONS)
                and 0 <= shell_at < view_at and "panels.system_selection_view import build_system_selection_form" in left_panel,
                f"{SERVICE.name}: tkinter imports at lines {imports or 'none'}, tkinter names {named or 'none'}, view functions "
                f"still there {still_there or 'none'}; the panel module defines {defined}; the command checks for a shell (char "
                f"{shell_at}) before the Tk window (char {view_at}); the 3D left panel takes the form from the panel module: "
                f"{'panels.system_selection_view' in left_panel}")

    return _claims((("S", s),))


def tk_checks() -> list:
    import tkinter as tk
    from tkinter import ttk

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.system_selection_view import build_system_selection_form
    from KrakenOS.UI.services.system_selection import system_selection_text

    editor = KrakenLayoutEditor()
    for _ in range(3):
        editor.update()

    def widgets(root, kind):
        found = []
        for child in root.winfo_children():
            if isinstance(child, kind):
                found.append(child)
            found += widgets(child, kind)
        return found

    def pump() -> None:
        for _ in range(4):
            editor.update()

    def calculators() -> list:
        return [w for w in widgets(editor.root, tk.Toplevel) if str(w.title()) == "System Selection Calculator"]

    def claim_t():
        before = len(calculators())
        editor.open_system_selection_calculator()
        pump()
        opened = calculators()
        window = opened[0]
        shown = {"windows": len(opened) - before, "entries": len(widgets(window, ttk.Entry)),
                 "buttons": [str(b.cget("text")) for b in widgets(window, ttk.Button)],
                 "resizable": tuple(bool(v) for v in window.resizable()), "owner_is_root": window.master is editor.root}

        # the form on its own: what it shows is what the model computes, on every keystroke
        host = ttk.Frame(editor.root)
        form = build_system_selection_form(host, editor, compact=False, prefill=False)
        entries = widgets(host, ttk.Entry)
        typed = {"fov_w": "55", "fov_h": "8.3", "resolution": "10.99", "wd_min": "100", "sensor_w": "23",
                 "sensor_h": "23", "wavelength": "0.55"}
        steps = []
        values = {key: "" for key in INPUTS}
        values["wavelength"] = "0.55"                       # the form's own default
        for entry, key in zip(entries, INPUTS):
            entry.delete(0, "end")
            entry.insert(0, typed[key])
            values[key] = typed[key]
            steps.append(str(form.out_var.get()) == system_selection_text(values, None))
        full = str(form.out_var.get())
        entries[2].delete(0, "end")
        entries[2].insert(0, "abc")
        values["resolution"] = "abc"
        garbled = (str(form.out_var.get()) == system_selection_text(values, None), str(form.out_var.get()) != full)
        host.destroy()

        next(b for b in widgets(window, ttk.Button) if str(b.cget("text")) == "Close").invoke()
        pump()
        closed = len(calculators()) == before
        return (shown == {"windows": 1, "entries": 7, "buttons": ["Close"], "resizable": (True, True), "owner_is_root": True}
                and len(entries) == 7 and all(steps) and len(full) > 80 and garbled == (True, True) and closed,
                f"the command opens {shown['windows']} window with {shown['entries']} entries, buttons {shown['buttons']}, "
                f"resizable {shown['resizable']}; after each of the 7 inputs the form shows the model's text: {steps} "
                f"({len(full)} characters with all typed); a resolution of 'abc' shows the model's answer for that too "
                f"{garbled}; Close closes it: {closed}")

    return _claims((("T", claim_t),))


def qt_checks() -> list:
    def claim_q():
        import time
        import tkinter as tk

        from KrakenOS.UI.panels import system_selection_view
        from KrakenOS.UI.qt.app import build
        from KrakenOS.UI.row_forms.system_selection import TITLE

        app, window = build(["guard"])
        window.show()
        app.processEvents()

        def settle(seconds: float = 0.4) -> None:
            end = time.time() + seconds
            while time.time() < end:
                app.processEvents()
                time.sleep(0.02)

        settle(1.0)
        asked: list = []
        real, system_selection_view.open_system_selection_dialog = (system_selection_view.open_system_selection_dialog,
                                                                    lambda editor: asked.append(editor))
        tk_windows: list = []
        init = tk.Toplevel.__init__
        tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), tk_windows.append(type(self).__name__))[0]
        try:
            window.last_model_form_dialog = None
            window.editor.open_system_selection_calculator()
            settle(0.8)
        finally:
            tk.Toplevel.__init__ = init
            system_selection_view.open_system_selection_dialog = real
        dialog = getattr(window, "last_model_form_dialog", None)
        title = dialog.windowTitle() if dialog is not None else ""
        fields = sorted(getattr(dialog, "widgets", {}) or {})
        visible = bool(dialog is not None and dialog.isVisible())
        if dialog is not None:
            dialog.close()
        return (dialog is not None and title == TITLE and visible and set(INPUTS) <= set(fields)
                and tk_windows == [] and asked == [],
                f"in the Qt shell the command opens a Qt form titled {title!r} (visible {visible}) with the inputs "
                f"{[key for key in INPUTS if key in fields]}; Tk windows made {tk_windows}; the Tk view asked for "
                f"{len(asked)} times")

    return _claims((("Q", claim_q),))


def _run(call: str, needs: str, claim: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        "from KrakenOS.UI.validate_system_selection_view import qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a Tk/Qt teardown crash must not lose it)
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
    try:
        rows = pure_checks()
    except Exception as exc:
        rows = [["S", False, f"raised {type(exc).__name__}: {exc}"]]
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
