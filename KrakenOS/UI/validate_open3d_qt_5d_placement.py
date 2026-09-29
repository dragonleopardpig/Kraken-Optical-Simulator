"""Phase 5d guard (docs/design_qt_migration.md): placement drags work in the Qt shell.

The Qt shell hosts the REAL inspector (0906), and a placement drag is the inspector's own handler
chain -- so the question for 5d is not "port the drags" but "does every drag, driven by real Qt
input, do what the same gesture does through `dispatch_viewport_event`?" -- 0905 proved dispatch
matches the Tk bindings. Deltas are compared, never absolute poses: each gesture runs on the same
body first with Qt events, then dispatched.

In a real Qt shell, on a promoted 42779 pentaprism with "Move/Rotate whole body" ON:

  M  a +Z move-handle drag (hover, press on the handle's pixel, 4 x 20 px along its screen axis,
     release) commits the SAME desp change as the dispatched gesture, and a non-zero one
  R  a click on a rotate handle applies the SAME rotation (compared as matrices -- tilt triples
     have equivalent forms) as the dispatched click, and a non-zero one
  C  a long-press carry of the imported STEP overlay: the press arms the hold, the HOST timer
     (a QTimer under Qt -- nothing pumps Tk) fires, the drag moves it -- same offset change as
     the dispatched carry. The Qt pointer really waits out the hold between press and motion.
  W  the same for a promoted solid's row carry (a press on the body away from the gizmo)
  P  "Place/Orient Selected CAD/STL Solid" opens as a Qt dialog, not a Tk frame in the withdrawn
     Toplevel: its actions rotate, seat and fit the solid and refresh the status line, the axis
     choice reaches the inspector, and Done -> 2D closes the dialog but NOT the shell's inspector
     (in Tk it closes the separate 3D window)

Static:
  S  every button of the Tk panel is an action of the form, calling the same inspector method
"""
from __future__ import annotations

import inspect
import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5D_RESULT "
SKIP_MARK = "QT5D_SKIP "


