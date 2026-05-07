"""Shared metadata helpers for ISO-style lens fabrication drawings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


DRAWING_PROPERTIES_ATTR = "DrawingProperties"
DRAWING_PROPERTIES_FORMAT = "krakenos.lens_drawing_properties.v1"


@dataclass(frozen=True)
class DrawingPropertyField:
    key: str
    label: str
    width: int = 18
    kind: str = "text"
    help: str = ""


DRAWING_PROPERTY_FIELDS: tuple[DrawingPropertyField, ...] = (
    DrawingPropertyField(
        "clear_aperture_mm",
        "Clear aperture",
        12,
        "positive_float",
        "Clear optical aperture in mm; exported as Oe/diameter in the ISO table.",
    ),
    DrawingPropertyField(
        "radius_tolerance",
        "R tolerance",
        12,
        "text",
        "Text appended to the radius value, e.g. +/-0.035 or +0/-0.02.",
    ),
    DrawingPropertyField(
        "thickness_tolerance",
        "CT tolerance",
        12,
        "text",
        "Text appended to the center-thickness dimension on the element page.",
    ),
    DrawingPropertyField(
        "diameter_tolerance",
        "Dia tolerance",
        12,
        "text",
        "Text appended to the outside-diameter dimension on the element page.",
    ),
    DrawingPropertyField(
        "form_error",
        "3/ form",
        22,
        "text",
        "ISO 10110 3/ power/form entry, e.g. 3/ 3 (0.5) lambda=632.8 nm.",
    ),
    DrawingPropertyField(
        "irregularity",
        "4/ irregularity",
        16,
        "text",
        "ISO 10110 4/ irregularity entry.",
    ),
    DrawingPropertyField(
        "scratch_dig",
        "5/ scratch-dig",
        22,
        "text",
        "ISO 10110 5/ surface imperfections or MIL scratch-dig entry.",
    ),
    DrawingPropertyField(
        "surface_note",
        "6/ surface",
        20,
        "text",
        "ISO 10110 6/ surface texture or local surface note.",
    ),
    DrawingPropertyField(
        "coating_note",
        "Coating",
        28,
        "text",
        "Coating callout attached to this surface.",
    ),
    DrawingPropertyField(
        "material_note",
        "Material note",
        18,
        "text",
        "Glass code or melt note appended to the material cell, e.g. 670/472.",
    ),
    DrawingPropertyField(
        "cement_note",
        "Cement",
        18,
        "text",
        "Cement note for a cemented interface, e.g. NOA 61 OR EQUIVALENT.",
    ),
    DrawingPropertyField(
        "centration_note",
        "Centering",
        14,
        "text",
        "Centering/tilt callout, commonly ISO 10110 4/ or 14/ text.",
    ),
    DrawingPropertyField(
        "edge_note",
        "Edge/chamfer",
        18,
        "text",
        "Edge blackening, bevel, protective chamfer, or mounting-surface note.",
    ),
)


DRAWING_PROPERTY_FIELD_MAP = {field.key: field for field in DRAWING_PROPERTY_FIELDS}
DRAWING_PROPERTY_ALLOWED_KEYS = frozenset(DRAWING_PROPERTY_FIELD_MAP)


def format_property_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def normalize_drawing_properties(value: object) -> dict[str, object]:
    """Return a cleaned DrawingProperties dictionary.

    Blank strings are removed. ``clear_aperture_mm`` is stored as a positive
    float when provided; all other fields are text because ISO callouts are often
    tolerance strings rather than scalar values.
    """
    if value is None:
        return {}
    if not isinstance(value, dict):
        return value  # Validation will report the type error.
    normalized: dict[str, object] = {}
    for key, raw_value in value.items():
        key_text = str(key).strip()
        if not key_text:
            continue
        if key_text not in DRAWING_PROPERTY_ALLOWED_KEYS:
            normalized[key_text] = raw_value
            continue
        text = format_property_value(raw_value).strip()
        if not text:
            continue
        field = DRAWING_PROPERTY_FIELD_MAP[key_text]
        if field.kind == "positive_float":
            normalized[key_text] = float(text)
        else:
            normalized[key_text] = text
    return normalized


def validate_drawing_properties(value: object) -> list[str]:
    if not isinstance(value, dict):
        return ["DrawingProperties must be a dictionary."]
    errors: list[str] = []
    unknown = sorted(str(key) for key in value if str(key) not in DRAWING_PROPERTY_ALLOWED_KEYS)
    if unknown:
        errors.append("DrawingProperties unknown keys: " + ", ".join(unknown))
    if "clear_aperture_mm" in value and str(value.get("clear_aperture_mm", "")).strip():
        try:
            parsed = float(value["clear_aperture_mm"])
        except Exception as exc:
            errors.append(f"DrawingProperties clear_aperture_mm must be numeric: {exc}.")
        else:
            if parsed <= 0:
                errors.append("DrawingProperties clear_aperture_mm must be positive.")
    return errors


def drawing_properties(row: object) -> dict[str, object]:
    advanced = getattr(row, "advanced", {}) or {}
    if not isinstance(advanced, dict):
        return {}
    props = advanced.get(DRAWING_PROPERTIES_ATTR, {})
    try:
        normalized = normalize_drawing_properties(props)
    except Exception:
        normalized = props
    return dict(normalized) if isinstance(normalized, dict) else {}


def surface_properties_payload(rows: list, indices: Iterable[int] | None = None) -> dict[str, object]:
    if indices is None:
        indices = range(len(rows))
    surfaces = []
    for index in indices:
        if not (0 <= int(index) < len(rows)):
            continue
        row = rows[int(index)]
        surfaces.append(
            {
                "surface_index": int(index),
                "label": str(getattr(row, "label", int(index))),
                "surface": str(getattr(row, "surface", "")),
                "name": str(getattr(row, "name", "")),
                "material": str(getattr(row, "glass", "")),
                "properties": drawing_properties(row),
            }
        )
    return {
        "format": DRAWING_PROPERTIES_FORMAT,
        "version": 1,
        "surfaces": surfaces,
    }


def apply_surface_properties_payload(rows: list, payload: object) -> int:
    if not isinstance(payload, dict):
        raise ValueError("Drawing property file must contain a JSON object.")
    surfaces = payload.get("surfaces", [])
    if not isinstance(surfaces, list):
        raise ValueError("Drawing property file must contain a 'surfaces' list.")
    applied = 0
    for record in surfaces:
        if not isinstance(record, dict):
            continue
        index = record.get("surface_index", record.get("index"))
        try:
            row_index = int(index)
        except Exception:
            continue
        if not (0 <= row_index < len(rows)):
            continue
        props = normalize_drawing_properties(record.get("properties", {}))
        errors = validate_drawing_properties(props)
        if errors:
            raise ValueError(f"S{row_index}: " + " ".join(errors))
        row = rows[row_index]
        row.advanced = dict(getattr(row, "advanced", {}) or {})
        if props:
            row.advanced[DRAWING_PROPERTIES_ATTR] = props
        else:
            row.advanced.pop(DRAWING_PROPERTIES_ATTR, None)
        applied += 1
    return applied
