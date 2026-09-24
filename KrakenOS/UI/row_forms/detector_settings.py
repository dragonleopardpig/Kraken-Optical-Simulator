"""The Detector Settings row form (docs/design_qt_migration.md phase 3).

Marks a surface as a terminal detector for the path analyses and sizes it. Four values, a Clear
action, and the model's own normaliser -- the framework absorbed it without needing anything new,
which is the point of having built it.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

TITLE = "Detector Settings"
NOTE = ("Detector settings mark this row as a terminal detector for path analyses. Active size "
        "controls DetMap/CohDet extents in detector-local coordinates; Bins overrides the global "
        "Detector bins field when set.")
BINS_HINT = "Blank, Auto, or an integer from 4 to 512. Blank uses the global Detector bins."


def model(owner):
    """The detector model, wherever the caller keeps it.

    `_detector_settings` is a workbench method on the editor, but `normalize_detector_settings`
    reaches the Tk shell as a constructor kwarg, so neither lives in one place. Read both off the
    owner when it has them and fall back to the defining module otherwise.
    """
    from types import SimpleNamespace

    from KrakenOS.UI.services.advanced_surface_attrs import DETECTOR_ADVANCED_ATTR
    from KrakenOS.UI.services.element_scene_metadata import _normalize_detector_settings

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    def read_settings(row):
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(DETECTOR_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return _normalize_detector_settings(value)

    return SimpleNamespace(
        read=held("_detector_settings", read_settings),
        normalize=held("normalize_detector_settings", _normalize_detector_settings),
    )


def build_detector_settings_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one row's detector settings."""
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or row_index < 0 or row_index >= len(owner.rows):
        raise FormRefused("Select a surface row first.")
    row = owner.rows[row_index]
    if row.surface == "Object":
        raise FormRefused("Object rows cannot be detector planes.")

    parts = model(owner)
    settings = parts.read(row)
    diameter = owner._safe_positive_float(getattr(row, "diameter", 0.0), 0.0)
    width = float(settings.get("active_width_mm", 0.0)) or diameter
    height = float(settings.get("active_height_mm", 0.0)) or diameter

    form = RowForm(
        title=f"{TITLE} - S{row_index}",
        row_index=row_index,
        fields=(
            FormField("active_width_mm", "Active width [mm]", kind="number", width=18),
            FormField("active_height_mm", "Active height [mm]", kind="number", width=18),
            FormField("bins", "Detector bins (blank = global)", kind="text", width=18,
                      hint=BINS_HINT),
            FormField("pixel_pitch_um", "Pixel pitch [um] (metadata)", kind="number", width=18),
        ),
        values={
            "active_width_mm": owner._format_table_float(width),
            "active_height_mm": owner._format_table_float(height),
            "bins": str(settings.get("bins", "") or ""),
            "pixel_pitch_um": owner._format_table_float(
                float(settings.get("pixel_pitch_um", 0.0))),
        },
        note=NOTE,
    )

    def collect(values: dict) -> dict:
        try:
            width_mm = float(str(values.get("active_width_mm", "")).strip() or "0")
            height_mm = float(str(values.get("active_height_mm", "")).strip() or "0")
            pitch = float(str(values.get("pixel_pitch_um", "")).strip() or "0")
        except ValueError as exc:
            raise FormRefused("Active size and pixel pitch must be numbers.") from exc
        if width_mm < 0.0 or height_mm < 0.0 or pitch < 0.0:
            raise FormRefused("Active size and pixel pitch must be non-negative.")
        bins = str(values.get("bins", "")).strip()
        if bins and bins.lower() not in {"auto", "default"}:
            try:
                bins_value = int(float(bins))
            except ValueError as exc:
                raise FormRefused("Detector bins must be blank, Auto, or an integer from 4 to "
                                  "512.") from exc
            if not 4 <= bins_value <= 512:
                raise FormRefused("Detector bins must be between 4 and 512.")
            bins = str(bins_value)
        else:
            bins = ""
        return parts.normalize({"active_width_mm": width_mm, "active_height_mm": height_mm,
                                "bins": bins, "pixel_pitch_um": pitch})

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        data = collect(values)
        return (f"{float(data['active_width_mm']):.6g} x "
                f"{float(data['active_height_mm']):.6g} mm, "
                f"bins={data.get('bins') or 'global'}, "
                f"pitch={float(data['pixel_pitch_um']):.6g} um")

    def write(data: dict, message: str) -> str:
        owner._begin_history_capture()
        owner._set_detector_settings(owner.rows[row_index], data)
        owner._sync_table()
        owner._select_table_row(row_index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        owner.status_var.set(message)
        return message

    def apply(values: dict) -> str:
        return write(collect(values),
                     f"Updated detector settings for S{row_index}. "
                     "Click Update to retrace analyses.")

    def clear(_form, _host) -> str:
        return write({}, f"Cleared detector settings for S{row_index}.")

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.summary = "Use blank bins for global Auto/manual Detector bins."
    form.actions = (FormAction("clear", "Clear", clear),)
    return form


build_detector_settings_form.TITLE = TITLE
