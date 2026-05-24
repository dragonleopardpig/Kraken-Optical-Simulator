"""Main layout-editor atmosphere controls and dialog."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any


ATMOSPHERE_CONTROL_SPECS = (
    ("Min wavelength [um]", "atmos_wavelength_min_var", "0.45"),
    ("Max wavelength [um]", "atmos_wavelength_max_var", "0.75"),
    ("Samples", "atmos_wavelength_count_var", "11"),
    ("Zenith angle [deg]", "atmos_zenith_deg_var", "45.0"),
    ("Temperature [K]", "atmos_temperature_k_var", "283.15"),
    ("Pressure [Pa]", "atmos_pressure_pa_var", "101300"),
    ("Humidity [0-1]", "atmos_humidity_var", "0.5"),
    ("CO2 [ppm]", "atmos_co2_ppm_var", "400"),
    ("Latitude [deg]", "atmos_latitude_deg_var", "31.0"),
    ("Altitude [m]", "atmos_altitude_m_var", "2800"),
)


class MainAtmospherePanel:
    """Build atmosphere controls while keeping settings on the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        atmos_plot_mode_default: str,
        atmos_plot_mode_values: Sequence[str],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "atmos_plot_mode_default", atmos_plot_mode_default)
        object.__setattr__(self, "atmos_plot_mode_values", tuple(atmos_plot_mode_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "atmos_plot_mode_default", "atmos_plot_mode_values"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def build_hidden_panel(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1)

        ttk.Label(parent, text="Observatory preset").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.atmos_observatory_var = tk.StringVar(value="Manual")
        self.atmos_observatory_menu = ttk.Combobox(
            parent,
            textvariable=self.atmos_observatory_var,
            state="readonly",
            width=16,
            values=self._atmos_observatory_names(),
        )
        self.atmos_observatory_menu.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.atmos_observatory_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.atmos_observatory_menu.bind("<<ComboboxSelected>>", self._on_atmos_observatory_changed)

        ttk.Label(parent, text="Atmos plot").grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.atmos_plot_mode_var = tk.StringVar(value=self.atmos_plot_mode_default)
        self.atmos_plot_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.atmos_plot_mode_var,
            state="readonly",
            width=16,
            values=self.atmos_plot_mode_values,
        )
        self.atmos_plot_mode_menu.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.atmos_plot_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.atmos_plot_mode_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        entries: list[ttk.Entry] = []
        for index, (label, attr_name, default) in enumerate(ATMOSPHERE_CONTROL_SPECS):
            row = 4 + (index // 2) * 2
            column = index % 2
            ttk.Label(parent, text=label).grid(
                row=row,
                column=column,
                sticky="w",
                pady=(0 if row == 0 else 6, 2),
                padx=(8 if column else 0, 0),
            )
            var = tk.StringVar(value=default)
            setattr(self, attr_name, var)
            entry = ttk.Entry(parent, textvariable=var, width=12)
            entry.grid(row=row + 1, column=column, sticky="ew", padx=(8 if column else 0, 0))
            entries.append(entry)

        self.atmosphere_summary_var = tk.StringVar(value="")
        ttk.Label(
            parent,
            textvariable=self.atmosphere_summary_var,
            foreground="#3f4a5a",
            wraplength=460,
            justify="left",
        ).grid(row=14, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        for entry in entries:
            self._bind_deferred_manual_update(entry)
        for _label, attr_name, _default in ATMOSPHERE_CONTROL_SPECS:
            var = getattr(self, attr_name)
            var.trace_add("write", lambda *_args: self._update_atmosphere_summary())
        self.atmos_plot_mode_var.trace_add("write", lambda *_args: self._update_atmosphere_summary())
        self._update_atmosphere_summary()

    def open_settings_dialog(self) -> None:
        window = self.__dict__.get("_atmosphere_settings_window")
        if window is not None:
            try:
                if window.winfo_exists():
                    window.deiconify()
                    window.lift()
                    window.focus_force()
                    return
            except Exception:
                pass

        window = tk.Toplevel(self.editor)
        self._atmosphere_settings_window = window
        window.title("Atmospheric Settings")
        window.transient(self.editor)
        window.protocol("WM_DELETE_WINDOW", self.close_settings_dialog)
        window.columnconfigure(0, weight=1)

        root = ttk.Frame(window, padding=12)
        root.grid(row=0, column=0, sticky="nsew")
        for column in range(2):
            root.columnconfigure(column, weight=1)

        ttk.Label(
            root,
            text=(
                "Atmospheric refraction/dispersion settings are advanced analysis inputs. "
                "Use the Atmos analysis button after changing these values."
            ),
            foreground="#475569",
            wraplength=520,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Label(root, text="Observatory preset").grid(row=1, column=0, sticky="w", pady=(0, 2))
        observatory_menu = ttk.Combobox(
            root,
            textvariable=self.atmos_observatory_var,
            state="readonly",
            values=self._atmos_observatory_names(),
            width=20,
        )
        observatory_menu.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        observatory_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        observatory_menu.bind("<<ComboboxSelected>>", self._on_atmos_observatory_changed)

        ttk.Label(root, text="Atmos plot").grid(row=3, column=0, sticky="w", pady=(0, 2))
        plot_menu = ttk.Combobox(
            root,
            textvariable=self.atmos_plot_mode_var,
            state="readonly",
            values=self.atmos_plot_mode_values,
            width=20,
        )
        plot_menu.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        plot_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        plot_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        for index, (label, attr_name, _default) in enumerate(ATMOSPHERE_CONTROL_SPECS):
            row = 5 + (index // 2) * 2
            column = index % 2
            ttk.Label(root, text=label).grid(
                row=row,
                column=column,
                sticky="w",
                pady=(6, 2),
                padx=(8 if column else 0, 0),
            )
            entry = ttk.Entry(root, textvariable=getattr(self, attr_name), width=14)
            entry.grid(row=row + 1, column=column, sticky="ew", padx=(8 if column else 0, 0))
            self._bind_deferred_manual_update(entry)

        ttk.Label(
            root,
            textvariable=self.atmosphere_summary_var,
            foreground="#3f4a5a",
            wraplength=520,
            justify="left",
        ).grid(row=16, column=0, columnspan=2, sticky="ew", pady=(10, 0))

        buttons = ttk.Frame(root)
        buttons.grid(row=17, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(
            buttons,
            text="Apply",
            command=lambda: (self._update_atmosphere_summary(), self._mark_plot_update_pending()),
        ).pack(side="left")
        ttk.Button(
            buttons,
            text="Apply + Atmos",
            command=lambda: (
                self._update_atmosphere_summary(),
                None if "atmosphere" in self.selected_analysis_modes else self.toggle_analysis_mode("atmosphere"),
                self._mark_plot_update_pending(),
            ),
        ).pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Close", command=self.close_settings_dialog).pack(side="left", padx=(8, 0))

        self._show_centered_dialog(window)

    def close_settings_dialog(self) -> None:
        window = self.__dict__.get("_atmosphere_settings_window")
        self._atmosphere_settings_window = None
        if window is not None:
            try:
                window.destroy()
            except Exception:
                pass
