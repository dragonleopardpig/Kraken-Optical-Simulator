"""Branch Gaussian q report dialog."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.branch_gaussian_q_report import (
    BRANCH_GAUSSIAN_Q_CSV_COLUMNS,
    branch_gaussian_q_report_text,
    branch_gaussian_q_table_values,
)


class MainBranchGaussianQDialog:
    """Own the Branch Gaussian Q report window while delegating q-record collection to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_branch_gaussian_q_report(self) -> None:
        window = self._branch_gaussian_q_window
        if window is not None and window.winfo_exists():
            self._refresh_branch_gaussian_q_report()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Branch Gaussian Q Report")
        window.geometry("1320x620")
        window.minsize(900, 420)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_branch_gaussian_q_report)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_branch_gaussian_q_report).pack(side="left")
        ttk.Button(toolbar, text="Copy", command=self.copy_branch_gaussian_q_report_to_clipboard).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_branch_gaussian_q_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_branch_gaussian_q_report).pack(side="left", padx=(6, 0))

        self._branch_gaussian_q_summary_var = tk.StringVar(master=window, value="No trace data. Click Update first.")
        ttk.Label(
            window,
            textvariable=self._branch_gaussian_q_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        frame = ttk.Frame(window, padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = (
            "ray",
            "path",
            "step",
            "surface",
            "event",
            "note",
            "incidence",
            "n",
            "ct",
            "cs",
            "qt",
            "qs",
            "w",
            "clip",
            "stable",
        )
        table = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        headings = {
            "ray": "Ray",
            "path": "Path",
            "step": "Step",
            "surface": "Surface",
            "event": "Event",
            "note": "q note",
            "incidence": "Inc [deg]",
            "n": "n0->n1",
            "ct": "Ct",
            "cs": "Cs",
            "qt": "qT [mm]",
            "qs": "qS [mm]",
            "w": "wT/wS [mm]",
            "clip": "Clip",
            "stable": "Stable",
        }
        widths = {
            "ray": 58,
            "path": 130,
            "step": 55,
            "surface": 150,
            "event": 92,
            "note": 240,
            "incidence": 78,
            "n": 80,
            "ct": 90,
            "cs": 90,
            "qt": 150,
            "qs": 150,
            "w": 120,
            "clip": 76,
            "stable": 70,
        }
        for column in columns:
            table.heading(column, text=headings[column])
            table.column(column, width=widths[column], anchor=("w" if column in {"path", "surface", "event", "note"} else "e"), stretch=column in {"path", "surface", "note"})
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=table.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=table.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self._branch_gaussian_q_window = window
        self._branch_gaussian_q_table = table
        self._show_centered_dialog(window)
        self._refresh_branch_gaussian_q_report()

    def _close_branch_gaussian_q_report(self) -> None:
        window = self._branch_gaussian_q_window
        self._branch_gaussian_q_window = None
        self._branch_gaussian_q_summary_var = None
        self._branch_gaussian_q_table = None
        self._branch_gaussian_q_records = []
        self._branch_gaussian_q_summary = {}
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_branch_gaussian_q_report_if_open(self) -> None:
        window = self._branch_gaussian_q_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_branch_gaussian_q_report()
            return
        self._refresh_branch_gaussian_q_report()

    def _refresh_branch_gaussian_q_report(self) -> None:
        table = self._branch_gaussian_q_table
        if table is None:
            return
        rows, summary = self._collect_branch_gaussian_q_records(records=self._active_ray_analysis_records())
        self._branch_gaussian_q_records = rows
        self._branch_gaussian_q_summary = summary
        table.delete(*table.get_children())
        for index, row in enumerate(rows):
            table.insert("", "end", iid=str(index), values=branch_gaussian_q_table_values(row))
        if self._branch_gaussian_q_summary_var is not None:
            self._branch_gaussian_q_summary_var.set(
                self._branch_gaussian_q_summary_text(summary)
                if rows or int(summary.get("failure_count", 0) or 0)
                else "No Gaussian q branch records. Click Update first."
            )

    def _branch_gaussian_q_report_text(self) -> str:
        rows = list(self.__dict__.get("_branch_gaussian_q_records", []) or [])
        summary = dict(self.__dict__.get("_branch_gaussian_q_summary", {}) or {})
        if not rows and not summary:
            rows, summary = self._collect_branch_gaussian_q_records(records=self._active_ray_analysis_records())
        return branch_gaussian_q_report_text(rows, summary)

    def copy_branch_gaussian_q_report_to_clipboard(self) -> None:
        try:
            text = self._branch_gaussian_q_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Branch Gaussian q report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Branch Gaussian q report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Branch Gaussian q report failed: {exc}")

    def export_branch_gaussian_q_csv(self) -> None:
        rows = list(self._branch_gaussian_q_records)
        if not rows:
            rows, summary = self._collect_branch_gaussian_q_records(records=self._active_ray_analysis_records())
            self._branch_gaussian_q_records = rows
            self._branch_gaussian_q_summary = summary
        if not rows:
            messagebox.showinfo("Export Branch Gaussian Q", "No Gaussian q branch records. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Branch Gaussian Q CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=BRANCH_GAUSSIAN_Q_CSV_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        self.status_var.set(f"Branch Gaussian q CSV exported: {Path(path).name}")
