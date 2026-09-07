"""Guard for bugs/0734 -- a drawn beam AXIS folds exactly 90 deg on a 45 deg mirror.

Flag 20260907_102940_169: "check all optical axis (not rays), some of them are not 90 degree
after after reflection?"

Correct. bugs/0723 drew each face's CHIEF RAY, aimed through the aperture stop so it would reach
the sensor. A chief ray meets a 45 deg mirror off-normal, so it turns by 90 +- 2*(its tilt).
Measured in the flagged state: 94.49, 85.51, 83.17 deg (face A) and 96.38, 85.80, 83.62 (face B).

An AXIS is parallel to the design axis between folds, so it turns exactly 90 deg. The traced ray
is still the SOURCE -- it discovers which mirrors the arm uses and where -- but the drawn guide is
now constructed: start at the face centre along its normal, intersect each mirror plane, reflect,
and finish on the sensor plane. Measured after: 90.000 deg at every fold on both faces.

Checks (display-free, synthetic geometry):
  A  folds_from_traced_path recovers the mirror normal for ANY angle of incidence (d_before -
     d_after is parallel to it), and ignores refraction-sized turns.
  B  fold_axis_polyline folds exactly 90 deg on a 45 deg mirror, and lands on the detector plane
     when one is given.
  C  an OFF-AXIS start (the +-8.8 mm beam offset of a split field) still folds exactly 90 deg --
     the tilt the user saw came from the ray, not from the offset.
  D  it refuses rather than guesses: a fold behind the start, or a mirror the axis runs along.
  E  wiring: the record builder constructs the axis from the traced folds; the inspector supplies
     the detector plane.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0734_beam_axis_folds_ninety
"""

from __future__ import annotations

import inspect

import numpy as np


