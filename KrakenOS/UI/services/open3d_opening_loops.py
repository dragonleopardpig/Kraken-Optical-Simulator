"""Closed OPENING loops of an analytic STEP body, for plain-hover rim snapping.

bugs/0328 -- the clear-aperture opening a user points at is not always a whole
analytic FACE.  On the vendor LED (OPT-ILS0202) the emitting *central square* is an
INNER hole loop of the wide front panel face (F0053), not a face of its own; the five
auto-detected clear-aperture candidates are all top/side mechanical openings.  So the
per-face CA snap (bugs/0326/0327) locked onto the wrong opening (the +y tray slot,
F0266, ~144 px from the cursor) and plain hover fell back to the whole-panel highlight
-- the flag read "no improvement at all".

The square *is* a deterministic closed edge loop; it is merely an inner boundary of a
face.  Mine every closed loop from the outlines of the LARGE faces (where real openings
live -- the same area gate the CA detector uses), drop each face's OUTER silhouette
(the panel edge, not an opening), and expose the rest so the hover pick can snap to the
NEAREST opening rim by screen proximity -- honouring the standing directive that "all
closed edges should be detected".

Display-free: pure geometry + a caller-supplied ``project`` callback.  The loop set is
memoised per mesh (id + content token), like the surface-triangle / edge caches, so the
~0.5 s extraction is paid once per layout pose, never per hover.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from .open3d_face_index_edges import (
    _line_polydata,
    _mesh_cache_token,
    face_outline_from_face_indices,
    line_segment_pairs,
    triangle_array_and_face_index,
)

# Real openings live in the wide housing panels; mirror the CA detector's area gate so
# the two agree on what counts as a "face big enough to hold an aperture".
_FACE_AREA_GATE_MM2 = 500.0
# Drop screw-hole / tessellation-sliver loops: a clear aperture is at least a few mm.
_MIN_PERIMETER_MM = 12.0
# Drop a loop that spans essentially the whole body (an outer silhouette that slipped
# through the per-face outer-loop filter). Scale-relative, not a per-scene constant.
_MAX_BBOX_DIAG_FRACTION = 0.9
# Weld tolerance for stitching the outline's per-segment duplicate endpoints back into a
# shared-vertex graph so loops can be traced.
_WELD_TOL_MM = 1.0e-4

_OPENING_LOOP_CACHE: "dict[int, tuple]" = {}
_OPENING_LOOP_ORDER: "list[int]" = []
_OPENING_LOOP_CACHE_MAX = 8


@dataclass(frozen=True)
class OpeningLoop:
    """One closed opening rim in world/scene coordinates."""

    points: np.ndarray  # (N, 3) ordered, welded, closed (first != last)
    centroid: np.ndarray  # (3,)
    normal: np.ndarray  # (3,) unit best-fit plane normal
    perimeter: float  # mm
    area: float  # mm^2 (planar polygon area estimate)
    face_index: int  # owning analytic face


def _weld(points: np.ndarray, pairs) -> "tuple[np.ndarray, list[tuple[int, int]]]":
    """Merge coincident outline endpoints into a shared-vertex edge graph."""
    keys: "dict[tuple[int, int, int], int]" = {}
    remap = np.empty(len(points), dtype=int)
    uniq: "list[np.ndarray]" = []
    for i, p in enumerate(points):
        key = (
            int(round(float(p[0]) / _WELD_TOL_MM)),
            int(round(float(p[1]) / _WELD_TOL_MM)),
            int(round(float(p[2]) / _WELD_TOL_MM)),
        )
        j = keys.get(key)
        if j is None:
            j = len(uniq)
            keys[key] = j
            uniq.append(np.asarray(p, dtype=float))
        remap[i] = j
    if not uniq:
        return np.empty((0, 3), dtype=float), []
    welded_pairs: "set[tuple[int, int]]" = set()
    for a, b in pairs:
        ra, rb = int(remap[a]), int(remap[b])
        if ra != rb:
            welded_pairs.add((ra, rb) if ra < rb else (rb, ra))
    return np.asarray(uniq, dtype=float), sorted(welded_pairs)


def _trace_loops(pairs) -> "list[list[int]]":
    """Trace clean closed cycles (every interior vertex has degree 2) from an edge set."""
    adj: "dict[int, list[int]]" = defaultdict(list)
    for a, b in pairs:
        adj[a].append(b)
        adj[b].append(a)
    seen: "set[tuple[int, int]]" = set()
    loops: "list[list[int]]" = []
    for start in list(adj):
        for first in adj[start]:
            edge0 = (start, first) if start < first else (first, start)
            if edge0 in seen:
                continue
            loop = [start]
            prev, cur = start, first
            seen.add(edge0)
            ok = True
            while cur != start:
                loop.append(cur)
                nbrs = [x for x in adj[cur] if x != prev]
                if len(nbrs) != 1:
                    ok = False
                    break
                nxt = nbrs[0]
                seen.add((cur, nxt) if cur < nxt else (nxt, cur))
                prev, cur = cur, nxt
                if len(loop) > 200000:
                    ok = False
                    break
            if ok and len(loop) >= 3:
                loops.append(loop)
    return loops


def _loop_plane(points: np.ndarray) -> "tuple[np.ndarray, np.ndarray, float]":
    """Newell's-method centroid, unit normal, and planar area for a loop."""
    centroid = points.mean(axis=0)
    n = len(points)
    nx = ny = nz = 0.0
    for i in range(n):
        cur = points[i]
        nxt = points[(i + 1) % n]
        nx += (cur[1] - nxt[1]) * (cur[2] + nxt[2])
        ny += (cur[2] - nxt[2]) * (cur[0] + nxt[0])
        nz += (cur[0] - nxt[0]) * (cur[1] + nxt[1])
    normal = np.asarray([nx, ny, nz], dtype=float)
    length = float(np.linalg.norm(normal))
    if length < 1e-12:
        return centroid, np.asarray([0.0, 0.0, 1.0]), 0.0
    return centroid, normal / length, 0.5 * length


