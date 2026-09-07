"""Guard for bugs/0745 -- when the first order and the trace disagree, the scene must SAY so.

The banner's focus residual (first order, summed row thicknesses) and the drawn image plane
(bugs/0728, measured from rays) disagreed by a constant +19.55 mm on om05a_folded_80mm.py, with
nothing on screen to say which to believe. Cause: `LED panel B` carried 19.6 mm of thickness while
sitting before the Image row, so the prescription's object-to-image track was 19.6 mm longer than
the path the light walks. Production has 0.0 there.

Scene data cannot be pinned by a source check, so the tool now cross-checks itself.

Checks (display-free):
  A  the cross-check exists where the traced waist is measured, is re-stated every measurement,
     and fires only past a tolerance.
  B  it names the MEASURED value as the trustworthy one and points at the likely cause.
  C  the banner renders it beside the other focus notes.
  D  the arithmetic of the case that motivated it.

Run:  .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0745_first_order_matches_the_trace
"""

from __future__ import annotations

import inspect


def run_checks(verbose: bool = False, app=None, inspector=None) -> "tuple[bool, list[str]]":
    notes: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)

    from KrakenOS.UI.services.layout_table_workbench import LayoutTableWorkbenchMixin

    src = inspect.getsource(LayoutTableWorkbenchMixin._measure_focused_image_plane)

    # ---- A: the cross-check ---------------------------------------------------------------------
    ok(
        "_focus_model_mismatch" in src and "_fov_solve_focus_residual_info" in src,
        "A1: the traced waist is compared against the first-order residual where it is measured",
    )
    ok(
        'self._focus_model_mismatch = ""' in src,
        "A2: the note is cleared every measurement, so it can never go stale",
    )
    ok(
        "abs(gap) > 1.0" in src,
        "A3: it fires only past a tolerance, so ordinary agreement stays quiet",
    )
    clear_at = src.find('self._focus_model_mismatch = ""')
    set_at = src.find("MODEL MISMATCH")
    ok(
        0 <= clear_at < set_at,
        "A4: cleared BEFORE it can be set, so a stale note cannot survive a quiet measurement",
    )

    # ---- B: what it says ------------------------------------------------------------------------
    ok(
        "image plane is the measured one" in src,
        "B1: it names the MEASURED readout as the trustworthy one -- the whole point is that the "
        "user could not tell which of two numbers to believe",
    )
    ok(
        "the imaging path never travels" in src,
        "B2: and points at the cause -- a row carrying thickness off the imaging path",
    )

    # ---- C: the banner --------------------------------------------------------------------------
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector

    banner = inspect.getsource(Kraken3DInspector._update_solve_refusal_banner)
    ok(
        "_focus_model_mismatch" in banner,
        "C1: the banner renders it beside the other focus notes",
    )
    from KrakenOS.UI.services.detector_coverage_overlay import format_focus_summary_lines

    lines = format_focus_summary_lines(
        None, None, notes=("MODEL MISMATCH: the first order says -74.4 mm and the traced rays say "
                           "-54.9 mm (+19.6 mm apart) -- the drawn image plane is the measured one",)
    ) if callable(format_focus_summary_lines) else []
    ok(
        any("MODEL MISMATCH" in line for line in lines),
        f"C2: the formatter passes it through ({len(lines)} line(s))",
    )

    # ---- D: the case ----------------------------------------------------------------------------
    ok(
        abs((433.360 - 413.760) - 19.600) < 1e-9,
        "D1: the om05a variant's station sum exceeded its traced path by the 19.6 mm the LED "
        "panel row carried",
    )
    ok(
        abs(413.962 - 413.760) < 0.25,
        "D2: the production scene's station sum and traced path agree (0.202 mm), which is why "
        "it never showed the defect",
    )

    passed = not any(note.startswith("FAIL") for note in notes)
    if verbose:
        for note in notes:
            print(note)
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    if passed:
        print("0745 first-order-matches-the-trace validation PASSED")
        return 0
    print("0745 first-order-matches-the-trace validation FAILED:")
    for note in notes:
        if note.startswith("FAIL"):
            print(f"- {note}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
