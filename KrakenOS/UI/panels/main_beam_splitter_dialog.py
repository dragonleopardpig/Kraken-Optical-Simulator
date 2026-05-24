"""Beam splitter settings dialog for the main layout editor."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any, Callable


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
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Beam Splitter", f"Could not read the surface table:\n\n{exc}", parent=self.editor)
            return

        if row_index is None:
            row_index = self._selected_surface_row_index()
        if row_index is None or row_index < 0 or row_index >= len(self.rows):
            messagebox.showinfo("Beam Splitter", "Select a Beam Splitter row first.", parent=self.editor)
            return

        row = self.rows[row_index]
        if row.surface != self.beam_splitter_surface:
            messagebox.showinfo("Beam Splitter", "Beam splitter settings apply only to Beam Splitter rows.", parent=self.editor)
            return

        advanced = dict(row.advanced or {})
        settings = self.normalize_beam_splitter_settings(advanced.get(self.beam_splitter_advanced_attr))
        window = tk.Toplevel(self.editor)
        window.withdraw()
        window.title(f"Beam Splitter - S{row_index}: {row.name}")
        window.geometry("860x520")
        window.minsize(740, 430)
        window.transient(self.editor)
        window.columnconfigure(0, weight=1)
        window.rowconfigure(1, weight=1)

        header = ttk.Frame(window, padding=(10, 10, 10, 4))
        header.grid(row=0, column=0, sticky="ew")
        ttk.Label(
            header,
            text=(
                "Beam Splitter can spawn deterministic transmitted and reflected child paths in "
                "Non-Sequential Preview. For a finite plate, use this row as the coated front face, "
                "set Glass to the substrate and Thickness to the plate thickness, then add a following "
                "Standard rear face with Glass=AIR and the same TiltX for a parallel plate. "
                "Use a different rear tilt to model a wedge. Deterministic coating table mode reads "
                "the row Coating table at trace wavelength and incidence angle. Fresnel P/S mode uses "
                "KrakenOS dielectric/metal P and S coefficients with a scalar P-polarization fraction."
            ),
            foreground="#475569",
            wraplength=740,
            justify="left",
        ).grid(row=0, column=0, sticky="ew")

        body = ttk.Frame(window, padding=(10, 4, 10, 8))
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.columnconfigure(3, weight=1)

        split_mode_var = tk.StringVar(master=window, value=str(settings["split_mode"]))
        reflectance_var = tk.StringVar(master=window, value=f"{float(settings['reflectance']):.6g}")
        absorption_var = tk.StringVar(master=window, value=f"{float(settings['absorption']):.6g}")
        p_fraction_var = tk.StringVar(master=window, value=f"{float(settings['polarization_p_fraction']):.6g}")
        s_phase_var = tk.StringVar(master=window, value=f"{float(settings['polarization_s_phase_deg']):.6g}")
        transmit_phase_var = tk.StringVar(master=window, value=f"{float(settings['transmit_phase_deg']):.6g}")
        reflect_phase_var = tk.StringVar(master=window, value=f"{float(settings['reflect_phase_deg']):.6g}")
        transmit_s_phase_var = tk.StringVar(master=window, value=f"{float(settings['transmit_s_phase_deg']):.6g}")
        reflect_s_phase_var = tk.StringVar(master=window, value=f"{float(settings['reflect_s_phase_deg']):.6g}")
        min_power_var = tk.StringVar(master=window, value=f"{float(settings['min_branch_power']):.6g}")
        max_depth_var = tk.StringVar(master=window, value=str(int(settings["max_branch_depth"])))
        summary_var = tk.StringVar(master=window, value="")

        ttk.Label(body, text="Split mode").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=3)
        ttk.Combobox(body, textvariable=split_mode_var, state="readonly", values=self.beam_splitter_split_modes, width=30).grid(
            row=0, column=1, columnspan=3, sticky="ew", pady=3
        )
        fields = (
            ("Reflectance R", reflectance_var, "Fixed mode value; fallback for coating-table mode."),
            ("Absorption A", absorption_var, "Fixed mode value; fallback for coating-table mode."),
            ("P fraction", p_fraction_var, "Fresnel P/S mode: 1.0 pure P, 0.0 pure S, 0.5 equal P/S."),
            ("S phase [deg]", s_phase_var, "Relative S component phase for Jones metadata; 90 deg gives circular at Pfrac=0.5."),
            ("T phase [deg]", transmit_phase_var, "Metadata used by current coherent-detector diagnostics."),
            ("R phase [deg]", reflect_phase_var, "Metadata used by current coherent-detector diagnostics."),
            ("T S-ret [deg]", transmit_s_phase_var, "Extra transmitted S phase relative to P after Fresnel/coating split."),
            ("R S-ret [deg]", reflect_s_phase_var, "Extra reflected S phase relative to P after Fresnel/coating split."),
            ("Min path power", min_power_var, "Deterministic pruning threshold."),
            ("Max path depth", max_depth_var, "Deterministic recursion cap."),
        )
        field_rows = (len(fields) + 1) // 2
        hint_base_row = 1 + field_rows
        for idx, (label, var, hint) in enumerate(fields, start=1):
            col = 0 if idx % 2 else 2
            row_num = 1 + (idx - 1) // 2
            ttk.Label(body, text=label).grid(row=row_num, column=col, sticky="w", padx=(0 if col == 0 else 12, 8), pady=3)
            ttk.Entry(body, textvariable=var, width=14).grid(row=row_num, column=col + 1, sticky="ew", pady=3)
            ttk.Label(body, text=hint, foreground="#6b7280").grid(
                row=hint_base_row + (idx - 1) // 2,
                column=col,
                columnspan=2,
                sticky="w",
                padx=(0 if col == 0 else 12, 0),
                pady=(3, 0),
            )

        footer = ttk.Frame(window, padding=(10, 0, 10, 10))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=summary_var, foreground="#5f6b7a").pack(side="left", fill="x", expand=True)

        def collect_settings() -> dict[str, object]:
            return self.normalize_beam_splitter_settings(
                {
                    "split_mode": split_mode_var.get().strip(),
                    "reflectance": float(reflectance_var.get()),
                    "absorption": float(absorption_var.get()),
                    "polarization_p_fraction": float(p_fraction_var.get()),
                    "polarization_s_phase_deg": float(s_phase_var.get()),
                    "transmit_phase_deg": float(transmit_phase_var.get()),
                    "reflect_phase_deg": float(reflect_phase_var.get()),
                    "transmit_s_phase_deg": float(transmit_s_phase_var.get()),
                    "reflect_s_phase_deg": float(reflect_s_phase_var.get()),
                    "min_branch_power": float(min_power_var.get()),
                    "max_branch_depth": int(float(max_depth_var.get())),
                }
            )

        def validate_values(*, show_success: bool = True) -> list[str]:
            try:
                candidate = collect_settings()
            except Exception as exc:
                summary_var.set(f"Validation failed: {self.short_error_message(exc)}")
                return [str(exc)]
            errors = self.validate_beam_splitter_settings(candidate)
            if errors:
                summary_var.set(f"Validation failed: {errors[0]}")
            elif show_success:
                summary_var.set("Validation passed: " + self.beam_splitter_summary(candidate))
            return errors

        def apply_values() -> None:
            try:
                candidate = collect_settings()
            except Exception as exc:
                messagebox.showerror("Beam Splitter", str(exc), parent=window)
                return
            errors = self.validate_beam_splitter_settings(candidate)
            if errors:
                messagebox.showerror(
                    "Beam Splitter Validation",
                    "Fix these values before applying:\n\n" + "\n".join(f"- {error}" for error in errors),
                    parent=window,
                )
                return
            self._begin_history_capture()
            new_advanced = dict(self.rows[row_index].advanced or {})
            new_advanced[self.beam_splitter_advanced_attr] = candidate
            new_advanced["Coating"] = self.beam_splitter_coating_for_settings(candidate, new_advanced.get("Coating"))
            self.rows[row_index].advanced = new_advanced
            self.rows[row_index].surface = self.beam_splitter_surface
            if str(self.rows[row_index].glass).upper() == "MIRROR":
                self.rows[row_index].glass = "AIR"
            self._sync_table()
            self._select_table_row(row_index)
            self._commit_history_capture()
            self._mark_plot_update_pending()
            self.status_var.set(f"Updated beam splitter S{row_index}: {self.beam_splitter_summary(candidate)}. Click Update.")
            window.destroy()

        validate_values(show_success=True)
        ttk.Button(footer, text="Validate", command=lambda: validate_values(show_success=True)).pack(side="right", padx=(0, 8))
        ttk.Button(footer, text="Apply", command=apply_values).pack(side="right")
        ttk.Button(footer, text="Cancel", command=window.destroy).pack(side="right", padx=(0, 8))
        self._show_centered_dialog(window)
