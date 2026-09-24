"""The two element row forms (docs/design_qt_migration.md phase 3).

Both edit an element BLOCK -- the run of consecutive rows that share one element key -- rather
than a single row, which is the one thing every previous row form assumed. `RowForm.row_index`
is the block's first row (what a view selects), and the block itself rides in `form.state`.

`build_path_local_pose_form` edits the pose of a placed path element in its own path frame;
`build_element_settings_form` edits the whole metadata record, and writes it THROUGH the pose
path when the record carries one.
"""
from __future__ import annotations

from KrakenOS.UI.row_forms.base import FormField, FormRefused, RowForm

POSE_TITLE = "Path-Local Pose"
SETTINGS_TITLE = "Element Settings"
POSE_NOTE = ("The UI recomputes global Tilt/Decenter values from the current path frame; for "
             "traced BRANCH_PATH elements, click Update first.")
SETTINGS_NOTE = ("Element metadata is saved with each surface row. It is used by path-aware UI "
                 "tools and future placement/analysis helpers.")
POSE_LABELS = (
    ("arm_distance", "Path distance [mm]"),
    ("local_decenter_x", "Local X offset [mm]"),
    ("local_decenter_y", "Local Y offset [mm]"),
    ("local_tilt_x", "Local tilt X [deg]"),
    ("local_tilt_y", "Local tilt Y [deg]"),
    ("local_tilt_z", "Local tilt Z [deg]"),
)
SETTINGS_LABELS = (
    ("arm_distance", "Path distance [mm]"),
    ("local_decenter_x", "Local decenter X [mm]"),
    ("local_decenter_y", "Local decenter Y [mm]"),
    ("local_tilt_x", "Local tilt X [deg]"),
    ("local_tilt_y", "Local tilt Y [deg]"),
    ("local_tilt_z", "Local tilt Z [deg]"),
)


def model(owner):
    """The element-metadata model, wherever the caller keeps it.

    Every one of these reaches the Tk dialog shell as a CONSTRUCTOR KWARG rather than as an
    editor attribute, so read it off the owner when it has it and fall back otherwise.
    """
    from types import SimpleNamespace

    from KrakenOS.UI import layout_editor
    from KrakenOS.UI.services import element_scene_metadata as metadata

    def held(name, fallback):
        value = getattr(owner, name, None)
        return fallback if value is None else value

    return SimpleNamespace(
        numeric_fields=held("element_metadata_numeric_fields",
                            metadata.ELEMENT_METADATA_NUMERIC_FIELDS),
        normalize=held("normalize_element_metadata", metadata._normalize_element_metadata),
        summary=held("element_metadata_summary", layout_editor._element_metadata_summary),
        short_error=held("short_error_message", layout_editor._short_error_message),
        arm_role_default=held("element_arm_role_default", metadata.ELEMENT_ARM_ROLE_DEFAULT),
        arm_role_values=held("element_arm_role_values", metadata.ELEMENT_ARM_ROLE_VALUES),
        branch_selector_values=held("element_branch_selector_values",
                                    metadata.ELEMENT_BRANCH_SELECTOR_VALUES),
    )


def resolve_block(owner, row_index, *, none_message: str, many_message: str) -> list:
    """The element block to edit: the caller's row, or the table's selection.

    A view that knows one row (the Qt surface table) hands it over and the block is grown around
    it exactly as `_selected_element_blocks` grows one; a view that does not (the Tk context
    menu) lets the selection decide, and a selection spanning two elements refuses.
    """
    if row_index is None:
        blocks = owner._selected_element_blocks()
        if not blocks:
            raise FormRefused(none_message)
        if len(blocks) > 1:
            raise FormRefused(many_message)
        return list(blocks[0])
    index = int(row_index)
    if not (0 < index < len(owner.rows) - 1):
        raise FormRefused(none_message)
    if owner._element_key(owner.rows[index]):
        start, end = owner._element_block_for_index(owner.rows, index)
    else:
        start, end = index, index
    return list(range(start, end + 1))


def _collect_numbers(parts, values: dict, data: dict) -> dict:
    """The six pose numbers, with the model's own messages."""
    import numpy as np

    for key in parts.numeric_fields:
        try:
            number = float(str(values.get(key, "")).strip())
        except ValueError as exc:
            raise FormRefused(f"{key.replace('_', ' ')} expects a number.") from exc
        if not np.isfinite(number):
            raise FormRefused(f"{key.replace('_', ' ')} must be finite.")
        data[key] = number
    return data


def build_path_local_pose_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one placed element's pose in its own path frame."""
    indices = resolve_block(
        owner, row_index,
        none_message="Select one placed path element or stock-lens block first.",
        many_message="Select one placed path element or stock-lens block first.")
    metadata = owner._element_metadata(owner.rows[indices[0]])
    if not owner._metadata_has_path_pose(metadata):
        raise FormRefused("The selected element has no path-placement metadata. Insert it with "
                          "a path-component/stock-lens command first.")

    parts = model(owner)
    label = (owner._element_key(owner.rows[indices[0]])
             or str(metadata.get("element_name", "") or "Path element"))
    branch_path = str(metadata.get("branch_path", "") or "").strip()
    frame_text = (owner._branch_path_compact_detail(branch_path) if branch_path
                  else parts.summary(metadata))

    form = RowForm(
        title=f"{POSE_TITLE} - rows {indices[0]}-{indices[-1]}",
        row_index=indices[0],
        fields=(FormField("path_frame", "Path frame", kind="static"),)
               + tuple(FormField(key, text, kind="number", width=16)
                       for key, text in POSE_LABELS),
        values={"path_frame": frame_text,
                **{key: owner._format_table_float(float(metadata.get(key, 0.0)))
                   for key, _text in POSE_LABELS}},
        summary="Validate checks that the saved path frame can still be resolved.",
        note=f"Edit the local pose of {label}. {POSE_NOTE}",
        state={"indices": list(indices), "label": label, "metadata": dict(metadata)},
    )

    def collect(values: dict) -> dict:
        data = _collect_numbers(parts, values, dict(metadata))
        data = parts.normalize(data)
        try:
            owner._path_frame_for_element_metadata(data)
        except Exception as exc:
            raise FormRefused(parts.short_error(exc)) from exc
        return data

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        collect(values)
        return "path frame resolved and pose values are finite."

    def apply(values: dict) -> str:
        data = collect(values)
        owner._begin_history_capture()
        try:
            updated = owner._apply_path_local_pose_to_indices(indices, data)
        except Exception as exc:
            owner._history_pending_state = None
            raise FormRefused(parts.short_error(exc)) from exc
        owner._normalize_special_rows()
        owner._sync_table()
        owner._select_table_indices(updated, focus_index=updated[0])
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        message = f"Updated path-local pose for {label}. Click Update to retrace."
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


