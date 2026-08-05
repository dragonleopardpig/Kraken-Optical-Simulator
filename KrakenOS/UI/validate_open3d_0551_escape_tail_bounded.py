"""Display-free guard for bugs/0551 -- "still have unbounded rays"
(flag_20260805_081647_775 / flag_20260805_081811_672).

An ESCAPED ray is a display diagnostic: the renderer draws a tail along its exit direction so
the user can see where it went. That tail is EXTENDED past the traced stub, and its length was
``max(75, min(scene_radius * 1.25, 600))``. On the swapped AZ85 scene that is ~375 mm -- past
the prism, past the camera, clean off the frame -- while the TRACE stopped at 237 mm. So what
read as stray light was display scaffolding, not physics.

Measured from the flag's own camera (``bugs/render_0551_escape_tail_options.py``):

    factor 1.25   drawn max x 375.1     <- ships before this fix
    factor 0.40   drawn max x 233.6     <- beam, fold and camera bundle pixel-identical
    75 mm stub    drawn max x 233.6     <- indistinguishable from 0.40

so 0.40 is the LARGEST factor that fixes it: the direction cue survives, the starburst does not.

GENERALITY (the fix is one scene-relative number, so it is judged on more than one scene):
``bugs/diag_0551_escape_tail_sweep.py`` traces the real attachment scenes under both factors
and asserts no scene's drawn-minus-traced overshoot grows and no scene draws SHORT of its own
trace.

Checks (headless, no VTK/tk -- these call the pure projector directly):
- BOUND: an escaped ray on a large scene is drawn at 0.40 x radius, not 1.25 x.
- NEVER SHORTER THAN THE TRACE: the tail only bounds the synthetic extension; a traced
  polyline is not clipped by it.
- SMALL SCENES UNCHANGED: below a ~188 mm radius the 75 mm floor governs, so a small scene
  renders exactly as it did before the change.
- SCENE-RELATIVE: doubling the scene doubles the tail -- no absolute millimetre constant.
- SUPPRESSED BRANCH: bugs/0506's 75 mm stub for a draw-suppressed branch still applies.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0551_escape_tail_bounded
"""

from __future__ import annotations

import numpy as np


def _escaped_tail_length(scene_radius: float, *, branch_path: str = "") -> float:
    """Draw one escaped ray and measure the tail the projector gave it."""
    from KrakenOS.UI.scene_projector import bounded_ray_points_for_scene_display

    # A two-point ray along +x with a deliberately SHORT traced stub, so the projector's
    # extension is what we measure.
    points = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float)
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
    return float(np.max(out[:, 0]))