def _perimeter(points: np.ndarray) -> float:
    return float(np.linalg.norm(np.diff(np.vstack([points, points[:1]]), axis=0), axis=1).sum())


def _compute_opening_loops(mesh) -> "list[OpeningLoop]":
    tris, fidx = triangle_array_and_face_index(mesh)
    fidx = np.asarray(fidx, dtype=int)
    if tris.size == 0 or fidx.size != tris.shape[0] or not np.any(fidx >= 0):
        return []
    try:
        bounds = np.asarray(mesh.bounds, dtype=float).reshape(3, 2)
        mesh_diag = float(np.linalg.norm(np.ptp(bounds, axis=1)))
    except Exception:
        mesh_diag = 0.0

    result: "list[OpeningLoop]" = []
    for fi in np.unique(fidx):
        if fi < 0:
            continue
        sel = tris[fidx == fi]
        if sel.shape[0] == 0:
            continue
        v0, v1, v2 = sel[:, 0], sel[:, 1], sel[:, 2]
        face_area = float(0.5 * np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1).sum())
        if face_area < _FACE_AREA_GATE_MM2:
            continue
        try:
            outline = face_outline_from_face_indices(mesh, (int(fi),))
        except Exception:
            outline = None
        if outline is None or int(getattr(outline, "n_points", 0)) == 0:
            continue
        pts = np.asarray(outline.points, dtype=float).reshape(-1, 3)
        pairs = line_segment_pairs(outline)
        if pts.shape[0] < 3 or not pairs:
            continue
        welded, welded_pairs = _weld(pts, pairs)
        loops = _trace_loops(welded_pairs)
        if not loops:
            continue
        records = []
        for loop in loops:
            loop_pts = welded[loop]
            centroid, normal, area = _loop_plane(loop_pts)
            records.append((area, _perimeter(loop_pts), loop_pts, centroid, normal))
        # A face's OUTER silhouette (its largest-area loop) is the panel edge, not an
        # opening. Drop it when the face has holes; a single-loop face IS itself an
        # opening (e.g. the tray slot), so keep it.
        outer = max(range(len(records)), key=lambda i: records[i][0]) if len(records) > 1 else -1
        for i, (area, perimeter, loop_pts, centroid, normal) in enumerate(records):
            if i == outer:
                continue
            if perimeter < _MIN_PERIMETER_MM:
                continue
            bbox_diag = float(np.linalg.norm(loop_pts.max(0) - loop_pts.min(0)))
            if mesh_diag > 0.0 and bbox_diag > _MAX_BBOX_DIAG_FRACTION * mesh_diag:
                continue
            result.append(
                OpeningLoop(
                    points=loop_pts,
                    centroid=np.asarray(centroid, dtype=float).reshape(3),
                    normal=np.asarray(normal, dtype=float).reshape(3),
                    perimeter=float(perimeter),
                    area=float(area),
                    face_index=int(fi),
                )
            )
    return result


