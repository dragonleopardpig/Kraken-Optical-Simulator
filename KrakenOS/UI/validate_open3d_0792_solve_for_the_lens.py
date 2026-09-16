"""bugs/0792 -- a fixed-conjugate catalogue states the conjugates, so solve for the LENS.

`f (2 + m + 1/m) + HH' = track` is one equation in two unknowns. bugs/0653 closed it by assuming
coincident principal planes, which is right near 1x and false above it: a 4x lens at 65 mm working
distance would need a 325 mm track, where Edmund's own 62-793 has 192.5 mm and the SPO TCL4.0X has
225 mm. The derived front principal plane then lands in front of the barrel and bugs/0647's
registration law refuses -- correctly, but the lens is perfectly describable.

Fix the two groups where the hardware puts them (just inside each end of the housing) and the
conjugates determine their powers exactly. Above 1x that pair comes out TELEPHOTO -- a negative
rear group -- which is why its equivalent principal planes sit outside the barrel. The groups
themselves stay inside, which is what the drawing and the trace care about.

Display-free and offline: closed-form optics, no PDF, no app.
"""

from __future__ import annotations

import math

from KrakenOS.UI.services.machine_vision_folder_import import (  # noqa: E402
    conjugate_stop_diameter,
    solve_conjugate_two_groups,
)

C_FLANGE = 17.526
CASES = (
    # name,                m,    WD,     housing, working f/#
    ("Edmund 62-793 (4X)", 4.00, 65.0,   110.0,   26.2),
    ("SPO TCL4.0X-65DI",   4.00, 65.0,   142.5,   12.5),
    ("a 2X at 80 mm WD",   2.00, 80.0,   120.0,   16.0),
)


def _delivered(solve: dict, wd: float, flange: float) -> "tuple[float, float, float]":
    """Trace the emitted groups paraxially: returns (magnification, object gap, image gap)."""
    sol = solve["solution"]
    a = wd + sol.g1
    v1 = a * sol.f1 / (a - sol.f1)
    m1 = -v1 / a
    s2 = v1 - sol.d
    b = 1.0 / (1.0 / sol.f2 + 1.0 / s2)
    return m1 * (b / s2), a - sol.g1, b - sol.g2


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    for name, m, wd, housing, fno in CASES:
        solve = solve_conjugate_two_groups(m, wd, housing, C_FLANGE)
        sol = solve["solution"]

        # ---- A: it delivers the CONTRACT: m, at WD, with the image at the flange ---------------
        delivered, object_gap, image_gap = _delivered(solve, wd, C_FLANGE)
        ok(abs(abs(delivered) - m) < 1e-3,
           f"A: {name}: delivers m = {delivered:+.4f} (datasheet {-m:+.1f})")
        ok(abs(object_gap - wd) < 1e-6,
           f"A: {name}: object sits at the stated working distance ({object_gap:.3f})")
        ok(abs(image_gap - C_FLANGE) < 1e-3,
           f"A: {name}: image lands at the mount flange ({image_gap:.3f})")

        # ---- B: both GROUPS are inside the housing (the equivalent PPs need not be) -------------
        ok(0.0 < sol.g1 < housing and 0.0 < sol.g2 < housing and sol.d > 0.0,
           f"B: {name}: both groups sit inside the {housing:g} mm housing")
        ok(sol.d + sol.g1 + sol.g2 - housing < 1e-6,
           f"B: {name}: the groups span exactly the housing")

        # ---- C: above 1x the pair is telephoto, which is the whole point ------------------------
        if m > 1.0:
            ok(sol.f1 > 0.0 > sol.f2,
               f"C: {name}: telephoto pair (f1 {sol.f1:.3f}, f2 {sol.f2:.3f}) -- a positive pair "
               f"cannot reach this magnification in this track")

        # ---- D: the stop is the CONE, not effl/f# ----------------------------------------------
        stop = conjugate_stop_diameter(solve, m, fno)
        naive = abs(solve["effl"]) / fno
        ok(stop > naive * 3.0,
           f"D: {name}: stop {stop:.3f} mm from the working f-number, not {naive:.3f} from effl/f#")
        # and the cone must come back OUT of that stop: trace the marginal ray from the stop rim
        # back to the object and recover the working f-number the catalogue stated
        v1 = solve["v1"]
        height_at_group1 = (stop / 2.0) / (1.0 - sol.f1 / v1)
        na_back = height_at_group1 / solve["a"]
        fno_back = m / (2.0 * na_back)
        ok(abs(fno_back - fno) < 1e-6,
           f"D: {name}: that stop traces back to f/{fno_back:.3f} (catalogue f/{fno:g})")

        # ---- E: telecentricity is placeable -- the stop falls between the groups ----------------
        ok(0.0 < sol.f1 < sol.d,
           f"E: {name}: the stop's telecentric position (f1 = {sol.f1:.3f}) lies between the groups")

    # ---- F: it refuses geometry it cannot honour ------------------------------------------------
    for bad, why in (((4.0, 65.0, 0.0, C_FLANGE), "a housing with no length"),
                     ((0.0, 65.0, 110.0, C_FLANGE), "a zero magnification")):
        try:
            solve_conjugate_two_groups(*bad)
            ok(False, f"F: accepted {why}")
        except ValueError:
            ok(True, f"F: refuses {why}")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0792 conjugate-solve validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
