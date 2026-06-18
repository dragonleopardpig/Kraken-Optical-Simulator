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

    import numpy as np

    rows = [
        SimpleNamespace(surface="Object"),
        SimpleNamespace(surface="Standard"),   # lens
        SimpleNamespace(surface="Solid 3D STL"),  # promoted BS cube (row 2, z~164)
        SimpleNamespace(surface="Image"),       # sequential Image (row 3, z=266)
    ]
    # targets: Object, the stale sequential Image (is_detector -> draws an orange
    # footprint at 266), and two branch detectors (reflect off-axis +y @164,
    # transmit on-axis @233).
    targets = [
        SimpleNamespace(row_index=0, surface="Object", is_detector=False,
                        center_world=np.array([0., 0., 0.]), metadata={"target_source": "table_row"}),
        SimpleNamespace(row_index=3, surface="Image", is_detector=True,
                        center_world=np.array([0., 0., 266.]), metadata={"target_source": "table_row"}),
        SimpleNamespace(row_index=100000, surface="Image", is_detector=True,
                        center_world=np.array([0., 80., 164.]), metadata={"target_source": "branch_detector"}),
        SimpleNamespace(row_index=100001, surface="Image", is_detector=True,
                        center_world=np.array([0., 0., 233.]), metadata={"target_source": "branch_detector"}),
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

    # 1) WITH a branch detector: the Image row's TARGET + curve + label are dropped;
    #    the branch detectors + the optics survive.
    t, c, l = drop_superseded_image_display(targets, curves, labels, rows, has_branch_detector=True)
    t_rows = sorted(getattr(x, "row_index") for x in t)
    c_rows = sorted(getattr(x, "row_index") for x in c)
    l_rows = sorted(getattr(x, "row_index") for x in l)
    if 3 in t_rows:
        failures.append(f"FAIL: stale Image TARGET (row 3, orange footprint) not dropped: targets={t_rows}")
    if 100000 not in t_rows or 100001 not in t_rows:
        failures.append(f"FAIL: branch detector targets wrongly dropped: {t_rows}")
    if 0 not in t_rows:
        failures.append(f"FAIL: Object target wrongly dropped: {t_rows}")
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

    # 2) WITHOUT a branch detector (plain sequential scene): nothing dropped.
    t0, c0, l0 = drop_superseded_image_display(targets, curves, labels, rows, has_branch_detector=False)
    if sorted(getattr(x, "row_index") for x in t0) != sorted(getattr(x, "row_index") for x in targets):
        failures.append("FAIL: sequential scene (no branch detector) lost its Image target")
    if sorted(getattr(x, "row_index") for x in c0) != sorted(getattr(x, "row_index") for x in curves):
        failures.append("FAIL: sequential scene (no branch detector) lost its Image curve")

    # 3) Scene with a branch detector but NO Image row: nothing to drop.
    rows_no_img = [r for r in rows if r.surface != "Image"]
    t2, c2, _ = drop_superseded_image_display(targets, curves, labels, rows_no_img, has_branch_detector=True)
    if 3 not in sorted(getattr(x, "row_index") for x in c2):
        failures.append("FAIL: dropped a curve when there was no Image row to supersede")
    if 3 not in sorted(getattr(x, "row_index") for x in t2):
        failures.append("FAIL: dropped a target when there was no Image row to supersede")

    # 4) Thickness dimension: the span into the superseded Image (row 2->3) is
    #    REDIRECTED to the on-axis (transmit) branch-detector focus, not the stale
    #    image -- so "the thickness after the splitting surface" still draws, to the
    #    real focus.
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    runs_to = Open3DThicknessDimensionService._dimension_runs_to_superseded_image
    if not runs_to(rows, 2, has_branch_detector=True):
        failures.append("FAIL: dimension into the superseded Image (row 2->3) not recognised")
    if runs_to(rows, 1, has_branch_detector=True):
        failures.append("FAIL: a lens->cube dimension (row 1->2) wrongly flagged")
    if runs_to(rows, 2, has_branch_detector=False):
        failures.append("FAIL: dimension flagged with NO branch detector (sequential scene must keep it)")

    focus_fn = Open3DThicknessDimensionService._superseding_branch_focus
    bundle = SimpleNamespace(targets=targets)
    # cube (p0 ~z164 on-axis) -> stale image (p1 z266): redirect to the on-axis
    # transmit detector (233), NOT the off-axis reflect detector (164,+y).
    focus = focus_fn(bundle, np.array([0., 0., 164.]), np.array([0., 0., 266.]))
    if focus is None or abs(float(np.asarray(focus)[2]) - 233.0) > 1.0:
        failures.append(f"FAIL: dimension redirect should pick the on-axis transmit focus z=233, got {focus}")
    # a forward-but-off-axis detector must be rejected (no skew arrow).
    off_bundle = SimpleNamespace(targets=[
        SimpleNamespace(center_world=np.array([0., 90., 233.]), metadata={"target_source": "branch_detector"}),
    ])
    if focus_fn(off_bundle, np.array([0., 0., 164.]), np.array([0., 0., 266.])) is not None:
        failures.append("FAIL: off-axis-only branch detector wrongly used as a dimension redirect focus")

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