def opening_loops_for_mesh(mesh) -> "list[OpeningLoop]":
    """Mined opening rims for a STEP mesh, memoised per mesh (id + content token)."""
    if mesh is None:
        return []
    key = id(mesh)
    token = _mesh_cache_token(mesh)
    cached = _OPENING_LOOP_CACHE.get(key)
    if cached is not None and cached[0] == token:
        return cached[1]
    loops = _compute_opening_loops(mesh)
    _OPENING_LOOP_CACHE[key] = (token, loops)
    if key in _OPENING_LOOP_ORDER:
        _OPENING_LOOP_ORDER.remove(key)
    _OPENING_LOOP_ORDER.append(key)
    while len(_OPENING_LOOP_ORDER) > _OPENING_LOOP_CACHE_MAX:
        evicted = _OPENING_LOOP_ORDER.pop(0)
        if evicted != key:
            _OPENING_LOOP_CACHE.pop(evicted, None)
    return loops


def loop_edge_pairs(loop: OpeningLoop) -> "list[tuple[int, int]]":
    """Sequential closed-loop segment index pairs for ``nearest_display_edge``."""
    n = int(len(loop.points))
    if n < 2:
        return []
    return [(i, (i + 1) % n) for i in range(n)]


def loop_outline_polydata(loop: OpeningLoop):
    """A lines-only polydata of the loop rim (for the gold edge overlay)."""
    pts = np.asarray(loop.points, dtype=float).reshape(-1, 3)
    if pts.shape[0] < 2:
        return None
    edges = [(pts[i], pts[(i + 1) % pts.shape[0]]) for i in range(pts.shape[0])]
    return _line_polydata(edges)


def nearest_opening_loop(
    loops,
    display_xy,
    project,
    *,
    tolerance_px: float = 30.0,
    gate_px: float = 260.0,
) -> "OpeningLoop | None":
    """The opening loop whose projected rim is nearest the cursor, or None.

    A cheap centroid gate (one projection per loop) prunes far loops; the survivors
    are edge-tested with ``nearest_display_edge`` in SCREEN space (``depth_reference``
    None -- a recessed rim is far in 3D but projects near the cursor, which is exactly
    the edge the user points at). Ties break toward the SMALLER opening (the tighter
    aperture pointed INTO, not a larger surrounding boundary).
    """
    from .open3d_face_index_edges import nearest_display_edge

    try:
        cursor = np.asarray(display_xy, dtype=float).reshape(2)
    except Exception:
        return None
    best = None
    best_rank = None
    for loop in loops:
        centroid_xy = project(loop.centroid)
        if centroid_xy is None:
            continue
        try:
            centroid_xy = np.asarray(centroid_xy, dtype=float).reshape(2)
        except Exception:
            continue
        if float(np.linalg.norm(centroid_xy - cursor)) > gate_px:
            continue
        hit = nearest_display_edge(
            loop.points,
            loop_edge_pairs(loop),
            display_xy,
            project,
            tolerance_px=float(tolerance_px),
            depth_reference=None,
        )
        if hit is None:
            continue
        rank = (float(hit[4]), float(loop.area))
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best = loop
    return best
