"""Coating and material editor dialog for the main layout editor."""

from __future__ import annotations

from pathlib import Path
from pprint import pformat
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

import numpy as np


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
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Material", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Coating / Material", "Select a surface row first.", parent=self.editor)
            return

        row = self.rows[row_index]
        advanced = dict(row.advanced or {})
        coating_value = advanced.get("Coating", [[], [], [], []])
        coating_text, coating_editable = self.literal_editor_text(coating_value)
        if not coating_editable:
            coating_text = "<non-literal coating object>"
        dialog_metal_catalogs = self.normalize_metal_catalog_specs(getattr(self, "metal_catalogs", []))
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Coating / Material - S{row_index}: {row.name}")
        window.geometry("860x440")
        window.minsize(720, 360)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)
        ttk.Label(header, text="Preset").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        preset_var = tk.StringVar(master=window, value=self._coating_preset_for_value(coating_value))
        preset_menu = ttk.Combobox(
            header,
            textvariable=preset_var,
            values=("Custom",) + self.coating_preset_names,
            state="readonly",
            width=28,
        )
        preset_menu.grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(
            header,
            text="Coating = [R, A, W, THETA]. R/A rows follow THETA; columns follow wavelength.",
            foreground="#5f6b7a",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 0))

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Coating table").grid(row=0, column=0, sticky="nw", padx=(0, 8), pady=3)
        coating_editor = tk.Text(body, height=10, wrap="none")
        coating_editor.insert("1.0", coating_text)
        coating_editor.grid(row=0, column=1, sticky="nsew", pady=3)
        body.rowconfigure(0, weight=1)
        scroll = ttk.Scrollbar(body, orient="vertical", command=coating_editor.yview)
        scroll.grid(row=0, column=2, sticky="ns")
        coating_editor.configure(yscrollcommand=scroll.set)

        ttk.Label(body, text="CoatingMet").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=3)
        coating_met_var = tk.StringVar(master=window, value=str(advanced.get("CoatingMet", 0)))
        ttk.Entry(body, textvariable=coating_met_var, width=16).grid(row=1, column=1, sticky="w", pady=3)

        ttk.Label(body, text="Metal catalog").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=3)
        metal_catalog_var = tk.StringVar(master=window, value="")
        metal_catalog_menu = ttk.Combobox(body, textvariable=metal_catalog_var, state="readonly", width=42)
        metal_catalog_menu.grid(row=2, column=1, sticky="w", pady=3)

        def metal_choice_labels() -> tuple[str, ...]:
            labels = []
            for index, catalog in enumerate(self.metal_catalog_entries(dialog_metal_catalogs)):
                labels.append(f"{index}: {catalog['name']} ({Path(str(catalog['path'])).name})")
            return tuple(labels)

        def refresh_metal_choices(selected_index: int | None = None) -> None:
            labels = metal_choice_labels()
            metal_catalog_menu["values"] = labels
            if not labels:
                return
            try:
                current_index = int(float(coating_met_var.get().strip() or "0"))
            except Exception:
                current_index = 0
            if selected_index is not None:
                current_index = int(selected_index)
            current_index = min(max(current_index, 0), len(labels) - 1)
            metal_catalog_var.set(labels[current_index])
            coating_met_var.set(str(current_index))

        def select_metal_catalog(_event=None) -> None:
            label = metal_catalog_var.get().strip()
            try:
                coating_met_var.set(str(int(label.split(":", 1)[0])))
            except Exception:
                pass

        def load_metal_csv() -> None:
            nonlocal dialog_metal_catalogs
            path_text = filedialog.askopenfilename(
                title="Load Metal CSV",
                initialdir=str(self.metal_catalog_dir),
                filetypes=[("CSV files", "*.csv"), ("All files", "*")],
                parent=window,
            )
            if not path_text:
                return
            path = Path(path_text).expanduser()
            spec = {"name": path.stem, "path": str(path), "type": self.metal_catalog_type_for_path(path)}
            dialog_metal_catalogs = self.normalize_metal_catalog_specs([*dialog_metal_catalogs, spec])
            entries = self.metal_catalog_entries(dialog_metal_catalogs)
            selected_index = next(
                (
                    index
                    for index, entry in enumerate(entries)
                    if str(entry["path"]) == str(path) and str(entry["name"]).lower() == path.stem.lower()
                ),
                len(entries) - 1,
            )
            refresh_metal_choices(selected_index)
            validation_var.set(f"Loaded metal catalog candidate: {path.name}. Click Apply to save it with this layout.")

        metal_catalog_menu.bind("<<ComboboxSelected>>", select_metal_catalog)
        ttk.Button(body, text="Load CSV...", command=load_metal_csv).grid(row=2, column=2, sticky="w", padx=(8, 0), pady=3)
        refresh_metal_choices()
        ttk.Label(
            body,
            text="Metal index for MIRROR Fresnel mode. Explicit coating tables override Fresnel values.",
            foreground="#5f6b7a",
        ).grid(row=3, column=1, sticky="w", pady=(0, 4))

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        validation_var = tk.StringVar(master=window, value="Validation has not been run.")
        ttk.Label(footer, textvariable=validation_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        def use_preset(_event=None) -> None:
            name = preset_var.get()
            if name not in self.coating_presets:
                return
            coating_editor.delete("1.0", "end")
            coating_editor.insert("1.0", pformat(self.coating_presets[name], width=100))

        preset_menu.bind("<<ComboboxSelected>>", use_preset)

        def collect_values() -> tuple[list, int]:
            text = coating_editor.get("1.0", "end").strip()
            coating = self.parse_literal_editor_text(text) if text else [[], [], [], []]
            try:
                coating_met_value = float(coating_met_var.get().strip() or "0")
            except Exception as exc:
                raise ValueError(f"CoatingMet must be an integer metal index: {exc}") from exc
            if not np.isfinite(coating_met_value) or int(coating_met_value) != coating_met_value:
                raise ValueError("CoatingMet must be an integer metal index.")
            coating_met = int(coating_met_value)
            return coating, coating_met

        def validate_values(*, show_success: bool = True) -> tuple[list[str], list[str]]:
            try:
                coating, coating_met = collect_values()
            except Exception as exc:
                errors = [str(exc)]
                validation_var.set(f"Validation failed: {errors[0]}")
                return errors, []
            candidate = dict(advanced)
            candidate["Coating"] = coating
            candidate["CoatingMet"] = coating_met
            errors, warnings_out = self.validate_advanced_surface_inputs(candidate, row.extra_data, row.uda)
            metal_count = len(self.metal_catalog_entries(dialog_metal_catalogs))
            if coating_met >= metal_count:
                errors.append(f"CoatingMet index {coating_met} has no loaded metal catalog; load a CSV first.")
            for catalog in self.normalize_metal_catalog_specs(dialog_metal_catalogs):
                path = Path(str(catalog["path"])).expanduser()
                if not path.exists():
                    errors.append(f"Metal catalog does not exist: {path}")
            if errors:
                validation_var.set(f"Validation failed: {errors[0]}")
            elif warnings_out:
                validation_var.set(f"Validation warning: {warnings_out[0]}")
            elif show_success:
                validation_var.set("Validation passed.")
            return errors, warnings_out

        def apply_values() -> None:
            try:
                coating, coating_met = collect_values()
            except Exception as exc:
                messagebox.showerror("Coating / Material", str(exc), parent=window)
                return
            errors, warnings_out = validate_values(show_success=False)
            if errors:
                messagebox.showerror(
                    "Coating / Material Validation",
                    "Fix these values before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return
            new_advanced = dict(row.advanced or {})
            if coating == [[], [], [], []]:
                new_advanced.pop("Coating", None)
            else:
                new_advanced["Coating"] = coating
            if coating_met == 0:
                new_advanced.pop("CoatingMet", None)
            else:
                new_advanced["CoatingMet"] = coating_met
            if warnings_out:
                self.append_debug("Coating validation warnings: " + " | ".join(warnings_out))
            self._begin_history_capture()
            self.metal_catalogs = self.normalize_metal_catalog_specs(dialog_metal_catalogs)
            self.rows[row_index].advanced = new_advanced
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated coating/material for S{row_index}: {self.rows[row_index].name}. Click Update.")
            window.destroy()

        ttk.Button(footer, text="Validate", command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
