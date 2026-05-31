"""Capture focused UI screenshots for the Sphinx manual.

This script needs a real display because it captures the actual Tk editor and
popup menus. Run it from the project root with:

    python -m KrakenOS.UI.capture_manual_ui_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from PIL import Image, ImageGrab

from KrakenOS.UI.layout_editor import (
    BEAM_SPLITTER_SURFACE,
    KrakenLayoutEditor,
    SurfaceRow,
    VARIABLE_REGISTRY,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "manual" / "ui"


def _configure_app(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1720x920+40+40")
    app.auto_save_plot_var.set(False)
    app.display_orientation_var.set("Vertical")
    app.wavelength_var.set("0.5876")
    app.ray_count_var.set("7")
    app.field_value_var.set("0")
    app.field_count_var.set("1")
    app.selected_analysis_modes.clear()


def _settle(app: KrakenLayoutEditor, delay: float = 0.25) -> None:
    app.update_idletasks()
    app.update()
    app.lift()
    try:
        app.attributes("-topmost", True)
        app.after(120, lambda: app.attributes("-topmost", False))
    except Exception:
        pass
    app.update_idletasks()
    app.update()
    time.sleep(delay)
    app.update()


def _settle_toplevel(app: KrakenLayoutEditor, window: tk.Toplevel, delay: float = 0.25) -> None:
    app.update_idletasks()
    window.update_idletasks()
    window.lift()
    try:
        window.attributes("-topmost", True)
        window.after(120, lambda: window.attributes("-topmost", False))
    except Exception:
        pass
    app.update()
    window.update_idletasks()
    time.sleep(delay)
    app.update()


def _set_sidebars(app: KrakenLayoutEditor, *, left: bool, right: bool) -> None:
    try:
        if app._pane_present(app.left_sidebar_host) != left:
            app.toggle_left_sidebar()
    except Exception:
        pass
    try:
        if app._pane_present(app.right_sidebar_host) != right:
            app.toggle_right_sidebar()
    except Exception:
        pass
    _settle(app, delay=0.05)


def _capture_window_image(widget) -> Image.Image:
    widget.update_idletasks()
    importer = shutil.which("import")
    tmp_path = DEFAULT_OUTPUT_DIR / "_capture_tmp.png"
    if importer:
        try:
            subprocess.run(
                [importer, "-window", str(widget.winfo_id()), str(tmp_path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if tmp_path.exists() and tmp_path.stat().st_size > 2048:
                image = Image.open(tmp_path).convert("RGB")
                try:
                    tmp_path.unlink()
                except OSError:
                    pass
                return image
        except Exception:
            pass
    x0 = int(widget.winfo_rootx())
    y0 = int(widget.winfo_rooty())
    x1 = x0 + int(widget.winfo_width())
    y1 = y0 + int(widget.winfo_height())
    return ImageGrab.grab(bbox=(x0, y0, x1, y1)).convert("RGB")


def _capture_widget_bounds_image(widget) -> Image.Image:
    widget.update_idletasks()
    x0 = int(widget.winfo_rootx())
    y0 = int(widget.winfo_rooty())
    x1 = x0 + int(widget.winfo_width())
    y1 = y0 + int(widget.winfo_height())
    return ImageGrab.grab(bbox=(x0, y0, x1, y1)).convert("RGB")


def _save_window_crop(app: KrakenLayoutEditor, output_dir: Path, filename: str, bbox: tuple[int, int, int, int]) -> Path:
    image = _capture_window_image(app)
    x0, y0, x1, y1 = bbox
    crop = image.crop((max(0, x0), max(0, y0), min(image.width, x1), min(image.height, y1)))
    path = output_dir / filename
    crop.save(path, optimize=True)
    return path


def _save_widget_image(widget, output_dir: Path, filename: str) -> Path:
    image = _capture_window_image(widget)
    path = output_dir / filename
    image.save(path, optimize=True)
    return path


def _save_widget_bounds_image(widget, output_dir: Path, filename: str) -> Path:
    image = _capture_widget_bounds_image(widget)
    path = output_dir / filename
    image.save(path, optimize=True)
    return path


def _save_screen_region(output_dir: Path, filename: str, bbox: tuple[int, int, int, int]) -> Path:
    image = ImageGrab.grab(bbox=bbox).convert("RGB")
    path = output_dir / filename
    image.save(path, optimize=True)
    return path


def _save_menu_excerpt(app: KrakenLayoutEditor, output_dir: Path, filename: str, title: str, rows: list[tuple[str, str]]) -> Path:
    window = tk.Toplevel(app)
    window.withdraw()
    window.title(title)
    window.configure(background="#f2f2f2")
    window.resizable(False, False)
    frame = ttk.Frame(window, padding=(8, 8, 8, 8))
    frame.grid(row=0, column=0, sticky="nsew")
    ttk.Label(frame, text=title, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
    for index, (label, marker) in enumerate(rows, start=1):
        if label == "---":
            ttk.Separator(frame, orient="horizontal").grid(row=index, column=0, columnspan=2, sticky="ew", pady=4)
            continue
        ttk.Label(frame, text=label).grid(row=index, column=0, sticky="w", padx=(0, 28), pady=2)
        ttk.Label(frame, text=marker).grid(row=index, column=1, sticky="e", pady=2)
    window.update_idletasks()
    req_w = max(260, window.winfo_reqwidth())
    req_h = max(80, window.winfo_reqheight())
    window.geometry(f"{req_w}x{req_h}+120+120")
    window.deiconify()
    window.lift()
    _settle(app, delay=0.1)
    path = _save_widget_image(window, output_dir, filename)
    window.destroy()
    return path


def _menu_excerpt_rows(menu: tk.Menu) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    end = menu.index("end")
    if end is None:
        return rows
    for index in range(int(end) + 1):
        entry_type = str(menu.type(index))
        if entry_type == "separator":
            rows.append(("---", ""))
            continue
        try:
            label = str(menu.entrycget(index, "label"))
        except Exception:
            continue
        marker = ">" if entry_type == "cascade" else ""
        rows.append((label, marker))
    return rows


def _basic_plate_rows(*, optimize_rc: bool = False) -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=25.0, drawing=0.0, glass="AIR"),
        SurfaceRow(
            surface="Standard",
            name="Front surface",
            rc=51.7 if optimize_rc else 0.0,
            thickness=5.0,
            diameter=25.0,
            glass="BK7",
            optimize_rc=optimize_rc,
            optimize_rc_bounds=(20.0, 100.0) if optimize_rc else None,
        ),
        SurfaceRow(surface="Standard", name="Rear flat surface", rc=0.0, thickness=96.7, diameter=25.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=1.0, drawing=0.0, glass="AIR"),
    ]


def _apply_rows(app: KrakenLayoutEditor, rows: list[SurfaceRow]) -> None:
    app.rows = app._normalized_rows_copy(rows)
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)


def _load_layout_if_available(app: KrakenLayoutEditor, name: str) -> bool:
    try:
        if name in app.layout_names:
            app.load_layout_by_name(name)
            return True
    except Exception:
        pass
    return False


def _first_row_index_for_surface(app: KrakenLayoutEditor, surface: str) -> int | None:
    for index, row in enumerate(app.rows):
        if row.surface == surface:
            return index
    return None


def _table_cell_root_bbox(app: KrakenLayoutEditor, row_index: int, field: str) -> tuple[int, int, int, int]:
    app._select_table_row(row_index)
    _settle(app, delay=0.05)
    for item in app.table.get_children():
        if app._table_item_row_index(item) == row_index:
            bbox = app.table.bbox(item, field)
            if bbox:
                x, y, w, h = bbox
                root_x = int(app.table.winfo_rootx()) + int(x)
                root_y = int(app.table.winfo_rooty()) + int(y)
                return root_x, root_y, root_x + int(w), root_y + int(h)
    raise RuntimeError(f"Could not find visible table cell for row {row_index}, field {field!r}")


def _capture_context_menu(app: KrakenLayoutEditor, output_dir: Path) -> Path:
    rows = [
        ("Convert Type", ">"),
        ("Insert Component Below", ">"),
        ("Shape / Aperture", ">"),
        ("Material", ">"),
        ("Coating / Polarization", ">"),
        ("Geometry", ">"),
        ("Element", ">"),
        ("Diagnostics", ">"),
        ("Advanced", ">"),
        ("Optimization / Solves", ">"),
    ]
    return _save_menu_excerpt(app, output_dir, "editable_table_context_menu.png", "Table right-click menu", rows)


def _capture_top_menu(app: KrakenLayoutEditor, output_dir: Path, menu, filename: str, *, width: int, height: int) -> Path:
    return _save_menu_excerpt(app, output_dir, filename, "Insert menu", _menu_excerpt_rows(menu))


def _capture_latest_toplevel(app: KrakenLayoutEditor, output_dir: Path, filename: str, *, geometry: str | None = None) -> Path:
    app.update_idletasks()
    app.update()
    windows = [child for child in app.winfo_children() if child.winfo_exists() and str(child.winfo_class()) == "Toplevel"]
    if not windows:
        raise RuntimeError(f"No Toplevel window found for {filename}")
    window = windows[-1]
    if geometry:
        window.geometry(geometry)
    _settle_toplevel(app, window, delay=0.35)
    return _save_widget_bounds_image(window, output_dir, filename)


def _capture_lens_drawing_dialog(app: KrakenLayoutEditor, output_dir: Path) -> Path:
    output_path = output_dir / "lens_drawing_surface_properties.png"

    def capture_and_close() -> None:
        for child in app.winfo_children():
            if child.winfo_exists() and str(child.winfo_class()) == "Toplevel" and "Lens Drawing Surface Properties" in child.title():
                _settle(app, delay=0.1)
                _capture_window_image(child).save(output_path, optimize=True)
                child.destroy()
                return

    # The production dialog waits for the user to close it. Schedule the capture
    # before opening so the script can snapshot the live dialog and continue.
    app.after(700, capture_and_close)
    app._open_lens_drawing_surface_properties_dialog()
    if not output_path.exists():
        raise RuntimeError("Lens drawing properties screenshot was not captured")
    return output_path


def _capture_beam_splitter_dialog(app: KrakenLayoutEditor, output_dir: Path) -> Path:
    index = _first_row_index_for_surface(app, BEAM_SPLITTER_SURFACE)
    if index is None:
        raise RuntimeError("Beam Splitter row not found")
    app._select_table_row(index)
    app.open_beam_splitter_settings(index)
    path = _capture_latest_toplevel(app, output_dir, "beam_splitter_settings_dialog.png")
    for child in app.winfo_children():
        if child.winfo_exists() and str(child.winfo_class()) == "Toplevel" and "Beam Splitter" in child.title():
            child.destroy()
    return path


def _capture_cad_face_dialog(app: KrakenLayoutEditor, output_dir: Path) -> Path | None:
    try:
        target_name = next((name for name in app.example_names if "Phase6" in name and "STL" in name), "")
        if target_name:
            app.load_example_by_name(target_name)
        else:
            return None
        index = next((i for i, row in enumerate(app.rows) if (row.advanced or {}).get("Solid_3d_stl")), None)
        if index is None:
            return None
        app._select_table_row(index)
        app.open_optical_solid_face_role_editor(index)
        path = _capture_latest_toplevel(app, output_dir, "cad_stl_face_assignment.png", geometry="2200x980+80+80")
        for child in app.winfo_children():
            if child.winfo_exists() and str(child.winfo_class()) == "Toplevel" and "CAD/STL Optical Faces" in child.title():
                child.destroy()
        return path
    except Exception as exc:
        print(f"Skipped CAD/STL face-assignment screenshot: {exc}")
        return None


def capture(output_dir: Path, *, include_cad: bool = True) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_app(app)

        _set_sidebars(app, left=False, right=False)
        _apply_rows(app, _basic_plate_rows(optimize_rc=True))
        spec = VARIABLE_REGISTRY.get("rc")
        if spec is not None:
            spec.set_enabled(app.rows[1], True)
            spec.set_bounds(app.rows[1], (20.0, 100.0))
        app._sync_table()
        app.refresh_plot(suppress_analysis=True)
        _settle(app)
        outputs.append(_save_window_crop(app, output_dir, "editable_table_variable_marker.png", (35, 38, 930, 160)))
        outputs.append(_capture_context_menu(app, output_dir))
        if app.insert_menu is not None:
            outputs.append(_capture_top_menu(app, output_dir, app.insert_menu, "insert_menu.png", width=330, height=210))

        _set_sidebars(app, left=True, right=False)
        try:
            app.load_layout_by_name("Gaussian Beam ABCD Example")
        except Exception:
            pass
        app.source_model_var.set("Gaussian beam")
        app.gaussian_input_mode_var.set("Diameter + divergence")
        app.gaussian_beam_diameter_var.set("1.0")
        app.gaussian_full_divergence_var.set("2.0")
        app.gaussian_m2_var.set("1.0")
        app._on_source_model_changed()
        _settle(app)
        outputs.append(_save_window_crop(app, output_dir, "gaussian_source_panel.png", (0, 38, 390, 900)))
        outputs.append(_save_window_crop(app, output_dir, "scene_trace_controls.png", (0, 560, 390, 900)))

        _set_sidebars(app, left=False, right=True)
        _apply_rows(app, _basic_plate_rows(optimize_rc=True))
        app._set_selected_operand_labels(["EFFL"])
        app.operand_target_vars["EFFL"].set("100")
        app.operand_weight_vars["EFFL"].set("1")
        app._update_operand_setup_visibility()
        _settle(app)
        outputs.append(_save_window_crop(app, output_dir, "optimization_panel_effl.png", (1335, 198, 1710, 560)))

        _set_sidebars(app, left=False, right=False)
        if _load_layout_if_available(app, "Beam Splitter 50/50 Example"):
            app.refresh_plot(suppress_analysis=True)
            _settle(app)
            outputs.append(_save_window_crop(app, output_dir, "path_view_selector.png", (1360, 0, 1715, 42)))
            outputs.append(_save_window_crop(app, output_dir, "analysis_toolbar.png", (35, 335, 1135, 392)))
            outputs.append(_capture_beam_splitter_dialog(app, output_dir))

        _set_sidebars(app, left=False, right=False)
        _apply_rows(app, _basic_plate_rows(optimize_rc=True))
        outputs.append(_capture_lens_drawing_dialog(app, output_dir))

        if include_cad:
            cad_path = _capture_cad_face_dialog(app, output_dir)
            if cad_path is not None:
                outputs.append(cad_path)
    finally:
        app.destroy()
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-cad", action="store_true", help="Skip the optional CAD/STL face-assignment dialog capture.")
    args = parser.parse_args()
    paths = capture(args.output_dir, include_cad=not args.skip_cad)
    for path in paths:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
