"""Top toolbar construction for the embedded Open 3D inspector."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

from KrakenOS.UI.widgets import (
    CommitEntry,
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
        # Save the current prescription (including a solve done entirely in 3D) back to
        # the layout .py, so the source file stops drifting from the exported STEP / scene.
        # Both write a <layout>.open3d.json sidecar so the full 3D session (measurements,
        # hidden items, overlay toggles, camera) reproduces on re-open; "Save As" forces a
        # new file (mirrors the main window's File -> Save As).
        pack_command_button(view_toolbar, "Save Layout", command=self.inspector.save_layout, padx=(8, 0))
        pack_command_button(view_toolbar, "Save As", command=self.inspector.save_layout_as, padx=(4, 0))
        # Camera-nav cleanup: the cardinal + Iso camera-preset buttons and the +-90
        # rotate buttons were removed from this toolbar -- the Nav Cube is the single
        # camera-navigation control now (its faces/corners drive set_camera_preset's
        # presets; its roll arrows drive the view roll). What stays is the "Iso up"
        # axis chooser (bugs/0231), which the Nav Cube has no equivalent for: which
        # WORLD axis points up in the Iso view (the other two carry the diagonal
        # horizontal spread). Picking one applies the Iso view immediately; the Nav
        # Cube's corner-Iso views also use the current choice.
        iso_up_menu = create_popup_menu(view_toolbar)
        for axis_label, axis_value in (("Y up (default)", "y"), ("Z up", "z"), ("X up", "x")):
            iso_up_menu.add_radiobutton(
                label=axis_label,
                value=axis_value,
                variable=self.inspector.iso_up_axis_var,
                command=self.inspector._on_iso_up_axis_changed,
            )
        pack_menubutton(view_toolbar, "Iso up ▾", iso_up_menu, padx=(4, 0))
        self.inspector._open3d_iso_up_menu = iso_up_menu
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
        # bugs/0093: the Ray count entry was removed from the top toolbar -- it
        # duplicated the Live Controls (Left Panel) "Ray count" entry (both bound to
        # ray_count_var). The Left Panel one is the single source.
        self.inspector._open3d_toolbar_ray_count_entry = None
        overlay_menu = create_popup_menu(view_toolbar)
        add_menu_checkbuttons(
            overlay_menu,
            (
                MenuCheckbutton("Refs", self.inspector.show_reference_surfaces_var, self.inspector._on_scene_visibility_changed),
                MenuCheckbutton("Det", self.inspector.show_detector_overlays_var, self.inspector._on_scene_visibility_changed),
                MenuCheckbutton("Miss", self.inspector.show_terminal_diagnostics_var, self.inspector._on_scene_visibility_changed),
                # Clipped rays share the 2D show_clipped_rays_var (via _editor_var)
                # so the 3D filter and the main-window "Show clipped rays" checkbox
                # stay in sync both ways (bugs/0061).
                MenuCheckbutton("Clipped", self.inspector._editor_var("show_clipped_rays_var"), self.inspector._on_clipped_rays_changed),
                MenuCheckbutton("Thickness", self.editor.show_physical_distances_var, self.inspector._on_scene_visibility_changed),
                # 3D field-curvature viz (idea #2): translucent curved best-focus
                # surface lofted over the flat detector.
                MenuCheckbutton("Focus surf", self.inspector.show_best_focus_surface_var, self.inspector._on_scene_visibility_changed),
                # 3D distortion viz (idea #2, 2nd half): rectilinear reference grid +
                # its warped real image on the detector.
                MenuCheckbutton("Distortion", self.inspector.show_distortion_grid_var, self.inspector._on_scene_visibility_changed),
                # 3D astigmatism viz (idea #2a): tangential + sagittal best-focus surfaces.
                MenuCheckbutton("Astigmatism", self.inspector.show_astigmatism_var, self.inspector._on_scene_visibility_changed),
                # 3D spot-quality viz (idea #1/#3): per-field RMS spot circles on the detector.
                MenuCheckbutton("Spot map", self.inspector.show_spot_field_map_var, self.inspector._on_scene_visibility_changed),
                # Camera pixel grid (idea #1): the spot footprint on the camera's real pixels.
                MenuCheckbutton("Pixel grid", self.inspector.show_pixel_grid_var, self.inspector._on_scene_visibility_changed),
                # On-detector illumination heatmap (idea #3): coaxial-LED fold-axis dark edges
                # draped on the sensor as a smooth quad (relative illumination, centre = 1.0).
                MenuCheckbutton("Illumination", self.inspector.show_source_illumination_var, self.inspector._on_scene_visibility_changed),
                # The REAL traced LED->BS->object rays, green=reaches FOV / red=clipped at the
                # foreshortened BS-exit stop (the 55*cos45~39 dark-edge mechanism, drawn directly).
                MenuCheckbutton("Illum rays", self.inspector.show_source_illumination_rays_var, self.inspector._on_scene_visibility_changed),
                # Additive full-surface EMISSION from a marked CAD/STL face (bugs/0267): the marked face
                # floods its whole surface with traced rays, isolated from the imaging trace (0266).
                MenuCheckbutton("Illum emission", self.inspector.show_illumination_marker_rays_var, self.inspector._on_scene_visibility_changed),
                # bugs/0354: translucent receiving-angle cone, imaged FOV -> entrance pupil.
                MenuCheckbutton("Accept cone", self.inspector.show_receiving_cone_var, self.inspector._on_scene_visibility_changed),
                # bugs/0355: translucent LED illumination volume, emitting rect -> BS fold -> FOV.
                MenuCheckbutton("Illum volume", self.inspector.show_illumination_volume_var, self.inspector._on_scene_visibility_changed),
            ),
        )
        # flag_20260709_114618_526: face-on the sensor so the on-detector overlays (illumination
        # heatmap etc.) fill the canvas without hand-zooming the Iso view. Snaps the camera down the
        # detector normal, centred + framed to the sensor.
        overlay_menu.add_separator()
        add_menu_commands(
            overlay_menu,
            (MenuCommand("Normal to Sensor", self.inspector.view_normal_to_sensor),),
        )
        pack_menubutton(view_toolbar, "Overlays", overlay_menu, padx=(8, 0))
        self.inspector._open3d_overlay_menu = overlay_menu
        # The Live-panel / Components checkboxes are replaced by the 2D-style
        # ◀ / ▶ collapse arrows on the panels themselves.
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
        # Discard companion: throw away the in-progress recording so a
        # mis-trigger doesn't leave a stray JSON on disk. Always visible
        # for discoverability; no-ops with a status message when no
        # recording is active.
        discard_button = ttk.Button(
            view_toolbar,
            text="Discard rec",
            command=self.inspector.discard_bug_recording,
        )
        discard_button.pack(side="right", padx=(8, 0))
        self.inspector._discard_button = discard_button
        # One-click bug flag: screenshot + scene state + user note. Works
        # standalone or alongside an active recording. Press `s` while
        # hovering over the bug to avoid moving the mouse and losing
        # hover-highlight state.
        flag_button = ttk.Button(
            view_toolbar,
            text="⚑ Flag bug (s)",
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
                MenuCommand("Import Imaging Lens STEP...", lambda: self.inspector.import_step_overlay("lens")),
                MenuCommand("Import Camera STEP...", lambda: self.inspector.import_step_overlay("camera")),
                MenuCommand("Import LED STEP...", lambda: self.inspector.import_step_overlay("led")),
            ),
        )
        cad_target_menu.add_cascade(label="Import STEP", menu=import_step_menu)
        add_menu_commands(
            cad_target_menu,
            (
                MenuCommand(
                    "Import Lens from Folder (replaces scene)...",  # bugs/0381: distinct from Swap
                    self.inspector.import_machine_vision_lens_from_folder,
                ),
                MenuCommand(
                    "Swap Imaging Lens from Folder (keeps scene)...",
                    self.inspector.swap_imaging_lens_from_folder,
                ),
                MenuCommand(
                    "Import Camera from Folder...",
                    self.inspector.import_vendor_camera_from_folder,
                ),
                None,
                MenuCommand("Delete Selected STEP", self.inspector.delete_selected_step),
                MenuCommand("Clear STEP Imports", self.inspector.clear_step_imports),
                None,
                MenuCommand("Arm Selected STEP Carry", self.inspector.start_selected_step_carry),
                # One promotion for every imported STEP: make it a ray-traceable
                # optical solid (mesh body, traced per-physics non-sequentially)
                # and pop the Face Editor so the user assigns face roles. The
                # former Optical Solid Row / Native Rows / Analytic Surfaces split
                # is gone from the UI (analytic/native remain as internal/scripted
                # helpers for the folded-cascade builders).
                MenuCommand("Promote to Optical Element", self.inspector.promote_selected_step_to_optical_solid_row),
                None,
                MenuCommand("Center STEP Axis", self.editor.start_any_step_axis_pick),
                MenuCommand("Snap STEP Surface-Center Normal->Optical Axis", self.inspector.snap_selected_step_normal_to_optical_axis),
                MenuCommand("Snap STEP Pick-Point Normal->Optical Axis", self.inspector.snap_selected_step_pick_point_normal_to_optical_axis),
                MenuCommand("Center STEP Surface->Optical Axis", self.inspector.center_selected_step_surface_to_optical_axis),
                MenuCommand("Glue STEP to Surrogate", self.inspector.glue_selected_step_to_surrogate),
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
                None,
                MenuCommand("Move Elements to Optical Axis", self.inspector.start_axis_to_axis_move),
                MenuCommand("Snap Selected to Optical Axis", self.inspector.start_snap_selected_to_axis),
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
        # Measure tool, moved up here from the Left Panel (Live Controls): CAD-style 2-point
        # measure -> a dimension between two picked edges/surfaces, plus Clear. start_measure_pick
        # sets the "click 2 edges/surfaces" status, so the help text is conveyed at click time.
        pack_command_button(scene_toolbar, "Measure", command=self.inspector.start_measure_pick, padx=(12, 0))
        # bugs/0358: dedicated CAD-style ENTITY measure -- every click picks an edge
        # (closest edge-to-edge distance), no Alt, no axis snap. Plain Measure untouched.
        pack_command_button(scene_toolbar, "Measure E/E", command=self.inspector.start_measure_entity_pick, padx=(4, 0))
        pack_command_button(scene_toolbar, "Clear meas.", command=self.inspector.clear_measurements, padx=(4, 0))
        return scene_toolbar

    def build_carry_toolbar(self, parent: tk.Widget) -> ttk.Frame:
        carry_toolbar = ttk.Frame(parent)
        carry_toolbar.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(carry_toolbar, text="Carry").pack(side="left", padx=(0, 6))
        ttk.Label(carry_toolbar, text="Hold-drag STEP to move freely; Ctrl+drag rotates view.").pack(side="left")
        pack_commit_checkbutton(
            carry_toolbar,
            "Move/Rotate whole body",
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
        # Free-input move/drag snap step (mm): blank = the auto grid, 0 = smooth (continuous drag),
        # any number = snap to exactly that step -- so the BS can be dragged smoothly or to a
        # precise step instead of the coarse auto span/20 placement-handle snap.
        ttk.Label(carry_toolbar, text="Snap mm").pack(side="left", padx=(10, 2))
        ttk.Entry(carry_toolbar, textvariable=self.inspector.carry_snap_mm_var, width=6).pack(side="left")
        pack_commit_checkbutton(
            carry_toolbar,
            "Placement handles",
            variable=self.inspector.show_placement_handles_var,
            command=self.inspector._on_scene_visibility_changed,
            padx=(12, 0),
        )
        return carry_toolbar
