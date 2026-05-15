from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import KrakenOS as Kos

from KrakenOS.UI.layout_editor import (
    ARM_VIEW_DEFAULT,
    ATMOS_PLOT_MODE_DEFAULT,
    BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
    DETECTOR_BINS_DEFAULT,
    PUPIL_PATTERN_DEFAULT,
    SOURCE_ANGULAR_WEIGHT_DEFAULT,
    SOURCE_MODEL_DEFAULT,
    TOLERANCE_COMPARE_VIEW_DEFAULT,
    TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS,
    WAVEFRONT_STYLE_DEFAULT,
    KrakenLayoutEditor,
    SurfaceRow,
    _normalize_metal_catalog_specs,
)
from KrakenOS.UI.scene_projector import SceneProjector2D, projection_axis_labels
from KrakenOS.UI.scene_renderer_2d import render_scene_2d, set_plot_limits
from KrakenOS.UI.scene_row_mapping import SOURCE_ROW_ORDER_DEFAULT, normalize_source_row_order


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


def _rows_from_surface_specs(surface_specs: list[dict]) -> list[SurfaceRow]:
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in surface_specs]
    if rows:
        rows[0].surface = "Object"
        rows[-1].surface = "Image"
    for row in rows[1:-1]:
        if row.surface == "Mirror":
            row.glass = "MIRROR"
        elif row.surface == "Aperture":
            row.glass = "AIR"
            row.rc = 0.0
    return rows


