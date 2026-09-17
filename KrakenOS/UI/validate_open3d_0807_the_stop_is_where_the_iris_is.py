"""bugs/0807 -- the stop is where the iris is.

flag_20260917_133231 (SPO TCL4.0X-65DI-5M, object-space telecentric): "what looks weird is the rays
sudden bend outward". bugs/0792's conjugate solve fixed both ideal groups 5 mm inside the housing
ends. For a 4x lens in a 225 mm track the rear group must be negative (telephoto), and at the rear rim
all of that power became one kink 5 mm before the camera: the edge chief ray bent 5.9 deg there and
reached the sensor at 7.6 deg. The stop landed at 52.1 mm behind the front face, IN FRONT of the
54.9..66.5 mm iris ring the vendor's own drawing labels.

The drawing states the stop: a LEADER labelled IRIS whose tip falls inside a dimensioned ring of the
housing run. Pinning the telecentric stop there leaves a one-parameter family; the member taken is the
one whose front group is as large as the drawn Ø31 front barrel can hold -- the weakest rear group the
housing allows (rear group 72.05 mm behind the front face, 1.20 deg of bend, 3.31 deg at the sensor).
Magnification, working distance, NA and the image at the flange are unchanged.

A: closed-form solve (display-free, offline).  B: the DWG reader (SKIPs without libredwg).
C: the folder import (SKIPs without libredwg / the attachment).
"""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from types import SimpleNamespace

from KrakenOS.UI.services import machine_vision_folder_import as mvi  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPO = PROJECT_ROOT / "attachment" / "Information" / "RD-80000" / "Drawings" / "SPO TCL4.0X-65DI-5M"
DRAWING = SPO / "TCL4.0X-65DI-5M-V2.dwg"
M, WD, HOUSING, FLANGE, FNO = 4.0, 65.0, 142.5, 17.526, 12.5
FIELD_HALF = 11.0 / 2.0 / M          # the 2/3" image circle, at the object
IRIS, RING_END, BARREL = 60.7, 66.5, 15.5


def _delivered(solve: dict) -> "tuple[float, float]":
    sol = solve["solution"]
    a = WD + sol.g1
    v1 = a * sol.f1 / (a - sol.f1)
    s2 = v1 - sol.d
    b = 1.0 / (1.0 / sol.f2 + 1.0 / s2)
    return (-v1 / a) * (b / s2), b - sol.g2


