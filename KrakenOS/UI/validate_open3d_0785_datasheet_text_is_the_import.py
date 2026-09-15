"""bugs/0785 -- a datasheet the app cannot read is a vendor it cannot import.

``attachment/error.png``: "Could not extract a sensor size from this folder" on the Hikrobot
MV-CH120-60UM, whose datasheet states the sensor plainly. The shared ``extract_pdf_text`` (used
by BOTH the camera folder importer and the machine-vision lens importer) had three independent
defects, none of them brand-specific:

  A  the raw-literal fallback harvested PDF plumbing -- one ``/Lang (en-US)`` marked-content
     property per text run, glued between every label and its value
  B  a show-string whose font carried no ToUnicode was DROPPED, so a sheet mixing fonts inside
     one spec row lost half of every row; and the printability test must count Latin-1
     160..255 or the row's own separator (U+00D7) goes with it
  C  the stdlib decoder understands a slice of PDF, not the format -- a real parser reads
     sheets it cannot, and vice versa, so the two must COMPETE (stdlib wins ties, which is what
     keeps every existing scrape byte-identical)

Display-free: no Tk, no VTK, no rendering. Synthetic streams pin each mechanism; the real vendor
folders pin the outcome and are skipped when absent.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

from KrakenOS.UI.services import camera_folder_import as cfi  # noqa: E402
from KrakenOS.UI.services import datasheet_prescription_import as dpi  # noqa: E402

FLAGGED = PROJECT_ROOT / "attachment/Information/RD-80000/Drawings/MV-CH120-60UM"
BOPIXEL_PDF = (PROJECT_ROOT / "attachment/Cameras/BC-GM25M12X4"
               / "BC-Gx25M12X4_Spec_EN_ver02_bopixel.pdf")
ELS_PDF = PROJECT_ROOT / "attachment/Lens/ELS-85-4.5V16K/ELS-85 4.5V16K_specification.pdf"


def _check_a() -> list[str]:
    """The harvest takes page text, and ONLY page text."""
    bad: list[str] = []
    stream = (
        b"q /P <</MCID 2/Lang (en-US)>> BDC\r\n"
        b"BT /F1 10 Tf [(Pixel size)-300(3.45 um)] TJ ET\r\n"
        b"EMC /P <</MCID 3/Lang (en-US)>> BDC\r\n"
        b"BT /F1 10 Tf [(Resolution)] TJ ET EMC Q\r\n"
    )
    text = dpi._harvest_literal_text({1: stream})
    if "en-US" in text:
        bad.append("marked-content plumbing still harvested as page text")
    for want in ("Pixel size", "3.45 um", "Resolution"):
        if want not in text:
            bad.append(f"page text lost: {want!r}")
    # STRUCTURAL, not a blacklist: a different language tag must be excluded the same way, so a
    # fix that merely strips the literal string "en-US" cannot pass this.
    other = dpi._harvest_literal_text(
        {1: b"/P <</Lang (de-DE)>> BDC BT /F1 10 Tf [(Sensor size)] TJ ET EMC"}
    )
    if "de-DE" in other:
        bad.append("excluded only the en-US spelling, not the position (blacklist, not structure)")
    if "Sensor size" not in other:
        bad.append("structural rule dropped real page text")
    return bad


def _check_b() -> list[str]:
    """A no-ToUnicode show-string falls back IN ORDER; a mapped one still decodes."""
    bad: list[str] = []
    if dpi._show_text(b"Pixel size", {}) != "Pixel size":
        bad.append("empty CMap dropped a readable literal instead of falling back")
    cmap = {0x4162: "A"}
    if dpi._show_text(b"Ab", cmap) != "A":
        bad.append("a font WITH a usable CMap stopped decoding through it")
    if dpi._show_text(b"Pixel size", cmap) != "Pixel size":
        bad.append("a CMap that maps nothing in this string blocked the literal fallback")
    # the separator that decides a spec row lives at Latin-1 0xD7
    if not dpi._printable_ratio("4096 × 3000") > 0.8:
        bad.append("printability test rejects the row separator U+00D7 (x)")
    if not dpi._printable_ratio("3.45 µm") > 0.8:
        bad.append("printability test rejects the micro sign U+00B5")
    if dpi._printable_ratio("\x00\x01\x02\x03\x04") > 0.8:
        bad.append("printability test accepts raw CID bytes as text")
    return bad


def _check_c() -> list[str]:
    """(cid:N) is not text, and the two extractors compete with stdlib winning ties."""
    bad: list[str] = []
    placeholders = "(cid:1239)(cid:2801)(cid:6320)"
    if dpi._useful_letter_count(placeholders) != 0:
        bad.append("pdfminer (cid:N) placeholders counted as real letters")
    if dpi._ascii_letter_count(placeholders) == 0:
        bad.append("test is vacuous: the placeholders carry no ASCII letters to discount")
    saved = (dpi._extract_pdf_text_pdfplumber, dpi._extract_pdf_text_stdlib)
    try:
        dpi._extract_pdf_text_pdfplumber = lambda _p: "parser text here"
        dpi._extract_pdf_text_stdlib = lambda _p: "stdlib text here"
        if dpi.extract_pdf_text("ignored") != "stdlib text here":
            bad.append("stdlib does not win a tie -- existing scrapes are not pinned")
        dpi._extract_pdf_text_pdfplumber = lambda _p: "parser text here and plenty more besides"
        if dpi.extract_pdf_text("ignored") != "parser text here and plenty more besides":
            bad.append("the parser cannot win even when it reads strictly more")
        dpi._extract_pdf_text_pdfplumber = lambda _p: "(cid:11)(cid:22)(cid:33)(cid:44)(cid:55)"
        dpi._extract_pdf_text_stdlib = lambda _p: "real"
        if dpi.extract_pdf_text("ignored") != "real":
            bad.append("a page of (cid:N) placeholders beat real text")
    finally:
        dpi._extract_pdf_text_pdfplumber, dpi._extract_pdf_text_stdlib = saved
    return bad


def _check_real() -> tuple[list[str], list[str]]:
    """The outcome on the real vendor folders (skipped when a folder is absent)."""
    bad: list[str] = []
    notes: list[str] = []
    if FLAGGED.is_dir():
        try:
            imp = cfi.import_camera_folder(FLAGGED, persist=False)
            rec = imp.record
            w, h = float(rec["sensor_width_mm"]), float(rec["sensor_height_mm"])
            if abs(w - 4096 * 3.45 / 1000.0) > 1e-6 or abs(h - 3000 * 3.45 / 1000.0) > 1e-6:
                bad.append(f"flagged folder sensor {w:.4f} x {h:.4f}, expected 14.1312 x 10.3500")
            mount = str(rec.get("lens_mount") or "")
            if "Dimension" in mount or len(mount) > 12:
                bad.append(f"mount captured past its value: {mount!r}")
            if not rec.get("step_path"):
                bad.append("flagged folder imported without its STEP body")
            notes.append(f"PASS: real: {FLAGGED.name} -> {w:.4f} x {h:.4f} mm, mount {mount!r}")
        except Exception as exc:
            bad.append(f"flagged folder still refuses: {type(exc).__name__}: {exc}")
    else:
        notes.append(f"SKIP: real: {FLAGGED.name} is not in this checkout")
    if BOPIXEL_PDF.exists():
        # The FOLDER already imported before this fix -- but only because someone hand-wrote
        # BC-GM25M12X4_camera.json, the very workaround the error dialog suggests. Pin the
        # DATASHEET itself, which is what makes that sidecar unnecessary; testing the folder
        # here would pass on the sidecar alone and guard nothing.
        try:
            spec = cfi.parse_camera_datasheet(BOPIXEL_PDF)
            if spec is None or not spec.has_sensor_size:
                bad.append("the Bopixel spec sheet still yields no sensor size of its own")
            elif abs(float(spec.sensor_width_mm) - 12.8) > 1e-6:
                bad.append(f"Bopixel datasheet sensor {spec.sensor_width_mm}, expected 12.8")
            else:
                notes.append(
                    "PASS: real: the Bopixel spec sheet parses on its own (12.8 mm) -- "
                    "no hand-written sidecar needed"
                )
        except Exception as exc:
            bad.append(f"Bopixel datasheet refuses: {type(exc).__name__}: {exc}")
    else:
        notes.append("SKIP: real: the Bopixel datasheet is not in this checkout")
    if ELS_PDF.exists():
        # bugs/0565's designation path reads the STDLIB decode; the competition must hand this
        # sheet back to it rather than to a page of (cid:N).
        focal, fno = dpi.model_designation_cardinals(dpi.extract_pdf_text(ELS_PDF))
        if focal != 85.0 or fno != 4.5:
            bad.append(f"ELS-85 designation path broke: {focal}, {fno} (expected 85.0, 4.5)")
        else:
            notes.append("PASS: real: the ELS-85 designation path still reads 85 mm f/4.5")
    else:
        notes.append("SKIP: real: the ELS-85 folder is not in this checkout")
    return bad, notes


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    """Penta entry point: ``(passed, notes)`` with one PASS:/FAIL: line per check."""
    problems: list[str] = []
    notes: list[str] = []
    for label, check in (
        ("A: the harvest takes page text, and only page text", _check_a),
        ("B: a no-ToUnicode show-string falls back in order, separators survive", _check_b),
        ("C: (cid:N) is not text; the two extractors compete, stdlib wins ties", _check_c),
    ):
        try:
            bad = check()
        except Exception as exc:
            bad = [f"{type(exc).__name__}: {exc}"]
        problems.extend(bad)
        notes.append(("FAIL: " if bad else "PASS: ") + label + (f": {bad}" if bad else ""))
    try:
        bad, real_notes = _check_real()
    except Exception as exc:
        bad, real_notes = [f"{type(exc).__name__}: {exc}"], []
    notes.extend(real_notes)
    problems.extend(bad)
    notes.extend(f"FAIL: real: {item}" for item in bad)
    return (not problems), notes


def main() -> int:
    passed, notes = run_checks()
    for note in notes:
        print(note)
    print("bugs/0785 datasheet-text validation " + ("PASSED." if passed else "FAILED."))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
