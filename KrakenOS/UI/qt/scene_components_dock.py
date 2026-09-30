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
        self._in_selection = False
        # the dock: the tree over the Properties / Selected-Element pane (bugs/0932)
        self.container = self._build_pane()
        # the model tells the shell when the browser or its selection's properties changed
        inspector.scene_components_changed = self.rebuild
        inspector.scene_properties_changed = self.refresh_properties
        self.rebuild()
        self.refresh_properties()

    def _build_pane(self):
        """The tree above the pane the Tk browser shows under it: Import, Properties, Selected
        Element (the ten actions + face direction) and STEP Placement -- the same panel methods."""
        from PySide6.QtWidgets import (QComboBox, QFormLayout, QGridLayout, QGroupBox, QLabel, QPushButton,
                                       QSplitter, QScrollArea, QVBoxLayout, QWidget)
        from PySide6.QtCore import Qt

        panel = self.panel()
        self.controls: dict = {}
        pane = QWidget()
        layout = QVBoxLayout(pane)

        imports = QGroupBox("Import")
        grid = QGridLayout(imports)
        for index, (label, key) in enumerate((("Optical", "optical"), ("Imaging Lens", "lens"),
                                               ("Camera", "camera"), ("LED", "led"))):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, k=key: self.panel()._import_step(k))
            grid.addWidget(button, index // 2, index % 2)
            self.controls[f"Import/{label}"] = button
        layout.addWidget(imports)

        properties = QGroupBox("Properties")
        form = QFormLayout(properties)
        self.property_labels: dict = {}
        for key, label in panel.PROPERTY_ROWS:
            value = QLabel("-")
            value.setWordWrap(True)
            form.addRow(label, value)
            self.property_labels[key] = value
        layout.addWidget(properties)

        actions = QGroupBox("Selected Element")
        grid = QGridLayout(actions)
        self.action_buttons: dict = {}
        for index, (key, label, method) in enumerate(panel.SELECTION_ACTIONS):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, m=method: getattr(self.panel(), m)())
            grid.addWidget(button, index // 2, index % 2)
            self.action_buttons[key] = button
        grid.addWidget(QLabel("Face direction"), (len(panel.SELECTION_ACTIONS) + 1) // 2, 0)
        self.face_direction = QComboBox()
        self.face_direction.addItems(["", *panel.FACE_DIRECTIONS])
        self.face_direction.activated.connect(
            lambda _index: self.panel().apply_face_direction(self.face_direction.currentText()))
        grid.addWidget(self.face_direction, (len(panel.SELECTION_ACTIONS) + 1) // 2, 1)
        layout.addWidget(actions)

        placement = QGroupBox("STEP Placement")
        grid = QGridLayout(placement)
        # (label, inspector method, row, column, column span) -- the Tk pane's layout
        for label, method, row, column, span in (
                ("Accept STEP Placement", "accept_selected_step_placement", 0, 0, 2),
                ("Promote STEP Row", "promote_selected_step_to_optical_solid_row", 1, 0, 1),
                ("Clear STEP", "clear_step_imports", 1, 1, 1)):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, m=method: getattr(self.inspector, m)())
            grid.addWidget(button, row, column, 1, span)
            self.controls[label] = button
        layout.addWidget(placement)
        layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidget(pane)
        scroll.setWidgetResizable(True)
        split = QSplitter(Qt.Orientation.Vertical)
        split.addWidget(self.widget)
        split.addWidget(scroll)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        # the dock may shrink to the tree's own minimum: the splitter summed both children's, and
        # the 74 extra pixels came out of the 3D viewport (phase 707's L measured 377 px, 0932)
        split.setMinimumHeight(self.widget.minimumSizeHint().height())
        return split

    def refresh_properties(self) -> None:
        """Show what the browser's pane shows for its current selection."""
        panel = self.panel()
        if panel is None or not hasattr(self, "property_labels"):
            return
        shown = panel.properties_for(str(getattr(panel, "_selected_item_id", "") or ""))
        for key, label in self.property_labels.items():
            label.setText(str(shown["values"].get(key, "-")))
        for key, button in self.action_buttons.items():
            button.setEnabled(bool(shown["buttons"].get(key, False)))
        self.face_direction.setEnabled(bool(shown["face_direction"]))

    def panel(self):
        return self.inspector._open3d_step_admin_panel()

    def rebuild(self) -> None:
        """Re-draw the nodes, keeping each item's expansion and the browser's selection."""
        from PySide6.QtGui import QBrush, QColor
        from PySide6.QtWidgets import QTreeWidgetItem

        if self._in_selection:
            # a click's selection reaches the editor, whose refresh asks for this rebuild -- and
            # clear() would delete the very item Qt is still selecting: an intermittent segfault
            # (bugs/0932, measured 3 of 3 selections re-entering). Rebuild once the signal returns.
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, self.rebuild)
            return
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
            self._in_selection = True
            try:
                panel.select_iid(self._iid_of(chosen[0]) if chosen else "")
            finally:
                self._in_selection = False

    def _context_menu(self, position) -> None:
        item = self.widget.itemAt(position)
        panel = self.panel()
        if panel is None:
            return
        point = self.widget.viewport().mapToGlobal(position)
        event = SimpleNamespace(x=position.x(), y=position.y(), x_root=point.x(), y_root=point.y())
        panel.show_menu_for_iid(self._iid_of(item), event)
