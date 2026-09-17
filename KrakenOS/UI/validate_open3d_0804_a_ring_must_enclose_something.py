"""bugs/0804 -- an outline ring must enclose something.

User, on attachment/Scene_DXF.png: stray broken lines still inside the lens taper of the scene
export -- while the lens and camera six-view sheets were clean.

Measured on the user's own file (MV-CH120-60UM_WWK10-110CP-111V3_view.dxf): of 24 closed rings,
**18 enclosed exactly zero area** -- collinear 3-4 point "rings" traced out and back. Reproducing
the export in the same -yz view gave 302 body polylines and 24 closed rings, matching the file, and
tagged the source: bugs/0799's outline union emitted 21 rings, 18 of them zero-area; the writer's
ends-meet rule contributed none.

Why: seen from the side the tapered flank's triangles are nearly edge-on, and simplifying their
union at simplify_tol collapses thin slivers into collinear points. Being CLOSED they were passed
through whole by hidden-line removal and the post-process (bugs/0802, 0799), so they drew.

Why the six-view sheets were clean: only the viewport collector calls mesh_outline_polygons.

Display-free: synthetic meshes, no app.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.services.dxf_viewport_export import mesh_outline_polygons  # noqa: E402

VIEW = (0.0, 0.0, 1.0)


def _mesh(*quads):
    """A polydata made of flat quads in the z=0 plane, each given as (x0, x1, y0, y1)."""
    import pyvista as pv

    points, faces = [], []
    for x0, x1, y0, y1 in quads:
        base = len(points)
        points += [[x0, y0, 0.0], [x1, y0, 0.0], [x1, y1, 0.0], [x0, y1, 0.0]]
        faces += [3, base, base + 1, base + 2, 3, base, base + 2, base + 3]
    return pv.PolyData(np.asarray(points, float), np.asarray(faces, np.int64))


def _width(ring) -> float:
    a = np.asarray(ring, float)
    c = a - a.mean(axis=0)
    _u, _s, vt = np.linalg.svd(c, full_matrices=False)
    uv = c @ vt[:2].T
    uv = np.vstack([uv, uv[:1]])
    area = abs(float(np.sum(uv[:-1, 0] * uv[1:, 1] - uv[1:, 0] * uv[:-1, 1]))) / 2.0
    perimeter = float(np.sum(np.linalg.norm(np.diff(uv, axis=0), axis=1)))
    return 2.0 * area / perimeter if perimeter > 0 else 0.0


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: a sliver thinner than the simplify tolerance is not a shape ---------------------
    sliver = _mesh((50.0, 60.0, 0.0, 0.005))                 # 10 mm x 5 um
    rings = mesh_outline_polygons(sliver, VIEW, simplify_tol=0.02)
    ok(rings == [],
       f"A: a 5 um sliver under a 20 um simplify tolerance yields no ring ({len(rings)}) -- the "
       "zero-area 'rings' that drew as stray lines in the lens taper")

    # ---- B: a thin but REAL shape survives ---------------------------------------------------
    strip = _mesh((50.0, 60.0, 0.0, 1.0))                    # 10 mm x 1 mm
    rings = mesh_outline_polygons(strip, VIEW, simplify_tol=0.02)
    ok(len(rings) == 1 and _width(rings[0]) > 0.4,
       f"B: a 1 mm strip is kept ({len(rings)} ring, mean width "
       f"{_width(rings[0]) if rings else 0.0:.3f} mm)")

    # ---- C: in one mesh the body survives and only the sliver goes --------------------------
    both = _mesh((0.0, 20.0, 0.0, 10.0), (50.0, 60.0, 0.0, 0.005))
    rings = mesh_outline_polygons(both, VIEW, simplify_tol=0.02)
    ok(len(rings) == 1 and _width(rings[0]) > 4.0,
       f"C: a body plus a detached sliver gives only the body's ring ({len(rings)})")

    # ---- D: every ring emitted encloses something ---------------------------------------------
    import pyvista as pv

    cone = pv.Cone(center=(0.0, 0.0, 0.0), direction=(1.0, 0.0, 0.0), height=20.0,
                   radius=8.0, resolution=64).triangulate()
    side = mesh_outline_polygons(cone, (0.0, 1.0, 0.0), simplify_tol=0.02)
    widths = [_width(r) for r in side]
    ok(bool(side) and min(widths) >= 0.02,
       f"D: a cone seen from the SIDE -- the case whose edge-on flank made the slivers -- emits "
       f"only rings wider than the tolerance ({len(side)} rings, narrowest "
       f"{min(widths) if widths else 0.0:.3f} mm)")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0804 ring-encloses-something validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
