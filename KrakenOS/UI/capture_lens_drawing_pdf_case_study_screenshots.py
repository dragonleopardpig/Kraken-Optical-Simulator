"""Capture screenshots and artifacts for the lens drawing PDF case study.

Run from the project root with:

    python -m KrakenOS.UI.capture_lens_drawing_pdf_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageGrab

from KrakenOS.Examples.Examp_Lens_Drawing_PDF_Export import (
    build_rows,
    export_pdf,
    export_properties_json,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "lens_drawing_pdf_export"
PDF_NAME = "multi_element_lens_fabrication_drawing.pdf"
JSON_NAME = "triplet_surface_properties.json"


def _capture_window_image(widget) -> Image.Image:
    tmp_path = Path("/tmp/kraken_lens_drawing_case_capture_tmp.png")
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


def _settle(app: KrakenLayoutEditor, delay: float = 0.35) -> None:
    app.update_idletasks()
    app.update()
    time.sleep(delay)
    app.update_idletasks()
    app.update()


def _configure_app(app: KrakenLayoutEditor) -> None:
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.rows = build_rows()
    app.current_layout_file = None
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Sequential")
    app.ray_count_var.set("7")
    app.source_radius_var.set("8.0")
    app.field_value_var.set("0.0")
    app.wavelength_var.set("0.55")
    app.auto_save_plot_var.set(False)
    for field, width in (
        ("label", 82),
        ("surface", 120),
        ("name", 245),
        ("glass", 110),
        ("rc", 105),
        ("thickness", 105),
        ("diameter", 95),
        ("advanced", 380),
    ):
        try:
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
    _settle(app, delay=0.15)


def _save_window(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    path = output_dir / filename
    _capture_window_image(app).save(path, optimize=True)
    return path


def _capture_surface_properties_dialog(app: KrakenLayoutEditor, output_dir: Path) -> Path:
    path = output_dir / "02_lens_drawing_surface_properties_dialog.png"

    def capture_and_close() -> None:
        for child in app.winfo_children():
            if child.winfo_exists() and str(child.winfo_class()) == "Toplevel" and "Lens Drawing Surface Properties" in child.title():
                child.geometry("1640x760+70+70")
                _settle(app, delay=0.25)
                _capture_window_image(child).save(path, optimize=True)
                child.destroy()
                return

    app.after(900, capture_and_close)
    app._open_lens_drawing_surface_properties_dialog()
    if not path.exists():
        raise RuntimeError("Lens drawing surface properties dialog screenshot was not captured.")
    return path


def _render_pdf_pages(pdf_path: Path, output_dir: Path) -> list[Path]:
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError("pdftoppm is required to render PDF pages for the docs screenshots.")
    prefix = output_dir / "pdf_page"
    subprocess.run(
        [pdftoppm, "-png", "-r", "140", str(pdf_path), str(prefix)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    rendered = sorted(output_dir.glob("pdf_page-*.png"))
    names = [
        "03_pdf_assembly_sheet.png",
        "04_pdf_element_1_sheet.png",
        "05_pdf_element_2_sheet.png",
        "06_pdf_element_3_sheet.png",
    ]
    outputs: list[Path] = []
    for source, name in zip(rendered, names, strict=False):
        target = output_dir / name
        source.replace(target)
        outputs.append(target)
    for leftover in output_dir.glob("pdf_page-*.png"):
        leftover.unlink(missing_ok=True)
    if len(outputs) != 4:
        raise RuntimeError(f"Expected four rendered PDF pages, got {len(outputs)}.")
    return outputs


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = build_rows()
    outputs: list[Path] = []
    export_properties_json(rows, output_dir / JSON_NAME)
    pdf_path = export_pdf(rows, output_dir / PDF_NAME)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry("1760x960+40+40")
        _configure_app(app)
        _set_sidebars(app, left=True, right=True)
        app.refresh_plot(suppress_analysis=True)
        _settle(app)
        outputs.append(_save_window(app, output_dir, "01_multi_element_lens_table_ui.png"))
        outputs.append(_capture_surface_properties_dialog(app, output_dir))
    finally:
        app.destroy()

    outputs.extend(_render_pdf_pages(pdf_path, output_dir))
    outputs.append(pdf_path)
    outputs.append(output_dir / JSON_NAME)
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
