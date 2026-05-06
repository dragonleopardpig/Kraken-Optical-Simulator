from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import (
    AUTO_PLOT_PATH,
    ARM_VIEW_DEFAULT,
    ATMOS_PLOT_MODE_DEFAULT,
    DETECTOR_BINS_DEFAULT,
    PUPIL_PATTERN_DEFAULT,
    SOURCE_ANGULAR_WEIGHT_DEFAULT,
    SOURCE_MODEL_DEFAULT,
    WAVEFRONT_STYLE_DEFAULT,
    KrakenLayoutEditor,
    SurfaceRow,
    _build_system_from_specs,
    _coerce_bounds,
    _coerce_opt_flag,
    _load_python_data,
    _normalize_metal_catalog_specs,
)
from KrakenOS.UI.scene_projector import SceneProjector2D
from KrakenOS.UI.scene_renderer_2d import render_scene_2d, set_plot_limits


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


def _load_layout_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load layout file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows_from_layout_info(info: dict) -> list[SurfaceRow]:
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
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


def _build_runtime_system(path: Path, rows: list[SurfaceRow]):
    module = _load_layout_module(path)
    build_runtime = getattr(module, "build_runtime_system", None)
    if callable(build_runtime):
        return build_runtime()
    settings = getattr(module, "SETTINGS", {})
    metal_catalogs = _normalize_metal_catalog_specs(settings.get("metal_catalogs", [])) if isinstance(settings, dict) else []
    row_specs = [
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "k": row.k,
            "axicon": row.axicon,
            "diff_ord": row.diff_ord,
            "grating_d": row.grating_d,
            "grating_angle": row.grating_angle,
            "thickness": row.thickness,
            "diameter": row.diameter,
            "in_diameter": row.in_diameter,
            "drawing": row.drawing,
            "extra_data": row.extra_data,
            "uda": row.uda,
            "advanced": row.advanced,
            "tilt_x": row.tilt_x,
            "tilt_y": row.tilt_y,
            "tilt_z": row.tilt_z,
            "desp_x": row.desp_x,
            "desp_y": row.desp_y,
            "desp_z": row.desp_z,
            "axis_move": row.axis_move,
            "glass": row.glass,
        }
        for row in rows
    ]
    if row_specs and metal_catalogs:
        row_specs[0]["_metal_catalogs"] = metal_catalogs
    return _build_system_from_specs(row_specs)


def _snapshot_editor(rows: list[SurfaceRow], settings: dict) -> KrakenLayoutEditor:
    editor = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    editor.headless = True
    editor.rows = rows
    editor.last_system = None
    editor.layout_scene_source_specs = KrakenLayoutEditor._normalize_scene_source_specs(settings.get("scene_sources", []))
    editor.last_rays = None
    editor._last_preview_trace_signature = None
    editor._last_preview_trace_backend = "none"
    editor._last_preview_trace_note = ""
    editor.analysis_mode = "none"
    editor.selected_analysis_modes = []
    editor.secondary_analysis_mode = None
    editor.layout_preview_mode = "none"
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
    # Headless snapshots should be deterministic and work in sandboxed shells
    # where multiprocessing semaphores may be unavailable.
    editor.optimization_workers_var = _Var("1")
    editor.image_diameter_mode_var = _Var(str(settings.get("image_diameter_mode", "Manual")))
    editor.spot_view_mode_var = _Var(str(settings.get("spot_view_mode", "Grid")))
    editor.wavefront_style_var = _Var(str(settings.get("wavefront_style", WAVEFRONT_STYLE_DEFAULT)))
    editor.show_cardinals_var = _Var(bool(settings.get("show_cardinals", False)))
    editor.show_physical_distances_var = _Var(bool(settings.get("show_physical_distances", False)))
    editor._analysis_executor = None
    editor._analysis_executor_workers = 0
    editor._branch_throughput_records = []
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


