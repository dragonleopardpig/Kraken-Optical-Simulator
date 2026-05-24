"""Main layout-editor optimization panel."""

from __future__ import annotations

import os
import tkinter as tk
from collections.abc import Iterable
from tkinter import ttk
from typing import Any


class MainOptimizationPanel:
    """Build optimization controls while keeping optimizer state on the editor."""

    def __init__(self, editor: Any, *, operand_specs: Iterable[Any]) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "operand_specs", tuple(operand_specs))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "operand_specs"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def edit_current_bounds(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        current = spec.get_bounds(row)
        current_value = spec.value_from_row(row)
        default_bounds = current or spec.default_bounds(current_value)

        dialog = tk.Toplevel(self)
        dialog.withdraw()
        dialog.title(f"Bounds for {row.name} {spec.label}")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        ttk.Label(dialog, text="Lower").grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")
        lower_var = tk.StringVar(value=f"{default_bounds[0]:g}")
        ttk.Entry(dialog, textvariable=lower_var, width=16).grid(row=1, column=0, padx=12, pady=(0, 8))

        ttk.Label(dialog, text="Upper").grid(row=2, column=0, padx=12, pady=(0, 4), sticky="w")
        upper_var = tk.StringVar(value=f"{default_bounds[1]:g}")
        ttk.Entry(dialog, textvariable=upper_var, width=16).grid(row=3, column=0, padx=12, pady=(0, 12))

        def accept():
            try:
                lower = float(lower_var.get())
                upper = float(upper_var.get())
            except ValueError:
                self.append_debug("Invalid optimization bounds entry.")
                return
            if lower >= upper:
                self.append_debug("Optimization bounds rejected: lower must be less than upper.")
                return
            self._begin_history_capture()
            spec.set_bounds(row, (lower, upper))
            self._commit_history_capture()
            self.append_progress(
                f"Bounds set for row {index} {spec.label}: [{lower:g}, {upper:g}]"
            )
            dialog.destroy()

        buttons = ttk.Frame(dialog)
        buttons.grid(row=4, column=0, padx=12, pady=(0, 12), sticky="w")
        ttk.Button(buttons, text="Save", command=accept).pack(side="left")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

        self._show_centered_dialog(dialog)
        self.wait_window(dialog)
        self._cleanup_current_popup_menu()


    def build(self, parent: tk.Widget) -> None:
        specs = self.operand_specs
        operand_list_width = max((len(spec.label) for spec in specs), default=14) + 2
        operand_list_minsize = max(150, operand_list_width * 8)
        parent.columnconfigure(0, weight=0, minsize=operand_list_minsize)
        parent.columnconfigure(1, weight=1, minsize=220)

        button_row = ttk.Frame(parent)
        button_row.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(button_row, text="Start Optimization", command=self.start_optimization).pack(side="left")
        ttk.Button(button_row, text="Stop", command=self.stop_optimization).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Check Backend", command=self.check_optimization_backend).pack(
            side="left",
            padx=(8, 0),
        )
        cpu_total = max(1, int(os.cpu_count() or 1))
        worker_choices = ["Auto", "1"]
        for candidate in (2, 4, 6, 8, 12, 16, cpu_total):
            candidate = max(1, min(cpu_total, int(candidate)))
            text = str(candidate)
            if text not in worker_choices:
                worker_choices.append(text)
        ttk.Label(button_row, text="Workers").pack(side="left", padx=(14, 0))
        self.optimization_workers_var = tk.StringVar(value="Auto")
        ttk.Combobox(
            button_row,
            textvariable=self.optimization_workers_var,
            state="readonly",
            width=6,
            values=worker_choices,
        ).pack(side="left", padx=(6, 0))

        ttk.Label(parent, text="Merit operands").grid(row=1, column=0, sticky="w", pady=(0, 2))
        self.merit_mode_list = tk.Listbox(
            parent,
            exportselection=False,
            selectmode="extended",
            height=min(4, max(2, len(specs))),
            width=operand_list_width,
        )
        for spec in specs:
            self.merit_mode_list.insert("end", spec.label)
        if specs:
            self.merit_mode_list.selection_set(0)
        self.merit_mode_list.grid(row=2, column=0, sticky="nsw", pady=(0, 8), padx=(0, 8))
        self.merit_mode_list.bind("<ButtonPress-1>", self._begin_history_capture, add="+")
        self.merit_mode_list.bind("<<ListboxSelect>>", lambda _e: self._update_operand_setup_visibility())

        setup_holder = ttk.Frame(parent, height=320)
        setup_holder.grid(row=2, column=1, sticky="nsew", pady=(0, 8), padx=(4, 0))
        setup_holder.grid_propagate(False)
        setup_holder.columnconfigure(0, weight=1)
        setup_holder.rowconfigure(0, weight=1)

        setup_frame = ttk.Frame(setup_holder)
        setup_frame.grid(row=0, column=0, sticky="nsew")
        setup_frame.columnconfigure(0, weight=1, minsize=220)
        ttk.Label(setup_frame, text="Operand setup").grid(row=0, column=0, sticky="w", pady=(0, 2))

        for idx, spec in enumerate(specs, start=1):
            card = ttk.LabelFrame(setup_frame, text=spec.label, padding=6)
            card.grid(row=idx, column=0, sticky="ew", pady=(0, 8))
            card.columnconfigure(1, weight=1, minsize=120)
            control_widgets: dict[str, tuple[tk.Widget, ...]] = {}

            weight_var = tk.StringVar(value=f"{spec.default_weight:g}")
            self.operand_weight_vars[spec.label] = weight_var
            weight_label = ttk.Label(card, text="Weight")
            weight_label.grid(row=0, column=0, sticky="w")
            weight_entry = ttk.Entry(card, textvariable=weight_var, width=12)
            weight_entry.grid(row=0, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
            self._bind_deferred_refresh(weight_entry)
            control_widgets["weight"] = (weight_label, weight_entry)

            target_var = tk.StringVar(value=f"{spec.default_target:g}")
            self.operand_target_vars[spec.label] = target_var
            target_label = ttk.Label(card, text="Target")
            target_label.grid(row=1, column=0, sticky="w")
            target_entry = ttk.Entry(card, textvariable=target_var, width=12)
            target_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
            self._bind_deferred_refresh(target_entry)
            control_widgets["target"] = (target_label, target_entry)

            wavelength_var = tk.StringVar(value=self.wavelength_var.get())
            self.operand_wavelength_vars[spec.label] = wavelength_var
            wavelength_label = ttk.Label(card, text="Wvl")
            wavelength_label.grid(row=2, column=0, sticky="w")
            wavelength_entry = ttk.Entry(card, textvariable=wavelength_var, width=12)
            wavelength_entry.grid(row=2, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
            self._bind_deferred_refresh(wavelength_entry)
            control_widgets["wavelength"] = (wavelength_label, wavelength_entry)

            field_var = tk.StringVar(value="0")
            self.operand_field_vars[spec.label] = field_var
            field_label = ttk.Label(card, text="Field")
            field_label.grid(row=3, column=0, sticky="w")
            field_entry = ttk.Entry(card, textvariable=field_var, width=12)
            field_entry.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
            self._bind_deferred_refresh(field_entry)
            control_widgets["field"] = (field_label, field_entry)

            surface_row = 4
            frequency_row = 6
            mode_row = 7
            algorithm_row = 8

            if spec.label == "MTF @ freq":
                field_x_var = tk.StringVar(value="0")
                field_y_var = tk.StringVar(value="0")
                self.operand_field_x_vars[spec.label] = field_x_var
                self.operand_field_y_vars[spec.label] = field_y_var
                field_x_label = ttk.Label(card, text="Field X")
                field_x_label.grid(row=3, column=0, sticky="w")
                field_x_entry = ttk.Entry(card, textvariable=field_x_var, width=12)
                field_x_entry.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
                self._bind_deferred_refresh(field_x_entry)
                field_y_label = ttk.Label(card, text="Field Y(s)")
                field_y_label.grid(row=4, column=0, sticky="w")
                field_y_entry = ttk.Entry(card, textvariable=field_y_var, width=12)
                field_y_entry.grid(row=4, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
                self._bind_deferred_refresh(field_y_entry)
                control_widgets["field_xy"] = (field_x_label, field_x_entry, field_y_label, field_y_entry)
                field_label.grid_remove()
                field_entry.grid_remove()
                surface_row = 5
                frequency_row = 6
                mode_row = 7
                algorithm_row = 8

            surface_var = tk.StringVar(value="Auto")
            self.operand_surface_vars[spec.label] = surface_var
            surface_label = ttk.Label(card, text="Surf")
            surface_label.grid(row=surface_row, column=0, sticky="w")
            surface_menu = ttk.Combobox(card, textvariable=surface_var, state="readonly", width=12, values=["Auto"])
            surface_menu.grid(row=surface_row, column=1, sticky="ew", padx=(6, 0), pady=(0, 4))
            surface_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
            surface_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)
            control_widgets["surface"] = (surface_label, surface_menu)

            if spec.label == "MTF @ freq":
                frequency_var = tk.StringVar(value="5")
                self.operand_frequency_vars[spec.label] = frequency_var
                frequency_label = ttk.Label(card, text="Freq")
                frequency_label.grid(row=frequency_row, column=0, sticky="w")
                frequency_entry = ttk.Entry(card, textvariable=frequency_var, width=12)
                frequency_entry.grid(row=frequency_row, column=1, sticky="ew", padx=(6, 0), pady=(0, 0))
                self._bind_deferred_refresh(frequency_entry)
                control_widgets["frequency"] = (frequency_label, frequency_entry)

                mtf_mode_var = tk.StringVar(value="Average")
                self.operand_mtf_mode_vars[spec.label] = mtf_mode_var
                mode_label = ttk.Label(card, text="Mode")
                mode_label.grid(row=mode_row, column=0, sticky="w")
                mtf_mode_menu = ttk.Combobox(
                    card,
                    textvariable=mtf_mode_var,
                    state="readonly",
                    width=12,
                    values=["Average", "Tangential", "Sagittal"],
                )
                mtf_mode_menu.grid(row=mode_row, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
                mtf_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
                mtf_mode_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)
                control_widgets["mtf_mode"] = (mode_label, mtf_mode_menu)

                mtf_algorithm_var = tk.StringVar(value="Diffraction FFT")
                self.operand_mtf_algorithm_vars[spec.label] = mtf_algorithm_var
                algorithm_label = ttk.Label(card, text="Alg")
                algorithm_label.grid(row=algorithm_row, column=0, sticky="w")
                mtf_algorithm_menu = ttk.Combobox(
                    card,
                    textvariable=mtf_algorithm_var,
                    state="readonly",
                    width=12,
                    values=["Diffraction FFT", "PSF FFT", "LSF FFT"],
                )
                mtf_algorithm_menu.grid(row=algorithm_row, column=1, sticky="ew", padx=(6, 0), pady=(4, 0))
                mtf_algorithm_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
                mtf_algorithm_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)
                control_widgets["mtf_algorithm"] = (algorithm_label, mtf_algorithm_menu)

            self.operand_control_widgets[spec.label] = control_widgets
            self.operand_setup_frames[spec.label] = card
            self._apply_operand_control_visibility(spec.label)

        self._update_operand_setup_visibility()
