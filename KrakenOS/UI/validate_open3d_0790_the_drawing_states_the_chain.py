"""bugs/0790 -- read the vendor DWG, and refuse for the RIGHT reason.

The SPO TCL4.0X-65DI-5M refused with "the datasheet PDF did not yield an effective focal length",
which sent the user back to a PDF that was never the problem: its title block flattens every label
away from its value (bugs/0565's failure mode) and OCR recovers the labels but not the small
isolated value cells (bugs/0788's). The DWG beside it states everything as TEXT with coordinates.

Reading it is now solved. The refusal that remains is a MODELLING one, and this guard pins both
halves: the drawing IS read (chain + corroborations), and the focal length is NOT invented from it.

Display-free. Every DWG check skips when libredwg is absent.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import dwg_spec_import as dwg  # noqa: E402
from KrakenOS.UI.services import machine_vision_folder_import as mvi  # noqa: E402

FOLDER = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/SPO TCL4.0X-65DI-5M"
DRAWING = FOLDER / "TCL4.0X-65DI-5M-V2.dwg"


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: the AutoCAD text codes, which decide whether a value is readable at all -------------
    ok(dwg._clean_dwg_text(r"{\fArial|b0|i0|c0|p34;Optical Mgnification}") == "Optical Mgnification",
       "A: inline font formatting is stripped")
    ok(dwg._clean_dwg_text("WD65 %%P2") == "WD65 ±2", "A: %%P becomes ±")
    ok(dwg._clean_dwg_text("%%C34") == "Ø34", "A: %%C becomes Ø")
    ok(dwg._clean_dwg_text(r"{\C3;C-MOUNT}") == "C-MOUNT", "A: colour formatting is stripped")

    # ---- B: the chain is IDENTIFIED, not guessed ------------------------------------------------
    # its last entry must equal a standard flange; a row that ends in anything else is not a chain
    ok(dwg._as_float("17,526") is None,
       "B: a comma-decimal (the metric view of the same dimension) is not silently misread")
    ok(dwg._as_float("142.5") == 142.5, "B: a plain dimension reads")

    if not dwg.dwg_available():
        notes.append("SKIP: C/D/E: libredwg (dwgread) is not on PATH in this checkout")
        return (not problems), notes
    if not DRAWING.exists():
        notes.append("SKIP: C/D/E: the SPO TCL4.0X-65DI-5M drawing is not in this checkout")
        return (not problems), notes

    # ---- C: the real drawing's chain --------------------------------------------------------
    chain = dwg.dwg_conjugate_chain(DRAWING)
    if not chain:
        ok(False, "C: the conjugate chain was not found in the real drawing")
    else:
        ok(abs(chain["wd"] - 65.0) < 1e-9, f"C: working distance {chain['wd']}")
        ok(abs(chain["housing"] - 142.5) < 1e-9, f"C: housing {chain['housing']}")
        ok(abs(chain["flange"] - 17.526) < 1e-9 and chain["mount"] == "C",
           f"C: the run ends at a STANDARD flange -- {chain['flange']} = {chain['mount']}-mount")
        ok(abs(chain["total"] - 225.026) < 1e-6, f"C: object-to-image track {chain['total']}")

    # ---- D: the spec table pairs label with value by geometry -----------------------------------
    text = dwg.dwg_spec_text(DRAWING)
    for want in ("Optical Mgnification 4.0X", "W.D(mm) 65", "F/# 12.5", "C-MOUNT"):
        ok(want in text, f"D: the rebuilt rows contain {want!r}")

    # ---- E: and the focal length is NOT invented from it ----------------------------------------
    card = dwg.dwg_telecentric_cardinals(DRAWING)
    ok(card is None,
       "E: no EFL is derived -- (m, WD, track) pin the TRACK, and with HH' unstated the "
       "coincident-principal-plane value would put the front principal outside the housing")
    try:
        mvi.import_lens_folder(FOLDER)
        ok(False, "E: the folder imported, so an unverified focal length reached a surrogate")
    except ValueError as exc:
        message = str(exc)
        ok("225.026" in message and "HH'" in message,
           "E: the refusal reports the chain it read and what is missing, not 'the PDF failed'")
        ok("datasheet PDF did not yield" not in message,
           "E: it no longer sends the user back to the PDF, which was never the problem")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0790 DWG-chain validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
