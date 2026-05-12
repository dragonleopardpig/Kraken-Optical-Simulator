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


def surface_row_element_key(row: SurfaceRow) -> str:
    return str(getattr(row, "element", "") or "").strip()


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


def component_rows_from_layout(
    layout_rows: list[SurfaceRow],
    *,
    element_name: str = "",
) -> list[SurfaceRow]:
    additions = clone_surface_rows(layout_rows[1:-1])
    if not additions:
        return []
    component_element = str(element_name).strip()
    if not component_element:
        component_element = next((surface_row_element_key(row) for row in additions if surface_row_element_key(row)), "")
    if not component_element and len(additions) > 1:
        component_element = str(additions[0].name or "Element").strip()
    if component_element:
        for row in additions:
            if not surface_row_element_key(row):
                row.element = component_element
    return additions


def append_layout_rows(
    existing_rows: list[SurfaceRow],
    layout_rows: list[SurfaceRow],
    *,
    insert_after: int | None = None,
    element_name: str = "",
) -> list[SurfaceRow]:
    base = clone_surface_rows(existing_rows)
    additions = component_rows_from_layout(layout_rows, element_name=element_name)
    if not additions:
        return base
    if insert_after is None:
        insert_at = len(base)
        if base and base[-1].surface == "Image":
            insert_at -= 1
    else:
        insert_at = max(0, min(int(insert_after) + 1, len(base)))
        if base and base[-1].surface == "Image":
            insert_at = min(insert_at, len(base) - 1)
    for offset, row in enumerate(additions):
        base.insert(insert_at + offset, row)
    return base


def pasteable_component_rows(rows: Iterable[SurfaceRow]) -> list[SurfaceRow]:
    return [clone_surface_row(row) for row in rows if row.surface not in {"Object", "Image"}]


def duplicate_rows_for_indices(rows: list[SurfaceRow], indices: Iterable[int]) -> list[SurfaceRow]:
    duplicates: list[SurfaceRow] = []
    for index in indices:
        if 0 <= int(index) < len(rows):
            duplicates.append(clone_surface_row(rows[int(index)]))
    return duplicates


def insert_surface_rows(
    existing_rows: list[SurfaceRow],
    new_rows: list[SurfaceRow],
    *,
    insert_after: int | None = None,
    starter_rows: list[SurfaceRow] | None = None,
) -> tuple[list[SurfaceRow], int]:
    if not new_rows:
        return clone_surface_rows(existing_rows), -1
    rows = clone_surface_rows(existing_rows)
    if not rows:
        rows = clone_surface_rows(
            starter_rows
            or [
                SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
            ]
        )
    insert_at = len(rows)
    if rows and rows[-1].surface == "Image":
        insert_at = len(rows) - 1
    if insert_after is not None:
        insert_at = max(1, min(int(insert_after) + 1, len(rows)))
        if rows and rows[-1].surface == "Image":
            insert_at = min(insert_at, len(rows) - 1)
    for offset, row in enumerate(new_rows):
        rows.insert(insert_at + offset, clone_surface_row(row))
    return rows, insert_at


def inserted_layout_row_indices(
    total_rows_after_insert: int,
    layout_rows: list[SurfaceRow],
    *,
    insert_after: int | None = None,
    final_row_is_image: bool = True,
) -> list[int]:
    additions = max(len(layout_rows) - 2, 0)
    if additions <= 0:
        return []
    if insert_after is None:
        insert_at = int(total_rows_after_insert) - additions
        if final_row_is_image:
            insert_at -= 1
    else:
        insert_at = min(int(insert_after) + 1, int(total_rows_after_insert) - additions)
    return list(range(insert_at, insert_at + additions))


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
