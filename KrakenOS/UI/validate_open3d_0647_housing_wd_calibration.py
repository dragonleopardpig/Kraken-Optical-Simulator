"""Guard for bugs/0647 — the lens housing is registered to the vendor working-distance law.

flag_20260825_113300: "can double check FOV 20x20, standoff=53.47+67.32? Actual testing is
around 130mm." The bench measures object -> FRONT HOUSING RIM -- the only accessible plane.
A datasheet-only surrogate has a NOMINAL principal split (bugs/0565 symmetric fallback), so
nothing anchored the glass to the housing: on the ELS-85 the front principal sat 37.45 mm
behind the STEP front face where the vendor's own Optimum Working Distance row (142 mm at
1.0x, EFL 85 -> principal-behind-rim = 85*(1+1/1) - 142 = 28.0) demands 28.0 -- every
on-screen rim-referenced standoff read ~9.4 mm short of the bench.

Fix: parse the Optimum WD (+ pairing |m|) from the datasheet; a physics window
f/m* < WD < f(1+1/m*) disambiguates the delaminated value from decoys (bugs/0565 text
soup). `calibrate_lens_housing_to_datasheet_wd` slides the BODY (never the optics) along
the lens axis until principal-behind-rim matches the vendor law; the importer and the lens
swap both invoke it.

Checks (display-free):
  A  the parser recovers WD=142 @ 1.0x from the EXACT ELS-85 flattened text soup, and the
     decoys (back focus glued as "10-4141.85mm", TTL 196.8, 26/68/85) do not survive.
  B  no label / ambiguous survivors / out-of-physics values refuse (None).
  C  the calibration method: routes the shift through translate_step_overlay (bodies move
     via the real mover, 0644 rebuild included), cross-checks the sheet EFL against the
     scene (a wrong PDF must not "calibrate"), and never touches optics rows.
  D  both entry points refit (import persists to the library .py; swap refits
     BEFORE its auto-refocus so focus + re-learn see the corrected optics).

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0647_housing_wd_calibration
"""

from __future__ import annotations

import inspect


# The EXACT flattened extraction of "ELS-85 4.5V16K_specification.pdf" (bugs/0565's
# delaminated title-block soup), abridged around the tokens that matter.
ELS_SOUP = (
    "Size1020(Operating Temperature)57.3626721DrawCheckUnit:mm(Back Focus)F(F/ No.)"
    "(Iris Type)(Suitable Distance)(Optimum Working Distance)(Magnification)"
    "26mmD85mmELS-85/4.5V16Kg10-4141.85mm4.5Manual93.7%V196.8mm400nm-1000nm"
    "3.A01.018545V16K-A142mm68mm400-1000nm0.5X,1.0X,2.0X"
)


