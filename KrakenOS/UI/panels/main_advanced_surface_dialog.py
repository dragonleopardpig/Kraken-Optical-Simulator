"""Advanced native surface-attribute editor dialog."""

from __future__ import annotations

from dataclasses import asdict
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable


class MainAdvancedSurfaceDialog:
    """Build the advanced surface dialog while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        advanced_row_shape_fields: tuple[tuple[str, str, str], ...],
        advanced_surface_field_groups: tuple[tuple[str, tuple[tuple[str, str], ...]], ...],
        advanced_surface_attr_names: tuple[str, ...],
        variable_registry: dict[str, object],
        column_labels: dict[str, str],
        literal_editor_text: Callable[[object], tuple[str, bool]],
        parse_literal_editor_text: Callable[[str], object],
        format_float_sequence: Callable[[object], str],
        parse_float_sequence_text: Callable[[str], list[float]],
        validate_advanced_surface_inputs: Callable[[dict[str, object], object, object], tuple[list[str], list[str]]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "advanced_row_shape_fields", tuple(advanced_row_shape_fields))
        object.__setattr__(self, "advanced_surface_field_groups", tuple(advanced_surface_field_groups))
        object.__setattr__(self, "advanced_surface_attr_names", tuple(advanced_surface_attr_names))
        object.__setattr__(self, "variable_registry", dict(variable_registry))
        object.__setattr__(self, "column_labels", dict(column_labels))
        object.__setattr__(self, "literal_editor_text", literal_editor_text)
        object.__setattr__(self, "parse_literal_editor_text", parse_literal_editor_text)
        object.__setattr__(self, "format_float_sequence", format_float_sequence)
        object.__setattr__(self, "parse_float_sequence_text", parse_float_sequence_text)
        object.__setattr__(self, "validate_advanced_surface_inputs", validate_advanced_surface_inputs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "advanced_row_shape_fields",
            "advanced_surface_field_groups",
            "advanced_surface_attr_names",
            "variable_registry",
            "column_labels",
            "literal_editor_text",
            "parse_literal_editor_text",
            "format_float_sequence",
            "parse_float_sequence_text",
            "validate_advanced_surface_inputs",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open(self, row_index: int | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Advanced Surface", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Advanced Surface", "Select a surface row first.", parent=self.editor)
            return

        row = self.rows[row_index]
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Advanced Surface - S{row_index}: {row.name}")
        window.geometry("980x620")
        window.minsize(820, 520)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text=(
                "Edit KrakenOS-native surface attributes. Values use Python literals; "
                "imported callable/object values are preserved but read-only here."
            ),
            justify="left",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        notebook = ttk.Notebook(window)
        notebook.grid(row=1, column=0, sticky="nsew", padx=10, pady=(4, 8))

        attr_entries: dict[str, tuple[ttk.Entry, bool]] = {}
        row_shape_entries: dict[str, tuple[ttk.Entry, bool]] = {}

        def add_attr_row(parent: ttk.Frame, grid_row: int, attr: str, label: str, value, *, editable: bool | None = None) -> None:
            text, literal_editable = self.literal_editor_text(value) if value != "" else ("", True)
            is_editable = literal_editable if editable is None else bool(editable and literal_editable)
            ttk.Label(parent, text=label).grid(row=grid_row, column=0, sticky="nw", padx=(8, 6), pady=3)
            ttk.Label(parent, text=attr, foreground="#5f6b7a").grid(row=grid_row, column=1, sticky="nw", padx=(0, 6), pady=3)
            value_frame = ttk.Frame(parent)
            value_frame.grid(row=grid_row, column=2, sticky="ew", padx=(0, 8), pady=3)
            value_frame.columnconfigure(0, weight=1)
            entry = ttk.Entry(value_frame)
            entry.insert(0, text)
            if not is_editable:
                entry.configure(state="readonly")
            entry.grid(row=0, column=0, sticky="ew")
            default_text = self._advanced_surface_default_text(attr)
            ttk.Label(
                value_frame,
                text=f"Default: {default_text}",
                foreground="#6b7280",
                wraplength=520,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))
            attr_entries[attr] = (entry, is_editable)

        shape_frame = ttk.Frame(notebook, padding=(0, 8, 0, 8))
        shape_frame.columnconfigure(2, weight=1)
        notebook.add(shape_frame, text="Shape Params")
        ttk.Label(shape_frame, text="Control").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(0, 4))
        ttk.Label(shape_frame, text="Row field").grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(shape_frame, text="Value").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(0, 4))
        row_shape_editable = row.surface not in {"Object", "Image"}
        for offset, (field, label, help_text) in enumerate(self.advanced_row_shape_fields, start=1):
            ttk.Label(shape_frame, text=label).grid(row=offset, column=0, sticky="nw", padx=(8, 6), pady=3)
            ttk.Label(shape_frame, text=field, foreground="#5f6b7a").grid(row=offset, column=1, sticky="nw", padx=(0, 6), pady=3)
            value_frame = ttk.Frame(shape_frame)
            value_frame.grid(row=offset, column=2, sticky="ew", padx=(0, 8), pady=3)
            value_frame.columnconfigure(0, weight=1)
            entry = ttk.Entry(value_frame)
            entry.insert(0, self._format_table_float(float(getattr(row, field))))
            if not row_shape_editable:
                entry.configure(state="disabled")
            entry.grid(row=0, column=0, sticky="ew")
            ttk.Label(
                value_frame,
                text=help_text,
                foreground="#6b7280",
                wraplength=560,
                justify="left",
            ).grid(row=1, column=0, sticky="w", pady=(2, 0))
            row_shape_entries[field] = (entry, row_shape_editable)

        k_spec = self.variable_registry.get("k")
        k_optimize_var = tk.BooleanVar(
            master=window,
            value=bool(k_spec is not None and k_spec.is_supported(row) and self._variable_enabled_for_row(row, k_spec)),
        )
        k_bounds = k_spec.get_bounds(row) if k_spec is not None else None
        k_bounds_var = tk.StringVar(master=window, value=self.format_float_sequence(k_bounds) if k_bounds else "")
        opt_row = len(self.advanced_row_shape_fields) + 1
        optimize_frame = ttk.Frame(shape_frame)
        optimize_frame.grid(row=opt_row, column=2, sticky="ew", padx=(0, 8), pady=(10, 3))
        optimize_frame.columnconfigure(1, weight=1)
        k_optimize = ttk.Checkbutton(
            optimize_frame,
            text="Optimize conic k",
            variable=k_optimize_var,
        )
        k_optimize.grid(row=0, column=0, sticky="w", padx=(0, 10))
        ttk.Label(optimize_frame, text="Bounds").grid(row=0, column=1, sticky="e", padx=(0, 6))
        k_bounds_entry = ttk.Entry(optimize_frame, textvariable=k_bounds_var, width=22)
        k_bounds_entry.grid(row=0, column=2, sticky="ew")
        ttk.Label(
            optimize_frame,
            text="Optional two-value bounds, for example -2, 0. This writes native Var/VarBounds without putting k back in the main table.",
            foreground="#6b7280",
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(2, 0))
        if k_spec is None or not k_spec.is_supported(row):
            k_optimize.configure(state="disabled")
            k_bounds_entry.configure(state="disabled")

        for group_name, fields in self.advanced_surface_field_groups:
            frame = ttk.Frame(notebook, padding=(0, 8, 0, 8))
            frame.columnconfigure(2, weight=1)
            notebook.add(frame, text=group_name)
            ttk.Label(frame, text="Control").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(0, 4))
            ttk.Label(frame, text="KrakenOS attr").grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 4))
            ttk.Label(frame, text="Override value").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(0, 4))
            for offset, (attr, label) in enumerate(fields, start=1):
                add_attr_row(frame, offset, attr, label, row.advanced.get(attr, ""))

        custom_frame = ttk.Frame(notebook, padding=(0, 8, 0, 8))
        custom_frame.columnconfigure(2, weight=1)
        notebook.add(custom_frame, text="Custom Surface")
        ttk.Label(custom_frame, text="Control").grid(row=0, column=0, sticky="w", padx=(8, 6), pady=(0, 4))
        ttk.Label(custom_frame, text="KrakenOS attr").grid(row=0, column=1, sticky="w", padx=(0, 6), pady=(0, 4))
        ttk.Label(custom_frame, text="Override value").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(0, 4))
        add_attr_row(custom_frame, 1, "ExtraData", "Custom sag data", "" if self._is_default_extra_data(row.extra_data) else row.extra_data)
        add_attr_row(custom_frame, 2, "UDA", "Useful diameter area", "" if self._is_default_uda(row.uda) else row.uda)

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        def collect_values() -> tuple[dict[str, object], object, object, float, float]:
            new_advanced = dict(row.advanced)
            new_k = float(row.k)
            new_axicon = float(row.axicon)
            for field, (entry, editable) in row_shape_entries.items():
                if not editable:
                    continue
                text = entry.get().strip()
                try:
                    value = float(text) if text else 0.0
                except ValueError as exc:
                    raise ValueError(f"{self.column_labels.get(field, field)} expects a number.") from exc
                if field == "k":
                    new_k = value
                elif field == "axicon":
                    new_axicon = value
            for attr in self.advanced_surface_attr_names:
                entry, editable = attr_entries[attr]
                if not editable:
                    continue
                text = entry.get().strip()
                if not text:
                    new_advanced.pop(attr, None)
                    continue
                new_advanced[attr] = self.parse_literal_editor_text(text)

            extra_entry, extra_editable = attr_entries["ExtraData"]
            uda_entry, uda_editable = attr_entries["UDA"]
            new_extra = row.extra_data
            new_uda = row.uda
            if extra_editable:
                parsed = self.parse_literal_editor_text(extra_entry.get())
                new_extra = 0.0 if parsed is None else parsed
            if uda_editable:
                parsed = self.parse_literal_editor_text(uda_entry.get())
                new_uda = "None" if parsed is None else parsed
            if k_spec is not None and k_spec.is_supported(row):
                shape_row = type(row)(**asdict(row))
                shape_row.advanced = dict(new_advanced)
                shape_row.k = float(new_k)
                k_spec.set_enabled(shape_row, bool(k_optimize_var.get()))
                if k_optimize_var.get():
                    bounds_text = k_bounds_var.get().strip()
                    if bounds_text:
                        values = self.parse_float_sequence_text(bounds_text)
                        if len(values) < 2:
                            raise ValueError("Conic k optimization bounds need two numbers, for example -2, 0.")
                        lower = float(values[0])
                        upper = float(values[1])
                        if lower >= upper:
                            raise ValueError("Conic k optimization bounds must be increasing.")
                        k_spec.set_bounds(shape_row, (lower, upper))
                    else:
                        k_spec.set_bounds(shape_row, None)
                else:
                    k_spec.set_bounds(shape_row, None)
                new_advanced = dict(shape_row.advanced or {})
            return new_advanced, new_extra, new_uda, new_k, new_axicon

        def validate_values(*, show_success: bool = True) -> tuple[list[str], list[str]]:
            try:
                new_advanced, new_extra, new_uda, _new_k, _new_axicon = collect_values()
            except Exception as exc:
                errors = [str(exc)]
                validation_var.set(f"Validation failed: {errors[0]}")
                return errors, []
            errors, warnings_out = self.validate_advanced_surface_inputs(new_advanced, new_extra, new_uda)
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif warnings_out:
                validation_var.set(f"Validation warning: {warnings_out[0]}")
            elif show_success:
                validation_var.set("Validation passed.")
            return errors, warnings_out

        def apply_values() -> None:
            try:
                new_advanced, new_extra, new_uda, new_k, new_axicon = collect_values()
            except Exception as exc:
                messagebox.showerror(
                    "Advanced Surface Validation",
                    f"Fix this value before applying:\n\n{exc}",
                    parent=window,
                )
                return
            errors, warnings_out = validate_values(show_success=False)
            if errors:
                messagebox.showerror(
                    "Advanced Surface Validation",
                    "Fix these values before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return
            if warnings_out:
                self.append_debug("Advanced surface validation warnings: " + " | ".join(warnings_out))

            self._begin_history_capture()
            self.rows[row_index].advanced = new_advanced
            self.rows[row_index].extra_data = new_extra
            self.rows[row_index].uda = new_uda
            self.rows[row_index].k = new_k
            self.rows[row_index].axicon = new_axicon
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated advanced attributes for S{row_index}: {self.rows[row_index].name}. Click Update.")
            window.destroy()

        ttk.Button(footer, text="Validate", command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
