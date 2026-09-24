"""The scene-source edit row form (docs/design_qt_migration.md phase 3).

bugs/0363's "general 3D source element" UX: right-click a source in the Scene Components browser
-> Edit Source... and set its name, origin, emit direction, emitting size, cone half-angle, ray
count and power. Apply writes through `update_scene_source_spec` -- the same path the
seat-on-face glue uses -- so the glyph, the illumination volume and the trace all follow.

A coaxial illuminator gets two more fields (bugs/0401): the illumination-edge profile and its
width. They are conditional on the SPEC, so the builder adds them or does not -- which is the
model deciding what the dialog contains, not the view.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

TITLE = "Edit Source"
NOTE = ("Origin and direction are world millimetres; the emitting width and height are the "
        "source's own rectangle. Apply re-applies the scene sources, so the glyph, the "
        "illumination volume and the trace follow immediately.")
NUMERIC = (("source_x", "Origin X (mm)"), ("source_y", "Origin Y (mm)"),
           ("source_z", "Origin Z (mm)"), ("source_l", "Direction L"),
           ("source_m", "Direction M"), ("source_n", "Direction N"),
           ("width", "Width (mm)"), ("height", "Height (mm)"),
           ("cone_deg", "Cone half-angle (deg)"), ("power", "Power"))


def model(owner):
    """The scene-source model, wherever the caller keeps it."""
    from types import SimpleNamespace

    from KrakenOS.UI.panels.open3d_source_edit_dialog import _spec_for_source, _vec3
    from KrakenOS.UI.scene_source_analysis import (COAXIAL_EDGE_PROFILES,
                                                   COAXIAL_ILLUMINATOR_KEY,
                                                   coaxial_edge_penumbra_mm,
                                                   coaxial_edge_profile_and_width)

    return SimpleNamespace(
        spec_for=_spec_for_source,
        vector=_vec3,
        edge_profiles=tuple(COAXIAL_EDGE_PROFILES),
        coaxial_key=COAXIAL_ILLUMINATOR_KEY,
        edge_penumbra=coaxial_edge_penumbra_mm,
        edge_profile_and_width=coaxial_edge_profile_and_width,
    )


def build_scene_source_edit_form(owner, source_id: "str | None" = None, **_kwargs) -> RowForm:
    """The form for one scene source's geometry."""
    parts = model(owner)
    if not source_id:
        raise FormRefused("Pick a scene source to edit.")
    spec = parts.spec_for(owner, str(source_id))
    if spec is None:
        raise FormRefused(f"Edit Source: {source_id} not found.")

    origin = parts.vector(spec, "origin", ("source_x", "source_y", "source_z"), (0.0, 0.0, 0.0))
    direction = parts.vector(spec, "direction", ("source_l", "source_m", "source_n"),
                             (0.0, 0.0, 1.0))

    def number(key, fallback):
        try:
            return float(spec.get(key, fallback))
        except Exception:
            return float(fallback)

    coaxial = bool(spec.get(parts.coaxial_key, False))
    profile, edge_width = parts.edge_profile_and_width(spec)

    fields = [FormField("name", "Name", kind="text", width=20)]
    fields.extend(FormField(key, label, kind="number", width=18) for key, label in NUMERIC)
    fields.insert(11, FormField("ray_count", "Ray count", kind="int", width=18))
    if coaxial:
        # bugs/0401: only a coaxial illuminator has an illumination EDGE to shape
        fields.append(FormField("coaxial_edge_profile", "Illumination edge", kind="choice",
                                choices=parts.edge_profiles))
        fields.append(FormField("coaxial_edge_width", "Edge width (mm)", kind="number",
                                width=18))

    form = RowForm(
        title=f"{TITLE} - {spec.get('name', source_id)}",
        row_index=0,
        fields=tuple(fields),
        note=NOTE,
        state={"owner": owner, "parts": parts, "source_id": str(source_id),
               "coaxial": coaxial},
    )
    form.values = {
        "name": str(spec.get("name", source_id)),
        "source_x": f"{origin[0]:.4g}", "source_y": f"{origin[1]:.4g}",
        "source_z": f"{origin[2]:.4g}",
        "source_l": f"{direction[0]:.6g}", "source_m": f"{direction[1]:.6g}",
        "source_n": f"{direction[2]:.6g}",
        "width": f"{2.0 * number('radius_x', number('radius', 5.0)):.4g}",
        "height": f"{2.0 * number('radius_y', number('radius', 5.0)):.4g}",
        "cone_deg": f"{number('cone_deg', 30.0):.4g}",
        "ray_count": str(int(number("ray_count", 2000))),
        "power": f"{number('power', 1.0):.4g}",
    }
    if coaxial:
        form.values["coaxial_edge_profile"] = str(profile)
        form.values["coaxial_edge_width"] = str(edge_width)
    form.summary = f"Editing {spec.get('name', source_id)} ({source_id})."

    def validate(values: dict) -> list[str]:
        try:
            _update_from_values(form, values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        update = _update_from_values(form, values)
        return (f"{update['name']}: {2.0 * update['radius_x']:.4g} x "
                f"{2.0 * update['radius_y']:.4g} mm at "
                f"({update['source_x']:.4g}, {update['source_y']:.4g}, "
                f"{update['source_z']:.4g}) mm")

    def apply(values: dict) -> str:
        update = _update_from_values(form, values)
        note = (f"; edge {update['coaxial_edge_profile']}"
                if "coaxial_edge_profile" in update else "")
        message = (f"Updated scene source {form.state['source_id']} "
                   f"({2.0 * update['radius_x']:.4g} x {2.0 * update['radius_y']:.4g} mm"
                   f"{note}).")
        if not owner.update_scene_source_spec(form.state["source_id"], update, status=message):
            raise FormRefused("Source not found any more -- was it deleted?")
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


def _update_from_values(form, values: dict) -> dict:
    """The spec update this form writes -- the same keys the seat-on-face glue writes."""
    parts = form.state["parts"]
    try:
        numbers = {key: float(str(values.get(key, "")).strip())
                   for key, _label in NUMERIC}
        rays = max(1, int(float(str(values.get("ray_count", "")).strip())))
    except Exception as exc:
        raise FormRefused(
            "Enter numeric values (direction may be any non-zero vector).") from exc
    direction = np.asarray([numbers["source_l"], numbers["source_m"], numbers["source_n"]],
                           dtype=float)
    norm = float(np.linalg.norm(direction))
    if norm <= 1e-9:
        raise FormRefused("Direction must be a non-zero vector.")
    if numbers["width"] <= 0.0 or numbers["height"] <= 0.0:
        raise FormRefused("Width and height must be positive.")
    unit = direction / norm
    update = {
        "name": str(values.get("name", "")).strip() or form.state["source_id"],
        "origin": [numbers["source_x"], numbers["source_y"], numbers["source_z"]],
        "direction": [float(unit[0]), float(unit[1]), float(unit[2])],
        "source_x": numbers["source_x"], "source_y": numbers["source_y"],
        "source_z": numbers["source_z"],
        "source_l": float(unit[0]), "source_m": float(unit[1]), "source_n": float(unit[2]),
        "radius_x": 0.5 * numbers["width"], "radius_y": 0.5 * numbers["height"],
        "cone_deg": numbers["cone_deg"], "ray_count": rays, "power": numbers["power"],
    }
    if form.state["coaxial"]:
        profile = str(values.get("coaxial_edge_profile", "")).strip()
        update["coaxial_edge_profile"] = profile
        update["coaxial_penumbra_mm"] = parts.edge_penumbra(
            profile, str(values.get("coaxial_edge_width", "")).strip())
    return update


build_scene_source_edit_form.TITLE = TITLE
