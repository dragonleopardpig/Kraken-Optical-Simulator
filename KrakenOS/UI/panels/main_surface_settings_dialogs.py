"""Specialized surface settings dialogs for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable

import numpy as np


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
        if index is None:
            index = self._selected_surface_row_index()
        if index is None or not (0 <= index < len(self.rows)):
            self.status_var.set("No mirror row selected.")
            return
        row = self.rows[index]
        if row.surface != "Mirror":
            self.status_var.set("Galvo scan overlay applies to Mirror rows.")
            return

        display_settings = dict((row.advanced or {}).get("Display2D", {}) or {})
        existing = display_settings.get(self.galvo_scan_overlay_key)
        current_slant = self._mirror_display_slant_deg_for_rows(self.rows, index)
        existing_slants = self._mirror_overlay_display_slants_for_rows(self.rows, index) if existing is not None else []
        default_text = self.format_float_sequence(existing_slants) if existing_slants else f"{current_slant - 5:g}, {current_slant:g}, {current_slant + 5:g}"

        window = tk.Toplevel(self.editor)
        window.title(f"Galvo Scan Overlay - S{index}: {row.name}")
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)

        ttk.Label(
            frame,
            text=(
                "TiltX overlay values [deg], using the same mirror angle shown in the table. Use comma values or start:stop:step, "
                "for example -50,-45,-40 for a -10, 0, +10 degree optical scan; -55,-45,-35 is the Figure 8 full field."
            ),
            wraplength=440,
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))
        values_var = tk.StringVar(value=default_text)
        entry = ttk.Entry(frame, textvariable=values_var, width=46)
        entry.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(
            frame,
            text="You can also type these values directly into the mirror TiltX table cell. The middle value becomes the nominal pose; the full list is display-only scan overlay.",
            wraplength=440,
        ).grid(row=2, column=0, sticky="ew", pady=(0, 10))

        buttons = ttk.Frame(frame)
        buttons.grid(row=3, column=0, sticky="e")

        def set_values(values: list[float]) -> None:
            self._begin_history_capture()
            target = self.rows[index]
            branch_angle = self._mirror_branch_angle_before_index(self.rows, index)
            if values:
                local_values = [
                    self._mirror_local_tilt_deg_from_display(branch_angle, display_value)
                    for display_value in values
                ]
                target.tilt_x = float(local_values[len(local_values) // 2])
                advanced = self._advanced_with_galvo_scan_overlay(target.advanced, local_values)
                status = f"Galvo scan overlay set to {self.format_float_sequence(values)} deg. Click Update."
            else:
                advanced = self._advanced_with_galvo_scan_overlay(target.advanced, [])
                status = "Galvo scan overlay cleared. Click Update."
            target.advanced = advanced
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(status)
            window.destroy()

        def apply_values() -> None:
            try:
                values = self.parse_float_sequence_text(values_var.get())
            except Exception as exc:
                messagebox.showerror("Galvo scan overlay", f"Invalid TiltX list:\n\n{self.short_error_message(exc)}", parent=window)
                return
            if len(values) > 25:
                messagebox.showerror("Galvo scan overlay", "Use 25 or fewer overlay angles to keep the plot readable.", parent=window)
                return
            set_values(values)

        ttk.Button(buttons, text="Clear", command=lambda: set_values([])).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Apply", command=apply_values).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=window.destroy).pack(side="left", padx=(8, 0))
        entry.focus_set()
        entry.selection_range(0, "end")
        self._show_centered_dialog(window)

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
        if not (0 <= row_index < len(self.rows)):
            return
        row = self.rows[row_index]
        window = tk.Toplevel(self.editor)
        window.title(f"Grating Settings - S{row_index}: {row.name}")
        window.transient(self.editor)
        window.columnconfigure(1, weight=1)
        frame = ttk.Frame(window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        frame.columnconfigure(1, weight=1)
        ttk.Label(
            frame,
            text="These grating-only fields are stored on the row but no longer occupy main-table columns.",
            wraplength=420,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        field_specs = (
            ("diff_ord", "Diffraction order"),
            ("grating_d", "Pitch [um]"),
            ("grating_angle", "Line angle [deg]"),
        )
        variables: dict[str, tk.StringVar] = {}
        for grid_row, (field, label) in enumerate(field_specs, start=1):
            ttk.Label(frame, text=label).grid(row=grid_row, column=0, sticky="w", padx=(0, 10), pady=3)
            variable = tk.StringVar(value=self._format_table_float(getattr(row, field)))
            variables[field] = variable
            ttk.Entry(frame, textvariable=variable, width=18).grid(row=grid_row, column=1, sticky="ew", pady=3)

        validation_var = tk.StringVar(value="Right-click the Grating name cell to reopen this dialog.")
        ttk.Label(frame, textvariable=validation_var, foreground="#475569", wraplength=420).grid(
            row=len(field_specs) + 1,
            column=0,
            columnspan=2,
            sticky="w",
            pady=(10, 0),
        )

        def parsed_values() -> dict[str, float] | None:
            parsed: dict[str, float] = {}
            for field, label in field_specs:
                text = variables[field].get().strip()
                try:
                    value = float(text)
                except ValueError:
                    validation_var.set(f"{label} expects a number.")
                    return None
                if not np.isfinite(value):
                    validation_var.set(f"{label} must be finite.")
                    return None
                parsed[field] = value
            if abs(parsed["grating_d"]) < 1e-12:
                validation_var.set("Pitch [um] must be non-zero.")
                return None
            validation_var.set("Validation passed.")
            return parsed

        def apply_values() -> None:
            parsed = parsed_values()
            if parsed is None:
                return
            self._begin_history_capture()
            target = self.rows[row_index]
            target.diff_ord = parsed["diff_ord"]
            target.grating_d = parsed["grating_d"]
            target.grating_angle = parsed["grating_angle"]
            self._sync_table()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated grating settings for S{row_index}: {target.name}. Click Update.")
            window.destroy()

        footer = ttk.Frame(frame)
        footer.grid(row=len(field_specs) + 2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(footer, text="Validate", command=parsed_values).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
