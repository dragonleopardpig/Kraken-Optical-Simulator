"""0687 (flag 201645): six-part fix on the remodelled om05a scene.

1. Outer + centre mirrors -> clean extruded-triangle RA prisms (the proven 0675
   recipe; RA mirrors 1/2 in this scene arm first-surface) with the hypotenuse ON
   the CAD coated plane -- the 3 mm slab's Mirror face never armed, so the beam
   refracted through and TIR'd at the BACK plane (the user's "second surface" +
   the 548 um red-field defocus).
2. Re-anchor the world on the PART: every free-placed solid shifts +3.9 in z so
   face A of the centred 50-mm part IS the object plane z=0 (face B = -50, the
   symmetry plane -25). "The ray is not launching from the object plane" fixed at
   the root; the launch grid needs no change.
3. faceB mirrored launch: mirror_launch_plane_z -> -25.0, bounds opened to the
   full FOV (radius 27.5) so arm B launches the same 3x3 field grid as arm A
   ("only launching one point of ray missing the other two").
4. Bands on BOTH part faces (z=0 and z=-50) at the CALCULATED one-side FOV.
5. Refocus is measured separately (0687_refocus) after this geometry lands.
"""
import math
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")
COMP = Path("attachment/om05a_components")
SHIFT_Z = 3.9

# station -> (row name, CAD source solid index, approx beam fold point PRE-shift)
MIRROR_STATIONS = [
    ("Outer RA mirror A", 7, (0.0, 10.5, 4.88)),
    ("Centre RA mirror A", 9, (0.0, 10.5, -19.6)),
    ("Outer RA mirror B", 8, (0.0, 10.5, -62.68)),
    ("Centre RA mirror B", 9, (0.0, 10.5, -38.2)),
]
HYP_HALF = 10.5   # half-length of the hypotenuse in the fold plane
DEPTH = 7.0       # right-angle depth behind the coated plane
HALF_X = 37.5


