"""Display-free guard: the fast integer coord-id boundary-edge selection is
edge-for-edge identical to the reference per-triangle walk.

Bug 0142 made a re-placed analytic STEP overlay reuse a cached point-index
silhouette instead of re-walking it (pose invariance, phase 131). But the COLD
first build of a heavy body still ran ``_boundary_edge_index_pairs`` over the raw
triangle-edge soup, and that selection deduplicated edges with two
``np.unique(..., axis=0)`` LEXSORTS over ~1.77 M six-float rows for the 591 k-cell
camera -- ~5 s on the UI thread, the residual multi-second freeze the user still
felt ("super lagging, I can't even use it for anything useful now").

Bug 0146 keeps the exact same selection but rewrites the key: an analytic STEP
body has many COINCIDENT points with distinct indices along shared face seams, so
each point is first resolved to a coordinate-ID via ONE
``np.unique(points, axis=0, return_inverse=True)`` over the 3-float points, the
canonical unordered edge pair is packed into a single int64, and all three dedup
passes then run as cheap 1-D ``np.unique`` calls. Camera 5.1 s -> 1.2 s (4.4x),
lens 0.31 s -> 0.05 s (6.4x), edge-for-edge identical.

This guard pins the contract without any rendering:

  1. The synthetic body is unwelded triangle soup with COINCIDENT duplicate
     vertices, so the coordinate-ID dedup path is genuinely exercised.
  2. For BOTH ``include_open_boundaries`` flags the integer-key selection is
     edge-for-edge identical to the reference walk
     ``face_boundary_edges_from_face_index`` (no visual regression).
  3. ``include_open_boundaries=False`` (shared-by->=2-faces only) is a subset of
     the ``True`` selection (open boundary edges are the difference).
  4. A clean cube selects exactly its 12 geometric edges (face-internal diagonals
     excluded).
  5. Degenerate inputs (no triangles; every face id negative) return an empty
     ``(0, 2)`` array rather than raising.
  6. Source markers: the function uses the integer coordinate-id key and the old
     per-row 6-float coordinate lexsort (``_coord_rows_gt``) is gone -- so a
     future "simplification" that reverts the optimisation is caught.

Penta phase 135 (baseline -> 135).
"""

from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.services import open3d_face_index_edges as fie

FACE_INDEX_CELL_DATA = "kraken_step_face_index"
ANALYTIC_FIELD_DATA = "kraken_step_analytic"


def _box_triangles(pv, *, x, y, z, translate=(0.0, 0.0, 0.0), rotate_z_deg=0.0):
    """Unwelded (T, 3, 3) triangle coordinates for one triangulated box."""
    box = pv.Cube(x_length=x, y_length=y, z_length=z).triangulate()
    if rotate_z_deg:
        box = box.rotate_z(rotate_z_deg, inplace=False)
    box = box.translate(tuple(translate), inplace=False)
    faces = np.asarray(box.faces, dtype=np.int64).reshape((-1, 4))[:, 1:4]
    points = np.asarray(box.points, dtype=float)
    return points[faces]


def _face_index_by_normal(triangles: np.ndarray, start_id: int) -> tuple[np.ndarray, int]:
    """Assign each triangle a face id by its rounded outward normal."""
    v0, v1, v2 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norm > 0.0, norm, 1.0)
    keys = np.round(normals, 4)
    _uniq, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1).astype(np.int64)
    return inverse + int(start_id), int(_uniq.shape[0])


def _analytic_step_mesh(pv, *, boxes):
    """Mirror the real bake: unwelded triangle soup + per-cell face index."""
    tri_blocks: list[np.ndarray] = []
    fid_blocks: list[np.ndarray] = []
    next_id = 0
    for spec in boxes:
        tris = _box_triangles(pv, **spec)
        fids, n_faces = _face_index_by_normal(tris, next_id)
        tri_blocks.append(tris)
        fid_blocks.append(fids)
        next_id += n_faces
    triangles = np.concatenate(tri_blocks, axis=0)
    face_index = np.concatenate(fid_blocks, axis=0)
    count = int(triangles.shape[0])
    points = triangles.reshape((-1, 3))
    faces = np.empty((count, 4), dtype=np.int64)
    faces[:, 0] = 3
    faces[:, 1] = np.arange(0, 3 * count, 3, dtype=np.int64)
    faces[:, 2] = faces[:, 1] + 1
    faces[:, 3] = faces[:, 1] + 2
    mesh = pv.PolyData(points, faces.reshape(-1))
    mesh.cell_data[FACE_INDEX_CELL_DATA] = face_index.astype(np.int32)
    mesh.field_data[ANALYTIC_FIELD_DATA] = np.asarray([1], dtype=np.int8)
    return mesh


def _pairs_edge_set(points, pairs, dec: int = 6) -> set:
    """Canonical, order-independent set of edges given as point-index pairs."""
    pts = np.round(np.asarray(points, dtype=float), dec)
    out: set = set()
    for i0, i1 in np.asarray(pairs, dtype=np.int64):
        a = tuple(pts[i0])
        b = tuple(pts[i1])
        if a == b:
            continue
        out.add((a, b) if a <= b else (b, a))
    return out


