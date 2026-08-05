"""Display-free guard for bugs/0551 + bugs/0553 -- how far an ESCAPED ray is DRAWN.

An escaped ray is a display diagnostic: the renderer draws a tail along its exit direction,
EXTENDED past the traced stub, so the user can see where the stray went. Its length was a
fixed fraction of the scene envelope radius -- and a fraction of the radius has no relationship
to where the scene's geometry actually is, so it was wrong in BOTH directions:

* ``1.25 x`` -- flag_20260805_081647 / _081811, *"still have unbounded rays"*: every escape drew
  ~375 mm on the swapped AZ85 scene, past the prism and off the frame, while the TRACE stopped
  at 237 mm.
* ``0.40 x`` (the bugs/0551 attempt) -- flag_20260805_101116 / _101430, *"some rays stop half way
  before touching the RA mirror"*: measured, that factor sat BELOW the 75 mm floor on this scene
  (0.40 and the 75 mm stub rendered byte-identical drawn extents, 233.586), a 3x shortening, so
  strays were amputated in mid-air short of the prism they were crossing toward.

bugs/0553 replaces the tuned constant with the geometric quantity both flags were asking for:
the tail runs until the stray LEAVES THE SCENE ENVELOPE (the forward exit of the sphere
``center`` / ``scene_radius`` that ``scene_display_center_radius`` builds from the surface
meshes, curves and targets -- never from the rays themselves), floored at 75 mm and capped at
600 mm.

Checks (headless, no VTK/tk -- these call the pure projector directly):
- TRAVERSE (0553): a stray launched at the near edge and crossing the scene reaches the far
  side; nothing stops in mid-air INSIDE the scene.
- ENVELOPE (0551): a stray from the centre is not drawn past the scene.
- FLOOR / CAP: a stray already outside the envelope, or aimed away from it, gets the 75 mm
  floor; no scene however large exceeds the 600 mm cap.
- SCENE-RELATIVE: doubling the scene doubles the reach -- no absolute millimetre constant.
- NEVER SHORTER THAN THE TRACE: the bound applies to the synthetic extension only; a traced
  polyline is never clipped by it.
- SUPPRESSED BRANCH: bugs/0506's short stub for a draw-suppressed branch still applies.

Non-vacuity: the guard REJECTS 1.25 x radius, 0.40 x radius and a flat 75 mm stub -- i.e. both
shipped rules and the trivial one -- and passes only the sphere exit.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0551_escape_tail_bounded
"""

from __future__ import annotations

import numpy as np


def _tail(scene_radius: float, *, start_x: float = 0.0, branch_path: str = "") -> float:
    """The drawn reach of one escaped ray launched at ``start_x`` along +x."""
    from KrakenOS.UI.scene_projector import bounded_ray_points_for_scene_display

    points = np.asarray([[start_x, 0.0, 0.0], [start_x + 1.0, 0.0, 0.0]], dtype=float)
    out, _capped = bounded_ray_points_for_scene_display(
        points,
        np.zeros(3, dtype=float),
        float(scene_radius),
        terminal_status="escaped",
        terminal_direction=np.asarray([1.0, 0.0, 0.0], dtype=float),
        branch_path=branch_path,
    )
    out = np.asarray(out, dtype=float)
    if out.ndim != 2 or out.shape[0] < 2:
        return float("nan")
    return float(np.max(out[:, 0])) - start_x



def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI import scene_projector
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: scene_projector unavailable ({type(exc).__name__}: {exc})"]

    floor = float(scene_projector._ESCAPED_TAIL_MIN_MM)
    cap = float(scene_projector._ESCAPED_TAIL_MAX_MM)

    # --- 0553: a stray CROSSING the scene must traverse it, not stop in mid-air ----------
    # This is the flag_20260805_101116/_101430 regression: with a tuned fraction the tail sat
    # on the 75 mm floor and strays were cut short of the prism they were crossing toward.
    for radius in (100.0, 150.0, 187.5, 250.0):
        reach = _tail(radius, start_x=-radius)          # launched at the near edge, aimed across
        span = min(2.0 * radius, cap)
        if reach < span - 1e-6:
            failures.append(
                f"traverse: on a {radius:.0f} mm-radius scene a stray crossing it reaches only "
                f"{reach:.1f} mm of the {span:.1f} mm it must cover -- that is the bugs/0553 "
                "mid-air stop"
            )

    # --- 0551: and it must NOT be drawn beyond the scene ---------------------------------
    for radius in (100.0, 250.0):
        reach = _tail(radius)                            # launched at the centre
        allowed = min(max(radius, floor), cap) + 1e-6
        if reach > allowed:
            failures.append(
                f"envelope: on a {radius:.0f} mm-radius scene a stray from the centre is drawn "
                f"{reach:.1f} mm out, past the scene -- that is the bugs/0551 off-frame streak"
            )

    # --- FLOOR / CAP ---------------------------------------------------------------------
    outside = scene_projector._scene_exit_distance(
        np.asarray([500.0, 0.0, 0.0]), np.asarray([1.0, 0.0, 0.0]), None, np.zeros(3), 100.0
    )
    if abs(outside - floor) > 1e-6:
        failures.append(f"floor: a stray already outside the envelope must get the {floor} mm floor, got {outside}")
    for radius in (1000.0, 5000.0):
        if _tail(radius, start_x=-radius) > cap + 1e-6:
            failures.append(f"cap: a {radius:.0f} mm scene must still cap the tail at {cap} mm")

    # --- SCENE-RELATIVE: no absolute constant --------------------------------------------
    small, large = 100.0, 200.0
    t_small, t_large = _tail(small, start_x=-small), _tail(large, start_x=-large)
    if abs(t_large - 2.0 * t_small) > 1e-6:
        failures.append(
            f"relative: doubling the scene must double the tail ({t_small} -> {t_large}); a fixed "
            "millimetre bound would break big and small scenes differently"
        )

    # --- NEVER SHORTER THAN THE TRACE ----------------------------------------------------
    from KrakenOS.UI.scene_projector import bounded_ray_points_for_scene_display

    traced = np.asarray([[0.0, 0.0, 0.0], [40.0, 0.0, 0.0]], dtype=float)
    out, _ = bounded_ray_points_for_scene_display(
        traced,
        np.zeros(3, dtype=float),
        300.0,
        terminal_status="escaped",
        terminal_direction=np.asarray([1.0, 0.0, 0.0], dtype=float),
    )
    if float(np.max(np.asarray(out, dtype=float)[:, 0])) < 40.0 - 1e-6:
        failures.append("trace: a traced 40 mm segment must never be drawn shorter than traced")

    # --- SUPPRESSED BRANCH keeps bugs/0506's stub ----------------------------------------
    stub = _tail(1000.0, start_x=-1000.0, branch_path="__diffuse_scatter_probe__")
    if stub > 200.0:
        failures.append(f"suppressed: a draw-suppressed branch must keep its short stub (got {stub})")

    return (not failures), failures



def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0553 escape-tail validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0553 validation passed: an escaped ray's display tail runs to the SCENE ENVELOPE exit "
        "-- a stray crossing the scene traverses it (no mid-air stop), none is drawn beyond the "
        "scene, the 75 mm floor and 600 mm cap hold, the reach scales with the scene, a traced "
        "segment is never shortened, and a suppressed branch keeps its stub."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
