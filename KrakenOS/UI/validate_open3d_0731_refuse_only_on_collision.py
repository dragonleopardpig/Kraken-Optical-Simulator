"""Guard for bugs/0731 -- only a real collision refuses the FOV solve.

User: "Refusal of solve is unnecessary for the case of image location shift since we already have
image detached from sensor shows up. Only apply to real collision will do."

Before, an image plane that landed off the sensor bailed the folded conjugate solver to None and
the whole solve refused ("No real-image conjugate for that size"), even though the OBJECT side --
the lens move that actually sets |m| -- was perfectly reachable. Since bugs/0728/0729 the scene
DRAWS the focused image where it forms, so the shift is visible and needs no refusal.

Now the solver books the object side and reports the image shift as a focus residual; the only
refusals left are real ones: no conjugate at all, no lens block, a parked solid inside the block,
or the object-side physical-room gate (a collision).

Measured on om05a (`bugs/0731_refuse_only_on_collision.md`):
  FOV 20 -> solves (lens -138.6 mm, residual -98.0)   FOV 30 -> now solves (+35.8, -93.9)
  FOV 55 -> now solves (+89.4, -33.2)                 FOV 5  -> still REFUSES (needs 178.8 mm
                                                       of room, has 145.5, short by 33.3)

Checks (display-free source pins -- the behaviour itself is scene-level and evidenced in the doc):
  A  the folded solver no longer returns None on the image-side gate; it flags the result.
  B  the flag rides the returned dict on every path (False when the image side is reachable).
  C  the caller turns the flag into a focus residual (never an image-gap write) and says why,
     pointing at the focused-image plane.
  D  the collision refusals are untouched: the object-side room gate still returns False, and the
     Force hint still exists.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0731_refuse_only_on_collision
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import paraxial_tools
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    folded = inspect.getsource(paraxial_tools.ParaxialToolsMixin._folded_conjugate_gaps_for_magnification)

    # ---- A / B: the solver reports instead of bailing ------------------------------------------
    gate_at = folded.find("if image_distance <= 1e-6:")
    tail_at = folded.find("return {")
    between = folded[gate_at:tail_at] if gate_at >= 0 and tail_at > gate_at else ""
    ok(
        gate_at >= 0 and tail_at > gate_at and "return None" not in between,
        "A1: the image-side gate no longer returns None -- the solve is not refused for a shift",
    )
    ok(
        "image_side_unreachable = True" in folded and "image_side_unreachable = False" in folded,
        "A2: the gate flags the result both ways",
    )
    ok(
        '"image_side_unreachable": bool(image_side_unreachable)' in folded,
        "B1: the flag rides the returned dict",
    )
    # the OBJECT-side bail is a different thing and must still refuse
    object_bail = folded.find("no lens-leg slide to book it on")
    ok(
        object_bail >= 0 and "return None" in folded[object_bail: object_bail + 200],
        "B2: the OBJECT-side bail (no way to move the lens) still returns None -- that one is real",
    )

    # ---- C: the caller reports it as a residual ---------------------------------------------------
    solve = inspect.getsource(QuickEstimationService._apply_conjugate_pair)
    ok(
        'folded.get("image_side_unreachable")' in solve and "image_locked_reason = image_locked_reason or (" in solve,
        "C1: the caller turns the flag into an image-write lock rather than a refusal",
    )
    ok(
        "see the focused-image plane" in solve,
        "C2: the reason points the user at the drawn focused-image plane",
    )
    ok(
        'bool(folded.get("image_side_unreachable"))' in solve
        and "_fov_solve_focus_residual_info" in solve,
        "C3: the residual branch fires for an unreachable image side even when the lens did not "
        "move as a thickness pair",
    )
    lock_at = solve.find('folded.get("image_side_unreachable")')
    write_at = solve.find("img_changes = (")
    ok(
        0 <= lock_at < write_at,
        "C4: the lock is decided BEFORE the image-gap write is assembled (so nothing is booked)",
    )

    # ---- D: collisions still refuse ----------------------------------------------------------------
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    mover = inspect.getsource(ScenePlacementMixin.translate_lens_block_along_leg)
    # bugs/0740 reworded the refusal (the zero-room case now reads "no physical room is left at
    # all"), so pin the GATE, not its prose -- the sentence is not the contract.
    ok(
        '"kind": "physical_room"' in mover and "of physical room is left" in mover
        and "return None" in mover,
        "D1: the object-side physical-room gate (the real collision) still refuses, and stamps a "
        "structured refusal the solve can act on",
    )
    ok(
        "Force FOV to SEE the collision" in mover,
        "D2: the refusal still offers the Force bypass",
    )
    from KrakenOS.UI.services.system_info_hud import format_solve_refusal_lines

    lines = format_solve_refusal_lines(
        {
            "requested_fov_wh": [5.0, 5.0],
            "lens_move_needed_mm": -178.8,
            "leg_room_mm": 145.5,
            "reason": "that field needs the lens -178.8 mm along its leg, but only 145.5 mm of "
                      "physical room is left before its body reaches RA mirror 1 (50 mm)",
        }
    )
    ok(
        lines and lines[0].startswith("SOLVE REFUSED") and any("short by 33.3" in line for line in lines),
        f"D3: a collision refusal still banners with the shortfall ({lines[1] if len(lines) > 1 else None!r})",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0731 refuse-only-on-collision validation PASSED")
        return 0
    print("0731 refuse-only-on-collision validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
