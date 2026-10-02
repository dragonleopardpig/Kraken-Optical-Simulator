"""Lens-drawing surface properties: one session, rendered by Tk and by Qt (bugs/0945).

The ISO-style fabrication properties of every lens surface (`lens_drawing_properties`), edited
before a PDF lens drawing is exported or on their own. The state -- which surfaces, the text in
every field, the status line, whether the export may go on -- and every action (apply, clear,
save / load the JSON sidecar) live here. A view only lays the fields out, copies what the user
typed in with `set_value`, and closes when `closed` turns true.

It was a 240-line Tk window with the logic inside its closures (`panels/main_lens_drawing_dialogs`):
the Qt shell could neither show it nor export a drawing, which waits on its answer.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from KrakenOS.UI.lens_drawing_export import identify_elements
from KrakenOS.UI.lens_drawing_properties import (
    DRAWING_PROPERTIES_ATTR,
    DRAWING_PROPERTY_FIELDS,
    apply_surface_properties_payload,
    drawing_properties,
    format_property_value,
    normalize_drawing_properties,
    surface_properties_payload,
    validate_drawing_properties,
)
from KrakenOS.UI.surface_table_model import SurfaceRow
from KrakenOS.UI.uihost import host_of

TITLE = "Lens Drawing Surface Properties"
#: what its message boxes are titled -- the Tk window's own wording
MESSAGE_TITLE = "Lens Drawing Properties"
NOTE = ("Enter ISO-style fabrication drawing properties for each optical surface. Blank fields keep drawing "
        "placeholders. Values are saved in each row's DrawingProperties advanced metadata and can also be "
        "saved/loaded as an editable JSON sidecar before PDF export.")
FIXED_COLUMNS = ("Surface", "Name", "Type", "Material", "Rc", "Dia", "CT")
READY = "Blank fields are allowed and become drawing placeholders."
NO_LENSES = "No lens elements found in the surface table."
JSON_FILETYPES = [("JSON", "*.json"), ("All files", "*")]
JSON_NAME = "lens_drawing_properties.json"


def lens_surface_indices(rows) -> list[int]:
    """The rows a lens drawing describes: both faces of every lens element, in element order."""
    groups, _info = identify_elements(rows)
    indices: list[int] = []
    for group in groups:
        for element in group.elements:
            for index in (getattr(element, "left_row_index", -1), getattr(element, "right_row_index", -1)):
                if 0 <= index < len(rows) and index not in indices:
                    indices.append(index)
    return indices


def has_lens_elements(rows) -> bool:
    groups, _info = identify_elements(rows)
    return bool(groups)


class LensDrawingPropertiesSession:
    """The dialog's state and actions. `owner` is the editor (or a panel forwarding to it)."""

    def __init__(self, owner, *, for_export: bool = False, screenshot_dir=None) -> None:
        self.owner = owner
        self.for_export = bool(for_export)
        self.screenshot_dir = Path(screenshot_dir) if screenshot_dir is not None else Path.cwd()
        self.surface_indices = lens_surface_indices(owner.rows)
        self.values: dict[int, dict[str, str]] = {}
        for index in self.surface_indices:
            props = drawing_properties(owner.rows[index])
            self.values[index] = {field.key: format_property_value(props.get(field.key, ""))
                                  for field in DRAWING_PROPERTY_FIELDS}
        self.status = READY
        #: True once the caller may go on: properties applied, or "continue without changes"
        self.result_ok = False
        #: True once the dialog should go away
        self.closed = False
        self.listeners: list = []

    # ---- what a view shows ------------------------------------------------------------------------
    @staticmethod
    def fields():
        return DRAWING_PROPERTY_FIELDS

    def headings(self) -> list[str]:
        return list(FIXED_COLUMNS) + [field.label for field in DRAWING_PROPERTY_FIELDS]

    def fixed_cells(self, row_index: int) -> list[str]:
        row = self.owner.rows[row_index]
        fmt = self.owner._format_table_float
        return [f"S{row_index}", str(row.name or row.surface), str(row.surface), str(row.glass),
                fmt(float(row.rc)), fmt(float(row.diameter)), fmt(float(row.thickness))]

    def buttons(self) -> list[tuple[str, str]]:
        """(label, method) of the footer, right to left as the Tk window packs them."""
        common = [("Load JSON...", "ask_load_json"), ("Save JSON...", "ask_save_json"), ("Clear", "clear_all")]
        if self.for_export:
            return common + [("Continue Without Changes", "continue_without_changes"),
                             ("Apply && Continue", "apply_and_close"), ("Cancel Export", "cancel")]
        return common + [("Apply && Close", "apply_and_close"), ("Apply", "apply_only"),
                         ("Close", "continue_without_changes")]

    def _changed(self) -> None:
        for listener in list(self.listeners):
            listener()

    # ---- edits --------------------------------------------------------------------------------------
    def set_value(self, row_index: int, key: str, text: str) -> None:
        if row_index in self.values and key in self.values[row_index]:
            self.values[row_index][key] = str(text)

    def collect_updates(self) -> dict[int, dict[str, object]]:
        """The typed values as normalised properties per row; ValueError names the bad surface."""
        updates: dict[int, dict[str, object]] = {}
        for row_index, row_values in self.values.items():
            raw = {key: text.strip() for key, text in row_values.items() if str(text).strip()}
            props = normalize_drawing_properties(raw)
            errors = validate_drawing_properties(props)
            if errors:
                raise ValueError(f"S{row_index}: " + " ".join(errors))
            updates[row_index] = props
        return updates

    def _refuse(self, exc: Exception, *, prefix: str = "", parent=None) -> None:
        self.status = str(exc)
        self._changed()
        host_of(self.owner).showerror(MESSAGE_TITLE, f"{prefix}{exc}", parent=parent)

    # ---- actions ------------------------------------------------------------------------------------
    def apply(self, *, close: bool, parent=None) -> bool:
        try:
            updates = self.collect_updates()
        except ValueError as exc:
            self._refuse(exc, parent=parent)
            return False
        owner = self.owner
        owner._begin_history_capture()
        for row_index, props in updates.items():
            row = owner.rows[row_index]
            row.advanced = dict(row.advanced or {})
            if props:
                row.advanced[DRAWING_PROPERTIES_ATTR] = props
            else:
                row.advanced.pop(DRAWING_PROPERTIES_ATTR, None)
        owner._sync_table()
        owner._commit_history_capture()
        self.result_ok = True
        if close:
            self.closed = True
        else:
            self.status = "Applied drawing properties to the surface table."
        self._changed()
        return True

    def apply_only(self, parent=None) -> bool:
        return self.apply(close=False, parent=parent)

    def apply_and_close(self, parent=None) -> bool:
        return self.apply(close=True, parent=parent)

    def continue_without_changes(self, parent=None) -> None:
        self.result_ok = True
        self.closed = True
        self._changed()

    def cancel(self, parent=None) -> None:
        self.closed = True
        self._changed()

    def clear_all(self, parent=None) -> None:
        for row_values in self.values.values():
            for key in row_values:
                row_values[key] = ""
        self.status = "Cleared dialog fields. Click Apply to remove saved DrawingProperties."
        self._changed()

    def save_payload(self) -> dict:
        """The JSON sidecar: the table's surfaces with the properties AS TYPED (validated)."""
        updates = self.collect_updates()
        payload = surface_properties_payload(self.owner.rows, self.surface_indices)
        for record in payload.get("surfaces", []):
            if isinstance(record, dict):
                record["properties"] = updates.get(int(record.get("surface_index", -1)), {})
        return payload

    def save_json(self, path, parent=None) -> bool:
        try:
            payload = self.save_payload()
        except ValueError as exc:
            self._refuse(exc, parent=parent)
            return False
        try:
            Path(path).write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
        except Exception as exc:
            self._refuse(exc, prefix="Could not save JSON:\n\n", parent=parent)
            return False
        self.status = f"Saved editable surface properties: {Path(path).name}"
        self._changed()
        return True

    def ask_save_json(self, parent=None) -> bool:
        try:
            self.collect_updates()
        except ValueError as exc:
            self._refuse(exc, parent=parent)
            return False
        path = host_of(self.owner).asksaveasfilename(
            title="Save Lens Drawing Surface Properties", initialdir=str(self.screenshot_dir),
            initialfile=JSON_NAME, defaultextension=".json", filetypes=JSON_FILETYPES, parent=parent)
        return bool(path) and self.save_json(path, parent=parent)

    def load_json(self, path, parent=None) -> bool:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            temp_rows = [SurfaceRow(**asdict(row)) for row in self.owner.rows]
            apply_surface_properties_payload(temp_rows, payload)
        except Exception as exc:
            self._refuse(exc, prefix="Could not load JSON:\n\n", parent=parent)
            return False
        for row_index, row_values in self.values.items():
            props = drawing_properties(temp_rows[row_index])
            for key in row_values:
                row_values[key] = format_property_value(props.get(key, ""))
        self.status = (f"Loaded editable surface properties from {Path(path).name}; "
                       "click Apply to save them in the layout.")
        self._changed()
        return True

    def ask_load_json(self, parent=None) -> bool:
        path = host_of(self.owner).askopenfilename(
            title="Load Lens Drawing Surface Properties", initialdir=str(self.screenshot_dir),
            filetypes=JSON_FILETYPES, parent=parent)
        return bool(path) and self.load_json(path, parent=parent)
