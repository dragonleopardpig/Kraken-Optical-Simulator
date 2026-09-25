"""Two small per-surface settings row forms (docs/design_qt_migration.md phase 3).

The galvo scan overlay (a list of TiltX angles a mirror is drawn at) and the grating fields
(order, pitch, line angle) that no longer occupy main-table columns. Both are one row's data,
both validate in the model, and neither needed anything new from the framework -- which is what
the tail of phase 3 should look like.
"""
from __future__ import annotations

import numpy as np

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

GALVO_TITLE = "Galvo Scan Overlay"
GALVO_NOTE = ("TiltX overlay values [deg], using the same mirror angle shown in the table. Use "
              "comma values or start:stop:step -- for example -50,-45,-40 for a -10, 0, +10 "
              "degree optical scan; -55,-45,-35 is the Figure 8 full field. You can also type "
              "these straight into the mirror's TiltX cell. The middle value becomes the "
              "nominal pose; the full list is a display-only scan overlay.")
GALVO_LIMIT = 25
GRATING_TITLE = "Grating Settings"
GRATING_NOTE = ("These grating-only fields are stored on the row but no longer occupy "
                "main-table columns. Right-click the Grating name cell to reopen this dialog.")
GRATING_FIELDS = (("diff_ord", "Diffraction order"), ("grating_d", "Pitch [um]"),
                  ("grating_angle", "Line angle [deg]"))


def model(owner):
    """The surface-settings model, wherever the caller keeps it.

    All four reach the Tk dialog shell as CONSTRUCTOR KWARGS rather than as editor attributes,
    so read each off the owner when it has it and fall back to the defining module otherwise.
    """
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor as editor_module
    from KrakenOS.UI.services import surface_value_parsing

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        overlay_key=held("galvo_scan_overlay_key", editor_module.GALVO_SCAN_OVERLAY_KEY),
        format_sequence=held("format_float_sequence",
                             surface_value_parsing._format_float_sequence),
        parse_sequence=held("parse_float_sequence_text",
                            surface_value_parsing._parse_float_sequence_text),
        short_error=held("short_error_message", editor_module._short_error_message),
    )


def _row_index(owner, row_index: "int | None", message: str) -> int:
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or not (0 <= int(row_index) < len(owner.rows)):
        raise FormRefused(message)
    return int(row_index)


# ---- the galvo scan overlay --------------------------------------------------------------------
def build_galvo_scan_form(owner, row_index: "int | None" = None) -> RowForm:
    """The TiltX angles one mirror is drawn at."""
    index = _row_index(owner, row_index, "No mirror row selected.")
    row = owner.rows[index]
    if row.surface != "Mirror":
        raise FormRefused("Galvo scan overlay applies to Mirror rows.")

    parts = model(owner)
    display = dict((row.advanced or {}).get("Display2D", {}) or {})
    existing = display.get(parts.overlay_key)
    nominal = owner._mirror_display_slant_deg_for_rows(owner.rows, index)
    slants = (owner._mirror_overlay_display_slants_for_rows(owner.rows, index)
              if existing is not None else [])
    seeded = (parts.format_sequence(slants) if slants
              else f"{nominal - 5:g}, {nominal:g}, {nominal + 5:g}")

    form = RowForm(
        title=f"{GALVO_TITLE} - S{index}: {row.name}",
        row_index=index,
        fields=(FormField("angles", "TiltX overlay [deg]", kind="text", width=46),),
        values={"angles": seeded},
        note=GALVO_NOTE,
        state={"owner": owner, "parts": parts, "index": index},
    )
    form.summary = f"Nominal mirror angle is {nominal:g} deg."

    def collect(values: dict) -> list:
        try:
            angles = parts.parse_sequence(str(values.get("angles", "")))
        except Exception as exc:
            raise FormRefused(f"Invalid TiltX list: {parts.short_error(exc)}") from exc
        if len(angles) > GALVO_LIMIT:
            raise FormRefused(f"Use {GALVO_LIMIT} or fewer overlay angles to keep the plot "
                              "readable.")
        return list(angles)

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        angles = collect(values)
        if not angles:
            return "Clears the overlay."
        return (f"{len(angles)} angle(s), nominal "
                f"{angles[len(angles) // 2]:g} deg")

    def apply(values: dict) -> str:
        return _write_galvo(form, collect(values))

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (FormAction("clear", "Clear", lambda current, _host: _write_galvo(current,
                                                                                     [])),)
    return form


def _write_galvo(form, angles: list) -> str:
    owner = form.state["owner"]
    index = form.state["index"]
    owner._begin_history_capture()
    target = owner.rows[index]
    branch_angle = owner._mirror_branch_angle_before_index(owner.rows, index)
    if angles:
        local = [owner._mirror_local_tilt_deg_from_display(branch_angle, value)
                 for value in angles]
        # the MIDDLE value is the nominal pose; the rest are display-only
        target.tilt_x = float(local[len(local) // 2])
        target.advanced = owner._advanced_with_galvo_scan_overlay(target.advanced, local)
        message = (f"Galvo scan overlay set to {form.state['parts'].format_sequence(angles)} deg. "
                   "Click Update.")
    else:
        target.advanced = owner._advanced_with_galvo_scan_overlay(target.advanced, [])
        message = "Galvo scan overlay cleared. Click Update."
    owner._sync_table()
    owner._commit_history_capture()
    owner._mark_plot_update_pending()
    owner.status_var.set(message)
    return message


# ---- the grating fields ------------------------------------------------------------------------
def build_grating_settings_form(owner, row_index: "int | None" = None) -> RowForm:
    """The order, pitch and line angle of one grating row."""
    index = _row_index(owner, row_index, "Select a surface row first.")
    row = owner.rows[index]

    form = RowForm(
        title=f"{GRATING_TITLE} - S{index}: {row.name}",
        row_index=index,
        fields=tuple(FormField(key, label, kind="number", width=18)
                     for key, label in GRATING_FIELDS),
        values={key: owner._format_table_float(getattr(row, key))
                for key, _label in GRATING_FIELDS},
        note=GRATING_NOTE,
        state={"owner": owner, "index": index},
    )
    form.summary = "Right-click the Grating name cell to reopen this dialog."

    def collect(values: dict) -> dict:
        parsed = {}
        for key, label in GRATING_FIELDS:
            try:
                number = float(str(values.get(key, "")).strip())
            except ValueError as exc:
                raise FormRefused(f"{label} expects a number.") from exc
            if not np.isfinite(number):
                raise FormRefused(f"{label} must be finite.")
            parsed[key] = number
        if abs(parsed["grating_d"]) < 1e-12:
            raise FormRefused("Pitch [um] must be non-zero.")
        return parsed

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        parsed = collect(values)
        return (f"order {parsed['diff_ord']:g}, pitch {parsed['grating_d']:g} um, "
                f"lines at {parsed['grating_angle']:g} deg")

    def apply(values: dict) -> str:
        parsed = collect(values)
        owner._begin_history_capture()
        target = owner.rows[index]
        for key, value in parsed.items():
            setattr(target, key, value)
        owner._sync_table()
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        message = (f"Updated grating settings for S{index}: {target.name}. Click Update.")
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


build_galvo_scan_form.TITLE = GALVO_TITLE
build_grating_settings_form.TITLE = GRATING_TITLE
