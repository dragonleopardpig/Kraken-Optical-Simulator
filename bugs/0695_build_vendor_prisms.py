"""0695: generate VENDOR-EXACT prism solids for om05a (root cause of 0694).

Vendor truth (OPT-ILS8275 STEP, z=0 section, vendor frame; see
bugs/0695_vendor_section.png and the extracted vertices):
  first RA mirror bar : legs 9.8 (x 29.1..38.9) x 9.9 (y 20.9..30.8), hyp 45
                        facing up-inward; 60 long
  cube BS near half   : legs 13.5 (x 25.5..39.0) x 13.5 (y 7.0..20.5), hyp from
                        (25.5,7.0) to (39.0,20.5) facing down-outward; 60 long
  cube BS far half    : the complementary triangle (NOT in the vendor CAD --
                        synthesized; plain glass, completes the cube for the LED)
  centre prism (ONE)  : apex-down V, corners (+-11.892, 18.192), apex (0, 6.30);
                        60 long; modeled as two back-to-back half prisms so each
                        arm keeps its own Mirror row
  LED panel           : 18.1 x 1.6 x 75 flat at y -1.6..0 under each tower
  device              : faces at vendor x +-25, beam height y_d (calibrated
                        against the scene's proven face-A fold: gap 8.78 ->
                        y_d = 59.8 - (25 + 8.78) = 26.02)

Scene mapping (side A; side B mirrors across the z=-25 split line):
  scene_z = vendor_x - 25          (face A at z=0 looks toward +z)
  scene_y = 0.25 + (26.02 - vendor_y)
  scene_x = vendor_z               (the 60/75-long bar axis)

Writes STEPs into attachment/om05a_components/ (prefix 0695v) + a manifest of
scene-frame centres. The scene stamp is a separate script.
"""
import json
from pathlib import Path

from OCC.Core.BRepBuilderAPI import (
    BRepBuilderAPI_MakeEdge,
    BRepBuilderAPI_MakeFace,
    BRepBuilderAPI_MakeWire,
)
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCC.Core.gp import gp_Pnt, gp_Vec
from OCC.Core.Interface import Interface_Static
from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer

OUT = Path("attachment/om05a_components")
Y_D = 26.02          # vendor beam height of the device plane (calibrated)
FACE_Y = 0.25        # scene y of the device mid-plane
BAR_LEN = 60.0       # optical bars run vendor z +-30 -> scene x +-30
SPLIT = -25.0        # scene split line


def scene_pt(vx, vy):
    """vendor (x, y) -> scene (z, y) for side A."""
    return vx - 25.0, FACE_Y + (Y_D - vy)


def mirror_b(z):
    return 2.0 * SPLIT - z


def extruded_solid(profile_zy, length=BAR_LEN):
    """Extrude a scene-frame (z, y) polygon along scene x, LOCAL-CENTRED about its
    bbox centre (the promotion convention: mesh local, pose in the manifest --
    the first build authored absolute world meshes and every face landed
    displaced: 0/3249 reach, the 0684 'wrong fold face = Fresnel splitter'
    signature). Returns (shape, bbox_centre_world)."""
    zs = [z for z, _ in profile_zy]
    ys = [y for _, y in profile_zy]
    cz = 0.5 * (min(zs) + max(zs))
    cy = 0.5 * (min(ys) + max(ys))
    pts = [gp_Pnt(-length / 2.0, y - cy, z - cz) for (z, y) in profile_zy]
    wire = BRepBuilderAPI_MakeWire()
    for a, b in zip(pts, pts[1:] + pts[:1]):
        wire.Add(BRepBuilderAPI_MakeEdge(a, b).Edge())
    face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(length, 0.0, 0.0)).Shape(), (0.0, cy, cz)


def save_step(shape, name):
    Interface_Static.SetCVal("write.step.schema", "AP214")
    w = STEPControl_Writer()
    w.Transfer(shape, STEPControl_AsIs)
    path = OUT / name
    w.Write(str(path))
    assert path.exists()
    return path


def main():
    manifest = {}

    def emit(name, profile, side):
        prof = profile if side == "A" else [(mirror_b(z), y) for (z, y) in profile]
        shape, (cx, cy, cz) = extruded_solid(prof)
        save_step(shape, f"{name}_{side}_0695v.step")
        manifest[f"{name}_{side}_0695v"] = [0.0, round(cy, 4), round(cz, 4)]
        print(f"{name}_{side}: profile {[(round(z,2), round(y,2)) for z, y in prof]}")

    # first RA mirror bar: FIRST-SURFACE (the vendor CAD models a ~0.17 mm^2
    # section thin plate on this plane; the user calls it a MIRROR) -- hyp
    # exposed to the beam, glass BEHIND it (right angle at the outer corner),
    # so neither the face leg nor the down-tower leg crosses glass.
    ra = [scene_pt(29.1, 30.8), scene_pt(38.9, 20.9), scene_pt(38.9, 30.8)]
    emit("ra_mirror", ra, "A")
    emit("ra_mirror", ra, "B")

    # cube BS near half: vendor (25.5,7.0)-(25.5,20.5)-(39.0,20.5); hypotenuse
    # (25.5,7.0)-(39.0,20.5) carries the 50/50 coating
    bs_near = [scene_pt(25.5, 7.0), scene_pt(25.5, 20.5), scene_pt(39.0, 20.5)]
    emit("bs_near", bs_near, "A")
    emit("bs_near", bs_near, "B")

    # cube BS far half (synthesized): (25.5,7.0)-(39.0,7.0)-(39.0,20.5), with the
    # hyp edge pulled 0.1 mm off the coated plane (cement gap) -- EXACTLY coplanar
    # meshes coin-flip which face a crossing ray interacts with (measured: 2-5
    # vertex spread INSIDE single field cones, 0.8-1.3 mm waists).
    g = 0.1 / (2 ** 0.5)
    bs_far = [(scene_pt(25.5, 7.0)[0] + g, scene_pt(25.5, 7.0)[1] + g),
              scene_pt(39.0, 7.0),
              (scene_pt(39.0, 20.5)[0] + g, scene_pt(39.0, 20.5)[1] + g)]
    emit("bs_far", bs_far, "A")
    emit("bs_far", bs_far, "B")

    # centre prism half (side A = the half toward face A): vendor corners
    # (11.892,18.192) (apex 0,6.30) (0,18.192); the back face pulled 0.05 mm off
    # the split line so the two halves never share a coplanar face.
    centre = [scene_pt(11.892, 18.192), scene_pt(0.05, 6.30 + 0.05), scene_pt(0.05, 18.192)]
    emit("centre_half", centre, "A")
    emit("centre_half", centre, "B")

    # LED panel: vendor x 20.9..39.0, y -1.6..0 (flat, dies up in vendor = the
    # scene face the diffuser side; drawn as a thin slab, 75 long)
    led = [scene_pt(20.9, 0.0), scene_pt(39.0, 0.0), scene_pt(39.0, -1.6), scene_pt(20.9, -1.6)]
    for side in ("A", "B"):
        prof = led if side == "A" else [(mirror_b(z), y) for (z, y) in led]
        shape, (cx, cy, cz) = extruded_solid(prof, length=75.0)
        save_step(shape, f"led_panel_{side}_0695v.step")
        manifest[f"led_panel_{side}_0695v"] = [0.0, round(cy, 4), round(cz, 4)]

    (OUT / "manifest_0695v.json").write_text(json.dumps(manifest, indent=1))
    print("manifest:", json.dumps(manifest, indent=1))


if __name__ == "__main__":
    main()
