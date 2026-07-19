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
    color=RECEIVING_CONE_COLOR,
    opacity: float = RECEIVING_CONE_OPACITY,
):
    """Loft the imaged-FOV rectangle (Object plane) to the entrance-pupil disc.

    Both rings are sampled at the same ``segments`` angles so the correspondence is
    twist-free.  Returns a spec dict with ``points`` ((2n,3) float), ``faces`` (VTK
    triangle cells), colour/opacity, and the input anchors -- or ``None`` on
    degenerate geometry.
    """
    try:
        hx, hy = float(fov_half_x), float(fov_half_y)
        z0, z1, pr = float(object_z), float(pupil_z), float(pupil_radius)
    except Exception:
        return None
    n = max(int(segments), 8)
    if not all(np.isfinite(v) for v in (hx, hy, z0, z1, pr)):
        return None
    if hx <= 1e-9 or hy <= 1e-9 or pr <= 1e-9 or abs(z1 - z0) <= 1e-9:
        return None
    angles = np.linspace(0.0, 2.0 * np.pi, n, endpoint=False)
    fov_ring = np.empty((n, 3), dtype=float)
    pupil_ring = np.empty((n, 3), dtype=float)
    for i, a in enumerate(angles):
        rx, ry = _rect_boundary_point(float(a), hx, hy)
        fov_ring[i] = (rx, ry, z0)
        pupil_ring[i] = (pr * np.cos(a), pr * np.sin(a), z1)
    points = np.vstack([fov_ring, pupil_ring])
    faces: list[int] = []
    for i in range(n):
        j = (i + 1) % n
        a0, a1 = i, j
        b0, b1 = n + i, n + j
        faces.extend((3, a0, a1, b1))
        faces.extend((3, a0, b1, b0))
    return {
        "kind": "receiving_cone",
        "points": points,
        "faces": np.asarray(faces, dtype=np.int64),
        "color": tuple(float(c) for c in color),
        "opacity": float(opacity),
        "fov_half": (hx, hy),
        "object_z": z0,
        "pupil_z": z1,
        "pupil_radius": pr,
    }
