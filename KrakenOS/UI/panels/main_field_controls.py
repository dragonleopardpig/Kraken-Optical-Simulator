"""Main layout-editor field controls panel."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.widgets import grid_labeled_commit_combobox, grid_labeled_commit_entry


class MainFieldControlsPanel:
    """Build field controls while keeping state on the owning editor."""

    def __init__(
        self,
        editor: Any,
        *,
        field_type_values: Sequence[str],
        camera_none_label: str,
        camera_names: Callable[[], Sequence[str]],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "field_type_values", tuple(field_type_values))
        object.__setattr__(self, "camera_none_label", camera_none_label)
        object.__setattr__(self, "camera_names", camera_names)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {"editor", "field_type_values", "camera_none_label", "camera_names"}:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def build(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1)

        self.field_type_var = tk.StringVar(value=self._field_type_display_label("Angle"))
        self.field_type_menu = grid_labeled_commit_combobox(
            parent,
            0,
            0,
            "Field type",
            self.field_type_var,
            values=[self._field_type_display_label(value) for value in self.field_type_values],
            on_commit=self._on_field_type_changed,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.field_mode_note_var = tk.StringVar(value="")

        self.field_value_label_var = tk.StringVar(value=self._field_type_value_label("Angle"))
        self.field_value_var = tk.StringVar(value="5.0")
        field_value_entry = grid_labeled_commit_entry(
            parent,
            0,
            1,
            "",
            self.field_value_var,
            on_commit=self._commit_field_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
            label_textvariable=self.field_value_label_var,
        )
        self.field_value_entry = field_value_entry

        self.field_count_var = tk.StringVar(value="1")
        field_count_entry = grid_labeled_commit_entry(
            parent,
            2,
            0,
            "Field samples",
            self.field_count_var,
            on_commit=self._commit_field_controls,
            on_focus_in=self._begin_history_capture,
            width=12,
        )
        self.field_count_entry = field_count_entry
        self.field_count_label = field_count_entry.label_widget

        self.image_diameter_mode_var = tk.StringVar(value="Auto")
        self.image_diameter_mode_menu = grid_labeled_commit_combobox(
            parent,
            2,
            1,
            "Image dia mode",
            self.image_diameter_mode_var,
            values=["Auto", "Manual"],
            on_commit=self._on_image_diameter_mode_changed,
            on_focus_in=self._begin_history_capture,
            width=12,
        )

        self.camera_model_var = tk.StringVar(value=self.camera_none_label)
        self.camera_model_menu = grid_labeled_commit_combobox(
            parent,
            4,
            0,
            "Camera",
            self.camera_model_var,
            values=[self.camera_none_label, *self.camera_names()],
            on_commit=self._on_camera_model_changed,
            on_focus_in=self._begin_history_capture,
            width=12,
            combo_columnspan=2,
        )

        self.field_warning_var = tk.StringVar(value="")
        self.field_summary_var = tk.StringVar(value="")

        self._sync_field_mode_ui()

    def _commit_field_controls(self, _event=None) -> None:
        self._sync_object_controls()
        self._mark_plot_update_pending()
