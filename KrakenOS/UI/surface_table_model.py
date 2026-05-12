"""Pure surface-row data helpers for the KrakenOS UI table.

The Tk editor still owns widget parsing and surface-type side effects.  This
module owns the stable row record shape used by layouts, clipboard payloads,
and runtime system serialization.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Iterable


SURFACE_ROW_CLIPBOARD_FORMAT = "krakenos.surface_rows.v1"


@dataclass
class SurfaceRow:
    label: str = "0"
    element: str = ""
    surface: str = "Standard"
    name: str = "Surface"
    optimize_rc: bool = False
    optimize_rc_bounds: tuple[float, float] | None = None
    rc: float = 0.0
    k: float = 0.0
    axicon: float = 0.0
    diff_ord: float = 0.0
    grating_d: float = 0.0
    grating_angle: float = 0.0
    optimize_thickness: bool = False
    optimize_thickness_bounds: tuple[float, float] | None = None
    thickness: float = 0.0
    diameter: float = 25.0
    in_diameter: float = 0.0
    drawing: float = 1.0
    extra_data: object = 0.0
    uda: object = "None"
    advanced: dict[str, object] = field(default_factory=dict)
    tilt_x: float = 0.0
    tilt_y: float = 0.0
    tilt_z: float = 0.0
    desp_x: float = 0.0
    desp_y: float = 0.0
    desp_z: float = 0.0
    axis_move: float = 0.0
    glass: str = "AIR"


def clone_surface_row(row: SurfaceRow) -> SurfaceRow:
    return SurfaceRow(**asdict(row))


def clone_surface_rows(rows: Iterable[SurfaceRow]) -> list[SurfaceRow]:
    return [clone_surface_row(row) for row in rows]


def normalized_rows_copy(
    rows: list[SurfaceRow],
    *,
    element_advanced_attr: str = "Element",
) -> list[SurfaceRow]:
    copied = clone_surface_rows(rows)
    if copied:
        copied[0].element = ""
        copied[0].advanced = dict(copied[0].advanced or {})
        copied[0].advanced.pop(element_advanced_attr, None)
        copied[0].surface = "Object"
        if not copied[0].name or copied[0].name == "Surface":
            copied[0].name = "Object"
        copied[-1].element = ""
        copied[-1].advanced = dict(copied[-1].advanced or {})
        copied[-1].advanced.pop(element_advanced_attr, None)
        copied[-1].surface = "Image"
        if not copied[-1].name or copied[-1].name == "Surface":
            copied[-1].name = "Image"
    return copied


def surface_row_to_spec(row: SurfaceRow) -> dict:
    return {
        "label": row.label,
        "element": row.element,
        "surface": row.surface,
        "name": row.name,
        "optimize_rc": row.optimize_rc,
        "optimize_rc_bounds": row.optimize_rc_bounds,
        "rc": row.rc,
        "k": row.k,
        "axicon": row.axicon,
        "diff_ord": row.diff_ord,
        "grating_d": row.grating_d,
        "grating_angle": row.grating_angle,
        "optimize_thickness": row.optimize_thickness,
        "optimize_thickness_bounds": row.optimize_thickness_bounds,
        "thickness": row.thickness,
        "diameter": row.diameter,
        "in_diameter": row.in_diameter,
        "drawing": row.drawing,
        "extra_data": row.extra_data,
        "uda": row.uda,
        "advanced": dict(row.advanced),
        "tilt_x": row.tilt_x,
        "tilt_y": row.tilt_y,
        "tilt_z": row.tilt_z,
        "desp_x": row.desp_x,
        "desp_y": row.desp_y,
        "desp_z": row.desp_z,
        "axis_move": row.axis_move,
        "glass": row.glass,
    }


def surface_rows_to_specs(
    rows: Iterable[SurfaceRow],
    *,
    metal_catalogs: list[dict[str, object]] | None = None,
) -> list[dict]:
    row_specs = [surface_row_to_spec(row) for row in rows]
    if row_specs and metal_catalogs:
        row_specs[0]["_metal_catalogs"] = list(metal_catalogs)
    return row_specs


def surface_rows_to_records(rows: Iterable[SurfaceRow]) -> list[dict[str, object]]:
    return [asdict(row) for row in rows]


def surface_rows_from_records(records: object) -> list[SurfaceRow]:
    if not isinstance(records, list):
        return []
    fields = set(SurfaceRow.__dataclass_fields__)
    rows: list[SurfaceRow] = []
    for record in records:
        if not isinstance(record, dict):
            continue
        data = {key: value for key, value in record.items() if key in fields}
        try:
            rows.append(SurfaceRow(**data))
        except Exception:
            continue
    return rows


def surface_rows_to_clipboard_text(rows: Iterable[SurfaceRow]) -> str:
    payload = {
        "format": SURFACE_ROW_CLIPBOARD_FORMAT,
        "rows": surface_rows_to_records(rows),
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def surface_rows_from_clipboard_text(text: str) -> list[SurfaceRow]:
    try:
        payload = json.loads(text)
    except Exception:
        return []
    if not isinstance(payload, dict):
        return []
    if str(payload.get("format", "") or "") != SURFACE_ROW_CLIPBOARD_FORMAT:
        return []
    return surface_rows_from_records(payload.get("rows"))
