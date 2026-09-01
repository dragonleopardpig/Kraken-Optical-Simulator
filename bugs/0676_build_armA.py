"""0676: om05a ARM-A FULLY-FOLDED scene -- the three prism folds become REAL
free-placed clean wedges (through-glass: enter a leg face, reflect at the flagged
hypotenuse, exit), so the actual prism-assembly geometry finally fits the scene.

World = CAD mapped by M3: scene = (-x_cad, -y_cad, z_cad), anchored so device face
A sits at the origin with the chain launching +z. All fold-plane families derive
from the CAD (arm A):
  fold1 outer prism  centre (0,  0.00,  5.35)  hyp plane (0,1,-1): +z -> +y
  fold2 lower prism  centre (0, 11.65,  2.60)  hyp plane (0,1, 1): +y -> -z
  fold3 centre prism centre (0, 13.73,-24.40)  hyp plane (0,1, 1): -z -> +y
  fold4 mirror1      centre (0, 52.80,-28.90)  hyp plane (1,1, 0): +y -> -x
  fold5 mirror2      centre (-272.7, 52.75, -28.9) plane (1,-1,0)-ish: -x -> -y
The row THICKNESS ladder is the tunnel's (it IS the unfolded real path), so the
optical prescription is unchanged; plates are removed (the prisms carry the real
glass). Free-placed contract (0672/0675): StepOverlayPromotion.center_world +
desp/tilts; hyp = Mirror + Interaction Surface, other faces Transmit/Port + Auto.
Prism seating = through-glass (hyp NOT facing the beam); mirror seating =
first-surface (hyp facing the beam). Tilts chosen by the pure-math scan.
Stages save + reload-fresh + trace so a failure localizes.
"""
import math
from dataclasses import asdict
from pathlib import Path

import numpy as np

STRAIGHT = Path("attachment/om05a_two_side.py")
SCENE = Path("attachment/om05a_folded_armA.py")
COMP = Path("attachment/om05a_components")

# (label, plate-row name to replace, wedge size, wedge step, world centre,
#  design fold plane normal (sign-free), incoming direction, want_first_surface)
FOLDS = [
    ("Outer prism A", "Outer prism 4336A", 10.5, "wedge_105.step",
     (0.0, 0.0, 5.35), (0.0, 1.0, -1.0), (0.0, 0.0, 1.0), False),
    ("Lower prism A", "Lower prism 4337A", 15.0, "wedge_150.step",
     (0.0, 11.65, 2.60), (0.0, 1.0, 1.0), (0.0, 1.0, 0.0), False),
    ("Centre prism A", "Centre prism 4338A", 12.0, "wedge_120.step",
     (0.0, 13.73, -24.40), (0.0, 1.0, 1.0), (0.0, 0.0, -1.0), False),
    ("RA mirror 1 (50 mm)", "RA mirror 1 (50 mm)", 50.0, "mirror1_cleanb.step",
     (0.0, 52.80, -28.90), (1.0, 1.0, 0.0), (0.0, 1.0, 0.0), True),
    ("RA mirror 2 (40 mm)", "RA mirror 2 (40 mm)", 40.0, "mirror2_cleanb.step",
     (-272.70, 52.75, -28.90), (1.0, -1.0, 0.0), (-1.0, 0.0, 0.0), True),
]


def make_wedge(size: float, fname: str):
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_MakeEdge,
        BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_MakeWire,
    )
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.gp import gp_Pnt, gp_Trsf, gp_Vec

    if (COMP / fname).exists():
        return
    s = float(size)
    p0, p1, p2 = gp_Pnt(0, 0, 0), gp_Pnt(0, s, 0), gp_Pnt(0, 0, -s)
    wire = BRepBuilderAPI_MakeWire(
        BRepBuilderAPI_MakeEdge(p0, p1).Edge(),
        BRepBuilderAPI_MakeEdge(p1, p2).Edge(),
        BRepBuilderAPI_MakeEdge(p2, p0).Edge(),
    ).Wire()
    solid = BRepPrimAPI_MakePrism(BRepBuilderAPI_MakeFace(wire).Face(), gp_Vec(70.0, 0, 0)).Shape()
    box = Bnd_Box()
    brepbndlib.Add(solid, box)
    x0, y0, z0, x1, y1, z1 = box.Get()
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(-(x0 + x1) / 2, -(y0 + y1) / 2, -(z0 + z1) / 2))
    w = STEPControl_Writer()
    w.Transfer(solid.Moved(TopLoc_Location(tr)), STEPControl_AsIs)
    w.Write(str(COMP / fname))
    print(f"{fname}: clean wedge {s} (70 long), hyp local (0,1,-1)")


