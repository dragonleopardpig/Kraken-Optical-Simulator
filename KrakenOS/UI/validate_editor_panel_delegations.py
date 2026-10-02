"""Guard: every editor command that delegates to a panel reaches a method the panel DEFINES (bugs/0941).

The panel classes (`MainXxxDialog`) forward any attribute they lack to the editor through
``__getattr__``. So when a refactor removes a panel method but leaves the editor's one-line
delegation ``self._main_xxx().method()`` in place, the call goes panel -> editor -> panel ... and
recurses until Python gives up. 0888 did exactly that to "Add Component to Current Path View": both
menu items were a RecursionError in both shells for a week, and nothing noticed.

  S  static: for every ``self._main_<panel>().<method>(`` in the editor's mixins, the panel class
     (the factory's return annotation, or the class it constructs) defines <method> itself
  R  runtime, in a real Tk editor on om05a_folded and in the real Qt shell: the menu command
     "Add Component to Current Path View" finishes without a RecursionError -- it asks for a Path
     view first (no traced path is chosen), through the shell's own dialog host
"""
from __future__ import annotations

import inspect
import json
import os
import re
import subprocess
import sys
import typing
from pathlib import Path

RESULT_MARK = "DELEG_RESULT "
SCENE = Path("attachment/om05a_folded.py")


def delegation_failures() -> tuple[int, list[tuple]]:
    import KrakenOS.UI.layout_editor as le
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    broken, checked = [], 0
    for cls in KrakenLayoutEditor.__mro__:
        if not getattr(cls, "__module__", "").startswith("KrakenOS.UI"):
            continue
        for name, fn in list(vars(cls).items()):
            if not callable(fn):
                continue
            try:
                source = inspect.getsource(fn)
            except (OSError, TypeError):
                continue
            for factory, target in re.findall(r"self\.(_main_[a-z_0-9]+)\(\)\.([a-zA-Z_0-9]+)", source):
                factory_fn = getattr(KrakenLayoutEditor, factory, None)
                if factory_fn is None:
                    broken.append((cls.__name__, name, factory, target, "no such factory"))
                    continue
                panel = typing.get_type_hints(factory_fn).get("return")
                if not isinstance(panel, type):
                    match = re.search(r"dialog = ([A-Z][A-Za-z0-9_]+)\(", inspect.getsource(factory_fn))
                    panel = getattr(le, match.group(1), None) if match else None
                if not isinstance(panel, type):
                    continue
                checked += 1
                if not any(target in vars(k) for k in panel.__mro__ if k is not object):
                    broken.append((cls.__name__, name, factory, target, panel.__name__))
    return checked, broken


def runtime_checks(shell: str) -> list:
    os.environ.pop("WAYLAND_DISPLAY", None)
    os.environ["QT_QPA_PLATFORM"] = "xcb"
    shown: list = []
    if shell == "qt":
        from KrakenOS.UI.qt.app import build
        from KrakenOS.UI.uihost.qt_host import QtUiHost

        QtUiHost.showinfo = lambda self, title=None, message=None, **_k: shown.append((title, message))
        QtUiHost.showerror = lambda self, title=None, message=None, **_k: shown.append((title, message))
        app, window = build(["guard"])
        window.show()
        app.processEvents()
        window.load_layout_path(SCENE)
        editor = window.editor
    else:
        import tkinter.messagebox as tkmb

        from KrakenOS.UI.layout_editor import KrakenLayoutEditor

        tkmb.showinfo = lambda title=None, message=None, **_k: shown.append((title, message))
        tkmb.showerror = lambda title=None, message=None, **_k: shown.append((title, message))
        editor = KrakenLayoutEditor(headless=True)
        editor.load_layout_by_name(SCENE.stem)
    error = ""
    try:
        editor.open_current_path_component_placement()
    except RecursionError:
        error = "RecursionError"
    except Exception as exc:  # any other failure is reported, not hidden
        error = f"{type(exc).__name__}: {exc}"
    asked = any(title == "Path Component" and "Path view" in str(message) for title, message in shown)
    return [[f"R-{shell}", not error and asked,
             f"{shell}: the command returned without error ({error or 'none'}) and asked for a Path view: {asked} {shown[:1]}"]]


def _run(shell: str) -> list:
    driver = (
        "import json, os\n"
        "from KrakenOS.UI.validate_editor_panel_delegations import runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(runtime_checks({shell!r})), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=900,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [[f"R-{shell}", False, "timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-4:]
    return [[f"R-{shell}", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    checked, broken = delegation_failures()
    rows = [["S", checked >= 100 and not broken,
             f"{checked} editor -> panel delegations; targeting a method the panel lacks: {broken}"]]
    if SCENE.exists() and os.environ.get("DISPLAY"):
        rows += _run("tk") + _run("qt")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
