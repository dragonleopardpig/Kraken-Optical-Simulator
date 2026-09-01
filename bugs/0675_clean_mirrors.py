"""0675: replace the assembly's RA-mirror meshes (which carry the mechanical
engineer's ray-representation BUMP on the hypotenuse -- rays leak through it) with
geometrically CLEAN right-angle prisms, and shrink the lens surrogate discs to the
beam-honest size. Rebuild + verify the folded scene."""
import importlib.util
from pathlib import Path

COMP = Path("attachment/om05a_components")


def make_clean_prism(size: float, fname: str):
    """A clean RA prism, chain-seated like the s2 extraction: legs along +y and +z,
    hypotenuse plane (0,1,-1)-family, extruded along x, AABB-centred."""
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

    s = float(size)
    # right-triangle cross-section in the y-z plane at x=0: legs along +y and -z,
    # hypotenuse plane y-z=s with outward normal (0,1,-1)/sqrt2 -- the SAME local
    # family as the assembly extractions, so every 0672 seating contract holds.
    p0 = gp_Pnt(0.0, 0.0, 0.0)
    p1 = gp_Pnt(0.0, s, 0.0)
    p2 = gp_Pnt(0.0, 0.0, -s)
    wire = BRepBuilderAPI_MakeWire(
        BRepBuilderAPI_MakeEdge(p0, p1).Edge(),
        BRepBuilderAPI_MakeEdge(p1, p2).Edge(),
        BRepBuilderAPI_MakeEdge(p2, p0).Edge(),
    ).Wire()
    face = BRepBuilderAPI_MakeFace(wire).Face()
    solid = BRepPrimAPI_MakePrism(face, gp_Vec(s, 0.0, 0.0)).Shape()
    box = Bnd_Box()
    brepbndlib.Add(solid, box)
    x0, y0, z0, x1, y1, z1 = box.Get()
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(-(x0 + x1) / 2, -(y0 + y1) / 2, -(z0 + z1) / 2))
    centred = solid.Moved(TopLoc_Location(tr))
    w = STEPControl_Writer()
    w.Transfer(centred, STEPControl_AsIs)
    w.Write(str(COMP / fname))
    print(f"{fname}: clean RA prism, size {s}")


def main():
    make_clean_prism(50.0, "mirror1_cleanb.step")
    make_clean_prism(40.0, "mirror2_cleanb.step")
    # retarget the folded builder at the clean prisms
    p = Path("bugs/0672_build_om05a_folded.py")
    s = p.read_text()
    s = s.replace('"mirror1_chain.step"', '"mirror1_cleanb.step"')
    s = s.replace('"mirror2_chain_s2.step"', '"mirror2_cleanb.step"')
    p.write_text(s)
    spec = importlib.util.spec_from_file_location("b", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    m.build()
    # beam-honest lens discs on the freshly built scene (V38 glass ~ Ø36; the trace
    # apertures extend beyond drawn discs per bugs/0624, so no ray is clipped)
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    for scene in ("attachment/om05a_folded.py", "attachment/om05a_two_side.py"):
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["p"] = Path(scene).resolve()
        editor.load_layout_by_name("p")
        n = 0
        for r in editor.rows:
            if "Datum" in str(r.name) or "Group" in str(r.name):
                r.diameter = 36.0
                n += 1
        editor._sync_table()
        editor._write_layout_file(Path(scene).resolve())
        editor.destroy()
        print(f"{scene}: {n} surrogate discs -> 36.0")
    m.verify()


if __name__ == "__main__":
    main()
