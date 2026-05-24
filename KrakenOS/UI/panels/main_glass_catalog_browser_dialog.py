"""Glass catalog browser dialog."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable


class MainGlassCatalogBrowserDialog:
    """Own the glass catalog browser while delegating row edits to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        shared_setup: Callable[[], Any],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "shared_setup", shared_setup)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "shared_setup", "short_error_message"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _glass_catalog_records(self) -> list[dict[str, object]]:
        setup = self.shared_setup()
        names_raw = getattr(setup, "NAMES", [])
        nm_raw = getattr(setup, "NM", [])
        names = list(names_raw) if names_raw is not None else []
        nm_rows = list(nm_raw) if nm_raw is not None else []
        records: list[dict[str, object]] = []
        for index, name in enumerate(names):
            text = str(name).strip()
            if not text:
                continue
            nd = ""
            vd = ""
            formula = ""
            try:
                nm = list(nm_rows[index])
                if len(nm) >= 1:
                    formula = f"{float(nm[0]):.0f}"
                if len(nm) >= 4:
                    nd = f"{float(nm[2]):.8g}"
                    vd = f"{float(nm[3]):.8g}"
            except Exception:
                pass
            records.append({"index": index, "name": text, "nd": nd, "vd": vd, "formula": formula})
        return records

    def open_glass_catalog_browser(self) -> None:
        try:
            records = self._glass_catalog_records()
        except Exception as exc:
            message = self.short_error_message(exc)
            messagebox.showerror(
                "Glass Catalog Browser",
                f"Could not load KrakenOS glass catalogs:\n\n{message}",
                parent=self.editor,
            )
            self.status_var.set(f"Glass catalog browser failed: {message}")
            return
        if not records:
            messagebox.showinfo(
                "Glass Catalog Browser",
                "No glass names were found in the KrakenOS catalogs.",
                parent=self.editor,
            )
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title("Glass Catalog Browser")
        window.geometry("820x560")
        window.minsize(620, 400)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(window, padding=(8, 8, 8, 4))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Filter").grid(row=0, column=0, sticky="w", padx=(0, 6))
        filter_var = tk.StringVar(master=window, value="")
        filter_entry = ttk.Entry(toolbar, textvariable=filter_var)
        filter_entry.grid(row=0, column=1, sticky="ew")

        frame = ttk.Frame(window, padding=8)
        frame.grid(row=1, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        columns = ("index", "name", "nd", "vd", "formula")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for column, heading, width in (
            ("index", "#", 70),
            ("name", "Glass", 220),
            ("nd", "n(d)", 110),
            ("vd", "V(d)", 110),
            ("formula", "Formula", 90),
        ):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor=("w" if column == "name" else "e"), stretch=column == "name")
        tree.grid(row=0, column=0, sticky="nsew")
        yscroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        tree.configure(yscrollcommand=yscroll.set)

        footer = ttk.Frame(window, padding=(8, 0, 8, 8))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        count_var = tk.StringVar(master=window, value="")
        ttk.Label(footer, textvariable=count_var, foreground="#5f6b7a").grid(row=0, column=0, sticky="w")

        def refresh_list(*_args) -> None:
            query = filter_var.get().strip().lower()
            tree.delete(*tree.get_children())
            shown = 0
            for record in records:
                haystack = f"{record['name']} {record['nd']} {record['vd']} {record['formula']}".lower()
                if query and query not in haystack:
                    continue
                iid = str(record["index"])
                tree.insert(
                    "",
                    "end",
                    iid=iid,
                    values=(record["index"], record["name"], record["nd"], record["vd"], record["formula"]),
                )
                shown += 1
            count_var.set(f"{shown} / {len(records)} catalog glasses")
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                tree.focus(children[0])

        def selected_glass_name() -> str | None:
            selected = tree.selection()
            if not selected:
                return None
            values = tree.item(selected[0], "values")
            return str(values[1]).strip() if len(values) > 1 else None

        def apply_to_selected_row() -> None:
            glass = selected_glass_name()
            if not glass:
                return
            row_index = self._selected_surface_row_index()
            if row_index is None or not (0 <= row_index < len(self.rows)):
                messagebox.showinfo(
                    "Glass Catalog Browser",
                    "Select a surface row first, then apply the glass.",
                    parent=window,
                )
                return
            self._commit_pending_table_edit()
            self._begin_history_capture()
            self.rows[row_index].glass = glass
            if self.rows[row_index].surface == "Mirror":
                self.rows[row_index].surface = "Standard"
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self.status_var.set(f"Applied glass {glass} to row {row_index}. Click Update.")
            self._mark_plot_update_pending()

        filter_var.trace_add("write", refresh_list)
        filter_entry.bind("<Return>", lambda _event: apply_to_selected_row())
        tree.bind("<Double-1>", lambda _event: apply_to_selected_row())
        ttk.Button(footer, text="Apply to Selected Row", command=apply_to_selected_row).grid(row=0, column=1, sticky="e", padx=(8, 0))
        ttk.Button(footer, text="Close", command=window.destroy).grid(row=0, column=2, sticky="e", padx=(6, 0))

        refresh_list()
        self._show_centered_dialog(window)
        filter_entry.focus_set()
