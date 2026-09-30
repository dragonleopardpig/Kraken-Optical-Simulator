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

from KrakenOS.UI.qt.actions import ActionManager
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
    """Menus, a surface table, a 3D viewport and a status line over a live editor."""

    def __init__(self, editor, ui=None) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QAbstractItemView, QTableView, QVBoxLayout, QWidget

        super().__init__()
        self.editor = editor
        self.ui = ui if ui is not None else host_of(editor)
        self.viewport = None
        #: the real 3D inspector, hosted in a dock once asked for (bugs/0906)
        self.inspector_view = None

        self.setWindowTitle("KrakenOS -- Qt shell")
        self.resize(1500, 950)

        self.action_manager = ActionManager(self)
        self.action_manager.create_all_actions()
        self.menus = self.action_manager.populate_menu_bar(self.menuBar())

        # The viewport is NOT created here: it must be built once this window is shown, because
        # the VTK widget hands VTK its window id in its constructor and Qt recreates a native
        # window on reparenting. This container is its stable parent -- `build_viewport()` adds
        # the widget to the container's own layout, so nothing is ever reparented.
        self.plot2d = None
        self.viewport_host = QWidget()
        self.viewport_layout = QVBoxLayout(self.viewport_host)
        self.viewport_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.viewport_host)

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

        self.dock_manager = DockManager(self)
        self.dock_manager.create_dock(self.table_widget, "SurfaceTableDock", "Surface Table",
                                      Qt.DockWidgetArea.LeftDockWidgetArea)
        # the two panels the model used to write into Tk widgets directly (bugs/0898)
        self.results_panel = ResultsPanel(editor)
        self.dock_manager.create_dock(self.results_panel.table, "ResultsDock", "Results",
                                      Qt.DockWidgetArea.RightDockWidgetArea)
        self.dock_manager.create_dock(self.results_panel.log, "DebugDock", "Debug",
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_manager.create_dock(self.results_panel.progress, "ProgressDock", "Progress",
                                      Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock_manager.setup_default_layout()
        # the analysis picker and Update: the Qt shell could open every dialog and show every
        # result, but could not set an analysis up (bugs/0899)
        self.analysis_toolbar = AnalysisToolbar(self)
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
        # the CAD/STL face-roles editor opens here, over the model's session (bugs/0934)
        editor.show_face_roles_dialog = self.show_face_roles_dialog
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
        """Create the 3D viewport. Call this AFTER `show()` -- see the container above."""
        from KrakenOS.UI.qt.viewport import SceneViewport

        if self.viewport is None:
            self.viewport = SceneViewport(self.viewport_host)
            self.viewport_layout.addWidget(self.viewport.widget)
        return self.viewport

    def build_inspector_view(self):
        """Host the real 3D inspector in a dock. Call this AFTER `show()`, like `build_viewport`.

        The dock may move between areas but never float: floating makes the dock a new native
        top-level, and the VTK widget inside was handed its window id when it was built.
        """
        if self.inspector_view is not None:
            return self.inspector_view
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDockWidget, QVBoxLayout, QWidget

        from KrakenOS.UI.qt.inspector_view import InspectorView

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        # the top area, which nothing else uses: the right one already stacks five docks at
        # their minimum heights, and the inspector squeezed in there got 0 pixels (measured)
        dock = self.dock_manager.create_dock(container, "InspectorDock", "3D Inspector",
                                             area=Qt.DockWidgetArea.TopDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable
                         | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        dock.show()
        self.inspector_view = InspectorView(self.editor, container,
                                            status=self.statusBar().showMessage)
        # the View / Scene / Carry rows above the viewport, from the same catalogue as Tk (5f)
        if self.inspector_view.inspector.available:
            from KrakenOS.UI.qt.inspector_toolbar import build_toolbar

            self.inspector_view.toolbar = build_toolbar(self.inspector_view.inspector, container)
            layout.addWidget(self.inspector_view.toolbar)
            # the Live Controls the docks do not already carry, tabbed with them (5f part 2)
            from KrakenOS.UI.qt.live_controls_dock import LiveControlsForm

            self.live_controls = LiveControlsForm(self.inspector_view.inspector,
                                                  open_system_selection=self.system_selection_action)
            self.dock_manager.create_dock(self.live_controls.widget, "LiveControlsDock", "3D Live",
                                          Qt.DockWidgetArea.RightDockWidgetArea, scroll=True)
            self.dock_manager.tabify(("SystemDock", "SourceDock", "TraceDock", "OptimizationDock",
                                      "LiveControlsDock"))
            # the Scene Components browser, from the Tk browser's own nodes / selection / menus (5f 3b)
            from KrakenOS.UI.qt.scene_components_dock import SceneComponentsTree

            self.scene_components = SceneComponentsTree(self.inspector_view.inspector)
            self.dock_manager.create_dock(self.scene_components.container, "SceneComponentsDock",
                                          "Scene Components", Qt.DockWidgetArea.LeftDockWidgetArea)
        layout.addWidget(self.inspector_view.widget)
        # a VTK widget has no size hint, so the dock would open 0 pixels tall (measured) -- and a
        # 0-pixel viewport picks nothing
        self.inspector_view.widget.setMinimumSize(320, 240)
        self.resize_inspector_dock()
        if self.inspector_view.inspector.available:
            self.inspector_view.inspector.refresh_from_editor()
        else:
            self.statusBar().showMessage(
                f"3D inspector unavailable: {self.inspector_view.inspector.unavailable_reason}")
        return self.inspector_view

    def resize_inspector_dock(self) -> None:
        """Give the inspector two thirds of the height -- once the layout has run, since a
        `resizeDocks` before it is ignored (measured: the dock stayed at its minimum)."""
        from PySide6.QtCore import QTimer, Qt

        dock = self.dock_manager.docks.get("InspectorDock")
        if dock is None:
            return
        QTimer.singleShot(0, lambda: self.resizeDocks(
            [dock], [max(420, self.height() * 2 // 3)], Qt.Orientation.Vertical))

    def inspector_action(self) -> None:
        view = self.build_inspector_view()
        view.show()

    def build_plot2d(self):
        """Create the 2D layout plot and hand the editor its figure (bugs/0893).

        The model draws into `editor.ax`; this only supplies the canvas and connects the three
        matplotlib events both shells use. It lives in a dock so the 3D view keeps the centre.
        """
        from KrakenOS.UI.qt.plot2d import LayoutPlot2D

        if self.plot2d is None:
            self.plot2d = LayoutPlot2D(self.editor)
            from PySide6.QtCore import Qt

            self.dock_manager.create_dock(self.plot2d.widget, "plot2d", "2D Layout",
                                          area=Qt.DockWidgetArea.RightDockWidgetArea)
        return self.plot2d

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
        current = getattr(self.editor, "current_layout_file", None)
        self.setWindowTitle(f"KrakenOS -- Qt shell -- {Path(current).name}" if current
                            else "KrakenOS -- Qt shell")
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

    def toggle_rays_action(self, checked: bool = True) -> None:
        """Show or hide the traced light -- the Tk 3D view has the same switch."""
        if self.viewport is not None:
            self.viewport.set_rays_visible(bool(checked))
            self.viewport.render()
        self.statusBar().showMessage(
            f"Rays {'shown' if checked else 'hidden'} "
            f"({len(self.viewport.ray_actors) if self.viewport else 0} traced).")

    def reset_camera_action(self) -> None:
        if self.viewport is not None:
            self.viewport.reset_camera()
            self.viewport.render()

    def open_report(self, builder):
        """Open a report dialog: build the data, show it, say what happened.

        This is the whole Qt side of a report dialog -- a port is a builder under
        `KrakenOS/UI/reports/` plus a menu entry (docs/design_qt_migration.md phase 3).
        """
        from KrakenOS.UI.qt.dialogs.report_dialog import ReportDialog
        from KrakenOS.UI.reports import ReportFailed

        try:
            report = builder(self.editor)
        except ReportFailed as exc:
            title = getattr(builder, "TITLE", "Report")
            host_of(self).showerror(title, f"Could not build the report:\n\n{exc}")
            self.statusBar().showMessage(f"{title} failed: {exc}")
            return None

        # the dialog rebuilds through the same builder when one of its controls changes
        dialog = ReportDialog(report, parent=self, host=host_of(self),
                              rebuild=lambda **values: builder(self.editor, **values))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
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
        layout.addWidget(self.table_toolbar)
        layout.addWidget(self.rows_view)
        # a refused edit says why, in the status bar rather than a Tk message box
        self.rows_view.itemDelegate().closeEditor.connect(self._report_refused_edit)
        # the optimisation entries of the Tk cell menu's Solve submenu (bugs/0904)
        from PySide6.QtCore import Qt as _Qt

        self.rows_view.setContextMenuPolicy(_Qt.ContextMenuPolicy.CustomContextMenu)
        self.rows_view.customContextMenuRequested.connect(self._show_cell_menu)
        return widget

    def cell_menu_actions(self, row: int, field: str) -> list:
        """(label, enabled, callable) for a cell's optimisation menu -- the model decides.

        A separate method so a guard can read the menu without popping one up.
        """
        state = self.editor.optimization_cell_state(row, field)
        if not state["supported"]:
            return []
        name = state["label"]
        return [
            (f"{'Unselect' if state['marked'] else 'Select'} {name} for optimization", True,
             lambda: self.editor.toggle_optimization_cell(row, field)),
            ("Set bounds...", True, lambda: self.open_bounds_form(row, field)),
            ("Clear bounds", state["has_bounds"],
             lambda: self.editor.clear_bounds_for_cell(row, field)),
        ]

    def open_bounds_form(self, row: int, field: str):
        """The same bounds form the Tk "Set bounds..." opens (row_forms/presets, bugs/0891)."""
        from KrakenOS.UI.row_forms.presets import build_optimization_bounds_form

        spec = self.editor._variable_spec_for_field(field)

        def builder(owner, index):
            return build_optimization_bounds_form(owner, index, spec=spec)

        builder.TITLE = "Optimization bounds"
        return self.open_row_form(builder, row)

    def _show_cell_menu(self, position) -> None:
        from PySide6.QtWidgets import QMenu

        index = self.rows_view.indexAt(position)
        if not index.isValid():
            return
        actions = self.cell_menu_actions(index.row(), self.rows_model.field(index.column()))
        if not actions:
            return
        menu = QMenu(self.rows_view)
        for label, enabled, run in actions:
            action = menu.addAction(label)
            action.setEnabled(bool(enabled))
            action.triggered.connect(lambda _checked=False, run=run: (run(), self.refresh_from_model()))
        menu.exec(self.rows_view.viewport().mapToGlobal(position))

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
