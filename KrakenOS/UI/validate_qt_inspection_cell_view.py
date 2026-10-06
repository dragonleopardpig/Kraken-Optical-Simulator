"""Guard for bugs/0967: the Inspection Cell VIEW is a Qt window in the Qt shell, over one session.

"Open Cell View" opened a Tk window in the Qt shell: on screen, and dead -- nothing pumps Tk there,
so it never repainted, took no click and never noticed a saved station layout. It was the last
window a Qt user could reach that was a `tk.Toplevel`.

  P  the session (`services/inspection_cell_session.py`), no display, on a SCRIPTED clock, with the
     composition stubbed (three actors, two stations):
       P1 compose puts every composed actor into the view's renderer, maps the stations' actors to
          their faces, says the cell's summary, counts itself, and closes the PREVIOUS off-screen
          plotter only once its actors are replaced; a composition that fails says so and leaves
          the scene as it was
       P2 a station opens through the shell's own layout loader when it gave one, else through the
          editor's; the editor's window is brought forward; a face with no layout is refused
       P3 the watch is ONE timer on the host at 2000 ms: unchanged files compose nothing, a touched
          file composes once, and it re-arms itself; close() cancels it, closes the plotter and
          empties the renderer, and nothing composes afterwards
       P4 the STEP export asks its file through the host (with the view as parent): a cancel writes
          nothing, a path is exported and reported
       P5 the opener: with a shell's `show_inspection_cell` the SHELL is handed a session and the Tk
          window module is not asked; with none, the Tk opener is
  Q  in a real Qt shell, with two real stations (the fixtures in git): the form's own "Open Cell
     View" opens a Qt dialog, not modal, with the session's buttons, and NO Tk window is made; its
     view is a real OpenGL render window holding the composed actors, both stations reachable. A
     REAL double-click on the top station opens that station's layout in the shell (the editor's
     file, the shell's table). Touching that file re-composes the cell -- the watch fires on Qt's
     clock. The Export button asks through the host. Close ends the session and the shell goes on
     drawing
  T  the Tk window is a view of the same session: its buttons are the session's, its status line is
     the session's, and closing it closes the session
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RESULT_MARK = "CELLVIEW_RESULT "
SKIP_MARK = "CELLVIEW_SKIP "
FRONT_SCENE = Path("test_fixtures/Basler_Telecentric.py")
TOP_SCENE = Path("test_fixtures/machine_vision_Pyrite90_0.3X.py")
PART = {"width_mm": 60, "height_mm": 40, "depth_mm": 20}


class _FakePlotter:
    """What the session needs of a composed pyvista plotter: named actors, and close()."""

    def __init__(self, names, log) -> None:
        from types import SimpleNamespace

        from vtkmodules.vtkRenderingCore import vtkActor

        self.renderer = SimpleNamespace(actors={name: vtkActor() for name in names})
        self.name = f"plotter{len(log['made']) + 1}"
        self._log = log
        log["made"].append(self.name)

    def close(self) -> None:
        # were this plotter's own actors still in the view when it was closed?
        view = self._log.get("renderer")
        self._log["own_actors_in_view_at_close"].append(
            bool(view is not None and any(view.HasViewProp(actor) for actor in self.renderer.actors.values())))
        self._log["closed"].append(self.name)


def _stub_composition(cell_service, log, layouts):
    """Replace the heavy composition by three actors, two of them stations'."""
    def compose(cell, *, off_screen=False, trace_rays=True):
        if log.get("fail"):
            raise RuntimeError("station file unreadable")
        log["props_at_compose"].append(log["renderer"].GetViewProps().GetNumberOfItems() if log.get("renderer") else None)
        log["closed_at_compose"].append(list(log["closed"]))
        plotter = _FakePlotter(["cell_part", "front_body", "top_body"], log)
        report = {"stations": [{"face": face, "layout": str(layouts[face]), "actors": 1, "object_point_cell": [0.0, 0.0, 0.0],
                                "bounds": None} for face in ("front", "top")],
                  "errors": [], "interferences": [], "station_actor_keys": {"front": ["front_body"], "top": ["top_body"]}}
        return plotter, report

    return compose


