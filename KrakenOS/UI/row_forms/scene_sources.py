"""The Scene Source Manager record-list form (docs/design_qt_migration.md phase 3).

The seventh dialog family, and the first that edits a COLLECTION: scene sources are source
records, not KrakenOS surface rows, and the manager owns the whole list -- add one, add one from
the Source panel, duplicate, delete, apply them all, or throw them away and fall back to the
panel.

So `RowForm.records` (a `RecordList`) carries the master list, `form.state["specs"]` the working
copy and `form.state["index"]` the selection. Everything else is the row-form framework as it
already stood: ~30 fields, two choices that rewrite others (the model and the direction preset),
and two actions that ASK the model where to point (`scene_source_direction_to_row`,
`scene_source_place_at_row_standoff`).
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.row_forms.base import (FormAction, FormField, FormRefused, RecordList, RowForm)

TITLE = "Scene Source Manager"
NOTE = ("Scene sources are source records, not KrakenOS surface rows. Physical emitter models "
        "launch independent illumination; Pupil / field is a nonphysical reference that stays "
        "synchronized with the left Source panel.")
COLUMNS = ("ID", "Name", "Model", "Rays", "Origin XYZ", "Direction LMN")
VECTOR_KEYS = ("source_x", "source_y", "source_z", "source_l", "source_m", "source_n")


def model(owner):
    """The scene-source model, wherever the caller keeps it.

    Every one of these reaches the Tk dialog shell as a CONSTRUCTOR KWARG rather than as an
    editor attribute, so read it off the owner when it has it and fall back otherwise.
    """
    from types import SimpleNamespace

    from KrakenOS.UI import source_trace_helpers as helpers
    from KrakenOS.UI import scene_row_mapping as rows_module
    from KrakenOS.UI.trace_intent import SOURCE_MODEL_DEFAULT

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        model_values=tuple(held("source_model_values", helpers.SOURCE_MODEL_VALUES)),
        model_default=held("source_model_default", SOURCE_MODEL_DEFAULT),
        preset_values=tuple(held("source_direction_preset_values",
                                 helpers.SOURCE_DIRECTION_PRESET_VALUES)),
        angular_default=held("source_angular_weight_default",
                             helpers.SOURCE_ANGULAR_WEIGHT_DEFAULT),
        angular_values=tuple(held("source_angular_weight_values",
                                  helpers.SOURCE_ANGULAR_WEIGHT_VALUES)),
        row_order_default=held("source_row_order_default", rows_module.SOURCE_ROW_ORDER_DEFAULT),
        row_order_before=held("source_row_order_before_object",
                              rows_module.SOURCE_ROW_ORDER_BEFORE_OBJECT),
        row_order_after=held("source_row_order_after_object",
                             rows_module.SOURCE_ROW_ORDER_AFTER_OBJECT),
        normalize_row_order=held("normalize_source_row_order",
                                 rows_module.normalize_source_row_order),
        pupil_pattern_default=held("pupil_pattern_default", helpers.PUPIL_PATTERN_DEFAULT),
        pupil_pattern_values=tuple(held("pupil_pattern_values", helpers.PUPIL_PATTERN_VALUES)),
        gaussian_mode_default=held("gaussian_input_mode_default",
                                   helpers.GAUSSIAN_INPUT_MODE_DEFAULT),
        gaussian_mode_values=tuple(held("gaussian_input_mode_values",
                                        helpers.GAUSSIAN_INPUT_MODE_VALUES)),
        waist_side_default=held("gaussian_waist_side_default",
                                helpers.GAUSSIAN_WAIST_SIDE_DEFAULT),
        waist_side_values=tuple(held("gaussian_waist_side_values",
                                     helpers.GAUSSIAN_WAIST_SIDE_VALUES)),
    )


def _fields(parts, aim_choices) -> tuple:
    """The per-record form. Order is the Tk dialog's, so a user sees the same page."""
    number = "number"
    return (
        FormField("enabled", "Enabled", kind="bool"),
        FormField("physical", "Physical emitter", kind="bool"),
        FormField("model", "Model", kind="choice", choices=parts.model_values,
                  on_change=lambda form, value: _follow_model(form, value)),
        FormField("source_id", "Source ID", kind="text", width=16),
        FormField("name", "Name", kind="text", width=18),
        FormField("role", "Role", kind="text", width=16),
        FormField("ray_count", "Ray count", kind="int"),
        FormField("power", "Power", kind=number),
        FormField("wavelength", "Wavelength [um]", kind=number),
        FormField("radius", "Radius [mm]", kind=number),
        FormField("cone_deg", "Cone half-angle [deg]", kind=number),
        FormField("source_x", "Source X [mm]", kind=number),
        FormField("source_y", "Source Y [mm]", kind=number),
        FormField("source_z", "Source Z [mm]", kind=number),
        FormField("seed", "Random seed", kind="int"),
        FormField("source_l", "Direction L", kind=number),
        FormField("source_m", "Direction M", kind=number),
        FormField("source_n", "Direction N", kind=number),
        FormField("angular_weight", "Angular weight", kind="choice",
                  choices=parts.angular_values),
        FormField("direction_preset", "Direction preset", kind="choice",
                  choices=parts.preset_values,
                  on_change=lambda form, value: _apply_direction_preset(form, value)),
        FormField("aim_target", "Aim direction at row", kind="choice", editable=True,
                  choices=tuple(aim_choices)),
        FormField("placement_standoff", "Placement standoff [mm]", kind=number),
        FormField("waist_radius", "GB waist [mm]", kind=number),
        FormField("waist_offset", "GB waist offset [mm]", kind=number),
        FormField("m2", "GB M2", kind=number),
        FormField("gaussian_input_mode", "GB input mode", kind="choice",
                  choices=parts.gaussian_mode_values),
        FormField("gaussian_beam_diameter", "GB beam dia [mm]", kind=number),
        FormField("gaussian_full_divergence", "GB full div [mrad]", kind=number),
        FormField("gaussian_waist_side", "GB waist side", kind="choice",
                  choices=parts.waist_side_values),
        FormField("pupil_pattern", "Pupil pattern", kind="choice",
                  choices=parts.pupil_pattern_values),
        FormField("pupil_rad", "Pupil radial samples", kind="int"),
        FormField("pupil_theta", "Pupil angular samples", kind="int"),
        FormField("row_order", "Visible row order", kind="choice",
                  choices=(parts.row_order_after, parts.row_order_before),
                  hint="after_object = Object, Source(s), Image"),
    )


