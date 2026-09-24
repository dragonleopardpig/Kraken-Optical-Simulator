"""Diffuse / BRDF scatter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.diffuse_scatter import build_diffuse_scatter_form
from KrakenOS.UI.panels.row_form_view import render_row_form


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
        # bugs/0884: the Tk layout is the SHARED renderer now -- this file keeps only the
        # read-the-table prologue and the builder call.
        render_row_form(self, form, wraplength=560)
