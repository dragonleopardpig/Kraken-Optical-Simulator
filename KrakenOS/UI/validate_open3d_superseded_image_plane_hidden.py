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

    # 4) Thickness dimension: the sequential span that would run out to the
    #    superseded Image (row 2->3) is SKIPPED -- the per-branch exit->detector
    #    overlay measures that arm instead. Only when a branch detector exists.
    from KrakenOS.UI.services.open3d_thickness_dimensions import Open3DThicknessDimensionService

    runs_to = Open3DThicknessDimensionService._dimension_runs_to_superseded_image
    if not runs_to(rows, 2, has_branch_detector=True):
        failures.append("FAIL: dimension into the superseded Image (row 2->3) not recognised")
    if runs_to(rows, 1, has_branch_detector=True):
        failures.append("FAIL: a lens->cube dimension (row 1->2) wrongly flagged")
    if runs_to(rows, 2, has_branch_detector=False):
        failures.append("FAIL: dimension flagged with NO branch detector (sequential scene must keep it)")

    # 5) Per-branch exit->detector overlay: the branch detector scene target carries
    #    exit_point_world (where the arm exits the cube), and the arm label is
    #    extracted from branch_path. (The overlay itself is VTK -- the geometry +
    #    metadata are what's display-free verifiable here.)
    from KrakenOS.UI.services.branch_detectors import BranchDetector, branch_detector_scene_target

    bd = BranchDetector(
        detector_id="x", branch_path="S4:BS/reflect",
        center_world=np.array([0., 121., 162.]), normal_world=np.array([0., 1., 0.]),
        tangent_world=np.array([1., 0., 0.]), half_w=10.0, half_h=10.0,
        exit_point_world=np.array([0., 25.0, 159.0]),
    )
    tgt = branch_detector_scene_target(bd, row_index=100000)
    ept = (getattr(tgt, "metadata", {}) or {}).get("exit_point_world")
    if ept is None or abs(float(ept[1]) - 25.0) > 1e-6 or abs(float(ept[2]) - 159.0) > 1e-6:
        failures.append(f"FAIL: branch detector target missing/odd exit_point_world: {ept}")
    arm = Open3DThicknessDimensionService._branch_arm_label
    if arm("S4:BS/transmit -> S7:BS2/reflect") != "reflect":
        failures.append(f"FAIL: cascaded branch arm label wrong: {arm('S4:BS/transmit -> S7:BS2/reflect')!r}")
    if arm("S4:BS/transmit") != "transmit":
        failures.append(f"FAIL: transmit branch arm label wrong: {arm('S4:BS/transmit')!r}")

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