def _follow_model(form, value: str) -> str:
    """The Pupil / field reference is never a physical emitter -- the model decides, not the view."""
    parts = form.state["parts"]
    if str(value).strip() == parts.model_default:
        form.values["physical"] = "false"
        form.values["role"] = "pupil_field_reference"
        return "Pupil / field is the nonphysical imaging reference; role set accordingly."
    if str(form.values.get("role", "")).strip() in {"", "pupil_field_reference"}:
        form.values["physical"] = "true"
        form.values["role"] = "illumination"
    return ""


def _apply_direction_preset(form, label: str) -> str:
    owner = form.state["owner"]
    vector = owner._source_direction_preset_vector(label)
    if vector is None:
        return ""
    for key, value in zip(("source_l", "source_m", "source_n"), vector):
        form.values[key] = owner._format_source_direction_component(float(value))
    return (f"Direction preset applied: LMN=({float(vector[0]):.4g}, {float(vector[1]):.4g}, "
            f"{float(vector[2]):.4g}). Click Save Source before Apply.")


def build_scene_source_manager_form(
    owner,
    selected_source_id: "str | None" = None,
    *,
    aim_row_index: "int | None" = None,
    aim_face_id: str = "",
) -> RowForm:
    """The manager for the whole scene-source list."""
    parts = model(owner)
    specs = [dict(spec) for spec in owner._normalize_scene_source_specs(
        getattr(owner, "layout_scene_source_specs", []) or [])]
    if not specs:
        specs = [owner._scene_source_spec_from_current_panel()]
    specs = owner._dedupe_scene_source_ids(specs)

    index = 0
    if selected_source_id:
        for position, spec in enumerate(specs):
            if str(spec.get("source_id", "")) == str(selected_source_id):
                index = position
                break

    aim_choices = list(owner._scene_source_aim_target_choices())
    requested = ""
    if aim_row_index is not None:
        try:
            requested = owner._scene_source_target_choice_for(int(aim_row_index), aim_face_id)
        except Exception:
            requested = ""

    form = RowForm(
        title=TITLE,
        row_index=index,
        fields=_fields(parts, aim_choices),
        note=NOTE,
        state={"owner": owner, "parts": parts, "specs": specs, "index": index},
        records=RecordList(columns=COLUMNS, rows=_record_rows, select=_select_record),
    )
    form.values = {
        "aim_target": requested or (aim_choices[-1] if aim_choices else ""),
        "placement_standoff": "50.0",
        "row_order": parts.normalize_row_order(
            getattr(owner, "layout_scene_row_order", parts.row_order_default)),
    }
    _select_record(form, index)

    def collect(values: dict) -> dict:
        return _spec_from_values(form, values)

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        spec = collect(values)
        return (f"{spec['source_id']} ({spec['model']}), {spec['ray_count']} rays, "
                f"origin ({spec['source_x']:.4g}, {spec['source_y']:.4g}, "
                f"{spec['source_z']:.4g}) mm")

    def apply(values: dict) -> str:
        _save_current(form, values)
        specs_now = form.state["specs"]
        owner._set_scene_source_specs(
            specs_now,
            row_order=str(values.get("row_order", parts.row_order_default)),
            record_history=True,
            status=f"Applied {len(specs_now)} scene source(s). Click Update.",
        )
        return f"Applied {len(specs_now)} scene source(s). Click Update."

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (
        FormAction("save", "Save Source", lambda f, _host: _save_action(f)),
        FormAction("add", "Add", lambda f, _host: _add(f)),
        FormAction("add_panel", "Add From Source Panel", lambda f, _host: _add_from_panel(f)),
        FormAction("duplicate", "Duplicate", lambda f, _host: _duplicate(f)),
        FormAction("delete", "Delete", lambda f, _host: _delete(f)),
        FormAction("aim", "Aim Direction At Row", lambda f, _host: _aim_at_row(f)),
        FormAction("place", "Place Origin At Standoff", lambda f, _host: _place_at_standoff(f)),
        FormAction("panel_only", "Use Source Panel Only", lambda f, _host: _clear_to_panel(f)),
    )
    return form


