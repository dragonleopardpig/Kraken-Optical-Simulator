#!/usr/bin/env python3
"""Display-free regression for bugs/0088 Phase B1: one branch detector per
TERMINAL leaf branch of the traced ray tree (beam-splitter arms, generalized to
cascading splitters), derived from the traced rays.

Drives `KrakenOS.UI.services.branch_detectors.derive_branch_detectors` against
synthesized ray paths (no trace, no Xvfb, no VTK):
  - single beam splitter -> TWO derived detectors (transmit + reflect leaves),
    each at its converging focus, sized to a visible plane (bugs/0090).
  - CASCADING (two splitters) -> a detector on each TERMINAL leaf arm (incl. the
    straight-through transmit), NONE on the intermediate arm feeding splitter 2.
  - absorbing reflect output (reflect branch absent from the rays) -> none.
  - no splitter (only the sequential leaf) -> none.
  - a derived detector is an is_detector target AND appears in Phase A's
    `scene_projector.detector_planes_for_hard_stop` (so reflect rays hard-stop).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_beam_splitter_branch_detectors

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np


def _converging_paths(branch_path, focus, *, n=3, reaches_image=False):
    """n RayPath3D rays concurrent at `focus` (exit segment = last polyline seg)."""
    from KrakenOS.UI.scene_geometry import RayPath3D

    focus = np.asarray(focus, dtype=float)
    paths = []
    for k in range(n):
        origin = focus + np.asarray((float(k - (n - 1) / 2.0) * 3.0, -55.0, 0.0), dtype=float)
        direction = focus - origin
        direction = direction / np.linalg.norm(direction)
        prior = origin - direction * 5.0
        tail = origin + direction * 300.0
        pts = np.vstack((prior, origin, tail))
        paths.append(RayPath3D(branch_path=branch_path, reaches_image=bool(reaches_image), points_world=pts))
    return paths


def _sequential_paths(branch_path="primary", n=3):
    """Rays that reach the Image along +Z (the transmit/sequential leaf)."""
    from KrakenOS.UI.scene_geometry import RayPath3D

    paths = []
    for k in range(n):
        y = float(k - (n - 1) / 2.0) * 2.0
        pts = np.asarray([[0.0, y, 0.0], [0.0, y * 0.2, 120.0], [0.0, 0.0, 200.0]], dtype=float)
        paths.append(RayPath3D(branch_path=branch_path, reaches_image=True, points_world=pts))
    return paths


def _absorbed_paths(branch_path, focus, *, n=3):
    """bugs/0108: reflect-arm rays that are PRESENT (heading toward `focus`) but die
    by absorption at a cube face -- a terminal event tagged termination_reason=absorbed.
    Their last segment would extrapolate to a phantom focus if not dropped."""
    from KrakenOS.UI.scene_geometry import RayPath3D, RayEvent3D

    focus = np.asarray(focus, dtype=float)
    paths = []
    for k in range(n):
        origin = focus + np.asarray((float(k - (n - 1) / 2.0) * 3.0, -55.0, 0.0), dtype=float)
        direction = focus - origin
        direction = direction / np.linalg.norm(direction)
        prior = origin - direction * 5.0
        tail = origin + direction * 300.0
        pts = np.vstack((prior, origin, tail))
        terminal = RayEvent3D(event_kind="terminal", termination_reason="absorbed")
        paths.append(RayPath3D(branch_path=branch_path, reaches_image=False, points_world=pts, events=[terminal]))
    return paths


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.branch_detectors import (
        derive_branch_detectors,
        branch_detector_scene_target,
    )

    failures: list[str] = []

    # 1) single beam splitter -> a detector on BOTH arms, each at its converging
    #    focus, with a visible (non-sliver) size (bugs/0090).
    reflect_focus = np.asarray((0.0, 80.0, 150.0), dtype=float)
    single = _sequential_paths("S4:BS/transmit") + _converging_paths("S4:BS/reflect", reflect_focus)
    dets = derive_branch_detectors(single, existing_targets=[], scene_radius=50.0)
    if len(dets) != 2:
        failures.append(f"FAIL: single BS expected 2 branch detectors (both arms), got {len(dets)} ({[d.branch_path for d in dets]})")
    reflect = next((d for d in dets if "reflect" in d.branch_path), None)
    transmit = next((d for d in dets if "transmit" in d.branch_path), None)
    if reflect is None or transmit is None:
        failures.append(f"FAIL: single BS missing an arm detector: {[d.branch_path for d in dets]}")
    else:
        if not np.allclose(reflect.center_world, reflect_focus, atol=1.0):
            failures.append(f"FAIL: reflect detector focus {reflect.center_world} != {reflect_focus}")
        if reflect.focus_source != "converging_rays":
            failures.append(f"FAIL: reflect focus_source = {reflect.focus_source!r}, expected converging_rays")
        if not np.allclose(transmit.center_world, (0.0, 0.0, 200.0), atol=1.5):
            failures.append(f"FAIL: transmit detector focus {transmit.center_world} != ~(0,0,200)")
        if min(reflect.half_w, reflect.half_h, transmit.half_w, transmit.half_h) < 5.0:
            failures.append(
                f"FAIL: detector plane collapsed to a sliver (half<5mm): "
                f"reflect={reflect.half_w:.2f},{reflect.half_h:.2f} transmit={transmit.half_w:.2f},{transmit.half_h:.2f}"
            )

    # 2) cascading: BS1 reflect -> BS2 splits again. Detector ONLY on the two
    #    terminal leaves, NOT on the intermediate BS1-reflect arm.
    fa = np.asarray((40.0, 80.0, 150.0), dtype=float)
    fb = np.asarray((-40.0, 80.0, 150.0), dtype=float)
    cascading = (
        _sequential_paths("S4:BS/transmit")
        + _converging_paths("S4:BS/reflect", np.asarray((0.0, 40.0, 150.0)))  # intermediate (escaped, no image)
        + _converging_paths("S4:BS/reflect -> S7:BS2/transmit", fa)
        + _converging_paths("S4:BS/reflect -> S7:BS2/reflect", fb)
    )
    cdets = derive_branch_detectors(cascading, existing_targets=[], scene_radius=50.0)
    cpaths = sorted(d.branch_path for d in cdets)
    expected = sorted([
        "S4:BS/transmit",
        "S4:BS/reflect -> S7:BS2/transmit",
        "S4:BS/reflect -> S7:BS2/reflect",
    ])
    if cpaths != expected:
        failures.append(f"FAIL: cascading leaves wrong. got {cpaths}, expected {expected}")
    if "S4:BS/reflect" in cpaths:
        failures.append("FAIL: intermediate arm 'S4:BS/reflect' must NOT get a detector (it feeds BS2)")

    # 3) absorbing reflect output: reflect branch absent -> only the transmit leaf.
    absorbing = _sequential_paths("S4:BS/transmit")
    adets = derive_branch_detectors(absorbing, existing_targets=[], scene_radius=50.0)
    if adets:
        failures.append(f"FAIL: absorbing reflect output produced {len(adets)} detector(s), expected 0")

    # 3b) bugs/0108: reflect rays PRESENT but absorbed inside the cube (the realistic
    #     case the synthetic test #3 omitted). The absorbed leaf must be dropped, so
    #     no phantom reflect detector floats beyond the cube -- and with the reflect
    #     arm gone the transmit leaf reaches the sequential Image -> 0 branch detectors.
    absorbed_arm = _sequential_paths("S4:BS/transmit") + _absorbed_paths(
        "S4:BS/reflect", np.asarray((0.0, 80.0, 150.0))
    )
    abdets = derive_branch_detectors(absorbed_arm, existing_targets=[], scene_radius=50.0)
    if any("reflect" in d.branch_path for d in abdets):
        failures.append(
            "FAIL: an ABSORBED reflect arm still produced a reflect branch detector "
            f"(phantom image plane): {[d.branch_path for d in abdets]}")
    if abdets:
        failures.append(
            f"FAIL: absorbing one arm of a splitter should collapse to the surviving "
            f"transmit leaf (sequential Image), got {len(abdets)} branch detector(s)")

    # 4) no splitter: only the sequential leaf -> none.
    ndets = derive_branch_detectors(_sequential_paths("primary"), existing_targets=[], scene_radius=50.0)
    if ndets:
        failures.append(f"FAIL: no-splitter scene produced {len(ndets)} branch detector(s), expected 0")

    # 5) hard-stop integration: a derived detector is an is_detector target and
    #    appears in Phase A's hard-stop planes.
    if dets:
        from KrakenOS.UI.scene_projector import detector_planes_for_hard_stop

        target = branch_detector_scene_target(dets[0], row_index=100000)
        if not bool(getattr(target, "is_detector", False)):
            failures.append("FAIL: branch detector scene target is not is_detector")
        bundle = SimpleNamespace(targets=[target])
        planes = detector_planes_for_hard_stop(bundle, radius=200.0)
        if len(planes) != 1:
            failures.append(f"FAIL: branch detector not in hard-stop planes (got {len(planes)})")
        elif not np.allclose(planes[0][0], dets[0].center_world, atol=1.0):
            failures.append("FAIL: hard-stop plane center != branch detector focus")

    # 6) B2 (bugs/0093, vendor camera STEP = sensor size): a camera registered to a
    #    branch BLENDS that detector to the camera's active sensor (w x h) and tags
    #    it; arms without a camera keep their footprint size. The scene target then
    #    carries the sensor as its active dims (so the per-branch FOV / sensor
    #    quick-estimation reads the real sensor).
    sized = derive_branch_detectors(
        single, existing_targets=[], scene_radius=50.0,
        branch_camera_sensors={"S4:BS/reflect": ("hr25MCX", (23.04, 23.04))},
    )
    rs = next((d for d in sized if "reflect" in d.branch_path), None)
    ts = next((d for d in sized if "transmit" in d.branch_path), None)
    if rs is None or ts is None:
        failures.append("FAIL: B2 camera-sized derive missing an arm")
    else:
        if abs(rs.half_w - 11.52) > 1e-6 or abs(rs.half_h - 11.52) > 1e-6:
            failures.append(f"FAIL: reflect detector not blended to the 23.04x23.04 sensor (half {rs.half_w},{rs.half_h})")
        if rs.assigned_camera_label != "hr25MCX":
            failures.append(f"FAIL: reflect detector assigned_camera_label = {rs.assigned_camera_label!r}, expected 'hr25MCX'")
        if ts.assigned_camera_label is not None:
            failures.append(f"FAIL: transmit (no camera) should keep assigned_camera_label=None, got {ts.assigned_camera_label!r}")
        if abs(ts.half_w - 11.52) < 1e-6:
            failures.append("FAIL: transmit (no camera) was wrongly resized to the sensor")
        tgt = branch_detector_scene_target(rs, row_index=100000)
        if abs(float(tgt.active_width_mm) - 23.04) > 1e-6 or abs(float(tgt.active_height_mm) - 23.04) > 1e-6:
            failures.append(f"FAIL: reflect scene target active dims != sensor 23.04 ({tgt.active_width_mm},{tgt.active_height_mm})")
        if (tgt.metadata or {}).get("assigned_camera_label") != "hr25MCX":
            failures.append("FAIL: reflect scene target metadata missing assigned_camera_label")

    # 7) reached-image pinning (bugs/0093): a transmit leaf that REACHES the sequential
    #    Image is pinned ONTO that Image (the user's designed focus), not a forward
    #    convergence -- so the detector and image coincide (cube-before-lens fix:
    #    "the original is correct, the image plane lands on the detector"). The reflect
    #    arm (does NOT reach the image) keeps its own converging focus.
    img_target = SimpleNamespace(
        is_detector=True, surface="Image",
        center_world=np.asarray((0.0, 0.0, 300.0), dtype=float),
        active_width_mm=20.0, active_height_mm=20.0,
        metadata={"target_source": "table_row"},
    )
    pinned = derive_branch_detectors(single, existing_targets=[img_target], scene_radius=50.0)
    tp = next((d for d in pinned if "transmit" in d.branch_path), None)
    rp = next((d for d in pinned if "reflect" in d.branch_path), None)
    if tp is None:
        failures.append("FAIL: reached-image pin -- transmit detector missing")
    else:
        if abs(float(tp.center_world[2]) - 300.0) > 1.0:
            failures.append(f"FAIL: transmit detector not pinned to the reached Image z=300 (got {tp.center_world})")
        if tp.focus_source != "reached_image":
            failures.append(f"FAIL: transmit focus_source should be 'reached_image', got {tp.focus_source!r}")
    if rp is not None and not np.allclose(rp.center_world, reflect_focus, atol=1.0):
        failures.append(f"FAIL: reflect arm wrongly moved (should keep its focus {reflect_focus}): {rp.center_world}")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0088 Phase B1 branch detectors")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] one branch detector per terminal leaf branch (cascading + absorbing correct) (bugs/0088 B1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
