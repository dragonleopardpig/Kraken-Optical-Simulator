"""The Tk view of a `Report` (docs/design_qt_migration.md phase 4).

The Tk half of what `qt/dialogs/report_dialog.py` does for Qt. A report dialog is a summary
line, some controls that rebuild it, a table (or a tree) and an export; none of that is report
specific, so all four of the Tk report windows are this one class over their own builder. What
a report SHOWS lives in `KrakenOS/UI/reports/`; this decides only how it is laid out.

The window is modeless and reusable -- Update refreshes whichever report is open -- so unlike
`render_row_form` this is a class: the panel keeps the handle and asks it to refresh.
"""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.reports import ReportFailed

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
        self.window: tk.Toplevel | None = None
        self.table: ttk.Treeview | None = None
        self.detail_table: ttk.Treeview | None = None
        self.detail_widget: tk.Text | None = None
        self.summary_var: tk.StringVar | None = None
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

    def is_open(self) -> bool:
        window = self.window
        if window is None:
            return False
        try:
            return bool(window.winfo_exists())
        except tk.TclError:
            return False

    def open(self) -> "tk.Toplevel | None":
        """Show the report, reusing the window when it is already up."""
        if self.is_open():
            self.refresh()
            window = self.window
            window.deiconify()
            window.lift()
            window.focus_force()
            return window
        report = self._build()
        if report is None:
            return None
        self.report = report
        self._make_window(report)
        self._render(report)
        return self.window

    def close(self) -> None:
        window = self.window
        self.window = None
        self.table = None
        self.detail_table = None
        self.detail_widget = None
        self.summary_var = None
        self.controls = {}
        self.control_widgets = {}
        if window is not None:
            try:
                if window.winfo_exists():
                    window.destroy()
            except tk.TclError:
                pass

    def refresh_if_open(self) -> None:
        """What Update calls: refresh a live window, forget a window the user already closed."""
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
        self._render(report)

    # ---- model ----------------------------------------------------------------------------
    def control_values(self) -> dict:
        return {key: var.get() for key, var in self.controls.items()}

    def _build(self):
        try:
            return self.build(**self.control_values())
        except ReportFailed as exc:
            messagebox.showerror("Report", str(exc), parent=self.editor)
            self._set_status(f"Report failed: {exc}")
            return None

    def _set_status(self, text: str) -> None:
        status_var = getattr(self.owner, "status_var", None)
        if status_var is not None and text:
            status_var.set(text)

    # ---- widgets --------------------------------------------------------------------------
    def _make_window(self, report) -> None:
        editor = self.editor
        window = tk.Toplevel(editor)
        window.withdraw()
        window.title(report.title)
        window.geometry(self.geometry)
        window.minsize(*self.minsize)
        window.transient(editor)
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)
        self.window = window

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="left")
        if report.text:
            # a report the model can render as text; the others have nothing to copy
            ttk.Button(toolbar, text="Copy", command=self.copy_text).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_csv).pack(side="left", padx=(6, 0))
        for action in report.actions:
            ttk.Button(toolbar, text=action.label,
                       command=lambda action=action: self.run_action(action)).pack(
                           side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self.close).pack(side="left", padx=(6, 0))
        for control in report.controls:
            ttk.Label(toolbar, text=control.label).pack(side="left", padx=(18, 4))
            var = tk.StringVar(master=window, value=str(control.value))
            if hasattr(control, "choices"):
                widget = ttk.Combobox(toolbar, textvariable=var, state="readonly", width=36,
                                      values=list(control.choices))
                widget.bind("<<ComboboxSelected>>", lambda _event: self.refresh(), add="+")
            else:
                # a typed-in value: rebuild when the field is committed, not per keystroke
                widget = ttk.Entry(toolbar, textvariable=var, width=max(control.width, 6))
                widget.bind("<Return>", lambda _event: self.refresh(), add="+")
                widget.bind("<FocusOut>", lambda _event: self.refresh(), add="+")
            widget.pack(side="left")
            self.controls[control.key] = var
            self.control_widgets[control.key] = widget

        self.summary_var = tk.StringVar(master=window, value=report.summary)
        ttk.Label(window, textvariable=self.summary_var, padding=(8, 6, 8, 0), anchor="w",
                  justify="left").grid(row=1, column=0, sticky="ew")

        body = ttk.Frame(window, padding=8)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=3)
        self.table = self._make_table(body, report)
        if report.detail is not None:
            body.rowconfigure(2, weight=2)
            ttk.Label(body, text=report.detail.label, anchor="w").grid(row=1, column=0,
                                                                      sticky="ew", pady=(8, 2))
            self.detail_table = self._make_detail_table(body, report.detail)
        elif report.detail_text is not None:
            body.rowconfigure(2, weight=0)
            frame = ttk.LabelFrame(body, text=report.detail_text.label, padding=(8, 6, 8, 8))
            frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
            frame.columnconfigure(0, weight=1)
            widget = tk.Text(frame, height=report.detail_text.height, wrap="word",
                             borderwidth=0, relief="flat")
            widget.grid(row=0, column=0, sticky="ew")
            widget.configure(state="disabled")
            for binder in ("_bind_text_copy_shortcuts", "_bind_text_context_menu"):
                bind = getattr(self.owner, binder, None)
                if bind is not None:
                    bind(widget)
            self.detail_widget = widget

        show = getattr(self.owner, "_show_centered_dialog", None)
        if show is not None:
            show(window)
        else:
            window.deiconify()

    def _make_table(self, parent, report) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = list(report.keys)
        if report.tree is not None:
            table = ttk.Treeview(frame, columns=columns, show="tree headings",
                                 selectmode="browse")
            table.heading("#0", text=report.tree_heading)
            table.column("#0", width=200, stretch=False)
        else:
            table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for column in report.columns:
            table.heading(column.key, text=column.heading)
            table.column(column.key, width=column.width, stretch=column.stretch,
                         anchor={"l": "w", "c": "center", "r": "e"}[column.alignment])
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        table.bind("<<TreeviewSelect>>", lambda _event: self.refresh_detail(), add="+")
        activate = next((action for action in report.actions if action.on_activate), None)
        if activate is not None:
            table.bind("<Double-1>", lambda _event, action=activate: self.run_action(action),
                       add="+")
        return table

    def _make_detail_table(self, parent, detail) -> ttk.Treeview:
        frame = ttk.Frame(parent)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = [column.key for column in detail.columns]
        table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for column in detail.columns:
            table.heading(column.key, text=column.heading)
            table.column(column.key, width=column.width, stretch=column.stretch,
                         anchor={"l": "w", "c": "center", "r": "e"}[column.alignment])
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        table.configure(yscrollcommand=y_scroll.set)
        return table

    # ---- rendering ------------------------------------------------------------------------
    def _render(self, report) -> None:
        # a refresh must land where the user was, not back at the top: Update rebuilds these
        # windows behind them, and the Ray Inspector's own dialog always kept its row
        previous = self.selected_key() if self.report is not None else None
        if self.summary_var is not None:
            self.summary_var.set(report.summary)
        self._refresh_controls(report)
        table = self.table
        if table is not None:
            table.delete(*table.get_children())
            self._tree_keys = {}
            if report.tree is not None:
                self._insert_tree(table, "", report.tree)
            else:
                for index in range(len(report.rows)):
                    table.insert("", "end", iid=str(index),
                                 values=[report.cell(index, column)
                                         for column in range(len(report.columns))])
        self.select_key(previous if previous is not None else report.initial_key)
        self._set_status(report.status)

    def _insert_tree(self, table, parent, rows) -> None:
        for position, row in enumerate(rows):
            iid = f"{parent or 'root'}_{position}"
            table.insert(parent, "end", iid=iid, text=str(row.label),
                         values=[str(cell) for cell in row.cells],
                         open=bool(row.expanded))
            self._tree_keys[iid] = row.detail_key
            if row.children:
                self._insert_tree(table, iid, row.children)

    def _refresh_controls(self, report) -> None:
        """Follow the data: a filter's choices change with the trace, so the combobox must too.

        Writing a StringVar does not raise <<ComboboxSelected>> (Tk raises that only for a
        user's pick) nor <Return>/<FocusOut>, so this cannot re-enter the rebuild that called it.
        """
        for control in report.controls:
            var = self.controls.get(control.key)
            widget = self.control_widgets.get(control.key)
            if var is None:
                continue
            if hasattr(control, "choices"):
                choices = list(control.choices)
                if widget is not None:
                    widget["values"] = choices
                if var.get() not in choices:
                    var.set(str(control.value) if str(control.value) in choices
                            else (choices[0] if choices else ""))
            elif var.get() != str(control.value):
                var.set(str(control.value))

    # ---- master/detail --------------------------------------------------------------------
    def selected_key(self):
        """The detail key of the selected row: its index in a table, its node key in a tree."""
        table = self.table
        if table is None:
            return None
        selection = table.selection()
        if not selection:
            return None
        iid = str(selection[0])
        if self.report is not None and self.report.tree is not None:
            return self._tree_keys.get(iid)
        try:
            return int(iid)
        except ValueError:
            return None

    def select_key(self, key) -> None:
        """Select the row or node carrying `key`, falling back to the first row."""
        table = self.table
        if table is None or self.report is None:
            return
        if key is not None:
            if self.report.tree is not None:
                for iid, node_key in self._tree_keys.items():
                    if node_key == key:
                        table.selection_set(iid)
                        table.see(iid)
                        self.refresh_detail()
                        return
            elif isinstance(key, int) and 0 <= key < len(self.report.rows):
                self.select_row(key)
                return
        self.select_row(0)

    def select_row(self, index: int) -> None:
        """Select master row `index` (a table row, or the index-th node that carries a key).

        Selecting is this method's job whether or not there IS a detail view: a report without
        one still opens on a row, and its verbs act on whatever is selected (bugs/0897).
        """
        table = self.table
        if table is None or self.report is None:
            return
        if self.report.tree is not None:
            nodes = [iid for iid, key in self._tree_keys.items() if key is not None]
            if not nodes:
                self._show_detail(None)
                return
            index = max(0, min(int(index), len(nodes) - 1))
            table.selection_set(nodes[index])
            table.see(nodes[index])
            # <<TreeviewSelect>> is delivered through the event loop, so show the detail here
            # too: a caller that selects a row must not have to pump Tk to see it
            self.refresh_detail()
            return
        if not self.report.rows:
            self._show_detail(None)
            return
        index = max(0, min(int(index), len(self.report.rows) - 1))
        table.selection_set(str(index))
        table.focus(str(index))
        table.see(str(index))
        self.refresh_detail()

    def refresh_detail(self) -> None:
        """Show the detail of whatever is selected -- what a selection change calls."""
        self._show_detail(self.selected_key())

    def _show_detail(self, key) -> None:
        report = self.report
        if report is None:
            return
        if self.detail_table is not None and report.detail is not None:
            self.detail_table.delete(*self.detail_table.get_children())
            if key is None:
                return
            for index, row in enumerate(report.detail.rows(key)):
                self.detail_table.insert("", "end", iid=str(index),
                                         values=[str(cell) for cell in row])
            return
        if self.detail_widget is not None and report.detail_text is not None:
            text = report.detail_text.empty if key is None else report.detail_text.text(key)
            widget = self.detail_widget
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", str(text or ""))
            widget.configure(state="disabled")

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
            path = filedialog.asksaveasfilename(
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
            messagebox.showinfo(f"Export {report.title}",
                                "No data. Click Update first.", parent=self.editor)
            return ""
        path = filedialog.asksaveasfilename(
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
