"""Imaging-lens receiving-angle cone (bugs/0354) -- pure geometry, display-free.

The acceptance volume the imaging lens RECEIVES from the object: every FOV point's
accepted bundle subtends the lens entrance pupil, so the union over the imaged FOV
is the loft between the FOV rectangle at the Object plane and the entrance-pupil
disc.  Drawn as a faint translucent skin (no caps) so the scene stays readable; a
point outside this skin cannot contribute to the image.

Pure numpy: the caller supplies the imaged-FOV half extents, the Object-plane z,
and the entrance pupil (z + radius) -- all from the editor's existing first-order
machinery -- and gets back VTK-ready points/faces.
"""

from __future__ import annotations

import numpy as np

RECEIVING_CONE_COLOR = (0.25, 0.62, 0.88)  # faint steel-blue, distinct from ray green/red
RECEIVING_CONE_OPACITY = 0.12
RECEIVING_CONE_SEGMENTS = 48
# bugs/0419: axial rings along object->pupil so a folded scene can CREASE the cone (a 2-ring loft is a
# straight ruled surface -> cuts a diagonal wedge across the mirror instead of bending onto each leg).
RECEIVING_CONE_AXIAL_SEGMENTS = 40


def _rect_boundary_point(angle: float, half_x: float, half_y: float) -> tuple[float, float]:
    """Point on the axis-aligned rectangle boundary in direction ``angle`` from centre."""
    c, s = float(np.cos(angle)), float(np.sin(angle))
    scale = max(abs(c) / max(half_x, 1e-12), abs(s) / max(half_y, 1e-12))
    r = 1.0 / max(scale, 1e-12)
    return c * r, s * r


def build_receiving_cone_overlay(
    fov_half_x: float,
    fov_half_y: float,
    object_z: float,
    pupil_z: float,
    pupil_radius: float,
    *,
    segments: int = RECEIVING_CONE_SEGMENTS,
    axial_segments: int = RECEIVING_CONE_AXIAL_SEGMENTS,
    color=RECEIVING_CONE_COLOR,
    opacity: float = RECEIVING_CONE_OPACITY,
):
    """Loft the imaged-FOV rectangle (Object plane) to the entrance-pupil disc.

    The section morphs from the FOV RECTANGLE at ``object_z`` to the pupil DISC at
    ``pupil_z`` over ``axial_segments`` intermediate rings (bugs/0419): a 2-ring loft
    is always a straight ruled surface, so on a FOLDED scene it cannot CREASE at the
    mirror -- it cuts a diagonal wedge from the FOV straight to the lens. Sampling
    the section along the axis lets the display fold bend each ring onto its leg, so
    the cone follows the object leg then the lens leg. All rings share the same
    ``segments`` angles so the correspondence is twist-free.

    Returns a spec dict with ``points`` (((axial_segments+1)*n, 3) float), ``faces``
    (VTK triangle cells), colour/opacity, ``axial_rings`` and the input anchors -- or
    ``None`` on degenerate geometry.
    """
    try:
        hx, hy = float(fov_half_x), float(fov_half_y)
        z0, z1, pr = float(object_z), float(pupil_z), float(pupil_radius)
    except Exception:
        return None
    n = max(int(segments), 8)
    m = max(int(axial_segments), 1)  # number of axial slabs -> m+1 rings
    if not all(np.isfinite(v) for v in (hx, hy, z0, z1, pr)):
        return None
    if hx <= 1e-9 or hy <= 1e-9 or pr <= 1e-9 or abs(z1 - z0) <= 1e-9:
        return None
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    rect_xy = np.array([_rect_boundary_point(float(a), hx, hy) for a in angles], dtype=float)  # (n,2)
    disc_xy = np.column_stack([pr * np.cos(angles), pr * np.sin(angles)])  # (n,2)
    rings: list[np.ndarray] = []
    for k in range(m + 1):
        t = k / m
        xy = (1.0 - t) * rect_xy + t * disc_xy  # morph rectangle -> disc
        z = z0 + t * (z1 - z0)
        rings.append(np.column_stack([xy, np.full(n, z)]))
    points = np.vstack(rings)
    faces: list[int] = []
    for k in range(m):  # connect ring k to ring k+1
        base0, base1 = k * n, (k + 1) * n
        for i in range(n):
            j = (i + 1) % n
            faces.extend((3, base0 + i, base0 + j, base1 + j))
            faces.extend((3, base0 + i, base1 + j, base1 + i))
    return {
        "kind": "receiving_cone",
        "points": points,
        "faces": np.asarray(faces, dtype=np.int64),
        "color": tuple(float(c) for c in color),
        "opacity": float(opacity),
        "axial_rings": m + 1,
        "fov_half": (hx, hy),
        "object_z": z0,
        "pupil_z": z1,
        "pupil_radius": pr,
    }
