"""Beam splitter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form


class MainBeamSplitterDialog:
    """Build the beam splitter dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        beam_splitter_surface: str,
        beam_splitter_advanced_attr: str,
        beam_splitter_split_modes: tuple[str, ...],
        normalize_beam_splitter_settings: Callable[[object], dict[str, object]],
        validate_beam_splitter_settings: Callable[[dict[str, object]], list[str]],
        beam_splitter_coating_for_settings: Callable[[dict[str, object], object], object],
        beam_splitter_summary: Callable[[object], str],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "beam_splitter_surface", beam_splitter_surface)
        object.__setattr__(self, "beam_splitter_advanced_attr", beam_splitter_advanced_attr)
        object.__setattr__(self, "beam_splitter_split_modes", tuple(beam_splitter_split_modes))
        object.__setattr__(self, "normalize_beam_splitter_settings", normalize_beam_splitter_settings)
        object.__setattr__(self, "validate_beam_splitter_settings", validate_beam_splitter_settings)
        object.__setattr__(self, "beam_splitter_coating_for_settings", beam_splitter_coating_for_settings)
        object.__setattr__(self, "beam_splitter_summary", beam_splitter_summary)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "beam_splitter_surface",
            "beam_splitter_advanced_attr",
            "beam_splitter_split_modes",
            "normalize_beam_splitter_settings",
            "validate_beam_splitter_settings",
            "beam_splitter_coating_for_settings",
            "beam_splitter_summary",
            "short_error_message",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        # docs/design_qt_migration.md phase 3: the fields, the validation and what Apply writes
        # live in KrakenOS/UI/row_forms/beam_splitter.py, which the Qt dialog uses too. This
        # function is layout.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Beam Splitter", f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_beam_splitter_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Beam Splitter", str(exc), parent=self.editor)
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.geometry("860x520")
        window.minsize(740, 430)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(header, text=form.note, foreground="#475569", wraplength=740,
                  justify="left").grid(row=0, column=0, sticky="ew")

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.columnconfigure(3, weight=1)

        variables = {field.key: tk.StringVar(master=window, value=form.values.get(field.key, ""))
                     for field in form.fields}
        summary_var = tk.StringVar(master=window, value="")

        choice_fields = [field for field in form.fields if field.kind == "choice"]
        value_fields = [field for field in form.fields if field.kind != "choice"]
        for index, field in enumerate(choice_fields):
            ttk.Label(body, text=field.label).grid(row=index, column=0, sticky="w",
                                                   padx=(0, 8), pady=3)
            ttk.Combobox(body, textvariable=variables[field.key], state="readonly",
                         values=list(field.choices), width=field.width).grid(
                row=index, column=1, columnspan=3, sticky="ew", pady=3)

        hint_base_row = len(choice_fields) + (len(value_fields) + 1) // 2 + 1
        for index, field in enumerate(value_fields):
            col = 0 if index % 2 == 0 else 2
            row_num = len(choice_fields) + index // 2
            ttk.Label(body, text=field.label).grid(
                row=row_num, column=col, sticky="w", padx=(0 if col == 0 else 12, 8), pady=3)
            ttk.Entry(body, textvariable=variables[field.key], width=field.width).grid(
                row=row_num, column=col + 1, sticky="ew", pady=3)
            ttk.Label(body, text=field.hint, foreground="#6b7280").grid(
                row=hint_base_row + index // 2, column=col, columnspan=2, sticky="w",
                padx=(0 if col == 0 else 12, 0), pady=(3, 0))

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=summary_var, foreground="#5f6b7a").pack(
            side="left", fill="x", expand=True)

        def current_values() -> dict[str, str]:
            return {key: variable.get() for key, variable in variables.items()}

        def validate_values(*, show_success: bool = True) -> list[str]:
            errors = list(form.validate(current_values()))
            if errors:
                summary_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                try:
                    summary_var.set("Validation passed: " + form.describe(current_values()))
                except FormRefused as exc:
                    summary_var.set(f"Validation failed: {exc}")
            return errors

        def apply_values() -> None:
            try:
                status = form.apply(current_values())
            except FormRefused as exc:
                messagebox.showerror("Beam Splitter", str(exc), parent=window)
                return
            self.status_var.set(status)
            window.destroy()

        validate_values(show_success=True)
        ttk.Button(footer, text="Validate",
                   command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
