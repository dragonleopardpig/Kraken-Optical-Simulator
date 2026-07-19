"""Measure the OPT-CO90 coaxial module's two window openings straight from the vendor STEP.

Answers flags 20260719_142831 ("LED Botton view") / 20260719_142846 ("LED Front view"):
the module has two effective openings on the coaxial view axis and the Measure tool
cannot yet click edge-to-edge (bugs/0353), so this probe reads them from the CAD.

Method: the camera-side window is an INNER WIRE on its frame faces (direct read); the
emitting-side window is a stepped recess whose right edge is the interior wall ending
just below the top plate, so it is profiled with z-plane sections (crosshair clearance
about the window centre + top-plate rail extents).

Run:  .devenv/state/venv/bin/python bugs/diag_co90_window_openings.py \
          "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"
"""
import sys

import numpy as np

from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Section
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve, BRepAdaptor_Surface
from OCC.Core.GeomAbs import GeomAbs_Plane
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE, TopAbs_WIRE
from OCC.Core.TopoDS import topods
from OCC.Core.gp import gp_Dir, gp_Pln, gp_Pnt

try:
    from OCC.Core.BRepBndLib import brepbndlib

    def _bbox_add(shape, box):
        brepbndlib.Add(shape, box)
except Exception:  # older pythonocc spelling
    from OCC.Core.BRepBndLib import brepbndlib_Add

    def _bbox_add(shape, box):
        brepbndlib_Add(shape, box)

try:
    from OCC.Core.BRepTools import breptools

    def _outer_wire(face):
        return breptools.OuterWire(face)
except Exception:
    from OCC.Core.BRepTools import breptools_OuterWire

    def _outer_wire(face):
        return breptools_OuterWire(face)


def _extents(shape):
    box = Bnd_Box()
    _bbox_add(shape, box)
    return box.Get()


def load(path):
    reader = STEPControl_Reader()
    assert reader.ReadFile(path) == IFSelect_RetDone, f"STEP read failed: {path}"
    reader.TransferRoots()
    return reader.OneShape()


def inner_wire_windows(shape, min_span=15.0):
    """Planar faces carrying a large inner wire -> (normal, face lo/hi, opening lo/hi)."""
    hits = []
    fx = TopExp_Explorer(shape, TopAbs_FACE)
    while fx.More():
        face = topods.Face(fx.Current())
        fx.Next()
        surf = BRepAdaptor_Surface(face)
        if surf.GetType() != GeomAbs_Plane:
            continue
        try:
            ow = _outer_wire(face)
        except Exception:
            continue
        wx = TopExp_Explorer(face, TopAbs_WIRE)
        while wx.More():
            wire = topods.Wire(wx.Current())
            wx.Next()
            if wire.IsSame(ow):
                continue
            wx0, wy0, wz0, wx1, wy1, wz1 = _extents(wire)
            spans = sorted([wx1 - wx0, wy1 - wy0, wz1 - wz0])
            if spans[1] < min_span:
                continue
            n = surf.Plane().Axis().Direction()
            hits.append(
                {
                    "normal": (round(n.X(), 3), round(n.Y(), 3), round(n.Z(), 3)),
                    "face": _extents(face),
                    "open": (wx0, wy0, wz0, wx1, wy1, wz1),
                }
            )
    return hits