def _render_layout_file(path: Path, output: Path, dpi: int, mode: str = "2d") -> None:
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    row_specs = [
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "k": row.k,
            "axicon": row.axicon,
            "diff_ord": row.diff_ord,
            "grating_d": row.grating_d,
            "grating_angle": row.grating_angle,
            "thickness": row.thickness,
            "diameter": row.diameter,
            "in_diameter": row.in_diameter,
            "drawing": row.drawing,
            "extra_data": row.extra_data,
            "uda": row.uda,
            "advanced": row.advanced,
            "tilt_x": row.tilt_x,
            "tilt_y": row.tilt_y,
            "tilt_z": row.tilt_z,
            "desp_x": row.desp_x,
            "desp_y": row.desp_y,
            "desp_z": row.desp_z,
            "axis_move": row.axis_move,
            "glass": row.glass,
        }
        for row in rows
    ]
    if row_specs and editor.metal_catalogs:
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    if editor._apply_image_diameter_mode():
        max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)

    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor._last_scene_bundle = bundle
    projected = SceneProjector2D(editor._current_display_orientation()).project_bundle(bundle)
    editor._refresh_auto_leg_graph(projected)

    analysis_mode = mode if mode in {"mtf", "polarization", "detector_map", "coherent_detector", "psf_map", "field_map", "illum_map", "wavefront_map", "atmosphere", "wavefront", "zernike", "interferogram"} else None
    fig = plt.figure(figsize=(16, 9))
    editor.figure = fig
    if analysis_mode is None:
        ax = fig.add_subplot(111)
        analysis_ax = None
    else:
        gs = fig.add_gridspec(1, 2, width_ratios=[3.9, 1.75], wspace=0.18)
        ax = fig.add_subplot(gs[0])
        analysis_ax = fig.add_subplot(gs[1])
    render_projected = editor._projected_scene_for_layout_render(projected)
    render_scene_2d(
        render_projected,
        ax,
        show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
        ray_count_hint=max(1, int(editor._preview_field_ray_count)),
    )
    editor.ax = ax
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
    if editor._current_display_orientation() == "Horizontal":
        ax.set_xlabel("Y [mm]")
        ax.set_ylabel("-Z [mm]")
    else:
        ax.set_xlabel("Z [mm]")
        ax.set_ylabel("Y [mm]")
    if analysis_mode is not None and analysis_ax is not None:
        editor.analysis_mode = analysis_mode
        editor.selected_analysis_modes = [analysis_mode]
        editor._analysis_ax = analysis_ax
        editor._analysis_axes = [analysis_ax]
        editor._plot_analysis(analysis_ax, system, rays, wavelength)
    fig.text(0.5, 0.035, "KrakenOS Layout", ha="center", va="center")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Kraken layout snapshot without opening the UI.")
    parser.add_argument(
        "--mode",
        choices=["2d", "native", "mtf", "polarization", "detector_map", "coherent_detector", "psf_map", "field_map", "illum_map", "wavefront_map", "atmosphere", "wavefront", "zernike", "interferogram"],
        default="2d",
        help="Render mode",
    )
    parser.add_argument("--layout", default=None, help="Common layout title to load")
    parser.add_argument("--file", type=Path, default=None, help="Saved layout file to render directly")
    parser.add_argument("--output", type=Path, default=AUTO_PLOT_PATH, help="Output image path")
    parser.add_argument("--dpi", type=int, default=180, help="Output DPI")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.file is not None:
        _render_layout_file(args.file, args.output, args.dpi, args.mode)
        print(args.output)
        return

    app = KrakenLayoutEditor(headless=True)
    try:
        if args.layout:
            app.load_layout_by_name(args.layout)
        if args.mode in {"mtf", "polarization", "detector_map", "coherent_detector", "psf_map", "field_map", "illum_map", "wavefront_map", "atmosphere", "wavefront", "zernike", "interferogram"}:
            app.analysis_mode = args.mode
            app.selected_analysis_modes = [app.analysis_mode]
        else:
            app.analysis_mode = "none"
            app.selected_analysis_modes = []
        app.auto_save_plot_var.set(False)
        try:
            app.attributes("-alpha", 0.0)
        except Exception:
            pass
        app.geometry("1800x1100")
        app.update()
        app.refresh_plot()
        app.update()
        app.figure.set_size_inches(16, 9, forward=True)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        app.figure.savefig(args.output, dpi=args.dpi)
        print(args.output)
    finally:
        app.destroy()


if __name__ == "__main__":
    main()
