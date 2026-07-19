"""Edge-entity picks for the Measure tool (bugs/0353) -- pure geometry, display-free.

The Measure tool is point-based: two snap POINTS make a segment.  0353 adds Alt+click
EDGE picks (mirroring the hover contract: plain=face, Alt=nearest drawn edge) so the
user can click one edge of an opening and then the other and read the clear width.
Every pick pair is REDUCED here to two world points before recording, so the existing
segment/label/offset-handle/persistence/STEP-export pipeline is untouched:

* edge + edge   -> the closest pair between the two polylines (for the parallel edges
                   of an opening this IS the clear width);
* point + edge  -> the closest point on the edge to the point (either order);
* point + point -> unchanged passthrough.

Closest-pair math is the standard clamped segment-segment algorithm (Ericson,
Real-Time Collision Detection 5.1.9), iterated over polyline segment pairs.  Drawn
edges carry at most a few dozen vertices, so the O(n*m) pairwise sweep is trivial.
"""

from __future__ import annotations

import numpy as np

# A pick is a dict: {"kind": "point", "world": (3,)} or {"kind": "edge", "polyline": (N,3)}.
MEASURE_PICK_POINT = "point"
MEASURE_PICK_EDGE = "edge"

_EPS = 1e-12


def _as_polyline(points) -> np.ndarray:
    arr = np.asarray(points, dtype=float).reshape(-1, 3)
    if arr.shape[0] == 0 or not np.all(np.isfinite(arr)):
        raise ValueError("degenerate polyline")
    return arr


def _segment_segment_closest(p1, q1, p2, q2):
    """Closest points between segments [p1,q1] and [p2,q2] (all (3,) float arrays)."""
    d1 = q1 - p1
    d2 = q2 - p2
    r = p1 - p2
    a = float(np.dot(d1, d1))
    e = float(np.dot(d2, d2))
    f = float(np.dot(d2, r))
    if a <= _EPS and e <= _EPS:
        return p1, p2
    if a <= _EPS:
        t = float(np.clip(f / e, 0.0, 1.0))
        return p1, p2 + t * d2
    c = float(np.dot(d1, r))
    if e <= _EPS:
        s = float(np.clip(-c / a, 0.0, 1.0))
        return p1 + s * d1, p2
    b = float(np.dot(d1, d2))
    denom = a * e - b * b
    # parallel segments fall to s=0; the t clamp below still lands the true
    # perpendicular pair whenever the segments overlap in projection
    s = float(np.clip((b * f - c * e) / denom, 0.0, 1.0)) if denom > _EPS else 0.0
    t = (b * s + f) / e
    if t < 0.0:
        t = 0.0
        s = float(np.clip(-c / a, 0.0, 1.0))
    elif t > 1.0:
        t = 1.0
        s = float(np.clip((b - c) / a, 0.0, 1.0))
    return p1 + s * d1, p2 + t * d2


def closest_point_on_polyline(polyline, point):
    """(q, dist): the closest point q on ``polyline`` ((N,3)) to ``point`` ((3,))."""
    arr = _as_polyline(polyline)
    p = np.asarray(point, dtype=float).reshape(3)
    if arr.shape[0] == 1:
        q = arr[0]
        return q.copy(), float(np.linalg.norm(p - q))
    best_q, best_d = None, np.inf
    for i in range(arr.shape[0] - 1):
        a, b = arr[i], arr[i + 1]
        d = b - a
        L2 = float(np.dot(d, d))
        t = 0.0 if L2 <= _EPS else float(np.clip(np.dot(p - a, d) / L2, 0.0, 1.0))
        q = a + t * d
        dist = float(np.linalg.norm(p - q))
        if dist < best_d:
            best_q, best_d = q, dist
    return best_q, best_d


def closest_points_between_polylines(polyline_a, polyline_b):
    """(pa, pb, dist): the closest pair between two polylines ((N,3) each).

    For the two parallel drawn edges of a rectangular opening the returned distance is
    the clear width of the opening.
    """
    a = _as_polyline(polyline_a)
    b = _as_polyline(polyline_b)
    if a.shape[0] == 1:
        q, d = closest_point_on_polyline(b, a[0])
        return a[0].copy(), q, d
    if b.shape[0] == 1:
        q, d = closest_point_on_polyline(a, b[0])
        return q, b[0].copy(), d
    best = (None, None, np.inf)
    for i in range(a.shape[0] - 1):
        for j in range(b.shape[0] - 1):
            pa, pb = _segment_segment_closest(a[i], a[i + 1], b[j], b[j + 1])
            dist = float(np.linalg.norm(pa - pb))
            if dist < best[2]:
                best = (pa, pb, dist)
    return best


