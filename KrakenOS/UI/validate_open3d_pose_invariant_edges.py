"""Display-free guard: analytic STEP-overlay silhouette edges are pose-invariant.

A heavy imported STEP overlay (the 591k-triangle camera body, the LED plate, the
beam-splitter) draws its silhouette as analytic-face boundary edges. That edge
selection was keyed on ``id(mesh)`` (``cached_display_feature_edges``), so every
re-placement -- a glued LED following its partner, the camera tracking the image
plane, any drag / rotate / resize -- built a brand-new mesh object whose id missed
the cache and re-ran the full per-triangle boundary walk cold (~31 s on the
camera, ~3 s on the LED), paid on essentially every editing action (bug 0142, the
"Open 3D seems takes longer ... still very lag").

But a rigid/uniform re-placement only moves the vertices: the triangle
connectivity, the per-cell ``kraken_step_face_index`` and therefore the SELECTION
of which edges are analytic-face boundaries are all invariant -- only the
coordinates change. ``pose_invariant_feature_edges`` caches that selection as
POINT-INDEX PAIRS keyed on the body's intrinsic identity (face-index fingerprint
+ structure), so a re-placed copy rebuilds its silhouette with a vectorised
coordinate gather instead of the walk.

This guard pins the contract without any rendering:

  1. SAME pose -- the index-pair selection is edge-for-edge identical to the
     production loop (``face_boundary_edges_from_face_index``) and to the old
     ``cached_display_feature_edges`` output (no visual regression).
  2. A clean cube selects exactly its 12 geometric edges (face-internal diagonals
     are correctly excluded).
  3. POSE INVARIANCE -- after a rigid re-placement (points moved only) the body
     hits the index-pair cache WITHOUT re-running the boundary walk, and the
     gathered edges (a) equal the loop re-run at the new pose (0 drift) and
     (b) equal the original edges carried through the same rigid transform.
  4. A non-analytic mesh (no ``kraken_step_analytic`` flag) transparently falls
     back to ``cached_display_feature_edges`` and never touches the index cache.
  5. Source wiring -- the inspector's ``_display_feature_edges`` routes to
     ``pose_invariant_feature_edges``.

Penta phase 131 (baseline -> 131).
"""

from __future__ import annotations

from pathlib import Path

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
    """Assign each triangle a face id by its (raw, outward) rounded normal."""
    v0, v1, v2 = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    normals = np.cross(v1 - v0, v2 - v0)
    norm = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = normals / np.where(norm > 0.0, norm, 1.0)
    keys = np.round(normals, 4)
    _uniq, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1).astype(np.int64)
    return inverse + int(start_id), int(_uniq.shape[0])


def _analytic_step_mesh(pv, *, boxes, analytic: bool = True):
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
    if analytic:
        mesh.field_data[ANALYTIC_FIELD_DATA] = np.asarray([1], dtype=np.int8)
    return mesh


