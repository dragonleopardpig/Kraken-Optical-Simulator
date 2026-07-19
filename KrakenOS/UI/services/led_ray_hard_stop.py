"""Flat-LED plate hard stop for drawn rays (bugs/0356) -- pure geometry.

The flat LED panel is OPAQUE: an imaging ray reflected off the beam splitter toward
the LED must terminate AT the plate, not sail past it.  On vendor scenes the LED
module is display-only CAD (never a traced surface), so nothing physical stops the
drawn polyline -- the same class of display honesty as the bugs/0088 detector hard
stop, and this module reuses exactly that plane contract:

``(center_world, normal_unit, radial_limit)`` consumed by
``scene_projector._clip_polyline_at_detector_planes`` -- a polyline crossing the
plane FORWARD (``(p-centre)·normal`` from <0 to >=0) within ``radial_limit`` is
truncated at the crossing.  With ``normal = -emit_direction`` a ray approaching the
plate from the scene side crosses forward and stops; the LED's own illumination
rays START on the plane heading away and never cross it.
"""

from __future__ import annotations

import numpy as np

# The physical module face is larger than its emitting window (housing, frame), so
# the stop board is a generous multiple of the window half-diagonal -- mirroring the
# 0088 detector "board, not tight active-area rect" philosophy.
LED_PLATE_LIMIT_SCALE = 1.5
LED_PLATE_LIMIT_MIN_MM = 20.0


def led_plate_hard_stop_plane(origin, direction, half_x, half_y):
    """``(center, normal, radial_limit)`` for an opaque emitter plate, or None.

    ``origin``/``direction`` are the emitter seat (the scene-source glyph frame);
    the normal points INTO the plate (against the emit direction) so only rays
    travelling toward the plate cross forward and truncate.
    """
    try:
        center = np.asarray(origin, dtype=float).reshape(3)
        d = np.asarray(direction, dtype=float).reshape(3)
        hx, hy = float(half_x), float(half_y)
    except Exception:
        return None
    norm = float(np.linalg.norm(d))
    if norm <= 1e-9 or not np.all(np.isfinite(center)) or not (hx > 0.0 and hy > 0.0):
        return None
    normal = -(d / norm)
    limit = max(LED_PLATE_LIMIT_SCALE * float(np.hypot(hx, hy)), LED_PLATE_LIMIT_MIN_MM)
    return center, normal, float(limit)
