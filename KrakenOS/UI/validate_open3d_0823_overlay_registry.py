"""Guard for bugs/0823 -- the app names the overlay family, the user does not guess.

Three Open 3D overlay families draw at the object plane and two of them use the SAME
green literal (0.2, 0.9, 0.35) scaled to the same field semi-diagonal. Telling them
apart has required reading a note that lists opacities, and bugs/0659 round 1 read it
wrong and blamed the reference-surface family for a disc it does not draw.

The registry makes the signature -> family mapping data the app can answer from, and
`verify_registry_against_source` re-reads the real literals so a drifted colour fails
HERE rather than turning this file into the next stale note.

The reference-surface family is the interesting case: its disc opacity comes from the
scene bundle's mesh opacity, not a literal. It therefore must never be excluded by an
opacity argument -- excluding it is exactly the 0659 mistake, performed automatically.

Checks (display-free, pure -- the registry is data and three lookup functions):
  A  the clash is reported: both green families are named, with what separates them;
  B  opacity discriminates the two green families, and the tolerance cannot span the
     0.02 gap between them;
  C  the colourless family is never ruled out by colour or opacity -- the 0659 trap;
  D  shape rules out the rectangle-drawer, which opacity alone nearly cannot;
  E  every family names a toggle var and at least one UI path to reach it;
  F  declared literals still exist in their source modules (drift check);
  G  the bugs/0660 lifecycle fact is recorded for the family it was proved on;
  H  lookups degrade sanely: no criteria returns everything, absurd input returns none.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0823_overlay_registry
"""

from __future__ import annotations

_GREEN = (0.2, 0.9, 0.35)


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.overlay_registry import (
        OPACITY_MATCH_TOLERANCE,
        OVERLAY_FAMILIES,
        describe_family,
        families_sharing_color,
        identify_overlay,
        overlay_clash_report,
        verify_registry_against_source,
    )

    # ---- A: the clash is reported at all -------------------------------------------------------
    report = "\n".join(overlay_clash_report())
    sharing = families_sharing_color(_GREEN)
    ok(len(sharing) == 2,
       f"A1: exactly two families declare the shared green (got {len(sharing)})")
    ok("Quick Estimation FOV" in report and "Detector coverage FOV" in report,
       "A2: the clash report names BOTH green families")
    ok("quick_estimation_var" in report and "show_detector_overlays_var" in report,
       "A3: and names the toggle var for each, so the report is actionable")

    # ---- B: opacity discriminates the two green families ---------------------------------------
    qe = identify_overlay(color=_GREEN, opacity=0.10)
    det = identify_overlay(color=_GREEN, opacity=0.08)
    ok([f.name for f in qe] == ["quick_estimation", "reference_surfaces"],
       f"B1: green at 0.10 is Quick Estimation (plus the colourless family) "
       f"(got {[f.name for f in qe]})")
    ok([f.name for f in det] == ["detector_coverage", "reference_surfaces"],
       f"B2: green at 0.08 is Detector coverage (plus the colourless family) "
       f"(got {[f.name for f in det]})")
    ok(OPACITY_MATCH_TOLERANCE < 0.01,
       f"B3: the opacity window cannot span the 0.02 gap between 0.08 and 0.10 "
       f"(got {OPACITY_MATCH_TOLERANCE})")

    # ---- C: the colourless family is never wrongly excluded -- the 0659 trap --------------------
    refs = next(f for f in OVERLAY_FAMILIES if f.name == "reference_surfaces")
    ok(refs.color is None and refs.opacities == (),
       "C1: the reference-surface family declares NO colour or opacity literal")
    ok(all("reference_surfaces" in [f.name for f in identify_overlay(color=_GREEN, opacity=o)]
           for o in (0.08, 0.10, 0.5, 1.0)),
       "C2: it survives every opacity query -- it has no literal to contradict")
    ok("never be ruled out" in "\n".join(overlay_clash_report()),
       "C3: and the report says so in words, rather than leaving it implied")
    ok("0659" in refs.notes,
       "C4: the note records that 0659 blamed this family for a disc it does not draw")

    # ---- D: shape separates what opacity nearly cannot ------------------------------------------
    by_disc = identify_overlay(color=_GREEN, shape="disc")
    by_rect = identify_overlay(color=_GREEN, shape="rectangle")
    # The reference-surface family draws a PLANE DISC too, so "disc" cannot narrow to
    # one family -- what it does is exclude Detector coverage, which draws a rectangle.
    ok([f.name for f in by_disc] == ["quick_estimation", "reference_surfaces"],
       f"D1: a green DISC excludes Detector coverage, leaving the two disc-drawers "
       f"(got {[f.name for f in by_disc]})")
    ok("detector_coverage" not in [f.name for f in by_disc],
       "D1b: and Detector coverage specifically is ruled out by shape")
    ok([f.name for f in by_rect] == ["detector_coverage"],
       f"D2: a green RECTANGLE is Detector coverage alone (got {[f.name for f in by_rect]})")

    # ---- E: every family is reachable in the UI --------------------------------------------------
    for fam in OVERLAY_FAMILIES:
        ok(bool(fam.toggle_var) and bool(fam.toggle_paths),
           f"E: {fam.name} names a toggle var and at least one UI path to it")
        text = describe_family(fam.name)
        ok(fam.toggle_var in text and fam.owner_module in text,
           f"E: describe_family({fam.name}) carries the toggle and the drawing module")

    # ---- F: the registry cannot silently rot ------------------------------------------------------
    problems = verify_registry_against_source()
    ok(problems == [],
       f"F1: every declared literal still appears in its source module (got {problems})")
    declared = sum(len(f.source_literals) for f in OVERLAY_FAMILIES)
    ok(declared >= 2,
       f"F2: at least the two clashing opacities are drift-checked (got {declared})")

    # ---- G: the 0660 lifecycle law is recorded ----------------------------------------------------
    qe_fam = next(f for f in OVERLAY_FAMILIES if f.name == "quick_estimation")
    ok(qe_fam.owns_actors is True and "0660" in qe_fam.notes,
       "G1: the family bugs/0660 proved the owns-its-actors law on records it")
    ok("owns and clears its own actors" in describe_family("quick_estimation"),
       "G2: and the description states the lifecycle, not just the flag")

    # ---- H: lookups degrade sanely ----------------------------------------------------------------
    ok(len(identify_overlay()) == len(OVERLAY_FAMILIES),
       "H1: no criteria returns every family rather than an empty guess")
    ok(identify_overlay(color=(1.0, 0.0, 1.0), shape="octagon") == (),
       "H2: a signature nothing draws returns nothing")
    ok(len(families_sharing_color((0.0, 0.0, 0.0))) == 0,
       "H3: a colour no family declares has an empty clash set")
    try:
        describe_family("no_such_family")
        raised = False
    except KeyError:
        raised = True
    ok(raised, "H4: an unknown family name raises rather than returning empty text")

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0823 overlay-registry validation PASSED")
        return 0
    print("0823 overlay-registry validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
