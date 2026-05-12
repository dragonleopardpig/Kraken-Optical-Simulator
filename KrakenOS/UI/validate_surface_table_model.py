from __future__ import annotations

from KrakenOS.UI import layout_editor
from KrakenOS.UI.surface_table_model import (
    SURFACE_ROW_CLIPBOARD_FORMAT,
    SurfaceRow,
    clone_surface_row,
    normalized_rows_copy,
    surface_rows_from_clipboard_text,
    surface_rows_from_records,
    surface_rows_to_clipboard_text,
    surface_rows_to_specs,
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    _require(layout_editor.SurfaceRow is SurfaceRow, "layout_editor no longer re-exports SurfaceRow compatibility")
    _require(
        layout_editor.SURFACE_ROW_CLIPBOARD_FORMAT == SURFACE_ROW_CLIPBOARD_FORMAT,
        "layout_editor no longer re-exports the clipboard format compatibility constant",
    )

    rows = [
        SurfaceRow(surface="Standard", name="Surface", element="Bad", advanced={"Element": {"path_key": "bad"}}),
        SurfaceRow(
            surface="Standard",
            name="Lens front",
            element="E1",
            rc=12.5,
            thickness=3.0,
            diameter=20.0,
            glass="BK7",
            advanced={"Display2D": {"pose_tolerance_overlay": {"tilt_y": [-1.0, 0.0, 1.0]}}},
        ),
        SurfaceRow(surface="Standard", name="Surface", element="Bad", advanced={"Element": {"path_key": "bad"}}),
    ]

    normalized = normalized_rows_copy(rows)
    _require(normalized[0].surface == "Object", "first row was not normalized to Object")
    _require(normalized[-1].surface == "Image", "last row was not normalized to Image")
    _require(normalized[0].element == "", "Object row retained an Element label")
    _require("Element" not in normalized[-1].advanced, "Image row retained Element metadata")
    _require(rows[0].surface == "Standard" and rows[0].element == "Bad", "normalization mutated input rows")

    cloned = clone_surface_row(rows[1])
    cloned.advanced["Display2D"]["pose_tolerance_overlay"]["tilt_y"][0] = -2.0
    original_values = rows[1].advanced["Display2D"]["pose_tolerance_overlay"]["tilt_y"]
    _require(original_values[0] == -1.0, "clone_surface_row did not isolate nested advanced data")

    specs = surface_rows_to_specs(normalized, metal_catalogs=[{"name": "Alum", "path": "Cat/Alum.csv", "type": 1}])
    _require(specs[0]["_metal_catalogs"][0]["name"] == "Alum", "metal catalogs were not attached to first row spec")
    _require(specs[1]["surface"] == "Standard" and specs[1]["glass"] == "BK7", "row spec lost surface/glass data")

    text = surface_rows_to_clipboard_text([rows[1]])
    pasted = surface_rows_from_clipboard_text(text)
    _require(len(pasted) == 1 and pasted[0].name == "Lens front", "clipboard round trip failed")
    _require(surface_rows_from_clipboard_text("{not json") == [], "invalid clipboard JSON was not rejected")
    _require(surface_rows_from_clipboard_text('{"format":"other","rows":[]}') == [], "foreign clipboard format was accepted")

    restored = surface_rows_from_records([{"surface": "Mirror", "glass": "MIRROR", "unknown": "ignored"}, "skip"])
    _require(len(restored) == 1 and restored[0].surface == "Mirror", "record restore failed to filter unknown fields")

    print("Surface table model validation passed.")


if __name__ == "__main__":
    main()
