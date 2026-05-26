"""Main layout-editor trace and display controls panel."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.widgets import grid_labeled_commit_entry


class MainTraceDisplayControlsPanel:
    """Build trace/display controls while keeping state on the owning editor."""

    def __init__(
        self,
        editor: Any,
        *,
        source_model_default: str,
        folded_detector_policy_default: str,
        folded_detector_policy_values: Sequence[str],
        wavefront_style_default: str,
        wavefront_style_values: Sequence[str],
        tolerance_compare_view_default: str,
        tolerance_compare_view_values: Sequence[str],
        analysis_path_filter_default: str,
        detector_bins_default: str,
        coherent_sum_mode_default: str,
        coherent_sum_mode_values: Sequence[str],
        branch_field_propagation_mm_default: str,
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(
            self,
            "_config",
            {
                "source_model_default": source_model_default,
                "folded_detector_policy_default": folded_detector_policy_default,
                "folded_detector_policy_values": tuple(folded_detector_policy_values),
                "wavefront_style_default": wavefront_style_default,
                "wavefront_style_values": tuple(wavefront_style_values),
                "tolerance_compare_view_default": tolerance_compare_view_default,
                "tolerance_compare_view_values": tuple(tolerance_compare_view_values),
                "analysis_path_filter_default": analysis_path_filter_default,
                "detector_bins_default": detector_bins_default,
                "coherent_sum_mode_default": coherent_sum_mode_default,
                "coherent_sum_mode_values": tuple(coherent_sum_mode_values),
                "branch_field_propagation_mm_default": branch_field_propagation_mm_default,
            },
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _commit_trace_controls(self, _event=None) -> None:
        self._sync_left_mode_controls()
        self._mark_plot_update_pending()

    def build(self, parent: tk.Widget) -> None:
        cfg = self._config
        source_model_default = cfg["source_model_default"]
        folded_detector_policy_default = cfg["folded_detector_policy_default"]
        folded_detector_policy_values = cfg["folded_detector_policy_values"]
        wavefront_style_default = cfg["wavefront_style_default"]
        wavefront_style_values = cfg["wavefront_style_values"]
        tolerance_compare_view_default = cfg["tolerance_compare_view_default"]
        tolerance_compare_view_values = cfg["tolerance_compare_view_values"]
        analysis_path_filter_default = cfg["analysis_path_filter_default"]
        detector_bins_default = cfg["detector_bins_default"]
        coherent_sum_mode_default = cfg["coherent_sum_mode_default"]
        coherent_sum_mode_values = cfg["coherent_sum_mode_values"]
        branch_field_propagation_mm_default = cfg["branch_field_propagation_mm_default"]

        for column in range(2):
            parent.columnconfigure(column, weight=1)

        ttk.Label(parent, text="Object mode").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.object_mode_var = tk.StringVar(value="Infinity")
        self.object_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.object_mode_var,
            state="readonly",
            width=12,
            values=["Finite", "Infinity"],
        )
        self.object_mode_menu.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.object_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.object_mode_menu.bind("<<ComboboxSelected>>", self._on_object_mode_changed)

        self.wavelength_var = tk.StringVar(value="0.55")
        wavelength_entry = grid_labeled_commit_entry(
            parent,
            0,
            1,
            "Wavelength [um]",
            self.wavelength_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.ray_count_var = tk.StringVar(value="31")
        ray_count_entry = grid_labeled_commit_entry(
            parent,
            2,
            0,
            "Ray fan count",
            self.ray_count_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.ray_height_factor_var = tk.StringVar(value="0.8")
        ray_height_entry = grid_labeled_commit_entry(
            parent,
            2,
            1,
            "Pupil factor",
            self.ray_height_factor_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        ttk.Label(parent, text="Analysis stop surface").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.analysis_surface_var = tk.StringVar(value="Auto")
        self.analysis_surface_menu = ttk.Combobox(
            parent,
            textvariable=self.analysis_surface_var,
            state="readonly",
            width=12,
            values=["Auto"],
        )
        self.analysis_surface_menu.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        self.analysis_surface_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.analysis_surface_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        ttk.Label(parent, text="Aperture type").grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.aperture_type_var = tk.StringVar(value="EPD")
        self.aperture_type_menu = ttk.Combobox(
            parent,
            textvariable=self.aperture_type_var,
            state="readonly",
            width=12,
            values=["STOP", "EPD", "FNO"],
        )
        self.aperture_type_menu.grid(row=7, column=0, sticky="ew")
        self.aperture_type_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.aperture_type_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        self.aperture_value_var = tk.StringVar(value="4.0")
        aperture_value_entry = grid_labeled_commit_entry(
            parent,
            6,
            1,
            "Aperture value",
            self.aperture_value_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
            entry_pady=(0, 0),
        )

        ttk.Label(parent, text="Spot view").grid(row=8, column=0, sticky="w", pady=(8, 2))
        self.spot_view_mode_var = tk.StringVar(value="Grid")
        self.spot_view_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.spot_view_mode_var,
            state="readonly",
            width=12,
            values=["Grid", "Absolute", "Centroid"],
        )
        self.spot_view_mode_menu.grid(row=9, column=0, sticky="ew")
        self.spot_view_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.spot_view_mode_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        ttk.Label(parent, text="Scene trace").grid(row=8, column=1, sticky="w", pady=(8, 2), padx=(8, 0))
        self.trace_mode_var = tk.StringVar(value=self.trace_mode)
        self.trace_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.trace_mode_var,
            state="readonly",
            width=12,
            values=["Auto", "Non-Sequential Preview", "Sequential", "Folded Preview"],
        )
        self.trace_mode_menu.grid(row=9, column=1, sticky="ew", padx=(8, 0))
        self.trace_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.trace_mode_menu.bind("<<ComboboxSelected>>", self._on_trace_mode_changed)

        ttk.Label(parent, text="NS target").grid(row=10, column=0, sticky="w", pady=(8, 2))
        self.nonseq_target_surface_var = tk.StringVar(value="Auto")
        self.nonseq_target_surface_menu = ttk.Combobox(
            parent,
            textvariable=self.nonseq_target_surface_var,
            state="readonly",
            width=12,
            values=["Auto"],
        )
        self.nonseq_target_surface_menu.grid(row=11, column=0, sticky="ew")
        self.nonseq_target_surface_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.nonseq_target_surface_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        self.nonseq_ns_limit_var = tk.StringVar(value="200")
        nonseq_limit_entry = grid_labeled_commit_entry(
            parent,
            10,
            1,
            "NS hit limit",
            self.nonseq_ns_limit_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            entry_pady=(0, 0),
        )

        ttk.Label(parent, text="Folded reach").grid(row=12, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.folded_detector_policy_var = tk.StringVar(value=folded_detector_policy_default)
        self.folded_detector_policy_menu = ttk.Combobox(
            parent,
            textvariable=self.folded_detector_policy_var,
            state="readonly",
            width=18,
            values=folded_detector_policy_values,
        )
        self.folded_detector_policy_menu.grid(row=13, column=0, columnspan=2, sticky="ew")
        self.folded_detector_policy_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.folded_detector_policy_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        nonseq_energy_check = ttk.Checkbutton(
            parent,
            text="NS probabilistic coating split",
            variable=self.nonseq_energy_probability_var,
            command=self._mark_plot_update_pending,
        )
        nonseq_energy_check.grid(row=14, column=0, columnspan=2, sticky="w", pady=(8, 0))
        nonseq_energy_check.bind("<ButtonPress-1>", self._begin_history_capture, add="+")

        ttk.Label(parent, text="Wavefront style").grid(row=15, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.wavefront_style_var = tk.StringVar(value=wavefront_style_default)
        self.wavefront_style_menu = ttk.Combobox(
            parent,
            textvariable=self.wavefront_style_var,
            state="readonly",
            width=18,
            values=wavefront_style_values,
        )
        self.wavefront_style_menu.grid(row=16, column=0, columnspan=2, sticky="ew")
        self.wavefront_style_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.wavefront_style_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        ttk.Label(parent, text="Tolerance compare").grid(row=17, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.tolerance_compare_view_var = tk.StringVar(value=tolerance_compare_view_default)
        self.tolerance_compare_view_menu = ttk.Combobox(
            parent,
            textvariable=self.tolerance_compare_view_var,
            state="readonly",
            width=18,
            values=tolerance_compare_view_values,
        )
        self.tolerance_compare_view_menu.grid(row=18, column=0, columnspan=2, sticky="ew")
        self.tolerance_compare_view_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.tolerance_compare_view_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        clipped_check = ttk.Checkbutton(
            parent,
            text="Show clipped rays",
            variable=self.show_clipped_rays_var,
            command=self._mark_plot_update_pending,
        )
        clipped_check.grid(row=19, column=0, columnspan=2, sticky="w", pady=(8, 0))
        clipped_check.bind("<ButtonPress-1>", self._begin_history_capture, add="+")

        ttk.Label(parent, text="Analysis path").grid(row=20, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.analysis_branch_filter_var = tk.StringVar(value=analysis_path_filter_default)
        self.analysis_branch_filter_menu = ttk.Combobox(
            parent,
            textvariable=self.analysis_branch_filter_var,
            state="readonly",
            width=18,
            values=[analysis_path_filter_default],
        )
        self.analysis_branch_filter_menu.grid(row=21, column=0, columnspan=2, sticky="ew")
        self.analysis_branch_filter_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.analysis_branch_filter_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        self.detector_bins_var = tk.StringVar(value=detector_bins_default)
        detector_bins_entry = grid_labeled_commit_entry(
            parent,
            22,
            0,
            "Detector bins",
            self.detector_bins_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            entry_pady=(0, 0),
        )
        detector_bins_hint = ttk.Label(parent, text="Auto or 4-512")
        detector_bins_hint.grid(row=23, column=1, sticky="w", padx=(8, 0))
        ttk.Label(parent, text="Coherent sum").grid(row=24, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self.coherent_sum_mode_var = tk.StringVar(value=coherent_sum_mode_default)
        self.coherent_sum_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.coherent_sum_mode_var,
            state="readonly",
            width=18,
            values=coherent_sum_mode_values,
        )
        self.coherent_sum_mode_menu.grid(row=25, column=0, columnspan=2, sticky="ew")
        self.coherent_sum_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.coherent_sum_mode_menu.bind("<<ComboboxSelected>>", self._mark_plot_update_pending)

        self.branch_field_propagation_mm_var = tk.StringVar(value=branch_field_propagation_mm_default)
        branch_field_propagation_entry = grid_labeled_commit_entry(
            parent,
            26,
            0,
            "BField z [mm]",
            self.branch_field_propagation_mm_var,
            on_commit=self._commit_trace_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            entry_pady=(0, 0),
        )
        branch_field_propagation_hint = ttk.Label(parent, text="0 = detector plane")
        branch_field_propagation_hint.grid(row=27, column=1, sticky="w", padx=(8, 0))

        self.show_cardinals_var = tk.BooleanVar(value=True)
        self.show_physical_distances_var = tk.BooleanVar(value=False)

        self._register_left_mode_control(
            "object_mode_var",
            self.object_mode_menu,
            lambda: self._current_source_model() == source_model_default,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "wavelength_var",
            wavelength_entry,
            lambda: True,
        )
        self._register_left_mode_control(
            "ray_count_var",
            ray_count_entry,
            lambda: True,
        )
        self._register_left_mode_control(
            "ray_height_factor_var",
            ray_height_entry,
            lambda: self._current_source_model() == source_model_default,
        )
        self._register_left_mode_control(
            "analysis_surface_var",
            self.analysis_surface_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "aperture_type_var",
            self.aperture_type_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "aperture_value_var",
            aperture_value_entry,
            lambda: True,
        )
        self._register_left_mode_control(
            "spot_view_mode_var",
            self.spot_view_mode_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "trace_mode_var",
            self.trace_mode_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "nonseq_target_surface_var",
            self.nonseq_target_surface_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "nonseq_ns_limit_var",
            nonseq_limit_entry,
            lambda: True,
        )
        self._register_left_mode_control(
            "folded_detector_policy_var",
            self.folded_detector_policy_menu,
            lambda: self._folded_detector_policy_control_enabled(),
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "nonseq_energy_probability_var",
            nonseq_energy_check,
            lambda: True,
            include_label=False,
        )
        self._register_left_mode_control(
            "wavefront_style_var",
            self.wavefront_style_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "tolerance_compare_view_var",
            self.tolerance_compare_view_menu,
            lambda: "tolerance_compare" in getattr(self, "selected_analysis_modes", []),
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "show_clipped_rays_var",
            clipped_check,
            lambda: True,
            include_label=False,
        )
        self._register_left_mode_control(
            "analysis_branch_filter_var",
            self.analysis_branch_filter_menu,
            lambda: True,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "detector_bins_var",
            detector_bins_entry,
            lambda: any(
                mode in {"detector_map", "coherent_detector", "branch_field", "diffraction_detector"}
                for mode in getattr(self, "selected_analysis_modes", [])
            ),
            extra_widgets=(detector_bins_hint,),
        )
        self._register_left_mode_control(
            "coherent_sum_mode_var",
            self.coherent_sum_mode_menu,
            lambda: any(
                mode in {"coherent_detector", "branch_field", "diffraction_detector"}
                for mode in getattr(self, "selected_analysis_modes", [])
            ),
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "branch_field_propagation_mm_var",
            branch_field_propagation_entry,
            lambda: "branch_field" in getattr(self, "selected_analysis_modes", []),
            extra_widgets=(branch_field_propagation_hint,),
        )
