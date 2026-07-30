"""bugs/0482 -- a solved image leg is shared between BOTH sections, and its floor sees the camera.

Flag flag_20260730_103719: "change to 30x30 not working: the sensor misplaced to RA mirror. The
camera crash to RA mirror."

Two defects, measured on ``attachment/machine_vision_AZ85_RA_Mirror_BS.py``:

1. The solve fixes the lens->sensor TOTAL, but the whole change landed on the section the gap row
   happens to be -- ``mirror -> sensor``. Across 23x23 then 30x30 that section went
   51.500 -> 38.728 -> 18.860 mm while ``lens rear -> mirror`` sat at 103.270 mm throughout with
   room to spare.
2. ``_image_gap_collision_floor`` protected the SENSOR PLANE (bugs/0468: ``far_min``, half the
   mirror's own extent = 12.5 mm). The leading edge is the camera BODY, bolted behind the sensor
   and reaching its vendor front-to-sensor distance (11.48 mm) back up the leg. 18.86 mm cleared
   the 12.5 mm sensor floor, so the 0468 resolver stood down -- and the body, needing 11.48 mm of
   the 6.36 mm that remained past the mirror face, ended 5.3 mm inside the prism.

Fixed: the floor is ``far_min + front_to_sensor + margin`` (24.98 mm here), and the change is
shared 50:50 between the two sections through ``_apply_folded_image_split`` (which on a frozen
scene slides the breadcrumbed mirror and re-seats sensor AND camera, bugs/0447). Certified on the
real scene with the camera re-seated after each solve, and with bugs/0483 making the mirror's box
truthful -- without 0483 the clearance cannot even be measured:

    field    sec3     sec4     z-gap camera->mirror     baseline sec4 / gap
    23x23   96.884   45.114        +21.13 mm              38.728  /  +3.68
    30x30   86.950   35.180        +11.20 mm              18.860  / -44.86  <- the report
    35x35   82.287   30.517         +6.54 mm              12.500  / -26.89
    40x40   79.525   27.755         +3.78 mm              12.500  / -24.07

Display-free: drives the floor and the share against a stub editor. No Tk, no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0482_fov_solve_shares_image_leg
"""
from __future__ import annotations

from types import SimpleNamespace


def _service(editor):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    return QuickEstimationService(SimpleNamespace(editor=editor))


def _editor(*, split, camera_step=True, front_to_sensor=11.48, applied=None):
    """A stub carrying only what the floor and the share read."""
    return SimpleNamespace(
        _folded_image_conjugate_split=lambda: dict(split) if split is not None else None,
        _step_path_for_label=lambda label: ("/tmp/camera.step" if (camera_step and label == "camera") else None),
        _current_camera_front_to_sensor_mm=lambda: float(front_to_sensor),
        _apply_folded_image_split=(
            applied if applied is not None else (lambda leg, value: (True, f"split {leg}={value}"))
        ),
        rows=[],
    )


