"""Guard for bugs/0733 -- the focused-image plane must be SQUARE to the axis, not to a ray.

Flag 20260907_102153_232: "image location tilted."

bugs/0729 placed the plane correctly but oriented it by the winning field's local ray direction.
In a split-field design the beams enter the lens OFF-AXIS by design, so no chief ray is parallel
to the axis: the drawn plane came out 3.6 deg tilted against a sensor that is square to the axis.
Averaging fields only reduced it to 1.0 deg, and picking the "axial" field made it worse (4.3 deg)
-- because the axial FIELD's chief ray is not the axis either when the whole beam rides off-axis.

The axis is not any ray. It is the SENSOR NORMAL transported back through the same folds the ray
took: at a big turn the ray reflected about ``m = normalise(d_before - d_after)``, so the running
axis reflects about the same ``m``. A small turn is a refraction and does not re-orient the leg.
Measured on om05a: the plane normal is now (1.0, -2.9e-8, 2.1e-8) -- 0.000 deg from the lens axis
-- with the placement unchanged at the Filter.

Checks (display-free, synthetic paths):
  A  a 90 deg fold transports the sensor normal onto the leg axis exactly, whatever the ray's own
     direction, and the placement is unchanged.
  B  an off-axis ray on the same fold gives the SAME plane normal (the tilt is gone), where the
     ray direction itself differs.
  C  a straight (unfolded) path returns the sensor normal.
  D  a small refraction does not re-orient the plane.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0733_focus_plane_square_to_the_axis
"""

from __future__ import annotations

import numpy as np


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import focus_point_along_paths

    sensor = np.array([272.63, -1.76, -25.0])
    axis = np.array([0.0, -1.0, 0.0])          # the sensor faces -y
    mirror = np.array([272.63, 52.80, -25.0])  # the 90 deg fold, 54.56 mm above the sensor

    # ---- A: on-axis ray through the fold ----------------------------------------------------
    upstream = np.array([90.0, 52.80, -25.0])
    polyline = np.asarray([upstream, mirror, sensor])
    final_dir = (sensor - mirror) / np.linalg.norm(sensor - mirror)
    placed = focus_point_along_paths([polyline], [final_dir], -78.546, axis)
    ok(placed is not None, "A0: the folded walk places")
    centre, normal = placed
    ok(
        abs(abs(float(normal[0])) - 1.0) < 1e-9 and abs(float(normal[1])) < 1e-6 and abs(float(normal[2])) < 1e-6,
        f"A1: the sensor normal transported through the 90 deg fold IS the leg axis "
        f"({np.round(normal, 9).tolist()})",
    )
    expected = mirror - np.array([1.0, 0.0, 0.0]) * (78.546 - float(np.linalg.norm(sensor - mirror)))
    ok(
        np.allclose(centre, expected, atol=1e-6),
        f"A2: the placement is unchanged by the orientation fix ({np.round(centre, 3).tolist()})",
    )

    # ---- B: an OFF-AXIS ray on the same PHYSICAL mirror gives the same plane ---------------------
    # the fold that turns +x into -y has normal m; a ray at any other incidence reflects about
    # the SAME m (which is why d_before - d_after is always parallel to it)
    m = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)
    tilted_up = np.array([90.0, 52.80 + 9.0, -25.0 + 3.0])   # arrives 8-9 mm off the axis
    ray_dir = (mirror - tilted_up) / np.linalg.norm(mirror - tilted_up)
    tilt_of_ray = float(np.degrees(np.arccos(abs(float(ray_dir[0])))))
    out_dir = ray_dir - 2.0 * float(ray_dir @ m) * m          # the real reflected direction
    tilted = np.asarray([tilted_up, mirror, mirror + out_dir * float(np.linalg.norm(sensor - mirror))])
    placed_off = focus_point_along_paths([tilted], [out_dir], -78.546, axis)
    ok(placed_off is not None, "B0: the off-axis walk places")
    normal_off = placed_off[1]
    ok(
        float(np.degrees(np.arccos(abs(float(normal_off[0]))))) < 1e-6,
        f"B1: the plane stays square to the axis even though the RAY runs {tilt_of_ray:.2f} deg "
        f"off it -- the 3.6 deg tilt the user saw is gone ({np.round(normal_off, 8).tolist()})",
    )
    ok(
        float(np.degrees(np.arccos(abs(float(np.dot(normal, normal_off)))))) < 1e-6,
        "B2: on-axis and off-axis fields agree on the plane orientation",
    )

    # ---- C: no fold -> the sensor normal ----------------------------------------------------------
    straight = np.asarray([sensor + np.array([0.0, 300.0, 0.0]), sensor + np.array([0.0, 100.0, 0.0]), sensor])
    placed_straight = focus_point_along_paths([straight], [axis], -20.0, axis)
    ok(
        placed_straight is not None
        and float(np.degrees(np.arccos(abs(float(np.dot(placed_straight[1], axis)))))) < 1e-6,
        f"C1: an unfolded path keeps the sensor normal "
        f"({np.round(placed_straight[1], 8).tolist() if placed_straight else None})",
    )

    # ---- D: a refraction does not re-orient --------------------------------------------------------
    bend = np.array([0.03, -0.99955, 0.0])   # ~1.7 deg, a plate refraction
    bend = bend / np.linalg.norm(bend)
    refracted = np.asarray([sensor - bend * 300.0, sensor - axis * 100.0, sensor])
    placed_ref = focus_point_along_paths([refracted], [axis], -20.0, axis)
    ok(
        placed_ref is not None
        and float(np.degrees(np.arccos(abs(float(np.dot(placed_ref[1], axis)))))) < 1e-6,
        "D1: a small (refraction-sized) turn leaves the plane orientation alone",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0733 focus-plane-square-to-the-axis validation PASSED")
        return 0
    print("0733 focus-plane-square-to-the-axis validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
