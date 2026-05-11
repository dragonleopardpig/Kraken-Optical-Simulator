"""Capture UI screenshots for the tolerance Monte Carlo case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_tolerance_monte_carlo_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import textwrap
import time
from pathlib import Path
import tkinter as tk

from PIL import Image, ImageGrab

from KrakenOS.UI.layout_editor import KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "tolerance_monte_carlo"
LAYOUT_NAME = "Native Variable Breadth Example"
TOLERANCE_SAMPLE_COUNT = 9
TOLERANCE_SEED = 2026


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1760x960+40+40")
    app.auto_save_plot_var.set(False)
    app.load_layout_by_name(LAYOUT_NAME, refresh=False)
    app.display_orientation_var.set("Vertical")
    app.tolerance_compare_view_var.set("Spot overlay")
    app.ray_count_var.set("15")
    app.field_count_var.set("3")
    app.field_value_var.set("3.0")
    app.wavelength_var.set("0.55")
    app.spot_view_mode_var.set("Grid")
    try:
        for field, width in (
            ("label", 80),
            ("surface", 135),
            ("name", 260),
            ("glass", 110),
            ("rc", 105),
            ("k", 95),
            ("thickness", 115),
            ("diameter", 105),
            ("tilt_x", 95),
            ("advanced", 190),
        ):
            app.table.column(field, width=width)
    except Exception:
        pass


def _configure_tolerance_metadata(app: KrakenLayoutEditor) -> dict[str, object]:
    app.set_tolerance_compensator_enabled(1, "k", True)
    app.set_tolerance_compensator_enabled(1, "TiltX", False)
    app.set_tolerance_coupling(1, "k", "shared_mount", sign=1)
    app.set_tolerance_coupling(1, "TiltX", "shared_mount", sign=-1)
    app.add_tolerance_manufacturing_template(
        "Shared machined mount",
        source_type="machined mount",
        source_id="MNT-001",
        tags=("cell", "vendor-a"),
        note="shared cell machining",
    )
    for parameter in ("k", "TiltX"):
        app.apply_tolerance_manufacturing_template(1, parameter, "Shared machined mount")
    preset = app.save_tolerance_solve_preset(
        "K-only compensation",
        sample_count=TOLERANCE_SAMPLE_COUNT,
        seed=TOLERANCE_SEED,
        compensator_steps=5,
        multi_steps=3,
        multi_passes=2,
        tolerance_compare_view="Spot overlay",
    )
    app.apply_tolerance_solve_preset("K-only compensation")
    app._sync_table()
    app.update_idletasks()
    app.update()
    return preset


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
    tmp_path = Path("/tmp/kraken_tolerance_case_capture_tmp.png")
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


def _save_analysis_aoi(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    image = _capture_window_image(app.canvas.get_tk_widget())
    width, height = image.size
    crop = image.crop((int(width * 0.50), int(height * 0.04), int(width * 0.985), int(height * 0.965)))
    crop.save(path, optimize=True)
    return path


def _save_report_window(app: KrakenLayoutEditor, output_dir: Path, filename: str, title: str, report: str) -> Path:
    window = tk.Toplevel(app)
    window.withdraw()
    window.title(title)
    window.geometry("1180x760+180+120")
    window.transient(app)
    frame = tk.Frame(window, padx=14, pady=14)
    frame.pack(fill="both", expand=True)
    label = tk.Label(frame, text=title, anchor="w", font=("DejaVu Sans", 15, "bold"))
    label.pack(fill="x", pady=(0, 8))
    text = tk.Text(frame, wrap="word", font=("DejaVu Sans Mono", 10), padx=10, pady=10)
    scroll = tk.Scrollbar(frame, command=text.yview)
    text.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    text.pack(side="left", fill="both", expand=True)
    text.insert("1.0", textwrap.dedent(report).strip() + "\n")
    text.configure(state="disabled")
    window.deiconify()
    window.lift()
    window.update_idletasks()
    window.update()
    time.sleep(0.35)
    window.update()
    path = output_dir / filename
    _capture_window_image(window).save(path, optimize=True)
    window.destroy()
    app.update_idletasks()
    app.update()
    return path


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)
        preset = _configure_tolerance_metadata(app)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_tolerance_ui.png"))

        summary = app.run_tolerance_monte_carlo(sample_count=TOLERANCE_SAMPLE_COUNT, seed=TOLERANCE_SEED)
        comparison = app.tolerance_worst_sample_comparison(summary)
        stackup = app.tolerance_stackup_dashboard(summary)
        sweep = app.run_tolerance_compensator_sweep(summary, steps=5)
        multi = app.run_tolerance_multi_compensator_solve(summary, steps=3, passes=2)

        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "02_tolerance_solve_preset_report.png",
                "Tolerance Solve Preset",
                app.tolerance_solve_preset_report_text(preset),
            )
        )
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "03_monte_carlo_report.png",
                "Tolerance Monte Carlo Report",
                app.tolerance_monte_carlo_report_text(summary),
            )
        )
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "04_worst_sample_report.png",
                "Tolerance Worst-Sample Comparison",
                app.tolerance_worst_sample_comparison_report_text(comparison),
            )
        )

        _set_sidebars(app, left=False, right=False)
        app.tolerance_compare_view_var.set("Spot overlay")
        _show_state(app, analysis_mode="tolerance_compare")
        outputs.append(_save_analysis_aoi(app, output_dir, "05_tolcmp_spot_overlay_aoi.png"))

        app.tolerance_compare_view_var.set("Stack-up bars")
        _show_state(app, analysis_mode="tolerance_compare")
        outputs.append(_save_analysis_aoi(app, output_dir, "06_tolcmp_stackup_bars_aoi.png"))

        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "07_compensator_sweep_report.png",
                "Tolerance Compensator Sweep",
                app.tolerance_compensator_sweep_report_text(sweep),
            )
        )
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "08_multi_compensator_report.png",
                "Tolerance Multi-Compensator Solve",
                app.tolerance_multi_compensator_report_text(multi),
            )
        )

        app.tolerance_compare_view_var.set("MTF overlay")
        _show_state(app, analysis_mode="tolerance_compare")
        outputs.append(_save_analysis_aoi(app, output_dir, "09_tolcmp_mtf_overlay_aoi.png"))
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
