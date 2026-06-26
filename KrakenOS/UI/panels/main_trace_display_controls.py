"""Main layout-editor trace and display controls panel."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.source_trace_helpers import (
    RAY_FAN_COUNT_DEFAULT,
    RAY_FAN_COUNT_VALUES,
)
from KrakenOS.UI.widgets import (
    grid_commit_checkbutton,
    grid_labeled_commit_combobox,
    grid_labeled_commit_entry,
)


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

        self.object_mode_var = tk.StringVar(value="Infinity")
        self.object_mode_menu = grid_labeled_commit_combobox(
            parent,
            0,
            0,
            "Object mode",
            self.object_mode_var,
            values=["Finite", "Infinity"],
            on_commit=self._on_object_mode_changed,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

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

        self.ray_count_var = tk.StringVar(value=RAY_FAN_COUNT_DEFAULT)
        ray_count_entry = grid_labeled_commit_combobox(
            parent,
            2,
            0,
            "Ray fan count",
            self.ray_count_var,
            values=RAY_FAN_COUNT_VALUES,
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

        self.analysis_surface_var = tk.StringVar(value="Auto")
        self.analysis_surface_menu = grid_labeled_commit_combobox(
            parent,
            4,
            0,
            "Analysis stop surface",
            self.analysis_surface_var,
            values=["Auto"],
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.aperture_type_var = tk.StringVar(value="EPD")
        self.aperture_type_menu = grid_labeled_commit_combobox(
            parent,
            6,
            0,
            "Aperture type",
            self.aperture_type_var,
            values=["STOP", "EPD", "FNO"],
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=12,
            combo_pady=(0, 0),
        )

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

        self.spot_view_mode_var = tk.StringVar(value="Grid")
        self.spot_view_mode_menu = grid_labeled_commit_combobox(
            parent,
            8,
            0,
            "Spot view",
            self.spot_view_mode_var,
            values=["Grid", "Absolute", "Centroid"],
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            combo_pady=(0, 0),
        )

        self.trace_mode_var = tk.StringVar(value=self.trace_mode)
        self.trace_mode_menu = grid_labeled_commit_combobox(
            parent,
            8,
            1,
            "Scene trace",
            self.trace_mode_var,
            values=["Auto", "Non-Sequential Preview", "Sequential", "Folded Preview"],
            on_commit=self._on_trace_mode_changed,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            combo_pady=(0, 0),
        )

        self.nonseq_target_surface_var = tk.StringVar(value="Auto")
        self.nonseq_target_surface_menu = grid_labeled_commit_combobox(
            parent,
            10,
            0,
            "NS target",
            self.nonseq_target_surface_var,
            values=["Auto"],
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_pady=(8, 2),
            combo_pady=(0, 0),
        )

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

        self.folded_detector_policy_var = tk.StringVar(value=folded_detector_policy_default)
        self.folded_detector_policy_menu = grid_labeled_commit_combobox(
            parent,
            12,
            0,
            "Folded reach",
            self.folded_detector_policy_var,
            values=folded_detector_policy_values,
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=18,
            label_pady=(8, 2),
            combo_pady=(0, 0),
            label_columnspan=2,
            combo_columnspan=2,
        )

        nonseq_energy_check = grid_commit_checkbutton(
            parent,
            14,
            0,
            text="NS probabilistic coating split",
            variable=self.nonseq_energy_probability_var,
            command=self._mark_plot_update_pending,
            on_press=self._begin_history_capture,
            columnspan=2,
            pady=(8, 0),
        )

        self.wavefront_style_var = tk.StringVar(value=wavefront_style_default)
        self.wavefront_style_menu = grid_labeled_commit_combobox(
            parent,
            15,
            0,
            "Wavefront style",
            self.wavefront_style_var,
            values=wavefront_style_values,
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=18,
            label_pady=(8, 2),
            combo_pady=(0, 0),
            label_columnspan=2,
            combo_columnspan=2,
        )

        self.tolerance_compare_view_var = tk.StringVar(value=tolerance_compare_view_default)
        self.tolerance_compare_view_menu = grid_labeled_commit_combobox(
            parent,
            17,
            0,
            "Tolerance compare",
            self.tolerance_compare_view_var,
            values=tolerance_compare_view_values,
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=18,
            label_pady=(8, 2),
            combo_pady=(0, 0),
            label_columnspan=2,
            combo_columnspan=2,
        )

        clipped_check = grid_commit_checkbutton(
            parent,
            19,
            0,
            text="Show clipped rays",
            variable=self.show_clipped_rays_var,
            command=self._mark_plot_update_pending,
            on_press=self._begin_history_capture,
            columnspan=2,
            pady=(8, 0),
        )

        self.analysis_branch_filter_var = tk.StringVar(value=analysis_path_filter_default)
        self.analysis_branch_filter_menu = grid_labeled_commit_combobox(
            parent,
            20,
            0,
            "Analysis path",
            self.analysis_branch_filter_var,
            values=[analysis_path_filter_default],
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=18,
            label_pady=(8, 2),
            combo_pady=(0, 0),
            label_columnspan=2,
            combo_columnspan=2,
        )

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
        self.coherent_sum_mode_var = tk.StringVar(value=coherent_sum_mode_default)
        self.coherent_sum_mode_menu = grid_labeled_commit_combobox(
            parent,
            24,
            0,
            "Coherent sum",
            self.coherent_sum_mode_var,
            values=coherent_sum_mode_values,
            on_commit=self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
            width=18,
            label_pady=(8, 2),
            combo_pady=(0, 0),
            label_columnspan=2,
            combo_columnspan=2,
        )

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
            normal_state="readonly",
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
