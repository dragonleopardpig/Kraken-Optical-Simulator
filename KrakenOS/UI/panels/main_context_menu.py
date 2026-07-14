"""Main editable-table context menu builder."""

from __future__ import annotations

import tkinter as tk
from typing import Any

from KrakenOS.Optimization.variables import OpticalVariable


class MainContextMenu:
    """Own the main surface-table context menu while delegating actions to the editor."""

    def __init__(
        self,
        editor: Any,
        *,
        fields: tuple[str, ...],
        scene_row_source: str,
        object_target_surface: str,
        diffuse_object_surface: str,
        beam_splitter_surface: str,
        coating_preset_names: tuple[str, ...],
        element_arm_role_default: str,
        element_arm_role_values: tuple[str, ...],
    ) -> None:
        object.__setattr__(self, "editor", editor)
        object.__setattr__(self, "fields", tuple(fields))
        object.__setattr__(self, "scene_row_source", scene_row_source)
        object.__setattr__(self, "object_target_surface", object_target_surface)
        object.__setattr__(self, "diffuse_object_surface", diffuse_object_surface)
        object.__setattr__(self, "beam_splitter_surface", beam_splitter_surface)
        object.__setattr__(self, "coating_preset_names", tuple(coating_preset_names))
        object.__setattr__(self, "element_arm_role_default", element_arm_role_default)
        object.__setattr__(self, "element_arm_role_values", tuple(element_arm_role_values))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name in {
            "editor",
            "fields",
            "scene_row_source",
            "object_target_surface",
            "diffuse_object_surface",
            "beam_splitter_surface",
            "coating_preset_names",
            "element_arm_role_default",
            "element_arm_role_values",
        }:
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def show_context_menu(self, event: tk.Event) -> None:
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_index = int(column_id.replace("#", "")) - 1
        field = self.fields[column_index]
        row_index = self._table_item_row_index(row_id)
        if row_index is None:
            source_record = self._table_item_scene_record(row_id)
            if source_record is not None and getattr(source_record, "kind", "") == self.scene_row_source:
                self.table.selection_set(row_id)
                self.table.focus(row_id)
                self._cleanup_current_popup_menu()
                self.current_menu_row_id = row_id
                self.current_menu_field = field
                menu = tk.Menu(self.editor, tearoff=0)
                source_id = str(getattr(source_record, "source_id", "") or "")
                menu.add_command(
                    label="Edit Scene Sources...",
                    command=lambda selected_source_id=source_id: self.open_scene_source_manager(
                        selected_source_id=selected_source_id
                    ),
                )
                menu.add_command(
                    label="Duplicate Source Row",
                    command=lambda selected_source_id=source_id: self.duplicate_scene_source_by_id(selected_source_id),
                )
                source_specs = self._scene_source_specs_for_direct_editing()
                source_index = self._scene_source_index_for_id(source_specs, source_id)
                move_up_state = "normal" if source_index is not None and source_index > 0 else "disabled"
                move_down_state = (
                    "normal"
                    if source_index is not None and source_index < len(source_specs) - 1
                    else "disabled"
                )
                delete_state = "normal" if len(source_specs) > 1 else "disabled"
                menu.add_command(
                    label="Move Source Up",
                    state=move_up_state,
                    command=lambda selected_source_id=source_id: self.move_scene_source_by_id(selected_source_id, "up"),
                )
                menu.add_command(
                    label="Move Source Down",
                    state=move_down_state,
                    command=lambda selected_source_id=source_id: self.move_scene_source_by_id(selected_source_id, "down"),
                )
                menu.add_command(
                    label="Delete Source Row",
                    state=delete_state,
                    command=lambda selected_source_id=source_id: self.delete_scene_source_by_id(selected_source_id),
                )
                menu.add_separator()
                menu.add_command(label="Open Scene Graph", command=self.open_nonseq_scene_graph)
                self._current_popup_menu = menu
                try:
                    menu.tk_popup(event.x_root, event.y_root)
                finally:
                    menu.grab_release()
                self.status_var.set("Source scene rows are edited in Scene Source Manager; they do not consume KrakenOS surface indices.")
                self._schedule_active_cell_border_update()
            return
        if row_id not in self.table.selection():
            if field == "label":
                block_indices = self._element_indices_for_index(self.rows, row_index)
                self._select_table_indices(block_indices or [row_index], focus_index=row_index)
            else:
                self._select_table_indices([row_index], focus_index=row_index)
        self._active_cell = (row_id, column_id)
        if not self._table_cell_enabled(row_index, field):
            self.status_var.set(self._surface_type_disabled_message(row_index, field))
            self._schedule_active_cell_border_update()
        paraxial_target = self._paraxial_solve_target_for_cell(row_index, field)
        paraxial_variable_target = self._paraxial_variable_thickness_target_for_cell(row_index, field)
        best_focus_target = self._best_focus_solve_target_for_cell(row_index, field)
        spec = self._variable_spec_for_field(field)
        row = self.rows[row_index]
        supports_optimization = False
        bounds = None
        if spec is not None and row.surface != "Image" and spec.is_supported(row):
            supports_optimization = True
            bounds = spec.get_bounds(row)
        self._cleanup_current_popup_menu()
        self.current_menu_row_id = row_id
        self.current_menu_field = field
        menu = tk.Menu(self.editor, tearoff=0)
        selected_indices = self._selected_table_indices()
        selected_has_element = any(
            0 <= index < len(self.rows) and bool(self._element_key(self.rows[index]))
            for index in selected_indices
        )
        selected_assignable = any(0 < index < len(self.rows) - 1 for index in selected_indices)
        selected_element_blocks = self._selected_element_blocks()

        convert_menu = tk.Menu(menu, tearoff=0)
        convert_surface_types = (
            "Standard",
            "Aperture",
            "Mirror",
            self.object_target_surface,
            self.diffuse_object_surface,
            self.beam_splitter_surface,
            "Thin Lens",
            "Grating",
            "Image",
        )
        for surface_type in convert_surface_types:
            convert_menu.add_command(
                label=surface_type,
                command=lambda selected=surface_type, index=row_index: self.convert_surface_type(index, selected),
            )
        convert_menu.add_separator()
        convert_menu.add_command(label="Optical CAD/STL Solid...", command=lambda index=row_index: self.convert_row_to_optical_stl_solid(index))
        menu.add_cascade(label="Convert Type", menu=convert_menu)

        insert_menu = tk.Menu(menu, tearoff=0)
        component_specs = (
            ("Singlet", "singlet"),
            ("Doublet", "doublet"),
            ("Flat Mirror", "flat_mirror"),
            ("Object Target", "object_target"),
            ("Diffuse Object", "diffuse_object"),
            ("Plate / Window", "plate"),
            ("Wedge Prism", "wedge_prism"),
            ("Right-Angle Prism", "right_angle_prism"),
            ("Cube Beam Splitter", "cube_beam_splitter"),
        )
        for label, kind in component_specs:
            insert_menu.add_command(
                label=label,
                command=lambda selected=kind, index=row_index: self.insert_surface_context_component(index, selected),
            )
        insert_menu.add_command(
            label="Fold Mirror (rows below follow reflected path)",
            command=lambda index=row_index: self.insert_fold_mirror_below_index(index),
        )
        insert_menu.add_separator()
        insert_menu.add_command(label="Stock Lens Catalog...", command=self.open_stock_lens_importer)
        insert_menu.add_command(label="Optical CAD/STL Solid...", command=self.import_optical_stl_solid)
        insert_menu.add_command(label="Component to Current Path View...", command=self.open_current_path_component_placement)
        machine_vision_names = list(getattr(self, "machine_vision_names", []) or [])
        machine_vision_menu = tk.Menu(insert_menu, tearoff=0)
        machine_vision_menu.add_command(
            label="Import Lens from Folder...",
            command=self.import_machine_vision_lens_from_folder,
        )
        if machine_vision_names:
            machine_vision_menu.add_separator()
            for machine_vision_name in machine_vision_names:
                machine_vision_menu.add_command(
                    label=machine_vision_name,
                    command=lambda value=machine_vision_name: self.insert_machine_vision_lens_by_name(value),
                )
        insert_menu.add_cascade(label="Machine Vision Lens", menu=machine_vision_menu)
        insert_menu.add_command(
            label="Import Vendor Camera from Folder...",
            command=self.import_vendor_camera_from_folder,
        )
        if row.surface == self.beam_splitter_surface:
            insert_menu.add_separator()
            insert_menu.add_command(
                label="Component to Transmitted Path...",
                command=lambda index=row_index: self.open_arm_path_component_placement(index, "Transmit"),
            )
            insert_menu.add_command(
                label="Stock Lens to Transmitted Path...",
                command=lambda index=row_index: self.open_arm_stock_lens_placement(index, "Transmit"),
            )
            insert_menu.add_command(
                label="Component to Reflected Path...",
                command=lambda index=row_index: self.open_arm_path_component_placement(index, "Reflect"),
            )
            insert_menu.add_command(
                label="Stock Lens to Reflected Path...",
                command=lambda index=row_index: self.open_arm_stock_lens_placement(index, "Reflect"),
            )
            insert_menu.add_command(
                label="Detector to Transmitted Path...",
                command=lambda index=row_index: self.open_arm_detector_placement(index, "Transmit"),
            )
            insert_menu.add_command(
                label="Detector to Reflected Path...",
                command=lambda index=row_index: self.open_arm_detector_placement(index, "Reflect"),
            )
        menu.add_cascade(label="Insert Component Below", menu=insert_menu)

        shape_menu = tk.Menu(menu, tearoff=0)
        shape_menu.add_command(label="Shape Builder...", command=lambda index=row_index: self.open_surface_shape_builder(index))
        shape_menu.add_separator()
        shape_menu.add_command(label="Circular clear aperture", command=lambda index=row_index: self.apply_shape_aperture_preset(index, "circular"))
        shape_menu.add_command(label="Rectangular UDA aperture", command=lambda index=row_index: self.apply_shape_aperture_preset(index, "rectangular"))
        shape_menu.add_command(label="Polygon / UDA editor...", command=lambda index=row_index: self.open_surface_shape_builder(index))
        shape_menu.add_command(label="Annulus aperture", command=lambda index=row_index: self.apply_shape_aperture_preset(index, "annulus"))
        shape_menu.add_command(label="Spider mask", command=lambda index=row_index: self.apply_shape_aperture_preset(index, "spider"))
        shape_menu.add_command(label="Rectangular clear aperture", command=lambda index=row_index: self.apply_shape_aperture_preset(index, "rectangular_clear"))
        menu.add_cascade(label="Shape / Aperture", menu=shape_menu)

        material_menu = tk.Menu(menu, tearoff=0)
        material_menu.add_command(label="Glass Catalog Browser...", command=self.open_glass_catalog_browser)
        material_menu.add_separator()
        for glass in ("AIR", "BK7", "F2"):
            material_menu.add_command(label=f"Apply {glass} to selected rows", command=lambda value=glass: self.apply_material_to_selected(value))
        material_menu.add_command(label="Make MIRROR", command=lambda: self.apply_material_to_selected("MIRROR", mirror_surface=True))
        menu.add_cascade(label="Material", menu=material_menu)

        coating_menu = tk.Menu(menu, tearoff=0)
        coating_menu.add_command(label="Coating / Material Editor...", command=lambda index=row_index: self.open_coating_material_editor(index))
        coating_menu.add_separator()
        for preset_name in self.coating_preset_names:
            coating_menu.add_command(
                label=f"Apply {preset_name}",
                command=lambda value=preset_name: self.apply_coating_preset_to_selected(value),
            )
        coating_menu.add_command(label="Enable metal Fresnel mirror mode", command=self.apply_metal_fresnel_mode_to_selected)
        coating_menu.add_separator()
        coating_menu.add_command(
            label="Beam Splitter Settings...",
            command=lambda index=row_index: self.open_beam_splitter_settings(index),
            state=("normal" if row.surface == self.beam_splitter_surface else "disabled"),
        )
        coating_menu.add_command(
            label="Diffuse / BRDF Settings...",
            command=lambda index=row_index: self.open_diffuse_scatter_settings(index),
            state=("normal" if row.surface == self.diffuse_object_surface else "disabled"),
        )
        coating_menu.add_command(
            label="Enable Beam Splitter Fresnel P/S mode",
            command=lambda index=row_index: self.apply_beam_splitter_fresnel_ps(index),
        )
        menu.add_cascade(label="Coating / Polarization", menu=coating_menu)

        geometry_menu = tk.Menu(menu, tearoff=0)
        geometry_menu.add_command(label="Align normal to previous path", command=lambda index=row_index: self.align_surface_normal_to_previous(index))
        geometry_menu.add_command(label="Set incidence angle...", command=lambda index=row_index: self.set_surface_incidence_angle(index))
        geometry_menu.add_separator()
        geometry_menu.add_command(label="Flip / reverse selected element", command=self.flip_selected, state=("normal" if len(selected_indices) >= 2 else "disabled"))
        geometry_menu.add_command(label="Reverse element", command=lambda index=row_index: self.reverse_element_for_row(index), state=("normal" if selected_has_element else "disabled"))
        geometry_menu.add_command(label="Place along current Path view", command=self.assign_selected_to_current_path_view)
        geometry_menu.add_command(label="Add component along current Path view...", command=self.open_current_path_component_placement)
        geometry_menu.add_command(
            label="Edit path-local pose...",
            command=self.open_selected_path_local_pose_editor,
            state=(
                "normal"
                if len(selected_element_blocks) == 1
                and self._metadata_has_path_pose(self._element_metadata(self.rows[selected_element_blocks[0][0]]))
                else "disabled"
            ),
        )
        menu.add_cascade(label="Geometry", menu=geometry_menu)

        element_menu = tk.Menu(menu, tearoff=0)
        element_menu.add_command(
            label="Group selected rows as element",
            command=self.group_selected_as_element,
            state=(
                "normal"
                if len(selected_indices) >= 2
                and self._indices_are_contiguous(selected_indices)
                and selected_indices[0] > 0
                and selected_indices[-1] < len(self.rows) - 1
                else "disabled"
            ),
        )
        element_menu.add_command(label="Ungroup element", command=self.ungroup_selected_elements, state=("normal" if selected_has_element else "disabled"))
        element_menu.add_command(label="Element settings...", command=self.open_element_settings, state=("normal" if len(selected_element_blocks) == 1 else "disabled"))
        element_menu.add_separator()
        element_menu.add_command(label="Copy selected surfaces/elements", command=self.copy_selected_rows_to_clipboard, state=("normal" if self._selected_copy_indices() else "disabled"))
        element_menu.add_command(label="Paste surfaces/elements below selection", command=self.paste_rows_from_clipboard, state=("normal" if self._pasted_surface_rows() else "disabled"))
        element_menu.add_separator()
        element_menu.add_command(label="Move element up", command=self.move_up, state=("normal" if selected_indices else "disabled"))
        element_menu.add_command(label="Move element down", command=self.move_down, state=("normal" if selected_indices else "disabled"))

        leg_catalog = self._leg_catalog()
        if leg_catalog:
            leg_menu = tk.Menu(element_menu, tearoff=0)
            for entry in leg_catalog:
                leg_menu.add_command(
                    label=f"Assign to {entry['label']}",
                    command=lambda selected_key=entry["key"]: self.assign_selected_elements_to_arm_key(selected_key),
                )
            leg_menu.add_separator()
            leg_menu.add_command(
                label="Clear path assignment",
                command=lambda: self.assign_selected_elements_to_arm(self.element_arm_role_default),
            )
            element_menu.add_cascade(
                label="Path assignment",
                menu=leg_menu,
                state=("normal" if selected_assignable else "disabled"),
            )
        else:
            path_catalog = self._arm_catalog()
            if path_catalog:
                path_menu = tk.Menu(element_menu, tearoff=0)
                for entry in path_catalog:
                    path_menu.add_command(
                        label=f"Assign to {entry['label']}",
                        command=lambda selected_key=entry["key"]: self.assign_selected_elements_to_arm_key(selected_key),
                    )
                path_menu.add_separator()
                path_menu.add_command(
                    label="Clear path assignment",
                    command=lambda: self.assign_selected_elements_to_arm(self.element_arm_role_default),
                )
                element_menu.add_cascade(
                    label="Path assignment",
                    menu=path_menu,
                    state=("normal" if selected_assignable else "disabled"),
                )
        arm_menu = tk.Menu(element_menu, tearoff=0)
        for role in self.element_arm_role_values:
            label = "Clear path role" if role == self.element_arm_role_default else f"Assign to {role} path"
            arm_menu.add_command(label=label, command=lambda selected_role=role: self.assign_selected_elements_to_arm(selected_role))
        element_menu.add_cascade(
            label="Path role",
            menu=arm_menu,
            state=("normal" if selected_assignable else "disabled"),
        )
        menu.add_cascade(label="Element", menu=element_menu)

        diagnostics_menu = tk.Menu(menu, tearoff=0)
        diagnostics_menu.add_command(label="Trace to this surface", command=lambda index=row_index: self.set_nonseq_target_to_row(index))
        diagnostics_menu.add_command(label="Make this analysis surface", command=lambda index=row_index: self.set_analysis_surface_to_row(index))
        diagnostics_menu.add_command(
            label="Detector settings...",
            command=lambda index=row_index: self.open_detector_settings(index),
            state=("normal" if row.surface != "Object" else "disabled"),
        )
        diagnostics_menu.add_separator()
        diagnostics_menu.add_command(label="Inspect Ray / Surface Physics", command=self.open_ray_inspector)
        diagnostics_menu.add_command(label="Ray Inspector", command=self.open_ray_inspector)
        diagnostics_menu.add_command(label="Trace Path Inspector", command=self.open_branch_tree_inspector)
        diagnostics_menu.add_command(label="Detector Aperture Report", command=self.open_detector_aperture_report)
        diagnostics_menu.add_command(label="Non-Sequential Scene Graph", command=self.open_nonseq_scene_graph)
        diagnostics_menu.add_command(
            label="Inspect missed / clipped rays",
            command=lambda: (self.open_ray_inspector(), self.status_var.set("Use Ray Inspector hit status and clipped-ray rows to inspect missed rays.")),
        )
        diagnostics_menu.add_separator()
        diagnostics_menu.add_command(label="Validate row physics", command=lambda index=row_index: self.validate_surface_row_physics(index))
        menu.add_cascade(label="Diagnostics", menu=diagnostics_menu)

        advanced_menu = tk.Menu(menu, tearoff=0)
        advanced_menu.add_command(label="Native KrakenOS attributes...", command=lambda index=row_index: self.open_advanced_surface_editor(index))
        advanced_menu.add_command(label="Lens drawing surface properties...", command=self._open_lens_drawing_surface_properties_dialog)
        advanced_menu.add_command(label="Shape Builder...", command=lambda index=row_index: self.open_surface_shape_builder(index))
        advanced_menu.add_command(label="Error Map...", command=lambda index=row_index: self.open_error_map_editor(index))
        if row.surface == "Grating":
            advanced_menu.add_command(
                label="Grating additional settings...",
                command=lambda index=row_index: self.open_surface_additional_settings(index),
            )
        if row.surface == "Mirror":
            advanced_menu.add_command(
                label="Galvo scan overlay...",
                command=lambda index=row_index: self.open_galvo_scan_overlay_settings(index),
            )
        advanced_menu.add_separator()
        advanced_menu.add_command(label="Inspect Optical CAD/STL Solids", command=self.open_optical_stl_diagnostics)
        advanced_menu.add_command(
            label="Assign CAD/STL Optical Faces",
            command=lambda index=row_index: self.open_optical_solid_face_role_editor(index),
        )
        advanced_menu.add_command(label="Place/Orient Selected CAD/STL Solid", command=self.open_optical_stl_placement_assistant)
        menu.add_cascade(label="Advanced", menu=advanced_menu)

        solve_menu = tk.Menu(menu, tearoff=0)
        if supports_optimization and spec is not None:
            marked = self._variable_enabled_for_row(row, spec)
            solve_menu.add_command(
                label=f"{'Unselect' if marked else 'Select'} {spec.label} for optimization",
                command=self.toggle_current_optimization_cell,
            )
            comp_enabled = self._tolerance_variable_compensator_enabled(
                OpticalVariable(row_index, spec.parameter, 0.0, 1.0, name=f"{row.name} {spec.label}")
            )
            solve_menu.add_command(
                label=f"{'Do not use' if comp_enabled else 'Use'} {spec.label} as tolerance compensator",
                command=self.toggle_current_tolerance_compensator,
                state=("normal" if marked else "disabled"),
            )
            coupling = self._tolerance_variable_coupling(
                OpticalVariable(row_index, spec.parameter, 0.0, 1.0, name=f"{row.name} {spec.label}")
            )
            coupling_label = "Set tolerance coupling group..."
            if coupling:
                sign_prefix = "-" if int(coupling.get("sign", 1) or 1) < 0 else ""
                coupling_label = f"Set tolerance coupling group... ({sign_prefix}{coupling.get('group', '')})"
            solve_menu.add_command(
                label=coupling_label,
                command=self.edit_current_tolerance_coupling,
                state=("normal" if marked else "disabled"),
            )
            solve_menu.add_command(
                label="Clear tolerance coupling group",
                command=self.clear_current_tolerance_coupling,
                state=("normal" if marked and coupling else "disabled"),
            )
            manufacturing = self._tolerance_variable_manufacturing(
                OpticalVariable(row_index, spec.parameter, 0.0, 1.0, name=f"{row.name} {spec.label}")
            )
            manufacturing_label = "Set manufacturing metadata..."
            if manufacturing:
                source_type = str(manufacturing.get("source_type", "") or "").strip()
                source_id = str(manufacturing.get("source_id", "") or "").strip()
                manufacturing_label = "Set manufacturing metadata..."
                if source_type or source_id:
                    manufacturing_label = f"Set manufacturing metadata... ({source_type or source_id})"
            solve_menu.add_command(
                label=manufacturing_label,
                command=self.edit_current_tolerance_manufacturing,
                state=("normal" if marked else "disabled"),
            )
            manufacturing_templates = self._normalize_tolerance_manufacturing_templates(
                self.__dict__.get("tolerance_manufacturing_templates", [])
            )
            solve_menu.add_command(
                label="Apply manufacturing template...",
                command=self.apply_current_tolerance_manufacturing_template,
                state=("normal" if marked and manufacturing_templates else "disabled"),
            )
            solve_menu.add_command(
                label="Save manufacturing as template...",
                command=self.save_current_tolerance_manufacturing_template,
                state=("normal" if marked and manufacturing else "disabled"),
            )
            solve_menu.add_command(
                label="Clear manufacturing metadata",
                command=self.clear_current_tolerance_manufacturing,
                state=("normal" if marked and manufacturing else "disabled"),
            )
            solve_menu.add_command(label="Set bounds...", command=self.edit_current_bounds)
            solve_menu.add_command(
                label="Clear bounds",
                command=self.clear_current_bounds,
                state=("normal" if bounds else "disabled"),
            )
            solve_menu.add_separator()
        if paraxial_target is not None:
            solve_menu.add_command(
                label=(
                    "Paraxial Solve Object Distance"
                    if paraxial_target == "object"
                    else "Paraxial Solve Image Distance"
                ),
                command=self.solve_current_paraxial_distance,
            )
            if paraxial_target == "object":
                solve_menu.add_command(label="Set Object to 2F", command=self.set_current_object_to_two_f)
                solve_menu.add_command(label="Set 2F <-> 2F", command=self.set_current_two_f_pair)
            else:
                solve_menu.add_command(label="Set Image to 2F", command=self.set_current_image_to_two_f)
                solve_menu.add_command(label="Set 2F <-> 2F", command=self.set_current_two_f_pair)
        if paraxial_variable_target is not None:
            solve_menu.add_command(
                label="Paraxial Solve This Thickness",
                command=self.solve_current_paraxial_variable_thickness,
            )
        if best_focus_target is not None:
            solve_menu.add_command(
                label="Best Image Solve",
                command=self.solve_current_best_focus_distance,
            )
        if solve_menu.index("end") is None:
            solve_menu.add_command(label="No cell-specific solve/optimization actions", state="disabled")
        menu.add_cascade(label="Optimization / Solves", menu=solve_menu)

        self._post_popup_menu(menu, event.x_root, event.y_root)

