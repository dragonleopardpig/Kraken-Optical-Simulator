#!/usr/bin/env python3
"""Display-free regression for bugs/0093: when a beam-splitter split derives a
branch detector at the transmit arm's true focus, the sequential Image -- which
inserting the splitter shoved BACK by the element's thickness -- must not still
draw as a plane curve/label BEHIND the detector.

User (re-recording flag_20260618_085815): "after promotion, the original image
plane is still behind the new detector." The detector sits at the physically
correct focus (bare focus + plate shift); the Image at the old +thickness
location is a stale leftover. 0092 hid only the 3-D aperture disk; this drops the
Image's bundle curve + label (drawn by BOTH the 2-D and 3-D views).

Drives `scene_builder.drop_superseded_image_display` (no trace, no VTK).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_superseded_image_plane_hidden

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.scene_builder import drop_superseded_image_display

    failures: list[str] = []

    rows = [
        SimpleNamespace(surface="Object"),
        SimpleNamespace(surface="Standard"),   # lens
        SimpleNamespace(surface="Solid 3D STL"),  # promoted BS cube
        SimpleNamespace(surface="Image"),       # sequential Image (row 3)
    ]
    # curves: object(0), lens(1), the sequential Image plane(3), and the branch
    # detector curve (row_index=-1, as branch_detector_plane_curve emits).
    curves = [
        SimpleNamespace(row_index=0, kind="object"),
        SimpleNamespace(row_index=1, kind="standard"),
        SimpleNamespace(row_index=3, kind="image"),     # the stale Image plane
        SimpleNamespace(row_index=-1, kind="image"),    # branch detector plane
    ]
    labels = [
        SimpleNamespace(row_index=0, text="Object"),
        SimpleNamespace(row_index=3, text="Image"),     # the stale Image label
    ]

    # 1) WITH a branch detector: the Image row's curve + label are dropped; the
    #    branch detector curve (row -1) and the optics survive.
    c, l = drop_superseded_image_display(curves, labels, rows, has_branch_detector=True)
    c_rows = sorted(getattr(x, "row_index") for x in c)
    l_rows = sorted(getattr(x, "row_index") for x in l)
    if 3 in c_rows:
        failures.append(f"FAIL: stale Image plane curve (row 3) not dropped: curves={c_rows}")
    if 3 in l_rows:
        failures.append(f"FAIL: stale Image label (row 3) not dropped: labels={l_rows}")
    if -1 not in c_rows:
        failures.append("FAIL: branch detector curve (row -1) was wrongly dropped")
    if 0 not in c_rows or 1 not in c_rows:
        failures.append(f"FAIL: non-Image curves were dropped: {c_rows}")
    if 0 not in l_rows:
        failures.append(f"FAIL: Object label wrongly dropped: {l_rows}")

    # 2) WITHOUT a branch detector (plain sequential scene): Image curve + label
    #    stay -- no behaviour change.
    c0, l0 = drop_superseded_image_display(curves, labels, rows, has_branch_detector=False)
    if sorted(getattr(x, "row_index") for x in c0) != sorted(getattr(x, "row_index") for x in curves):
        failures.append("FAIL: sequential scene (no branch detector) lost its Image curve")
    if sorted(getattr(x, "row_index") for x in l0) != sorted(getattr(x, "row_index") for x in labels):
        failures.append("FAIL: sequential scene (no branch detector) lost its Image label")

    # 3) Scene with a branch detector but NO Image row (e.g. all arms escape):
    #    nothing to drop, returns curves unchanged.
    rows_no_img = [r for r in rows if r.surface != "Image"]
    c2, _ = drop_superseded_image_display(curves, labels, rows_no_img, has_branch_detector=True)
    if 3 not in sorted(getattr(x, "row_index") for x in c2):
        failures.append("FAIL: dropped a curve when there was no Image row to supersede")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0093 superseded Image plane still drawn behind the branch detector")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] superseded sequential Image plane hidden behind the branch detector (bugs/0093)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
