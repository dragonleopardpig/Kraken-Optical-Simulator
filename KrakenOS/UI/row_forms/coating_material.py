"""The Coating / Material row form (docs/design_qt_migration.md phase 3).

The most tangled of the row dialogs, and the one that finished the framework:

- the coating table is a **Python literal** edited as text, with a preset list that REWRITES it;
- the metal index and the metal-catalog list are linked -- choosing a catalog sets the index --
  and an action loads another CSV, growing the list;
- validation is the shared advanced-surface validator, which reports warnings as well as errors.

Presets, the literal reader/writer and the catalog directory live on `layout_editor`; the catalog
helpers in `services/catalog_metadata.py`; the validator in
`services/advanced_surface_validation.py`. This module is what a dialog needs on top.
"""
from __future__ import annotations

from pathlib import Path
from pprint import pformat

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

TITLE = "Coating / Material"
NOTE = ("Coating = [R, A, W, THETA]. R/A rows follow THETA; columns follow wavelength.\n\n"
        "Metal index for MIRROR Fresnel mode. Explicit coating tables override Fresnel values.")
UNEDITABLE = "<non-literal coating object>"
EMPTY_COATING = [[], [], [], []]


def model(owner):
    """The coating model, wherever the caller keeps it (see row_forms.beam_splitter)."""
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor as editor_module
    from KrakenOS.UI.services import catalog_metadata
    from KrakenOS.UI.services.advanced_surface_validation import _validate_advanced_surface_inputs

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        presets=dict(held("coating_presets", editor_module.COATING_PRESETS)),
        preset_names=tuple(held("coating_preset_names", editor_module.COATING_PRESET_NAMES)),
        catalog_dir=Path(held("metal_catalog_dir", editor_module.METAL_CATALOG_DIR)),
        literal_text=held("literal_editor_text", editor_module._literal_editor_text),
        parse_literal=held("parse_literal_editor_text", editor_module._parse_literal_editor_text),
        normalize_specs=held("normalize_metal_catalog_specs",
                             catalog_metadata._normalize_metal_catalog_specs),
        entries=held("metal_catalog_entries", catalog_metadata._metal_catalog_entries),
        type_for_path=held("metal_catalog_type_for_path",
                           catalog_metadata._metal_catalog_type_for_path),
        validate_advanced=held("validate_advanced_surface_inputs",
                               _validate_advanced_surface_inputs),
    )


def catalog_labels(parts, catalogs) -> tuple[str, ...]:
    """"0: Aluminium (al.csv)" for every loaded catalog, as the Tk dialog lists them."""
    return tuple(f"{index}: {catalog['name']} ({Path(str(catalog['path'])).name})"
                 for index, catalog in enumerate(parts.entries(catalogs)))


def preset_for_value(owner, value) -> str:
    """Which preset this coating equals, or "Custom"."""
    finder = getattr(owner, "_coating_preset_for_value", None)
    if finder is not None:
        try:
            return str(finder(value))
        except Exception:
            pass
    return "Custom"