def _solve(barrel=BARREL, stop=IRIS):
    return mvi.solve_conjugate_two_groups_at_stop(
        M, WD, HOUSING, FLANGE, stop, working_fno=FNO, object_field_half=FIELD_HALF,
        front_barrel_radius=barrel, rear_group_after=RING_END)


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the solve --------------------------------------------------------------------------
    rim = mvi.solve_conjugate_two_groups(M, WD, HOUSING, FLANGE)
    rim_profile = mvi.conjugate_beam_profile(rim, M, FNO, FIELD_HALF)
    ok(rim["solution"].g1 + rim["solution"].f1 < 54.9,
       f"A0: the rim placement's stop ({rim['solution'].g1 + rim['solution'].f1:.2f} mm) sits in FRONT "
       "of the drawn iris ring -- the flagged state")
    pinned = _solve()
    sol = pinned["solution"]
    m, image_gap = _delivered(pinned)
    ok(abs(abs(m) - M) < 1e-4 and abs(image_gap - FLANGE) < 1e-3,
       f"A1: the contract is unchanged: |m| {abs(m):.5f}, image {image_gap:.4f} mm behind the rear datum")
    ok(abs(sol.g1 + sol.f1 - IRIS) < 1e-3,
       f"A2: the telecentric stop (group 1's back focal plane) is AT the iris ({sol.g1 + sol.f1:.4f} mm)")
    ok(0.0 < sol.g1 < IRIS and HOUSING - sol.g2 >= RING_END - 1e-9 and sol.g2 >= 5.0 - 1e-9,
       f"A3: group 1 in front of the iris ({sol.g1:.2f}), group 2 behind its ring and inside the rear "
       f"({HOUSING - sol.g2:.2f} mm)")
    ok(sol.f1 > 0.0 > sol.f2, f"A4: still a telephoto pair (f1 {sol.f1:.3f}, f2 {sol.f2:.3f})")
    ok(pinned["placement"] == "barrel-limited" and abs(pinned["front_beam_radius"] - BARREL) < 1e-3,
       f"A5: group 1 is as large as the barrel holds ({pinned['front_beam_radius']:.4f} of {BARREL})")
    ok(pinned["chief_bend_deg"] < 0.5 * rim_profile["chief_bend_deg"]
       and pinned["chief_angle_at_image_deg"] < 0.5 * rim_profile["chief_angle_at_image_deg"],
       f"A6: the rear kink {rim_profile['chief_bend_deg']:.2f} -> {pinned['chief_bend_deg']:.2f} deg and the "
       f"sensor angle {rim_profile['chief_angle_at_image_deg']:.2f} -> "
       f"{pinned['chief_angle_at_image_deg']:.2f} deg")
    stop_d = mvi.conjugate_stop_diameter(pinned, M, FNO)
    ok(abs(stop_d - 2.0 * sol.f1 * M / (2.0 * FNO)) < 1e-6,
       f"A7: the stop passes NA {M / (2 * FNO):.2f} at its new focal length (Ø{stop_d:.4f})")
    wide = _solve(barrel=16.5)
    narrow = _solve(barrel=13.0)
    ok(wide["placement"] == "rear-group-at-the-iris" and abs(HOUSING - wide["solution"].g2 - RING_END) < 1e-6,
       f"A8: a wider barrel stops at the iris ring ({wide['placement']}, {HOUSING - wide['solution'].g2:.2f})")
    ok(narrow["placement"] == "front-beam-exceeds-barrel",
       f"A9: a barrel too narrow for any member is SAID, not hidden ({narrow['placement']})")
    try:
        _solve(stop=10.0)
        ok(False, "A10: a stop no two groups can reach was accepted")
    except ValueError:
        ok(True, "A10: a stop no two groups can reach is refused (the importer keeps the rim placement)")

    # ---- A11: without a drawn stop nothing changes ------------------------------------------------
    from KrakenOS.UI.services.datasheet_prescription_import import DatasheetCardinals

    card = DatasheetCardinals(effl=10.0)
    card.telecentric = True
    card.conjugate_constrained = True
    card.magnification, card.optimum_wd, card.mount_flange_mm = -M, WD, FLANGE
    card.span, card.fno, card.image_circle = HOUSING, FNO, 11.0
    assets = SimpleNamespace(primary_step=None, primary_pdf=None, folder=str(SPO), dwg_files=[])
    core = mvi._core_from_datasheet_cardinals(card, assets)
    ok(abs(core.solution.g1 - 5.0) < 1e-9 and abs(core.solution.g2 - 5.0) < 1e-9
       and core.group1_aperture is None,
       f"A11: no drawn stop -> the bugs/0792 rim placement, untouched (g1 {core.solution.g1}, g2 {core.solution.g2})")
    card.stop_from_front_mm, card.stop_ring_mm, card.front_barrel_radius_mm = IRIS, (54.9, RING_END), BARREL
    core = mvi._core_from_datasheet_cardinals(card, assets)
    ok(abs(core.solution.g1 + core.solution.f1 - IRIS) < 1e-3
       and any("bugs/0807" in note for note in core.extra_notes),
       "A12: a drawn stop is honoured by the builder and the surrogate says so")
    cone_at_front = 2.0 * (WD * M / (2.0 * FNO) + FIELD_HALF)
    ok(core.front_aperture >= cone_at_front and core.group1_aperture >= 2.0 * BARREL - 1e-6
       and core.group2_aperture >= 2.0 * pinned["rear_beam_radius"],
       f"A13: every disc passes its beam: front datum {core.front_aperture} >= {cone_at_front:.3f}, "
       f"group 1 {core.group1_aperture}, group 2 {core.group2_aperture}")

    # ---- B: the drawing ----------------------------------------------------------------------------
    from KrakenOS.UI.services import dwg_spec_import as dwg

    if not dwg.dwg_available():
        notes.append("SKIP: B/C: libredwg (dwgread) is not on PATH -- run inside `devenv shell`")
        return (not problems), notes
    if not DRAWING.exists():
        notes.append("SKIP: B/C: the SPO TCL4.0X-65DI-5M drawing is not in this checkout")
        return (not problems), notes
    iris = dwg.dwg_iris_stop(DRAWING)
    ok(iris is not None and iris["label"] == "IRIS" and iris["ring_mm"] is not None
       and abs(iris["ring_mm"][0] - 54.9) < 1e-3 and abs(iris["ring_mm"][1] - 66.5) < 1e-3
       and abs(iris["stop_mm"] - IRIS) < 1e-3 and 54.9 < iris["tip_mm"] < 66.5,
       f"B1: the IRIS leader's tip lands in the 11.6 mm ring; the stop is its middle ({iris})")
    ok(abs((dwg.dwg_barrel_radius(DRAWING, before_mm=IRIS) or 0.0) - BARREL) < 1e-3,
       "B2: the barrel in front of the iris is the Ø31 section (the Ø16 illumination port is not coaxial)")
    card = dwg.dwg_telecentric_cardinals(DRAWING)
    ok(card is not None and abs((card.stop_from_front_mm or 0.0) - IRIS) < 1e-3
       and abs((card.front_barrel_radius_mm or 0.0) - BARREL) < 1e-3,
       "B3: the cardinals carry the stop and the barrel")

    # ---- C: the import ------------------------------------------------------------------------------
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        model = mvi.import_lens_folder(SPO)
    rows = {row["name"]: row for row in model.surfaces}
    stop_z = sum(float(r["thickness"]) for r in model.surfaces[1:3])
    ok(abs(stop_z - IRIS) < 1e-3,
       f"C1: the imported stop row sits {stop_z:.4f} mm behind the front datum (the iris)")
    ok(abs(float(model.aperture_value) - stop_d) < 1e-3 and str(model.aperture_type).upper() == "STOP",
       f"C2: the declared STOP is the pinned stop (Ø{model.aperture_value})")
    ok(float(rows["Blackbox Group 2"]["rc"]) < 0.0 and abs(float(rows["Rear Optical Vertex Datum"]["thickness"]) - FLANGE) < 1e-6,
       "C3: rear group negative, image at the C-mount flange")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0807 stop-is-where-the-iris-is validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
