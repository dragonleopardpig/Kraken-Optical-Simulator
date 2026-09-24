"""The Advanced Surface row form (docs/design_qt_migration.md phase 3).

Every KrakenOS surface attribute the main table does not show, in tabs: the shape parameters
(with the conic-k optimisation switch), one tab per attribute group, and the custom sag/UDA pair.
Each override is a Python LITERAL; one the reader cannot parse back is shown but not editable,
so it can never be mangled by a round trip.

The groups, the attribute names, the literal reader/writer, the float-sequence parser, the
variable registry and the validator all already exist -- this module is what a dialog needs on
top, and both toolkits use it.
"""
from __future__ import annotations

from dataclasses import asdict

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Advanced Surface"
NOTE = ("Overrides are KrakenOS attributes written as Python literals. An empty box removes the "
        "override. A value this editor cannot read back is shown but locked, so it is never "
        "rewritten by accident.")
SHAPE_TAB = "Shape Params"
CUSTOM_TAB = "Custom Surface"
OPTIMIZE_KEY = "optimize_k"
BOUNDS_KEY = "k_bounds"


def model(owner):
    """The advanced-surface model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor as editor_module
    from KrakenOS.UI.services import advanced_surface_attrs
    from KrakenOS.UI.services.advanced_surface_validation import _validate_advanced_surface_inputs

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        shape_fields=tuple(held("advanced_row_shape_fields",
                                editor_module.ADVANCED_ROW_SHAPE_FIELDS)),
        groups=tuple(held("advanced_surface_field_groups",
                          advanced_surface_attrs.ADVANCED_SURFACE_FIELD_GROUPS)),
        attr_names=tuple(held("advanced_surface_attr_names",
                              advanced_surface_attrs.ADVANCED_SURFACE_ATTR_NAMES)),
        registry=dict(held("variable_registry", editor_module.VARIABLE_REGISTRY)),
        labels=dict(held("column_labels", editor_module.COLUMN_LABELS)),
        literal_text=held("literal_editor_text", editor_module._literal_editor_text),
        parse_literal=held("parse_literal_editor_text", editor_module._parse_literal_editor_text),
        format_sequence=held("format_float_sequence", editor_module._format_float_sequence),
        parse_sequence=held("parse_float_sequence_text",
                            editor_module._parse_float_sequence_text),
        validate_advanced=held("validate_advanced_surface_inputs",
                               _validate_advanced_surface_inputs),
    )


def _truthy(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def build_advanced_surface_form(owner, row_index: "int | None" = None) -> RowForm:
    """Every advanced attribute of one surface row, in tabs."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a surface row first.")
    parts = model(owner)
    row = owner.rows[row_index]
    advanced = dict(row.advanced or {})

    fields: list[FormField] = []
    values: dict[str, str] = {}
    editable_attrs: dict[str, bool] = {}

    # ---- the shape parameters ------------------------------------------------------------------
    shape_editable = row.surface not in {"Object", "Image"}
    for name, label, hint in parts.shape_fields:
        fields.append(FormField(name, label, kind="number", group=SHAPE_TAB, hint=hint,
                                enabled=shape_editable, width=18))
        values[name] = owner._format_table_float(float(getattr(row, name)))

    k_spec = parts.registry.get("k")
    k_supported = bool(k_spec is not None and k_spec.is_supported(row))
    k_enabled = bool(k_supported and owner._variable_enabled_for_row(row, k_spec))
    k_bounds = k_spec.get_bounds(row) if k_supported else None
    fields.append(FormField(OPTIMIZE_KEY, "Optimize conic k", kind="bool", group=SHAPE_TAB,
                            enabled=k_supported,
                            hint="Writes native Var/VarBounds without putting k back in the main "
                                 "table."))
    values[OPTIMIZE_KEY] = "true" if k_enabled else "false"
    fields.append(FormField(BOUNDS_KEY, "Conic k bounds", kind="text", group=SHAPE_TAB, width=22,
                            enabled=k_supported,
                            hint="Optional two-value bounds, for example -2, 0."))
    values[BOUNDS_KEY] = parts.format_sequence(k_bounds) if k_bounds else ""

    # ---- one tab per attribute group ------------------------------------------------------------
    def attribute_field(attr: str, label: str, value, group: str, *, allowed: bool = True) -> None:
        text, literal_editable = parts.literal_text(value) if value != "" else ("", True)
        editable = bool(allowed and literal_editable)
        editable_attrs[attr] = editable
        fields.append(FormField(attr, label, kind="text", group=group, width=32, enabled=editable,
                                hint=f"KrakenOS attr {attr}"
                                     + ("" if editable else " (not a literal this editor can "
                                                            "read back -- locked)")))
        values[attr] = text

    for group_name, group_fields in parts.groups:
        for attr, label in group_fields:
            attribute_field(attr, label, advanced.get(attr, ""), group_name)

    attribute_field("ExtraData", "Custom sag data",
                    "" if owner._is_default_extra_data(row.extra_data) else row.extra_data,
                    CUSTOM_TAB)
    attribute_field("UDA", "Useful diameter area",
                    "" if owner._is_default_uda(row.uda) else row.uda, CUSTOM_TAB)

    form = RowForm(title=f"{TITLE} - S{row_index}: {row.name}", row_index=row_index,
                   fields=tuple(fields), values=values, note=NOTE)

    def collect(form_values: dict):
        """The Tk dialog's own collect: shape floats, literal overrides, then the k variable."""
        new_advanced = dict(advanced)
        new_k = float(row.k)
        new_axicon = float(row.axicon)
        if shape_editable:
            for name, _label, _hint in parts.shape_fields:
                text = str(form_values.get(name, "")).strip()
                try:
                    value = float(text) if text else 0.0
                except ValueError as exc:
                    raise FormRefused(
                        f"{parts.labels.get(name, name)} expects a number.") from exc
                if name == "k":
                    new_k = value
                elif name == "axicon":
                    new_axicon = value

        for attr in parts.attr_names:
            if not editable_attrs.get(attr, False):
                continue
            text = str(form_values.get(attr, "")).strip()
            if not text:
                new_advanced.pop(attr, None)
                continue
            try:
                new_advanced[attr] = parts.parse_literal(text)
            except Exception as exc:
                raise FormRefused(f"{attr}: {exc}") from exc

        new_extra = row.extra_data
        new_uda = row.uda
        if editable_attrs.get("ExtraData", False):
            parsed = parts.parse_literal(str(form_values.get("ExtraData", "")))
            new_extra = 0.0 if parsed is None else parsed
        if editable_attrs.get("UDA", False):
            parsed = parts.parse_literal(str(form_values.get("UDA", "")))
            new_uda = "None" if parsed is None else parsed

        if k_supported:
            shape_row = type(row)(**asdict(row))
            shape_row.advanced = dict(new_advanced)
            shape_row.k = float(new_k)
            wants = _truthy(form_values.get(OPTIMIZE_KEY, "false"))
            k_spec.set_enabled(shape_row, wants)
            bounds_text = str(form_values.get(BOUNDS_KEY, "")).strip()
            if wants and bounds_text:
                numbers = parts.parse_sequence(bounds_text)
                if len(numbers) < 2:
                    raise FormRefused("Conic k optimization bounds need two numbers, "
                                      "for example -2, 0.")
                lower, upper = float(numbers[0]), float(numbers[1])
                if lower >= upper:
                    raise FormRefused("Conic k optimization bounds must be increasing.")
                k_spec.set_bounds(shape_row, (lower, upper))
            else:
                k_spec.set_bounds(shape_row, None)
            new_advanced = dict(shape_row.advanced or {})

        return new_advanced, new_extra, new_uda, new_k, new_axicon

    def check(form_values: dict) -> tuple[list[str], list[str]]:
        try:
            new_advanced, new_extra, new_uda, _k, _axicon = collect(form_values)
        except FormRefused as exc:
            return [str(exc)], []
        errors, warnings = parts.validate_advanced(new_advanced, new_extra, new_uda)
        return list(errors), list(warnings)

    def validate(form_values: dict) -> list[str]:
        return check(form_values)[0]

    def describe(form_values: dict) -> str:
        errors, warnings = check(form_values)
        if errors:
            return errors[0]
        return f"Validation warning: {warnings[0]}" if warnings else "Validation passed."

    def apply(form_values: dict) -> str:
        new_advanced, new_extra, new_uda, new_k, new_axicon = collect(form_values)
        errors, warnings = check(form_values)
        if errors:
            raise FormRefused("Fix these values before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        if warnings:
            owner.append_debug("Advanced surface validation warnings: " + " | ".join(warnings))
        owner._begin_history_capture()
        target = owner.rows[row_index]
        target.advanced = new_advanced
        target.extra_data = new_extra
        target.uda = new_uda
        target.k = new_k
        target.axicon = new_axicon
        owner._sync_table()
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        status = (f"Updated advanced attributes for S{row_index}: "
                  f"{owner.rows[row_index].name}. Click Update.")
        owner.status_var.set(status)
        return status

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.summary = describe(form.values)
    form.state = {"editable_attrs": editable_attrs, "k_supported": k_supported}
    return form


build_advanced_surface_form.TITLE = TITLE
