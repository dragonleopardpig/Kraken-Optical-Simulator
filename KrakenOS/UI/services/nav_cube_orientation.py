"""Pure orientation math for the Open 3D navigation cube (no VTK).

The cube is a unit cube spanning ``[-0.5, 0.5]^3`` in its own local frame, whose
axes coincide with world X/Y/Z. A left-click on the cube surface is picked to a
LOCAL hit point; :func:`classify_pick` turns that point into one of 26
orientations (6 faces, 12 edges, 8 corners), each identified by a sign triple in
``{-1, 0, 1}^3`` (never all zero). :func:`orientation_pose` maps a sign triple to
the camera pose ``(offset_unit, view_up)``: the camera sits at
``center + offset_unit * distance`` looking at the center with ``view_up`` up.

Faces reproduce the six cardinal presets in
``open3d_inspector.set_camera_preset`` EXACTLY, so clicking a cube face is
identical to pressing the matching ``+YZ``/``-YZ``/... toolbar button::

    +X face -> +yz    -X -> -yz    +Z -> +xy    -Z -> -xy    +Y -> +xz    -Y -> -xz

Edges and corners use a projected-up rule: the scene's visual vertical (world
``+Y``) projected onto the plane perpendicular to the view direction, so the
oblique ("angled") views stay upright; when the view runs along ``+/-Y`` the
fallback vertical is world ``+Z``.

CAD face labels (the user's choice): ``+Z = FRONT``, ``+Y = TOP``, ``+X = RIGHT``
and their opposites.
"""
from __future__ import annotations

from itertools import product

import numpy as np

# Outward axis sign triple -> CAD face label for the annotated cube.
FACE_LABELS: dict[tuple[int, int, int], str] = {
    (1, 0, 0): "RIGHT",
    (-1, 0, 0): "LEFT",
    (0, 1, 0): "TOP",
    (0, -1, 0): "BOTTOM",
    (0, 0, 1): "FRONT",
    (0, 0, -1): "BACK",
}

# Face poses == the six cardinal presets: (offset_unit, view_up).
_FACE_POSE: dict[tuple[int, int, int], tuple[tuple[float, float, float], tuple[float, float, float]]] = {
    (1, 0, 0): ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),    # +yz
    (-1, 0, 0): ((-1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),  # -yz
    (0, 0, 1): ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),    # +xy
    (0, 0, -1): ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),  # -xy
    (0, 1, 0): ((0.0, 1.0, 0.0), (1.0, 0.0, 0.0)),    # +xz  (TOP)
    (0, -1, 0): ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0)),  # -xz  (BOTTOM)
}

# All 26 orientations: every sign triple in {-1,0,1}^3 except the origin.
ORIENTATION_KEYS: tuple[tuple[int, int, int], ...] = tuple(
    triple for triple in product((-1, 0, 1), repeat=3) if any(triple)
)

_WORLD_UP = np.array([0.0, 1.0, 0.0])
_WORLD_UP_FALLBACK = np.array([0.0, 0.0, 1.0])


def orientation_kind(sign) -> str:
    """``"face"`` / ``"edge"`` / ``"corner"`` from the count of extreme axes."""
    extremes = sum(1 for s in sign if s)
    return {1: "face", 2: "edge", 3: "corner"}.get(extremes, "none")


def classify_pick(local_point, edge_fraction: float = 0.30):
    """Sign triple in ``{-1,0,1}^3`` for a local hit point in ``[-0.5, 0.5]^3``.

    A coordinate is "extreme" (``+/-1``) when it lies within ``edge_fraction`` of
    its ``+/-0.5`` face; otherwise it is "mid" (``0``). One extreme axis -> face,
    two -> edge, three -> corner. Returns ``None`` when the point is not on/near
    the cube surface (no extreme axis) so the caller can ignore stray picks.
    """
    point = np.asarray(local_point, dtype=float).reshape(3)
    threshold = 0.5 * (1.0 - float(edge_fraction))
    sign = tuple(int(np.sign(coord)) if abs(coord) >= threshold else 0 for coord in point)
    if not any(sign):
        return None
    return sign


def _projected_up(offset_unit) -> np.ndarray:
    """World vertical projected perpendicular to the view direction (upright up)."""
    look = -np.asarray(offset_unit, dtype=float)
    norm = float(np.linalg.norm(look))
    look = look / norm if norm > 1e-12 else look
    for preferred in (_WORLD_UP, _WORLD_UP_FALLBACK):
        up = preferred - float(np.dot(preferred, look)) * look
        up_norm = float(np.linalg.norm(up))
        if up_norm > 1e-6:
            return up / up_norm
    return np.array([1.0, 0.0, 0.0])


def orientation_pose(sign):
    """``(offset_unit, view_up)`` unit tuples for a sign triple from a pick.

    Faces return their cardinal-preset pose verbatim; edges/corners return the
    normalized outward direction with a projected, upright view-up.
    """
    key = tuple(int(s) for s in sign)
    if key in _FACE_POSE:
        offset, view_up = _FACE_POSE[key]
        return (tuple(offset), tuple(view_up))
    offset = np.asarray(key, dtype=float)
    norm = float(np.linalg.norm(offset))
    offset = offset / norm if norm > 1e-12 else offset
    view_up = _projected_up(offset)
    return (
        tuple(float(v) for v in offset),
        tuple(float(v) for v in view_up),
    )


def roll_view_up(view_direction, view_up, angle_deg: float):
    """Rotate ``view_up`` about the sight line by ``angle_deg`` (discrete roll).

    Rodrigues rotation of the up vector about the (normalized) view direction --
    the pure-math twin of ``vtkCamera.Roll`` used by the cube's discrete
    rotation-step arrows so a step can be predicted/tested without VTK.
    """
    axis = np.asarray(view_direction, dtype=float)
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm <= 1e-12:
        return tuple(float(v) for v in view_up)
    axis = axis / axis_norm
    up = np.asarray(view_up, dtype=float)
    angle = np.radians(float(angle_deg))
    rotated = (
        up * np.cos(angle)
        + np.cross(axis, up) * np.sin(angle)
        + axis * float(np.dot(axis, up)) * (1.0 - np.cos(angle))
    )
    rotated_norm = float(np.linalg.norm(rotated))
    if rotated_norm > 1e-12:
        rotated = rotated / rotated_norm
    return tuple(float(v) for v in rotated)
