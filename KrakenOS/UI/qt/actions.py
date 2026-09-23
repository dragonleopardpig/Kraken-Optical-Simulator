"""The action registry for the Qt shell (docs/design_qt_migration.md phase 2).

Structure follows `optiland_gui/action_manager.py` (MIT, (c) 2024 Kramer Harrison) -- a factory
that builds every QAction into one dictionary, so the window stays orchestration and a menu, a
toolbar and a test all reach the same action by name.
"""
from __future__ import annotations

#: name -> (menu, text, shortcut, main-window method, tooltip)
ACTIONS = (
    ("open", "&File", "&Open Layout...", "Ctrl+O", "open_layout_action",
     "Open a Kraken layout -- the same model code the Tk editor's File menu runs"),
    ("reload", "&File", "&Reload Layout", "Ctrl+R", "reload_layout_action",
     "Re-read the current layout file from disk"),
    ("quit", "&File", "&Quit", "Ctrl+Q", "quit_action", "Close the Qt shell"),
    ("reset_camera", "&View", "&Fit Scene", "Ctrl+0", "reset_camera_action",
     "Frame every drawn body"),
    ("redraw", "&View", "&Redraw", "F5", "redraw_action", "Rebuild the scene from the model"),
    ("about", "&Help", "&About", None, "about_action", "What this window is"),
)


class ActionManager:
    """Creates every QAction of the shell and keeps them under their names."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.actions: dict[str, object] = {}

    def create_all_actions(self) -> dict[str, object]:
        from PySide6.QtGui import QAction, QKeySequence

        for name, _menu, text, shortcut, method, tooltip in ACTIONS:
            action = QAction(text, self.main_window)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            action.setToolTip(tooltip)
            handler = getattr(self.main_window, method)
            action.triggered.connect(handler)
            self.actions[name] = action
        return self.actions

    def populate_menu_bar(self, menu_bar) -> dict[str, object]:
        """Add every action to its menu, in declaration order. Returns menu title -> QMenu."""
        menus: dict[str, object] = {}
        for name, title, *_rest in ACTIONS:
            menu = menus.get(title)
            if menu is None:
                menu = menus[title] = menu_bar.addMenu(title)
            menu.addAction(self.actions[name])
        return menus

    def __getitem__(self, name):
        return self.actions[name]
