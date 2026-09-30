"""Phase 5e guard (docs/design_qt_migration.md): measure, box select, navigation cube and the
banner / HUD work in the Qt shell.

A static audit of the 5e code (measure, rubber-band select, the navigation cube widget, the system
HUD, the banner) found no Tk-bound call on the interaction path. What remains is proof that each
tool, driven by real Qt input, lands where the Tk bindings' own sequence lands -- the VTK
interactor gets the motion first, then the handler is dispatched (0906). In a real Qt shell on
om05a_folded, each gesture runs with Qt input, the view is reset, then the same gesture runs
dispatched:

  N  a click on the navigation cube turns the camera -- to the same pose both ways, and away from
     where it started
  M  Measure: arm, click two bodies -- the same segment (both picked points and the offset)
  B  Rubber-band select: arm, drag a box -- the same rows selected, and some
  T  every text the viewport shows (banner, HUD, labels) lies inside the render window and clear
     of the navigation cube's corner (the bugs/0841 rule), at the first window size AND after a
     Qt resize -- the layout follows the Qt widget's size, not a Tk <Configure>
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

RESULT_MARK = "QT5E_RESULT "
SKIP_MARK = "QT5E_SKIP "
SCENE = Path("attachment/om05a_folded.py")


def qt_runtime_checks() -> list:
    import time

    import numpy as np
    from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.qt.app import build
    from KrakenOS.UI.viewport_events import ViewportEvent, button_handler

    app, window = build(["guard"])
    window.show()
    app.processEvents()
    window.build_viewport()
    window.load_layout_path(SCENE)
    view = window.build_inspector_view()
    for _ in range(30):
        app.processEvents()
    insp, widget, editor = view.inspector, view.widget, window.editor
    iren = insp._vtk_interactor
    ratio = view.pixel_ratio() or 1.0
    render_window = widget.GetRenderWindow()
    NONE, LEFT = Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton

    def pump(ms: float = 60.0) -> None:
        end = time.monotonic() + ms / 1000.0
        app.processEvents()
        while time.monotonic() < end:
            time.sleep(0.01)
            app.processEvents()

    def mouse(kind, x, y, button=NONE, buttons=NONE) -> None:
        QApplication.sendEvent(widget, QMouseEvent(kind, QPointF(x, y), QPointF(widget.mapToGlobal(QPoint(x, y))),
                                                   button, buttons, Qt.KeyboardModifier.NoModifier))
        app.processEvents()

    def qt_gesture(points) -> None:
        mouse(QEvent.Type.MouseMove, *points[0])
        pump(30)
        mouse(QEvent.Type.MouseButtonPress, *points[0], LEFT, LEFT)
        for point in points[1:]:
            mouse(QEvent.Type.MouseMove, *point, NONE, LEFT)
        mouse(QEvent.Type.MouseButtonRelease, *points[-1], LEFT, NONE)
        pump(150)

    def tk_move(x, y):
        iren.SetEventInformationFlipY(x, y, 0, 0, chr(0), 0, None)
        iren.MouseMoveEvent()

    def tk_gesture(points) -> None:
        x0, y0 = (int(v * ratio) for v in points[0])
        tk_move(x0, y0)
        insp.dispatch_viewport_event("hover", ViewportEvent(x0, y0))
        pump(30)
        insp.dispatch_viewport_event(button_handler(1, 0, "press"), ViewportEvent(x0, y0, 0))
        for x, y in points[1:]:
            px, py = int(x * ratio), int(y * ratio)
            tk_move(px, py)
            insp.dispatch_viewport_event(button_handler(1, 0x100, "motion"), ViewportEvent(px, py, 0x100))
        xl, yl = (int(v * ratio) for v in points[-1])
        insp.dispatch_viewport_event(button_handler(1, 0x100, "release"), ViewportEvent(xl, yl, 0x100))
        pump(150)

    cam = insp._renderer.GetActiveCamera()

    def camera():
        return [list(cam.GetPosition()), list(cam.GetFocalPoint()), list(cam.GetViewUp())]

    def set_camera(state) -> None:
        cam.SetPosition(*state[0])
        cam.SetFocalPoint(*state[1])
        cam.SetViewUp(*state[2])
        insp._renderer.ResetCameraClippingRange()
        render_window.Render()
        pump(50)

    def close(a, b, tol=1e-6) -> bool:
        return bool(np.allclose(np.asarray(a, float), np.asarray(b, float), atol=tol))

    rows = []
    width, height = widget.width(), widget.height()
    home = camera()

    # ---- N: the navigation cube ------------------------------------------------------------
    cube = {}
    for mode, gesture in (("qt", qt_gesture), ("tk", tk_gesture)):
        set_camera(home)
        gesture([(width - 60, 60)])
        pump(600)
        cube[mode] = camera()
    moved = not close(cube["qt"], home, 1e-3)
    rows.append(["N", moved and close(cube["qt"], cube["tk"]),
                 f"a click on the navigation cube turns the camera (moved={moved}) to the same pose "
                 f"with Qt input and dispatched: {close(cube['qt'], cube['tk'])}"])

    # ---- M: measure -----------------------------------------------------------------------
    set_camera(home)
    render_height = render_window.GetSize()[1]
    bodies = []
    for j in range(6):
        for i in range(10):
            x, y = int(width * (i + 0.5) / 10), int(height * (j + 0.5) / 6)
            if insp._picker.Pick(x * ratio, render_height - y * ratio, 0.0, insp._renderer) \
                    and insp._picker.GetActor() is not None:
                bodies.append((x, y))
    segments = {}
    if len(bodies) >= 2:
        for mode, gesture in (("qt", qt_gesture), ("tk", tk_gesture)):
            set_camera(home)
            insp.clear_measurements()
            insp.start_measure_pick()
            pump(50)
            gesture([bodies[0]])
            gesture([bodies[-1]])
            segments[mode] = [
                {k: v for k, v in seg.items() if k in ("p0", "p1", "offset")}
                for seg in list(getattr(insp, "_measure_segments", []) or [])
            ]
        insp.clear_measurements()
    same_measure = (len(segments.get("qt", [])) == 1 and len(segments.get("tk", [])) == 1
                    and all(close(segments["qt"][0][k], segments["tk"][0][k], 1e-6) for k in ("p0", "p1", "offset")))
    length = (float(np.linalg.norm(np.asarray(segments["qt"][0]["p1"], float) - np.asarray(segments["qt"][0]["p0"], float)))
              if segments.get("qt") else None)
    rows.append(["M", same_measure and length is not None and length > 1e-3,
                 f"two clicks on bodies {bodies[:1] + bodies[-1:]} measure "
                 f"{None if length is None else round(length, 4)} mm with Qt input; the same segment "
                 f"dispatched: {same_measure}"])

    # ---- B: rubber-band select --------------------------------------------------------------
    box = {}
    path = [(int(width * 0.2), int(height * 0.2)), (int(width * 0.5), int(height * 0.5)),
            (int(width * 0.8), int(height * 0.8))]
    for mode, gesture in (("qt", qt_gesture), ("tk", tk_gesture)):
        set_camera(home)
        insp.start_rubber_band_select()
        pump(50)
        gesture(path)
        box[mode] = list(editor._selected_table_indices())
    rows.append(["B", bool(box["qt"]) and box["qt"] == box["tk"],
                 f"a box over the middle 60% selects rows {box['qt']} with Qt input and "
                 f"{box['tk']} dispatched"])

    # ---- T: text layout at two window sizes -------------------------------------------------
    def text_layout() -> tuple[int, list]:
        render_window.Render()
        pump(100)
        w, h = render_window.GetSize()
        nav = insp._navigation_cube
        corner = getattr(nav, "_viewport", None) if nav is not None else None
        cube_x0 = float(corner[0]) * w if corner else float(w)
        cube_y0 = float(corner[1]) * h if corner else float(h)
        shown, bad = 0, []
        renderers = render_window.GetRenderers()
        for r_index in range(renderers.GetNumberOfItems()):
            renderer = renderers.GetItemAsObject(r_index)
            props = renderer.GetViewProps()
            for p_index in range(props.GetNumberOfItems()):
                prop = props.GetItemAsObject(p_index)
                if prop.GetClassName() not in ("vtkTextActor", "vtkOpenGLTextActor") or not prop.GetVisibility():
                    continue
                text = str(prop.GetInput() or "").strip()
                if not text:
                    continue
                bbox = [0.0, 0.0, 0.0, 0.0]
                prop.GetBoundingBox(renderer, bbox)
                # the box is relative to the actor's anchor; place it at the anchor's display pixel
                ax, ay = prop.GetPositionCoordinate().GetComputedDisplayValue(renderer)
                x0, x1, y0, y1 = bbox[0] + ax, bbox[1] + ax, bbox[2] + ay, bbox[3] + ay
                bbox = [x0, x1, y0, y1]
                shown += 1
                outside = x0 < -1 or y0 < -1 or x1 > w + 1 or y1 > h + 1
                on_cube = x1 > cube_x0 + 1 and y1 > cube_y0 + 1
                if outside or on_cube:
                    bad.append({"text": text[:40], "bbox": [round(v) for v in bbox], "window": [w, h],
                                "cube_from": [round(cube_x0), round(cube_y0)]})
        return shown, bad

    first = text_layout()
    window.resize(max(900, int(window.width() * 0.72)), window.height())
    pump(500)
    second = text_layout()
    rows.append(["T", first[0] >= 1 and second[0] >= 1 and not first[1] and not second[1],
                 f"{first[0]} texts at {list(render_window.GetSize())} after the resize "
                 f"({second[0]} texts); outside the window or on the cube: {first[1][:2] + second[1][:2]}"])
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
        "from KrakenOS.UI.validate_open3d_qt_5e_tools import qt_runtime_checks\n"
        # flushed, then exit WITHOUT interpreter teardown: VTK/Qt objects can segfault while
        # being destroyed, and a crash there loses a buffered result line (0932)
        f"print({RESULT_MARK!r} + json.dumps(qt_runtime_checks()), flush=True)\n"
        "os._exit(0)\n"
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


def run_checks() -> tuple[bool, list[str]]:
    if not SCENE.exists():
        return True, [f"SKIP = {SCENE} absent"]
    status, rows = _run_qt_subprocess()
    notes, passed = [], True
    for key, ok, detail in rows:
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
