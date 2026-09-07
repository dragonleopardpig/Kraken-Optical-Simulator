"""Guard for bugs/0729 -- the focused-image plane must follow the FOLD, not a straight line.

Flag 20260907_094552_625: "the focused image shown at the bottom of the 40mm RA mirror? Please
check whether this is correct." -- then "I think it skip the fold. It should be located somewhere
near the Filter."

Measured on om05a: the waist is 78.55 mm back along the beam, but the last leg (RA mirror 2 ->
sensor) is only 60.31 mm. The bugs/0728 placement extrapolated the final straight segment, so the
plane landed 18.2 mm PAST the fold mirror -- through the 40 mm prism and out the far side. Walking
the real traced path instead puts it at x 248.6 with the Filter at x 249.95, exactly where the
user expected.

Checks (display-free, synthetic folded paths):
  A  focus_point_along_paths: a waist further back than the final leg lands ON the upstream leg
     at the right arc length, with the local ray direction as the plane normal.
  B  an oblique ray walks its OWN path length (|offset| / |d.n|), not the axial distance.
  C  a path too short for the walk, or empty input, returns None (no fabricated placement).
  D  focused_image_plane_specs draws at the folded placement when one is supplied -- rectangle
     centred there and lying in the plane of the LOCAL ray direction -- and falls back to the
     straight extrapolation when it is absent.
  E  wiring pins: the grouped measurement reports which field won; the editor walks that group's
     polylines and stashes focus_center_world / focus_normal_world.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0729_focus_plane_follows_the_fold
"""

from __future__ import annotations

import inspect

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import (
        focus_point_along_paths,
        focused_image_plane_specs,
    )

    # om05a shape: a long +x leg into the fold mirror, then a short -y leg down to the sensor.
    mirror = np.array([272.63, 52.80, -25.0])
    sensor = np.array([272.63, -1.76, -25.0])   # 54.56 mm below the mirror
    upstream = np.array([90.0, 52.80, -25.0])
    axis = np.array([0.0, -1.0, 0.0])           # the detector normal
    polyline = np.asarray([upstream, mirror, sensor])
    final_dir = (sensor - mirror) / np.linalg.norm(sensor - mirror)

    # ---- A: past the fold --------------------------------------------------------------------
    offset = -78.546
    placed = focus_point_along_paths([polyline], [final_dir], offset, axis)
    ok(placed is not None, "A0: a folded path returns a placement")
    centre, normal = placed
    final_leg = float(np.linalg.norm(sensor - mirror))
    expected_back = abs(offset) - final_leg          # how far up the +x leg
    expected = mirror - np.array([1.0, 0.0, 0.0]) * expected_back
    ok(
        np.allclose(centre, expected, atol=1e-6),
        f"A1: the waist lands ON the upstream leg, {expected_back:.3f} mm before the fold "
        f"({np.round(centre, 3).tolist()} vs {np.round(expected, 3).tolist()})",
    )
    ok(
        np.allclose(np.abs(normal), np.array([1.0, 0.0, 0.0]), atol=1e-6),
        f"A2: the plane normal is the LOCAL ray direction on that leg, not the sensor normal "
        f"({np.round(normal, 4).tolist()})",
    )
    ok(
        centre[1] < mirror[1] + 1e-9 and abs(centre[1] - mirror[1]) < 1e-6,
        "A3: it does not sit beyond the mirror (the bug drew it 18.2 mm past the fold)",
    )

    # ---- B: an oblique ray walks its own longer distance ----------------------------------------
    oblique = np.array([0.30, -0.9539392014169456, 0.0])
    oblique = oblique / np.linalg.norm(oblique)
    short = np.asarray([mirror + np.array([0.0, 400.0, 0.0]), mirror, mirror + oblique * 500.0])
    placed_ob = focus_point_along_paths([short], [oblique], -10.0, axis)
    ok(placed_ob is not None, "B0: an oblique ray still places")
    walked = float(np.linalg.norm(placed_ob[0] - short[-1]))
    ok(
        abs(walked - 10.0 / abs(float(oblique @ axis))) < 1e-6 and walked > 10.0,
        f"B1: it walks |offset| / |d.n| = {10.0 / abs(float(oblique @ axis)):.4f} mm along the ray, "
        f"not the axial 10 mm (walked {walked:.4f})",
    )

    # ---- C: never fabricate ---------------------------------------------------------------------
    ok(
        focus_point_along_paths([polyline], [final_dir], -5000.0, axis) is None,
        "C1: a path shorter than the walk returns None rather than a point off the end",
    )
    ok(
        focus_point_along_paths([], [], -10.0, axis) is None
        and focus_point_along_paths([polyline], [np.zeros(3)], -10.0, axis) is None,
        "C2: no paths, or a degenerate direction -> None",
    )

    # ---- D: the drawn plane honours the folded placement -------------------------------------------
    info = {
        "offset_mm": offset,
        "side": "in front of",
        "rms_waist_mm": 0.0002,
        "rms_plane_mm": 1.86,
        "focus_center_world": [float(v) for v in centre],
        "focus_normal_world": [float(v) for v in normal],
    }
    specs = focused_image_plane_specs(sensor, axis, info, 11.52, 11.52)
    rect = np.asarray(specs[0]["points"], dtype=float)
    corners = rect[:4]
    out_of_plane = float(np.max(np.abs((rect - centre) @ normal)))
    ok(
        np.allclose(corners.mean(axis=0), centre, atol=1e-6) and out_of_plane < 1e-9,
        f"D1: the rectangle is centred on the FOLDED point and lies perpendicular to the local ray "
        f"({np.round(corners.mean(axis=0), 3).tolist()}, out-of-plane {out_of_plane:.1e})",
    )
    gap = np.asarray(specs[1]["points"], dtype=float)
    ok(
        np.allclose(gap[0], sensor, atol=1e-6) and np.allclose(gap[1], centre, atol=1e-6),
        "D2: the dashed connector runs from the sensor to that point",
    )
    straight = focused_image_plane_specs(
        sensor, axis, {k: v for k, v in info.items() if not k.startswith("focus_")}, 11.52, 11.52
    )
    fallback = np.asarray(straight[0]["points"], dtype=float)[:4].mean(axis=0)
    ok(
        np.allclose(fallback, sensor + axis * offset, atol=1e-6),
        f"D3: with no folded placement it falls back to the straight extrapolation "
        f"({np.round(fallback, 3).tolist()})",
    )

    # ---- E: wiring pins -----------------------------------------------------------------------------
    from KrakenOS.UI.services import detector_coverage_overlay
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    grouped = inspect.getsource(detector_coverage_overlay.focus_waist_from_grouped_rays)
    ok(
        '"group_index"' in grouped and "indices.append" in grouped,
        "E1: the grouped measurement reports WHICH field set the plane",
    )
    measure = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "focus_point_along_paths(" in measure
        and "polylines" in measure
        and '"focus_center_world"' in measure
        and '"focus_normal_world"' in measure,
        "E2: the editor walks the winning field's traced polylines and stashes the folded placement",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0729 focus-plane fold-following validation PASSED")
        return 0
    print("0729 focus-plane fold-following validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
