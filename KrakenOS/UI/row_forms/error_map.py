"""The Error Map row form (docs/design_qt_migration.md phase 3).

A row form with no editable fields: it holds a CANDIDATE error map, shows where it came from and
what it contains, and offers two actions -- Import (ask for a file, load it, validate it) and
Clear. Apply writes `Error_map` into the row's advanced settings, or removes it.

The actions ask for the file through the UI HOST, so the same builder serves the Tk dialog's
`filedialog` and the Qt dialog's `QFileDialog`.
"""
from __future__ import annotations

from pathlib import Path

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

TITLE = "Error Map"
NOTE = "Imports measured sag/departure as KrakenOS Error_map = [X, Y, Z, SPACE]."
FORMATS = (
    "CSV/TXT: x,y,z columns or a rectangular Z matrix. NPZ: X, Y, Z arrays plus optional SPACE. "
    "NPY: x/y/z columns, stacked X/Y/Z grids, or a Z matrix."
)
FILETYPES = [
    ("Error map files", "*.csv *.txt *.dat *.tsv *.npy *.npz"),
    ("Text files", "*.csv *.txt *.dat *.tsv"),
    ("NumPy files", "*.npy *.npz"),
    ("All files", "*"),
]
EMPTY = ("No Error_map will be stored on this surface.\n\n"
         "Click Import... to load measured data, or Apply to clear the current surface error map.")
STORED = "\n\nStored form: flattened X, Y, and Z sample lists plus one scalar SPACE pitch."


def model(owner):
    """The error map's model side, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.services import error_map_metadata as metadata

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        literal=held("error_map_literal", metadata._error_map_literal),
        summary=held("error_map_summary", metadata._error_map_summary),
        load=held("load_error_map_file", metadata._load_error_map_file),
        validate=held("validate_error_map", metadata._validate_error_map),
    )


def describe_map(parts, candidate) -> str:
    return EMPTY if candidate is None else (parts.summary(candidate) + STORED)


def build_error_map_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one surface's measured error map."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a surface row first.")
    row = owner.rows[row_index]
    if row.surface in {"Object", "Image"}:
        raise FormRefused(
            "Measured error maps apply to physical surfaces, not Object/Image rows.")

    parts = model(owner)
    current = dict(row.advanced or {}).get("Error_map")
    candidate = None
    if current is not None:
        try:
            candidate = parts.literal(current)
        except Exception:
            candidate = current

    form = RowForm(
        title=f"{TITLE} - S{row_index}: {row.name}",
        row_index=row_index,
        fields=(FormField("surface", "Surface", kind="static"),
                FormField("source", "Source", kind="static")),
        values={"surface": f"S{row_index}: {row.name}",
                "source": "Current row" if candidate is not None else "None"},
        summary=describe_map(parts, candidate),
        note=f"{NOTE}\n\n{FORMATS}",
        state={"error_map": candidate},
    )

    def validate(_values) -> list[str]:
        held = form.state.get("error_map")
        return [] if held is None else list(parts.validate(held))

    def describe(_values) -> str:
        return describe_map(parts, form.state.get("error_map"))

    def import_map(this_form, host) -> str:
        directory = getattr(owner, "attachment_dir", None)
        if directory is None or not Path(directory).exists():
            directory = getattr(owner, "project_root", Path.cwd())
        path_text = host.askopenfilename(title="Import Error Map",
                                         initialdir=str(directory), filetypes=FILETYPES)
        if not path_text:
            return "Import cancelled."
        path = Path(path_text).expanduser()
        try:
            loaded = parts.load(path)
            errors = parts.validate(loaded)
            if errors:
                raise ValueError(errors[0])
        except Exception as exc:
            raise FormRefused(f"Could not import {path.name}:\n\n{exc}") from exc
        this_form.state["error_map"] = loaded
        this_form.values["source"] = str(path)
        this_form.summary = describe_map(parts, loaded)
        return f"Loaded {path.name}. Validation passed."

    def clear_map(this_form, _host) -> str:
        this_form.state["error_map"] = None
        this_form.values["source"] = "None"
        this_form.summary = describe_map(parts, None)
        return "Error map will be cleared on Apply."

    def apply(_values) -> str:
        errors = validate(_values)
        if errors:
            raise FormRefused("Fix this error map before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        held = form.state.get("error_map")
        owner._begin_history_capture()
        advanced = dict(owner.rows[row_index].advanced or {})
        if held is None:
            advanced.pop("Error_map", None)
            status = (f"Cleared error map for S{row_index}: {owner.rows[row_index].name}. "
                      "Click Update.")
        else:
            normalized = parts.literal(held)
            advanced["Error_map"] = normalized
            status = (f"Updated error map for S{row_index}: {owner.rows[row_index].name} "
                      f"({parts.summary(normalized)}). Click Update.")
        owner.rows[row_index].advanced = advanced
        owner._sync_table()
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        owner.status_var.set(status)
        return status

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (FormAction("import", "Import...", import_map),
                    FormAction("clear", "Clear", clear_map))
    return form


build_error_map_form.TITLE = TITLE
