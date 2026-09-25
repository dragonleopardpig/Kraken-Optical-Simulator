"""Specialized surface settings dialogs for the main layout editor."""

from __future__ import annotations

from typing import Any, Callable

from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.surface_settings import (build_galvo_scan_form,
                                                    build_grating_settings_form)


class MainSurfaceSettingsDialogs:
    """Build small surface-specific dialogs while keeping row state on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        galvo_scan_overlay_key: str,
        format_float_sequence: Callable[[object], str],
        parse_float_sequence_text: Callable[[str], list[float]],
        short_error_message: Callable[[BaseException], str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "galvo_scan_overlay_key", galvo_scan_overlay_key)
        object.__setattr__(self, "format_float_sequence", format_float_sequence)
        object.__setattr__(self, "parse_float_sequence_text", parse_float_sequence_text)
        object.__setattr__(self, "short_error_message", short_error_message)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "galvo_scan_overlay_key",
            "format_float_sequence",
            "parse_float_sequence_text",
            "short_error_message",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def open_galvo_scan_overlay_settings(self, index: int | None = None) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0890): the angle list, its 25-angle limit,
        # the nominal-pose rule and Clear live in
        # KrakenOS/UI/row_forms/surface_settings.py, which the Qt dialog uses too. A refusal
        # goes to the STATUS LINE here, as it always did -- not a message box.
        try:
            form = build_galvo_scan_form(self, index)
        except FormRefused as exc:
            self.status_var.set(str(exc))
            return
        render_row_form(self, form, wraplength=440)

    def open_surface_additional_settings(self, index: int | None = None) -> None:
        if index is None:
            index = self._selected_surface_row_index()
        if index is None or not (0 <= index < len(self.rows)):
            self.status_var.set("No surface selected.")
            return
        row = self.rows[index]
        if row.surface == "Grating":
            self.open_grating_settings_editor(index)
            return
        self.status_var.set(f"No additional settings are defined for {row.surface} rows.")

    def open_grating_settings_editor(self, row_index: int) -> None:
        # docs/design_qt_migration.md phase 3 (bugs/0890): the fields, the validation and Apply
        # live in KrakenOS/UI/row_forms/surface_settings.py, which the Qt dialog uses too.
        try:
            form = build_grating_settings_form(self, row_index)
        except FormRefused as exc:
            self.status_var.set(str(exc))
            return
        render_row_form(self, form, wraplength=420)