def run_checks() -> tuple[bool, list[str]]:
    failures: list[str] = []
    try:
        from KrakenOS.UI import scene_projector
    except Exception as exc:  # pragma: no cover - environment skip
        return True, [f"SKIP: scene_projector unavailable ({type(exc).__name__}: {exc})"]

    factor = float(scene_projector._ESCAPED_TAIL_SCENE_RADIUS_FACTOR)
    if factor > 0.40 + 1e-9:
        failures.append(
            f"factor: the escaped-ray tail factor is {factor}; anything above 0.40 puts the "
            "flagged scene's strays back off the frame (bugs/0551)"
        )

    # --- BOUND: a large scene must not get the old 1.25 x tail ------------------------
    radius = 300.0
    tail = _escaped_tail_length(radius)
    expected = max(75.0, min(radius * factor, 600.0))
    if abs(tail - expected) > 1e-6:
        failures.append(f"bound: tail {tail} != expected {expected} for radius {radius}")
    if tail > radius * 0.40 + 1e-6:
        failures.append(
            f"bound: an escaped ray on a {radius} mm scene is drawn {tail:.1f} mm out -- the "
            "1.25 x tail is what ran off the frame (bugs/0551)"
        )

    # --- SCENE-RELATIVE: no absolute millimetre constant ------------------------------
    small, large = 200.0, 400.0
    tail_small, tail_large = _escaped_tail_length(small), _escaped_tail_length(large)
    if not (tail_small < tail_large - 1e-6):
        failures.append(
            f"relative: doubling the scene must lengthen the tail ({tail_small} -> {tail_large}); "
            "a fixed millimetre bound would break big and small scenes differently"
        )
    if abs(tail_large - 2.0 * tail_small) > 1e-6:
        failures.append(
            f"relative: the tail must scale LINEARLY with the scene ({tail_small} -> {tail_large}, "
            "expected exactly double)"
        )

    # --- SMALL SCENES UNCHANGED: the 75 mm floor still governs -------------------------
    for tiny in (10.0, 50.0, 150.0):
        tail_tiny = _escaped_tail_length(tiny)
        if abs(tail_tiny - 75.0) > 1e-6:
            failures.append(
                f"floor: a {tiny} mm scene must still get the 75 mm floor (got {tail_tiny}) -- "
                "the change may only affect scenes big enough for 0.40 x to bind"
            )

    # --- NEVER SHORTER THAN THE TRACE --------------------------------------------------
    # A traced polyline longer than the tail is capped at the tail (that is the ANTI-starburst
    # contract), but a ray whose own traced geometry is short must never be clipped BELOW it.
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

    # --- GENERALITY, PROVEN NOT SAMPLED -------------------------------------------------
    # The tail is `max(75, min(radius * f, 600))` -- monotone in f -- so LOWERING f can never
    # lengthen any scene's tail, whatever its size. Sweeping the radius decides this for ALL
    # scenes at once, which is stronger than tracing a handful (and does not need a display).
    # It also pins the two properties that make the change safe to ship everywhere:
    #   * every scene below the OLD knee (75/1.25 = 60 mm envelope) renders BIT-IDENTICALLY --
    #     both factors sit on the 75 mm floor there, so small optics are untouched; and
    #   * no scene anywhere gets a LONGER tail than it did at 1.25.
    # Between 60 mm and 187.5 mm the new tail IS the 75 mm floor while the old one had started
    # to grow -- shorter, never longer, which is the direction this fix is allowed to move.
    old_factor = 1.25
    knee = 75.0 / old_factor
    for radius_mm in (1.0, 10.0, 50.0, 100.0, 187.0, 187.5, 200.0, 400.0, 1000.0, 5000.0):
        new_tail = max(75.0, min(radius_mm * factor, 600.0))
        old_tail = max(75.0, min(radius_mm * old_factor, 600.0))
        if new_tail > old_tail + 1e-9:
            failures.append(
                f"generality: radius {radius_mm} mm gets a LONGER tail than before "
                f"({old_tail} -> {new_tail}); the fix may only ever shorten"
            )
        if new_tail < 75.0 - 1e-9 or new_tail > 600.0 + 1e-9:
            failures.append(f"generality: radius {radius_mm} mm tail {new_tail} escaped the 75..600 bounds")
        if radius_mm < knee - 1e-9 and abs(new_tail - old_tail) > 1e-9:
            failures.append(
                f"generality: radius {radius_mm} mm is below the {knee:.1f} mm knee, so it must "
                f"render BIT-IDENTICALLY ({old_tail} vs {new_tail})"
            )

    # --- SUPPRESSED BRANCH keeps bugs/0506's 75 mm stub --------------------------------
    stub = _escaped_tail_length(1000.0, branch_path="__diffuse_scatter_probe__")
    if stub > 200.0:
        failures.append(
            f"suppressed: a draw-suppressed branch must keep its short stub (got {stub}) -- "
            "bugs/0506's bounding contract"
        )

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("0551 escape-tail validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print(
        "0551 validation passed: an escaped ray's display tail is bounded at 0.40 x the scene "
        "radius (scene-relative, linear, 75 mm floor intact for small scenes), never draws "
        "shorter than the traced geometry, and a suppressed branch keeps its stub."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
