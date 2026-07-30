"""bugs/0480 -- the camera seats on the arm that IS its sensor, never on whichever sorted first.

``seat_camera_on_sensor`` took "the arm pinned to the designed Image, else the FIRST
``is_detector`` target". A beam splitter puts a detector on every terminal leaf and
``derive_branch_detectors`` enumerates ``sorted(leaves)`` -- branch-path alphabetical, so
``reflect`` before ``transmit``. On a scene where NO arm is pinned, that fallback seated a
physical camera body onto whichever arm happened to sort first.

Measured on the built-in ``Beam Splitter Two Path Doublets`` (5 detector targets, 0 pinned):

    [0] row=6      Transmit path detector   centre=(0, -0.71, 140.00)   <-- the OLD pick
    [1] row=10     Reflect path detector    centre=(0, 130.00, 45.00)
    [2] row=11     Global diagnostic image  centre=(0, 0, 192.00)       <-- the sensor
    [3] row=100000 Branch (S1/reflect)      centre=(0, 176.33, 45.00)
    [4] row=100001 Branch (S1/transmit)     centre=(0, -0.71, 184.33)

so the body was seated 52 mm short of the Image, on a diagnostic detector row.

The ladder now lives in ``branch_detectors.camera_seating_detector_target`` -- rung 1 reuses
``_reached_image_target``, the SAME helper the branch-detector pin uses, so seating and pinning
cannot disagree about which target is the designed Image.

Display-free: drives the extracted pure ladder against target sets MEASURED from the real
scenes (see bugs/0480 for the transcripts). No Tk, no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0480_camera_seating_arm_choice
"""
from __future__ import annotations


class _Target:
    """The fields the seating ladder reads off a bundle target."""

    def __init__(
        self,
        name,
        centre,
        *,
        surface="Image",
        source="branch_detector",
        focus_source="converging_rays",
        reaches=False,
        camera=None,
        is_detector=True,
        row_index=100000,
    ):
        self.name = name
        self.center_world = tuple(float(v) for v in centre)
        self.surface = surface
        self.is_detector = bool(is_detector)
        self.row_index = int(row_index)
        self.metadata = {
            "target_source": source,
            "focus_source": focus_source,
            "reaches_designed_image": bool(reaches),
            "assigned_camera_label": camera,
        }


def _row(name, centre, *, surface="Standard", row_index=0):
    """A prescription table-row detector (what a scene's own detector/Image rows look like)."""
    return _Target(
        name,
        centre,
        surface=surface,
        source="table_row",
        focus_source="",
        row_index=row_index,
    )


# --- the measured scenes -----------------------------------------------------------------
# Beam Splitter Two Path Doublets: 5 detectors, NONE pinned -> the old fallback decided.
TWO_PATH_DOUBLETS = [
    _row("Transmit path detector", (0.0, -0.71, 140.0), row_index=6),
    _row("Reflect path detector", (0.0, 130.0, 45.0), row_index=10),
    _row("Global diagnostic image", (0.0, 0.0, 192.0), surface="Image", row_index=11),
    _Target("Branch (S1/reflect)", (0.0, 176.33, 45.0), reaches=True, row_index=100000),
    _Target("Branch (S1/transmit)", (0.0, -0.71, 184.33), reaches=True, row_index=100001),
]
TWO_PATH_DOUBLETS_IMAGE = (0.0, 0.0, 192.0)

# machine_vision_AZ85_RA_Mirror_BS: the prescription Image target is DROPPED once branch
# detectors exist (bugs/0093/0098), so only arms remain -- one of them pinned.
AZ85_BS = [
    _Target("Branch (S3/reflect)", (229.9299, 0.0, 2.3032), focus_source="reached_image", reaches=True, row_index=100000),
    _Target("Branch (S3/transmit -> reflect)", (74.39, 0.0989, 31.3456), row_index=100001),
    _Target("Branch (S3/transmit -> transmit)", (-0.4666, 0.0623, 68.3956), row_index=100002),
]
AZ85_BS_IMAGE = (229.9299, 0.0, 2.3032)

