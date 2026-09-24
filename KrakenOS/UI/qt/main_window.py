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
from KrakenOS.UI.qt.rows_table import make_rows_model
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

        self.setWindowTitle("KrakenOS -- Qt shell")
        self.resize(1500, 950)

        self.action_manager = ActionManager(self)
        self.action_manager.create_all_actions()
        self.menus = self.action_manager.populate_menu_bar(self.menuBar())

        # The viewport is NOT created here: it must be built once this window is shown, because
        # the VTK widget hands VTK its window id in its constructor and Qt recreates a native
        # window on reparenting. This container is its stable parent -- `build_viewport()` adds
        # the widget to the container's own layout, so nothing is ever reparented.
        self.viewport_host = QWidget()
        self.viewport_layout = QVBoxLayout(self.viewport_host)
        self.viewport_layout.setContentsMargins(0, 0, 0, 0)
        self.setCentralWidget(self.viewport_host)

        self.rows_model = make_rows_model(editor)
        self.rows_view = QTableView()
        self.rows_view.setModel(self.rows_model)
        self.rows_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.rows_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.rows_view.horizontalHeader().setStretchLastSection(True)
        self.rows_view.verticalHeader().setVisible(False)  # the "#" column already numbers them

        self.dock_manager = DockManager(self)
        self.dock_manager.create_dock(self.rows_view, "SurfaceTableDock", "Surface Table",
                                      Qt.DockWidgetArea.LeftDockWidgetArea)
        self.dock_manager.setup_default_layout()

        self._open_dialogs: list = []  # a modeless dialog must outlive the call that opened it
        self._status_trace = None
        self._bind_status_line()
        self.statusBar().showMessage(self._model_status() or "KrakenOS Qt shell ready.")

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

    def refresh_from_model(self) -> dict:
        """Rebuild every view from the editor: the table, the scene, the window title."""
        # A model reset clears the view's current index, and the row forms open on whatever is
        # selected -- so applying one would leave the next Edit action with no row and a "Select
        # a surface row first" refusal (bugs/0871). Put the selection back.
        selected = self.selected_row_index()
        self.rows_model.refresh()
        if selected is not None and 0 <= selected < self.rows_model.rowCount():
            self.rows_view.selectRow(selected)
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
