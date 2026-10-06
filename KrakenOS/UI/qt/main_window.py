"""The Qt shell's main window (docs/design_qt_migration.md phase 2).

It owns no optics. The model is a `KrakenLayoutEditor` reached through the 0851 seam, with a
`QtUiHost` answering its dialogs and scheduling, so `File -> Open Layout` calls the SAME
`editor.open_layout()` the Tk menu calls and the file chooser that appears is Qt's.

Transitional, until the inspector becomes a Qt widget in phase 5: that editor still builds a Tk
widget tree behind the scenes (bugs/0853 freed it from BEING a root, not from having one). The
shell builds it with `headless=True` and withdraws the root, so nothing Tk is ever shown.
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.qt.actions import TABLE_SHORTCUTS, ActionManager
from KrakenOS.UI.qt.docks import DockManager
from KrakenOS.UI.qt.analysis_toolbar import AnalysisToolbar
from KrakenOS.UI.qt.optimization_panel import OptimizationPanel
from KrakenOS.UI.qt.results_panel import ResultsPanel
from KrakenOS.UI.qt.system_panel import SystemPanel
from KrakenOS.UI.system_controls import SOURCE_CONTROLS, TRACE_CONTROLS
from KrakenOS.UI.qt.rows_table import make_cell_delegate, make_rows_model
from KrakenOS.UI.uihost import host_of


def _main_window_class():
    from PySide6.QtWidgets import QMainWindow

    return QMainWindow


class KrakenQtMainWindow(_main_window_class()):
    """A ribbon, a surface table, a 3D viewport and a status line over a live editor."""

    def __init__(self, editor, ui=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QAbstractItemView, QApplication, QStackedWidget, QTableView, QVBoxLayout,
                                       QWidget)

        super().__init__()
        self.editor = editor
        self.ui = ui if ui is not None else host_of(editor)
        #: the bare preview of the scene: the fallback when the inspector cannot be built
        self.viewport = None
        #: the real 3D inspector -- THE 3D scene of the window (bugs/0906; central since 0951)
        self.inspector_view = None

        self.setWindowTitle("KrakenOS -- Qt shell")
        self.resize(1500, 950)

        self.action_manager = ActionManager(self)
        self.action_manager.create_all_actions()
        # no menu bar (bugs/0949): the ribbon is the one command surface. A shortcut only fires for
        # an action some visible widget holds -- the menu bar used to be that widget. The table's
        # own shortcuts stay off the window: held here, Ctrl+C would copy rows from every view
        self.addActions([action for name, action in self.action_manager.actions.items()
                         if name not in TABLE_SHORTCUTS])

        # The viewport is NOT created here: it must be built once this window is shown, because
        # the VTK widget hands VTK its window id in its constructor and Qt recreates a native
        # window on reparenting. This container is its stable parent -- `build_viewport()` adds
        # the widget to the container's own layout, so nothing is ever reparented.
        self.plot2d = None
        self.viewport_host = QWidget()
        self.viewport_layout = QVBoxLayout(self.viewport_host)
        self.viewport_layout.setContentsMargins(0, 0, 0, 0)
        # The centre of the window is ONE 3D scene (bugs/0951): the real inspector, with its Nav
        # Cube, gizmos and readouts. It used to be a dock in the top area over a bare preview in
        # the centre -- two 3D views, and the side panels crushed into the band left under the
        # inspector. The preview keeps its page: it is what shows when the inspector cannot be
        # built. Both pages are stable parents, made here, for the same reason as above.
        self.inspector_host = QWidget()
        self.inspector_layout = QVBoxLayout(self.inspector_host)
        self.inspector_layout.setContentsMargins(0, 0, 0, 0)
        self.scene_stack = QStackedWidget()
        self.scene_stack.addWidget(self.viewport_host)
        self.scene_stack.addWidget(self.inspector_host)
        self.setCentralWidget(self.scene_stack)

        self.rows_model = make_rows_model(editor)
        self.rows_view = QTableView()
        self.rows_view.setModel(self.rows_model)
        self.rows_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        # editable since bugs/0903: every edit goes through the model's own commit_cell
        self.rows_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.rows_view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                       | QAbstractItemView.EditTrigger.EditKeyPressed
                                       | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.rows_view.setItemDelegate(make_cell_delegate(self.rows_view))
        self.rows_view.horizontalHeader().setStretchLastSection(True)
        self.rows_view.verticalHeader().setVisible(False)  # the "#" column already numbers them
        # the model's table verbs ask the SHELL which rows are selected, and tell it what to
        # select afterwards; a rebuilt table is news here too (bugs/0903)
        editor.selected_row_indices = self.selected_row_indices
        editor.select_rows = self.select_rows
        editor.show_rows = self.show_rows
        self.table_widget = self._build_table_widget()
        for name in TABLE_SHORTCUTS:
            action = self.action_manager[name]
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            self.rows_view.addAction(action)

        self.dock_manager = DockManager(self)
        # one click puts every panel away, the next brings the same ones back (bugs/0961)
        self.dock_manager.rails.add_hide_all_button(self.action_manager["hide_panels"])
        self.dock_manager.rails.listeners.append(self._follow_panels)
        #: what Clean 3D Scene put away, to put back; None while it is off
        self._clean_scene_saved = None
        self.action_manager["toolbar_3d"].setEnabled(False)     # until the 3D scene has its toolbar
        # the table is many columns wide: across the top of the window it shows them all and its
        # rows run DOWN, where the left column made it scroll sideways (user request, bugs/0940)
        self.dock_manager.create_dock(self.table_widget, "SurfaceTableDock", "Surface Table",
                                      Qt.DockWidgetArea.TopDockWidgetArea)
        # the two panels the model used to write into Tk widgets directly (bugs/0898)
        self.results_panel = ResultsPanel(editor)
        self.dock_manager.create_dock(self.results_panel.log, "DebugDock", "Debug",
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_manager.create_dock(self.results_panel.progress, "ProgressDock", "Progress",
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        # Results sits in the bottom row beside Debug and Progress: stacked over the right column's
        # input tabs it held the middle band ~90 px tall, and that height came out of the 3D view
        # once the surface table moved to the top (bugs/0940)
        self.dock_manager.create_dock(self.results_panel.table, "ResultsDock", "Results",
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_manager.setup_default_layout()
        # the analysis picker and Update: the Qt shell could open every dialog and show every
        # result, but could not set an analysis up (bugs/0899)
        self.analysis_toolbar = AnalysisToolbar(self)
        # every command as tabbed icon groups + a command palette; it takes over the analysis
        # toolbar's row, so the 3D view loses no height to it (bugs/0935)
        from KrakenOS.UI.qt.ribbon import Ribbon

        self.ribbon = Ribbon(self)
        # the top edge's panel tabs ride in the ribbon's tab row -- not a 36-px row of their own --
        # while the ribbon is docked at the top; undocked or at the bottom, they go back (bugs/0962)
        self.ribbon.dock.topLevelChanged.connect(lambda *_a: self._place_top_rail())
        self.ribbon.dock.dockLocationChanged.connect(lambda *_a: self._place_top_rail())
        self._place_top_rail()
        # the top area, top to bottom: ribbon, surface table, then the 3D inspector (built later)
        self.splitDockWidget(self.ribbon.dock, self.dock_manager["SurfaceTableDock"], Qt.Orientation.Vertical)
        # the inputs that define the system: the Qt shell could analyse a loaded layout but not
        # change what was traced (bugs/0900)
        self.system_panel = SystemPanel(editor)
        self.dock_manager.create_dock(self.system_panel.widget, "SystemDock", "System",
                                      Qt.DockWidgetArea.RightDockWidgetArea, scroll=True)
        # and what launches the light (bugs/0901) -- the same class over the other group
        self.source_panel = SystemPanel(editor, SOURCE_CONTROLS)
        self.dock_manager.create_dock(self.source_panel.widget, "SourceDock", "Source",
                                      Qt.DockWidgetArea.RightDockWidgetArea, scroll=True)
        # and how the trace runs and what the plots show (bugs/0902)
        self.trace_panel = SystemPanel(editor, TRACE_CONTROLS)
        self.dock_manager.create_dock(self.trace_panel.widget, "TraceDock", "Trace",
                                      Qt.DockWidgetArea.RightDockWidgetArea, scroll=True)
        # the model says when relevance or a live list may have changed; every form re-reads
        editor.show_control_state = self.refresh_control_panels
        # a table-cell solve shows its result for review before it applies it (bugs/0955)
        editor.show_solve_review = self.show_solve_review
        #: the review dialog last shown, for a guard to read and answer
        self.last_solve_review_dialog = None
        # Atmospheric Settings: the same catalogue mechanism, in a window of its own (bugs/0954)
        editor.show_atmosphere_settings = self.show_atmosphere_settings
        #: the one Atmospheric Settings window, made the first time it is asked for
        self.atmosphere_dialog = None
        # the layout's missing CAD files -- what the search by name could not find -- are asked
        # about in a Qt window (bugs/0965): the Tk one was a window on the hidden Tk root here
        editor.show_missing_assets = self.show_missing_assets
        #: the window `show_missing_assets` last opened, for a guard to drive
        self.last_missing_assets_dialog = None
        # the Inspection Cell VIEW is a Qt window here (bugs/0967): the Tk one was on screen and
        # dead -- nothing pumps Tk under this shell
        editor.show_inspection_cell = self.show_inspection_cell
        self.last_inspection_cell_dialog = None
        # the CAD/STL face-roles editor opens here, over the model's session (bugs/0934)
        editor.show_face_roles_dialog = self.show_face_roles_dialog
        # a report a model command opens -- the table menu's Diagnostics, the inspector's verbs --
        # shows in the Qt report dialog (bugs/0948)
        editor.show_report = self.show_model_report
        #: the dialog `show_model_report` last opened, for a guard to read
        self.last_model_report_dialog = None
        # the lens-drawing surface properties, modal: a PDF export waits on the answer (bugs/0945)
        editor.show_lens_drawing_properties = self.show_lens_drawing_properties
        #: the dialog `show_lens_drawing_properties` last opened, for a guard to drive
        self.last_lens_drawing_dialog = None
        # the `s` bug flag asks for its description in a Qt window (bugs/0950): the inspector's Tk
        # popup would never be seen here, so the flag kept its screenshot but never its words
        editor.show_flag_description = self.show_flag_description
        #: the dialog `show_flag_description` last opened, for a guard to drive
        self.last_flag_description_dialog = None
        # and every flag carries this window: its picture, its dialogs' and its state (bugs/0959)
        editor.capture_flag_shell = self.capture_flag_shell
        # Flag Bug must work from a dialog too -- a dialog is often what is wrong -- and a window's
        # shortcut does not reach one, least of all a modal one: each window that takes the
        # keyboard is given the action
        QApplication.instance().focusChanged.connect(self._offer_flag_bug)
        # a form a model command builds itself (the Path-view placements) opens here (bugs/0944)
        editor.show_row_form = self.show_model_row_form
        #: the dialog `show_model_row_form` last opened, for a guard to read and drive
        self.last_model_form_dialog = None
        # undo / redo enable as the model's history changes (bugs/0942)
        editor.show_undo_state = self.show_undo_state
        self.show_undo_state(bool(getattr(editor, "_undo_stack", None)), bool(getattr(editor, "_redo_stack", None)))
        # and "Measure MTF from Image" (bugs/0938)
        editor.show_mtf_from_image_dialog = self.show_mtf_from_image_dialog
        self.last_mtf_from_image_dialog = None
        self.last_face_roles_dialog = None
        # optimisation: operands, their settings, workers and Start/Stop (bugs/0904)
        self.optimization_panel = OptimizationPanel(editor)
        self.dock_manager.create_dock(self.optimization_panel.widget, "OptimizationDock",
                                      "Optimization", Qt.DockWidgetArea.RightDockWidgetArea,
                                      scroll=True)
        # the four input forms share one tabbed stack: stacked, their minimum heights summed to
        # ~1600 px and forced the window past the screen, leaving the 3D inspector 0 px (bugs/0906)
        self.dock_manager.tabify(("SystemDock", "SourceDock", "TraceDock", "OptimizationDock"))

        self._open_dialogs: list = []  # a modeless dialog must outlive the call that opened it
        self._status_trace = None
        self._bind_status_line()
        self.statusBar().showMessage(self._model_status() or "KrakenOS Qt shell ready.")

    def refresh_control_panels(self) -> None:
        """The model's `show_control_state` seam: re-read relevance and live lists (0902)."""
        for panel in (self.system_panel, self.source_panel, self.trace_panel):
            panel.refresh_state()
        if self.atmosphere_dialog is not None:
            self.atmosphere_dialog.panel.refresh_state()
        self._refresh_path_view_choices()

    def show_solve_review(self, review) -> bool:
        """The model's `show_solve_review` seam (bugs/0955): a solve's result in a modal Qt dialog;
        True when the user chose Apply."""
        from PySide6.QtWidgets import QDialog

        from KrakenOS.UI.qt.dialogs.solve_review_dialog import SolveReviewDialog

        dialog = SolveReviewDialog(review, parent=self)
        self.last_solve_review_dialog = dialog
        return dialog.exec() == QDialog.DialogCode.Accepted

    def show_atmosphere_settings(self):
        """The model's `show_atmosphere_settings` seam (bugs/0954): one window, not modal -- asked
        for again, it comes back to the front, as the Tk one does."""
        from KrakenOS.UI.qt.dialogs.atmosphere_dialog import AtmosphereSettingsDialog

        if self.atmosphere_dialog is None:
            self.atmosphere_dialog = AtmosphereSettingsDialog(self.editor, parent=self)
        self.atmosphere_dialog.show()
        self.atmosphere_dialog.raise_()
        self.atmosphere_dialog.activateWindow()
        return self.atmosphere_dialog

    def show_missing_assets(self, session):
        """The model's `show_missing_assets` seam (bugs/0965): the missing-CAD-assets window, not
        modal -- the layout has loaded with placeholders and the scene stays usable."""
        from KrakenOS.UI.qt.dialogs.missing_assets_dialog import MissingAssetsDialog

        dialog = MissingAssetsDialog(session, host=host_of(self), parent=self)
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        self.last_missing_assets_dialog = dialog
        dialog.show()
        return dialog

    def show_inspection_cell(self, session):
        """The model's `show_inspection_cell` seam (bugs/0967): the cell's view as a Qt window, not
        modal. A station opened from it loads through THIS window's loader, so the table and the
        scene follow. Returns the session, as the model's opener does."""
        from KrakenOS.UI.qt.dialogs.inspection_cell_dialog import InspectionCellDialog

        session.open_layout = self.load_layout_path
        session.raise_editor = self._come_forward
        dialog = InspectionCellDialog(session, host=host_of(self), parent=self)
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        self.last_inspection_cell_dialog = dialog
        dialog.show()
        dialog.build_view()           # VTK takes the shown window's native id
        return session

    def _come_forward(self) -> None:
        self.raise_()
        self.activateWindow()

    def missing_assets_action(self) -> None:
        """Ask about the layout's missing CAD files again -- or say that none are missing."""
        self.editor._prompt_for_missing_cad_assets(announce_none=True)

    def show_lens_drawing_properties(self, session) -> bool:
        """The model's `show_lens_drawing_properties` seam (bugs/0945): the session in a modal Qt
        dialog; returns once the session is closed, with whether the caller may go on."""
        from KrakenOS.UI.qt.dialogs.lens_drawing_dialog import LensDrawingPropertiesDialog

        dialog = LensDrawingPropertiesDialog(session, parent=self)
        self.last_lens_drawing_dialog = dialog
        dialog.exec()
        return bool(session.result_ok)

    def show_flag_description(self, session):
        """The model's `show_flag_description` seam (bugs/0950): the flag's description prompt as
        a Qt window that is NOT modal -- a carry or a drag stays live while it is open.

        Flagged from a modal dialog, the prompt belongs to that dialog: a window of this one would
        be shut out by it and could not be typed in (bugs/0959)."""
        from PySide6.QtWidgets import QApplication, QDialog

        from KrakenOS.UI.qt.dialogs.flag_description_dialog import FlagDescriptionDialog

        modal = QApplication.activeModalWidget()
        dialog = FlagDescriptionDialog(session, parent=modal if modal is not None else self)
        if isinstance(modal, QDialog):
            # the dialog it belongs to is closing and takes the prompt with it: keep what was typed
            modal.finished.connect(lambda _result, d=dialog: d.finish("save" if d.text.toPlainText().strip() else "keep"))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        self.last_flag_description_dialog = dialog
        dialog.show()
        return dialog

    def capture_flag_shell(self, bundle_dir, *, as_screenshot: bool = False) -> dict:
        """The model's `capture_flag_shell` seam (bugs/0959): this window's pictures into a flag
        bundle, and its state for the bundle's state.json."""
        from KrakenOS.UI.qt import flag_capture

        self.ribbon._close_popups()      # a folded ribbon's page is a pop-up over the window
        return flag_capture.capture(self, bundle_dir, as_screenshot=as_screenshot)

    def flag_bug_action(self):
        """Flag a bug about the window (bugs/0959): the ribbon, the tables, a panel, a dialog.

        The `s` key flags what is under the pointer in the 3D scene and shows the scene. This shows
        the window in front -- this one, or the dialog over it -- and works wherever the keyboard
        is. Both write one kind of bundle, and both carry the scene and the window."""
        inspector = self._scene_inspector()
        if inspector is not None:
            return inspector.flag_bug(subject="window")
        from KrakenOS.UI.services.shell_flag import flag_shell_window

        return flag_shell_window(self.editor, self.capture_flag_shell, set_status=self.statusBar().showMessage,
                                 show_description=self.show_flag_description)

    def _offer_flag_bug(self, _old, now) -> None:
        """Give the window that now has the keyboard the Flag Bug action, so its shortcut works
        there. Not a flag's own prompt: Ctrl+Shift+B while describing one bug is not another. And
        not a pop-up: a menu SHOWS its actions, so it would grow a Flag Bug entry."""
        from PySide6.QtCore import Qt

        top = now.window() if now is not None else None
        if top is None or top is self or getattr(top, "is_flag_prompt", False):
            return
        if top.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip):
            return
        action = self.action_manager["flag_bug"]
        if action not in top.actions():
            top.addAction(action)

    def show_model_row_form(self, form, *, on_close=None, modal=False, geometry=None, wait=False):
        """The model's `show_row_form` seam (bugs/0944): a form a model command builds itself, in a
        Qt dialog instead of a Tk window. Since bugs/0947 every row form the model opens comes
        here -- the table's and the inspector's verbs included.

        `geometry` is the Tk window's "WIDTHxHEIGHT"; `wait` runs the dialog to its end (a caller
        that reads the result afterwards), where a plain modal one only blocks the window."""
        from KrakenOS.UI.qt.dialogs.row_form_dialog import RowFormDialog

        dialog = RowFormDialog(form, parent=self, host=host_of(self))
        dialog.setModal(bool(modal) or bool(wait))
        size = str(geometry or "").split("+")[0].lower().split("x")
        if len(size) == 2 and all(part.isdigit() for part in size):
            dialog.resize(int(size[0]), int(size[1]))
        if on_close is not None:
            dialog.finished.connect(lambda _result: on_close())
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        self.last_model_form_dialog = dialog
        if wait:
            dialog.exec()
        else:
            dialog.show()
        return dialog

    # ---- the model's status line drives ours ---------------------------------------------------
    def _model_status(self) -> str:
        variable = getattr(self.editor, "status_var", None)
        try:
            return "" if variable is None else str(variable.get())
        except Exception:
            return ""

    def _bind_status_line(self) -> None:
        """Model -> view, through the variable the model already writes.

        `status_var` is written over a thousand times by model code. Whether it is a real
        `tk.StringVar` (the Tk panels made it) or an `ObservableValue` (a host made it), it has
        the same `trace_add`, so this one binding works on both -- which is the whole point of
        step 1c.
        """
        variable = getattr(self.editor, "status_var", None)
        if variable is None or not hasattr(variable, "trace_add"):
            return
        self._status_trace = variable.trace_add("write", self._on_model_status_written)

    def _on_model_status_written(self, *_args) -> None:
        self.statusBar().showMessage(self._model_status())

    # ---- the viewport --------------------------------------------------------------------------
    def build_viewport(self):
        """Create the bare PREVIEW of the scene -- what shows when the inspector cannot be built
        (the window's 3D scene is the inspector: `build_scene`). Call this AFTER `show()` -- see
        the container above."""
        from KrakenOS.UI.qt.viewport import SceneViewport

        if self.viewport is None:
            self.viewport = SceneViewport(self.viewport_host)
            self.viewport_layout.addWidget(self.viewport.widget)
        return self.viewport

    def build_scene(self):
        """The window's 3D scene: the real inspector, or the bare preview when it cannot be built --
        and the 2D plot beside it (bugs/0964). Call this AFTER `show()`."""
        view = self.build_inspector_view()
        if not view.inspector.available:
            self.build_viewport()
        self.build_plot2d()
        return view

    def build_inspector_view(self):
        """Host the real 3D inspector as the window's central 3D scene (bugs/0951). Call this
        AFTER `show()`, like `build_viewport`.

        Its page of the central stack is made current BEFORE the VTK widget is built, so the widget
        is created under a parent that is on screen.
        """
        if self.inspector_view is not None:
            return self.inspector_view
        from PySide6.QtCore import Qt

        from KrakenOS.UI.qt.inspector_view import InspectorView

        container, layout = self.inspector_host, self.inspector_layout
        self.scene_stack.setCurrentWidget(container)
        self.inspector_view = InspectorView(self.editor, container,
                                            status=self.statusBar().showMessage)
        inspector = self.inspector_view.inspector
        # the View / Scene / Carry rows above the viewport, from the same catalogue as Tk (5f)
        if inspector.available:
            from KrakenOS.UI.qt.inspector_toolbar import build_toolbar

            self.inspector_view.toolbar = build_toolbar(inspector, container)
            layout.addWidget(self.inspector_view.toolbar)
            # its arrow hides it; the 3D Toolbar switch (Home > Workspace) brings it back (bugs/0961)
            toolbar_switch = self.action_manager["toolbar_3d"]
            toolbar_switch.setEnabled(True)
            self.inspector_view.toolbar.setVisible(toolbar_switch.isChecked())
            self.inspector_view.toolbar.hide_button.clicked.connect(lambda _checked=False: toolbar_switch.trigger())
            # the Live Controls the docks do not already carry, tabbed with them (5f part 2)
            from KrakenOS.UI.qt.live_controls_dock import LiveControlsForm

            self.live_controls = LiveControlsForm(inspector,
                                                  open_system_selection=self.system_selection_action)
            self.dock_manager.create_dock(self.live_controls.widget, "LiveControlsDock", "3D Live",
                                          Qt.DockWidgetArea.RightDockWidgetArea, scroll=True)
            self.dock_manager.tabify(("SystemDock", "SourceDock", "TraceDock", "OptimizationDock",
                                      "LiveControlsDock"))
            # the Scene Components browser, from the Tk browser's own nodes / selection / menus (5f 3b)
            from KrakenOS.UI.qt.scene_components_dock import SceneComponentsTree

            self.scene_components = SceneComponentsTree(inspector)
            self.dock_manager.create_dock(self.scene_components.container, "SceneComponentsDock",
                                          "Scene Components", Qt.DockWidgetArea.LeftDockWidgetArea)
            # the ribbon's Show Rays and the inspector's own box are one switch
            inspector.show_rays_var.trace_add("write", lambda *_a: self._follow_inspector_rays())
        layout.addWidget(self.inspector_view.widget)
        # a VTK widget has no size hint, so it would open 0 pixels tall (measured) -- and a
        # 0-pixel viewport picks nothing. Its WIDTH has a floor too: the scene's readouts do not
        # shrink (the system box is ~500 px, the banner wraps no narrower than 48 characters,
        # the Nav Cube takes its corner), so in a small window the panels beside it must give
        # way first -- measured: at 462 px both texts ran off the edge (bugs/0951).
        self.inspector_view.widget.setMinimumSize(self.SCENE_MIN_WIDTH, 240)
        self.fit_side_docks()
        if inspector.available:
            inspector.refresh_from_editor()
        else:
            self.scene_stack.setCurrentWidget(self.viewport_host)
            self.statusBar().showMessage(f"3D inspector unavailable: {inspector.unavailable_reason}")
        return self.inspector_view

    #: the surface table's starting height at the top: a header and about five rows; drag it
    #: taller (bugs/0940)
    TABLE_DOCK_HEIGHT = 170
    #: the narrowest the 3D scene may get: its readouts and the Nav Cube side by side
    SCENE_MIN_WIDTH = 700
    #: starting sizes of the panels around the 3D scene (bugs/0951); the scene takes the rest
    BOTTOM_DOCK_HEIGHT = 150
    LEFT_DOCK_WIDTH = 300
    RIGHT_DOCK_WIDTH = 400

    def fit_side_docks(self) -> None:
        """Give the panels around the 3D scene their starting sizes, so the scene gets the rest --
        once the layout has run, since a `resizeDocks` before it is ignored (measured: the dock
        stayed at its minimum)."""
        from PySide6.QtCore import QTimer, Qt

        def area_docks(area):
            return [dock for dock in self.dock_manager.docks.values()
                    if self.dockWidgetArea(dock) == area and not dock.isFloating() and dock.isVisible()]

        def fit() -> None:
            for area, size, orientation in (
                    (Qt.DockWidgetArea.TopDockWidgetArea, self.TABLE_DOCK_HEIGHT, Qt.Orientation.Vertical),
                    (Qt.DockWidgetArea.BottomDockWidgetArea, self.BOTTOM_DOCK_HEIGHT, Qt.Orientation.Vertical),
                    (Qt.DockWidgetArea.LeftDockWidgetArea, self.LEFT_DOCK_WIDTH, Qt.Orientation.Horizontal),
                    (Qt.DockWidgetArea.RightDockWidgetArea, self.RIGHT_DOCK_WIDTH, Qt.Orientation.Horizontal)):
                docks = area_docks(area)
                if docks:
                    self.resizeDocks(docks, [size] * len(docks), orientation)

        QTimer.singleShot(0, fit)

    def _scene_inspector(self):
        """The hosted inspector when it is the 3D scene on show, else None."""
        view = self.inspector_view
        inspector = getattr(view, "inspector", None)
        return inspector if inspector is not None and getattr(inspector, "available", False) else None

    def _follow_inspector_rays(self) -> None:
        inspector = self._scene_inspector()
        if inspector is None:
            return
        shown = bool(inspector.show_rays_var.get())
        action = self.action_manager["show_rays"]
        if action.isChecked() != shown:
            action.setChecked(shown)       # `toggled`, not `triggered`: the handler does not run again

    def inspector_action(self) -> None:
        view = self.build_inspector_view()
        if view.inspector.available:
            self.scene_stack.setCurrentWidget(self.inspector_host)
        view.show()

    def build_plot2d(self):
        """Create the 2D layout plot and hand the editor its figure (bugs/0893).

        The model draws into `editor.ax`; this only supplies the canvas and connects the three
        matplotlib events both shells use. It lives in a dock so the 3D view keeps the centre:
        tabbed behind the System panel on the right, its own tab on the right edge.

        Until bugs/0964 only its guard built it: the running shell had NO 2D plot, and every
        analysis plot (MTF, spot, ...) was drawn into the hidden Tk window. Its toolbar is the Tk
        plot toolbar's controls (`plot2d_toolbar.PLOT_2D`) and the shell's Trace Now, Update and
        Ray Inspector.
        """
        from KrakenOS.UI.qt.plot2d import LayoutPlot2D

        if self.plot2d is None:
            from types import SimpleNamespace

            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QVBoxLayout, QWidget

            from KrakenOS.UI.plot2d_toolbar import PLOT_2D
            from KrakenOS.UI.qt.inspector_toolbar import row_toolbar

            self.plot2d = LayoutPlot2D(self.editor)
            panel = QWidget()
            column = QVBoxLayout(panel)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(0)
            self.plot2d.controls = {}
            bar, _hints = row_toolbar(SimpleNamespace(editor=self.editor), PLOT_2D, self.plot2d.controls)
            bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)   # named, not bare icons
            for action in (self.action_manager["trace_now"], self.analysis_toolbar.update_action,
                           self.action_manager["ray_inspector"]):
                bar.addAction(action)
            self.plot2d.toolbar = bar
            column.addWidget(bar)
            self.plot2d.canvas.setParent(panel)
            column.addWidget(self.plot2d.canvas, 1)
            self.dock_manager.create_dock(panel, "plot2d", "2D Plot",
                                          area=Qt.DockWidgetArea.RightDockWidgetArea)
            if "SystemDock" in self.dock_manager.docks:
                self.dock_manager.tabify(("SystemDock", "plot2d"))
            # an analysis run draws into the 2D plot: show it, or the user sees nothing happen
            self.analysis_toolbar.update_action.triggered.connect(lambda *_a: self.plot_2d_action())
        return self.plot2d

    def plot_2d_action(self) -> None:
        """Bring the 2D plot to the front -- shown, and in front of the panels tabbed with it."""
        plot = self.build_plot2d()
        dock = self.dock_manager["plot2d"]
        if dock.isHidden():
            self.dock_manager.rails.toggle(dock)
        dock.raise_()
        self.dock_manager.rails.refresh()
        plot.canvas.draw_idle()

    def refresh_from_model(self) -> dict:
        """Rebuild every view from the editor: the table, the scene, the window title."""
        # A model reset clears the view's current index, and the row forms open on whatever is
        # selected -- so applying one would leave the next Edit action with no row and a "Select
        # a surface row first" refusal (bugs/0871). Put the selection back.
        # The WHOLE selection, not just the current row: a table verb that just selected the
        # two rows it duplicated must not come back with one (bugs/0903).
        kept = self.selected_row_indices()
        current = self.selected_row_index()
        self.rows_model.refresh()
        if kept:
            self.select_rows(kept, current if current in kept else kept[0])
        self.rows_view.resizeColumnsToContents()
        drawn: dict = {"elements": [], "bodies": [], "error": None}
        if self.viewport is not None:
            drawn = self.viewport.show_editor_scene(self.editor)
            self.viewport.render()
        self._show_layout_title()
        self._adopt_replaced_layout()
        self._refresh_path_view_choices()
        if drawn.get("error"):
            # The model could not build its display geometry: say so rather than showing a
            # viewport that is quietly missing every optical element.
            self.statusBar().showMessage(
                f"3D view: the optical elements could not be built -- {drawn['error']}")
        elif self.viewport is not None:
            # a freshly drawn scene honours the View menu's current ray state
            self.viewport.set_rays_visible(bool(self.action_manager["show_rays"].isChecked()))
            self.statusBar().showMessage(
                f"3D view: {len(drawn['elements'])} optical elements, {drawn['rays']} rays, "
                f"{len(drawn['bodies'])} imported bodies.")
        return drawn

    def _show_layout_title(self) -> None:
        current = getattr(self.editor, "current_layout_file", None)
        self.setWindowTitle(f"KrakenOS -- Qt shell -- {Path(current).name}" if current
                            else "KrakenOS -- Qt shell")

    def _adopt_replaced_layout(self) -> None:
        """A whole new layout came in (Open, Reload, Reset, an import): the hosted 3D inspector now
        shows it. The model keeps a shell's inspector across the swap instead of destroying it as
        it does a separate Tk 3D window (bugs/0942)."""
        view = self.inspector_view
        inspector = getattr(view, "inspector", None)
        if inspector is None or not getattr(inspector, "_layout_replaced_pending", False):
            return
        try:
            alive = bool(inspector.winfo_exists())
        except Exception:
            alive = False
        if alive and inspector.available:
            inspector.adopt_replaced_layout()

    def load_layout_path(self, path) -> None:
        """Load a layout file by path, through the editor's own named-layout loader."""
        path = Path(path)
        self.editor.layout_files[path.stem] = path
        self.editor.load_layout_by_name(path.stem)
        self.editor.current_layout_file = path
        self.refresh_from_model()

    # ---- actions -------------------------------------------------------------------------------
    def open_layout_action(self) -> None:
        """The Tk File -> Open, unchanged: the model asks, our Qt host puts up the chooser."""
        self.editor.open_layout()
        self.refresh_from_model()

    def reload_layout_action(self) -> None:
        current = getattr(self.editor, "current_layout_file", None)
        if current is None:
            host_of(self).showinfo("Reload Layout", "No layout file is open yet.")
            return
        self.load_layout_path(current)

    def redraw_action(self) -> None:
        self.refresh_from_model()
        inspector = self._scene_inspector()
        if inspector is not None:
            inspector.refresh_from_editor()

    def toggle_rays_action(self, checked: bool = True) -> None:
        """Show or hide the traced light -- the Tk 3D view has the same switch."""
        if self.viewport is not None:
            self.viewport.set_rays_visible(bool(checked))
            self.viewport.render()
        inspector = self._scene_inspector()
        if inspector is not None and bool(inspector.show_rays_var.get()) != bool(checked):
            inspector.show_rays_var.set(bool(checked))      # the inspector's own Show rays box
            inspector._on_show_rays_changed()
        self.statusBar().showMessage(
            f"Rays {'shown' if checked else 'hidden'}"
            + (f" ({len(self.viewport.ray_actors)} traced)." if self.viewport is not None else "."))

    def reset_camera_action(self) -> None:
        if self.viewport is not None:
            self.viewport.reset_camera()
            self.viewport.render()
        inspector = self._scene_inspector()
        if inspector is not None:
            # frame the scene without turning the view -- what a Nav Cube snap does (bugs/0160)
            inspector._on_navigation_cube_snap()

    def open_report(self, builder):
        """Open a report dialog: build the data, show it, say what happened.

        This is the whole Qt side of a report dialog -- a port is a builder under
        `KrakenOS/UI/reports/` plus a menu entry (docs/design_qt_migration.md phase 3).
        """
        return self.show_model_report(lambda **values: builder(self.editor, **values),
                                      title=getattr(builder, "TITLE", "Report"))

    def show_model_report(self, build, *, title: str = "Report"):
        """Show a report in the Qt report dialog. `build(**controls)` is the report's own builder,
        already bound to its owner; the dialog rebuilds through it when a control changes.

        Also the model's `show_report` seam (bugs/0948): the Tk report handle a model command
        holds (`panels/report_view.ReportWindow`) shows its report here instead of in a Tk window.
        """
        from KrakenOS.UI.qt.dialogs.report_dialog import ReportDialog
        from KrakenOS.UI.reports import ReportFailed

        try:
            report = build()
        except ReportFailed as exc:
            host_of(self).showerror(title, f"Could not build the report:\n\n{exc}")
            self.statusBar().showMessage(f"{title} failed: {exc}")
            return None

        dialog = ReportDialog(report, parent=self, host=host_of(self), rebuild=build)
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        self.last_model_report_dialog = dialog
        dialog.show()
        self.statusBar().showMessage(report.status or report.title)
        return dialog

    def paraxial_matrix_report_action(self):
        """The system's paraxial matrices -- the Tk editor's dialog, rendered by Qt.

        Both views render the same `Report`: the builder is toolkit-free, so the numbers here
        cannot drift from the numbers there.
        """
        from KrakenOS.UI.reports import build_paraxial_matrix_report

        return self.open_report(build_paraxial_matrix_report)

    def branch_gaussian_q_report_action(self):
        """The Gaussian q of every traced branch, from the collector the Tk dialog uses."""
        from KrakenOS.UI.reports import build_branch_gaussian_q_report

        return self.open_report(build_branch_gaussian_q_report)

    def detector_aperture_report_action(self):
        """Which rays reach each detector, and which miss."""
        from KrakenOS.UI.reports import build_detector_aperture_report

        return self.open_report(build_detector_aperture_report)

    def branch_throughput_report_action(self):
        """Power delivered along every traced path (every path: the Tk filter is phase 3b)."""
        from KrakenOS.UI.reports import build_branch_throughput_report

        return self.open_report(build_branch_throughput_report)

    def source_illumination_report_action(self):
        """What each source puts onto the target surface the editor resolves."""
        from KrakenOS.UI.reports import build_source_illumination_report

        return self.open_report(build_source_illumination_report)

    def gaussian_beam_report_action(self):
        """The input beam through the system's paraxial matrices, step by step.

        The four inputs are report controls: typing one rebuilds through the same builder the Tk
        dialog uses. Its "Use Cavity Eigenmode" button is not here yet -- the model side exists
        (`reports.gaussian_cavity_eigenmode`), the Qt control does not.
        """
        from KrakenOS.UI.reports import build_gaussian_beam_report

        return self.open_report(build_gaussian_beam_report)

    def paraxial_calculator_action(self):
        """The Paraxial Calculator -- a form dialog, not a report: it can write back.

        The solve and the apply live in `KrakenOS/UI/paraxial_calculator.py`, which the Tk dialog
        was rewired onto, so both toolkits compute and apply the same way.
        """
        from KrakenOS.UI.qt.dialogs.calculator_dialog import ParaxialCalculatorDialog

        dialog = ParaxialCalculatorDialog(self.editor, parent=self, host=host_of(self))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        dialog.show()
        self.statusBar().showMessage(dialog.result.text())
        return dialog

    def ray_inspector_action(self):
        """Every traced ray, with the hits of the selected one beneath it."""
        from KrakenOS.UI.reports import build_ray_inspector_report

        return self.open_report(build_ray_inspector_report)

    def trace_paths_action(self):
        """Every traced path, nested under the ray it came from."""
        from KrakenOS.UI.reports import build_trace_path_report

        return self.open_report(build_trace_path_report)

    def nonseq_scene_graph_action(self):
        """The scene as the non-sequential trace sees it, with its three verbs."""
        from KrakenOS.UI.reports import build_nonseq_scene_graph_report

        return self.open_report(build_nonseq_scene_graph_report)

    # ---- the surface table: selection and the six verbs (bugs/0903) -----------------------------
    #: (label, editor method, tooltip) -- the Tk table toolbar's editing verbs
    TABLE_VERBS = (
        ("Add surface", "add_surface", "Insert a surface after the selection"),
        ("Delete", "delete_selected", "Delete the selected surfaces"),
        ("Duplicate", "duplicate_selected", "Duplicate the selected surfaces"),
        ("Flip", "flip_selected", "Reverse the selected surfaces (radii negated)"),
        ("\u25b2", "move_up", "Move the selected element up"),
        ("\u25bc", "move_down", "Move the selected element down"),
    )

    def _build_table_widget(self):
        """The table with its verbs above it, as the Tk table toolbar has them."""
        from PySide6.QtWidgets import QToolBar, QVBoxLayout, QWidget

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table_toolbar = QToolBar("Surface table")
        self.table_actions = {}
        for label, method, tip in self.TABLE_VERBS:
            action = self.table_toolbar.addAction(label)
            action.setToolTip(tip)
            action.triggered.connect(lambda _checked=False, method=method: self.run_table_verb(method))
            self.table_actions[method] = action
        # "Path view", right-aligned as on the Tk table toolbar: the Path-view placements act on it,
        # and choosing one selects that path's rows (bugs/0944)
        from PySide6.QtWidgets import QComboBox, QLabel, QSizePolicy

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.table_toolbar.addWidget(spacer)
        self.table_toolbar.addWidget(QLabel("Path view "))
        self.path_view = QComboBox()
        self.path_view.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.path_view.setMinimumContentsLength(24)
        self.path_view.setToolTip("The traced path the table, the 2-D plot and the Path-view placements use")
        self.path_view.activated.connect(self._choose_path_view)
        self.table_toolbar.addWidget(self.path_view)
        self._refresh_path_view_choices()
        layout.addWidget(self.table_toolbar)
        layout.addWidget(self.rows_view)
        # a refused edit says why, in the status bar rather than a Tk message box
        self.rows_view.itemDelegate().closeEditor.connect(self._report_refused_edit)
        # the optimisation entries of the Tk cell menu's Solve submenu (bugs/0904)
        from PySide6.QtCore import Qt as _Qt

        self.rows_view.setContextMenuPolicy(_Qt.ContextMenuPolicy.CustomContextMenu)
        self.rows_view.customContextMenuRequested.connect(self._show_cell_menu)
        return widget

    def _refresh_path_view_choices(self) -> None:
        """Offer the model's Path views; they change whenever a trace does."""
        combo = getattr(self, "path_view", None)
        if combo is None:
            return
        try:
            choices = list(self.editor.arm_view_options())
            current = str(self.editor.arm_view_var.get() or "")
        except Exception:
            return
        combo.blockSignals(True)
        try:
            if [combo.itemText(i) for i in range(combo.count())] != choices:
                combo.clear()
                combo.addItems(choices)
                # the labels are long ("Path 2: splitter to detector via ..."): the list shows them
                width = max((combo.fontMetrics().horizontalAdvance(text) for text in choices), default=0)
                combo.view().setMinimumWidth(width + 40)
            if current in choices:
                combo.setCurrentIndex(choices.index(current))
            elif choices:
                combo.setCurrentIndex(0)
        finally:
            combo.blockSignals(False)

    def _choose_path_view(self, index: int) -> None:
        """A Path view chosen here is the model's `set_arm_view`, as the Tk combobox commits it."""
        label = self.path_view.itemText(int(index))
        self.editor.arm_view_var.set(label)
        self.editor.set_arm_view()
        self.refresh_from_model()

    def cell_menu_actions(self, row: int, field: str) -> list:
        """(label, enabled, callable) of a cell's "Optimization / Solves" entries, from the model's
        own menu (bugs/0948). A separate method so a guard can read them without popping a menu.
        """
        model = self.editor.table_cell_menu(row, field)
        solves = next((entry.submenu for entry in (model.entries if model is not None else [])
                       if entry.kind == "cascade" and entry.label == "Optimization / Solves"), None)
        if solves is None:
            return []
        return [(entry.label, entry.enabled, (lambda entry=entry: solves.run(entry)))
                for entry in solves.entries if entry.kind == "command" and entry.command is not None]

    def _show_cell_menu(self, position) -> None:
        """The surface table's right-click menu: the model's own, recorded and drawn here.

        Until bugs/0948 this menu had three entries (the optimisation ones, 0904) where the Tk
        table's has over a hundred in thirteen submenus. The Tk builder now fills a `MenuModel`
        for a shell, exactly as the 3D inspector's menus do (0907), so nothing is ported twice.
        """
        from KrakenOS.UI.qt.inspector_view import build_qmenu

        index = self.rows_view.indexAt(position)
        if not index.isValid():
            return
        model = self.editor.table_cell_menu(index.row(), self.rows_model.field(index.column()))
        if model is None or not model.entries:
            return
        menu = build_qmenu(model, self.rows_view)
        model.on_close = menu.close

        def follow(qmenu) -> None:
            # after ANY entry, in whichever submenu, the table and the 3D view follow the model
            # (connected after build_qmenu's own slot, so the entry has run by then)
            for action in qmenu.actions():
                if action.menu() is not None:
                    follow(action.menu())
                elif not action.isSeparator():
                    action.triggered.connect(lambda _checked=False: self.refresh_from_model())

        follow(menu)
        #: the menu last shown and its model, for a guard to read and trigger
        self.last_cell_menu, self.last_cell_menu_model = menu, model
        menu.popup(self.rows_view.viewport().mapToGlobal(position))

    def _report_refused_edit(self, *_args) -> None:
        refusal = getattr(self.rows_model, "last_refusal", "")
        if refusal:
            self.statusBar().showMessage(f"Edit refused: {refusal}")
            self.rows_model.last_refusal = ""

    def run_table_verb(self, method: str) -> None:
        """Run one of the model's table verbs on the selection, then redraw."""
        getattr(self.editor, method)()
        self.refresh_from_model()

    def selected_row_indices(self) -> list:
        """The model's `selected_row_indices` seam: the rows selected in THIS table."""
        model = self.rows_view.selectionModel()
        if model is None:
            return []
        return sorted({index.row() for index in model.selectedRows()})

    def select_rows(self, indices, focus_index=None) -> None:
        """The model's `select_rows` seam: select what a verb just made or moved."""
        from PySide6.QtCore import QItemSelection, QItemSelectionModel

        model = self.rows_view.selectionModel()
        if model is None:
            return
        selection = QItemSelection()
        last_column = self.rows_model.columnCount() - 1
        for row in indices:
            if 0 <= int(row) < self.rows_model.rowCount():
                selection.select(self.rows_model.index(int(row), 0),
                                 self.rows_model.index(int(row), last_column))
        model.select(selection, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        if focus_index is not None and 0 <= int(focus_index) < self.rows_model.rowCount():
            model.setCurrentIndex(self.rows_model.index(int(focus_index), 0),
                                  QItemSelectionModel.SelectionFlag.NoUpdate)

    def show_rows(self) -> None:
        """The model's `show_rows` seam: the rows were rebuilt, keep the selection."""
        kept = self.selected_row_indices()
        self.rows_model.refresh()
        if kept:
            self.select_rows(kept, kept[0])

    def selected_row_index(self):
        """The surface table's current row -- what a row form edits."""
        index = self.rows_view.currentIndex()
        return index.row() if index.isValid() else None

    def open_row_form(self, builder, row_index=None):
        """Open a row-editing dialog on the selected row (docs/design_qt_migration.md phase 3)."""
        from KrakenOS.UI.qt.dialogs.row_form_dialog import RowFormDialog
        from KrakenOS.UI.row_forms import FormRefused

        if row_index is None:
            row_index = self.selected_row_index()
        title = getattr(builder, "TITLE", "Row settings")
        try:
            # row_index=False marks a builder that owns its own selection (a record list)
            form = builder(self.editor) if row_index is False else builder(self.editor, row_index)
        except FormRefused as exc:
            host_of(self).showinfo(title, str(exc))
            self.statusBar().showMessage(f"{title}: {exc}")
            return None

        dialog = RowFormDialog(form, parent=self, host=host_of(self))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        dialog.show()
        self.statusBar().showMessage(form.summary or form.title)
        return dialog

    def beam_splitter_action(self):
        """Edit the selected Beam Splitter row."""
        from KrakenOS.UI.row_forms import build_beam_splitter_form

        return self.open_row_form(build_beam_splitter_form)

    def diffuse_scatter_action(self):
        """Edit the selected Diffuse Object row."""
        from KrakenOS.UI.row_forms import build_diffuse_scatter_form

        return self.open_row_form(build_diffuse_scatter_form)

    def error_map_action(self):
        """Import or clear the selected surface's measured error map."""
        from KrakenOS.UI.row_forms import build_error_map_form

        return self.open_row_form(build_error_map_form)

    def coating_material_action(self):
        """Edit the selected surface's coating table and metal index."""
        from KrakenOS.UI.row_forms import build_coating_material_form

        return self.open_row_form(build_coating_material_form)

    def advanced_surface_action(self):
        """Every KrakenOS attribute of the selected surface, in tabs."""
        from KrakenOS.UI.row_forms import build_advanced_surface_form

        return self.open_row_form(build_advanced_surface_form)

    def detector_settings_action(self):
        """Mark the selected row as a terminal detector and size it."""
        from KrakenOS.UI.row_forms import build_detector_settings_form

        return self.open_row_form(build_detector_settings_form)

    def scene_target_action(self):
        """Edit the selected row's scene-target role, name and detector metadata."""
        from KrakenOS.UI.row_forms import build_scene_target_form

        return self.open_row_form(build_scene_target_form)

    def path_local_pose_action(self):
        """Edit the selected placed element's pose in its own path frame."""
        from KrakenOS.UI.row_forms import build_path_local_pose_form

        return self.open_row_form(build_path_local_pose_form)

    def element_settings_action(self):
        """Edit the selected element block's path metadata."""
        from KrakenOS.UI.row_forms import build_element_settings_form

        return self.open_row_form(build_element_settings_form)

    def scene_sources_action(self):
        """Add, edit and apply the scene's source records."""
        from KrakenOS.UI.row_forms import build_scene_source_manager_form

        # a record-list form owns its own selection, so it takes no row index
        return self.open_row_form(build_scene_source_manager_form, row_index=False)

    def glass_catalog_action(self):
        """Pick a catalogue glass and apply it to the selected row."""
        from KrakenOS.UI.row_forms import build_glass_catalog_form

        return self.open_row_form(build_glass_catalog_form, row_index=False)

    def stock_lens_action(self):
        """Search a .ZMF catalog and insert a stock lens as surface rows."""
        from KrakenOS.UI.row_forms import build_stock_lens_form

        return self.open_row_form(build_stock_lens_form, row_index=False)

    def inspection_cell_action(self):
        """Slot a station layout on each of the part's six faces."""
        from KrakenOS.UI.row_forms import build_inspection_cell_form

        return self.open_row_form(build_inspection_cell_form, row_index=False)

    def source_edit_action(self):
        """Edit a scene source's origin, direction and emitting size."""
        from KrakenOS.UI.row_forms import build_scene_source_edit_form

        specs = self.editor._normalize_scene_source_specs(
            getattr(self.editor, "layout_scene_source_specs", []) or [])
        source_id = str(specs[0].get("source_id", "")) if specs else ""

        def builder(editor, _row=None):
            return build_scene_source_edit_form(editor, source_id)

        builder.TITLE = build_scene_source_edit_form.TITLE
        return self.open_row_form(builder, row_index=False)

    def inspection_part_action(self):
        """Size the 3D part at the object plane and solve the FOV to its face."""
        from KrakenOS.UI.row_forms import build_inspection_part_form

        return self.open_row_form(build_inspection_part_form, row_index=False)

    def surface_shape_action(self):
        """Asphere, Zernike, ExtraData, UDA and mask, with a live sag plot."""
        from KrakenOS.UI.row_forms import build_surface_shape_form

        return self.open_row_form(build_surface_shape_form)

    def catalog_matcher_action(self):
        """List every registered camera x catalog lens combination that meets a requirement."""
        from KrakenOS.UI.row_forms import build_catalog_matcher_form

        return self.open_row_form(build_catalog_matcher_form, row_index=False)

    def system_selection_action(self):
        """Size the camera and the lens for a FOV, resolution and working distance (0631; 0930)."""
        from KrakenOS.UI.row_forms.system_selection import build_system_selection_form_model

        return self.open_row_form(build_system_selection_form_model, row_index=False)

    def galvo_scan_action(self):
        """The TiltX angles the selected mirror is drawn at."""
        from KrakenOS.UI.row_forms import build_galvo_scan_form

        return self.open_row_form(build_galvo_scan_form)

    def grating_settings_action(self):
        """Diffraction order, pitch and line angle for the selected row."""
        from KrakenOS.UI.row_forms import build_grating_settings_form

        return self.open_row_form(build_grating_settings_form)

    def tolerance_preset_action(self):
        """Save the Monte Carlo settings, merit operands and tolerance roles as a preset."""
        from KrakenOS.UI.row_forms import build_save_tolerance_preset_form

        return self.open_row_form(build_save_tolerance_preset_form, row_index=False)

    def apply_tolerance_preset_action(self):
        """Apply one of the layout's saved tolerance solve presets."""
        from KrakenOS.UI.row_forms import build_apply_tolerance_preset_form

        return self.open_row_form(build_apply_tolerance_preset_form, row_index=False)

    def optical_solid_diagnostics_action(self):
        """The trace-readiness of every CAD/STL solid row -- the report the Tk dialog shows (0936)."""
        from KrakenOS.UI.reports import build_optical_solid_diagnostics_report

        return self.open_report(build_optical_solid_diagnostics_report)

    def run_editor_command(self, method: str):
        """A menu command that is the editor's own method (bugs/0942): run it, and when it changes
        the model (`actions.EDITOR_REFRESH`), let every view re-read it."""
        from KrakenOS.UI.qt.actions import EDITOR_REFRESH

        result = getattr(self.editor, method)()
        if method in EDITOR_REFRESH:
            self.refresh_from_model()
        else:
            self._show_layout_title()  # Save / Save As may have named the layout
        return result

    def _place_top_rail(self) -> None:
        """The top edge's tab strip: in the ribbon's tab row, beside the search box, while the
        ribbon is docked at the top; its own row at the top of the window otherwise."""
        from PySide6.QtCore import QSize, Qt

        rails = self.dock_manager.rails
        strip = rails.rails["top"]
        ribbon = self.ribbon
        inside = (not ribbon.dock.isFloating()
                  and self.dockWidgetArea(ribbon.dock) == Qt.DockWidgetArea.TopDockWidgetArea)
        hosted = ribbon.corner_row.indexOf(strip) >= 0
        if inside and not hosted:
            self.removeToolBar(strip)
            ribbon.corner_row.insertWidget(0, strip)
            strip.setIconSize(QSize(16, 16))
            strip.setFixedHeight(ribbon.tabs.tabBar().sizeHint().height())
        elif not inside and hosted:
            ribbon.corner_row.removeWidget(strip)
            strip.setMinimumHeight(0)
            strip.setMaximumHeight(16777215)
            self.addToolBar(Qt.ToolBarArea.TopToolBarArea, strip)
        strip.setVisible(False)          # `refresh` shows it again when the edge has a tab
        rails.refresh()

    # ---- a big clean 3D scene (bugs/0961) -------------------------------------------------------
    def toolbar_3d_action(self, checked: bool = True) -> None:
        """Show or hide the 3D scene's tabbed View / Scene / Carry toolbar."""
        toolbar = getattr(self.inspector_view, "toolbar", None)
        if toolbar is not None:
            toolbar.setVisible(bool(checked))

    def hide_panels_action(self, checked: bool = True) -> None:
        """Put every panel away, or bring back the ones that were put away."""
        rails = self.dock_manager.rails
        if checked:
            rails.hide_all()
        else:
            rails.show_all()
        self._follow_panels()

    def _follow_panels(self) -> None:
        """Hide All Panels reads as on while no panel is open, however they were closed."""
        action = self.action_manager.actions.get("hide_panels")
        if action is not None:
            hidden = not self.dock_manager.rails.any_open()
            if action.isChecked() != hidden:
                action.setChecked(hidden)

    def clean_scene_action(self, checked: bool = True) -> None:
        """Only the 3D scene: fold the ribbon, hide the 3D toolbar and every panel -- and, switched
        off, put back exactly what it put away (a panel already closed stays closed)."""
        toolbar_switch = self.action_manager["toolbar_3d"]
        if checked:
            if self._clean_scene_saved is not None:
                return
            ribbon = self.ribbon
            self._clean_scene_saved = {
                "ribbon_folded": bool(ribbon.collapsed),
                "toolbar_shown": bool(toolbar_switch.isChecked()),
                "panels": self.dock_manager.rails.hide_all(),
            }
            if not ribbon.dock.isFloating() and not ribbon.collapsed:
                ribbon.set_collapsed(True)
            if toolbar_switch.isChecked():
                toolbar_switch.trigger()
            self.statusBar().showMessage("Clean 3D scene -- F11, or the button by the ribbon's fold arrow, "
                                         "puts the toolbars and panels back.")
        else:
            saved, self._clean_scene_saved = self._clean_scene_saved, None
            if saved is None:
                return
            # the ribbon first, while its neighbours are still away: it settles the top area's height
            # (its own fold keeps the heights of the docks beside it), then the panels take theirs
            if not self.ribbon.dock.isFloating() and self.ribbon.collapsed != saved["ribbon_folded"]:
                self.ribbon.set_collapsed(saved["ribbon_folded"])
            if saved["toolbar_shown"] and not toolbar_switch.isChecked():
                toolbar_switch.trigger()
            if saved["panels"]:
                self.dock_manager.rails.show_all(only=saved["panels"])
        self._follow_panels()

    def show_undo_state(self, can_undo: bool, can_redo: bool) -> None:
        """The model's `show_undo_state` seam: Undo / Redo enabled as its history allows."""
        for name, enabled in (("undo", can_undo), ("redo", can_redo)):
            action = self.action_manager.actions.get(name)
            if action is not None:
                action.setEnabled(bool(enabled))

    def mtf_from_image_action(self):
        """Measure a real MTF from a captured image: a slanted edge, or USAF three-bar elements."""
        self.editor.open_mtf_from_image_dialog()
        return self.last_mtf_from_image_dialog

    def show_mtf_from_image_dialog(self):
        """The model's `show_mtf_from_image_dialog` seam: a session, rendered by the Qt dialog."""
        from KrakenOS.UI.mtf_from_image_session import MtfFromImageSession
        from KrakenOS.UI.qt.dialogs.mtf_from_image_dialog import MtfFromImageDialog

        dialog = MtfFromImageDialog(MtfFromImageSession(self.editor), parent=self, host=host_of(self))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        dialog.show()
        self.last_mtf_from_image_dialog = dialog
        return dialog

    def face_roles_action(self):
        """Assign optical intent to the faces of the selected CAD/STL solid row."""
        row_index = self.selected_row_index()
        if row_index is None:
            host_of(self).showinfo("Assign CAD/STL Optical Faces", "Select an STL solid row first.")
            return None
        self.editor.open_optical_solid_face_role_editor(int(row_index))
        return self.last_face_roles_dialog

    def show_face_roles_dialog(self, session):
        """The model's `show_face_roles_dialog` seam: it built a `FaceRolesSession` for a row and
        hands it here instead of opening its Tk window (bugs/0934)."""
        from KrakenOS.UI.qt.dialogs.face_roles_dialog import FaceRolesDialog

        dialog = FaceRolesDialog(session, parent=self, host=host_of(self))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        dialog.show()
        dialog.build_preview()        # VTK takes the shown window's native id
        if session.records:
            session.select([0], 0)    # the first face, as the Tk dialog opens
        self.last_face_roles_dialog = dialog
        return dialog

    def _forget_dialog(self, dialog) -> None:
        if dialog in self._open_dialogs:
            self._open_dialogs.remove(dialog)

    def about_action(self) -> None:
        host_of(self).showinfo(
            "KrakenOS -- Qt shell",
            "The Qt front end of the Tk->Qt migration (docs/design_qt_migration.md).\n\n"
            "The optics model is the same KrakenLayoutEditor the Tk editor drives; this window "
            "reaches it through the UI host seam.")

    def quit_action(self) -> None:
        self.close()

    def resizeEvent(self, event):  # noqa: N802  (Qt's name)
        super().resizeEvent(event)
        # a short window folds the ribbon, a tall one opens it (bugs/0963)
        ribbon = getattr(self, "ribbon", None)
        if ribbon is not None:
            ribbon.follow_window_height()

    def closeEvent(self, event):  # noqa: N802  (Qt's name)
        variable = getattr(self.editor, "status_var", None)
        if self._status_trace is not None and variable is not None:
            try:
                variable.trace_remove("write", self._status_trace)
            except Exception:
                pass
        if self.viewport is not None:
            self.viewport.widget.close()
        super().closeEvent(event)