def qt_runtime_checks() -> list:
    import time

    import numpy as np
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.layout_editor import SurfaceRow
    from KrakenOS.UI.optical_solid_metadata import rotation_matrix_from_kraken_tilts
    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _import_step
    from KrakenOS.UI.viewport_events import ViewportEvent, button_handler

    rows: list = []
    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    editor = window.editor
    editor.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    editor._sync_table()
    view = window.build_inspector_view()
    for _ in range(20):
        app.processEvents()
    insp, widget = view.inspector, view.widget
    insp.show_rays_var.set(False)
    insp.show_rotation_handles_var.set(True)
    ratio = float(widget.devicePixelRatioF() or 1.0)
    render_window = widget.GetRenderWindow()
    NONE, LEFT = Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton

    def pump(ms: float = 0.0) -> None:
        end = time.monotonic() + ms / 1000.0
        app.processEvents()
        while time.monotonic() < end:
            time.sleep(0.01)
            app.processEvents()

    def mouse(kind, x, y, button=NONE, buttons=NONE) -> None:
        event = QMouseEvent(kind, QPointF(x, y), QPointF(widget.mapToGlobal(QPoint(int(x), int(y)))),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(widget, event)
        app.processEvents()

    def renderer_of(actor):
        renderers = render_window.GetRenderers()
        for i in range(renderers.GetNumberOfItems()):
            renderer = renderers.GetItemAsObject(i)
            if renderer.HasViewProp(actor):
                return renderer
        return insp._renderer

    def to_widget(point, renderer=None):
        renderer = renderer or insp._renderer
        height = render_window.GetSize()[1]
        renderer.SetWorldPoint(float(point[0]), float(point[1]), float(point[2]), 1.0)
        renderer.WorldToDisplay()
        dx, dy, _ = renderer.GetDisplayPoint()
        return dx / ratio, (height - dy) / ratio

    def qt_gesture(points, hold_ms: float = 0.0) -> None:
        mouse(QEvent.Type.MouseMove, *points[0])
        mouse(QEvent.Type.MouseButtonPress, *points[0], LEFT, LEFT)
        pump(hold_ms)
        for point in points[1:]:
            mouse(QEvent.Type.MouseMove, *point, NONE, LEFT)
            pump(30 if hold_ms else 0)
        mouse(QEvent.Type.MouseButtonRelease, *points[-1], LEFT, NONE)
        pump(300 if hold_ms else 50)

    def dispatched_gesture(points, hold_ms: float = 0.0) -> None:
        # the VTK interactor's own position comes from the move that precedes a press, as in
        # both shells; the handlers get the event's pixel
        x0, y0 = (int(v) for v in points[0])
        mouse(QEvent.Type.MouseMove, x0, y0)
        insp.dispatch_viewport_event("hover", ViewportEvent(x0, y0))
        insp.dispatch_viewport_event(button_handler(1, 0, "press"), ViewportEvent(x0, y0, 0))
        pump(hold_ms)
        for x, y in points[1:]:
            insp.dispatch_viewport_event(button_handler(1, 0x100, "motion"), ViewportEvent(int(x), int(y), 0x100))
            pump(30 if hold_ms else 0)
        last = points[-1]
        insp.dispatch_viewport_event(button_handler(1, 0x100, "release"),
                                     ViewportEvent(int(last[0]), int(last[1]), 0x100))
        pump(300 if hold_ms else 50)

    def along(start, direction, steps=4, px=20.0):
        return [(start[0] + direction[0] * px * i, start[1] + direction[1] * px * i) for i in range(steps + 1)]

    # ---- the promoted solid, selected with its gizmo ----------------------------------------
    _import_step(editor, PRISM_42779_STEP)
    insp.refresh_from_editor(force_retrace=False)
    pump(100)

    # ---- C: the STEP overlay carry (before promotion) -----------------------------------------
    hold = float(insp._step_carry_hold_delay_ms()) + 150.0

    def overlay_press_point():
        mesh = editor._transformed_imported_optical_step_mesh()
        points = np.asarray(mesh.points, dtype=float)
        centre = np.asarray(mesh.center, dtype=float)
        far = points[int(np.argmax(np.linalg.norm(points - centre, axis=1)))]
        return to_widget(centre + 0.6 * (far - centre))

    carry = {}
    for mode, runner in (("qt", qt_gesture), ("dispatch", dispatched_gesture)):
        insp.refresh_from_editor(force_retrace=False)
        pump(100)
        start = overlay_press_point()
        before = np.asarray(editor._step_placement_offset_xyz("optical"), dtype=float)
        runner(along(start, (1.0, 0.0), steps=4, px=15.0), hold_ms=hold)
        carry[mode] = np.asarray(editor._step_placement_offset_xyz("optical"), dtype=float) - before
    rows.append(["C", float(np.linalg.norm(carry["qt"])) > 0.5 and np.allclose(carry["qt"], carry["dispatch"], atol=1e-3),
                 f"a {hold:.0f} ms press-hold then a 60 px drag carries the STEP overlay by "
                 f"{np.round(carry['qt'], 3).tolist()} mm with Qt input and "
                 f"{np.round(carry['dispatch'], 3).tolist()} mm dispatched"])

    out = editor.promote_imported_step_to_optical_solid_row(
        "optical", open_face_editor=False, clear_overlay=True, refresh_open_3d=False)
    target = int(out["row_index"])

    def select() -> None:
        insp._placement_handle_selected_row_index = target
        insp._set_row_highlight(target)
        editor._select_table_row(target)
        insp.refresh_from_editor(force_retrace=False)
        pump(50)

    def desp():
        return np.asarray([float(getattr(editor.rows[target], k, 0.0) or 0.0) for k in ("desp_x", "desp_y", "desp_z")])

    def rotation():
        row = editor.rows[target]
        return np.asarray(rotation_matrix_from_kraken_tilts(
            float(row.tilt_x or 0.0), float(row.tilt_y or 0.0), float(row.tilt_z or 0.0)), dtype=float)

    def handle(kind, axis):
        table = insp._actor_placement_move_map if kind == "move" else insp._actor_placement_rotate_map
        for key, (row_index, handle_axis, delta) in (table or {}).items():
            if int(row_index) == target and handle_axis == axis and float(delta) > 0:
                actor = insp._actor_by_key.get(key)
                if actor is not None:
                    return actor
        return None

    # ---- M: move-handle drag -------------------------------------------------------------------
    moved = {}
    for mode, runner in (("qt", qt_gesture), ("dispatch", dispatched_gesture)):
        select()
        actor = handle("move", "z")
        if actor is None:
            moved[mode] = None
            continue
        renderer = renderer_of(actor)
        centre = np.asarray(actor.GetCenter(), dtype=float)
        p0 = np.asarray(to_widget(centre, renderer))
        p1 = np.asarray(to_widget(centre + np.array([0.0, 0.0, 5.0]), renderer))
        direction = (p1 - p0) / max(float(np.linalg.norm(p1 - p0)), 1e-9)
        before = desp()
        runner(along(tuple(p0), tuple(direction)))
        moved[mode] = desp() - before
    rows.append(["M", moved["qt"] is not None and moved["dispatch"] is not None
                 and float(np.linalg.norm(moved["qt"])) > 0.5
                 and np.allclose(moved["qt"], moved["dispatch"], atol=1e-3),
                 f"a +Z move-handle drag moves desp by {None if moved['qt'] is None else np.round(moved['qt'], 3).tolist()} "
                 f"mm with Qt input and {None if moved['dispatch'] is None else np.round(moved['dispatch'], 3).tolist()} dispatched"])

    # ---- R: rotate-handle click ------------------------------------------------------------------
    turned = {}
    for mode, runner in (("qt", qt_gesture), ("dispatch", dispatched_gesture)):
        select()
        actor = handle("rotate", "y")
        if actor is None:
            turned[mode] = None
            continue
        before = rotation()
        runner([to_widget(np.asarray(actor.GetCenter(), dtype=float), renderer_of(actor))])
        turned[mode] = rotation() @ before.T
    same_turn = turned["qt"] is not None and turned["dispatch"] is not None and np.allclose(turned["qt"], turned["dispatch"], atol=1e-6)
    angle = None if turned["qt"] is None else float(np.degrees(np.arccos(np.clip((np.trace(turned["qt"]) - 1.0) / 2.0, -1.0, 1.0))))
    rows.append(["R", same_turn and angle is not None and angle > 1.0,
                 f"a Y rotate-handle click turns the body by {None if angle is None else round(angle, 3)} deg with Qt "
                 f"input; the same rotation matrix dispatched: {same_turn}"])

    # ---- W: promoted-solid row carry -------------------------------------------------------------
    carried = {}
    for mode, runner in (("qt", qt_gesture), ("dispatch", dispatched_gesture)):
        insp._placement_handle_selected_row_index = None
        insp.refresh_from_editor(force_retrace=False)
        pump(50)
        keys = (insp._row_actor_map or {}).get(target, [])
        actor = next((insp._actor_by_key.get(k) for k in keys if insp._actor_by_key.get(k) is not None), None)
        bounds = np.asarray(actor.GetBounds(), dtype=float).reshape(3, 2)
        centre = bounds.mean(axis=1)
        start = to_widget(centre + 0.6 * (bounds[:, 1] - centre))
        before = desp()
        runner(along(start, (1.0, 0.0), steps=4, px=15.0), hold_ms=hold)
        carried[mode] = desp() - before
    rows.append(["W", float(np.linalg.norm(carried["qt"])) > 0.5 and np.allclose(carried["qt"], carried["dispatch"], atol=1e-3),
                 f"a press-hold-drag on the promoted body carries its row by {np.round(carried['qt'], 3).tolist()} mm "
                 f"with Qt input and {np.round(carried['dispatch'], 3).tolist()} dispatched"])

    # ---- P: the placement assistant --------------------------------------------------------------
    editor._select_table_row(target)
    editor.open_optical_stl_placement_assistant()
    pump(50)
    dialog = view.last_form_dialog
    opened = dialog is not None and dialog.isVisible() and insp._stl_placement_panel_visible() \
        and insp._stl_placement_popup is None
    notes = []
    ok = opened
    if opened:
        actions = {a.key: a for a in dialog.form.actions}
        before = rotation()
        status_before = str(dialog.form.values.get("status"))
        dialog.run_action(actions["y_plus"])
        turned_by_form = not np.allclose(rotation(), before) and dialog.form.values.get("status") != status_before
        before_z = desp()[2]
        dialog.run_action(actions["front"])
        seated = abs(desp()[2] - before_z) > 1e-6 or "Front" in dialog.summary.text()
        dialog.on_field_changed(dialog.form.field("axis"), "+X")
        axis_ok = insp.stl_axis_var.get() == "+X"
        dialog.run_action(actions["done"])
        pump(50)
        closed = not dialog.isVisible() and not insp._stl_placement_panel_visible()
        alive = editor._three_d_inspector is insp and bool(insp.available)
        ok = turned_by_form and seated and axis_ok and closed and alive
        notes = [f"turned={turned_by_form}", f"seated={seated}", f"axis_var={insp.stl_axis_var.get()}",
                 f"closed={closed}", f"inspector_alive={alive}"]
    rows.append(["P", ok, f"the placement assistant opened as a Qt dialog (no Tk frame): {opened}; " + ", ".join(notes)])
    return [[key, bool(passed), str(detail)] for key, passed, detail in rows]


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
        "from KrakenOS.UI.validate_open3d_qt_5d_placement import qt_runtime_checks\n"
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


def _static_checks() -> list:
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.row_forms import stl_placement

    panel = inspect.getsource(Kraken3DInspector.show_stl_placement_handler)
    form = inspect.getsource(stl_placement.build_stl_placement_form)
    methods = ("_fit_stl_from_handler", "_rotate_stl_from_handler", "_center_stl_from_handler",
               "_front_stl_from_handler")
    missing = [m for m in methods if m in panel and m not in form]
    done = "finish_stl_placement" in panel and "finish_stl_placement" in form
    return [["S", not missing and done,
             f"every Tk panel button calls a method the form's actions call too (missing: {missing}; Done: {done})"]]


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    passed = True
    status, qt_rows = _run_qt_subprocess()
    for key, ok, detail in _static_checks() + qt_rows:
        passed = passed and bool(ok)
        notes.append(f"{key} = {detail}" if ok else f"{key} FAILED: {detail}")
    if status == "skip":
        notes.append("Q = the Qt half was skipped (no PySide6 or no display)")
    return passed, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
