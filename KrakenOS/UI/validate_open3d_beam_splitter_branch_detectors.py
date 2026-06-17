#!/usr/bin/env python3
"""Display-free regression for bugs/0088 Phase B1: one branch detector per
TERMINAL leaf branch of the traced ray tree (beam-splitter arms, generalized to
cascading splitters), derived from the traced rays.

Drives `KrakenOS.UI.services.branch_detectors.derive_branch_detectors` against
synthesized ray paths (no trace, no Xvfb, no VTK):
  - single beam splitter -> exactly ONE derived detector (the reflect leaf) at
    the converging focus; the transmit leaf (reaches the Image) gets none.
  - CASCADING (two splitters) -> a detector on each TERMINAL leaf arm only, and
    NONE on the intermediate arm feeding the second splitter.
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


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.branch_detectors import (
        derive_branch_detectors,
        branch_detector_scene_target,
    )

    failures: list[str] = []

    # 1) single beam splitter: transmit (reaches Image) + reflect (converging up).
    reflect_focus = np.asarray((0.0, 80.0, 150.0), dtype=float)
    single = _sequential_paths("S4:BS/transmit") + _converging_paths("S4:BS/reflect", reflect_focus)
    dets = derive_branch_detectors(single, existing_targets=[], scene_radius=50.0)
    if len(dets) != 1:
        failures.append(f"FAIL: single BS expected 1 branch detector, got {len(dets)} ({[d.branch_path for d in dets]})")
    elif "reflect" not in dets[0].branch_path:
        failures.append(f"FAIL: single BS detector is on the wrong branch: {dets[0].branch_path}")
    else:
        d = dets[0]
        if not np.allclose(d.center_world, reflect_focus, atol=1.0):
            failures.append(f"FAIL: reflect detector focus {d.center_world} != converging focus {reflect_focus}")
        if d.focus_source != "converging_rays":
            failures.append(f"FAIL: reflect focus_source = {d.focus_source!r}, expected converging_rays")

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
    expected = ["S4:BS/reflect -> S7:BS2/reflect", "S4:BS/reflect -> S7:BS2/transmit"]
    if cpaths != expected:
        failures.append(f"FAIL: cascading leaves wrong. got {cpaths}, expected {expected} (intermediate must be pruned)")

    # 3) absorbing reflect output: reflect branch absent -> only the transmit leaf.
    absorbing = _sequential_paths("S4:BS/transmit")
    adets = derive_branch_detectors(absorbing, existing_targets=[], scene_radius=50.0)
    if adets:
        failures.append(f"FAIL: absorbing reflect output produced {len(adets)} detector(s), expected 0")

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
