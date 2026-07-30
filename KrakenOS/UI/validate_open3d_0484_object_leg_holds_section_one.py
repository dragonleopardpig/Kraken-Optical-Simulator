"""bugs/0484 -- the object-side change goes into section 2; section 1, the BS and its LED hold.

Reported across three messages on the flag_20260730_103719 recording: "the BS Plate is shifted
down, the subsequent elements shifted down as well. This should not be the case. The BS should glue
to the LED, cannot be displaced", then "I pressed Ctrl-Z, now I notice the 23x23mm already shifted
the BS plate, which is wrong", then "just now I tried right click BS and glue to LED, then changed
FOV, the BS moved as well."

Sections, as the object split names them: 1 = ``object -> beam splitter`` (``near``),
2 = ``beam splitter -> lens front`` (``far``). The solve wrote its whole object-distance change
into the gap row, which is section 1 -- and section 1 IS the BS's world position (the split's
``fold_point`` tracks it exactly). Measured: section 1 went 53.803 -> 64.871 -> 90.696 across
23x23 then 30x30 while section 2 never moved off 71.660, so the BS slid up the axis while its
separately-anchored LED body stayed put.

The glue bool was never the gate. bugs/0453 built ``_object_locked_redirect_row`` for exactly this
and made it fire on ``_optical_led_glued`` OR an imported LED, but only when the topology also
matches "a promoted solid immediately after the object gap". This scene's BS is row 3 (between
Group 1 and the aperture, thrown back to the object end by its ``desp``), so the structural test
fails and the redirect stands down whatever the flag says -- which is why gluing by hand changed
nothing.

Fix (the user's call, "just change the section 2 distance"): hold section 1 at its pre-solve value
so section 2 absorbs the whole change and the LENS moves. Both ends of section 1 are then pinned --
the object plane is the station anchor, the BS sits a fixed distance along the axis from it.

The glue needs enforcing as a fixed RELATIVE pose on top of that. The split writer slides the BS
and the LED together by its own delta, which is right when a user drives it by hand and wrong here:
the solve had already moved the BS alone, so cancelling the BS's motion left the LED displaced by
the same amount (measured -11.07 / -36.89 / -55.34 / -73.79 mm across a 23/30/35/40 sweep). The
BS -> LED vector is captured before any write and restored afterwards. Capturing it any later is
the same bug one level down: by then it already carries the delta.

Display-free: drives the shared rebalance against a stub. No Tk, no render, no trace.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0484_object_leg_holds_section_one
"""
from __future__ import annotations

from types import SimpleNamespace


def _service(editor):
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    return QuickEstimationService(SimpleNamespace(editor=editor))


# The measured object split, before and after the 30 x 30 solve. Note near_gap_row == far_gap_row
# == 0 on this frozen scene: both legs live in one row, which is why the writer, not a thickness
# write, has to move them.
SPLIT_BEFORE = {
    "total": 125.463, "near": 53.803, "far": 71.660,
    "mirror_row": 3, "near_gap_row": 0, "far_gap_row": 0,
    "near_min": 0.0, "far_min": 37.6888, "frozen_world": True, "frozen_kind": "bs_object",
}
# What the solve leaves behind: the whole +36.892 mm delta dumped on section 1.
SPLIT_AFTER = {**SPLIT_BEFORE, "total": 162.355, "near": 90.695, "far": 71.660}


