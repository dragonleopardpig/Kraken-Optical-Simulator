"""Path throughput report dialog."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.branch_throughput_analysis import (
    BRANCH_THROUGHPUT_TABLE_COLUMNS,
    BRANCH_THROUGHPUT_TABLE_HEADINGS,
    BRANCH_THROUGHPUT_TABLE_LAYOUT,
    branch_throughput_report_text,
    branch_throughput_summary_text,
    branch_throughput_table_values,
    filtered_branch_throughput_records,
    normalize_branch_throughput_filter_label as _normalize_path_filter_label,
    write_branch_throughput_csv,
)


class MainBranchThroughputReportDialog:
    """Own the Path Throughput Report window while delegating path analysis to the editor."""

    def __init__(self, editor: Any, *, analysis_path_filter_default: str) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "analysis_path_filter_default", analysis_path_filter_default)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "analysis_path_filter_default"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_branch_throughput_report(self) -> None:
        window = self._branch_throughput_window
        if window is not None and window.winfo_exists():
            self._refresh_branch_throughput_report()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Path Throughput Report")
        window.geometry("1120x560")
        window.minsize(820, 360)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_branch_throughput_report)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_branch_throughput_report).pack(side="left")
        ttk.Button(toolbar, text="Copy", command=self.copy_branch_throughput_report_to_clipboard).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_branch_throughput_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_branch_throughput_report).pack(side="left", padx=(6, 0))
        ttk.Label(toolbar, text="Filter").pack(side="left", padx=(18, 4))
        self._branch_throughput_filter_var = tk.StringVar(master=window, value=self.analysis_path_filter_default)
        self._branch_throughput_filter_menu = ttk.Combobox(
            toolbar,
            textvariable=self._branch_throughput_filter_var,
            state="readonly",
            width=36,
            values=[self.analysis_path_filter_default],
        )
        self._branch_throughput_filter_menu.pack(side="left")
        self._branch_throughput_filter_menu.bind("<<ComboboxSelected>>", lambda _event: self._refresh_branch_throughput_report(), add="+")

        self._branch_throughput_summary_var = tk.StringVar(master=window, value="No trace data. Click Update.")
        ttk.Label(
            window,
            textvariable=self._branch_throughput_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        table_frame = ttk.Frame(window, padding=8)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        columns = BRANCH_THROUGHPUT_TABLE_COLUMNS
        table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for column, heading in BRANCH_THROUGHPUT_TABLE_HEADINGS.items():
            table.heading(column, text=heading)
        for column, width, anchor in BRANCH_THROUGHPUT_TABLE_LAYOUT:
            table.column(column, width=width, anchor=anchor, stretch=column in {"terminal", "path"})
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self._branch_throughput_window = window
        self._branch_throughput_table = table
        self._show_centered_dialog(window)
        self._refresh_branch_throughput_report()

    def _close_branch_throughput_report(self) -> None:
        window = self._branch_throughput_window
        self._branch_throughput_window = None
        self._branch_throughput_summary_var = None
        self._branch_throughput_filter_var = None
        self._branch_throughput_filter_menu = None
        self._branch_throughput_table = None
        self._branch_throughput_records = []
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_branch_throughput_report_if_open(self) -> None:
        window = self._branch_throughput_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_branch_throughput_report()
            return
        self._refresh_branch_throughput_report()

    def _refresh_branch_throughput_report(self) -> None:
        table = self._branch_throughput_table
        if table is None:
            return
        all_records = self._collect_branch_throughput_records(ray_records=self._active_ray_analysis_records())
        choices = self._branch_throughput_filter_choices(all_records)
        if self._branch_throughput_filter_menu is not None:
            self._branch_throughput_filter_menu["values"] = choices
        if self._branch_throughput_filter_var is not None:
            current_filter = _normalize_path_filter_label(self._branch_throughput_filter_var.get())
            if current_filter not in choices:
                self._branch_throughput_filter_var.set(self.analysis_path_filter_default)
        filter_text = self._current_branch_throughput_filter()
        records = filtered_branch_throughput_records(all_records, filter_text)
        self._branch_throughput_records = records
        table.delete(*table.get_children())
        if self._branch_throughput_summary_var is not None:
            self._branch_throughput_summary_var.set(branch_throughput_summary_text(records, all_records, filter_text))
        for index, record in enumerate(records):
            table.insert(
                "",
                "end",
                iid=str(index),
                values=branch_throughput_table_values(record),
            )

    def _current_branch_throughput_filter(self) -> str:
        filter_var = self.__dict__.get("_branch_throughput_filter_var")
        return (
            _normalize_path_filter_label(filter_var.get())
            if filter_var is not None
            else self.analysis_path_filter_default
        )

    def _filtered_branch_throughput_records_for_dialog(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        return filtered_branch_throughput_records(records, self._current_branch_throughput_filter())

    def _branch_throughput_report_text(self) -> str:
        all_records = self._collect_branch_throughput_records(ray_records=self._active_ray_analysis_records())
        records = self._filtered_branch_throughput_records_for_dialog(all_records)
        filter_text = self._current_branch_throughput_filter()
        return branch_throughput_report_text(records, all_records, filter_text)

    def copy_branch_throughput_report_to_clipboard(self) -> None:
        try:
            text = self._branch_throughput_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Path throughput report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Path throughput report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Path throughput report failed: {exc}")

    def export_branch_throughput_csv(self) -> None:
        records = self._filtered_branch_throughput_records_for_dialog(
            self._collect_branch_throughput_records(ray_records=self._active_ray_analysis_records())
        )
        if not records:
            messagebox.showinfo("Export Path Throughput", "No path throughput data. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Path Throughput CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        write_branch_throughput_csv(path, records)
        self.status_var.set(f"Path throughput CSV exported: {Path(path).name}")