def pick_tilts(n_local, design_normal, d_in, want_first_surface):
    """The tilt combo whose mapped hyp matches the design plane AND faces the
    beam (first-surface) or away (through-glass)."""
    from KrakenOS.UI import optical_solid_metadata as osm

    design = np.asarray(design_normal, dtype=float)
    design /= np.linalg.norm(design)
    d = np.asarray(d_in, dtype=float)
    for tx in (0.0, 90.0, -90.0, 180.0):
        for ty in (0.0, 90.0, -90.0):
            for tz in (0.0, 90.0, -90.0, 180.0):
                R = osm.rotation_matrix_from_kraken_tilts(tx, ty, tz)
                n = R @ np.asarray(n_local, dtype=float)
                if abs(abs(float(n @ design)) - 1.0) > 1e-6:
                    continue
                faces_beam = float(n @ d) < -1e-9
                if faces_beam == bool(want_first_surface):
                    return (tx, ty, tz), n
    return None


def build():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import row_z_positions
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    import shutil

    shutil.copyfile("attachment/om05a_folded.py", SCENE)
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor.display_fold_spec = None

    for label, plate_name, size, fname, centre, plane, d_in, first_surface in FOLDS:
        idx = next(i for i, r in enumerate(editor.rows) if str(r.name) == plate_name)
        plate = editor.rows[idx]
        mesh_path, cad_source, source_format = _optical_solid_mesh_path_from_source((COMP / fname).resolve())
        row = editor._optical_stl_solid_row(mesh_path.resolve(), source_path=(COMP / fname).resolve(),
                                            source_format=source_format)
        row.name = label
        row.thickness = float(plate.thickness)
        row.diameter = 77.0
        row.glass = "BK7"
        row.drawing = 1.0
        faces = (row.advanced or {}).get("OpticalSolidFaces")
        face_list = (faces or {}).get("faces") if isinstance(faces, dict) else None
        hyp = None
        for rec in face_list or []:
            n = np.asarray(rec.get("normal") or [0, 0, 0], dtype=float)
            if abs(abs(n[1]) - 0.7071) < 0.06 and abs(abs(n[2]) - 0.7071) < 0.06:
                if hyp is None or int(rec.get("triangle_count") or 0) > int(hyp.get("triangle_count") or 0):
                    hyp = rec
        assert hyp is not None, label
        for rec in face_list or []:
            rec["port_role"] = "Auto"
        hyp["function"] = "Mirror"
        hyp["role"] = "Mirror"
        hyp["port_role"] = "Interaction Surface"
        hyp["assignment_source"] = "manual"
        n_local = np.asarray(hyp.get("normal"), dtype=float)
        picked = pick_tilts(n_local, plane, d_in, first_surface)
        assert picked is not None, f"{label}: no tilt matches"
        (tx, ty, tz), n_world = picked
        zs = row_z_positions(editor.rows[:idx] + [plate])
        z_station = float(zs[idx]) if idx < len(zs) else 0.0
        row.tilt_x, row.tilt_y, row.tilt_z = float(tx), float(ty), float(tz)
        row.desp_x = float(centre[0])
        row.desp_y = float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        row.advanced = dict(row.advanced or {})
        row.advanced["StepOverlayPromotion"] = {"center_world": list(map(float, centre))}
        editor.rows[idx] = row  # REPLACE the plate: the prism carries the real glass
        print(f"  {label}: wedge at {centre}, tilts ({tx},{ty},{tz}), hyp_world {np.round(n_world,3)}, "
              f"{'first-surface' if first_surface else 'through-glass'}")  # tilts=(tx,ty,tz)

    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)


def verify():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    try:
        editor._preview_trace_deferred_until_requested = False
    except Exception:
        pass
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    paths = list(getattr(bundle, "ray_paths", None) or [])
    reached = [rp for rp in paths if bool(getattr(rp, "reaches_image", False))]
    print(f"trace: {len(paths)} paths, {len(reached)} reach image")
    if reached:
        p = np.asarray(getattr(reached[len(reached) // 2], "points_world", None), dtype=float)
        segs = np.diff(p, axis=0)
        lens = np.linalg.norm(segs, axis=1)
        keep = lens > 2.0
        seq = []
        for d in segs[keep] / lens[keep][:, None]:
            key = tuple(int(round(c)) for c in d) if np.max(np.abs(np.abs(d) - 1.0) < 0.15) else None
            if key and (not seq or key != seq[-1]):
                seq.append(key)
        print("chief legs:", seq[:8])
        print("endpoint:", np.round(p[-1], 1).tolist())
    editor.destroy()


if __name__ == "__main__":
    make_wedge(10.5, "wedge_105.step")
    make_wedge(15.0, "wedge_150.step")
    make_wedge(12.0, "wedge_120.step")
    build()
    verify()
