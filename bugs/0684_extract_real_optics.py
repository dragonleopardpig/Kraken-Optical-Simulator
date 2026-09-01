"""0684: extract the REAL per-station optics from the om05a assembly CAD.

User (mid-0683): "Outer Prism is Right Angle Mirror ... Lower Prism is a Cube Beam
Splitter ... they should be attached ... Center Prism is a Right Angle Mirror."

CAD truth (solids of attachment/om05a_26_1_r03_2s_lr_asm.stp, armA map
scene = (-x-89.3, 160.95-y, z-30.4)):
  solid 10/11 = the BS half beyond the cement diagonal (75x10.5x10.5 bar, scene
                z ~+5.3 / -63.25) -- the LOWER station;
  solid  7/8  = the outer RA mirror (75x14.8x15, scene y 11.65) -- FIRST surface;
  solid  9    = ONE centre V-block, two opposed 45 deg flanks (scene z -28.9 +-12)
                -- cut at the midplane into the A / B centre mirrors.

Each extracted STEP is authored in the NATIVE CAD frame, origin at its own bbox
centre; the armA map (two mirrors = Rz(180) + T) is realized by the ROW pose
(tilt_z=180, desp = center_world - station) -- OCC mirror transforms inverted the
solids' orientation (rays traced INSIDE-OUT: no entry event, Mirror pass-through),
so the mesh is never mirrored on disk. The BS NEAR half (the piece the imaging
beam traverses; the fold is TIR at the cement plane) is synthesized from the cube
bbox cut 0.02 mm shy of the diagonal.
"""
from pathlib import Path

import numpy as np

OUT = Path("attachment/om05a_components")
ASM = Path("attachment/om05a_26_1_r03_2s_lr_asm.stp")


def scene_transform():
    """(R, t): scene = R @ cad + t."""
    R = np.diag([-1.0, -1.0, 1.0])
    t = np.array([-89.3, 160.95, -30.4])
    return R, t


def load_solids():
    from OCC.Core.STEPControl import STEPControl_Reader
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_SOLID

    reader = STEPControl_Reader()
    reader.ReadFile(str(ASM))
    reader.TransferRoots()
    shape = reader.OneShape()
    solids = []
    exp = TopExp_Explorer(shape, TopAbs_SOLID)
    while exp.More():
        solids.append(exp.Current())
        exp.Next()
    return solids


def to_scene(shape):
    """Apply the armA map to an OCC shape.

    (x, y, z) -> (-x - 89.3, 160.95 - y, z - 30.4): the linear part diag(-1,-1,1)
    IS a proper rotation -- 180 degrees about Z. Building it as SetRotation (not a
    pair of SetMirror ops) keeps OCC's face orientations untouched; the mirror
    construction traced INSIDE-OUT (no entry refraction, Mirror pass-through)."""
    import math

    from OCC.Core.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.pi)
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(-89.3, 160.95, -30.4))
    total = gp_Trsf()
    total.Multiply(tr)
    total.Multiply(rot)
    return BRepBuilderAPI_Transform(shape, total, True).Shape()


def fix_shape(shape):
    """bugs/0684: the assembly STEP's solids trace INSIDE-OUT (rays cross every
    face without refraction and the Mirror hyp without reflecting) -- run the
    OCC shape healer to repair face/shell orientation before meshing."""
    from OCC.Core.ShapeFix import ShapeFix_Shape

    fixer = ShapeFix_Shape(shape)
    fixer.Perform()
    return fixer.Shape()


def bbox(shape):
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib

    box = Bnd_Box()
    brepbndlib.Add(shape, box)
    return np.array(box.Get(), dtype=float)  # xmin ymin zmin xmax ymax zmax


def centre_local(shape):
    """Translate so the bbox centre is the origin. Returns (shape, world_centre)."""
    from OCC.Core.gp import gp_Trsf, gp_Vec
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

    b = bbox(shape)
    c = 0.5 * (b[:3] + b[3:])
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(-c[0], -c[1], -c[2]))
    return BRepBuilderAPI_Transform(shape, tr, True).Shape(), c


def save_step(shape, name):
    from OCC.Core.STEPControl import STEPControl_Writer, STEPControl_AsIs

    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    path = OUT / name
    writer.Write(str(path))
    print("wrote", path.name)
    return path


def half_space_cut(shape, point, normal):
    """Keep the part of `shape` on the -normal side of the plane."""
    from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Pln
    from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeFace
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeHalfSpace
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common

    pln = gp_Pln(gp_Pnt(*point), gp_Dir(*normal))
    face = BRepBuilderAPI_MakeFace(pln).Face()
    ref = gp_Pnt(*(np.asarray(point, dtype=float) - 10.0 * np.asarray(normal, dtype=float)))
    half = BRepPrimAPI_MakeHalfSpace(face, ref).Solid()
    return BRepAlgoAPI_Common(shape, half).Shape()


def make_box(lo, hi):
    from OCC.Core.gp import gp_Pnt
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox

    return BRepPrimAPI_MakeBox(gp_Pnt(*lo), gp_Pnt(*hi)).Solid()


