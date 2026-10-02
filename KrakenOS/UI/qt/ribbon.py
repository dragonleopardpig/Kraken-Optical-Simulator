"""The Qt shell's ribbon: tabbed groups of icon commands + a command palette (bugs/0935).

The ribbon is layout only. Every button runs one of the shell's own `QAction`s (`actions.ACTIONS`),
so a ribbon click, a menu click and a shortcut are the same call, a checkable action (Show Rays)
shows one state everywhere, and the menus stay for keyboard use. `RIBBON` is the whole layout as
data; `RIBBON_EXCLUDED` names the actions left off it on purpose, so a new action cannot quietly
go missing (the guard checks the two cover `ACTIONS` exactly).

The Analysis tab also carries the plot picker, Update and WFront 3D -- the same menu and actions as
`AnalysisToolbar`, whose own toolbar row is hidden so the ribbon does not cost the 3D viewport a
second strip of height.

Folded (the default on a short screen, or double-click a tab), only the tab row shows; clicking a
tab drops its page over the window as a pop-up, which closes once a command runs -- the 3D view
keeps its height. Double-click a tab to pin the ribbon open, or folded again.

It lives in a dock (bugs/0940): the slim title bar down its left edge undocks it (float button or
double-click) into a window of its own, which opens fully; dragged to the top or bottom edge it
docks again and returns to its folded / open state.
"""
from __future__ import annotations

#: tab -> groups -> (action name, "L" large | "S" small, ribbon label). Small buttons stack three
#: to a column. Labels are short forms of the action's text; "\n" breaks a large button's label.
RIBBON = (
    ("Home", (
        ("File", (("open", "L", "Open\nLayout"), ("reload", "L", "Reload"), ("save", "S", "Save"),
                  ("save_as", "S", "Save As"))),
        ("Edit", (("undo", "S", "Undo"), ("redo", "S", "Redo"))),
        ("View", (("reset_camera", "L", "Fit\nScene"), ("inspector", "L", "3D\nInspector"),
                  ("show_rays", "S", "Show Rays"), ("redraw", "S", "Redraw"), ("about", "S", "About"))),
    )),
    ("Surfaces", (
        ("Surface", (("advanced_surface", "L", "Advanced\nSurface"), ("surface_shape", "L", "Shape\nBuilder"),
                     ("coating_material", "S", "Coating / Material"), ("error_map", "S", "Error Map"))),
        ("Special rows", (("beam_splitter", "S", "Beam Splitter"), ("diffuse_scatter", "S", "Diffuse / BRDF"),
                          ("grating_settings", "S", "Grating"), ("detector_settings", "S", "Detector"),
                          ("galvo_scan", "S", "Galvo Scan"))),
        ("Catalogs", (("glass_catalog", "L", "Glass\nCatalog"), ("stock_lens", "L", "Stock\nLens"))),
    )),
    ("Scene", (
        ("Placement", (("scene_target", "L", "Scene\nTarget"), ("path_local_pose", "S", "Path-Local Pose"),
                       ("element_settings", "S", "Element Settings"))),
        ("Sources", (("scene_sources", "L", "Source\nManager"), ("source_edit", "L", "Edit\nSource"))),
        ("CAD", (("face_roles", "L", "Optical\nFaces"), ("optical_solid_diagnostics", "L", "Inspect\nSolids"))),
        ("Inspection", (("inspection_cell", "L", "Inspection\nCell"), ("inspection_part", "L", "Inspection\nPart"))),
    )),
    ("Analysis", (
        # the plot picker / Update / WFront 3D come first -- see `Ribbon._plots_group`
        ("Measure", (("mtf_from_image", "L", "MTF from\nImage"),)),
        ("Paraxial", (("paraxial_matrix", "L", "Paraxial\nMatrix"), ("paraxial_calculator", "L", "Paraxial\nCalculator"),
                      ("gaussian_beam", "S", "Gaussian Beam"), ("branch_gaussian_q", "S", "Branch Gaussian q"))),
        ("Rays", (("ray_inspector", "L", "Ray\nInspector"), ("trace_paths", "S", "Trace Paths"),
                  ("nonseq_scene_graph", "S", "Scene Graph"))),
        ("Power", (("detector_aperture", "S", "Detector Aperture"), ("branch_throughput", "S", "Path Throughput"),
                   ("source_illumination", "S", "Source Illumination"))),
        ("Design", (("system_selection", "L", "System\nSelection"), ("catalog_matcher", "L", "Lens\nMatcher"))),
    )),
    # its own tab since the reports were routed (bugs/0943): on the Analysis tab they made the window
    # at least ~1500 px wide (1240 before)
    ("Tolerance", (
        ("Run", (("tolerance_monte_carlo", "L", "Monte\nCarlo"), ("tolerance_worst_sample", "S", "Worst Sample"),
                 ("tolerance_stackup", "S", "Stack-Up"))),
        ("Compensators", (("tolerance_compensator", "L", "Compensator\nSweep"),
                          ("tolerance_multi_compensator", "L", "Multi-\nCompensator"))),
        ("Presets", (("tolerance_preset", "S", "Save Preset"), ("apply_tolerance_preset", "S", "Apply Preset"))),
    )),
)

