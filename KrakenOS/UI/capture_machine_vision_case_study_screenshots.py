"""Capture UI screenshots for the finite machine-vision case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_machine_vision_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageGrab

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "machine_vision_focus"
LAYOUT_NAME = "Machine Vision 150Mm Measured"
DEFOCUSED_SENSOR_DISTANCE_MM = 250.0
BEST_FOCUS_BOUNDS_MM = (240.0, 330.0)


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1760x960+40+40")
    app.auto_save_plot_var.set(False)
    app.load_layout_by_name(LAYOUT_NAME, refresh=False)
    app.object_mode_var.set("Finite")
    app.display_orientation_var.set("Vertical")
    app.wavelength_var.set("0.55")
    app.ray_count_var.set("21")
    app.ray_height_factor_var.set("0.8")
    app.source_model_var.set("Pupil / field")
    app.field_type_var.set("Object Height")
    app.field_value_var.set("0")
    app.field_count_var.set("1")
    app.aperture_type_var.set("FNO")
    app.aperture_value_var.set("5.6")
    app.spot_view_mode_var.set("Centroid")
    app.image_diameter_mode_var.set("Manual")
    app.show_cardinals_var.set(True)
    app.show_physical_distances_var.set(True)
    app.show_path_labels_var.set(False)
    app.show_path_labels = False
    app._set_selected_operand_labels(["Spot RMS", "MTF @ freq"])
    app.operand_target_vars["Spot RMS"].set("0")
    app.operand_weight_vars["Spot RMS"].set("1")
    app.operand_target_vars["MTF @ freq"].set("0.8")
    app.operand_weight_vars["MTF @ freq"].set("1")
    app.operand_frequency_vars["MTF @ freq"].set("20")
    app.operand_mtf_algorithm_vars["MTF @ freq"].set("PSF FFT")
    app.operand_field_vars["MTF @ freq"].set("0")
    app._update_operand_setup_visibility()
    try:
        for field, width in (
            ("label", 75),
            ("surface", 115),
            ("name", 180),
            ("thickness", 150),
            ("diameter", 115),
        ):
            app.table.column(field, width=width)
    except Exception:
        pass


def _set_sidebars(app: KrakenLayoutEditor, *, left: bool, right: bool) -> None:
    try:
        left_present = app._pane_present(app.left_sidebar_host)
        if left_present != left:
            app.toggle_left_sidebar()
    except Exception:
        pass
    try:
        right_present = app._pane_present(app.right_sidebar_host)
        if right_present != right:
            app.toggle_right_sidebar()
    except Exception:
        pass
    app.update_idletasks()
    app.update()


def _show_state(app: KrakenLayoutEditor, *, analysis_mode: str = "none") -> None:
    app.set_analysis_mode(analysis_mode)
    app.refresh_plot(suppress_analysis=(analysis_mode == "none"))
    app.update_idletasks()
    app.update()
    app.lift()
    try:
        app.attributes("-topmost", True)
        app.after(250, lambda: app.attributes("-topmost", False))
    except Exception:
        pass
    app.update_idletasks()
    app.update()
    time.sleep(0.35)
    app.update()


def _capture_window_image(widget) -> Image.Image:
    tmp_path = Path("/tmp/kraken_machine_vision_case_capture_tmp.png")
    importer = shutil.which("import")
    if importer:
        try:
            subprocess.run(
                [importer, "-window", str(widget.winfo_id()), str(tmp_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=15,
            )
            if tmp_path.exists() and tmp_path.stat().st_size > 2048:
                image = Image.open(tmp_path).convert("RGB")
                tmp_path.unlink(missing_ok=True)
                return image
        except Exception:
            tmp_path.unlink(missing_ok=True)
    x0 = int(widget.winfo_rootx())
    y0 = int(widget.winfo_rooty())
    screen_width = int(widget.winfo_screenwidth())
    screen_height = int(widget.winfo_screenheight())
    x1 = min(x0 + int(widget.winfo_width()), screen_width)
    y1 = min(y0 + int(widget.winfo_height()), screen_height)
    image = ImageGrab.grab(bbox=(max(0, x0), max(0, y0), x1, y1))
    return image.convert("RGB")


def _save_window(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    _capture_window_image(app).save(path, optimize=True)
    return path


def _save_canvas(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    image = _capture_window_image(app.canvas.get_tk_widget())
    image.save(path, optimize=True)
    return path


def _save_analysis_aoi(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    image = _capture_window_image(app.canvas.get_tk_widget())
    width, height = image.size
    # With an analysis active, the right side of the Matplotlib canvas is the
    # actionable analysis plot. Crop that AOI for boss-demo documentation.
    crop = image.crop((int(width * 0.50), int(height * 0.04), int(width * 0.985), int(height * 0.965)))
    crop.save(path, optimize=True)
    return path


def _defocus_sensor(app: KrakenLayoutEditor) -> None:
    app.rows[5].thickness = DEFOCUSED_SENSOR_DISTANCE_MM
    app.rows[5].optimize_thickness = False
    app.rows[5].optimize_thickness_bounds = None
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(5)
    app.status_var.set("Case Study 2: sensor deliberately moved too close to the lens.")


def _mark_sensor_for_focus_solve(app: KrakenLayoutEditor) -> None:
    app.rows[5].optimize_thickness = True
    app.rows[5].optimize_thickness_bounds = BEST_FOCUS_BOUNDS_MM
    app._sync_table()
    app._select_table_row(5)
    app.status_var.set("Case Study 2: S5 Thickness is the focus variable; Spot RMS is the target.")


def _apply_best_focus(app: KrakenLayoutEditor) -> dict[str, float | str]:
    result = app._compute_best_focus_result(5)
    app.rows[5].thickness = float(result["solved_distance"])
    app.rows[5].optimize_thickness = True
    app.rows[5].optimize_thickness_bounds = BEST_FOCUS_BOUNDS_MM
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(5)
    app.status_var.set(str(result["message"]))
    return result


def _set_wide_field(app: KrakenLayoutEditor) -> None:
    app.field_type_var.set("Real Image Height")
    app.field_value_var.set("11.52")
    app.field_count_var.set("3")
    app.spot_view_mode_var.set("Grid")
    app.status_var.set("Case Study 2: wide-field check at the measured sensor half-height.")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_machine_vision_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "01_loaded_machine_vision_plot.png"))

        _set_sidebars(app, left=False, right=False)
        _defocus_sensor(app)
        _show_state(app, analysis_mode="spot")
        outputs.append(_save_analysis_aoi(app, output_dir, "02_defocused_spot_aoi.png"))

        _show_state(app, analysis_mode="mtf")
        outputs.append(_save_analysis_aoi(app, output_dir, "03_defocused_mtf_aoi.png"))

        _set_sidebars(app, left=False, right=True)
        _mark_sensor_for_focus_solve(app)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "04_focus_variable_setup_ui.png"))

        _set_sidebars(app, left=False, right=False)
        _apply_best_focus(app)
        _show_state(app, analysis_mode="spot")
        outputs.append(_save_analysis_aoi(app, output_dir, "05_refocused_spot_aoi.png"))

        _show_state(app, analysis_mode="mtf")
        outputs.append(_save_analysis_aoi(app, output_dir, "06_refocused_mtf_aoi.png"))

        _set_wide_field(app)
        _show_state(app, analysis_mode="spot")
        outputs.append(_save_analysis_aoi(app, output_dir, "07_wide_field_spot_aoi.png"))
    finally:
        app.destroy()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    paths = capture(args.output_dir)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
