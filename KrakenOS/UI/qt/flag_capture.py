"""What a bug flag records about the Qt shell itself (bugs/0959).

The `s` flag was made for the 3D window: its picture is the VTK render and its state is the scene.
In the Qt shell the scene is one part of a window that also has a ribbon, a surface table, edge
panels and dialogs -- a flag about any of those had nothing to show for it.

`capture` writes, into a flag bundle:

* the WHOLE main window as one picture -- ribbon, table, panels, 3D scene -- with a crosshair where
  the pointer was;
* every other window the application has on screen (a dialog, an undocked panel, a pop-up, a
  tooltip), each as its own picture, whole even where it runs off the screen;
* the 2D layout plot, when the shell has one;

and returns the state to go with them: the window and screen sizes, the ribbon's tab and fold, each
panel (shown / hidden / undocked, and where), each open window (and whether it exceeds the screen),
what has the keyboard and what the pointer is over. The rows + settings as they are NOW go into
``layout_state.json`` (unsaved edits are not in the layout file).

The pictures are drawn by Qt (`QWidget.grab`), not taken from the screen: they do not depend on a
screenshot tool or the compositor, and they never show another application. A VTK view draws
through its own GL window, which `grab` cannot see, so each one is rendered by VTK and painted in
at its place.
"""
from __future__ import annotations

import json
from pathlib import Path

#: the pointer crosshair on the window picture: an outer ring, an inner ring, four ticks
POINTER_OUTER = (0, 255, 0)
POINTER_INNER = (255, 0, 255)
_AREAS = {"LeftDockWidgetArea": "left", "RightDockWidgetArea": "right",
          "TopDockWidgetArea": "top", "BottomDockWidgetArea": "bottom"}


def exceeds_screen(x: int, y: int, width: int, height: int, screen: "tuple[int, int, int, int]") -> bool:
    """True when a window is larger than its screen or runs off one of its edges (pure)."""
    sx, sy, sw, sh = (int(value) for value in screen)
    if width <= 0 or height <= 0 or sw <= 0 or sh <= 0:
        return False
    return bool(width > sw or height > sh or x < sx or y < sy or x + width > sx + sw or y + height > sy + sh)


def widget_path(widget, limit: int = 8) -> list:
    """A widget and its parents, nearest first, as "Class" or "Class(objectName)"."""
    path = []
    while widget is not None and len(path) < limit:
        name = str(widget.objectName() or "")
        path.append(f"{type(widget).__name__}({name})" if name else type(widget).__name__)
        widget = widget.parentWidget()
    return path


def vtk_views(top_level) -> list:
    """The VTK views inside a window: widgets that own a render window."""
    from PySide6.QtWidgets import QWidget

    return [child for child in top_level.findChildren(QWidget)
            if callable(getattr(child, "GetRenderWindow", None)) and child.isVisibleTo(top_level)]


def vtk_view_image(widget):
    """One VTK view as a QImage, rendered by VTK; None when it cannot be."""
    try:
        import numpy as np
        from PySide6.QtGui import QImage
        from vtkmodules.util.numpy_support import vtk_to_numpy
        from vtkmodules.vtkRenderingCore import vtkWindowToImageFilter

        render_window = widget.GetRenderWindow()
        render_window.Render()
        grab = vtkWindowToImageFilter()
        grab.SetInput(render_window)
        grab.SetInputBufferTypeToRGB()
        grab.ReadFrontBufferOff()
        grab.Update()
        output = grab.GetOutput()
        width, height, _depth = output.GetDimensions()
        if width <= 0 or height <= 0:
            return None
        pixels = vtk_to_numpy(output.GetPointData().GetScalars()).reshape(height, width, -1)
        pixels = np.ascontiguousarray(pixels[::-1, :, :3])          # VTK's origin is bottom-left
        return QImage(pixels.data, width, height, 3 * width, QImage.Format.Format_RGB888).copy()
    except Exception:
        return None


