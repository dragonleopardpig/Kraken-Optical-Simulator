#!/usr/bin/env python3
"""Display-free guard for bugs/0249: the Open 3D navigation cube is a FreeCAD-style
CHAMFERED cube whose 26 flat facets (6 faces, 12 bevelled edges, 8 cut corners) map
one-to-one onto the 26 camera orientations, so a picked facet CELL is a direct
sign-triple lookup (no hit-point threshold).

Why it exists (user flag 2026-07-07):
  "the text in the cube is too big. The color of the cube for each surface has low
   contrast difference. The edge if can be clicked, should be 'chamfered'. If corner
   can be clicked, chamfered it as well."

The visual half (smaller labels, per-kind colours, curved roll arrows) is eyeballed
from an offscreen render; THIS guard pins the pure geometry + the widget wiring that
makes the chamfer clickable, so a future edit can't silently break the facet<->sign
contract or fall back to the old opaque-unit-cube picking.

What it checks (no display required):
  A. chamfered_cube_facets(0.5, ...) yields exactly 48 shared vertices and 26 facets,
     shaped like FreeCAD's cube: 6 face OCTAGONS, 12 edge RECTANGLES, 8 corner HEXAGONS
     (bugs/0253 -- the corners are cut into big clickable hexagons, not small triangles).
  B. The facets partition into 6 faces + 12 edges + 8 corners by orientation kind.
  C. The 26 facet signs are exactly the 26 ORIENTATION_KEYS -- every orientation is
     covered once, none duplicated.
  D. Every facet is wound so its polygon normal points OUTWARD (normal . sign > 0),
     so back-face culling / lighting behave and the pick normal is meaningful.
  E. Every facet is planar (a genuine flat facet, not a warped quad).
  F. Every facet CENTROID classifies (classify_pick) back to the facet's own sign --
     the cell-id lookup agrees with the geometric orientation of the facet.
  G. The six FACE facets still reproduce the cardinal toolbar presets exactly
     (orientation_pose(face_sign) == _FACE_POSE[face_sign]).
  H. Source contract on nav_cube_widget: it builds self._cell_signs from
     chamfered_cube_facets, resolves a pick by GetCellId() -> self._cell_signs, and
     uses the curved _roll_arrow_actor for BOTH roll handles.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_nav_cube_geometry

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    ORIENTATION_KEYS,
    _FACE_POSE,
    chamfered_cube_facets,
    classify_pick,
    orientation_kind,
    orientation_pose,
)

_FACE_FRACTION = 0.74    # must match nav_cube_widget._FACE_FRACTION
_CORNER_FRACTION = 0.44  # must match nav_cube_widget._CORNER_FRACTION (bugs/0253)

# FreeCAD-style facet shapes: a face is an octagon, an edge a rectangle, a corner a hexagon.
_KIND_SIDES = {"face": 8, "edge": 4, "corner": 6}


def _newell(points, idxs) -> np.ndarray:
    n = np.zeros(3)
    m = len(idxs)
    for i in range(m):
        a = np.asarray(points[idxs[i]], dtype=float)
        b = np.asarray(points[idxs[(i + 1) % m]], dtype=float)
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []
    points, facets = chamfered_cube_facets(
        half=0.5, face_fraction=_FACE_FRACTION, corner_fraction=_CORNER_FRACTION
    )

    # --- A: 48 vertices, 26 facets, FreeCAD facet shapes (8 / 4 / 6) ---------------
    if len(points) != 48:
        failures.append(f"A FAIL: expected 48 shared vertices, got {len(points)}")
    if len(facets) != 26:
        failures.append(f"A FAIL: expected 26 facets, got {len(facets)}")
    for idxs, sign in facets:
        kind = orientation_kind(sign)
        want_sides = _KIND_SIDES.get(kind)
        if want_sides is not None and len(idxs) != want_sides:
            failures.append(
                f"A FAIL: {kind} facet {tuple(int(s) for s in sign)} has {len(idxs)} sides, "
                f"expected {want_sides} (face=octagon, edge=rectangle, corner=hexagon)"
            )

    # --- B: 6 faces + 12 edges + 8 corners ----------------------------------------
    kinds = {"face": 0, "edge": 0, "corner": 0, "none": 0}
    for _idxs, sign in facets:
        kinds[orientation_kind(sign)] += 1
    if (kinds["face"], kinds["edge"], kinds["corner"]) != (6, 12, 8):
        failures.append(
            f"B FAIL: partition is {kinds} -- expected 6 face / 12 edge / 8 corner"
        )

    # --- C: signs == the 26 orientation keys, no dup ------------------------------
    signs = [tuple(int(s) for s in sign) for _idxs, sign in facets]
    if len(set(signs)) != len(signs):
        failures.append("C FAIL: duplicate facet signs -- two facets share an orientation")
    if set(signs) != set(ORIENTATION_KEYS):
        missing = set(ORIENTATION_KEYS) - set(signs)
        extra = set(signs) - set(ORIENTATION_KEYS)
        failures.append(f"C FAIL: facet signs != ORIENTATION_KEYS (missing={missing}, extra={extra})")

    # --- D: outward winding, E: planar, F: centroid self-classifies ---------------
    for idxs, sign in facets:
        s = np.asarray(sign, dtype=float)
        normal = _newell(points, idxs)
        nn = float(np.linalg.norm(normal))
        if nn <= 1e-9:
            failures.append(f"D FAIL: degenerate facet {sign} (zero-area)")
            continue
        if float(np.dot(normal, s)) <= 0.0:
            failures.append(f"D FAIL: facet {sign} wound inward (normal . sign <= 0)")
        unit = normal / nn
        verts = np.array([points[i] for i in idxs], dtype=float)
        centroid = verts.mean(axis=0)
        planar_err = float(np.max(np.abs((verts - centroid) @ unit)))
        if planar_err > 1e-6:
            failures.append(f"E FAIL: facet {sign} non-planar (max out-of-plane {planar_err:.2e})")
        classified = classify_pick(centroid)
        if classified != tuple(int(s) for s in sign):
            failures.append(
                f"F FAIL: facet {sign} centroid classifies to {classified} -- pick would snap "
                "to the wrong orientation"
            )

    # --- G: face facets still equal the cardinal presets --------------------------
    for _idxs, sign in facets:
        key = tuple(int(s) for s in sign)
        if orientation_kind(key) != "face":
            continue
        got_offset, got_up = orientation_pose(key)
        want_offset, want_up = _FACE_POSE[key]
        if not (np.allclose(got_offset, want_offset) and np.allclose(got_up, want_up)):
            failures.append(
                f"G FAIL: face {key} pose {got_offset, got_up} != preset {want_offset, want_up}"
            )

    # --- H: widget wiring source contract -----------------------------------------
    try:
        from KrakenOS.UI.services import nav_cube_widget as W

        build_src = inspect.getsource(W.NavigationCube._build_chamfered_actor)
        if "chamfered_cube_facets(" not in build_src or "self._cell_signs" not in build_src:
            failures.append(
                "H FAIL: _build_chamfered_actor no longer builds self._cell_signs from "
                "chamfered_cube_facets -- the chamfer mesh / pick table is gone"
            )
        press_src = inspect.getsource(W.NavigationCube.handle_left_press)
        if "GetCellId()" not in press_src or "self._cell_signs[" not in press_src:
            failures.append(
                "H FAIL: handle_left_press no longer resolves a pick by GetCellId() -> "
                "self._cell_signs -- reverted to hit-point-only picking"
            )
        arrow_src = inspect.getsource(W.NavigationCube._build_arrow_renderer)
        if "_roll_arrow_actor(" not in arrow_src:
            failures.append(
                "H FAIL: the roll handles are not built with the curved _roll_arrow_actor"
            )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"H FAIL: could not inspect nav_cube_widget wiring: {exc!r}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0249 nav-cube chamfer geometry")
        for item in failures:
            print(f"  - {item}")
        return 1
    print(
        "[PASS] bugs/0249: the nav cube is a 26-facet chamfered cube (6/12/8), every facet maps "
        "to a distinct orientation, faces still equal the cardinal presets, and the widget picks "
        "by cell id with curved roll arrows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
