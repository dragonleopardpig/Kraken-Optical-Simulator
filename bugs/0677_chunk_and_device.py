"""0677 (flag 091046): import the red-boxed prism-assembly chunk (everything above
the first RA mirror) into the folded scene as DISPLAY geometry, and make the device
a 50 x 50 x 1 plate seated in the slot between the outer prisms.

Chunk extraction: the 9 assembly components near x_CAD=-89 with centre y_CAD>115
(housing, top plate, 2 lower blocks, 2 plate LEDs, centre prism, 2 outer prisms) --
NOT the mirror. Pre-oriented R_x(-90) so native z = -y_CAD (the chain direction in
the tunnel scene) and native y = z_CAD (device length -> the unfolded patch axis),
then translated so the DEVICE SLOT plane (y_CAD=160.95) sits at native z=0. The
unpromoted `optical_step_path` overlay is display-only and seats the mesh's
native-z-MIN face at scene z=0 -- a placement z-offset puts the slot back on the
object plane.
"""
import math
from pathlib import Path

COMP = Path("attachment/om05a_components")
SCENE = Path("attachment/om05a_folded.py")


def extract_chunk():
    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.TopoDS import TopoDS_Compound
    from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    from OCC.Extend.DataExchange import read_step_file_with_names_colors

    shapes = read_step_file_with_names_colors("attachment/om05a_26_1_r03_2s_lr_asm.stp")
    picked = []
    for shape, (name, _c) in shapes.items():
        box = Bnd_Box()
        brepbndlib.Add(shape, box)
        x0, y0, z0, x1, y1, z1 = box.Get()
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        if abs(cx + 89.3) < 3.0 and cy > 115.0 and "MIR" not in str(name):
            picked.append((str(name), shape))
    print(f"chunk components: {len(picked)} -> {[n for n, _s in picked]}")
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(comp)
    for _n, shape in picked:
        builder.Add(comp, shape)
    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.radians(-90.0))
    oriented = comp.Moved(TopLoc_Location(rot))
    # after R_x(-90): native = (x_CAD, z_CAD, -y_CAD). Shift so the slot plane
    # (y_CAD=160.95 -> native z=-160.95) lands at native z=0, the device-length
    # centre (z_CAD=1.5) at native y=0, and x_CAD=-89.3 at native x=0.
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(89.3, -1.5, 160.95))
    final = oriented.Moved(TopLoc_Location(tr))
    w = STEPControl_Writer()
    w.Transfer(final, STEPControl_AsIs)
    w.Write(str(COMP / "prism_assembly_chunk.step"))
    box = Bnd_Box()
    brepbndlib.Add(final, box)
    print("chunk native bounds:", [round(v, 1) for v in box.Get()])


def wire_scene():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor.imported_optical_step_path = (COMP / "prism_assembly_chunk.step").resolve()
    # the overlay normalizes the mesh's native z-min to scene z=0; the slot plane
    # sits (0 - zmin) above that, so shift it back onto the object plane.
    editor.optical_step_rotation_x_deg = 0.0
    editor.optical_step_rotation_y_deg = 0.0
    editor.optical_step_rotation_z_deg = 0.0
    # the DUT: a 50 x 50 x 1 plate in the slot (bugs/0661 part; face ON the plane)
    editor.set_inspection_part_spec(
        {"enabled": True, "width_mm": 50.0, "height_mm": 50.0, "depth_mm": 1.0, "active_face": "front"}
    )
    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("scene wired: chunk overlay + 50x50x1 device plate")


if __name__ == "__main__":
    extract_chunk()
    wire_scene()


def extract_chunk_armA():
    """The same 9-component chunk oriented for the ARM-A world:
    scene = (-x_CAD, -y_CAD, z_CAD) + (-89.3, 160.95, -30.4)."""
    from pathlib import Path as _P
    out = _P("attachment/om05a_components/prism_assembly_chunk_armA.step")
    if out.exists():
        # bugs/0679: re-extracting bumps the mtime -> a NEW mesh-cache key every
        # run -> the app rebuilds the cache at launch (and once raced its reader)
        from OCC.Core.Bnd import Bnd_Box as _BB
        from OCC.Core.BRepBndLib import brepbndlib as _bl
        from OCC.Extend.DataExchange import read_step_file as _rd
        box = _BB(); _bl.Add(_rd(str(out)), box)
        b = [round(v, 2) for v in box.Get()]
        print(f"armA chunk exists, reusing (bounds {b})")
        return b
    import math

    from OCC.Core.BRep import BRep_Builder
    from OCC.Core.Bnd import Bnd_Box
    from OCC.Core.BRepBndLib import brepbndlib
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer
    from OCC.Core.TopLoc import TopLoc_Location
    from OCC.Core.TopoDS import TopoDS_Compound
    from OCC.Core.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec
    from OCC.Extend.DataExchange import read_step_file_with_names_colors

    shapes = read_step_file_with_names_colors("attachment/om05a_26_1_r03_2s_lr_asm.stp")
    comp = TopoDS_Compound()
    builder = BRep_Builder()
    builder.MakeCompound(comp)
    n = 0
    for shape, (name, _c) in shapes.items():
        box = Bnd_Box()
        brepbndlib.Add(shape, box)
        x0, y0, z0, x1, y1, z1 = box.Get()
        if abs((x0 + x1) / 2 + 89.3) < 3.0 and (y0 + y1) / 2 > 115.0 and "MIR" not in str(name):
            builder.Add(comp, shape)
            n += 1
    rot = gp_Trsf()
    rot.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 0, 1)), math.radians(180.0))
    tr = gp_Trsf()
    tr.SetTranslation(gp_Vec(-89.3, 160.95, -30.4))
    final = comp.Moved(TopLoc_Location(rot)).Moved(TopLoc_Location(tr))
    w = STEPControl_Writer()
    w.Transfer(final, STEPControl_AsIs)
    w.Write("attachment/om05a_components/prism_assembly_chunk_armA.step")
    box = Bnd_Box()
    brepbndlib.Add(final, box)
    b = [round(v, 2) for v in box.Get()]
    print(f"armA chunk ({n} parts) authored bounds:", b)
    return b


def wire_armA():
    from pathlib import Path as _P

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    b = extract_chunk_armA()
    xmin, ymin, zmin, xmax, ymax, zmax = b
    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = _P("attachment/om05a_folded_armA.py").resolve()
    editor.load_layout_by_name("p")
    editor.imported_optical_step_path = _P("attachment/om05a_components/prism_assembly_chunk_armA.step").resolve()
    editor.optical_step_rotation_x_deg = 0.0
    editor.optical_step_rotation_y_deg = 0.0
    editor.optical_step_rotation_z_deg = 0.0
    # the overlay normalizes authored z-min to 0 AND centres the transverse (x, y)
    # on the axis (barrel behavior; axis_offset_xy is SUBTRACTED after centring) --
    # restore the FULL authored pose (flag 124838: the housing rendered 27.8 mm low,
    # sunk around the device plate, "3D object relocated")
    editor.optical_step_placement_offset_xyz = [0.0, 0.0, float(zmin)]
    editor.optical_step_axis_offset_xy = (
        -0.5 * (float(xmin) + float(xmax)),
        -0.5 * (float(ymin) + float(ymax)),
    )
    editor._sync_table()
    editor._write_layout_file(_P("attachment/om05a_folded_armA.py").resolve())
    editor.destroy()
    print("armA scene wired with the chunk")
