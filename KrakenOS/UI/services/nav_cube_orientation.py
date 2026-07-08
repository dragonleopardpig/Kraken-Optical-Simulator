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

Edges use a projected-up rule: the scene's visual vertical (world ``+Y``)
projected onto the plane perpendicular to the view direction, so the oblique
("angled") views stay upright; when the view runs along ``+/-Y`` the fallback
vertical is world ``+Z``.

Corners reproduce the ISO toolbar view for their octant (bugs/0252): the world
UP axis takes a small ``0.55`` elevation and the other two axes the ``0.95`` /
``0.8`` horizontal spread (mirroring
``open3d_inspector._iso_camera_offset_and_view_up``), each carrying the picked
octant's sign, with ``view_up`` world ``+Y``. So all 8 corners frame the scene
the same upright, wide-screen-friendly way the ISO button does -- instead of a
steeper symmetric ``(+-1, +-1, +-1)`` diagonal.

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

# bugs/0252 -- ISO-style corner weights. Mirrors
# ``open3d_inspector._iso_camera_offset_and_view_up``: the world UP axis takes the
# small +0.55 elevation and the other two axes the 0.95 / 0.8 horizontal spread, so a
# corner reproduces the ISO toolbar view for its octant (world-+Y up) rather than a
# steeper symmetric diagonal. The ISO octant (-1,+1,+1) yields exactly (-0.95,0.55,0.8).
_ISO_UP_WEIGHT = 0.55
_ISO_HORIZONTAL_WEIGHTS = (0.95, 0.8)
_ISO_UP_AXIS_INDEX = {"x": 0, "y": 1, "z": 2}


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


def iso_corner_pose(sign, up_axis: str = "y"):
    """``(offset_unit, view_up)`` for a CORNER, matching the ISO toolbar view (bugs/0252).

    The chosen world ``up_axis`` takes the small ``0.55`` elevation; the other two axes
    carry the ``0.95`` / ``0.8`` horizontal spread, each with the picked octant's sign.
    ``view_up`` is that world up axis. Reproduces
    ``open3d_inspector._iso_camera_offset_and_view_up`` so a corner is the ISO view for
    its octant (the ISO octant ``(-1,+1,+1)`` gives exactly ``(-0.95,0.55,0.8)`` normalized).
    """
    axis = _ISO_UP_AXIS_INDEX.get(str(up_axis or "y").strip().lower(), 1)
    others = [i for i in (0, 1, 2) if i != axis]
    triple = tuple(int(np.sign(s)) or 1 for s in np.asarray(sign, dtype=float).reshape(3))
    offset = np.zeros(3, dtype=float)
    offset[axis] = triple[axis] * _ISO_UP_WEIGHT
    offset[others[0]] = triple[others[0]] * _ISO_HORIZONTAL_WEIGHTS[0]
    offset[others[1]] = triple[others[1]] * _ISO_HORIZONTAL_WEIGHTS[1]
    norm = float(np.linalg.norm(offset))
    if norm > 1e-12:
        offset = offset / norm
    view_up = tuple(1.0 if i == axis else 0.0 for i in range(3))
    return (tuple(float(v) for v in offset), view_up)


def orientation_pose(sign, up_axis: str = "y"):
    """``(offset_unit, view_up)`` unit tuples for a sign triple from a pick.

    Faces return their cardinal-preset pose verbatim; corners return the ISO-style
    per-octant pose (bugs/0252); edges return the normalized outward direction with a
    projected, upright view-up.
    """
    key = tuple(int(s) for s in sign)
    if key in _FACE_POSE:
        offset, view_up = _FACE_POSE[key]
        return (tuple(offset), tuple(view_up))
    if orientation_kind(key) == "corner":
        return iso_corner_pose(key, up_axis=up_axis)
    offset = np.asarray(key, dtype=float)
    norm = float(np.linalg.norm(offset))
    offset = offset / norm if norm > 1e-12 else offset
    view_up = _projected_up(offset)
    return (
        tuple(float(v) for v in offset),
        tuple(float(v) for v in view_up),
    )


def _newell_normal(points, idxs) -> np.ndarray:
    """Outward polygon normal via Newell's method (robust for planar polygons)."""
    n = np.zeros(3)
    m = len(idxs)
    for i in range(m):
        a = np.asarray(points[idxs[i]], dtype=float)
        b = np.asarray(points[idxs[(i + 1) % m]], dtype=float)
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    return n