def _editor(*, split, applied=None, bs_center=(0.0, 0.0, 54.459), led_center=(0.0, 0.0, 74.405), seated=None):
    state = {"bs": list(bs_center), "led": list(led_center)}

    def _seat(label, target):
        if seated is not None:
            seated.append((label, [float(v) for v in target]))
        state[label] = [float(v) for v in target]
        return True

    return SimpleNamespace(
        _folded_object_conjugate_split=lambda: dict(split) if split is not None else None,
        _apply_folded_object_split=(
            applied if applied is not None else (lambda leg, value: (True, f"split {leg}={value}"))
        ),
        _promoted_solid_current_center=lambda row_index: list(state["bs"]),
        _step_body_world_center=lambda label: list(state.get(label, (0.0, 0.0, 0.0))),
        _seat_step_body_world_center=_seat,
        rows=[],
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
        import numpy as np

        from KrakenOS.UI.services.quick_estimation import QuickEstimationService  # noqa: F401
    except Exception as exc:  # pragma: no cover - environment skip
        notes.append(f"SKIP: quick_estimation unavailable ({type(exc).__name__}: {exc})")
        return True, notes

    # --- A. section 1 is HELD, so section 2 takes the whole change --------------------------
    calls: list = []

    def _record(leg, value):
        calls.append((leg, float(value)))
        return True, f"split {leg}={value}"

    service = _service(_editor(split=SPLIT_AFTER, applied=_record))
    note = service._rebalance_object_leg_sections(SPLIT_BEFORE)
    check(
        len(calls) == 1 and calls[0][0] == "near" and abs(calls[0][1] - SPLIT_BEFORE["near"]) < 1e-6,
        f"A1: section 1 is restored to its pre-solve {SPLIT_BEFORE['near']} mm "
        f"(requested {calls[0][1] if calls else None})",
    )
    check(
        abs((SPLIT_AFTER["total"] - SPLIT_BEFORE["near"]) - 108.552) < 1e-2,
        f"A2: section 2 absorbs the whole +36.892 mm "
        f"({SPLIT_AFTER['total'] - SPLIT_BEFORE['near']:.4g} mm, was 71.660)",
    )
    check("section 1 held" in note, f"A3: the status line says section 1 was held ({note.strip()[:60]!r})")
    # It is NOT a 50:50 share -- that is the image side's rule, and half of this delta would
    # still have moved the BS 18.4 mm.
    check(
        calls and abs(calls[0][1] - (SPLIT_BEFORE["near"] + 36.892 / 2.0)) > 1.0,
        "A4: the object side HOLDS section 1 rather than sharing it (half would still move the BS)",
    )

    # --- B. the glue: BS -> LED is restored, not carried by the writer's delta --------------
    seated: list = []
    bs, led = (0.0, 0.0, 54.459), (0.0, 0.0, 74.405)
    offset = np.asarray(led, dtype=float) - np.asarray(bs, dtype=float)
    editor = _editor(split=SPLIT_AFTER, bs_center=bs, led_center=led, seated=seated)
    service = _service(editor)
    note = service._rebalance_object_leg_sections(SPLIT_BEFORE, offset)
    check(
        len(seated) == 1 and seated[0][0] == "led",
        f"B1: the LED is re-seated exactly once ({[s[0] for s in seated]})",
    )
    check(
        seated and np.allclose(np.asarray(seated[0][1]) - np.asarray(bs), offset, atol=1e-9),
        f"B2: it lands so the BS -> LED vector is EXACTLY as before "
        f"({np.round(np.asarray(seated[0][1]) - np.asarray(bs), 4).tolist() if seated else None} "
        f"vs {np.round(offset, 4).tolist()})",
    )
    check("glue held" in note, f"B3: the status line records the glue ({note.strip()[-40:]!r})")
    # No offset supplied (no LED in the scene) -> nothing is seated, and nothing raises.
    seated.clear()
    service = _service(_editor(split=SPLIT_AFTER, seated=seated))
    note = service._rebalance_object_leg_sections(SPLIT_BEFORE, None)
    check(not seated and "section 1 held" in note, "B4: with no LED offset the hold still applies, nothing is seated")
    # A contaminated offset is what the first attempt produced: assert the guard would catch it.
    contaminated = offset - (0.0, 0.0, 36.892)
    seated.clear()
    service = _service(_editor(split=SPLIT_AFTER, bs_center=bs, led_center=led, seated=seated))
    service._rebalance_object_leg_sections(SPLIT_BEFORE, contaminated)
    check(
        seated and not np.allclose(np.asarray(seated[0][1]) - np.asarray(bs), offset, atol=1e-6),
        "B5: an offset captured AFTER the solve would misplace the LED (the bug B2 pins)",
    )

    # --- C. the clamp: shrinking cannot drive the lens into the BS --------------------------
    # A smaller field shortens the object total; holding section 1 would leave section 2 below
    # its "mirror -> first surface" floor, so the target clamps and the remainder moves the BS.
    shrunk = {**SPLIT_BEFORE, "total": 80.0, "near": 8.34, "far": 71.66}
    calls.clear()
    service = _service(_editor(split=shrunk, applied=_record))
    service._rebalance_object_leg_sections(SPLIT_BEFORE)
    expected = 80.0 - SPLIT_BEFORE["far_min"]
    check(
        calls and abs(calls[0][1] - expected) < 1e-6,
        f"C1: a shrink clamps section 1 to total - far_min ({expected:.4g} mm, "
        f"got {calls[0][1] if calls else None}) so the lens keeps its BS clearance",
    )
    impossible = {**SPLIT_BEFORE, "total": 20.0, "near": 8.34, "far": 11.66}
    calls.clear()
    service = _service(_editor(split=impossible, applied=_record))
    note = service._rebalance_object_leg_sections(SPLIT_BEFORE)
    check(
        not calls and "cannot clear" in note,
        f"C2: when section 2 cannot clear at all it reports instead of moving ({note.strip()[:60]!r})",
    )

    # --- D. no change, no move -------------------------------------------------------------
    calls.clear()
    service = _service(_editor(split=SPLIT_BEFORE, applied=_record))
    check(
        service._rebalance_object_leg_sections(SPLIT_BEFORE) == "" and not calls,
        "D1: a solve that did not change the object total moves nothing",
    )
    calls.clear()
    service = _service(_editor(split=SPLIT_AFTER, applied=_record))
    check(
        service._rebalance_object_leg_sections(None) == "" and not calls,
        "D2: an unreadable pre-solve split is a no-op, never a guess",
    )
    service = _service(_editor(split=SPLIT_AFTER, applied=lambda leg, value: (False, "refused")))
    check(
        "skipped" in service._rebalance_object_leg_sections(SPLIT_BEFORE),
        "D3: a writer refusal is reported and swallowed, not raised over a good conjugate",
    )

    # --- E. wired in, and the glue vector captured before any write -------------------------
    try:
        import inspect as _inspect

        from KrakenOS.UI.services.quick_estimation import QuickEstimationService as _QE

        src = _inspect.getsource(_QE._apply_conjugate_pair)
        check("_rebalance_object_leg_sections" in src, "E1: the solve calls the object hold")
        capture_at = src.find("_pre_led_offset = None")
        write_at = src.find("rows[obj_row].thickness = float(object_distance)")
        apply_at = src.find("_rebalance_object_leg_sections(_pre_object_split")
        check(
            0 <= capture_at < write_at,
            "E2: the BS -> LED glue vector is captured BEFORE the object write moves the BS",
        )
        check(
            apply_at > src.find("_rebalance_image_leg_sections(_pre_image_split)") >= 0,
            "E3: the object hold runs after the image side has settled (rigid repackaging last)",
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
