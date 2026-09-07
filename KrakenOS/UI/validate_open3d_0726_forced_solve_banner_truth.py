"""Guard for bugs/0726 -- the forced-solve banner must report what actually happened.

Flag 20260907_083535_680: "changed FOV to 20x20, solved refused, forced crash. But the lens is
not crashing." Forcing FOV 20 on om05a moves the lens 138.6 mm into 158.9 mm of physical room,
so it FITS with 20.3 mm clearance and the solve returns ok=True -- yet the in-scene banner read:

    SOLVE REFUSED -- the drawn scene does NOT deliver this request
    FORCED solve applied -- inspect the 3D overlap
    FORCED: applied; 20.32 mm clearance to RA mirror 1 (50 mm) body

...a refusal heading over a successful solve, and an instruction to inspect an overlap that does
not exist. The heading, the default reason and the banner colour now follow the outcome.

Checks (display-free, pure formatters + wiring pins):
  A  solve_banner_outcome classifies: nothing applied -> "refused"; applied with negative
     penetration -> "forced_crash"; applied with clearance (or unmeasured room) -> "forced_fits";
     empty/None -> "".
  B  a fits banner never says "SOLVE REFUSED" and never mentions an overlap; it names the
     clearance and the obstacle.
  C  a crash banner DOES say the lens penetrates and points at the 3D overlap; a plain refusal
     keeps the original heading and the Force hint.
  D  a fits banner still carries a REAL earlier refusal reason (why the plain solve said no) but
     never invents one.
  E  wiring pins: the forced branch only defaults the overlap reason when it penetrates; the
     inspector picks the banner colour from the outcome (amber when it fits, red otherwise).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0726_forced_solve_banner_truth
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.system_info_hud import (
        format_solve_refusal_lines,
        solve_banner_outcome,
    )

    refused = {
        "requested_fov_wh": [20.0, 20.0],
        "target_m": 1.152,
        "lens_move_needed_mm": -333.5,
        "leg_room_mm": 158.9,
        "reason": "No real-image conjugate for that size (near the focal point?).",
    }
    fits = {
        "forced_penetration_mm": 20.324,
        "forced_room_mm": 158.936,
        "forced_obstacle": "RA mirror 1 (50 mm)",
        "forced_moved_mm": 138.611,
        "forced_room_method": "aabb",
        "forced_station_room_mm": 180.47,
    }
    crash = {
        "forced_penetration_mm": -21.533,
        "forced_room_mm": 158.936,
        "forced_obstacle": "RA mirror 1 (50 mm)",
        "forced_moved_mm": 180.469,
        "forced_capped_mm": 192.3,
        "forced_drawn_mm": 180.469,
    }
    no_body = {"forced_moved_mm": 40.0, "forced_room_method": "none", "forced_station_room_mm": 90.0}

    # ---- A: classification -----------------------------------------------------------------
    ok(
        solve_banner_outcome(refused) == "refused"
        and solve_banner_outcome(fits) == "forced_fits"
        and solve_banner_outcome(crash) == "forced_crash"
        and solve_banner_outcome(no_body) == "forced_fits"
        and solve_banner_outcome({}) == ""
        and solve_banner_outcome(None) == "",
        "A1: outcomes classify as refused / forced_fits / forced_crash / '' "
        f"({solve_banner_outcome(refused)}, {solve_banner_outcome(fits)}, "
        f"{solve_banner_outcome(crash)}, {solve_banner_outcome(no_body)})",
    )

    # ---- B: the fits banner ------------------------------------------------------------------
    fits_lines = format_solve_refusal_lines(fits)
    fits_text = " ".join(fits_lines).lower()
    ok(
        fits_lines and "forced solve applied" in fits_lines[0].lower() and "fits" in fits_lines[0].lower(),
        f"B1: a forced move that fits leads with FITS, not REFUSED ({fits_lines[0] if fits_lines else None!r})",
    )
    ok(
        "solve refused" not in fits_text and "overlap" not in fits_text and "penetrat" not in fits_text,
        f"B2: the fits banner never says REFUSED, overlap or penetrates ({fits_text[:120]!r})",
    )
    ok(
        "20.32" in " ".join(fits_lines) and "RA mirror 1 (50 mm)" in " ".join(fits_lines),
        "B3: the fits banner still names the clearance and the obstacle",
    )

    # ---- C: the crash banner and the plain refusal --------------------------------------------
    crash_lines = format_solve_refusal_lines(crash)
    crash_text = " ".join(crash_lines)
    ok(
        crash_lines and "PENETRATES" in crash_lines[0] and "overlap" in crash_lines[0].lower(),
        f"C1: a forced move that penetrates leads with the collision ({crash_lines[0] if crash_lines else None!r})",
    )
    ok(
        "21.53" in crash_text and "capped at the fold mirror station" in crash_text,
        "C2: the crash banner keeps the penetration depth and the cap note",
    )
    refused_lines = format_solve_refusal_lines(refused)
    refused_text = " ".join(refused_lines)
    ok(
        refused_lines
        and refused_lines[0].startswith("SOLVE REFUSED")
        and "Force FOV (show collision)" in refused_text
        and "No real-image conjugate" in refused_text,
        "C3: a plain refusal keeps its heading, its reason and the Force hint",
    )

    # ---- D: a real reason survives, none is invented -------------------------------------------
    fits_with_reason = dict(fits)
    fits_with_reason["reason"] = "No real-image conjugate for that size (near the focal point?)."
    with_reason = " ".join(format_solve_refusal_lines(fits_with_reason))
    ok(
        "No real-image conjugate" in with_reason and "overlap" not in with_reason.lower(),
        "D1: a fits banner still shows WHY the plain solve refused, without inventing an overlap",
    )
    ok(
        not any("collision to inspect" in line.lower() for line in fits_lines),
        "D2: no invented reason line when the forced move simply fit",
    )

    # ---- E: wiring pins -------------------------------------------------------------------------
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    solve_source = inspect.getsource(QuickEstimationService)
    ok(
        'info.setdefault("reason", "FORCED solve applied -- inspect the 3D overlap")' in solve_source
        and "penetrates = pen is not None and float(pen) < 0.0" in solve_source,
        "E1: the forced branch defaults the overlap reason ONLY when the body penetrates",
    )
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    banner_source = inspect.getsource(Kraken3DInspector._update_solve_refusal_banner)
    ok(
        "solve_banner_outcome" in banner_source and 'outcome == "forced_fits"' in banner_source,
        "E2: the 3D banner colours itself from the outcome (amber when it fits, red otherwise)",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0726 forced-solve banner-truth validation PASSED")
        return 0
    print("0726 forced-solve banner-truth validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