def section_points(shape, z, samples=40):
    pln = gp_Pln(gp_Pnt(0.0, 0.0, float(z)), gp_Dir(0.0, 0.0, 1.0))
    sec = BRepAlgoAPI_Section(shape, pln)
    sec.Build()
    pts = []
    ex = TopExp_Explorer(sec.Shape(), TopAbs_EDGE)
    while ex.More():
        edge = topods.Edge(ex.Current())
        ex.Next()
        try:
            curve = BRepAdaptor_Curve(edge)
            u0, u1 = curve.FirstParameter(), curve.LastParameter()
        except Exception:
            continue
        for u in np.linspace(u0, u1, samples):
            p = curve.Value(float(u))
            pts.append((p.X(), p.Y()))
    return np.asarray(pts, dtype=float) if pts else np.empty((0, 2))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "attachment/LED/OPT-CO90-X-V1.6.2-H.STEP"
    shape = load(path)
    x0, y0, z0, x1, y1, z1 = _extents(shape)
    print(f"module bbox: {x1-x0:.2f} x {y1-y0:.2f} x {z1-z0:.2f} mm  (z [{z0:.2f},{z1:.2f}])")

    windows = inner_wire_windows(shape)
    cam = [w for w in windows if abs(w["normal"][2]) == 1.0]
    print(f"\ncamera-side window (inner-wire frames, {len(cam)} faces):")
    for w in cam:
        ox0, oy0, oz0, ox1, oy1, oz1 = w["open"]
        print(
            f"  n={w['normal']} at z={oz0:.2f}: opening {ox1-ox0:.2f} x {oy1-oy0:.2f} mm"
            f"  (x [{ox0:.2f},{ox1:.2f}]  y [{oy0:.2f},{oy1:.2f}])"
        )
    if cam:
        ox0, oy0, _, ox1, oy1, _ = cam[0]["open"]
        cx, cy = 0.5 * (ox0 + ox1), 0.5 * (oy0 + oy1)
    else:
        cx, cy = 5.56, -1.37

    # emitting-side: interior tunnel walls (right edge) + top-plate rails (y + left edge)
    zs = np.arange(z0 + 6.0, z1 - 14.0, 1.0)
    right_wall = []
    for z in zs:
        pts = section_points(shape, z, samples=24)
        if pts.size == 0:
            continue
        dx = pts[:, 0] - cx
        on_x = np.abs(pts[:, 1] - cy) <= 3.0
        right = dx[on_x & (dx > 0)]
        if right.size:
            right_wall.append(cx + float(right.min()))
    right_edge = float(np.median(right_wall)) if right_wall else float("nan")

    plate = []
    for z in np.arange(z1 - 15.5, z1 - 12.0, 0.6):
        pts = section_points(shape, float(z), samples=60)
        if pts.size == 0:
            continue
        body = pts[pts[:, 0] > x0 + 15.0]
        inner = body[(body[:, 1] > y0 + 1.0) & (body[:, 1] < y1 - 1.0)]
        if inner.size == 0:
            continue
        # rails span the full width; sample them right of centre, clear of the left
        # connector shelf whose edge lines would otherwise masquerade as a rail
        rail_zone = inner[inner[:, 0] > cx]
        ys = rail_zone[:, 1]
        top = ys[ys > cy + 20.0]
        bot = ys[ys < cy - 20.0]
        mid = inner[(inner[:, 1] > cy - 20.0) & (inner[:, 1] < cy + 20.0)]
        left = mid[mid[:, 0] < cx][:, 0]
        # plate signature: the window's right frame edge sits BELOW the plate, so a true
        # top-plate section has no mid-band material right of centre; wall-bearing slices do.
        if mid[mid[:, 0] > cx + 5.0].size:
            continue
        if top.size and bot.size and left.size:
            plate.append((float(left.max()), float(bot.max()), float(top.min())))
    if plate:
        left_edge = float(np.median([p[0] for p in plate]))
        rail_lo = float(np.median([p[1] for p in plate]))
        rail_hi = float(np.median([p[2] for p in plate]))
        print(
            f"\nemitting-side window (stepped recess):"
            f"\n  x [{left_edge:.2f},{right_edge:.2f}] = {right_edge-left_edge:.2f} mm"
            f"   y [{rail_lo:.2f},{rail_hi:.2f}] = {rail_hi-rail_lo:.2f} mm"
        )
    else:
        print("\nemitting-side window: top-plate rails not resolved")


if __name__ == "__main__":
    main()