# ---- the record list -------------------------------------------------------------------------
def _record_rows(form) -> tuple:
    owner = form.state["owner"]
    wavelength = owner._current_wavelength()
    rows = []
    for position, spec in enumerate(form.state["specs"]):
        source = owner._scene_source_from_spec(spec, position, wavelength=wavelength)
        ox, oy, oz = np.asarray(source.origin, dtype=float).reshape(-1)[:3]
        dl, dm, dn = np.asarray(source.direction, dtype=float).reshape(-1)[:3]
        rows.append((
            str(source.source_id),
            str(source.name),
            str(source.model),
            str(source.ray_count),
            f"{ox:.4g}, {oy:.4g}, {oz:.4g}",
            f"{dl:.4g}, {dm:.4g}, {dn:.4g}",
        ))
    return tuple(rows)


def _select_record(form, index: int) -> str:
    """Load one record into the form -- the model's own defaults, then the record over them."""
    owner = form.state["owner"]
    parts = form.state["parts"]
    specs = form.state["specs"]
    if not specs:
        return "No scene sources; Add one or use the Source panel."
    index = min(max(int(index), 0), len(specs) - 1)
    form.state["index"] = index
    form.row_index = index
    spec = dict(specs[index])
    values = dict(owner._default_scene_source_spec(index))
    values.update(spec)

    def vector(vector_keys, component_keys, defaults):
        if all(key in spec for key in component_keys):
            return np.asarray([owner._source_spec_float(spec, key, float(defaults[position]))
                               for position, key in enumerate(component_keys)], dtype=float)
        return owner._source_spec_vector(values, vector_keys, component_keys, defaults)

    # `_default_scene_source_spec` carries no wavelength, so a freshly added source used to load
    # with the field BLANK and refuse its own first save ("Wavelength expects a number."). The Tk
    # dialog initialised its variable to the scene wavelength and only lost it on load; keep that
    # intent -- a new source starts at the wavelength the scene is using.
    if not str(values.get("wavelength", "") or "").strip():
        values["wavelength"] = owner._current_wavelength()

    origin = vector(("origin", "source_xyz", "xyz"), ("source_x", "source_y", "source_z"),
                    (values["source_x"], values["source_y"], values["source_z"]))
    direction = vector(("direction", "source_lmn", "lmn"), ("source_l", "source_m", "source_n"),
                       (values["source_l"], values["source_m"], values["source_n"]))
    for key, value in zip(VECTOR_KEYS, list(origin[:3]) + list(direction[:3])):
        values[key] = float(value)

    for field in form.fields:
        if field.key in {"aim_target", "placement_standoff", "row_order", "direction_preset"}:
            continue
        if field.kind == "bool":
            raw = values.get(field.key, True)
            truthy = (raw.strip().lower() not in {"0", "false", "no", "off", "disabled"}
                      if isinstance(raw, str) else bool(raw))
            form.values[field.key] = "true" if truthy else "false"
        else:
            form.values[field.key] = "" if values.get(field.key) is None else str(
                values.get(field.key, ""))

    # snap every readonly choice onto a value it actually offers
    for key, allowed, default in (
        ("model", parts.model_values, "Collimated disk source"),
        ("angular_weight", parts.angular_values, parts.angular_default),
        ("pupil_pattern", parts.pupil_pattern_values, parts.pupil_pattern_default),
        ("gaussian_input_mode", parts.gaussian_mode_values, parts.gaussian_mode_default),
        ("gaussian_waist_side", parts.waist_side_values, parts.waist_side_default),
    ):
        if allowed and str(form.values.get(key, "")).strip() not in allowed:
            form.values[key] = default
    form.values["direction_preset"] = owner._source_direction_preset_label(
        (form.values["source_l"], form.values["source_m"], form.values["source_n"]))
    message = (f"Editing {spec.get('source_id', f'source:{index}')} - click Save Source before "
               "Apply.")
    form.summary = message
    return message


