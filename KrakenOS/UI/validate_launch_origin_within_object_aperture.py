"""Validate where a finite-object launch puts its 3x3 field grid.

North Star #4: ambiguous geometry must produce diagnostics, not silent paths.
The square-grid field sampler historically placed per-axis samples at the
configured field maximum and pushed grid CORNERS to sqrt(2) x max, which both
oversampled past the user's configured field and -- for finite-object
launches -- emitted rays from outside the object aperture. That is what the
radial-inscribed contract below fixed.

**bugs/0523 then changed the answer for any scene with a known object-FOV
rectangle**, on the user's flag ("all the outer 3 rays should relocate to the 4
corner and 4 edges, simulating rays launching from maximum FOV"). A camera
sees a RECTANGLE, not a disc, so when `_imaging_fov_half_extents()` is known the
grid spans it: 4 corners exactly on (+/-half_x, +/-half_y), 4 edge midpoints,
1 centre. Scenes with no rectangle keep the radial inscribed layout.

So there are two contracts, and this validator checks both:

* **rectangle path** (`_sample_imaging_field_grid_pairs`): the outer ring lands
  exactly ON the FOV rectangle; every one of the 9 bundles launches.
* **radial path** (`_sample_field_grid_pairs`, reached when no rectangle is
  known): the launch radial maximum is
  ``min(configured_field_height, object_radius, camera_fov_inscribed_radius)``,
  the corners land on it, and per-axis samples sit at ``radial_max/sqrt(2)``.

It also measures how the FOV rectangle sits inside the object's own clear
aperture. On MV150 the FOV is square (half = 10.046 mm) and the object row is a
disc of radius 12.5 mm, so the EDGE midpoints are inside it but the CORNERS
reach r = 14.21 mm -- 1.71 mm outside. The inscribed circle must fit; the
diagonal overhang is reported, not asserted, because whether the object
aperture should cover the FOV diagonal is a prescription question
(bugs/0878).

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

        field_height = float(app._current_field_height())
        object_radius = float(app.rows[0].diameter) * 0.5
        fov_inscribed = app._camera_fov_inscribed_object_radius()
        half = app._imaging_fov_half_extents()

        # Case 1: the rectangle path (bugs/0523). MV150 registers the hr25MCX, so the
        # object-FOV rectangle is known and the grid must span it.
        _assert(
            half is not None,
            f"MV150 stock config no longer reports an object-FOV rectangle "
            f"(half={half}); the bugs/0523 rectangle path is not being exercised.",
            failures,
        )
        if half is not None:
            half_x, half_y = float(half[0]), float(half[1])
            pairs = app._sample_imaging_field_grid_pairs()
            _assert(
                len(pairs) == 9,
                f"[fov-rectangle] expected 9 grid pairs for field_count=3, got {len(pairs)}",
                failures,
            )
            expected = {
                (round(x, 9), round(y, 9))
                for x in (-half_x, 0.0, half_x)
                for y in (-half_y, 0.0, half_y)
            }
            actual = {(round(float(x), 9), round(float(y), 9)) for x, y in pairs}
            _assert(
                actual == expected,
                f"[fov-rectangle] the outer ring must land ON the FOV rectangle; "
                f"got {sorted(actual)}, expected {sorted(expected)}",
                failures,
            )

            pupil_points = np.array([[0.0, 0.0]], dtype=float)
            bundles, _ = app._build_world_bundles_from_pupil_points(pupil_points)
            _assert(
                len(bundles) == 9,
                f"[fov-rectangle] expected 9 launch bundles, got {len(bundles)}",
                failures,
            )
            origins = {
                (round(float(bundle[0][0]), 9), round(float(bundle[1][0]), 9))
                for bundle in bundles
            }
            _assert(
                origins == expected,
                f"[fov-rectangle] every bundle must launch from a grid point; "
                f"got {sorted(origins)}",
                failures,
            )

            # The FOV's inscribed circle must fit inside the object's clear aperture. The
            # DIAGONAL overhang is measured and reported, not asserted -- see the module
            # docstring.
            inscribed = min(half_x, half_y)
            diagonal = float(np.hypot(half_x, half_y))
            _assert(
                inscribed <= object_radius + 1e-6,
                f"[fov-rectangle] the FOV inscribed radius {inscribed:.6g} mm does not fit "
                f"inside the object aperture radius {object_radius:.6g} mm",
                failures,
            )
            print(
                f"NOTE: FOV half extents ({half_x:.6g}, {half_y:.6g}) mm, inscribed "
                f"{inscribed:.6g} mm, diagonal {diagonal:.6g} mm; object aperture radius "
                f"{object_radius:.6g} mm -> corner overhang "
                f"{max(diagonal - object_radius, 0.0):.6g} mm"
            )

        # Case 2: the radial path, reached when no object-FOV rectangle is known. Hide the
        # rectangle so the inscribed-disc contract is exercised on the same scene.
        app._imaging_fov_half_extents = lambda: None
        _check_grid_inscribed(
            app,
            case="radial-no-rectangle",
            expected_radial_max=min(
                field_height,
                object_radius,
                float(fov_inscribed) if fov_inscribed is not None else field_height,
            ),
            failures=failures,
        )

        # Case 3: still the radial path, now aperture-limited -- shrink the object below the
        # camera FOV so the aperture clamp drives the launch maximum.
        smaller_object_radius = (
            float(fov_inscribed) * 0.5 if fov_inscribed is not None else field_height * 0.5
        )
        app.rows[0].diameter = smaller_object_radius * 2.0
        _check_grid_inscribed(
            app,
            case="radial-aperture-limited",
            expected_radial_max=smaller_object_radius,
            failures=failures,
        )
    finally:
        app.destroy()

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("Launch-origin field-grid contract validation passed.")
    return 0


def run_checks() -> tuple[bool, list[str]]:
    """Penta-harness entry point (bugs/0878)."""
    import contextlib
    import io

    stream = io.StringIO()
    with contextlib.redirect_stdout(stream):
        code = main()
    notes = []
    for line in stream.getvalue().splitlines():
        if not line.strip():
            continue
        notes.append(("FAIL " + line[6:]) if line.startswith("FAIL: ") else ("= " + line))
    return code == 0, notes


if __name__ == "__main__":
    raise SystemExit(main())
