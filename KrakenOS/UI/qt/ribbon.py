"""The Qt shell's ribbon: tabbed groups of icon commands + a command palette (bugs/0935).

The ribbon is layout only. Every button runs one of the shell's own `QAction`s (`actions.ACTIONS`),
so a ribbon click and a shortcut are the same call and a checkable action (Show Rays) shows one
state everywhere. `RIBBON` is the whole layout as data.

The ribbon is the shell's ONLY command surface (user request, bugs/0949): there is no menu bar, so
every action is on it -- as a button, or as an entry of a DROPDOWN button (`DROPDOWNS`: Import,
Export, Help, ...) where a list is long and used now and then. The guard checks that buttons and
dropdowns together reach every one of `ACTIONS` exactly once, so a new action cannot go missing.

The Analysis tab also carries the plot picker, Update and WFront 3D -- the same menu and actions as
`AnalysisToolbar`, whose own toolbar row is hidden so the ribbon does not cost the 3D viewport a
second strip of height.

Folded (while the window is short -- bugs/0963; the small arrow at the end of the tab row, or a
double-click on a tab), only the tab row shows; clicking a tab drops its page over the window as a pop-up, which
closes once a command runs -- the 3D view keeps its height. The arrow, or a double-click on a tab,
pins the ribbon open or folds it again. Whatever height the ribbon gives up or takes goes to the 3D
scene: the surface table under it keeps its own (bugs/0951).

It lives in a dock (bugs/0940): the slim title bar down its left edge undocks it (float button or
double-click) into a window of its own, which opens fully; dragged to the top or bottom edge it
docks again and returns to its folded / open state.
"""
from __future__ import annotations

#: tab -> groups -> (name, "L" large | "S" small, ribbon label). Small buttons stack three to a
#: column. Labels are short forms of the action's text; "\n" breaks a large button's label. A name
#: starting "menu:" is a dropdown button -- its commands are listed in `DROPDOWNS`.
RIBBON = (
    ("File", (
        ("Layout", (("open", "L", "Open\nLayout"), ("reload", "L", "Reload"), ("save", "S", "Save"),
                    ("save_as", "S", "Save As"), ("reset", "S", "Reset"))),
        ("Import / Export", (("menu:import", "L", "Import"), ("menu:export", "L", "Export"))),
        # Quit is small and last, on a tab that is not the one shown at start-up
        ("Application", (("menu:help", "L", "Help"), ("flag_bug", "S", "Flag Bug"), ("about", "S", "About"),
                         ("quit", "S", "Quit"))),
    )),
    ("Home", (
        ("Edit", (("undo", "S", "Undo"), ("redo", "S", "Redo"))),
        ("Rows", (("copy_rows", "S", "Copy"), ("paste_rows", "S", "Paste"))),
        ("View", (("reset_camera", "L", "Fit\nScene"), ("inspector", "L", "3D\nInspector"),
                  ("folded_assembly", "L", "Folded\nAssembly"), ("show_rays", "S", "Show Rays"),
                  ("redraw", "S", "Redraw"), ("refresh_plot", "S", "Refresh Plot"),
                  ("trace_now", "S", "Trace Now"), ("plot_2d", "S", "2D Plot"))),
        # a big clean 3D scene, and its parts one at a time (bugs/0961)
        ("Workspace", (("clean_scene", "L", "Clean\n3D Scene"), ("hide_panels", "S", "Hide Panels"),
                       ("toolbar_3d", "S", "3D Toolbar"))),
    )),
    ("Surfaces", (
        ("Surface", (("advanced_surface", "L", "Advanced\nSurface"), ("surface_shape", "L", "Shape\nBuilder"),
                     ("coating_material", "S", "Coating / Material"), ("error_map", "S", "Error Map"),
                     ("lens_drawing_properties", "S", "Drawing Properties"))),
        ("Special rows", (("beam_splitter", "S", "Beam Splitter"), ("diffuse_scatter", "S", "Diffuse / BRDF"),
                          ("grating_settings", "S", "Grating"), ("detector_settings", "S", "Detector"),
                          ("galvo_scan", "S", "Galvo Scan"))),
        ("Catalogs", (("glass_catalog", "L", "Glass\nCatalog"), ("stock_lens", "L", "Stock\nLens"))),
    )),
    ("Scene", (
        ("Placement", (("scene_target", "L", "Scene\nTarget"), ("path_local_pose", "S", "Path-Local Pose"),
                       ("element_settings", "S", "Element Settings"))),
        # they act on the Path view chosen on the surface table's toolbar (bugs/0944)
        ("Path view", (("add_path_component", "S", "Add Component"), ("add_path_stock_lens", "S", "Add Stock Lens"))),
        ("Sources", (("scene_sources", "L", "Source\nManager"), ("source_edit", "L", "Edit\nSource"))),
        ("CAD", (("face_roles", "L", "Optical\nFaces"), ("optical_solid_diagnostics", "L", "Inspect\nSolids"),
                 ("place_cad_solid", "S", "Place / Orient"), ("menu:cad_clear", "S", "Clear"),
                 ("missing_assets", "S", "Missing Files"))),
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
        ("More", (("menu:analysis_more", "L", "More"),)),
    )),
    # its own tab since the reports were routed (bugs/0943): on the Analysis tab they made the window
    # at least ~1500 px wide (1240 before)
    ("Tolerance", (
        ("Run", (("tolerance_monte_carlo", "L", "Monte\nCarlo"), ("tolerance_worst_sample", "S", "Worst Sample"),
                 ("tolerance_stackup", "S", "Stack-Up"))),
        ("Compensators", (("tolerance_compensator", "L", "Compensator\nSweep"),
                          ("tolerance_multi_compensator", "L", "Multi-\nCompensator"))),
        ("Presets", (("tolerance_preset", "S", "Save Preset"), ("apply_tolerance_preset", "S", "Apply Preset"))),
        ("Export", (("menu:tolerance_csv", "L", "Export\nCSV"),)),
    )),
)

