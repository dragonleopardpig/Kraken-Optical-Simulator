"""Display-free guard: the 2D layout plot in Qt, and the last two Tk leaks out of the model
(bugs/0893, docs/design_qt_migration.md phase 6).

The 2D plot was never view code -- the model draws into `editor.ax` and calls
`editor.canvas.draw_idle()`. What WAS toolkit-specific was the canvas, plus two things that had
leaked into `services/layout_plot_interaction.py`:

* a Tk `<Button-1>` binding whose event needed `get_tk_widget().winfo_height()` to flip y, and
* `canvas.get_tk_widget().configure(cursor=...)`.

Both are gone. The click is a matplotlib `button_press_event`, which already reports display
coordinates in the frame `get_window_extent` uses, and the cursor goes through
`editor.set_plot_cursor(name)`, which each shell implements.

  S  no `get_tk_widget()` is left in the plot-interaction service
  C  the cursor seam: the model asks by name, and no-ops when no view implements it
  Q  the Qt canvas IS the editor's canvas, and refresh_plot draws a real layout into it
  L  `refresh_plot` REPLACES editor.ax, so the view must read it live, not cache it
  K  a matplotlib click routes to the model and reaches the layout axis
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "@@QT-RESULT@@"
SKIP_MARK = "@@QT-SKIP@@"
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    from matplotlib.backend_bases import MouseButton, MouseEvent

    from KrakenOS.UI.qt.app import build

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()
    plot = window.build_plot2d()
    same = [window.editor.figure is plot.figure, window.editor.canvas is plot.canvas]
    window.load_layout_path(SCENE)
    app.processEvents()

    first_axes = window.editor.ax
    window.editor._preview_trace_deferred_until_requested = False
    window.editor.refresh_plot(suppress_analysis=True)
    app.processEvents()
    live = plot.axes
    drawn = [len(live.lines), len(live.collections), len(live.texts)]
    replaced = live is not first_axes

    plot.set_cursor("hand2")
    plot.set_cursor("")

    opened: list = []
    window.editor._open_plot_axis_once = lambda axis: opened.append(axis)
    box = live.get_window_extent(plot.figure.canvas.get_renderer())
    event = MouseEvent("button_press_event", plot.canvas,
                       float(box.x0 + box.width / 2), float(box.y0 + box.height / 2),
                       MouseButton.LEFT)
    handled = window.editor._on_plot_widget_click(event)

    window.close()
    return [same, drawn, replaced, str(live.get_title()), str(handled), len(opened)]


def _run_qt_subprocess() -> tuple[str, object]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the shell needs an X server')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0893_qt_layout_plot import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks(), default=str))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", "the Qt subprocess timed out after 900 s"
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", line[len(SKIP_MARK):]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", f"exit {proc.returncode}; " + " | ".join(tail)


def run_checks() -> tuple[bool, list[str]]:
    import inspect

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import layout_plot_interaction
    from KrakenOS.UI.panels import main_window as tk_window
    from KrakenOS.UI.qt import plot2d as qt_plot

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    service = inspect.getsource(layout_plot_interaction)
    tk_source = inspect.getsource(tk_window)
    qt_source = inspect.getsource(qt_plot)
    # look for the CALL, not the word: the docstring that explains the fix says
    # "get_tk_widget()" too, and an earlier version of this check failed on its own prose
    ok("canvas.get_tk_widget(" not in service
       and "winfo_height(" not in service
       and 'mpl_connect("button_press_event"' in tk_source
       and 'mpl_connect("button_press_event"' in qt_source,
       "S: no get_tk_widget() call and no winfo_height() are left in the plot-interaction "
       "service, and BOTH shells connect the same matplotlib button_press_event")

    ok("_set_plot_cursor" in service and 'getattr(self, "set_plot_cursor", None)' in service
       and "_set_tk_plot_cursor" in tk_source and "def set_cursor" in qt_source
       and "CURSORS" in qt_source,
       "C: the model asks for a cursor BY NAME through set_plot_cursor, each shell implements "
       "it, and a view that does not simply has no cursor to set")

    editor = KrakenLayoutEditor(headless=True)
    try:
        # a headless editor has no view: the seam must be silent, not an AttributeError
        editor._set_plot_cursor("hand2")
        ok(True, "C2: a headless editor takes the cursor call and does nothing with it")
    finally:
        editor.destroy()

    status, payload = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q: {payload}")
        return state["ok"], notes
    if status == "error":
        ok(False, f"Q: the Qt subprocess failed -- {payload}")
        return state["ok"], notes

    same, drawn, replaced, title, handled, opened = payload
    ok(same == [True, True] and sum(int(count) for count in drawn) > 50,
       f"Q: the editor's figure and canvas ARE the Qt ones, and refresh_plot drew "
       f"{drawn[0]} lines / {drawn[1]} collections / {drawn[2]} texts titled {title!r}")
    ok(bool(replaced),
       "L: refresh_plot REPLACED editor.ax, which is why the view reads it live instead of "
       "caching the axes it created")
    # which branch fires depends on what is under the centre of the layout -- a ray, a row, or
    # nothing, in which case the axis opens. "break" means the model handled it, which is the
    # claim; pinning one branch would pin the scene instead.
    ok(handled == "break",
       f"K: a matplotlib click in the layout axis reached the model and it acted (returned "
       f"{handled!r}; it opened {opened} axis/axes, the rest was a pick)")

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
