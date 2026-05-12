"""Capture screenshots for the Double Gauss analysis-suite case study.

Run from the project root with a display:

    python -m KrakenOS.UI.capture_double_gauss_analysis_case_study_screenshots
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "double_gauss_analysis_suite"
LAYOUT_NAME = "Double Gauss PSF MTF Wavefront Zernike Case Study"


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
    app.ray_count_var.set("17")
    app.ray_height_factor_var.set("0.8")
    app.source_model_var.set("Pupil / field")
    app.field_type_var.set("Angle")
    app.field_value_var.set("0.0")
    app.field_count_var.set("1")
    app.aperture_type_var.set("EPD")
    app.aperture_value_var.set("4.0")
    app.spot_view_mode_var.set("Centroid")
    app.image_diameter_mode_var.set("Auto")
    app.show_cardinals_var.set(True)
    app.show_physical_distances_var.set(True)
    app.show_path_labels_var.set(False)
    app.show_path_labels = False
    app.wavefront_style_var.set("Wavefront Function")
    app._set_selected_operand_labels(["Spot RMS", "MTF @ freq", "Wavefront RMS"])
    app.operand_target_vars["MTF @ freq"].set("0.35")
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
    tmp_path = Path("/tmp/kraken_double_gauss_analysis_capture_tmp.png")
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
    return ImageGrab.grab(bbox=(max(0, x0), max(0, y0), x1, y1)).convert("RGB")


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


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_double_gauss_analysis_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "01_double_gauss_layout.png"))

        _set_sidebars(app, left=False, right=False)
        for mode, filename in (
            ("spot", "02_spot_aoi.png"),
            ("psf", "03_psf_aoi.png"),
            ("mtf", "04_mtf_aoi.png"),
            ("wavefront", "05_wavefront_aoi.png"),
            ("zernike", "06_zernike_aoi.png"),
        ):
            _show_state(app, analysis_mode=mode)
            outputs.append(_save_analysis_aoi(app, output_dir, filename))
    finally:
        app.destroy()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    for path in capture(args.output_dir):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
