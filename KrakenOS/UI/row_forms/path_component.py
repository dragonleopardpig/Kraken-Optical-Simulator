"""The Path Component placement row form (docs/design_qt_migration.md phase 3).

Insert a component into a beam-splitter arm, or onto a traced BRANCH_PATH: pick what it is, say
how far along the path it sits and how wide it is, and give it a local decentre and tilt. The
editor derives the global Tilt/Decenter pose from the path frame.

The component choice does not just pick a type -- it CHANGES WHAT THE NEXT FIELD MEANS. For a
thin lens the parameter is a focal length; for a refracting surface it is a radius of curvature;
for a mirror it is a mirror radius; for a detector or an aperture there is no parameter at all,
and the glass is fixed. That is `RowForm.labels`, the live half of `FormField.label`, alongside
`locked` for the fields the choice turns off.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Add Path Component"
TRACED_TITLE = "Add Traced Path Component"
PARAMETRIC = ("Thin lens", "Refractive surface", "Mirror", "Object Target")
LOCAL_KEYS = ("local_decenter_x", "local_decenter_y", "local_tilt_x", "local_tilt_y",
              "local_tilt_z")
LOCAL_LABELS = ("Local X offset [mm]", "Local Y offset [mm]", "Local tilt X [deg]",
                "Local tilt Y [deg]", "Local tilt Z [deg]")


def model(owner):
    """The path-component model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor as editor_module

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        types=tuple(editor_module.PATH_COMPONENT_TYPES),
        detector=editor_module.PATH_COMPONENT_DETECTOR,
        aperture=editor_module.PATH_COMPONENT_APERTURE,
        thin_lens=editor_module.PATH_COMPONENT_THIN_LENS,
        refractive=editor_module.PATH_COMPONENT_REFRACTIVE_SURFACE,
        mirror=editor_module.PATH_COMPONENT_MIRROR,
        object_target=editor_module.PATH_COMPONENT_OBJECT_TARGET,
        splitter_surface=editor_module.BEAM_SPLITTER_SURFACE,
        short_error=held("short_error_message", editor_module._short_error_message),
    )


