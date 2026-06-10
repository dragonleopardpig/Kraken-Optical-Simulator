"""bugs/0047 -- display-free guard on the gate that decides whether the detector
coverage overlay will REPLACE the Object/Image reference disks.

The flagged bug: with "Det" on but no detector configured (the cemented doublet,
on-axis only), the reference disks were blanked even though the coverage overlay
drew nothing -- leaving the image plane empty ("click Det, Object Disk vanish, no
Image Disk"). The fix gates the disk suppression on
``Open3DSceneRefreshService._detector_coverage_will_draw``, which must be True
ONLY when the coverage overlay's own preconditions hold:

  * a target that is ``is_detector`` with usable active sensor dimensions, AND
  * ``editor._field_metrics_summary()["max_real_image_height"]`` finite and > 0.

This exercises the real helper against real ``SceneTarget3D`` instances (so the
``scene_target_active_dimensions`` fallback is faithful), with a tiny stub editor
supplying the field-metrics dict. No Tk root, no VTK -- it cannot segfault, so it
is the cheap first line of defence; the live render (``validate_det_mode_keeps_
reference_disks``) is the visual proof.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_det_coverage_gate
"""
from __future__ import annotations

from types import SimpleNamespace

from KrakenOS.UI.scene_geometry import SceneTarget3D
from KrakenOS.UI.services.open3d_scene_refresh import Open3DSceneRefreshService


def _service(max_real_image_height) -> Open3DSceneRefreshService:
    """Build the service with a stub inspector whose editor returns the given
    ``max_real_image_height`` from ``_field_metrics_summary``."""
    editor = SimpleNamespace(
        _field_metrics_summary=lambda: {"max_real_image_height": max_real_image_height}
    )
    inspector = SimpleNamespace(editor=editor)
    return Open3DSceneRefreshService(inspector)


def _bundle(*targets) -> SimpleNamespace:
    return SimpleNamespace(targets=list(targets))


def _detector(width=12.0, height=8.0) -> SceneTarget3D:
    return SceneTarget3D(is_detector=True, active_width_mm=width, active_height_mm=height)


def _auto_image_plane_detector() -> SceneTarget3D:
    """The on-axis auto image plane: registers as a detector with a 1 mm
    diameter fallback (no explicit active w/h) -- the flagged scene's target."""
    return SceneTarget3D(is_detector=True, diameter=1.0)


def _object_plane() -> SceneTarget3D:
    return SceneTarget3D(is_detector=False, is_object=True, diameter=20.0)


def run_checks() -> tuple[bool, list[str]]:
    """Return ``(passed, notes)``; notes are prefixed FAIL/PASS so the
    comprehensive harness (Phase 52) can surface them."""
    notes: list[str] = []
    failures: list[str] = []

    def check(label: str, got: bool, want: bool) -> None:
        notes.append(f"{label}: got {got}, want {want}")
        if bool(got) != bool(want):
            failures.append(f"FAIL: {label}: got {got}, expected {want}")

    # (A) No detector target at all -> coverage never draws -> disks must stay.
    check(
        "no detector target",
        _service(15.0)._detector_coverage_will_draw(_bundle(_object_plane())),
        False,
    )

    # (B) THE BUG: a 1 mm auto image-plane "detector" but max_real_image_height
    #     == 0 (on-axis only) -> coverage draws nothing -> disks must stay.
    check(
        "auto image-plane detector, max_real_image_height == 0",
        _service(0.0)._detector_coverage_will_draw(
            _bundle(_object_plane(), _auto_image_plane_detector())
        ),
        False,
    )

    # (C) A real detector with sensor dims AND a positive real image height ->
    #     coverage DOES draw the image circle -> disks are correctly suppressed.
    check(
        "real detector + positive max_real_image_height",
        _service(7.5)._detector_coverage_will_draw(
            _bundle(_object_plane(), _detector())
        ),
        True,
    )

    # (D) Real detector but a non-finite image height (degenerate trace) -> no
    #     draw -> disks stay (the helper must reject NaN, not crash).
    check(
        "real detector + non-finite max_real_image_height",
        _service(float("nan"))._detector_coverage_will_draw(
            _bundle(_detector())
        ),
        False,
    )

    # (E) Real detector but max_real_image_height missing/None -> no draw.
    check(
        "real detector + None max_real_image_height",
        _service(None)._detector_coverage_will_draw(_bundle(_detector())),
        False,
    )

    notes.extend(failures)
    if not failures:
        notes.append(
            "PASS: detector-coverage gate suppresses reference disks only when the "
            "coverage overlay will actually draw (bugs/0047)"
        )
    return (not failures), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    if not passed:
        fails = sum(1 for n in notes if n.startswith("FAIL"))
        print(f"[FAIL] {fails} detector-coverage gate check(s) failed (bugs/0047)")
        return 1
    print("[PASS] detector-coverage gate checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
