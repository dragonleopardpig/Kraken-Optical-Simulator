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
    KrakenLayoutEditor,
    SurfaceRow,
    _build_system_from_specs,
    _coerce_bounds,
    _coerce_opt_flag,
    _load_python_data,
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
    rows = [
        SurfaceRow(
            surface=str(item.get("surface", KrakenLayoutEditor._infer_surface_type(item))),
            name=str(item.get("name", "Surface")),
            optimize_rc=_coerce_opt_flag(item.get("optimize_rc", item.get("opt_rc", ""))),
            optimize_rc_bounds=_coerce_bounds(item.get("optimize_rc_bounds")),
            rc=float(item.get("rc", 0.0)),
            optimize_thickness=_coerce_opt_flag(item.get("optimize_thickness", item.get("opt_thickness", ""))),
            optimize_thickness_bounds=_coerce_bounds(item.get("optimize_thickness_bounds")),
            thickness=float(item.get("thickness", 0.0)),
            diameter=float(item.get("diameter", 25.0)),
            tilt_x=float(item.get("tilt_x", 0.0)),
            tilt_y=float(item.get("tilt_y", 0.0)),
            tilt_z=float(item.get("tilt_z", 0.0)),
            desp_x=float(item.get("desp_x", 0.0)),
            desp_y=float(item.get("desp_y", 0.0)),
            desp_z=float(item.get("desp_z", 0.0)),
            axis_move=float(item.get("axis_move", 0.0)),
            glass=str(item.get("glass", "AIR")),
        )
        for item in info["surfaces"]
    ]
    if rows:
        rows[0].surface = "Object"
        rows[-1].surface = "Image"
    for row in rows[1:-1]:
        if row.surface == "Mirror":
            row.glass = "MIRROR"
        elif row.surface == "Aperture":
            row.name = "Aperture"
            row.glass = "AIR"
            row.rc = 0.0
    return rows


def _build_runtime_system(path: Path, rows: list[SurfaceRow]):
    module = _load_layout_module(path)
    build_runtime = getattr(module, "build_runtime_system", None)
    if callable(build_runtime):
        return build_runtime()
    return _build_system_from_specs([
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "thickness": row.thickness,
            "diameter": row.diameter,
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
    ])


def _snapshot_editor(rows: list[SurfaceRow], settings: dict) -> KrakenLayoutEditor:
    editor = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    editor.headless = True
    editor.rows = rows
    editor.last_system = None
    editor.last_rays = None
    editor._last_preview_trace_signature = None
    editor.analysis_mode = "none"
    editor.selected_analysis_modes = []
    editor.secondary_analysis_mode = None
    editor.layout_preview_mode = "none"
    editor._preview_field_ray_count = 1
    editor._analysis_axes = []
    editor._analysis_ax = None
    editor._last_scene_bundle = None
    editor._last_optics_info = None
    editor.show_clipped_rays_var = _Var(bool(settings.get("show_clipped_rays", True)))
    editor.display_orientation_var = _Var(str(settings.get("display_orientation", "Vertical")))
    editor.object_mode_var = _Var(str(settings.get("object_mode", "Finite")))
    editor.wavelength_var = _Var(str(settings.get("wavelength", "0.55")))
    editor.ray_count_var = _Var(str(settings.get("ray_count", "5")))
    editor.ray_height_factor_var = _Var(str(settings.get("ray_height_factor", "0.8")))
    editor.analysis_surface_var = _Var(str(settings.get("analysis_surface", "Auto")))
    editor.aperture_type_var = _Var(str(settings.get("aperture_type", "EPD")))
    editor.aperture_value_var = _Var(str(settings.get("aperture_value", "4.0")))
    editor.field_type_var = _Var(str(settings.get("field_type", "Angle")))
    editor.field_value_var = _Var(str(settings.get("field_value", "0.0")))
    editor.field_count_var = _Var(str(settings.get("field_count", "1")))
    # Headless snapshots should be deterministic and work in sandboxed shells
    # where multiprocessing semaphores may be unavailable.
    editor.optimization_workers_var = _Var(str(settings.get("optimization_workers", "1")))
    editor.image_diameter_mode_var = _Var(str(settings.get("image_diameter_mode", "Manual")))
    editor.spot_view_mode_var = _Var(str(settings.get("spot_view_mode", "Grid")))
    editor.show_cardinals_var = _Var(bool(settings.get("show_cardinals", False)))
    editor._analysis_executor = None
    editor._analysis_executor_workers = 0
    editor.append_debug = lambda _message: None
    editor._field_defaults_initialized = True
    editor._field_type_defaults = {
        "Angle": "0.0",
        "Object Height": "0.0",
        "Paraxial Image Height": "0.0",
        "Real Image Height": "0.0",
    }
    return editor


def _render_layout_file(path: Path, output: Path, dpi: int) -> None:
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    system = _build_system_from_specs([
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "thickness": row.thickness,
            "diameter": row.diameter,
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
    ])
    wavelength = float(editor._current_wavelength())
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius)
    editor.last_system = system
    editor.last_rays = rays

    bundle = editor._build_scene_bundle(system, rays, max_radius)
    projected = SceneProjector2D(editor._current_display_orientation()).project_bundle(bundle)

    fig = plt.figure(figsize=(16, 9))
    ax = fig.add_subplot(111)
    render_scene_2d(
        projected,
        ax,
        show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
        ray_count_hint=max(1, int(editor._preview_field_ray_count)),
    )
    set_plot_limits(
        ax,
        projected.bounds,
        max_radius=max_radius,
        has_off_axis=bundle.has_off_axis,
        orientation=editor._current_display_orientation(),
    )
    if editor._current_display_orientation() == "Horizontal":
        ax.set_xlabel("Y [mm]")
        ax.set_ylabel("-Z [mm]")
    else:
        ax.set_xlabel("Z [mm]")
        ax.set_ylabel("Y [mm]")
    fig.text(0.5, 0.035, "KrakenOS Layout", ha="center", va="center")
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Kraken layout snapshot without opening the UI.")
    parser.add_argument("--mode", choices=["2d", "native", "mtf"], default="2d", help="Render mode")
    parser.add_argument("--layout", default=None, help="Common layout title to load")
    parser.add_argument("--file", type=Path, default=None, help="Saved layout file to render directly")
    parser.add_argument("--output", type=Path, default=AUTO_PLOT_PATH, help="Output image path")
    parser.add_argument("--dpi", type=int, default=180, help="Output DPI")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.file is not None:
        _render_layout_file(args.file, args.output, args.dpi)
        print(args.output)
        return

    app = KrakenLayoutEditor(headless=True)
    try:
        if args.layout:
            app.load_layout_by_name(args.layout)
        if args.mode == "mtf":
            app.analysis_mode = "mtf"
        else:
            app.analysis_mode = "none"
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