def collinear_edge_run(points, pairs, seed_pair, *, angle_cos_min: float = 0.9995):
    """Extend an outline segment to its full straight run (bugs/0353).

    Drawn edges arrive as chains of short segments; a user clicking anywhere along a
    subdivided straight edge means the WHOLE edge.  From the picked ``seed_pair`` (an
    ``(i0, i1)`` index pair into ``points``) walk the shared-vertex chain in both
    directions while the step direction stays within ``angle_cos_min`` of the seed
    direction, and return the ordered run as an (M,3) array.  Corners (angle breaks),
    forks and chain ends stop the walk, so one straight side of a rounded-rectangle
    window comes back as one edge -- never the whole rim loop.
    """
    pts = np.asarray(points, dtype=float).reshape(-1, 3)
    i0, i1 = int(seed_pair[0]), int(seed_pair[1])
    seed_dir = pts[i1] - pts[i0]
    norm = float(np.linalg.norm(seed_dir))
    if norm <= _EPS:
        return pts[[i0, i1]]
    seed_dir = seed_dir / norm
    adjacency: dict[int, list[int]] = {}
    for a, b in pairs:
        a, b = int(a), int(b)
        adjacency.setdefault(a, []).append(b)
        adjacency.setdefault(b, []).append(a)

    def _walk(start: int, prev: int, direction: np.ndarray) -> list[int]:
        run: list[int] = []
        current, previous = start, prev
        visited = {previous, current}
        while True:
            candidates = []
            for nxt in adjacency.get(current, []):
                if nxt == previous or nxt in visited:
                    continue
                step = pts[nxt] - pts[current]
                length = float(np.linalg.norm(step))
                if length <= _EPS:
                    continue
                if float(np.dot(step / length, direction)) >= float(angle_cos_min):
                    candidates.append(nxt)
            if len(candidates) != 1:
                return run
            previous, current = current, candidates[0]
            visited.add(current)
            run.append(current)

    forward = _walk(i1, i0, seed_dir)
    backward = _walk(i0, i1, -seed_dir)
    ordered = list(reversed(backward)) + [i0, i1] + forward
    return pts[np.asarray(ordered, dtype=int)]


def measure_point_pick(world) -> dict:
    return {"kind": MEASURE_PICK_POINT, "world": tuple(float(v) for v in np.asarray(world, dtype=float).reshape(3))}


def measure_edge_pick(polyline) -> dict:
    return {"kind": MEASURE_PICK_EDGE, "polyline": _as_polyline(polyline)}


def reduce_measure_picks(first: dict, second: dict):
    """Reduce any pick pair to ``(point_a, point_b, dist)`` world points for recording.

    The reduction keeps plain point+point picks byte-identical (pure passthrough), so
    only pairs involving an edge gain the closest-pair behaviour.
    """
    ka = str(first.get("kind", MEASURE_PICK_POINT))
    kb = str(second.get("kind", MEASURE_PICK_POINT))
    if ka == MEASURE_PICK_POINT and kb == MEASURE_PICK_POINT:
        pa = np.asarray(first["world"], dtype=float).reshape(3)
        pb = np.asarray(second["world"], dtype=float).reshape(3)
        return pa, pb, float(np.linalg.norm(pa - pb))
    if ka == MEASURE_PICK_POINT:
        pa = np.asarray(first["world"], dtype=float).reshape(3)
        pb, dist = closest_point_on_polyline(second["polyline"], pa)
        return pa, pb, dist
    if kb == MEASURE_PICK_POINT:
        pb = np.asarray(second["world"], dtype=float).reshape(3)
        pa, dist = closest_point_on_polyline(first["polyline"], pb)
        return pa, pb, dist
    return closest_points_between_polylines(first["polyline"], second["polyline"])