def pure_checks() -> list:
    from types import SimpleNamespace

    from vtkmodules.vtkRenderingCore import vtkRenderer

    from KrakenOS.UI.panels import inspection_cell_window as tk_window
    from KrakenOS.UI.services import inspection_cell as cell_service
    from KrakenOS.UI.services import inspection_cell_session as cell_session
    from KrakenOS.UI.uihost import ScriptedUiHost

    root = Path(tempfile.mkdtemp(prefix="cellview0967_"))
    layouts = {"front": root / "front.py", "top": root / "top.py"}
    for path in layouts.values():
        path.write_text("# station\n", encoding="utf-8")
    cell = {"part": PART, "stations": {face: {"layout": str(path), "enabled": True} for face, path in layouts.items()}}
    log = {"made": [], "closed": [], "props_at_compose": [], "closed_at_compose": [], "own_actors_in_view_at_close": []}
    real_compose, real_export = cell_service.compose_cell_plotter, cell_service.export_cell_step
    cell_service.compose_cell_plotter = _stub_composition(cell_service, log, layouts)
    exported: list = []
    cell_service.export_cell_step = lambda spec, path: (exported.append(str(path)), {"stations": [1, 2]})[1]
    rows = []
    try:
        # ---- P1
        loaded: list = []
        editor = SimpleNamespace(layout_files={}, load_layout_by_name=lambda name: loaded.append(name))
        host = ScriptedUiHost(answers={"asksaveasfilename": ["", str(root / "cell.step")]})
        session = cell_session.InspectionCellSession(editor, cell, host=host)
        renderer = log["renderer"] = vtkRenderer()
        draws: list = []
        session.attach(renderer, lambda: draws.append(1))
        said: list = []
        session.on_status(said.append)
        first = session.compose()
        props_first = renderer.GetViewProps().GetNumberOfItems()
        faces = sorted(set(session.actor_face.values()))
        summary_said = said[-1]
        second = session.compose()
        closed_before_second_transplant = log["closed_at_compose"][1]
        replaced_first = list(log["own_actors_in_view_at_close"])
        log["fail"] = True
        failed = session.compose()
        log["fail"] = False
        after_failure = (renderer.GetViewProps().GetNumberOfItems(), session.compose_count, said[-1])
        rows.append(["P1", bool(first) and props_first == 3 and faces == ["front", "top"] and len(session.actor_face) == 2
                     and "front" in summary_said and "top.py" in summary_said and said[1] == cell_session.COMPOSING
                     and bool(second) and session.compose_count == 2 and closed_before_second_transplant == []
                     and log["closed"] == ["plotter1"] and replaced_first == [False] and failed == {} and after_failure[0] == 3
                     and after_failure[1] == 2 and "failed" in after_failure[2] and len(draws) == 2,
                     f"first compose: {props_first} actors in the view, stations {faces}, status {summary_said.splitlines()[0]!r} "
                     f"after {said[1]!r}; second compose: count {session.compose_count}, plotters closed while it composed "
                     f"{closed_before_second_transplant}, closed after it {log['closed']} -- with its own actors still in the "
                     f"view: {replaced_first}; a failed composition returns "
                     f"{failed}, leaves {after_failure[0]} actors and count {after_failure[1]}, says {after_failure[2]!r}; "
                     f"the view was drawn {len(draws)} times"])

        # ---- P2
        own = session.open_station("top")
        own_state = (list(loaded), editor.layout_files.get("cell_top"), session.status)
        shell_loaded: list = []
        raised: list = []
        session.open_layout = shell_loaded.append
        session.raise_editor = lambda: raised.append(1)
        through_shell = session.open_station("front")
        refused = session.open_station("back")
        rows.append(["P2", own and own_state[0] == ["cell_top"] and own_state[1] == layouts["top"]
                     and "Opened the top station" in own_state[2] and through_shell and shell_loaded == [layouts["front"]]
                     and loaded == ["cell_top"] and raised == [1] and refused is False and "no station layout" in session.status,
                     f"with no shell loader the editor loads {own_state[0]} ({Path(str(own_state[1])).name}); with one the shell "
                     f"is handed {[p.name for p in shell_loaded]} and the editor's own loader is not called again "
                     f"({loaded}); the editor is brought forward {len(raised)}x; a face with no layout: {refused}, "
                     f"{session.status!r}"])

        # ---- P3
        session.open_layout = None
        count_before = session.compose_count
        session.start_watching()
        session.start_watching()
        armed = host.pending()
        ran_early = host.run_due(cell_session.InspectionCellSession.POLL_MS - 1)
        ran_due = host.run_due(1)
        after_quiet_poll = (session.compose_count - count_before, host.pending())
        time.sleep(0.05)
        stamp = time.time() + 5.0
        os.utime(layouts["top"], (stamp, stamp))
        host.run_due(cell_session.InspectionCellSession.POLL_MS)
        after_touch = (session.compose_count - count_before, host.pending())
        session.close()
        session.close()
        os.utime(layouts["top"], (stamp + 5.0, stamp + 5.0))
        ran_after_close = host.run_due(10 * cell_session.InspectionCellSession.POLL_MS)
        late = (session.compose(), session.check_station_files(), session.compose_count - count_before)
        rows.append(["P3", armed == 1 and ran_early == 0 and ran_due == 1 and after_quiet_poll == (0, 1)
                     and after_touch == (1, 1) and session.closed and host.pending() == 0 and ran_after_close == 0
                     and late == ({}, False, 1) and renderer.GetViewProps().GetNumberOfItems() == 0
                     and log["closed"][-1] == log["made"][-1] and len(log["closed"]) == len(log["made"]),
                     f"start_watching twice arms {armed} timer; it runs at 1999 ms {ran_early}x, at 2000 ms {ran_due}x; a quiet "
                     f"poll: composes {after_quiet_poll[0]}, timers armed {after_quiet_poll[1]}; after a touched file: composes "
                     f"{after_touch[0]}, armed {after_touch[1]}; close(): timers {host.pending()}, callbacks run later "
                     f"{ran_after_close}, the renderer holds {renderer.GetViewProps().GetNumberOfItems()}, plotters closed "
                     f"{len(log['closed'])} of {len(log['made'])}; compose and check after close: {late[:2]}"])

        # ---- P4
        parent = object()
        again = cell_session.InspectionCellSession(editor, cell, host=host)
        again.dialog_parent = parent
        cancelled = again.export_step()
        nothing_written = list(exported)
        written = again.export_step()
        asked = host.asked("asksaveasfilename")
        rows.append(["P4", cancelled == "" and nothing_written == [] and written == str(root / "cell.step")
                     and exported == [str(root / "cell.step")] and len(asked) == 2 and asked[0][1].get("parent") is parent
                     and asked[0][1].get("title") == "Export Cell STEP" and "Cell STEP written: cell.step (2 stations)" == again.status,
                     f"asked the host {len(asked)}x (title {asked[0][1].get('title')!r}, the view as parent "
                     f"{asked[0][1].get('parent') is parent}); a cancel exported {nothing_written}; a path exported "
                     f"{[Path(p).name for p in exported]} and says {again.status!r}"])

        # ---- P5
        handed: list = []
        tk_asked: list = []
        real_open = tk_window.open_inspection_cell_window
        tk_window.open_inspection_cell_window = lambda owner, spec: tk_asked.append(spec)
        try:
            shell_owner = SimpleNamespace()
            shell_owner.show_inspection_cell = lambda s: (handed.append(s), s)[1]
            from_shell = cell_session.open_inspection_cell_view(shell_owner, cell)
            asked_tk_under_shell = len(tk_asked)
            from_tk = cell_session.open_inspection_cell_view(SimpleNamespace(), cell)
        finally:
            tk_window.open_inspection_cell_window = real_open
        rows.append(["P5", len(handed) == 1 and from_shell is handed[0] and isinstance(from_shell, cell_session.InspectionCellSession)
                     and asked_tk_under_shell == 0 and len(tk_asked) == 1 and from_tk is None,
                     f"with a shell: handed {len(handed)} session(s), the Tk opener asked {asked_tk_under_shell}x; with none: "
                     f"the Tk opener asked {len(tk_asked) - asked_tk_under_shell}x (it gave no window, so the caller got {from_tk})"])
    finally:
        cell_service.compose_cell_plotter, cell_service.export_cell_step = real_compose, real_export
    return rows


