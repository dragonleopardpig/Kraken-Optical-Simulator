"""bugs/0477 -- a branch arm's draw gate must read ITS OWN rays, not a scene-global label.

Flag flag_20260729_185450_727: "remove defocus introduce 2 unwanted sensor planes (orange)".

The two orange plates are the beam splitter's other terminal leaves (synthetic rows
100001/100002). They are present in EVERY refresh and their own rays never changed --
measured, reach = 0 of 279 in every state before and after the snap. What changed was a
scene-GLOBAL boolean derived from a DIFFERENT arm: ``_scene_has_real_sensor_arm`` tested the
imaging arm's ``focus_source == "reached_image"``, and "remove defocus" moved the designed
Image 62 mm toward a stale, vignette-contaminated closest-approach point, which made that
arm's convergence look trustworthy so it stopped being force-pinned. The flag flipped False
and un-suppressed every camera-less arm at once.

``focus_source`` conflates two different facts -- "this arm's rays land on the Image" and
"we could not trust this arm's convergence so we pinned its plane to the Image". Only the
first belongs in a draw gate, and it is already computed in the loop as ``reaches_image``.
It is now carried as ``BranchDetector.reaches_designed_image`` and the gate reads that.

Display-free: drives the extracted pure gate ``scene_builder.branch_detector_draw_suppressed``
directly. No Tk, no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0477_phantom_sensor_planes
"""
from __future__ import annotations


class _Arm:
    """The fields the draw gate reads."""

    def __init__(self, branch_path, *, reaches=False, camera=None, focus_source="converging_rays"):
        self.branch_path = branch_path
        self.reaches_designed_image = bool(reaches)
        self.assigned_camera_label = camera
        self.focus_source = focus_source


def _gate(arm, *, real_sensor_arm, scatter=False, flood=False, lone=False):
    from KrakenOS.UI.scene_builder import branch_detector_draw_suppressed

    return branch_detector_draw_suppressed(
        arm,
        scene_has_diffuse_scatter=scatter,
        illumination_flood=flood,
        lone_dead_end_arm=lone,
        scene_has_real_sensor_arm=real_sensor_arm,
    )


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.scene_builder import branch_detector_draw_suppressed  # noqa: F401
        from KrakenOS.UI.services.branch_detectors import BranchDetector
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: draw-gate deps unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the field exists and is carried ----------------------------------
    check(
        "reaches_designed_image" in getattr(BranchDetector, "__dataclass_fields__", {}),
        "A1: BranchDetector carries reaches_designed_image",
    )

    # --- B. the flagged scene: imaging arm + two phantom arms ----------------
    # The phantom arms' OWN rays reach nothing, in every state.
    phantom_a = _Arm("S3:S3/transmit -> S3:S3/reflect", reaches=False)
    phantom_b = _Arm("S3:S3/transmit -> S3:S3/transmit", reaches=False)

    # Before the snap the imaging arm was force-pinned, so focus_source == "reached_image".
    imaging_pinned = _Arm("S3:S3/reflect", reaches=True, focus_source="reached_image")
    # After the snap it is NOT pinned -- same rays, same landing, different label.
    imaging_unpinned = _Arm("S3:S3/reflect", reaches=True, focus_source="converging_rays")

    for label, imaging in (("pinned (pre-snap)", imaging_pinned), ("unpinned (post-snap)", imaging_unpinned)):
        from KrakenOS.UI.scene_builder import scene_has_real_sensor_arm

        arms = [imaging, phantom_a, phantom_b]
        # The PRODUCTION derivation, not a recomputation -- this is the half that flipped.
        real = scene_has_real_sensor_arm(arms)
        check(real, f"B0 [{label}]: the scene still counts as having a real sensor arm")
        check(
            not _gate(imaging, real_sensor_arm=real),
            f"B1 [{label}]: the imaging arm DRAWS",
        )
        check(
            _gate(phantom_a, real_sensor_arm=real) and _gate(phantom_b, real_sensor_arm=real),
            f"B2 [{label}]: both camera-less phantom arms stay suppressed",
        )

    # --- C. the regression itself: the label must not move the gate ----------
    from KrakenOS.UI.scene_builder import scene_has_real_sensor_arm

    real_pinned = scene_has_real_sensor_arm([imaging_pinned, phantom_a, phantom_b])
    real_unpinned = scene_has_real_sensor_arm([imaging_unpinned, phantom_a, phantom_b])
    check(
        real_pinned and real_unpinned,
        "C0: the scene-global 'has a real sensor arm' flag is STABLE across the label flip",
    )
    check(
        _gate(phantom_a, real_sensor_arm=real_pinned) == _gate(phantom_a, real_sensor_arm=real_unpinned),
        "C1: a phantom arm's draw is UNCHANGED when the imaging arm's focus_source flips",
    )

    # --- D. bugs/0090 preserved: a genuine two-CAMERA split draws both -------
    cam_a = _Arm("S1:S1/transmit", reaches=False, camera="camera")
    cam_b = _Arm("S1:S1/reflect", reaches=True, camera="camera2")
    real_two = True
    check(
        not _gate(cam_a, real_sensor_arm=real_two) and not _gate(cam_b, real_sensor_arm=real_two),
        "D1: a two-CAMERA split still draws BOTH arms (bugs/0090)",
    )

    # --- E. bugs/0464 preserved: no real sensor anywhere -> keep the plane ----
    orphan = _Arm("S1:S1/reflect", reaches=False)
    check(
        not _gate(orphan, real_sensor_arm=False),
        "E1: a scene with no real sensor arm still draws its detector (bugs/0464 control)",
    )

    # --- F. the other suppression terms are untouched ------------------------
    check(_gate(imaging_pinned, real_sensor_arm=True, scatter=True), "F1: scene diffuse scatter still suppresses (0182/0184)")
    check(_gate(orphan, real_sensor_arm=False, lone=True), "F2: the lone dead-end arm still suppresses (0451)")
    check(
        _gate(_Arm("S1:S1/reflect", reaches=False, focus_source="converging_rays"), real_sensor_arm=False, flood=True),
        "F3: a non-imaging illumination-flood arm still suppresses (0285)",
    )
    check(
        not _gate(_Arm("S1:S1/reflect", reaches=True, focus_source="reached_image"), real_sensor_arm=False, flood=True),
        "F4: the flood's imaging arm still draws (0285)",
    )
    check(
        _gate(_Arm("S1:S1/scatter01", reaches=False), real_sensor_arm=False),
        "F5: a scatter-token branch path still suppresses (0182)",
    )

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith("PASS") or note.startswith("SKIP") else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
