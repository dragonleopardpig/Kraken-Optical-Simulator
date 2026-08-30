"""Inspection Cell -- six camera stations around one 3D part, in one view (bugs/0663,
phase 2 of the multi-station design; docs/inspection_cell_multi_station.md).

A KrakenOS layout is ONE imaging chain, and that engine is left untouched. A cell is
a PART (the bugs/0661 box, centred at the cell origin) plus up to six STATION LAYOUTS
-- one per face -- each an ordinary layout designed on its own with the part enabled
on that face. The cell composes them: every station is loaded HEADLESS (an editor
with no embedded inspector -- the one thing that can exist N times), traced
sequentially and independently, and its bodies/rays are placed into one scene under
the rigid transform that carries the station's object plane onto its face (object
point -> face centre, object axis -> outward face normal, field width -> face width).
This is the two-arm precedent (per-arm sequential traces composed by display
transforms) generalised to N arms.

Deliverables: the composite VIEW (a pyvista window / off-screen screenshot), the
composite STEP (every station's native export transformed into one compound, plus
the part), and an interference report (station body boxes that overlap).
"""

from __future__ import annotations

import json
import math
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from KrakenOS.UI.services.inspection_part import (
    FACE_ORDER,
    axis_records,
    box_corners,
    face_frames,
    normalize_inspection_part_spec,
    plane_basis,
)

CELL_SUFFIX = ".cell.json"


# ---------------------------------------------------------------------------------
# Cell spec
# ---------------------------------------------------------------------------------
def normalize_cell_spec(spec: Any) -> dict[str, Any]:
    """Canonical cell dict: {"part": <part spec>, "stations": {face: {"layout": str, "enabled": bool}}}."""
    spec = spec if isinstance(spec, dict) else {}
    part = normalize_inspection_part_spec(spec.get("part"))
    part["enabled"] = True
    stations_in = spec.get("stations") if isinstance(spec.get("stations"), dict) else {}
    stations: dict[str, dict[str, Any]] = {}
    for face in FACE_ORDER:
        entry = stations_in.get(face) if isinstance(stations_in.get(face), dict) else {}
        layout = str(entry.get("layout", "") or "").strip()
        stations[face] = {"layout": layout, "enabled": bool(entry.get("enabled", bool(layout)))}
    return {"part": part, "stations": stations}


def save_cell(path: str | Path, spec: dict[str, Any]) -> Path:
    target = Path(path).expanduser()
    if not target.name.endswith(CELL_SUFFIX):
        target = target.with_name(target.stem + CELL_SUFFIX)
    target.write_text(json.dumps(normalize_cell_spec(spec), indent=2), encoding="utf-8")
    return target