def build_coating_material_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one surface's coating and metal index."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a surface row first.")
    parts = model(owner)
    row = owner.rows[row_index]
    advanced = dict(row.advanced or {})
    coating_value = advanced.get("Coating", EMPTY_COATING)
    coating_text, editable = parts.literal_text(coating_value)
    if not editable:
        coating_text = UNEDITABLE

    catalogs = parts.normalize_specs(getattr(owner, "metal_catalogs", []) or [])
    labels = catalog_labels(parts, catalogs)
    met_index = 0
    try:
        met_index = int(float(advanced.get("CoatingMet", 0) or 0))
    except (TypeError, ValueError):
        met_index = 0

    form = RowForm(
        title=f"{TITLE} - S{row_index}: {row.name}",
        row_index=row_index,
        values={
            "preset": preset_for_value(owner, coating_value),
            "coating": coating_text,
            "coating_met": str(met_index),
            "metal_catalog": labels[met_index] if 0 <= met_index < len(labels) else
                             (labels[0] if labels else ""),
        },
        note=NOTE,
        state={"catalogs": list(catalogs)},
        choices={"metal_catalog": labels},
    )

    def use_preset(this_form, name: str) -> str:
        """A preset REWRITES the coating table -- the Tk combobox did the same."""
        if name not in parts.presets:
            return ""
        this_form.values["coating"] = pformat(parts.presets[name], width=100)
        return f"Coating table replaced with the {name} preset."

    def use_catalog(this_form, label: str) -> str:
        """Choosing a catalog sets the metal index it is listed under."""
        try:
            this_form.values["coating_met"] = str(int(str(label).split(":", 1)[0]))
        except (TypeError, ValueError):
            return ""
        return f"Metal index {this_form.values['coating_met']} selected."

    form.fields = (
        FormField("preset", "Preset", kind="choice",
                  choices=("Custom", *parts.preset_names), width=28, on_change=use_preset,
                  hint="Fills the coating table below."),
        FormField("coating", "Coating table", kind="textarea", height=10,
                  hint="Coating = [R, A, W, THETA] as a Python literal."),
        FormField("coating_met", "CoatingMet", kind="int", width=16,
                  hint="Metal index for MIRROR Fresnel mode."),
        FormField("metal_catalog", "Metal catalog", kind="choice", width=42,
                  on_change=use_catalog, hint="Selecting one sets CoatingMet."),
    )

    def collect(values: dict) -> tuple[list, int]:
        text = str(values.get("coating", "")).strip()
        if text == UNEDITABLE:
            raise FormRefused("This surface holds a coating object that is not a Python literal; "
                              "it cannot be edited here.")
        coating = parts.parse_literal(text) if text else list(EMPTY_COATING)
        raw = str(values.get("coating_met", "")).strip() or "0"
        try:
            number = float(raw)
        except ValueError as exc:
            raise FormRefused(f"CoatingMet must be an integer metal index: {exc}") from exc
        if number != int(number):
            raise FormRefused("CoatingMet must be an integer metal index.")
        return coating, int(number)

    def check(values: dict) -> tuple[list[str], list[str]]:
        try:
            coating, coating_met = collect(values)
        except FormRefused as exc:
            return [str(exc)], []
        candidate = dict(advanced)
        candidate["Coating"] = coating
        candidate["CoatingMet"] = coating_met
        errors, warnings = parts.validate_advanced(candidate, row.extra_data, row.uda)
        errors = list(errors)
        catalogs_now = form.state["catalogs"]
        if coating_met >= len(parts.entries(catalogs_now)):
            errors.append(f"CoatingMet index {coating_met} has no loaded metal catalog; "
                          "load a CSV first.")
        for catalog in parts.normalize_specs(catalogs_now):
            path = Path(str(catalog["path"])).expanduser()
            if not path.exists():
                errors.append(f"Metal catalog does not exist: {path}")
        return errors, list(warnings)

    def validate(values: dict) -> list[str]:
        return check(values)[0]

    def describe(values: dict) -> str:
        errors, warnings = check(values)
        if errors:
            return errors[0]
        return f"Validation warning: {warnings[0]}" if warnings else "Validation passed."

    def load_csv(this_form, host) -> str:
        path_text = host.askopenfilename(title="Load Metal CSV",
                                         initialdir=str(parts.catalog_dir),
                                         filetypes=[("CSV files", "*.csv"), ("All files", "*")])
        if not path_text:
            return "Load cancelled."
        path = Path(path_text).expanduser()
        spec = {"name": path.stem, "path": str(path),
                "type": parts.type_for_path(path)}
        this_form.state["catalogs"] = parts.normalize_specs(
            [*this_form.state["catalogs"], spec])
        entries = parts.entries(this_form.state["catalogs"])
        selected = next((index for index, entry in enumerate(entries)
                         if str(entry["path"]) == str(path)
                         and str(entry["name"]).lower() == path.stem.lower()),
                        len(entries) - 1)
        this_form.choices["metal_catalog"] = catalog_labels(parts, this_form.state["catalogs"])
        if this_form.choices["metal_catalog"]:
            this_form.values["metal_catalog"] = this_form.choices["metal_catalog"][selected]
            this_form.values["coating_met"] = str(selected)
        return (f"Loaded metal catalog candidate: {path.name}. "
                "Click Apply to save it with this layout.")

    def apply(values: dict) -> str:
        coating, coating_met = collect(values)
        errors, warnings = check(values)
        if errors:
            raise FormRefused("Fix these values before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        new_advanced = dict(owner.rows[row_index].advanced or {})
        if coating == EMPTY_COATING:
            new_advanced.pop("Coating", None)
        else:
            new_advanced["Coating"] = coating
        if coating_met == 0:
            new_advanced.pop("CoatingMet", None)
        else:
            new_advanced["CoatingMet"] = coating_met
        if warnings:
            owner.append_debug("Coating validation warnings: " + " | ".join(warnings))
        owner._begin_history_capture()
        owner.metal_catalogs = parts.normalize_specs(form.state["catalogs"])
        owner.rows[row_index].advanced = new_advanced
        owner._sync_table()
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        status = (f"Updated coating/material for S{row_index}: "
                  f"{owner.rows[row_index].name}. Click Update.")
        owner.status_var.set(status)
        return status

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.summary = describe(form.values)
    form.actions = (FormAction("load_csv", "Load CSV...", load_csv),)
    return form


build_coating_material_form.TITLE = TITLE