#: actions deliberately not on the ribbon -> why
RIBBON_EXCLUDED = {"quit": "leaves the application: File menu and Ctrl+Q only, never one stray click away"}
# menu + palette only (bugs/0942): Tk menu-bar commands given a Qt route -- occasional imports,
# exports, clears and reports, reached from the menus and Ctrl+Shift+P, not worth ribbon space
_MENU_ONLY = {
    "wipes the whole layout -- File menu only, like Quit (Undo brings it back)": ("reset",),
    "imports and exports (File menu)": ("import_zemax", "import_zemax_wavefront", "import_cad_solid",
                                        "import_lens_step", "import_camera_step", "import_led_step",
                                        "export_3d_step", "export_3d_dxf", "export_wavefront_csv",
                                        "export_zernike_csv"),
    "row clipboard and scene clears (Edit menu; Ctrl+C / Ctrl+V for rows)": (
        "copy_rows", "paste_rows", "clear_cad_axis_offsets", "clear_step_imports", "place_cad_solid"),
    "occasional view / analysis commands (View and Analysis menus)": (
        "refresh_plot", "folded_assembly", "benchmark_psf_mtf", "copy_phase2_report", "copy_wavefront_fit",
        "clear_zemax_wavefront", "clear_marks"),
    "help (Help menu)": ("formula_sheet", "manual_index", "copy_debug"),
    # bugs/0943: each needs its report or a trace first, so a ribbon button would mostly refuse
    "analysis CSV exports (File > Export Analysis CSV; tolerance ones in Analysis > Tolerance)": (
        "export_path_psf_csv", "export_path_mtf_csv", "export_detector_map_csv", "export_coherent_detector_csv",
        "export_branch_field_csv", "export_tolerance_monte_carlo_csv", "export_tolerance_comparison_csv",
        "export_tolerance_stackup_csv", "export_tolerance_compensator_csv",
        "export_tolerance_multi_compensator_csv", "export_tolerance_overlay_csv"),
}
RIBBON_EXCLUDED.update({name: f"menu + palette only: {why}" for why, names in _MENU_ONLY.items() for name in names})

LARGE_ICON = 26
SMALL_ICON = 16
PALETTE_SHORTCUT = "Ctrl+Shift+P"
#: below this many logical pixels of screen height the ribbon starts folded to its tab row: an open
#: ribbon is ~110 px, which a 1000-px screen cannot give up without squeezing the 3D view
FOLD_BELOW_SCREEN_HEIGHT = 1100


def ribbon_entries() -> list:
    """Every (tab, group, action name, size, label) on the ribbon, in order."""
    return [(tab, group, name, size, label)
            for tab, groups in RIBBON for group, entries in groups for name, size, label in entries]


def plain_text(text: str) -> str:
    """An action's menu text without its mnemonic and ellipsis: "&Open Layout..." -> "Open Layout"."""
    return str(text).replace("&&", "\0").replace("&", "").replace("\0", "&").rstrip(".").rstrip("…").strip()


