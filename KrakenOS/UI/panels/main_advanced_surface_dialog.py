"""Advanced native surface-attribute editor dialog."""

from __future__ import annotations

from dataclasses import asdict
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.advanced_surface import build_advanced_surface_form
from KrakenOS.UI.panels.row_form_view import render_row_form


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
        # docs/design_qt_migration.md phase 3: the fields, their tabs, which ones are locked, the
        # validation and what Apply writes live in KrakenOS/UI/row_forms/advanced_surface.py,
        # which the Qt dialog uses too. What stays here is Tk layout -- the scrolling tabs and
        # their wheel binding, which have no counterpart on the other side.
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Advanced Surface",
                                 f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return

        try:
            form = build_advanced_surface_form(self, row_index)
        except FormRefused as exc:
            messagebox.showinfo("Advanced Surface", str(exc), parent=self.editor)
            return
        # bugs/0884: the Tk layout is the SHARED renderer now -- this file keeps only the
        # read-the-table prologue and the builder call.
        render_row_form(self, form, wraplength=700)
