"""Dock widgets and the default window layout (docs/design_qt_migration.md phase 2).

Structure follows `optiland_gui/panel_manager.py` (MIT, (c) 2024 Kramer Harrison): one factory for
every dock, one place that arranges them, and an object name on each so Qt can save and restore
the arrangement.

`EdgeRails` (user request, bugs/0952): a slim strip on each window edge with one tab per panel
docked on that edge -- the text running along the edge, so upright on the left and right -- to hide
a panel and bring it back. The bottom strip is the status bar itself (its right end): a second row
there would cost the 3D scene 29 px for nothing. For the same reason the TOP strip rides in the
ribbon's tab row while the ribbon is docked at the top (bugs/0962): a row of its own took 36 px for
one tab, in a Clean 3D Scene as well.

Each strip starts with one more button, Hide All Panels (user request, bugs/0961: "the side tabs,
can have 'one click hide all' option?"): one click puts every open panel away, the next brings
back the same ones -- each in its place, at its size, the same tab in front.
"""
from __future__ import annotations

#: rail edge -> (the dock area it serves, the toolbar area its strip sits in -- None: the status
#: bar), as Qt attribute names
EDGES = {
    "left": ("LeftDockWidgetArea", "LeftToolBarArea"),
    "right": ("RightDockWidgetArea", "RightToolBarArea"),
    "top": ("TopDockWidgetArea", "TopToolBarArea"),
    "bottom": ("BottomDockWidgetArea", None),
}


def _tool_button_base():
    from PySide6.QtWidgets import QToolButton

    return QToolButton


class RailTab(_tool_button_base()):
    """One panel's tab on an edge rail. Checked while the panel is on show."""

    def __init__(self, text: str, edge: str, parent=None) -> None:
        from PySide6.QtCore import Qt

        super().__init__(parent)
        self.edge = edge
        self.setText(text)
        self.setCheckable(True)
        self.setAutoRaise(True)
        self.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    @property
    def upright(self) -> bool:
        return self.edge in ("left", "right")

    def sizeHint(self):  # noqa: N802  (Qt's name)
        size = super().sizeHint()
        return size.transposed() if self.upright else size

    def minimumSizeHint(self):  # noqa: N802  (Qt's name)
        return self.sizeHint()

    def paintEvent(self, event) -> None:  # noqa: N802  (Qt's name)
        if not self.upright:
            super().paintEvent(event)
            return
        from PySide6.QtWidgets import QStyle, QStyleOptionToolButton, QStylePainter

        painter = QStylePainter(self)
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        if self.edge == "left":            # reads bottom to top, as on the spine of a book
            painter.translate(0, self.height())
            painter.rotate(-90)
        else:                              # the right edge reads top to bottom
            painter.translate(self.width(), 0)
            painter.rotate(90)
        option.rect = option.rect.transposed()
        painter.drawComplexControl(QStyle.ComplexControl.CC_ToolButton, option)


