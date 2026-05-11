"""Capture UI screenshots for the Zemax LED diffuse-object case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_zemax_led_diffuse_case_study_screenshots
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
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "zemax_led_diffuse_imaging"
LAYOUT_NAME = "Zemax LED Beam-Splitter Imaging"
OBJECT_PATH_VIEW = "Path 2: 45 deg 50/50 beam splitter to 45 deg 50/50 beam splitter via Diffuse object target"
IMAGE_PATH_VIEW = "Path 5: 45 deg 50/50 beam splitter to Image plane via Splitter rear exit face, Imaging lens front, Imaging lens back"
DIFFUSE_TARGET = "3: Diffuse object target"
IMAGE_TARGET = "6: Image plane"


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
    app.ray_display_mode_var.set("Beam-splitter paths")
    app.detector_bins_var.set("64")
    app.analysis_branch_filter_var.set("All paths")
    try:
        for field, width in (
            ("label", 82),
            ("surface", 150),
            ("name", 255),
            ("glass", 130),
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
    tmp_path = Path("/tmp/kraken_zemax_led_diffuse_case_capture_tmp.png")
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
    crop = image.crop((int(width * 0.54), int(height * 0.04), int(width * 0.985), int(height * 0.965)))
    crop.save(path, optimize=True)
    return path


def _save_source_report(app: KrakenLayoutEditor, output_dir: Path, filename: str, target: str) -> Path:
    app.open_source_illumination_report()
    window = app._source_illumination_window
    if window is None:
        raise RuntimeError("Source Illumination Report window did not open")
    app._source_illumination_target_var.set(target)
    app._refresh_source_illumination_report()
    window.update_idletasks()
    window.update()
    time.sleep(0.35)
    window.update()
    path = output_dir / filename
    _capture_window_image(window).save(path, optimize=True)
    return path


def _save_diffuse_dialog(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    app.open_diffuse_scatter_settings(3)
    windows = [
        child
        for child in app.winfo_children()
        if getattr(child, "winfo_exists", lambda: False)() and str(child.winfo_class()) == "Toplevel"
    ]
    dialog = next((window for window in reversed(windows) if "Diffuse / BRDF" in str(window.title())), None)
    if dialog is None:
        raise RuntimeError("Diffuse / BRDF settings dialog did not open")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.35)
    dialog.update()
    path = output_dir / filename
    _capture_window_image(dialog).save(path, optimize=True)
    return path


def _set_path_view(app: KrakenLayoutEditor, path_view: str) -> None:
    app._refresh_arm_view_choices()
    choices = list(app.arm_view_menu["values"])
    if path_view not in choices:
        raise RuntimeError(f"{path_view!r} was not discovered; choices={choices!r}")
    app.arm_view_var.set(path_view)
    app.set_arm_view()
    app.update_idletasks()
    app.update()
    time.sleep(0.35)
    app.update()


def _assert_analysis_controls(app: KrakenLayoutEditor) -> None:
    targets = list(app.analysis_surface_menu["values"])
    for target in (DIFFUSE_TARGET, IMAGE_TARGET):
        if target not in targets:
            raise RuntimeError(f"{target!r} was not discovered; choices={targets!r}")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)
        _assert_analysis_controls(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_zemax_led_diffuse_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "02_zemax_led_diffuse_path_labels.png"))

        _set_sidebars(app, left=False, right=False)
        _set_path_view(app, OBJECT_PATH_VIEW)
        outputs.append(_save_window(app, output_dir, "03_diffuse_object_path_view_ui.png"))

        _set_path_view(app, IMAGE_PATH_VIEW)
        outputs.append(_save_window(app, output_dir, "04_image_path_view_ui.png"))

        outputs.append(_save_diffuse_dialog(app, output_dir, "05_diffuse_brdf_settings_dialog.png"))
        app.focus_force()
        _set_sidebars(app, left=False, right=False)
        app.arm_view_var.set("All paths")
        app.set_arm_view()
        app.analysis_surface_var.set(IMAGE_TARGET)
        app.analysis_branch_filter_var.set("All paths")
        _show_state(app, analysis_mode="none")

        outputs.append(_save_source_report(app, output_dir, "06_diffuse_object_source_report.png", DIFFUSE_TARGET))
        outputs.append(_save_source_report(app, output_dir, "07_image_plane_source_report.png", IMAGE_TARGET))

        _show_state(app, analysis_mode="detector_map")
        outputs.append(_save_analysis_aoi(app, output_dir, "08_image_detector_map_aoi.png"))

        _show_state(app, analysis_mode="relative_illumination")
        outputs.append(_save_analysis_aoi(app, output_dir, "09_image_source_illumination_map_aoi.png"))
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