def _snapshot_editor(rows: list[SurfaceRow], settings: dict) -> KrakenLayoutEditor:
    editor = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    editor.headless = True
    editor.rows = rows
    editor.last_system = None
    editor.layout_scene_source_specs = KrakenLayoutEditor._normalize_scene_source_specs(settings.get("scene_sources", []))
    editor.layout_scene_row_order = normalize_source_row_order(settings.get("scene_row_order", SOURCE_ROW_ORDER_DEFAULT))
    editor.last_rays = None
    editor._last_preview_trace_signature = None
    editor._last_preview_trace_backend = "none"
    editor._last_preview_trace_note = ""
    editor.analysis_mode = "none"
    editor.selected_analysis_modes = []
    editor.secondary_analysis_mode = None
    editor.layout_preview_mode = "none"
    editor._headless_selected_operand_labels = [
        str(label)
        for label in list(settings.get("selected_operands", []) or [])
        if str(label).strip()
    ]
    editor._preview_field_ray_count = 1
    editor._preview_field_bundle_count = 1
    editor._analysis_axes = []
    editor._analysis_ax = None
    editor._last_scene_bundle = None
    editor._last_auto_leg_entries = []
    editor._last_optics_info = None
    editor.optimization_running = False
    editor._spinner_phase = 0
    editor.progress_spinner_var = _Var("idle")
    editor.progress_percent_var = _Var("")
    editor.progress_bar_var = _Var(0.0)
    editor.status_var = _Var("")
    editor.show_clipped_rays_var = _Var(bool(settings.get("show_clipped_rays", True)))
    editor.show_path_labels = bool(settings.get("show_path_labels", True))
    editor.show_path_labels_var = _Var(editor.show_path_labels)
    editor.ray_display_mode_var = _Var(editor._normalize_ray_display_mode(settings.get("ray_display_mode", "All rays")))
    editor.display_orientation_var = _Var(str(settings.get("display_orientation", "Vertical")))
    editor.object_mode_var = _Var(str(settings.get("object_mode", "Finite")))
    editor.wavelength_var = _Var(str(settings.get("wavelength", "0.55")))
    editor.ray_count_var = _Var(str(settings.get("ray_count", "5")))
    editor.ray_height_factor_var = _Var(str(settings.get("ray_height_factor", "0.8")))
    editor.source_model_var = _Var(str(settings.get("source_model", SOURCE_MODEL_DEFAULT)))
    editor.pupil_pattern_var = _Var(str(settings.get("pupil_pattern", PUPIL_PATTERN_DEFAULT)))
    editor.arm_view_var = _Var(str(settings.get("arm_view", ARM_VIEW_DEFAULT)))
    editor.source_radius_var = _Var(str(settings.get("source_radius", "5.0")))
    editor.source_cone_angle_var = _Var(str(settings.get("source_cone_angle", "5.0")))
    editor.gaussian_input_mode_var = _Var(str(settings.get("gaussian_input_mode", "Waist + offset")))
    editor.gaussian_waist_radius_var = _Var(str(settings.get("gaussian_waist_radius", "0.5")))
    editor.gaussian_waist_offset_var = _Var(str(settings.get("gaussian_waist_offset", "0.0")))
    editor.gaussian_beam_diameter_var = _Var(str(settings.get("gaussian_beam_diameter", "1.0")))
    editor.gaussian_full_divergence_var = _Var(str(settings.get("gaussian_full_divergence", "1.0")))
    editor.gaussian_waist_side_var = _Var(str(settings.get("gaussian_waist_side", "Waist before source")))
    editor.gaussian_m2_var = _Var(str(settings.get("gaussian_m2", "1.0")))
    editor.source_power_var = _Var(str(settings.get("source_power", "1.0")))
    editor.source_seed_var = _Var(str(settings.get("source_seed", "1")))
    editor.source_x_var = _Var(str(settings.get("source_x", "0.0")))
    editor.source_y_var = _Var(str(settings.get("source_y", "0.0")))
    editor.source_z_var = _Var(str(settings.get("source_z", "0.0")))
    editor.source_l_var = _Var(str(settings.get("source_l", "0.0")))
    editor.source_m_var = _Var(str(settings.get("source_m", "0.0")))
    editor.source_n_var = _Var(str(settings.get("source_n", "1.0")))
    editor.source_angular_weight_var = _Var(str(settings.get("source_angular_weight", SOURCE_ANGULAR_WEIGHT_DEFAULT)))
    editor.analysis_surface_var = _Var(str(settings.get("analysis_surface", "Auto")))
    editor.analysis_branch_filter_var = _Var(str(settings.get("analysis_branch_filter", "All paths")))
    editor.detector_bins_var = _Var(str(settings.get("detector_bins", DETECTOR_BINS_DEFAULT)))
    editor.coherent_sum_mode_var = _Var(str(settings.get("coherent_sum_mode", "By source ray")))
    editor.branch_field_propagation_mm_var = _Var(
        str(settings.get("branch_field_propagation_mm", BRANCH_FIELD_PROPAGATION_MM_DEFAULT))
    )
    editor.aperture_type_var = _Var(str(settings.get("aperture_type", "EPD")))
    editor.aperture_value_var = _Var(str(settings.get("aperture_value", "4.0")))
    editor.emit_full_ray_var = _Var(bool(settings.get("full_pupil", False)))
    editor.trace_mode_var = _Var(str(settings.get("trace_mode", "Auto")))
    editor.field_type_var = _Var(str(settings.get("field_type", "Angle")))
    editor.field_value_var = _Var(str(settings.get("field_value", "0.0")))
    editor.field_count_var = _Var(str(settings.get("field_count", "1")))
    editor.atmos_observatory_var = _Var(str(settings.get("atmos_observatory", "Manual")))
    editor.atmos_plot_mode_var = _Var(str(settings.get("atmos_plot_mode", ATMOS_PLOT_MODE_DEFAULT)))
    editor.atmos_wavelength_min_var = _Var(str(settings.get("atmos_wavelength_min", "0.45")))
    editor.atmos_wavelength_max_var = _Var(str(settings.get("atmos_wavelength_max", "0.75")))
    editor.atmos_wavelength_count_var = _Var(str(settings.get("atmos_wavelength_count", "11")))
    editor.atmos_zenith_deg_var = _Var(str(settings.get("atmos_zenith_deg", "45.0")))
    editor.atmos_temperature_k_var = _Var(str(settings.get("atmos_temperature_k", "283.15")))
    editor.atmos_pressure_pa_var = _Var(str(settings.get("atmos_pressure_pa", "101300")))
    editor.atmos_humidity_var = _Var(str(settings.get("atmos_humidity", "0.5")))
    editor.atmos_co2_ppm_var = _Var(str(settings.get("atmos_co2_ppm", "400")))
    editor.atmos_latitude_deg_var = _Var(str(settings.get("atmos_latitude_deg", "31.0")))
    editor.atmos_altitude_m_var = _Var(str(settings.get("atmos_altitude_m", "2800")))
    editor.optimization_workers_var = _Var("1")
    editor.image_diameter_mode_var = _Var(str(settings.get("image_diameter_mode", "Manual")))
    editor.spot_view_mode_var = _Var(str(settings.get("spot_view_mode", "Grid")))
    editor.wavefront_style_var = _Var(str(settings.get("wavefront_style", WAVEFRONT_STYLE_DEFAULT)))
    editor.tolerance_compare_view_var = _Var(str(settings.get("tolerance_compare_view", TOLERANCE_COMPARE_VIEW_DEFAULT)))
    editor.tolerance_solve_presets = KrakenLayoutEditor._normalize_tolerance_solve_presets(
        settings.get("tolerance_solve_presets", [])
    )
    editor.tolerance_manufacturing_templates = KrakenLayoutEditor._normalize_tolerance_manufacturing_templates(
        settings.get(TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS, [])
    )
    preset_names = {str(preset.get("name", "")) for preset in editor.tolerance_solve_presets}
    active_preset = str(settings.get("active_tolerance_solve_preset", "") or "")
    editor.active_tolerance_solve_preset_name = active_preset if active_preset in preset_names else ""
    editor.show_cardinals_var = _Var(bool(settings.get("show_cardinals", False)))
    editor.show_physical_distances_var = _Var(bool(settings.get("show_physical_distances", False)))
    editor._analysis_executor = None
    editor._analysis_executor_workers = 0
    editor._branch_throughput_records = []
    editor._last_tolerance_monte_carlo_records = []
    editor._last_tolerance_monte_carlo_summary = {}
    editor._last_tolerance_comparison_records = []
    editor._last_tolerance_comparison_summary = {}
    editor._last_tolerance_stackup_records = []
    editor._last_tolerance_stackup_summary = {}
    editor._last_tolerance_compensator_records = []
    editor._last_tolerance_compensator_summary = {}
    editor._last_tolerance_multi_compensator_records = []
    editor._last_tolerance_multi_compensator_summary = {}
    editor._last_tolerance_spot_overlay = {}
    editor._last_tolerance_mtf_overlay = {}
    editor._last_tolerance_wavefront_overlay = {}
    editor._zemax_wavefront_reference = None
    editor._last_zemax_wavefront_comparison = None
    editor.operand_weight_vars = {}
    editor.operand_target_vars = {}
    editor.operand_wavelength_vars = {}
    editor.operand_field_vars = {}
    editor.operand_field_x_vars = {}
    editor.operand_field_y_vars = {}
    editor.operand_surface_vars = {}
    editor.operand_aperture_type_vars = {}
    editor.operand_aperture_value_vars = {}
    editor.operand_frequency_vars = {}
    editor.operand_mtf_mode_vars = {}
    editor.operand_mtf_algorithm_vars = {}
    operand_settings = settings.get("operands", {})
    if isinstance(operand_settings, dict):
        operand_maps = {
            "weight": editor.operand_weight_vars,
            "target": editor.operand_target_vars,
            "wavelength": editor.operand_wavelength_vars,
            "field": editor.operand_field_vars,
            "field_x": editor.operand_field_x_vars,
            "field_y": editor.operand_field_y_vars,
            "surface": editor.operand_surface_vars,
            "aperture_type": editor.operand_aperture_type_vars,
            "aperture_value": editor.operand_aperture_value_vars,
            "frequency": editor.operand_frequency_vars,
            "mtf_mode": editor.operand_mtf_mode_vars,
            "mtf_algorithm": editor.operand_mtf_algorithm_vars,
        }
        for label, payload in operand_settings.items():
            if not isinstance(payload, dict):
                continue
            for key, mapping in operand_maps.items():
                if key in payload:
                    mapping[str(label)] = _Var(str(payload[key]))
    editor.metal_catalogs = _normalize_metal_catalog_specs(settings.get("metal_catalogs", []))
    editor.results_table = None
    editor._last_wavefront_fit_report = ""
    editor.append_debug = lambda _message: None
    editor.append_progress = lambda _message: None
    editor.update_idletasks = lambda: None
    editor._field_defaults_initialized = True
    editor._field_type_defaults = {
        "Angle": "0.0",
        "Object Height": "0.0",
        "Paraxial Image Height": "0.0",
        "Real Image Height": "0.0",
    }
    return editor