def window_image(top_level, *, pointer=None):
    """A window as Qt draws it, its VTK views painted in, and a crosshair at ``pointer`` (a point
    in the window's own coordinates) when it is inside."""
    from PySide6.QtCore import QPoint, QRect
    from PySide6.QtGui import QColor, QImage, QPainter, QPen

    image = top_level.grab().toImage().convertToFormat(QImage.Format.Format_ARGB32)
    painter = QPainter(image)
    try:
        for view in vtk_views(top_level):
            rendered = vtk_view_image(view)
            if rendered is not None:
                painter.drawImage(QRect(view.mapTo(top_level, QPoint(0, 0)), view.size()), rendered)
        if pointer is not None and top_level.rect().contains(pointer):
            x, y = pointer.x(), pointer.y()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(QPen(QColor(*POINTER_OUTER), 3))
            painter.drawEllipse(QPoint(x, y), 16, 16)
            for dx, dy in ((-22, 0), (8, 0), (0, -22), (0, 8)):
                horizontal = dy == 0
                painter.drawLine(x + dx, y + dy, x + dx + (14 if horizontal else 0), y + dy + (0 if horizontal else 14))
            painter.setPen(QPen(QColor(*POINTER_INNER), 2))
            painter.drawEllipse(QPoint(x, y), 7, 7)
    finally:
        painter.end()
    return image


def _screen_block(window) -> "tuple[dict, tuple[int, int, int, int]]":
    screen = window.screen()
    if screen is None:
        return {}, (0, 0, 0, 0)
    geometry, available = screen.geometry(), screen.availableGeometry()
    rect = (geometry.x(), geometry.y(), geometry.width(), geometry.height())
    return ({"name": str(screen.name()), "x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3],
             "available": [available.x(), available.y(), available.width(), available.height()],
             "device_pixel_ratio": float(screen.devicePixelRatio())}, rect)


def _docks_block(window) -> list:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QDockWidget

    docks = []
    for dock in window.findChildren(QDockWidget):
        floating = bool(dock.isFloating())
        origin = dock.mapToGlobal(QPoint(0, 0)) if floating else dock.mapTo(window, QPoint(0, 0))
        area = _AREAS.get(str(getattr(window.dockWidgetArea(dock), "name", "")), "none")
        docks.append({"name": str(dock.objectName()), "title": str(dock.windowTitle()),
                      # "visible" is Qt's: true for a panel behind another's tab; "showing" has pixels
                      "visible": bool(dock.isVisible()), "showing": not dock.visibleRegion().isEmpty(),
                      "floating": floating, "area": area,
                      # in the window for a docked panel, on the screen for an undocked one
                      "x": origin.x(), "y": origin.y(), "width": dock.width(), "height": dock.height()})
    return sorted(docks, key=lambda dock: dock["name"])


def _ribbon_block(window) -> dict:
    ribbon = getattr(window, "ribbon", None)
    if ribbon is None:
        return {}
    tabs = ribbon.tabs
    return {"tab": str(tabs.tabText(tabs.currentIndex())), "folded": bool(getattr(ribbon, "collapsed", False)),
            "floating": bool(ribbon.dock.isFloating())}


def other_windows(window) -> list:
    """Every other window the application has on screen, the one in front last."""
    from PySide6.QtWidgets import QApplication

    active = QApplication.activeWindow()
    found = [widget for widget in QApplication.topLevelWidgets()
             if widget is not window and widget.isVisible() and widget.width() > 0 and widget.height() > 0]
    return sorted(found, key=lambda widget: widget is active)