def chamfered_cube_facets(
    half: float = 0.5,
    face_fraction: float = 0.74,
    corner_fraction: float = 0.44,
):
    """Geometry for a FreeCAD-style CHAMFERED navigation cube.

    A cube of half-extent ``half`` with both its 12 edges AND 8 corners bevelled, so the
    surface is exactly 26 flat facets -- one per orientation: 6 face OCTAGONS, 12 edge
    RECTANGLES, 8 corner HEXAGONS, sharing 48 vertices. Cutting the corners (not just the
    edges) turns each corner into a bigger, easier-to-click hexagon and each face into an
    octagon -- exactly FreeCAD's navigation cube (bugs/0253).

    Two knobs in (0, 1), with ``corner_fraction < face_fraction``:
      * ``face_fraction`` -- the octagon's flat half-width along an axis is
        ``p = face_fraction * half`` (bigger -> larger faces, thinner chamfers).
      * ``corner_fraction`` -- the corner cut starts ``q = corner_fraction * half`` from each
        axis (smaller -> bigger corner hexagons / longer octagon diagonal cuts).

    Every vertex is a signed permutation of the magnitudes ``(half, p, q)`` (all distinct), so
    there are exactly ``3! * 2**3 = 48`` of them, each shared by one face, one edge and one
    corner facet.

    Returns ``(points, facets)``: ``points`` is a list of 48 ``(x, y, z)`` vertices and
    ``facets`` a list of ``(point_indices, sign)`` in FACE, then EDGE, then CORNER order.
    ``sign`` is the ``{-1,0,1}^3`` triple :func:`orientation_pose` maps to a camera pose, so a
    picked facet's orientation is a direct table lookup (no threshold on the hit point). Each
    facet is wound so its polygon normal points outward (along ``sign``).
    """
    A = float(half)
    p = A * float(face_fraction)      # octagon flat half-width (was the square half-width)
    q = A * float(corner_fraction)    # corner-cut inset (starts the octagon's diagonal cut)

    points: list[tuple[float, float, float]] = []
    index: dict[tuple, int] = {}

    def vid(coord) -> int:
        key = tuple(round(float(c), 6) for c in coord)
        got = index.get(key)
        if got is None:
            got = len(points)
            index[key] = got
            points.append((float(coord[0]), float(coord[1]), float(coord[2])))
        return got

    def outward(idxs, sign):
        normal = _newell_normal(points, idxs)
        if float(np.dot(normal, np.asarray(sign, dtype=float))) < 0.0:
            idxs = list(reversed(idxs))
        return list(idxs)

    def at(a, va, o0, v0, o1, v1) -> int:
        """Vertex with axis ``a`` = ``va`` and the other two axes ``o0``/``o1`` = ``v0``/``v1``."""
        coord = [0.0, 0.0, 0.0]
        coord[a] = va
        coord[o0] = v0
        coord[o1] = v1
        return vid(coord)

    facets: list[tuple[list[int], tuple[int, int, int]]] = []
    axes = (0, 1, 2)

    # --- 6 FACES: the axis-'a' face at a = sa*A is an OCTAGON (square of half-width p with
    #     its four corners cut back to the inset q) ---------------------------------------
    for a in axes:
        o0, o1 = [ax for ax in axes if ax != a]
        for sa in (1, -1):
            octa = [
                at(a, sa * A, o0, p, o1, q), at(a, sa * A, o0, q, o1, p),
                at(a, sa * A, o0, -q, o1, p), at(a, sa * A, o0, -p, o1, q),
                at(a, sa * A, o0, -p, o1, -q), at(a, sa * A, o0, -q, o1, -p),
                at(a, sa * A, o0, q, o1, -p), at(a, sa * A, o0, p, o1, -q),
            ]
            sign = [0, 0, 0]
            sign[a] = sa
            facets.append((outward(octa, sign), tuple(sign)))

    # --- 12 EDGES: the bevel bridging face (a, sa) and face (c, sc), free axis b -- a
    #     RECTANGLE with two vertices on each face at the octagons' shared flat edge -------
    for a, c in ((0, 1), (0, 2), (1, 2)):
        b = ({0, 1, 2} - {a, c}).pop()
        for sa in (1, -1):
            for sc in (1, -1):
                rect = [
                    at(a, sa * A, c, sc * p, b, q), at(a, sa * A, c, sc * p, b, -q),
                    at(c, sc * A, a, sa * p, b, -q), at(c, sc * A, a, sa * p, b, q),
                ]
                sign = [0, 0, 0]
                sign[a] = sa
                sign[c] = sc
                facets.append((outward(rect, sign), tuple(sign)))

    # --- 8 CORNERS: the (sx, sy, sz) vertex is cut into a HEXAGON -- its 6 vertices are the
    #     signed permutations of (A, p, q), alternating a face-octagon diagonal edge with an
    #     edge-bevel edge around the corner -------------------------------------------------
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                hexa = [
                    vid((sx * A, sy * p, sz * q)), vid((sx * A, sy * q, sz * p)),
                    vid((sx * p, sy * q, sz * A)), vid((sx * q, sy * p, sz * A)),
                    vid((sx * q, sy * A, sz * p)), vid((sx * p, sy * A, sz * q)),
                ]
                sign = (sx, sy, sz)
                facets.append((outward(hexa, sign), sign))

    return points, facets


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
