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

Corners use a SYMMETRIC diagonal (bugs/0257, dropping the 0252 wide-screen bias): the
outward direction is the picked octant's ``(+-1, +-1, +-1)`` normalized and the roll-0
STANDARD up is world ``+Y`` projected perpendicular to it -- exactly the edge rule, but
with three extreme axes. So the pure pose is upright and octant-symmetric.

At snap time the inspector does NOT keep this absolute up: it ports FreeCAD's NaviCube
``getNearestOrientation`` via :func:`nearest_orientation_up` -- align the CURRENT camera's
view axis to the corner's diagonal (preserving the current roll), then SNAP the residual
roll to the nearest of six clean orientations (0/60/120/180/240/300 deg about the sight
line). So clicking a corner after you have rotated the scene gives the corner view whose
roll is closest to how you were already looking -- matching FreeCAD exactly -- instead of a
binary up/down flip (bugs/0254-0256, which only ever chose 0 or 180 and so landed visibly
wrong whenever the natural snap was 60/120/240/300).

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


def _unit(vec):
    """Unit vector for ``vec``, or ``None`` when it is (near) zero-length."""
    v = np.asarray(vec, dtype=float).reshape(3)
    n = float(np.linalg.norm(v))
    return (v / n) if n > 1e-12 else None


def _perp_unit(vec, axis):
    """``vec`` projected perpendicular to unit ``axis``, normalized -- or ``None``."""
    v = np.asarray(vec, dtype=float).reshape(3)
    perp = v - float(np.dot(v, axis)) * axis
    n = float(np.linalg.norm(perp))
    return (perp / n) if n > 1e-6 else None


def _rotate_between(vec, frm, to):
    """Rotate ``vec`` by the MINIMAL rotation taking unit ``frm`` onto unit ``to``.

    Returns ``vec`` unchanged when ``frm``/``to`` already coincide and ``None`` when they are
    ANTIparallel (the rotation axis is undefined), so the caller can fall back deterministically.
    """
    frm = np.asarray(frm, dtype=float).reshape(3)
    to = np.asarray(to, dtype=float).reshape(3)
    axis = np.cross(frm, to)
    sin_a = float(np.linalg.norm(axis))
    cos_a = float(np.dot(frm, to))
    v = np.asarray(vec, dtype=float).reshape(3)
    if sin_a <= 1e-9:
        return v if cos_a >= 0.0 else None
    axis = axis / sin_a
    angle = float(np.arctan2(sin_a, cos_a))
    return (
        v * np.cos(angle)
        + np.cross(axis, v) * np.sin(angle)
        + axis * float(np.dot(axis, v)) * (1.0 - np.cos(angle))
    )


def nearest_orientation_up(
    sight_axis,
    standard_up,
    current_sight_axis,
    current_up,
    steps: int = 6,
):
    """View-up for a CORNER click, porting FreeCAD's NaviCube ``getNearestOrientation``
    (bugs/0257, NaviCube.cpp:954).

    A corner click aims the camera along ``sight_axis`` (the octant diagonal, out of screen).
    Rather than resetting the roll, FreeCAD keeps the CURRENT view's roll and SNAPS it to the
    nearest of ``steps`` clean orientations about that axis -- SIX for a corner (0/60/120/180/
    240/300 deg) -- so a corner clicked after you rotated the scene lands at the roll closest to
    how you were already looking. (bugs/0254-0256 only ever chose 0 or 180 deg, so any view
    whose natural snap was 60/120/240/300 looked wrong no matter how the flip was tuned.)

    Args:
      sight_axis: the target out-of-screen direction (the pose's ``offset_unit``).
      standard_up: the roll-0 reference up for that axis (world +Y projected perpendicular to
        it -- itself one of the six clean corner rolls, so the snapped set matches FreeCAD's).
      current_sight_axis: the live camera's out-of-screen direction (``-view_direction``).
      current_up: the live camera's view-up.
      steps: clean-roll count (6 for corners; 4 for faces/edges, though only corners call this).

    Mirrors NaviCube.cpp: minimally rotate the current camera so its view axis aligns to
    ``sight_axis`` (this preserves the roll), measure the residual roll of that intermediate up
    from ``standard_up`` about the axis, round it to the nearest ``2*pi/steps``, and roll
    ``standard_up`` by it. Returns a unit ``(x, y, z)`` perpendicular to ``sight_axis``.
    """
    a = _unit(sight_axis)
    if a is None:
        return tuple(float(v) for v in _projected_up(sight_axis))
    s = _perp_unit(standard_up, a)
    if s is None:
        s = _projected_up(a)  # world-up projected perpendicular to a (already unit, perp)
    e2 = _perp_unit(np.cross(a, s), a)  # completes (s, e2, a) right-handed; roll basis
    if e2 is None:
        return tuple(float(v) for v in s)

    # Minimally rotate the current up so the current view axis lands on ``a`` (roll preserved),
    # then keep only its component in the sight plane -> the intermediate roll reference. An
    # antiparallel current axis (undefined rotation) falls back to the raw current up.
    c = _unit(current_sight_axis)
    inter = np.asarray(current_up, dtype=float).reshape(3)
    if c is not None:
        rotated = _rotate_between(inter, c, a)
        if rotated is not None:
            inter = rotated
    iup = _perp_unit(inter, a)
    if iup is None:
        return tuple(float(v) for v in s)

    # Signed residual roll from ``s`` to the intermediate up about ``a``, snapped to nearest step.
    phi = float(np.arctan2(float(np.dot(iup, e2)), float(np.dot(iup, s))))
    step = 2.0 * np.pi / int(max(1, steps))
    theta = float(np.floor(phi / step + 0.5)) * step  # round half toward +inf (deterministic)
    result = s * np.cos(theta) + e2 * np.sin(theta)
    result_unit = _unit(result)
    if result_unit is None:
        return tuple(float(v) for v in s)
    return tuple(float(v) for v in result_unit)


def orientation_pose(sign, up_axis: str = "y"):
    """``(offset_unit, view_up)`` unit tuples for a sign triple from a pick.

    Faces return their cardinal-preset pose verbatim; edges AND corners return the normalized
    outward direction with a projected, upright view-up -- for a corner that is the roll-0
    STANDARD (the inspector then snaps a corner's roll to the current view via
    :func:`nearest_orientation_up`). ``up_axis`` is accepted for call-site compatibility but no
    longer changes the pose (corners are the symmetric diagonal now -- bugs/0257).
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
