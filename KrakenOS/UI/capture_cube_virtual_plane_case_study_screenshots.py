"""Capture UI screenshots for the cube virtual-plane case study.

This script needs a real display because it captures the actual Tk editor
window. Run it from the project root with:

    python -m KrakenOS.UI.capture_cube_virtual_plane_case_study_screenshots
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

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
    KrakenLayoutEditor,
    SurfaceRow,
    build_optical_solid_cube_splitter_virtual_plane,
    cluster_optical_solid_planar_faces,
    normalize_optical_solid_face_metadata,
    optical_solid_face_record_from_candidate,
    optical_solid_trace_sequence_records,
    optical_solid_virtual_plane_world_records,
)
from KrakenOS.UI.stl_geometry import format_stl_mesh_diagnostics, inspect_stl_mesh


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "docs" / "source" / "_static" / "tutorials" / "cube_virtual_plane"
CUBE_SIZE_MM = 25.0
CUBE_STL_PATH = Path("/tmp/kraken_68551_cube_proxy.stl")
EDMUND_68551_STEP = PROJECT_ROOT / "attachment" / "68551" / "step_68551.step"
MICHELSON_LAYOUT = "Michelson Interferometer (Interferogram)"


def _write_cube_stl(path: Path, size_mm: float = CUBE_SIZE_MM) -> Path:
    half = float(size_mm) * 0.5

    def face(center: tuple[float, float, float], u: tuple[float, float, float], v: tuple[float, float, float]):
        c = np.asarray(center, dtype=float)
        u_arr = np.asarray(u, dtype=float) * half
        v_arr = np.asarray(v, dtype=float) * half
        p00 = c - u_arr - v_arr
        p10 = c + u_arr - v_arr
        p11 = c + u_arr + v_arr
        p01 = c - u_arr + v_arr
        normal = np.cross(u_arr, v_arr)
        normal = normal / max(float(np.linalg.norm(normal)), 1e-12)
        return [(normal, p00, p10, p11), (normal, p00, p11, p01)]

    triangles = []
    triangles.extend(face((0.0, 0.0, -half), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0)))
    triangles.extend(face((0.0, 0.0, half), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)))
    triangles.extend(face((0.0, half, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0, 0.0)))
    triangles.extend(face((0.0, -half, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
    triangles.extend(face((-half, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0, 0.0)))
    triangles.extend(face((half, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))

    lines = ["solid kraken_68551_cube_proxy"]
    for normal, p0, p1, p2 in triangles:
        lines.append("  facet normal {:.9g} {:.9g} {:.9g}".format(*normal))
        lines.append("    outer loop")
        for point in (p0, p1, p2):
            lines.append("      vertex {:.9g} {:.9g} {:.9g}".format(*point))
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid kraken_68551_cube_proxy")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")
    return path


def _cube_metadata(stl_path: Path) -> dict[str, object]:
    candidates = cluster_optical_solid_planar_faces(stl_path)
    records = [optical_solid_face_record_from_candidate(candidate) for candidate in candidates]
    for record in records:
        centroid = np.asarray(record.get("centroid", (0.0, 0.0, 0.0)), dtype=float)
        side = "Auto"
        if abs(float(centroid[2]) + CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Left"
        elif abs(float(centroid[2]) - CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Right"
        elif abs(float(centroid[1]) - CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Up"
        elif abs(float(centroid[1]) + CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Down"
        elif abs(float(centroid[0]) + CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Front"
        elif abs(float(centroid[0]) - CUBE_SIZE_MM * 0.5) < 1e-6:
            side = "Back"
        record["side_2d"] = side
        if side in {"Left", "Right", "Up", "Down"}:
            record["role"] = "Input" if side == "Left" else "Output"
            record["function"] = "Transmit/Port"
        elif side in {"Front", "Back"}:
            record["role"] = "Absorber/Mechanical"
            record["function"] = "Absorber/Mechanical"
    base = normalize_optical_solid_face_metadata(
        {"source_stl": str(stl_path), "faces": records},
        candidates,
        source_stl=str(stl_path),
    )
    plane = build_optical_solid_cube_splitter_virtual_plane(
        base,
        diagonal_mode=OPTICAL_SOLID_VIRTUAL_PLANE_DIAGONAL_REFLECT_POS_Y,
        split_ratio=0.5,
        loss=0.02,
        phase_deg=180.0,
        notes="Authoring metadata for Edmund 68551-style cube CAD; branch tracing still uses a Beam Splitter row.",
    )
    return normalize_optical_solid_face_metadata(
        {"source_stl": str(stl_path), "faces": base.get("faces", []), "virtual_planes": [plane]},
        candidates,
        source_stl=str(stl_path),
    )


def _cube_rows(stl_path: Path, metadata: dict[str, object]) -> list[SurfaceRow]:
    return [
        SurfaceRow(surface="Object", name="Source reference", thickness=35.0, diameter=18.0, glass="AIR"),
        SurfaceRow(
            surface="Solid 3D STL",
            name="Edmund 68551 CAD proxy cube",
            thickness=45.0,
            diameter=CUBE_SIZE_MM,
            glass="BK7",
            axis_move=2.0,
            advanced={
                "Solid_3d_stl": str(stl_path),
                "OpticalSolidSourcePath": str(EDMUND_68551_STEP.relative_to(PROJECT_ROOT)),
                "OpticalSolidSourceFormat": "STEP",
                OPTICAL_SOLID_FACES_ADVANCED_ATTR: metadata,
                "Note": (
                    "Generated 25 mm cube proxy for documentation capture. The saved source path "
                    "points to the Edmund 68551 STEP attachment; the virtual plane is authoring metadata."
                ),
            },
        ),
        SurfaceRow(surface="Image", name="Detector plane", thickness=0.0, diameter=35.0, glass="AIR"),
    ]


def _configure_cube_scene(app: KrakenLayoutEditor, stl_path: Path, metadata: dict[str, object]) -> None:
    app._reset_complete_layout_runtime_state(close_viewers=True)
    app.rows = _cube_rows(stl_path, metadata)
    app.current_layout_file = None
    app._normalize_special_rows()
    app._sync_table()
    app._select_table_row(1)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.ray_count_var.set("5")
    app.source_radius_var.set("2.5")
    app.wavelength_var.set("0.55")
    app.auto_save_plot_var.set(False)
    try:
        for field, width in (
            ("label", 82),
            ("surface", 140),
            ("name", 255),
            ("glass", 115),
            ("thickness", 125),
            ("diameter", 115),
            ("axis_move", 105),
            ("advanced", 340),
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
    tmp_path = Path("/tmp/kraken_cube_virtual_plane_case_capture_tmp.png")
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


def _virtual_plane_report(row: SurfaceRow, metadata: dict[str, object], stl_path: Path) -> str:
    planes = list(metadata.get("virtual_planes", []) or [])
    plane = dict(planes[0]) if planes else {}
    world_planes = optical_solid_virtual_plane_world_records(row, 35.0, assigned_only=True)
    world = dict(world_planes[0]) if world_planes else {}
    sequence = optical_solid_trace_sequence_records(
        row,
        35.0,
        [
            (0.0, 0.0, 35.0 - CUBE_SIZE_MM * 0.5),
            (0.0, 0.0, 35.0 + CUBE_SIZE_MM * 0.5),
        ],
        [(0.0, 0.0, -1.0), (0.0, 0.0, 1.0)],
    )
    kinds = [str(event.get("kind", "")) for event in sequence]
    labels = [str(event.get("side_2d", event.get("plane_kind", ""))) for event in sequence]
    lines = [
        "# Cube CAD Virtual Internal Plane Report",
        "",
        f"Generated STL proxy: {stl_path}",
        f"Vendor source path: {EDMUND_68551_STEP.relative_to(PROJECT_ROOT)}",
        f"Cube size: {CUBE_SIZE_MM:.6g} mm",
        "",
        "Saved virtual plane:",
        f"- ID: {plane.get('plane_id', '-')}",
        f"- Kind: {plane.get('kind', '-')}",
        f"- Diagonal: {plane.get('diagonal_mode', '-')}",
        f"- Local point: {plane.get('point', '-')}",
        f"- Local normal: {plane.get('normal', '-')}",
        f"- Split ratio: {float(plane.get('split_ratio', np.nan)):.6g}",
        f"- Loss: {float(plane.get('loss', np.nan)):.6g}",
        f"- Phase: {float(plane.get('phase_deg', np.nan)):.6g} deg",
        f"- Clear aperture: {float(plane.get('aperture_mm', np.nan)):.6g} mm",
        "",
        "World preview:",
        f"- Point: {world.get('point_world', '-')}",
        f"- Normal: {world.get('normal_world', '-')}",
        "",
        "Synthetic hit sequence:",
        f"- Kinds: {' -> '.join(kinds)}",
        f"- Labels: {' -> '.join(labels)}",
        "",
        "Important limitation:",
        "- The virtual plane is saved authoring/preview metadata for imported CAD/STL solids.",
        "- Current traced reflected/transmitted branch physics still belongs in a Beam Splitter row or cube primitive.",
        "- Vendor mechanical CAD usually does not encode split ratio, coating phase, loss, or polarization behavior.",
    ]
    return "\n".join(lines).strip() + "\n"


def _capture_michelson_primitive(app: KrakenLayoutEditor, output_dir: Path) -> Path:
    app.load_layout_by_name(MICHELSON_LAYOUT, refresh=False)
    app.display_orientation_var.set("Vertical")
    app.trace_mode_var.set("Non-Sequential Preview")
    app.ray_count_var.set("1")
    app.source_radius_var.set("0.5")
    app.nonseq_energy_probability_var.set(False)
    if hasattr(app, "show_path_labels_var"):
        app.show_path_labels_var.set(True)
        app.show_path_labels = True
    _set_sidebars(app, left=False, right=False)
    _show_state(app, analysis_mode="none")
    return _save_canvas(app, output_dir, "05_cube_primitive_michelson_split_plot.png")


def capture(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stl_path = _write_cube_stl(CUBE_STL_PATH)
    metadata = _cube_metadata(stl_path)
    app = KrakenLayoutEditor(headless=True)
    outputs: list[Path] = []
    try:
        app.geometry("1760x960+40+40")
        _configure_cube_scene(app, stl_path, metadata)
        _set_sidebars(app, left=True, right=True)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_window(app, output_dir, "01_loaded_cube_cad_proxy_ui.png"))

        _set_sidebars(app, left=False, right=False)
        _show_state(app, analysis_mode="none")
        outputs.append(_save_canvas(app, output_dir, "02_passive_cad_cube_no_split_plot.png"))

        outputs.append(_save_face_dialog(app, output_dir, "03_cube_virtual_plane_dialog.png"))
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "04_cube_virtual_plane_report.png",
                "Cube CAD Virtual Internal Plane Report",
                _virtual_plane_report(app.rows[1], metadata, stl_path),
            )
        )

        outputs.append(_capture_michelson_primitive(app, output_dir))
        outputs.append(
            _save_report_window(
                app,
                output_dir,
                "06_cube_proxy_mesh_diagnostics_report.png",
                "Cube Proxy STL Mesh Diagnostics",
                format_stl_mesh_diagnostics(inspect_stl_mesh(stl_path)),
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