def load_cell(path: str | Path) -> dict[str, Any]:
    return normalize_cell_spec(json.loads(Path(path).expanduser().read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------------
def cell_part_frames(part_spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Face frames of the part box CENTRED at the cell origin (front face on +z)."""
    spec = normalize_inspection_part_spec(part_spec)
    spec["active_face"] = "front"
    origin_front = np.array([0.0, 0.0, 0.5 * spec["depth_mm"]])
    return face_frames(spec, origin_front, np.array([0.0, 0.0, 1.0]))


def cell_part_corners(part_spec: dict[str, Any]) -> np.ndarray:
    spec = normalize_inspection_part_spec(part_spec)
    spec["active_face"] = "front"
    return box_corners(spec, np.array([0.0, 0.0, 0.5 * spec["depth_mm"]]), np.array([0.0, 0.0, 1.0]))


def cell_axis_records(part_spec: dict[str, Any]) -> list[dict[str, Any]]:
    spec = normalize_inspection_part_spec(part_spec)
    spec["active_face"] = "front"
    return axis_records(spec, np.array([0.0, 0.0, 0.5 * spec["depth_mm"]]), np.array([0.0, 0.0, 1.0]))


def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else np.array([0.0, 0.0, 1.0])


def station_frame_transform(obj_point, obj_axis, face_center, face_normal, face_u) -> np.ndarray:
    """4x4 rigid transform carrying a station's object plane onto a face of the part:
    object point -> face centre, object axis (object -> lens) -> outward face normal,
    field width direction -> face width direction."""
    O = np.asarray(obj_point, dtype=float).reshape(3)
    a_s = _unit(obj_axis)
    u_s, v_s = plane_basis(a_s)
    n_f = _unit(face_normal)
    u_f = _unit(face_u)
    u_f = _unit(u_f - n_f * float(np.dot(u_f, n_f)))
    v_f = np.cross(n_f, u_f)
    R = np.column_stack([u_f, v_f, n_f]) @ np.column_stack([u_s, v_s, a_s]).T
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = np.asarray(face_center, dtype=float).reshape(3) - R @ O
    return T


def apply_transform(T: np.ndarray, points) -> np.ndarray:
    pts = np.asarray(points, dtype=float).reshape(-1, 3)
    return (T[:3, :3] @ pts.T).T + T[:3, 3]


def station_object_pose(editor, system, scene_bundle) -> tuple[np.ndarray, np.ndarray] | None:
    """(object point, outward axis) of a station -- the object-plane centre and its true
    normal from the scene bundle's object target, falling back to object->image."""
    rows = getattr(editor, "rows", None) or []
    if len(rows) < 2:
        return None
    try:
        obj_pt = np.asarray(editor._surface_reference_world_point(0, system=system), dtype=float).reshape(3)
        img_pt = np.asarray(
            editor._surface_reference_world_point(len(rows) - 1, system=system), dtype=float
        ).reshape(3)
    except Exception:
        return None
    axis = img_pt - obj_pt
    for target_row in (getattr(scene_bundle, "targets", None) or []):
        if not getattr(target_row, "is_object", False):
            continue
        n = getattr(target_row, "normal_world", None)
        if n is None:
            continue
        try:
            n = np.asarray(n, dtype=float).reshape(3)
        except Exception:
            continue
        if np.all(np.isfinite(n)) and float(np.linalg.norm(n)) > 1e-9:
            axis = n if float(np.dot(n, axis)) >= 0.0 else -n
            break
    if float(np.linalg.norm(axis)) <= 1e-9 or not np.all(np.isfinite(obj_pt)):
        return None
    return obj_pt, axis


# ---------------------------------------------------------------------------------
# Headless stations
# ---------------------------------------------------------------------------------
@dataclass
class StationScene:
    face: str
    layout: Path
    editor: Any
    system: Any
    rays: Any
    bundle: Any
    obj_point: np.ndarray
    obj_axis: np.ndarray
    transform: np.ndarray
    notes: list[str] = field(default_factory=list)


def load_station(layout_path: str | Path, face: str, part_spec: dict[str, Any], *, trace_rays: bool = True) -> StationScene:
    """Load one station layout HEADLESS (no embedded inspector), trace it, and derive
    its face transform. The caller owns ``editor`` (call ``.destroy()``)."""
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    layout = Path(layout_path).expanduser()
    if not layout.exists():
        raise FileNotFoundError(f"station layout not found: {layout}")
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    # The legacy scene populator reads a few INSPECTOR-owned Tk vars through the
    # editor; a headless station has no inspector, so seed them (checked through
    # __dict__: a Tk widget's __getattr__ delegates to self.tk and recurses on a
    # missing attribute, the bugs/0594 trap).
    import tkinter as _tk

    for name, default in (("show_terminal_diagnostics_var", False), ("show_reference_surfaces_var", False)):
        if editor.__dict__.get(name) is None:
            try:
                setattr(editor, name, _tk.BooleanVar(master=editor, value=default))
            except Exception:
                pass
    editor.layout_files[f"cell_{face}"] = layout
    editor.load_layout_by_name(f"cell_{face}")
    try:
        editor._preview_trace_deferred_until_requested = False  # a cell wants the real trace
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=trace_rays)
    pose = station_object_pose(editor, system, bundle)
    if pose is None:
        editor.destroy()
        raise RuntimeError(f"station {face}: object plane pose not derivable from {layout.name}")
    fr = cell_part_frames(part_spec)[face]
    T = station_frame_transform(pose[0], pose[1], fr["center"], fr["normal"], fr["u"])
    return StationScene(face=face, layout=layout, editor=editor, system=system, rays=rays,
                        bundle=bundle, obj_point=pose[0], obj_axis=pose[1], transform=T)


def _vtk_matrix(T: np.ndarray):
    import vtk

    m = vtk.vtkMatrix4x4()
    for r in range(4):
        for c in range(4):
            m.SetElement(r, c, float(T[r, c]))
    return m


# ---------------------------------------------------------------------------------
# Composite view
# ---------------------------------------------------------------------------------
def compose_cell_plotter(cell_spec: dict[str, Any], *, off_screen: bool = False, trace_rays: bool = True):
    """Build ONE pyvista scene holding the part and every enabled station, each placed
    by its face transform. Returns (plotter, report)."""
    import pyvista as pv

    spec = normalize_cell_spec(cell_spec)
    part = spec["part"]
    plotter = pv.Plotter(off_screen=off_screen)
    try:
        plotter.set_background("white")
    except Exception:
        pass
    report: dict[str, Any] = {"stations": [], "errors": [], "interferences": [], "station_actor_keys": {}}

    # the part: translucent box + six dotted blow-out axes at the cell origin
    corners = cell_part_corners(part)
    faces = np.asarray([4, 0, 1, 3, 2, 4, 4, 6, 7, 5, 4, 0, 4, 5, 1, 4, 2, 3, 7, 6, 4, 0, 2, 6, 4, 4, 1, 5, 7, 3])
    box = pv.PolyData(corners, faces)
    plotter.add_mesh(box, color=(0.55, 0.60, 0.70), opacity=0.25, name="cell_part")
    for rec in cell_axis_records(part):
        pts = np.asarray(rec["points"], dtype=float)
        seg = pv.lines_from_points(pts)
        plotter.add_mesh(seg, color=(0.2, 0.4, 1.0), line_width=1.5, name=f"cell_axis_{rec['face']}")

    for face in FACE_ORDER:
        entry = spec["stations"][face]
        if not entry["enabled"] or not entry["layout"]:
            continue
        try:
            station = load_station(entry["layout"], face, part, trace_rays=trace_rays)
        except Exception as exc:
            report["errors"].append(f"{face}: {exc}")
            continue
        try:
            before = set(plotter.renderer.actors.keys())
            info = station.editor._populate_legacy_3d_plotter_scene(
                plotter, station.system, station.rays,
                scene_bundle=station.bundle, add_clip_plane=False, add_labels=False,
            ) or {}
            # The station's own dotted optical-axis guide is hundreds of mm long; six
            # of them transformed blew the scene extent up until the stations were
            # sub-pixel and polluted the interference boxes (measured 4809 mm
            # "overlaps"). The cell draws the face axes itself -- drop the helpers.
            for helper in list(info.get("helper_actors") or []):
                try:
                    plotter.remove_actor(helper, render=False)
                except Exception:
                    pass
            new_keys = [k for k in plotter.renderer.actors.keys() if k not in before]
            report["station_actor_keys"][face] = list(new_keys)  # the embedded view maps picks to faces
            matrix = _vtk_matrix(station.transform)
            for key in new_keys:
                try:
                    plotter.renderer.actors[key].SetUserMatrix(matrix)
                except Exception:
                    continue
            # Interference boxes: CAD BODIES only (lens/camera STEP meshes + any lens
            # or mirror solids) -- never rays, planes, or guides.
            bounds = None
            body_actors = []
            for entries in (info.get("cad_step_actors") or {}).values():
                for kind, actor in list(entries or []):
                    if str(kind) == "mesh":
                        body_actors.append(actor)
            for key in ("lens_actors", "mirror_actors"):
                body_actors.extend(list(info.get(key) or []))
            for actor in body_actors:
                try:
                    b = np.asarray(actor.GetBounds(), dtype=float)
                except Exception:
                    continue
                if b.size == 6 and np.all(np.isfinite(b)):
                    bounds = b if bounds is None else np.array(
                        [min(bounds[0], b[0]), max(bounds[1], b[1]), min(bounds[2], b[2]),
                         max(bounds[3], b[3]), min(bounds[4], b[4]), max(bounds[5], b[5])]
                    )
            report["stations"].append(
                {
                    "face": face,
                    "layout": str(station.layout),
                    "actors": len(new_keys),
                    "object_point_cell": apply_transform(station.transform, station.obj_point)[0].tolist(),
                    "bounds": None if bounds is None else bounds.tolist(),
                }
            )
        except Exception as exc:
            report["errors"].append(f"{face}: compose failed: {exc}")
        finally:
            try:
                station.editor.destroy()
            except Exception:
                pass
    report["interferences"] = interference_report(report["stations"])
    try:
        plotter.add_axes()
        plotter.reset_camera()
    except Exception:
        pass
    return plotter, report


def interference_report(stations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Pairwise axis-aligned overlap of the stations' body boxes (mm)."""
    out = []
    for i in range(len(stations)):
        for j in range(i + 1, len(stations)):
            a, b = stations[i].get("bounds"), stations[j].get("bounds")
            if a is None or b is None:
                continue
            ox = min(a[1], b[1]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[2], b[2])
            oz = min(a[5], b[5]) - max(a[4], b[4])
            if ox > 0 and oy > 0 and oz > 0:
                out.append({"a": stations[i]["face"], "b": stations[j]["face"],
                            "overlap_mm": [round(ox, 2), round(oy, 2), round(oz, 2)]})
    return out


def cell_summary(report: dict[str, Any]) -> str:
    lines = []
    for st in report.get("stations", []):
        p = st.get("object_point_cell") or [0, 0, 0]
        lines.append(f"{st['face']:6}: {Path(st['layout']).name} -- {st['actors']} actors, object plane at "
                     f"({p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f})")
    for err in report.get("errors", []):
        lines.append(f"ERROR {err}")
    inter = report.get("interferences", [])
    if inter:
        for it in inter:
            lines.append(f"INTERFERENCE {it['a']} x {it['b']}: overlap {it['overlap_mm']} mm (body boxes)")
    else:
        lines.append("No station body-box interference.")
    return "\n".join(lines) if lines else "No stations."


# ---------------------------------------------------------------------------------
# Composite STEP
# ---------------------------------------------------------------------------------
def export_cell_step(cell_spec: dict[str, Any], target_path: str | Path) -> dict[str, Any]:
    """Every enabled station's native STEP export, transformed onto its face, plus the
    part box, in ONE compound."""
    from dataclasses import asdict

    from KrakenOS.UI.services.cad_step_export import (
        _read_step_shape,
        _shape_with_affine,
        _write_step_with_cad_shapes_and_rays,
    )
    from KrakenOS.UI.surface_table_model import SurfaceRow

    try:
        from OCC.Core.BRep import BRep_Builder
        from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
        from OCC.Core.gp import gp_Pnt
        from OCC.Core.IFSelect import IFSelect_RetDone
        from OCC.Core.Interface import Interface_Static
        from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
        from OCC.Core.TopoDS import TopoDS_Compound
    except Exception as exc:  # pragma: no cover - environment
        raise RuntimeError(f"pythonocc-core is required for the cell STEP export: {exc}") from exc

    spec = normalize_cell_spec(cell_spec)
    part = spec["part"]
    builder = BRep_Builder()
    compound = TopoDS_Compound()
    builder.MakeCompound(compound)
    report: dict[str, Any] = {"stations": [], "errors": []}
    corners = cell_part_corners(part)
    lo, hi = corners.min(axis=0), corners.max(axis=0)
    builder.Add(compound, BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Shape())
    with tempfile.TemporaryDirectory() as tmp:
        for face in FACE_ORDER:
            entry = spec["stations"][face]
            if not entry["enabled"] or not entry["layout"]:
                continue
            try:
                station = load_station(entry["layout"], face, part, trace_rays=True)
            except Exception as exc:
                report["errors"].append(f"{face}: {exc}")
                continue
            try:
                cad_shapes = station.editor._collect_native_step_export_shapes(station.system)
                ray_polylines = station.editor._step_export_ray_polylines(station.system)
                rows_snapshot = [SurfaceRow(**asdict(row)) for row in station.editor.rows]
                tmp_path = Path(tmp) / f"station_{face}.step"
                _write_step_with_cad_shapes_and_rays(
                    station.system, rows_snapshot, cad_shapes, ray_polylines, tmp_path,
                    dimension_polylines=[],
                )
                shape = _shape_with_affine(_read_step_shape(tmp_path), station.transform)
                builder.Add(compound, shape)
                report["stations"].append({"face": face, "layout": str(station.layout)})
            except Exception as exc:
                report["errors"].append(f"{face}: STEP failed: {exc}")
            finally:
                try:
                    station.editor.destroy()
                except Exception:
                    pass
    writer = STEPControl_Writer()
    try:
        Interface_Static.SetCVal("write.step.unit", "MM")
    except Exception:
        pass
    writer.Transfer(compound, STEPControl_AsIs)
    status = writer.Write(str(Path(target_path).expanduser()))
    if status != IFSelect_RetDone:
        raise RuntimeError("STEP writer failed for the cell compound")
    report["path"] = str(Path(target_path).expanduser())
    return report


# ---------------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------------
def open_inspection_cell_dialog(editor):
    """Modeless dialog: part dims, six face -> station layout slots, Cell View, Cell
    STEP, save/load, interference report."""
    import tkinter as tk
    from tkinter import filedialog, ttk

    parent = editor.winfo_toplevel() if hasattr(editor, "winfo_toplevel") else editor
    dialog = tk.Toplevel(parent)
    dialog.title("Inspection Cell (6 stations)")
    try:
        dialog.transient(parent)
    except Exception:
        pass
    spec = normalize_cell_spec(getattr(editor, "inspection_cell_spec", None))
    if not getattr(editor, "inspection_cell_spec", None):
        # seed the part from the current layout's part, if it has one
        spec["part"] = normalize_inspection_part_spec(getattr(editor, "inspection_part_spec", None))
        spec["part"]["enabled"] = True
    w_var = tk.StringVar(value=f"{spec['part']['width_mm']:g}")
    h_var = tk.StringVar(value=f"{spec['part']['height_mm']:g}")
    d_var = tk.StringVar(value=f"{spec['part']['depth_mm']:g}")
    layout_vars = {face: tk.StringVar(value=spec["stations"][face]["layout"]) for face in FACE_ORDER}
    enabled_vars = {face: tk.BooleanVar(value=spec["stations"][face]["enabled"]) for face in FACE_ORDER}
    status_var = tk.StringVar(value="")

    body = ttk.Frame(dialog, padding=12)
    body.grid(row=0, column=0, sticky="nsew")
    ttk.Label(body, text="Part W x H x D (mm)").grid(row=0, column=0, sticky="w")
    dims = ttk.Frame(body)
    dims.grid(row=0, column=1, columnspan=3, sticky="w")
    for col, var in enumerate((w_var, h_var, d_var)):
        ttk.Entry(dims, textvariable=var, width=8).grid(row=0, column=col, padx=(0, 4))
    ttk.Label(body, text="Face").grid(row=1, column=0, sticky="w", pady=(8, 2))
    ttk.Label(body, text="Station layout (.py)").grid(row=1, column=1, sticky="w", pady=(8, 2))
    for r, face in enumerate(FACE_ORDER, start=2):
        ttk.Checkbutton(body, text=face.capitalize(), variable=enabled_vars[face]).grid(row=r, column=0, sticky="w")
        ttk.Entry(body, textvariable=layout_vars[face], width=52).grid(row=r, column=1, sticky="we", pady=1)

        def _browse(f=face):
            path = filedialog.askopenfilename(
                title=f"Station layout for the {f} face",
                filetypes=[("KrakenOS layout", "*.py"), ("All files", "*")],
                parent=dialog,
            )
            if path:
                layout_vars[f].set(path)
                enabled_vars[f].set(True)

        ttk.Button(body, text="Browse...", command=_browse).grid(row=r, column=2, padx=(4, 0))

    def _read() -> dict[str, Any]:
        raw = {
            "part": {"enabled": True, "width_mm": w_var.get(), "height_mm": h_var.get(), "depth_mm": d_var.get()},
            "stations": {face: {"layout": layout_vars[face].get().strip(), "enabled": bool(enabled_vars[face].get())}
                         for face in FACE_ORDER},
        }
        cell = normalize_cell_spec(raw)
        editor.inspection_cell_spec = cell
        return cell

    def _view():
        cell = _read()
        status_var.set("Opening the embedded cell view (each station is loaded and traced)...")
        dialog.update_idletasks()
        # bugs/0664 (phase 3): the embedded Tk/VTK window -- double-click a station to
        # edit it, saves re-compose. Falls back to the pyvista window on its own.
        try:
            from KrakenOS.UI.panels.inspection_cell_window import open_inspection_cell_window

            window = open_inspection_cell_window(editor, cell)
        except Exception as exc:
            status_var.set(f"Cell view failed: {exc}")
            return
        if window is not None:
            status_var.set(window.status_var.get() or "Cell view open.")
            editor.inspection_cell_window = window
        else:
            status_var.set("Cell shown in the pyvista window (embedded view unavailable).")

    def _report():
        cell = _read()
        status_var.set("Composing off-screen for the interference report...")
        dialog.update_idletasks()
        try:
            plotter, report = compose_cell_plotter(cell, off_screen=True)
            try:
                plotter.close()
            except Exception:
                pass
        except Exception as exc:
            status_var.set(f"Report failed: {exc}")
            return
        status_var.set(cell_summary(report))

    def _export():
        cell = _read()
        path = filedialog.asksaveasfilename(
            title="Export Cell STEP", defaultextension=".step",
            filetypes=[("STEP", "*.step *.stp"), ("All files", "*")], parent=dialog,
        )
        if not path:
            return
        status_var.set("Exporting the cell STEP (each station exported, transformed, merged)...")
        dialog.update_idletasks()
        try:
            report = export_cell_step(cell, path)
        except Exception as exc:
            status_var.set(f"Cell STEP failed: {exc}")
            return
        errs = "; ".join(report.get("errors", []))
        status_var.set(f"Cell STEP written: {Path(path).name} ({len(report['stations'])} stations)"
                       + (f" -- errors: {errs}" if errs else ""))

    def _save():
        cell = _read()
        path = filedialog.asksaveasfilename(
            title="Save Cell", defaultextension=CELL_SUFFIX,
            filetypes=[("Inspection cell", "*" + CELL_SUFFIX), ("All files", "*")], parent=dialog,
        )
        if path:
            target = save_cell(path, cell)
            status_var.set(f"Cell saved: {target.name}")

    def _load():
        path = filedialog.askopenfilename(
            title="Load Cell", filetypes=[("Inspection cell", "*" + CELL_SUFFIX), ("All files", "*")], parent=dialog,
        )
        if not path:
            return
        try:
            cell = load_cell(path)
        except Exception as exc:
            status_var.set(f"Load failed: {exc}")
            return
        w_var.set(f"{cell['part']['width_mm']:g}"); h_var.set(f"{cell['part']['height_mm']:g}")
        d_var.set(f"{cell['part']['depth_mm']:g}")
        for face in FACE_ORDER:
            layout_vars[face].set(cell["stations"][face]["layout"])
            enabled_vars[face].set(cell["stations"][face]["enabled"])
        editor.inspection_cell_spec = cell
        status_var.set(f"Cell loaded: {Path(path).name}")

    buttons = ttk.Frame(body)
    buttons.grid(row=9, column=0, columnspan=3, sticky="w", pady=(10, 4))
    for col, (text, cmd) in enumerate((("Open Cell View", _view), ("Interference Report", _report),
                                       ("Export Cell STEP...", _export), ("Save Cell...", _save),
                                       ("Load Cell...", _load), ("Close", dialog.destroy))):
        ttk.Button(buttons, text=text, command=cmd).grid(row=0, column=col, padx=(0, 6))
    ttk.Label(body, textvariable=status_var, wraplength=640, justify="left").grid(
        row=10, column=0, columnspan=3, sticky="w", pady=(6, 0)
    )
    ttk.Label(
        body,
        text="Design each face's station as its own layout (Actions -> Inspection Part, inspected face =\n"
             "that face), then slot the layouts here. The cell view/STEP place every station on its face.",
        justify="left",
    ).grid(row=11, column=0, columnspan=3, sticky="w", pady=(8, 0))
    try:
        editor._show_centered_dialog(dialog)
    except Exception:
        pass
    return dialog
