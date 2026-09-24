"""Diffuse / BRDF scatter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.diffuse_scatter import build_diffuse_scatter_form


class MainDiffuseScatterDialog:
    """Build the Diffuse / BRDF dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        diffuse_object_surface: str,
        diffuse_scatter_advanced_attr: str,
        diffuse_scatter_default_settings: dict[str, object],
        normalize_diffuse_scatter_settings: Callable[[object], dict[str, object]],
        validate_diffuse_scatter_settings: Callable[[dict[str, object]], list[str]],
        pyscatmech_status: Callable[[], dict[str, object]],
        format_pyscatmech_parameters: Callable[[object], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "diffuse_object_surface", diffuse_object_surface)
        object.__setattr__(self, "diffuse_scatter_advanced_attr", diffuse_scatter_advanced_attr)
        object.__setattr__(self, "diffuse_scatter_default_settings", dict(diffuse_scatter_default_settings))
        object.__setattr__(self, "normalize_diffuse_scatter_settings", normalize_diffuse_scatter_settings)
        object.__setattr__(self, "validate_diffuse_scatter_settings", validate_diffuse_scatter_settings)
        object.__setattr__(self, "pyscatmech_status", pyscatmech_status)
        object.__setattr__(self, "format_pyscatmech_parameters", format_pyscatmech_parameters)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "diffuse_object_surface",
            "diffuse_scatter_advanced_attr",
            "diffuse_scatter_default_settings",
            "normalize_diffuse_scatter_settings",
            "validate_diffuse_scatter_settings",
            "pyscatmech_status",
            "format_pyscatmech_parameters",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        # docs/design_qt_migration.md phase 3: the fields, their hints, the validation and what
        # Apply writes live in KrakenOS/UI/row_forms/diffuse_scatter.py, which the Qt dialog uses
        # too. This function is layout.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Diffuse / BRDF", f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_diffuse_scatter_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Diffuse / BRDF", str(exc), parent=self.editor)
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.geometry("860x680")
        window.minsize(760, 600)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)

        body = ttk.Frame(window, padding=(12, 10, 12, 8))
        body.grid(row=0, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        ttk.Label(body, text=form.note, foreground="#5f6b7a", wraplength=720).grid(
            row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))

        variables: dict[str, tk.StringVar] = {}
        text_widgets: dict[str, tk.Text] = {}
        for grid_row, field in enumerate(form.fields, start=1):
            ttk.Label(body, text=field.label).grid(row=grid_row, column=0, sticky="nw" if
                                                   field.kind == "textarea" else "w",
                                                   padx=(0, 8), pady=4)
            if field.kind == "textarea":
                widget = tk.Text(body, width=52, height=field.height, wrap="word")
                widget.insert("1.0", form.values.get(field.key, ""))
                widget.grid(row=grid_row, column=1, sticky="ew", pady=4)
                text_widgets[field.key] = widget
            else:
                variable = tk.StringVar(master=window, value=form.values.get(field.key, ""))
                variables[field.key] = variable
                if field.kind == "choice":
                    ttk.Combobox(body, textvariable=variable, values=list(field.choices),
                                 state="readonly", width=field.width).grid(
                        row=grid_row, column=1, sticky="w", pady=4)
                else:
                    ttk.Entry(body, textvariable=variable, width=field.width).grid(
                        row=grid_row, column=1, sticky="w", pady=4)
            ttk.Label(body, text=field.hint, foreground="#6b7280", wraplength=320,
                      justify="left").grid(row=grid_row, column=2, sticky="nw", pady=4)

        footer = ttk.Frame(window, padding=(12, 0, 12, 10))
        footer.grid(row=1, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(
            side="left", fill="x", expand=True)

        def current_values() -> dict[str, str]:
            values = {key: variable.get() for key, variable in variables.items()}
            values.update({key: widget.get("1.0", "end-1c")
                           for key, widget in text_widgets.items()})
            return values

        def validate_values(*, show_success: bool = True) -> list[str]:
            errors = list(form.validate(current_values()))
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set("Validation passed.")
            return errors

        def apply_values() -> None:
            try:
                form.apply(current_values())
            except FormRefused as exc:
                messagebox.showerror("Diffuse / BRDF Validation", str(exc), parent=window)
                return
            window.destroy()

        ttk.Button(footer, text="Validate",
                   command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
