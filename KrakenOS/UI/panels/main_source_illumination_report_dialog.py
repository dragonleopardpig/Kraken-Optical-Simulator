"""Source illumination report dialog."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.source_illumination_analysis import (
    SOURCE_ILLUMINATION_TABLE_COLUMNS,
    SOURCE_ILLUMINATION_TABLE_HEADINGS,
    SOURCE_ILLUMINATION_TABLE_WIDTHS,
    source_illumination_record_detail_text,
    source_illumination_report_text,
    source_illumination_summary_text,
    source_illumination_table_values,
    write_source_illumination_csv,
)


class MainSourceIlluminationReportDialog:
    """Own the Source Illumination Report window while delegating target/sample logic to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_source_illumination_report(self) -> None:
        window = self._source_illumination_window
        if window is not None and window.winfo_exists():
            self._refresh_source_illumination_report()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.title("Source Illumination Report")
        window.geometry("1160x600")
        window.protocol("WM_DELETE_WINDOW", self._close_source_illumination_report)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 4))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(toolbar, text="Target").pack(side="left")
        default_target = "Auto"
        self._source_illumination_target_var = tk.StringVar(master=window, value=default_target)
        self._source_illumination_target_menu = ttk.Combobox(
            toolbar,
            textvariable=self._source_illumination_target_var,
            values=self._source_illumination_target_choices(),
            state="readonly",
            width=28,
        )
        self._source_illumination_target_menu.pack(side="left", padx=(6, 10))
        self._source_illumination_target_menu.bind("<<ComboboxSelected>>", lambda _event: self._refresh_source_illumination_report(), add="+")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_source_illumination_report).pack(side="left")
        ttk.Button(toolbar, text="Copy", command=self.copy_source_illumination_report_to_clipboard).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_source_illumination_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_source_illumination_report).pack(side="left", padx=(6, 0))

        self._source_illumination_summary_var = tk.StringVar(master=window, value="No trace data. Click Update.")
        ttk.Label(window, textvariable=self._source_illumination_summary_var, padding=(8, 0, 8, 4)).grid(row=1, column=0, sticky="ew")

        columns = SOURCE_ILLUMINATION_TABLE_COLUMNS
        table = ttk.Treeview(window, columns=columns, show="headings", selectmode="browse")
        for column in columns:
            table.heading(column, text=SOURCE_ILLUMINATION_TABLE_HEADINGS[column])
            table.column(
                column,
                width=SOURCE_ILLUMINATION_TABLE_WIDTHS[column],
                anchor=("e" if column not in {"source", "model", "loss", "centroid", "span"} else "w"),
            )
        table.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        yscroll = ttk.Scrollbar(window, orient="vertical", command=table.yview)
        yscroll.grid(row=2, column=1, sticky="ns", pady=(0, 8))
        table.configure(yscrollcommand=yscroll.set)
        table.bind("<<TreeviewSelect>>", lambda _event: self._refresh_source_illumination_detail(), add="+")

        detail_frame = ttk.LabelFrame(window, text="Selected source details", padding=(8, 6, 8, 8))
        detail_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))
        detail_frame.columnconfigure(0, weight=1)
        detail_text = tk.Text(detail_frame, height=6, wrap="word", borderwidth=0, relief="flat")
        detail_text.grid(row=0, column=0, sticky="ew")
        detail_text.configure(state="disabled")
        self._bind_text_copy_shortcuts(detail_text)
        self._bind_text_context_menu(detail_text)

        self._source_illumination_window = window
        self._source_illumination_table = table
        self._source_illumination_detail_text = detail_text
        self._refresh_source_illumination_report()

    def _close_source_illumination_report(self) -> None:
        window = self._source_illumination_window
        self._source_illumination_window = None
        self._source_illumination_summary_var = None
        self._source_illumination_target_var = None
        self._source_illumination_target_menu = None
        self._source_illumination_table = None
        self._source_illumination_detail_text = None
        self._source_illumination_records = []
        if window is not None:
            try:
                window.destroy()
            except tk.TclError:
                pass

    def _set_source_illumination_detail_text(self, text: str) -> None:
        widget = self._source_illumination_detail_text
        if widget is None:
            return
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", str(text or ""))
        widget.configure(state="disabled")

    def _source_illumination_record_detail_text(self, record: dict[str, object]) -> str:
        return source_illumination_record_detail_text(record)

    def _refresh_source_illumination_detail(self) -> None:
        table = self._source_illumination_table
        if table is None:
            return
        selection = table.selection()
        if not selection:
            self._set_source_illumination_detail_text("Select a source row to inspect loss and footprint diagnostics.")
            return
        try:
            index = int(str(selection[0]).rsplit("_", 1)[-1])
        except Exception:
            index = -1
        if not (0 <= index < len(self._source_illumination_records)):
            self._set_source_illumination_detail_text("Selected source record is no longer available. Click Refresh.")
            return
        self._set_source_illumination_detail_text(
            self._source_illumination_record_detail_text(self._source_illumination_records[index])
        )

    def _refresh_source_illumination_report_if_open(self) -> None:
        window = self._source_illumination_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_source_illumination_report()
            return
        self._refresh_source_illumination_report()

    def _refresh_source_illumination_report(self) -> None:
        table = self._source_illumination_table
        if table is None:
            return
        if self._source_illumination_target_menu is not None:
            self._source_illumination_target_menu["values"] = self._source_illumination_target_choices()
        target_index = self._source_illumination_target_index()
        records = self._collect_source_illumination_records(
            target_index,
            ray_records=self._active_ray_analysis_records(),
        )
        self._source_illumination_records = records
        table.delete(*table.get_children())
        target_label = "None" if target_index is None else f"S{target_index}: {self.rows[target_index].name}"
        if self._source_illumination_summary_var is not None:
            self._source_illumination_summary_var.set(source_illumination_summary_text(records, target_label))
        for index, record in enumerate(records):
            table.insert(
                "",
                "end",
                iid=f"source_illum_{index}",
                values=source_illumination_table_values(record),
            )
        if records:
            first_iid = "source_illum_0"
            table.selection_set(first_iid)
            table.focus(first_iid)
            self._refresh_source_illumination_detail()
        else:
            self._set_source_illumination_detail_text(
                "No source illumination records. Click Update, then choose a target surface or leave Target as Auto."
            )

    def _source_illumination_report_text(self) -> str:
        target_index = self._source_illumination_target_index()
        records = self._collect_source_illumination_records(
            target_index,
            ray_records=self._active_ray_analysis_records(),
        )
        if target_index is None:
            target_label = "None"
        else:
            target_label = f"S{target_index}: {self.rows[target_index].name}"
        return source_illumination_report_text(records, target_label)

    def copy_source_illumination_report_to_clipboard(self) -> None:
        try:
            text = self._source_illumination_report_text()
            ok, backend = self._copy_text_to_clipboard(text)
            self.append_debug(text)
            if ok:
                self.status_var.set(f"Source illumination report copied to clipboard ({backend}).")
            else:
                self.status_var.set("Source illumination report written to Debug; clipboard unavailable.")
        except Exception as exc:
            self.append_debug(f"Source illumination report failed: {exc}")

    def export_source_illumination_csv(self) -> None:
        target_index = self._source_illumination_target_index()
        records = self._collect_source_illumination_records(
            target_index,
            ray_records=self._active_ray_analysis_records(),
        )
        if not records:
            messagebox.showinfo("Export Source Illumination", "No source illumination records. Click Update first.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Source Illumination CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        write_source_illumination_csv(path, records)
        self.status_var.set(f"Source illumination CSV exported: {Path(path).name}")
