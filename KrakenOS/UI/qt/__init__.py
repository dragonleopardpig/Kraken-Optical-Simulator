"""The Qt shell (docs/design_qt_migration.md phase 2).

Qt-side VIEWS. The model stays where it is: a `KrakenLayoutEditor` reached through the seam, with
a `QtUiHost` answering its dialogs and scheduling, so a Qt menu action runs exactly the model code
the Tk menu runs.

Nothing here is imported by the Tk application, and nothing here imports PySide6 at package level
-- `import KrakenOS.UI.qt` stays cheap and Qt-free until a shell is actually built.
"""
from __future__ import annotations

__all__ = ["ActionManager", "DockManager", "SceneViewport", "SurfaceRowsModel",
           "KrakenQtMainWindow", "run"]


def __getattr__(name):  # lazy: importing a symbol pulls in PySide6, importing the package does not
    if name == "ActionManager":
        from KrakenOS.UI.qt.actions import ActionManager

        return ActionManager
    if name == "DockManager":
        from KrakenOS.UI.qt.docks import DockManager

        return DockManager
    if name == "SceneViewport":
        from KrakenOS.UI.qt.viewport import SceneViewport

        return SceneViewport
    if name == "SurfaceRowsModel":
        from KrakenOS.UI.qt.rows_table import SurfaceRowsModel

        return SurfaceRowsModel
    if name in ("KrakenQtMainWindow", "run"):
        from KrakenOS.UI.qt import app, main_window

        return {"KrakenQtMainWindow": main_window.KrakenQtMainWindow, "run": app.run}[name]
    raise AttributeError(name)
