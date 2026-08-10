#!/usr/bin/env python3
"""Display-free guard for bugs/0253: the navigation cube matches FreeCAD's look -- the
corners are big clickable HEXAGONS (not small triangles) and the two orange roll handles are
big arcs CONCENTRIC with the cube (not small "ears" perched on top).

Why it exists (user flags 2026-07-08):
  1. "the 2 orange rotation arrows ... look like 'ears', a bit awkward. Can make them look
     like [FreeCAD]? ... the arrow segment align with the 'Top' edge. The 2 arrows located at
     the middle of the Up and Left/Right arrow."
  2. "The Corner is triangle, can make them same as [FreeCAD] hexagonal style? It is bigger,
     easier to click."

The fix cuts each cube corner into a hexagon (so each face becomes an octagon and each edge a
rectangle -- FreeCAD's chamfered cube) and rebuilds the roll handles as big origin-centred arcs
that flank the Up arrow. The exact camera framing / arrow feel is eyeballed from an offscreen
render; THIS guard pins the pure geometry + the widget wiring so a future edit can't silently
revert the shape.

What it checks (no display required, pure math + source contract):
  A. Facet shapes are FreeCAD's: 6 face OCTAGONS (8 sides), 12 edge RECTANGLES (4), 8 corner
     HEXAGONS (6); still 26 facets over 48 shared vertices.
  B. Each corner hexagon's 6 vertices are exactly the signed permutations of the magnitudes
     ``(half, p, q)`` -- the canonical FreeCAD corner cut -- planar and wound outward.
  C. The corner facet is materially BIGGER than the legacy triangle cut would be (the "bigger,
     easier to click" ask): hexagon area >= 2x the old (A,f,f)/(f,A,f)/(f,f,A) triangle.
  D. Roll-arrow source contract: ``_roll_arrow_actor`` is CONCENTRIC (origin-centred, no
     cx/cy offset) and big (``_ROLL_ARROW_RADIUS >= 1.0``, vs the old 0.28 ears); the two roll
     specs flank the top (one arc in the upper-left, one in the upper-right) and both feed the
     curved ``_roll_arrow_actor``.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services.nav_cube_orientation import (
    _newell_normal,
    chamfered_cube_facets,
    classify_pick,
    orientation_kind,
)
from KrakenOS.UI.services.nav_cube_widget import (
    _CORNER_FRACTION,
    _FACE_FRACTION,
)

_HALF = 0.5
_P = _HALF * _FACE_FRACTION
_Q = _HALF * _CORNER_FRACTION
_KIND_SIDES = {"face": 8, "edge": 4, "corner": 6}


def _poly_area(verts: np.ndarray) -> float:
    """Area of a planar polygon via the fan cross-product (verts in boundary order)."""
    c = verts.mean(axis=0)
    total = np.zeros(3)
    for i in range(len(verts)):
        total = total + np.cross(verts[i] - c, verts[(i + 1) % len(verts)] - c)
    return 0.5 * float(np.linalg.norm(total))


def run_checks():
    """Return ``(passed, notes)`` -- notes is a list of failure strings (empty on pass)."""
    failures: list[str] = []
    points, facets = chamfered_cube_facets(
        half=_HALF, face_fraction=_FACE_FRACTION, corner_fraction=_CORNER_FRACTION
    )

    # --- A: FreeCAD facet shapes (octagon / rectangle / hexagon) -------------------
    if len(points) != 48:
        failures.append(f"A FAIL: expected 48 shared vertices, got {len(points)}")
    if len(facets) != 26:
        failures.append(f"A FAIL: expected 26 facets, got {len(facets)}")
    for idxs, sign in facets:
        kind = orientation_kind(sign)
        want = _KIND_SIDES.get(kind)
        if want is not None and len(idxs) != want:
            failures.append(
                f"A FAIL: {kind} {tuple(int(s) for s in sign)} has {len(idxs)} sides, want {want}"
            )

    # --- B: each corner hexagon == signed permutations of (half, p, q) -------------
    want_mag = sorted([round(_HALF, 6), round(_P, 6), round(_Q, 6)])
    corner_areas: list[float] = []
    for idxs, sign in facets:
        if orientation_kind(sign) != "corner":
            continue
        verts = np.array([points[i] for i in idxs], dtype=float)
        # every vertex is a signed permutation of (half, p, q) in this octant's signs
        for v in verts:
            if sorted(round(abs(c), 6) for c in v) != want_mag:
                failures.append(f"B FAIL: corner {sign} vertex {np.round(v,3).tolist()} is not a (half,p,q) perm")
                break
            if not all(np.sign(c) == s for c, s in zip(v, sign)):
                failures.append(f"B FAIL: corner {sign} vertex {np.round(v,3).tolist()} leaves the octant")
                break
        # planar + outward
        normal = _newell_normal(points, idxs)
        nn = float(np.linalg.norm(normal))
        if nn <= 1e-9 or float(np.dot(normal, np.asarray(sign, float))) <= 0.0:
            failures.append(f"B FAIL: corner {sign} degenerate or wound inward")
            continue
        unit = normal / nn
        planar_err = float(np.max(np.abs((verts - verts.mean(0)) @ unit)))
        if planar_err > 1e-6:
            failures.append(f"B FAIL: corner {sign} non-planar ({planar_err:.2e})")
        if classify_pick(verts.mean(0)) != tuple(int(s) for s in sign):
            failures.append(f"B FAIL: corner {sign} centroid does not classify as its own corner")
        corner_areas.append(_poly_area(verts))

    # --- C: the hexagon corner is materially bigger than the legacy triangle -------
    f_legacy = _HALF * 0.72  # the old square-face keep-fraction that fixed the triangle corner
    tri = np.array([
        [_HALF, f_legacy, f_legacy],
        [f_legacy, _HALF, f_legacy],
        [f_legacy, f_legacy, _HALF],
    ], dtype=float)
    tri_area = _poly_area(tri)
    hex_area = float(np.mean(corner_areas)) if corner_areas else 0.0
    if hex_area < 2.0 * tri_area:
        failures.append(
            f"C FAIL: corner hexagon area {hex_area:.4f} is not >= 2x the legacy triangle "
            f"{tri_area:.4f} -- corners are not the bigger FreeCAD hexagons"
        )

    # --- D: roll-arrow restyle source contract ------------------------------------
    try:
        from KrakenOS.UI.services import nav_cube_widget as W

        # Re-derived for flag_20260810_151023/164247 (bugs/0603): the user asked twice for
        # the arcs to sit CLOSER to the cube, so the radius came down to 0.98 -- just
        # outside the cube silhouette (~0.87), still a concentric arc, nothing like the
        # old 0.28 ears this check exists to forbid. The bound is the silhouette, not 1.0.
        if getattr(W, "_ROLL_ARROW_RADIUS", 0.0) < 0.9:
            failures.append(
                f"D FAIL: _ROLL_ARROW_RADIUS {getattr(W, '_ROLL_ARROW_RADIUS', None)} < 0.9 -- "
                "roll handles are the old small 'ears', not concentric arcs outside the cube"
            )
        roll_src = inspect.getsource(W.NavigationCube._roll_arrow_actor)
        sig = roll_src.splitlines()[0]
        if "cx" in sig or "cy" in sig:
            failures.append("D FAIL: _roll_arrow_actor still takes a cx/cy offset -- not concentric with the cube")
        if "_ROLL_ARROW_RADIUS" not in roll_src:
            failures.append("D FAIL: _roll_arrow_actor no longer uses _ROLL_ARROW_RADIUS")
        arrow_src = inspect.getsource(W.NavigationCube._build_arrow_renderer)
        if "roll_ccw" not in arrow_src or "roll_cw" not in arrow_src:
            failures.append("D FAIL: the two roll specs (roll_ccw / roll_cw) are gone")
        if "_roll_arrow_actor(a0,a1" not in arrow_src.replace(" ", ""):
            failures.append("D FAIL: roll handles are not built from _roll_arrow_actor(a0, a1, ...)")
        # the two arcs flank the top: one centred upper-left (mid-angle > 90), one upper-right (< 90)
        specs = _extract_roll_specs(arrow_src)
        if specs is not None:
            mids = {k: 0.5 * (a0 + a1) for k, (a0, a1) in specs.items()}
            if not (mids.get("roll_ccw", 0) > 90.0 and mids.get("roll_cw", 180) < 90.0):
                failures.append(
                    f"D FAIL: roll arcs do not flank the top (mid-angles {mids}) -- expected "
                    "roll_ccw upper-left (>90 deg) and roll_cw upper-right (<90 deg)"
                )
            # the user asked TWICE for a SHORT rotation arc (bugs/0250 "curve segment too much",
            # then the 0253 follow-up "make the rotation arrow shorter") -- keep each sweep small
            spans = {k: abs(a1 - a0) for k, (a0, a1) in specs.items()}
            long = {k: round(s, 1) for k, s in spans.items() if s > 45.0}
            if long:
                failures.append(
                    f"D FAIL: roll arc sweep too long {long} deg -- keep each <= 45 deg (the user "
                    "asked twice for short rotation arcs: bugs/0250 + the 0253 follow-up)"
                )
    except Exception as exc:  # pragma: no cover - defensive
        failures.append(f"D FAIL: could not inspect nav_cube_widget roll wiring: {exc!r}")

    return (not failures), failures


def _extract_roll_specs(src: str):
    """Best-effort pull of the ``roll_specs = {..}`` (a0, a1) pairs from the widget source."""
    import ast

    try:
        for node in ast.walk(ast.parse(src.strip())):
            if isinstance(node, ast.Assign) and any(
                getattr(t, "id", "") == "roll_specs" for t in node.targets
            ):
                out = {}
                for k, v in zip(node.value.keys, node.value.values):
                    out[ast.literal_eval(k)] = tuple(ast.literal_eval(e) for e in v.elts)
                return out
    except Exception:
        return None
    return None


def main() -> int:
    passed, notes = run_checks()
    if passed:
        print("[PASS] nav cube matches FreeCAD: hexagon corners + concentric roll arrows (bugs/0253)")
        return 0
    print("[FAIL] bugs/0253 nav-cube FreeCAD-style guard:")
    for note in notes:
        print(f"   - {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