def diagonal_face_plane(shape):
    """The largest 45-degree (|ny| ~ |nz| ~ 0.707) planar face -> (point, normal)."""
    from OCC.Core.TopExp import TopExp_Explorer
    from OCC.Core.TopAbs import TopAbs_FACE
    from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
    from OCC.Core.GeomAbs import GeomAbs_Plane
    from OCC.Core.BRepGProp import brepgprop
    from OCC.Core.GProp import GProp_GProps

    best = None
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        f = exp.Current()
        surf = BRepAdaptor_Surface(f)
        if surf.GetType() == GeomAbs_Plane:
            pln = surf.Plane()
            n = np.array([pln.Axis().Direction().X(), pln.Axis().Direction().Y(), pln.Axis().Direction().Z()])
            if abs(abs(n[1]) - 0.7071) < 0.03 and abs(abs(n[2]) - 0.7071) < 0.03:
                props = GProp_GProps()
                brepgprop.SurfaceProperties(f, props)
                if best is None or props.Mass() > best[0]:
                    c = props.CentreOfMass()
                    best = (props.Mass(), np.array([c.X(), c.Y(), c.Z()]), n)
        exp.Next()
    assert best is not None, "no 45-degree face"
    return best[1], best[2]


def scene_centre(native_centre):
    c = np.asarray(native_centre, dtype=float)
    return np.array([-c[0] - 89.3, 160.95 - c[1], c[2] - 30.4])


def main():
    solids = load_solids()
    manifest = {}

    # BS far halves: whole CAD solids, scene frame (watertight as-is)
    for idx, name in ((10, "bs_far_half_A_0684r"), (11, "bs_far_half_B_0684r")):
        scene = fix_shape(to_scene(solids[idx]))
        local, centre = centre_local(scene)
        save_step(local, f"{name}.step")
        manifest[name] = centre.tolist()

    # outer RA mirrors: the CAD bodies mesh NON-WATERTIGHT (2236 tris, open edges)
    # -> the glass-volume logic fails and the solid traces INERT. First-surface
    # mirrors only need their coated plane, so synthesize a clean 3 mm slab whose
    # front face IS the CAD's beam-side 45-degree plane (the 0675 clean-mirror
    # pattern; the real body still displays via the chunk decoration).
    from OCC.Core.gp import gp_Pnt, gp_Vec
    from OCC.Core.BRepBuilderAPI import (
        BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeFace,
    )
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism

    for idx, name, fold_point in (
        (7, "outer_mirror_A_0684r", np.array([0.0, 9.4, 4.88])),
        (8, "outer_mirror_B_0684r", np.array([0.0, 9.4, -62.68])),
    ):
        scene = fix_shape(to_scene(solids[idx]))
        best = None
        from OCC.Core.TopExp import TopExp_Explorer
        from OCC.Core.TopAbs import TopAbs_FACE
        from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
        from OCC.Core.GeomAbs import GeomAbs_Plane
        from OCC.Core.BRepGProp import brepgprop
        from OCC.Core.GProp import GProp_GProps

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
                        dist = abs(float(n_hat @ (fold_point - c)))
                        if best is None or dist < best[0]:
                            best = (dist, c, n_hat)
            exp.Next()
        assert best is not None, name
        _dist, c, n_hat = best
        # coated side faces the beam; extrude the slab AWAY from it
        away = n_hat if float(n_hat @ (fold_point - c)) < 0.0 else -n_hat
        u = np.array([1.0, 0.0, 0.0])
        v = np.cross(away, u)
        v /= np.linalg.norm(v)
        hw, hv, thick = 37.5, 7.4, 3.0
        quad = [c + su * hw * u + sv * hv * v for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        wire = BRepBuilderAPI_MakeWire()
        for a, b_pt in zip(quad, quad[1:] + quad[:1]):
            wire.Add(BRepBuilderAPI_MakeEdge(gp_Pnt(*a), gp_Pnt(*b_pt)).Edge())
        face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
        slab = BRepPrimAPI_MakePrism(face, gp_Vec(*(away * thick))).Shape()
        local, centre = centre_local(slab)
        save_step(local, f"{name}.step")
        manifest[name] = centre.tolist()
        print(f"  {name}: coated plane n={np.round(n_hat, 3).tolist()} through {np.round(c, 2).tolist()}")

    # centre V-block: split at the scene midplane z = -28.9 into the two flanks
    centre_scene = fix_shape(to_scene(solids[9]))
    for name, keep_normal in (("centre_mirror_A_0684r", (0.0, 0.0, -1.0)),
                              ("centre_mirror_B_0684r", (0.0, 0.0, 1.0))):
        half = fix_shape(half_space_cut(centre_scene, (0.0, 13.75, -28.9), keep_normal))
        local, centre = centre_local(half)
        save_step(local, f"{name}.step")
        manifest[name] = centre.tolist()

    # BS near halves: scene cube bbox cut 0.02 mm shy of the cement diagonal;
    # keep the side facing the device (the beam's entry + TIR-fold volume)
    for far_idx, name in ((10, "bs_near_half_A_0684r"), (11, "bs_near_half_B_0684r")):
        far_scene = to_scene(solids[far_idx])
        b = bbox(far_scene)
        point, normal = diagonal_face_plane(far_scene)
        cube = make_box(b[:3], b[3:])
        z_near = b[2] if abs(b[2] + 28.9) < abs(b[5] + 28.9) else b[5]
        ref = np.array([0.5 * (b[0] + b[3]), 0.0, z_near])
        side = float((ref - point) @ normal)
        keep_n = normal if side > 0 else -normal
        near = half_space_cut(cube, point + 0.02 * (-keep_n), tuple(-keep_n))
        local, centre = centre_local(near)
        save_step(local, f"{name}.step")
        manifest[name] = centre.tolist()

    print("manifest (center_world):")
    for k, v in manifest.items():
        print(f"  {k}: {np.round(v, 3).tolist()}")
    import json

    (OUT / "manifest_0684r.json").write_text(json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
