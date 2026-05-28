"""Validate that finite-object launches keep the 3x3 field grid inscribed
within the achievable field disc.

North Star #4: ambiguous geometry must produce diagnostics, not silent paths.
The square-grid field sampler historically placed per-axis samples at the
configured field maximum and pushed grid CORNERS to sqrt(2) x max, which both
oversampled past the user's configured field and -- for finite-object
launches -- emitted rays from outside the object aperture.

The current contract is:

* The launch radial maximum is ``min(configured_field_height, object_radius)``.
* The 3x3 grid corners land exactly on that radial maximum.
* Per-axis samples sit at ``radial_max / sqrt(2)``.
* All 9 grid points launch successfully -- nothing is silently dropped.

This validator enforces both bounds (field-limited and aperture-limited)
against MV150 and a shrunk-aperture variant so a regression in either case is
caught.

Run from the repository root:

    python -m KrakenOS.UI.validate_launch_origin_within_object_aperture
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI import layout_editor as le
from KrakenOS.UI.layout_editor import KrakenLayoutEditor


SQRT2 = float(np.sqrt(2.0))


def _assert(cond: bool, msg: str, failures: list[str]) -> None:
    if not cond:
        failures.append(msg)


def _check_grid_inscribed(
    app: KrakenLayoutEditor,
    *,
    case: str,
    expected_radial_max: float,
    failures: list[str],
) -> None:
    launch_max = float(app._launch_field_radial_max())
    _assert(
        abs(launch_max - expected_radial_max) < 1e-6,
        f"[{case}] launch_field_radial_max={launch_max:.6g}, "
        f"expected {expected_radial_max:.6g}",
        failures,
    )

    pairs = app._sample_field_grid_pairs(launch_max)
    _assert(
        len(pairs) == 9,
        f"[{case}] expected 9 grid pairs for field_count=3, got {len(pairs)}",
        failures,
    )

    expected_axis = launch_max / SQRT2
    radii = [float(np.hypot(x, y)) for x, y in pairs]
    corner_count = sum(1 for r in radii if abs(r - launch_max) < 1e-6)
    axis_count = sum(1 for r in radii if abs(r - expected_axis) < 1e-6)
    center_count = sum(1 for r in radii if r < 1e-9)
    _assert(
        corner_count == 4,
        f"[{case}] expected 4 corner samples at r={launch_max:.4g}, "
        f"got {corner_count}. radii={radii}",
        failures,
    )
    _assert(
        axis_count == 4,
        f"[{case}] expected 4 axis-edge samples at r={expected_axis:.4g}, "
        f"got {axis_count}. radii={radii}",
        failures,
    )
    _assert(
        center_count == 1,
        f"[{case}] expected 1 center sample, got {center_count}. radii={radii}",
        failures,
    )

    # No grid point may exceed the launch maximum.
    for x, y in pairs:
        r = float(np.hypot(x, y))
        _assert(
            r <= launch_max + 1e-6,
            f"[{case}] grid point ({x:.4g}, {y:.4g}) radius {r:.4g} "
            f"exceeds launch maximum {launch_max:.4g}",
            failures,
        )

    # All 9 launches must produce a bundle (the old skip-or-warn behavior is
    # intentionally retired -- the rescale ensures everything fits).
    pupil_points = np.array([[0.0, 0.0]], dtype=float)
    bundles, _ = app._build_world_bundles_from_pupil_points(pupil_points)
    _assert(
        len(bundles) == 9,
        f"[{case}] expected 9 launch bundles, got {len(bundles)}",
        failures,
    )
    for index, bundle in enumerate(bundles):
        x0 = float(bundle[0][0])
        y0 = float(bundle[1][0])
        r = float(np.hypot(x0, y0))
        _assert(
            r <= launch_max + 1e-6,
            f"[{case}] launch bundle {index} origin ({x0:.4g}, {y0:.4g}) "
            f"radius {r:.4g} exceeds launch maximum {launch_max:.4g}",
            failures,
        )


def main() -> int:
    failures: list[str] = []
    le._load_3d_backends()
    app = KrakenLayoutEditor(headless=True)
    try:
        app.load_layouts()
        app.load_layout_by_name("Machine Vision 150Mm Measured", refresh=False)

        # Case 1: field-limited. MV150's stock field_height (~10.05 mm) is
        # smaller than the object aperture (12.5 mm), so the launch maximum
        # equals the field height.
        field_height = float(app._current_field_height())
        object_radius = float(app.rows[0].diameter) * 0.5
        _assert(
            field_height < object_radius,
            f"MV150 stock config no longer field-limited "
            f"(field_height={field_height:.4g}, object_radius={object_radius:.4g}). "
            f"Update the fixture so this case is exercised.",
            failures,
        )
        _check_grid_inscribed(
            app,
            case="field-limited",
            expected_radial_max=field_height,
            failures=failures,
        )

        # Case 2: aperture-limited. Shrink the object diameter to a value
        # smaller than the configured field so the clamp drives the launch
        # maximum. This simulates an inserted optic that constrains the
        # achievable object FOV.
        smaller_object_radius = field_height * 0.5
        app.rows[0].diameter = smaller_object_radius * 2.0
        _check_grid_inscribed(
            app,
            case="aperture-limited",
            expected_radial_max=smaller_object_radius,
            failures=failures,
        )
    finally:
        app.destroy()

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Launch-origin grid-inscribed contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
