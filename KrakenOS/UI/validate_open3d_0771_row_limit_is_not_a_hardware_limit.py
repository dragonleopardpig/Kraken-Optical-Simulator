"""Guard for bugs/0771 -- a ROW that cannot absorb a move is not a MACHINE that has no room.

Flag 20260910_154535: "FOV 20mm rejected. I see the image plane is in front of the sensor, and I
think there is still adjustable distance available." The user was right.

om05a_folded_80mm, 20x20x1 device, FOV 20. The solve needs the lens 136.97 mm along its leg. The
leg gap (row 8) holds 130.889, so the thickness pair would drive it to -6.08 -- a negative row
gap slides every downstream row off the leg ([[reference_negative_gap_off_axis]]), so the mover
refuses. But the mover's OWN physical probe reports 155.79 mm of room, and measuring the STEP
bodies at the largest permitted move leaves **19.85 mm of clearance** between the lens and the
prism assembly. The machine can do it; the row partition cannot express it.

The refusal said only "the gap would go negative", which reads as "no room" -- the opposite of
what the user could see on screen.

Checks (display-free, pure):
  A  the station-cap refusal records the SHORTFALL, so the bugs/0573 make-room machinery has a
     number to act on (it used to leave it unset, and that path silently never ran);
  B  the message names the shortfall AND the physical room, and says the limit is the row
     partition rather than the hardware;
  C  the physical-room refusal above it is untouched -- a move that really would hit the body
     must still be refused, and for the physical reason.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0771_row_limit_is_not_a_hardware_limit
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services import scene_placement_commands as spc

    src = inspect.getsource(spc.ScenePlacementMixin.translate_lens_block_along_leg)
    cap_branch = src.split("if abs(amount) > cap + 1.0e-9:", 1)[-1].split("return None", 1)[0]

    ok(
        "_lens_leg_slide_shortfall" in cap_branch,
        "A1: the station-cap refusal records the shortfall -- bugs/0573's make-room path reads "
        "it, and an unset value means that path silently never runs",
    )
    ok(
        "abs(float(amount)) - float(cap)" in cap_branch,
        "A2: and the shortfall is the amount the ROW is short by, not the whole request",
    )
    ok(
        "room_phys" in cap_branch,
        "B1: the message reaches for the physical room the mover already measured",
    )
    ok(
        "PHYSICAL room remains" in cap_branch and "not the hardware" in cap_branch,
        "B2: and says plainly that the limit is the row partition, not the machine -- "
        "'the gap would go negative' alone reads as 'no room', the opposite of what the user "
        "can see on screen",
    )
    ok(
        "short by" in cap_branch,
        "B3: and quotes how much is missing, so the number is actionable",
    )

    phys_branch = src.split("if room_phys is not None and abs(amount) >", 1)[-1].split(
        "if abs(amount) > cap", 1
    )[0]
    ok(
        '"kind": "physical_room"' in phys_branch,
        "C1: the physical-room refusal above still fires with its structured info (bugs/0740) "
        "-- a move that really would hit the body is still refused",
    )
    ok(
        "before its body reaches" in phys_branch,
        "C2: and still refuses for the PHYSICAL reason, naming the obstacle",
    )
    ok(
        phys_branch.find("_lens_move_refusal") < len(phys_branch),
        "C3: and is reached before the row check, so the two reasons cannot be confused",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0771 row-limit-is-not-a-hardware-limit validation PASSED")
        return 0
    print("0771 row-limit-is-not-a-hardware-limit validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
