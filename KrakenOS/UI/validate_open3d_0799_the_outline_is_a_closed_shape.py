"""bugs/0799 -- the DXF outline is a CLOSED shape, computed not assembled.

bugs/0798 halved the fragmentation but left the drawing with no closed shapes at all: not one
polyline carried the DXF closed flag, and a body's profile arrived as several chains ending a
median 1.38 mm apart.

The measurements said the assembly approach could not get there. Stitching the raw silhouette
and feature edges walks a connected graph whose vertices have degree > 2 (T-junctions, and one
contour per silhouette pass), so a greedy walk cannot know which incident edge continues a
profile: merge-then-stitch fragmented a bucket into 120 chains, and stitch-then-dedupe produced
2 giant chains carrying 129386 mm of line for 46156 mm of unique geometry.

A silhouette does not have to be assembled. Project every triangle into the view plane and take
the BOOLEAN UNION -- its boundary IS the outline, closed by construction, one exterior ring per
body and one interior ring per through-hole.

Display-free: synthetic meshes, no window, no rendering.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from KrakenOS.UI.services.dxf_viewport_export import (  # noqa: E402
    _postprocess_layer_polylines,
    _strips_not_already_drawn,
    mesh_outline_polygons,
    write_dxf_r12,
)


def _ring_area(ring: np.ndarray, axis_a: int = 0, axis_b: int = 1) -> float:
    a = np.asarray(ring, float)
    x, y = a[:, axis_a], a[:, axis_b]
    return abs(float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1])) / 2.0)


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    import pyvista as pv

    # ---- A: a solid body projects to ONE closed ring of the right area ---------------------
    box = pv.Box(bounds=(-10.0, 10.0, -5.0, 5.0, -2.0, 2.0)).triangulate()
    rings = mesh_outline_polygons(box, view_direction=(0.0, 0.0, 1.0))
    ok(len(rings) == 1, f"A: a box gives ONE outline ring ({len(rings)})")
    if rings:
        ring = rings[0]
        ok(bool(np.allclose(ring[0], ring[-1])),
           "A: and it is CLOSED -- its first vertex repeats as its last")
        ok(abs(_ring_area(ring) - 20.0 * 10.0) < 1.0,
           f"A: its area is the projected footprint ({_ring_area(ring):.2f} vs 200.0)")

    # viewed along a different axis the footprint changes accordingly
    rings_side = mesh_outline_polygons(box, view_direction=(1.0, 0.0, 0.0))
    ok(len(rings_side) == 1 and abs(_ring_area(rings_side[0], 1, 2) - 10.0 * 4.0) < 1.0,
       "A: viewed along +X the same box gives its 10 x 4 side footprint")

    # ---- B: a through-hole becomes an INTERIOR ring ----------------------------------------
    plate = pv.Box(bounds=(-10.0, 10.0, -10.0, 10.0, -1.0, 1.0)).triangulate()
    hole = pv.Cylinder(center=(0.0, 0.0, 0.0), direction=(0.0, 0.0, 1.0),
                       radius=3.0, height=6.0, resolution=48).triangulate()
    drilled = plate.boolean_difference(hole).triangulate()
    drilled_rings = mesh_outline_polygons(drilled, view_direction=(0.0, 0.0, 1.0))
    ok(len(drilled_rings) >= 2,
       f"B: a drilled plate gives an exterior AND an interior ring ({len(drilled_rings)})")
    if len(drilled_rings) >= 2:
        areas = sorted(_ring_area(r) for r in drilled_rings)
        ok(all(bool(np.allclose(r[0], r[-1])) for r in drilled_rings),
           "B: every ring is closed")
        ok(abs(areas[-1] - 400.0) < 5.0 and abs(areas[0] - np.pi * 9.0) < 3.0,
           f"B: the rings are the 20x20 plate and the r=3 hole "
           f"({areas[-1]:.1f} and {areas[0]:.1f})")

    # ---- C: an empty or absurd input is refused quietly -------------------------------------
    ok(mesh_outline_polygons(pv.PolyData(), view_direction=(0, 0, 1)) == [],
       "C: empty geometry yields no rings rather than raising")
    ok(mesh_outline_polygons(box, view_direction=(0, 0, 1), max_polys=1) == [],
       "C: a mesh past max_polys is skipped, as the strip path skips it")

    # ---- D: the post-process hands a closed ring straight through ----------------------------
    ring2d = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 6.0], [0.0, 6.0], [0.0, 0.0]])
    processed = _postprocess_layer_polylines(
        [{"points": ring2d, "color": None, "closed": True}], decompose=True)
    ok(len(processed) == 1 and processed[0].get("closed"),
       "D: a closed ring survives the body post-process intact (it is not decomposed and "
       "re-stitched by the walk that could not close it)")
    if processed:
        ok(np.allclose(np.asarray(processed[0]["points"], float), ring2d),
           "D: and its vertices are untouched")

    # ---- E: the writer says CLOSED in the file ----------------------------------------------
    with tempfile.TemporaryDirectory(prefix="kraken0799_") as tmp:
        out = Path(tmp) / "probe.dxf"
        write_dxf_r12(out, {"KRAKEN_BODIES": {"polylines": [
            {"points": ring2d, "color": None, "closed": True},
            {"points": np.array([[0.0, 0.0], [5.0, 5.0]]), "color": None},
        ]}})
        text = out.read_text(encoding="utf-8").splitlines()
        flags, vertices = [], 0
        for i in range(len(text) - 1):
            if text[i].strip() == "0" and text[i + 1].strip() == "POLYLINE":
                for j in range(i, min(i + 14, len(text) - 1)):
                    if text[j].strip() == "70":
                        flags.append(int(text[j + 1]))
                        break
            if text[i].strip() == "0" and text[i + 1].strip() == "VERTEX":
                vertices += 1
        ok(flags.count(1) == 1 and flags.count(0) == 1,
           f"E: exactly the closed ring carries group 70 bit 1 ({flags})")
        ok(vertices == 6,
           f"E: the closed ring drops its repeated vertex (4 + 2 = {vertices} written)")

    # ---- F: the coverage test samples a SPARSE reference ------------------------------------
    # An outline ring is a handful of long edges; a fragment lying on it is far from any
    # reference VERTEX, so the test has to sample along the reference.
    sparse = [np.array([[0.0, 0.0], [100.0, 0.0]])]
    mid = np.array([[40.0, 0.0], [60.0, 0.0]])
    off = np.array([[40.0, 9.0], [60.0, 9.0]])
    ok(_strips_not_already_drawn([mid], sparse) == [],
       "F: a fragment lying mid-edge of a sparse ring is recognised as already drawn")
    ok(len(_strips_not_already_drawn([off], sparse)) == 1,
       "F: a fragment genuinely off the ring is kept")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0799 closed-outline validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
