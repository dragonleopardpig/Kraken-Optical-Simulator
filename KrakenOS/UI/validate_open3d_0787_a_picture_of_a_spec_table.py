"""bugs/0787 -- when the spec table is a picture, read the picture (but never trust it alone).

The COOLENS WWK10-110CP-111V3 datasheet carries 212 character objects on the page, 26 of them in
the top 62% where its spec tables are, and those 26 are the title. Every spec row is inside an
image, so no text extractor can reach it and the lens folder refused with "the datasheet PDF did
not yield an effective focal length".

``_extract_pdf_text_ocr`` rasterises and recognises the pages, wired as a LAST resort. What this
guard pins is the wiring and the safety, not tesseract's accuracy:

  A  OCR is a FALLBACK -- never called when the text layer already yields the answer
  B  it degrades to "" without its binaries, so the importer refuses exactly as before
  C  its output is cached (OCR is slow; a datasheet does not change)
  D  the real folder imports at 70.0315 mm, and refuses with OCR switched off

Display-free: no Tk, no VTK.  C and D are skipped when the folder or the binaries are absent.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import datasheet_prescription_import as dpi  # noqa: E402
from KrakenOS.UI.services import machine_vision_folder_import as mvi  # noqa: E402

LENS_FOLDER = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/WWK10-110CP-111V3"
LENS_PDF = LENS_FOLDER / "WWK10-110CP-111V3 Datasheet (1).pdf"
READABLE = PROJECT_ROOT / "attachment/Lens/PYRITE_56_80_10x_V38_1097785/PYRITE_56_80_10x_V38_1097785_datasheet.pdf"
EXPECTED_EFFL = (110.0 + 152.6 + 17.526) / 4.0   # = 70.0315


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    problems: list[str] = []

    def ok(condition: bool, message: str) -> None:
        notes.append(("PASS: " if condition else "FAIL: ") + message)
        if not condition:
            problems.append(message)

    # ---- A: OCR is a fallback, not a step -------------------------------------------------------
    if READABLE.exists():
        calls: list[str] = []
        saved = dpi._extract_pdf_text_ocr
        try:
            dpi._extract_pdf_text_ocr = lambda p: (calls.append(str(p)) or "")
            card = dpi.parse_datasheet_cardinals(READABLE)
        finally:
            dpi._extract_pdf_text_ocr = saved
        ok(card is not None and bool(card.effl),
           f"A: a readable datasheet still parses from its text layer (effl {getattr(card, 'effl', None)})")
        ok(not calls, "A: OCR is NOT invoked when the text layer already answers")
    else:
        notes.append("SKIP: A: the readable PYRITE datasheet is not in this checkout")

    # ---- B: no binaries -> "" -> the importer refuses exactly as before --------------------------
    saved_probe = dpi._ocr_engine_available
    try:
        dpi._ocr_engine_available = lambda: False
        ok(dpi._extract_pdf_text_ocr(LENS_PDF if LENS_PDF.exists() else READABLE) == "",
           "B: without pdftoppm/tesseract the OCR extractor returns empty, never raises")
    finally:
        dpi._ocr_engine_available = saved_probe

    # ---- C/D: the real sheet -------------------------------------------------------------------
    if not LENS_PDF.exists():
        notes.append("SKIP: C/D: the WWK10-110CP-111V3 folder is not in this checkout")
        return (not problems), notes
    if not dpi._ocr_engine_available():
        notes.append("SKIP: C/D: pdftoppm/tesseract are not installed here")
        return (not problems), notes

    saved_probe = dpi._ocr_engine_available
    try:
        dpi._ocr_engine_available = lambda: False
        without = dpi.parse_datasheet_cardinals(LENS_PDF)
    finally:
        dpi._ocr_engine_available = saved_probe
    ok(without is None or not without.effl,
       "D: with OCR switched off the rasterised sheet still refuses (the text layer has no table)")

    card = dpi.parse_datasheet_cardinals(LENS_PDF)
    if card is None or not card.effl:
        ok(False, "D: the rasterised sheet did not parse even with OCR available")
    else:
        ok(abs(float(card.effl) - EXPECTED_EFFL) < 0.01,
           f"D: OCR + corroboration -> effl {card.effl} (WD+L+flange over 4 = {EXPECTED_EFFL:.4f})")
        ok(abs(float(card.optimum_wd) - 110.0) < 0.5,
           f"D: the tolerance glyph survived the render -- WD {card.optimum_wd}, not 1102")

    cache_dir = dpi._OCR_CACHE_DIR
    ok(cache_dir.is_dir() and any(cache_dir.glob("*.txt")),
       f"C: the recognised text is cached under {cache_dir.name}/")

    if LENS_FOLDER.is_dir():
        try:
            model = mvi.import_lens_folder(LENS_FOLDER)
            ok(abs(float(model.effl) - EXPECTED_EFFL) < 0.01,
               f"D: the folder builds a surrogate (effl {model.effl}, span {model.span})")
        except Exception as exc:
            ok(False, f"D: the folder still refuses: {type(exc).__name__}: {exc}")
    return (not problems), notes


def main() -> int:
    try:
        passed, notes = run_checks()
    except Exception as exc:
        # a mechanism that is not there at all is a failure, not a traceback
        passed, notes = False, [f"FAIL: {type(exc).__name__}: {exc}"]
    for note in notes:
        print(note)
    print("bugs/0787 picture-of-a-spec-table validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