def build_saved_layout_figure(
    surface_specs: list[dict],
    settings: dict,
    *,
    system,
    rays,
    layout_path: str | Path | None = None,
):
    rows = _rows_from_surface_specs(surface_specs)
    editor = _snapshot_editor(rows, settings if isinstance(settings, dict) else {})
    if layout_path is not None:
        editor.current_layout_file = Path(layout_path)
    editor._normalize_special_rows()
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    wavelength = float(editor._current_wavelength())
    display_rays = rays if rays is not None else Kos.raykeeper(system)
    editor._trace_preview_rays(
        system,
        display_rays,
        wavelength,
        max_radius,
        allow_full_pupil=True,
        sampling_mode=editor._preview_scene_sampling_mode(),
    )
    editor.last_system = system
    editor.last_rays = display_rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    if editor._apply_image_diameter_mode():
        max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)

    bundle = editor._build_scene_bundle(system, display_rays, max_radius)
    editor._last_scene_bundle = bundle
    projected = SceneProjector2D(editor._current_display_orientation()).project_bundle(bundle)
    editor._refresh_auto_leg_graph(projected)
    projected = editor._filter_projected_scene_for_arm_view(projected)
    projected = editor._filter_projected_scene_for_ray_display(projected)

    fig = plt.figure(figsize=(16, 9))
    layout_gs = fig.add_gridspec(
        2,
        2,
        width_ratios=[3.4, 1.15],
        height_ratios=[1.0, 1.0],
        wspace=0.22,
        hspace=0.30,
    )
    ax = fig.add_subplot(layout_gs[:, 0])
    aux_axes = {
        "XZ": fig.add_subplot(layout_gs[0, 1]),
        "XY": fig.add_subplot(layout_gs[1, 1]),
    }
    editor.figure = fig
    editor.ax = ax
    render_projected = editor._projected_scene_for_layout_render(projected)
    render_scene_2d(
        render_projected,
        ax,
        show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
        show_labels=bool(editor._current_show_path_labels()),
        ray_count_hint=max(1, int(editor._preview_field_ray_count)),
    )
    for plane, aux_ax in aux_axes.items():
        aux_projected = SceneProjector2D(plane).project_bundle(bundle)
        aux_projected = editor._filter_projected_scene_for_arm_view(aux_projected)
        aux_projected = editor._filter_projected_scene_for_ray_display(aux_projected)
        aux_render = editor._projected_scene_for_layout_render(aux_projected, suppress_scene_labels=True)
        render_scene_2d(
            aux_render,
            aux_ax,
            show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
            show_labels=False,
            ray_count_hint=max(1, int(editor._preview_field_ray_count)),
        )
        set_plot_limits(
            aux_ax,
            aux_projected.bounds,
            max_radius=max_radius,
            has_off_axis=True,
            orientation=plane,
            use_drawn_data=True,
        )
        aux_x_label, aux_y_label, aux_title = projection_axis_labels(plane)
        aux_ax.set_xlabel(aux_x_label, fontsize=8)
        aux_ax.set_ylabel(aux_y_label, fontsize=8)
        aux_ax.set_title(aux_title, fontsize=9)
        aux_ax.tick_params(axis="both", which="major", labelsize=8)
        aux_ax.grid(True, alpha=0.2)
    gaussian_extent = editor._draw_gaussian_beam_overlay(system, wavelength)
    if gaussian_extent is not None:
        max_radius = max(max_radius, float(gaussian_extent))
    scan_bounds = editor._draw_folded_scan_overlay(max_radius, system=system)
    tolerance_bounds = editor._draw_pose_tolerance_overlay(max_radius, wavelength=wavelength)
    plot_bounds = editor._combined_plot_bounds(projected.bounds, scan_bounds, tolerance_bounds)
    set_plot_limits(
        ax,
        plot_bounds,
        max_radius=max_radius,
        has_off_axis=bundle.has_off_axis,
        orientation=editor._current_display_orientation(),
        use_drawn_data=not scan_bounds.is_empty or not tolerance_bounds.is_empty,
    )
    editor._draw_arm_labels(projected)
    x_label, y_label, title = projection_axis_labels(editor._current_display_orientation())
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title, fontsize=10)
    ax.grid(True, alpha=0.2)
    fig.text(0.5, 0.035, "KrakenOS Layout", ha="center", va="center")
    return fig, ax


def display_saved_layout_2d(
    surface_specs: list[dict],
    settings: dict,
    *,
    system,
    rays,
    layout_path: str | Path | None = None,
):
    fig, ax = build_saved_layout_figure(
        surface_specs,
        settings,
        system=system,
        rays=rays,
        layout_path=layout_path,
    )
    plt.show()
    return fig, ax
