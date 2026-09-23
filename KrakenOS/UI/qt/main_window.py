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
        self.rows_model.refresh()
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

    def paraxial_matrix_report_action(self) -> None:
        """Open the Paraxial Matrix Report -- the Tk editor's dialog, rendered by Qt.

        Both views render the same `Report`: the builder is toolkit-free, so the numbers here
        cannot drift from the numbers there.
        """
        from KrakenOS.UI.qt.dialogs.report_dialog import ReportDialog
        from KrakenOS.UI.reports import ReportFailed, build_paraxial_matrix_report

        try:
            report = build_paraxial_matrix_report(self.editor)
        except ReportFailed as exc:
            host_of(self).showerror(
                "Paraxial Matrix Report", f"Could not build paraxial matrix report:\n\n{exc}")
            self.statusBar().showMessage(f"Paraxial matrix report failed: {exc}")
            return

        dialog = ReportDialog(report, parent=self, host=host_of(self))
        dialog.finished.connect(lambda _result, d=dialog: self._forget_dialog(d))
        self._open_dialogs.append(dialog)
        dialog.show()
        self.statusBar().showMessage(report.status)
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
