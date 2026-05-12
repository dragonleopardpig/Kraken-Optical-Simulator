from __future__ import annotations

from KrakenOS.UI import layout_editor
from KrakenOS.UI.surface_table_model import (
    SURFACE_ROW_CLIPBOARD_FORMAT,
    SurfaceRow,
    append_layout_rows,
    clone_surface_row,
    component_rows_from_layout,
    duplicate_rows_for_indices,
    inserted_layout_row_indices,
    insert_surface_rows,
    normalized_rows_copy,
    pasteable_component_rows,
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

    component_layout = [
        SurfaceRow(surface="Object", name="Object", thickness=10.0),
        SurfaceRow(surface="Standard", name="Front", glass="BK7"),
        SurfaceRow(surface="Standard", name="Back", glass="AIR"),
        SurfaceRow(surface="Image", name="Image"),
    ]
    component_rows = component_rows_from_layout(component_layout, element_name="Catalog Doublet")
    _require(len(component_rows) == 2, "component extraction did not strip Object/Image rows")
    _require(all(row.element == "Catalog Doublet" for row in component_rows), "component extraction did not assign element labels")
    _require(component_layout[1].element == "", "component extraction mutated source layout rows")

    base = [
        SurfaceRow(surface="Object", name="Object"),
        SurfaceRow(surface="Aperture", name="Stop"),
        SurfaceRow(surface="Image", name="Image"),
    ]
    appended = append_layout_rows(base, component_layout, insert_after=0, element_name="Inserted")
    _require([row.name for row in appended] == ["Object", "Front", "Back", "Stop", "Image"], "append layout inserted at wrong position")
    _require(all(row.element == "Inserted" for row in appended[1:3]), "append layout lost inserted element label")
    _require([row.name for row in base] == ["Object", "Stop", "Image"], "append layout mutated source rows")

    inserted_rows, insert_at = insert_surface_rows(base, [SurfaceRow(surface="Mirror", name="Fold")], insert_after=10)
    _require(insert_at == 2, "surface insertion did not clamp before Image")
    _require([row.name for row in inserted_rows] == ["Object", "Stop", "Fold", "Image"], "surface insertion produced wrong row order")

    seeded_rows, seeded_at = insert_surface_rows([], [SurfaceRow(surface="Aperture", name="Stop")])
    _require(seeded_at == 1 and [row.surface for row in seeded_rows] == ["Object", "Aperture", "Image"], "empty insertion did not create Object/Image starter rows")

    duplicates = duplicate_rows_for_indices(appended, [2, 100, -1])
    _require(len(duplicates) == 1 and duplicates[0].name == "Back", "duplicate helper did not filter invalid indices")
    duplicates[0].name = "Changed"
    _require(appended[2].name == "Back", "duplicate helper mutated source rows")

    pasteable = pasteable_component_rows([SurfaceRow(surface="Object"), SurfaceRow(surface="Mirror"), SurfaceRow(surface="Image")])
    _require(len(pasteable) == 1 and pasteable[0].surface == "Mirror", "pasteable helper did not filter Object/Image")

    selected_indices = inserted_layout_row_indices(len(appended), component_layout, insert_after=0)
    _require(selected_indices == [1, 2], "inserted layout selection indices changed")

    print("Surface table model validation passed.")


if __name__ == "__main__":
    main()