class Ribbon:
    """The ribbon for ``main_window`` -- built from its `action_manager` actions."""

    def __init__(self, main_window) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget, QTabWidget

        from KrakenOS.UI.qt.icons import icon

        self.main_window = main_window
        self.actions = main_window.action_manager.actions
        #: action name -> the ribbon button that runs it (on the docked pages)
        self.buttons: dict[str, object] = {}
        #: tab index -> its pop-up page, built the first time it is shown folded
        self.popups: dict[int, object] = {}
        self._building_popup = False
        # the menus get the same icons as the ribbon
        for name, action in self.actions.items():
            action.setIcon(icon(name))
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("Ribbon")
        for tab, groups in RIBBON:
            self.tabs.addTab(self._page(tab, groups), tab)
        self.tabs.setCornerWidget(self._palette(), Qt.Corner.TopRightCorner)
        # double-click a tab to fold the ribbon to its tab row, and again to open it (as Office);
        # folded, a click on a tab shows its page as a pop-up
        self.tabs.tabBarDoubleClicked.connect(lambda _index: self.set_collapsed(not self.collapsed))
        self.tabs.tabBarClicked.connect(self._tab_clicked)
        self.collapsed = False
        # a dock, so it can be undocked (user request, bugs/0940): its title bar runs down the
        # LEFT edge (no height taken from the 3D view) -- its float button, or a double-click on
        # it, makes the ribbon a window of its own; dragged back to the top or bottom it docks
        dock = self.dock = QDockWidget("Ribbon", main_window)
        dock.setObjectName("RibbonDock")
        dock.setWidget(self.tabs)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetFloatable
                         | QDockWidget.DockWidgetFeature.DockWidgetVerticalTitleBar)
        dock.setAllowedAreas(Qt.DockWidgetArea.TopDockWidgetArea | Qt.DockWidgetArea.BottomDockWidgetArea)
        main_window.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, dock)
        dock.topLevelChanged.connect(self._on_floating_changed)
        self._collapsed_when_docked = False
        if self._short_screen():
            self.set_collapsed(True)
        else:
            self._fit_docked_height()

    # ---- the pages ------------------------------------------------------------------------------
    def _page(self, tab: str, groups):
        from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget

        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(2, 1, 2, 0)
        row.setSpacing(2)
        built = [self._plots_group()] if tab == "Analysis" else []
        built += [self._group(title, entries) for title, entries in groups]
        for index, group in enumerate(built):
            if index:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.VLine)
                line.setFrameShadow(QFrame.Shadow.Sunken)
                row.addWidget(line)
            row.addWidget(group)
        row.addStretch(1)
        return page

    def _group_frame(self, title: str):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

        group = QWidget()
        column = QVBoxLayout(group)
        column.setContentsMargins(2, 0, 2, 0)
        column.setSpacing(0)
        buttons = QHBoxLayout()
        buttons.setSpacing(2)
        column.addLayout(buttons, 1)
        caption = QLabel(title)
        caption.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        caption.setEnabled(False)          # the palette's muted text colour
        column.addWidget(caption)
        return group, buttons

    def _group(self, title: str, entries):
        from PySide6.QtWidgets import QVBoxLayout

        group, buttons = self._group_frame(title)
        stack = None
        for name, size, label in entries:
            button = self._button(name, size, label)
            if size == "L":
                stack = None
                buttons.addWidget(button)
                continue
            if stack is None or stack.count() >= 3:
                stack = QVBoxLayout()
                stack.setSpacing(0)
                buttons.addLayout(stack)
            stack.addWidget(button)
        return group

    def _button(self, name: str, size: str, label: str):
        from PySide6.QtCore import QSize, Qt
        from PySide6.QtWidgets import QToolButton

        action = self.actions[name]
        button = QToolButton()
        button.setAutoRaise(True)
        button.setIcon(action.icon())
        button.setText(label)
        large = size == "L"
        button.setIconSize(QSize(LARGE_ICON, LARGE_ICON) if large else QSize(SMALL_ICON, SMALL_ICON))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon if large
                                  else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        shortcut = action.shortcut().toString()
        tip = plain_text(action.text()) + (f"  ({shortcut})" if shortcut else "")
        button.setToolTip(f"<b>{tip}</b><br>{action.toolTip()}" if action.toolTip() else tip)
        if action.isCheckable():
            # one state everywhere: the button mirrors the action, and a click runs trigger() --
            # which toggles the action and hands its handler the NEW state. (Emitting `triggered`
            # by hand reached the handler with its default argument: the button said "hidden"
            # while the rays stayed on -- caught by the guard's R.)
            button.setCheckable(True)
            button.setChecked(action.isChecked())
            action.toggled.connect(button.setChecked)
        button.clicked.connect(lambda _checked=False, a=action: a.trigger())
        action.changed.connect(lambda b=button, a=action: b.setEnabled(a.isEnabled()))
        button.clicked.connect(self._close_popups)
        if not self._building_popup:
            self.buttons[name] = button
        return button

    def _plots_group(self):
        """The Analysis picker as a ribbon group: its "Select plots" menu, Update and WFront 3D --
        `AnalysisToolbar`'s own menu and actions, so the model's caption shows here too."""
        from PySide6.QtCore import QSize, Qt
        from PySide6.QtWidgets import QToolButton, QVBoxLayout

        from KrakenOS.UI.qt.icons import icon

        bar = self.main_window.analysis_toolbar
        bar.toolbar.hide()                     # its row would cost the viewport another strip
        group, buttons = self._group_frame("Plots")
        picker = QToolButton()
        picker.setAutoRaise(True)
        picker.setIcon(icon("branch_throughput"))
        picker.setIconSize(QSize(LARGE_ICON, LARGE_ICON))
        picker.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        picker.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        picker.setMenu(bar.menu)
        picker.setToolTip(bar.button.toolTip())
        picker.setText(bar.button.text())
        bar.caption_listeners.append(picker.setText)
        if not self._building_popup:
            self.plot_picker_docked = picker
        buttons.addWidget(picker)
        stack = QVBoxLayout()
        stack.setSpacing(0)
        for action, name in ((bar.update_action, "redraw"), (bar.wavefront_action, "surface_shape")):
            action.setIcon(icon(name))
            button = QToolButton()
            button.setAutoRaise(True)
            button.setIconSize(QSize(SMALL_ICON, SMALL_ICON))
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.setDefaultAction(action)
            stack.addWidget(button)
        if not self._building_popup:
            self.update_button, self.wavefront_button = stack.itemAt(0).widget(), stack.itemAt(1).widget()
        buttons.addLayout(stack)
        return group

    # ---- the command palette ----------------------------------------------------------------------
    def _palette(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QKeySequence, QShortcut
        from PySide6.QtWidgets import QCompleter, QLineEdit

        from KrakenOS.UI.qt.icons import icon

        self.commands = {plain_text(action.text()): name for name, action in self.actions.items()}
        box = self.palette = QLineEdit()
        box.setPlaceholderText(f"Search commands ({PALETTE_SHORTCUT})")
        box.setClearButtonEnabled(True)
        box.addAction(icon("search"), QLineEdit.ActionPosition.LeadingPosition)
        box.setMinimumWidth(260)
        completer = self.completer = QCompleter(sorted(self.commands), box)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        box.setCompleter(completer)
        completer.activated.connect(self.run_command)
        box.returnPressed.connect(lambda: self.run_command(box.text()))
        shortcut = self.palette_shortcut = QShortcut(QKeySequence(PALETTE_SHORTCUT), self.main_window)
        shortcut.activated.connect(self.focus_palette)
        return box

    def focus_palette(self) -> None:
        # the palette sits in the tab row, which stays up when folded: no need to unfold (and
        # take the 3D view's height) just to type a command
        self.palette.setFocus()
        self.palette.selectAll()

    def match(self, text: str) -> "str | None":
        """The action a typed query means: an exact title, else the one title containing it."""
        query = str(text).strip().lower()
        if not query:
            return None
        exact = [name for title, name in self.commands.items() if title.lower() == query]
        if exact:
            return exact[0]
        hits = [name for title, name in self.commands.items() if query in title.lower()]
        return hits[0] if len(hits) == 1 else None

    def run_command(self, text: str) -> "str | None":
        """Run the command ``text`` names (a completion or a unique fragment); returns its name."""
        name = self.match(text)
        if name is None:
            self.main_window.statusBar().showMessage(f"No single command matches {text!r}")
            return None
        self.palette.clear()
        self.actions[name].trigger()
        return name

    # ---- folding + floating --------------------------------------------------------------------
    def _short_screen(self) -> bool:
        screen = self.main_window.screen()
        return screen is not None and screen.availableGeometry().height() < FOLD_BELOW_SCREEN_HEIGHT

    def set_collapsed(self, collapsed: bool) -> None:
        """Fold the ribbon to its tab row (more room for the 3D view), or open it again."""
        from PySide6.QtWidgets import QStackedWidget

        self.collapsed = bool(collapsed)
        self._close_popups()
        bar_height = self.tabs.tabBar().sizeHint().height()
        # fold by hiding the tab widget's PAGE STACK: showing each page by hand on unfold made
        # all four visible at once, drawn over each other (bugs/0940 -- seen floating; the
        # double-click unfold had it since 0935). The stack keeps showing only the current page.
        stack = self.tabs.findChild(QStackedWidget)
        if stack is not None:
            stack.setVisible(not self.collapsed)
        self.tabs.setMaximumHeight(bar_height + 4 if self.collapsed else 16777215)
        self._fit_docked_height()

    def _fit_docked_height(self) -> None:
        """Docked, the ribbon is exactly as tall as its content -- the dock splitter must not hand
        it (or take from it) the 3D view's height. Floating, it is a free window."""
        dock = getattr(self, "dock", None)
        if dock is None:
            return
        if dock.isFloating():
            dock.setMinimumHeight(0)
            dock.setMaximumHeight(16777215)
            return
        # FIXED, not just capped: re-docked, the layout kept the floating window's height even
        # under a 30-px maximum (measured: 114 px folded)
        dock.setFixedHeight(self.tabs.maximumHeight() if self.collapsed else self.tabs.sizeHint().height() + 2)

    def set_floating(self, floating: bool) -> None:
        """Undock the ribbon into a window of its own, or dock it back at the top."""
        self.dock.setFloating(bool(floating))

    def _on_floating_changed(self, floating: bool) -> None:
        # a floating ribbon costs the 3D view nothing, so it opens fully; docked again, it goes
        # back to how it was (folded on a short screen)
        if floating:
            self._collapsed_when_docked = self.collapsed
            self.dock.setMinimumHeight(0)
            self.dock.setMaximumHeight(16777215)
            if self.collapsed:
                self.set_collapsed(False)
            self.dock.adjustSize()
        else:
            self.set_collapsed(self._collapsed_when_docked)

    def _tab_clicked(self, index: int) -> None:
        if self.collapsed and index >= 0:
            self.show_popup(index)

    def show_popup(self, index: int):
        """Folded: drop tab ``index``'s page under the tab row, over the window, until a command
        runs or the user clicks away (Qt closes a pop-up on an outside click)."""
        from PySide6.QtCore import QPoint, Qt
        from PySide6.QtWidgets import QFrame, QVBoxLayout

        popup = self.popups.get(index)
        if popup is None:
            tab, groups = RIBBON[index]
            self._building_popup = True
            try:
                page = self._page(tab, groups)
            finally:
                self._building_popup = False
            popup = QFrame(self.main_window, Qt.WindowType.Popup)
            popup.setFrameShape(QFrame.Shape.StyledPanel)
            layout = QVBoxLayout(popup)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(page)
            self.popups[index] = popup
        popup.adjustSize()
        popup.move(self.tabs.mapToGlobal(QPoint(0, self.tabs.tabBar().height())))
        popup.show()
        return popup

    def _close_popups(self, *_args) -> None:
        for popup in self.popups.values():
            popup.hide()
