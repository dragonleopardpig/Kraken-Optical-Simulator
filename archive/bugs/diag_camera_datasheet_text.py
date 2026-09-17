"""Dump the raw text `extract_pdf_text` recovers from vendor camera datasheets,
so the camera folder-importer's spec parser can be written against the REAL
extracted token stream (not the visual PDF layout, which reorders text).

Run: .devenv/state/venv/bin/python bugs/diag_camera_datasheet_text.py
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.services.datasheet_prescription_import import extract_pdf_text

CAMERAS = Path("attachment/Cameras")
SHEETS = [
    "hr25MCX_Datasheet.pdf",
    "BC-Gx25M12X4_Spec_EN_ver02_bopixel.pdf",
]


def main() -> int:
    for name in SHEETS:
        path = CAMERAS / name
        print("=" * 78)
        print(name, "exists=" + str(path.exists()))
        print("=" * 78)
        if not path.exists():
            continue
        text = extract_pdf_text(path)
        print(f"[{len(text)} chars]")
        print(text)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
