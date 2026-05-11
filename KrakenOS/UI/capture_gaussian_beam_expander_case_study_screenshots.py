"""Capture UI screenshots for the Gaussian beam-expander case study.

This script needs a real display because it captures the actual Tk editor
window and Gaussian Beam Report dialog. Run it from the project root with:

    python -m KrakenOS.UI.capture_gaussian_beam_expander_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
import tkinter as tk
import warnings
from dataclasses import asdict
from pathlib import Path

from PIL import Image, ImageGrab

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "gaussian_beam_expander"
LAYOUT_NAME = "Gaussian Laser Beam Expander Case Study"

warnings.filterwarnings("ignore", message="divide by zero encountered in scalar divide", category=RuntimeWarning)
warnings.filterwarnings("ignore", message="invalid value encountered in scalar divide", category=RuntimeWarning)


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
    app.wavelength_var.set("0.6328")
    app.ray_count_var.set("25")
    app.source_model_var.set("Gaussian beam")
    app.gaussian_input_mode_var.set("Diameter + divergence")
    app.gaussian_beam_diameter_var.set("1.0")
    app.gaussian_full_divergence_var.set("1.0")
    app.gaussian_waist_side_var.set("Waist before source")
    app.gaussian_m2_var.set("1.0")
    app.source_power_var.set("1.0")
    app.source_x_var.set("0.0")
    app.source_y_var.set("0.0")
    app.source_z_var.set("0.0")
    app.source_l_var.set("0.0")
    app.source_m_var.set("0.0")
    app.source_n_var.set("1.0")
    app.source_direction_preset_var.set("Horizontal +Z (right)")
    app.detector_bins_var.set("64")
    app.coherent_sum_mode_var.set("Mutual coherent")
    app.branch_field_propagation_mm_var.set("0.0")
    app.show_cardinals_var.set(True)
    app.show_physical_distances_var.set(True)
    app.show_path_labels_var.set(True)
    app.show_path_labels = True
    app._sync_left_mode_controls()
    try:
        for field, width in (
            ("label", 70),
            ("surface", 130),
            ("name", 210),
            ("rc", 115),
            ("thickness", 145),
            ("diameter", 120),
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
    tmp_path = Path("/tmp/kraken_gaussian_expander_case_capture_tmp.png")
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


def _open_gaussian_report(app: KrakenLayoutEditor) -> tk.Toplevel:
    before = {id(child) for child in app.winfo_children()}
    app.open_gaussian_beam_report()
    app.update_idletasks()
    app.update()
    time.sleep(0.4)
    app.update()
    candidates = [
        child
        for child in app.winfo_children()
        if id(child) not in before
        and isinstance(child, tk.Toplevel)
        and child.winfo_exists()
        and "Gaussian Beam Report" in str(child.title())
    ]
    if not candidates:
        candidates = [
            child
            for child in app.winfo_children()
            if isinstance(child, tk.Toplevel)
            and child.winfo_exists()
            and "Gaussian Beam Report" in str(child.title())
        ]
    if not candidates:
        raise RuntimeError("Gaussian Beam Report dialog was not created")
    window = candidates[-1]
    window.lift()
    window.update_idletasks()
    window.update()
    time.sleep(0.35)
    window.update()
    return window


def _save_gaussian_report(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    window = _open_gaussian_report(app)
    try:
        path = output_dir / filename
        _capture_window_image(window).save(path, optimize=True)
        return path
    finally:
        try:
            window.destroy()
        except Exception:
            pass
        app.update()


def _apply_expander(app: KrakenLayoutEditor) -> None:
    rows = [
        SurfaceRow(surface="Object", name="Laser output", thickness=80.0, diameter=16.0, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="Input lens f=50", rc=50.0, thickness=200.0, diameter=20.0, glass="AIR"),
        SurfaceRow(surface="Thin Lens", name="Collimating lens f=150", rc=150.0, thickness=320.0, diameter=45.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Readout plane", thickness=0.0, diameter=50.0, glass="AIR"),
    ]
    app.rows = [SurfaceRow(**asdict(row)) for row in rows]
    app._auto_assign_missing_elements(app.rows)
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(2)
    app.status_var.set("Case Study 3: Keplerian 3x beam expander inserted.")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_sidebars(app, left=True, right=False)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_datasheet_gaussian_source_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "02_free_space_gaussian_layout.png"))
        outputs.append(_save_gaussian_report(app, output_dir, "03_free_space_gaussian_report.png"))

        _apply_expander(app)
        _set_sidebars(app, left=False, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "04_expander_table_ui.png"))
        outputs.append(_save_canvas(app, output_dir, "05_expander_gaussian_layout.png"))
        outputs.append(_save_gaussian_report(app, output_dir, "06_expander_gaussian_report.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="branch_field")
        outputs.append(_save_analysis_aoi(app, output_dir, "07_expander_bfield_aoi.png"))
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
