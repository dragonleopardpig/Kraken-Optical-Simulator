"""Top toolbar construction for the embedded Open 3D inspector."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.widgets import (
    MenuCheckbutton,
    MenuCommand,
    add_menu_checkbuttons,
    add_menu_commands,
    create_popup_menu,
    pack_command_button,
    pack_commit_checkbutton,
    pack_commit_combobox,
    pack_menubutton,
)


class Open3DTopControlsPanel:
    """Build the View, Scene, and Carry toolbar rows."""

    def __init__(self, inspector: Any, *, normal_target_choices: Sequence[str]) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.normal_target_choices = tuple(normal_target_choices)

    def build(self, parent: tk.Widget) -> ttk.Frame:
        toolbar_container = ttk.Frame(parent, padding=(8, 8, 8, 0))
        toolbar_container.grid(row=0, column=0, columnspan=3, sticky="ew")
        toolbar_container.columnconfigure(0, weight=1)

        self.build_view_toolbar(toolbar_container)
        self.build_scene_toolbar(toolbar_container)
        self.build_carry_toolbar(toolbar_container)
        return toolbar_container

    def build_view_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        view_toolbar = ttk.Frame(parent)
        view_toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(view_toolbar, text="View").pack(side="left", padx=(0, 6))
        pack_command_button(view_toolbar, "Refresh", command=self.inspector.refresh_from_editor)
        pack_command_button(view_toolbar, "Snapshot", command=self.inspector.save_snapshot, padx=(8, 0))
        ttk.Label(view_toolbar, text="Camera").pack(side="left", padx=(10, 4))
        for label, preset in (
            ("Iso", "iso"),
            ("YZ", "zy"),
            ("XY", "xy"),
            ("XZ", "xz"),
            ("Bottom", "bottom"),
        ):
            pack_command_button(
                view_toolbar,
                label,
                width=max(4, len(label)),
                command=lambda value=preset: self.inspector.set_camera_preset(value),
                padx=(2, 0),
            )
        pack_commit_checkbutton(
            view_toolbar,
            "Show rays",
            variable=self.inspector.show_rays_var,
            command=self.inspector._on_show_rays_changed,
            padx=(12, 0),
        )
        pack_commit_checkbutton(
            view_toolbar,
            "Pick rays",
            variable=self.inspector.ray_pick_enabled_var,
            command=self.inspector._on_ray_pick_changed,
            padx=(8, 0),
        )
        overlay_menu = create_popup_menu(view_toolbar)
        add_menu_checkbuttons(
            overlay_menu,
            (
                MenuCheckbutton("Refs", self.inspector.show_reference_surfaces_var, self.inspector._on_scene_visibility_changed),
                MenuCheckbutton("Det", self.inspector.show_detector_overlays_var, self.inspector._on_scene_visibility_changed),
                MenuCheckbutton("Miss", self.inspector.show_terminal_diagnostics_var, self.inspector._on_scene_visibility_changed),
                MenuCheckbutton("Thickness", self.editor.show_physical_distances_var, self.inspector._on_scene_visibility_changed),
            ),
        )
        pack_menubutton(view_toolbar, "Overlays", overlay_menu, padx=(8, 0))
        self.inspector._open3d_overlay_menu = overlay_menu
        pack_commit_checkbutton(
            view_toolbar,
            "Live panel",
            variable=self.inspector.show_live_controls_panel_var,
            command=self.inspector._on_open3d_panel_visibility_changed,
            padx=(8, 0),
        )
        pack_commit_checkbutton(
            view_toolbar,
            "Components",
            variable=self.inspector.show_scene_components_panel_var,
            command=self.inspector._on_open3d_panel_visibility_changed,
            padx=(8, 0),
        )
        pack_command_button(view_toolbar, "Done 2D", command=self.inspector.finish_stl_placement, side="right", padx=(8, 0))
        pack_command_button(view_toolbar, "Close", command=self.inspector._on_close, side="right", padx=(8, 0))
        # Bug recorder: start/stop button next to Close so it's always visible.
        recorder_button = ttk.Button(
            view_toolbar,
            textvariable=self.inspector.recorder_button_var,
            command=self.inspector.toggle_bug_recording,
        )
        recorder_button.pack(side="right", padx=(8, 0))
        self.inspector._recorder_button = recorder_button
        # One-click bug flag: screenshot + scene state + user note. Works
        # standalone or alongside an active recording.
        flag_button = ttk.Button(
            view_toolbar,
            text="⚑ Flag bug",
            command=self.inspector.flag_bug,
        )
        flag_button.pack(side="right", padx=(8, 0))
        self.inspector._flag_bug_button = flag_button
        return view_toolbar

    def build_scene_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        scene_toolbar = ttk.Frame(parent)
        scene_toolbar.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(scene_toolbar, text="Scene").pack(side="left", padx=(0, 6))

        cad_target_menu = create_popup_menu(scene_toolbar)
        import_step_menu = create_popup_menu(cad_target_menu)
        add_menu_commands(
            import_step_menu,
            (
                MenuCommand("Import Optical STEP...", self.inspector.import_optical_step_overlay),
                MenuCommand("Import Lens STEP...", lambda: self.inspector.import_step_overlay("lens")),
                MenuCommand("Import Camera STEP...", lambda: self.inspector.import_step_overlay("camera")),
                MenuCommand("Import LED STEP...", lambda: self.inspector.import_step_overlay("led")),
            ),
        )
        cad_target_menu.add_cascade(label="Import STEP", menu=import_step_menu)
        add_menu_commands(
            cad_target_menu,
            (
                MenuCommand("Delete Selected STEP", self.inspector.delete_selected_step),
                MenuCommand("Clear STEP Imports", self.inspector.clear_step_imports),
                None,
                MenuCommand("Arm Selected STEP Carry", self.inspector.start_selected_step_carry),
                MenuCommand("Accept STEP Placement", self.inspector.accept_selected_step_placement),
                MenuCommand("Promote STEP to Optical Solid Row", self.inspector.promote_selected_step_to_optical_solid_row),
                MenuCommand("Promote STEP to Native Rows", self.inspector.promote_selected_step_to_native_surface_rows),
                None,
                MenuCommand("Center STEP Axis", self.editor.start_any_step_axis_pick),
                MenuCommand("Snap STEP Surface-Center Normal->Optical Axis", self.inspector.snap_selected_step_normal_to_optical_axis),
                MenuCommand("Snap STEP Pick-Point Normal->Optical Axis", self.inspector.snap_selected_step_pick_point_normal_to_optical_axis),
                MenuCommand("Center STEP Surface->Optical Axis", self.inspector.center_selected_step_surface_to_optical_axis),
                MenuCommand("Obj->LED", self.editor.start_led_object_edge_pick),
                MenuCommand("Export STEP", self.editor.export_3d_step),
                None,
                MenuCommand("Faces...", self.inspector.open_selected_optical_faces),
                MenuCommand("Source Target", self.inspector.start_source_target_pick),
            ),
        )
        pack_menubutton(scene_toolbar, "CAD / target", cad_target_menu)

        placement_menu = create_popup_menu(scene_toolbar)
        add_menu_commands(
            placement_menu,
            (
                MenuCommand("Center Row->Optical Axis", self.inspector.start_center_row_to_ray),
                MenuCommand("Snap Row->Target", self.inspector.start_placement_target_pick),
            ),
        )
        pack_menubutton(scene_toolbar, "Place", placement_menu, padx=(8, 0))

        orientation_menu = create_popup_menu(scene_toolbar)
        add_menu_commands(
            orientation_menu,
            (
                MenuCommand("Orient Row->Target", self.inspector.start_placement_orient_pick),
                MenuCommand("Orient Row->Ray", self.inspector.start_placement_orient_ray_pick),
                MenuCommand("Orient Row->Source", self.inspector.orient_selected_row_to_source_direction),
                MenuCommand("Orient Row->Path", self.inspector.orient_selected_row_to_path_frame),
                None,
                MenuCommand("Orient Row->CAD Axis", self.inspector.orient_selected_row_to_local_axis),
                MenuCommand("Orient Row->Scene Source", self.inspector.orient_selected_row_to_scene_source),
                None,
                MenuCommand("Animate Galvo Scan", self.inspector.start_galvo_scan_animation),
                MenuCommand("Stop Galvo Scan", self.inspector.stop_galvo_scan_animation),
                None,
                MenuCommand("Preview Normal", self.inspector.preview_selected_row_normal_target),
                MenuCommand("Orient Row->Normal", self.inspector.orient_selected_row_to_named_normal_target),
            ),
        )
        pack_menubutton(scene_toolbar, "Orient", orientation_menu, padx=(8, 0))

        self.inspector._open3d_cad_target_menu = cad_target_menu
        self.inspector._open3d_import_step_menu = import_step_menu
        self.inspector._open3d_placement_menu = placement_menu
        self.inspector._open3d_orientation_menu = orientation_menu

        ttk.Label(scene_toolbar, text="Axis").pack(side="left", padx=(12, 4))
        pack_commit_combobox(
            scene_toolbar,
            textvariable=self.inspector.orient_axis_var,
            on_commit=lambda _event: None,
            state="readonly",
            values=("+X", "-X", "+Y", "-Y", "+Z", "-Z"),
            width=4,
        )
        ttk.Label(scene_toolbar, text="Normal").pack(side="left", padx=(12, 4))
        pack_commit_combobox(
            scene_toolbar,
            textvariable=self.inspector.normal_target_var,
            on_commit=lambda _event: None,
            state="readonly",
            values=self.normal_target_choices,
            width=12,
        )
        return scene_toolbar

    def build_carry_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        carry_toolbar = ttk.Frame(parent)
        carry_toolbar.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(carry_toolbar, text="Carry").pack(side="left", padx=(0, 6))
        ttk.Label(carry_toolbar, text="Hold-drag STEP to move freely; Ctrl+drag rotates view.").pack(side="left")
        pack_commit_checkbutton(
            carry_toolbar,
            "Rotation handles",
            variable=self.inspector.show_rotation_handles_var,
            command=self.inspector._toggle_rotation_handles,
            padx=(12, 0),
        )
        ttk.Label(carry_toolbar, text="Rot").pack(side="left", padx=(8, 2))
        pack_commit_combobox(
            carry_toolbar,
            textvariable=self.inspector.rotation_step_deg_var,
            on_commit=self.inspector._on_rotation_step_changed,
            state="readonly",
            values=("15", "30", "45", "90", "180"),
            width=4,
        )
        pack_commit_checkbutton(
            carry_toolbar,
            "Placement handles",
            variable=self.inspector.show_placement_handles_var,
            command=self.inspector._on_scene_visibility_changed,
            padx=(12, 0),
        )
        pack_commit_checkbutton(
            carry_toolbar,
            "Slide along axis",
            variable=self.inspector.slide_along_axis_mode_var,
            command=self.inspector._toggle_axis_slide_mode,
            padx=(12, 0),
        )
        return carry_toolbar