#: dropdown button -> (what it holds, its actions in order; None is a separator). These are the
#: long, occasional lists -- a button each would only widen the ribbon.
DROPDOWNS = {
    "menu:import": ("Bring a design, a wavefront map or vendor CAD into the layout",
                    ("import_zemax", "import_zemax_wavefront", None, "import_cad_solid", "import_lens_step",
                     "import_camera_step", "import_led_step")),
    "menu:export": ("Write the 3D scene, a lens drawing or analysis data to a file",
                    ("export_3d_step", "export_3d_dxf", "export_lens_drawing", None, "export_wavefront_csv",
                     "export_zernike_csv", "export_path_psf_csv", "export_path_mtf_csv", "export_detector_map_csv",
                     "export_coherent_detector_csv", "export_branch_field_csv")),
    "menu:help": ("The formula sheet, the manual and the debug log",
                  ("formula_sheet", "manual_index", None, "copy_debug")),
    "menu:cad_clear": ("Remove the imported STEP bodies, or only their axis offsets",
                       ("clear_cad_axis_offsets", "clear_step_imports")),
    "menu:analysis_more": ("Atmospheric settings, benchmarks, report copies and clears",
                           ("atmosphere_settings", None, "benchmark_psf_mtf", None, "copy_phase2_report",
                            "copy_wavefront_fit", None,
                            "clear_zemax_wavefront", "clear_marks")),
    # each needs its report run first, so six buttons would mostly refuse
    "menu:tolerance_csv": ("Write a tolerance run as CSV -- run its report first",
                           ("export_tolerance_monte_carlo_csv", "export_tolerance_comparison_csv",
                            "export_tolerance_stackup_csv", "export_tolerance_compensator_csv",
                            "export_tolerance_multi_compensator_csv", "export_tolerance_overlay_csv")),
}
#: the tab shown at start-up: the everyday one, not File
START_TAB = "Home"

LARGE_ICON = 26
SMALL_ICON = 16
PALETTE_SHORTCUT = "Ctrl+Shift+P"
#: below this many logical pixels of WINDOW height the ribbon is folded to its tab row: an open
#: ribbon is ~110 px, which a 1000-px window cannot give up without squeezing the 3D view. It was the
#: SCREEN's height (bugs/0963): a 950-px window on a 1440-px screen opened with the ribbon open and
#: a 339-px 3D view
FOLD_BELOW_WINDOW_HEIGHT = 1100


def ribbon_entries() -> list:
    """Every (tab, group, name, size, label) on the ribbon, in order -- a button's action name, or a
    dropdown's "menu:..." key."""
    return [(tab, group, name, size, label)
            for tab, groups in RIBBON for group, entries in groups for name, size, label in entries]


def ribbon_actions() -> list:
    """Every action the ribbon reaches, in order: its buttons, and each dropdown's commands."""
    names = []
    for _tab, _group, name, _size, _label in ribbon_entries():
        if name in DROPDOWNS:
            names.extend(member for member in DROPDOWNS[name][1] if member is not None)
        else:
            names.append(name)
    return names


def plain_text(text: str) -> str:
    """An action's menu text without its mnemonic and ellipsis: "&Open Layout..." -> "Open Layout"."""
    return str(text).replace("&&", "\0").replace("&", "").replace("\0", "&").rstrip(".").rstrip("…").strip()


