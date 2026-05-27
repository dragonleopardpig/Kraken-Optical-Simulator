"""Ray-display geometry helpers shared by 2D and Open 3D views."""

from __future__ import annotations

import numpy as np


def _finite_polyline_points(polyline: np.ndarray) -> np.ndarray:
    pts = np.asarray(polyline, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return np.empty((0, 3), dtype=float)
    pts = pts[:, :3]
    return pts[np.all(np.isfinite(pts), axis=1)]


def _convex_hull_indices_2d(points_2d: np.ndarray, *, tolerance: float = 1e-9) -> set[int]:
    pts = np.asarray(points_2d, dtype=float)
    if pts.ndim != 2 or pts.shape[0] == 0 or pts.shape[1] < 2:
        return set()
    finite_mask = np.all(np.isfinite(pts[:, :2]), axis=1)
    if not np.any(finite_mask):
        return set()
    original_indices = np.flatnonzero(finite_mask)
    pts = pts[finite_mask, :2]
    if pts.shape[0] <= 2:
        return {int(index) for index in original_indices}
    span = np.ptp(pts, axis=0)
    if float(np.linalg.norm(span)) <= tolerance:
        return {int(original_indices[0])}

    order = sorted(range(pts.shape[0]), key=lambda idx: (float(pts[idx, 0]), float(pts[idx, 1]), idx))

    def cross(o: int, a: int, b: int) -> float:
        return float(
            (pts[a, 0] - pts[o, 0]) * (pts[b, 1] - pts[o, 1])
            - (pts[a, 1] - pts[o, 1]) * (pts[b, 0] - pts[o, 0])
        )

    lower: list[int] = []
    for idx in order:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], idx) <= tolerance:
            lower.pop()
        lower.append(idx)
    upper: list[int] = []
    for idx in reversed(order):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], idx) <= tolerance:
            upper.pop()
        upper.append(idx)
    hull_local = lower[:-1] + upper[:-1]
    if not hull_local:
        return {int(original_indices[order[0]]), int(original_indices[order[-1]])}
    return {int(original_indices[idx]) for idx in hull_local}


def _ray_group_envelope_indices(polylines: list[np.ndarray]) -> set[int]:
    """Return boundary-ray indices for one launch group.

    STEP export is for mechanical envelope review, not optical debugging. The
    useful geometry is therefore the outside of the traced bundle. We select
    convex-hull rays in launch-position, launch-direction, and terminal-position
    spaces so meridional fans collapse to two edge rays, cross fans to four
    edge rays, and split/non-sequential paths still keep branch extremes.
    """
    starts: list[np.ndarray] = []
    ends: list[np.ndarray] = []
    directions: list[np.ndarray] = []
    point_counts: list[int] = []
    valid_indices: list[int] = []
    for index, polyline in enumerate(polylines):
        finite = _finite_polyline_points(polyline)
        if finite.shape[0] < 2:
            continue
        deltas = np.diff(finite, axis=0)
        lengths = np.linalg.norm(deltas, axis=1)
        direction = np.zeros(3, dtype=float)
        for delta, length in zip(deltas, lengths):
            if float(length) > 1e-9:
                direction = delta / float(length)
                break
        starts.append(finite[0])
        ends.append(finite[-1])
        directions.append(direction)
        point_counts.append(int(finite.shape[0]))
        valid_indices.append(index)

    if not valid_indices:
        return set()
    if len(valid_indices) <= 4:
        return set(valid_indices)

    candidate_local_indices = list(range(len(valid_indices)))
    counts = np.asarray(point_counts, dtype=int)
    if counts.size:
        max_count = int(np.max(counts))
        min_count = int(np.min(counts))
        longest = [idx for idx, count in enumerate(counts) if int(count) == max_count]
        if max_count > min_count and len(longest) >= max(2, int(np.ceil(0.5 * len(valid_indices)))):
            # In sequential layouts, clipped rays usually have fewer recorded
            # hit points than rays reaching the image/analysis plane. For
            # mechanical envelope export, prefer the through-going envelope
            # when it is the dominant ray population.
            candidate_local_indices = longest
    if len(candidate_local_indices) <= 4:
        return {int(valid_indices[idx]) for idx in candidate_local_indices}

    selected: set[int] = set()
    spaces = (
        np.asarray([starts[idx] for idx in candidate_local_indices], dtype=float)[:, :2],
        np.asarray([directions[idx] for idx in candidate_local_indices], dtype=float)[:, :2],
        np.asarray([ends[idx] for idx in candidate_local_indices], dtype=float)[:, :2],
    )
    for points in spaces:
        for local_idx in _convex_hull_indices_2d(points):
            if 0 <= local_idx < len(candidate_local_indices):
                selected.add(int(valid_indices[candidate_local_indices[local_idx]]))

    if not selected:
        start_arr = np.asarray([starts[idx] for idx in candidate_local_indices], dtype=float)
        end_arr = np.asarray([ends[idx] for idx in candidate_local_indices], dtype=float)
        radii = np.linalg.norm(start_arr[:, :2] - np.mean(start_arr[:, :2], axis=0), axis=1)
        if float(np.ptp(radii)) <= 1e-9:
            radii = np.linalg.norm(end_arr[:, :2] - np.mean(end_arr[:, :2], axis=0), axis=1)
        selected.add(int(valid_indices[candidate_local_indices[int(np.argmin(radii))]]))
        selected.add(int(valid_indices[candidate_local_indices[int(np.argmax(radii))]]))
    return selected