# ---- parsing ---------------------------------------------------------------------------------
def _number(values: dict, key: str, label: str, *, minimum: "float | None" = None) -> float:
    try:
        value = float(str(values.get(key, "")).strip())
    except Exception as exc:
        raise FormRefused(f"{label} expects a number.") from exc
    if not np.isfinite(value):
        raise FormRefused(f"{label} must be finite.")
    if minimum is not None and value < minimum:
        raise FormRefused(f"{label} must be >= {minimum:g}.")
    return float(value)


def _integer(values: dict, key: str, label: str, *, minimum: int = 1) -> int:
    return max(int(minimum), int(round(_number(values, key, label, minimum=float(minimum)))))


def _truthy(values: dict, key: str) -> bool:
    return str(values.get(key, "")).strip().lower() in ("1", "true", "yes", "on")


def _spec_from_values(form, values: dict) -> dict:
    owner = form.state["owner"]
    parts = form.state["parts"]
    source_id = str(values.get("source_id", "")).strip()
    if not source_id:
        raise FormRefused("Source ID cannot be empty.")
    source_model = str(values.get("model", "")).strip()
    if source_model not in parts.model_values:
        raise FormRefused("Choose a valid source model.")
    physical = _truthy(values, "physical")
    role = str(values.get("role", "")).strip()
    if source_model == parts.model_default:
        physical = False
        role = "pupil_field_reference"
    elif not role or role == "pupil_field_reference":
        role = "illumination"
    dl = _number(values, "source_l", "Direction L")
    dm = _number(values, "source_m", "Direction M")
    dn = _number(values, "source_n", "Direction N")
    if float(np.linalg.norm([dl, dm, dn])) <= 1e-12:
        raise FormRefused("Direction vector cannot be zero.")
    spec = {
        "source_id": source_id,
        "name": str(values.get("name", "")).strip() or source_id,
        "enabled": _truthy(values, "enabled"),
        "physical": physical,
        "role": role,
        "model": source_model,
        "ray_count": _integer(values, "ray_count", "Ray count", minimum=1),
        "power": _number(values, "power", "Power", minimum=0.0),
        "wavelength": _number(values, "wavelength", "Wavelength", minimum=1e-12),
        "radius": _number(values, "radius", "Radius", minimum=0.0),
        "cone_deg": min(_number(values, "cone_deg", "Cone half-angle", minimum=0.0), 89.9),
        "seed": _integer(values, "seed", "Random seed", minimum=0),
        "source_x": _number(values, "source_x", "Source X"),
        "source_y": _number(values, "source_y", "Source Y"),
        "source_z": _number(values, "source_z", "Source Z"),
        "source_l": dl,
        "source_m": dm,
        "source_n": dn,
        "angular_weight": str(values.get("angular_weight", "")).strip() or parts.angular_default,
        "waist_radius": _number(values, "waist_radius", "GB waist", minimum=1e-12),
        "waist_offset": _number(values, "waist_offset", "GB waist offset"),
        "m2": _number(values, "m2", "GB M2", minimum=1e-12),
    }
    if spec["angular_weight"] not in parts.angular_values:
        spec["angular_weight"] = parts.angular_default

    # bugs/0402: the folded-in imaging controls are carried through, parsed TOLERANTLY -- a blank
    # Gaussian/pupil field on an unrelated model must never refuse the save.
    def optional_float(key: str, default: float) -> float:
        try:
            value = float(str(values.get(key, "")).strip())
            return float(value) if np.isfinite(value) else float(default)
        except Exception:
            return float(default)

    def optional_int(key: str, default: int) -> int:
        try:
            return max(0, int(round(float(str(values.get(key, "")).strip()))))
        except Exception:
            return int(default)

    spec["pupil_pattern"] = (str(values.get("pupil_pattern", "")).strip()
                             or parts.pupil_pattern_default)
    spec["pupil_rad"] = optional_int("pupil_rad", 3)
    spec["pupil_theta"] = optional_int("pupil_theta", 6)
    spec["gaussian_input_mode"] = (str(values.get("gaussian_input_mode", "")).strip()
                                   or parts.gaussian_mode_default)
    spec["gaussian_beam_diameter"] = optional_float("gaussian_beam_diameter", 0.0)
    spec["gaussian_full_divergence"] = optional_float("gaussian_full_divergence", 0.0)
    spec["gaussian_waist_side"] = (str(values.get("gaussian_waist_side", "")).strip()
                                   or parts.waist_side_default)
    return {str(key): owner._scene_source_setting_value(value) for key, value in spec.items()}


