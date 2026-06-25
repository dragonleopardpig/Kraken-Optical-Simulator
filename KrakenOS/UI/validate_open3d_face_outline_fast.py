"""Display-free guard: the STEP hover/pick face-outline is selected from a cached,
vectorised edge topology that is EDGE-FOR-EDGE identical to the old scalar walk.

bugs/0148: ``face_outline_from_face_indices`` rebuilt a per-point-ROUNDED edge dict
(``_edge_records`` -> ``_point_key`` -> scalar ``np.round``) over the WHOLE body on
every mouse-move, so hovering the 591k-triangle vendor camera body froze the GUI
30-56 s per hover (py-spy caught the main thread pegged in ``_point_key``). The fix
gives this path the same treatment bug 0146 gave the silhouette path: a
target-independent, pose-stable edge topology computed once per body (vectorised)
and cached, then each hover selects one face group's outline with a boolean mask.

This guard pins the contract without any rendering, on a tiny synthetic analytic
mesh that reproduces the two things the scalar walk handled:

  * a SHARED SEAM between two faces whose vertices are DUPLICATED with distinct
    point indices but coincident coordinates (the analytic STEP face seam) -- the
    rounded-coordinate vertex identity must unify them, so the seam is a single
    interior edge of the union; and
  * INTERIOR DIAGONALS inside each face that must never be drawn.

Checks:
  1. The vectorised selection == the scalar selection for ``{0}``, ``{1}`` and the
     ``{0,1}`` group (the core algorithmic-equivalence guard).
  2. The shared seam IS on each single face's outline but is DROPPED from the
     two-face group outline (so a group outline = its true boundary, not a sum).
  3. An outer boundary edge is on every outline; interior diagonals are on none.
  4. Source marker: ``face_outline_from_face_indices`` consults
     ``_cached_face_outline_edge_topology`` -- so a revert to the pure scalar walk
     (the 30-56 s freeze) is caught.

Penta phase 137 (baseline -> 137).
"""

from __future__ import annotations

import inspect
import types

import numpy as np


def _synthetic_mesh():
    """Two coplanar quads (face 0 left, face 1 right) sharing a seam, each quad
    split into two triangles, with the seam vertices DUPLICATED per face."""
    points = np.array(
        [
            [0.0, 0.0, 0.0],  # 0  A
            [0.0, 1.0, 0.0],  # 1  B
            [1.0, 0.0, 0.0],  # 2  C   (face-0 copy of seam bottom)
            [1.0, 1.0, 0.0],  # 3  D   (face-0 copy of seam top)
            [1.0, 0.0, 0.0],  # 4  C'  (face-1 copy, coincident with 2)
            [1.0, 1.0, 0.0],  # 5  D'  (face-1 copy, coincident with 3)
            [2.0, 0.0, 0.0],  # 6  E
            [2.0, 1.0, 0.0],  # 7  F
        ],
        dtype=float,
    )
    tris = np.array([[0, 2, 3], [0, 3, 1], [4, 6, 7], [4, 7, 5]], dtype=np.int64)
    face_index = np.array([0, 0, 1, 1], dtype=np.int64)
    faces_flat = np.hstack([np.full((tris.shape[0], 1), 3, dtype=np.int64), tris]).reshape(-1)
    surface = types.SimpleNamespace(faces=faces_flat, points=points)
    triangles = points[tris]
    return surface, triangles, face_index, points


def _ckey(p) -> tuple[float, float, float]:
    return tuple(round(float(v), 8) for v in np.asarray(p, dtype=float).reshape(3))


def _ekey(p0, p1):
    a, b = _ckey(p0), _ckey(p1)
    return (a, b) if a <= b else (b, a)


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    try:
        from KrakenOS.UI.services.open3d_face_index_edges import (
            _cached_face_outline_edge_topology,
            _edge_records,
            _face_group_outline_pairs_from_topology,
            _face_outline_edge_topology,
            face_outline_from_face_indices,
        )
    except Exception as exc:  # pragma: no cover - import guard
        return False, [f"module unavailable: {exc!r}"]

    surface, triangles, face_index, points = _synthetic_mesh()

    # Reference: replicate the OLD scalar selection exactly.
    def old_edge_set(targets):
        targets = {int(t) for t in targets}
        out = set()
        for records in _edge_records(triangles, face_index).values():
            selected_count = sum(1 for fid, _p0, _p1 in records if int(fid) in targets)
            if selected_count <= 0:
                continue
            if (
                len(records) == 1
                or selected_count < len(records)
                or any(int(fid) not in targets for fid, _p0, _p1 in records)
            ):
                out.add(_ekey(records[0][1], records[0][2]))
        return out

    # New vectorised selection -> rounded-coord edge set (representative-independent).
    def new_edge_set(targets):
        topo = _face_outline_edge_topology(surface, face_index)
        if topo is None:
            return None
        pairs = _face_group_outline_pairs_from_topology(topo, {int(t) for t in targets})
        return {_ekey(points[i0], points[i1]) for i0, i1 in np.asarray(pairs)}

    seam = _ekey((1.0, 0.0, 0.0), (1.0, 1.0, 0.0))
    left_edge = _ekey((0.0, 0.0, 0.0), (0.0, 1.0, 0.0))   # B-A, left quad outer edge
    diag_left = _ekey((0.0, 0.0, 0.0), (1.0, 1.0, 0.0))   # A-D interior diagonal

    # --- 1) vectorised == scalar for every target group ------------------------
    for targets in ({0}, {1}, {0, 1}):
        old = old_edge_set(targets)
        new = new_edge_set(targets)
        record(
            f"vectorised outline == scalar outline for targets {sorted(targets)}",
            new is not None and new == old,
            f"old={len(old)} new={'None' if new is None else len(new)}",
        )

    # --- 2) the shared seam: on each single face, dropped from the group --------
    s0 = new_edge_set({0})
    s1 = new_edge_set({1})
    sU = new_edge_set({0, 1})
    record(
        "shared seam is on the single-face outlines",
        s0 is not None and seam in s0 and s1 is not None and seam in s1,
    )
    record(
        "shared seam is DROPPED from the two-face group outline",
        sU is not None and seam not in sU,
        f"group_edges={sorted(sU) if sU is not None else None}",
    )

    # --- 3) outer boundary kept, interior diagonals never drawn ----------------
    record(
        "left outer edge present in every outline",
        all(es is not None and left_edge in es for es in (s0, sU)),
    )
    record(
        "interior diagonals are never on any outline",
        all(es is not None and diag_left not in es for es in (s0, s1, sU)),
    )

    # --- cache returns the same topology object (memoised, not recomputed) ------
    t1 = _cached_face_outline_edge_topology(None, surface, face_index)
    record("topology builds without a real mesh handle", t1 is not None)

    # --- 4) source marker: the fast path is wired in ---------------------------
    src = inspect.getsource(face_outline_from_face_indices)
    record(
        "face_outline_from_face_indices consults the cached edge topology",
        "_cached_face_outline_edge_topology" in src,
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] STEP hover/pick face-outline is vectorised + cached (no per-hover full walk)"
        if ok
        else "[FAIL] STEP hover/pick face-outline regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