def subject_window(window, others):
    """The window a flag about "the window" is about: the dialog in front when one is, else the
    main window. A pop-up or a tooltip is never the subject, and neither is a flag's own prompt."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    active = QApplication.activeWindow()
    if active is None or active is window or active not in others:
        return window
    kind = active.windowType()
    if kind in (Qt.WindowType.Popup, Qt.WindowType.ToolTip) or getattr(active, "is_flag_prompt", False):
        return window
    return active


def capture(window, bundle_dir, *, as_screenshot: bool = False) -> dict:
    """Write the shell's pictures into ``bundle_dir`` and return its state block.

    The main window is ``window.png`` and every other window ``window_<n>.png``. With
    ``as_screenshot`` the flag is ABOUT the shell, and the window in front -- the main window, or
    the dialog over it -- is written as ``screenshot.png`` instead ("screenshot_of" says which).

    Never raises: a part that cannot be captured is left out and named under "errors"."""
    from PySide6.QtGui import QCursor
    from PySide6.QtWidgets import QApplication

    bundle_dir = Path(bundle_dir)
    errors: list = []
    block: dict = {"toolkit": "qt"}

    def attempt(what: str, work):
        try:
            return work()
        except Exception as exc:
            errors.append(f"{what}: {type(exc).__name__}: {exc}")
            return None

    screen_block, screen_rect = attempt("screen", lambda: _screen_block(window)) or ({}, (0, 0, 0, 0))
    block["screen"] = screen_block
    frame = window.frameGeometry()
    block["window"] = {"title": str(window.windowTitle()), "x": frame.x(), "y": frame.y(),
                       "width": window.width(), "height": window.height(),
                       "maximized": bool(window.isMaximized()), "fullscreen": bool(window.isFullScreen())}
    pointer_global = QCursor.pos()
    pointer = window.mapFromGlobal(pointer_global)
    over = attempt("pointer", lambda: QApplication.widgetAt(pointer_global))
    block["pointer"] = {"screen_xy": [pointer_global.x(), pointer_global.y()],
                        "window_xy": [pointer.x(), pointer.y()] if window.rect().contains(pointer) else None,
                        "over": widget_path(over) if over is not None else []}
    focus = QApplication.focusWidget()
    block["focus"] = {"widget": widget_path(focus) if focus is not None else [],
                      "window": str(focus.window().windowTitle()) if focus is not None else ""}
    modal = QApplication.activeModalWidget()
    block["modal_window"] = str(modal.windowTitle()) if modal is not None else None
    block["central"] = ("inspector" if getattr(window, "inspector_view", None) is not None
                        else "preview" if getattr(window, "viewport", None) is not None else "none")
    block["ribbon"] = attempt("ribbon", lambda: _ribbon_block(window)) or {}
    block["docks"] = attempt("docks", lambda: _docks_block(window)) or []

    def save(image, name: str) -> "str | None":
        return name if image is not None and image.save(str(bundle_dir / name)) else None

    others = attempt("windows", lambda: other_windows(window)) or []
    subject = (attempt("subject", lambda: subject_window(window, others)) or window) if as_screenshot else None
    block["screenshot_of"] = None if subject is None else "window" if subject is window else "dialog"
    block["window_png"] = attempt("window picture", lambda: save(
        window_image(window, pointer=pointer), "screenshot.png" if subject is window else "window.png"))

    windows = []
    for index, other in enumerate(others, start=1):
        frame = other.frameGeometry()
        entry = {"class": type(other).__name__, "title": str(other.windowTitle()),
                 "x": frame.x(), "y": frame.y(), "width": other.width(), "height": other.height(),
                 "modal": bool(other.isModal()), "active": other is QApplication.activeWindow(),
                 "exceeds_screen": exceeds_screen(frame.x(), frame.y(), frame.width(), frame.height(), screen_rect)}
        name = "screenshot.png" if other is subject else f"window_{index}.png"
        entry["png"] = attempt(f"picture of {entry['title'] or entry['class']}",
                               lambda o=other, n=name: save(window_image(o, pointer=o.mapFromGlobal(pointer_global)), n))
        windows.append(entry)
    block["open_windows"] = windows
    block["oversized_windows"] = [entry["title"] or entry["class"] for entry in windows if entry["exceeds_screen"]]

    plot = getattr(window, "plot2d", None)
    figure = getattr(window.editor, "figure", None) if plot is not None else None
    if figure is not None:
        def plot_png():
            figure.savefig(str(bundle_dir / "layout_2d.png"), dpi=150)
            return "layout_2d.png"

        block["layout_2d_png"] = attempt("2D layout plot", plot_png)

    def layout_state():
        # a file of its own: with the STEP solids' face tables it is several times the rest
        state = window.editor._capture_saved_layout_state()
        (bundle_dir / "layout_state.json").write_text(json.dumps(state, indent=1, default=str), encoding="utf-8")
        return "layout_state.json"

    block["layout_state_json"] = attempt("rows and settings", layout_state)
    if errors:
        block["errors"] = errors
    # the bundle's writer dumps this as JSON: whatever is not JSON goes in as its text
    return json.loads(json.dumps(block, default=str))
