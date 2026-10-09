"""Guard: the Qt shell hosts the REAL 3D inspector, and Qt input drives it (bugs/0906,
docs/design_qt_migration.md phase 5a part 2).

0905 made the inspector's handlers reachable without Tk and proved that a gesture through genuine Tk
events and the same gesture through `dispatch_viewport_event` leave the camera in the same place.
This step puts the inspector itself in the Qt shell: `Kraken3DInspector(editor, vtk_host=...)`
draws into a QVTKRenderWindowInteractor, schedules on the shell's host, and never shows its Tk
Toplevel; `qt/inspector_view.InspectorView` turns Qt input into those same dispatches. So what a
Qt gesture does is what the Tk gesture does: Qt == dispatch here, dispatch == Tk in 0905.

Static (no Qt event loop):
  R  the Qt routing rule is the Tk binding rule (`button_handler`) for every button, modifier and
     phase -- except the right button's PRESS, which posts a Tk menu and is held back until 5c
  C  every cursor the inspector asks for has a Qt cursor shape that exists
  T  the inspector's viewport timers (live refresh, trailing hover re-pick, async-trace poll) and
     its "is the pointer over the viewport" test go through the host/seams, not a Tk object

In a real Qt shell (subprocess, xcb):
  W  the inspector is the editor's, available, on the shell's host, its Toplevel withdrawn; its
     renderer is in the Qt widget's window with the interactor observers and the navigation cube
  L  the 3D view is a usable size and the window fits the screen (measured: stacked forms had
     pushed it to 2141 px and left the inspector 0 px -- where nothing can be picked); since
     bugs/0951 it is the window's central scene, in no dock, so it cannot float
  O  an orbit (left drag), a Shift+left pan and a middle pan sent as Qt mouse events MOVE the
     camera and leave it where the same gestures dispatched as ViewportEvents leave it
  P  a Qt hover + click on a body selects exactly what the dispatched hover + click selects
  K2 (bugs/0957) one key press runs ONE handler: `s`, Escape and Delete each run their handler
     once and do not also reach VTK's own key observer (one `s` used to write two flag bundles);
     a key the inspector does not bind still goes to VTK
  K  Escape pressed on the Qt widget cancels an armed pick mode
  A  Alt pressed and released on the Qt widget turns edge hover ON and then OFF
  D  a right press dispatches nothing (no Tk menu under Qt); the release is still routed
  U  the cursor seam sets the Qt cursor; the pointer seam reports inside and outside
  S  the timers fire in the Qt loop: a live refresh and a trailing hover re-pick both RUN
  V  Open 3D View with the Qt inspector up re-uses it and keeps the Tk Toplevel withdrawn
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
RESULT_MARK = "GUARD0906:"
SKIP_MARK = "GUARD0906-SKIP:"


# ---- the Qt half -----------------------------------------------------------------------------
def qt_runtime_checks() -> list:
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QCursor, QKeyEvent, QMouseEvent
    from PySide6.QtWidgets import QApplication, QDockWidget

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.uihost import host_of
    from KrakenOS.UI.viewport_events import SHIFT, ViewportEvent, button_handler

    rows: list = []
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(20):
        app.processEvents()
    inspector = view.inspector
    widget = view.widget
    editor = window.editor

    # ---- W ---------------------------------------------------------------------------------
    interactor = inspector._vtk_interactor
    observed = [name for name in ("LeftButtonPressEvent", "MouseMoveEvent", "KeyPressEvent",
                                  "InteractionEvent", "EndInteractionEvent")
                if interactor is not None and interactor.HasObserver(name)]
    renderers = widget.GetRenderWindow().GetRenderers()
    in_window = any(renderers.GetItemAsObject(i) is inspector._renderer
                    for i in range(renderers.GetNumberOfItems()))
    # its Tk window is withdrawn and never shown -- or, when the shell was asked to build the
    # inspector without one (KRAKEN_QT_TK_FREE, bugs/0998), is not there at all
    from KrakenOS.UI.qt.tk_free import tk_free

    owned = inspector.__dict__.get("window")
    toplevel = "none" if owned is None else str(owned.state())
    withdrawn = toplevel == ("none" if tk_free("inspector") else "withdrawn")
    rows.append(["W", bool(inspector.available) and editor._three_d_inspector is inspector
                 and host_of(inspector) is window.ui and withdrawn and in_window
                 and len(observed) == 5 and inspector._navigation_cube is not None
                 and inspector._vtk_widget is widget,
                 f"the inspector is the editor's (available={inspector.available}), on the shell's "
                 f"host, its Toplevel {toplevel}; its renderer is in the Qt widget's "
                 f"window with observers {observed} and the navigation cube"])

    # ---- L ---------------------------------------------------------------------------------
    for _ in range(10):
        app.processEvents()
    # since bugs/0951 the inspector is the window's CENTRAL 3D scene, not a dock: it cannot float
    # (floating would recreate the native window VTK was handed), and the panels sit beside it
    screen = window.screen().availableGeometry().height()
    central = (window.centralWidget() is window.scene_stack
               and window.scene_stack.currentWidget() is window.inspector_host
               and widget.parentWidget() is window.inspector_host)
    docked = [dock.objectName() for dock in window.findChildren(QDockWidget) if dock.isAncestorOf(widget)]
    rows.append(["L", widget.height() >= 400 and window.height() <= screen and central and not docked,
                 f"the viewport is {widget.width()}x{widget.height()} px, the window "
                 f"{window.height()} px on a {screen} px screen; it is the central scene: {central}; "
                 f"docks holding it (it must not float): {docked}"])

    cam = inspector._renderer.GetActiveCamera()

    def camera():
        return (tuple(cam.GetPosition()), tuple(cam.GetFocalPoint()), tuple(cam.GetViewUp()))

    def set_camera(state) -> None:
        cam.SetPosition(*state[0])
        cam.SetFocalPoint(*state[1])
        cam.SetViewUp(*state[2])
        inspector._renderer.ResetCameraClippingRange()

    def same(a, b, tol=1e-6) -> bool:
        return all(abs(x - y) <= tol for ta, tb in zip(a, b) for x, y in zip(ta, tb))

    def settle(turns=2) -> None:
        for _ in range(turns):
            app.processEvents()

    NONE = Qt.MouseButton.NoButton
    QT_BUTTON = {1: Qt.MouseButton.LeftButton, 2: Qt.MouseButton.MiddleButton,
                 3: Qt.MouseButton.RightButton}

    def mouse(kind, x, y, button=NONE, buttons=NONE, modifiers=Qt.KeyboardModifier.NoModifier):
        local = QPointF(x, y)
        event = QMouseEvent(kind, local, QPointF(widget.mapToGlobal(QPoint(int(x), int(y)))),
                            button, buttons, modifiers)
        QApplication.sendEvent(widget, event)
        settle(1)

    def qt_drag(button, modifiers, points) -> None:
        (x0, y0), (x1, y1) = points
        qb = QT_BUTTON[button]
        mouse(QEvent.Type.MouseButtonPress, x0, y0, qb, qb, modifiers)
        for step in range(1, 5):
            mouse(QEvent.Type.MouseMove, x0 + (x1 - x0) * step // 4, y0 + (y1 - y0) * step // 4,
                  NONE, qb, modifiers)
        mouse(QEvent.Type.MouseButtonRelease, x1, y1, qb, NONE, modifiers)
        settle()

    def dispatched_drag(button, state, points) -> None:
        (x0, y0), (x1, y1) = points
        inspector.dispatch_viewport_event(button_handler(button, state, "press"),
                                          ViewportEvent(x0, y0, state))
        for step in range(1, 5):
            inspector.dispatch_viewport_event(
                button_handler(button, state, "motion"),
                ViewportEvent(x0 + (x1 - x0) * step // 4, y0 + (y1 - y0) * step // 4, state))
        inspector.dispatch_viewport_event(button_handler(button, state, "release"),
                                          ViewportEvent(x1, y1, state))
        settle()

    # ---- O ---------------------------------------------------------------------------------
    ratio = view.pixel_ratio()
    cx, cy = widget.width() // 2, widget.height() // 2
    start = camera()
    results = {}
    for name, button, qt_mods, state, points in (
            ("orbit", 1, Qt.KeyboardModifier.NoModifier, 0, ((cx, cy), (cx + 90, cy + 40))),
            ("shift-pan", 1, Qt.KeyboardModifier.ShiftModifier, SHIFT,
             ((cx - 60, cy - 50), (cx + 30, cy - 10))),
            ("middle-pan", 2, Qt.KeyboardModifier.NoModifier, 0,
             ((cx + 40, cy + 30), (cx - 50, cy + 60)))):
        set_camera(start)
        qt_drag(button, qt_mods, points)
        by_qt = camera()
        set_camera(start)
        dispatched_drag(button, state,
                        tuple((int(round(x * ratio)), int(round(y * ratio))) for x, y in points))
        by_dispatch = camera()
        results[name] = (not same(by_qt, start), same(by_qt, by_dispatch))
    set_camera(start)
    rows.append(["O", all(moved and alike for moved, alike in results.values()),
                 f"Qt drags moved the camera and left it where the dispatched gestures did "
                 f"(moved, same): {results}"])

    # ---- P ---------------------------------------------------------------------------------
    selection = inspector._selection_model

    def picked():
        return (selection.picked_row_index, tuple(sorted(selection.picked_row_indices)),
                selection.picked_step_label, selection.picked_ray_index,
                selection.picked_optical_axis_id)

    def qt_click(x, y):
        selection.clear()
        mouse(QEvent.Type.MouseMove, x, y)
        mouse(QEvent.Type.MouseButtonPress, x, y, Qt.MouseButton.LeftButton,
              Qt.MouseButton.LeftButton)
        mouse(QEvent.Type.MouseButtonRelease, x, y, Qt.MouseButton.LeftButton, NONE)
        settle()
        return picked()

    def dispatched_click(x, y):
        selection.clear()
        px, py = int(round(x * ratio)), int(round(y * ratio))
        # the VTK hover pick a bare move runs (the Tk VTK widget's own <Motion> binding)
        inspector._mouse_move_last_ts = 0.0
        interactor.SetEventInformationFlipY(px, py, 0, 0, chr(0), 0, None)
        interactor.MouseMoveEvent()
        inspector.dispatch_viewport_event("hover", ViewportEvent(px, py))
        inspector.dispatch_viewport_event("left_press", ViewportEvent(px, py))
        inspector.dispatch_viewport_event("left_release", ViewportEvent(px, py))
        settle()
        return picked()

    empty = (None, (), None, None, None)
    found = None
    width, height = widget.width(), widget.height()
    for gy in range(1, 10):
        for gx in range(1, 12):
            x, y = width * gx // 12, height * gy // 10
            by_qt = qt_click(x, y)
            if by_qt != empty:
                found = (x, y, by_qt, dispatched_click(x, y))
                break
        if found:
            break
    rows.append(["P", found is not None and found[2] == found[3],
                 f"a Qt hover + click at {found[:2] if found else None} selected "
                 f"{found[2] if found else None}; the dispatched hover + click selected "
                 f"{found[3] if found else None}"])
    selection.clear()

    # ---- K ---------------------------------------------------------------------------------
    def key(kind, qt_key, text="", modifiers=Qt.KeyboardModifier.NoModifier):
        QApplication.sendEvent(widget, QKeyEvent(kind, qt_key, modifiers, text))
        settle(1)

    inspector._placement_target_pick_mode = True
    key(QEvent.Type.KeyPress, Qt.Key.Key_Escape)
    rows.append(["K", inspector._placement_target_pick_mode is False,
                 "Escape pressed on the Qt widget cancelled the armed placement-target pick"])

    # ---- K2 (bugs/0957): one key press runs ONE handler ---------------------------------------
    # A bound key used to go to VTK as well, whose own key observer handles the same three keys:
    # one `s` wrote two flag bundles, one Escape cancelled AND cleared the selection.
    calls: list = []
    inspector.flag_bug = lambda *_a, **_k: calls.append("flag")
    inspector.cancel_active_3d_operation = lambda *_a, **_k: calls.append("cancel")
    inspector.delete_selected_step = lambda *_a, **_k: calls.append("delete")
    reached_vtk: list = []
    interactor = inspector._vtk_interactor
    tag = interactor.AddObserver("KeyPressEvent", lambda *_a: reached_vtk.append(str(interactor.GetKeySym())))
    key(QEvent.Type.KeyPress, Qt.Key.Key_S, text="s")
    key(QEvent.Type.KeyPress, Qt.Key.Key_Escape)
    key(QEvent.Type.KeyPress, Qt.Key.Key_Delete)
    bound = (list(calls), list(reached_vtk))
    key(QEvent.Type.KeyPress, Qt.Key.Key_F9)                 # a key the inspector does not bind
    unbound = (list(calls), list(reached_vtk))
    interactor.RemoveObserver(tag)
    del inspector.flag_bug, inspector.cancel_active_3d_operation, inspector.delete_selected_step
    rows.append(["K2", bound == (["flag", "cancel", "delete"], []) and unbound == (["flag", "cancel", "delete"], ["F9"]),
                 f"`s`, Escape, Delete pressed once each ran {bound[0]} and reached VTK's own key observer "
                 f"{bound[1]}; an unbound key (F9) ran nothing more and reached VTK {unbound[1]}"])

    # ---- A ---------------------------------------------------------------------------------
    inspector._edge_pick_alt_active = False
    key(QEvent.Type.KeyPress, Qt.Key.Key_Alt, modifiers=Qt.KeyboardModifier.AltModifier)
    on = bool(inspector._edge_pick_alt_active)
    key(QEvent.Type.KeyRelease, Qt.Key.Key_Alt)
    off = bool(inspector._edge_pick_alt_active)
    rows.append(["A", on and not off,
                 f"Alt on the Qt widget turned edge hover on ({on}) and its release off ({off})"])

    # ---- D ---------------------------------------------------------------------------------
    # 0906 held the right press back (it posted a Tk menu); since 0907 it is routed and the
    # menu it builds is shown as a QMenu -- never a Tk menu
    from KrakenOS.UI.context_menu import MenuModel
    from KrakenOS.UI.qt.inspector_view import DEFERRED_PRESSES

    view.dispatched.clear()
    view.last_menu = None
    rb = Qt.MouseButton.RightButton
    mouse(QEvent.Type.MouseButtonPress, cx, cy, rb, rb)
    mouse(QEvent.Type.MouseButtonRelease, cx, cy, rb, NONE)
    menu = getattr(inspector, "_active_context_menu", None)
    press_routed = "right_press" in view.dispatched
    if 3 in DEFERRED_PRESSES:
        right_ok = not press_routed and menu is None
    else:
        right_ok = press_routed and (menu is None or isinstance(menu, MenuModel))
    rows.append(["D", right_ok and "right_release" in view.dispatched,
                 f"a right click dispatched {view.dispatched}; the live menu is "
                 f"{type(menu).__name__} (a Tk menu never, under Qt)"])
    if view.last_menu is not None:
        view.last_menu.close()
        settle()

    # ---- U ---------------------------------------------------------------------------------
    inspector._set_viewport_cursor("crosshair")
    crossed = widget.cursor().shape() == Qt.CursorShape.CrossCursor
    inspector._set_viewport_cursor("")
    reset = widget.cursor().shape() == Qt.CursorShape.ArrowCursor
    QCursor.setPos(widget.mapToGlobal(QPoint(cx, cy)))
    settle()
    inside = inspector._current_widget_pointer_xy()
    over = inspector._pointer_over_vtk_widget()
    QCursor.setPos(widget.mapToGlobal(QPoint(-50, -50)))
    settle()
    outside = inspector._current_widget_pointer_xy()
    not_over = inspector._pointer_over_vtk_widget()
    near = inside is not None and abs(inside[0] - cx * ratio) <= 2 and abs(inside[1] - cy * ratio) <= 2
    rows.append(["U", crossed and reset and near and over and outside is None and not not_over,
                 f"cursor crosshair={crossed}, reset={reset}; pointer inside={inside} "
                 f"(centre {cx},{cy}) over={over}, outside={outside} over={not_over}"])

    # ---- S ---------------------------------------------------------------------------------
    ran = {"repick": 0, "refresh": 0}
    inspector._on_trailing_hover_repick = lambda: ran.__setitem__("repick", ran["repick"] + 1)
    inspector._schedule_trailing_hover_repick()
    service = inspector._open3d_live_refresh_service()
    inspector.live_mode_var.set(True)
    real_run = service.run

    def counting_run():
        ran["refresh"] += 1
        real_run()

    service.run = counting_run
    scheduled = inspector.schedule_live_refresh("guard 0906", delay_ms=10)
    import time

    deadline = time.time() + 300
    while (ran["repick"] == 0 or ran["refresh"] == 0 or service.busy) and time.time() < deadline:
        app.processEvents()
        time.sleep(0.02)
    inspector.live_mode_var.set(False)
    rows.append(["S", scheduled and ran["repick"] == 1 and ran["refresh"] == 1
                 and service.after_id is None,
                 f"in the Qt loop the trailing hover re-pick ran {ran['repick']}x and the live "
                 f"refresh ran {ran['refresh']}x (scheduled={scheduled})"])

    # ---- V ---------------------------------------------------------------------------------
    editor.open_3d_view()
    settle()
    # ... and did not show a Tk window: the one it owns is still withdrawn -- or, built without
    # one (KRAKEN_QT_TK_FREE, bugs/0998), there is still none
    from KrakenOS.UI.qt.tk_free import tk_free

    owned = inspector.__dict__.get("window")
    toplevel = "none" if owned is None else str(owned.state())
    rows.append(["V", editor._three_d_inspector is inspector
                 and toplevel == ("none" if tk_free("inspector") else "withdrawn"),
                 f"Open 3D View re-used the Qt inspector "
                 f"({editor._three_d_inspector is inspector}); its Toplevel is "
                 f"{toplevel}"])
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
        "from KrakenOS.UI.validate_open3d_0906_qt_hosts_inspector import qt_runtime_checks\n"
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()))\n"
    )
    env = dict(os.environ)
    env.pop("WAYLAND_DISPLAY", None)
    env["QT_QPA_PLATFORM"] = "xcb"
    try:
        proc = subprocess.run([sys.executable, "-c", driver], capture_output=True, text=True,
                              timeout=1200, env=env, cwd=str(Path.cwd()))
    except subprocess.TimeoutExpired:
        return "error", [["Q", False, "the Qt subprocess timed out after 1200 s"]]
    for line in proc.stdout.splitlines():
        if line.startswith(RESULT_MARK):
            return "ok", json.loads(line[len(RESULT_MARK):])
        if line.startswith(SKIP_MARK):
            return "skip", [["Q", True, line[len(SKIP_MARK):]]]
    tail = (proc.stderr or proc.stdout or "").strip().splitlines()[-5:]
    return "error", [["Q", False, f"exit {proc.returncode}; " + " | ".join(tail)]]


# ---- the static half -------------------------------------------------------------------------
def _cursor_names_asked_for() -> set:
    """Every literal a `_set_viewport_cursor(...)` call can pass, conditionals included."""
    from KrakenOS.UI import open3d_inspector
    from KrakenOS.UI.services import open3d_mouse_bindings

    names: set = set()
    for module in (open3d_inspector, open3d_mouse_bindings):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "_set_viewport_cursor":
                for arg in node.args:
                    for leaf in ast.walk(arg):
                        if isinstance(leaf, ast.Constant) and isinstance(leaf.value, str):
                            names.add(leaf.value)
    return names


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.qt import inspector_view
    from KrakenOS.UI.services import trace_preview_async
    from KrakenOS.UI.services.open3d_live_refresh import Open3DLiveRefreshService
    from KrakenOS.UI.viewport_events import ALT, CONTROL, SHIFT, button_handler

    notes: list[str] = []
    state = {"ok": True}

    def ok(cond, text):
        notes.append(("= " if cond else "FAIL ") + text)
        if not cond:
            state["ok"] = False

    # ---- R ---------------------------------------------------------------------------------
    differ = []
    for button in (1, 2, 3):
        for mods in (0, SHIFT, CONTROL, ALT, SHIFT | CONTROL):
            for phase in ("press", "motion", "release"):
                want = (None if phase == "press" and button in inspector_view.DEFERRED_PRESSES
                        else button_handler(button, mods, phase))
                got = inspector_view.routed_kind(button, mods, phase)
                if got != want:
                    differ.append((button, mods, phase, got, want))
    ok(not differ,
       "R: the Qt routing is button_handler for all 45 button/modifier/phase cases, bar any press "
       f"still held back ({sorted(inspector_view.DEFERRED_PRESSES) or 'none since 0907'})"
       + (f" -- differ {differ}" if differ else ""))

    # ---- C ---------------------------------------------------------------------------------
    asked = _cursor_names_asked_for()
    try:
        from PySide6.QtCore import Qt

        missing = sorted(name for name in asked
                         if name not in inspector_view.QT_CURSOR_SHAPES
                         or not hasattr(Qt.CursorShape, inspector_view.qt_cursor_shape(name)))
        ok(asked and not missing,
           f"C: every cursor the inspector asks for {sorted(asked)} maps to a real Qt shape"
           + (f" -- unmapped {missing}" if missing else ""))
    except ImportError as exc:
        notes.append(f"SKIP C: {exc!r}")

    # ---- T ---------------------------------------------------------------------------------
    sources = {
        "live refresh": inspect.getsource(Open3DLiveRefreshService),
        "trailing re-pick": inspect.getsource(Kraken3DInspector._schedule_trailing_hover_repick)
        + inspect.getsource(Kraken3DInspector._cancel_trailing_hover_repick),
        "async poll": inspect.getsource(trace_preview_async._schedule_async_poll),
    }
    tk_timer = {name: [token for token in ("inspector.after", "widget.after", "editor.after(")
                       if token in text.replace("host_of(inspector).after", "")
                       .replace("host_of(self.inspector).after", "")
                       .replace("host_of(inspector.editor).after", "")]
                for name, text in sources.items()}
    pointer_over = inspect.getsource(Kraken3DInspector._pointer_over_vtk_widget)
    seam_first = pointer_over.find('"viewport_pointer"') < pointer_over.find("winfo_pointerx")
    ok(not any(tk_timer.values()) and seam_first,
       "T: the live refresh, trailing hover re-pick and async-trace poll timers go through the "
       "host, and 'is the pointer over the viewport' asks the shell's seam before Tk"
       + (f" -- still on Tk: {tk_timer}" if any(tk_timer.values()) else ""))

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
