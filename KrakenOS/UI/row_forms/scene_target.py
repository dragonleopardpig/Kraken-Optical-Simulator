"""The Scene Target row form (docs/design_qt_migration.md phase 3).

Scene-target metadata is stored on the surface row and feeds the scene graph, the detector/path
analyses and non-sequential target selection: a name, a role, whether this row is the active
non-sequential `TargSurf`, and -- only when the role is Detector -- the detector's own size,
bins and pitch.

That last "only when" is the one thing the framework was missing. `FormField.enabled` is the
STATIC answer (a value the model will never take edits to); choosing a role turns the four
detector fields on and off while the dialog is open, so `RowForm.locked` holds the LIVE answer
and both views ask `form.is_enabled(key)`.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormAction, FormField, FormRefused, RowForm

TITLE = "Scene Target"
NOTE = ("Scene target settings are stored on the surface row and feed the scene graph, "
        "detector/path analysis, and non-sequential target selection.")
DETECTOR_KEYS = ("active_width_mm", "active_height_mm", "bins", "pixel_pitch_um")


def model(owner):
    """The scene-target model, wherever the caller keeps it.

    All four of these reach the Tk dialog shell as CONSTRUCTOR KWARGS rather than as editor
    attributes, so read them off the owner when it has them and fall back to the module that
    defines them otherwise -- the same split the other row forms hit.
    """
    from types import SimpleNamespace

    from KrakenOS.UI.services import element_scene_metadata as metadata

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        kind_labels=held("scene_target_editor_kind_labels",
                         metadata.SCENE_TARGET_EDITOR_KIND_LABELS),
        kind_choices=held("scene_target_editor_kind_choices",
                          metadata.SCENE_TARGET_EDITOR_KIND_CHOICES),
        normalize_kind=held("normalize_scene_target_editor_kind",
                            metadata._normalize_scene_target_editor_kind),
        normalize_detector=held("normalize_detector_settings",
                                metadata._normalize_detector_settings),
    )


def resolve_row_index(owner, row_index: "int | None" = None) -> int:
    """Which row the editor opens on: the caller's, the scene-graph selection, then the table."""
    if row_index is None:
        record = owner._nonseq_scene_selected_record()
        if record is not None:
            try:
                row_index = int(record.get("row_index"))
            except Exception:
                row_index = None
    if row_index is None:
        row_index = owner._selected_surface_row_index()
    if row_index is None or not (0 <= int(row_index) < len(owner.rows)):
        raise FormRefused("Select a surface row or scene target first.")
    return int(row_index)


def build_scene_target_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one row's scene-target metadata."""
    index = resolve_row_index(owner, row_index)
    row = owner.rows[index]
    parts = model(owner)

    kind_key = owner._scene_target_editor_kind_for_row(index)
    defaults = owner._default_detector_settings_for_target_row(index)
    role_label = parts.kind_labels.get(kind_key, parts.kind_labels["auto"])

    def follow_role(current, label: str) -> str:
        """The detector fields are editable only while the role IS Detector."""
        current.lock(*DETECTOR_KEYS, locked=parts.normalize_kind(label) != "detector")
        return ""

    form = RowForm(
        title=f"{TITLE} - S{index}",
        row_index=index,
        fields=(
            FormField("surface", "Row", kind="static"),
            FormField("name", "Name", kind="text", width=28),
            FormField("role", "Target role", kind="choice",
                      choices=tuple(parts.kind_choices), on_change=follow_role),
            FormField("active", "Set as active non-sequential TargSurf", kind="bool"),
            FormField("active_width_mm", "Active width [mm]", kind="number", width=18),
            FormField("active_height_mm", "Active height [mm]", kind="number", width=18),
            FormField("bins", "Detector bins (blank = global)", kind="text", width=18,
                      hint="Blank, Auto, or an integer from 4 to 512."),
            FormField("pixel_pitch_um", "Pixel pitch [um]", kind="number", width=18),
        ),
        values={
            "surface": f"S{index}: {row.surface} | {row.glass}",
            "name": str(row.name or row.surface or f"S{index}"),
            "role": role_label,
            "active": "true" if owner._current_nonseq_target_surface_index() == index else "false",
            "active_width_mm": owner._format_table_float(
                float(defaults.get("active_width_mm", 0.0))),
            "active_height_mm": owner._format_table_float(
                float(defaults.get("active_height_mm", 0.0))),
            "bins": str(defaults.get("bins", "") or ""),
            "pixel_pitch_um": owner._format_table_float(
                float(defaults.get("pixel_pitch_um", 0.0))),
        },
        summary="Scene target metadata is row-backed; click Apply to update the table state.",
        note=NOTE,
    )

    follow_role(form, role_label)

    def collect_detector(values: dict) -> dict:
        try:
            width = float(str(values.get("active_width_mm", "")).strip() or "0")
            height = float(str(values.get("active_height_mm", "")).strip() or "0")
            pitch = float(str(values.get("pixel_pitch_um", "")).strip() or "0")
        except ValueError as exc:
            raise FormRefused("Detector active size and pixel pitch must be numbers.") from exc
        if width < 0.0 or height < 0.0 or pitch < 0.0:
            raise FormRefused("Detector active size and pixel pitch must be non-negative.")
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
        return parts.normalize_detector({"active_width_mm": width, "active_height_mm": height,
                                         "bins": bins, "pixel_pitch_um": pitch})

    def collect(values: dict) -> tuple:
        kind = parts.normalize_kind(values.get("role", ""))
        detector = collect_detector(values)
        if kind == "detector" and row.surface == "Object":
            raise FormRefused("Object rows cannot be detector planes.")
        return kind, detector

    def is_active(values: dict) -> bool:
        return str(values.get("active", "")).strip().lower() in ("1", "true", "yes", "on")

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        kind, _detector = collect(values)
        return (f"role={parts.kind_labels.get(kind, kind)}, "
                f"active={'yes' if is_active(values) else 'no'}.")

    def apply(values: dict) -> str:
        kind, detector = collect(values)
        owner._begin_history_capture()
        try:
            result = owner._apply_scene_target_editor_update(
                index,
                target_kind=kind,
                detector_settings=detector,
                active_target=is_active(values),
                row_name=str(values.get("name", "")),
            )
        except Exception as exc:
            owner._history_pending_state = None
            raise FormRefused(str(exc)) from exc
        return finish(f"Updated scene target S{index}: {result['surface']} / "
                      f"{result['target_kind']}. Click Update to trace.")

    def clear(_form, _host) -> str:
        owner._begin_history_capture()
        owner._clear_scene_target_editor_metadata(index)
        return finish(f"Cleared scene-target metadata for S{index}.")

    def finish(message: str) -> str:
        owner._sync_table()
        owner._select_table_row(index)
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        owner._refresh_nonseq_scene_graph_if_open()
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    form.actions = (FormAction("clear", "Clear Target", clear),)
    return form


build_scene_target_form.TITLE = TITLE
