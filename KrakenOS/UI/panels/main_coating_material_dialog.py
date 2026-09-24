"""Coating and material editor dialog for the main layout editor."""

from __future__ import annotations

from pathlib import Path
from pprint import pformat
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.coating_material import build_coating_material_form
from KrakenOS.UI.uihost import host_of


class MainCoatingMaterialDialog:
    """Build the coating/material dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        coating_presets: dict[str, object],
        coating_preset_names: tuple[str, ...],
        metal_catalog_dir: Path,
        literal_editor_text: Callable[[object], tuple[str, bool]],
        parse_literal_editor_text: Callable[[str], object],
        normalize_metal_catalog_specs: Callable[[object], list[dict[str, object]]],
        metal_catalog_entries: Callable[[object], list[dict[str, object]]],
        metal_catalog_type_for_path: Callable[[Path], str],
        validate_advanced_surface_inputs: Callable[[dict[str, object], object, object], tuple[list[str], list[str]]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "coating_presets", dict(coating_presets))
        object.__setattr__(self, "coating_preset_names", tuple(coating_preset_names))
        object.__setattr__(self, "metal_catalog_dir", Path(metal_catalog_dir))
        object.__setattr__(self, "literal_editor_text", literal_editor_text)
        object.__setattr__(self, "parse_literal_editor_text", parse_literal_editor_text)
        object.__setattr__(self, "normalize_metal_catalog_specs", normalize_metal_catalog_specs)
        object.__setattr__(self, "metal_catalog_entries", metal_catalog_entries)
        object.__setattr__(self, "metal_catalog_type_for_path", metal_catalog_type_for_path)
        object.__setattr__(self, "validate_advanced_surface_inputs", validate_advanced_surface_inputs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "coating_presets",
            "coating_preset_names",
            "metal_catalog_dir",
            "literal_editor_text",
            "parse_literal_editor_text",
            "normalize_metal_catalog_specs",
            "metal_catalog_entries",
            "metal_catalog_type_for_path",
            "validate_advanced_surface_inputs",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        # docs/design_qt_migration.md phase 3: the presets, the literal coating table, the metal
        # catalogue list, the validation and what Apply writes live in
        # KrakenOS/UI/row_forms/coating_material.py, which the Qt dialog uses too.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Material",
                                 f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_coating_material_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Coating / Material", str(exc), parent=self.editor)
            return

        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(form.title)
        window.geometry("860x440")
        window.minsize(720, 360)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text=form.note, foreground="#5f6b7a", wraplength=760,
                  justify="left").grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 4))

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        variables: dict[str, tk.StringVar] = {}
        text_widgets: dict[str, tk.Text] = {}
        combos: dict[str, ttk.Combobox] = {}

        def current_values() -> dict[str, str]:
            values = {key: variable.get() for key, variable in variables.items()}
            values.update({key: widget.get("1.0", "end-1c")
                           for key, widget in text_widgets.items()})
            return values

        def refresh_from_form() -> None:
            for key, variable in variables.items():
                if variable.get() != form.values.get(key, ""):
                    variable.set(form.values.get(key, ""))
            for key, widget in text_widgets.items():
                if widget.get("1.0", "end-1c") != form.values.get(key, ""):
                    widget.delete("1.0", "end")
                    widget.insert("1.0", form.values.get(key, ""))
            for key, combo in combos.items():
                combo["values"] = list(form.choices_for(key))

        for grid_row, field in enumerate(form.fields):
            ttk.Label(body, text=field.label).grid(
                row=grid_row, column=0, sticky="nw" if field.kind == "textarea" else "w",
                padx=(0, 8), pady=3)
            if field.kind == "textarea":
                widget = tk.Text(body, height=field.height, wrap="none")
                widget.insert("1.0", form.values.get(field.key, ""))
                widget.grid(row=grid_row, column=1, sticky="nsew", pady=3)
                body.rowconfigure(grid_row, weight=1)
                scroll = ttk.Scrollbar(body, orient="vertical", command=widget.yview)
                scroll.grid(row=grid_row, column=2, sticky="ns")
                widget.configure(yscrollcommand=scroll.set)
                text_widgets[field.key] = widget
                continue
            variable = tk.StringVar(master=window, value=form.values.get(field.key, ""))
            variables[field.key] = variable
            if field.kind == "choice":
                combo = ttk.Combobox(body, textvariable=variable, state="readonly",
                                     values=list(form.choices_for(field.key)), width=field.width)
                combo.grid(row=grid_row, column=1, sticky="w", pady=3)
                combos[field.key] = combo
                if field.on_change is not None:
                    def on_selected(_event=None, f=field, v=variable) -> None:
                        form.values[f.key] = v.get()
                        message = f.on_change(form, v.get())
                        refresh_from_form()
                        if message:
                            validation_var.set(message)
                    combo.bind("<<ComboboxSelected>>", on_selected)
            else:
                ttk.Entry(body, textvariable=variable, width=field.width).grid(
                    row=grid_row, column=1, sticky="w", pady=3)
            if field.hint:
                ttk.Label(body, text=field.hint, foreground="#6b7280").grid(
                    row=grid_row, column=2, sticky="w", padx=(8, 0), pady=3)

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(
            side="left", fill="x", expand=True)

        def run_action(action) -> None:
            form.values.update(current_values())
            try:
                message = action.run(form, host_of(self))
            except FormRefused as exc:
                messagebox.showerror("Coating / Material", str(exc), parent=window)
                return
            refresh_from_form()
            validation_var.set(message or "")

        def validate_values(*, show_success: bool = True) -> list[str]:
            values = current_values()
            errors = list(form.validate(values))
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                validation_var.set(form.describe(values))
            return errors

        def apply_values() -> None:
            try:
                form.apply(current_values())
            except FormRefused as exc:
                messagebox.showerror("Coating / Material Validation", str(exc), parent=window)
                return
            window.destroy()

        for action in form.actions:
            ttk.Button(footer, text=action.label,
                       command=lambda a=action: run_action(a)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Validate",
                   command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
