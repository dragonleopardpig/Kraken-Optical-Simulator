from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from KrakenOS.UI.layout_editor import (
    FIELDS,
    LAYOUTS_DIR,
    POSE_TOLERANCE_OVERLAY_KEY,
    KrakenLayoutEditor,
    SurfaceRow,
    _load_python_title,
)


@dataclass
class TableComponentWorkflowCheck:
    check: str
    ok: bool
    detail: str


class _Var:
    def __init__(self, value):
        self._value = value

    def get(self):
        return self._value

    def set(self, value) -> None:
        self._value = value


class _FakeTable:
    def __init__(self) -> None:
        self._children: list[str] = []
        self._selection: list[str] = []
        self._focus = ""
        self._values: dict[str, tuple[str, ...]] = {}

    def sync(self, rows: list[SurfaceRow]) -> None:
        self._children = [f"row_{index}" for index, _row in enumerate(rows)]
        self._values = {item: self._values.get(item, ()) for item in self._children}
        self._selection = [item for item in self._selection if item in self._children]
        if self._focus not in self._children:
            self._focus = self._selection[0] if self._selection else ""

    def get_children(self):
        return tuple(self._children)

    def selection(self):
        return tuple(self._selection)

    def selection_set(self, items) -> None:
        if isinstance(items, str):
            items = [items]
        self._selection = [item for item in items if item in self._children]

    def selection_remove(self, *items) -> None:
        remove = set(items)
        self._selection = [item for item in self._selection if item not in remove]

    def focus(self, item=None):
        if item is None:
            return self._focus
        self._focus = str(item)

    def see(self, _item) -> None:
        return None

    def exists(self, item) -> bool:
        return str(item) in self._children

    def item(self, item, option=None):
        if option == "values":
            return self._values.get(str(item), ())
        return {"values": self._values.get(str(item), ())}

    def set_values(self, row_index: int, values: list[str]) -> None:
        self._values[f"row_{int(row_index)}"] = tuple(values)


def _layout_path_by_title(title: str) -> Path:
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    raise ValueError(f"Common layout not found: {title}")