def build_path_component_form(owner, splitter_index: int = -1, arm_role: str = "",
                              *, default_component: "str | None" = None,
                              branch_path: str = "") -> RowForm:
    """The form for one component on one path."""
    parts = model(owner)
    path = str(branch_path or "").strip()
    traced = bool(path)
    if traced:
        try:
            owner._branch_path_frame(path)
        except Exception as exc:
            raise FormRefused(parts.short_error(exc)) from exc
        role = "Path"
        title = TRACED_TITLE
        default_diameter = 25.0
        description = (
            f"Insert a component on traced path {owner._branch_path_compact_detail(path)}. "
            "The editor derives the global Tilt/Decenter pose from the latest traced "
            "BRANCH_PATH segment and preserves exact branch_path metadata for nested splitter "
            "filtering.")
        opening = ("Distance is measured from the last splitter hit in: "
                   f"{owner._branch_path_detail(path)}")
    else:
        if not (0 <= int(splitter_index) < len(owner.rows)) or \
                owner.rows[int(splitter_index)].surface != parts.splitter_surface:
            raise FormRefused("Right-click a Beam Splitter row first.")
        role = str(arm_role).strip()
        if role not in {"Transmit", "Reflect"}:
            raise FormRefused(f"Unsupported path: {arm_role}")
        title = f"Add {role} Path Component"
        default_diameter = max(float(owner.rows[int(splitter_index)].diameter) * 2.0, 25.0)
        description = (
            f"Insert a component in the {role.lower()} path. The editor calculates the global "
            "Tilt/Decenter pose from the splitter path frame and preserves path metadata.")
        opening = "Distance is measured along the central transmitted/reflected path."

    form = RowForm(
        title=title,
        row_index=max(int(splitter_index), 0),
        fields=(
            FormField("component", "Component", kind="choice", choices=parts.types,
                      on_change=lambda current, value: _follow_component(current, value,
                                                                         reset=True)),
            FormField("distance", "Distance from splitter [mm]", kind="number", width=16),
            FormField("diameter", "Clear diameter [mm]", kind="number", width=16),
            FormField("parameter", "Parameter", kind="number", width=16),
            FormField("glass", "Glass", kind="text", width=16),
            *(FormField(key, label, kind="number", width=16)
              for key, label in zip(LOCAL_KEYS, LOCAL_LABELS)),
        ),
        note=description,
        state={"owner": owner, "parts": parts, "path": path, "traced": traced, "role": role,
               "splitter_index": int(splitter_index)},
    )
    form.values = {
        "component": owner._normalize_path_component_type(
            default_component if default_component is not None else parts.detector),
        "distance": "60",
        "diameter": owner._format_table_float(default_diameter),
        "parameter": "0",
        "glass": "BK7",
        **{key: "0" for key in LOCAL_KEYS},
    }
    form.summary = opening
    _follow_component(form, form.values["component"], reset=True)

    def validate(values: dict) -> list[str]:
        try:
            _parse(form, values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        kind, distance, diameter, parameter, glass, _local = _parse(form, values)
        detail = f", {form.label_for('parameter')} {parameter:.6g}" if parameter is not None \
            else ""
        return f"{kind} at {distance:.6g} mm, {diameter:.6g} mm clear{detail}, glass {glass}"

    def apply(values: dict) -> str:
        return _insert(form, values)

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


def _follow_component(form, value: str, *, reset: bool = False) -> str:
    """What the next two fields MEAN depends on what the component is."""
    owner = form.state["owner"]
    parts = form.state["parts"]
    kind = owner._normalize_path_component_type(value)
    # keep the form's own value in step with the choice, so a caller that drives on_change
    # directly (a guard, a script) sees the same form a view would
    form.values["component"] = kind
    if reset:
        if kind == parts.thin_lens:
            form.values["parameter"] = "100"
        elif kind == parts.refractive:
            form.values["parameter"] = "100"
            form.values["glass"] = str(form.values.get("glass", "")).strip() or "BK7"
        else:
            form.values["parameter"] = "0"

    if kind == parts.thin_lens:
        form.labels["parameter"] = "Focal length [mm]"
        form.labels["glass"] = "Glass (not used)"
        form.lock("parameter", locked=False)
        form.lock("glass", locked=True)
        message = ("Thin Lens stores focal length in the Rc table column, matching KrakenOS "
                   "Thin_Lens.")
    elif kind == parts.refractive:
        form.labels["parameter"] = "Radius of curvature [mm]"
        form.labels["glass"] = "Glass"
        form.lock("parameter", "glass", locked=False)
        message = ("A refractive surface is a single native Standard surface; add a second "
                   "surface for thickness.")
    elif kind in {parts.mirror, parts.object_target}:
        form.labels["parameter"] = f"{kind} radius [mm] (0 = flat)"
        form.labels["glass"] = "Glass (MIRROR)"
        form.lock("parameter", locked=False)
        form.lock("glass", locked=True)
        message = ("Object Target marks the object location but currently reflects specularly "
                   "as a proxy." if kind == parts.object_target else
                   "A flat normal mirror reflects back along the path; edit Tilt for a fold "
                   "mirror.")
    else:
        form.labels["parameter"] = "Parameter (not used)"
        form.labels["glass"] = "Glass (AIR)"
        form.lock("parameter", "glass", locked=True)
        message = ("Detector planes are tagged as Detector path metadata for detector "
                   "analyses." if kind == parts.detector else
                   "Aperture stops use the native Aperture row type and path metadata.")
    form.summary = message
    return message


def _positive(values: dict, key: str, label: str) -> float:
    try:
        value = float(str(values.get(key, "")).strip())
    except Exception as exc:
        raise FormRefused("Distance and diameter must be numbers.") from exc
    if not np.isfinite(value) or value <= 0.0:
        raise FormRefused(f"{label} must be positive.")
    return value


def _parse(form, values: dict) -> tuple:
    owner = form.state["owner"]
    parts = form.state["parts"]
    kind = owner._normalize_path_component_type(values.get("component", ""))
    distance = _positive(values, "distance", "Distance")
    diameter = _positive(values, "diameter", "Diameter")
    parameter = None
    if kind in {parts.thin_lens, parts.refractive, parts.mirror, parts.object_target}:
        try:
            parameter = float(str(values.get("parameter", "")).strip() or "0")
        except Exception as exc:
            raise FormRefused("Component parameter must be numeric.") from exc
        if not np.isfinite(parameter):
            raise FormRefused("Component parameter must be finite.")
        if kind == parts.thin_lens and abs(parameter) <= 1e-12:
            raise FormRefused("Thin lens focal length cannot be zero.")
    try:
        local = tuple(float(str(values.get(key, "")).strip() or "0") for key in LOCAL_KEYS)
    except Exception as exc:
        raise FormRefused("Local offset and tilt values must be numeric.") from exc
    if not all(np.isfinite(value) for value in local):
        raise FormRefused("Local offset and tilt values must be finite.")
    return kind, distance, diameter, parameter, str(values.get("glass", "")).strip() or "BK7", local


def _insert(form, values: dict) -> str:
    owner = form.state["owner"]
    parts = form.state["parts"]
    kind, distance, diameter, parameter, glass, local = _parse(form, values)
    path = form.state["path"]
    try:
        if form.state["traced"]:
            insert_index = owner._default_insert_index_for_arm_key(
                owner._arm_key_from_branch_path(path))
            component = owner._path_component_row_for_branch_path(
                path, kind, distance, diameter, parameter_mm=parameter, glass=glass,
                insert_at=insert_index, local_decenter_x=local[0], local_decenter_y=local[1],
                local_tilt_x=local[2], local_tilt_y=local[3], local_tilt_z=local[4])
        else:
            insert_index = max(1, len(owner.rows) - 1)
            component = owner._path_component_row_for_arm(
                form.state["splitter_index"], form.state["role"], kind, distance, diameter,
                parameter_mm=parameter, glass=glass, insert_at=insert_index,
                local_decenter_x=local[0], local_decenter_y=local[1], local_tilt_x=local[2],
                local_tilt_y=local[3], local_tilt_z=local[4])
    except Exception as exc:
        raise FormRefused(parts.short_error(exc)) from exc
    owner._begin_history_capture()
    owner.rows.insert(insert_index, component)
    owner._normalize_special_rows()
    owner._sync_table()
    owner._select_table_indices([insert_index], focus_index=insert_index)
    owner._commit_history_capture()
    owner._mark_plot_update_pending()
    placement = (f"traced path {owner._branch_path_compact_detail(path)}"
                 if form.state["traced"] else f"{form.state['role'].lower()} path")
    message = (f"Inserted {component.name} at {distance:.6g} mm in the {placement}. "
               "Click Update.")
    owner.status_var.set(message)
    return message


build_path_component_form.TITLE = TITLE
