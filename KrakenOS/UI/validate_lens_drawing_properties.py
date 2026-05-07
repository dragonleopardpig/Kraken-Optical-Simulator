"""Validate ISO-style lens drawing surface property persistence and export."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from KrakenOS.UI.lens_drawing_export import export_lens_drawing, identify_elements
from KrakenOS.UI.lens_drawing_properties import (
    DRAWING_PROPERTIES_ATTR,
    apply_surface_properties_payload,
    normalize_drawing_properties,
    surface_properties_payload,
    validate_drawing_properties,
)


def _row(
    surface: str,
    name: str,
    rc: float,
    thickness: float,
    diameter: float,
    glass: str,
    *,
    advanced: dict | None = None,
    label: str = "",
) -> SimpleNamespace:
    return SimpleNamespace(
        label=label,
        surface=surface,
        name=name,
        rc=rc,
        thickness=thickness,
        diameter=diameter,
        glass=glass,
        advanced=dict(advanced or {}),
    )


def _sample_rows() -> list[SimpleNamespace]:
    full_props = normalize_drawing_properties(
        {
            "clear_aperture_mm": "24",
            "radius_tolerance": "+/-0.035",
            "thickness_tolerance": "+/-0.1",
            "diameter_tolerance": "+0/-0.025",
            "form_error": "3/ 3 (0.5) lambda=632.8 nm",
            "irregularity": "4/ -",
            "scratch_dig": "5/ 40-20 (MIL-PRF-13830B)",
            "surface_note": "6/ -",
            "coating_note": "1/4 wave MgF2 @ 550 nm",
            "material_note": "670/472",
            "centration_note": "14/ 1'",
            "edge_note": "Protective chamfers as needed",
            "other_requirement": "Edge blacken after coating",
        }
    )
    errors = validate_drawing_properties(full_props)
    if errors:
        raise AssertionError("Unexpected DrawingProperties validation errors: " + " ".join(errors))
    cement_props = normalize_drawing_properties(
        {
            "clear_aperture_mm": 24.0,
            "radius_tolerance": "+/-0.022",
            "form_error": "3/ 3 (0.5) lambda=632.8 nm",
            "scratch_dig": "5/ 40-20 (MIL-PRF-13830B)",
            "cement_note": "NOA 61 OR EQUIVALENT",
            "material_note": "728/284",
        }
    )
    rear_props = normalize_drawing_properties(
        {
            "clear_aperture_mm": 24.0,
            "radius_tolerance": "+/-0.215",
            "coating_note": "R(avg) < 1.75% from 400-700 nm",
        }
    )
    return [
        _row("Object", "Object", 0.0, 0.0, 25.0, "AIR", label="0"),
        _row("Standard", "L2,1 front", 34.53, 9.0, 25.0, "N-BaF10", advanced={DRAWING_PROPERTIES_ATTR: full_props}, label="1"),
        _row("Standard", "Cement interface", -21.98, 2.5, 25.0, "N-SF10", advanced={DRAWING_PROPERTIES_ATTR: cement_props}, label="2"),
        _row("Standard", "L2,2 rear", 214.63, 43.53, 25.0, "AIR", advanced={DRAWING_PROPERTIES_ATTR: rear_props}, label="3"),
        _row("Image", "Image", 0.0, 0.0, 25.0, "AIR", label="4"),
    ]


def main() -> int:
    rows = _sample_rows()
    groups, _info = identify_elements(rows)
    if len(groups) != 1 or not groups[0].is_cemented or len(groups[0].elements) != 2:
        raise AssertionError("Expected one cemented two-element lens group.")

    payload = surface_properties_payload(rows, [1, 2, 3])
    cloned = _sample_rows()
    for row in cloned:
        row.advanced = {}
    applied = apply_surface_properties_payload(cloned, payload)
    if applied != 3:
        raise AssertionError(f"Expected 3 drawing-property records to apply, got {applied}.")
    if cloned[1].advanced.get(DRAWING_PROPERTIES_ATTR, {}).get("radius_tolerance") != "+/-0.035":
        raise AssertionError("DrawingProperties JSON round trip did not preserve radius tolerance.")
    if cloned[1].advanced.get(DRAWING_PROPERTIES_ATTR, {}).get("other_requirement") != "Edge blacken after coating":
        raise AssertionError("DrawingProperties JSON round trip did not preserve other_requirement.")

    out = Path("/tmp/kraken_lens_drawing_properties_validation.pdf")
    export_lens_drawing(rows, out, title="ISO 10110 Drawing Properties Validation", dwg_no="KRAKEN-ISO-TEST")
    if not out.exists() or out.stat().st_size < 10_000:
        raise AssertionError(f"Expected non-empty PDF export at {out}.")
    print("Lens drawing surface properties validation passed.")
    print(f"Generated: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
