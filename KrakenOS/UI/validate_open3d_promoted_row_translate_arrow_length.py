"""Display-free contract for bugs/0006: a STEP promoted to an analytic-lens row
must keep the same big Move-gizmo translate arrows it had as a STEP overlay,
instead of reverting to the short scene-grid stub.

Two gizmos draw the "same" Move/Rotate handles -- the STEP overlay
(``Open3DStepRotationHandleService.add_handles``) and the row placement
(``_add_scene_placement_translate_handles`` / ``_add_scene_placement_rotate_handles``).
bugs/0004 lengthened only the STEP overlay's arrows, so promotion (STEP -> row)
shrank them. The fix routes both gizmos through one length seam
``Kraken3DInspector._transform_translate_arrow_length`` and sizes the row gizmo
off the row's *visible body* (``_row_display_body_extent``), never the grid.

This pins the formula and source-couples both gizmos so a future edit can't
silently revert either to grid-only sizing. The rendered-pixel / live-arrow
guarantee lives in ``validate_open3d_promoted_row_translate_arrow_length_snapshot``
and Phase 13 of the comprehensive validator.

Run from the repository root:

    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promoted_row_translate_arrow_length
"""

from __future__ import annotations

import inspect

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.services.open3d_step_rotation_handles import (
    Open3DStepRotationHandleService,
)


def _historical_step_length(extent: float) -> float:
    """The STEP overlay's pre-0006 inline formula, reproduced here so the test
    proves the shared seam is byte-equivalent."""
    extent = max(float(extent), 1.0)
    radius = max(extent * 0.62, 3.0)
    return max(extent * 1.05, radius * 1.55)


def _checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []
    length = Kraken3DInspector._transform_translate_arrow_length

    # The seam reproduces the STEP service's historical arrow length exactly, at
    # a range of body sizes (so the gizmo is identical before and after promotion).
    for extent in (0.5, 1.0, 3.0, 9.525, 25.0, 100.0):
        got = length(extent)
        want = _historical_step_length(extent)
        checks.append(
            (f"length({extent}) matches the STEP overlay formula", abs(got - want) < 1e-9, f"got={got} want={want}")
        )
        # Always at least span the body (so the arrow visibly clears the glass).
        checks.append(
            (f"length({extent}) >= extent*1.05", got >= max(float(extent), 1.0) * 1.05 - 1e-9, f"got={got}")
        )

    # Monotonic in the body extent: a bigger lens gets bigger arrows.
    samples = [length(e) for e in (1.0, 5.0, 10.0, 25.0, 60.0, 120.0)]
    monotonic = all(b >= a for a, b in zip(samples, samples[1:]))
    checks.append(("arrow length is monotonic in extent", monotonic, f"samples={[round(s, 3) for s in samples]}"))

    # A short body floors at the radius*1.55 branch, never collapsing to 0.
    checks.append(("tiny extent floors above the 3.0 arc radius", length(0.1) >= 3.0 * 1.55 - 1e-9, f"got={length(0.1)}"))

    # ---- Source coupling: both gizmos must route through the shared seam. ----
    step_src = inspect.getsource(Open3DStepRotationHandleService.add_handles)
    checks.append(
        (
            "STEP overlay add_handles calls _transform_translate_arrow_length",
            "_transform_translate_arrow_length" in step_src,
            "missing in Open3DStepRotationHandleService.add_handles",
        )
    )

    move_src = inspect.getsource(Kraken3DInspector._add_scene_placement_translate_handles)
    checks.append(
        (
            "row translate handles call _transform_translate_arrow_length",
            "_transform_translate_arrow_length" in move_src,
            "missing in _add_scene_placement_translate_handles",
        )
    )
    checks.append(
        (
            "row translate handles size off _row_display_body_extent",
            "_row_display_body_extent" in move_src,
            "missing in _add_scene_placement_translate_handles",
        )
    )

    rotate_src = inspect.getsource(Kraken3DInspector._add_scene_placement_rotate_handles)
    checks.append(
        (
            "row rotate arcs size off _row_display_body_extent",
            "_row_display_body_extent" in rotate_src,
            "missing in _add_scene_placement_rotate_handles",
        )
    )

    # ---- _row_display_body_extent must accept the non-file-backed body markers
    # (a promoted analytic lens is glassy / round-lens-like, not file-backed). --
    extent_src = inspect.getsource(Kraken3DInspector._row_display_body_extent)
    for marker in (
        "_kraken_file_backed_row_body",
        "_kraken_glassy_lens_body",
        "_kraken_round_lens_like_step_body",
    ):
        checks.append(
            (
                f"_row_display_body_extent accepts the {marker} body marker",
                marker in extent_src,
                f"{marker} missing -- a promoted analytic lens body would be skipped",
            )
        )

    return checks


def main() -> int:
    checks = _checks()
    failed = [(name, detail) for name, ok, detail in checks if not ok]
    if failed:
        print("Open 3D promoted-row translate-arrow length validation failed:")
        for name, detail in failed:
            print(f"- {name}: {detail}")
        return 1
    print(f"Open 3D promoted-row translate-arrow length validation passed ({len(checks)} checks).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
