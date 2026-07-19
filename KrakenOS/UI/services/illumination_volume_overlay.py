"""Flat-LED illumination volume (bugs/0355) -- pure geometry, display-free.

The side LED's illumination drawn as one faint translucent volume: the emitting
rectangle extrudes along the emit direction to the beam-splitter fold, folds by the
mirror law, and continues to the Object/FOV plane.  Reflection is an ISOMETRY
(docs/knowledge_base/coaxial_led_dark_edges.rst): the folded footprint stays
congruent to the emitting rectangle -- no cos-squash -- so the volume is an honest
envelope of the collimated support, not a synthetic frustum.

The caller passes the emitting rectangle in the SAME (origin, direction, u, v,
half_u, half_v) frame the scene-source glyph draws, so volume and glyph coincide.
The fold is derived from the scene's optical axis, not from any BS pose: the fold
point is the closest point on the axis to the emit ray, the exit direction aims at
the Object-plane axis point, and the fold plane normal is the mirror-law bisector.
An emitter already aiming down the axis (the unfolded teaching scene) yields a
single straight leg.
"""

from __future__ import annotations

import numpy as np

ILLUMINATION_VOLUME_COLOR = (0.35, 0.85, 1.0)  # the illumination cyan family (0267)
ILLUMINATION_VOLUME_OPACITY = 0.10
_EPS = 1e-9


def _unit(v):
    arr = np.asarray(v, dtype=float).reshape(3)
    n = float(np.linalg.norm(arr))
    return None if n <= _EPS else arr / n


def _ray_plane_t(origin, direction, plane_point, plane_normal):
    denom = float(np.dot(direction, plane_normal))
    if abs(denom) <= _EPS:
        return None
    return float(np.dot(np.asarray(plane_point) - np.asarray(origin), plane_normal) / denom)


def build_illumination_volume_overlay(
    origin,
    direction,
    u_axis,
    v_axis,
    half_u: float,
    half_v: float,
    object_z: float,
    *,
    axis_point=(0.0, 0.0, 0.0),
    axis_dir=(0.0, 0.0, 1.0),
    color=ILLUMINATION_VOLUME_COLOR,
    opacity: float = ILLUMINATION_VOLUME_OPACITY,
):
    """Build the (possibly folded) translucent illumination volume.

    Returns a spec dict with ``points``/``faces`` (VTK triangles, side skin only),
    colour/opacity, ``folded`` and the ring arrays -- or ``None`` when degenerate.
    """
    o = np.asarray(origin, dtype=float).reshape(3)
    d = _unit(direction)
    u = _unit(u_axis)
    v = _unit(v_axis)
    try:
        hu, hv, z_obj = float(half_u), float(half_v), float(object_z)
    except Exception:
        return None
    if d is None or u is None or v is None or hu <= _EPS or hv <= _EPS:
        return None
    ring0 = np.asarray(
        [o - hu * u - hv * v, o + hu * u - hv * v, o + hu * u + hv * v, o - hu * u + hv * v],
        dtype=float,
    )

    ax_p = np.asarray(axis_point, dtype=float).reshape(3)
    ax_d = _unit(axis_dir)
    if ax_d is None:
        return None
    rings = [ring0]
    folded = False
    leg_dir = d
    if abs(float(np.dot(d, ax_d))) < 0.9:
        # Sideways emitter: fold at the optical axis by the mirror law.
        w = o - ax_p
        # closest point between the emit ray (o, d) and the axis line (ax_p, ax_d)
        a = 1.0
        b = float(np.dot(d, ax_d))
        c = 1.0
        e = float(np.dot(d, w))
        f = float(np.dot(ax_d, w))
        denom = a * c - b * b
        if abs(denom) <= _EPS:
            return None
        s_axis = (a * f - b * e) / denom
        fold_point = ax_p + s_axis * ax_d
        # exit aims at the Object-plane point ON the axis
        t_obj = _ray_plane_t(ax_p, ax_d, (0.0, 0.0, z_obj), (0.0, 0.0, 1.0))
        target = ax_p + (t_obj if t_obj is not None else 0.0) * ax_d
        exit_dir = _unit(target - fold_point)
        if exit_dir is None:
            return None
        fold_normal = _unit(exit_dir - d)  # mirror-law bisector plane normal
        if fold_normal is None:
            return None
        ring1 = np.empty_like(ring0)
        for i, corner in enumerate(ring0):
            t = _ray_plane_t(corner, d, fold_point, fold_normal)
            if t is None or t <= 0.0:
                return None
            ring1[i] = corner + t * d
        rings.append(ring1)
        folded = True
        leg_dir = exit_dir
    # final leg: to the Object plane along leg_dir
    last = rings[-1]
    ring_end = np.empty_like(last)
    for i, corner in enumerate(last):
        t = _ray_plane_t(corner, leg_dir, (0.0, 0.0, z_obj), (0.0, 0.0, 1.0))
        if t is None or t <= 0.0:
            return None
        ring_end[i] = corner + t * leg_dir
    rings.append(ring_end)

    points = np.vstack(rings)
    faces: list[int] = []
    for ring_index in range(len(rings) - 1):
        base0 = 4 * ring_index
        base1 = 4 * (ring_index + 1)
        for i in range(4):
            j = (i + 1) % 4
            faces.extend((3, base0 + i, base0 + j, base1 + j))
            faces.extend((3, base0 + i, base1 + j, base1 + i))
    return {
        "kind": "illumination_volume",
        "points": points,
        "faces": np.asarray(faces, dtype=np.int64),
        "color": tuple(float(c) for c in color),
        "opacity": float(opacity),
        "folded": folded,
        "rings": [np.asarray(r, dtype=float) for r in rings],
    }
