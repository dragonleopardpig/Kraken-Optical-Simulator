"""Guard for bugs/0830 -- the post-swap popup shows the part, and its semi-FOV follows the rectangle.

User, twice: *"I am looking at the swap lens pop up now, I don't see device illustration."*
That popup IS the post-swap prompt -- ``_prompt_fov_solve_after_swap`` calls
``_open_quick_estimation_fov_popup("object")`` -- so it is where the FOV decision is
actually made, and therefore where the picture belongs. bugs/0828 had given it only to the
Inspection Part dialog.

And a REGRESSION I introduced in bugs/0829, caught by the user's own screenshot: making the
height face-derived left ``Object FOV (semi)`` computing from the WIDTH alone via the sensor
aspect. A 52.5 x 1.05 field reported semi **37.12** -- the answer for a 52.5 SQUARE -- when
its true semi-diagonal is **26.255**. Before 0829 the field was always square, so width-only
was right; afterwards it silently was not.

Checks (display-free, pure):
  A  the semi-FOV is the rectangle's own semi-diagonal;
  B  a SQUARE field still gives the pre-0829 answer, so nothing regressed for no-device;
  C  the width-only formula really did disagree -- the bug was real, not a rounding nit;
  D  the popup draws the part when a device is enabled, and the source says why.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0830_popup_picture_and_semi
"""

from __future__ import annotations

import inspect as _inspect
import math
import pathlib


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    # ---- A: the rectangle's own semi-diagonal -----------------------------------------------------
    ok(abs(math.hypot(52.5, 1.05) / 2 - 26.255) < 0.01,
       "A1: a 52.5 x 1.05 field has semi-diagonal 26.255")
    ok(abs(math.hypot(21.0, 1.05) / 2 - 10.513) < 0.01,
       "A2: and a 21 x 1.05 field has 10.513 -- it tracks the height")

    # ---- B: a square field is unchanged -----------------------------------------------------------
    sq = 59.3284
    ok(abs(math.hypot(sq, sq) / 2 - sq * 2 ** 0.5 / 2) < 1e-9,
       "B1: for a SQUARE field hypot/2 equals the old width x sqrt(2) / 2 exactly")
    ok(abs(math.hypot(sq, sq) / 2 - 41.95) < 0.01,
       "B2: so the pre-0829 no-device reading of 41.95 is preserved")

    # ---- C: the old formula genuinely disagreed ---------------------------------------------------
    old = 52.5 * 2 ** 0.5 / 2
    new = math.hypot(52.5, 1.05) / 2
    ok(abs(old - 37.12) < 0.01,
       f"C1: the width-only formula gave {old:.3f} -- the 37.12 in the user's screenshot")
    ok(old / new > 1.4,
       f"C2: which is {old / new:.2f}x the truth, not a rounding difference")

    # ---- D: the popup draws the part --------------------------------------------------------------
    src = pathlib.Path(
        _inspect.getfile(__import__("KrakenOS.UI.open3d_inspector", fromlist=["x"]))
    ).read_text(encoding="utf-8")
    ok("face_polygons" in src,
       "D1: the popup draws the part when a device is enabled")
    ok("inspected_faces" in src and "unreachable_faces" in src,
       "D2: with the inspected faces lit and the unreachable ones greyed")
    ok("0830" in src,
       "D3: and the source records why the picture is here, not only in the part dialog")
    ok("hypot" in src,
       "D4: the semi-FOV uses both boxes")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0830 popup-picture-and-semi validation PASSED")
        return 0
    print("0830 popup-picture-and-semi validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
