"""Geometry helpers for Open 3D CAD/STL face picking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass(frozen=True, slots=True)
class FaceRayPick:
    """Resolved face hit from a ray cast through a transparent CAD body."""

    face: dict[str, object]
    point_world: tuple[float, float, float]
    normal_world: tuple[float, float, float]
    distance: float
    internal: bool = False


def _unit_vector(values) -> np.ndarray | None:
    try:
        vector = np.asarray(values, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if vector.size < 3 or not np.all(np.isfinite(vector[:3])):
        return None
    norm = float(np.linalg.norm(vector[:3]))
    if not np.isfinite(norm) or norm <= 1e-12:
        return None
    return np.asarray(vector[:3] / norm, dtype=float)


def _nonnegative_indices(values: object) -> tuple[int, ...]:
    result: list[int] = []
    try:
        iterable = values if isinstance(values, Iterable) and not isinstance(values, (str, bytes)) else ()
    except Exception:
        iterable = ()
    for value in iterable:
        try:
            index = int(value)
        except Exception:
            continue
        if index >= 0:
            result.append(index)
    return tuple(result)


def _face_triangle_indices(face: dict[str, object]) -> tuple[int, ...]:
    return _nonnegative_indices(face.get("triangle_indices", face.get("cell_indices", ())))


def _ray_triangles_nearest_hit(origin: np.ndarray, direction: np.ndarray, triangles: np.ndarray):
    """Vectorized Moller-Trumbore: nearest forward hit over an (N,3,3) batch.

    Replaces a per-triangle Python loop that dominated round-lens hover --
    a ~114k-triangle body intersected every triangle one at a time on each
    mouse move (~1.7 s). Returns ``(distance, point, triangle)`` for the
    closest non-negative intersection, or ``None``.
    """
    tris = np.asarray(triangles, dtype=float)
    if tris.ndim != 3 or tris.shape[1:] != (3, 3) or tris.shape[0] == 0:
        return None
    v0 = tris[:, 0, :3]
    edge1 = tris[:, 1, :3] - v0
    edge2 = tris[:, 2, :3] - v0
    pvec = np.cross(direction[:3], edge2)
    det = np.einsum("ij,ij->i", edge1, pvec)
    valid = np.isfinite(det) & (np.abs(det) > 1e-10)
    if not np.any(valid):
        return None
    inv_det = np.zeros_like(det)
    inv_det[valid] = 1.0 / det[valid]
    tvec = origin[:3] - v0
    u = np.einsum("ij,ij->i", tvec, pvec) * inv_det
    qvec = np.cross(tvec, edge1)
    v = np.einsum("j,ij->i", direction[:3], qvec) * inv_det
    distance = np.einsum("ij,ij->i", edge2, qvec) * inv_det
    mask = (
        valid
        & (u >= -1e-8)
        & (u <= 1.0 + 1e-8)
        & (v >= -1e-8)
        & (u + v <= 1.0 + 1e-8)
        & np.isfinite(distance)
        & (distance >= -1e-8)
    )
    if not np.any(mask):
        return None
    masked_distance = np.where(mask, distance, np.inf)
    idx = int(np.argmin(masked_distance))
    if not np.isfinite(masked_distance[idx]):
        return None
    dist = max(float(distance[idx]), 0.0)
    point = origin[:3] + dist * direction[:3]
    if not np.all(np.isfinite(point[:3])):
        return None
    return dist, np.asarray(point[:3], dtype=float), np.asarray(tris[idx], dtype=float)


def _face_normal(face: dict[str, object], fallback_triangle: np.ndarray | None = None) -> np.ndarray | None:
    for key in ("normal_world", "normal"):
        normal = _unit_vector(face.get(key))
        if normal is not None:
            if bool(face.get("flip_normal", False)):
                normal = -normal
            return normal
    if fallback_triangle is None:
        return None
    try:
        tri = np.asarray(fallback_triangle, dtype=float).reshape(3, 3)
    except Exception:
        return None
    return _unit_vector(np.cross(tri[1] - tri[0], tri[2] - tri[0]))


def _face_is_internal(face: dict[str, object], all_points: np.ndarray | None, face_triangles: np.ndarray) -> bool:
    points = np.asarray(all_points if all_points is not None else face_triangles.reshape((-1, 3)), dtype=float)
    if points.ndim != 2 or points.shape[0] < 4 or points.shape[1] < 3:
        return False
    normal = _face_normal(face, face_triangles[0] if face_triangles.size else None)
    if normal is None:
        return False
    projections = points[:, :3] @ normal[:3]
    finite = projections[np.isfinite(projections)]
    if finite.size < 4:
        return False
    face_points = np.asarray(face_triangles, dtype=float).reshape((-1, 3))
    if face_points.size == 0:
        return False
    face_projection = float(np.nanmean(face_points[:, :3] @ normal[:3]))
    span = float(np.max(finite) - np.min(finite))
    margin = max(span * 2.0e-4, 0.02)
    return bool(face_projection > float(np.min(finite)) + margin and face_projection < float(np.max(finite)) - margin)


def pick_face_from_ray(
    faces: Iterable[dict[str, object]],
    triangles,
    ray_origin,
    ray_direction,
    *,
    all_points=None,
    prefer_internal: bool = True,
) -> FaceRayPick | None:
    """Pick the best CAD face intersected by a display ray.

    Transparent optical solids often contain internal planes. Toolkit pickers
    normally return the first exterior face along the camera ray, so this helper
    intersects the ray with every known face triangle and can prefer an internal
    plane over the nearer shell hit.
    """
    origin = np.asarray(ray_origin, dtype=float).reshape(-1)[:3]
    direction = _unit_vector(ray_direction)
    triangle_array = np.asarray(triangles, dtype=float)
    if (
        origin.size < 3
        or direction is None
        or not np.all(np.isfinite(origin[:3]))
        or triangle_array.ndim != 3
        or triangle_array.shape[1:] != (3, 3)
        or triangle_array.shape[0] == 0
    ):
        return None
    try:
        all_point_array = np.asarray(all_points, dtype=float).reshape((-1, 3)) if all_points is not None else triangle_array.reshape((-1, 3))
    except Exception:
        all_point_array = triangle_array.reshape((-1, 3))

    candidates: list[tuple[int, float, int, FaceRayPick]] = []
    for order, face in enumerate(list(faces or [])):
        if not isinstance(face, dict):
            continue
        indices = [index for index in _face_triangle_indices(face) if 0 <= index < int(triangle_array.shape[0])]
        if not indices:
            continue
        face_triangles = np.asarray(triangle_array[np.asarray(indices, dtype=int)], dtype=float)
        best_hit = _ray_triangles_nearest_hit(origin[:3], direction[:3], face_triangles)
        if best_hit is None:
            continue
        normal = _face_normal(face, best_hit[2])
        if normal is None:
            continue
        internal = _face_is_internal(face, all_point_array, face_triangles)
        rank = 0 if prefer_internal and internal else 1
        pick = FaceRayPick(
            face=dict(face),
            point_world=tuple(float(value) for value in best_hit[1][:3]),
            normal_world=tuple(float(value) for value in normal[:3]),
            distance=float(best_hit[0]),
            internal=bool(internal),
        )
        candidates.append((rank, float(best_hit[0]), int(order), pick))
    if not candidates:
        return None
    candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return candidates[0][3]
