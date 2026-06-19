#!/usr/bin/env python3
"""Display-free regression for bugs/0097: branch detectors on a folded two-arm scene.

`derive_branch_detectors` pins a leaf's focus to the reached sequential Image (the
bugs/0093 reached-image pin) so a transmit detector coincides with the image it
reaches. But `_reached_image_target` returns the single furthest global Image, and
in a beam-splitter SPLIT *every* terminal leaf that lands on a detector trips
`reaches_image`. So the reflect leaf -- whose rays travel +Y to its own detector --
was pinned onto the +Z global Image too, collapsing BOTH branch detectors onto
(0,0,192): the user's "two perpendicular orange squares at the transmit end" of
beam_splitter_two_arm_doublets (one +Z normal, one +Y normal, same point).

The fix only applies the pin when the reached image lies on THIS leaf's beam (ahead
of the exit and aligned with the mean exit direction), so the reflect leaf keeps its
own +Y convergence focus.

This builds two synthetic leaf bundles -- transmit converging at the +Z global
image, reflect converging up the +Y arm -- and asserts the two detectors land on
their own arms (not collapsed).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_branch_detector_multi_arm

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np


def _ray(points, branch_path):
    return SimpleNamespace(
        points_world=np.asarray(points, dtype=float),
        branch_path=branch_path,
        branch_label=branch_path,
        reaches_image=True,  # both arms land on a detector -> both trip reaches_image
    )


def _scene():
    # Transmit leaf: four rays converging at the +Z global image (0,0,192).
    transmit = [
        _ray([[4.0, 0.0, 140.0], [-4.0, 0.0, 244.0]], "S1:BS/transmit"),
        _ray([[-4.0, 0.0, 140.0], [4.0, 0.0, 244.0]], "S1:BS/transmit"),
        _ray([[0.0, 4.0, 140.0], [0.0, -4.0, 244.0]], "S1:BS/transmit"),
        _ray([[0.0, -4.0, 140.0], [0.0, 4.0, 244.0]], "S1:BS/transmit"),
    ]
    # Reflect leaf: four rays converging UP the +Y arm at (0,130,45).
    reflect = [
        _ray([[4.0, 100.0, 45.0], [-4.0, 160.0, 45.0]], "S1:BS/reflect"),
        _ray([[-4.0, 100.0, 45.0], [4.0, 160.0, 45.0]], "S1:BS/reflect"),
        _ray([[0.0, 100.0, 49.0], [0.0, 160.0, 41.0]], "S1:BS/reflect"),
        _ray([[0.0, 100.0, 41.0], [0.0, 160.0, 49.0]], "S1:BS/reflect"),
    ]
    global_image = SimpleNamespace(
        is_detector=True,
        surface="Image",
        metadata={},
        center_world=np.asarray([0.0, 0.0, 192.0], dtype=float),
        diameter=45.0,
    )
    return transmit + reflect, [global_image]


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.branch_detectors import derive_branch_detectors

    failures: list[str] = []
    ray_paths, targets = _scene()
    detectors = derive_branch_detectors(ray_paths, existing_targets=targets, scene_radius=200.0)

    if len(detectors) != 2:
        return False, [f"FAIL: expected 2 branch detectors (one per arm), got {len(detectors)}"]

    by_arm = {("transmit" if "transmit" in d.branch_path else "reflect"): d for d in detectors}
    if set(by_arm) != {"transmit", "reflect"}:
        return False, [f"FAIL: expected a transmit + a reflect leaf, got {[d.branch_path for d in detectors]}"]

    tx, rx = by_arm["transmit"], by_arm["reflect"]
    tx_c = np.asarray(tx.center_world, dtype=float)
    rx_c = np.asarray(rx.center_world, dtype=float)

    # Transmit detector pins to the global image it reaches.
    if np.linalg.norm(tx_c - np.asarray([0.0, 0.0, 192.0])) > 2.0:
        failures.append(f"FAIL: transmit detector should pin to the global image (0,0,192), got {tx_c.tolist()}")

    # Reflect detector must stay on its OWN +Y arm, NOT collapse onto the global image.
    if np.linalg.norm(rx_c - np.asarray([0.0, 0.0, 192.0])) < 5.0:
        failures.append(f"FAIL: reflect detector collapsed onto the global image at {rx_c.tolist()} (0097 not fixed)")
    if rx_c[1] < 50.0:
        failures.append(f"FAIL: reflect detector should sit up the +Y arm (y~130), got y={rx_c[1]:.1f}")

    # Their normals stay per-arm (transmit +Z, reflect +Y).
    if abs(float(np.asarray(tx.normal_world, dtype=float)[2])) < 0.7:
        failures.append("FAIL: transmit detector normal should be ~+Z")
    if abs(float(np.asarray(rx.normal_world, dtype=float)[1])) < 0.7:
        failures.append("FAIL: reflect detector normal should be ~+Y")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0097 two-arm branch-detector collapse")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] branch detectors stay on their own arms; the reflect leaf is not pinned to the global image (bugs/0097)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
