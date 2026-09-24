"""Beam splitter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.beam_splitter import build_beam_splitter_form
from KrakenOS.UI.panels.row_form_view import render_row_form


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
        # bugs/0884: the Tk layout is the SHARED renderer now -- this file keeps only the
        # read-the-table prologue and the builder call.
        render_row_form(self, form, wraplength=520)
