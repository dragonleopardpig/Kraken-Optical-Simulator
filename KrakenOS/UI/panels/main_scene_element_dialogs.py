"""Detector, scene target, path-pose, and element settings dialogs."""

from __future__ import annotations

from tkinter import messagebox

from typing import Any, Callable

from KrakenOS.UI.panels.row_form_view import render_row_form
from KrakenOS.UI.row_forms import FormRefused
from KrakenOS.UI.row_forms.detector_settings import build_detector_settings_form
from KrakenOS.UI.row_forms.element_forms import (build_element_settings_form,
                                                 build_path_local_pose_form)
from KrakenOS.UI.row_forms.scene_target import build_scene_target_form



class MainSceneElementDialogs:
    """Own scene/element settings dialogs while delegating state to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        normalize_detector_settings: Callable[[dict[str, object]], dict[str, object]],
        scene_target_editor_kind_labels: dict[str, str],
        scene_target_editor_kind_choices: tuple[str, ...],
        normalize_scene_target_editor_kind: Callable[[str], str],
        element_metadata_numeric_fields: tuple[str, ...],
        normalize_element_metadata: Callable[[dict[str, object]], dict[str, object]],
        element_metadata_summary: Callable[[dict[str, object]], str],
        short_error_message: Callable[[BaseException], str],
        element_arm_role_default: str,
        element_arm_role_values: tuple[str, ...],
        element_branch_selector_values: tuple[str, ...],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "normalize_detector_settings", normalize_detector_settings)
        object.__setattr__(self, "scene_target_editor_kind_labels", dict(scene_target_editor_kind_labels))
        object.__setattr__(self, "scene_target_editor_kind_choices", tuple(scene_target_editor_kind_choices))
        object.__setattr__(self, "normalize_scene_target_editor_kind", normalize_scene_target_editor_kind)
        object.__setattr__(self, "element_metadata_numeric_fields", tuple(element_metadata_numeric_fields))
        object.__setattr__(self, "normalize_element_metadata", normalize_element_metadata)
        object.__setattr__(self, "element_metadata_summary", element_metadata_summary)
        object.__setattr__(self, "short_error_message", short_error_message)
        object.__setattr__(self, "element_arm_role_default", element_arm_role_default)
        object.__setattr__(self, "element_arm_role_values", tuple(element_arm_role_values))
        object.__setattr__(self, "element_branch_selector_values", tuple(element_branch_selector_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "normalize_detector_settings",
            "scene_target_editor_kind_labels",
            "scene_target_editor_kind_choices",
            "normalize_scene_target_editor_kind",
            "element_metadata_numeric_fields",
            "normalize_element_metadata",
            "element_metadata_summary",
            "short_error_message",
            "element_arm_role_default",
            "element_arm_role_values",
            "element_branch_selector_values",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _run_row_form_dialog(self, form, *, wraplength: int = 520):
        """Show a `RowForm` -- the Tk view lives in panels/row_form_view.py (bugs/0881)."""
        return render_row_form(self, form, wraplength=wraplength,
                               on_close=self._cleanup_current_popup_menu)

    def _open_row_form(self, title: str, builder, *args, wraplength: int = 520):
        """Read the table, build the form, show it -- what all four of these dialogs do."""
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror(title, f"Could not read the surface table:\n\n{exc}",
                                 parent=self.editor)
            return None
        try:
            form = builder(self, *args)
        except FormRefused as exc:
            messagebox.showinfo(title, str(exc), parent=self.editor)
            return None
        return self._run_row_form_dialog(form, wraplength=wraplength)

    def open_detector_settings(self, row_index: int) -> None:
        self._open_row_form("Detector Settings", build_detector_settings_form, row_index)

    def open_scene_target_editor(self, row_index: int | None = None) -> None:
        self._open_row_form("Scene Target", build_scene_target_form, row_index, wraplength=560)

    def open_selected_path_local_pose_editor(self) -> None:
        self._open_row_form("Path-Local Pose", build_path_local_pose_form)

    def open_element_settings(self) -> None:
        self._open_row_form("Element Settings", build_element_settings_form)