def _rigid_replace(pv, mesh, *, dz: float, deg: float):
    """Deep-copy then move points only (a pose change), with the matrix used."""
    out = mesh.copy(deep=True)
    theta = np.radians(deg)
    c, s = np.cos(theta), np.sin(theta)
    rot = np.asarray([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    shift = np.asarray([0.0, 0.0, dz])
    out.points = np.asarray(mesh.points, dtype=float) @ rot.T + shift
    return out, rot, shift


def _edge_set(poly, dec: int = 6) -> set:
    """Canonical, order-independent set of rounded edge segments."""
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


def _edge_rows(poly) -> np.ndarray:
    """(N, 6) raw endpoint coordinates per edge segment (no canonicalisation)."""
    if poly is None:
        return np.empty((0, 6), dtype=float)
    pts = np.asarray(poly.points, dtype=float)
    lines = np.asarray(poly.lines, dtype=np.int64).reshape((-1, 3))
    rows = [np.concatenate([pts[i0], pts[i1]]) for _two, i0, i1 in lines]
    return np.asarray(rows, dtype=float) if rows else np.empty((0, 6), dtype=float)


def _transform_rows(rows: np.ndarray, rot: np.ndarray, shift: np.ndarray) -> np.ndarray:
    """Carry (N, 6) edge endpoints through a rigid transform."""
    if rows.size == 0:
        return rows
    a = rows[:, :3] @ rot.T + shift
    b = rows[:, 3:] @ rot.T + shift
    return np.concatenate([a, b], axis=1)


def _rows_close(a: np.ndarray, b: np.ndarray, *, atol: float = 1e-6) -> bool:
    """Whether two edge-row sets match within ``atol``, endpoint order agnostic.

    Greedy one-to-one match (N is tiny). Tolerance + an endpoint swap sidestep the
    last-ULP representative jitter that makes fixed-decimal rounding brittle right
    on a rounding boundary -- the geometry is identical to ~1e-8, far below atol.
    """
    if a.shape != b.shape:
        return False
    remaining = list(range(b.shape[0]))
    for row in a:
        swapped = np.concatenate([row[3:], row[:3]])
        hit = -1
        for j in remaining:
            if np.allclose(row, b[j], atol=atol) or np.allclose(swapped, b[j], atol=atol):
                hit = j
                break
        if hit < 0:
            return False
        remaining.remove(hit)
    return True


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

    # Isolate the module caches so the checks are deterministic.
    fie._BOUNDARY_INDEX_CACHE.clear()
    fie._BOUNDARY_INDEX_CACHE_ORDER.clear()

    two_box = [
        dict(x=2.0, y=2.0, z=2.0),
        dict(x=3.0, y=1.0, z=1.0, translate=(8.0, 0.0, 0.0), rotate_z_deg=30.0),
    ]
    mesh = _analytic_step_mesh(pv, boxes=two_box, analytic=True)

    # --- 1) same pose: faithful to the loop AND to the old id()-keyed path ----
    ground = _edge_set(fie.face_boundary_edges_from_face_index(mesh, include_open_boundaries=True))
    old_path = _edge_set(fie.cached_display_feature_edges(mesh, feature_angle=55.0, boundary_edges=True))
    fie._BOUNDARY_INDEX_CACHE.clear()
    fie._BOUNDARY_INDEX_CACHE_ORDER.clear()
    new_path = _edge_set(fie.pose_invariant_feature_edges(mesh, feature_angle=55.0, boundary_edges=True))
    record(
        "same-pose edges identical to production loop",
        new_path == ground and len(new_path) > 0,
        f"|loop|={len(ground)} |pose_inv|={len(new_path)} sym_diff={len(new_path ^ ground)}",
    )
    record(
        "same-pose edges identical to old cached_display_feature_edges",
        new_path == old_path,
        f"sym_diff={len(new_path ^ old_path)}",
    )
    record(
        "analytic body populated the index-pair cache",
        len(fie._BOUNDARY_INDEX_CACHE) == 1,
        f"entries={len(fie._BOUNDARY_INDEX_CACHE)}",
    )

    # --- 2) a clean cube selects exactly its 12 geometric edges ---------------
    cube = _analytic_step_mesh(pv, boxes=[dict(x=2.0, y=2.0, z=2.0)], analytic=True)
    fie._BOUNDARY_INDEX_CACHE.clear()
    fie._BOUNDARY_INDEX_CACHE_ORDER.clear()
    cube_edges = _edge_set(fie.pose_invariant_feature_edges(cube, boundary_edges=True))
    record(
        "clean cube selects exactly 12 boundary edges (diagonals excluded)",
        len(cube_edges) == 12,
        f"edges={len(cube_edges)}",
    )

    # --- 3) pose invariance: cache HIT, no re-walk, 0 drift -------------------
    fie._BOUNDARY_INDEX_CACHE.clear()
    fie._BOUNDARY_INDEX_CACHE_ORDER.clear()
    warm = fie.pose_invariant_feature_edges(mesh, feature_angle=55.0, boundary_edges=True)
    warm_rows = _edge_rows(warm)

    real_pairs = fie._boundary_edge_index_pairs
    calls = {"n": 0}

    def _counting_pairs(*args, **kwargs):
        calls["n"] += 1
        return real_pairs(*args, **kwargs)

    moved, rot, shift = _rigid_replace(pv, mesh, dz=42.0, deg=7.0)
    fie._boundary_edge_index_pairs = _counting_pairs
    try:
        fast = fie.pose_invariant_feature_edges(moved, feature_angle=55.0, boundary_edges=True)
    finally:
        fie._boundary_edge_index_pairs = real_pairs
    fast_rows = _edge_rows(fast)

    record(
        "re-placed body hits the cache without re-running the boundary walk",
        calls["n"] == 0 and len(fie._BOUNDARY_INDEX_CACHE) == 1,
        f"recompute_calls={calls['n']} cache_entries={len(fie._BOUNDARY_INDEX_CACHE)}",
    )
    moved_ground_rows = _edge_rows(
        fie.face_boundary_edges_from_face_index(moved, include_open_boundaries=True)
    )
    record(
        "re-placed edges equal the loop re-run at the moved pose (0 drift)",
        fast_rows.shape[0] > 0 and _rows_close(fast_rows, moved_ground_rows),
        f"|fast|={fast_rows.shape[0]} |moved_loop|={moved_ground_rows.shape[0]}",
    )
    record(
        "re-placed edges equal the original silhouette carried by the rigid transform",
        _rows_close(fast_rows, _transform_rows(warm_rows, rot, shift)),
        f"|warm|={warm_rows.shape[0]} |fast|={fast_rows.shape[0]}",
    )

    # --- 4) non-analytic mesh falls back and never touches the index cache ----
    fie._BOUNDARY_INDEX_CACHE.clear()
    fie._BOUNDARY_INDEX_CACHE_ORDER.clear()
    plain = mesh.copy(deep=True)
    try:
        del plain.field_data[ANALYTIC_FIELD_DATA]
    except Exception:
        plain.field_data[ANALYTIC_FIELD_DATA] = np.asarray([0], dtype=np.int8)
    fallback = _edge_set(fie.pose_invariant_feature_edges(plain, feature_angle=55.0, boundary_edges=True))
    reference = _edge_set(fie.cached_display_feature_edges(plain, feature_angle=55.0, boundary_edges=True))
    record(
        "non-analytic mesh falls back to cached_display_feature_edges identically",
        fallback == reference and len(fie._BOUNDARY_INDEX_CACHE) == 0,
        f"sym_diff={len(fallback ^ reference)} index_cache_entries={len(fie._BOUNDARY_INDEX_CACHE)}",
    )

    # --- 5) source wiring: the inspector routes to the pose-invariant entry ----
    inspector_src = (Path(__file__).resolve().parent / "open3d_inspector.py").read_text(encoding="utf-8")
    routed = (
        "pose_invariant_feature_edges as _pose_invariant_feature_edges_mesh" in inspector_src
        and "_pose_invariant_feature_edges_mesh(mesh, feature_angle=feature_angle" in inspector_src
    )
    record("inspector _display_feature_edges routes to pose_invariant_feature_edges", routed)

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for note in notes:
        print(note)
    print(
        "[PASS] analytic STEP silhouette edges are pose-invariant (re-placement skips the boundary walk)"
        if ok
        else "[FAIL] pose-invariant STEP edge cache regressed"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
