"""Measured error map editor dialog for the main layout editor."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.error_map import build_error_map_form
from KrakenOS.UI.uihost import host_of
from KrakenOS.UI.panels.row_form_view import render_row_form


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
        # bugs/0884: the Tk layout is the SHARED renderer now -- this file keeps only the
        # read-the-table prologue and the builder call.
        render_row_form(self, form, wraplength=560)