# ---- the collection actions -------------------------------------------------------------------
def _save_current(form, values: dict) -> dict:
    specs = form.state["specs"]
    index = form.state["index"]
    if not (0 <= index < len(specs)):
        return {}
    spec = _spec_from_values(form, values)
    others = {str(item.get("source_id", "")) for position, item in enumerate(specs)
              if position != index}
    if str(spec.get("source_id", "")) in others:
        raise FormRefused("Source ID must be unique.")
    specs[index] = spec
    return spec


def _save_action(form) -> str:
    spec = _save_current(form, dict(form.values))
    if not spec:
        return "No scene source selected."
    return f"Saved {spec['source_id']} in the manager. Click Apply to update the layout."


def _add(form) -> str:
    owner = form.state["owner"]
    _save_current(form, dict(form.values))
    form.state["specs"].append(owner._default_scene_source_spec(len(form.state["specs"])))
    return _select_record(form, len(form.state["specs"]) - 1)


def _add_from_panel(form) -> str:
    owner = form.state["owner"]
    _save_current(form, dict(form.values))
    specs = form.state["specs"]
    specs.append(owner._scene_source_spec_from_current_panel(
        source_id=f"source:{len(specs)}", name=f"Source {len(specs) + 1}"))
    return _select_record(form, len(specs) - 1)


def _duplicate(form) -> str:
    owner = form.state["owner"]
    specs = form.state["specs"]
    index = form.state["index"]
    if not (0 <= index < len(specs)):
        raise FormRefused("Select a scene source to duplicate.")
    _save_current(form, dict(form.values))
    duplicate = dict(specs[index])
    duplicate["source_id"] = f"{duplicate.get('source_id', f'source:{index}')}_copy"
    duplicate["name"] = f"{duplicate.get('name', f'Source {index + 1}')} Copy"
    specs.insert(index + 1, duplicate)
    specs[:] = owner._dedupe_scene_source_ids(specs)
    return _select_record(form, index + 1)


