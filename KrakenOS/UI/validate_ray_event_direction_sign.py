"""Validate that RayKeeper trace-event directions follow the physical ray path.

KrakenOS stores ``R_LMN``/``LMN`` as the raw ``ResVec`` without the cumulative
``SIGN`` flip, so a naive trace-event record points its ``outgoing_direction``/
``incoming_direction`` backwards after an odd number of reflections.  RayKeeper
must reconcile event directions against the traced polyline geometry before
emitting ``TraceEventRecord``s.

This validator traces a 45 degree fold mirror (exactly one reflection, so the
cumulative ``SIGN`` is ``-1`` for every event after the mirror) and asserts that
every event direction agrees with the polyline that the trace actually drew.
It fails if RayKeeper regresses to emitting raw ``R_LMN``/``LMN``.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.TraceEvents import TRACE_EVENT_KIND_SURFACE


def _unit(vector) -> np.ndarray | None:
    try:
        arr = np.asarray(vector, dtype=float).reshape(-1)[:3]
    except Exception:
        return None
    if arr.size < 3 or not np.all(np.isfinite(arr)):
        return None
    norm = float(np.linalg.norm(arr))
    if not np.isfinite(norm) or norm <= 1.0e-12:
        return None
    return arr / norm


def _build_fold_mirror_system():
    p_obj = Kos.surf()
    p_obj.Rc = 0.0
    p_obj.Thickness = 25.0
    p_obj.Glass = "AIR"
    p_obj.Diameter = 25.0

    mirror = Kos.surf()
    mirror.Rc = 0.0
    mirror.Thickness = -25.0
    mirror.Glass = "MIRROR"
    mirror.Diameter = 25.0
    mirror.Name = "Fold mirror 45 deg"
    mirror.TiltX = 45.0
    mirror.AxisMove = 2.0

    p_ima = Kos.surf()
    p_ima.Rc = 0.0
    p_ima.Thickness = 0.0
    p_ima.Glass = "AIR"
    p_ima.Diameter = 25.0
    p_ima.Name = "Image"

    return Kos.system([p_obj, mirror, p_ima], Kos.Setup())


def validate_ray_event_direction_sign() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    system = _build_fold_mirror_system()
    rays = Kos.raykeeper(system)
    system.Trace([0.0, 0.0, 0.0], [0.0, 0.0, 1.0], 0.55)
    rays.push()

    events = list(rays.TRACE_EVENTS[0])
    surface_events = [
        event for event in events
        if getattr(event, "event_kind", "") == TRACE_EVENT_KIND_SURFACE
    ]
    reflections = [
        event for event in surface_events
        if "reflect" in str(getattr(event, "event_type", "")).lower()
    ]
    checks.append((
        "fold-mirror trace produces a reflection event (cumulative SIGN flips)",
        len(reflections) >= 1,
        f"surface_events={len(surface_events)} reflections={len(reflections)}",
    ))

    # Every event direction must agree with the polyline the trace drew:
    # consecutive event points define the physical travel segment, and the
    # leaving event's outgoing_direction plus the arriving event's
    # incoming_direction must both point along it.
    geometry_ok = True
    detail_parts: list[str] = []
    for current, following in zip(events[:-1], events[1:]):
        segment = _unit(
            np.asarray(following.point_world, dtype=float)
            - np.asarray(current.point_world, dtype=float)
        )
        if segment is None:
            continue
        out_dir = _unit(current.outgoing_direction)
        in_dir = _unit(following.incoming_direction)
        out_ok = out_dir is None or float(np.dot(out_dir, segment)) > 0.0
        in_ok = in_dir is None or float(np.dot(in_dir, segment)) > 0.0
        if not (out_ok and in_ok):
            geometry_ok = False
        detail_parts.append(
            f"S{current.surface_id}->S{following.surface_id}:"
            f"out={'ok' if out_ok else 'REVERSED'},in={'ok' if in_ok else 'REVERSED'}"
        )
    checks.append((
        "event outgoing/incoming directions follow the traced polyline after reflection",
        geometry_ok,
        "; ".join(detail_parts) or "no event segments",
    ))
    return checks


def main() -> int:
    checks = validate_ray_event_direction_sign()
    failed = [check for check in checks if not check[1]]
    for name, passed, detail in checks:
        print(f"{'PASS' if passed else 'FAIL'}: {name} - {detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
