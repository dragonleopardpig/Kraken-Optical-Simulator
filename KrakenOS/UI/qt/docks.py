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

    def create_dock(self, widget, name: str, title: str, area=None, *, scroll: bool = False):
        """`scroll`: show a tall form in a scroll area, so its full height is not the dock's
        MINIMUM height -- stacked forms otherwise push the window past the screen (bugs/0906)."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget, QScrollArea

        dock = QDockWidget(title, self.main_window)
        dock.setObjectName(name)
        if scroll:
            area_widget = QScrollArea()
            area_widget.setWidgetResizable(True)
            area_widget.setWidget(widget)
            widget = area_widget
        dock.setWidget(widget)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable
                         | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.main_window.addDockWidget(area or Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.docks[name] = dock
        return dock

    def setup_default_layout(self, width_hint: int = 620) -> None:
        """The side columns' width. The surface table is across the TOP since bugs/0940 (its
        height is set with the inspector's, once the layout has run)."""
        from PySide6.QtCore import Qt

        side = [dock for name, dock in self.docks.items()
                if self.main_window.dockWidgetArea(dock) == Qt.DockWidgetArea.LeftDockWidgetArea]
        if side:
            self.main_window.resizeDocks(side, [width_hint] * len(side), Qt.Orientation.Horizontal)

    def tabify(self, names) -> None:
        """Stack the named docks as tabs of the first one, which stays in front."""
        docks = [self.docks[name] for name in names if name in self.docks]
        for dock in docks[1:]:
            self.main_window.tabifyDockWidget(docks[0], dock)
        if docks:
            docks[0].raise_()

    def __getitem__(self, name):
        return self.docks[name]