def _turns(points):
    pts = np.asarray(points, dtype=float)
    dirs = []
    for k in range(1, pts.shape[0]):
        v = pts[k] - pts[k - 1]
        n = float(np.linalg.norm(v))
        if n > 1e-9:
            dirs.append(v / n)
    return [
        float(np.degrees(np.arccos(np.clip(float(dirs[i - 1] @ dirs[i]), -1.0, 1.0))))
        for i in range(1, len(dirs))
    ]


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.detector_coverage_overlay import (
        fold_axis_polyline,
        folds_from_traced_path,
        split_field_beam_axis_records,
    )

    # a 45 deg mirror that turns +z into +y, and a second that turns +y into +x
    m1 = np.array([0.0, 1.0, -1.0]) / np.sqrt(2.0)     # +z -> +y
    m2 = np.array([1.0, -1.0, 0.0]) / np.sqrt(2.0)     # +y -> +x
    m3 = np.array([1.0, 1.0, 0.0]) / np.sqrt(2.0)      # +x -> -y, onto the sensor
    hit1 = np.array([0.0, 0.0, 8.5])
    hit2 = np.array([0.0, 52.8, 8.5])
    hit3 = np.array([272.63, 52.8, 8.5])

    # ---- A: recovering the mirrors from a ray at ANY incidence -------------------------------
    tilted = np.array([0.0, -0.06, 0.998])
    tilted = tilted / np.linalg.norm(tilted)
    out1 = tilted - 2.0 * float(tilted @ m1) * m1
    ray = np.asarray([hit1 - tilted * 30.0, hit1, hit1 + out1 * 40.0])
    folds = folds_from_traced_path(ray)
    ok(
        len(folds) == 1 and float(np.degrees(np.arccos(abs(float(folds[0][1] @ m1))))) < 1e-6,
        f"A1: the mirror normal is recovered from an off-normal ray "
        f"({np.round(folds[0][1], 6).tolist() if folds else None})",
    )
    ray_turn = _turns(ray)[0]
    ok(
        abs(ray_turn - 90.0) > 3.0,
        f"A2: that RAY itself turns {ray_turn:.2f} deg -- not 90, which is exactly what the user saw",
    )
    bend = np.array([0.03, 0.0, 0.99955])
    bend = bend / np.linalg.norm(bend)
    refraction = np.asarray([hit1 - np.array([0.0, 0.0, 30.0]), hit1, hit1 + bend * 30.0])
    ok(
        folds_from_traced_path(refraction) == [],
        "A3: a refraction-sized turn is not a fold",
    )

    # ---- B: the constructed axis ---------------------------------------------------------------
    sensor_point = np.array([272.63, -1.76, -25.0])
    sensor_normal = np.array([0.0, -1.0, 0.0])
    axis_pts = fold_axis_polyline(
        np.array([0.0, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]),
        [(hit1, m1), (hit2, m2), (hit3, m3)],
        end_point=sensor_point, end_normal=sensor_normal,
    )
    ok(axis_pts is not None, "B0: the axis is constructed")
    turns = _turns(axis_pts)
    ok(
        len(turns) == 3 and all(abs(t - 90.0) < 1e-9 for t in turns),
        f"B1: every fold is EXACTLY 90 deg on a 45 deg mirror ({[round(t, 6) for t in turns]})",
    )
    ok(
        abs(float((axis_pts[-1] - sensor_point) @ sensor_normal)) < 1e-9,
        f"B2: the axis finishes ON the sensor plane ({np.round(axis_pts[-1], 3).tolist()})",
    )

    # ---- C: an OFF-AXIS start still folds 90 deg -------------------------------------------------
    # the offset must be PERPENDICULAR to travel: offsetting along +z would be the same line
    offset_pts = fold_axis_polyline(
        np.array([8.8, 0.0, 0.0]), np.array([0.0, 0.0, 1.0]),
        [(hit1, m1), (hit2, m2), (hit3, m3)],
        end_point=sensor_point, end_normal=sensor_normal,
    )
    offset_turns = _turns(offset_pts) if offset_pts is not None else []
    ok(
        offset_pts is not None and all(abs(t - 90.0) < 1e-9 for t in offset_turns),
        f"C1: a beam that rides its own offset still folds exactly 90 deg "
        f"({[round(t, 6) for t in offset_turns]})",
    )
    ok(
        offset_pts is not None
        and abs(float(np.linalg.norm(offset_pts[-1] - axis_pts[-1])) - 8.8) < 1e-6,
        f"C2: the two axes stay 8.8 mm apart end to end -- parallel, not coincident "
        f"({float(np.linalg.norm(offset_pts[-1] - axis_pts[-1])):.4f} mm)",
    )

    # ---- D: refuse rather than guess ---------------------------------------------------------------
    ok(
        fold_axis_polyline(np.array([0.0, 0.0, 40.0]), np.array([0.0, 0.0, 1.0]), [(hit1, m1)]) is None,
        "D1: a fold BEHIND the start is refused (that train is not this axis')",
    )
    ok(
        fold_axis_polyline(np.array([0.0, 0.0, 0.0]), np.array([0.0, 1.0, 1.0]) / np.sqrt(2.0),
                           [(hit1, m1)]) is None,
        "D2: an axis running along the mirror plane has no intersection -> None",
    )
    ok(
        fold_axis_polyline(np.array([0.0, 0.0, 0.0]), np.zeros(3), [(hit1, m1)]) is None,
        "D3: a degenerate direction -> None",
    )

    # ---- E: wiring -----------------------------------------------------------------------------------
    builder = inspect.getsource(split_field_beam_axis_records)
    ok(
        "folds_from_traced_path(pts)" in builder and "fold_axis_polyline(" in builder,
        "E1: the record builder harvests the folds from the trace and draws the constructed axis",
    )
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    wiring = inspect.getsource(Kraken3DInspector._split_field_beam_axis_records)
    ok(
        "image_point=detector_point" in wiring and "image_axis=detector_normal" in wiring,
        "E2: the inspector supplies the detector plane so the axis ends on the sensor",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0734 beam-axis-folds-ninety validation PASSED")
        return 0
    print("0734 beam-axis-folds-ninety validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
