"""Dock widgets and the default window layout (docs/design_qt_migration.md phase 2).

Structure follows `optiland_gui/panel_manager.py` (MIT, (c) 2024 Kramer Harrison): one factory for
every dock, one place that arranges them, and an object name on each so Qt can save and restore
the arrangement.
"""
from __future__ import annotations


class DockManager:
    """Creates the shell's docks and arranges them."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.docks: dict[str, object] = {}

    def create_dock(self, widget, name: str, title: str, area=None):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget

        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(name)
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable
                         | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.main_window.addDockWidget(area or Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.docks[name] = dock
        return dock

    def setup_default_layout(self, width_hint: int = 620) -> None:
        """The surface table down the left, everything else stacked under it."""
        from PySide6.QtCore import Qt

        docks = [self.docks[name] for name in ("SurfaceTableDock",) if name in self.docks]
        if docks:
            self.main_window.resizeDocks(docks, [width_hint] * len(docks),
                                         Qt.Orientation.Horizontal)

    def __getitem__(self, name):
        return self.docks[name]
