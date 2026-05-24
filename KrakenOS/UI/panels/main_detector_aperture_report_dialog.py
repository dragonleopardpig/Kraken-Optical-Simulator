"""Detector aperture report dialog."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.detector_aperture_analysis import (
    DETECTOR_APERTURE_TABLE_COLUMNS,
    DETECTOR_APERTURE_TABLE_HEADINGS,
    DETECTOR_APERTURE_TABLE_LAYOUT,
    detector_aperture_report_text,
    detector_aperture_summary_text,
    detector_aperture_table_values,
    write_detector_aperture_csv,
)


class MainDetectorApertureReportDialog:
    """Own the Detector Aperture Report window while delegating sample collection to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_detector_aperture_report(self) -> None:
        window = self._detector_aperture_window
        if window is not None and window.winfo_exists():
            self._refresh_detector_aperture_report()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Detector Aperture Report")
        window.geometry("1160x520")
        window.minsize(860, 340)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_detector_aperture_report)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_detector_aperture_report).pack(side="left")
        ttk.Button(toolbar, text="Copy", command=self.copy_detector_aperture_report_to_clipboard).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_detector_aperture_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_detector_aperture_report).pack(side="left", padx=(6, 0))

        self._detector_aperture_summary_var = tk.StringVar(master=window, value="No detector aperture data. Click Update.")
        ttk.Label(
            window,
            textvariable=self._detector_aperture_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        table_frame = ttk.Frame(window, padding=8)
        table_frame.grid(row=2, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        table = ttk.Treeview(table_frame, columns=DETECTOR_APERTURE_TABLE_COLUMNS, show="headings", selectmode="browse")
        for column, heading in DETECTOR_APERTURE_TABLE_HEADINGS.items():
            table.heading(column, text=heading)
        for column, width, anchor in DETECTOR_APERTURE_TABLE_LAYOUT:
            table.column(column, width=width, anchor=anchor, stretch=column in {"detector", "dominant"})
        table.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=table.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=table.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        table.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        self._detector_aperture_window = window
        self._detector_aperture_table = table
        self._show_centered_dialog(window)
        self._refresh_detector_aperture_report()

    def _close_detector_aperture_report(self) -> None:
        window = self._detector_aperture_window
        self._detector_aperture_window = None
        self._detector_aperture_summary_var = None
        self._detector_aperture_table = None
        self._detector_aperture_records = []
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_detector_aperture_report_if_open(self) -> None:
        window = self._detector_aperture_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_detector_aperture_report()
            return
        self._refresh_detector_aperture_report()

    def _refresh_detector_aperture_report(self) -> None:
        table = self._detector_aperture_table
        if table is None:
            return
        records = self._collect_detector_aperture_records(ray_records=self._active_ray_analysis_records())
        self._detector_aperture_records = records
        table.delete(*table.get_children())
        if self._detector_aperture_summary_var is not None:
            self._detector_aperture_summary_var.set(detector_aperture_summary_text(records))
        for index, record in enumerate(records):
            table.insert(
                "",
                "end",
                iid=str(index),
                values=detector_aperture_table_values(record),
            )

    def _detector_aperture_report_text(self) -> str:
        records = list(self.__dict__.get("_detector_aperture_records", []) or [])
        if not records:
            records = self._collect_detector_aperture_records(ray_records=self._active_ray_analysis_records())
        return detector_aperture_report_text(records)

    def copy_detector_aperture_report_to_clipboard(self) -> None:
        try:
            text = self._detector_aperture_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Detector aperture report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Detector aperture report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Detector aperture report failed: {exc}")

    def export_detector_aperture_csv(self) -> None:
        records = list(self._detector_aperture_records or self._collect_detector_aperture_records(ray_records=self._active_ray_analysis_records()))
        if not records:
            messagebox.showinfo("Export Detector Aperture", "No detector aperture data. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Detector Aperture CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        write_detector_aperture_csv(path, records)
        self.status_var.set(f"Detector aperture CSV exported: {Path(path).name}")