def _headless_editor() -> KrakenLayoutEditor:
    editor = KrakenLayoutEditor.__new__(KrakenLayoutEditor)
    editor.headless = True
    editor.layout_files = {"Doublet Lens": _layout_path_by_title("Doublet Lens")}
    editor.rows = [
        SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    editor.table = _FakeTable()
    editor.table.sync(editor.rows)
    editor.editor = None
    editor._editor_row_id = None
    editor._editor_field = None
    editor.current_layout_file = None
    editor.status_var = _Var("")
    editor.layout_var = _Var("Common Optical Layout")
    editor.machine_vision_var = _Var("Machine Vision Lens")
    editor.example_var = _Var("Examples")
    editor.field_value_var = _Var("0.0")
    editor.ray_count_var = _Var("5")
    editor.source_model_var = _Var("Collimated disk")
    editor._surface_row_clipboard = []
    editor._clipboard_text = ""
    editor.append_progress = lambda _message: None
    editor.append_debug = lambda _message: None
    editor.refresh_plot = lambda *args, **kwargs: None
    editor._begin_history_capture = lambda: None
    editor._commit_history_capture = lambda: None
    editor._commit_pending_table_edit = lambda: None
    editor._read_rows_from_table = lambda: None
    editor.after_idle = lambda _callback, *args: None
    editor._schedule_table_grid_update = lambda *args, **kwargs: None
    editor._refresh_analysis_surface_choices = lambda: None
    editor._refresh_operand_surface_choices = lambda: None
    editor._normalize_special_rows = lambda: None
    editor._copy_text_to_clipboard = lambda text: (
        setattr(editor, "_clipboard_text", text) or (True, "test")
    )
    editor.clipboard_get = lambda: editor._clipboard_text

    def sync_table() -> None:
        editor.table.sync(editor.rows)

    editor._sync_table = sync_table
    return editor


def _table_values_for_row(row: SurfaceRow, row_index: int) -> list[str]:
    values: dict[str, object] = {
        "label": str(row_index),
        "surface": row.surface,
        "name": row.name,
        "glass": row.glass,
    }
    for field in FIELDS:
        values.setdefault(field, getattr(row, field, ""))
    return [str(values.get(field, "")) for field in FIELDS]


def validate_table_component_workflow() -> list[TableComponentWorkflowCheck]:
    checks: list[TableComponentWorkflowCheck] = []
    app = _headless_editor()
    try:
        app.field_value_var.set("12.345")
        app.ray_count_var.set("7")
        app.source_model_var.set("Gaussian Beam")

        settings_before = {
            "field_value": app.field_value_var.get(),
            "ray_count": app.ray_count_var.get(),
            "source_model": app.source_model_var.get(),
        }
        app.insert_layout_component_by_name("Doublet Lens", refresh=False)
        inserted_rows = [row for row in app.rows if row.surface not in {"Object", "Image"}]
        settings_after = {
            "field_value": app.field_value_var.get(),
            "ray_count": app.ray_count_var.get(),
            "source_model": app.source_model_var.get(),
        }
        checks.append(
            TableComponentWorkflowCheck(
                "insert common component preserves global settings",
                bool(inserted_rows) and settings_before == settings_after,
                f"inserted={len(inserted_rows)}, before={settings_before}, after={settings_after}",
            )
        )

        first_component_indices = [index for index, row in enumerate(app.rows) if row.surface not in {"Object", "Image"}]
        if first_component_indices:
            app._select_table_indices(first_component_indices, focus_index=first_component_indices[0])
            before_copy_labels = [app._element_key(app.rows[index]) for index in first_component_indices]
            copy_result = app.copy_selected_rows_to_clipboard()
            row_count_before_paste = len(app.rows)
            app.paste_rows_from_clipboard()
            pasted_count = len(app.rows) - row_count_before_paste
            pasted_indices = list(range(row_count_before_paste - 1, row_count_before_paste - 1 + pasted_count))
            pasted_labels = [app._element_key(app.rows[index]) for index in pasted_indices if 0 <= index < len(app.rows)]
            checks.append(
                TableComponentWorkflowCheck(
                    "ctrl-c/ctrl-v copies component rows, not object/image",
                    copy_result == "break"
                    and pasted_count == len(first_component_indices)
                    and app.rows[0].surface == "Object"
                    and app.rows[-1].surface == "Image",
                    f"copied={len(first_component_indices)}, pasted={pasted_count}, rows={len(app.rows)}",
                )
            )
            checks.append(
                TableComponentWorkflowCheck(
                    "pasted element labels are independent",
                    bool(before_copy_labels)
                    and bool(pasted_labels)
                    and set(before_copy_labels).isdisjoint(set(pasted_labels)),
                    f"source_labels={before_copy_labels}, pasted_labels={pasted_labels}",
                )
            )

            before_context_insert = len(app.rows)
            app.insert_surface_context_component(first_component_indices[-1], "wedge_prism")
            wedge_rows = [row for row in app.rows if "Wedge" in row.name]
            checks.append(
                TableComponentWorkflowCheck(
                    "right-click wedge prism inserts tilted glass/air pair",
                    len(app.rows) == before_context_insert + 2
                    and [row.glass for row in wedge_rows] == ["BK7", "AIR"]
                    and any(abs(float(row.tilt_x)) > 0.0 for row in wedge_rows),
                    f"surfaces={[row.surface for row in wedge_rows]}, glass={[row.glass for row in wedge_rows]}, tilts={[row.tilt_x for row in wedge_rows]}",
                )
            )

            before_cube_insert = len(app.rows)
            app.insert_surface_context_component(len(app.rows) - 2, "cube_beam_splitter")
            cube_rows = [row for row in app.rows if row.name.startswith("Cube BS")]
            checks.append(
                TableComponentWorkflowCheck(
                    "right-click cube beam splitter inserts splitter primitive",
                    len(app.rows) == before_cube_insert + 3
                    and any(row.surface == "Beam Splitter" for row in cube_rows)
                    and any("BeamSplitter" in (row.advanced or {}) for row in cube_rows),
                    f"surfaces={[row.surface for row in cube_rows]}, elements={[row.element for row in cube_rows]}",
                )
            )

            pose_advanced = KrakenLayoutEditor._advanced_with_pose_tolerance_overlay(
                {},
                "desp_x",
                [-0.05, 0.0, 0.05],
            )
            pose_row = SurfaceRow(
                surface="Standard",
                name="Tolerance test",
                glass="BK7",
                thickness=10.0,
                diameter=20.0,
                desp_x=0.0,
                advanced=pose_advanced,
            )
            pose_values = KrakenLayoutEditor._pose_tolerance_overlay_values(pose_row, "desp_x")
            checks.append(
                TableComponentWorkflowCheck(
                    "pose tolerance overlay stores decenter list",
                    pose_values == [-0.05, 0.0, 0.05]
                    and POSE_TOLERANCE_OVERLAY_KEY in pose_row.advanced.get("Display2D", {}),
                    f"values={pose_values}, advanced={pose_row.advanced}",
                )
            )

            app.rows = [
                SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                SurfaceRow(
                    surface="Standard",
                    name="Tilt tolerance",
                    glass="BK7",
                    thickness=10.0,
                    diameter=20.0,
                    tilt_y=0.0,
                    advanced=KrakenLayoutEditor._advanced_with_pose_tolerance_overlay(
                        {},
                        "tilt_y",
                        [-0.1, 0.0, 0.1],
                    ),
                ),
                SurfaceRow(
                    surface="Standard",
                    name="Decenter tolerance",
                    glass="AIR",
                    thickness=25.0,
                    diameter=20.0,
                    desp_x=0.0,
                    advanced=KrakenLayoutEditor._advanced_with_pose_tolerance_overlay(
                        {},
                        "desp_x",
                        [-0.05, 0.0, 0.05],
                    ),
                ),
                SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
            ]
            assignments = app._pose_tolerance_variant_assignments()
            checks.append(
                TableComponentWorkflowCheck(
                    "same-length pose tolerance lists sweep together",
                    len(assignments) == 2 and all(len(assignment) == 2 for assignment in assignments),
                    f"assignments={assignments}",
                )
            )

            parse_app = _headless_editor()
            delattr(parse_app, "_read_rows_from_table")
            parse_app.rows = [
                SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                SurfaceRow(surface="Standard", name="DespY parse", glass="BK7", thickness=10.0, diameter=20.0),
                SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
            ]
            parse_app.table.sync(parse_app.rows)
            for index, row in enumerate(parse_app.rows):
                values = _table_values_for_row(row, index)
                if index == 1:
                    values[FIELDS.index("desp_y")] = "-5,0,5"
                parse_app.table.set_values(index, values)
            parse_app._read_rows_from_table()
            parsed_desp_y = parse_app.rows[1].desp_y
            parsed_values = KrakenLayoutEditor._pose_tolerance_overlay_values(parse_app.rows[1], "desp_y")
            display_text = KrakenLayoutEditor._format_pose_cell(parse_app.rows, 1, "desp_y")
            checks.append(
                TableComponentWorkflowCheck(
                    "table parser preserves DespY tolerance list",
                    parsed_desp_y == 0.0
                    and parsed_values == [-5.0, 0.0, 5.0]
                    and display_text == "-5, 0, 5",
                    f"nominal={parsed_desp_y}, values={parsed_values}, display={display_text!r}",
                )
            )

            group_app = _headless_editor()
            delattr(group_app, "_read_rows_from_table")
            group_app.rows = [
                SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
                SurfaceRow(surface="Standard", name="Doublet front", glass="BK7", thickness=4.0, diameter=20.0, element="Doublet"),
                SurfaceRow(surface="Standard", name="Doublet cement", glass="F2", thickness=3.0, diameter=20.0, element="Doublet"),
                SurfaceRow(surface="Standard", name="Doublet rear", glass="AIR", thickness=80.0, diameter=20.0, element="Doublet"),
                SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
            ]
            group_app.table.sync(group_app.rows)
            for index, row in enumerate(group_app.rows):
                values = _table_values_for_row(row, index)
                if index == 1:
                    values[FIELDS.index("desp_y")] = "-5,0,5"
                group_app.table.set_values(index, values)
            group_app._read_rows_from_table()
            group_values = [
                KrakenLayoutEditor._pose_tolerance_overlay_values(group_app.rows[index], "desp_y")
                for index in (1, 2, 3)
            ]
            group_assignments = group_app._pose_tolerance_variant_assignments()
            checks.append(
                TableComponentWorkflowCheck(
                    "grouped element DespY list propagates to whole element",
                    all(values == [-5.0, 0.0, 5.0] for values in group_values)
                    and all(float(group_app.rows[index].desp_y) == 0.0 for index in (1, 2, 3))
                    and len(group_assignments) == 2
                    and all(len(assignment) == 3 for assignment in group_assignments),
                    f"values={group_values}, assignments={group_assignments}",
                )
            )
        else:
            checks.append(
                TableComponentWorkflowCheck(
                    "ctrl-c/ctrl-v copies component rows, not object/image",
                    False,
                    "No inserted component rows available for clipboard validation",
                )
            )
    finally:
        pass
    return checks


def _print_table(checks: list[TableComponentWorkflowCheck]) -> None:
    print("KrakenOS editable-table component workflow validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate component insertion and surface-row clipboard workflows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_table_component_workflow()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
