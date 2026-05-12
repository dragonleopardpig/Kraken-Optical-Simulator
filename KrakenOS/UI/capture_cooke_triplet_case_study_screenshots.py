"""Capture UI screenshots for the Cooke-triplet optimization case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_cooke_triplet_case_study_screenshots
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageGrab

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, LAYOUTS_DIR


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "cooke_triplet_optimization"
LAYOUT_NAME = "Cooke Triplet Optimization Case Study"
LAYOUT_PATH = LAYOUTS_DIR / "cooke_triplet_optimization_case_study.py"


def _load_layout_module():
    spec = importlib.util.spec_from_file_location("cooke_triplet_optimization_case_study", LAYOUT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load layout module: {LAYOUT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1760x960+40+40")
    app.auto_save_plot_var.set(False)
    app.load_layout_by_name(LAYOUT_NAME, refresh=False)
    app.object_mode_var.set("Infinity")
    app.display_orientation_var.set("Vertical")
    app.wavelength_var.set("0.55")
    app.ray_count_var.set("13")
    app.ray_height_factor_var.set("0.8")
    app.source_model_var.set("Pupil / field")
    app.field_type_var.set("Angle")
    app.field_value_var.set("14.0")
    app.field_count_var.set("2")
    app.aperture_type_var.set("EPD")
    app.aperture_value_var.set("10.0")
    app.spot_view_mode_var.set("Grid")
    app.image_diameter_mode_var.set("Manual")
    app.show_cardinals_var.set(True)
    app.show_physical_distances_var.set(True)
    app.show_path_labels_var.set(False)
    app.show_path_labels = False
    app._set_selected_operand_labels(["Spot RMS", "MTF @ freq"])
    app.operand_target_vars["Spot RMS"].set("0")
    app.operand_weight_vars["Spot RMS"].set("1")
    app.operand_wavelength_vars["Spot RMS"].set("0.55")
    app.operand_field_vars["Spot RMS"].set("0")
    app.operand_target_vars["MTF @ freq"].set("0.35")
    app.operand_weight_vars["MTF @ freq"].set("0.5")
    app.operand_wavelength_vars["MTF @ freq"].set("0.55")
    app.operand_field_vars["MTF @ freq"].set("14")
    app.operand_frequency_vars["MTF @ freq"].set("20")
    app.operand_mtf_algorithm_vars["MTF @ freq"].set("PSF FFT")
    app._update_operand_setup_visibility()
    try:
        for field, width in (
            ("label", 80),
            ("surface", 120),
            ("name", 230),
            ("rc", 125),
            ("thickness", 135),
            ("diameter", 110),
            ("glass", 95),
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
    tmp_path = Path("/tmp/kraken_cooke_triplet_case_capture_tmp.png")
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
    _capture_window_image(app.canvas.get_tk_widget()).save(path, optimize=True)
    return path


def _save_analysis_aoi(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    image = _capture_window_image(app.canvas.get_tk_widget())
    width, height = image.size
    crop = image.crop((int(width * 0.50), int(height * 0.04), int(width * 0.985), int(height * 0.965)))
    crop.save(path, optimize=True)
    return path


def _apply_optimized_prescription(app: KrakenLayoutEditor) -> None:
    module = _load_layout_module()
    app.rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in module.OPTIMIZED_SURFACES]
    app._auto_assign_missing_elements(app.rows)
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)
    app.status_var.set("Case Study 15: optimized Cooke-triplet prescription applied.")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_starting_cooke_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "01_starting_cooke_layout.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="spot")
        outputs.append(_save_analysis_aoi(app, output_dir, "02_starting_spot_aoi.png"))

        _show_state(app, analysis_mode="mtf")
        outputs.append(_save_analysis_aoi(app, output_dir, "03_starting_mtf_aoi.png"))

        _apply_optimized_prescription(app)
        _set_sidebars(app, left=False, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "04_optimized_prescription_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "04_optimized_cooke_layout.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="spot")
        outputs.append(_save_analysis_aoi(app, output_dir, "05_optimized_spot_aoi.png"))

        _show_state(app, analysis_mode="mtf")
        outputs.append(_save_analysis_aoi(app, output_dir, "06_optimized_mtf_aoi.png"))
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
