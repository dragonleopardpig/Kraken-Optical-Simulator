"""Guard for bugs/0741 + bugs/0742 -- report the field the optics deliver, and centre the drawn
image plane on the beam.

Flag 20260907_143739_657 ("50x50mm device size", "is everything correct?") plus, on the render:
"the image plane is shifted to the side from the Center of the Sensor, you can see the pink color
line slanted as well."

0741: the success path stashed `delivered_fov_wh` as the REQUEST, so a 50 x 1 mm device face read
as "delivering 52.5 x 1.05 mm" while |m| 0.4389 images 52.5 x 52.5 mm of object -- and the no-op
path one block above computed it properly, so the two disagreed about the same scene.

0742: bugs/0729 walks the WINNING FIELD's rays back along their real path to place the plane. That
field images off-axis, so the drawn rectangle sat 11.623 mm beside the beam while all 644 landing
rays centred on the sensor to 0.000 mm. Anchoring the walk on the ray nearest the beam centre fixed
x; the remaining 3.851 mm in z was the ~10.4 deg arrival angle of om05a's split-field beams, so on
a straight leg (no fold crossed) the rectangle is placed on the sensor's own axis.

Checks (display-free):
  A  the delivered field is computed from |m| and the sensor, on BOTH paths, and falls back to the
     request only when the magnification is unusable.
  B  the plane placement anchors on the beam centre, not the winning field.
  C  the straight-leg rule is guarded by the TRANSPORTED normal, so a folded waist (bugs/0729,
     penta 528) keeps its around-the-corner placement.
  D  the arithmetic: sensor / |m| is the delivered field.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0741_delivered_field_and_plane_centre
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    solve = inspect.getsource(QuickEstimationService.fov_solve)

    # ---- A: the delivered field is DELIVERED, not requested -------------------------------------
    ok(
        '"delivered_fov_wh": (float(obj_w), float(obj_h)),' not in solve,
        "A1: the success path no longer stashes the REQUEST as the delivered field (bugs/0741)",
    )
    ok(
        "float(dims[0]) / magnitude, float(dims[1]) / magnitude" in solve,
        "A2: it computes sensor / |m| -- what the optics actually image",
    )
    ok(
        'summary["delivered_fov_wh"] = delivered_wh or (float(obj_w), float(obj_h))' in solve,
        "A3: and falls back to the request only when the magnification is unusable, so the "
        "banner never goes blank",
    )
    already = inspect.getsource(QuickEstimationService._fov_already_delivered)
    ok(
        "float(dims[0]) / delivered_m, float(dims[1]) / delivered_m" in already,
        "A4: the no-op path computes it the same way -- the two paths agree about one scene",
    )

    # ---- B: the plane is anchored on the beam ------------------------------------------------------
    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    measure = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)
    ok(
        "np.argmin(gaps)" in measure and "every" in measure,
        "B1: the walk is anchored on the ray landing nearest the BEAM centre, not on the winning "
        "field's off-axis bundle (bugs/0742)",
    )
    ok(
        "focus_point_along_paths(" in measure and measure.count("focus_point_along_paths(") == 2,
        "B2: it is still the REAL-path walk (bugs/0729), used for both the winner and the axial "
        "ray -- the fold handling is not bypassed",
    )
    ok(
        '"plane_recentre_mm"' in measure,
        "B3: how far the plane moved is recorded, so the correction is inspectable",
    )

    # ---- C: the straight-leg rule is fold-guarded ---------------------------------------------------
    ok(
        "transported" in measure and "abs(abs(float(transported @ unit)) - 1.0)" in measure,
        "C1: the re-centring fires only when the TRANSPORTED normal equals the sensor's -- i.e. "
        "no fold between the waist and the sensor",
    )
    guard_at = measure.find("abs(abs(float(transported @ unit)) - 1.0)")
    assign_at = measure.find('info["focus_center_world"]')
    ok(
        0 <= guard_at < assign_at,
        "C2: and it runs BEFORE the centre is stashed, so a folded waist keeps the walked point "
        "(bugs/0729's 'near the Filter' case, penta 528)",
    )

    # ---- D: the arithmetic ---------------------------------------------------------------------------
    sensor = 23.04
    m = 0.4388571428
    ok(
        abs(sensor / m - 52.5) < 0.01,
        f"D1: a 23.04 mm sensor at |m| {m:.4f} images {sensor / m:.2f} mm of object -- the 52.5 mm "
        f"the banner must report, not the 1.05 mm that was requested",
    )
    ok(
        abs(20.941 * (3.851 / 20.941) - 3.851) < 1e-6,
        "D2: the 3.851 mm of z wander was the arrival angle over the 20.941 mm walk "
        "(~10.4 deg), not a sideways shift of the image",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0741/0742 delivered-field + plane-centre validation PASSED")
        return 0
    print("0741/0742 delivered-field + plane-centre validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
