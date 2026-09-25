"""The Surface Shape Builder row form (docs/design_qt_migration.md phase 3, with the phase-6
matplotlib seam).

Asphere and Zernike coefficients, an ExtraData preset, a UDA preset, a mask preset and an
optical CAD/STL path -- everything that makes a surface a SHAPE rather than a radius. Its
explanation is a PLOT: an imshow of the sag/departure map with a colorbar beside the
aperture/UDA/mask footprint, redrawn as the values are typed, so a coefficient list is judged by
the surface it makes rather than by reading it back.

`FormPreview` could not carry that -- it draws polygons and text. `FormFigure` can: the model
draws into a figure the view supplies, and matplotlib already has a canvas for both toolkits.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.row_forms.base import (FormAction, FormField, FormFigure, FormRefused, RowForm)

TITLE = "Surface Shape Builder"
NOTE = ("Everything that makes this surface a shape rather than a radius. The plot is the "
        "sag/departure map beside the aperture footprint, redrawn as you type -- a coefficient "
        "list is judged by the surface it makes.")
EXTRA_PRESETS = ("None", "xy_cosines", "radial_sine", "micro_lens_array")
UDA_PRESETS = ("Current", "None", "Circle", "Hexagon", "Square")
UDA_SIDES = {"Circle": 48, "Hexagon": 6, "Square": 4}
MASK_PRESETS = ("None", "Ronchi mask", "Spider mask")


def model(owner):
    """The shape model, wherever the caller keeps it.

    Every one of these reaches the Tk dialog shell as a CONSTRUCTOR KWARG rather than as an
    editor attribute, so read it off the owner when it has it and fall back otherwise.
    """
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor as editor_module
    from KrakenOS.UI.custom_surfaces import encode_custom_surface_value
    from KrakenOS.UI.services.advanced_surface_validation import (
        _validate_advanced_surface_inputs)

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        encode=held("encode_custom_surface_value", encode_custom_surface_value),
        parse_literal=held("parse_literal_editor_text",
                           editor_module._parse_literal_editor_text),
        validate=held("validate_advanced_surface_inputs", _validate_advanced_surface_inputs),
        mesh_path=held("optical_solid_mesh_path_from_source",
                       editor_module._optical_solid_mesh_path_from_source),
        short_error=held("short_error_message", editor_module._short_error_message),
        filetypes=held("optical_solid_filetypes", (("All files", "*"),)),
        attachment_dir=held("attachment_dir", Path.cwd()),
    )


def build_surface_shape_form(owner, row_index: "int | None" = None) -> RowForm:
    """The shape builder for one surface row."""
    parts = model(owner)
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a surface row first.")
    row = owner.rows[row_index]
    if row.surface in {"Object", "Image"}:
        raise FormRefused("Shape builders apply to physical surfaces, not Object/Image rows.")

    advanced = dict(row.advanced or {})
    diameter = max(float(row.diameter), 1.0)
    extra_preset, extra_params = "None", "[8.0, 0.02]"
    encoded = parts.encode(row.extra_data)
    if isinstance(encoded, dict) and str(encoded.get("preset", "")).strip():
        from pprint import pformat

        extra_preset = str(encoded["preset"]).strip()
        extra_params = pformat(encoded.get("params", []), width=80)
    mask_summary = owner._mask_preset_summary(advanced.get("Mask_Shape"))
    solid = advanced.get("OpticalSolidSourcePath") or advanced.get("Solid_3d_stl")

    form = RowForm(
        title=f"{TITLE} - S{row_index}: {row.name}",
        row_index=row_index,
        fields=(
            FormField("aspher", "Asphere coeffs", kind="text", width=34),
            FormField("znk", "Zernike coeffs", kind="text", width=34),
            FormField("extra_preset", "ExtraData preset", kind="choice", choices=EXTRA_PRESETS),
            FormField("extra_params", "Extra params", kind="text", width=24),
            FormField("uda_preset", "UDA preset", kind="choice", choices=UDA_PRESETS),
            FormField("uda_radius", "UDA radius", kind="number", width=14),
            FormField("uda_rotation", "UDA rotation", kind="number", width=14),
            FormField("mask_preset", "Mask preset", kind="choice", choices=MASK_PRESETS),
            FormField("mask_pitch", "Mask pitch/width", kind="number", width=14),
            FormField("mask_extent", "Mask extent", kind="number", width=14),
            FormField("stl", "Optical CAD/STL", kind="text", width=28),
        ),
        note=NOTE,
        state={"owner": owner, "parts": parts, "row": row, "row_index": row_index,
               "advanced": advanced, "uda": row.uda},
        figure=FormFigure(width=7.2, height=5.4, draw=_draw),
    )
    form.values = {
        "aspher": owner._short_numeric_list(advanced.get("AspherData", []), 12),
        "znk": owner._short_numeric_list(advanced.get("ZNK", []), 12),
        "extra_preset": extra_preset,
        "extra_params": extra_params,
        "uda_preset": "Current" if not owner._is_default_uda(row.uda) else "None",
        "uda_radius": f"{max(diameter * 0.45, 1.0):.6g}",
        "uda_rotation": "0.0",
        "mask_preset": mask_summary if mask_summary in {"Ronchi mask", "Spider mask"} else "None",
        "mask_pitch": f"{max(diameter / 20.0, 0.25):.6g}",
        "mask_extent": f"{max(diameter * 1.1, 1.0):.6g}",
        "stl": str(solid) if solid not in (None, "None") else "",
    }
    form.summary = "Preview shows sag/custom surface and aperture/UDA/mask footprint."

    def validate(values: dict) -> list[str]:
        try:
            candidate = _candidate(form, values)
        except FormRefused as exc:
            return [str(exc)]
        errors, _warnings = parts.validate(*candidate)
        return list(errors)

    def describe(values: dict) -> str:
        next_advanced, next_extra, next_uda = _candidate(form, values)
        _errors, warnings = parts.validate(next_advanced, next_extra, next_uda)
        shapes = [name for name in ("AspherData", "ZNK", "Mask_Shape", "Solid_3d_stl")
                  if next_advanced.get(name)]
        note = f" ({warnings[0]})" if warnings else ""
        return f"{', '.join(shapes) or 'plain surface'}{note}"

    def apply(values: dict) -> str:
        next_advanced, next_extra, next_uda = _candidate(form, values)
        errors, warnings = parts.validate(next_advanced, next_extra, next_uda)
        stl_text = str(next_advanced.get("Solid_3d_stl", "") or "").strip()
        if stl_text:
            # STEP/IGES is meshed to a cached STL here, not while typing
            try:
                mesh_path, source_path, source_format = parts.mesh_path(Path(stl_text))
                next_advanced["Solid_3d_stl"] = str(mesh_path)
                if source_path is not None:
                    next_advanced["OpticalSolidSourcePath"] = str(source_path)
                    next_advanced["OpticalSolidSourceFormat"] = source_format
                else:
                    next_advanced.pop("OpticalSolidSourcePath", None)
                    next_advanced.pop("OpticalSolidSourceFormat", None)
            except Exception as exc:
                errors.append(f"Optical solid import failed: {parts.short_error(exc)}")
        if errors:
            raise FormRefused("Fix these values before applying:\n\n"
                              + "\n".join(f"- {error}" for error in errors))
        if warnings:
            owner.append_debug("Surface shape builder warnings: " + " | ".join(warnings))
        owner._begin_history_capture()
        owner.rows[row_index].advanced = next_advanced
        owner.rows[row_index].extra_data = next_extra
        owner.rows[row_index].uda = next_uda
        owner._sync_table()
        owner._select_table_row(row_index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        message = (f"Updated shape/custom/mask settings for S{row_index}: "
                   f"{owner.rows[row_index].name}. Click Update.")
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (FormAction("browse_stl", "Browse CAD/STL...", _browse_stl),)
    return form


# ---- the candidate ---------------------------------------------------------------------------
def _numeric_list(form, text: str, label: str) -> "list[float] | None":
    parts = form.state["parts"]
    stripped = str(text).strip()
    if not stripped:
        return None
    value = parts.parse_literal(stripped)
    try:
        array = np.asarray(value, dtype=float).ravel()
    except Exception as exc:
        raise FormRefused(f"{label} must be a numeric list: {exc}") from exc
    if array.size == 0:
        return None
    if not np.all(np.isfinite(array)):
        raise FormRefused(f"{label} contains non-finite values")
    return array.tolist()


def _number(values: dict, key: str, fallback: float) -> float:
    try:
        return float(str(values.get(key, "")).strip() or fallback)
    except Exception as exc:
        raise FormRefused(f"{key.replace('_', ' ')} expects a number.") from exc


def _candidate(form, values: dict) -> tuple:
    """The (advanced, extra_data, uda) this form would write -- what the plot draws too."""
    parts = form.state["parts"]
    row = form.state["row"]
    next_advanced = dict(form.state["advanced"])
    aspher = _numeric_list(form, values.get("aspher", ""), "Asphere coefficients")
    znk = _numeric_list(form, values.get("znk", ""), "Zernike coefficients")
    for key, value in (("AspherData", aspher), ("ZNK", znk)):
        if value:
            next_advanced[key] = value
        else:
            next_advanced.pop(key, None)

    preset = str(values.get("extra_preset", "")).strip()
    if preset == "None":
        next_extra = 0.0
    else:
        next_extra = {"kind": "extra_surface", "preset": preset,
                      "params": parts.parse_literal(str(values.get("extra_params", "")))}

    uda_preset = str(values.get("uda_preset", "")).strip()
    if uda_preset == "Current":
        next_uda = form.state["uda"]
    elif uda_preset == "None":
        next_uda = "None"
    else:
        next_uda = {"kind": "regular_polygon",
                    "radius": _number(values, "uda_radius", 1.0),
                    "sides": UDA_SIDES[uda_preset],
                    "rotation_deg": _number(values, "uda_rotation", 0.0)}

    mask_preset = str(values.get("mask_preset", "")).strip()
    if mask_preset == "None":
        next_advanced.pop("Mask_Shape", None)
        next_advanced.pop("Mask_Type", None)
    else:
        extent = _number(values, "mask_extent", max(float(row.diameter), 1.0))
        pitch = _number(values, "mask_pitch", max(float(row.diameter) / 20.0, 0.25))
        if mask_preset == "Ronchi mask":
            next_advanced["Mask_Shape"] = {"kind": "mask_shape", "preset": "ronchi",
                                           "period": pitch, "duty_cycle": 0.5,
                                           "extent": extent}
        else:
            next_advanced["Mask_Shape"] = {"kind": "mask_shape", "preset": "spider", "arms": 4,
                                           "arm_width": pitch,
                                           "hub_radius": max(pitch * 1.5, extent * 0.04),
                                           "extent": extent}
        next_advanced["Mask_Type"] = 2

    stl_text = str(values.get("stl", "")).strip()
    for key in ("Solid_3d_stl", "OpticalSolidSourcePath", "OpticalSolidSourceFormat"):
        next_advanced.pop(key, None)
    if stl_text:
        next_advanced["Solid_3d_stl"] = stl_text
    return next_advanced, next_extra, next_uda


# ---- the plot ---------------------------------------------------------------------------------
def _draw(form, values: dict, figure) -> str:
    """Draw the sag map and the aperture footprint, and say what the candidate validates as."""
    from matplotlib.patches import Rectangle

    owner = form.state["owner"]
    parts = form.state["parts"]
    row = form.state["row"]
    try:
        next_advanced, next_extra, next_uda = _candidate(form, values)
    except FormRefused as exc:
        return f"Preview failed: {exc}"
    errors, warnings = parts.validate(next_advanced, next_extra, next_uda)

    sag_axis = figure.add_subplot(121)
    aperture_axis = figure.add_subplot(122)
    x_grid, y_grid, sag, inside = owner._surface_preview_grid(row, next_advanced, next_extra)
    finite = sag[np.isfinite(sag) & inside]
    if finite.size:
        image = sag_axis.imshow(
            sag,
            extent=[float(np.nanmin(x_grid)), float(np.nanmax(x_grid)),
                    float(np.nanmin(y_grid)), float(np.nanmax(y_grid))],
            origin="lower", cmap="viridis")
        figure.colorbar(image, ax=sag_axis, fraction=0.046, pad=0.04,
                        label="Sag / departure [mm]")
    else:
        sag_axis.text(0.5, 0.5, "No finite sag data", transform=sag_axis.transAxes,
                      ha="center", va="center")
    sag_axis.set_title("Sag + Asphere/Zernike/ExtraData")
    sag_axis.set_xlabel("X [mm]")
    sag_axis.set_ylabel("Y [mm]")

    radius = max(float(row.diameter) * 0.5, 1.0)
    circle = np.linspace(0.0, 2.0 * np.pi, 240)
    aperture_axis.plot(radius * np.cos(circle), radius * np.sin(circle), color="#334155",
                       lw=1.2, label="Diameter")
    polygon = owner._decoded_uda_polygon(next_uda)
    if polygon is not None:
        px, py = polygon
        aperture_axis.plot(px, py, color="#0f766e", lw=2.0, label="UDA")
        aperture_axis.fill(px, py, color="#0f766e", alpha=0.12)
    mask_value = next_advanced.get("Mask_Shape")
    if isinstance(mask_value, dict):
        preset = str(mask_value.get("preset", "")).strip().lower()
        extent = max(float(mask_value.get("extent", row.diameter)), 1.0)
        if preset == "ronchi":
            period = max(float(mask_value.get("period", extent / 20.0)), 1e-6)
            width = period * float(mask_value.get("duty_cycle", 0.5))
            for x_pos in np.arange(-0.5 * extent, 0.5 * extent + period, period):
                aperture_axis.add_patch(Rectangle((x_pos - 0.5 * width, -0.5 * extent), width,
                                                  extent, color="#dc2626", alpha=0.18))
        elif preset == "spider":
            arms = max(int(mask_value.get("arms", 4)), 1)
            width = max(float(mask_value.get("arm_width", extent * 0.035)), 1e-6)
            for index in range(arms):
                angle = float(index) * np.pi / max(float(arms), 1.0)
                dx = np.cos(angle) * 0.5 * extent
                dy = np.sin(angle) * 0.5 * extent
                aperture_axis.plot([-dx, dx], [-dy, dy], color="#dc2626",
                                   lw=max(width, 1.0), alpha=0.45)
    aperture_axis.set_aspect("equal", adjustable="box")
    aperture_axis.set_title("Aperture / UDA / Mask")
    aperture_axis.set_xlabel("X [mm]")
    aperture_axis.set_ylabel("Y [mm]")
    aperture_axis.grid(True, alpha=0.2)
    aperture_axis.legend(loc="upper right", fontsize=8)

    if errors:
        return f"Validation failed: {errors[0]}"
    if warnings:
        return f"Validation warning: {warnings[0]}"
    note = " Optical solid path staged." if next_advanced.get("Solid_3d_stl") else ""
    return f"Preview OK.{note} Click Apply to store values on this surface."


def _browse_stl(form, host) -> str:
    parts = form.state["parts"]
    directory = parts.attachment_dir
    path = host.askopenfilename(title="Import Optical CAD/STL",
                                initialdir=str(directory),
                                filetypes=list(parts.filetypes))
    if not path:
        return "Browse cancelled."
    form.values["stl"] = str(path)
    return "Optical solid path staged. STEP/IGES will be meshed to cached STL on Apply."


build_surface_shape_form.TITLE = TITLE
