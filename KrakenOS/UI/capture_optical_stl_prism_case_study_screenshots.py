"""Capture UI screenshots for the optical STL prism case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_optical_stl_prism_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import textwrap
import time
from pathlib import Path
import tkinter as tk

import numpy as np
from PIL import Image, ImageGrab

from KrakenOS.Examples.Examp_Phase6_Optical_STL_Prism import (
    PRISM_STL,
    Prism_Solid,
    build_system,
    trace_collimated_grid,
)
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    KrakenLayoutEditor,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_trace_sequence_records,
)
from KrakenOS.UI.scene_builder import _build_ray_hit_records
from KrakenOS.UI.stl_geometry import format_stl_mesh_diagnostics, inspect_stl_mesh


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "optical_stl_prism_faces"
EXAMPLE_NAME = "Examp_Phase6_Optical_STL_Prism"


def _configure_common(app: KrakenLayoutEditor) -> None:
    try:
        app.attributes("-type", "utility")
    except Exception:
        pass
    app.geometry("1760x960+40+40")
    app.auto_save_plot_var.set(False)
    app.load_example_by_name(EXAMPLE_NAME)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.ray_count_var.set("7")
    app.source_radius_var.set("0.8")
    app.wavelength_var.set("0.55")
    if hasattr(app, "show_path_labels_var"):
        app.show_path_labels_var.set(True)
        app.show_path_labels = True
    try:
        for field, width in (
            ("label", 80),
            ("surface", 135),
            ("name", 230),
            ("glass", 115),
            ("thickness", 120),
            ("diameter", 115),
            ("tilt_x", 95),
            ("desp_y", 95),
            ("axis_move", 105),
            ("advanced", 300),
        ):
            app.table.column(field, width=width)
    except Exception:
        pass


def _stl_row_index(app: KrakenLayoutEditor) -> int:
    for index, row in enumerate(app.rows):
        if (row.advanced or {}).get("Solid_3d_stl"):
            return index
    raise RuntimeError("No file-backed Solid_3d_stl row found in the loaded example.")


def _prism_face_metadata() -> dict[str, object]:
    candidates = cluster_optical_solid_planar_faces(PRISM_STL)
    records = auto_assign_optical_solid_face_roles(
        [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    )
    for record in records:
        side = str(record.get("side_2d", "") or "")
        if side == "Left":
            record["role"] = "Input"
            record["function"] = "Transmit/Port"
            record["port_role"] = "Input Port"
        elif side == "Right":
            record["role"] = "Output"
            record["function"] = "Transmit/Port"
            record["port_role"] = "Output Port"
        elif side == "Down":
            record["function"] = "Transmit/Port"
            record["port_role"] = "Interaction Surface"
        elif side in {"Front", "Back"}:
            record["role"] = "Absorber/Mechanical"
            record["function"] = "Absorber/Mechanical"
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(PRISM_STL), "faces": records},
        candidates,
        source_stl=str(PRISM_STL),
    )


def _assign_prism_face_metadata(app: KrakenLayoutEditor, row_index: int) -> None:
    row = app.rows[row_index]
    advanced = dict(row.advanced or {})
    advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = _prism_face_metadata()
    row.advanced = advanced
    app._sync_table()
    app._select_table_row(row_index)
    app.update_idletasks()
    app.update()


def _sequence_report() -> str:
    system = build_system()
    rays = trace_collimated_grid(system, grid_count=1, radius_mm=0.0, wavelength_um=0.55)
    prism_hits = [hit for hit in _build_ray_hit_records(system.SDT, rays, 0) if hit.surface_id == 1]
    row = SurfaceRow(
        surface="Solid 3D STL",
        name=Prism_Solid.Name,
        glass=Prism_Solid.Glass,
        diameter=Prism_Solid.Diameter,
        thickness=Prism_Solid.Thickness,
        desp_y=Prism_Solid.DespY,
        axis_move=Prism_Solid.AxisMove,
        advanced={
            OPTICAL_SOLID_FACES_ADVANCED_ATTR: _prism_face_metadata(),
            "Solid_3d_stl": str(PRISM_STL),
        },
    )
    sequence = optical_solid_trace_sequence_records(
        row,
        30.0,
        [hit.point_world for hit in prism_hits],
        [hit.surface_normal for hit in prism_hits],
    )
    face_events = [event for event in sequence if str(event.get("kind", "")) == "face_hit"]
    sides = [str(event.get("side_2d", "")) for event in face_events]
    surfaces = np.asarray(system.SURFACE, dtype=int)
    stl_indices = np.flatnonzero(surfaces == 1)
    if stl_indices.size == 0:
        raise RuntimeError("Chief ray did not hit the STL prism row.")
    first = int(stl_indices[0])
    entry_n0 = float(system.N0[first])
    entry_n1 = float(system.N1[first])
    outgoing = np.asarray(system.R_LMN[first], dtype=float)
    lines = [
        "# Optical STL Prism Trace Report",
        "",
        f"STL: {PRISM_STL}",
        f"Material: {Prism_Solid.Glass}",
        f"Chief-ray STL hits: {len(prism_hits)}",
        f"Classified face sequence: {' -> '.join(sides) if sides else 'none'}",
        "",
        "First STL boundary:",
        f"- Media: n0={entry_n0:.6g} -> n1={entry_n1:.6g}",
        f"- Outgoing direction cosine: {np.round(outgoing, 6).tolist()}",
        "",
        "Per-hit face classification:",
    ]
    for index, event in enumerate(face_events, start=1):
        point = np.asarray(event.get("point_world", (np.nan, np.nan, np.nan)), dtype=float)
        normal = np.asarray(event.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float)
        lines.append(
            "- hit {idx}: side={side}, function={function}, point={point}, normal={normal}, plane_error={plane:.3g} mm".format(
                idx=index,
                side=event.get("side_2d", ""),
                function=event.get("function", ""),
                point=np.round(point, 4).tolist(),
                normal=np.round(normal, 4).tolist(),
                plane=float(event.get("plane_distance_mm", np.nan)),
            )
        )
    lines.extend(
        [
            "",
            "Interpretation:",
            "- The core trace enters BK7 at the STL boundary instead of reporting n=1 -> 1.",
            "- Face-role metadata maps traced mesh hits back to user-visible side/function labels.",
            "- The editable table remains the source of truth for material, pose, and detector distance.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


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
    tmp_path = Path("/tmp/kraken_optical_stl_prism_case_capture_tmp.png")
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


def _save_face_dialog(app: KrakenLayoutEditor, output_dir: Path, filename: str, row_index: int) -> Path:
    app._select_table_row(row_index)
    app.open_optical_solid_face_role_editor(row_index)
    windows = [
        child
        for child in app.winfo_children()
        if getattr(child, "winfo_exists", lambda: False)() and str(child.winfo_class()) == "Toplevel"
    ]
    dialog = next((window for window in reversed(windows) if "CAD/STL Optical Faces" in str(window.title())), None)
    if dialog is None:
        raise RuntimeError("CAD/STL Optical Faces dialog did not open")
    dialog.geometry("2200x980+80+80")
    dialog.deiconify()
    dialog.lift()
    try:
        dialog.attributes("-topmost", True)
        dialog.after(250, lambda: dialog.attributes("-topmost", False))
    except Exception:
        pass
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.8)
    dialog.update()
    path = output_dir / filename
    _capture_widget_bounds_image(dialog).save(path, optimize=True)
    dialog.destroy()
    app.update_idletasks()
    app.update()
    return path


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        _configure_common(app)
        row_index = _stl_row_index(app)
        _assign_prism_face_metadata(app, row_index)

        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_optical_stl_prism_ui.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_canvas(app, output_dir, "02_optical_stl_prism_layout_plot.png"))

        outputs.append(_save_face_dialog(app, output_dir, "03_cad_stl_face_assignment_dialog.png", row_index))
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "04_stl_mesh_diagnostics_report.png",
                "STL Mesh Diagnostics",
                format_stl_mesh_diagnostics(inspect_stl_mesh(PRISM_STL)),
            )
        )
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "05_trace_sequence_report.png",
                "Optical STL Prism Trace Report",
                _sequence_report(),
            )
        )
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