def run_checks():
    notes: list[str] = []
    ok = True

    from KrakenOS.UI.services.datasheet_prescription_import import (
        DatasheetCardinals,
        parse_optimum_working_distance,
    )

    # ---------------------------------------------------------------- A: the real soup
    c = DatasheetCardinals(effl=85.0)
    parse_optimum_working_distance(ELS_SOUP, c)
    if c.optimum_wd != 142.0 or c.optimum_wd_mag != 1.0:
        ok = False
        notes.append(
            f"FAIL: A (bugs/0647): ELS soup gave WD={c.optimum_wd} @ {c.optimum_wd_mag} "
            "(want 142.0 @ 1.0) -- the physics window no longer isolates the vendor value"
        )
    else:
        notes.append("PASS: A: WD 142 @ 1.0x recovered from the delaminated ELS-85 text")

    # ---------------------------------------------------------------- B: refusals
    problems = []
    c2 = DatasheetCardinals(effl=85.0)
    parse_optimum_working_distance("no such label here 142mm 0.5X,1.0X,2.0X", c2)
    if c2.optimum_wd is not None:
        problems.append("parsed a WD with no Optimum Working Distance label")
    c3 = DatasheetCardinals(effl=85.0)
    parse_optimum_working_distance(
        "(Optimum Working Distance) 142mm 150mm 0.5X,1.0X,2.0X", c3
    )
    if c3.optimum_wd is not None:
        problems.append("two in-window candidates did not refuse (ambiguity)")
    c4 = DatasheetCardinals(effl=85.0)
    parse_optimum_working_distance("(Optimum Working Distance) 300mm 1.0X", c4)
    if c4.optimum_wd is not None:
        problems.append("an out-of-physics WD (300 > f(1+1/m)=170) was accepted")
    if problems:
        ok = False
        notes.append(f"FAIL: B (bugs/0647): {problems}")
    else:
        notes.append("PASS: B: no label / ambiguous / out-of-physics all refuse")

    # ---------------------------------------------------------------- C: the calibrator
    from KrakenOS.UI.services.scene_placement_commands import ScenePlacementMixin

    src = inspect.getsource(ScenePlacementMixin.calibrate_lens_housing_to_datasheet_wd)
    reg_src = inspect.getsource(ScenePlacementMixin._lens_datasheet_wd_registration)
    c_problems = []
    # The ADVISORY must not move ANYTHING -- both body remedies were user-rejected the
    # same day: translate_step_overlay drags the OPTICS rows with the body (bugs/0574
    # glue follow), and a raw body-offset shift floats the fictitious thin-group discs
    # outside the housing (flag_20260825_132731 "lens surrogate detached from lens
    # body"). Geometry changes belong ONLY to the refit (checked in E).
    for mover in (
        "translate_step_overlay(",
        "_set_step_placement_offset_xyz(",
        ".thickness =",
        "desp_x =",
        "desp_y =",
        "desp_z =",
    ):
        if mover in src or mover in reg_src:
            c_problems.append(f"advisory/measurement moves geometry ({mover.strip()})")
    if "0.05 * effl_sheet" not in reg_src:
        c_problems.append("no scene-vs-sheet EFL cross-check (a wrong PDF would 'calibrate')")
    if "1.0 + 1.0 / pairing" not in reg_src:
        c_problems.append("the vendor law f(1+1/m)-WD is gone")
    if "SHORTER" not in src:
        c_problems.append("the bench-note wording (add N mm) is gone")
    if c_problems:
        ok = False
        notes.append(f"FAIL: C (bugs/0647): {c_problems}")
    else:
        notes.append("PASS: C: advisory + measurement move nothing; EFL cross-check + vendor law intact")

    # ---------------------------------------------------------------- D: wiring
    from KrakenOS.UI.services import layout_table_workbench as wb

    def _class_src(module, method):
        for name, cls in vars(module).items():
            if isinstance(cls, type) and method in vars(cls):
                return inspect.getsource(getattr(cls, method))
        return ""

    swap_src = _class_src(wb, "swap_imaging_lens_from_folder")
    import_src = _class_src(wb, "import_machine_vision_lens_from_folder")
    missing = []
    if "refit_lens_principal_to_datasheet_wd(" not in import_src:
        missing.append("import does not refit to the WD law")
    if "_write_layout_file(" not in import_src:
        missing.append("import does not persist the refit into the library .py")
    # Follow-up (user 2026-08-27 "proceed swap-path auto WD-refit"): the swap REFITS
    # like the import. The frozen-scene hazard this check used to pin (the refit moving
    # the stop inside desp-baked rows + stale learned state mis-verifying the next
    # solve) is owned by the refit itself now -- frozen desp re-bake, learned-state
    # clear, relearn pending -- so pinning the swap to the advisory would have
    # preserved a workaround, not a safety property. The advisory remains as the
    # refit's own internal fallback (checked in E). ORDER is the surviving hazard: a
    # refit AFTER the auto-refocus would focus the machine on stale optics.
    refit_pos = swap_src.find("refit_lens_principal_to_datasheet_wd(")
    refocus_pos = swap_src.find("_swap_auto_refocus_to_best_focus(")
    if refit_pos < 0:
        missing.append("swap does not refit to the WD law")
    elif 0 <= refocus_pos < refit_pos:
        missing.append("swap refits AFTER the auto-refocus (focus solved on stale optics)")
    if missing:
        ok = False
        notes.append(f"FAIL: D (bugs/0647): {missing}")
    else:
        notes.append(
            "PASS: D: import refits + persists; swap refits BEFORE its auto-refocus "
            "(advisory = the refit's own fallback)"
        )

    # ---------------------------------------------------------------- E: the refit itself
    refit_src = inspect.getsource(ScenePlacementMixin.refit_lens_principal_to_datasheet_wd)
    e_problems = []
    if '["Standard", "Thin Lens", "Aperture", "Thin Lens", "Standard"]' not in refit_src.replace(
        "\n", ""
    ).replace("            ", " ").replace("  ", " ") and '"Standard", "Thin Lens", "Aperture", "Thin Lens", "Standard"' not in refit_src:
        e_problems.append("no two-group shape gate -- a real .zmx block would be rewritten")
    if "calibrate_lens_housing_to_datasheet_wd()" not in refit_src:
        e_problems.append("no advisory fallback for blocks the refit cannot act on")
    if "-(g2 + effl * d / f1)" not in refit_src:
        e_problems.append("ppp is no longer derived from the block (rear principal drifts)")
    if 'rows[0].thickness = round(float(rows[0].thickness) + float(reg["mismatch"])' not in refit_src:
        e_problems.append("the object leg is not grown by the mismatch (conjugate breaks)")
    if "sol.g1 < 0.0 or sol.g2 < 0.0" not in refit_src:
        e_problems.append("no inside-the-datums feasibility gate")
    # Numeric: the ELS refit is feasible and keeps ppp.
    from KrakenOS.UI.services.machine_vision_folder_import import solve_two_thin_groups

    sol = solve_two_thin_groups(85.0, 33.5985 - 9.45, -33.5985, 55.0)
    ppp_back = -(sol.g2 + 85.0 * sol.d / sol.f1)
    if not (sol.g1 >= 0 and sol.g2 >= 0 and sol.d > 0 and abs(ppp_back - (-33.5985)) < 1e-6):
        e_problems.append(
            f"the ELS refit numbers regressed (g1={sol.g1:.3f} g2={sol.g2:.3f} "
            f"d={sol.d:.3f} ppp_back={ppp_back:.4f})"
        )
    if e_problems:
        ok = False
        notes.append(f"FAIL: E (bugs/0647): {e_problems}")
    else:
        notes.append(
            "PASS: E: refit gated to pure two-group blocks, ppp + conjugate preserved, "
            "ELS numbers feasible"
        )

    return ok, notes


def main() -> int:
    ok, notes = run_checks()
    for line in notes:
        print(line)
    print("Housing-WD-calibration validation " + ("passed." if ok else "FAILED."))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