def build_element_settings_form(owner, row_index: "int | None" = None) -> RowForm:
    """The form for one element block's whole metadata record."""
    indices = resolve_block(
        owner, row_index,
        none_message="Select a non-Object/non-Image row or element group first.",
        many_message="Open Element Settings for one element at a time.")
    row = owner.rows[indices[0]]
    metadata = owner._element_metadata(row)
    parts = model(owner)
    element_label = (owner._element_key(row)
                     or str(row.name or owner._next_manual_element_label()).strip())
    selector = str(metadata.get("branch_selector", "") or "")

    form = RowForm(
        title=f"{SETTINGS_TITLE} - rows {indices[0]}-{indices[-1]}",
        row_index=indices[0],
        fields=(
            FormField("element_name", "Element name", kind="text", width=28),
            FormField("element_id", "Element ID", kind="text", width=28),
            FormField("arm_role", "Path role", kind="choice",
                      choices=tuple(parts.arm_role_values)),
            # the splitter list is a convenience, not the whole domain -- an element may name a
            # parent this scene does not hold yet, exactly as the Tk combobox allowed
            FormField("parent_splitter", "Parent splitter", kind="choice", editable=True,
                      choices=tuple(owner._beam_splitter_element_choices())),
            FormField("branch_selector", "Split selector", kind="choice", editable=True,
                      choices=tuple(parts.branch_selector_values)),
            FormField("branch_path", "Traced branch path", kind="text", width=28),
        ) + tuple(FormField(key, text, kind="number", width=16)
                  for key, text in SETTINGS_LABELS),
        values={
            "element_name": element_label,
            "element_id": str(metadata.get("element_id", "")
                              or owner._element_id_from_label(element_label)),
            "arm_role": str(metadata.get("arm_role", parts.arm_role_default)),
            "parent_splitter": str(metadata.get("parent_splitter", "") or ""),
            "branch_selector": selector if selector else "Auto",
            "branch_path": str(metadata.get("branch_path", "") or ""),
            **{key: owner._format_table_float(float(metadata.get(key, 0.0)))
               for key, _text in SETTINGS_LABELS},
        },
        summary="Set Common/Transmit/Reflect/Detector path metadata for this element.",
        note=SETTINGS_NOTE,
        state={"indices": list(indices), "metadata": dict(metadata)},
    )

    def collect(values: dict) -> dict:
        label = str(values.get("element_name", "")).strip()
        if not label:
            raise FormRefused("Element name cannot be empty.")
        role = str(values.get("arm_role", "")).strip()
        if role not in parts.arm_role_values:
            raise FormRefused("Choose a valid path role.")
        chosen = str(values.get("branch_selector", "")).strip()
        data = dict(metadata)
        data.update({
            "element_id": str(values.get("element_id", "")).strip(),
            "element_name": label,
            "arm_role": role,
            "parent_splitter": str(values.get("parent_splitter", "")).strip(),
            "branch_selector": "" if chosen == "Auto" else chosen,
            "branch_path": str(values.get("branch_path", "")).strip(),
        })
        data = _collect_numbers(parts, values, data)
        if not data["branch_selector"]:
            data["branch_selector"] = owner._branch_selector_for_arm_role(role)
        return parts.normalize(data)

    def validate(values: dict) -> list[str]:
        try:
            collect(values)
        except FormRefused as exc:
            return [str(exc)]
        return []

    def describe(values: dict) -> str:
        return parts.summary(collect(values))

    def apply(values: dict) -> str:
        data = collect(values)
        label = str(data.get("element_name", "") or "").strip()
        owner._begin_history_capture()
        if owner._metadata_has_path_pose(data):
            # a placed element keeps its path frame: the pose path rewrites the rows
            try:
                owner._apply_path_local_pose_to_indices(indices, data)
            except Exception as exc:
                owner._history_pending_state = None
                raise FormRefused(parts.short_error(exc)) from exc
        else:
            for index in indices:
                owner.rows[index].element = label
                owner._set_element_metadata(owner.rows[index], data)
        owner._normalize_special_rows()
        owner._sync_table()
        owner._select_table_indices(indices, focus_index=indices[0])
        owner._commit_history_capture()
        owner._mark_plot_update_pending()
        message = f"Updated element settings for {label}: {parts.summary(data)}."
        owner.status_var.set(message)
        return message

    form.validate = validate
    form.describe = describe
    form.apply = apply
    return form


build_path_local_pose_form.TITLE = POSE_TITLE
build_element_settings_form.TITLE = SETTINGS_TITLE
