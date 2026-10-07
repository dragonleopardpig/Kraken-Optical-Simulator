"""The handle of one report window -- what the model talks to, whichever toolkit shows the report.

A report window is modeless and reusable: Update refreshes whichever report is open, so the panel
keeps a handle and asks it to open, refresh, close, select, copy and export.

Under a shell that draws its own dialogs (the Qt shell installs `show_report` on the editor) the
handle shows the report in the shell's dialog, and everything asked of it goes to that dialog
(bugs/0948). Otherwise Tk draws it: the widgets and everything that makes or drives them are
`panels/report_view.py`, which this module imports only then (bugs/0984). Until that bug this
class WAS the Tk view, so every panel that wanted a report handle loaded tkinter with it -- and
through the panels, `services/analysis_reports.py`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from KrakenOS.UI.reports.base import ReportFailed
from KrakenOS.UI.uihost import host_of


class ReportWindow:
    """One modeless report window: build, show, refresh, copy, export.

    `build(**controls)` is the report builder -- the same callable the Qt shell hands its
    dialog, called with every control's current value. `owner` is the panel, which forwards
    unknown attributes to the editor.
    """

    def __init__(self, owner: Any, build, *, geometry: str = "1160x560",
                 minsize: tuple[int, int] = (860, 360), csv_title: str = "") -> None:
        self.owner = owner
        self.build = build
        self.geometry = geometry
        self.minsize = minsize
        self.csv_title = csv_title
        self.report = None
        #: the shell's own dialog, while a shell (not this Tk window) is showing the report
        self.shell_view = None
        # ---- what the Tk view makes, when Tk draws (panels/report_view.py); None / empty otherwise
        self.window: Any = None
        self.table: Any = None
        self.detail_table: Any = None
        self.detail_widget: Any = None
        self.summary_var: Any = None
        self.controls: dict[str, Any] = {}
        #: widget per control key, so a rebuild can refresh a combobox's own choices
        self.control_widgets: dict[str, Any] = {}
        #: tree node iid -> its detail key; rebuilt with the tree, so a stale node cannot answer
        self._tree_keys: dict[str, Any] = {}

    # ---- lifecycle ------------------------------------------------------------------------
    @property
    def editor(self) -> Any:
        # `or self.owner`: the editor forwards unknown attributes to its Tk root, so
        # `editor.editor` returns None rather than raising (bugs/0883).
        return getattr(self.owner, "editor", None) or self.owner

    def _shell_report(self):
        """The running shell's `show_report`, when it draws its own report dialogs."""
        editor = self.editor
        return editor.__dict__.get("show_report") if hasattr(editor, "__dict__") else None

    def _shell_view(self):
        """The shell's dialog showing this report, while it is up."""
        view = self.shell_view
        if view is None:
            return None
        try:
            if view.isVisible():
                return view
        except Exception:
            pass
        self.shell_view = None
        return None

    def is_open(self) -> bool:
        if self._shell_view() is not None:
            return True
        if self.window is None:
            return False
        return self._tk().window_exists(self)

    def open(self):
        """Show the report, reusing the window when it is already up."""
        shell = self._shell_report()
        if shell is not None:
            view = self._shell_view()
            if view is not None:
                self.refresh()
                view.raise_()
                view.activateWindow()
                return view
            self.shell_view = shell(self.build)
            self.report = getattr(self.shell_view, "report", None)
            return self.shell_view
        if self.is_open():
            self.refresh()
            return self._tk().raise_window(self)
        report = self._build()
        if report is None:
            return None
        self.report = report
        self._make_window(report)
        self._render(report)
        return self.window

    def close(self) -> None:
        view, self.shell_view = self.shell_view, None
        if view is not None:
            try:
                view.close()
            except Exception:
                pass
        window = self.window
        self.window = None
        self.table = None
        self.detail_table = None
        self.detail_widget = None
        self.summary_var = None
        self.controls = {}
        self.control_widgets = {}
        if window is not None:
            self._tk().destroy_window(window)

    def refresh_if_open(self) -> None:
        """What Update calls: refresh a live window, forget a window the user already closed."""
        if self._shell_view() is not None:
            self.refresh()
            return
        if self.window is None:
            return
        if not self.is_open():
            self.close()
            return
        self.refresh()

    def refresh(self) -> None:
        if not self.is_open():
            return
        report = self._build()
        if report is None:
            return
        self.report = report
        view = self._shell_view()
        if view is not None:
            view.set_report(report)
            return
        self._render(report)

    # ---- model ----------------------------------------------------------------------------
    def control_values(self) -> dict:
        view = self._shell_view()
        if view is not None:
            return dict(view.control_values())
        return {key: var.get() for key, var in self.controls.items()}

    def _build(self):
        try:
            return self.build(**self.control_values())
        except ReportFailed as exc:
            host_of(self.editor).showerror("Report", str(exc), parent=self.editor)
            self._set_status(f"Report failed: {exc}")
            return None

    def _set_status(self, text: str) -> None:
        status_var = getattr(self.owner, "status_var", None)
        if status_var is not None and text:
            status_var.set(text)

    # ---- the Tk view -----------------------------------------------------------------------
    # The widgets are Tk's to make and to drive: `panels/report_view.py`. Each name below is what
    # this class always called it; the body is over there.
    @staticmethod
    def _tk():
        """The Tk view of a report -- imported when Tk draws one, never under another shell."""
        from KrakenOS.UI.panels import report_view

        return report_view

    def _make_window(self, report) -> None:
        self._tk().make_window(self, report)

    def _make_table(self, parent, report):
        return self._tk().make_table(self, parent, report)

    def _make_detail_table(self, parent, detail):
        return self._tk().make_detail_table(self, parent, detail)

    def _render(self, report) -> None:
        self._tk().render(self, report)

    def _insert_tree(self, table, parent, rows) -> None:
        self._tk().insert_tree(self, table, parent, rows)

    def _refresh_controls(self, report) -> None:
        self._tk().refresh_controls(self, report)

    # ---- master/detail --------------------------------------------------------------------
    def selected_key(self):
        """The detail key of the selected row: its index in a table, its node key in a tree."""
        view = self._shell_view()
        if view is not None:
            return view.selected_key()
        if self.table is None:
            return None
        return self._tk().selected_key(self)

    def select_key(self, key) -> None:
        """Select the row or node carrying `key`, falling back to the first row."""
        view = self._shell_view()
        if view is not None:
            view.select_key(key)
            return
        if self.table is None or self.report is None:
            return
        self._tk().select_key(self, key)

    def select_row(self, index: int) -> None:
        """Select master row `index` (a table row, or the index-th node that carries a key).

        Selecting is this method's job whether or not there IS a detail view: a report without
        one still opens on a row, and its verbs act on whatever is selected (bugs/0897).
        """
        view = self._shell_view()
        if view is not None:
            view.select_master_row(int(index))
            return
        if self.table is None or self.report is None:
            return
        self._tk().select_row(self, int(index))

    def refresh_detail(self) -> None:
        """Show the detail of whatever is selected -- what a selection change calls."""
        if self._shell_view() is not None:
            return                      # the shell's dialog follows its own selection
        self._show_detail(self.selected_key())

    def _show_detail(self, key) -> None:
        if self.report is None or (self.detail_table is None and self.detail_widget is None):
            return
        self._tk().show_detail(self, key)

    # ---- toolbar --------------------------------------------------------------------------
    def copy_text(self) -> str:
        """Put the whole report on the clipboard, and in Debug when the clipboard refuses."""
        # `or self._build()`: copying and exporting are offered whether or not the window is up
        report = self.report or self._build()
        if report is None:
            return ""
        text = report.text
        append_debug = getattr(self.owner, "append_debug", None)
        copy = getattr(self.owner, "_copy_text_to_clipboard", None)
        ok, backend = copy(text) if copy is not None else (False, "")
        if append_debug is not None:
            append_debug(text)
        self._set_status(f"{report.title} copied to clipboard ({backend})." if ok
                         else f"{report.title} written to Debug; clipboard unavailable.")
        return text

    def run_action(self, action) -> str:
        """A toolbar verb the MODEL defines.

        The view supplies only what a toolkit must: a save path, the current control values and
        which row is selected. A verb that also changes the controls returns a `ReportUpdate`,
        and adopting those values is this method's other job.
        """
        arguments: tuple = ()
        if action.save_title:
            path = host_of(self.editor).asksaveasfilename(
                title=action.save_title, defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*")], parent=self.editor)
            if not path:
                return ""
            arguments += (path,)
        if action.needs_controls:
            arguments += (self.control_values(),)
        if action.needs_selection:
            arguments += (self.selected_key(),)
        result = action.run(*arguments)
        controls = getattr(result, "controls", None)
        if controls is None:
            status = str(result or "")
        else:
            for key, value in controls.items():
                variable = self.controls.get(key)
                if variable is not None:
                    variable.set(str(value))
            if result.rebuild:
                self.refresh()
            status = str(result.status or "")
        self._set_status(status)
        return status

    def export_csv(self) -> str:
        report = self.report or self._build()
        if report is None:
            return ""
        if not report.rows:
            host_of(self.editor).showinfo(f"Export {report.title}",
                                          "No data. Click Update first.", parent=self.editor)
            return ""
        path = host_of(self.editor).asksaveasfilename(
            title=f"Export {self.csv_title or report.title} CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return ""
        report.write_csv(path)
        self._set_status(f"{self.csv_title or report.title} CSV exported: {Path(path).name}")
        return str(path)
