"""The editor's model state variables, declared by the model (docs/design_qt_migration.md step 1c).

Measured 2026-09-22: of the 135 ``tk.*Var`` state variables, 92 are created by PANELS -- views --
through their delegation shells onto the editor, and model code reads or writes 100 of them
(1174 ``set`` and 191 ``get`` calls). The model's state lived in view-made objects: a Qt view
cannot create a ``tk.StringVar``, and without the Tk panels these attributes would not exist.

This registry declares the 64 such variables a freshly built editor has, with their values after
start-up. :func:`ensure_model_variables` creates any that are MISSING through the owner's UI host.
Under Tk the panels have already created every one, so it creates nothing and Tk behaviour does not
change; without Tk panels (a Qt shell, a scripted guard) it creates all of them -- a real
``tk.*Var`` from ``TkUiHost``, an ``ObservableValue`` otherwise.

Not here, on purpose: the 9 dialog-scoped summary/filter variables (``_branch_throughput_summary_var``
...) that exist only while their report dialog is open -- they are that dialog's view state and go
with it -- and the 20 view-only variables no model code touches. Guard 0852 keeps this table
honest: every panel-made variable model code uses must be here or in that dialog-scoped list, and
every default here must equal what a real editor holds after start-up.
"""
from __future__ import annotations

from typing import Any

#: name -> (kind, value after start-up). kind: string / int / double / boolean.
MODEL_VARIABLES: dict[str, tuple[str, Any]] = {
    'analysis_branch_filter_var': ('string', 'All paths'),
    'analysis_surface_var': ('string', 'Auto'),
    'aperture_type_var': ('string', 'EPD'),
    'aperture_value_var': ('string', '4.0'),
    'atmos_observatory_var': ('string', 'Manual'),
    'atmos_plot_mode_var': ('string', 'Refraction / dispersion'),
    'branch_field_propagation_mm_var': ('string', '0.0'),
    'camera_model_var': ('string', 'None'),
    'camera_overlay_mode_var': ('string', 'Off'),
    'coherent_sum_mode_var': ('string', 'By source ray'),
    'detector_bins_var': ('string', 'Auto'),
    'display_orientation_var': ('string', 'YZ'),
    'external_camera_var': ('string', 'None'),
    'field_count_var': ('string', 'NA'),
    'field_mode_note_var': ('string', 'Preferred: Field half-angle for infinity object. Image semi-height modes are derived targets.'),
    'field_summary_var': ('string', ''),
    'field_type_var': ('string', 'Field Half-Angle'),
    'field_value_label_var': ('string', 'Field Half-Angle [deg]'),
    'field_value_var': ('string', '0.0'),
    'field_warning_var': ('string', ''),
    'folded_detector_policy_var': ('string', 'Trace events'),
    'gaussian_beam_diameter_var': ('string', '1.0'),
    'gaussian_full_divergence_var': ('string', '1.0'),
    'gaussian_input_mode_var': ('string', 'Waist + offset'),
    'gaussian_m2_var': ('string', '1.0'),
    'gaussian_waist_offset_var': ('string', '0.0'),
    'gaussian_waist_radius_var': ('string', '0.5'),
    'gaussian_waist_side_var': ('string', 'Waist before source'),
    'image_diameter_mode_var': ('string', 'Auto'),
    'layout_preview_mode_var': ('string', 'none'),
    'nonseq_ns_limit_var': ('string', '200'),
    'nonseq_target_surface_var': ('string', 'Auto'),
    'object_mode_var': ('string', 'Infinity'),
    'optimization_workers_var': ('string', 'Auto'),
    'progress_bar_var': ('double', 0.0),
    'progress_percent_var': ('string', '0%'),
    'progress_spinner_var': ('string', 'idle'),
    'projection_display_mode_var': ('string', 'Full 3D'),
    'pupil_pattern_var': ('string', 'Meridional fan'),
    'pupil_rad_var': ('string', '0.0'),
    'pupil_theta_var': ('string', '0.0'),
    'ray_count_var': ('string', '31'),
    'ray_height_factor_var': ('string', '0.8'),
    'show_cardinals_var': ('boolean', True),
    'show_physical_distances_var': ('boolean', False),
    'source_angular_weight_var': ('string', 'Uniform solid angle'),
    'source_cone_angle_var': ('string', '0.0'),
    'source_l_var': ('string', '0.0'),
    'source_m_var': ('string', '0.0'),
    'source_model_var': ('string', 'Pupil / field'),
    'source_n_var': ('string', '1.0'),
    'source_power_var': ('string', '1.0'),
    'source_radius_var': ('string', '5.0'),
    'source_seed_var': ('string', '1'),
    'source_x_var': ('string', '0.0'),
    'source_y_var': ('string', '0.0'),
    'source_z_var': ('string', '0.0'),
    'spot_view_mode_var': ('string', 'Grid'),
    # the editor's status line (made by the main-window panel); the inspector and two dialogs have
    # their OWN status_var on their own objects -- not this one
    'status_var': ('string', 'Ready'),
    'status_hint_var': ('string', 'Preferred: Field half-angle for infinity object. Image semi-height modes are derived targets.  ||  Field samples: NA while angle span is 0 deg.'),
    'tolerance_compare_view_var': ('string', 'Spot overlay'),
    'trace_mode_var': ('string', 'Auto'),
    'wavefront_style_var': ('string', 'Wavefront Function'),
    'wavelength_var': ('string', '0.55'),
}

#: Created by report / inspector dialogs while they are open -- view state of those dialogs.
DIALOG_SCOPED_VARIABLES: frozenset[str] = frozenset({
    "_branch_gaussian_q_summary_var", "_branch_throughput_filter_var", "_branch_throughput_summary_var",
    "_branch_tree_summary_var", "_detector_aperture_summary_var", "_nonseq_scene_summary_var",
    "_ray_inspector_summary_var", "_source_illumination_summary_var", "_source_illumination_target_var",
})


def ensure_model_variables(owner) -> list[str]:
    """Create every declared model variable ``owner`` lacks, through its UI host; returns the
    names created. Existing variables are never replaced -- a panel's variable, and any trace a
    view put on it, stays exactly as it was."""
    from KrakenOS.UI.uihost import host_of

    host = host_of(owner)
    factories = {"string": host.string_var, "int": host.int_var, "double": host.double_var,
                 "boolean": host.boolean_var}
    created: list[str] = []
    for name, (kind, value) in MODEL_VARIABLES.items():
        if getattr(owner, name, None) is not None:
            continue
        setattr(owner, name, factories[kind](value=value))
        created.append(name)
    return created