def beam_side_plane(solid, fold_point):
    """The 45-degree plane of `solid` (scene frame) closest to the beam point."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("ex", "bugs/0684_extract_real_optics.py")
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    scene = ex.fix_shape(ex.to_scene(solid))

    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    target = np.asarray(fold_point, dtype=float)
    best = None
    exp = TopExp_Explorer(scene, TopAbs_FACE)
    while exp.More():
        f = exp.Current()
        surf = BRepAdaptor_Surface(f)
        if surf.GetType() == GeomAbs_Plane:
            pln = surf.Plane()
            n = np.array([pln.Axis().Direction().X(), pln.Axis().Direction().Y(), pln.Axis().Direction().Z()])
            if abs(abs(n[1]) - 0.7071) < 0.03 and abs(abs(n[2]) - 0.7071) < 0.03:
                props = GProp_GProps()
                brepgprop.SurfaceProperties(f, props)
                if props.Mass() > 400.0:
                    c = np.array([props.CentreOfMass().X(), props.CentreOfMass().Y(), props.CentreOfMass().Z()])
                    n_hat = n / np.linalg.norm(n)
                    dist = abs(float(n_hat @ (target - c)))
                    if best is None or dist < best[0]:
                        best = (dist, c, n_hat)
        exp.Next()
    assert best is not None
    _d, c, n_hat = best
    # orient the normal toward the beam side
    if float(n_hat @ (target - c)) < 0.0:
        n_hat = -n_hat
    return c, n_hat


def clean_prism(c, n_beam):
    """Watertight extruded-triangle RA prism: hypotenuse ON the plane (c, n_beam),
    body extruded BEHIND it (0675 recipe). Scene-frame mesh, centred at bbox centre.
    Returns (occ shape local, bbox centre world)."""
    from OCC.Core.gp import gp_Pnt, gp_Vec
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace,
        BRepBuilderAPI_Transform,
    )
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCC.Core.gp import gp_Trsf

    x_hat = np.array([1.0, 0.0, 0.0])
    t_hat = np.cross(x_hat, n_beam)
    t_hat /= np.linalg.norm(t_hat)
    p1 = c - t_hat * HYP_HALF
    p2 = c + t_hat * HYP_HALF
    p3 = c - n_beam * DEPTH
    tri = [p - x_hat * HALF_X for p in (p1, p2, p3)]
    wire = BRepBuilderAPI_MakeWire()
    for a, b in zip(tri, tri[1:] + tri[:1]):
        wire.Add(BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b)).Edge())
    face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    prism = BRepPrimAPI_MakePrism(face, gp_Vec(*(x_hat * 2 * HALF_X))).Shape()
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    brepbndlib.Add(prism, box)
    b = np.array(box.Get(), dtype=float)
    centre = 0.5 * (b[:3] + b[3:])
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(*(-centre)))
    local = BRepBuilderAPI_Transform(prism, tr, True).Shape()
    return local, centre


def save_step(shape, name):
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs

    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    writer.Write(str(COMP / name))
    print("wrote", name)


def synthesize_mirrors():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ex", "bugs/0684_extract_real_optics.py")
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    solids = ex.load_solids()
    manifest = {}
    for name, idx, fold_pt in MIRROR_STATIONS:
        c, n_beam = beam_side_plane(solids[idx], fold_pt)
        # centre mirrors share solid 9 -- keep only the flank on this station's side
        if idx == 9:
            flank_z_sign = 1.0 if fold_pt[2] > -28.9 else -1.0
            if (n_beam[2] > 0) != (flank_z_sign > 0):
                # wrong flank matched: search again constrained by z-side of centre
                pass  # beam_side_plane's fold point already selects the right flank
        local, centre = clean_prism(c, n_beam)
        mesh_name = name.lower().replace(" ", "_") + "_0687"
        save_step(local, f"{mesh_name}.step")
        manifest[name] = {"mesh": mesh_name, "centre": centre.tolist(),
                          "plane_c": c.tolist(), "plane_n": n_beam.tolist()}
        print(f"  {name}: coated plane through {np.round(c,2).tolist()} n {np.round(n_beam,3).tolist()}")
    import json

    (COMP / "manifest_0687.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def apply_scene(manifest):
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import row_z_positions
    from KrakenOS.UI.services.optical_solid_workflow import _optical_solid_mesh_path_from_source

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    # 1) swap the four mirror rows to the clean prisms (pose already includes no shift;
    #    the +3.9 re-anchor below applies to them too)
    for index, row in enumerate(list(editor.rows)):
        name = str(row.name)
        if name not in manifest:
            continue
        entry = manifest[name]
        centre = np.asarray(entry["centre"], dtype=float)
        mesh_path, _src, source_format = _optical_solid_mesh_path_from_source(
            (COMP / f"{entry['mesh']}.step").resolve()
        )
        fresh = editor._optical_stl_solid_row(
            mesh_path.resolve(), source_path=(COMP / f"{entry['mesh']}.step").resolve(),
            source_format=source_format,
        )
        row.element = fresh.element
        row.glass = "BK7"
        row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        adv = dict(row.advanced or {})
        fresh_adv = dict(fresh.advanced or {})
        for key in ("Solid_3d_stl", "OpticalSolidSourcePath", "OpticalSolidSourceFormat",
                    "OpticalSolidFaces", "Note"):
            if key in fresh_adv:
                adv[key] = fresh_adv[key]
        adv["StepOverlayPromotion"] = {"center_world": centre.tolist()}
        row.advanced = adv
        faces = (adv.get("OpticalSolidFaces") or {}).get("faces") or []
        hyp = None
        for rec in faces:
            rec["port_role"] = "Auto"
            n = np.asarray(rec.get("normal") or (0, 0, 0), dtype=float)
            if abs(abs(n[1]) - 0.7071) < 0.05 and abs(abs(n[2]) - 0.7071) < 0.05:
                if hyp is None or int(rec.get("triangle_count") or 0) > int(hyp.get("triangle_count") or 0):
                    hyp = rec
        assert hyp is not None, name
        hyp["function"] = "Mirror"
        hyp["role"] = "Mirror"
        hyp["port_role"] = "Interaction Surface"
        hyp["assignment_source"] = "manual"
        zs = row_z_positions(editor.rows)
        z_station = float(zs[index]) if index < len(zs) else 0.0
        row.desp_x, row.desp_y = float(centre[0]), float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        print(f"  swapped {name} -> clean prism at {np.round(centre, 2).tolist()}")

    # 2) re-anchor the world on the part face: every free-placed solid +SHIFT_Z in z
    for index, row in enumerate(editor.rows):
        adv = row.advanced if isinstance(row.advanced, dict) else {}
        promo = adv.get("StepOverlayPromotion")
        if isinstance(promo, dict) and isinstance(promo.get("center_world"), (list, tuple)):
            cw = [float(v) for v in promo["center_world"]]
            cw[2] += SHIFT_Z
            promo["center_world"] = cw
            row.desp_z = float(row.desp_z) + SHIFT_Z
    # the part now spans z 0..-50 exactly
    part = dict(getattr(editor, "inspection_part_spec", None) or {})
    part["axis_offset_mm"] = 0.0
    editor.inspection_part_spec = part

    # 3) faceB mirrored launch: symmetry plane -25, full-FOV bounds
    specs = list(getattr(editor, "layout_scene_source_specs", []) or [])
    for spec_dict in specs:
        if str(spec_dict.get("source_id", "")) == "source:faceB":
            spec_dict["mirror_launch_plane_z"] = -25.0
            spec_dict["source_z"] = -50.0
            spec_dict["radius_x"] = 27.5
            spec_dict["radius_y"] = 27.5
            spec_dict["radius"] = 27.5
    editor.layout_scene_source_specs = specs

    # 4) bands ON the part faces at the calculated one-side FOV:
    #    width = sensor 23.04 / m 0.419 = 55.0; height = the geometric acceptance
    #    (outer-window +-5.25 into the centre-flank window) ~ y -5.25..+3.1
    editor.layout_object_fov_bands = [
        {"name": "Face A field", "center": [0.0, 0.0, 0.0], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1},
        {"name": "Face B field", "center": [0.0, 0.0, -50.0], "axis": [0.0, 0.0, 1.0],
         "half_width": 27.5, "v_lo": -5.25, "v_hi": 3.1},
    ]

    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)


if __name__ == "__main__":
    manifest = synthesize_mirrors()
    apply_scene(manifest)
