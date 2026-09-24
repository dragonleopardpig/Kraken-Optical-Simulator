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
from KrakenOS.UI.panels.row_form_view import render_row_form


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
        # bugs/0884: the Tk layout is the SHARED renderer now -- this file keeps only the
        # read-the-table prologue and the builder call.
        render_row_form(self, form, wraplength=560)