# Beam Splitter 50/50 Example: two arms, the transmit one pinned. Note the REFLECT arm sorts
# first -- the exact ordering the old fallback would have followed.
FIFTY_FIFTY = [
    _Target("Branch (S1/reflect)", (0.11, 100.11, 45.11), focus_source="default_distance", row_index=100000),
    _Target("Branch (S1/transmit)", (0.0, 0.0, 108.0), focus_source="reached_image", reaches=True, row_index=100001),
]
FIFTY_FIFTY_IMAGE = (0.0, 0.0, 108.0)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    ok = True

    def check(cond: bool, label: str) -> None:
        nonlocal ok
        notes.append(("PASS " if cond else "FAIL ") + label)
        if not cond:
            ok = False

    try:
        from KrakenOS.UI.services.branch_detectors import (
            SEATING_REASON_AMBIGUOUS,
            SEATING_REASON_ASSIGNED,
            SEATING_REASON_DESIGNED_IMAGE,
            SEATING_REASON_NONE,
            SEATING_REASON_PINNED_ARM,
            SEATING_REASON_REACHING_ARM,
            SEATING_REASON_SOLE,
            camera_seating_detector_target,
        )
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: seating ladder unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    def pick(targets, *, label="camera", image=None):
        return camera_seating_detector_target(targets, camera_label=label, designed_image_point=image)

    # --- A. the reported scene: the sensor, not the alphabetically-first arm --------------
    chosen, reason = pick(TWO_PATH_DOUBLETS, image=TWO_PATH_DOUBLETS_IMAGE)
    check(
        chosen is not None and chosen.name == "Global diagnostic image",
        f"A1: Two Path Doublets seats on the Image row, not the first target "
        f"(got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )
    check(reason == SEATING_REASON_DESIGNED_IMAGE, f"A2: chosen because it IS the designed Image ({reason!r})")
    # The regression itself: the old rule is "first is_detector when nothing is pinned".
    old = next((t for t in TWO_PATH_DOUBLETS if t.is_detector), None)
    check(
        old is not None and chosen is not None and old.name != chosen.name,
        f"A3: the OLD first-target rule would have picked {getattr(old, 'name', None)!r} "
        f"(52 mm short of the Image) -- the ladder does not",
    )
    # ... and it must not depend on target order, which is what "sorted(leaves)" made it do.
    for shift in range(1, len(TWO_PATH_DOUBLETS)):
        rotated = TWO_PATH_DOUBLETS[shift:] + TWO_PATH_DOUBLETS[:shift]
        rotated_choice, _ = pick(rotated, image=TWO_PATH_DOUBLETS_IMAGE)
        if getattr(rotated_choice, "name", None) != "Global diagnostic image":
            check(False, f"A4: the choice moved when the target list was rotated by {shift}")
            break
    else:
        check(True, "A4: the choice is INDEPENDENT of target order (every rotation agrees)")

    # --- B. a scene whose Image target was dropped falls to the pinned arm ---------------
    chosen, reason = pick(AZ85_BS, image=AZ85_BS_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S3/reflect)" and reason == SEATING_REASON_PINNED_ARM,
        f"B1: AZ85 BS (no Image target left) seats on the arm pinned to the Image "
        f"(got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )
    # bugs/0473's reported symptom: the LED-side arm at x = -0.47 must never win.
    check(
        chosen is not None and float(chosen.center_world[0]) > 100.0,
        f"B2: the seated arm is the camera arm (x = {getattr(chosen, 'center_world', (float('nan'),))[0]:.2f}), "
        f"not the LED-side arm at x = -0.47",
    )
    chosen, reason = pick(FIFTY_FIFTY, image=FIFTY_FIFTY_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S1/transmit)" and reason == SEATING_REASON_PINNED_ARM,
        f"B3: 50/50 example seats on the transmit arm although REFLECT sorts first "
        f"(got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )

    # --- C. bugs/0477's stable predicate is the next rung ---------------------------------
    # Same arms, but the imaging one is no longer force-pinned: focus_source flips, its OWN
    # rays still land on the Image. The choice must not move.
    unpinned = [
        _Target("Branch (S3/reflect)", (229.9299, 0.0, 2.3032), focus_source="converging_rays", reaches=True, row_index=100000),
        _Target("Branch (S3/transmit -> reflect)", (74.39, 0.0989, 31.3456), row_index=100001),
        _Target("Branch (S3/transmit -> transmit)", (-0.4666, 0.0623, 68.3956), row_index=100002),
    ]
    chosen, reason = pick(unpinned, image=AZ85_BS_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S3/reflect)" and reason == SEATING_REASON_REACHING_ARM,
        f"C1: an UNPINNED imaging arm is still found, via its own rays (got {reason!r})",
    )
    # The uncommitted precursor to this fix gated candidates on "within 1 mm of the Image",
    # which rejects exactly this arm -- an unpinned arm sits at its own convergence.
    far = [
        _Target("Branch (S3/reflect)", (229.9299, 0.0, 47.7), focus_source="converging_rays", reaches=True, row_index=100000),
        _Target("Branch (S3/transmit)", (-0.4666, 0.0623, 68.3956), row_index=100001),
    ]
    chosen, reason = pick(far, image=AZ85_BS_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S3/reflect)",
        f"C2: an imaging arm 45 mm off the Image is still seated on, not refused "
        f"(got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )

    # --- D. an explicit per-arm camera outranks everything (Phase B2) ---------------------
    assigned = [
        _row("Global diagnostic image", (0.0, 0.0, 192.0), surface="Image", row_index=11),
        _Target("Branch (S1/reflect)", (0.0, 176.33, 45.0), reaches=True, camera="camera2", row_index=100000),
        _Target("Branch (S1/transmit)", (0.0, -0.71, 184.33), reaches=True, camera="camera", row_index=100001),
    ]
    chosen, reason = pick(assigned, label="camera", image=TWO_PATH_DOUBLETS_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S1/transmit)" and reason == SEATING_REASON_ASSIGNED,
        f"D1: a camera REGISTERED to an arm seats on that arm, not on the designed Image "
        f"(got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )
    chosen, reason = pick(assigned, label="camera2", image=TWO_PATH_DOUBLETS_IMAGE)
    check(
        chosen is not None and chosen.name == "Branch (S1/reflect)" and reason == SEATING_REASON_ASSIGNED,
        f"D2: a SECOND camera seats on its own arm (got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )

    # --- E. a plain sequential scene still seats (the 0471 case) --------------------------
    plain = [_row("Image", (0.0, 0.0, 192.0), surface="Image", row_index=8)]
    chosen, reason = pick(plain, image=(0.0, 0.0, 192.0))
    check(chosen is not None, f"E1: a single-detector sequential scene seats ({reason!r})")
    sole = [_Target("Branch (primary)", (0.0, 0.0, 50.0), focus_source="default_distance", row_index=100000)]
    chosen, reason = pick(sole, image=(0.0, 0.0, 192.0))
    check(
        chosen is not None and reason == SEATING_REASON_SOLE,
        f"E2: a lone unpinned arm is still the sensor -- there is nothing to confuse it with ({reason!r})",
    )
    # No designed-Image point at all: the ladder must still work (it is only a tie-break).
    chosen, reason = pick(AZ85_BS, image=None)
    check(
        chosen is not None and chosen.name == "Branch (S3/reflect)",
        f"E3: the ladder works with NO designed-Image point (got {getattr(chosen, 'name', None)!r})",
    )

    # --- F. refuse rather than guess -----------------------------------------------------
    ambiguous = [
        _Target("transmit detector", (0.0, 0.0, 615.1), surface="", source="", focus_source="", row_index=0),
        _Target("reflect detector", (0.0, 411.01, 90.0), surface="", source="", focus_source="", row_index=0),
    ]
    chosen, reason = pick(ambiguous, image=(0.0, 0.0, 868.0))
    check(
        chosen is None and reason == SEATING_REASON_AMBIGUOUS,
        f"F1: two unidentifiable detectors REFUSE (0473: seating the wrong arm is worse than "
        f"not seating) (got {getattr(chosen, 'name', None)!r} via {reason!r})",
    )
    chosen, reason = pick([], image=None)
    check(chosen is None and reason == SEATING_REASON_NONE, f"F2: no detectors at all refuses ({reason!r})")
    lens_only = [_Target("a lens surface", (0.0, 0.0, 1.0), is_detector=False, source="table_row", row_index=2)]
    chosen, reason = pick(lens_only, image=None)
    check(
        chosen is None and reason == SEATING_REASON_NONE,
        f"F3: a non-detector target is never mistaken for a sensor ({reason!r})",
    )

    # --- G. the seating actually consults the ladder --------------------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

        src = _inspect.getsource(ScenePlacementMixin.seat_camera_on_sensor)
        check(
            "camera_seating_detector_target" in src,
            "G1: seat_camera_on_sensor calls the ladder",
        )
        check(
            "is_detector" not in src.split("camera_seating_detector_target")[-1],
            "G2: no hand-rolled detector scan survives after the ladder call",
        )
        check(
            "_designed_image_world_point" in _inspect.getsource(ScenePlacementMixin),
            "G3: the fold-aware designed-Image point helper exists",
        )
    except Exception as exc:
        notes.append(f"SKIP: seating source unreadable ({type(exc).__name__}: {exc})")

    return ok, notes


def run() -> int:
    passed, notes = run_checks()
    for note in notes:
        print((" " if note.startswith(("PASS", "SKIP", "  ")) else "!"), note)
    print("PASS" if passed else "FAIL")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(run())
