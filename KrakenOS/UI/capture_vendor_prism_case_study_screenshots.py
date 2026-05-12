"""Capture UI screenshots for the vendor prism CAD placement case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_vendor_prism_case_study_screenshots
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
import tkinter as tk

import numpy as np
from PIL import Image, ImageGrab

import KrakenOS.UI.layout_editor as le
from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    KrakenLayoutEditor,
    SurfaceRow,
    auto_assign_optical_solid_face_roles,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_face_world_records,
    solve_optical_solid_left_input_pose,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "vendor_prism_cad_placement"
PRISM_42779_STEP = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "step_42779.step"
PRISM_42779_IGES = PROJECT_ROOT / "attachment" / "prisms" / "42779" / "iges_42779.igs"


def _mesh_vendor_prism(cache_dir: Path) -> tuple[Path, Path, str, le.StlMeshDiagnostics]:
    original_cache = le.CAD_CACHE_DIR
    le.CAD_CACHE_DIR = cache_dir
    try:
        mesh_path, source_path, source_format = le._optical_solid_mesh_path_from_source(PRISM_42779_STEP)
        diagnostics = le.inspect_stl_mesh(mesh_path)
    finally:
        le.CAD_CACHE_DIR = original_cache
    return mesh_path, source_path, source_format, diagnostics


def _metadata_for_mesh(mesh_path: Path) -> dict[str, object]:
    candidates = cluster_optical_solid_planar_faces(mesh_path)
    records = auto_assign_optical_solid_face_roles(
        [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    )
    for record in records:
        face_id = str(record.get("face_id", "") or "").strip()
        record["side_2d"] = "Auto"
        record["role"] = "Unassigned"
        record["function"] = "Unassigned"
        record["notes"] = ""
        if face_id == "F005":
            record["side_2d"] = "Left"
            record["role"] = "Input"
            record["function"] = "Transmit/Port"
            record["notes"] = "Demo input/anchor face; confirm against vendor drawing before production."
        elif face_id == "F006":
            record["side_2d"] = "Down"
            record["role"] = "Output"
            record["function"] = "Transmit/Port"
            record["notes"] = "Demo output face."
        elif face_id == "F003":
            record["side_2d"] = "Right"
            record["role"] = "Mirror"
            record["function"] = "Mirror"
            record["notes"] = "Vendor aluminized fold face."
        elif face_id == "F004":
            record["side_2d"] = "Up"
            record["role"] = "Mirror"
            record["function"] = "Mirror"
            record["notes"] = "Vendor aluminized fold face."
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(mesh_path), "faces": records},
        candidates,
        source_stl=str(mesh_path),
    )


def _anchor_face_id(metadata: dict[str, object]) -> str:
    for face in list(metadata.get("faces", []) or []):
        if isinstance(face, dict) and str(face.get("side_2d", "")) == "Left":
            return str(face.get("face_id", "") or "")
    return ""


def _base_rows(mesh_path: Path, metadata: dict[str, object]) -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Source reference", thickness=45.0, diameter=30.0, glass="AIR"),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Edmund 42779 vendor prism",
            thickness=70.0,
            diameter=45.0,
            glass="BK7",
            axis_move=2.0,
            advanced={
                "Solid_3d_stl": str(mesh_path),
                "OpticalSolidSourcePath": str(PRISM_42779_STEP.relative_to(PROJECT_ROOT)),
                "OpticalSolidSourceFormat": "STEP",
                "OpticalSolidAlternatePath": str(PRISM_42779_IGES.relative_to(PROJECT_ROOT)),
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata,
                "Note": (
                    "Edmund 42779 vendor prism CAD imported through STEP and meshed to cached STL. "
                    "Face labels are demo authoring metadata; verify the intended ports against the drawing."
                ),
            },
        ),
        SurfaceRow(surface="Image", name="Detector plane", thickness=0.0, diameter=50.0, glass="AIR"),
    ]


def _configure_app(app: KrakenLayoutEditor, mesh_path: Path, metadata: dict[str, object]) -> None:
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.rows = _base_rows(mesh_path, metadata)
    app.current_layout_file = None
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.ray_count_var.set("7")
    app.source_radius_var.set("2.0")
    app.wavelength_var.set("0.55")
    app.auto_save_plot_var.set(False)
    try:
        for field, width in (
            ("label", 82),
            ("surface", 140),
            ("name", 250),
            ("glass", 115),
            ("thickness", 125),
            ("diameter", 115),
            ("tilt_x", 95),
            ("tilt_y", 95),
            ("tilt_z", 95),
            ("desp_x", 95),
            ("desp_y", 95),
            ("desp_z", 95),
            ("advanced", 360),
        ):
            app.table.column(field, width=width)
    except Exception:
        pass


def _apply_face_fit(app: KrakenLayoutEditor, metadata: dict[str, object]) -> dict[str, object]:
    solution = solve_optical_solid_left_input_pose(metadata)
    if solution is None:
        raise RuntimeError("Face-fit solver did not return a placement solution.")
    row = app.rows[1]
    row.tilt_x = float(solution["tilts"][0])
    row.tilt_y = float(solution["tilts"][1])
    row.tilt_z = float(solution["tilts"][2])
    row.desp_x = float(solution["desp"][0])
    row.desp_y = float(solution["desp"][1])
    row.desp_z = float(solution["desp"][2])
    app._sync_table()
    app._select_table_row(1)
    app.update_idletasks()
    app.update()
    return solution


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
    tmp_path = Path("/tmp/kraken_vendor_prism_case_capture_tmp.png")
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


def _save_face_dialog(app: KrakenLayoutEditor, output_dir: Path, filename: str) -> Path:
    app._select_table_row(1)
    app.open_optical_solid_face_role_editor(1)
    windows = [
        child
        for child in app.winfo_children()
        if getattr(child, "winfo_exists", lambda: False)() and str(child.winfo_class()) == "Toplevel"
    ]
    dialog = next((window for window in reversed(windows) if "CAD/STL Optical Faces" in str(window.title())), None)
    if dialog is None:
        raise RuntimeError("CAD/STL Optical Faces dialog did not open")
    dialog.update_idletasks()
    dialog.update()
    time.sleep(0.8)
    dialog.update()
    path = output_dir / filename
    _capture_window_image(dialog).save(path, optimize=True)
    dialog.destroy()
    app.update_idletasks()
    app.update()
    return path


def _face_fit_report(app: KrakenLayoutEditor, metadata: dict[str, object], solution: dict[str, object]) -> str:
    faces = optical_solid_face_world_records(app.rows[1], 45.0, assigned_only=False)
    face_id = str(solution.get("face_id", "") or "")
    anchor = next((face for face in faces if str(face.get("face_id", "")) == face_id), {})
    normal = np.asarray(anchor.get("normal_world", (np.nan, np.nan, np.nan)), dtype=float)
    centroid = np.asarray(anchor.get("centroid_world", (np.nan, np.nan, np.nan)), dtype=float)
    records = list(metadata.get("faces", []) or [])
    lines = [
        "# Vendor Prism CAD Face-Fit Report",
        "",
        f"STEP source: {PRISM_42779_STEP.relative_to(PROJECT_ROOT)}",
        f"IGES alternative: {PRISM_42779_IGES.relative_to(PROJECT_ROOT)}",
        f"Planar face records: {len(records)}",
        "",
        "Assigned demo roles:",
    ]
    for record in records:
        lines.append(
            "- {face}: side={side}, function={function}, area={area:.6g} mm^2".format(
                face=record.get("face_id", ""),
                side=record.get("side_2d", ""),
                function=record.get("function", ""),
                area=float(record.get("area_mm2", 0.0) or 0.0),
            )
        )
    lines.extend(
        [
            "",
            "Face-fit placement:",
            f"- Anchor face: {face_id} ({solution.get('label', '')})",
            f"- Roll side: {solution.get('roll_side', '-')}",
            f"- TiltX/Y/Z: {tuple(round(float(value), 6) for value in solution.get('tilts', (0, 0, 0)))} deg",
            f"- DespX/Y/Z: {tuple(round(float(value), 6) for value in solution.get('desp', (0, 0, 0)))} mm",
            f"- Anchor centroid world: {np.round(centroid, 6).tolist()}",
            f"- Anchor normal world: {np.round(normal, 6).tolist()}",
            "",
            "Interpretation:",
            "- The selected Left/input face normal is aligned to layout -Z; the layout ray travels +Z into the prism.",
            "- This solves one anchor pose; final production placement still needs the intended input/output ports verified against the vendor drawing.",
            "- The row stores the solved KrakenOS Tilt/Desp values so the model remains editable in the table.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="kraken-prism42779-capture-") as tmp_dir:
        cache_dir = Path(tmp_dir)
        mesh_path, _source_path, _source_format, diagnostics = _mesh_vendor_prism(cache_dir)
        metadata = _metadata_for_mesh(mesh_path)
        app = KrakenLayoutEditor(headless=True)
        try:
            app.geometry("1760x960+40+40")
            _configure_app(app, mesh_path, metadata)
            _set_sidebars(app, left=True, right=True)
            _show_state(app, analysis_mode="none")
            outputs.append(_save_window(app, output_dir, "01_loaded_vendor_prism_cad_ui.png"))

            outputs.append(
                _save_report_window(
                    app,
                    output_dir,
                    "02_vendor_prism_mesh_diagnostics_report.png",
                    "Vendor Prism CAD Mesh Diagnostics",
                    le.format_stl_mesh_diagnostics(diagnostics),
                )
            )

            outputs.append(_save_face_dialog(app, output_dir, "03_vendor_prism_face_assignment_dialog.png"))

            solution = _apply_face_fit(app, metadata)
            outputs.append(
                _save_report_window(
                    app,
                    output_dir,
                    "04_vendor_prism_face_fit_report.png",
                    "Vendor Prism CAD Face-Fit Report",
                    _face_fit_report(app, metadata, solution),
                )
            )

            _set_sidebars(app, left=False, right=False)
            _show_state(app, analysis_mode="none")
            outputs.append(_save_canvas(app, output_dir, "05_vendor_prism_fitted_layout_plot.png"))
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
