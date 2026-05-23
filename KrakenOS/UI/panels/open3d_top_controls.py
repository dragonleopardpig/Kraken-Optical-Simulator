"""Top toolbar construction for the embedded Open 3D inspector."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any


class Open3DTopControlsPanel:
    """Build the View, Scene, and Carry toolbar rows."""

    def __init__(self, inspector: Any, *, normal_target_choices: Sequence[str]) -> None:
        self.inspector = inspector
        self.editor = inspector.editor
        self.normal_target_choices = tuple(normal_target_choices)

    def build(self, parent: tk.Widget) -> ttk.Frame:
        toolbar_container = ttk.Frame(parent, padding=(8, 8, 8, 0))
        toolbar_container.grid(row=0, column=0, columnspan=2, sticky="ew")
        toolbar_container.columnconfigure(0, weight=1)

        self.build_view_toolbar(toolbar_container)
        self.build_scene_toolbar(toolbar_container)
        self.build_carry_toolbar(toolbar_container)
        return toolbar_container

    def build_view_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        view_toolbar = ttk.Frame(parent)
        view_toolbar.grid(row=0, column=0, sticky="ew")
        ttk.Label(view_toolbar, text="View").pack(side="left", padx=(0, 6))
        ttk.Button(view_toolbar, text="Refresh", command=self.inspector.refresh_from_editor).pack(side="left")
        ttk.Button(view_toolbar, text="Snapshot", command=self.inspector.save_snapshot).pack(side="left", padx=(8, 0))
        ttk.Label(view_toolbar, text="Camera").pack(side="left", padx=(10, 4))
        for label, preset in (
            ("Iso", "iso"),
            ("YZ", "zy"),
            ("XY", "xy"),
            ("XZ", "xz"),
            ("Bottom", "bottom"),
        ):
            ttk.Button(
                view_toolbar,
                text=label,
                width=max(4, len(label)),
                command=lambda value=preset: self.inspector.set_camera_preset(value),
            ).pack(side="left", padx=(2, 0))
        ttk.Checkbutton(
            view_toolbar,
            text="Show rays",
            variable=self.inspector.show_rays_var,
            command=self.inspector._on_show_rays_changed,
        ).pack(side="left", padx=(12, 0))
        overlay_button = ttk.Menubutton(view_toolbar, text="Overlays")
        overlay_menu = tk.Menu(overlay_button, tearoff=False)
        overlay_menu.add_checkbutton(
            label="Refs",
            variable=self.inspector.show_reference_surfaces_var,
            command=self.inspector._on_scene_visibility_changed,
        )
        overlay_menu.add_checkbutton(
            label="Det",
            variable=self.inspector.show_detector_overlays_var,
            command=self.inspector._on_scene_visibility_changed,
        )
        overlay_menu.add_checkbutton(
            label="Miss",
            variable=self.inspector.show_terminal_diagnostics_var,
            command=self.inspector._on_scene_visibility_changed,
        )
        overlay_button["menu"] = overlay_menu
        overlay_button.pack(side="left", padx=(8, 0))
        self.inspector._open3d_overlay_menu = overlay_menu
        ttk.Button(view_toolbar, text="Done 2D", command=self.inspector.finish_stl_placement).pack(side="right", padx=(8, 0))
        ttk.Button(view_toolbar, text="Close", command=self.inspector._on_close).pack(side="right", padx=(8, 0))
        return view_toolbar

    def build_scene_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        scene_toolbar = ttk.Frame(parent)
        scene_toolbar.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(scene_toolbar, text="Scene").pack(side="left", padx=(0, 6))

        cad_target_button = ttk.Menubutton(scene_toolbar, text="CAD / target")
        cad_target_menu = tk.Menu(cad_target_button, tearoff=False)
        import_step_menu = tk.Menu(cad_target_menu, tearoff=False)
        import_step_menu.add_command(label="Import Optical STEP...", command=self.inspector.import_optical_step_overlay)
        import_step_menu.add_command(label="Import Lens STEP...", command=lambda: self.inspector.import_step_overlay("lens"))
        import_step_menu.add_command(label="Import Camera STEP...", command=lambda: self.inspector.import_step_overlay("camera"))
        import_step_menu.add_command(label="Import LED STEP...", command=lambda: self.inspector.import_step_overlay("led"))
        cad_target_menu.add_cascade(label="Import STEP", menu=import_step_menu)
        cad_target_menu.add_command(label="Delete Selected STEP", command=self.inspector.delete_selected_step)
        cad_target_menu.add_command(label="Clear STEP Imports", command=self.inspector.clear_step_imports)
        cad_target_menu.add_separator()
        cad_target_menu.add_command(label="Arm Selected STEP Carry", command=self.inspector.start_selected_step_carry)
        cad_target_menu.add_command(label="Accept STEP Placement", command=self.inspector.accept_selected_step_placement)
        cad_target_menu.add_command(label="Promote STEP to Optical Solid Row", command=self.inspector.promote_selected_step_to_optical_solid_row)
        cad_target_menu.add_separator()
        cad_target_menu.add_command(label="Center STEP Axis", command=self.editor.start_any_step_axis_pick)
        cad_target_menu.add_command(label="Snap STEP Normal->Optical Axis", command=self.inspector.snap_selected_step_normal_to_optical_axis)
        cad_target_menu.add_command(label="Obj->LED", command=self.editor.start_led_object_edge_pick)
        cad_target_menu.add_command(label="Export STEP", command=self.editor.export_3d_step)
        cad_target_menu.add_separator()
        cad_target_menu.add_command(label="Faces...", command=self.inspector.open_selected_optical_faces)
        cad_target_menu.add_command(label="Source Target", command=self.inspector.start_source_target_pick)
        cad_target_button["menu"] = cad_target_menu
        cad_target_button.pack(side="left")

        placement_button = ttk.Menubutton(scene_toolbar, text="Place")
        placement_menu = tk.Menu(placement_button, tearoff=False)
        placement_menu.add_command(label="Center Row->Optical Axis", command=self.inspector.start_center_row_to_ray)
        placement_menu.add_command(label="Snap Row->Target", command=self.inspector.start_placement_target_pick)
        placement_button["menu"] = placement_menu
        placement_button.pack(side="left", padx=(8, 0))

        orientation_button = ttk.Menubutton(scene_toolbar, text="Orient")
        orientation_menu = tk.Menu(orientation_button, tearoff=False)
        orientation_menu.add_command(label="Orient Row->Target", command=self.inspector.start_placement_orient_pick)
        orientation_menu.add_command(label="Orient Row->Ray", command=self.inspector.start_placement_orient_ray_pick)
        orientation_menu.add_command(label="Orient Row->Source", command=self.inspector.orient_selected_row_to_source_direction)
        orientation_menu.add_command(label="Orient Row->Path", command=self.inspector.orient_selected_row_to_path_frame)
        orientation_menu.add_separator()
        orientation_menu.add_command(label="Orient Row->CAD Axis", command=self.inspector.orient_selected_row_to_local_axis)
        orientation_menu.add_command(label="Orient Row->Scene Source", command=self.inspector.orient_selected_row_to_scene_source)
        orientation_menu.add_separator()
        orientation_menu.add_command(label="Preview Normal", command=self.inspector.preview_selected_row_normal_target)
        orientation_menu.add_command(label="Orient Row->Normal", command=self.inspector.orient_selected_row_to_named_normal_target)
        orientation_button["menu"] = orientation_menu
        orientation_button.pack(side="left", padx=(8, 0))

        self.inspector._open3d_cad_target_menu = cad_target_menu
        self.inspector._open3d_import_step_menu = import_step_menu
        self.inspector._open3d_placement_menu = placement_menu
        self.inspector._open3d_orientation_menu = orientation_menu

        ttk.Label(scene_toolbar, text="Axis").pack(side="left", padx=(12, 4))
        ttk.Combobox(
            scene_toolbar,
            textvariable=self.inspector.orient_axis_var,
            state="readonly",
            values=("+X", "-X", "+Y", "-Y", "+Z", "-Z"),
            width=4,
        ).pack(side="left")
        ttk.Label(scene_toolbar, text="Normal").pack(side="left", padx=(12, 4))
        ttk.Combobox(
            scene_toolbar,
            textvariable=self.inspector.normal_target_var,
            state="readonly",
            values=self.normal_target_choices,
            width=12,
        ).pack(side="left")
        return scene_toolbar

    def build_carry_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        carry_toolbar = ttk.Frame(parent)
        carry_toolbar.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(carry_toolbar, text="Carry").pack(side="left", padx=(0, 6))
        ttk.Label(carry_toolbar, text="Hold-drag STEP to move freely; Ctrl+drag rotates view.").pack(side="left")
        ttk.Checkbutton(
            carry_toolbar,
            text="Rotation handles",
            variable=self.inspector.show_rotation_handles_var,
            command=self.inspector._toggle_rotation_handles,
        ).pack(side="left", padx=(12, 0))
        ttk.Label(carry_toolbar, text="Rot").pack(side="left", padx=(8, 2))
        rotation_step_box = ttk.Combobox(
            carry_toolbar,
            textvariable=self.inspector.rotation_step_deg_var,
            state="readonly",
            values=("15", "30", "45", "90", "180"),
            width=4,
        )
        rotation_step_box.pack(side="left")
        rotation_step_box.bind("<<ComboboxSelected>>", self.inspector._on_rotation_step_changed)
        ttk.Checkbutton(
            carry_toolbar,
            text="Placement handles",
            variable=self.inspector.show_placement_handles_var,
            command=self.inspector._on_scene_visibility_changed,
        ).pack(side="left", padx=(12, 0))
        return carry_toolbar
