"""Validate the multi-element lens drawing PDF case-study artifacts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from KrakenOS.Examples.Examp_Lens_Drawing_PDF_Export import (
    build_rows,
    export_pdf,
    export_properties_json,
)
from KrakenOS.UI.lens_drawing_export import identify_elements
from KrakenOS.UI.lens_drawing_properties import apply_surface_properties_payload


def main() -> int:
    rows = build_rows()
    groups, _info = identify_elements(rows)
    if len(groups) != 1:
        raise AssertionError(f"Expected one cemented lens group, got {len(groups)}.")
    if not groups[0].is_cemented or len(groups[0].elements) != 3:
        raise AssertionError("Expected one cemented three-element triplet group.")

    with tempfile.TemporaryDirectory(prefix="kraken-lens-drawing-case-") as tmp_dir:
        tmp = Path(tmp_dir)
        json_path = export_properties_json(rows, tmp / "triplet_surface_properties.json")
        pdf_path = export_pdf(rows, tmp / "multi_element_lens_fabrication_drawing.pdf")
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        cloned = build_rows()
        for row in cloned:
            row.advanced = {}
        applied = apply_surface_properties_payload(cloned, payload)
        if applied != 4:
            raise AssertionError(f"Expected four drawing-property records, got {applied}.")
        if not pdf_path.exists() or pdf_path.stat().st_size < 20_000:
            raise AssertionError(f"Expected non-empty PDF export at {pdf_path}.")

    print("Lens drawing PDF case study validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