def _real_cell(root: Path) -> tuple[dict, dict]:
    """Two real stations, as PRIVATE copies -- the watch test touches one of them."""
    copies = {"front": root / "station_front.py", "top": root / "station_top.py"}
    shutil.copyfile(FRONT_SCENE, copies["front"])
    shutil.copyfile(TOP_SCENE, copies["top"])
    return ({"part": PART, "stations": {face: {"layout": str(path), "enabled": True} for face, path in copies.items()}}, copies)


def qt_checks() -> list:
    import tkinter as tk

    import numpy as np
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QDialog

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.row_forms import build_inspection_cell_form
    from KrakenOS.UI.services import inspection_cell as cell_service
    from KrakenOS.UI.services import inspection_cell_session as cell_session
    from KrakenOS.UI.uihost import host_of

    app, window = build(["guard"])
    window.resize(1500, 950)
    window.show()
    app.processEvents()
    window.build_scene()
    editor = window.editor

    def settle(seconds: float = 0.3) -> None:
        end = time.time() + seconds
        while time.time() < end:
            app.processEvents()
            time.sleep(0.02)

    def wait_for(condition, seconds: float) -> bool:
        end = time.time() + seconds
        while time.time() < end:
            if condition():
                return True
            settle(0.2)
        return bool(condition())

    settle(1.0)
    root = Path(tempfile.mkdtemp(prefix="cellviewqt0967_"))
    cell, copies = _real_cell(root)
    editor.inspection_cell_spec = cell_service.normalize_cell_spec(cell)
    tk_windows: list = []
    init = tk.Toplevel.__init__
    tk.Toplevel.__init__ = lambda self, *a, **k: (init(self, *a, **k), tk_windows.append(type(self).__name__))[0]
    rows = []
    try:
        form = build_inspection_cell_form(editor)
        view = next(action for action in form.actions if action.key == "view")
        message = view.run(form, host_of(window))            # the form's own "Open Cell View"
        dialog = window.last_inspection_cell_dialog
        session = getattr(editor, "inspection_cell_view", None)
        opened = (isinstance(dialog, QDialog) and dialog.isVisible() and not dialog.isModal()
                  and isinstance(session, cell_session.InspectionCellSession) and dialog.session is session)
        said_at_once = str(message)
        composed = opened and wait_for(lambda: session.compose_count >= 1, 240.0)
        settle(0.5)
        if not composed:
            return [["Q", False, f"the Qt view did not open and compose: opened {opened}, action said {said_at_once!r}, "
                                 f"Tk windows {tk_windows}, status {getattr(session, 'status', None)!r}"]]
        render_window = dialog.vtk_widget.GetRenderWindow()
        props = dialog.renderer.GetViewProps().GetNumberOfItems()
        faces = sorted(set(session.actor_face.values()))
        buttons = list(dialog.buttons)
        status_shown = dialog.status.text()

        # a REAL double-click on the top station's body
        top = next(station for station in session.report["stations"] if station["face"] == "top")
        b = top["bounds"]
        centre = np.array([(b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2])
        dialog.renderer.SetWorldPoint(float(centre[0]), float(centre[1]), float(centre[2]), 1.0)
        dialog.renderer.WorldToDisplay()
        dx, dy, _dz = dialog.renderer.GetDisplayPoint()
        try:
            ratio = float(dialog.vtk_widget._getPixelRatio())
        except Exception:
            ratio = 1.0
        height = render_window.GetSize()[1]
        point = QPoint(int(round(dx / ratio)), int(round((height - 1 - dy) / ratio)))
        loads: list = []
        real_load = session.open_layout
        session.open_layout = lambda path: (loads.append(Path(path)), real_load(path))[1]
        QTest.mouseDClick(dialog.vtk_widget, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, point)
        settle(1.5)
        opened_file = Path(str(editor.current_layout_file or ""))
        table_rows = window.rows_model.rowCount()
        after_click = session.status

        # the watch, on Qt's clock: touch the station, pump the Qt loop, nothing else
        before = session.compose_count
        time.sleep(1.1)
        os.utime(copies["top"], None)
        recomposed = wait_for(lambda: session.compose_count > before, 240.0)
        settle(0.5)

        # Export asks through the host; the STEP writer itself is not this guard's subject
        host = host_of(window)
        asked: list = []
        exported: list = []
        real_export = cell_service.export_cell_step
        cell_service.export_cell_step = lambda spec, path: (exported.append(str(path)), {"stations": [1, 2]})[1]
        host.asksaveasfilename = lambda **options: (asked.append(options), str(root / "cell.step"))[1]
        try:
            QTest.mouseClick(dialog.buttons["Export Cell STEP..."], Qt.MouseButton.LeftButton)
            settle(0.3)
        finally:
            del host.asksaveasfilename
            cell_service.export_cell_step = real_export
        export_said = session.status

        # Close: the session ends, the render window is finalized, and the shell goes on drawing
        QTest.mouseClick(dialog.buttons["Close"], Qt.MouseButton.LeftButton)
        settle(0.5)
        closed = (not dialog.isVisible(), session.closed, dialog.renderer.GetViewProps().GetNumberOfItems())
        count_at_close = session.compose_count
        os.utime(copies["top"], None)
        settle(cell_session.InspectionCellSession.POLL_MS / 1000.0 + 1.0)
        quiet_after_close = session.compose_count == count_at_close
        inspector = window._scene_inspector()
        drew_after = False
        if inspector is not None:
            inspector.render()
            settle(0.3)
            drew_after = True
        rows.append(["Q", opened and tk_windows == [] and render_window.GetClassName() == "vtkXOpenGLRenderWindow"
                     and props > 10 and faces == ["front", "top"]
                     and buttons == [label for label, _method in session.BUTTONS] + ["Close"]
                     and "front" in status_shown and "top" in status_shown
                     and loads == [copies["top"]] and opened_file.resolve() == copies["top"].resolve()
                     and table_rows == len(editor.rows) > 2 and "Opened the top station" in after_click
                     and recomposed and len(asked) == 1 and asked[0].get("parent") is dialog
                     and exported == [str(root / "cell.step")] and "Cell STEP written" in export_said
                     and closed == (True, True, 0) and quiet_after_close and drew_after,
                     f"a Qt window, not modal, over the form's session: {opened} (the action said {said_at_once.splitlines()[0]!r}); "
                     f"Tk windows made {tk_windows}; view {render_window.GetClassName()} holding {props} actors, stations {faces}; "
                     f"buttons {buttons}; a double-click at {point.x()},{point.y()} loaded {[p.name for p in loads]} through the "
                     f"shell -- the editor's file is {opened_file.name}, the table shows {table_rows} of {len(editor.rows)} rows, "
                     f"status {after_click.split(' -- ')[0]!r}; touching that file re-composed the cell on Qt's clock: "
                     f"{recomposed} (count {before} -> {session.compose_count}); Export asked the host {len(asked)}x with the "
                     f"dialog as parent {bool(asked) and asked[0].get('parent') is dialog} and said {export_said!r}; Close: "
                     f"(hidden, session closed, actors left) {closed}, no compose after it {quiet_after_close}, the shell's "
                     f"scene drew afterwards {drew_after}"])
    finally:
        tk.Toplevel.__init__ = init
    return rows


def tk_checks() -> list:
    """T: the Tk window over a session -- the composition stubbed, the window real."""
    from tkinter import ttk

    from vtkmodules.vtkRenderingCore import vtkActor  # noqa: F401  (the stub's actors)

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.panels.inspection_cell_window import InspectionCellWindow
    from KrakenOS.UI.services import inspection_cell as cell_service
    from KrakenOS.UI.services import inspection_cell_session as cell_session

    root = Path(tempfile.mkdtemp(prefix="cellviewtk0967_"))
    layouts = {"front": root / "front.py", "top": root / "top.py"}
    for path in layouts.values():
        path.write_text("# station\n", encoding="utf-8")
    cell = {"part": PART, "stations": {face: {"layout": str(path), "enabled": True} for face, path in layouts.items()}}
    log = {"made": [], "closed": [], "props_at_compose": [], "closed_at_compose": [], "own_actors_in_view_at_close": []}
    real_compose = cell_service.compose_cell_plotter
    cell_service.compose_cell_plotter = _stub_composition(cell_service, log, layouts)
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda *a, **k: None
    try:
        session = cell_session.InspectionCellSession(editor, cell)
        window = InspectionCellWindow(editor, session=session)
        if not window.available:
            return [["T", True, f"SKIP: the Tk VTK widget is unavailable here ({window.unavailable_reason})"]]
        for _ in range(4):
            window.update()

        def texts(widget) -> list:
            found = [str(widget.cget("text"))] if isinstance(widget, ttk.Button) else []
            for child in widget.winfo_children():
                found.extend(texts(child))
            return found

        buttons = texts(window)
        props = window._renderer.GetViewProps().GetNumberOfItems()
        status_shown = str(window.status_var.get())
        same = window.session is session and window._compose_count == session.compose_count == 1
        window.destroy()
        closed = (session.closed, len(log["closed"]) == len(log["made"]))
    finally:
        cell_service.compose_cell_plotter = real_compose
    return [["T", same and buttons == [label for label, _method in session.BUTTONS] + ["Close"] and props == 3
             and status_shown == session.status and "front" in status_shown and closed == (True, True),
             f"the Tk window shows the session it was handed: {same}; buttons {buttons}; {props} actors in its view; its "
             f"status line is the session's ({status_shown.splitlines()[0]!r}); destroying it: (session closed, every "
             f"plotter closed) {closed}"]]


def _run(call: str, needs: str) -> list:
    driver = (
        "import json, os\n"
        "if not os.environ.get('DISPLAY'):\n"
        f"    print({SKIP_MARK!r} + 'no DISPLAY')\n"
        "    raise SystemExit(0)\n"
        f"{needs}"
        f"from KrakenOS.UI.validate_qt_inspection_cell_view import qt_checks, tk_checks\n"
        # flushed, then exit WITHOUT interpreter teardown (a VTK/Qt teardown crash must not lose it)
        f"print({RESULT_MARK!r} + json.dumps({call}), flush=True)\n"
        "os._exit(0)\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True, timeout=1500,
                              env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return [["X", False, f"{call} timed out"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return [["X", True, f"SKIP {call}: " + line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-8:]
    return [["X", False, f"{call} exit {proc.returncode}; " + " | ".join(tail)]]


def run_checks() -> tuple[bool, list[str]]:
    rows = pure_checks()
    if FRONT_SCENE.exists() and TOP_SCENE.exists():
        rows += _run("qt_checks()", "import PySide6\n")
    else:
        rows.append(["Q", False, f"the station fixtures are missing: {FRONT_SCENE}, {TOP_SCENE}"])
    rows += _run("tk_checks()", "")
    return all(ok for _k, ok, _d in rows), [f"{k} = {d}" if ok else f"{k} FAILED: {d}" for k, ok, d in rows]


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
