"""Main layout-editor source controls panel."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from KrakenOS.UI.widgets import grid_labeled_commit_entry


class MainSourceControlsPanel:
    """Build source controls while keeping state on the owning editor."""

    def __init__(
        self,
        editor: Any,
        *,
        source_model_default: str,
        source_model_values: tuple[str, ...],
        pupil_pattern_default: str,
        pupil_pattern_values: tuple[str, ...],
        gaussian_input_mode_default: str,
        gaussian_input_mode_values: tuple[str, ...],
        gaussian_waist_side_default: str,
        gaussian_waist_side_values: tuple[str, ...],
        source_direction_preset_values: tuple[str, ...],
        source_angular_weight_default: str,
        source_angular_weight_values: tuple[str, ...],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(
            self,
            "_config",
            {
                "source_model_default": source_model_default,
                "source_model_values": source_model_values,
                "pupil_pattern_default": pupil_pattern_default,
                "pupil_pattern_values": pupil_pattern_values,
                "gaussian_input_mode_default": gaussian_input_mode_default,
                "gaussian_input_mode_values": gaussian_input_mode_values,
                "gaussian_waist_side_default": gaussian_waist_side_default,
                "gaussian_waist_side_values": gaussian_waist_side_values,
                "source_direction_preset_values": source_direction_preset_values,
                "source_angular_weight_default": source_angular_weight_default,
                "source_angular_weight_values": source_angular_weight_values,
            },
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _commit_source_controls(self, _event=None) -> None:
        self._sync_left_mode_controls()
        self._mark_plot_update_pending()

    def build(self, parent: tk.Widget) -> None:
        cfg = self._config
        source_model_default = cfg["source_model_default"]
        source_model_values = cfg["source_model_values"]
        pupil_pattern_default = cfg["pupil_pattern_default"]
        pupil_pattern_values = cfg["pupil_pattern_values"]
        gaussian_input_mode_default = cfg["gaussian_input_mode_default"]
        gaussian_input_mode_values = cfg["gaussian_input_mode_values"]
        gaussian_waist_side_default = cfg["gaussian_waist_side_default"]
        gaussian_waist_side_values = cfg["gaussian_waist_side_values"]
        source_direction_preset_values = cfg["source_direction_preset_values"]
        source_angular_weight_default = cfg["source_angular_weight_default"]
        source_angular_weight_values = cfg["source_angular_weight_values"]

        for column in range(2):
            parent.columnconfigure(column, weight=1)

        self.source_model_label = ttk.Label(parent, text="Source model")
        self.source_model_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.source_model_var = tk.StringVar(value=source_model_default)
        self.source_model_menu = ttk.Combobox(
            parent,
            textvariable=self.source_model_var,
            state="readonly",
            width=16,
            values=source_model_values,
        )
        self.source_model_menu.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.source_model_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.source_model_menu.bind("<<ComboboxSelected>>", self._on_source_model_changed)

        self.pupil_pattern_label = ttk.Label(parent, text="Pupil pattern")
        self.pupil_pattern_label.grid(row=0, column=1, sticky="w", pady=(0, 2), padx=(8, 0))
        self.pupil_pattern_var = tk.StringVar(value=pupil_pattern_default)
        self.pupil_pattern_menu = ttk.Combobox(
            parent,
            textvariable=self.pupil_pattern_var,
            state="readonly",
            width=16,
            values=pupil_pattern_values,
        )
        self.pupil_pattern_menu.grid(row=1, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))
        self.pupil_pattern_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.pupil_pattern_menu.bind("<<ComboboxSelected>>", self._on_source_model_changed)

        self.source_radius_var = tk.StringVar(value="5.0")
        source_radius_entry = grid_labeled_commit_entry(
            parent,
            2,
            0,
            "Source radius [mm]",
            self.source_radius_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_cone_angle_var = tk.StringVar(value="0.0")
        source_cone_angle_entry = grid_labeled_commit_entry(
            parent,
            2,
            1,
            "Cone half-angle [deg]",
            self.source_cone_angle_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )
        self._add_widget_tooltip(
            source_cone_angle_entry,
            "Angular half-angle for physical cone sources and non-sequential source-cone previews.",
        )

        ttk.Label(parent, text="GB input mode").grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.gaussian_input_mode_var = tk.StringVar(value=gaussian_input_mode_default)
        gaussian_input_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.gaussian_input_mode_var,
            state="readonly",
            width=16,
            values=gaussian_input_mode_values,
        )
        gaussian_input_mode_menu.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        gaussian_input_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        gaussian_input_mode_menu.bind("<<ComboboxSelected>>", self._on_source_model_changed)

        self.gaussian_waist_radius_var = tk.StringVar(value="0.5")
        gaussian_waist_entry = grid_labeled_commit_entry(
            parent,
            6,
            0,
            "GB waist [mm]",
            self.gaussian_waist_radius_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.gaussian_waist_offset_var = tk.StringVar(value="0.0")
        gaussian_offset_entry = grid_labeled_commit_entry(
            parent,
            6,
            1,
            "GB waist offset [mm]",
            self.gaussian_waist_offset_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.gaussian_beam_diameter_var = tk.StringVar(value="1.0")
        gaussian_diameter_entry = grid_labeled_commit_entry(
            parent,
            8,
            0,
            "GB diameter [mm]",
            self.gaussian_beam_diameter_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.gaussian_full_divergence_var = tk.StringVar(value="1.0")
        gaussian_divergence_entry = grid_labeled_commit_entry(
            parent,
            8,
            1,
            "GB full div [mrad]",
            self.gaussian_full_divergence_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )
        self._add_widget_tooltip(
            gaussian_divergence_entry,
            "Gaussian laser datasheet divergence: full far-field angle in milliradians.",
        )

        self.gaussian_m2_var = tk.StringVar(value="1.0")
        gaussian_m2_entry = grid_labeled_commit_entry(
            parent,
            10,
            0,
            "GB M2",
            self.gaussian_m2_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        ttk.Label(parent, text="GB waist side").grid(row=10, column=1, sticky="w", pady=(0, 2), padx=(8, 0))
        self.gaussian_waist_side_var = tk.StringVar(value=gaussian_waist_side_default)
        gaussian_waist_side_menu = ttk.Combobox(
            parent,
            textvariable=self.gaussian_waist_side_var,
            state="readonly",
            width=16,
            values=gaussian_waist_side_values,
        )
        gaussian_waist_side_menu.grid(row=11, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))
        gaussian_waist_side_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        gaussian_waist_side_menu.bind("<<ComboboxSelected>>", self._on_source_model_changed)

        self.pupil_rad_var = tk.StringVar(value="0.0")
        pupil_rad_entry = grid_labeled_commit_entry(
            parent,
            12,
            0,
            "Pupil r [0..1]",
            self.pupil_rad_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.pupil_theta_var = tk.StringVar(value="0.0")
        pupil_theta_entry = grid_labeled_commit_entry(
            parent,
            12,
            1,
            "Pupil theta [deg]",
            self.pupil_theta_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_power_var = tk.StringVar(value="1.0")
        source_power_entry = grid_labeled_commit_entry(
            parent,
            14,
            0,
            "Source power [arb]",
            self.source_power_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_seed_var = tk.StringVar(value="1")
        source_seed_entry = grid_labeled_commit_entry(
            parent,
            14,
            1,
            "Random seed",
            self.source_seed_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_x_var = tk.StringVar(value="0.0")
        source_x_entry = grid_labeled_commit_entry(
            parent,
            16,
            0,
            "Source X [mm]",
            self.source_x_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_y_var = tk.StringVar(value="0.0")
        source_y_entry = grid_labeled_commit_entry(
            parent,
            16,
            1,
            "Source Y [mm]",
            self.source_y_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_z_var = tk.StringVar(value="0.0")
        source_z_entry = grid_labeled_commit_entry(
            parent,
            18,
            0,
            "Source Z [mm]",
            self.source_z_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_l_var = tk.StringVar(value="0.0")
        source_l_entry = grid_labeled_commit_entry(
            parent,
            18,
            1,
            "Source L",
            self.source_l_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_m_var = tk.StringVar(value="0.0")
        source_m_entry = grid_labeled_commit_entry(
            parent,
            20,
            0,
            "Source M",
            self.source_m_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.source_n_var = tk.StringVar(value="1.0")
        source_n_entry = grid_labeled_commit_entry(
            parent,
            20,
            1,
            "Source N",
            self.source_n_var,
            on_commit=self._commit_source_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        ttk.Label(parent, text="Direction preset").grid(row=22, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.source_direction_preset_var = tk.StringVar(value="Horizontal +Z (right)")
        source_direction_preset_menu = ttk.Combobox(
            parent,
            textvariable=self.source_direction_preset_var,
            state="readonly",
            width=16,
            values=source_direction_preset_values,
        )
        source_direction_preset_menu.grid(row=23, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        source_direction_preset_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        source_direction_preset_menu.bind("<<ComboboxSelected>>", self._on_source_direction_preset_changed)

        ttk.Label(parent, text="SourceRnd angular weight").grid(row=24, column=0, columnspan=2, sticky="w", pady=(0, 2))
        self.source_angular_weight_var = tk.StringVar(value=source_angular_weight_default)
        source_angular_weight_menu = ttk.Combobox(
            parent,
            textvariable=self.source_angular_weight_var,
            state="readonly",
            width=16,
            values=source_angular_weight_values,
        )
        source_angular_weight_menu.grid(row=25, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        source_angular_weight_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        source_angular_weight_menu.bind("<<ComboboxSelected>>", self._on_source_model_changed)

        source_physical_note = ttk.Label(
            parent,
            text="Physical sources launch from Source X/Y/Z along Source L/M/N; L/M/N are X/Y/Z direction cosines.",
            foreground="#5f6b7a",
            wraplength=220,
            justify="left",
        )
        source_physical_note.grid(row=26, column=0, columnspan=2, sticky="ew")

        self.source_summary_var = tk.StringVar(value="")
        source_summary_label = ttk.Label(
            parent,
            textvariable=self.source_summary_var,
            foreground="#3f4a5a",
            wraplength=460,
            justify="left",
        )
        source_summary_label.grid(row=27, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        source_manager_button = ttk.Button(
            parent,
            text="Scene Source Manager...",
            command=self.open_scene_source_manager,
        )
        source_manager_button.grid(row=28, column=0, columnspan=2, sticky="ew", pady=(8, 0))

        for var in (
            self.source_model_var,
            self.pupil_pattern_var,
            self.source_radius_var,
            self.source_cone_angle_var,
            self.gaussian_input_mode_var,
            self.gaussian_waist_radius_var,
            self.gaussian_waist_offset_var,
            self.gaussian_beam_diameter_var,
            self.gaussian_full_divergence_var,
            self.gaussian_m2_var,
            self.gaussian_waist_side_var,
            self.pupil_rad_var,
            self.pupil_theta_var,
            self.source_power_var,
            self.source_seed_var,
            self.source_x_var,
            self.source_y_var,
            self.source_z_var,
            self.source_l_var,
            self.source_m_var,
            self.source_n_var,
            self.source_direction_preset_var,
            self.source_angular_weight_var,
        ):
            var.trace_add("write", lambda *_args: self._update_source_summary())
        for var in (self.source_l_var, self.source_m_var, self.source_n_var):
            var.trace_add("write", lambda *_args: self._sync_source_direction_preset_from_lmn())
        self._register_source_mode_controls(
            source_radius_entry=source_radius_entry,
            source_cone_angle_entry=source_cone_angle_entry,
            gaussian_input_mode_menu=gaussian_input_mode_menu,
            gaussian_waist_entry=gaussian_waist_entry,
            gaussian_offset_entry=gaussian_offset_entry,
            gaussian_diameter_entry=gaussian_diameter_entry,
            gaussian_divergence_entry=gaussian_divergence_entry,
            gaussian_m2_entry=gaussian_m2_entry,
            gaussian_waist_side_menu=gaussian_waist_side_menu,
            pupil_rad_entry=pupil_rad_entry,
            pupil_theta_entry=pupil_theta_entry,
            source_power_entry=source_power_entry,
            source_seed_entry=source_seed_entry,
            source_x_entry=source_x_entry,
            source_y_entry=source_y_entry,
            source_z_entry=source_z_entry,
            source_l_entry=source_l_entry,
            source_m_entry=source_m_entry,
            source_n_entry=source_n_entry,
            source_direction_preset_menu=source_direction_preset_menu,
            source_angular_weight_menu=source_angular_weight_menu,
            source_physical_note=source_physical_note,
            source_summary_label=source_summary_label,
            source_manager_button=source_manager_button,
        )
        self._update_source_summary()
        self._sync_left_mode_controls()
