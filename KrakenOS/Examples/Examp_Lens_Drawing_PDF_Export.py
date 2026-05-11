#!/usr/bin/env python3
"""Build a multi-element lens prescription and export fabrication PDF drawings.

This example mirrors the UI workflow:

1. enter the optical surfaces in the editable table;
2. fill the Lens Drawing Surface Properties dialog;
3. export an ISO-style multi-page PDF drawing.

The generated PDF is a fabrication starting point. Verify shop tolerances,
coatings, material melt data, and drawing notes before release.
"""

from __future__ import annotations

import json
from pathlib import Path

from KrakenOS.UI.layout_editor import SurfaceRow
from KrakenOS.UI.lens_drawing_export import export_lens_drawing
from KrakenOS.UI.lens_drawing_properties import (
    DRAWING_PROPERTIES_ATTR,
    normalize_drawing_properties,
    surface_properties_payload,
)


DEFAULT_OUTPUT_DIR = Path("/tmp/kraken_lens_drawing_pdf_export")


def _drawing_props(**values: object) -> dict[str, object]:
    return normalize_drawing_properties(values)


def build_rows() -> list[SurfaceRow]:
    """Return a compact cemented triplet suitable for PDF drawing export."""
    return [
        SurfaceRow(
            label="0",
            surface="Object",
            name="Object",
            thickness=25.0,
            diameter=32.0,
            glass="AIR",
            drawing=0.0,
        ),
        SurfaceRow(
            label="1",
            surface="Standard",
            name="E1 front crown",
            rc=42.0,
            thickness=6.0,
            diameter=28.0,
            glass="N-BK7",
            drawing=1.0,
            advanced={
                DRAWING_PROPERTIES_ATTR: _drawing_props(
                    clear_aperture_mm=26.0,
                    radius_tolerance="+/-0.035",
                    thickness_tolerance="+/-0.05",
                    diameter_tolerance="+0/-0.03",
                    form_error="3/ 3 (0.5) lambda=632.8 nm",
                    irregularity="4/ -",
                    scratch_dig="5/ 40-20",
                    surface_note="6/ -",
                    coating_note="R(avg) < 0.75% from 450-650 nm",
                    material_note="Melt data required",
                    centration_note="14/ 1'",
                    edge_note="0.2 mm protective chamfer",
                )
            },
        ),
        SurfaceRow(
            label="2",
            surface="Standard",
            name="E1/E2 cement interface",
            rc=-28.0,
            thickness=3.2,
            diameter=27.5,
            glass="N-SF5",
            drawing=1.0,
            advanced={
                DRAWING_PROPERTIES_ATTR: _drawing_props(
                    clear_aperture_mm=25.5,
                    radius_tolerance="+/-0.025",
                    form_error="3/ 3 (0.5) lambda=632.8 nm",
                    scratch_dig="5/ 40-20",
                    cement_note="NOA 61 or equivalent",
                    coating_note="No coating on cemented surface",
                    material_note="High-index flint element",
                )
            },
        ),
        SurfaceRow(
            label="3",
            surface="Standard",
            name="E2/E3 cement interface",
            rc=64.0,
            thickness=5.8,
            diameter=27.0,
            glass="N-LAK22",
            drawing=1.0,
            advanced={
                DRAWING_PROPERTIES_ATTR: _drawing_props(
                    clear_aperture_mm=25.0,
                    radius_tolerance="+/-0.030",
                    thickness_tolerance="+/-0.05",
                    form_error="3/ 3 (0.5) lambda=632.8 nm",
                    scratch_dig="5/ 40-20",
                    cement_note="NOA 61 or equivalent",
                    material_note="Lanthanum crown element",
                )
            },
        ),
        SurfaceRow(
            label="4",
            surface="Standard",
            name="E3 rear surface",
            rc=-55.0,
            thickness=42.0,
            diameter=26.5,
            glass="AIR",
            drawing=1.0,
            advanced={
                DRAWING_PROPERTIES_ATTR: _drawing_props(
                    clear_aperture_mm=24.5,
                    radius_tolerance="+/-0.040",
                    diameter_tolerance="+0/-0.03",
                    form_error="3/ 3 (0.5) lambda=632.8 nm",
                    irregularity="4/ -",
                    scratch_dig="5/ 40-20",
                    coating_note="R(avg) < 0.75% from 450-650 nm",
                    edge_note="Edge blacken after coating",
                    other_requirement="Inspect cement wedge after assembly",
                )
            },
        ),
        SurfaceRow(
            label="5",
            surface="Image",
            name="Image",
            thickness=0.0,
            diameter=32.0,
            glass="AIR",
            drawing=0.0,
        ),
    ]


def export_properties_json(rows: list[SurfaceRow], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = surface_properties_payload(rows, [1, 2, 3, 4])
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def export_pdf(rows: list[SurfaceRow], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return export_lens_drawing(
        rows,
        path,
        title="Case Study Cemented Triplet",
        dwg_no="KRAKEN-CS13-TRIPLET",
        efl=50.0,
        bfl=42.0,
    )


def main() -> int:
    rows = build_rows()
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path = export_properties_json(rows, DEFAULT_OUTPUT_DIR / "triplet_surface_properties.json")
    pdf_path = export_pdf(rows, DEFAULT_OUTPUT_DIR / "multi_element_lens_fabrication_drawing.pdf")
    print(f"Surface-property JSON: {json_path}")
    print(f"Fabrication PDF: {pdf_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
