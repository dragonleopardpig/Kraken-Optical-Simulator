"""Display-free guard: the Qt shell (bugs/0855, docs/design_qt_migration.md phase 2).

`KrakenOS/UI/qt/` is the Qt-side VIEW layer over the existing model: a `KrakenLayoutEditor`
reached through the 0851 seam with a `QtUiHost` answering its dialogs. The claim worth guarding is
not "a window opens" -- it is that the Qt window drives the SAME model code the Tk editor drives,
and that what it shows comes from that model.

The Qt half runs in a SUBPROCESS on the xcb platform: a QApplication must never be created inside
the penta harness, which already holds a Tk interpreter and a live VTK render window. It needs a
DISPLAY (VTK draws through a real GL context and the model still builds a Tk tree); without one,
or without PySide6, the Q sections report SKIP and the rest still runs.

  A  importing `KrakenOS.UI.qt` loads no Qt binding (a Tk run must not pull in PySide6)
  B  every declared action names a real main-window method, and the menus follow the declaration
  Q1 the window builds: menus, the docked surface table with its object name, and a viewport
     container that is the central widget (the viewport is built after `show()`, on purpose)
  Q2 the Qt table shows the REAL rows -- row count, headings and cell values read back to
     `editor.rows`, with no copy in between
  Q3 model -> view: `status_var.set(...)` from model code reaches the status bar, through the
     same `trace_add` a tk.StringVar and an ObservableValue both have
  Q4 the viewport: an OpenGL render window, a TRACKBALL style (the default switch style starts in
     joystick mode and a drag would do nothing), bodies drawn with scalar colouring off
  Q5 `File -> Open Layout` triggered as an ACTION runs the model's own `open_layout()`, takes the
     path from the Qt file dialog, and the table and title follow -- the seam, end to end
  Q6 a Qt mouse drag on the viewport rotates VTK's camera
  Q7 closing drops the trace (last, because closing finalizes the VTK widget -- rendering after
     it is the bugs/0294 use-after-free)
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


def qt_runtime_checks() -> list[list]:
    """Drive the REAL shell. Returns [name, ok, detail] rows."""
    import time

    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QDockWidget, QTableView

    from KrakenOS.UI.qt.actions import ACTIONS
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.qt.rows_table import COLUMNS
    from KrakenOS.UI.uihost import host_of
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    rows: list[list] = []

    def row(name, ok, detail):
        rows.append([name, bool(ok), detail])

    app, window = build(["kraken"])
    window.show()
    app.processEvents()
    window.build_viewport()

    def settle(turns=4):
        for _ in range(turns):
            window.viewport.render()
            app.processEvents()
            time.sleep(0.05)

    # ---- Q1 the window --------------------------------------------------------------------
    menu_titles = [menu.title() for menu in window.menus.values()]
    dock = window.findChild(QDockWidget, "SurfaceTableDock")
    table = window.findChild(QTableView)
    declared_menus = []
    for _name, title, *_rest in ACTIONS:
        if title not in declared_menus:
            declared_menus.append(title)
    row("Q1", menu_titles == declared_menus and dock is not None and table is not None
        and window.centralWidget() is window.viewport_host
        and window.viewport.widget.parent() is window.viewport_host,
        f"menus {menu_titles} match the declaration; the surface table is docked as "
        f"{dock.objectName()!r}; the viewport sits in the central container "
        f"(never reparented after construction)")

    # ---- Q2 the table reads the model -------------------------------------------------------
    window.load_layout_path(SCENE)
    settle()
    editor_rows = list(window.editor.rows)
    headings = [window.rows_model.headerData(i, Qt.Orientation.Horizontal)
                for i in range(window.rows_model.columnCount())]
    sampled = []
    mismatched = []
    for index in (0, len(editor_rows) // 2, len(editor_rows) - 1):
        for column, (heading, attribute, form) in enumerate(COLUMNS):
            shown = window.rows_model.data(window.rows_model.index(index, column))
            expected = form(getattr(editor_rows[index], attribute))
            if shown != expected:
                mismatched.append((index, heading, shown, expected))
        sampled.append((index, window.rows_model.data(window.rows_model.index(index, 1))))
    row("Q2", window.rows_model.rowCount() == len(editor_rows) == 25
        and headings == [c[0] for c in COLUMNS] and not mismatched,
        f"{window.rows_model.rowCount()} rows, headings {headings}; sampled names {sampled}"
        + (f" -- MISMATCHED {mismatched[:3]}" if mismatched else ""))

    # ---- Q3 model -> view ---------------------------------------------------------------------
    window.editor.status_var.set("Solve refused: 3.20 mm short.")
    app.processEvents()
    after_write = window.statusBar().currentMessage()
    row("Q3", after_write == "Solve refused: 3.20 mm short." and window._status_trace is not None,
        f"the status bar followed the model's write ({after_write!r}) through the trace the "
        f"variable carries, whether a tk.StringVar or an ObservableValue")

    # ---- Q4 the viewport ----------------------------------------------------------------------
    drawn = window.viewport.show_editor_scene(window.editor)
    settle()
    scalars_off = all(not actor.GetMapper().GetScalarVisibility()
                      for actor in window.viewport.body_actors.values())
    bounds = window.viewport.renderer.ComputeVisiblePropBounds()
    row("Q4", window.viewport.render_window.IsA("vtkOpenGLRenderWindow")
        and type(window.viewport.interactor_style).__name__ == "vtkInteractorStyleTrackballCamera"
        and len(drawn["bodies"]) >= 3 and drawn["elements"] and drawn["error"] is None
        and scalars_off and bounds[1] > bounds[0],
        f"{window.viewport.render_window.GetClassName()} with a "
        f"{type(window.viewport.interactor_style).__name__}; drew {len(drawn['elements'])} "
        f"optical elements and bodies {[b[0] for b in drawn['bodies']]} with scalar colouring "
        f"off ({scalars_off}); visible bounds span {bounds[1] - bounds[0]:.0f} mm")

    # ---- Q5 File -> Open, as an action, through the Qt host ----------------------------------
    asked = {}

    class FakeFileDialog:
        @staticmethod
        def getOpenFileName(parent, caption, directory, filt):
            asked.update(caption=caption, directory=directory, filt=filt)
            return str(SCENE), filt

    host = host_of(window.editor)
    window.editor.current_layout_file = None
    window.rows_model.refresh()
    window.setWindowTitle("cleared")
    host._dialog = lambda: FakeFileDialog  # instance attribute shadows QtUiHost._dialog
    try:
        window.action_manager["open"].trigger()
        app.processEvents()
    finally:
        del host._dialog
    row("Q5", isinstance(host, QtUiHost) and asked.get("caption") == "Open Kraken layout"
        and "*.py" in str(asked.get("filt"))
        and Path(str(window.editor.current_layout_file)).name == SCENE.name
        and window.rows_model.rowCount() == 25 and SCENE.name in window.windowTitle(),
        f"the action ran the model's own open_layout(): it asked the Qt host "
        f"{asked.get('caption')!r} with filter {asked.get('filt')!r}, loaded "
        f"{Path(str(window.editor.current_layout_file)).name}, and the table "
        f"({window.rows_model.rowCount()} rows) and title ({window.windowTitle()!r}) followed")

    # ---- Q6 the interaction bridge ------------------------------------------------------------
    settle()
    camera = window.viewport.renderer.GetActiveCamera()
    before = camera.GetPosition()
    widget = window.viewport.widget
    centre = QPointF(widget.rect().center())

    def send(kind, point, button, buttons):
        event = QMouseEvent(kind, point, widget.mapToGlobal(point.toPoint()).toPointF(),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(widget, event)
        app.processEvents()

    send(QEvent.Type.MouseButtonPress, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    for fraction in (0.3, 0.6, 1.0):
        send(QEvent.Type.MouseMove,
             QPointF(centre.x() + 160 * fraction, centre.y() + 90 * fraction),
             Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    send(QEvent.Type.MouseButtonRelease, QPointF(centre.x() + 160, centre.y() + 90),
         Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    after = camera.GetPosition()
    moved = max(abs(a - b) for a, b in zip(before, after))
    row("Q6", moved > 1.0,
        f"a Qt press-drag-release moved VTK's camera {moved:.1f} mm")

    # ---- Q7 closing, LAST: it finalizes the VTK widget --------------------------------------
    # Rendering into a closed VTK widget is a use-after-free (bugs/0294), so nothing may touch
    # the viewport after this.
    last_shown = window.statusBar().currentMessage()
    window.close()
    app.processEvents()
    window.editor.status_var.set("written after the window closed")
    app.processEvents()
    after_close = window.statusBar().currentMessage()
    row("Q7", after_close == last_shown != "written after the window closed",
        f"after close the trace is gone: the bar still reads {after_close!r} and the later model "
        f"write did not reach it")
    return rows


def _run_qt_subprocess() -> tuple[str, list[list]]:
    driver = (
        "import json, os, sys\n"
        "try:\n"
        "    import PySide6\n"
        "except Exception as exc:\n"
        f"    print({SKIP_MARK!r} + repr(exc))\n"
        "    raise SystemExit(0)\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY: the viewport needs a GL context')\n"
        "    raise SystemExit(0)\n"
        "from KrakenOS.UI.validate_open3d_0855_qt_shell import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    # Qt must land on the SAME window system VTK opens on: with WAYLAND_DISPLAY set, Qt goes to
    # the compositor and ignores the DISPLAY the harness's Xvfb provides.
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=900, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Qt subprocess", False, "timed out after 900 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Qt shell", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Qt subprocess", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.qt.actions import ACTIONS

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- A importing the Qt package pulls in no Qt binding -----------------------------------
    probe = ("import sys\n"
             "import KrakenOS.UI.qt as qt\n"
             "print(sorted(m for m in sys.modules if m.split('.')[0] in "
             "('PySide6', 'PyQt5', 'shiboken6')))\n")
    proc = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, timeout=180)
    loaded = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "<no output>"
    ok(proc.returncode == 0 and loaded == "[]",
       f"A: importing KrakenOS.UI.qt loaded no Qt binding ({loaded})")

    # ---- B every declared action names a real window method ----------------------------------
    import ast

    source = Path("KrakenOS/UI/qt/main_window.py").read_text(encoding="utf-8")
    defined = {node.name for node in ast.walk(ast.parse(source))
               if isinstance(node, ast.FunctionDef)}
    missing = [(name, method) for name, _menu, _text, _short, method, _tip in ACTIONS
               if method not in defined]
    ok(len(ACTIONS) >= 6 and not missing,
       f"B: all {len(ACTIONS)} declared actions name a method KrakenQtMainWindow defines"
       + (f" -- missing {missing}" if missing else ""))

    # ---- Q the shell itself, in its own process ----------------------------------------------
    status, rows = _run_qt_subprocess()
    if status == "skip":
        notes.append(f"SKIP Q1-Q6: {rows[0][2]}")
    else:
        for name, passed, detail in rows:
            ok(passed, f"{name}: {detail}")

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
