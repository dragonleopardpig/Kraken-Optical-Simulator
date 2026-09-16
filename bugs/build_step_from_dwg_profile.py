"""Build a STEP body from a vendor DWG's own dimensioned profile (bugs/0794).

A vendor who ships a drawing but no STEP leaves the importer without the one thing several
algorithms measure against: a body. The clearance clamp has nothing to clear, bugs/0656's
working-distance placement has no rim to measure to, and the scene draws no lens.

The drawing already states the barrel, though, in entities that carry both a value and the two
points it spans. On the SPO TCL4.0X-65DI-5M every dimension is 1:1 mm:

    axis            y = 184.5     (all three radial dimensions centre on it)
    front rim       x = 181.82    rear face x = 324.30    ->  142.482 mm long
    0 .. 54.90      diameter 31   (the 31.000 dimension sits at x = 213.06)
    54.90 .. 66.50  diameter 34   (34.000 at x = 247.82)
    66.50 .. 142.48 diameter 30   (30.000 at x = 323.80)
    coaxial port    diameter 16, centred 45.56 mm from the rim, standing 20.5 mm proud

54.90 + 11.60 + 75.98 = 142.48 -- the bands close on the total exactly, which is the check that
the bands were read correctly rather than guessed.

This is a MECHANICAL ENVELOPE, not the vendor's CAD: it is what the drawing dimensions, and it is
labelled as such in the STEP product name so nobody mistakes it for the real part. Replace it the
moment the vendor's own STEP arrives.

Usage:
    .devenv/state/venv/bin/python bugs/build_step_from_dwg_profile.py <drawing.dwg> [out.step]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from KrakenOS.UI.services.dwg_spec_import import dwg_available  # noqa: E402

AXIS_TOL_MM = 0.5


def read_dimensions(path: Path) -> list[dict]:
    """Every linear dimension as ``{value, p1, p2, axial}``; [] when libredwg is absent."""
    import json
    import subprocess
    import tempfile

    if not dwg_available():
        return []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "d.json"
        subprocess.run(["dwgread", "-O", "JSON", "-o", str(out), str(path)],
                       check=True, capture_output=True, timeout=180)
        payload = json.loads(out.read_text(encoding="utf-8", errors="replace"))
    dims = []
    for obj in payload.get("OBJECTS", []) or []:
        if not isinstance(obj, dict) or not str(obj.get("entity", "")).startswith("DIMENSION"):
            continue
        p1, p2 = obj.get("xline1_pt"), obj.get("xline2_pt")
        value = obj.get("act_measurement")
        if not (isinstance(p1, list) and isinstance(p2, list) and value):
            continue
        dims.append({
            "value": float(value), "p1": [float(v) for v in p1[:2]], "p2": [float(v) for v in p2[:2]],
            "axial": abs(p1[0] - p2[0]) > abs(p1[1] - p2[1]),
        })
    return dims


def profile_from_dimensions(dims: list[dict]) -> dict:
    """The barrel as ``{axis_y, front_x, length, bands:[(start, end, diameter)], port}``.

    Derived, not assumed, and deliberately conservative about WHICH dimensions describe the
    profile:

    * the axis is where the radial dimensions centre;
    * the body is the LONGEST axial dimension, giving the rim and the total length;
    * **each on-axis radial dimension marks one band**, at its own x station -- that is what a
      diameter callout means -- and the bands are ordered by station;
    * the boundary between two adjacent bands is the axial-dimension ENDPOINT that falls between
      their stations. Nothing else may cut the profile, which is what keeps a reference dimension
      (the drawing's parenthesised 45.561 to the illumination port) from inventing a step.

    The bands must close on the total length, or this raises rather than guessing.
    """
    radial = [d for d in dims if not d["axial"]]
    axial = [d for d in dims if d["axial"]]
    if not radial or not axial:
        raise ValueError("drawing carries no usable radial/axial dimension pair")
    centres = [(d["p1"][1] + d["p2"][1]) / 2.0 for d in radial]
    axis_y = sorted(centres)[len(centres) // 2]
    diameters = [d for d in radial if abs((d["p1"][1] + d["p2"][1]) / 2.0 - axis_y) <= AXIS_TOL_MM]
    if not diameters:
        raise ValueError("no radial dimension centres on the axis")
    body = max(axial, key=lambda d: d["value"])
    front_x = min(body["p1"][0], body["p2"][0])
    rear_x = max(body["p1"][0], body["p2"][0])
    length = float(body["value"])

    stations = sorted(((d["p1"][0] + d["p2"][0]) / 2.0, float(d["value"])) for d in diameters)

    # Find the coaxial port BEFORE the bands, because its own dimensions must not cut the
    # profile: the drawing's parenthesised reference to the port centre sits between the 31 and
    # 34 callouts and, taken as a step, moved the first band from 54.900 to 45.561.
    port = None
    off_axis = [d for d in radial if d not in diameters]
    if off_axis:
        stand = max(off_axis, key=lambda d: d["value"])
        centre = (stand["p1"][0] + stand["p2"][0]) / 2.0
        bores = [d for d in axial if d is not body and d["value"] < 30.0
                 and min(d["p1"][0], d["p2"][0]) <= centre + 12.0
                 and max(d["p1"][0], d["p2"][0]) >= centre - 12.0]
        if bores:
            bore = min(bores, key=lambda d: d["value"])
            port = {"diameter": float(bore["value"]),
                    "stand": float(stand["value"]),
                    "station": float((bore["p1"][0] + bore["p2"][0]) / 2.0 - front_x)}

    def _is_port_endpoint(x: float) -> bool:
        if not port:
            return False
        return abs(x - (front_x + port["station"])) <= port["diameter"] / 2.0 + 1e-6

    endpoints = sorted({point[0] for d in axial if d is not body for point in (d["p1"], d["p2"])
                        if front_x + 1e-6 < point[0] < rear_x - 1e-6
                        and not _is_port_endpoint(point[0])})
    edges = [front_x]
    for (x_left, _d_left), (x_right, _d_right) in zip(stations, stations[1:]):
        between = [x for x in endpoints if x_left < x < x_right]
        if not between:
            raise ValueError(f"no boundary dimension between the {_d_left:g} and {_d_right:g} bands")
        # the endpoint nearest the midpoint of the two callouts is the step they share
        edges.append(min(between, key=lambda x: abs(x - (x_left + x_right) / 2.0)))
    edges.append(rear_x)
    bands = [(round(a - front_x, 4), round(b - front_x, 4), diameter)
             for (a, b), (_x, diameter) in zip(zip(edges, edges[1:]), stations)]
    if abs(sum(e - s for s, e, _d in bands) - length) > 1e-4:
        raise ValueError("bands do not close on the body length")

    return {"axis_y": axis_y, "front_x": front_x, "rear_x": rear_x,
            "length": length, "bands": bands, "port": port}


def build_step(profile: dict, destination: Path, label: str) -> Path:
    """Revolve the bands about +Z and add the port; write a STEP."""
    from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeCylinder
    from OCC.Core.gp import gp_Ax2, gp_Dir, gp_Pnt
    from OCC.Core.Interface import Interface_Static
    from OCC.Core.STEPControl import STEPControl_AsIs, STEPControl_Writer

    shape = None
    for start, end, diameter in profile["bands"]:
        axis = gp_Ax2(gp_Pnt(0.0, 0.0, float(start)), gp_Dir(0.0, 0.0, 1.0))
        band = BRepPrimAPI_MakeCylinder(axis, float(diameter) / 2.0, float(end - start)).Shape()
        shape = band if shape is None else BRepAlgoAPI_Fuse(shape, band).Shape()
    port = profile.get("port")
    if port:
        radius = float(port["diameter"]) / 2.0
        # start inside the barrel so the fuse is watertight, run out to the drawn stand-off
        base_r = max(d for _s, _e, d in profile["bands"]) / 2.0
        axis = gp_Ax2(gp_Pnt(0.0, 0.0, float(port["station"])), gp_Dir(0.0, 1.0, 0.0))
        tower = BRepPrimAPI_MakeCylinder(axis, radius, base_r + float(port["stand"])).Shape()
        shape = BRepAlgoAPI_Fuse(shape, tower).Shape()
    Interface_Static.SetCVal("write.step.product.name", label)
    writer = STEPControl_Writer()
    writer.Transfer(shape, STEPControl_AsIs)
    if writer.Write(str(destination)) != 1:
        raise RuntimeError("STEP write failed")
    return destination


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    drawing = Path(argv[0])
    destination = Path(argv[1]) if len(argv) > 1 else drawing.with_suffix(".envelope.step")
    dims = read_dimensions(drawing)
    if not dims:
        print("no dimensions read (is libredwg's dwgread on PATH?)")
        return 1
    profile = profile_from_dimensions(dims)
    print(f"axis y {profile['axis_y']:.3f}   front x {profile['front_x']:.3f}   "
          f"length {profile['length']:.3f} mm")
    for start, end, diameter in profile["bands"]:
        print(f"   {start:8.3f} .. {end:8.3f} mm   diameter {diameter:6.2f}")
    if profile.get("port"):
        p = profile["port"]
        print(f"   port diameter {p['diameter']:.2f} standing {p['stand']:.2f} at {p['station']:.2f} mm")
    out = build_step(profile, destination, f"{drawing.stem} mechanical envelope (from the drawing)")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
