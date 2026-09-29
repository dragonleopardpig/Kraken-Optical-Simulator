"""The Scene Components browser in the Qt shell (docs/design_qt_migration.md phase 5f, part 3b).

The Tk browser (`panels/open3d_step_admin.py`) sits in the inspector's withdrawn window. Its tree
is data now (`tree_nodes`), a click is `select_iid` and a right-click is `show_menu_for_iid`, whose
menus record a `MenuModel` under a shell and open as a QMenu (0907) -- so this is layout and
routing only: the same nodes, the same selection, the same menus.
"""
from __future__ import annotations

from types import SimpleNamespace

ROLE_IID = 32  # Qt.ItemDataRole.UserRole


class SceneComponentsTree:
    """A QTreeWidget over the browser's nodes; ``items`` maps an iid to its item."""

    def __init__(self, inspector) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QTreeWidget

        self.inspector = inspector
        self.widget = QTreeWidget()
        self.widget.setHeaderHidden(True)
        self.widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.widget.itemSelectionChanged.connect(self._selected)
        self.widget.customContextMenuRequested.connect(self._context_menu)
        self.items: dict = {}
        self._rebuilding = False
        # the model tells the shell when the browser changed (inspector.refresh_step_admin_panel)
        inspector.scene_components_changed = self.rebuild
        self.rebuild()

    def panel(self):
        return self.inspector._open3d_step_admin_panel()

    def rebuild(self) -> None:
        """Re-draw the nodes, keeping each item's expansion and the browser's selection."""
        from PySide6.QtGui import QBrush, QColor
        from PySide6.QtWidgets import QTreeWidgetItem

        panel = self.panel()
        if panel is None:
            return
        expanded = {iid: item.isExpanded() for iid, item in self.items.items()}
        self._rebuilding = True
        try:
            self.widget.clear()
            self.items = {}
            for node in panel.tree_nodes():
                parent = self.items.get(node["parent"]) if node["parent"] else None
                item = QTreeWidgetItem([str(node["text"])])
                item.setData(0, ROLE_IID, node["iid"])
                if "hidden" in node["tags"]:
                    item.setForeground(0, QBrush(QColor("#9a9a9a")))
                if parent is None:
                    self.widget.addTopLevelItem(item)
                else:
                    parent.addChild(item)
                self.items[node["iid"]] = item
                if node["open"] is not None:
                    item.setExpanded(expanded.get(node["iid"], bool(node["open"])))
            selected = str(getattr(panel, "_selected_item_id", "") or "")
            if selected in self.items:
                self.items[selected].setSelected(True)
                self.widget.setCurrentItem(self.items[selected])
        finally:
            self._rebuilding = False

    def _iid_of(self, item) -> str:
        return "" if item is None else str(item.data(0, ROLE_IID) or "")

    def _selected(self) -> None:
        if self._rebuilding:
            return
        chosen = self.widget.selectedItems()
        panel = self.panel()
        if panel is not None:
            panel.select_iid(self._iid_of(chosen[0]) if chosen else "")

    def _context_menu(self, position) -> None:
        item = self.widget.itemAt(position)
        panel = self.panel()
        if panel is None:
            return
        point = self.widget.viewport().mapToGlobal(position)
        event = SimpleNamespace(x=position.x(), y=position.y(), x_root=point.x(), y_root=point.y())
        panel.show_menu_for_iid(self._iid_of(item), event)
