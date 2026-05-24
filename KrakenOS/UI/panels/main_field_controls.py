"""Main layout-editor field controls panel."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from typing import Any


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

        ttk.Label(parent, text="Field type").grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.field_type_var = tk.StringVar(value=self._field_type_display_label("Angle"))
        self.field_type_menu = ttk.Combobox(
            parent,
            textvariable=self.field_type_var,
            state="readonly",
            width=12,
            values=[self._field_type_display_label(value) for value in self.field_type_values],
        )
        self.field_type_menu.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.field_type_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.field_type_menu.bind("<<ComboboxSelected>>", self._on_field_type_changed)

        self.field_mode_note_var = tk.StringVar(value="")

        self.field_value_label_var = tk.StringVar(value=self._field_type_value_label("Angle"))
        ttk.Label(parent, textvariable=self.field_value_label_var).grid(
            row=0,
            column=1,
            sticky="w",
            pady=(0, 2),
            padx=(8, 0),
        )
        self.field_value_var = tk.StringVar(value="5.0")
        field_value_entry = ttk.Entry(parent, textvariable=self.field_value_var, width=12)
        self.field_value_entry = field_value_entry
        field_value_entry.grid(row=1, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))

        self.field_count_label = ttk.Label(parent, text="Field samples")
        self.field_count_label.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.field_count_var = tk.StringVar(value="1")
        field_count_entry = ttk.Entry(parent, textvariable=self.field_count_var, width=12)
        self.field_count_entry = field_count_entry
        field_count_entry.grid(row=3, column=0, sticky="ew", pady=(0, 8))

        ttk.Label(parent, text="Image dia mode").grid(
            row=2,
            column=1,
            sticky="w",
            pady=(0, 2),
            padx=(8, 0),
        )
        self.image_diameter_mode_var = tk.StringVar(value="Auto")
        self.image_diameter_mode_menu = ttk.Combobox(
            parent,
            textvariable=self.image_diameter_mode_var,
            state="readonly",
            width=12,
            values=["Auto", "Manual"],
        )
        self.image_diameter_mode_menu.grid(row=3, column=1, sticky="ew", pady=(0, 8), padx=(8, 0))
        self.image_diameter_mode_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.image_diameter_mode_menu.bind("<<ComboboxSelected>>", self._on_image_diameter_mode_changed)

        ttk.Label(parent, text="Camera").grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.camera_model_var = tk.StringVar(value=self.camera_none_label)
        self.camera_model_menu = ttk.Combobox(
            parent,
            textvariable=self.camera_model_var,
            state="readonly",
            width=12,
            values=[self.camera_none_label, *self.camera_names()],
        )
        self.camera_model_menu.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.camera_model_menu.bind("<FocusIn>", self._begin_history_capture, add="+")
        self.camera_model_menu.bind("<<ComboboxSelected>>", self._on_camera_model_changed)

        self.field_warning_var = tk.StringVar(value="")
        self.field_summary_var = tk.StringVar(value="")

        self._bind_deferred_manual_update(field_value_entry, sync_fields=True)
        self._bind_deferred_manual_update(field_count_entry, sync_fields=True)
        self._sync_field_mode_ui()