class EdgeRails:
    """The four edge strips and the tabs on them.

    A click on a tab:
      * of a hidden panel shows it (with the panels it was tabbed with, itself in front);
      * of a panel behind another tab brings it to the front;
      * of the panel on show hides it -- together with the panels tabbed with it, so one click
        folds that edge's stack and gives its room to the 3D scene.
    """

    def __init__(self, main_window) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QHBoxLayout, QToolBar, QWidget

        self.main_window = main_window
        #: edge -> its strip: a toolbar on the left, right and top; a row in the status bar below
        self.rails: dict[str, object] = {}
        #: dock object name -> its tab
        self.tabs: dict[str, object] = {}
        self._docks: dict[str, object] = {}
        #: dock -> the docks hidden with it by one click, to show again together
        self._folded_with: dict = {}
        #: dock -> its (width, height) when a tab hid it; Qt would bring it back at its minimum
        self._size_when_hidden: dict = {}
        #: (dock, was in front) for each panel Hide All put away, to bring back the same ones
        self._all_hidden: list = []
        #: callables run after every refresh -- the shell keeps its Hide All switch in step
        self.listeners: list = []
        #: edge -> its Hide All button
        self.hide_all_buttons: dict = {}
        for edge, (_dock_area, bar_area) in EDGES.items():
            if bar_area is None:
                strip = QWidget()
                row = QHBoxLayout(strip)
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(2)
                main_window.statusBar().addPermanentWidget(strip)
            else:
                strip = QToolBar(f"{edge.title()} panels", main_window)
                strip.setMovable(False)
                strip.setFloatable(False)
                strip.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
                strip.toggleViewAction().setVisible(False)      # a rail is not itself hidden
                main_window.addToolBar(getattr(Qt.ToolBarArea, bar_area), strip)
            strip.setObjectName(f"EdgeRail{edge.title()}")
            strip.hide()                                         # until a panel lands on that edge
            self.rails[edge] = strip

    # ---- which edge, and what state -------------------------------------------------------------
    def edge_of(self, dock) -> "str | None":
        from PySide6.QtCore import Qt

        area = self.main_window.dockWidgetArea(dock)
        for edge, (dock_area, _bar_area) in EDGES.items():
            if area == getattr(Qt.DockWidgetArea, dock_area):
                return edge
        return None

    @staticmethod
    def is_open(dock) -> bool:
        return not dock.isHidden()

    @staticmethod
    def is_front(dock) -> bool:
        """On show: open, and not behind another tab of its stack."""
        return not dock.isHidden() and (dock.isFloating() or not dock.visibleRegion().isEmpty())

    # ---- building -------------------------------------------------------------------------------
    def add(self, dock) -> None:
        """Give ``dock`` a tab on the rail of the edge it is docked on."""
        name = dock.objectName()
        if name in self.tabs:
            return
        self._docks[name] = dock
        self._place_tab(dock, self.edge_of(dock) or "left")
        dock.visibilityChanged.connect(lambda _visible: self.refresh())
        dock.topLevelChanged.connect(lambda _floating: self.refresh())
        dock.dockLocationChanged.connect(lambda _area, d=dock: self._moved(d))
        self.refresh()

    def _place_tab(self, dock, edge: str) -> None:
        tab = RailTab(dock.windowTitle(), edge)
        tab.setToolTip(f"Hide or show the {dock.windowTitle()} panel")
        tab.clicked.connect(lambda _checked=False, d=dock: self.toggle(d))
        strip = self.rails[edge]
        if EDGES[edge][1] is None:
            strip.layout().addWidget(tab)
            tab._rail_action = None
        else:
            tab._rail_action = strip.addWidget(tab)
        self.tabs[dock.objectName()] = tab

    def _moved(self, dock) -> None:
        """The user dragged a panel to another edge: its tab follows -- a new one, drawn for that
        edge, in place of the old."""
        name = dock.objectName()
        tab = self.tabs.get(name)
        edge = self.edge_of(dock)
        if tab is None or edge is None or edge == tab.edge:
            return
        if tab._rail_action is not None:
            self.rails[tab.edge].removeAction(tab._rail_action)
        else:
            self.rails[tab.edge].layout().removeWidget(tab)
        tab.hide()
        tab.deleteLater()
        self._place_tab(dock, edge)
        self.refresh()

    def refresh(self) -> None:
        """Tabs follow their panels: checked while on show; a rail with no tab is not drawn."""
        used = set()
        for name, tab in self.tabs.items():
            front = self.is_front(self._docks[name])
            if tab.isChecked() != front:
                tab.setChecked(front)
            used.add(tab.edge)
        for edge, bar in self.rails.items():
            if bar.isVisible() != (edge in used):
                bar.setVisible(edge in used)
        for listener in self.listeners:
            listener()

    # ---- the click --------------------------------------------------------------------------------
    def toggle(self, dock) -> None:
        window = self.main_window
        if not self.is_open(dock):
            group = self._folded_with.pop(dock, None) or [dock]
            for member in group:
                self._folded_with.pop(member, None)
                member.show()
            dock.raise_()
            self._restore_size(dock)
        elif not self.is_front(dock):
            dock.raise_()
        else:
            group = [dock] + [other for other in window.tabifiedDockWidgets(dock) if self.is_open(other)]
            for member in group:
                self._folded_with[member] = group
                self._size_when_hidden[member] = (dock.width(), dock.height())
            for member in group:
                member.hide()
        self.refresh()

    def _restore_size(self, dock) -> None:
        """Back at the size it was hidden at, once the layout has run (measured: the surface table
        came back 124 px tall, its minimum, where it had been 170)."""
        size = self._size_when_hidden.pop(dock, None)
        edge = self.edge_of(dock)
        if size is None or edge is None or dock.isFloating():
            return
        from PySide6.QtCore import QTimer, Qt

        upright = edge in ("left", "right")
        QTimer.singleShot(0, lambda: self.main_window.resizeDocks(
            [dock], [size[0] if upright else size[1]],
            Qt.Orientation.Horizontal if upright else Qt.Orientation.Vertical))

    # ---- every panel at once (bugs/0961) -----------------------------------------------------------
    def add_hide_all_button(self, action) -> None:
        """Put ``action`` -- the shell's Hide All Panels switch -- first on every strip."""
        from PySide6.QtCore import QSize, Qt
        from PySide6.QtWidgets import QToolButton

        for edge, strip in self.rails.items():
            button = QToolButton(strip)
            button.setDefaultAction(action)
            button.setAutoRaise(True)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            # no wider than a tab: a 32-px button made each side strip 11 px wider, and the
            # window's minimum width with it (measured 1232 -> 1254 px)
            button.setIconSize(QSize(16, 16))
            button.setFixedSize(22, 22)
            if EDGES[edge][1] is None:
                strip.layout().insertWidget(0, button)
            else:
                first = strip.actions()[0] if strip.actions() else None
                if first is None:
                    strip.addWidget(button)
                else:
                    strip.insertWidget(first, button)
            self.hide_all_buttons[edge] = button

    def any_open(self) -> bool:
        return any(self.is_open(dock) for dock in self._docks.values())

    def hide_all(self) -> list:
        """Put every open panel away; returns them. Remembers which were open, which was in front
        of its stack, and each one's size."""
        open_docks = [dock for dock in self._docks.values() if self.is_open(dock)]
        if not open_docks:
            return []
        self._all_hidden = [(dock, self.is_front(dock)) for dock in open_docks]
        for dock, front in self._all_hidden:
            # the size of the panel in FRONT is its stack's; one behind a tab keeps a stale size
            # (measured: 100 px) that would shrink the whole stack when it came back
            if front:
                self._size_when_hidden[dock] = (dock.width(), dock.height())
            else:
                self._size_when_hidden.pop(dock, None)
            self._folded_with.pop(dock, None)
        for dock in open_docks:
            dock.hide()
        self.refresh()
        return open_docks

    def show_all(self, only=None) -> list:
        """Bring back what `hide_all` put away -- or, when it put nothing away (the panels were
        closed one by one), every panel. ``only``: bring back just these, those still closed
        (Clean 3D Scene puts back its own, whatever happened since). Returns the panels shown."""
        if only is not None:
            fronts = dict(self._all_hidden)
            remembered = [(dock, fronts.get(dock, True)) for dock in only if not self.is_open(dock)]
        else:
            remembered = self._all_hidden or [(dock, True) for dock in self._docks.values() if not self.is_open(dock)]
        self._all_hidden = []
        for dock, _front in remembered:
            self._folded_with.pop(dock, None)
            dock.show()
        for dock, front in remembered:
            if front:
                dock.raise_()
        self._restore_sizes([dock for dock, _front in remembered])
        self.refresh()
        return [dock for dock, _front in remembered]

    def _restore_sizes(self, docks) -> None:
        """Every panel back at its size, BOTH ways and in one pass, once the layout has run: panels
        side by side on one edge share its length (measured: the bottom row's Debug came back
        628 px wide where it had been 470, its height right)."""
        sized = [(dock, self._size_when_hidden.pop(dock)) for dock in docks
                 if dock in self._size_when_hidden and not dock.isFloating()]
        if not sized:
            return
        from PySide6.QtCore import QTimer, Qt

        def resize() -> None:
            window = self.main_window
            panels = [dock for dock, _size in sized]
            window.resizeDocks(panels, [size[0] for _dock, size in sized], Qt.Orientation.Horizontal)
            window.resizeDocks(panels, [size[1] for _dock, size in sized], Qt.Orientation.Vertical)

        QTimer.singleShot(0, resize)

    def set_edge_shown(self, edge: str, shown: bool) -> None:
        """Hide or show every panel of one edge."""
        for name, tab in self.tabs.items():
            if tab.edge == edge and self.is_open(self._docks[name]) != bool(shown):
                self._docks[name].setVisible(bool(shown))
        self.refresh()


class DockManager:
    """Creates the shell's docks and arranges them."""

    def __init__(self, main_window) -> None:
        self.main_window = main_window
        self.docks: dict[str, object] = {}
        #: the edge strips with a tab per panel (bugs/0952)
        self.rails = EdgeRails(main_window)

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
        self.rails.add(dock)
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
