"""Open 3D Live Controls panel construction."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from typing import Any


class Open3DLiveControlsPanel:
    """Build the left-docked Open 3D controls without owning trace policy."""

    def __init__(
        self,
        inspector: Any,
        *,
        source_model_values: Sequence[str],
        pupil_pattern_values: Sequence[str],
        field_type_values: Sequence[str],
        source_direction_preset_values: Sequence[str],
        camera_none_label: str,
        camera_names: Callable[[], Sequence[str]],
    ) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.source_model_values = tuple(source_model_values)
        self.pupil_pattern_values = tuple(pupil_pattern_values)
        self.field_type_values = tuple(field_type_values)
        self.source_direction_preset_values = tuple(source_direction_preset_values)
        self.camera_none_label = camera_none_label
        self.camera_names = camera_names

    def build(self, parent: tk.Widget) -> None:
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        header.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            header,
            text="Live Mode",
            variable=self.inspector.live_mode_var,
            command=self.inspector._on_live_mode_toggled,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(header, text="Trace now", command=self.inspector._trace_live_now).grid(
            row=0,
            column=2,
            sticky="e",
            padx=(6, 0),
        )
        ttk.Button(header, text="Update 2D", command=self.editor._manual_update_plot).grid(
            row=0,
            column=3,
            sticky="e",
            padx=(6, 0),
        )

        canvas = tk.Canvas(parent, highlightthickness=0, borderwidth=0, width=280)
        canvas.grid(row=1, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scroll.grid(row=1, column=1, sticky="ns", padx=(6, 0))
        canvas.configure(yscrollcommand=scroll.set)
        stack = ttk.Frame(canvas)
        stack.columnconfigure(0, weight=1)
        window_id = canvas.create_window((0, 0), window=stack, anchor="nw")
        stack.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(window_id, width=max(int(event.width), 1)))

        source = ttk.LabelFrame(stack, text="Source", padding=8)
        source.grid(row=0, column=0, sticky="ew")
        self.build_source_controls(source)

        field = ttk.LabelFrame(stack, text="Field", padding=8)
        field.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        self.build_field_controls(field)

        trace = ttk.LabelFrame(stack, text="Trace / Display", padding=8)
        trace.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.build_trace_controls(trace)

        step = ttk.LabelFrame(stack, text="STEP Placement", padding=8)
        step.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.build_step_controls(step)

    def editor_var(self, name: str, default: str = ""):
        var = getattr(self.editor, name, None)
        if var is None:
            var = tk.StringVar(value=default)
        return var

    def live_labeled_entry(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        label: str,
        var_name: str,
        *,
        sync_fields: bool = False,
        width: int = 10,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=(0, 2), padx=(8 if column else 0, 0))
        entry = ttk.Entry(parent, textvariable=self.editor_var(var_name), width=width)
        entry.grid(row=row + 1, column=column, sticky="ew", pady=(0, 8), padx=(8 if column else 0, 0))
        entry.bind("<FocusIn>", self.editor._begin_history_capture, add="+")
        entry.bind(
            "<FocusOut>",
            lambda _event: self.inspector._commit_live_control_update(sync_fields=sync_fields),
            add="+",
        )
        entry.bind(
            "<Return>",
            lambda _event: self.inspector._commit_live_control_update(sync_fields=sync_fields),
            add="+",
        )
        entry.bind(
            "<KP_Enter>",
            lambda _event: self.inspector._commit_live_control_update(sync_fields=sync_fields),
            add="+",
        )
        return entry

    def live_labeled_combo(
        self,
        parent: tk.Widget,
        row: int,
        column: int,
        label: str,
        var_name: str,
        values,
        *,
        handler=None,
        width: int = 12,
    ) -> ttk.Combobox:
        ttk.Label(parent, text=label).grid(row=row, column=column, sticky="w", pady=(0, 2), padx=(8 if column else 0, 0))
        combo = ttk.Combobox(
            parent,
            textvariable=self.editor_var(var_name),
            state="readonly",
            width=width,
            values=tuple(values),
        )
        combo.grid(row=row + 1, column=column, sticky="ew", pady=(0, 8), padx=(8 if column else 0, 0))
        combo.bind("<FocusIn>", self.editor._begin_history_capture, add="+")
        combo.bind(
            "<<ComboboxSelected>>",
            lambda _event: self.inspector._commit_live_control_update(handler=handler),
            add="+",
        )
        return combo

    def build_source_controls(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1, uniform="live_source")
        self.live_labeled_combo(
            parent,
            0,
            0,
            "Source model",
            "source_model_var",
            self.source_model_values,
            handler=self.editor._on_source_model_changed,
            width=14,
        )
        self.live_labeled_combo(
            parent,
            0,
            1,
            "Pupil pattern",
            "pupil_pattern_var",
            self.pupil_pattern_values,
            handler=self.editor._on_source_model_changed,
            width=14,
        )
        self.live_labeled_entry(parent, 2, 0, "Ray count", "ray_count_var", sync_fields=True)
        self.live_labeled_entry(parent, 2, 1, "Cone [deg]", "source_cone_angle_var")
        self.live_labeled_entry(parent, 4, 0, "Source radius", "source_radius_var")
        self.live_labeled_entry(parent, 4, 1, "Power", "source_power_var")
        self.live_labeled_entry(parent, 6, 0, "Source X", "source_x_var")
        self.live_labeled_entry(parent, 6, 1, "Source Y", "source_y_var")
        self.live_labeled_entry(parent, 8, 0, "Source Z", "source_z_var")
        self.live_labeled_entry(parent, 8, 1, "Seed", "source_seed_var")
        self.live_labeled_entry(parent, 10, 0, "Source L", "source_l_var")
        self.live_labeled_entry(parent, 10, 1, "Source M", "source_m_var")
        self.live_labeled_entry(parent, 12, 0, "Source N", "source_n_var")
        self.live_labeled_combo(
            parent,
            12,
            1,
            "Direction",
            "source_direction_preset_var",
            self.source_direction_preset_values,
            handler=self.editor._on_source_direction_preset_changed,
            width=14,
        )
        ttk.Button(parent, text="Scene Source Manager...", command=self.editor.open_scene_source_manager).grid(
            row=14,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 0),
        )

    def build_field_controls(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1, uniform="live_field")
        self.live_labeled_combo(
            parent,
            0,
            0,
            "Field type",
            "field_type_var",
            [self.editor._field_type_display_label(value) for value in self.field_type_values],
            handler=self.editor._on_field_type_changed,
            width=13,
        )
        self.live_labeled_entry(parent, 0, 1, "Field value", "field_value_var", sync_fields=True)
        self.live_labeled_entry(parent, 2, 0, "Field samples", "field_count_var", sync_fields=True)
        self.live_labeled_combo(
            parent,
            2,
            1,
            "Image dia",
            "image_diameter_mode_var",
            ("Auto", "Manual"),
            handler=self.editor._on_image_diameter_mode_changed,
        )
        self.live_labeled_combo(
            parent,
            4,
            0,
            "Camera",
            "camera_model_var",
            [self.camera_none_label, *self.camera_names()],
            handler=self.editor._on_camera_model_changed,
            width=22,
        ).grid(columnspan=2)

    def build_trace_controls(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1, uniform="live_trace")
        self.live_labeled_combo(
            parent,
            0,
            0,
            "Object mode",
            "object_mode_var",
            ("Finite", "Infinity"),
            handler=self.editor._on_object_mode_changed,
        )
        self.live_labeled_entry(parent, 0, 1, "Wavelength", "wavelength_var", sync_fields=True)
        self.live_labeled_entry(parent, 2, 0, "Pupil factor", "ray_height_factor_var", sync_fields=True)
        self.live_labeled_combo(
            parent,
            2,
            1,
            "Trace",
            "trace_mode_var",
            ("Auto", "Non-Sequential Preview", "Sequential", "Folded Preview"),
            handler=self.editor._on_trace_mode_changed,
            width=18,
        )
        self.live_labeled_combo(
            parent,
            4,
            0,
            "Aperture",
            "aperture_type_var",
            ("STOP", "EPD", "FNO"),
        )
        self.live_labeled_entry(parent, 4, 1, "Aperture value", "aperture_value_var", sync_fields=True)
        nonseq_menu = getattr(self.editor, "nonseq_target_surface_menu", None)
        self.live_labeled_combo(
            parent,
            6,
            0,
            "NS target",
            "nonseq_target_surface_var",
            nonseq_menu.cget("values") if nonseq_menu is not None else ("Auto",),
        )
        self.live_labeled_entry(parent, 6, 1, "NS hit limit", "nonseq_ns_limit_var")
        ttk.Checkbutton(
            parent,
            text="NS probabilistic coating split",
            variable=self.editor_var("nonseq_energy_probability_var"),
            command=self.inspector._commit_live_control_update,
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(4, 0))

    def build_step_controls(self, parent: tk.Widget) -> None:
        for column in range(2):
            parent.columnconfigure(column, weight=1, uniform="live_step")
        ttk.Button(
            parent,
            text="Accept STEP Placement",
            command=self.inspector.accept_selected_step_placement,
        ).grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Button(
            parent,
            text="Promote STEP Row",
            command=self.inspector.promote_selected_step_to_optical_solid_row,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0), padx=(0, 3))
        ttk.Button(
            parent,
            text="Clear STEP",
            command=self.inspector.clear_step_imports,
        ).grid(row=1, column=1, sticky="ew", pady=(6, 0), padx=(3, 0))