def _ray_bundle_envelope_polylines(polylines: list[np.ndarray], rays_per_group: int | None) -> list[np.ndarray]:
    clean_polylines: list[np.ndarray] = []
    for polyline in polylines:
        pts = np.asarray(polyline, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
            continue
        clean_polylines.append(pts[:, :3].copy())
    if len(clean_polylines) <= 4:
        return clean_polylines
    group_size = int(rays_per_group or 0)
    if group_size <= 0:
        group_size = len(clean_polylines)

    selected_global: set[int] = set()
    for start in range(0, len(clean_polylines), group_size):
        group = clean_polylines[start:start + group_size]
        for local_idx in _ray_group_envelope_indices(group):
            selected_global.add(start + int(local_idx))
    if not selected_global:
        return clean_polylines
    envelope: list[np.ndarray] = []
    seen: set[tuple[tuple[int, int], tuple[float, ...]]] = set()
    for index in sorted(selected_global):
        polyline = clean_polylines[index]
        finite = _finite_polyline_points(polyline)
        key_values = tuple(np.round(finite.ravel(), decimals=9).tolist())
        key = ((int(finite.shape[0]), int(finite.shape[1]) if finite.ndim == 2 else 0), key_values)
        if key in seen:
            continue
        seen.add(key)
        envelope.append(polyline)
    return envelope


def _raykeeper_branch_path_strings(rays) -> list[str]:
    branch_paths: list[str] = []
    raw_paths = getattr(rays, "BRANCH_PATH", [])
    if raw_paths is None:
        raw_paths = []
    for value in list(raw_paths):
        try:
            array = np.asarray(value, dtype=object).reshape(-1)
        except Exception:
            array = np.asarray([], dtype=object)
        if array.size:
            branch_paths.append(str(array[-1] or "").strip())
        else:
            branch_paths.append(str(value or "").strip())
    return branch_paths


def _raykeeper_has_non_primary_branch_paths(rays, *, expected_launch_count: int | None = None) -> bool:
    branch_paths = _raykeeper_branch_path_strings(rays)
    if any(path and path != "primary" for path in branch_paths):
        return True
    if expected_launch_count is not None:
        try:
            raw_paths = getattr(rays, "CC", [])
            traced_count = len(raw_paths) if raw_paths is not None else 0
        except Exception:
            traced_count = 0
        try:
            launch_count = int(expected_launch_count)
        except Exception:
            launch_count = 0
        if launch_count > 0 and traced_count > launch_count:
            return True
    return False


def _finite_bounds_array(bounds) -> np.ndarray:
    try:
        b = np.asarray(bounds, dtype=float).reshape(-1)
    except Exception:
        b = np.asarray([], dtype=float)
    if b.size != 6 or not np.all(np.isfinite(b)) or b[0] > b[1] or b[2] > b[3] or b[4] > b[5]:
        b = np.asarray([-10.0, 10.0, -10.0, 10.0, 0.0, 100.0], dtype=float)
    return b


def _bounds_span(bounds) -> float:
    b = _finite_bounds_array(bounds)
    span = max(float(b[1] - b[0]), float(b[3] - b[2]), float(b[5] - b[4]), 20.0)
    return float(span)


def _optical_axis_z_span(bounds) -> tuple[float, float]:
    b = _finite_bounds_array(bounds)
    span = _bounds_span(b)
    z0 = min(float(b[4]), 0.0) - 0.65 * span
    z1 = max(float(b[5]), 0.0) + 0.65 * span
    if z1 <= z0:
        z1 = z0 + max(span, 20.0)
    return float(z0), float(z1)


def _extended_axis_points(point, direction, bounds) -> np.ndarray | None:
    try:
        origin = np.asarray(point, dtype=float).reshape(-1)[:3]
        vector = np.asarray(direction, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if origin.size < 3 or vector.size < 3 or not np.all(np.isfinite(origin[:3])) or not np.all(np.isfinite(vector[:3])):
        return None
    norm = float(np.linalg.norm(vector[:3]))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    vector = vector[:3] / norm
    span = _bounds_span(bounds)
    half = max(0.85 * span, 10.0)
    return np.vstack((origin[:3] - vector * half, origin[:3] + vector * half))


def _clean_polyline_points(points) -> np.ndarray:
    try:
        pts = np.asarray(points, dtype=float)
    except Exception:
        return np.empty((0, 3), dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 3:
        return np.empty((0, 3), dtype=float)
    clean: list[np.ndarray] = []
    for point in pts[:, :3]:
        if not np.all(np.isfinite(point)):
            continue
        if clean and float(np.linalg.norm(point - clean[-1])) <= 1e-8:
            continue
        clean.append(np.asarray(point, dtype=float))
    if len(clean) < 2:
        return np.empty((0, 3), dtype=float)
    return np.vstack(clean)


def _dotted_axis_records_from_ray_path(path, bounds, *, max_segments: int = 6) -> list[dict[str, object]]:
    points = _clean_polyline_points(getattr(path, "points_world", np.empty((0, 3))))
    if points.shape[0] < 2:
        return []
    surface_events = [
        event
        for event in list(getattr(path, "events", []) or [])
        if str(getattr(event, "event_kind", "") or "") == "surface"
    ]
    records: list[dict[str, object]] = []
    seen: set[tuple[float, ...]] = set()
    try:
        ray_index = int(getattr(path, "ray_index", -1))
    except Exception:
        ray_index = -1
    branch_path = str(getattr(path, "branch_path", "") or "")
    source_id = str(getattr(path, "source_id", "") or "")

    def _event_surface_index(event) -> int | None:
        try:
            value = getattr(event, "surface_id", None)
            return None if value is None else int(value)
        except Exception:
            return None

    def _is_external_between_surface_axis(event_before, event_after) -> bool:
        if event_before is None or event_after is None:
            return False
        before_surface = _event_surface_index(event_before)
        after_surface = _event_surface_index(event_after)
        if before_surface is None or after_surface is None or before_surface == after_surface:
            return False
        before_inside = str(getattr(event_before, "inside_volumes_after", "") or "").strip()
        after_inside = str(getattr(event_after, "inside_volumes_before", "") or "").strip()
        if before_inside and before_inside == after_inside:
            return False
        before_action = str(getattr(event_before, "event_type", "") or "").strip().lower()
        after_action = str(getattr(event_after, "event_type", "") or "").strip().lower()
        if before_action in {"reflection", "reflect", "reflect_mirror", "reflect_tir", "scatter", "absorb", "absorption"}:
            return False
        if after_action in {"reflection", "reflect", "reflect_mirror", "reflect_tir", "scatter", "absorb", "absorption"}:
            return False
        return True

    for index, (start, end) in enumerate(zip(points[:-1], points[1:]), start=1):
        event_before = surface_events[index - 2] if 0 <= index - 2 < len(surface_events) else None
        event_after = surface_events[index - 1] if 0 <= index - 1 < len(surface_events) else None
        if event_before is None:
            axis_role = "launch_segment"
        elif event_after is None:
            axis_role = "post_surface"
        else:
            axis_role = "between_surfaces"
        if axis_role == "launch_segment":
            continue
        if axis_role == "between_surfaces" and not _is_external_between_surface_axis(event_before, event_after):
            continue
        direction = end - start
        length = float(np.linalg.norm(direction))
        if not np.isfinite(length) or length <= 1e-6:
            continue
        direction = direction / length
        from_face = str(getattr(event_before, "mesh_face_id", "") or "") if event_before is not None else ""
        to_face = str(getattr(event_after, "mesh_face_id", "") or "") if event_after is not None else ""
        if float(np.hypot(direction[0], direction[1])) <= 1e-4:
            keep_axial_solid_exit = (
                (axis_role == "between_surfaces" and bool(from_face or to_face))
                or (axis_role == "post_surface" and bool(from_face))
            )
            if not keep_axial_solid_exit:
                continue
        axis_origin = 0.5 * (start + end)
        if axis_role == "post_surface":
            span = _bounds_span(bounds)
            # Escaped non-sequential paths can carry a long synthetic terminal
            # tail. Anchor the pickable optical-axis guide near the last real
            # surface event instead of at that tail's midpoint, otherwise the
            # guide can poison camera-fit bounds by many orders of magnitude.
            offset = min(length * 0.5, max(0.08 * span, 2.0))
            axis_origin = start + direction * offset
        axis_points = _extended_axis_points(axis_origin, direction, bounds)
        if axis_points is None:
            continue
        key = tuple(np.round(np.concatenate((axis_points[0], axis_points[1])), 5))
        reverse_key = tuple(np.round(np.concatenate((axis_points[1], axis_points[0])), 5))
        if key in seen or reverse_key in seen:
            continue
        seen.add(key)
        from_surface = getattr(event_before, "surface_id", None) if event_before is not None else None
        to_surface = getattr(event_after, "surface_id", None) if event_after is not None else None
        from_action = str(getattr(event_before, "event_type", "") or "") if event_before is not None else ""
        to_action = str(getattr(event_after, "event_type", "") or "") if event_after is not None else ""
        records.append(
            {
                "axis_id": f"axis:ray:{ray_index}:segment:{index}",
                "axis_label": f"Optical Axis {len(records) + 2}",
                "axis_kind": "traced_chief_ray_segment",
                "axis_role": axis_role,
                "branch_path": branch_path,
                "source_id": source_id,
                "ray_index": ray_index,
                "segment_index": int(index),
                "segment_start": tuple(float(value) for value in start[:3]),
                "segment_end": tuple(float(value) for value in end[:3]),
                "segment_midpoint": tuple(float(value) for value in (0.5 * (start + end))[:3]),
                "segment_direction": tuple(float(value) for value in direction[:3]),
                "from_surface_id": None if from_surface is None else int(from_surface),
                "to_surface_id": None if to_surface is None else int(to_surface),
                "from_mesh_face_id": from_face,
                "to_mesh_face_id": to_face,
                "from_event_type": from_action,
                "to_event_type": to_action,
                "points": axis_points,
            }
        )
        if len(records) >= int(max_segments):
            break
    return records
