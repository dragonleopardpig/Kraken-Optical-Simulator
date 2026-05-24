"""Measured error map editor dialog for the main layout editor."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable


class MainErrorMapDialog:
    """Build the error-map dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        attachment_dir: Path,
        project_root: Path,
        error_map_literal: Callable[[object], object],
        error_map_summary: Callable[[object], str],
        load_error_map_file: Callable[[Path], object],
        validate_error_map: Callable[[object], list[str]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "attachment_dir", Path(attachment_dir))
        object.__setattr__(self, "project_root", Path(project_root))
        object.__setattr__(self, "error_map_literal", error_map_literal)
        object.__setattr__(self, "error_map_summary", error_map_summary)
        object.__setattr__(self, "load_error_map_file", load_error_map_file)
        object.__setattr__(self, "validate_error_map", validate_error_map)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "attachment_dir",
            "project_root",
            "error_map_literal",
            "error_map_summary",
            "load_error_map_file",
            "validate_error_map",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Error Map", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Error Map", "Select a surface row first.", parent=self.editor)
            return

        row = self.rows[row_index]
        if row.surface in {"Object", "Image"}:
            messagebox.showinfo("Error Map", "Measured error maps apply to physical surfaces, not Object/Image rows.", parent=self.editor)
            return

        advanced = dict(row.advanced or {})
        current_error_map = advanced.get("Error_map")
        candidate_error_map = None
        if current_error_map is not None:
            try:
                candidate_error_map = self.error_map_literal(current_error_map)
            except Exception:
                candidate_error_map = current_error_map

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Error Map - S{row_index}: {row.name}")
        window.geometry("760x360")
        window.minsize(660, 300)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Surface").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Label(header, text=f"S{row_index}: {row.name}").grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(
            header,
            text="Imports measured sag/departure as KrakenOS Error_map = [X, Y, Z, SPACE].",
            foreground="#5f6b7a",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        source_var = tk.StringVar(master=window, value="Current row" if candidate_error_map is not None else "None")
        ttk.Label(body, text="Source").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Label(body, textvariable=source_var).grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(body, text="Summary").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=3)
        summary_text = tk.Text(body, height=8, wrap="word")
        summary_text.grid(row=1, column=1, sticky="nsew", pady=3)
        summary_scroll = ttk.Scrollbar(body, orient="vertical", command=summary_text.yview)
        summary_scroll.grid(row=1, column=2, sticky="ns")
        summary_text.configure(yscrollcommand=summary_scroll.set)

        ttk.Label(
            body,
            text=(
                "CSV/TXT: x,y,z columns or a rectangular Z matrix. "
                "NPZ: X, Y, Z arrays plus optional SPACE. NPY: x/y/z columns, stacked X/Y/Z grids, or a Z matrix."
            ),
            foreground="#5f6b7a",
            wraplength=660,
            justify="left",
        ).grid(row=2, column=1, sticky="ew", pady=(4, 0))

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        def update_summary() -> None:
            summary_text.configure(state="normal")
            summary_text.delete("1.0", "end")
            if candidate_error_map is None:
                summary_text.insert(
                    "1.0",
                    "No Error_map will be stored on this surface.\n\n"
                    "Click Import... to load measured data, or Apply to clear the current surface error map.",
                )
            else:
                summary_text.insert(
                    "1.0",
                    self.error_map_summary(candidate_error_map)
                    + "\n\nStored form: flattened X, Y, and Z sample lists plus one scalar SPACE pitch.",
                )
            summary_text.configure(state="disabled")

        def import_error_map() -> None:
            nonlocal candidate_error_map
            path_text = filedialog.askopenfilename(
                title="Import Error Map",
                initialdir=str(self.attachment_dir if self.attachment_dir.exists() else self.project_root),
                filetypes=[
                    ("Error map files", "*.csv *.txt *.dat *.tsv *.npy *.npz"),
                    ("Text files", "*.csv *.txt *.dat *.tsv"),
                    ("NumPy files", "*.npy *.npz"),
                    ("All files", "*"),
                ],
                parent=window,
            )
            if not path_text:
                return
            path = Path(path_text).expanduser()
            try:
                loaded = self.load_error_map_file(path)
                errors = self.validate_error_map(loaded)
                if errors:
                    raise ValueError(errors[0])
            except Exception as exc:
                messagebox.showerror("Import Error Map", f"Could not import {path.name}:\n\n{exc}", parent=window)
                return
            candidate_error_map = loaded
            source_var.set(str(path))
            update_summary()
            validation_var.set(f"Loaded {path.name}. Validation passed.")

        def clear_error_map() -> None:
            nonlocal candidate_error_map
            candidate_error_map = None
            source_var.set("None")
            update_summary()
            validation_var.set("Error map will be cleared on Apply.")

        def validate_values(*, show_success: bool = True) -> list[str]:
            if candidate_error_map is None:
                if show_success:
                    validation_var.set("Validation passed: no error map.")
                return []
            errors = self.validate_error_map(candidate_error_map)
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set("Validation passed.")
            return errors

        def apply_values() -> None:
            errors = validate_values(show_success=False)
            if errors:
                messagebox.showerror(
                    "Error Map Validation",
                    "Fix this error map before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return

            self._begin_history_capture()
            new_advanced = dict(self.rows[row_index].advanced or {})
            if candidate_error_map is None:
                new_advanced.pop("Error_map", None)
                status_message = f"Cleared error map for S{row_index}: {self.rows[row_index].name}. Click Update."
            else:
                normalized = self.error_map_literal(candidate_error_map)
                new_advanced["Error_map"] = normalized
                status_message = (
                    f"Updated error map for S{row_index}: {self.rows[row_index].name} "
                    f"({self.error_map_summary(normalized)}). Click Update."
                )
            self.rows[row_index].advanced = new_advanced
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(status_message)
            window.destroy()

        update_summary()
        ttk.Button(footer, text="Import...", command=import_error_map).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Clear", command=clear_error_map).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Validate", command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