# The measured scene's image split, before and after the 30 x 30 solve.
SPLIT_BEFORE = {
    "total": 154.77, "near": 103.27, "far": 51.50,
    "mirror_row": 7, "near_gap_row": 6, "far_gap_row": 7,
    "near_min": 12.5, "far_min": 12.5, "frozen_world": True, "frozen_kind": "image_mirror",
}
SPLIT_AFTER = {**SPLIT_BEFORE, "total": 122.13, "near": 103.27, "far": 18.86}


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.services.quick_estimation import QuickEstimationService  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: quick_estimation unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. the floor sees the camera body -------------------------------------------------
    service = _service(_editor(split=SPLIT_BEFORE))
    floor = float(service._image_gap_collision_floor())
    margin = float(service.IMAGE_LEG_ASSEMBLY_MARGIN_MM)
    check(
        abs(floor - (12.5 + 11.48 + margin)) < 1.0e-9,
        f"A1: the floor is mirror + body + margin = {floor:.4g} mm, not the 12.5 mm sensor floor",
    )
    check(
        abs(float(service._camera_body_image_leg_reach_mm()) - 11.48) < 1.0e-9,
        "A2: the body's reach up the leg is the vendor front-to-sensor distance",
    )
    # The reported gap cleared the OLD floor, which is why 0468 never fired.
    check(
        18.86 > 12.5 and 18.86 < floor,
        f"A3: the reported 18.86 mm gap clears the old 12.5 mm floor but not {floor:.4g} mm",
    )
    # No camera imported -> the sensor plane really is the leading edge; floor unchanged.
    bare = _service(_editor(split=SPLIT_BEFORE, camera_step=False))
    check(
        abs(float(bare._image_gap_collision_floor()) - 12.5) < 1.0e-9,
        "A4: with no camera STEP the floor stays the bare sensor floor (no phantom margin)",
    )
    check(
        float(_service(_editor(split=None))._image_gap_collision_floor()) == 0.0,
        "A5: a scene with no image-side fold has no floor at all",
    )

    # --- B. the change is shared 50:50 -----------------------------------------------------
    calls: list = []

    def _record(leg, value):
        calls.append((leg, float(value)))
        return True, f"split {leg}={value}"

    service = _service(_editor(split=SPLIT_AFTER, applied=_record))
    note = service._rebalance_image_leg_sections(SPLIT_BEFORE)
    delta = SPLIT_AFTER["total"] - SPLIT_BEFORE["total"]  # -32.64
    expected = SPLIT_BEFORE["near"] + delta / 2.0  # 86.95
    check(
        len(calls) == 1 and calls[0][0] == "near" and abs(calls[0][1] - expected) < 1.0e-6,
        f"B1: half the {delta:+.4g} mm change goes to lens->mirror "
        f"({expected:.4g} mm requested, got {calls[0][1] if calls else None})",
    )
    check(
        abs((SPLIT_AFTER["total"] - expected) - 35.18) < 1.0e-2,
        f"B2: the other half leaves mirror->sensor at "
        f"{SPLIT_AFTER['total'] - expected:.4g} mm, clear of the {floor:.4g} mm floor",
    )
    check(bool(note) and "50:50" in note, f"B3: the share is reported to the user ({note.strip()[:60]!r})")

    # --- C. clamped, never below a floor ---------------------------------------------------
    # A total so short that an even share would breach the camera floor: it clamps, and the
    # writer holds the total, so the remainder lands on the other section.
    tight_before = {**SPLIT_BEFORE, "total": 60.0, "near": 40.0, "far": 20.0}
    tight_after = {**tight_before, "total": 40.0, "near": 40.0, "far": 0.0}
    calls.clear()
    service = _service(_editor(split=tight_after, applied=_record))
    service._rebalance_image_leg_sections(tight_before)
    check(
        len(calls) == 1 and abs(calls[0][1] - (40.0 - floor)) < 1.0e-6,
        f"C1: an even share that would breach the floor clamps to total - floor "
        f"({40.0 - floor:.4g} mm, got {calls[0][1] if calls else None})",
    )
    # Both floors cannot fit -> report, do not thrash the geometry.
    impossible_before = {**SPLIT_BEFORE, "total": 60.0, "near": 40.0, "far": 20.0}
    impossible_after = {**impossible_before, "total": 20.0}
    calls.clear()
    service = _service(_editor(split=impossible_after, applied=_record))
    note = service._rebalance_image_leg_sections(impossible_before)
    check(
        not calls and "cannot clear" in note,
        f"C2: when neither section can clear, it reports instead of moving anything ({note.strip()[:70]!r})",
    )

    # --- D. no change, no move -------------------------------------------------------------
    calls.clear()
    service = _service(_editor(split=SPLIT_BEFORE, applied=_record))
    note = service._rebalance_image_leg_sections(SPLIT_BEFORE)
    check(not calls and note == "", "D1: a solve that did not change the total moves nothing")
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, applied=_record))
    check(
        service._rebalance_image_leg_sections(None) == "" and not calls,
        "D2: an unreadable pre-solve split is a no-op, never a guess",
    )
    # A refusing writer must not fail the solve -- the conjugate is already correct.
    service = _service(_editor(split=SPLIT_AFTER, applied=lambda leg, value: (False, "refused")))
    check(
        "skipped" in service._rebalance_image_leg_sections(SPLIT_BEFORE),
        "D3: a writer refusal is reported and swallowed, not raised over a good conjugate",
    )

    # --- E. wired into the solve, after the frozen write (bugs/0447 ordering) --------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.quick_estimation import QuickEstimationService as _QE

        src = _inspect.getsource(_QE._apply_conjugate_pair)
        check("_rebalance_image_leg_sections" in src, "E1: the solve calls the share")
        frozen_at = src.find("apply_image_distance_frozen_aware")
        share_at = src.find("_rebalance_image_leg_sections(_pre_image_split)")
        check(
            frozen_at >= 0 and share_at > frozen_at,
            "E2: the share runs AFTER the frozen image write re-bakes world centres (bugs/0447)",
        )
    except Exception as exc:
        notes.append(f"SKIP: solve source unreadable ({type(exc).__name__}: {exc})")

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
