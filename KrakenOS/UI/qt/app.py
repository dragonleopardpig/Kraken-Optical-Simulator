"""Run the Qt shell (docs/design_qt_migration.md phase 2).

    python -m KrakenOS.UI.qt.app [attachment/om05a_folded.py]

Needs a display: VTK draws through a real GL context, and the model still builds (never shows) a
Tk widget tree.

On a Wayland desktop the shell puts Qt on **XWayland** for itself (see :func:`choose_qt_platform`)
-- not a preference, a requirement: VTK's on-screen render window is X11, and it is handed the Qt
widget's window id.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

#: The only Qt platform the VTK viewport can live on (bugs/0856).
VIEWPORT_PLATFORM = "xcb"


def choose_qt_platform(env=None) -> tuple[str | None, str]:
    """Which Qt platform plugin this process must use, and why.

    `QVTKRenderWindowInteractor` gives VTK the Qt widget's window id, and VTK's on-screen render
    window on Linux is X11 (`vtkXOpenGLRenderWindow`). Under the Wayland platform plugin that id
    is a Wayland surface, so VTK calls `X_ConfigureWindow` on a window the X server has never
    heard of and Xlib ABORTS THE PROCESS -- `BadWindow (invalid Window parameter)`, no traceback,
    which is exactly what bugs/0856 was.

    Returns ``(platform or None, reason)``; ``None`` means "leave the environment alone".
    """
    env = os.environ if env is None else env
    if not sys.platform.startswith("linux"):
        return None, "not Linux: the X11 constraint does not apply"
    chosen = str(env.get("QT_QPA_PLATFORM") or "").strip()
    if chosen:
        return None, f"QT_QPA_PLATFORM is already {chosen!r}; leaving the choice to whoever set it"
    if not env.get("WAYLAND_DISPLAY"):
        return None, "no Wayland session: Qt already picks the X11 plugin"
    if not env.get("DISPLAY"):
        return None, ("a Wayland session with no DISPLAY: there is no X server for VTK to draw "
                      "on. Start XWayland, or run the Tk editor")
    return VIEWPORT_PLATFORM, ("a Wayland session: Qt would hand VTK a Wayland surface id, which "
                               "VTK would use as an X window -- putting Qt on XWayland instead")


def require_viewport_platform(platform_name: str) -> None:
    """Fail with an explanation rather than letting Xlib abort the process."""
    if not sys.platform.startswith("linux") or platform_name in (VIEWPORT_PLATFORM, "offscreen"):
        return
    raise RuntimeError(
        f"the Qt platform is {platform_name!r}, but the VTK viewport needs {VIEWPORT_PLATFORM!r}: "
        "VTK is given the Qt widget's window id and draws on X11, so on any other platform the "
        "X server rejects that id and Xlib aborts the process. Re-run with "
        f"QT_QPA_PLATFORM={VIEWPORT_PLATFORM}.")


def build(argv=None):
    """Build the application, the model and the window. Returns (app, window)."""
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.qt.main_window import KrakenQtMainWindow
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    argv = list(sys.argv if argv is None else argv)
    if QApplication.instance() is None:
        platform, reason = choose_qt_platform()
        if platform:
            os.environ["QT_QPA_PLATFORM"] = platform
            print(f"[KrakenOS] Qt platform -> {platform}: {reason}.")
        elif not os.environ.get("QT_QPA_PLATFORM") and "no X server" in reason:
            raise SystemExit(f"[KrakenOS] cannot start the Qt shell: {reason}.")
    app = QApplication.instance() or QApplication(argv)

    host = QtUiHost()
    # headless: the editor must not maximize or show the Tk tree it still builds (phase 5 makes
    # the inspector a Qt widget and this goes away). Withdrawing the root keeps Tk off the screen.
    editor = KrakenLayoutEditor(headless=True, ui=host)
    try:
        editor.root.withdraw()
    except Exception:
        pass

    window = KrakenQtMainWindow(editor, ui=host)
    host.set_parent(window)
    return app, window


def run(argv=None) -> int:
    argv = list(sys.argv if argv is None else argv)
    app, window = build(argv)
    window.show()
    window.build_viewport()

    scene = next((arg for arg in argv[1:] if arg.endswith(".py") and Path(arg).exists()), None)
    if scene:
        window.load_layout_path(scene)
    else:
        window.refresh_from_model()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(run())