def _delete(form) -> str:
    specs = form.state["specs"]
    index = form.state["index"]
    if not (0 <= index < len(specs)):
        raise FormRefused("Select a scene source to delete.")
    removed = str(specs[index].get("source_id", ""))
    del specs[index]
    if not specs:
        form.state["index"] = 0
        form.summary = f"Deleted {removed}; no scene sources left."
        return form.summary
    return _select_record(form, min(index, len(specs) - 1))


def _aim_target(form) -> tuple:
    owner = form.state["owner"]
    text = str(form.values.get("aim_target", "") or "").strip()
    if not text:
        raise FormRefused("Choose a target row for source aiming.")
    prefix = text.split(":", 1)[0].strip()
    row_text, _sep, face_id = prefix.partition("/")
    try:
        row_index = int(row_text)
    except Exception as exc:
        raise FormRefused("Choose a valid target row for source aiming.") from exc
    if not (0 <= row_index < len(owner.rows)):
        raise FormRefused("Target row is out of range.")
    return row_index, str(face_id or "").strip()


def _aim_at_row(form) -> str:
    owner = form.state["owner"]
    row_index, face_id = _aim_target(form)
    values = dict(form.values)
    try:
        result = owner.scene_source_direction_to_row(
            {key: _number(values, key, key) for key in ("source_x", "source_y", "source_z")},
            row_index,
            face_id=face_id,
        )
    except FormRefused:
        raise
    except Exception as exc:
        raise FormRefused(str(exc)) from exc
    for key in ("source_l", "source_m", "source_n"):
        form.values[key] = owner._format_source_direction_component(float(result[key]))
    form.values["direction_preset"] = owner._source_direction_preset_label(
        (form.values["source_l"], form.values["source_m"], form.values["source_n"]))
    tx, ty, tz = np.asarray(result.get("target_point", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
    return (f"Aimed source at {result.get('target_label', result.get('row_name', ''))}: "
            f"target=({tx:.4g}, {ty:.4g}, {tz:.4g}) mm, "
            f"distance={float(result.get('distance_mm', 0.0)):.4g} mm. "
            "Click Save Source before Apply.")


def _place_at_standoff(form) -> str:
    owner = form.state["owner"]
    row_index, face_id = _aim_target(form)
    values = dict(form.values)
    standoff = _number(values, "placement_standoff", "Placement standoff")
    if standoff <= 0.0:
        raise FormRefused("Placement standoff must be a positive number.")
    try:
        result = owner.scene_source_place_at_row_standoff(
            {key: _number(values, key, key) for key in ("source_l", "source_m", "source_n")},
            row_index,
            standoff,
            face_id=face_id,
        )
    except FormRefused:
        raise
    except Exception as exc:
        raise FormRefused(str(exc)) from exc
    for key in VECTOR_KEYS:
        form.values[key] = owner._format_source_direction_component(float(result[key]))
    form.values["direction_preset"] = owner._source_direction_preset_label(
        (form.values["source_l"], form.values["source_m"], form.values["source_n"]))
    tx, ty, tz = np.asarray(result.get("target_point", (0.0, 0.0, 0.0)), dtype=float).reshape(3)
    return (f"Placed source {float(result.get('distance_mm', 0.0)):.4g} mm before "
            f"{result.get('target_label', result.get('row_name', ''))}: "
            f"target=({tx:.4g}, {ty:.4g}, {tz:.4g}) mm. Click Save Source before Apply.")


def _clear_to_panel(form) -> str:
    owner = form.state["owner"]
    message = "Scene sources cleared; using the Source panel fallback. Click Update."
    owner._set_scene_source_specs(
        [],
        row_order=str(form.values.get("row_order", form.state["parts"].row_order_default)),
        record_history=True,
        status=message,
    )
    form.state["specs"] = []
    form.state["close_after"] = True
    return message


build_scene_source_manager_form.TITLE = TITLE
