"""Capture UI screenshots for the PCX-from-plate Sphinx tutorial.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_pcx_tutorial_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from pathlib import Path

from PIL import ImageGrab

from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow, VARIABLE_REGISTRY


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "pcx_from_plate"


def _plate_rows(*, front_rc: float = 0.0, image_distance: float = 100.0, optimize_rc: bool = False) -> list[SurfaceRow]:
    front = SurfaceRow(
        surface="Standard",
        name="Front surface",
        rc=float(front_rc),
        thickness=5.0,
        diameter=25.0,
        glass="BK7",
        optimize_rc=bool(optimize_rc),
        optimize_rc_bounds=(20.0, 100.0) if optimize_rc else None,
    )
    rear = SurfaceRow(
        surface="Standard",
        name="Rear flat surface",
        rc=0.0,
        thickness=float(image_distance),
        diameter=25.0,
        glass="AIR",
    )
    return [
        SurfaceRow(surface="Object", name="Object", thickness=25.0, diameter=25.0, drawing=0.0, glass="AIR"),
        front,
        rear,
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, drawing=0.0, glass="AIR"),
    ]


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1720x920+40+40")
    app.auto_save_plot_var.set(False)
    app.object_mode_var.set("Infinity")
    app.display_orientation_var.set("Horizontal")
    app.wavelength_var.set("0.5876")
    app.ray_count_var.set("5")
    app.ray_height_factor_var.set("0.8")
    app.field_value_var.set("0")
    app.field_count_var.set("1")
    app.emit_full_ray_var.set(False)
    app.show_cardinals_var.set(True)
    app.analysis_mode = "none"
    app.selected_analysis_modes.clear()
    try:
        app.table.column("rc", width=140)
        app.table.column("thickness", width=140)
    except Exception:
        pass
    app._set_selected_operand_labels(["EFFL"])
    app.operand_target_vars["EFFL"].set("100")
    app.operand_weight_vars["EFFL"].set("1")


def _apply_rows(app: KrakenLayoutEditor, rows: list[SurfaceRow]) -> None:
    app.rows = app._normalized_rows_copy(rows)
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)


def _show_state(app: KrakenLayoutEditor, *, refresh_plot: bool = True) -> None:
    if refresh_plot:
        app.refresh_plot(suppress_analysis=True)
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


def _capture_app(app: KrakenLayoutEditor, path: Path) -> None:
    app.update_idletasks()
    importer = shutil.which("import")
    if importer:
        try:
            subprocess.run(
                [importer, "-window", str(app.winfo_id()), str(path)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            if path.exists() and path.stat().st_size > 2048:
                return
        except Exception:
            pass
    x0 = int(app.winfo_rootx())
    y0 = int(app.winfo_rooty())
    screen_width = int(app.winfo_screenwidth())
    screen_height = int(app.winfo_screenheight())
    x1 = min(x0 + int(app.winfo_width()), screen_width)
    y1 = min(y0 + int(app.winfo_height()), screen_height)
    x0 = max(0, x0)
    y0 = max(0, y0)
    image = ImageGrab.grab(bbox=(x0, y0, x1, y1))
    image.save(path, optimize=True)


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)

        _set_sidebars(app, left=False, right=False)
        _apply_rows(app, _plate_rows())
        app.status_var.set("Tutorial state 1: starting 5 mm BK7 plate.")
        _show_state(app)
        path = output_dir / "01_starting_bk7_plate_ui.png"
        _capture_app(app, path)
        outputs.append(path)

        _set_sidebars(app, left=False, right=False)
        _apply_rows(app, _plate_rows(optimize_rc=True))
        app.status_var.set("Tutorial state 2: front Rc marked as variable with bounds 20..100 mm.")
        _show_state(app)
        path = output_dir / "02_front_radius_variable_ui.png"
        _capture_app(app, path)
        outputs.append(path)

        _set_sidebars(app, left=False, right=True)
        _set_effl_operand_visible(app)
        app.status_var.set("Tutorial state 3: EFFL operand target set to 100 mm.")
        _show_state(app, refresh_plot=False)
        path = output_dir / "03_effl_operand_setup_ui.png"
        _capture_app(app, path)
        outputs.append(path)

        # Approximate BK7 PCX result for EFFL ~= 100 mm at the d line. The
        # image-space thickness is the paraxial back focal distance estimate.
        _set_sidebars(app, left=False, right=False)
        final_rows = _plate_rows(front_rc=51.7, image_distance=96.7, optimize_rc=True)
        _apply_rows(app, final_rows)
        app.status_var.set("Tutorial state 4: PCX result, then image distance solved near focus.")
        _show_state(app)
        path = output_dir / "04_final_pcx_layout_ui.png"
        _capture_app(app, path)
        outputs.append(path)
    finally:
        app.destroy()
    return outputs


def _set_effl_operand_visible(app: KrakenLayoutEditor) -> None:
    app._set_selected_operand_labels(["EFFL"])
    app.operand_target_vars["EFFL"].set("100")
    app.operand_weight_vars["EFFL"].set("1")
    # Keep only the EFFL card visible in the Optimization panel.
    app._update_operand_setup_visibility()
    # Make the variable marker obvious in the table too.
    spec = VARIABLE_REGISTRY.get("rc")
    if spec is not None:
        row = app.rows[1]
        spec.set_enabled(row, True)
        spec.set_bounds(row, (20.0, 100.0))
    app._sync_table()


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
