"""Editable table row reading service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class EditableTableRowService:
    """Read committed table cells back into SurfaceRow records."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _read_rows_from_table(self) -> None:
        le = _layout_module()
        COLUMN_LABELS = le.COLUMN_LABELS
        DISABLED_TABLE_CELL_TEXT = le.DISABLED_TABLE_CELL_TEXT
        ELEMENT_ADVANCED_ATTR = le.ELEMENT_ADVANCED_ATTR
        FIELDS = le.FIELDS
        PATH_LOCAL_COLUMN_LABELS = le.PATH_LOCAL_COLUMN_LABELS
        PATH_LOCAL_TABLE_FIELD_MAP = le.PATH_LOCAL_TABLE_FIELD_MAP
        POSE_TOLERANCE_MAX_VARIANTS = le.POSE_TOLERANCE_MAX_VARIANTS
        SurfaceRow = le.SurfaceRow
        _parse_float_sequence_text = le._parse_float_sequence_text
        rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        path_local_pose_edits: dict[tuple[int, int], dict[str, object]] = {}
        for item in self.table.get_children():
            row_index = self._table_item_row_index(item)
            if row_index is None or not (0 <= row_index < len(rows)):
                continue
            values = self.table.item(item, "values")
            fields = {field: values[index] if index < len(values) else "" for index, field in enumerate(FIELDS)}
            previous = self.rows[row_index] if row_index < len(self.rows) else SurfaceRow(label=str(row_index))
            surface = str(fields["surface"] or previous.surface)
            enabled_fields = self._surface_type_enabled_fields(surface)
            advanced = dict(previous.advanced)
            previous_metadata = self._element_metadata(previous)
            use_path_local_pose = bool(self.editor.__dict__.get("_table_path_local_mode_active", False)) and self._metadata_has_path_pose(previous_metadata)
            if use_path_local_pose:
                enabled_fields = set(enabled_fields) | set(PATH_LOCAL_TABLE_FIELD_MAP)

            def text_field(field: str, attr: str) -> str:
                value = str(fields.get(field, "")).strip()
                if field not in fields or field not in enabled_fields:
                    return str(getattr(previous, attr))
                return value

            def numeric_field(field: str, attr: str) -> float:
                value = str(fields.get(field, "")).strip()
                if field not in fields or field not in enabled_fields or not value or value.upper() == DISABLED_TABLE_CELL_TEXT:
                    return float(getattr(previous, attr))
                if field in {"rc", "thickness"}:
                    return self._parse_numeric_display(value)
                return float(value)

            def pose_numeric_field(field: str, attr: str) -> float:
                nonlocal advanced
                value = str(fields.get(field, "")).replace("*", "").strip()
                if field not in fields or field not in enabled_fields or not value or value.upper() == DISABLED_TABLE_CELL_TEXT:
                    return float(getattr(previous, attr))
                values = _parse_float_sequence_text(value)
                if not values:
                    advanced = self._advanced_with_pose_tolerance_overlay(advanced, field, [])
                    if field == "tilt_x":
                        advanced = self._advanced_with_galvo_scan_overlay(advanced, [])
                    return float(getattr(previous, attr))
                if len(values) > POSE_TOLERANCE_MAX_VARIANTS:
                    raise ValueError(f"{COLUMN_LABELS.get(field, field)} tolerance overlay supports {POSE_TOLERANCE_MAX_VARIANTS} or fewer values.")

                if field == "tilt_x" and surface == "Mirror":
                    advanced = self._advanced_with_pose_tolerance_overlay(advanced, field, [])
                    branch_angle = self._mirror_branch_angle_before_index(rows, row_index)
                    local_values = [
                        self._mirror_local_tilt_deg_from_display(branch_angle, display_value)
                        for display_value in values
                    ]
                    if len(local_values) > 1:
                        advanced = self._advanced_with_galvo_scan_overlay(advanced, local_values)
                        return float(local_values[len(local_values) // 2])
                    advanced = self._advanced_with_galvo_scan_overlay(advanced, [])
                    return float(local_values[0])

                if field == "tilt_x":
                    advanced = self._advanced_with_galvo_scan_overlay(advanced, [])
                if len(values) > 1:
                    advanced = self._advanced_with_pose_tolerance_overlay(advanced, field, values)
                    return float(values[len(values) // 2])
                advanced = self._advanced_with_pose_tolerance_overlay(advanced, field, [])
                return float(values[0])

            path_local_metadata = dict(previous_metadata)

            def path_local_numeric_field(field: str, metadata_key: str) -> float:
                value = str(fields.get(field, "")).replace("*", "").strip()
                if field not in fields or not value or value.upper() == DISABLED_TABLE_CELL_TEXT:
                    return float(previous_metadata.get(metadata_key, 0.0))
                parsed = _parse_float_sequence_text(value)
                if len(parsed) != 1:
                    raise ValueError(f"{PATH_LOCAL_COLUMN_LABELS.get(field, COLUMN_LABELS.get(field, field))} expects one number in Path view.")
                return float(parsed[0])

            if use_path_local_pose:
                for field, metadata_key in PATH_LOCAL_TABLE_FIELD_MAP.items():
                    path_local_metadata[metadata_key] = path_local_numeric_field(field, metadata_key)
                advanced[ELEMENT_ADVANCED_ATTR] = path_local_metadata
                start, end = self._element_block_for_index(self.rows, row_index)
                changed = any(
                    abs(float(path_local_metadata.get(metadata_key, 0.0)) - float(previous_metadata.get(metadata_key, 0.0))) > 1e-12
                    for metadata_key in PATH_LOCAL_TABLE_FIELD_MAP.values()
                )
                if changed or (start, end) not in path_local_pose_edits:
                    path_local_pose_edits[(start, end)] = dict(path_local_metadata)
                tilt_x_value = float(previous.tilt_x)
                tilt_y_value = float(previous.tilt_y)
                tilt_z_value = float(previous.tilt_z)
                desp_x_value = float(previous.desp_x)
                desp_y_value = float(previous.desp_y)
                desp_z_value = float(previous.desp_z)
            else:
                tilt_x_value = pose_numeric_field("tilt_x", "tilt_x")
                tilt_y_value = pose_numeric_field("tilt_y", "tilt_y")
                tilt_z_value = pose_numeric_field("tilt_z", "tilt_z")
                desp_x_value = pose_numeric_field("desp_x", "desp_x")
                desp_y_value = pose_numeric_field("desp_y", "desp_y")
                desp_z_value = pose_numeric_field("desp_z", "desp_z")
            rows[row_index] = (
                SurfaceRow(
                    label=str(row_index),
                    element=previous.element,
                    surface=surface,
                    name=text_field("name", "name"),
                    glass=text_field("glass", "glass"),
                    optimize_rc=previous.optimize_rc,
                    optimize_rc_bounds=previous.optimize_rc_bounds,
                    rc=numeric_field("rc", "rc"),
                    k=numeric_field("k", "k"),
                    axicon=numeric_field("axicon", "axicon"),
                    diff_ord=numeric_field("diff_ord", "diff_ord"),
                    grating_d=numeric_field("grating_d", "grating_d"),
                    grating_angle=numeric_field("grating_angle", "grating_angle"),
                    optimize_thickness=previous.optimize_thickness,
                    optimize_thickness_bounds=previous.optimize_thickness_bounds,
                    thickness=numeric_field("thickness", "thickness"),
                    diameter=numeric_field("diameter", "diameter"),
                    in_diameter=numeric_field("in_diameter", "in_diameter"),
                    drawing=previous.drawing,
                    extra_data=previous.extra_data,
                    uda=previous.uda,
                    advanced=advanced,
                    tilt_x=tilt_x_value,
                    tilt_y=tilt_y_value,
                    tilt_z=tilt_z_value,
                    desp_x=desp_x_value,
                    desp_y=desp_y_value,
                    desp_z=desp_z_value,
                    axis_move=numeric_field("axis_move", "axis_move"),
                )
            )
        self._propagate_element_pose_tolerances(rows, self.rows)
        self.rows = rows
        for (start, end), metadata in path_local_pose_edits.items():
            indices = list(range(max(1, start), min(end, len(self.rows) - 2) + 1))
            if indices:
                self._apply_path_local_pose_to_indices(indices, metadata)
