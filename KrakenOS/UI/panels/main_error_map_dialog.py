"""Measured error map editor dialog for the main layout editor."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.error_map import build_error_map_form
from KrakenOS.UI.uihost import host_of


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
        # docs/design_qt_migration.md phase 3: the candidate map, the import, the clear, the
        # validation and what Apply writes live in KrakenOS/UI/row_forms/error_map.py, which the
        # Qt dialog uses too. This function is layout.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Error Map", f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_error_map_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Error Map", str(exc), parent=self.editor)
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.geometry("760x360")
        window.minsize(660, 300)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Surface").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Label(header, text=form.values["surface"]).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(header, text=form.note, foreground="#5f6b7a", wraplength=660,
                  justify="left").grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(1, weight=1)

        source_var = tk.StringVar(master=window, value=form.values["source"])
        ttk.Label(body, text="Source").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Label(body, textvariable=source_var).grid(row=0, column=1, sticky="ew", pady=3)

        ttk.Label(body, text="Contents").grid(row=1, column=0, sticky="nw", padx=(0, 8), pady=3)
        summary_text = tk.Text(body, height=8, wrap="word")
        summary_text.grid(row=1, column=1, sticky="nsew", pady=3)
        summary_scroll = ttk.Scrollbar(body, orient="vertical", command=summary_text.yview)
        summary_scroll.grid(row=1, column=2, sticky="ns")
        summary_text.configure(yscrollcommand=summary_scroll.set)

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(
            side="left", fill="x", expand=True)

        def refresh_from_form() -> None:
            source_var.set(form.values["source"])
            summary_text.configure(state="normal")
            summary_text.delete("1.0", "end")
            summary_text.insert("1.0", form.summary)
            summary_text.configure(state="disabled")

        def run_action(action) -> None:
            try:
                message = action.run(form, host_of(self))
            except FormRefused as exc:
                messagebox.showerror(f"{action.label} {form.title}", str(exc), parent=window)
                return
            refresh_from_form()
            validation_var.set(message or "")

        def validate_values(*, show_success: bool = True) -> list[str]:
            errors = list(form.validate(form.values))
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set("Validation passed."
                                   if form.state.get("error_map") is not None
                                   else "Validation passed: no error map.")
            return errors

        def apply_values() -> None:
            try:
                form.apply(form.values)
            except FormRefused as exc:
                messagebox.showerror("Error Map Validation", str(exc), parent=window)
                return
            window.destroy()

        refresh_from_form()
        for action in form.actions:
            ttk.Button(footer, text=action.label,
                       command=lambda a=action: run_action(a)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Validate",
                   command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
