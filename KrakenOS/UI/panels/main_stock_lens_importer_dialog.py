"""Stock lens importer dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import numpy as np


class MainStockLensImporterDialog:
    """Own the stock lens importer UI while delegating layout mutations to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        available_stock_lens_catalogs: Callable[[], dict[str, Any]],
        load_stock_lens_catalog: Callable[[Any], dict[str, Any]],
        stock_lens_summary: Callable[[str, Any], dict[str, Any]],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "available_stock_lens_catalogs", available_stock_lens_catalogs)
        object.__setattr__(self, "load_stock_lens_catalog", load_stock_lens_catalog)
        object.__setattr__(self, "stock_lens_summary", stock_lens_summary)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "available_stock_lens_catalogs",
            "load_stock_lens_catalog",
            "stock_lens_summary",
            "short_error_message",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_stock_lens_importer(self, *, path_placement: dict[str, object] | None = None) -> None:
        catalogs = self.available_stock_lens_catalogs()
        if not catalogs:
            messagebox.showerror(
                "Import Stock Lens",
                "No Edmund/Thorlabs .ZMF catalogs were found in attachment/ or KrakenOS/LensCat.",
                parent=self.editor,
            )
            return
        path_placement = dict(path_placement or {})
        path_mode = bool(path_placement)

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Add Stock Lens to Path" if path_mode else "Import Stock Lens")
        window.geometry("980x620")
        window.minsize(760, 460)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        state: dict[str, object] = {"catalog": {}, "summaries": []}
        header = ttk.Frame(window, padding=(10, 10, 10, 6))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        header.columnconfigure(3, weight=1)

        ttk.Label(header, text="Catalog").grid(row=0, column=0, sticky="w", padx=(0, 8))
        catalog_var = tk.StringVar(master=window, value=next(iter(catalogs)))
        catalog_menu = ttk.Combobox(
            header,
            textvariable=catalog_var,
            values=tuple(catalogs.keys()),
            state="readonly",
            width=34,
        )
        catalog_menu.grid(row=0, column=1, sticky="ew", padx=(0, 14))
        ttk.Label(header, text="Search").grid(row=0, column=2, sticky="w", padx=(0, 8))
        search_var = tk.StringVar(master=window, value="")
        search_entry = ttk.Entry(header, textvariable=search_var)
        search_entry.grid(row=0, column=3, sticky="ew")

        catalog_info_var = tk.StringVar(master=window, value="")
        ttk.Label(header, textvariable=catalog_info_var, foreground="#5f6b7a").grid(
            row=1, column=0, columnspan=4, sticky="w", pady=(6, 0)
        )

        body = ttk.Frame(window, padding=(10, 0, 10, 6))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            body,
            columns=("part", "description", "surfaces", "diameter"),
            show="headings",
            selectmode="browse",
        )
        tree.heading("part", text="Part")
        tree.heading("description", text="Description")
        tree.heading("surfaces", text="Surf")
        tree.heading("diameter", text="Dia mm")
        tree.column("part", width=130, stretch=False)
        tree.column("description", width=620, stretch=True)
        tree.column("surfaces", width=58, stretch=False, anchor="e")
        tree.column("diameter", width=76, stretch=False, anchor="e")
        tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=tree_scroll.set)

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(6, weight=1)
        inverse_var = tk.BooleanVar(master=window, value=False)
        ttk.Checkbutton(footer, text="Reverse element", variable=inverse_var).grid(row=0, column=0, sticky="w")
        ttk.Label(footer, text="Gap after").grid(row=0, column=1, sticky="w", padx=(14, 6))
        gap_after_var = tk.StringVar(master=window, value="25.0")
        ttk.Entry(footer, textvariable=gap_after_var, width=10).grid(row=0, column=2, sticky="w")
        ttk.Label(footer, text="mm").grid(row=0, column=3, sticky="w", padx=(4, 14))
        distance_var = tk.StringVar(master=window, value="60.0")
        local_decenter_x_var = tk.StringVar(master=window, value="0")
        local_decenter_y_var = tk.StringVar(master=window, value="0")
        local_tilt_x_var = tk.StringVar(master=window, value="0")
        local_tilt_y_var = tk.StringVar(master=window, value="0")
        local_tilt_z_var = tk.StringVar(master=window, value="0")
        if path_mode:
            ttk.Label(footer, text="Path distance").grid(row=0, column=4, sticky="w", padx=(4, 6))
            ttk.Entry(footer, textvariable=distance_var, width=10).grid(row=0, column=5, sticky="w")
            ttk.Label(footer, text="mm").grid(row=0, column=6, sticky="w", padx=(4, 14))
            ttk.Label(footer, text="Local X").grid(row=1, column=0, sticky="w", padx=(0, 6), pady=(6, 0))
            ttk.Entry(footer, textvariable=local_decenter_x_var, width=8).grid(row=1, column=1, sticky="w", pady=(6, 0))
            ttk.Label(footer, text="Local Y").grid(row=1, column=2, sticky="w", padx=(8, 6), pady=(6, 0))
            ttk.Entry(footer, textvariable=local_decenter_y_var, width=8).grid(row=1, column=3, sticky="w", pady=(6, 0))
            ttk.Label(footer, text="Tilt X/Y/Z").grid(row=1, column=4, sticky="w", padx=(8, 6), pady=(6, 0))
            tilt_frame = ttk.Frame(footer)
            tilt_frame.grid(row=1, column=5, columnspan=3, sticky="w", pady=(6, 0))
            ttk.Entry(tilt_frame, textvariable=local_tilt_x_var, width=7).pack(side="left")
            ttk.Entry(tilt_frame, textvariable=local_tilt_y_var, width=7).pack(side="left", padx=(4, 0))
            ttk.Entry(tilt_frame, textvariable=local_tilt_z_var, width=7).pack(side="left", padx=(4, 0))
        result_var = tk.StringVar(master=window, value="")
        result_row = 2 if path_mode else 0
        result_col = 0 if path_mode else 4
        result_span = 7 if path_mode else 3
        ttk.Label(footer, textvariable=result_var, foreground="#5f6b7a").grid(
            row=result_row,
            column=result_col,
            columnspan=result_span,
            sticky="w",
            pady=(6, 0) if path_mode else 0,
        )

        def update_results(*_args) -> None:
            summaries = list(state.get("summaries", []))
            terms = [term for term in search_var.get().strip().lower().split() if term]
            tree.delete(*tree.get_children())
            shown = 0
            matched = 0
            for summary in summaries:
                haystack = f"{summary['part_number']} {summary['description']}".lower()
                if terms and not all(term in haystack for term in terms):
                    continue
                matched += 1
                if shown >= 500:
                    continue
                diameter = float(summary.get("diameter", 0.0) or 0.0)
                tree.insert(
                    "",
                    "end",
                    values=(
                        summary["part_number"],
                        summary["description"],
                        summary["surface_count"],
                        f"{diameter:.6g}" if diameter > 0 else "",
                    ),
                )
                shown += 1
            if tree.get_children():
                first = tree.get_children()[0]
                tree.selection_set(first)
                tree.focus(first)
            suffix = "" if matched <= shown else f" showing first {shown}"
            result_var.set(f"{matched} match(es){suffix}.")

        def load_selected_catalog(*_args) -> None:
            label = catalog_var.get().strip()
            path = catalogs.get(label)
            if path is None:
                return
            try:
                self.config(cursor="watch")
                window.config(cursor="watch")
                catalog_info_var.set(f"Loading {path.name}...")
                window.update_idletasks()
                catalog = self.load_stock_lens_catalog(path)
                summaries = [self.stock_lens_summary(part, item) for part, item in sorted(catalog.items())]
                state["catalog"] = catalog
                state["summaries"] = summaries
                catalog_info_var.set(f"{label}: {len(summaries)} parts from {path}")
                update_results()
            except Exception as exc:
                state["catalog"] = {}
                state["summaries"] = []
                tree.delete(*tree.get_children())
                catalog_info_var.set(f"Failed to load {label}: {self.short_error_message(exc)}")
                messagebox.showerror("Import Stock Lens", f"Could not load catalog:\n\n{exc}", parent=window)
            finally:
                self.config(cursor="")
                window.config(cursor="")

        def import_selected(_event=None) -> None:
            selected = tree.selection()
            if not selected:
                messagebox.showinfo("Import Stock Lens", "Select a part number first.", parent=window)
                return
            values = tree.item(selected[0], "values")
            if not values:
                return
            part_number = str(values[0])
            catalog = state.get("catalog", {})
            if not isinstance(catalog, dict) or part_number not in catalog:
                messagebox.showerror("Import Stock Lens", f"Catalog item not loaded: {part_number}", parent=window)
                return
            try:
                gap_after = float(gap_after_var.get().strip() or "0")
            except Exception as exc:
                messagebox.showerror("Import Stock Lens", f"Gap after must be numeric:\n\n{exc}", parent=window)
                return
            distance = None
            local_values = (0.0, 0.0, 0.0, 0.0, 0.0)
            if path_mode:
                try:
                    distance = float(distance_var.get().strip() or "0")
                except Exception as exc:
                    messagebox.showerror("Import Stock Lens", f"Path distance must be numeric:\n\n{exc}", parent=window)
                    return
                if not np.isfinite(distance) or distance <= 0.0:
                    messagebox.showerror("Import Stock Lens", "Path distance must be positive.", parent=window)
                    return
                try:
                    local_values = (
                        float(local_decenter_x_var.get().strip() or "0"),
                        float(local_decenter_y_var.get().strip() or "0"),
                        float(local_tilt_x_var.get().strip() or "0"),
                        float(local_tilt_y_var.get().strip() or "0"),
                        float(local_tilt_z_var.get().strip() or "0"),
                    )
                except ValueError:
                    messagebox.showerror("Import Stock Lens", "Local offset and tilt values must be numeric.", parent=window)
                    return
                if not all(np.isfinite(value) for value in local_values):
                    messagebox.showerror("Import Stock Lens", "Local offset and tilt values must be finite.", parent=window)
                    return
            try:
                rows = self._stock_lens_rows_from_catalog_item(
                    part_number,
                    catalog[part_number],
                    inverse=bool(inverse_var.get()),
                    gap_after=gap_after,
                )
            except Exception as exc:
                messagebox.showerror("Import Stock Lens", f"Could not convert {part_number}:\n\n{exc}", parent=window)
                return
            self._commit_pending_table_edit()
            try:
                self._read_rows_from_table()
            except Exception as exc:
                messagebox.showerror("Import Stock Lens", f"Could not read the surface table:\n\n{exc}", parent=window)
                return
            try:
                if path_mode:
                    context = self._path_stock_lens_context(
                        splitter_index=int(path_placement.get("splitter_index", -1)),
                        arm_role=str(path_placement.get("arm_role", "") or ""),
                        branch_path=str(path_placement.get("branch_path", "") or ""),
                    )
                    rows = self._stock_lens_rows_for_path_context(
                        rows,
                        part_number=part_number,
                        context=context,
                        distance_mm=float(distance),
                        local_decenter_x=local_values[0],
                        local_decenter_y=local_values[1],
                        local_tilt_x=local_values[2],
                        local_tilt_y=local_values[3],
                        local_tilt_z=local_values[4],
                    )
                    insert_index = max(1, min(int(context.get("insert_index", len(self.rows) - 1)), len(self.rows) - 1))
                    insert_after = insert_index - 1
                    placement_label = str(context.get("placement_label", "path") or "path")
                else:
                    insert_after = self._selected_insert_index()
                    placement_label = ""
            except Exception as exc:
                messagebox.showerror("Import Stock Lens", f"Could not place {part_number} on the selected path:\n\n{exc}", parent=window)
                return
            self._begin_history_capture()
            insert_at = self._insert_surface_rows(rows, insert_after=insert_after)
            self._commit_history_capture()
            self.current_layout_file = None
            if path_mode:
                message = (
                    f"Inserted stock lens {part_number} as a rigid {len(rows)}-row block "
                    f"at S{insert_at} on {placement_label}. Click Update."
                )
            else:
                message = f"Imported stock lens {part_number} as {len(rows)} surface rows at S{insert_at}."
            self.status_var.set(message)
            self.append_progress(message)
            window.destroy()
            self.refresh_plot(suppress_analysis=True)

        catalog_menu.bind("<<ComboboxSelected>>", load_selected_catalog)
        search_var.trace_add("write", lambda *_args: update_results())
        tree.bind("<Double-1>", import_selected)
        button_row = 2 if path_mode else 0
        ttk.Button(footer, text="Insert on Path" if path_mode else "Import Selected", command=import_selected).grid(
            row=button_row,
            column=7,
            sticky="e",
            padx=(8, 0),
            pady=(6, 0) if path_mode else 0,
        )
        ttk.Button(footer, text="Cancel", command=window.destroy).grid(
            row=button_row,
            column=8,
            sticky="e",
            padx=(8, 0),
            pady=(6, 0) if path_mode else 0,
        )

        self._show_centered_dialog(window)
        load_selected_catalog()
        search_entry.focus_set()
