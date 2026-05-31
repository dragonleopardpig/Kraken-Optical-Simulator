"""Capture UI screenshots for the multi-source illumination case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_multi_source_case_study_screenshots
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "multi_source_illumination"
LAYOUT_NAME = "Multi-Source Illumination Example"
DETECTOR_TARGET = "2: Shared detector"


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
    app.show_path_labels_var.set(True)
    app.show_path_labels = True
    app.ray_display_mode_var.set("All rays")
    app.detector_bins_var.set("64")
    app.analysis_branch_filter_var.set("All paths")
    app.analysis_surface_var.set(DETECTOR_TARGET)
    try:
        for field, width in (
            ("label", 82),
            ("surface", 155),
            ("name", 245),
            ("glass", 150),
            ("rc", 105),
            ("thickness", 130),
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


def _fit_multisource_axes(app: KrakenLayoutEditor) -> None:
    try:
        app.ax.set_xlim(-6.0, 86.0)
        app.ax.set_ylim(-17.0, 17.0)
        app.canvas.draw_idle()
    except Exception:
        pass


def _show_state(app: KrakenLayoutEditor, *, analysis_mode: str = "none", fit_axes: bool = True) -> None:
    app.set_analysis_mode(analysis_mode)
    app.refresh_plot(suppress_analysis=(analysis_mode == "none"))
    if fit_axes:
        _fit_multisource_axes(app)
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
    tmp_path = Path("/tmp/kraken_multi_source_case_capture_tmp.png")
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


def _capture_widget_bounds_image(widget) -> Image.Image:
    widget.update_idletasks()
    x0 = int(widget.winfo_rootx())
    y0 = int(widget.winfo_rooty())
    x1 = x0 + int(widget.winfo_width())
    y1 = y0 + int(widget.winfo_height())
    return ImageGrab.grab(bbox=(x0, y0, x1, y1)).convert("RGB")


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
    crop = image.crop((int(width * 0.67), int(height * 0.04), int(width * 0.985), int(height * 0.965)))
    crop.save(path, optimize=True)
    return path


def _save_source_manager(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    app.open_scene_source_manager()
    windows = [
        child
        for child in app.winfo_children()
        if getattr(child, "winfo_exists", lambda: False)() and str(child.winfo_class()) == "Toplevel"
    ]
    dialog = next((window for window in reversed(windows) if "Scene Source Manager" in str(window.title())), None)
    if dialog is None:
        raise RuntimeError("Scene Source Manager did not open")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.35)
    dialog.update()
    path = output_dir / filename
    _capture_window_image(dialog).save(path, optimize=True)
    dialog.destroy()
    app.update_idletasks()
    app.update()
    return path


def _save_source_report(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    dialog = app._main_source_illumination_report_dialog()
    dialog.open_source_illumination_report()
    window = dialog._source_illumination_window
    if window is None:
        raise RuntimeError("Source Illumination Report window did not open")
    dialog._source_illumination_target_var.set(DETECTOR_TARGET)
    dialog._refresh_source_illumination_report()
    window.update_idletasks()
    window.update()
    time.sleep(0.35)
    window.update()
    path = output_dir / filename
    _capture_widget_bounds_image(window).save(path, optimize=True)
    return path


def _assert_controls(app: KrakenLayoutEditor) -> None:
    targets = list(app.analysis_surface_menu["values"])
    if DETECTOR_TARGET not in targets:
        raise RuntimeError(f"{DETECTOR_TARGET!r} was not discovered; choices={targets!r}")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)
        _assert_controls(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_multi_source_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "02_multi_source_layout_plot.png"))

        outputs.append(_save_source_manager(app, output_dir, "03_scene_source_manager.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_source_report(app, output_dir, "04_source_illumination_report.png"))

        _show_state(app, analysis_mode="detector_map")
        outputs.append(_save_analysis_aoi(app, output_dir, "05_detector_map_aoi.png"))

        _show_state(app, analysis_mode="relative_illumination")
        outputs.append(_save_analysis_aoi(app, output_dir, "06_source_illumination_map_aoi.png"))
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
