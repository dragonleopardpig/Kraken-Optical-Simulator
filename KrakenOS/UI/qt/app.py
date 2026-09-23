"""Run the Qt shell (docs/design_qt_migration.md phase 2).

    python -m KrakenOS.UI.qt.app [attachment/om05a_folded.py]

Needs a display: VTK draws through a real GL context, and the model still builds (never shows) a
Tk widget tree. On this desktop, run it with `unset WAYLAND_DISPLAY; QT_QPA_PLATFORM=xcb` under
Xvfb for a headless check -- Qt otherwise goes to the compositor while VTK goes to the X server.
"""
from __future__ import annotations

import sys
from pathlib import Path


def build(argv=None):
    """Build the application, the model and the window. Returns (app, window)."""
    from PySide6.QtWidgets import QApplication

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.qt.main_window import KrakenQtMainWindow
    from KrakenOS.UI.uihost.qt_host import QtUiHost

    argv = list(sys.argv if argv is None else argv)
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
