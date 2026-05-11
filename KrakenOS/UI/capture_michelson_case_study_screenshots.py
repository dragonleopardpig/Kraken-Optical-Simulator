"""Capture UI screenshots for the Michelson beam-splitter case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_michelson_case_study_screenshots
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "michelson_interferometer"
LAYOUT_NAME = "Michelson Interferometer (Interferogram)"
DETECTOR_PATH_VIEW = "Path 4: Detector output path"


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1760x960+40+40")
    app.auto_save_plot_var.set(False)
    app.load_layout_by_name(LAYOUT_NAME, refresh=False)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.nonseq_energy_probability_var.set(False)
    app.show_path_labels_var.set(True)
    app.show_path_labels = True
    app.ray_display_mode_var.set("All rays")
    app.coherent_sum_mode_var.set("Mutual coherent")
    app.branch_field_propagation_mm_var.set("0.0")
    app.detector_bins_var.set("128")
    try:
        for field, width in (
            ("label", 78),
            ("surface", 135),
            ("name", 220),
            ("rc", 110),
            ("thickness", 135),
            ("diameter", 115),
            ("tilt_x", 95),
            ("desp_y", 95),
            ("desp_z", 95),
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
    tmp_path = Path("/tmp/kraken_michelson_case_capture_tmp.png")
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


def _set_chief_ray_demo(app: KrakenLayoutEditor) -> None:
    app.ray_count_var.set("1")
    app.source_radius_var.set("0.5")
    app.detector_bins_var.set("64")
    app.arm_view_var.set("All paths")


def _set_dense_detector_demo(app: KrakenLayoutEditor) -> None:
    app.ray_count_var.set("121")
    app.source_radius_var.set("8.0")
    app.detector_bins_var.set("128")
    app.coherent_sum_mode_var.set("Mutual coherent")
    app.branch_field_propagation_mm_var.set("0.0")
    app.arm_view_var.set("All paths")


def _set_detector_path_view(app: KrakenLayoutEditor) -> None:
    app._refresh_arm_view_choices()
    choices = list(app.arm_view_menu["values"])
    if DETECTOR_PATH_VIEW not in choices:
        raise RuntimeError(f"{DETECTOR_PATH_VIEW!r} was not discovered; choices={choices!r}")
    app.arm_view_var.set(DETECTOR_PATH_VIEW)
    app.set_arm_view()
    app.update_idletasks()
    app.update()
    time.sleep(0.35)
    app.update()


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_chief_ray_demo(app)
        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_michelson_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "02_michelson_path_labels.png"))

        _set_sidebars(app, left=False, right=False)
        _set_detector_path_view(app)
        outputs.append(_save_window(app, output_dir, "03_detector_path_view_ui.png"))

        _set_dense_detector_demo(app)
        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="detector_map")
        outputs.append(_save_analysis_aoi(app, output_dir, "04_detector_map_aoi.png"))

        _show_state(app, analysis_mode="coherent_detector")
        outputs.append(_save_analysis_aoi(app, output_dir, "05_coherent_detector_aoi.png"))

        _show_state(app, analysis_mode="interferogram")
        outputs.append(_save_analysis_aoi(app, output_dir, "06_interferogram_aoi.png"))

        _show_state(app, analysis_mode="branch_field")
        outputs.append(_save_analysis_aoi(app, output_dir, "07_branch_field_aoi.png"))
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