def action_tip(action) -> str:
    """A button's tooltip: the command's name and shortcut in bold, then what it does."""
    shortcut = action.shortcut().toString()
    tip = plain_text(action.text()) + (f"  ({shortcut})" if shortcut else "")
    return f"<b>{tip}</b><br>{action.toolTip()}" if action.toolTip() else tip


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
        #: "menu:..." key -> its dropdown button (on the docked pages)
        self.dropdowns: dict[str, object] = {}
        #: tab index -> its pop-up page, built the first time it is shown folded
        self.popups: dict[int, object] = {}
        self._building_popup = False
        # an action carries its icon wherever it shows: its button, or a dropdown's list
        for name, action in self.actions.items():
            action.setIcon(icon(name))
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("Ribbon")
        for tab, groups in RIBBON:
            self.tabs.addTab(self._page(tab, groups), tab)
        self.tabs.setCurrentIndex([tab for tab, _groups in RIBBON].index(START_TAB))
        self.tabs.setCornerWidget(self._corner(), Qt.Corner.TopRightCorner)
        # double-click a tab to fold the ribbon to its tab row, and again to open it (as Office);
        # folded, a click on a tab shows its page as a pop-up
        self.tabs.tabBarDoubleClicked.connect(lambda _index: self.fold_by_hand(not self.collapsed))
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
        #: the ribbon follows the window's height until the user folds or opens it by hand
        self.follows_window = True
        self._window_short = self._short_window()
        if self._window_short:
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

        if name in DROPDOWNS:
            return self._dropdown(name, size, label)
        action = self.actions[name]
        button = QToolButton()
        button.setAutoRaise(True)
        button.setIcon(action.icon())
        button.setText(label)
        large = size == "L"
        button.setIconSize(QSize(LARGE_ICON, LARGE_ICON) if large else QSize(SMALL_ICON, SMALL_ICON))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon if large
                                  else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setToolTip(action_tip(action))
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

    def _dropdown(self, name: str, size: str, label: str):
        """A button that drops a list of commands -- the shell's own actions, so an entry is the
        same call as a button or a shortcut (bugs/0949: there is no menu bar to hold them)."""
        from PySide6.QtCore import QSize, Qt
        from PySide6.QtWidgets import QMenu, QToolButton

        from KrakenOS.UI.qt.icons import icon

        about, members = DROPDOWNS[name]
        button = QToolButton()
        button.setAutoRaise(True)
        button.setIcon(icon(name.replace(":", "_")))
        button.setText(label)
        large = size == "L"
        button.setIconSize(QSize(LARGE_ICON, LARGE_ICON) if large else QSize(SMALL_ICON, SMALL_ICON))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon if large
                                  else Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        menu = QMenu(button)
        menu.setToolTipsVisible(True)
        for member in members:
            if member is None:
                menu.addSeparator()
            else:
                menu.addAction(self.actions[member])
        # folded, the page is a pop-up: a command chosen from the list closes it, as a button does
        menu.triggered.connect(lambda _action: self._close_popups())
        button.setMenu(menu)
        button.setToolTip(f"<b>{label.replace(chr(10), ' ')}</b><br>{about}")
        if not self._building_popup:
            self.dropdowns[name] = button
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

    # ---- the tab row's corner: the command palette and the fold arrow ---------------------------
    def _corner(self):
        """The search box, then the small arrow that folds the ribbon to its tab row and opens it
        again (user request, bugs/0952) -- where other ribbons keep theirs."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

        corner = QWidget()
        row = self.corner_row = QHBoxLayout(corner)
        row.setContentsMargins(0, 0, 2, 0)
        row.setSpacing(4)
        row.addWidget(self._palette())
        # Flag Bug is here as well as on the File tab: one click from every tab, and with the
        # ribbon folded it opens no page over the window it is about to picture (bugs/0959)
        flag = self.flag_button = QToolButton()
        flag.setAutoRaise(True)
        flag.setIcon(self.actions["flag_bug"].icon())
        flag.setToolTip(action_tip(self.actions["flag_bug"]))
        flag.setFixedSize(22, 20)
        flag.clicked.connect(lambda _checked=False: self.actions["flag_bug"].trigger())
        row.addWidget(flag)
        # and Clean 3D Scene, where the ribbon's own fold is: one click from the scene alone and
        # back, on every tab (bugs/0961)
        clean_action = self.actions["clean_scene"]
        clean = self.clean_button = QToolButton()
        clean.setAutoRaise(True)
        clean.setCheckable(True)
        clean.setChecked(clean_action.isChecked())
        clean.setIcon(clean_action.icon())
        clean.setToolTip(action_tip(clean_action))
        clean.setFixedSize(22, 20)
        clean.clicked.connect(lambda _checked=False: clean_action.trigger())
        clean_action.toggled.connect(clean.setChecked)
        row.addWidget(clean)
        arrow = self.fold_button = QToolButton()
        arrow.setAutoRaise(True)
        arrow.setArrowType(Qt.ArrowType.UpArrow)
        arrow.setFixedSize(20, 20)
        arrow.clicked.connect(lambda _checked=False: self.fold_by_hand(not self.collapsed))
        row.addWidget(arrow)
        self._show_fold_state()
        return corner

    def _show_fold_state(self) -> None:
        from PySide6.QtCore import Qt

        folded = bool(getattr(self, "collapsed", False))
        self.fold_button.setArrowType(Qt.ArrowType.DownArrow if folded else Qt.ArrowType.UpArrow)
        self.fold_button.setToolTip("Show the ribbon's buttons again" if folded
                                    else "Fold the ribbon to its tab row (more room for the 3D scene)")

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
    def _short_window(self) -> bool:
        return self.main_window.height() < FOLD_BELOW_WINDOW_HEIGHT

    def follow_window_height(self) -> None:
        """The window was resized: fold the ribbon when the window gets short, open it when it gets
        tall -- on CROSSING the line only, so a fold made in between is not undone on every resize.
        Not once the user has folded or opened it by hand, not while it floats, and not while
        Clean 3D Scene is on (which puts the ribbon back itself) (bugs/0963)."""
        short = self._short_window()
        if short == getattr(self, "_window_short", short):
            return
        self._window_short = short
        if not self.follows_window or self.dock.isFloating():
            return
        if getattr(self.main_window, "_clean_scene_saved", None) is not None:
            return
        if self.collapsed != short:
            self.set_collapsed(short)

    def fold_by_hand(self, collapsed: bool) -> None:
        """The arrow, or a double-click on a tab: the user's choice, kept from now on."""
        self.follows_window = False
        self.set_collapsed(collapsed)

    def set_collapsed(self, collapsed: bool) -> None:
        """Fold the ribbon to its tab row (more room for the 3D view), or open it again."""
        from PySide6.QtWidgets import QStackedWidget

        kept = self._neighbour_heights()
        self.collapsed = bool(collapsed)
        self._show_fold_state()
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
        self._restore_neighbour_heights(kept)

    def _neighbour_heights(self) -> dict:
        """The heights of the docks that share the top area with the ribbon (the surface table),
        read BEFORE the ribbon changes height."""
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget

        window = self.main_window
        dock = getattr(self, "dock", None)
        if dock is None or not window.isVisible():
            return {}
        return {other: other.height() for other in window.findChildren(QDockWidget)
                if other is not dock and other.isVisible() and not other.isFloating()
                and window.dockWidgetArea(other) == Qt.DockWidgetArea.TopDockWidgetArea}

    def _restore_neighbour_heights(self, heights: dict) -> None:
        """Put those heights back once the layout has run. Qt keeps the top area's total height,
        so a ribbon that folds would hand its height to the table beside it; the 3D scene is what
        should gain it, and give it back (bugs/0951 -- measured: the scene lost 40 px to the table
        each time the ribbon was undocked and docked again)."""
        if not heights:
            return
        from PySide6.QtCore import QTimer, Qt

        QTimer.singleShot(0, lambda: self.main_window.resizeDocks(
            list(heights), list(heights.values()), Qt.Orientation.Vertical))

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
        if bool(floating) and not self.dock.isFloating():
            self._heights_before_floating = self._neighbour_heights()
        self.dock.setFloating(bool(floating))

    def _on_floating_changed(self, floating: bool) -> None:
        # a floating ribbon costs the 3D view nothing, so it opens fully; docked again, it goes
        # back to how it was (folded on a short screen)
        if floating:
            if not getattr(self, "_heights_before_floating", None):
                self._heights_before_floating = self._neighbour_heights()
            self._restore_neighbour_heights(self._heights_before_floating)
            self._collapsed_when_docked = self.collapsed
            self.dock.setMinimumHeight(0)
            self.dock.setMaximumHeight(16777215)
            if self.collapsed:
                self.set_collapsed(False)
            self.dock.adjustSize()
        else:
            self.set_collapsed(self._collapsed_when_docked)
            self._restore_neighbour_heights(getattr(self, "_heights_before_floating", None) or {})
            self._heights_before_floating = None

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
