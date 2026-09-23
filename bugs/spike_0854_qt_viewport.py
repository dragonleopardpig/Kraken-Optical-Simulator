"""Phase 2 spike: a PySide6 window with a VTK viewport showing REAL KrakenOS geometry
(docs/design_qt_migration.md, bugs/0854).

Three things this has to answer before phase 5 is planned:
  1. does QVTKRenderWindowInteractor work against THIS VTK (nixpkgs 9.5.2) and PySide6 6.10;
  2. does real KrakenOS geometry -- the transformed imported STEP bodies of a saved scene --
     render in it;
  3. do Qt mouse events reach VTK's interactor, i.e. is the camera actually drivable? That is the
     bridge the ~50 shipped interaction bugs have to be re-proved across.

Two traps this cost an hour on, both worth knowing before phase 5:

  * `vtkmodules.vtkRenderingOpenGL2` must be imported BEFORE the render window is created, or
    VTK's object factory has no OpenGL override and `vtkRenderWindow()` hands back the ABSTRACT
    base class: `Render()` then draws nothing (silently), pixel readback returns 0 pixels, and
    `vtkWindowToImageFilter` SEGFAULTS asking a non-GL window for an image. `GetClassName()` is
    the tell -- it must say `vtkXOpenGLRenderWindow`, not `vtkRenderWindow`.
  * the Qt platform and VTK's X display must be the SAME window system. In this shell
    WAYLAND_DISPLAY is set, so Qt goes to the compositor and ignores the DISPLAY xvfb-run just
    set, while VTK opens on the Xvfb server -- and the widget then hands VTK a window handle
    from the wrong window system.
  * the viewport must be built once its parent chain reaches a shown top-level: the widget hands
    VTK its window id in `__init__`, and Qt destroys and recreates a native window on reparenting.
  * an imported STEP body carries `kraken_step_selection_face_index` as its ACTIVE cell scalars
    (that is what face picking reads), so a mapper colours by that array through the default
    lookup table and ignores the actor's colour -- the body came out invisible against the white
    background, with only its handful of line cells showing as specks. `ScalarVisibilityOff()`.
  * `vtkInteractorStyleSwitch` starts in JOYSTICK mode, where the camera moves on timer ticks
    rather than on move deltas: a press-drag-release does nothing at all unless the interactor's
    timers are running. The app's trackball style has to be set explicitly.

Run:  unset WAYLAND_DISPLAY; QT_QPA_PLATFORM=xcb \
      xvfb-run -a -s "-screen 0 1400x1000x24" python bugs/spike_0854_qt_viewport.py out.png
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

SCENE = Path("attachment/om05a_folded.py")


def step(message: str) -> None:
    """Flushed, because a VTK segfault under Xvfb loses everything still buffered."""
    print(f"[spike] {message}", flush=True)


BODIES = (("optical", (0.29, 0.64, 0.71)), ("lens", (0.25, 0.45, 0.55)),
          ("camera", (0.45, 0.45, 0.50)), ("led", (0.85, 0.65, 0.20)))


def _write_png(render_window, path: str) -> None:
    from vtkmodules.vtkIOImage import vtkPNGWriter
    from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

    capture = vtkWindowToImageFilter()
    capture.SetInput(render_window)
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtkPNGWriter()
    writer.SetFileName(path)
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()


def _run(out: str) -> int:
    import vtkmodules.vtkInteractionStyle  # noqa: F401  (registers the interactor styles)
    import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (registers the OpenGL factory overrides)
    import vtkmodules.qt

    vtkmodules.qt.PyQtImpl = "PySide6"
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout, QWidget
    from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
    from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera
    from vtkmodules.vtkRenderingCore import vtkActor, vtkDataSetMapper, vtkRenderer

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    step("QApplication")
    app = QApplication.instance() or QApplication(sys.argv)

    window = QMainWindow()
    window.setWindowTitle("KrakenOS -- Qt viewport spike")
    central = QWidget()
    layout = QVBoxLayout(central)
    layout.addWidget(QLabel(f"{SCENE.name} -- imported STEP bodies drawn from the KrakenOS model"))
    window.setCentralWidget(central)
    window.resize(1200, 860)
    # Trap 3 (docstring): QVTKRenderWindowInteractor hands VTK its window id in __init__
    # (SetWindowInfo(winId()), QVTKRenderWindowInteractor.py:379). Reparenting a widget makes Qt
    # destroy and recreate its native window, so a viewport built before its parent chain reaches
    # a shown top-level leaves VTK drawing into a dead handle -- a blank viewport that also
    # receives no mouse events. Build it once the window is up.
    window.show()
    app.processEvents()
    step("QVTKRenderWindowInteractor (parent chain live)")
    viewport = QVTKRenderWindowInteractor(central)
    layout.addWidget(viewport, stretch=1)
    app.processEvents()

    renderer = vtkRenderer()
    renderer.SetBackground(1.0, 1.0, 1.0)
    render_window = viewport.GetRenderWindow()
    render_window.AddRenderer(renderer)
    step(f"render window: {render_window.GetClassName()} "
         f"(OpenGL={bool(render_window.IsA('vtkOpenGLRenderWindow'))})")
    if not render_window.IsA("vtkOpenGLRenderWindow"):
        step("ABORT: no OpenGL factory override -- see the module docstring")
        return 1

    step("building the headless editor")
    started = time.monotonic()
    editor = KrakenLayoutEditor(headless=True)
    editor.layout_files["spike"] = SCENE
    editor.load_layout_by_name("spike")
    loaded = time.monotonic() - started

    step("scene loaded; collecting STEP bodies")
    drawn: list[tuple[str, int]] = []
    for name, colour in BODIES:
        try:
            mesh = editor._transformed_imported_step_mesh_for_label(name)
        except Exception as exc:  # a scene need not carry every body
            print(f"   {name}: {type(exc).__name__}: {exc}")
            continue
        if mesh is None:
            continue
        mapper = vtkDataSetMapper()
        mapper.SetInputData(mesh)
        mapper.ScalarVisibilityOff()  # else it colours by the face-index array, not by us
        actor = vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(*colour)
        actor.GetProperty().SetOpacity(0.45)
        renderer.AddActor(actor)
        drawn.append((name, int(mesh.GetNumberOfPoints())))
        step(f"  {name}: {drawn[-1][1]} points")
    renderer.ResetCamera()

    step("Initialize")
    viewport.Initialize()
    viewport._Iren.SetInteractorStyle(vtkInteractorStyleTrackballCamera())
    app.processEvents()
    first_frame = time.monotonic()
    # The first frame of a freshly mapped X window is not ready after one Render(): under
    # llvmpipe the widget needs a few turns of the event loop before the buffer holds the scene.
    for _ in range(5):
        render_window.Render()
        app.processEvents()
        time.sleep(0.1)
    render_ms = (time.monotonic() - first_frame) * 1000.0
    bounds = renderer.ComputeVisiblePropBounds()
    camera = renderer.GetActiveCamera()
    step(f"viewport {render_window.GetSize()}, visible bounds "
         f"({bounds[0]:.0f}..{bounds[1]:.0f}, {bounds[2]:.0f}..{bounds[3]:.0f}, "
         f"{bounds[4]:.0f}..{bounds[5]:.0f}), camera at "
         f"({camera.GetPosition()[0]:.0f}, {camera.GetPosition()[1]:.0f}, {camera.GetPosition()[2]:.0f})")
    step("capturing the first frame")
    _write_png(render_window, out)

    # --- do Qt mouse events actually drive VTK's camera? --------------------------------------
    step("driving a Qt mouse drag")
    before = camera.GetPosition()
    centre = QPointF(viewport.rect().center())

    def send(kind, point, button, buttons):
        event = QMouseEvent(kind, point, viewport.mapToGlobal(point.toPoint()).toPointF(),
                            button, buttons, Qt.KeyboardModifier.NoModifier)
        app.sendEvent(viewport, event)
        app.processEvents()

    send(QEvent.Type.MouseButtonPress, centre, Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton)
    for fraction in (0.25, 0.5, 0.75, 1.0):
        # a move carries NoButton in button() and the held buttons in buttons()
        send(QEvent.Type.MouseMove, QPointF(centre.x() + 200 * fraction, centre.y() + 110 * fraction),
             Qt.MouseButton.NoButton, Qt.MouseButton.LeftButton)
    send(QEvent.Type.MouseButtonRelease, QPointF(centre.x() + 200, centre.y() + 110),
         Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton)
    after = camera.GetPosition()
    moved = max(abs(a - b) for a, b in zip(before, after))
    rotated = Path(out).with_name(Path(out).stem + "_after_drag.png")
    for _ in range(3):
        render_window.Render()
        app.processEvents()
        time.sleep(0.05)
    _write_png(render_window, str(rotated))

    # --- the host the model already talks to, answered by Qt ----------------------------------
    step("QtUiHost timer")
    host = QtUiHost(window)
    fired: list[str] = []
    host.after(1, fired.append, "qt timer")
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and not fired:
        app.processEvents()

    print(f"scene loaded in {loaded:.1f} s; bodies drawn: {drawn}")
    print(f"first Qt-hosted VTK frame: {render_ms:.0f} ms -> {out}")
    print(f"Qt mouse drag moved the VTK camera by {moved:.2f} mm -> {rotated}")
    print(f"QtUiHost timer fired: {fired}")

    step("teardown")
    editor.destroy()
    viewport.close()
    return 0 if drawn and moved > 1e-6 and fired else 1


if __name__ == "__main__":
    raise SystemExit(_run(sys.argv[1] if len(sys.argv) > 1 else "/tmp/qt_spike.png"))