def _walk_edge_set(poly, dec: int = 6) -> set:
    """Canonical edge set from the reference per-triangle walk polydata."""
    if poly is None:
        return set()
    pts = np.asarray(poly.points, dtype=float)
    lines = np.asarray(poly.lines, dtype=np.int64).reshape((-1, 3))
    out: set = set()
    for _two, i0, i1 in lines:
        a = tuple(np.round(pts[i0], dec))
        b = tuple(np.round(pts[i1], dec))
        if a == b:
            continue
        out.add((a, b) if a <= b else (b, a))
    return out


def run_checks() -> tuple[bool, list[str]]:
    notes: list[str] = []
    try:
        import pyvista as pv
    except Exception as exc:  # pragma: no cover - environment guard
        return False, [f"pyvista unavailable: {exc!r}"]

    ok = True

    def record(name: str, passed: bool, detail: str = "") -> None:
        nonlocal ok
        ok = ok and bool(passed)
        status = "PASS" if passed else "FAIL"
        notes.append(f"{name} | {status}" + (f" | {detail}" if detail else ""))

    two_box = [
        dict(x=2.0, y=2.0, z=2.0),
        dict(x=3.0, y=1.0, z=1.0, translate=(8.0, 0.0, 0.0), rotate_z_deg=30.0),
    ]
    mesh = _analytic_step_mesh(pv, boxes=two_box)
    surface, triangles, face_index = fie._surface_triangles_and_face_index(mesh)

    # --- 1) the soup genuinely has coincident duplicate vertices --------------
    raw = np.round(triangles.reshape((-1, 3)), 8)
    _, raw_cid = np.unique(raw, axis=0, return_inverse=True)
    n_distinct = int(np.asarray(raw_cid).max()) + 1
    record(
        "triangle soup has coincident duplicate vertices (dedup path exercised)",
        n_distinct < raw.shape[0],
        f"soup_points={raw.shape[0]} distinct_coords={n_distinct}",
    )

    # --- 2) + 3) edge-for-edge identical to the reference walk, both flags -----
    sets: dict[bool, set] = {}
    for inc in (True, False):
        pairs = fie._boundary_edge_index_pairs(
            surface, triangles, face_index, include_open_boundaries=inc
        )
        fast_set = _pairs_edge_set(surface.points, pairs)
        ref_set = _walk_edge_set(
            fie.face_boundary_edges_from_face_index(mesh, include_open_boundaries=inc)
        )
        sets[inc] = fast_set
        record(
            f"int-key selection identical to reference walk (include_open={inc})",
            fast_set == ref_set and len(fast_set) > 0,
            f"|fast|={len(fast_set)} |ref|={len(ref_set)} sym_diff={len(fast_set ^ ref_set)}",
        )
    record(
        "include_open=False is a subset of include_open=True",
        sets[False] <= sets[True],
        f"|False|={len(sets[False])} |True|={len(sets[True])} extra_open={len(sets[True] - sets[False])}",
    )

    # --- 4) a clean cube selects exactly its 12 geometric edges ---------------
    cube = _analytic_step_mesh(pv, boxes=[dict(x=2.0, y=2.0, z=2.0)])
    c_surface, c_tris, c_fids = fie._surface_triangles_and_face_index(cube)
    cube_pairs = fie._boundary_edge_index_pairs(
        c_surface, c_tris, c_fids, include_open_boundaries=True
    )
    cube_edges = _pairs_edge_set(c_surface.points, cube_pairs)
    record(
        "clean cube selects exactly 12 boundary edges (diagonals excluded)",
        len(cube_edges) == 12,
        f"edges={len(cube_edges)}",
    )

    # --- 5) degenerate inputs return an empty (0, 2) array, no raise ----------
    empty_tris = fie._boundary_edge_index_pairs(
        surface, np.empty((0, 3, 3), dtype=float), np.empty((0,), dtype=np.int64),
        include_open_boundaries=True,
    )
    record(
        "no triangles -> empty (0, 2)",
        isinstance(empty_tris, np.ndarray) and empty_tris.shape == (0, 2),
        f"shape={getattr(empty_tris, 'shape', None)}",
    )
    all_neg = fie._boundary_edge_index_pairs(
        surface, triangles, np.full(int(triangles.shape[0]), -1, dtype=np.int64),
        include_open_boundaries=True,
    )
    record(
        "every face id negative -> empty (0, 2)",
        isinstance(all_neg, np.ndarray) and all_neg.shape == (0, 2),
        f"shape={getattr(all_neg, 'shape', None)}",
    )

    # --- 6) source markers: integer key present, old lexsort gone -------------
    src = inspect.getsource(fie._boundary_edge_index_pairs)
    record(
        "uses the integer coordinate-id key (coord_id + packed edge_key)",
        "coord_id" in src and "edge_key" in src,
    )
    record(
        "old per-row 6-float coordinate lexsort (_coord_rows_gt) removed",
        "_coord_rows_gt" not in src and not hasattr(fie, "_coord_rows_gt"),
    )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] fast integer coord-id boundary-edge selection is edge-for-edge identical to the walk"
        if ok
        else "[FAIL] fast boundary-edge selection regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
