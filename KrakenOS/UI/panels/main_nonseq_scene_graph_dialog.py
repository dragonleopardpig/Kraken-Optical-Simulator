"""Non-sequential scene graph dialog."""

from __future__ import annotations

import csv
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any

from KrakenOS.UI.scene_row_mapping import SOURCE_ROW_ORDER_DEFAULT, normalize_source_row_order


class MainNonSequentialSceneGraphDialog:
    """Own the Non-Sequential Scene Graph window while delegating records to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_nonseq_scene_graph(self) -> None:
        window = self._nonseq_scene_window
        if window is not None and window.winfo_exists():
            self._refresh_nonseq_scene_graph()
            window.deiconify()
            window.lift()
            window.focus_force()
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Non-Sequential Scene Graph")
        window.geometry("1180x620")
        window.minsize(860, 420)
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self._close_nonseq_scene_graph)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 0))
        toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Button(toolbar, text="Refresh", command=self._refresh_nonseq_scene_graph).pack(side="left")
        ttk.Button(toolbar, text="Select Row", command=self._select_nonseq_scene_row).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Set Target", command=self._set_nonseq_scene_target).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Edit Target", command=self.open_scene_target_editor).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Export CSV", command=self.export_nonseq_scene_graph_csv).pack(side="left", padx=(6, 0))
        ttk.Button(toolbar, text="Close", command=self._close_nonseq_scene_graph).pack(side="left", padx=(6, 0))

        self._nonseq_scene_summary_var = tk.StringVar(master=window, value="")
        ttk.Label(
            window,
            textvariable=self._nonseq_scene_summary_var,
            padding=(8, 6, 8, 0),
            anchor="w",
            justify="left",
        ).grid(row=1, column=0, sticky="ew")

        frame = ttk.Frame(window, padding=8)
        frame.grid(row=2, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("scene_row", "row", "trace_surface", "source_id", "kind", "surface", "material", "features", "target", "detail")
        tree = ttk.Treeview(frame, columns=columns, show="tree headings", selectmode="browse")
        tree.heading("#0", text="Node")
        for column, heading in (
            ("scene_row", "Scene Row"),
            ("row", "Table Row"),
            ("trace_surface", "Trace Surf"),
            ("source_id", "Source ID"),
            ("kind", "Kind"),
            ("surface", "Surface / mode"),
            ("material", "Material"),
            ("features", "Features"),
            ("target", "Target"),
            ("detail", "Detail"),
        ):
            tree.heading(column, text=heading)
        tree.column("#0", width=220, anchor="w", stretch=False)
        tree.column("scene_row", width=86, anchor="center", stretch=False)
        tree.column("row", width=76, anchor="center", stretch=False)
        tree.column("trace_surface", width=76, anchor="center", stretch=False)
        tree.column("source_id", width=120, anchor="w", stretch=False)
        tree.column("kind", width=116, anchor="w", stretch=False)
        tree.column("surface", width=130, anchor="w", stretch=False)
        tree.column("material", width=115, anchor="w", stretch=False)
        tree.column("features", width=220, anchor="w", stretch=True)
        tree.column("target", width=100, anchor="w", stretch=False)
        tree.column("detail", width=360, anchor="w", stretch=True)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        tree.bind("<Double-1>", lambda _event: self._select_nonseq_scene_row(), add="+")

        self._nonseq_scene_window = window
        self._nonseq_scene_table = tree
        self._show_centered_dialog(window)
        self._refresh_nonseq_scene_graph()

    def _close_nonseq_scene_graph(self) -> None:
        window = self._nonseq_scene_window
        self._nonseq_scene_window = None
        self._nonseq_scene_summary_var = None
        self._nonseq_scene_table = None
        self._nonseq_scene_records = []
        if window is not None and window.winfo_exists():
            window.destroy()

    def _refresh_nonseq_scene_graph_if_open(self) -> None:
        window = self._nonseq_scene_window
        if window is None:
            return
        if not window.winfo_exists():
            self._close_nonseq_scene_graph()
            return
        self._refresh_nonseq_scene_graph()

    def _refresh_nonseq_scene_graph(self) -> None:
        tree = self._nonseq_scene_table
        if tree is None:
            return
        selected = tree.selection()
        selected_iid = selected[0] if selected else None
        records = self._collect_nonseq_scene_graph_records()
        self._nonseq_scene_records = records
        tree.delete(*tree.get_children())
        for record in records:
            parent = str(record.get("parent", ""))
            iid = str(record.get("id", ""))
            if parent and not tree.exists(parent):
                parent = ""
            tree.insert(
                parent,
                "end",
                iid=iid,
                text=str(record.get("text", "")),
                values=(
                    record.get("scene_row", ""),
                    record.get("row", ""),
                    record.get("trace_surface", ""),
                    record.get("source_id", ""),
                    record.get("kind", ""),
                    record.get("surface", ""),
                    record.get("material", ""),
                    record.get("features", ""),
                    record.get("target", ""),
                    record.get("detail", ""),
                ),
                open=True,
            )
        if selected_iid and tree.exists(selected_iid):
            tree.selection_set(selected_iid)
            tree.focus(selected_iid)
            tree.see(selected_iid)
        elif records:
            first_surface = next((str(record["id"]) for record in records if str(record.get("id", "")).startswith("surface:")), str(records[0]["id"]))
            tree.selection_set(first_surface)
            tree.focus(first_surface)
            tree.see(first_surface)
        if self._nonseq_scene_summary_var is not None:
            target_index = self._current_nonseq_target_surface_index()
            target_text = "Auto image/termination target" if target_index is None else f"S{target_index}: {self.rows[target_index].name}"
            volume_count = sum(1 for record in records if str(record.get("kind", "")) == "OpticalVolume")
            boundary_count = sum(1 for record in records if str(record.get("kind", "")) == "BoundaryFace")
            target_count = sum(1 for record in records if str(record.get("kind", "")) == "SceneTarget")
            detector_count = sum(
                1
                for record in records
                if str(record.get("kind", "")) == "SceneTarget" and "detector" in str(record.get("features", "")).lower()
            )
            self._nonseq_scene_summary_var.set(
                "KrakenOS non-sequential scene = scene source records + ordered SDT surface/object list. "
                f"Scene rows={len(self._current_scene_row_mapping().records)} "
                f"({normalize_source_row_order(getattr(self, 'layout_scene_row_order', SOURCE_ROW_ORDER_DEFAULT))}) | "
                f"surface rows={len(self.rows)} | targets={target_count} ({detector_count} detectors) | "
                f"optical volumes={volume_count} | boundary faces={boundary_count} | "
                f"target={target_text} | trace paths are shown in Trace Path Inspector."
            )

    def _nonseq_scene_selected_record(self) -> dict[str, object] | None:
        tree = self._nonseq_scene_table
        if tree is None:
            return None
        selected = tree.selection()
        if not selected:
            return None
        iid = str(selected[0])
        for record in self._nonseq_scene_records:
            if str(record.get("id", "")) == iid:
                return record
        return None

    def _select_nonseq_scene_row(self) -> None:
        record = self._nonseq_scene_selected_record()
        if record is None:
            return
        row_index = record.get("row_index")
        try:
            index = int(row_index)
        except Exception:
            return
        if 0 <= index < len(self.rows):
            if str(record.get("id", "")).startswith("element:"):
                indices = self._element_indices_for_index(self.rows, index)
                self._select_table_indices(indices, focus_index=index)
            else:
                self._select_table_indices([index], focus_index=index)
            self.status_var.set(f"Selected row {index}: {self.rows[index].name}")

    def _set_nonseq_scene_target(self) -> None:
        record = self._nonseq_scene_selected_record()
        if record is None:
            return
        row_index = record.get("row_index")
        try:
            index = int(row_index)
        except Exception:
            return
        if not (0 <= index < len(self.rows)):
            return
        self._begin_history_capture()
        self._refresh_analysis_surface_choices()
        self.nonseq_target_surface_var.set(f"{index}: {self.rows[index].name}")
        if hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
        self._commit_history_capture()
        self._refresh_nonseq_scene_graph()
        self._mark_plot_update_pending()
        self.status_var.set(f"Non-sequential target set to row {index}: {self.rows[index].name}")

    def export_nonseq_scene_graph_csv(self) -> None:
        records = list(self._nonseq_scene_records or self._collect_nonseq_scene_graph_records())
        if not records:
            messagebox.showinfo("Export Non-Sequential Scene Graph", "No scene graph data to export.", parent=self.editor)
            return
        path = filedialog.asksaveasfilename(
            title="Export Non-Sequential Scene Graph CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*")],
            parent=self.editor,
        )
        if not path:
            return
        columns = (
            "id",
            "parent",
            "text",
            "scene_row",
            "row",
            "trace_surface",
            "source_id",
            "kind",
            "surface",
            "material",
            "features",
            "target",
            "detail",
            "row_index",
        )
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            for record in records:
                writer.writerow({column: record.get(column, "") for column in columns})
        self.status_var.set(f"Non-sequential scene graph CSV exported: {Path(path).name}")

