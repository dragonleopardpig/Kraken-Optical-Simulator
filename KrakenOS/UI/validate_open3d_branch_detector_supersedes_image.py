#!/usr/bin/env python3
"""Display-free regression for bugs/0092: when a beam-splitter split derives a
branch detector on the transmit arm, the redundant (often zero-size) sequential
Image clear-aperture marker must not still draw beyond it.

User: "there is a previous 1mm detector after the new detector." The transmit arm
gets a derived branch detector at its focus (bugs/0090); the sequential Image
(z further along, ~0 size) is superseded but was still drawn as a ~1 mm marker.

Fix: `Open3DSceneRefreshService._suppress_reference_aperture` also suppresses the
Image reference disk when the scene has a branch detector (in addition to the
existing detector-coverage-overlay suppression, bugs/0033/0047). Object planes and
single-path scenes are unaffected.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_branch_detector_supersedes_image

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations


def run_checks() -> tuple[bool, list[str]]:
    from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService

    f = Open3DSceneRefreshService._suppress_reference_aperture
    failures: list[str] = []

    # bugs/0092: Image suppressed once a branch detector supersedes it.
    if not f("Image", detector_coverage_active=False, scene_has_branch_detector=True):
        failures.append("FAIL: sequential Image not suppressed when a branch detector supersedes it (bugs/0092)")

    # Single-path scene (no branch detector, no coverage) -> Image disk stays.
    if f("Image", detector_coverage_active=False, scene_has_branch_detector=False):
        failures.append("FAIL: Image disk wrongly suppressed in a plain single-path scene")

    # Object plane is never a branch-detector arm -> not suppressed by the branch rule.
    if f("Object", detector_coverage_active=False, scene_has_branch_detector=True):
        failures.append("FAIL: Object disk suppressed by the branch-detector rule (should stay)")

    # Existing bugs/0033/0047 behaviour intact: coverage overlay suppresses both.
    if not f("Object", detector_coverage_active=True, scene_has_branch_detector=False):
        failures.append("FAIL: Object disk not suppressed under detector-coverage overlay (bugs/0047 regressed)")
    if not f("Image", detector_coverage_active=True, scene_has_branch_detector=False):
        failures.append("FAIL: Image disk not suppressed under detector-coverage overlay (bugs/0047 regressed)")

    # A non Object/Image surface is never suppressed by this gate.
    if f("Standard", detector_coverage_active=True, scene_has_branch_detector=True):
        failures.append("FAIL: a Standard optical surface was suppressed as a reference aperture")

    return (not failures), failures


def main() -> int:
    passed, failures = run_checks()
    if not passed:
        print("[FAIL] bugs/0092 branch detector supersedes the sequential Image disk")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] branch detector supersedes the redundant sequential Image marker (bugs/0092)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
