"""Editable table, layout workbench, and path-component actions.

This mixin is a transitional extraction of the large table/workbench region from
``layout_editor.py``.  The methods still operate on the editor instance and use
late-bound editor globals so behavior stays identical while the coordinator file
shrinks; later cleanup can move the remaining constants into smaller dedicated
modules.
"""

from __future__ import annotations

from KrakenOS.UI.camera_database import (
    camera_model_for_step_path,
    refresh_imported_cameras,
)
from KrakenOS.UI.custom_surfaces import encode_custom_surface_value
from KrakenOS.UI.services.camera_folder_import import (
    build_camera_record_from_assets,
    scan_camera_folder,
    write_imported_camera,
)
from KrakenOS.UI.services.fold_insertion import can_insert_fold_mirror, plan_fold_mirror
from KrakenOS.UI.services.machine_vision_folder_import import (
    import_lens_folder,
    render_surrogate_layout_source,
)
from KrakenOS.UI.services.open3d_timing import open3d_timing_event, open3d_timing_span
from KrakenOS.UI.widgets import place_commit_cell_entry


_PROTECTED_GLOBALS = {
    "LayoutTableWorkbenchMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
    "__builtins__",
    "__doc__",
    "__file__",
    "__loader__",
    "__name__",
    "__package__",
    "__spec__",
}

PATH_COMPONENT_DETECTOR = "Detector plane"

_STEP_DISPLAY_HISTORY_SETTING_KEYS = frozenset(
    {
        # Pose-only STEP overlay settings -- undoing one of these keeps
        # the same set of actors in the scene, so the inspector can take
        # the fast translate-only path instead of a full plot refresh.
        # `_step_path` keys are intentionally NOT in this set: when the
        # path flips between None and a file, an overlay needs to be
        # added or removed, which the translate path can't express.
        # Captured in flag_20260531_094104_762 "pressing Ctrl-z to Undo:
        # wierd changed of color and placement of elements." -- a path
        # transition was treated as display-only and the scene was left
        # with a stale STEP actor while the editor thought no overlay
        # was selected.
        "camera_step_rotation_x_deg",
        "camera_step_rotation_y_deg",
        "camera_step_rotation_z_deg",
        "camera_step_axis_offset_xy",
        "camera_step_placement_offset_xyz",
        "lens_step_largest_component_only",
        "lens_step_rotation_x_deg",
        "lens_step_rotation_y_deg",
        "lens_step_rotation_z_deg",
        "lens_step_axis_offset_xy",
        "lens_step_placement_offset_xyz",
        "optical_step_rotation_x_deg",
        "optical_step_rotation_y_deg",
        "optical_step_rotation_z_deg",
        "optical_step_axis_offset_xy",
        "optical_step_placement_offset_xyz",
        "led_step_rotation_x_deg",
        "led_step_rotation_y_deg",
        "led_step_rotation_z_deg",
        "led_object_edge_distance_mm",
        "led_step_object_edge_local_z",
        "led_step_axis_offset_xy",
        "led_step_placement_offset_xyz",
    }
)


def _sync_layout_globals(source: dict[str, object]) -> None:
    """Late-bind layout-editor globals used by the extracted workbench methods."""
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutTableWorkbenchMixin:


    @staticmethod
    def _flatten_table_item_args(*items: object) -> list[str]:
        flattened: list[str] = []
        for item in items:
            if item is None:
                continue
            if isinstance(item, str):
                if item:
                    flattened.append(item)
                continue
            if isinstance(item, (list, tuple, set)):
                flattened.extend(LayoutTableWorkbenchMixin._flatten_table_item_args(*item))
                continue
            text = str(item)
            if text:
                flattened.append(text)
        return flattened

    def _install_border_only_table_selection(self) -> None:
        self._native_table_selection = self.table.selection
        self._native_table_selection_set = self.table.selection_set
        self._native_table_selection_remove = self.table.selection_remove

        def selection() -> tuple[str, ...]:
            selected = tuple(item for item in self._table_selected_items if self.table.exists(item))
            if len(selected) != len(self._table_selected_items):
                self._table_selected_items = list(selected)
            return selected

        def selection_set(*items: object) -> None:
            ordered: list[str] = []
            seen: set[str] = set()
            for item in self._flatten_table_item_args(*items):
                if self.table.exists(item) and item not in seen:
                    ordered.append(item)
                    seen.add(item)
            self._table_selected_items = ordered
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_remove(*items: object) -> None:
            remove = set(self._flatten_table_item_args(*items))
            if remove:
                self._table_selected_items = [item for item in self._table_selected_items if item not in remove]
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_add(*items: object) -> None:
            selected = list(selection())
            seen = set(selected)
            for item in self._flatten_table_item_args(*items):
                if self.table.exists(item) and item not in seen:
                    selected.append(item)
                    seen.add(item)
            self._table_selected_items = selected
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        def selection_toggle(*items: object) -> None:
            selected = list(selection())
            selected_set = set(selected)
            for item in self._flatten_table_item_args(*items):
                if not self.table.exists(item):
                    continue
                if item in selected_set:
                    selected_set.remove(item)
                    selected = [candidate for candidate in selected if candidate != item]
                else:
                    selected.append(item)
                    selected_set.add(item)
            self._table_selected_items = selected
            self._clear_native_table_selection()
            self._schedule_custom_table_selection_changed()

        self.table.selection = selection  # type: ignore[method-assign]
        self.table.selection_set = selection_set  # type: ignore[method-assign]
        self.table.selection_remove = selection_remove  # type: ignore[method-assign]
        self.table.selection_add = selection_add  # type: ignore[method-assign]
        self.table.selection_toggle = selection_toggle  # type: ignore[method-assign]

    def _clear_native_table_selection(self) -> None:
        native_selection = self._native_table_selection
        native_remove = self._native_table_selection_remove
        if native_selection is None or native_remove is None:
            return
        try:
            selected = tuple(native_selection())
        except Exception:
            selected = ()
        if selected:
            try:
                native_remove(*selected)
            except Exception:
                pass

    def _schedule_custom_table_selection_changed(self) -> None:
        if self._table_selection_after_id is not None:
            return
        try:
            self._table_selection_after_id = self.after_idle(self._emit_custom_table_selection_changed)
        except tk.TclError:
            self._table_selection_after_id = None

    def _emit_custom_table_selection_changed(self) -> None:
        self._table_selection_after_id = None
        self._on_table_selection_changed()

    def _current_selected_row_index(self) -> int | None:
        items = self.table.selection()
        if not items:
            return None
        return self._table_item_row_index(items[0])

    def _on_table_selection_changed(self, _event: tk.Event | None = None) -> None:
        self._update_selection_row_borders()
        selected = self.table.selection()
        if selected:
            source_record = self._table_item_scene_record(selected[0])
            if source_record is not None and getattr(source_record, "kind", "") == SCENE_ROW_SOURCE:
                metadata = dict(getattr(source_record, "metadata", {}) or {})
                model = str(metadata.get("model", "") or "Source")
                rays = metadata.get("ray_count", "-")
                self._sync_surface_selection(None, from_table=False)
                self.status_var.set(
                    f"Selected {getattr(source_record, 'label', 'Src')}: {getattr(source_record, 'name', 'Source')} "
                    f"({model}, rays={rays}). Edit source parameters in the Source panel; this row does not consume a KrakenOS surface index."
                )
                return
        self._sync_surface_selection(self._current_selected_row_index(), from_table=True)

    def _clear_table_selection(self) -> None:
        items = list(self.table.get_children())
        if items:
            self.table.selection_remove(*items)
        self.table.focus("")
        self._active_cell = None
        self._hide_active_cell_border()
        self._clear_selection_row_borders()
        self._selection_anchor_row = None
        self._sync_surface_selection(None, from_table=True)
        self.status_var.set("No surface selected")

    def _select_table_indices(self, indices: list[int], *, focus_index: int | None = None) -> None:
        selected_items = [
            item
            for index in indices
            for item in [self._table_item_for_row_index(index)]
            if item is not None
        ]
        if not selected_items:
            return
        self.table.selection_set(selected_items)
        focus_item = self._table_item_for_row_index(focus_index) if focus_index is not None else None
        if focus_item is None:
            focus_item = selected_items[0]
        self.table.focus(focus_item)
        self.table.see(focus_item)
        self._selection_anchor_row = focus_item
        self._schedule_active_cell_border_update()

    def _clear_table_selection_event(self, _event: tk.Event | None = None) -> str:
        self._clear_table_selection()
        return "break"

    def _sync_surface_selection(self, row_index: int | None, *, from_table: bool = False) -> None:
        self._layout_selected_ray_index = None
        # bugs/0145: a table-selection change drives the Open 3D row highlight
        # through here. During a promote the inspector's actor map is mid-rebuild
        # (the retrace+refresh hasn't repopulated `_actor_row_map` yet), so a
        # table-event highlight against that STALE map pinks whatever actor sat at
        # the new solid's index BEFORE it -- the upstream imaging-lens "Lens Front
        # Datum". 0139 killed the SYNCHRONOUS `_select_table_row` trigger, but the
        # deferred `<<TreeviewSelect>>` sync still fires while the map is stale. The
        # promote does its OWN authoritative highlight against the FRESH map (the
        # scene rebuild's re-apply + an explicit `highlight_row`), both via direct
        # `inspector.highlight_row` that bypasses this path -- so suppressing the
        # table-event 3-D sync for the promote window drops only the stale flash.
        suppress_3d_sync = bool(getattr(self, "_suppress_3d_row_selection_sync", False))
        if self._three_d_inspector is not None and not suppress_3d_sync:
            try:
                if self._three_d_inspector.winfo_exists() and self._three_d_inspector.available:
                    self._three_d_inspector.highlight_row(row_index)
            except Exception:
                pass
        if self._legacy_3d_plotter is not None:
            try:
                self._legacy_3d_set_selected_row(self._legacy_3d_plotter, row_index)
            except Exception:
                pass
        self._update_layout_selection_overlay(row_index)
        if from_table and row_index is not None and 0 <= row_index < len(self.rows):
            self.status_var.set(f"Selected row {row_index}: {self.rows[row_index].name}")

    def _select_table_row(self, index: int) -> None:
        row_id = self._table_item_for_row_index(index)
        if row_id is None:
            return
        self.table.selection_set(row_id)
        self.table.focus(row_id)
        self.table.see(row_id)
        self._active_cell = (row_id, "#1")
        self._update_active_cell_border()
        self._sync_surface_selection(index)

    def _startup_refresh_plot(self) -> None:
        if not self.rows:
            return
        self.refresh_plot(suppress_analysis=True)

    def _set_optional_var(self, attr_name: str, value: object) -> None:
        var = self.__dict__.get(attr_name)
        if var is None:
            return
        try:
            var.set(value)
        except Exception:
            pass

    def _clear_imported_step_runtime_state(self) -> None:
        self.imported_camera_step_path = None
        self.imported_lens_step_path = None
        self.imported_optical_step_path = None
        self.imported_led_step_path = None
        self.lens_step_largest_component_only = True
        self.camera_step_rotation_x_deg = 0.0
        self.lens_step_rotation_x_deg = 0.0
        self.optical_step_rotation_x_deg = 0.0
        self.led_step_rotation_x_deg = 0.0
        self.camera_step_rotation_y_deg = 0.0
        self.lens_step_rotation_y_deg = 0.0
        self.optical_step_rotation_y_deg = 0.0
        self.led_step_rotation_y_deg = 0.0
        self.camera_step_rotation_z_deg = 0.0
        self.lens_step_rotation_z_deg = 0.0
        self.optical_step_rotation_z_deg = 0.0
        self.led_step_rotation_z_deg = 0.0
        self.led_object_edge_distance_mm = 0.0
        self.led_step_object_edge_local_z = None
        self.lens_step_axis_offset_xy = (0.0, 0.0)
        self.optical_step_axis_offset_xy = (0.0, 0.0)
        self.camera_step_axis_offset_xy = (0.0, 0.0)
        self.led_step_axis_offset_xy = (0.0, 0.0)
        self.lens_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.optical_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.camera_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = None
        self._open3d_step_overlay_physics_preview_labels = set()

    def _close_scene_viewers_for_layout_replacement(self) -> None:
        # bug 0294: "Import Lens from Folder" can be launched from *inside* the 3D
        # inspector. The import replaces the working layout, which lands here --
        # destroying the very inspector whose handler is still running. Returning
        # to that handler and refreshing the now-dead vtkTkRenderWindowInteractor
        # is a use-after-free that SIGSEGVs on real GL drivers (NVIDIA GLX). When
        # the initiating inspector asks to survive the swap, keep it: it refreshes
        # itself in place once the new layout is applied.
        keep_inspector = bool(
            self.__dict__.get("_keep_scene_viewers_across_layout_replacement")
        )
        inspector = self.__dict__.get("_three_d_inspector")
        if inspector is not None and not keep_inspector:
            try:
                inspector.destroy()
            except Exception:
                pass
            self._three_d_inspector = None
        try:
            self._close_legacy_3d_plotter()
        except Exception:
            self._legacy_3d_plotter = None
            self._legacy_3d_after_id = None

    def _reset_complete_layout_runtime_state(self, *, close_viewers: bool = True) -> None:
        """Clear scene state that must not leak between complete preset loads."""
        # bugs/0053: row-keyed dimension re-anchor overrides are reset up-front on
        # a complete preset load; _apply_layout_settings then restores the loaded
        # layout's own overrides afterward (so this must NOT live in the late
        # _clear_imported_step_runtime_state, which would wipe that restore).
        self._dimension_anchor_overrides = {}
        self.metal_catalogs = []
        self.layout_scene_source_specs = []
        self.layout_scene_row_order = SOURCE_ROW_ORDER_DEFAULT
        self.tolerance_solve_presets = []
        self.tolerance_manufacturing_templates = []
        self.active_tolerance_solve_preset_name = ""
        self._clear_imported_step_runtime_state()
        for cache_name in (
            "_external_cad_mesh_cache",
            "_external_cad_reference_cache",
            "_external_cad_section_cache",
        ):
            cache = self.__dict__.get(cache_name)
            if isinstance(cache, dict):
                cache.clear()
        self._last_scene_bundle = None
        self._last_auto_leg_entries = []
        self._layout_pick_regions = {}
        self._layout_ray_pick_regions = []
        self._set_optional_var("trace_mode_var", "Auto")
        self.trace_mode = "Auto"
        self._set_optional_var("folded_detector_policy_var", FOLDED_DETECTOR_POLICY_DEFAULT)
        self._set_optional_var("nonseq_target_surface_var", "Auto")
        self._set_optional_var("nonseq_ns_limit_var", "200")
        self._set_optional_var("nonseq_energy_probability_var", False)
        self._set_optional_var("arm_view_var", ARM_VIEW_DEFAULT)
        self._set_optional_var("ray_display_mode_var", RAY_DISPLAY_DEFAULT)
        self._set_optional_var("analysis_branch_filter_var", ANALYSIS_PATH_FILTER_DEFAULT)
        self.show_path_labels = True
        self._set_optional_var("show_path_labels_var", True)
        self._set_optional_var("source_model_var", SOURCE_MODEL_DEFAULT)
        self._set_optional_var("pupil_pattern_var", PUPIL_PATTERN_DEFAULT)
        self._set_optional_var("source_radius_var", "5.0")
        self._set_optional_var("source_cone_angle_var", "0.0")
        self._set_optional_var("gaussian_input_mode_var", GAUSSIAN_INPUT_MODE_DEFAULT)
        self._set_optional_var("gaussian_waist_radius_var", "0.5")
        self._set_optional_var("gaussian_waist_offset_var", "0.0")
        self._set_optional_var("gaussian_beam_diameter_var", "1.0")
        self._set_optional_var("gaussian_full_divergence_var", "1.0")
        self._set_optional_var("gaussian_waist_side_var", GAUSSIAN_WAIST_SIDE_DEFAULT)
        self._set_optional_var("gaussian_m2_var", "1.0")
        self._set_optional_var("pupil_rad_var", "0.0")
        self._set_optional_var("pupil_theta_var", "0.0")
        self._set_optional_var("source_power_var", "1.0")
        self._set_optional_var("source_seed_var", "1")
        self._set_optional_var("source_x_var", "0.0")
        self._set_optional_var("source_y_var", "0.0")
        self._set_optional_var("source_z_var", "0.0")
        self._set_optional_var("source_l_var", "0.0")
        self._set_optional_var("source_m_var", "0.0")
        self._set_optional_var("source_n_var", "1.0")
        self._set_optional_var("source_direction_preset_var", "Horizontal +Z (right)")
        self._set_optional_var("source_angular_weight_var", SOURCE_ANGULAR_WEIGHT_DEFAULT)
        self._set_optional_var("detector_bins_var", DETECTOR_BINS_DEFAULT)
        self._set_optional_var("coherent_sum_mode_var", COHERENT_SUM_MODE_DEFAULT)
        self._set_optional_var("branch_field_propagation_mm_var", BRANCH_FIELD_PROPAGATION_MM_DEFAULT)
        self._set_optional_var("wavefront_style_var", WAVEFRONT_STYLE_DEFAULT)
        self._set_optional_var("camera_model_var", CAMERA_NONE_LABEL)
        self._set_optional_var("external_camera_var", "None")
        self._set_optional_var("camera_overlay_mode_var", "Off")
        self._set_optional_var("projection_display_mode_var", PROJECTION_MODE_FULL_3D)
        self.layout_preview_mode = "none"
        self._set_optional_var("layout_preview_mode_var", "none")
        self.selected_analysis_modes = []
        self.analysis_mode = "none"
        self.secondary_analysis_mode = None
        try:
            self._sync_analysis_mode_buttons()
        except Exception:
            pass
        if close_viewers:
            self._close_scene_viewers_for_layout_replacement()

    def _load_reset_system(self) -> None:
        """Reset to a minimal Object + Image system."""
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self.rows = [
            SurfaceRow(surface="Object", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
            SurfaceRow(surface="Image", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
        ]
        self.current_layout_file = None
        self._layout_is_unsaved_import = False  # bugs/0375: a fresh blank layout is not an import
        self._sync_table()
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        self._apply_initial_layout_view_defaults("Reset")

    def reset_layout(self) -> None:
        """Fast UI reset: clear prescription and preview without ray tracing."""
        self._begin_history_capture()
        self._load_reset_system()
        self._commit_history_capture()
        self._clear_preview_after_reset()

    def load_layout_by_name(self, name: str, *, refresh: bool = True) -> None:
        path = self.layout_files.get(name)
        if path is None:
            return
        if self.rows:
            self._begin_history_capture()
        self.current_layout_file = path
        # bugs/0375: a normal menu/Open load ties the layout to this file; the lens
        # importer re-marks it transient AFTER this call (it loads then imports).
        self._layout_is_unsaved_import = False
        had_existing_rows = bool(self.rows)
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(path)
            loaded_rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
        except Exception:
            surfaces = self._extract_surfaces_from_example(path)
            loaded_rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]

        loaded_rows = self._normalized_rows_copy(loaded_rows)
        self._auto_assign_missing_elements(loaded_rows)
        replace_existing = self._is_empty_starter_rows(self.rows)
        append_to_existing = (
            had_existing_rows
            and not replace_existing
            and self._is_insertable_common_layout(name, loaded_rows, info)
        )
        insert_after = self._selected_insert_index() if append_to_existing else None
        if append_to_existing:
            self.rows = self._append_layout_rows(
                self.rows,
                loaded_rows,
                insert_after=insert_after,
                element_name=name,
            )
        else:
            self._reset_complete_layout_runtime_state(close_viewers=True)
            self.rows = loaded_rows
            self._apply_initial_field_defaults()
            self._apply_initial_layout_view_defaults(name)
            self._apply_layout_settings(info.get("settings", {}))

        self._normalize_special_rows()
        # Prompt for any missing on-disk CAD references *before* the
        # table sync and first plot refresh. ``load_layout_by_name`` is
        # the entry point used by the Common Optical Layout / Machine
        # Vision Lens / Examples menus -- without this hook, layouts
        # loaded through those menus skipped the prompt that
        # ``open_layout`` already has, so missing-asset bugs fell
        # silently through the same fallback path. Best-effort wrapped
        # so headless tests that monkeypatch out the dialog don't blow
        # up the load.
        try:
            self._prompt_for_missing_cad_assets()
        except Exception:
            pass
        self._sync_table()
        # bug 0033: a full layout load that restores a camera selection sets
        # ``camera_model_var`` directly (no widget commit), so the coverage
        # auto-fill never ran and the layout opened in the un-covered state.
        # Re-apply it here so loading lands in the covered state, matching an
        # interactive camera pick. Skipped when appending into an existing scene
        # (that path keeps the current camera/field untouched).
        if not append_to_existing and hasattr(self, "_current_camera_model"):
            loaded_camera = self._current_camera_model()
            if loaded_camera != CAMERA_NONE_LABEL:
                self._apply_camera_coverage_autofill(loaded_camera)
        if append_to_existing:
            self._select_inserted_layout_rows(loaded_rows, insert_after=insert_after)
        if had_existing_rows:
            self._commit_history_capture()
        if refresh:
            self.refresh_plot(suppress_analysis=True)
        if path.stem.startswith("machine_vision_"):
            self.layout_var.set("Common Optical Layout")
            self.machine_vision_var.set(name)
        else:
            self.layout_var.set(name)
            self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        action = "Appended" if append_to_existing else "Loaded"
        self.status_var.set(f"{action} {name}. Click Update to run analysis.")

    @staticmethod
    def _is_insertable_common_layout(name: str, _loaded_rows: list[SurfaceRow], info: dict[str, object]) -> bool:
        settings = info.get("settings", {}) if isinstance(info, dict) else {}
        role = ""
        if isinstance(settings, dict):
            role = str(settings.get("layout_role", settings.get("load_mode", ""))).strip().lower()
        if role in {"component", "insert", "insertable"}:
            return True
        if role in {"layout", "replace", "example", "system"}:
            return False
        if name in INSERTABLE_COMMON_LAYOUT_TITLES:
            return True
        return False

    def _layout_component_rows_for_insert(self, layout_rows: list[SurfaceRow], element_name: str = "") -> list[SurfaceRow]:
        additions = component_rows_from_layout(layout_rows, element_name=element_name)
        if not additions:
            return []
        self._remap_inserted_element_labels(additions)
        return additions

    def insert_layout_component_by_name(self, name: str, *, refresh: bool = True) -> None:
        """Insert a component-style common layout without applying its global settings."""
        path = self.layout_files.get(name)
        if path is None:
            messagebox.showerror("Insert Component", f"Common layout not found:\n\n{name}", parent=self)
            return
        info: dict[str, object] = {"surfaces": [], "settings": {}}
        try:
            info = _load_python_data(path)
            loaded_rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
        except Exception:
            try:
                surfaces = self._extract_surfaces_from_example(path)
                loaded_rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
            except Exception as exc:
                messagebox.showerror("Insert Component", f"Could not load {name}:\n\n{exc}", parent=self)
                return

        loaded_rows = self._normalized_rows_copy(loaded_rows)
        self._auto_assign_missing_elements(loaded_rows)
        additions = self._layout_component_rows_for_insert(loaded_rows, element_name=name)
        if not additions:
            messagebox.showinfo("Insert Component", f"{name} has no component rows between Object and Image.", parent=self)
            return

        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Insert Component", f"Could not read the surface table:\n\n{exc}", parent=self)
            return

        insert_after = self._selected_insert_index()
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(additions, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set("Examples")
        message = (
            f"Inserted {name} as {len(additions)} surface row(s) at S{insert_at}; "
            "source, field, pupil, and analysis settings were not changed."
        )
        self.status_var.set(message)
        self.append_progress(message)
        if refresh:
            self.refresh_plot(suppress_analysis=True)

    def insert_machine_vision_lens_by_name(self, name: str, *, refresh: bool = True) -> None:
        """Insert a machine-vision lens surrogate into the current path, independent
        of the top Machine Vision menu.

        The surrogate's optical body (the rows between Object and Image -- the ideal
        blackbox groups and the stop between the vertex datums) is inserted at the
        current selection; the scene's own source/camera/FOV settings are left
        untouched, so an imported lens can then be folded (Insert Fold Mirror) or
        re-centered like any other component.
        """
        if name not in getattr(self, "machine_vision_files", {}):
            messagebox.showerror(
                "Import Machine Vision Lens",
                f"Machine-vision lens not found:\n\n{name}",
                parent=self,
            )
            return
        self.insert_layout_component_by_name(name, refresh=refresh)

    def import_machine_vision_lens_from_folder(
        self, folder: str | None = None, *, dialog_parent=None
    ):
        """Item 3: ingest a whole vendor lens folder into one auto-built surrogate.

        The user picks a folder; everything useful in it is read and a single
        first-order surrogate is synthesised, from the best available optical
        source (tried in order of fidelity):

        * a Zemax sequential prescription (``.zmx``); OR
        * for a real Black-Box lens whose surfaces are encrypted, the System/
          Prescription Data text dump; OR
        * the vendor **datasheet PDF** alone -- most vendors ship only a
          datasheet, so the cardinals are scraped from its spec table.

        The mechanical STEP is wired as the overlay and a wavefront export onto
        the first ideal group.  The emitted ``machine_vision_<slug>.py`` is written
        into the common-layout library, re-discovered, and loaded as the working
        layout -- after which it is also insertable from the right-click Machine
        Vision cascade (item 2) and foldable (item 1) like any other surrogate.

        ``dialog_parent`` re-parents the folder chooser / error dialogs (the Open
        3D inspector passes itself so the chooser is modal to the 3D window).
        Returns the built :class:`SurrogateModel` on success, or ``None`` when the
        chooser was cancelled or the surrogate could not be built.
        """
        parent = dialog_parent if dialog_parent is not None else self
        # bugs/0381: Import REPLACES the whole scene (it loads a fresh single-lens layout).
        # When the working scene is a real assembly (beam splitter / camera / LED / promoted
        # solid), that wipes content the user likely meant to keep -- and "Swap Imaging Lens"
        # sits right next to this in the menu. Confirm, and point at Swap, before destroying
        # it. Skipped for a programmatic call (folder passed) -- the caller opted in.
        if folder is None and self._import_would_discard_scene():
            front, _rear = self._imaging_lens_block_indices()
            swap_hint = (
                '\n\nTo KEEP this assembly and only change the lens, cancel and use '
                '"Swap Imaging Lens from Folder" instead.'
                if front is not None else ""
            )
            if not messagebox.askyesno(
                "Import Lens from Folder — this replaces the whole scene",
                "Importing a lens from a folder REPLACES the entire working scene: the beam "
                "splitter, camera, LED and any promoted solids are removed and a fresh "
                "single-lens layout is loaded." + swap_hint + "\n\nReplace the scene now?",
                parent=parent,
                default=messagebox.NO,
            ):
                self.status_var.set("Import Lens from Folder cancelled; scene kept.")
                return None
        if folder is None:
            folder = filedialog.askdirectory(
                title="Import Machine Vision Lens from Folder", parent=parent
            )
        if not folder:
            return None
        try:
            model = import_lens_folder(folder)
            source = render_surrogate_layout_source(model)
            destination = LAYOUTS_DIR / model.filename
            destination.write_text(source, encoding="utf-8")
        except Exception as exc:
            messagebox.showerror(
                "Import Machine Vision Lens",
                "Could not build a surrogate from this folder:\n\n"
                f"{folder}\n\n{exc}",
                parent=parent,
            )
            return None
        self.load_layouts()
        self.load_layout_by_name(model.title)
        # bugs/0375: the working scene is now a FRESH import -- a library surrogate,
        # not the user's own saved layout. Mark it transient so (a) its stale session
        # sidecar is NOT restored on the rebuild and (b) Save prompts the user to
        # create their own .py rather than overwriting the auto-generated one.
        self._layout_is_unsaved_import = True
        message = (
            f"Imported {model.title} (EFL {model.effl:.4g} mm) from "
            f"{Path(folder).name}; surrogate saved as {model.filename}."
        )
        self.status_var.set(message)
        self.append_progress(message)
        return model

    def _imaging_lens_block_indices(self, rows=None):
        """``(front, rear)`` row indices of the imaging-lens surrogate block -- the
        vertex/lens datum PAIR that brackets the ideal Blackbox groups + aperture stop
        (bugs/0378, the "Swap Imaging Lens" flow). ``(None, None)`` when the scene has
        no such block. This is the block a swap replaces; a beam splitter, fold mirror
        or other component between Object and Image is deliberately NOT part of it."""
        rows = self.rows if rows is None else rows

        def _is_datum(name, side):
            n = (name or "").strip().lower()
            return ("datum" in n or "vertex" in n) and side in n

        front = None
        for index, row in enumerate(rows):
            if _is_datum(getattr(row, "name", ""), "front"):
                front = index
                break  # the FIRST front datum
        if front is None:
            return None, None
        # bugs/0381: the rear datum must be the FIRST one AFTER this front datum -- a TIGHT
        # single-lens block -- not the LAST rear datum in the whole scene. The old
        # first-front/last-rear span swallowed everything between two lens blocks (or up to
        # a later camera/mount "rear vertex"), so a swap spliced them away. Only the lens's
        # own Blackbox/Aperture rows may sit inside the block; anything else (a promoted
        # solid, another element) means this is NOT a clean lens block to swap.
        rear = None
        for index in range(front + 1, len(rows)):
            if _is_datum(getattr(rows[index], "name", ""), "rear"):
                rear = index
                break
        if rear is None or rear <= front:
            return None, None
        for index in range(front + 1, rear):
            name = (getattr(rows[index], "name", "") or "").strip().lower()
            if "promoted" in name or "optical step solid" in name or name in ("object", "image"):
                return None, None
        return front, rear

    # Minimum mechanical clearance (mm) the auto-refocus keeps between the last optical
    # element and the sensor, so the sensor/camera can't be solved INTO it (bugs/0388).
    _SWAP_REFOCUS_MIN_CLEARANCE_MM = 2.0

    def _swap_refocus_min_gap(self) -> float:
        """Minimum gap (mm) the auto-refocus leaves ahead of the sensor so the CAMERA can't be
        solved into the upstream element (e.g. the RA mirror).

        A glued camera's sensor sits ``camera_front_to_sensor_mm`` BEHIND the body's front
        (flange) face, so the body reaches that far toward the upstream element. The clamp must
        reserve room for the whole body, not just the sensor plane -- otherwise best focus
        pulls the sensor to a safe 2 mm yet the body (e.g. the hr25MCX's 11.48 mm flange depth)
        still crashes into the mirror (bugs/0391, follow-up to 0388's sensor-plane-only clamp).
        With no camera glued, fall back to the conservative sensor floor, capped by a thin fold
        mirror's own reserve so it never demands more room than the mirror occupies."""
        clearance = float(self._SWAP_REFOCUS_MIN_CLEARANCE_MM)
        standoff = 0.0
        try:
            standoff = float(self._current_camera_front_to_sensor_mm() or 0.0)
        except Exception:
            standoff = 0.0
        if 0.0 < standoff < 1.0e6:  # bounds also reject NaN/inf without numpy
            # Reserve the whole camera body: sensor floor + the flange-to-sensor depth.
            return clearance + standoff
        rows = getattr(self, "rows", None) or []
        if len(rows) >= 3:
            upstream = rows[-2]
            name = str(getattr(upstream, "name", "") or "").lower()
            if "promoted" in name or "optical step solid" in name or "mirror" in name:
                # A fold mirror's reserve IS the sensor's headroom past it; don't over-demand.
                try:
                    reserve = float(getattr(upstream, "thickness", 0.0) or 0.0)
                except Exception:
                    reserve = 0.0
                if 0.0 < reserve < clearance:
                    return reserve
        return clearance

    def _swap_auto_refocus_to_best_focus(self) -> None:
        """After a lens swap, move the IMAGE to the new lens's best focus (bugs/0388).

        A different lens images at a different plane, but bugs/0383 kept the camera/mounts at
        their absolute positions, so the image is defocused on the fixed sensor. Reuse
        snap_detector_to_image_plane -- it moves ONLY the final gap (image distance), never
        the beam geometry, so it can't reproduce the broken/escaping rays. Then CLAMP that gap
        to a mechanical minimum (``_swap_refocus_min_gap``: a clearance floor PLUS the glued
        camera's flange-to-sensor depth, so the whole camera BODY -- not just the sensor plane
        -- clears the upstream element, bugs/0391) so the camera can never be solved into the
        RA mirror, flagging when focus is clearance-limited rather than colliding. Any
        already-applied thickness bounds are honoured by the underlying solve."""
        rows = getattr(self, "rows", None) or []
        if len(rows) < 3 or str(getattr(rows[-1], "surface", "") or "") != "Image":
            return
        gap_index = len(rows) - 2
        try:
            moved = self.snap_detector_to_image_plane()
        except Exception:
            return
        if not moved:
            return
        min_gap = self._swap_refocus_min_gap()
        try:
            gap = float(getattr(rows[gap_index], "thickness", 0.0) or 0.0)
        except Exception:
            return
        if gap < min_gap:
            try:
                rows[gap_index].thickness = float(min_gap)
            except Exception:
                return
            self.status_var.set(
                f"Swapped lens; focus limited to {min_gap:.1f} mm so the camera body clears "
                "the upstream element (best focus would collide it with the RA mirror)."
            )

    @staticmethod
    def _swap_preserves_downstream(rows, rear_index) -> bool:
        """Should a lens swap keep the first row AFTER the lens block at its absolute axial
        position? (bugs/0383) Yes when a PHYSICAL element (a fold mirror / camera / mount)
        follows the lens; No for a bare lens whose next row is the terminal image (there the
        image follows the new back focal distance)."""
        downstream_index = int(rear_index) + 1
        if downstream_index >= len(rows):
            return False
        name = (getattr(rows[downstream_index], "name", "") or "").lower()
        return "image" not in name

    @staticmethod
    def _swap_downstream_gap(rows, rear_index, downstream_start_z):
        """The new Rear Datum thickness that lands the first downstream row back at
        ``downstream_start_z`` (its pre-swap absolute z), or None if that would be negative
        (the replacement lens is longer than the space to the downstream mount)."""
        new_rear_start = sum(
            float(getattr(r, "thickness", 0.0) or 0.0) for r in rows[: int(rear_index)]
        )
        gap = float(downstream_start_z) - new_rear_start
        return gap if gap >= 0.0 else None

    def _import_would_discard_scene(self) -> bool:
        """True when replacing the working layout would throw away user-built assembly
        content -- a beam splitter / camera / LED overlay or a promoted solid (bugs/0381).

        "Import Lens from Folder" loads a FRESH single-lens layout and wipes the scene;
        "Swap Imaging Lens" keeps it. The two commands sit next to each other, so this
        drives a confirmation that steers the user to Swap when Import would destroy an
        assembly they likely meant to keep."""
        for attr in ("imported_camera_step_path", "imported_led_step_path", "imported_optical_step_path"):
            if getattr(self, attr, None):
                return True
        for row in (getattr(self, "rows", None) or []):
            name = (getattr(row, "name", "") or "").lower()
            if "promoted" in name or "optical step solid" in name:
                return True
        return False

    def _apply_swapped_lens_step_settings(self, settings) -> None:
        """Rewire the lens-STEP overlay GEOMETRY to the swapped-in lens: its STEP path +
        largest-component flag ONLY. The overlay's SCENE POSE -- rotation, axis offset,
        placement offset, flip -- is PRESERVED from the lens it replaces (bugs/0381).

        bugs/0378 originally reset the pose to the fresh single-lens FOLDER's defaults.
        In a folded assembly the user has aligned the old lens onto the fold leg (a real
        rotation + offset), and the fresh folder's default pose is on-axis for a bare
        single-lens layout -- so the reset snapped the swapped lens OFF the fold leg to a
        default (vertical) orientation: the "multiple misplacement after swap" flag. A
        swap changes the lens, not where the user put it; a different lens LENGTH is a
        small along-axis nudge the user makes, not a re-orientation. The camera / LED /
        optical overlays and source/field/pupil settings are likewise left untouched."""
        settings = settings if isinstance(settings, dict) else {}
        path = settings.get("lens_step_path")
        self.imported_lens_step_path = Path(str(path)).expanduser() if path else None
        self.lens_step_largest_component_only = bool(settings.get("lens_step_largest_component_only", True))
        # rotation_{x,y,z}_deg / axis_offset_xy / placement_offset_xyz / reverse_direction:
        # PRESERVED (untouched) so the swapped lens keeps the pose the user aligned it to.

    def swap_imaging_lens_from_folder(self, folder: str | None = None, *, dialog_parent=None, refresh: bool = True):
        """SWAP the scene's imaging-lens surrogate (rows + STEP overlay) for a newly
        imported lens, IN PLACE (bugs/0378).

        The new lens's optical body (its Front..Rear vertex-datum block) replaces the
        old one at the SAME front-datum position, so it sits on-axis where the old lens
        was; Object, beam splitter, LED, camera, FOV and all source/field/pupil settings
        are preserved. The image side follows the new lens's back focal distance (a
        different lens genuinely images at a different plane; the glued camera tracks it).

        This is distinct from **Add Imaging Lens** (a SECOND lens on another/the same
        axis). Returns the built :class:`SurrogateModel`, or ``None`` on cancel / no
        lens to swap / build failure.
        """
        parent = dialog_parent if dialog_parent is not None else self
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception:
            pass
        front, rear = self._imaging_lens_block_indices()
        if front is None:
            messagebox.showerror(
                "Swap Imaging Lens",
                "This scene has no imaging-lens surrogate (Front/Rear Vertex Datum) to swap.\n\n"
                "Use Add Imaging Lens to add one first.",
                parent=parent,
            )
            return None
        if folder is None:
            folder = filedialog.askdirectory(
                title="Swap Imaging Lens -- choose the replacement lens folder", parent=parent
            )
        if not folder:
            return None
        try:
            model = import_lens_folder(folder)
            source = render_surrogate_layout_source(model)
            destination = LAYOUTS_DIR / model.filename
            destination.write_text(source, encoding="utf-8")
            new_info = _load_python_data(destination)
            new_rows = self._normalized_rows_copy(
                [self._row_from_layout_item(item) for item in new_info["surfaces"]]
            )
        except Exception as exc:
            messagebox.showerror(
                "Swap Imaging Lens",
                f"Could not build a surrogate from this folder:\n\n{folder}\n\n{exc}",
                parent=parent,
            )
            return None
        new_front, new_rear = self._imaging_lens_block_indices(new_rows)
        if new_front is None:
            messagebox.showerror(
                "Swap Imaging Lens",
                "The imported lens has no Front/Rear Vertex Datum block to swap in.",
                parent=parent,
            )
            return None
        raw_block = new_rows[new_front:new_rear + 1]
        new_block = self._normalized_rows_copy(raw_block)
        # bugs/0385: _normalized_rows_copy treats the slice as a STANDALONE layout and
        # forces its FIRST row -> "Object" and LAST row -> "Image". This block is spliced
        # into the MIDDLE of the scene, where its ends are the lens Front/Rear Vertex
        # DATUMS (surface "Standard"). An Object-surfaced front datum is SKIPPED by the
        # fold-override follower walk (nonseq_output_ports), so on a folded scene the
        # swapped lens overlay anchors to a row that no longer folds and renders UNFOLDED
        # off the mirror leg (the "lens misplaced/vertical after swap" flag). Restore the
        # datum ends' real surface so the block stays a proper mid-scene lens block.
        if new_block and raw_block:
            new_block[0].surface = raw_block[0].surface
            new_block[-1].surface = raw_block[-1].surface
        # bugs/0383: preserve the DOWNSTREAM elements' axial positions across the swap.
        # The old lens block's Rear Datum thickness is the SCENE gap to whatever follows
        # the lens -- a fold mirror, camera or image the user placed -- NOT part of the
        # lens. The fresh lens folder carries its own bare rear thickness (often ~0), so a
        # naive splice collapses that downstream arm onto the lens (the "misplaced after
        # swap" flag: an RA mirror + camera + image jumped ~100 mm toward the lens). When a
        # PHYSICAL element (a mount / promoted solid, not the terminal image) follows the
        # lens, keep the first downstream row at its ABSOLUTE axial position by absorbing
        # the lens-length change into the new Rear Datum thickness. A bare lens (image
        # immediately after) keeps letting the image follow the new back focal distance.
        downstream_start_z = (
            sum(float(getattr(r, "thickness", 0.0) or 0.0) for r in self.rows[:rear + 1])
            if self._swap_preserves_downstream(self.rows, rear) else None
        )
        self._begin_history_capture()
        self.rows = list(self.rows[:front]) + list(new_block) + list(self.rows[rear + 1:])
        self._apply_swapped_lens_step_settings(new_info.get("settings", {}))
        self._auto_assign_missing_elements(self.rows)
        self._normalize_special_rows()
        # bugs/0383: restore the downstream anchor AFTER normalisation (which recomputes the
        # datum thicknesses from the new lens and would otherwise re-collapse the arm). The
        # new Rear Datum's thickness is set so the first downstream row keeps its absolute
        # axial position -- fold mirror / camera / image stay put.
        if downstream_start_z is not None:
            _swap_front, swap_rear = self._imaging_lens_block_indices()
            if swap_rear is not None and 0 <= swap_rear < len(self.rows):
                gap = self._swap_downstream_gap(self.rows, swap_rear, downstream_start_z)
                if gap is not None:
                    try:
                        self.rows[swap_rear].thickness = float(gap)
                    except Exception:
                        pass
        self._sync_table()
        self.load_layouts()  # discover the new library surrogate (also insertable later)
        self._commit_history_capture()
        # bugs/0388: the swapped lens focuses at a different plane; 0383 kept the camera/mounts
        # at their absolute positions, so the image is defocused on the sensor. Auto re-solve
        # by moving the image to best focus, clamped so it never collides with the RA mirror.
        try:
            self._swap_auto_refocus_to_best_focus()
        except Exception as exc:
            self.append_debug(f"swap auto-refocus skipped: {exc}")
        message = (
            f"Swapped imaging lens -> {model.title} (EFL {model.effl:.4g} mm) in place; "
            "Object / beam splitter / LED / camera / FOV preserved."
        )
        self.status_var.set(message)
        self.append_progress(message)
        # bugs/0386: the 2D refresh here is a FULL system build + trace (~5s on a folded
        # multi-STEP scene). When the swap is driven from the Open 3D inspector, the wrapper
        # immediately calls _apply_model_change() -- which retraces the 3D AND marks the 2D
        # stale for a later redraw -- so this 2D trace is pure redundant work that DOUBLES
        # the freeze. The inspector passes refresh=False; the 2D UI keeps refresh=True.
        if refresh and hasattr(self, "refresh_plot"):
            self.refresh_plot(suppress_analysis=True)
        return model

    def import_vendor_camera_from_folder(
        self, folder: str | None = None, *, dialog_parent=None, refresh_open_3d: bool = True
    ):
        """Camera analogue of :meth:`import_machine_vision_lens_from_folder`:
        ingest a whole vendor *camera* folder, register its sensor as a
        ``CAMERA_DATABASE`` entry, then import the mechanical STEP as the camera
        body -- which couples the surrogate to that sensor (field -> sensor
        half-diagonal, image circle -> sensor) exactly like picking the camera
        from the dropdown.

        The folder must carry the mechanical ``STEP`` plus a spec source: the
        vendor **datasheet PDF** (its spec table is scraped) or a curated
        ``.json`` sidecar with at least ``sensor_width_mm`` / ``sensor_height_mm``
        (for a datasheet whose text cannot be extracted).  The record is
        persisted to ``attachment/Cameras/imported_cameras.json`` and folded into
        the live database, so re-importing or a fresh session both find it.

        ``dialog_parent`` re-parents the folder chooser / error dialogs (the Open
        3D inspector passes itself).  Returns the built
        :class:`~KrakenOS.UI.services.camera_folder_import.ImportedCamera` on
        success, or ``None`` when cancelled or the record could not be built.
        """
        parent = dialog_parent if dialog_parent is not None else self
        if folder is None:
            folder = filedialog.askdirectory(
                title="Import Vendor Camera from Folder", parent=parent
            )
        if not folder:
            return None
        try:
            assets = scan_camera_folder(folder)
            if assets.primary_step is None:
                raise ValueError(
                    "No STEP (.step / .stp) file found in this folder; the camera "
                    "body CAD is required to place the camera and couple its sensor."
                )
            imported = build_camera_record_from_assets(assets)
            # bugs/0309: a vendor datasheet carries the flange-to-sensor optical
            # distance only in the mechanical drawing (BC-OM25M = 12 mm), so ask the
            # user for it here -- before persist -- when it could not be scraped, so
            # the sensor / image plane snaps to its true axial location.
            self._prompt_camera_flange_distance(imported, parent)
            write_imported_camera(imported.name, imported.record)
            # Fold the just-written record into the live CAMERA_DATABASE so the
            # STEP import below reverse-resolves it (no app restart needed).
            refresh_imported_cameras()
        except Exception as exc:
            messagebox.showerror(
                "Import Vendor Camera",
                "Could not import a camera from this folder:\n\n"
                f"{folder}\n\n{exc}",
                parent=parent,
            )
            return None
        # Import the vendor STEP as the camera body.  Because the sensor is now a
        # known CAMERA_DATABASE entry, import_camera_step reverse-resolves it and
        # auto-fills the field / image circle to the sensor -- the same complete
        # state as picking the camera from the dropdown.
        self.import_camera_step(
            path=assets.primary_step, dialog_parent=parent, refresh_open_3d=refresh_open_3d
        )
        message = (
            f"Imported camera {imported.name} from {Path(folder).name}: registered "
            f"its sensor and placed {assets.primary_step.name}."
        )
        self.status_var.set(message)
        self.append_progress(message)
        return imported

    def _apply_camera_flange_distance(self, imported, value_provider):
        """Stamp the flange-to-sensor (optical) distance onto a freshly imported
        camera record when the folder import could not recover it (bugs/0309).

        A vendor datasheet gives this distance only in the mechanical drawing
        (BC-OM25M = 12 mm), so ``build_camera_record_from_assets`` leaves
        ``camera_front_to_sensor_mm`` unset and the sensor / image plane cannot snap
        to its true axial location (``_current_camera_front_to_sensor_mm`` reads 0).
        ``value_provider()`` returns the value in mm (or ``None`` to skip). The
        provider is INJECTED so the decision is testable without a Tk dialog. Returns
        the applied value, or ``None`` when already known, declined, or invalid.
        """
        record = imported.record
        existing = record.get("camera_front_to_sensor_mm")
        try:
            if existing is not None and float(existing) > 0.0:
                return None  # already scraped -- do not re-prompt or overwrite
        except (TypeError, ValueError):
            pass
        value = value_provider()
        if value is None:
            return None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        if not (0.0 < value < 1.0e6):
            return None
        record["camera_front_to_sensor_mm"] = value
        imported.notes.append(
            f"Flange-to-sensor (optical) distance set to {value:g} mm from the import "
            "dialog (the datasheet carries it only in the mechanical drawing)."
        )
        return value

    def _prompt_camera_flange_distance(self, imported, parent):
        """Ask the user for the camera's flange-to-sensor optical distance when the
        folder import could not recover it (bugs/0309). It is a mechanical-drawing
        dimension, absent from both the spec table and the STEP, so it cannot be
        scraped. Cancel / blank leaves the record unchanged -- sensor size and FOV
        coupling are unaffected, only the axial image-plane snap is skipped. Returns
        the applied value or ``None``.
        """
        def provider():
            try:
                return simpledialog.askfloat(
                    "Camera Flange-to-Sensor Distance",
                    (
                        f"'{imported.name}': the datasheet does not list the optical "
                        "distance from the lens-mount flange to the sensor (it appears "
                        "only in the mechanical drawing -- e.g. BC-OM25M = 12 mm).\n\n"
                        "Enter it in millimetres so the sensor / image plane lands at "
                        "the real sensor location. Cancel to skip (sensor size and FOV "
                        "coupling are unaffected; only the axial snap is skipped)."
                    ),
                    parent=parent,
                    minvalue=0.0,
                    maxvalue=1000.0,
                )
            except Exception:
                return None

        return self._apply_camera_flange_distance(imported, provider)

    def _selected_operand_labels(self) -> list[str]:
        if "merit_mode_list" not in self.__dict__:
            return [str(label) for label in getattr(self, "_headless_selected_operand_labels", [])]
        return [self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()]

    def _set_selected_operand_labels(self, labels: list[str]) -> None:
        if "merit_mode_list" not in self.__dict__:
            self._headless_selected_operand_labels = [str(label) for label in labels]
            return
        self.merit_mode_list.selection_clear(0, "end")
        wanted = {str(label) for label in labels}
        for index in range(self.merit_mode_list.size()):
            label = self.merit_mode_list.get(index)
            if label in wanted:
                self.merit_mode_list.selection_set(index)
        self._update_operand_setup_visibility()

    def _capture_editor_state(self) -> dict[str, object]:
        selected_indices = []
        if hasattr(self, "table"):
            try:
                selected_indices = self._selected_table_indices()
            except Exception:
                selected_indices = []
        active_cell = None
        if self._active_cell is not None:
            row_id, field = self._active_cell
            try:
                row_index = self._table_item_row_index(row_id)
                active_cell = None if row_index is None else {"row": int(row_index), "field": str(field)}
            except Exception:
                active_cell = None
        layout_path = str(self.current_layout_file) if self.current_layout_file is not None else None
        return {
            "rows": [asdict(row) for row in self.rows],
            "settings": self._collect_layout_settings(),
            "selected_indices": selected_indices,
            "active_cell": active_cell,
            "current_layout_file": layout_path,
        }

    def _begin_history_capture(self, _event: tk.Event | None = None) -> None:
        if self._history_restoring or self._history_pending_state is not None:
            return
        self._history_pending_state = self._capture_editor_state()

    def _commit_history_capture(self) -> None:
        if self._history_restoring:
            self._history_pending_state = None
            return
        snapshot = self._history_pending_state
        self._history_pending_state = None
        if snapshot is None:
            return
        current = self._capture_editor_state()
        if snapshot == current:
            return
        self._undo_stack.append(snapshot)
        if len(self._undo_stack) > self._history_limit:
            self._undo_stack = self._undo_stack[-self._history_limit :]
        self._redo_stack.clear()
        self._update_undo_redo_buttons()

    def _push_history_snapshot(self) -> None:
        if self._history_restoring:
            return
        self._history_pending_state = self._capture_editor_state()
        self._commit_history_capture()

    @staticmethod
    def _history_rows_equal(left: dict[str, object] | None, right: dict[str, object] | None) -> bool:
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        return left.get("rows", []) == right.get("rows", [])

    @staticmethod
    def _history_settings_delta_keys(left: dict[str, object] | None, right: dict[str, object] | None) -> set[str]:
        if not isinstance(left, dict) or not isinstance(right, dict):
            return set()
        left_settings = left.get("settings", {})
        right_settings = right.get("settings", {})
        if not isinstance(left_settings, dict) or not isinstance(right_settings, dict):
            return set()
        keys = set(left_settings) | set(right_settings)
        return {key for key in keys if left_settings.get(key) != right_settings.get(key)}

    def _history_restore_is_open3d_step_display_only(
        self,
        previous_state: dict[str, object] | None,
        target_state: dict[str, object],
    ) -> bool:
        if self.__dict__.get("_three_d_inspector") is None:
            return False
        if not self._history_rows_equal(previous_state, target_state):
            return False
        if not isinstance(previous_state, dict):
            return False
        if previous_state.get("current_layout_file") != target_state.get("current_layout_file"):
            return False
        changed_settings = self._history_settings_delta_keys(previous_state, target_state)
        if not changed_settings or not changed_settings <= _STEP_DISPLAY_HISTORY_SETTING_KEYS:
            return False
        inspector = self.__dict__.get("_three_d_inspector")
        try:
            if inspector is None or not inspector.winfo_exists():
                return False
        except Exception:
            return False
        try:
            return not bool(inspector.show_rays_var.get())
        except Exception:
            return False

    @staticmethod
    def _history_setting_vector(
        state: dict[str, object] | None,
        key: str,
        *,
        length: int,
    ) -> tuple[float, ...] | None:
        if not isinstance(state, dict):
            return None
        settings = state.get("settings", {})
        if not isinstance(settings, dict):
            return None
        value = settings.get(key)
        if not isinstance(value, (list, tuple)) or len(value) < length:
            return None
        try:
            vector = tuple(float(value[index]) for index in range(length))
        except Exception:
            return None
        return vector

    def _history_step_placement_delta(
        self,
        previous_state: dict[str, object] | None,
        target_state: dict[str, object],
        changed_settings: set[str],
    ) -> tuple[str, tuple[float, float, float]] | None:
        if len(changed_settings) != 1:
            return None
        key = next(iter(changed_settings))
        suffix = "_step_placement_offset_xyz"
        if not key.endswith(suffix):
            return None
        label = key[: -len(suffix)]
        if label not in {"camera", "lens", "optical", "led"}:
            return None
        previous = self._history_setting_vector(previous_state, key, length=3)
        target = self._history_setting_vector(target_state, key, length=3)
        if previous is None or target is None:
            return None
        delta = tuple(float(target[index] - previous[index]) for index in range(3))
        if not any(abs(value) > 1e-12 for value in delta):
            return None
        return label, delta

    def _refresh_history_restore_views(
        self,
        *,
        previous_state: dict[str, object] | None,
        target_state: dict[str, object],
        changed_settings: set[str],
        display_only_open3d_step: bool,
    ) -> None:
        if display_only_open3d_step:
            open3d_timing_event("history_restore_skip_plot_refresh", reason="open3d_step_display_only")
            placement_delta = self._history_step_placement_delta(previous_state, target_state, changed_settings)
            inspector = self.__dict__.get("_three_d_inspector")
            if placement_delta is not None and inspector is not None:
                label, delta = placement_delta
                try:
                    moved = int(inspector._translate_step_overlay_actors(label, delta))
                except Exception as exc:
                    moved = 0
                    self.append_debug(f"Open 3D history actor translate failed: {exc}")
                open3d_timing_event(
                    "history_restore_actor_translate",
                    label=label,
                    moved=moved,
                    delta_xyz=list(delta),
                )
                if moved > 0:
                    return
            try:
                self._refresh_open_3d_views(force_retrace=False)
            except Exception as exc:
                self.append_debug(f"Open 3D history display-only refresh failed: {exc}")
            return
        with open3d_timing_span("history_restore_plot_refresh"):
            self.refresh_plot()

    def _clear_step_runtime_after_history_restore(self, changed_settings: set[str]) -> None:
        labels_to_clear: set[str] = set()
        for key in set(changed_settings or set()):
            key_text = str(key or "").strip().lower()
            for label in ("lens", "optical", "camera", "led"):
                if key_text.startswith(f"{label}_step_"):
                    labels_to_clear.add(label)
        if labels_to_clear:
            try:
                service = self._open3d_trace_refresh_service()
                for label in labels_to_clear:
                    service.clear_step_overlay_physics_preview(label)
            except Exception:
                pass
        inspector = self.__dict__.get("_three_d_inspector")
        if inspector is None:
            return
        try:
            if not inspector.winfo_exists():
                return
        except Exception:
            return
        try:
            inspector._clear_step_overlay_interaction_state()
        except Exception as exc:
            self.append_debug(f"Open 3D history STEP interaction clear failed: {exc}")

    def _restore_history_state(
        self,
        state: dict[str, object],
        *,
        previous_state: dict[str, object] | None = None,
        action: str = "restore",
    ) -> None:
        display_only_open3d_step = self._history_restore_is_open3d_step_display_only(previous_state, state)
        changed_settings = sorted(self._history_settings_delta_keys(previous_state, state))
        open3d_timing_event(
            "history_restore_requested",
            action=action,
            display_only_open3d_step=display_only_open3d_step,
            changed_settings=",".join(changed_settings[:32]),
            changed_setting_count=len(changed_settings),
        )
        with open3d_timing_span(
            "history_restore",
            action=action,
            display_only_open3d_step=display_only_open3d_step,
        ):
            self._history_restoring = True
            try:
                rows = state.get("rows", [])
                restored_rows = [SurfaceRow(**dict(item)) for item in rows if isinstance(item, dict)]
                self.rows = self._normalized_rows_copy(restored_rows)
                layout_path = state.get("current_layout_file")
                self.current_layout_file = Path(layout_path) if isinstance(layout_path, str) and layout_path else None
                self._sync_table()
                self._apply_layout_settings(state.get("settings", {}))
                self._normalize_special_rows()
                self._sync_table()
                selected_indices = [int(index) for index in state.get("selected_indices", []) if isinstance(index, int)]
                items = list(self.table.get_children())
                selected_items = [items[index] for index in selected_indices if 0 <= index < len(items)]
                if selected_items:
                    self.table.selection_set(selected_items)
                    self.table.focus(selected_items[0])
                    self.table.see(selected_items[0])
                else:
                    self.table.selection_remove(*items)
                active_cell = state.get("active_cell")
                self._active_cell = None
                if isinstance(active_cell, dict):
                    row_index = int(active_cell.get("row", -1))
                    field = str(active_cell.get("field", ""))
                    if 0 <= row_index < len(items) and field in FIELDS:
                        self._active_cell = (items[row_index], field)
                self._update_active_cell_border()
                self._refresh_analysis_surface_choices()
                self._refresh_operand_surface_choices()
            finally:
                self._history_restoring = False
                self._history_pending_state = None
        self._clear_step_runtime_after_history_restore(set(changed_settings))
        self._refresh_history_restore_views(
            previous_state=previous_state,
            target_state=state,
            changed_settings=set(changed_settings),
            display_only_open3d_step=display_only_open3d_step,
        )
        self._update_undo_redo_buttons()

    def _update_undo_redo_buttons(self) -> None:
        undo_state = "normal" if self._undo_stack else "disabled"
        redo_state = "normal" if self._redo_stack else "disabled"
        if self._edit_menu is not None:
            try:
                self._edit_menu.entryconfigure("Undo", state=undo_state)
                self._edit_menu.entryconfigure("Redo", state=redo_state)
            except tk.TclError:
                pass
        if self._undo_button is not None:
            self._undo_button.configure(state=undo_state)
        if self._redo_button is not None:
            self._redo_button.configure(state=redo_state)

    def undo(self) -> None:
        if not self._undo_stack:
            return
        with open3d_timing_span("history_undo", undo_depth=len(self._undo_stack), redo_depth=len(self._redo_stack)):
            current = self._capture_editor_state()
            state = self._undo_stack.pop()
            self._redo_stack.append(current)
            self._restore_history_state(state, previous_state=current, action="undo")
            self.status_var.set("Undo applied.")

    def redo(self) -> None:
        if not self._redo_stack:
            return
        with open3d_timing_span("history_redo", undo_depth=len(self._undo_stack), redo_depth=len(self._redo_stack)):
            current = self._capture_editor_state()
            state = self._redo_stack.pop()
            self._undo_stack.append(current)
            self._restore_history_state(state, previous_state=current, action="redo")
            self.status_var.set("Redo applied.")

    def _undo_event(self, _event=None) -> str:
        self.undo()
        return "break"

    def _redo_event(self, _event=None) -> str:
        self.redo()
        return "break"

    def _layout_settings_service(self) -> LayoutSettingsService:
        service = self.__dict__.get("_layout_settings_service_instance")
        if service is None:
            service = LayoutSettingsService(self)
            self._layout_settings_service_instance = service
        return service

    def _collect_layout_settings(self) -> dict[str, object]:
        return self._layout_settings_service()._collect_layout_settings()

    def _apply_layout_settings(self, settings: object) -> None:
        self._layout_settings_service()._apply_layout_settings(settings)

    def load_example_by_name(self, name: str) -> None:
        path = self.example_files.get(name)
        if path is None:
            return
        if self.rows:
            self._begin_history_capture()
        info: dict[str, object] | None = None
        try:
            code = path.read_text(encoding="utf-8", errors="ignore")
            if python_code_defines_layout_data(code):
                info = _load_python_data(path)
                self.rows = [self._row_from_layout_item(item) for item in info["surfaces"]]
                self.rows = self._normalized_rows_copy(self.rows)
            else:
                surfaces = self._extract_surfaces_from_example(path)
                self.rows = [self._row_from_surface(surface, index, len(surfaces)) for index, surface in enumerate(surfaces)]
        except Exception as exc:
            self._history_pending_state = None
            self.status_var.set(f"Failed to load example {name}: {exc}")
            return
        self.current_layout_file = None
        self._reset_complete_layout_runtime_state(close_viewers=True)
        self._normalize_special_rows()
        self._apply_example_display_defaults(path)
        if info is not None:
            self._apply_layout_settings(info.get("settings", {}))
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot(suppress_analysis=True)
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self.example_var.set(name)
        warned = False if info is not None else self._report_example_feature_gaps(name, path, surfaces)
        if not warned:
            self.status_var.set(f"Loaded example {name}. Click Update to run analysis.")

    def _on_layout_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.layout_var.get().strip()
        if selected == "Common Optical Layout":
            return
        self.load_layout_by_name(selected)

    def _on_machine_vision_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.machine_vision_var.get().strip()
        if selected == "Machine Vision Lens":
            return
        self.load_layout_by_name(selected)

    def _on_example_selected(self, _event: tk.Event | None = None) -> None:
        selected = self.example_var.get().strip()
        if selected == "Examples":
            return
        self.load_example_by_name(selected)

    @staticmethod
    def _element_tag_palette() -> tuple[tuple[str, str], ...]:
        return (
            ("element_group_0", "#e8f5e9"),
            ("element_group_1", "#e3f2fd"),
            ("element_group_2", "#fff3e0"),
            ("element_group_3", "#f3e5f5"),
            ("element_group_4", "#e0f7fa"),
            ("element_group_5", "#fce4ec"),
        )

    @staticmethod
    def _element_key(row: SurfaceRow) -> str:
        return str(getattr(row, "element", "") or "").strip()

    @staticmethod
    def _element_metadata(row: SurfaceRow) -> dict[str, object]:
        return _normalize_element_metadata((row.advanced or {}).get(ELEMENT_ADVANCED_ATTR))

    @staticmethod
    def _detector_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(DETECTOR_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return _normalize_detector_settings(value)

    @staticmethod
    def _scene_target_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(SCENE_TARGET_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return _normalize_scene_target_settings(value)

    @staticmethod
    def _scene_placement_settings(row: SurfaceRow) -> dict[str, object]:
        advanced = getattr(row, "advanced", {}) or {}
        value = advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR) if isinstance(advanced, dict) else None
        return normalize_scene_placement_settings(value)

    @staticmethod
    def _set_detector_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = _normalize_detector_settings(settings)
        row.advanced = dict(row.advanced or {})
        if _detector_settings_is_default(normalized):
            row.advanced.pop(DETECTOR_ADVANCED_ATTR, None)
        else:
            row.advanced[DETECTOR_ADVANCED_ATTR] = normalized

    @staticmethod
    def _set_scene_target_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = _normalize_scene_target_settings(settings)
        row.advanced = dict(row.advanced or {})
        if _scene_target_settings_is_default(normalized):
            row.advanced.pop(SCENE_TARGET_ADVANCED_ATTR, None)
        else:
            row.advanced[SCENE_TARGET_ADVANCED_ATTR] = normalized

    @staticmethod
    def _set_scene_placement_settings(row: SurfaceRow, settings: dict[str, object]) -> None:
        normalized = normalize_scene_placement_settings(settings)
        row.advanced = dict(row.advanced or {})
        if scene_placement_settings_is_default(normalized):
            row.advanced.pop(SCENE_PLACEMENT_ADVANCED_ATTR, None)
        else:
            row.advanced[SCENE_PLACEMENT_ADVANCED_ATTR] = normalized

    @staticmethod
    def _row_has_detector_output_metadata(row: SurfaceRow) -> bool:
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return False
        if DETECTOR_ADVANCED_ATTR in advanced:
            return True
        metadata = _normalize_element_metadata(advanced.get(ELEMENT_ADVANCED_ATTR))
        if str(metadata.get("arm_role", "") or "") == "Detector":
            return True
        display_settings = advanced.get("Display2D")
        if isinstance(display_settings, dict) and isinstance(display_settings.get("branch_output_targets"), dict):
            return True
        return isinstance(advanced.get("Interferogram"), dict)

    @staticmethod
    def _set_element_metadata(row: SurfaceRow, metadata: dict[str, object]) -> None:
        normalized = _normalize_element_metadata(metadata)
        row.advanced = dict(row.advanced or {})
        if _element_metadata_is_default(normalized):
            row.advanced.pop(ELEMENT_ADVANCED_ATTR, None)
        else:
            row.advanced[ELEMENT_ADVANCED_ATTR] = normalized

    @classmethod
    def _element_arm_role_for_index(cls, rows: list[SurfaceRow], index: int) -> str:
        if not (0 <= index < len(rows)):
            return ELEMENT_ARM_ROLE_DEFAULT
        start, _end = cls._element_block_for_index(rows, index)
        return str(cls._element_metadata(rows[start]).get("arm_role", ELEMENT_ARM_ROLE_DEFAULT))

    @classmethod
    def _element_arm_badge_for_index(cls, rows: list[SurfaceRow], index: int) -> str:
        if not (0 <= index < len(rows)):
            return ""
        start, _end = cls._element_block_for_index(rows, index)
        if index != start:
            return ""
        role = cls._element_arm_role_for_index(rows, index)
        return ELEMENT_ARM_BADGES.get(role, "")

    @staticmethod
    def _leg_badge_text(short_label: str) -> str:
        text = str(short_label or "").strip()
        match = re.fullmatch(r"(?:Leg|Path)\s+(\d+)", text, flags=re.IGNORECASE)
        return f"P{match.group(1)}" if match else text

    def _layout_interferometer_hint(self) -> str:
        texts: list[str] = []
        for row in getattr(self, "rows", []) or []:
            texts.extend(
                [
                    str(getattr(row, "element", "") or ""),
                    str(getattr(row, "name", "") or ""),
                    str(getattr(row, "surface", "") or ""),
                ]
            )
            advanced = getattr(row, "advanced", {}) or {}
            if isinstance(advanced, dict):
                for key in ("Note", "Interferogram", "Display2D"):
                    value = advanced.get(key)
                    if isinstance(value, dict):
                        texts.extend(str(item) for item in value.values())
                    elif value is not None:
                        texts.append(str(value))
        return " ".join(texts).lower()

    def _auto_leg_entries(self) -> list[dict[str, object]]:
        return list(getattr(self, "_last_auto_leg_entries", []) or [])

    def _auto_leg_entry_for_id(self, leg_id: str) -> dict[str, object] | None:
        target = str(leg_id or "").strip().lower()
        if not target:
            return None
        for entry in self._auto_leg_entries():
            if str(entry.get("leg_id", "") or "").strip().lower() == target:
                return entry
        return None

    @staticmethod
    def _auto_leg_point_key(point: np.ndarray, tolerance: float = 0.25) -> str:
        return auto_leg_point_key(point, tolerance)

    @staticmethod
    def _auto_leg_node_label(node: dict[str, object]) -> str:
        return auto_leg_node_label(node)

    def _auto_leg_node_for_hit(
        self,
        point: np.ndarray,
        surface_id: int | None,
        *,
        branch_path: str = "",
        branch_label: str = "",
    ) -> dict[str, object]:
        return auto_leg_node_for_hit(
            point,
            surface_id,
            self.rows,
            branch_path=branch_path,
            branch_label=branch_label,
            beam_splitter_surface=BEAM_SPLITTER_SURFACE,
        )

    @staticmethod
    def _auto_leg_hit_point_index(points: np.ndarray, surface_ids: np.ndarray, hit_index: int) -> int:
        return auto_leg_hit_point_index(points, surface_ids, hit_index)

    def _auto_leg_candidate_key(
        self,
        start_node: dict[str, object],
        end_node: dict[str, object],
        non_branch_surface_ids: tuple[int, ...],
    ) -> tuple[tuple[str, str], tuple[int, ...]]:
        return auto_leg_candidate_key(start_node, end_node, non_branch_surface_ids)

    @staticmethod
    def _auto_leg_midpoint(polyline: np.ndarray) -> np.ndarray:
        return auto_leg_midpoint(polyline)

    def _auto_leg_representative_polyline(self, polylines: list[np.ndarray]) -> np.ndarray:
        return auto_leg_representative_polyline(polylines)

    def _auto_leg_direction_from_node(self, entry: dict[str, object], node_key: str) -> np.ndarray:
        return auto_leg_direction_from_node(entry, node_key)

    def _ordered_auto_leg_keys(self, legs: dict[tuple[tuple[str, str], tuple[int, ...]], dict[str, object]]) -> list[tuple[tuple[str, str], tuple[int, ...]]]:
        return ordered_auto_leg_keys(legs)

    def _build_auto_leg_entries_from_projected(self, projected: ProjectedScene2D) -> list[dict[str, object]]:
        return build_auto_leg_entries_from_projected(
            projected,
            self.rows,
            beam_splitter_surface=BEAM_SPLITTER_SURFACE,
        )

    def _refresh_auto_leg_graph(self, projected: ProjectedScene2D | None) -> None:
        if projected is None:
            self._last_auto_leg_entries = []
            return
        try:
            self._last_auto_leg_entries = self._build_auto_leg_entries_from_projected(projected)
        except Exception as exc:
            self._last_auto_leg_entries = []
            self.append_debug(f"Automatic path graph skipped: {_short_error_message(exc)}")

    def _physical_leg_workflow(self) -> str:
        if not getattr(self, "rows", None):
            return ""
        hint = self._layout_interferometer_hint()
        if "mach" in hint and "zehnder" in hint:
            return "mach_zehnder"
        if "michelson" in hint or "twyman" in hint:
            return "michelson"
        target_codes = set(self._branch_output_display_targets())
        if {"TT", "TR", "RT", "RR"}.issubset(target_codes):
            return "michelson"
        return ""

    def _physical_leg_definitions(self) -> tuple[tuple[str, str, str], ...]:
        workflow = self._physical_leg_workflow()
        if workflow == "mach_zehnder":
            return MACH_ZEHNDER_LEG_DEFINITIONS
        if workflow == "michelson":
            return MICHELSON_LEG_DEFINITIONS
        auto_entries = self._auto_leg_entries()
        if auto_entries:
            return tuple(
                (
                    str(entry.get("leg_id", "") or "").strip().lower(),
                    str(entry.get("short_label", "") or "").strip(),
                    str(entry.get("detail", "") or "").strip(),
                )
                for entry in auto_entries
                if str(entry.get("leg_id", "") or "").strip()
            )
        return ()

    def _physical_leg_ids(self) -> set[str]:
        ids = {leg_id for leg_id, _short_label, _detail in self._physical_leg_definitions()}
        for row in getattr(self, "rows", []) or []:
            leg_id = str(self._element_metadata(row).get("leg_id", "") or "").strip().lower()
            if leg_id:
                ids.add(leg_id)
        return ids

    def _leg_short_label(self, leg_id: str) -> str:
        leg_id = str(leg_id or "").strip().lower()
        for defined_id, short_label, _detail in self._physical_leg_definitions():
            if leg_id == defined_id:
                return short_label
        return ""

    def _leg_id_from_element_metadata(
        self,
        metadata: dict[str, object],
        *,
        row: SurfaceRow | None = None,
        row_index: int | None = None,
    ) -> str:
        valid_leg_ids = self._physical_leg_ids()
        explicit = str(metadata.get("leg_id", "") or "").strip().lower()
        if explicit in valid_leg_ids:
            return explicit
        workflow = self._physical_leg_workflow()
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT).strip()
        selector = str(metadata.get("branch_selector", "") or "").strip().lower()
        parent = str(metadata.get("parent_splitter", "") or "").strip().lower()
        row_text = ""
        if row is not None:
            row_text = " ".join(
                [
                    str(getattr(row, "element", "") or ""),
                    str(getattr(row, "name", "") or ""),
                    str(getattr(row, "surface", "") or ""),
                    str(metadata.get("element_id", "") or ""),
                    str(metadata.get("element_name", "") or ""),
                ]
            ).lower()
        if workflow == "mach_zehnder":
            if row_index == 0:
                return "input"
            if role == "Common":
                if selector == "primary" or "bs1" in row_text or "input splitter" in row_text:
                    return "input"
                return ""
            if selector == "transmit" and role in {"Transmit", "Return"}:
                return "transmit"
            if selector == "reflect" and role in {"Reflect", "Return"}:
                return "reflect"
            if role == "Detector":
                if selector == "transmit" or "cross" in row_text:
                    return "cross"
                if selector == "reflect" or "return" in row_text:
                    return "return"
            if parent == "bs2" and selector == "transmit":
                return "cross"
            if parent == "bs2" and selector == "reflect":
                return "return"
            return ""
        if workflow == "michelson":
            if row_index == 0:
                return "input"
            if role == "Common" or selector == "primary":
                return "input"
            if row is not None and self._row_has_detector_output_metadata(row):
                return "detector"
            if role == "Detector":
                return "detector"
            if role == "Reflect" or selector == "reflect":
                return "reflect"
            if role == "Transmit" or selector == "transmit":
                return "transmit"
        return ""

    def _michelson_leg_badge_for_index(self, index: int) -> str:
        if not self._uses_michelson_leg_workflow() or not (0 <= index < len(self.rows)):
            return ""
        row = self.rows[index]
        metadata = self._element_metadata(row)
        leg_id = self._leg_id_from_element_metadata(metadata, row=row, row_index=index)
        return self._leg_badge_text(self._leg_short_label(leg_id)) if leg_id else ""

    @staticmethod
    def _branch_selector_for_arm_role(role: str) -> str:
        if role == "Transmit":
            return "transmit"
        if role == "Reflect":
            return "reflect"
        return ""

    @staticmethod
    def _arm_key_from_metadata(metadata: dict[str, object]) -> str:
        branch_path = str(metadata.get("branch_path", "") or "").strip()
        if branch_path and branch_path != "primary":
            return LayoutTableWorkbenchMixin._arm_key_from_branch_path(branch_path)
        leg_id = str(metadata.get("leg_id", "") or "").strip().lower()
        if leg_id:
            return f"leg|{leg_id}"
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT).strip()
        if role in {"", ELEMENT_ARM_ROLE_DEFAULT, "Common"}:
            return ""
        selector = str(metadata.get("branch_selector", "") or "").strip().lower()
        parent = str(metadata.get("parent_splitter", "") or "").strip()
        if selector in {"primary", "transmit", "reflect", "return"}:
            return f"branch|{parent}|{selector}"
        return f"role|{role}"

    @staticmethod
    def _arm_key_from_branch_path(branch_path: str) -> str:
        path = str(branch_path or "").strip()
        if not path or path == "primary":
            return ""
        return f"path|{path}"

    @staticmethod
    def _leg_key(leg_id: str) -> str:
        return f"leg|{str(leg_id or '').strip().lower()}"

    @staticmethod
    def _leg_id_from_arm_key(key: str) -> str:
        text = str(key or "").strip()
        if not text.startswith("leg|"):
            return ""
        return text.split("|", 1)[1].strip().lower()

    @staticmethod
    def _branch_path_for_arm_key(key: str) -> str:
        text = str(key or "").strip()
        if text.startswith("path|"):
            return text.split("|", 1)[1].strip()
        return ""

    @staticmethod
    def _branch_path_leaf_selector(branch_path: str) -> str:
        leaf = str(branch_path or "").split("->")[-1].strip()
        if "/" not in leaf:
            return ""
        return leaf.rsplit("/", 1)[1].strip().lower()

    @staticmethod
    def _branch_path_surface_indices(branch_path: str) -> set[int]:
        return set(LayoutTableWorkbenchMixin._branch_path_surface_sequence(branch_path))

    @staticmethod
    def _branch_path_surface_sequence(branch_path: str) -> list[int]:
        indices: list[int] = []
        for match in re.finditer(r"(?:^|\s)S(\d+):", str(branch_path or "")):
            try:
                indices.append(int(match.group(1)))
            except ValueError:
                continue
        return indices

    @staticmethod
    def _branch_path_detail(branch_path: str) -> str:
        parts: list[str] = []
        for component in str(branch_path or "").split("->"):
            text = component.strip()
            if not text:
                continue
            surface_text, _, selector = text.rpartition("/")
            if not surface_text:
                surface_text = text
            if ":" in surface_text:
                surface_text = surface_text.split(":", 1)[1].strip()
            surface_text = surface_text.strip()
            selector = selector.strip()
            if surface_text and selector:
                parts.append(f"{surface_text} {selector}")
            elif selector:
                parts.append(selector)
            elif surface_text:
                parts.append(surface_text)
        return " -> ".join(parts) if parts else str(branch_path or "").strip()

    @staticmethod
    def _branch_path_depth(branch_path: str) -> int:
        return sum(1 for component in str(branch_path or "").split("->") if component.strip())

    @staticmethod
    def _branch_path_selector_sequence(branch_path: str) -> list[str]:
        return branch_path_selector_sequence(branch_path)

    @staticmethod
    def _branch_path_compact_detail(branch_path: str) -> str:
        selectors = LayoutTableWorkbenchMixin._branch_path_selector_sequence(branch_path)
        if selectors:
            return " -> ".join(selectors)
        return LayoutTableWorkbenchMixin._branch_path_detail(branch_path)

    def _arm_key_detail(self, key: str) -> str:
        parts = str(key or "").split("|")
        if len(parts) >= 2 and parts[0] == "leg":
            leg_id = parts[1].strip().lower()
            for defined_id, _short_label, detail in self._physical_leg_definitions():
                if leg_id == defined_id:
                    return detail
            return leg_id
        if len(parts) >= 2 and parts[0] == "path":
            path = "|".join(parts[1:])
            if LayoutTableWorkbenchMixin._branch_path_depth(path) > 1:
                return LayoutTableWorkbenchMixin._branch_path_compact_detail(path)
            return LayoutTableWorkbenchMixin._branch_path_detail(path)
        if len(parts) >= 3 and parts[0] == "branch":
            parent = parts[1].strip()
            selector = parts[2].strip()
            return f"{parent} {selector}".strip() if parent else selector
        if len(parts) >= 2 and parts[0] == "role":
            return parts[1].strip()
        return str(key or "").strip()

    def _traced_branch_paths(self) -> list[str]:
        bundle = getattr(self, "_last_scene_bundle", None)
        paths: list[str] = []
        seen: set[str] = set()
        for path in getattr(bundle, "ray_paths", []) or []:
            branch_path = str(getattr(path, "branch_path", "") or "").strip()
            if not branch_path or branch_path == "primary" or branch_path in seen:
                continue
            seen.add(branch_path)
            paths.append(branch_path)
        return paths

    @classmethod
    def _metadata_arm_key_matches_branch_path(cls, arm_key: str, branch_path: str) -> bool:
        parts = str(arm_key or "").split("|")
        target_path = cls._branch_path_for_arm_key(arm_key)
        if target_path:
            return str(branch_path or "").strip() == target_path
        if len(parts) < 3 or parts[0] != "branch":
            return False
        parent = parts[1].strip().lower()
        selector = parts[2].strip().lower()
        if selector and selector != cls._branch_path_leaf_selector(branch_path):
            return False
        if not parent:
            return True
        path_text = str(branch_path or "").lower()
        if parent in path_text:
            return True
        # Saved Element metadata often uses a stable splitter id such as BS1,
        # while traced paths use the KrakenOS surface label. A matching leaf
        # selector is still the same logical path and should not create a
        # duplicate metadata label beside the traced branch/path label.
        return bool(selector)

    def _uses_michelson_leg_workflow(self) -> bool:
        return bool(self._physical_leg_definitions())

    def _leg_catalog(self) -> list[dict[str, str]]:
        definitions = self._physical_leg_definitions()
        if not definitions:
            return []
        catalog: list[dict[str, str]] = []
        for leg_id, short_label, detail in definitions:
            catalog.append(
                {
                    "key": self._leg_key(leg_id),
                    "short_label": short_label,
                    "label": f"{short_label}: {detail}",
                    "detail": detail,
                    "kind": "leg",
                }
            )
        return catalog

    def _arm_catalog(self) -> list[dict[str, str]]:
        catalog: list[dict[str, str]] = []
        seen: set[str] = set()
        if not self.rows:
            return catalog
        leg_catalog = self._leg_catalog()
        if leg_catalog:
            return leg_catalog

        def add_entry(key: str, detail: str, prefix: str = "Path") -> None:
            if not key or key in seen:
                return
            seen.add(key)
            arm_number = len(catalog) + 1
            label = f"{prefix} {arm_number}: {detail}" if detail else f"{prefix} {arm_number}"
            catalog.append(
                {
                    "key": key,
                    "short_label": f"{prefix} {arm_number}",
                    "label": label,
                    "detail": detail,
                    "kind": prefix.lower(),
                }
            )

        traced_paths = self._traced_branch_paths()
        for branch_path in traced_paths:
            depth = self._branch_path_depth(branch_path)
            detail = (
                self._branch_path_compact_detail(branch_path)
                if depth > 1
                else self._branch_path_detail(branch_path)
            )
            add_entry(self._arm_key_from_branch_path(branch_path), detail, prefix="Path")

        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            metadata = self._element_metadata(self.rows[start])
            key = self._arm_key_from_metadata(metadata)
            if key and not any(self._metadata_arm_key_matches_branch_path(key, path) for path in traced_paths):
                add_entry(key, self._arm_key_detail(key))
            index = max(end + 1, index + 1)
        return catalog

    @classmethod
    def _element_block_for_index(cls, rows: list[SurfaceRow], index: int) -> tuple[int, int]:
        if not (0 <= index < len(rows)):
            return index, index
        key = cls._element_key(rows[index])
        if not key:
            return index, index
        start = index
        end = index
        while start > 0 and cls._element_key(rows[start - 1]) == key:
            start -= 1
        while end + 1 < len(rows) and cls._element_key(rows[end + 1]) == key:
            end += 1
        return start, end

    @classmethod
    def _swap_element_block_same_arm(
        cls,
        rows: list[SurfaceRow],
        selected_index: int,
        direction: str,
    ) -> tuple[list[SurfaceRow], int, int, bool]:
        start, end = cls._element_block_for_index(rows, selected_index)
        role = cls._element_arm_role_for_index(rows, selected_index)
        if role == ELEMENT_ARM_ROLE_DEFAULT:
            return rows, start, end, False
        current = rows[start : end + 1]
        if direction == "up":
            scan = start - 1
            while scan > 0:
                previous_start, previous_end = cls._element_block_for_index(rows, scan)
                if cls._element_arm_role_for_index(rows, previous_start) == role:
                    previous = rows[previous_start : previous_end + 1]
                    middle = rows[previous_end + 1 : start]
                    new_rows = rows[:previous_start] + current + middle + previous + rows[end + 1 :]
                    new_start = previous_start
                    return new_rows, new_start, new_start + len(current) - 1, True
                scan = previous_start - 1
            return rows, start, end, False
        if direction == "down":
            scan = end + 1
            while scan < len(rows) - 1:
                next_start, next_end = cls._element_block_for_index(rows, scan)
                if cls._element_arm_role_for_index(rows, next_start) == role:
                    next_block = rows[next_start : next_end + 1]
                    middle = rows[end + 1 : next_start]
                    new_rows = rows[:start] + next_block + middle + current + rows[next_end + 1 :]
                    new_start = start + len(next_block) + len(middle)
                    return new_rows, new_start, new_start + len(current) - 1, True
                scan = next_end + 1
            return rows, start, end, False
        return rows, start, end, False

    @classmethod
    def _swap_element_block(
        cls,
        rows: list[SurfaceRow],
        selected_index: int,
        direction: str,
        *,
        same_arm_only: bool = False,
    ) -> tuple[list[SurfaceRow], int, int, bool]:
        if not rows or not (0 <= selected_index < len(rows)):
            return rows, selected_index, selected_index, False
        start, end = cls._element_block_for_index(rows, selected_index)
        if same_arm_only:
            arm_rows, arm_start, arm_end, arm_moved = cls._swap_element_block_same_arm(rows, selected_index, direction)
            if arm_moved:
                return arm_rows, arm_start, arm_end, True
            if cls._element_arm_role_for_index(rows, selected_index) != ELEMENT_ARM_ROLE_DEFAULT:
                return rows, start, end, False
        if direction == "up":
            if start <= 1:
                return rows, start, end, False
            previous_start, previous_end = cls._element_block_for_index(rows, start - 1)
            if previous_start <= 0:
                return rows, start, end, False
            current = rows[start : end + 1]
            previous = rows[previous_start : previous_end + 1]
            new_rows = rows[:previous_start] + current + previous + rows[end + 1 :]
            new_start = previous_start
            return new_rows, new_start, new_start + len(current) - 1, True
        if direction == "down":
            if end >= len(rows) - 2:
                return rows, start, end, False
            next_start, next_end = cls._element_block_for_index(rows, end + 1)
            if next_end >= len(rows) - 1:
                return rows, start, end, False
            current = rows[start : end + 1]
            next_block = rows[next_start : next_end + 1]
            new_rows = rows[:start] + next_block + current + rows[next_end + 1 :]
            new_start = start + len(next_block)
            return new_rows, new_start, new_start + len(current) - 1, True
        return rows, start, end, False

    @classmethod
    def _element_indices_for_index(cls, rows: list[SurfaceRow], index: int) -> list[int]:
        if not (0 <= index < len(rows)):
            return []
        start, end = cls._element_block_for_index(rows, index)
        return list(range(start, end + 1))

    @staticmethod
    def _table_iid_for_row_index(index: int) -> str:
        return f"row_{int(index)}"

    def _table_item_row_index(self, item: str | None) -> int | None:
        if not item:
            return None
        text = str(item)
        mapping = self.__dict__.get("_table_iid_to_row_index", {})
        if text in mapping:
            mapped = mapping.get(text)
            if mapped is None:
                return None
            return int(mapped)
        if text.startswith("scene_source_"):
            return None
        if text.startswith("row_"):
            try:
                return int(text.split("_", 1)[1])
            except ValueError:
                return None
        try:
            return int(self.table.index(text))
        except Exception:
            return None

    def _table_item_for_row_index(self, row_index: int) -> str | None:
        item = self._table_iid_for_row_index(row_index)
        try:
            return item if self.table.exists(item) else None
        except Exception:
            return None

    @staticmethod
    def _table_iid_for_scene_source_record(record) -> str:
        source_id = str(getattr(record, "source_id", "") or getattr(record, "scene_row_index", ""))
        safe_source_id = "".join(ch if ch.isalnum() else "_" for ch in source_id).strip("_") or "source"
        return f"scene_source_{int(getattr(record, 'scene_row_index', 0))}_{safe_source_id}"

    def _table_item_scene_record(self, item: str | None):
        if not item:
            return None
        return self.__dict__.get("_table_iid_to_scene_record", {}).get(str(item))

    def _current_arm_view_key(self) -> str:
        return self._arm_key_for_view_label(str(self.arm_view_var.get() or ARM_VIEW_DEFAULT))

    def _path_local_table_mode_enabled(self) -> bool:
        return bool(self._current_arm_view_key())

    def _row_uses_path_local_table_pose(self, row: SurfaceRow) -> bool:
        return self._path_local_table_mode_enabled() and self._metadata_has_path_pose(self._element_metadata(row))

    def _path_local_pose_cell_enabled(self, row_index: int, field: str) -> bool:
        if field not in PATH_LOCAL_TABLE_FIELD_MAP:
            return False
        if not (0 <= row_index < len(self.rows)):
            return False
        return self._row_uses_path_local_table_pose(self.rows[row_index])

    def _format_path_local_table_pose_cell(self, row: SurfaceRow, field: str) -> str:
        metadata_key = PATH_LOCAL_TABLE_FIELD_MAP.get(field, "")
        if not metadata_key:
            return ""
        metadata = self._element_metadata(row)
        return self._format_table_float(float(metadata.get(metadata_key, 0.0)))

    def _sync_table_headings(self) -> None:
        table = self.__dict__.get("table")
        if table is None:
            return
        local_mode = self._path_local_table_mode_enabled()
        self._table_path_local_mode_active = local_mode
        for field in FIELDS:
            label = PATH_LOCAL_COLUMN_LABELS.get(field, COLUMN_LABELS[field]) if local_mode else COLUMN_LABELS[field]
            try:
                table.heading(field, text=label)
            except Exception:
                continue

    def _default_insert_index_for_arm_key(self, arm_key: str) -> int:
        leg_id = self._leg_id_from_arm_key(arm_key)
        arm_indices = self._indices_for_arm_key(arm_key)
        if leg_id == "input":
            for index in range(1, max(len(self.rows) - 1, 1)):
                if self.rows[index].surface == BEAM_SPLITTER_SURFACE:
                    return index
            return 1
        if leg_id in {"reflect", "transmit", "detector", "cross", "return"} and arm_indices:
            return min(arm_indices)
        return (max(arm_indices) + 1) if arm_indices else max(1, len(self.rows) - 1)

    def _visible_row_indices_for_current_arm_view(self) -> list[int]:
        if not self.rows:
            return []
        arm_key = self._current_arm_view_key()
        if not arm_key:
            return list(range(len(self.rows)))
        allowed = self._context_surface_indices_for_arm_key(arm_key) | self._surface_indices_for_arm_key(arm_key)
        return [index for index in range(len(self.rows)) if index in allowed]

    def _visible_table_scene_sources(self) -> list[SceneSource3D]:
        sources = self._collect_scene_sources()
        explicit_scene_sources = bool(getattr(self, "layout_scene_source_specs", []) or [])
        return [source for source in sources if explicit_scene_sources or bool(source.physical)]

    def _visible_scene_row_records_for_table(self, visible_indices: list[int]):
        source_records = self._visible_table_scene_sources()
        if not source_records:
            mapping = build_scene_row_mapping(
                self.rows,
                [],
                include_sources=False,
            )
            return [mapping.record_for_table_row(index) for index in visible_indices]
        visible_set = {int(index) for index in visible_indices}
        mapping = build_scene_row_mapping(
            self.rows,
            source_records,
            include_sources=True,
            source_row_order=normalize_source_row_order(
                getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)
            ),
        )
        return [
            record
            for record in mapping.records
            if record is not None
            and (
                record.kind == SCENE_ROW_SOURCE
                or (record.table_row_index is not None and int(record.table_row_index) in visible_set)
            )
        ]

    def _table_values_for_surface_row(self, index: int, row: SurfaceRow) -> list[str]:
        arm_badge = self._michelson_leg_badge_for_index(index) or self._element_arm_badge_for_index(self.rows, index)
        label_text = f"{index} {arm_badge}" if arm_badge else str(index)
        use_path_local_pose = self._row_uses_path_local_table_pose(row)
        raw_values = {
            "label": label_text,
            "surface": row.surface,
            "name": row.name,
            "glass": row.glass,
            "rc": self._format_numeric_cell("rc", row),
            "k": self._format_numeric_cell("k", row),
            "axicon": self._format_table_float(row.axicon),
            "diff_ord": self._format_table_float(row.diff_ord),
            "grating_d": self._format_numeric_cell("grating_d", row),
            "grating_angle": self._format_numeric_cell("grating_angle", row),
            "thickness": self._format_numeric_cell("thickness", row),
            "diameter": self._format_table_float(row.diameter),
            "in_diameter": self._format_table_float(row.in_diameter),
            "tilt_x": self._format_pose_cell(self.rows, index, "tilt_x"),
            "tilt_y": self._format_pose_cell(self.rows, index, "tilt_y"),
            "tilt_z": self._format_pose_cell(self.rows, index, "tilt_z"),
            "desp_x": self._format_pose_cell(self.rows, index, "desp_x"),
            "desp_y": self._format_pose_cell(self.rows, index, "desp_y"),
            "desp_z": self._format_pose_cell(self.rows, index, "desp_z"),
            "axis_move": self._format_numeric_cell("axis_move", row),
        }
        if use_path_local_pose:
            for field in PATH_LOCAL_TABLE_FIELD_MAP:
                raw_values[field] = self._format_path_local_table_pose_cell(row, field)
        return [self._table_display_value_for_row(index, row, field, raw_values[field]) for field in FIELDS]

    @staticmethod
    def _table_values_for_source_scene_row(record) -> list[str]:
        metadata = dict(getattr(record, "metadata", {}) or {})
        model = str(metadata.get("model", "") or "Source")
        ray_count = metadata.get("ray_count", "")
        name = str(getattr(record, "name", "") or "Source")
        if ray_count not in ("", None):
            name = f"{name} ({ray_count} rays)"
        surface_text = "Illumination Source" if bool(getattr(record, "physical", True)) else "Source Reference"
        raw_values = {
            "label": str(getattr(record, "label", "Src")),
            "surface": surface_text,
            "name": name,
            "glass": model,
        }
        for field in FIELDS:
            raw_values.setdefault(field, DISABLED_TABLE_CELL_TEXT)
        return [str(raw_values.get(field, DISABLED_TABLE_CELL_TEXT)) for field in FIELDS]

    def _sync_table(self) -> None:
        self._apply_image_diameter_mode()
        self._sync_table_headings()
        self.table.delete(*self.table.get_children())
        self._table_iid_to_row_index = {}
        self._table_iid_to_scene_record = {}
        self._refresh_arm_view_choices()
        visible_indices = self._visible_row_indices_for_current_arm_view()
        self._table_visible_row_indices = list(visible_indices)
        visible_records = [
            record for record in self._visible_scene_row_records_for_table(visible_indices) if record is not None
        ]
        palette = self._element_tag_palette()
        element_tags: dict[str, str] = {}
        for record in visible_records:
            if record.kind == SCENE_ROW_SOURCE:
                iid = self._table_iid_for_scene_source_record(record)
                self._table_iid_to_row_index[iid] = None
                self._table_iid_to_scene_record[iid] = record
                self.table.insert("", "end", iid=iid, values=self._table_values_for_source_scene_row(record), tags=("scene_source",))
                continue
            if record.table_row_index is None:
                continue
            index = int(record.table_row_index)
            if not (0 <= index < len(self.rows)):
                continue
            row = self.rows[index]
            row.label = str(index)
            tags: list[str] = []
            element_key = self._element_key(row)
            if element_key:
                tag = element_tags.get(element_key)
                if tag is None:
                    tag = palette[len(element_tags) % len(palette)][0]
                    element_tags[element_key] = tag
                tags.append(tag)
            iid = self._table_iid_for_row_index(index)
            self._table_iid_to_row_index[iid] = index
            self._table_iid_to_scene_record[iid] = record
            self.table.insert("", "end", iid=iid, values=self._table_values_for_surface_row(index, row), tags=tags)
        self._refresh_analysis_surface_choices()
        self._refresh_operand_surface_choices()
        self._schedule_table_grid_update(delay=1)

    def _sync_image_row_table_value(self) -> None:
        table = self.__dict__.get("table")
        if table is None or not self.rows:
            return
        items = table.get_children()
        if not items:
            return
        image_item = self._table_item_for_row_index(len(self.rows) - 1)
        if image_item is None:
            return
        values = list(table.item(image_item, "values"))
        diameter_index = FIELDS.index("diameter")
        if len(values) <= diameter_index:
            return
        values[diameter_index] = self._table_display_value(
            self.rows[-1],
            "diameter",
            self._format_table_float(self.rows[-1].diameter),
        )
        table.item(image_item, values=values)

    def _refresh_analysis_surface_choices(self) -> None:
        options = ["Auto"]
        for index, row in enumerate(self.rows):
            options.append(f"{index}: {row.name}")
        current = self.analysis_surface_var.get()
        self.analysis_surface_menu["values"] = options
        if current not in options:
            self.analysis_surface_var.set("Auto")
        if hasattr(self, "nonseq_target_surface_menu") and hasattr(self, "nonseq_target_surface_var"):
            target_current = self.nonseq_target_surface_var.get()
            self.nonseq_target_surface_menu["values"] = options
            if target_current not in options:
                self.nonseq_target_surface_var.set("Auto")
        self._schedule_table_grid_update()
        self._schedule_active_cell_border_update()

    @staticmethod
    def _parse_numeric_display(value: str) -> float:
        return float(value.replace("*", "").strip())

    @staticmethod
    def _normalized_rows_copy(rows: list[SurfaceRow]) -> list[SurfaceRow]:
        return _surface_table_normalized_rows_copy(rows, element_advanced_attr=ELEMENT_ADVANCED_ATTR)

    @staticmethod
    def _is_air_like_glass(glass: str) -> bool:
        value = str(glass or "").strip().upper()
        return value in {"", "AIR", "VACUUM", "NONE", "NULL"} or value.startswith("AIR")

    @classmethod
    def _auto_element_label_for_group(
        cls,
        rows: list[SurfaceRow],
        group: list[int],
        element_number: int,
    ) -> tuple[str, bool]:
        if len(group) == 1:
            row = rows[group[0]]
            if row.surface == "Aperture":
                return (str(row.name or "Stop").strip() or "Stop"), False
            if row.surface in {"Mirror", BEAM_SPLITTER_SURFACE, "Thin Lens", "Grating"}:
                return (str(row.name or row.surface).strip() or row.surface), True
        materials: list[str] = []
        for index in group:
            glass = str(rows[index].glass or "").strip()
            if not cls._is_air_like_glass(glass) and glass.upper() != "MIRROR" and glass not in materials:
                materials.append(glass)
        suffix = f" {'/'.join(materials)}" if materials else ""
        return f"E{element_number}{suffix}", True

    @classmethod
    def _auto_assign_missing_elements(cls, rows: list[SurfaceRow]) -> None:
        """Infer Element groups for legacy sequential layouts with no metadata."""
        if not rows or any(cls._element_key(row) for row in rows[1:-1]):
            return
        groups: list[list[int]] = []
        current_group: list[int] = []
        for index, row in enumerate(rows[1:-1], start=1):
            if row.surface in {"Object", "Image"}:
                continue
            if row.surface == "Aperture":
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([index])
                continue
            if row.surface in {"Mirror", BEAM_SPLITTER_SURFACE, "Thin Lens", "Grating"}:
                if current_group:
                    groups.append(current_group)
                    current_group = []
                groups.append([index])
                continue
            if cls._is_air_like_glass(row.glass):
                if current_group:
                    current_group.append(index)
                    groups.append(current_group)
                    current_group = []
                continue
            current_group.append(index)
        if current_group:
            groups.append(current_group)

        element_number = 1
        for group in groups:
            label, consumes_number = cls._auto_element_label_for_group(rows, group, element_number)
            for index in group:
                rows[index].element = label
            if consumes_number:
                element_number += 1

    @staticmethod
    def _is_empty_starter_rows(rows: list[SurfaceRow]) -> bool:
        return (
            len(rows) == 2
            and rows[0].surface == "Object"
            and rows[-1].surface == "Image"
            and rows[0].glass == "AIR"
            and rows[-1].glass == "AIR"
        )

    def _selected_insert_index(self) -> int | None:
        selected = self.table.selection()
        if not selected:
            return None
        element_blocks = self._selected_element_blocks()
        if element_blocks:
            return max(index for block in element_blocks for index in block)
        indices = self._selected_table_indices()
        if not indices:
            return None
        return indices[-1]

    def _select_inserted_layout_rows(self, layout_rows: list[SurfaceRow], insert_after: int | None) -> None:
        indices = inserted_layout_row_indices(
            len(self.rows),
            layout_rows,
            insert_after=insert_after,
            final_row_is_image=bool(self.rows and self.rows[-1].surface == "Image"),
        )
        if not indices:
            return
        self._select_table_indices(indices, focus_index=indices[0])

    @staticmethod
    def _append_layout_rows(
        existing_rows: list[SurfaceRow],
        layout_rows: list[SurfaceRow],
        insert_after: int | None = None,
        element_name: str = "",
    ) -> list[SurfaceRow]:
        return _surface_table_append_layout_rows(
            existing_rows,
            layout_rows,
            insert_after=insert_after,
            element_name=element_name,
        )

    @classmethod
    def _format_numeric_cell(cls, field: str, row: SurfaceRow, *, display_value: float | None = None) -> str:
        spec = VARIABLE_REGISTRY.get(field)
        value = getattr(row, spec.field if spec is not None else field, 0.0)
        if display_value is not None:
            value = display_value
        text = LayoutTableWorkbenchMixin._format_table_float(value)
        return text

    @classmethod
    def _format_sequence_cell(cls, field: str, row: SurfaceRow, values: list[float]) -> str:
        return _format_float_sequence(values)

    @classmethod
    def _format_pose_cell(cls, rows: list[SurfaceRow], row_index: int, field: str) -> str:
        row = rows[row_index]
        values = cls._pose_field_display_values_for_row(rows, row_index, field)
        if len(values) > 1:
            return cls._format_sequence_cell(field, row, values)
        if field == "tilt_x" and row.surface == "Mirror":
            return cls._format_numeric_cell(
                field,
                row,
                display_value=cls._mirror_display_slant_deg_for_rows(rows, row_index),
            )
        return cls._format_numeric_cell(field, row)

    @staticmethod
    def _format_table_float(value: float) -> str:
        return f"{float(value):.12g}"

    @staticmethod
    def _surface_type_enabled_fields(surface_type: str) -> set[str]:
        return set(SURFACE_TYPE_ENABLED_FIELDS.get(str(surface_type), SURFACE_TYPE_ENABLED_FIELDS["Standard"]))

    @classmethod
    def _surface_type_field_enabled(cls, row: SurfaceRow, field: str) -> bool:
        return field in cls._surface_type_enabled_fields(row.surface)

    @classmethod
    def _table_display_value(cls, row: SurfaceRow, field: str, value: object) -> str:
        if not cls._surface_type_field_enabled(row, field):
            return DISABLED_TABLE_CELL_TEXT
        return str(value)

    def _table_display_value_for_row(self, row_index: int, row: SurfaceRow, field: str, value: object) -> str:
        if field in PATH_LOCAL_TABLE_FIELD_MAP and 0 <= row_index < len(self.rows) and self._row_uses_path_local_table_pose(row):
            return str(value)
        return self._table_display_value(row, field, value)

    def _table_cell_enabled(self, row_index: int, field: str) -> bool:
        if not (0 <= row_index < len(self.rows)):
            return True
        if self._path_local_pose_cell_enabled(row_index, field):
            return True
        return self._surface_type_field_enabled(self.rows[row_index], field)

    def _surface_type_disabled_message(self, row_index: int, field: str) -> str:
        row = self.rows[row_index]
        return (
            f"{COLUMN_LABELS.get(field, field)} is not used by {row.surface} rows. "
            "Use Advanced... for KrakenOS-native attributes outside this template."
        )

    @staticmethod
    def _normalize_mirror_slant_deg(angle_deg: float) -> float:
        angle = float(angle_deg)
        while angle <= -90.0:
            angle += 180.0
        while angle > 90.0:
            angle -= 180.0
        if abs(angle) < 1e-12:
            return 0.0
        return angle

    @classmethod
    def _mirror_branch_after_slant_deg(cls, branch_angle_deg: float, slant_angle_deg: float) -> float:
        direction = np.array(
            [np.cos(np.deg2rad(float(branch_angle_deg))), np.sin(np.deg2rad(float(branch_angle_deg)))],
            dtype=float,
        )
        reflected = cls._reflect_2d(direction, float(slant_angle_deg))
        return float(np.rad2deg(np.arctan2(reflected[1], reflected[0])))

    @classmethod
    def _mirror_display_slant_deg_for_rows(cls, rows: list[SurfaceRow], row_index: int) -> float:
        branch_angle = 0.0
        for index, row in enumerate(rows):
            if row.surface != "Mirror":
                continue
            slant_angle = cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))
            if index == row_index:
                return slant_angle
            branch_angle = cls._mirror_branch_after_slant_deg(branch_angle, slant_angle)
        return float(rows[row_index].tilt_x)

    @classmethod
    def _mirror_local_tilt_deg_from_display(
        cls,
        branch_angle_deg: float,
        display_slant_deg: float,
    ) -> float:
        return cls._normalize_mirror_slant_deg(float(display_slant_deg) - branch_angle_deg + 90.0)

    @classmethod
    def _mirror_branch_angle_before_index(cls, rows: list[SurfaceRow], row_index: int) -> float:
        branch_angle = 0.0
        for index, row in enumerate(rows):
            if index >= row_index:
                break
            if row.surface != "Mirror":
                continue
            slant_angle = cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(row.tilt_x))
            branch_angle = cls._mirror_branch_after_slant_deg(branch_angle, slant_angle)
        return branch_angle

    @staticmethod
    def _advanced_with_galvo_scan_overlay(advanced: dict | None, values: list[float]) -> dict:
        updated = dict(advanced or {})
        display = dict(updated.get("Display2D", {}) or {})
        if values:
            display[GALVO_SCAN_OVERLAY_KEY] = [float(value) for value in values]
            updated["Display2D"] = display
        else:
            display.pop(GALVO_SCAN_OVERLAY_KEY, None)
            if display:
                updated["Display2D"] = display
            else:
                updated.pop("Display2D", None)
        return updated

    @staticmethod
    def _advanced_with_pose_tolerance_overlay(advanced: dict | None, field: str, values: list[float]) -> dict:
        updated = dict(advanced or {})
        display = dict(updated.get("Display2D", {}) or {})
        overlay = dict(display.get(POSE_TOLERANCE_OVERLAY_KEY, {}) or {})
        if field in POSE_TOLERANCE_FIELDS and len(values) > 1:
            overlay[field] = [float(value) for value in values]
        else:
            overlay.pop(field, None)
        if overlay:
            display[POSE_TOLERANCE_OVERLAY_KEY] = overlay
            updated["Display2D"] = display
        else:
            display.pop(POSE_TOLERANCE_OVERLAY_KEY, None)
            if display:
                updated["Display2D"] = display
            else:
                updated.pop("Display2D", None)
        return updated

    @staticmethod
    def _pose_tolerance_overlay_values(row: SurfaceRow, field: str) -> list[float]:
        if field not in POSE_TOLERANCE_FIELDS:
            return []
        advanced = getattr(row, "advanced", {}) or {}
        if not isinstance(advanced, dict):
            return []
        display_settings = advanced.get("Display2D", {})
        if not isinstance(display_settings, dict):
            return []
        overlay = display_settings.get(POSE_TOLERANCE_OVERLAY_KEY, {})
        if not isinstance(overlay, dict):
            return []
        raw_values = overlay.get(field)
        if raw_values in (None, "", "None"):
            return []
        try:
            if isinstance(raw_values, str):
                values = _parse_float_sequence_text(raw_values)
            elif isinstance(raw_values, (int, float)):
                values = [float(raw_values)]
            else:
                values = _dedupe_float_values([float(value) for value in raw_values])
        except Exception:
            return []
        return values if len(values) > 1 else []

    @classmethod
    def _pose_field_display_values_for_row(cls, rows: list[SurfaceRow], row_index: int, field: str) -> list[float]:
        if not (0 <= row_index < len(rows)) or field not in POSE_TOLERANCE_FIELDS:
            return []
        row = rows[row_index]
        if field == "tilt_x" and row.surface == "Mirror":
            return cls._mirror_overlay_display_slants_for_rows(rows, row_index)
        return cls._pose_tolerance_overlay_values(row, field)

    @classmethod
    def _mirror_overlay_display_slants_for_rows(cls, rows: list[SurfaceRow], row_index: int) -> list[float]:
        if not (0 <= row_index < len(rows)) or rows[row_index].surface != "Mirror":
            return []
        local_values = cls._galvo_scan_overlay_values(rows[row_index])
        if not local_values:
            return []
        branch_angle = cls._mirror_branch_angle_before_index(rows, row_index)
        return [
            cls._normalize_mirror_slant_deg(branch_angle - 90.0 + float(local_tilt))
            for local_tilt in local_values
        ]

    def _editable_table_row_service(self) -> EditableTableRowService:
        service = self.__dict__.get("_editable_table_row_service_instance")
        if service is None:
            service = EditableTableRowService(self)
            self._editable_table_row_service_instance = service
        return service

    def _read_rows_from_table(self) -> None:
        self._editable_table_row_service()._read_rows_from_table()

    @classmethod
    def _propagate_element_pose_tolerances(cls, rows: list[SurfaceRow], previous_rows: list[SurfaceRow]) -> None:
        """Treat pose lists on grouped elements as rigid element tolerances.

        A user should not have to enter the same DespY/TiltY list on every
        surface of a doublet. When any grouped row has a pose tolerance list,
        the list is converted into deltas about that row's nominal value and
        applied to every row in the contiguous element block.
        """
        visited: set[tuple[int, int, str]] = set()
        index = 1
        while index < len(rows) - 1:
            element_key = cls._element_key(rows[index])
            if not element_key:
                index += 1
                continue
            start, end = cls._element_block_for_index(rows, index)
            block = list(range(max(start, 1), min(end, len(rows) - 2) + 1))
            if not block:
                index = end + 1
                continue
            for field in POSE_TOLERANCE_FIELDS:
                if field == "tilt_x" and any(rows[row_index].surface == "Mirror" for row_index in block):
                    continue
                key = (start, end, field)
                if key in visited:
                    continue
                visited.add(key)
                source_index = next(
                    (
                        row_index
                        for row_index in block
                        if field in cls._surface_type_enabled_fields(rows[row_index].surface)
                        and len(cls._pose_tolerance_overlay_values(rows[row_index], field)) > 1
                    ),
                    None,
                )
                if source_index is None:
                    continue
                source_values = cls._pose_tolerance_overlay_values(rows[source_index], field)
                if len(source_values) <= 1:
                    continue
                source_nominal = float(getattr(rows[source_index], field))
                previous_source_nominal = (
                    float(getattr(previous_rows[source_index], field))
                    if 0 <= source_index < len(previous_rows)
                    else source_nominal
                )
                nominal_delta = source_nominal - previous_source_nominal
                value_deltas = [float(value) - source_nominal for value in source_values]
                for row_index in block:
                    row = rows[row_index]
                    if field not in cls._surface_type_enabled_fields(row.surface):
                        continue
                    if row_index == source_index:
                        row_nominal = source_nominal
                    else:
                        base_nominal = (
                            float(getattr(previous_rows[row_index], field))
                            if 0 <= row_index < len(previous_rows)
                            else float(getattr(row, field))
                        )
                        row_nominal = base_nominal + nominal_delta
                        setattr(row, field, float(row_nominal))
                    row_values = [float(row_nominal) + delta for delta in value_deltas]
                    row.advanced = cls._advanced_with_pose_tolerance_overlay(row.advanced, field, row_values)
            index = end + 1

    def _on_table_click(self, event: tk.Event) -> str | None:
        region = self.table.identify_region(event.x, event.y)
        if region == "separator":
            self._table_column_resize_active = True
            self._clear_table_grid()
            self._hide_active_cell_border()
            self._schedule_table_grid_update(delay=1)
            return None
        if region == "heading":
            return None
        self._table_column_resize_active = False
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        self.table.focus_set()
        if not row_id or not column_id:
            self._clear_table_selection()
            return "break"
        self._active_cell = (row_id, column_id)
        children = list(self.table.get_children())
        shift_pressed = bool(event.state & 0x0001)
        control_pressed = bool(event.state & 0x0004)
        if column_id == "#1" and children and not shift_pressed:
            row_index = self._table_item_row_index(row_id)
            if row_index is None:
                if control_pressed:
                    selected = set(self.table.selection())
                    if row_id in selected:
                        selected.remove(row_id)
                    else:
                        selected.add(row_id)
                    ordered = [item for item in children if item in selected]
                    if ordered:
                        self.table.selection_set(ordered)
                    else:
                        self.table.selection_remove(*children)
                else:
                    self.table.selection_set(row_id)
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
                self._schedule_active_cell_border_update()
                return "break"
            block_indices = self._element_indices_for_index(self.rows, row_index)
            block_items = [
                item
                for index in block_indices
                for item in [self._table_item_for_row_index(index)]
                if item is not None
            ]
            self._active_cell = None
            if control_pressed:
                selected = set(self.table.selection())
                if block_items and all(item in selected for item in block_items):
                    selected.difference_update(block_items)
                else:
                    selected.update(block_items or [row_id])
                ordered = [item for item in children if item in selected]
                if ordered:
                    self.table.selection_set(ordered)
                else:
                    self.table.selection_remove(*children)
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
            else:
                self.table.selection_set(block_items or [row_id])
                self._selection_anchor_row = row_id
                self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        if shift_pressed and children:
            anchor = self._selection_anchor_row
            if anchor not in children:
                anchor = self.table.focus() or row_id
            if anchor not in children:
                anchor = row_id
            start = children.index(anchor)
            end = children.index(row_id)
            if start <= end:
                selected_range = children[start : end + 1]
            else:
                selected_range = children[end : start + 1]
            if control_pressed:
                selected = set(self.table.selection())
                selected.update(selected_range)
                ordered = [item for item in children if item in selected]
                self.table.selection_set(ordered)
            else:
                self.table.selection_set(selected_range)
            self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        elif control_pressed:
            selected = set(self.table.selection())
            if row_id in selected:
                selected.remove(row_id)
            else:
                selected.add(row_id)
            ordered = [item for item in children if item in selected]
            self.table.selection_set(ordered)
            self._selection_anchor_row = row_id
            self.table.focus(row_id)
            self._schedule_active_cell_border_update()
            return "break"
        else:
            self.table.selection_set(row_id)
            self._selection_anchor_row = row_id
        self.table.focus(row_id)
        self._schedule_active_cell_border_update()
        return "break"

    def _on_table_drag(self, event: tk.Event) -> str | None:
        if self._table_column_resize_active:
            self._schedule_table_grid_update(delay=1)
            self._schedule_active_cell_border_update(delay=1)
        return None

    def _on_table_button_release(self, event: tk.Event) -> str | None:
        if self._table_column_resize_active:
            self._table_column_resize_active = False
            self._schedule_table_grid_update(delay=1)
            self._schedule_active_cell_border_update(delay=1)
        return None

    def _move_active_cell(self, event: tk.Event) -> str:
        self.table.focus_set()
        children = list(self.table.get_children())
        if not children:
            return "break"
        if self._active_cell is None:
            row_id = children[0]
            column_id = "#2"
        else:
            row_id, column_id = self._active_cell
            if row_id not in children:
                row_id = children[0]
            column_index = int(column_id.replace("#", ""))
            row_index = children.index(row_id)
            if event.keysym == "Left":
                column_index = max(2, column_index - 1)
            elif event.keysym == "Right":
                column_index = min(len(FIELDS), column_index + 1)
            elif event.keysym == "Up":
                row_index = max(0, row_index - 1)
            elif event.keysym == "Down":
                row_index = min(len(children) - 1, row_index + 1)
            row_id = children[row_index]
            column_id = f"#{column_index}"
        self._active_cell = (row_id, column_id)
        self.table.focus(row_id)
        self.table.selection_set(row_id)
        self._ensure_active_cell_visible(row_id, column_id)
        self._schedule_active_cell_border_update()
        self._schedule_table_grid_update(delay=1)
        return "break"

    def _ensure_active_cell_visible(self, row_id: str, column_id: str) -> None:
        self.table.see(row_id)
        self.update_idletasks()
        columns = list(self.table["columns"])
        if column_id == "#2":
            self.table.xview_moveto(0.0)
            self.update_idletasks()
        target_bbox = self.table.bbox(row_id, column_id)
        if target_bbox:
            x, _y, width, _height = target_bbox
            visible_width = max(self.table.winfo_width(), 1)
            if x >= 0 and (x + width) <= visible_width:
                self._schedule_active_cell_border_update()
                self._schedule_table_grid_update(delay=1)
                return

        total_width = 0
        target_left = 0
        target_width = 0
        target_field = FIELDS[int(column_id.replace("#", "")) - 1]
        for field in columns:
            width = int(self.table.column(field, "width"))
            if field == target_field:
                target_left = total_width
                target_width = width
            total_width += width
        if total_width <= 0:
            return
        visible_width = max(self.table.winfo_width(), 1)
        view_left, _view_right = self.table.xview()
        visible_left = view_left * total_width
        visible_right = visible_left + visible_width
        if target_left < visible_left:
            desired_left = max(0.0, target_left - 16.0)
            self.table.xview_moveto(desired_left / total_width)
        elif target_left + target_width > visible_right:
            desired_left = max(0.0, target_left + target_width - visible_width + 16.0)
            self.table.xview_moveto(min(1.0, desired_left / total_width))
        self.update_idletasks()
        self._schedule_active_cell_border_update()
        self._schedule_table_grid_update(delay=1)

    def _hide_active_cell_border(self) -> None:
        for part in self._cell_border_parts:
            part.place_forget()

    def _clear_selection_row_borders(self) -> None:
        overlays = self.__dict__.get("_selection_border_overlays", [])
        for part in overlays:
            try:
                part.destroy()
            except Exception:
                pass
        self._selection_border_overlays = []

    def _update_selection_row_borders(self) -> None:
        if "table" not in self.__dict__:
            return
        self._clear_selection_row_borders()
        selected = list(self.table.selection())
        if not selected:
            return
        border_color = "#2563eb"
        table_width = max(int(self.table.winfo_width()), 1)
        columns = list(self.table["columns"])
        children = list(self.table.get_children())
        selected_indices = sorted(children.index(item) for item in selected if item in children)
        if not selected_indices:
            return

        blocks: list[list[int]] = []
        for index in selected_indices:
            if not blocks or index != blocks[-1][-1] + 1:
                blocks.append([index])
            else:
                blocks[-1].append(index)

        def row_bbox(item: str) -> tuple[int, int, int, int] | None:
            for column_index in range(1, len(columns) + 1):
                bbox = self.table.bbox(item, f"#{column_index}")
                if bbox and len(bbox) == 4:
                    return bbox
            return None

        for block in blocks:
            visible_ranges: list[tuple[int, int]] = []
            for index in block:
                item = children[index]
                if not self.table.exists(item):
                    continue
                bbox = row_bbox(item)
                if not bbox:
                    continue
                _x, y, _width, height = bbox
                if height <= 0:
                    continue
                visible_ranges.append((y, y + height))
            if not visible_ranges:
                continue
            y_top = min(start for start, _end in visible_ranges)
            y_bottom = max(end for _start, end in visible_ranges)
            height = max(0, y_bottom - y_top)
            if height <= 0:
                continue
            top = tk.Frame(self.table, bg=border_color, height=2)
            bottom = tk.Frame(self.table, bg=border_color, height=2)
            left = tk.Frame(self.table, bg=border_color, width=2)
            right = tk.Frame(self.table, bg=border_color, width=2)
            top.place(x=0, y=y_top, width=table_width, height=2)
            bottom.place(x=0, y=y_bottom - 2, width=table_width, height=2)
            left.place(x=0, y=y_top, width=2, height=height)
            right.place(x=table_width - 2, y=y_top, width=2, height=height)
            self._selection_border_overlays.extend([top, bottom, left, right])

    def _update_active_cell_border(self, _event: tk.Event | None = None) -> None:
        self._active_cell_border_after_id = None
        if self._active_cell is None:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        row_id, column_id = self._active_cell
        if not self.table.exists(row_id):
            self._active_cell = None
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        try:
            bbox = self.table.bbox(row_id, column_id)
        except tk.TclError:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        if not bbox or len(bbox) != 4:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        x, y, width, height = bbox
        if width <= 0 or height <= 0:
            self._hide_active_cell_border()
            self._update_selection_row_borders()
            return
        self._update_selection_row_borders()
        top, bottom, left, right = self._cell_border_parts
        top.place(x=x, y=y, width=width, height=2)
        bottom.place(x=x, y=y + height - 2, width=width, height=2)
        left.place(x=x, y=y, width=2, height=height)
        right.place(x=x + width - 2, y=y, width=2, height=height)

    def _schedule_active_cell_border_update(self, *, delay: int | None = None) -> None:
        if self._active_cell_border_after_id is not None:
            return
        try:
            if delay is None:
                self._active_cell_border_after_id = self.after_idle(self._update_active_cell_border)
            else:
                self._active_cell_border_after_id = self.after(max(0, int(delay)), self._update_active_cell_border)
        except tk.TclError:
            self._active_cell_border_after_id = None

    def _on_table_scroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._schedule_table_grid_update()
        self._schedule_active_cell_border_update()

    def _on_table_xview(self, *args: object) -> None:
        self.table.xview(*args)
        self._schedule_table_grid_update(delay=16)
        self._update_active_cell_border()

    def _on_table_xscroll(self, scrollbar: ttk.Scrollbar, first: str, last: str) -> None:
        scrollbar.set(first, last)
        self._update_active_cell_border()

    def _clear_table_grid(self) -> None:
        for part in self._grid_overlays:
            part.destroy()
        self._grid_overlays.clear()

    def _table_grid_context(self) -> tuple[list[str], tuple[str, ...], list[tuple[str, tuple[int, int, int, int]]]]:
        columns = list(self.table["columns"])
        items = tuple(self.table.get_children())
        visible_bboxes = []
        if columns and items:
            column_ids = [f"#{column_index}" for column_index in range(1, len(columns) + 1)]
            for item in items:
                for column_id in column_ids:
                    bbox = self.table.bbox(item, column_id)
                    if bbox:
                        visible_bboxes.append((item, bbox))
                        break
        return columns, items, visible_bboxes

    def _schedule_table_grid_update(self, _event: tk.Event | None = None, delay: int = 30) -> None:
        if self._grid_after_id is not None:
            try:
                self.after_cancel(self._grid_after_id)
            except tk.TclError:
                pass
            self._grid_after_id = None
        try:
            self._grid_after_id = self.after(max(0, int(delay)), self._update_table_grid)
        except tk.TclError:
            self._grid_after_id = None

    def _update_table_grid(self, _event: tk.Event | None = None) -> None:
        self._grid_after_id = None
        self._clear_table_grid()
        columns, items, visible_bboxes = self._table_grid_context()
        grid_color = "#e2e7ef"
        if not columns or not items or not visible_bboxes:
            return
        data_top = min(bbox[1] for _, bbox in visible_bboxes)
        data_bottom = max(bbox[1] + bbox[3] for _, bbox in visible_bboxes)
        data_height = max(0, data_bottom - data_top)
        if data_height <= 0:
            return

        first_item = visible_bboxes[0][0]
        for column_index in range(1, len(columns)):
            bbox = self.table.bbox(first_item, f"#{column_index}")
            if not bbox:
                continue
            x, _y, width, _height = bbox
            separator = tk.Frame(self.table, bg=grid_color, width=1)
            separator.place(x=x + width - 1, y=data_top, width=1, height=data_height)
            self._grid_overlays.append(separator)

        for item, bbox in visible_bboxes:
            _x, y, width, height = bbox
            row_line = tk.Frame(self.table, bg=grid_color, height=1)
            row_line.place(x=0, y=y + height - 1, relwidth=1.0, height=1)
            self._grid_overlays.append(row_line)

        self._draw_optimization_cell_markers(items, columns)
        self._schedule_active_cell_border_update()

    def _draw_optimization_cell_markers(self, items: tuple[str, ...], columns: list[str]) -> None:
        if not items or not columns:
            return
        field_to_column = {field: f"#{index + 1}" for index, field in enumerate(columns)}
        for item in items:
            row_index = self._table_item_row_index(item)
            if row_index is None or not (0 <= row_index < len(self.rows)):
                continue
            row = self.rows[row_index]
            for field in self._optimization_marker_fields_for_row(row):
                column_id = field_to_column.get(field)
                if not column_id:
                    continue
                bbox = self.table.bbox(item, column_id)
                if not bbox or len(bbox) != 4:
                    continue
                x, y, width, height = bbox
                if width <= 24 or height <= 8:
                    continue
                marker_width = min(max(16, int(width * 0.22)), 24)
                marker = tk.Label(
                    self.table,
                    text=OPTIMIZATION_CELL_MARKER_TEXT,
                    bg=OPTIMIZATION_CELL_MARKER_BG,
                    fg=OPTIMIZATION_CELL_MARKER_FG,
                    bd=1,
                    relief="solid",
                    padx=0,
                    pady=0,
                    font=("TkDefaultFont", 8, "bold"),
                )
                marker.place(
                    x=x + width - marker_width - 1,
                    y=y + 2,
                    width=marker_width,
                    height=max(1, height - 4),
                )
                marker.bind(
                    "<Button-1>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                marker.bind(
                    "<Button-3>",
                    lambda event, selected_item=item, selected_field=field: self._on_optimization_marker_click(
                        event,
                        selected_item,
                        selected_field,
                    ),
                )
                self._grid_overlays.append(marker)

    def _on_optimization_marker_click(self, event: tk.Event, row_id: str, field: str) -> str:
        if not self.table.exists(row_id) or field not in FIELDS:
            return "break"
        column_id = f"#{FIELDS.index(field) + 1}"
        self._active_cell = (row_id, column_id)
        self.table.focus(row_id)
        self.table.selection_set(row_id)
        self._schedule_active_cell_border_update()
        return "break"

    def _refresh_operand_surface_choices(self) -> None:
        values = ["Auto"]
        for index, row in enumerate(self.rows):
            if row.surface in {"Object", "Image"}:
                continue
            values.append(f"{index}: {row.name}")
        for label, var in self.operand_surface_vars.items():
            current = var.get().strip() if var.get() else "Auto"
            if current not in values:
                var.set("Auto")
        for widget in self.winfo_children():
            self._apply_surface_values_to_descendants(widget, values)

    def _apply_surface_values_to_descendants(self, widget, values) -> None:
        if isinstance(widget, ttk.Combobox):
            textvar = widget.cget("textvariable")
            for var in self.operand_surface_vars.values():
                if str(var) == textvar:
                    widget["values"] = values
                    break
        for child in widget.winfo_children():
            self._apply_surface_values_to_descendants(child, values)

    def _sync_object_controls(self) -> None:
        if not hasattr(self, "field_summary_var"):
            return
        self._apply_image_diameter_mode()
        self._sync_field_mode_ui()
        metrics = self._field_metrics()
        self.field_summary_var.set(
            "Field half-angle: {angle:.3g} deg\nObject semi-height: {obj:.3g} mm\nParaxial image semi-height: {parax:.3g} mm\nReal image semi-height: {real:.3g} mm".format(
                angle=metrics["angle_deg"],
                obj=metrics["object_height"],
                parax=metrics["paraxial_image_height"],
                real=metrics["real_image_height"],
            )
        )
        warning = ""
        if self.rows and self._current_object_mode() == "Finite":
            object_half_size = max(float(self.rows[0].diameter) / 2.0, 0.0)
            if abs(metrics["object_height"]) > object_half_size + 1e-9:
                warning = f"Field semi-height exceeds object half-size ({object_half_size:.3g} mm)."
        self.field_warning_var.set(warning)
        self._update_field_status_hint()

    def _on_object_mode_changed(self, _event=None) -> None:
        self._sync_field_default_from_current_type()
        self._sync_field_mode_ui()
        self._sync_left_mode_controls()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _on_image_diameter_mode_changed(self, _event=None) -> None:
        self._apply_image_diameter_mode()
        self._sync_table()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _apply_camera_coverage_autofill(self, camera_name: str) -> dict | None:
        """Set the image-surface aperture + Real Image Height so the image
        circle covers the selected camera's sensor (corners included).

        Shared by the interactive camera dropdown (``_on_camera_model_changed``)
        and layout load, so a layout that *loads* with a camera already selected
        lands in the covered state too (bug 0033 -- previously the auto-fill ran
        only on an interactive dropdown commit). Pure model mutation: it does not
        touch history capture, status text, or the plot-update flag. Returns the
        applied ``{"image_diameter", "real_image_height"}`` or ``None`` when no
        sensor size is available.
        """
        if camera_name == CAMERA_NONE_LABEL:
            return None
        # The image circle must *cover* the rectangular sensor (corners
        # included), so the image-surface clear aperture follows the sensor
        # diagonal rather than the inscribed sensor width (the old
        # ``image_diameter_mm``, which clipped the corners). The vendor sensor
        # active area itself is drawn at its real size by the detector override.
        coverage = camera_image_coverage_mm(camera_name)
        image_diameter = coverage[0] if coverage is not None else camera_image_diameter_mm(camera_name)
        if image_diameter is None or not self.rows or self.rows[-1].surface != "Image":
            return None
        self._set_image_diameter_mode("Manual")
        self.rows[-1].diameter = float(image_diameter)
        # Auto-fill the field so the outermost field lands on the sensor corner
        # (Real Image Height = sensor half-diagonal); the image circle then
        # covers the whole sensor instead of inscribing it.
        real_image_height = coverage[1] if coverage is not None else None
        if real_image_height is not None and hasattr(self, "field_type_var"):
            self.field_type_var.set(self._field_type_display_label("Real Image Height"))
            self._last_field_type = "Real Image Height"
            self._field_type_defaults["Real Image Height"] = f"{float(real_image_height):.6g}"
            self.field_value_var.set(f"{float(real_image_height):.6g}")
            self._sync_field_mode_ui()
            # bugs/0311: mark the field as camera-pinned so decouple can un-pin it
            # (and never wipe a surrogate's legitimate Real Image Height field).
            self._camera_pinned_field = True
        camera_info = self._current_camera_record() or {}
        step_path = camera_info.get("step_path")
        if self.imported_camera_step_path is None and step_path:
            candidate = Path(step_path).expanduser()
            if candidate.exists():
                self.imported_camera_step_path = candidate
        self._sync_object_diameter_from_manual_image()
        self._sync_table()
        self._sync_object_controls()
        return {"image_diameter": float(image_diameter), "real_image_height": real_image_height}

    def _stash_camera_precouple_field_state(self) -> None:
        """bugs/0296: remember the field / image-surface aperture the layout had
        *before* a camera sensor coupling overwrote it, so deleting (or
        de-selecting) the camera can put it back. Captured only on the
        uncoupled->coupled transition (guarded by an existing stash) so that
        re-coupling to a different camera preserves the original pre-camera
        state. Interactive-couple only (dropdown / STEP import) -- never on
        layout load, which has no meaningful "before" to remember.
        """
        if getattr(self, "_camera_coverage_precouple_stash", None) is not None:
            return
        image_diameter = None
        if self.rows and self.rows[-1].surface == "Image":
            try:
                image_diameter = float(self.rows[-1].diameter)
            except (TypeError, ValueError):
                image_diameter = None
        self._camera_coverage_precouple_stash = {
            "field_type": self._current_field_type(),
            "field_value": self.field_value_var.get(),
            "image_diameter_mode": self._current_image_diameter_mode(),
            "image_diameter": image_diameter,
        }

    def _decouple_camera_model(self) -> bool:
        """bugs/0296: reverse the camera sensor coupling -- reset the camera
        model to None and restore the pre-couple field / image-surface aperture
        stashed on the first couple. Called when the camera STEP overlay is
        deleted (flag 20260713_160023 "after BC-GM camera deleted, the sensor
        size remain on the screen") and when the dropdown is set back to None,
        so that no camera means no sensor coverage (the display follows the
        model). Returns True when a stash was restored.
        """
        if hasattr(self, "camera_model_var"):
            self.camera_model_var.set(CAMERA_NONE_LABEL)
        stash = getattr(self, "_camera_coverage_precouple_stash", None)
        if stash is None:
            # bugs/0312: capture the camera-autofill VALUE fingerprint BEFORE the
            # Manual->Auto flip below, since the flip rewrites the image aperture
            # mode that is part of that signature. An orphaned-camera load skipped
            # the flag-setting autofill, so the flag is False here -- the signature
            # is the only surviving evidence that this field was camera-pinned.
            pinned_by_signature = self._field_matches_camera_autofill_signature()
            # bugs/0306: a layout saved with a camera coupled *before* the precouple
            # stash was persisted (any legacy camera file) has no pre-camera state to
            # restore. Don't leave the image aperture locked to the now-deleted sensor
            # -- flip Manual back to the self-computing Auto mode so the aperture is no
            # longer pinned. The exact pre-camera field can't be reconstructed from a
            # legacy file, so rebuilding the camera layout records the perfect revert.
            if self._current_image_diameter_mode() == "Manual":
                self._set_image_diameter_mode("Auto")
                self._apply_image_diameter_mode()
                self._sync_object_diameter_from_manual_image()
                self._sync_table()
                self._sync_object_controls()
            # bugs/0311: the couple also pinned the field to Real Image Height =
            # sensor half-diagonal, which drives the image-circle / object-FOV
            # overlay. The Manual->Auto flip above freed the image APERTURE but
            # left that field pinned, so deleting the camera left the image circle
            # / FOV on-screen (flag 20260715_084524 "After camera deleted, FOV,
            # Max Sensor, Image circle remains"). Un-pin the field back to the
            # object-mode default -- no camera means no coverage overlay. Gated on
            # the couple's own pin flag OR (bugs/0312) the camera-autofill value
            # signature, so an orphaned-camera load -- whose invalid model skipped
            # the flag-setting autofill -- is still un-pinned, while a surrogate
            # that *legitimately* uses a Real Image Height field (no camera) is
            # never wiped.
            if getattr(self, "_camera_pinned_field", False) or pinned_by_signature:
                self._reset_camera_pinned_field_to_default()
            self._camera_pinned_field = False
            return False
        self._camera_coverage_precouple_stash = None
        mode = stash.get("image_diameter_mode")
        if mode in {"Auto", "Manual"}:
            self._set_image_diameter_mode(mode)
        image_diameter = stash.get("image_diameter")
        if image_diameter is not None and self.rows and self.rows[-1].surface == "Image":
            self.rows[-1].diameter = float(image_diameter)
        field_type = stash.get("field_type")
        if field_type and hasattr(self, "field_type_var"):
            field_value = str(stash.get("field_value", ""))
            self.field_type_var.set(self._field_type_display_label(field_type))
            self._last_field_type = field_type
            self._field_type_defaults[field_type] = field_value
            self.field_value_var.set(field_value)
            self._sync_field_mode_ui()
        self._sync_object_diameter_from_manual_image()
        self._sync_table()
        self._sync_object_controls()
        self._camera_pinned_field = False  # bugs/0311: stash restored the real field
        return True

    def _field_matches_camera_autofill_signature(self) -> bool:
        """bugs/0312: recognise a camera-pinned field by its VALUE fingerprint,
        independent of the ``_camera_pinned_field`` flag.

        ``_apply_camera_coverage_autofill`` writes a unique, camera-only signature:
        image aperture Manual, field ``Real Image Height`` = the sensor
        half-diagonal, and the Image-surface clear aperture = the sensor
        *diagonal* -- i.e. ``image_diameter == 2 x field_value`` exactly
        (``camera_image_coverage_mm`` returns ``(diagonal, 0.5 * diagonal)``).

        The flag alone is not enough: a layout saved with a camera that isn't in
        THIS machine's registry (cross-machine sync moves the scene, not the
        per-machine imported-camera JSON) loads with ``camera_model`` forced to
        None, so the load-time autofill that sets the flag never runs -- yet the
        Real Image Height field is still restored, so deleting the still-shown
        camera STEP left the image-circle / FOV overlay on-screen (flag
        20260715_092801, a 0311 resurface). This value test catches that
        orphaned-camera case on the editor. It stays narrow: a surrogate that
        legitimately uses Real Image Height keeps its own (Auto, or non-2x) image
        aperture, so its aperture never equals twice the field and it is untouched.
        """
        if self._current_field_type() != "Real Image Height":
            return False
        if self._current_image_diameter_mode() != "Manual":
            return False
        if not self.rows or self.rows[-1].surface != "Image":
            return False
        try:
            field_value = float(self.field_value_var.get())
            image_diameter = float(self.rows[-1].diameter)
        except (TypeError, ValueError):
            return False
        if not (field_value > 0.0 and image_diameter > 0.0):
            return False
        return abs(image_diameter - 2.0 * field_value) <= max(0.05, 2e-3 * image_diameter)

    def _reset_camera_pinned_field_to_default(self) -> bool:
        """bugs/0311: reset a still-pinned camera field back to the object-mode
        default so the image-circle / object-FOV overlay clears on decouple.

        Coupling a camera pins the field to ``Real Image Height`` = the sensor
        half-diagonal (``_apply_camera_coverage_autofill``), and that field drives
        ``_image_circle_radius`` / the object-FOV box. When the camera is decoupled
        WITHOUT a pre-couple stash to restore (a layout that *loaded* with a camera
        coupled -- the stash is interactive-only), that pin would otherwise linger.
        Only touches the field when it is still in the camera-set Real Image Height
        mode; returns True when a reset was applied.
        """
        if self._current_field_type() != "Real Image Height" or not hasattr(self, "field_type_var"):
            return False
        default_type = "Angle" if self._current_object_mode() == "Infinity" else "Object Height"
        self.field_type_var.set(self._field_type_display_label(default_type))
        self._last_field_type = default_type
        self._field_type_defaults[default_type] = "0.0"
        self.field_value_var.set("0.0")
        self._sync_field_mode_ui()
        return True

    def _couple_camera_model_from_step(self, step_path) -> str | None:
        """When an imported camera STEP is a recognised vendor camera, select
        that model and run the sensor autofill -- the same field/image-circle
        sync a dropdown selection performs (bug 0295 Stage 2).

        This closes the "import from folder -> create lens surrogate seems not
        complete" gap: after the surrogate is built, importing the vendor camera
        STEP now shrinks the field from the datasheet max real image height
        (image-circle/2) to the true sensor half-diagonal, so the object-plane
        FOV follows the real sensor instead of the lens's max-sensor capability.
        Returns the coupled model name, or ``None`` when the STEP is not a known
        vendor camera (the raw body is then shown as-is).
        """
        model = camera_model_for_step_path(step_path)
        if model is None or model == CAMERA_NONE_LABEL:
            return None
        if not hasattr(self, "camera_model_var"):
            return None
        self._stash_camera_precouple_field_state()  # bugs/0296: enable delete-decouple revert
        self.camera_model_var.set(model)
        applied = self._apply_camera_coverage_autofill(model)
        return model if applied is not None else None

    def _on_camera_model_changed(self, _event=None) -> None:
        self._begin_history_capture()
        camera_name = self._current_camera_model()
        if camera_name == CAMERA_NONE_LABEL:
            # bugs/0296: setting the dropdown back to None decouples the sensor
            # coverage too (symmetric with a camera-STEP delete) -- restore the
            # pre-couple field / image aperture instead of leaving it stuck.
            self._decouple_camera_model()
            self._commit_history_capture()
            self._mark_plot_update_pending()
            return
        self._stash_camera_precouple_field_state()  # bugs/0296: enable decouple revert
        applied = self._apply_camera_coverage_autofill(camera_name)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        if applied is None:
            self.status_var.set(f"Camera selected: {camera_name}; no sensor size available.")
            return
        image_diameter = applied["image_diameter"]
        real_image_height = applied["real_image_height"]
        summary = camera_short_summary(camera_name)
        detail = f" ({summary})" if summary else ""
        field_note = (
            f"; Real Image Height set to {float(real_image_height):.6g} mm"
            if real_image_height is not None
            else ""
        )
        self.status_var.set(
            f"Camera selected: {camera_name}{detail}; image diameter set to "
            f"{float(image_diameter):.6g} mm{field_note}. Click Update."
        )

    def _apply_initial_field_defaults(self) -> None:
        if self._field_defaults_initialized or not hasattr(self, "field_type_var"):
            return
        if self._current_object_mode() == "Infinity":
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
        else:
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
        self._field_defaults_initialized = True
        self._sync_field_mode_ui()

    def _apply_initial_layout_view_defaults(self, name: str) -> None:
        if not hasattr(self, "display_orientation_var"):
            return
        if hasattr(self, "projection_display_mode_var"):
            self.projection_display_mode_var.set(PROJECTION_MODE_FULL_3D)
        if name == FOLDED_STARTER_LAYOUT_TITLE:
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Finite")
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        elif name == "Reset":
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Infinity")
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        elif name == "Doublet Lens":
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Infinity")
            self.field_type_var.set(self._field_type_display_label("Angle"))
            self._last_field_type = "Angle"
            self._field_type_defaults["Angle"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()
        else:
            self.display_orientation_var.set("YZ")
            self.object_mode_var.set("Finite")
            self.field_type_var.set(self._field_type_display_label("Object Height"))
            self._last_field_type = "Object Height"
            self._field_type_defaults["Object Height"] = "0.0"
            self.field_value_var.set("0.0")
            self._sync_field_mode_ui()

    def _on_field_type_changed(self, _event=None) -> None:
        self._sync_field_default_from_current_type()
        self._sync_field_mode_ui()
        self._sync_object_controls()
        self._mark_plot_update_pending()

    def _sync_field_default_from_current_type(self) -> None:
        if not hasattr(self, "field_value_var"):
            return
        previous_type = getattr(self, "_last_field_type", self._current_field_type())
        field_type = self._current_field_type()
        current_text = self.field_value_var.get().strip()
        if current_text:
            self._field_type_defaults[previous_type] = current_text
        default_text = self._field_type_defaults.get(field_type, "0.0")
        self._last_field_type = field_type
        if current_text != default_text:
            self.field_value_var.set(default_text)

    def _sync_field_mode_ui(self) -> None:
        if not hasattr(self, "field_type_menu"):
            return
        current_type = self._current_field_type()
        if self._current_object_mode() == "Infinity":
            values = [
                "Angle",
                "Paraxial Image Height",
                "Real Image Height",
                "Object Height",
            ]
            note = "Preferred: Field half-angle for infinity object. Image semi-height modes are derived targets."
        else:
            values = [
                "Object Height",
                "Paraxial Image Height",
                "Real Image Height",
                "Angle",
            ]
            note = "Preferred: Object semi-height for finite object. Field half-angle remains available as a derived field."
        self.field_type_menu["values"] = [self._field_type_display_label(value) for value in values]
        self.field_type_var.set(self._field_type_display_label(current_type))
        if hasattr(self, "field_mode_note_var"):
            self.field_mode_note_var.set(note)
        if hasattr(self, "field_value_label_var"):
            self.field_value_label_var.set(self._field_type_value_label(current_type))
        self._sync_field_sample_count_state()
        self._update_field_status_hint()

    def _sync_field_sample_count_state(self) -> None:
        field_count_var = self.__dict__.get("field_count_var")
        field_count_entry = self.__dict__.get("field_count_entry")
        if field_count_var is None or field_count_entry is None:
            return
        if self._current_source_model() != SOURCE_MODEL_DEFAULT:
            return

        saved = self.__dict__.get("_left_mode_saved_values")
        if saved is None:
            saved = {}
            self._left_mode_saved_values = saved

        active = self._field_sampling_is_active()
        try:
            current = str(field_count_var.get()).strip()
        except Exception:
            current = ""

        if active:
            if current == "NA":
                restored = str(saved.pop("field_count_var", "1")).strip()
                if not restored or restored == "NA":
                    restored = "1"
                try:
                    field_count_var.set(restored)
                except Exception:
                    pass
            state = "normal"
        else:
            if current not in {"", "NA"}:
                saved["field_count_var"] = current
            if current != "NA":
                try:
                    field_count_var.set("NA")
                except Exception:
                    pass
            state = "disabled"

        for widget in (field_count_entry, self.__dict__.get("field_count_label")):
            if widget is None:
                continue
            try:
                widget.configure(state=state)
            except Exception:
                pass

    def add_surface(self) -> None:
        self._begin_history_capture()
        arm_key = self._current_arm_view_key()
        selected_indices = self._selected_table_indices()
        if selected_indices:
            insert_at = max(selected_indices) + 1
        elif arm_key:
            insert_at = self._default_insert_index_for_arm_key(arm_key)
        else:
            insert_at = len(self.rows)
            if self.rows and self.rows[-1].surface == "Image":
                insert_at -= 1
        insert_at = max(1, min(insert_at, len(self.rows) - (1 if self.rows and self.rows[-1].surface == "Image" else 0)))
        row = SurfaceRow()
        if arm_key:
            self._apply_arm_key_metadata_to_row(row, arm_key)
        self.rows.insert(insert_at, row)
        self._sync_table()
        self._select_table_indices([insert_at], focus_index=insert_at)
        self._commit_history_capture()
        self.refresh_plot()

    def delete_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        indices = self._selected_table_indices()
        for index in reversed(indices):
            del self.rows[index]
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot()

    def delete_optical_step_rows(self, indices) -> int:
        """Delete the promoted optical-solid STEP rows among *indices*.

        Only rows carrying ``StepOverlayPromotion`` metadata are removed, so a
        plain prescription row that happens to be selected is never deleted.
        Returns the number of rows removed.
        """
        targets = sorted(
            {
                int(index)
                for index in indices
                if 0 <= int(index) < len(self.rows)
                and self._is_open3d_promoted_optical_solid_row(self.rows[int(index)])
            },
            reverse=True,
        )
        if not targets:
            return 0
        self._commit_pending_table_edit()
        self._begin_history_capture()
        for index in targets:
            del self.rows[index]
        self._normalize_special_rows()
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        return len(targets)

    def duplicate_selected(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        indices = self._selected_table_indices()
        insert_at = indices[-1] + 1
        duplicates = duplicate_rows_for_indices(self.rows, indices)
        for offset, row in enumerate(duplicates):
            self.rows.insert(insert_at + offset, row)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(list(range(insert_at, insert_at + len(duplicates))), focus_index=insert_at)
        self._commit_history_capture()
        self.refresh_plot()

    def _selected_copy_indices(self) -> list[int]:
        indices: list[int] = []
        seen: set[int] = set()
        for block in self._selected_element_blocks():
            for index in block:
                if index <= 0 or index >= len(self.rows) - 1 or index in seen:
                    continue
                seen.add(index)
                indices.append(index)
        return sorted(indices)

    @staticmethod
    def _surface_rows_from_clipboard_records(records: object) -> list[SurfaceRow]:
        return surface_rows_from_records(records)

    @classmethod
    def _surface_rows_from_clipboard_text(cls, text: str) -> list[SurfaceRow]:
        return surface_rows_from_clipboard_text(text)

    def copy_selected_rows_to_clipboard(self, _event: tk.Event | None = None) -> str:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Copy Surfaces", f"Could not read the surface table:\n\n{exc}", parent=self)
            return "break"
        indices = self._selected_copy_indices()
        if not indices:
            self.status_var.set("Select one or more component surface rows before copying.")
            return "break"
        rows = [SurfaceRow(**asdict(self.rows[index])) for index in indices]
        records = surface_rows_to_records(rows)
        self._surface_row_clipboard = records
        text = surface_rows_to_clipboard_text(rows)
        try:
            ok, backend = self._copy_text_to_clipboard(text)
        except Exception as exc:
            self.append_debug(f"Copy surface rows failed: {exc}")
            ok, backend = False, "none"
        suffix = f" ({backend})" if ok else " (internal clipboard only)"
        self.status_var.set(f"Copied {len(rows)} surface row(s){suffix}.")
        return "break"

    def _pasted_surface_rows(self) -> list[SurfaceRow]:
        try:
            text = self.clipboard_get()
        except Exception:
            text = ""
        rows = self._surface_rows_from_clipboard_text(text) if text else []
        if rows:
            return rows
        return self._surface_rows_from_clipboard_records(self._surface_row_clipboard)

    def paste_rows_from_clipboard(self, _event: tk.Event | None = None) -> str:
        rows = self._pasted_surface_rows()
        if not rows:
            self.status_var.set("No copied KrakenOS surface rows are available to paste.")
            return "break"
        rows = pasteable_component_rows(rows)
        if not rows:
            self.status_var.set("Clipboard contains no pasteable component surface rows.")
            return "break"
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Paste Surfaces", f"Could not read the surface table:\n\n{exc}", parent=self)
            return "break"
        self._remap_inserted_element_labels(rows)
        insert_after = self._selected_insert_index()
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(rows, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.status_var.set(f"Pasted {len(rows)} surface row(s) at S{insert_at}. Click Update to trace.")
        self.refresh_plot(suppress_analysis=True)
        return "break"

    def _selected_table_indices(self) -> list[int]:
        indices = [
            index
            for item in self.table.selection()
            for index in [self._table_item_row_index(item)]
            if index is not None
        ]
        return sorted(indices)

    @staticmethod
    def _indices_are_contiguous(indices: list[int]) -> bool:
        return bool(indices) and indices == list(range(indices[0], indices[-1] + 1))

    def _next_manual_element_label(self) -> str:
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        counter = 1
        while f"Element {counter}" in used:
            counter += 1
        return f"Element {counter}"

    def group_selected_as_element(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Group Element", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        indices = self._selected_table_indices()
        if len(indices) < 2:
            messagebox.showinfo("Group Element", "Select two or more contiguous surface rows first.", parent=self)
            return
        if indices[0] <= 0 or indices[-1] >= len(self.rows) - 1:
            messagebox.showinfo("Group Element", "Object and Image rows cannot be grouped into an element.", parent=self)
            return
        if not self._indices_are_contiguous(indices):
            messagebox.showinfo("Group Element", "Select a contiguous block of rows before grouping.", parent=self)
            return

        self._begin_history_capture()
        label = self._next_manual_element_label()
        for index in indices:
            self.rows[index].element = label
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self.status_var.set(f"Grouped rows {indices[0]}-{indices[-1]} as one element.")

    def ungroup_selected_elements(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Ungroup Element", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        selected_keys = {
            self._element_key(self.rows[index])
            for index in self._selected_table_indices()
            if 0 <= index < len(self.rows)
        }
        selected_keys.discard("")
        if not selected_keys:
            messagebox.showinfo("Ungroup Element", "The selected rows are not part of an element.", parent=self)
            return

        self._begin_history_capture()
        ungrouped_indices = []
        for index, row in enumerate(self.rows):
            if self._element_key(row) in selected_keys:
                row.element = ""
                row.advanced = dict(row.advanced or {})
                row.advanced.pop(ELEMENT_ADVANCED_ATTR, None)
                ungrouped_indices.append(index)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(ungrouped_indices, focus_index=ungrouped_indices[0] if ungrouped_indices else None)
        self._commit_history_capture()
        self.status_var.set(f"Ungrouped {len(ungrouped_indices)} surface row(s).")

    @staticmethod
    def _element_id_from_label(label: str) -> str:
        text = re.sub(r"[^A-Za-z0-9]+", "_", str(label or "").strip()).strip("_")
        return text or "Element"

    @staticmethod
    def _unique_element_label(base: str, used: set[str]) -> str:
        stem = str(base or "Element").strip() or "Element"
        if stem not in used:
            used.add(stem)
            return stem
        counter = 2
        while True:
            candidate = f"{stem} {counter}"
            if candidate not in used:
                used.add(candidate)
                return candidate
            counter += 1

    def _remap_inserted_element_labels(self, rows: list[SurfaceRow]) -> None:
        """Keep inserted/copied element blocks independent from existing blocks."""
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        mapping: dict[str, str] = {}
        for row in rows:
            old_label = self._element_key(row)
            if not old_label:
                continue
            new_label = mapping.get(old_label)
            if new_label is None:
                new_label = self._unique_element_label(old_label, used)
                mapping[old_label] = new_label
            row.element = new_label
            metadata = self._element_metadata(row)
            if _element_metadata_is_default(metadata):
                continue
            metadata["element_name"] = new_label
            metadata["element_id"] = self._element_id_from_label(new_label)
            self._set_element_metadata(row, metadata)

    def _selected_element_blocks(self) -> list[list[int]]:
        blocks: list[list[int]] = []
        seen: set[tuple[int, int]] = set()
        for index in self._selected_table_indices():
            if index <= 0 or index >= len(self.rows) - 1:
                continue
            if self._element_key(self.rows[index]):
                start, end = self._element_block_for_index(self.rows, index)
            else:
                start, end = index, index
            key = (start, end)
            if key in seen:
                continue
            seen.add(key)
            blocks.append(list(range(start, end + 1)))
        return blocks

    def _ensure_element_for_block(self, indices: list[int]) -> str:
        existing = next((self._element_key(self.rows[index]) for index in indices if self._element_key(self.rows[index])), "")
        label = existing or str(self.rows[indices[0]].name or self._next_manual_element_label()).strip()
        if not label:
            label = self._next_manual_element_label()
        for index in indices:
            self.rows[index].element = label
        return label

    def _beam_splitter_element_choices(self) -> list[str]:
        choices = [""]
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            label = self._element_key(row) or str(row.name or f"S{index}").strip() or f"S{index}"
            if label not in choices:
                choices.append(label)
        return choices

    def _metadata_matches_leg_id(
        self,
        metadata: dict[str, object],
        leg_id: str,
        *,
        row: SurfaceRow | None = None,
        row_index: int | None = None,
    ) -> bool:
        return self._leg_id_from_element_metadata(metadata, row=row, row_index=row_index) == str(leg_id or "").strip().lower()

    def _indices_for_leg_key(self, arm_key: str) -> list[int]:
        leg_id = self._leg_id_from_arm_key(arm_key)
        if not leg_id or not self.rows:
            return []
        indices: list[int] = []
        auto_entry = self._auto_leg_entry_for_id(leg_id)
        if auto_entry is not None:
            for index in sorted(set(auto_entry.get("surface_indices", set()) or set())):
                if 0 <= int(index) < len(self.rows):
                    indices.append(int(index))
        seen_blocks: set[tuple[int, int]] = set()
        index = 0 if leg_id == "input" else 1
        last_inclusive = len(self.rows) if leg_id in {"detector", "cross", "return"} or auto_entry is not None else max(len(self.rows) - 1, 0)
        while index < last_inclusive:
            start, end = self._element_block_for_index(self.rows, index)
            block_key = (start, end)
            metadata = self._element_metadata(self.rows[start])
            if block_key not in seen_blocks and self._metadata_matches_leg_id(
                metadata,
                leg_id,
                row=self.rows[start],
                row_index=start,
            ):
                indices.extend(candidate for candidate in range(start, end + 1) if candidate not in indices)
                seen_blocks.add(block_key)
            index = max(end + 1, index + 1)
        return indices

    def _indices_for_arm_key(self, arm_key: str) -> list[int]:
        key = str(arm_key or "").strip()
        if not key or not self.rows:
            return []
        if self._leg_id_from_arm_key(key):
            return self._indices_for_leg_key(key)
        indices: list[int] = []
        seen_blocks: set[tuple[int, int]] = set()
        index = 1
        while index < len(self.rows) - 1:
            start, end = self._element_block_for_index(self.rows, index)
            block_key = (start, end)
            metadata = self._element_metadata(self.rows[start])
            metadata_key = self._arm_key_from_metadata(metadata)
            path = self._branch_path_for_arm_key(key)
            matches_key = metadata_key == key
            if path and self._metadata_arm_key_matches_branch_path(metadata_key, path):
                matches_key = True
            if block_key not in seen_blocks and matches_key:
                indices.extend(range(start, end + 1))
                seen_blocks.add(block_key)
            index = max(end + 1, index + 1)
        return indices

    def _move_blocks_to_physical_leg_position(
        self,
        blocks: list[list[int]],
        leg_id: str,
    ) -> list[int]:
        leg_id = str(leg_id or "").strip().lower()
        leg_order = {
            defined_id: order
            for order, (defined_id, _short_label, _detail) in enumerate(self._physical_leg_definitions())
        }
        target_order = leg_order.get(leg_id)
        if target_order is None or not blocks:
            return []

        selected_positions: set[int] = set()
        for block in blocks:
            for index in block:
                if 0 < index < len(self.rows) - 1:
                    selected_positions.add(int(index))
        if not selected_positions:
            return []

        selected_rows = [row for index, row in enumerate(self.rows) if index in selected_positions]
        remaining_rows = [row for index, row in enumerate(self.rows) if index not in selected_positions]
        if not selected_rows or len(remaining_rows) < 2:
            return []

        def block_leg_id(rows: list[SurfaceRow], start: int) -> str:
            if not (0 <= start < len(rows)):
                return ""
            metadata = self._element_metadata(rows[start])
            return self._leg_id_from_element_metadata(metadata, row=rows[start], row_index=start)

        insert_at = max(1, len(remaining_rows) - 1)
        index = 1
        while index < len(remaining_rows):
            start, end = self._element_block_for_index(remaining_rows, index)
            if remaining_rows[start].surface == "Image":
                insert_at = start
                break
            existing_order = leg_order.get(block_leg_id(remaining_rows, start))
            if existing_order is not None and existing_order > target_order:
                insert_at = start
                break
            index = max(end + 1, index + 1)

        self.rows = remaining_rows[:insert_at] + selected_rows + remaining_rows[insert_at:]
        return list(range(insert_at, insert_at + len(selected_rows)))

    def _surface_indices_for_arm_key(self, arm_key: str) -> set[int]:
        indices = set(self._indices_for_arm_key(arm_key))
        path = self._branch_path_for_arm_key(arm_key)
        if path:
            indices.update(self._branch_path_surface_indices(path))
        return indices

    def _refresh_arm_view_choices(self) -> None:
        menu = self.__dict__.get("arm_view_menu")
        if menu is None:
            return
        choices = [ARM_VIEW_DEFAULT]
        for entry in self._arm_catalog():
            label = entry["label"]
            if label not in choices:
                choices.append(label)
        menu["values"] = choices
        current = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        if current not in choices:
            self.arm_view_var.set(ARM_VIEW_DEFAULT)

    def _arm_key_for_view_label(self, label: str) -> str:
        text = str(label or ARM_VIEW_DEFAULT).strip()
        if text == ARM_VIEW_DEFAULT:
            return ""
        for entry in self._arm_catalog():
            if entry["label"] == text:
                return entry["key"]
        return ""

    def set_arm_view(self, _event: tk.Event | None = None) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path View", f"Could not read the surface table:\n\n{exc}", parent=self)
            self.arm_view_var.set(ARM_VIEW_DEFAULT)
            return
        self._refresh_arm_view_choices()
        focus_label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        self._sync_table()
        if focus_label == ARM_VIEW_DEFAULT:
            self.status_var.set("Path view set to All paths; all components, table rows, and traced paths are shown.")
        else:
            key = self._arm_key_for_view_label(focus_label)
            indices = self._indices_for_arm_key(key)
            if indices and self.__dict__.get("table") is not None:
                self._select_table_indices(indices, focus_index=indices[0])
            self.status_var.set(
                f"Path view set to {focus_label}; table and 2-D plot show common path plus this path."
            )
        self.refresh_plot()

    @staticmethod
    def _normalized_vector(values) -> np.ndarray:
        vector = np.asarray(values, dtype=float).reshape(3)
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            raise ValueError("Cannot normalize a zero vector.")
        return vector / norm

    @staticmethod
    def _surface_tilts_for_normal(direction) -> tuple[float, float, float]:
        unit = LayoutTableWorkbenchMixin._normalized_vector(direction)
        dx, dy, dz = (float(value) for value in unit)
        tilt_y = float(np.rad2deg(np.arcsin(np.clip(dx, -1.0, 1.0))))
        tilt_x = float(np.rad2deg(np.arctan2(-dy, dz)))
        return (tilt_x, tilt_y, 0.0)

    @staticmethod
    def _kraken_tilts_from_rotation_matrix(rotation) -> tuple[float, float, float]:
        return optical_solid_metadata.kraken_tilts_from_rotation_matrix(rotation)

    @staticmethod
    def _path_local_pose(
        frame: dict[str, object],
        *,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> tuple[np.ndarray, tuple[float, float, float]]:
        base_tilts = tuple(float(value) for value in frame["tilts"])  # type: ignore[index]
        base_rotation = _rotation_matrix_from_kraken_tilts(*base_tilts)
        local_rotation = _rotation_matrix_from_kraken_tilts(local_tilt_x, local_tilt_y, local_tilt_z)
        combined = base_rotation @ local_rotation
        local_offset = (
            base_rotation[:, 0] * float(local_decenter_x)
            + base_rotation[:, 1] * float(local_decenter_y)
        )
        tilts = LayoutTableWorkbenchMixin._kraken_tilts_from_rotation_matrix(combined)
        return np.asarray(local_offset, dtype=float), tilts

    def _surface_transform_for_rows(self, rows: list[SurfaceRow], row_index: int) -> np.ndarray:
        system = _build_system_from_specs(self._serializable_specs_for_rows(rows))
        transforms = self._system_transform_list(system)
        if transforms is None or not (0 <= row_index < len(transforms)):
            raise RuntimeError("KrakenOS did not provide surface transforms for path placement.")
        return np.asarray(transforms[row_index], dtype=float)

    def _arm_frame_for_splitter(self, splitter_index: int, arm_role: str) -> dict[str, np.ndarray | tuple[float, float, float]]:
        if not (0 <= splitter_index < len(self.rows)):
            raise RuntimeError("Selected splitter row is out of range.")
        row = self.rows[splitter_index]
        if row.surface != BEAM_SPLITTER_SURFACE:
            raise RuntimeError("Path placement starts from a Beam Splitter row.")
        transform = self._surface_transform_for_rows(self.rows, splitter_index)
        origin = np.asarray(transform[:3, 3], dtype=float)
        normal = self._normalized_vector(transform[:3, 2])
        incoming = np.asarray([0.0, 0.0, 1.0], dtype=float)
        role = str(arm_role).strip()
        if role == "Transmit":
            direction = incoming
        elif role == "Reflect":
            direction = incoming - 2.0 * float(np.dot(incoming, normal)) * normal
        else:
            raise RuntimeError(f"Unsupported path role for placement: {arm_role}")
        direction = self._normalized_vector(direction)
        return {
            "origin": origin,
            "direction": direction,
            "tilts": self._surface_tilts_for_normal(direction),
        }

    def _branch_path_frame(self, branch_path: str) -> dict[str, np.ndarray | tuple[float, float, float] | int]:
        path = str(branch_path or "").strip()
        if not path or path == "primary":
            raise RuntimeError("Choose a traced non-primary Path view first.")
        surface_indices = self._branch_path_surface_sequence(path)
        if not surface_indices:
            raise RuntimeError(f"Could not identify splitter surfaces in traced path: {path}")
        origin_surface = int(surface_indices[-1])
        bundle = getattr(self, "_last_scene_bundle", None)
        candidates = []
        for ray in getattr(bundle, "ray_paths", []) or []:
            if str(getattr(ray, "branch_path", "") or "").strip() != path:
                continue
            surface_ids = np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel()
            points = np.asarray(getattr(ray, "points_world", []), dtype=float)
            if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 2:
                continue
            hit_positions = np.flatnonzero(surface_ids == origin_surface)
            if hit_positions.size == 0:
                continue
            hit_index = int(hit_positions[-1])
            point_index = min(hit_index + 1, points.shape[0] - 1)
            origin = np.asarray(points[point_index], dtype=float)
            if point_index + 1 < points.shape[0]:
                direction = np.asarray(points[point_index + 1], dtype=float) - origin
            elif point_index > 0:
                direction = origin - np.asarray(points[point_index - 1], dtype=float)
            else:
                continue
            norm = float(np.linalg.norm(direction))
            if not np.isfinite(norm) or norm <= 1e-9:
                continue
            candidates.append((origin, direction / norm))
        if not candidates:
            raise RuntimeError(
                "No traced ray segment is available for this BRANCH_PATH. Click Update, choose a traced Path view, then retry."
            )
        origins = np.vstack([origin for origin, _direction in candidates])
        directions = np.vstack([direction for _origin, direction in candidates])
        origin = np.nanmedian(origins, axis=0)
        direction = np.nanmean(directions, axis=0)
        direction = self._normalized_vector(direction)
        return {
            "origin": np.asarray(origin, dtype=float),
            "direction": direction,
            "tilts": self._surface_tilts_for_normal(direction),
            "origin_surface": origin_surface,
            "sample_count": len(candidates),
        }

    @staticmethod
    def _line_frame_near_point(origin, direction, reference_point) -> dict[str, object]:
        base_origin = np.asarray(origin, dtype=float).reshape(3)
        base_direction = LayoutTableWorkbenchMixin._normalized_vector(direction)
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        projection = float(np.dot(reference - base_origin, base_direction))
        target = base_origin + base_direction * projection
        return {
            "origin": base_origin,
            "direction": base_direction,
            "target_point": target,
        }

    @staticmethod
    def _row_local_point_from_world(target_point, z_station: float) -> tuple[float, float, float]:
        point = np.asarray(target_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(point)):
            raise ValueError("Target point must be finite.")
        return (float(point[0]), float(point[1]), float(point[2]) - float(z_station))

    def _optical_solid_face_reference_point(
        self,
        row_index: int,
        metadata: dict[str, object],
        *,
        face_id: str = "",
    ) -> np.ndarray:
        z_positions = self._row_z_positions()
        z_station = float(z_positions[row_index]) if 0 <= row_index < len(z_positions) else 0.0
        row = SurfaceRow(**asdict(self.rows[row_index]))
        row.advanced = dict(row.advanced or {})
        row.advanced[OPTICAL_SOLID_FACES_ADVANCED_ATTR] = metadata
        selected_id = str(face_id or "").strip()
        for face in optical_solid_face_world_records(row, z_station, assigned_only=False):
            if selected_id and str(face.get("face_id", "") or "").strip() != selected_id:
                continue
            anchor = np.asarray(
                face.get("anchor_world", face.get("centroid_world", (np.nan, np.nan, np.nan))),
                dtype=float,
            ).reshape(-1)[:3]
            if anchor.size == 3 and np.all(np.isfinite(anchor)):
                return anchor
        return np.asarray((float(row.desp_x), float(row.desp_y), z_station + float(row.desp_z)), dtype=float)

    def _nearest_traced_ray_frame_near_point(self, reference_point, *, branch_path: str = "") -> dict[str, object]:
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(reference)):
            raise RuntimeError("Reference point is not finite.")
        target_branch = str(branch_path or "").strip()
        bundle = getattr(self, "_last_scene_bundle", None)
        candidates: list[dict[str, object]] = []
        for path in getattr(bundle, "ray_paths", []) or []:
            path_branch = str(getattr(path, "branch_path", "") or "").strip()
            if target_branch and path_branch != target_branch:
                continue
            points = np.asarray(getattr(path, "points_world", []), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                continue
            try:
                target_point, direction = self._closest_polyline_point_and_direction(points[:, :3], reference)
                distance = float(np.linalg.norm(np.asarray(target_point, dtype=float)[:3] - reference))
            except Exception:
                continue
            if not np.isfinite(distance):
                continue
            candidates.append(
                {
                    "distance": distance,
                    "target_point": np.asarray(target_point, dtype=float).reshape(3),
                    "direction": np.asarray(direction, dtype=float).reshape(3),
                    "branch_path": path_branch,
                    "source_id": str(getattr(path, "source_id", "") or "").strip(),
                    "ray_index": int(getattr(path, "ray_index", -1)),
                }
            )
        if not candidates:
            detail = f" for path {target_branch}" if target_branch else ""
            raise RuntimeError(f"No traced 3D ray path is available{detail}. Click Update first.")
        closest = min(candidates, key=lambda item: float(item["distance"]))
        closest_branch = str(closest.get("branch_path", "") or "")
        branch_candidates = [item for item in candidates if str(item.get("branch_path", "") or "") == closest_branch]
        branch_candidates.sort(key=lambda item: float(item["distance"]))
        sample_limit = min(len(branch_candidates), 25)
        samples = branch_candidates[:sample_limit]
        points = np.vstack([np.asarray(item["target_point"], dtype=float).reshape(3) for item in samples])
        directions = np.vstack([np.asarray(item["direction"], dtype=float).reshape(3) for item in samples])
        target_point = np.nanmedian(points, axis=0)
        direction = np.nanmean(directions, axis=0)
        try:
            direction = self._normalized_vector(direction)
        except Exception:
            direction = self._normalized_vector(closest["direction"])
        return {
            "origin": np.asarray(target_point, dtype=float),
            "direction": np.asarray(direction, dtype=float),
            "target_point": np.asarray(target_point, dtype=float),
            "branch_path": closest_branch,
            "sample_count": int(len(samples)),
            "distance_mm": float(closest["distance"]),
            "ray_index": int(closest.get("ray_index", -1)),
            "source_id": str(closest.get("source_id", "") or ""),
        }

    def _traced_frame_after_table_surface(self, row_index: int, reference_point) -> dict[str, object]:
        reference = np.asarray(reference_point, dtype=float).reshape(3)
        if not np.all(np.isfinite(reference)):
            raise RuntimeError("Reference point is not finite.")
        bundle = getattr(self, "_last_scene_bundle", None)
        for surface_index in range(int(row_index) - 1, 0, -1):
            candidates: list[dict[str, object]] = []
            for path in getattr(bundle, "ray_paths", []) or []:
                surface_ids = np.asarray(getattr(path, "surface_ids", []), dtype=int).ravel()
                points = np.asarray(getattr(path, "points_world", []), dtype=float)
                if surface_ids.size == 0 or points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
                    continue
                hit_positions = np.flatnonzero(surface_ids == int(surface_index))
                if hit_positions.size == 0:
                    continue
                hit_index = int(hit_positions[-1])
                point_index = min(hit_index + 1, points.shape[0] - 1)
                if point_index + 1 < points.shape[0]:
                    origin = np.asarray(points[point_index], dtype=float)
                    direction = np.asarray(points[point_index + 1], dtype=float) - origin
                elif point_index > 0:
                    origin = np.asarray(points[point_index], dtype=float)
                    direction = origin - np.asarray(points[point_index - 1], dtype=float)
                else:
                    continue
                norm = float(np.linalg.norm(direction))
                if not np.isfinite(norm) or norm <= 1e-9:
                    continue
                line_frame = self._line_frame_near_point(origin, direction, reference)
                distance = float(np.linalg.norm(np.asarray(line_frame["target_point"], dtype=float) - reference))
                if not np.isfinite(distance):
                    continue
                candidates.append(
                    {
                        "distance": distance,
                        "target_point": np.asarray(line_frame["target_point"], dtype=float).reshape(3),
                        "direction": np.asarray(line_frame["direction"], dtype=float).reshape(3),
                        "branch_path": str(getattr(path, "branch_path", "") or "").strip(),
                        "source_id": str(getattr(path, "source_id", "") or "").strip(),
                        "ray_index": int(getattr(path, "ray_index", -1)),
                    }
                )
            if not candidates:
                continue
            candidates.sort(key=lambda item: float(item["distance"]))
            sample_limit = min(len(candidates), 25)
            samples = candidates[:sample_limit]
            points = np.vstack([np.asarray(item["target_point"], dtype=float).reshape(3) for item in samples])
            directions = np.vstack([np.asarray(item["direction"], dtype=float).reshape(3) for item in samples])
            target_point = np.nanmedian(points, axis=0)
            direction = np.nanmean(directions, axis=0)
            try:
                direction = self._normalized_vector(direction)
            except Exception:
                direction = self._normalized_vector(samples[0]["direction"])
            return {
                "origin": np.asarray(target_point, dtype=float),
                "direction": np.asarray(direction, dtype=float),
                "target_point": np.asarray(target_point, dtype=float),
                "branch_path": str(samples[0].get("branch_path", "") or ""),
                "sample_count": int(len(samples)),
                "distance_mm": float(samples[0]["distance"]),
                "ray_index": int(samples[0].get("ray_index", -1)),
                "source_id": str(samples[0].get("source_id", "") or ""),
                "source_surface_index": int(surface_index),
            }
        raise RuntimeError("No traced outgoing segment is available before this row. Click Update first.")

    def _solve_optical_solid_path_input_pose(self, row_index: int, metadata: dict[str, object]) -> dict[str, object] | None:
        if not (0 <= row_index < len(self.rows)):
            return None
        normalized = normalize_optical_solid_face_metadata(metadata)
        input_face = optical_solid_metadata.optical_solid_input_anchor_face(normalized)
        if input_face is None:
            return None
        face_id = str(input_face.get("face_id", "") or "").strip()
        z_positions = self._row_z_positions()
        z_station = float(z_positions[row_index]) if 0 <= row_index < len(z_positions) else 0.0
        reference = self._optical_solid_face_reference_point(row_index, normalized, face_id=face_id)
        frame_source = "nearest traced ray"
        branch_path = self._current_path_view_branch_path()
        if branch_path:
            try:
                frame = self._current_path_view_frame_near_point(reference)
                frame_source = "current Path view"
            except Exception:
                frame = self._traced_frame_after_table_surface(row_index, reference)
                frame_source = "previous table surface"
        else:
            try:
                frame = self._traced_frame_after_table_surface(row_index, reference)
                frame_source = "previous table surface"
            except Exception:
                frame = self._nearest_traced_ray_frame_near_point(reference)
        direction = self._normalized_vector(frame["direction"])
        target_world = np.asarray(frame["target_point"], dtype=float).reshape(3)
        solution = solve_optical_solid_face_fit(
            normalized,
            face_id=face_id,
            target_normal=tuple(float(value) for value in -direction),
            target_point=self._row_local_point_from_world(target_world, z_station),
            roll_mode=OPTICAL_SOLID_FACE_FIT_ROLL_DEFAULT,
        )
        if solution is not None:
            solution["fit_source"] = frame_source
            solution["target_world_point"] = tuple(float(value) for value in target_world)
            solution["path_direction"] = tuple(float(value) for value in direction)
            solution["branch_path"] = str(frame.get("branch_path", "") or "")
            solution["sample_count"] = int(frame.get("sample_count", 0))
            solution["distance_mm"] = float(frame.get("distance_mm", 0.0) or 0.0)
        return solution

    def _selected_ray_index_from_ui(self) -> int | None:
        table = self._ray_inspector_ray_table
        if table is not None:
            selected = table.selection()
            if selected:
                try:
                    return int(selected[0])
                except Exception:
                    pass
        inspector = getattr(self, "_three_d_inspector", None)
        picked = getattr(inspector, "_picked_ray_index", None) if inspector is not None else None
        if picked is not None:
            try:
                return int(picked)
            except Exception:
                pass
        plotter = getattr(self, "_legacy_3d_plotter", None)
        if plotter is not None:
            try:
                picked = getattr(plotter, "_kraken_selected_ray", None)
                if picked is not None:
                    return int(picked)
            except Exception:
                pass
        return None

    def _ray_path_by_index(self, ray_index: int):
        bundle = getattr(self, "_last_scene_bundle", None)
        for path in getattr(bundle, "ray_paths", []) or []:
            try:
                if int(getattr(path, "ray_index", -1)) == int(ray_index):
                    return path
            except Exception:
                continue
        return None

    def _ray_terminal_hint_text(self, ray_index: int, *, label: str | None = None) -> str:
        try:
            index = int(ray_index)
        except Exception:
            return ""
        text = str(label or f"Ray {index}")
        path = self._ray_path_by_index(index)
        if path is None:
            return text
        detail = ray_path_terminal_diagnostic_text(path)
        return f"{text}: {detail}" if detail else text

    def _ray_frame_near_point(self, ray_index: int, reference_point) -> dict[str, object]:
        ray_index = int(ray_index)
        path = self._ray_path_by_index(ray_index)
        if path is None:
            raise RuntimeError(f"Ray {ray_index} is not available in the current preview.")
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            raise RuntimeError("Selected ray does not contain a valid 3D polyline.")
        target_point, direction = self._closest_polyline_point_and_direction(points[:, :3], np.asarray(reference_point, dtype=float))
        return {
            "ray_index": int(ray_index),
            "origin": np.asarray(target_point, dtype=float),
            "direction": np.asarray(direction, dtype=float),
            "target_point": np.asarray(target_point, dtype=float),
            "branch_path": str(getattr(path, "branch_path", "") or ""),
            "source_id": str(getattr(path, "source_id", "") or ""),
        }

    def _selected_ray_frame_near_point(self, reference_point) -> dict[str, object]:
        ray_index = self._selected_ray_index_from_ui()
        if ray_index is None:
            raise RuntimeError("Select a traced ray first in the 2D plot, 3D view, or Ray Inspector.")
        return self._ray_frame_near_point(ray_index, reference_point)

    def _current_path_view_branch_path(self) -> str:
        focus_label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        if not focus_label or focus_label == ARM_VIEW_DEFAULT:
            return ""
        key = self._arm_key_for_view_label(focus_label)
        return self._branch_path_for_arm_key(key)

    def _current_path_view_frame_near_point(self, reference_point) -> dict[str, object]:
        branch_path = self._current_path_view_branch_path()
        if not branch_path:
            raise RuntimeError("Choose a traced Path view first.")
        frame = self._branch_path_frame(branch_path)
        line_frame = self._line_frame_near_point(frame["origin"], frame["direction"], reference_point)
        line_frame["branch_path"] = branch_path
        line_frame["sample_count"] = int(frame.get("sample_count", 0))
        line_frame["origin_surface"] = int(frame.get("origin_surface", -1))
        return line_frame

    @staticmethod
    def _normalize_path_component_type(component_type: object) -> str:
        text = str(component_type or "").strip()
        lookup = {re.sub(r"[^a-z0-9]", "", value.lower()): value for value in PATH_COMPONENT_TYPES}
        return lookup.get(re.sub(r"[^a-z0-9]", "", text.lower()), PATH_COMPONENT_DETECTOR)

    def _next_path_component_element_label(self, arm_role: str, component_type: object) -> str:
        kind = self._normalize_path_component_type(component_type)
        suffix = PATH_COMPONENT_LABEL_SUFFIXES.get(kind, "component")
        base = f"{arm_role} {suffix}"
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        if base not in used:
            return base
        counter = 2
        while f"{base} {counter}" in used:
            counter += 1
        return f"{base} {counter}"

    def _next_branch_path_component_element_label(self, branch_path: str, component_type: object) -> str:
        selectors = "".join(self._branch_path_selector_sequence(branch_path)) or "Path"
        return self._next_path_component_element_label(f"Path {selectors}", component_type)

    def _next_detector_element_label(self, arm_role: str) -> str:
        return self._next_path_component_element_label(arm_role, PATH_COMPONENT_DETECTOR)

    def _path_component_row_for_arm(
        self,
        splitter_index: int,
        arm_role: str,
        component_type: object,
        distance_mm: float,
        diameter_mm: float,
        *,
        parameter_mm: float | None = None,
        glass: str = "AIR",
        insert_at: int | None = None,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> SurfaceRow:
        distance = float(distance_mm)
        diameter = float(diameter_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path component distance must be positive.")
        if not np.isfinite(diameter) or diameter <= 0.0:
            raise RuntimeError("Path component diameter must be positive.")
        role = str(arm_role).strip()
        if role not in {"Transmit", "Reflect"}:
            raise RuntimeError("Path placement supports Transmit or Reflect paths.")
        kind = self._normalize_path_component_type(component_type)
        insert_index = len(self.rows) - 1 if insert_at is None else int(insert_at)
        insert_index = max(1, min(insert_index, len(self.rows) - 1))
        frame = self._arm_frame_for_splitter(splitter_index, role)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = np.asarray(frame["direction"], dtype=float)
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        center = origin + direction * distance + local_offset
        splitter_row = self.rows[splitter_index]
        splitter_metadata = self._element_metadata(splitter_row)
        parent = (
            str(splitter_metadata.get("element_id", "") or "").strip()
            or self._element_key(splitter_row)
            or str(splitter_row.name or f"S{splitter_index}").strip()
        )

        rc = 0.0
        surface = "Standard"
        row_glass = "AIR"
        axis_move = 0.0
        if kind == PATH_COMPONENT_APERTURE:
            surface = "Aperture"
        elif kind == PATH_COMPONENT_THIN_LENS:
            try:
                focal = float(parameter_mm)
            except Exception:
                focal = float("nan")
            if not np.isfinite(focal) or abs(focal) <= 1e-12:
                raise RuntimeError("Thin lens focal length must be a non-zero number.")
            surface = "Thin Lens"
            rc = focal
        elif kind == PATH_COMPONENT_REFRACTIVE_SURFACE:
            try:
                radius = float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError("Refractive surface radius must be a finite number.")
            surface = "Standard"
            rc = radius
            row_glass = str(glass or "BK7").strip() or "BK7"
        elif kind in {PATH_COMPONENT_MIRROR, PATH_COMPONENT_OBJECT_TARGET}:
            try:
                radius = 0.0 if parameter_mm is None else float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError(f"{kind} radius must be a finite number.")
            surface = OBJECT_TARGET_SURFACE if kind == PATH_COMPONENT_OBJECT_TARGET else "Mirror"
            rc = radius
            row_glass = "MIRROR"
            axis_move = 2.0

        element_label = self._next_path_component_element_label(role, kind)
        metadata_role = "Detector" if kind == PATH_COMPONENT_DETECTOR else role
        component = SurfaceRow(
            element=element_label,
            surface=surface,
            name=element_label,
            rc=rc,
            k=0.0,
            thickness=0.0,
            diameter=diameter,
            glass=row_glass,
            tilt_x=float(tilt_x),
            tilt_y=float(tilt_y),
            tilt_z=float(tilt_z),
            axis_move=axis_move,
            advanced={
                ELEMENT_ADVANCED_ATTR: {
                    "element_id": self._element_id_from_label(element_label),
                    "element_name": element_label,
                    "arm_role": metadata_role,
                    "parent_splitter": parent,
                    "branch_selector": self._branch_selector_for_arm_role(role),
                    "arm_distance": distance,
                    "local_decenter_x": float(local_decenter_x),
                    "local_decenter_y": float(local_decenter_y),
                    "local_tilt_x": float(local_tilt_x),
                    "local_tilt_y": float(local_tilt_y),
                    "local_tilt_z": float(local_tilt_z),
                    "path_component_type": kind,
                },
                **(
                    {DETECTOR_ADVANCED_ATTR: _normalize_detector_settings({"active_width_mm": diameter, "active_height_mm": diameter})}
                    if kind == PATH_COMPONENT_DETECTOR
                    else {}
                ),
                **(
                    {
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Object Target traces as a specular reflective proxy. "
                            "Use a Diffuse Object row for Lambertian, Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF scattering."
                        ),
                    }
                    if kind == PATH_COMPONENT_OBJECT_TARGET
                    else {}
                ),
            },
        )
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        temp_rows.insert(insert_index, SurfaceRow(**asdict(component)))
        baseline = self._surface_transform_for_rows(temp_rows, insert_index)[:3, 3]
        decenter = center - np.asarray(baseline, dtype=float)
        component.desp_x = float(decenter[0])
        component.desp_y = float(decenter[1])
        component.desp_z = float(decenter[2])
        return component

    def _path_component_row_for_branch_path(
        self,
        branch_path: str,
        component_type: object,
        distance_mm: float,
        diameter_mm: float,
        *,
        parameter_mm: float | None = None,
        glass: str = "AIR",
        insert_at: int | None = None,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> SurfaceRow:
        distance = float(distance_mm)
        diameter = float(diameter_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path component distance must be positive.")
        if not np.isfinite(diameter) or diameter <= 0.0:
            raise RuntimeError("Path component diameter must be positive.")
        path = str(branch_path or "").strip()
        frame = self._branch_path_frame(path)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = np.asarray(frame["direction"], dtype=float)
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        center = origin + direction * distance + local_offset
        kind = self._normalize_path_component_type(component_type)
        insert_index = len(self.rows) - 1 if insert_at is None else int(insert_at)
        insert_index = max(1, min(insert_index, len(self.rows) - 1))
        selector = self._branch_path_leaf_selector(path)
        role = {
            "transmit": "Transmit",
            "reflect": "Reflect",
            "return": "Return",
        }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)

        rc = 0.0
        surface = "Standard"
        row_glass = "AIR"
        axis_move = 0.0
        if kind == PATH_COMPONENT_APERTURE:
            surface = "Aperture"
        elif kind == PATH_COMPONENT_THIN_LENS:
            try:
                focal = float(parameter_mm)
            except Exception:
                focal = float("nan")
            if not np.isfinite(focal) or abs(focal) <= 1e-12:
                raise RuntimeError("Thin lens focal length must be a non-zero number.")
            surface = "Thin Lens"
            rc = focal
        elif kind == PATH_COMPONENT_REFRACTIVE_SURFACE:
            try:
                radius = float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError("Refractive surface radius must be a finite number.")
            surface = "Standard"
            rc = radius
            row_glass = str(glass or "BK7").strip() or "BK7"
        elif kind in {PATH_COMPONENT_MIRROR, PATH_COMPONENT_OBJECT_TARGET}:
            try:
                radius = 0.0 if parameter_mm is None else float(parameter_mm)
            except Exception:
                radius = float("nan")
            if not np.isfinite(radius):
                raise RuntimeError(f"{kind} radius must be a finite number.")
            surface = OBJECT_TARGET_SURFACE if kind == PATH_COMPONENT_OBJECT_TARGET else "Mirror"
            rc = radius
            row_glass = "MIRROR"
            axis_move = 2.0

        element_label = self._next_branch_path_component_element_label(path, kind)
        metadata_role = "Detector" if kind == PATH_COMPONENT_DETECTOR else role
        component = SurfaceRow(
            element=element_label,
            surface=surface,
            name=element_label,
            rc=rc,
            k=0.0,
            thickness=0.0,
            diameter=diameter,
            glass=row_glass,
            tilt_x=float(tilt_x),
            tilt_y=float(tilt_y),
            tilt_z=float(tilt_z),
            axis_move=axis_move,
            advanced={
                ELEMENT_ADVANCED_ATTR: {
                    "element_id": self._element_id_from_label(element_label),
                    "element_name": element_label,
                    "arm_role": metadata_role,
                    "parent_splitter": self._branch_path_detail(path),
                    "branch_selector": selector,
                    "branch_path": path,
                    "arm_distance": distance,
                    "local_decenter_x": float(local_decenter_x),
                    "local_decenter_y": float(local_decenter_y),
                    "local_tilt_x": float(local_tilt_x),
                    "local_tilt_y": float(local_tilt_y),
                    "local_tilt_z": float(local_tilt_z),
                    "path_component_type": kind,
                    "path_frame_source": "traced_branch_path",
                    "path_frame_surface": int(frame.get("origin_surface", -1)),
                    "path_frame_samples": int(frame.get("sample_count", 0)),
                },
                **(
                    {DETECTOR_ADVANCED_ATTR: _normalize_detector_settings({"active_width_mm": diameter, "active_height_mm": diameter})}
                    if kind == PATH_COMPONENT_DETECTOR
                    else {}
                ),
                **(
                    {
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Object Target traces as a specular reflective proxy. "
                            "Use a Diffuse Object row for Lambertian, Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF scattering."
                        ),
                    }
                    if kind == PATH_COMPONENT_OBJECT_TARGET
                    else {}
                ),
            },
        )
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        temp_rows.insert(insert_index, SurfaceRow(**asdict(component)))
        baseline = self._surface_transform_for_rows(temp_rows, insert_index)[:3, 3]
        decenter = center - np.asarray(baseline, dtype=float)
        component.desp_x = float(decenter[0])
        component.desp_y = float(decenter[1])
        component.desp_z = float(decenter[2])
        return component

    @staticmethod
    def _block_axial_offsets(rows: list[SurfaceRow]) -> list[float]:
        offsets: list[float] = []
        axial = 0.0
        for row in rows:
            offsets.append(float(axial))
            try:
                thickness = float(row.thickness)
            except Exception:
                thickness = 0.0
            axial += thickness if np.isfinite(thickness) else 0.0
        return offsets

    def _path_stock_lens_context(
        self,
        *,
        splitter_index: int = -1,
        arm_role: str = "",
        branch_path: str = "",
    ) -> dict[str, object]:
        path = str(branch_path or "").strip()
        if path:
            frame = self._branch_path_frame(path)
            selector = self._branch_path_leaf_selector(path)
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            return {
                **frame,
                "arm_role": role,
                "metadata_role": role,
                "branch_selector": selector,
                "branch_path": path,
                "parent_splitter": self._branch_path_detail(path),
                "path_frame_source": "traced_branch_path",
                "path_frame_surface": int(frame.get("origin_surface", -1)),
                "path_frame_samples": int(frame.get("sample_count", 0)),
                "insert_index": self._default_insert_index_for_arm_key(self._arm_key_from_branch_path(path)),
                "placement_label": f"traced path {self._branch_path_compact_detail(path)}",
            }
        role = str(arm_role or "").strip()
        if role not in {"Transmit", "Reflect"}:
            raise RuntimeError("Stock-lens path placement supports Transmit, Reflect, or a traced Path view.")
        frame = self._arm_frame_for_splitter(int(splitter_index), role)
        splitter_row = self.rows[int(splitter_index)]
        splitter_metadata = self._element_metadata(splitter_row)
        parent = (
            str(splitter_metadata.get("element_id", "") or "").strip()
            or self._element_key(splitter_row)
            or str(splitter_row.name or f"S{int(splitter_index)}").strip()
        )
        return {
            **frame,
            "arm_role": role,
            "metadata_role": role,
            "branch_selector": self._branch_selector_for_arm_role(role),
            "branch_path": "",
            "parent_splitter": parent,
            "path_frame_source": "splitter_row",
            "path_frame_surface": int(splitter_index),
            "path_frame_samples": 0,
            "insert_index": max(1, len(self.rows) - 1),
            "placement_label": f"{role.lower()} path",
        }

    def _stock_lens_rows_for_path_context(
        self,
        rows: list[SurfaceRow],
        *,
        part_number: str,
        context: dict[str, object],
        distance_mm: float,
        local_decenter_x: float = 0.0,
        local_decenter_y: float = 0.0,
        local_tilt_x: float = 0.0,
        local_tilt_y: float = 0.0,
        local_tilt_z: float = 0.0,
    ) -> list[SurfaceRow]:
        if not rows:
            raise RuntimeError("Stock lens has no rows to place.")
        distance = float(distance_mm)
        if not np.isfinite(distance) or distance <= 0.0:
            raise RuntimeError("Path distance must be positive.")
        insert_index = max(1, min(int(context.get("insert_index", len(self.rows) - 1)), len(self.rows) - 1))
        origin = np.asarray(context["origin"], dtype=float)
        direction = self._normalized_vector(context["direction"])
        local_offset, tilts = self._path_local_pose(
            context,
            local_decenter_x=local_decenter_x,
            local_decenter_y=local_decenter_y,
            local_tilt_x=local_tilt_x,
            local_tilt_y=local_tilt_y,
            local_tilt_z=local_tilt_z,
        )
        tilt_x, tilt_y, tilt_z = tilts
        role = str(context.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)
        selector = str(context.get("branch_selector", "") or "").strip()
        branch_path = str(context.get("branch_path", "") or "").strip()
        parent = str(context.get("parent_splitter", "") or "").strip()
        path_source = str(context.get("path_frame_source", "") or "").strip()
        base_label = f"{role} {part_number}".strip() if role else str(part_number).strip()
        if branch_path:
            selectors = "".join(self._branch_path_selector_sequence(branch_path)) or "Path"
            base_label = f"Path {selectors} {part_number}".strip()
        used = {self._element_key(row) for row in self.rows if self._element_key(row)}
        element_label = self._unique_element_label(base_label or "Path stock lens", used)
        offsets = self._block_axial_offsets(rows)
        additions = [SurfaceRow(**asdict(row)) for row in rows]
        row_count = len(additions)
        for offset, row in zip(offsets, additions):
            row.element = element_label
            row.tilt_x = float(tilt_x)
            row.tilt_y = float(tilt_y)
            row.tilt_z = float(tilt_z)
            row.desp_x = float(getattr(row, "desp_x", 0.0) or 0.0)
            row.desp_y = float(getattr(row, "desp_y", 0.0) or 0.0)
            row.desp_z = float(getattr(row, "desp_z", 0.0) or 0.0)
            metadata = {
                "element_id": self._element_id_from_label(element_label),
                "element_name": element_label,
                "arm_role": role,
                "parent_splitter": parent,
                "branch_selector": selector,
                "branch_path": branch_path,
                "arm_distance": distance,
                "local_decenter_x": float(local_decenter_x),
                "local_decenter_y": float(local_decenter_y),
                "local_tilt_x": float(local_tilt_x),
                "local_tilt_y": float(local_tilt_y),
                "local_tilt_z": float(local_tilt_z),
                "path_component_type": PATH_COMPONENT_STOCK_LENS,
                "path_component_part": str(part_number).strip(),
                "path_component_row_count": row_count,
                "path_component_axial_offset": float(offset),
                "path_frame_source": path_source,
                "path_frame_surface": int(context.get("path_frame_surface", -1)),
                "path_frame_samples": int(context.get("path_frame_samples", 0)),
            }
            row.advanced = dict(row.advanced or {})
            row.advanced[ELEMENT_ADVANCED_ATTR] = metadata

        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for offset, row in enumerate(additions):
            temp_rows.insert(insert_index + offset, SurfaceRow(**asdict(row)))
        for offset, row in enumerate(additions):
            row_index = insert_index + offset
            baseline = self._surface_transform_for_rows(temp_rows, row_index)[:3, 3]
            target = origin + direction * (distance + offsets[offset]) + local_offset
            decenter = np.asarray(target, dtype=float) - np.asarray(baseline, dtype=float)
            row.desp_x = float(row.desp_x) + float(decenter[0])
            row.desp_y = float(row.desp_y) + float(decenter[1])
            row.desp_z = float(row.desp_z) + float(decenter[2])
            temp_rows[row_index] = SurfaceRow(**asdict(row))
        return additions

    @staticmethod
    def _normalized_metadata_key(value: object) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value or "").strip().lower())

    def _splitter_index_for_path_parent(self, parent: object) -> int | None:
        parent_key = self._normalized_metadata_key(parent)
        candidates: list[tuple[int, set[str]]] = []
        for index, row in enumerate(self.rows):
            if row.surface != BEAM_SPLITTER_SURFACE:
                continue
            metadata = self._element_metadata(row)
            labels = {
                f"S{index}",
                str(row.name or ""),
                self._element_key(row),
                str(metadata.get("element_id", "") or ""),
                str(metadata.get("element_name", "") or ""),
            }
            candidates.append((index, {self._normalized_metadata_key(label) for label in labels if str(label or "").strip()}))
        if parent_key:
            for index, keys in candidates:
                if parent_key in keys:
                    return index
        if not parent_key and len(candidates) == 1:
            return candidates[0][0]
        return None

    def _path_frame_for_element_metadata(self, metadata: dict[str, object]) -> dict[str, object]:
        data = _normalize_element_metadata(metadata)
        branch_path = str(data.get("branch_path", "") or "").strip()
        if branch_path:
            return dict(self._branch_path_frame(branch_path))
        selector = str(data.get("branch_selector", "") or "").strip().lower()
        if not selector:
            selector = self._branch_selector_for_arm_role(str(data.get("arm_role", "") or ""))
        role = {"transmit": "Transmit", "reflect": "Reflect"}.get(selector)
        if role is None:
            raise RuntimeError("This element is not tied to a transmitted/reflected path frame.")
        splitter_index = self._splitter_index_for_path_parent(data.get("parent_splitter", ""))
        if splitter_index is None:
            raise RuntimeError("Could not find the parent Beam Splitter row for this path element.")
        return dict(self._arm_frame_for_splitter(splitter_index, role))

    def _metadata_has_path_pose(self, metadata: dict[str, object]) -> bool:
        data = _normalize_element_metadata(metadata)
        component_type = str(data.get("path_component_type", "") or "").strip()
        frame_source = str(data.get("path_frame_source", "") or "").strip()
        return bool(component_type or frame_source)

    def _apply_path_local_pose_to_indices(
        self,
        indices: list[int],
        metadata: dict[str, object],
    ) -> list[int]:
        selected = sorted(int(index) for index in indices if 0 < int(index) < len(self.rows) - 1)
        if not selected:
            raise RuntimeError("Select one placed path element first.")
        data = _normalize_element_metadata(metadata)
        if not self._metadata_has_path_pose(data):
            raise RuntimeError("Selected element does not contain path-placement metadata.")
        distance = float(data.get("arm_distance", 0.0))
        if not np.isfinite(distance):
            raise RuntimeError("Path distance must be finite.")
        frame = self._path_frame_for_element_metadata(data)
        origin = np.asarray(frame["origin"], dtype=float)
        direction = self._normalized_vector(frame["direction"])
        local_dx = float(data.get("local_decenter_x", 0.0))
        local_dy = float(data.get("local_decenter_y", 0.0))
        local_tx = float(data.get("local_tilt_x", 0.0))
        local_ty = float(data.get("local_tilt_y", 0.0))
        local_tz = float(data.get("local_tilt_z", 0.0))
        local_offset, tilts = self._path_local_pose(
            frame,
            local_decenter_x=local_dx,
            local_decenter_y=local_dy,
            local_tilt_x=local_tx,
            local_tilt_y=local_ty,
            local_tilt_z=local_tz,
        )
        tilt_x, tilt_y, tilt_z = tilts
        fallback_offsets = dict(zip(selected, self._block_axial_offsets([self.rows[index] for index in selected])))
        temp_rows = [SurfaceRow(**asdict(row)) for row in self.rows]
        for index in selected:
            temp_rows[index].tilt_x = float(tilt_x)
            temp_rows[index].tilt_y = float(tilt_y)
            temp_rows[index].tilt_z = float(tilt_z)
            temp_rows[index].desp_x = 0.0
            temp_rows[index].desp_y = 0.0
            temp_rows[index].desp_z = 0.0

        label = str(data.get("element_name", "") or self._element_key(self.rows[selected[0]])).strip()
        for index in selected:
            row = self.rows[index]
            row_metadata = self._element_metadata(row)
            row_data = dict(row_metadata)
            row_data.update(data)
            for key in (
                "path_component_axial_offset",
                "path_component_row_count",
                "path_component_part",
                "path_frame_source",
                "path_frame_surface",
                "path_frame_samples",
            ):
                if key in row_metadata:
                    row_data[key] = row_metadata[key]
            axial_offset = float(row_data.get("path_component_axial_offset", fallback_offsets.get(index, 0.0)) or 0.0)
            row.tilt_x = float(tilt_x)
            row.tilt_y = float(tilt_y)
            row.tilt_z = float(tilt_z)
            baseline = self._surface_transform_for_rows(temp_rows, index)[:3, 3]
            target = origin + direction * (distance + axial_offset) + local_offset
            decenter = np.asarray(target, dtype=float) - np.asarray(baseline, dtype=float)
            row.desp_x = float(decenter[0])
            row.desp_y = float(decenter[1])
            row.desp_z = float(decenter[2])
            if label:
                row.element = label
                row_data["element_name"] = label
                row_data["element_id"] = str(row_data.get("element_id", "") or self._element_id_from_label(label))
            row_data["local_decenter_x"] = local_dx
            row_data["local_decenter_y"] = local_dy
            row_data["local_tilt_x"] = local_tx
            row_data["local_tilt_y"] = local_ty
            row_data["local_tilt_z"] = local_tz
            self._set_element_metadata(row, row_data)
            temp_rows[index] = SurfaceRow(**asdict(row))
        return selected

    def _detector_row_for_arm(
        self,
        splitter_index: int,
        arm_role: str,
        distance_mm: float,
        diameter_mm: float,
        *,
        insert_at: int | None = None,
    ) -> SurfaceRow:
        return self._path_component_row_for_arm(
            splitter_index,
            arm_role,
            PATH_COMPONENT_DETECTOR,
            distance_mm,
            diameter_mm,
            insert_at=insert_at,
        )

    def open_arm_detector_placement(self, splitter_index: int, arm_role: str) -> None:
        self.open_arm_path_component_placement(splitter_index, arm_role, default_component=PATH_COMPONENT_DETECTOR)

    def _main_path_component_placement_dialog(self) -> MainPathComponentPlacementDialog:
        dialog = self.__dict__.get("_main_path_component_placement_dialog_instance")
        if dialog is None:
            dialog = MainPathComponentPlacementDialog(self, short_error_message=_short_error_message)
            self._main_path_component_placement_dialog_instance = dialog
        return dialog

    def open_arm_path_component_placement(
        self,
        splitter_index: int,
        arm_role: str,
        *,
        default_component: object = PATH_COMPONENT_DETECTOR,
        branch_path: str = "",
    ) -> None:
        self._main_path_component_placement_dialog().open_arm_path_component_placement(
            splitter_index,
            arm_role,
            default_component=default_component,
            branch_path=branch_path,
        )

    def open_current_path_component_placement(self) -> None:
        self._main_path_component_placement_dialog().open_current_path_component_placement()

    def open_arm_stock_lens_placement(self, splitter_index: int, arm_role: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Stock Lens", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        if not (0 <= int(splitter_index) < len(self.rows)) or self.rows[int(splitter_index)].surface != BEAM_SPLITTER_SURFACE:
            messagebox.showinfo("Path Stock Lens", "Right-click a Beam Splitter row first.", parent=self)
            return
        role = str(arm_role or "").strip()
        if role not in {"Transmit", "Reflect"}:
            messagebox.showerror("Path Stock Lens", f"Unsupported path: {arm_role}", parent=self)
            return
        self.open_stock_lens_importer(path_placement={"splitter_index": int(splitter_index), "arm_role": role})

    def open_current_path_stock_lens_placement(self) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Path Stock Lens", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._refresh_arm_view_choices()
        label = str(self.arm_view_var.get() or ARM_VIEW_DEFAULT).strip()
        arm_key = self._arm_key_for_view_label(label)
        branch_path = self._branch_path_for_arm_key(arm_key)
        if not branch_path:
            messagebox.showinfo(
                "Path Stock Lens",
                "Choose a traced Path view first, then run Insert/Actions -> Stock Lens to Current Path View.",
                parent=self,
            )
            return
        self.open_stock_lens_importer(path_placement={"branch_path": branch_path})

    def assign_selected_elements_to_arm(self, role: str) -> None:
        role = _normalize_element_metadata({"arm_role": role})["arm_role"]
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Assign Path", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        blocks = self._selected_element_blocks()
        if not blocks:
            messagebox.showinfo("Assign Path", "Select one or more non-Object/non-Image rows or element groups first.", parent=self)
            return

        self._begin_history_capture()
        selected_indices: list[int] = []
        for indices in blocks:
            if role == ELEMENT_ARM_ROLE_DEFAULT:
                for index in indices:
                    self._set_element_metadata(self.rows[index], {})
                selected_indices.extend(indices)
                continue
            label = self._ensure_element_for_block(indices)
            metadata = self._element_metadata(self.rows[indices[0]])
            metadata["element_name"] = label
            if not str(metadata.get("element_id", "") or "").strip():
                metadata["element_id"] = self._element_id_from_label(label)
            previous_role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT))
            previous_selector = str(metadata.get("branch_selector", "") or "").strip()
            metadata["arm_role"] = role
            if previous_selector in {"", self._branch_selector_for_arm_role(previous_role)}:
                metadata["branch_selector"] = self._branch_selector_for_arm_role(role)
            metadata["leg_id"] = ""
            for index in indices:
                self._set_element_metadata(self.rows[index], metadata)
            selected_indices.extend(indices)
        self._normalize_special_rows()
        self._sync_table()
        if selected_indices:
            self._select_table_indices(selected_indices, focus_index=selected_indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        role_text = role if role != ELEMENT_ARM_ROLE_DEFAULT else "Unassigned"
        self.status_var.set(f"Assigned {len(blocks)} element(s) to {role_text} path metadata.")
        self._cleanup_current_popup_menu()

    def _element_metadata_for_arm_key(self, arm_key: str, label: str) -> dict[str, object] | None:
        parts = str(arm_key or "").split("|")
        leg_id = self._leg_id_from_arm_key(arm_key)
        selector = self._branch_selector_for_arm_key(arm_key)
        branch_path = self._branch_path_for_arm_key(arm_key)
        if branch_path:
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            parent = self._branch_path_detail(branch_path)
        elif leg_id:
            workflow = self._physical_leg_workflow()
            if workflow == "mach_zehnder":
                bs1_parent = self._splitter_id_by_ordinal(0)
                bs2_parent = self._splitter_id_by_ordinal(1)
                role, selector, parent = {
                    "input": ("Common", "primary", bs1_parent),
                    "transmit": ("Return", "transmit", bs1_parent),
                    "reflect": ("Return", "reflect", bs1_parent),
                    "cross": ("Detector", "transmit", bs2_parent),
                    "return": ("Detector", "reflect", bs2_parent),
                }.get(leg_id, (ELEMENT_ARM_ROLE_DEFAULT, "", ""))
            else:
                parent_default = self._default_parent_splitter_id()
                role, selector, parent = {
                    "input": ("Common", "primary", parent_default),
                    "reflect": ("Return", "reflect", parent_default),
                    "transmit": ("Return", "transmit", parent_default),
                    "detector": ("Detector", "reflect", parent_default),
                }.get(leg_id, (ELEMENT_ARM_ROLE_DEFAULT, "", ""))
        else:
            if not selector:
                return None
            role = {
                "transmit": "Transmit",
                "reflect": "Reflect",
                "return": "Return",
            }.get(selector, ELEMENT_ARM_ROLE_DEFAULT)
            parent = parts[1].strip() if len(parts) >= 3 and parts[0] == "branch" else ""
        return _normalize_element_metadata(
            {
                "element_id": self._element_id_from_label(label),
                "element_name": label,
                "leg_id": leg_id,
                "arm_role": role,
                "parent_splitter": parent,
                "branch_selector": selector,
                "branch_path": branch_path,
                "arm_distance": 0.0,
                "local_decenter_x": 0.0,
                "local_decenter_y": 0.0,
                "local_tilt_x": 0.0,
                "local_tilt_y": 0.0,
                "local_tilt_z": 0.0,
            }
        )

    def assign_selected_elements_to_arm_key(self, arm_key: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Assign Path", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        blocks = self._selected_element_blocks()
        if not blocks:
            messagebox.showinfo("Assign Path", "Select one or more non-Object/non-Image rows or element groups first.", parent=self)
            return

        self._begin_history_capture()
        selected_indices: list[int] = []
        detail = self._arm_key_detail(arm_key)
        for indices in blocks:
            label = self._ensure_element_for_block(indices)
            metadata = self._element_metadata_for_arm_key(arm_key, label)
            if metadata is None:
                continue
            for index in indices:
                self.rows[index].element = label
                self._set_element_metadata(self.rows[index], metadata)
            selected_indices.extend(indices)
        if not selected_indices:
            self._history_pending_state = None
            messagebox.showinfo("Assign Path", "The selected path is not assignable for these rows.", parent=self)
            return
        self._normalize_special_rows()
        leg_id = self._leg_id_from_arm_key(arm_key)
        moved_indices = self._move_blocks_to_physical_leg_position(blocks, leg_id) if leg_id else []
        if moved_indices:
            selected_indices = moved_indices
        self._sync_table()
        self._select_table_indices(selected_indices, focus_index=selected_indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        move_note = " and moved into path order" if moved_indices else ""
        self.status_var.set(f"Assigned {len(blocks)} element(s) to {detail} path metadata{move_note}.")
        self._cleanup_current_popup_menu()

    def _main_scene_element_dialogs(self) -> MainSceneElementDialogs:
        dialogs = self.__dict__.get("_main_scene_element_dialogs_instance")
        if dialogs is None:
            dialogs = MainSceneElementDialogs(
                self,
                normalize_detector_settings=_normalize_detector_settings,
                scene_target_editor_kind_labels=SCENE_TARGET_EDITOR_KIND_LABELS,
                scene_target_editor_kind_choices=SCENE_TARGET_EDITOR_KIND_CHOICES,
                normalize_scene_target_editor_kind=_normalize_scene_target_editor_kind,
                element_metadata_numeric_fields=ELEMENT_METADATA_NUMERIC_FIELDS,
                normalize_element_metadata=_normalize_element_metadata,
                element_metadata_summary=_element_metadata_summary,
                short_error_message=_short_error_message,
                element_arm_role_default=ELEMENT_ARM_ROLE_DEFAULT,
                element_arm_role_values=ELEMENT_ARM_ROLE_VALUES,
                element_branch_selector_values=ELEMENT_BRANCH_SELECTOR_VALUES,
            )
            self._main_scene_element_dialogs_instance = dialogs
        return dialogs

    def open_detector_settings(self, row_index: int) -> None:
        self._main_scene_element_dialogs().open_detector_settings(row_index)


    def _scene_target_editor_kind_for_row(self, row_index: int) -> str:
        if not (0 <= int(row_index) < len(self.rows)):
            return "auto"
        row = self.rows[int(row_index)]
        surface = str(getattr(row, "surface", "") or "")
        if surface == OBJECT_TARGET_SURFACE:
            return "object_target"
        if surface == DIFFUSE_OBJECT_SURFACE:
            return "diffuse_object"
        if surface == "Aperture":
            return "aperture"
        role = str(self._scene_target_settings(row).get("role", "") or "")
        if role == "object_target":
            return "object_target"
        if role in {"analysis_target", "aperture", "detector"}:
            return role
        if surface != "Object" and (surface == "Image" or self._row_has_detector_output_metadata(row)):
            return "detector"
        return "auto"

    def _default_detector_settings_for_target_row(self, row_index: int) -> dict[str, object]:
        row = self.rows[int(row_index)]
        settings = self._detector_settings(row)
        diameter = self._safe_positive_float(getattr(row, "diameter", 0.0), 0.0)
        active_width = float(settings.get("active_width_mm", 0.0) or 0.0) or diameter or 1.0
        active_height = float(settings.get("active_height_mm", 0.0) or 0.0) or diameter or 1.0
        return _normalize_detector_settings(
            {
                "active_width_mm": active_width,
                "active_height_mm": active_height,
                "bins": settings.get("bins", ""),
                "pixel_pitch_um": settings.get("pixel_pitch_um", 0.0),
            }
        )

    def _set_nonseq_target_surface_index(self, row_index: int | None) -> None:
        self._refresh_analysis_surface_choices()
        var = self.__dict__.get("nonseq_target_surface_var")
        if var is None:
            return
        if row_index is None:
            var.set("Auto")
            return
        index = int(row_index)
        if 0 <= index < len(self.rows):
            var.set(f"{index}: {self.rows[index].name}")

    def _apply_scene_target_editor_update(
        self,
        row_index: int,
        *,
        target_kind: object,
        detector_settings: dict[str, object] | None = None,
        active_target: bool | None = None,
        row_name: str | None = None,
        clear_detector: bool = False,
    ) -> dict[str, object]:
        if not (0 <= int(row_index) < len(self.rows)):
            raise ValueError(f"Invalid target row index: {row_index}")
        index = int(row_index)
        row = self.rows[index]
        kind = _normalize_scene_target_editor_kind(target_kind)
        role = _scene_target_role_for_editor_kind(kind)
        if row_name is not None:
            name = str(row_name or "").strip()
            if name:
                row.name = name

        if kind == "detector":
            if row.surface == "Object":
                raise ValueError("Object rows cannot be detector planes.")
            data = _normalize_detector_settings(detector_settings or self._default_detector_settings_for_target_row(index))
            if _detector_settings_is_default(data):
                data = self._default_detector_settings_for_target_row(index)
            self._set_detector_settings(row, data)
        elif kind == "object_target":
            row.surface = OBJECT_TARGET_SURFACE
            self._apply_surface_type_defaults(index, row, OBJECT_TARGET_SURFACE)
            self._set_detector_settings(row, {})
        elif kind == "diffuse_object":
            row.surface = DIFFUSE_OBJECT_SURFACE
            self._apply_surface_type_defaults(index, row, DIFFUSE_OBJECT_SURFACE)
            self._set_detector_settings(row, {})
        elif kind == "aperture":
            row.surface = "Aperture"
            self._apply_surface_type_defaults(index, row, "Aperture")
            self._set_detector_settings(row, {})
        elif kind == "analysis_target":
            self._set_detector_settings(row, {})
        elif clear_detector:
            self._set_detector_settings(row, {})

        self._set_scene_target_settings(row, {"role": role})
        if active_target is not None:
            if bool(active_target):
                self._set_nonseq_target_surface_index(index)
                trace_mode_var = self.__dict__.get("trace_mode_var")
                if trace_mode_var is not None:
                    trace_mode_var.set("Non-Sequential Preview")
            elif self._current_nonseq_target_surface_index() == index:
                self._set_nonseq_target_surface_index(None)
        self._normalize_special_rows()
        return {
            "row_index": index,
            "target_kind": kind,
            "target_role": role,
            "surface": row.surface,
            "detector_settings": self._detector_settings(row),
            "scene_target_settings": self._scene_target_settings(row),
            "active_target": self._current_nonseq_target_surface_index() == index,
        }

    def _clear_scene_target_editor_metadata(self, row_index: int) -> dict[str, object]:
        if not (0 <= int(row_index) < len(self.rows)):
            raise ValueError(f"Invalid target row index: {row_index}")
        index = int(row_index)
        row = self.rows[index]
        self._set_scene_target_settings(row, {})
        self._set_detector_settings(row, {})
        if self._current_nonseq_target_surface_index() == index:
            self._set_nonseq_target_surface_index(None)
        self._normalize_special_rows()
        return {
            "row_index": index,
            "surface": row.surface,
            "detector_settings": self._detector_settings(row),
            "scene_target_settings": self._scene_target_settings(row),
            "active_target": self._current_nonseq_target_surface_index() == index,
        }

    def open_scene_target_editor(self, row_index: int | None = None) -> None:
        self._main_scene_element_dialogs().open_scene_target_editor(row_index)


    def open_selected_path_local_pose_editor(self) -> None:
        self._main_scene_element_dialogs().open_selected_path_local_pose_editor()


    def open_element_settings(self) -> None:
        self._main_scene_element_dialogs().open_element_settings()


    def flip_selected(self) -> None:
        if not self.table.selection():
            return
        self.flip_rows(self._selected_table_indices())

    def flip_rows(self, indices: list[int]) -> bool:
        cleaned = sorted({int(value) for value in indices if 0 <= int(value) < len(self.rows)})
        if len(cleaned) < 2:
            return False
        self._begin_history_capture()
        selected_rows = [SurfaceRow(**asdict(self.rows[index])) for index in cleaned]
        selected_thicknesses = [row.thickness for row in selected_rows]
        selected_glasses = [row.glass for row in selected_rows]
        flipped_rows = list(reversed(selected_rows))

        for row in flipped_rows:
            if row.surface == "Standard" and row.rc != 0.0:
                row.rc = -row.rc
            row.name = self._flipped_name(row.name)

        remapped_thicknesses = list(reversed(selected_thicknesses[:-1])) + [selected_thicknesses[-1]]
        remapped_glasses = list(reversed(selected_glasses[:-1])) + [selected_glasses[-1]]

        for row, thickness, glass in zip(flipped_rows, remapped_thicknesses, remapped_glasses):
            row.thickness = thickness
            row.glass = glass

        for index, row in zip(cleaned, flipped_rows):
            self.rows[index] = row
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(cleaned, focus_index=cleaned[0])
        self._commit_history_capture()
        self.refresh_plot()
        return True

    def move_up(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        selected_indices = self._selected_table_indices()
        if not selected_indices:
            self._history_pending_state = None
            return
        index = min(selected_indices)
        new_rows, new_start, new_end, moved = self._swap_element_block(self.rows, index, "up", same_arm_only=True)
        if not moved:
            if self._element_arm_role_for_index(self.rows, index) != ELEMENT_ARM_ROLE_DEFAULT:
                self.status_var.set("No previous element in the same path to move above.")
            self._history_pending_state = None
            return
        self.rows = new_rows
        self._sync_table()
        self._select_table_indices(list(range(new_start, new_end + 1)), focus_index=new_start)
        self._commit_history_capture()
        self.refresh_plot()

    def move_down(self) -> None:
        selected = self.table.selection()
        if not selected:
            return
        self._begin_history_capture()
        selected_indices = self._selected_table_indices()
        if not selected_indices:
            self._history_pending_state = None
            return
        index = max(selected_indices)
        new_rows, new_start, new_end, moved = self._swap_element_block(self.rows, index, "down", same_arm_only=True)
        if not moved:
            if self._element_arm_role_for_index(self.rows, index) != ELEMENT_ARM_ROLE_DEFAULT:
                self.status_var.set("No next element in the same path to move below.")
            self._history_pending_state = None
            return
        self.rows = new_rows
        self._sync_table()
        self._select_table_indices(list(range(new_start, new_end + 1)), focus_index=new_start)
        self._commit_history_capture()
        self.refresh_plot()

    def begin_edit(self, event: tk.Event) -> None:
        row_id = self.table.identify_row(event.y)
        column_id = self.table.identify_column(event.x)
        if not row_id or not column_id:
            return
        column_index = int(column_id.replace("#", "")) - 1
        field = FIELDS[column_index]
        if field == "label":
            return
        row_index = self._table_item_row_index(row_id)
        if row_index is None:
            source_record = self._table_item_scene_record(row_id)
            if source_record is not None and getattr(source_record, "kind", "") == SCENE_ROW_SOURCE:
                self.open_scene_source_manager(selected_source_id=str(getattr(source_record, "source_id", "") or ""))
            return
        if not self._table_cell_enabled(row_index, field):
            self.status_var.set(self._surface_type_disabled_message(row_index, field))
            self._schedule_active_cell_border_update()
            return
        bbox = self.table.bbox(row_id, column_id)
        if not bbox or len(bbox) != 4:
            return
        current_value = self.table.set(row_id, field)
        if field in {"rc", "thickness"}:
            current_value = current_value.replace("*", "").strip()

        if self.editor is not None:
            self.editor.destroy()
            self.editor = None
            self._editor_row_id = None
            self._editor_field = None

        if field == "surface":
            self._show_choice_menu(row_id, field, SURFACE_TYPES, event.x_root, event.y_root)
            return
        elif field == "glass":
            self._show_choice_menu(
                row_id,
                field,
                ("AIR", "BK7", "F2", "MIRROR"),
                event.x_root,
                event.y_root,
            )
            return
        else:
            editor = place_commit_cell_entry(
                self.table,
                value=current_value,
                bbox=tuple(int(value) for value in bbox),
                on_commit=lambda: self._finish_edit(row_id, field),
                on_cancel=self._cancel_edit,
            )
        self.editor = editor
        self._editor_row_id = row_id
        self._editor_field = field

    def _selected_surface_row_index(self) -> int | None:
        selected = self.table.selection()
        if selected:
            return self._table_item_row_index(selected[0])
        focused = self.table.focus()
        if focused:
            return self._table_item_row_index(focused)
        return None

    def convert_surface_type(self, row_index: int, surface_type: str) -> None:
        if not (0 <= row_index < len(self.rows)) or surface_type not in SURFACE_TYPES:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Convert Surface Type", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        row = self.rows[row_index]
        row.surface = surface_type
        self._apply_surface_type_defaults(row_index, row, surface_type)
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Converted S{row_index} to {surface_type}. Click Update to trace.")

    def _context_insert_after_index(self, row_index: int) -> int | None:
        if not (0 <= row_index < len(self.rows)):
            return self._selected_insert_index()
        block = self._element_indices_for_index(self.rows, row_index)
        return max(block) if block else row_index

    def _insert_quick_component_rows(
        self,
        rows: list[SurfaceRow],
        *,
        insert_after: int | None,
        element_name: str,
        status_label: str,
    ) -> None:
        if not rows:
            return
        for row in rows:
            row.element = element_name
        self._remap_inserted_element_labels(rows)
        self._begin_history_capture()
        insert_at = self._insert_surface_rows(rows, insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.refresh_plot(suppress_analysis=True)
        self.status_var.set(f"Inserted {status_label} at S{insert_at}. Click Update to trace.")

    def insert_surface_context_component(self, row_index: int, kind: str) -> None:
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Insert Component", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        insert_after = self._context_insert_after_index(row_index)
        common_layouts = {
            "singlet": "Single Lens",
            "doublet": "Doublet Lens",
            "flat_mirror": "Flat Mirror 45 Deg",
        }
        if kind in common_layouts:
            if insert_after is not None:
                self._select_table_indices([insert_after], focus_index=insert_after)
            self.insert_layout_component_by_name(common_layouts[kind])
            return

        diameter = 25.0
        if 0 <= row_index < len(self.rows):
            diameter = max(float(self.rows[row_index].diameter), 1.0)

        if kind == "object_target":
            rows = [
                SurfaceRow(
                    surface=OBJECT_TARGET_SURFACE,
                    name="Object target",
                    glass="MIRROR",
                    thickness=50.0,
                    diameter=max(diameter, 25.0),
                    axis_move=2.0,
                    advanced={
                        "Display2D": {"label": "Object target"},
                        "Note": (
                            "Specular proxy object: current tracing reflects rays from this target. "
                            "Replace with a Diffuse Object row when rough/diffuse scattering is required."
                        ),
                    },
                ),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Object target",
                status_label="object target proxy",
            )
            return

        if kind == "diffuse_object":
            settings = _normalize_diffuse_scatter_settings(DIFFUSE_SCATTER_DEFAULT_SETTINGS)
            rows = [
                SurfaceRow(
                    surface=DIFFUSE_OBJECT_SURFACE,
                    name="Diffuse object",
                    glass="MIRROR",
                    thickness=50.0,
                    diameter=max(diameter, 25.0),
                    axis_move=2.0,
                    advanced={
                        DIFFUSE_SCATTER_ADVANCED_ATTR: settings,
                        "Display2D": {"label": "Diffuse object"},
                        "Note": (
                            "Built-in diffuse scatter target. Use Diffuse / BRDF Settings to choose Lambertian, "
                            "Oren-Nayar, Cosine Lobe, or pySCATMECH BRDF behavior and adjust reflectance, samples, "
                            "cone, backend model, and target guidance."
                        ),
                    },
                ),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Diffuse object",
                status_label="diffuse object",
            )
            return

        if kind == "plate":
            rows = [
                SurfaceRow(surface="Standard", name="Window front", glass="BK7", thickness=10.0, diameter=diameter),
                SurfaceRow(surface="Standard", name="Window rear", glass="AIR", thickness=25.0, diameter=diameter),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Plate / Window",
                status_label="plate/window",
            )
            return

        if kind == "wedge_prism":
            rows = [
                SurfaceRow(surface="Standard", name="Wedge entrance", glass="BK7", thickness=20.0, diameter=diameter, tilt_x=20.0),
                SurfaceRow(surface="Standard", name="Wedge exit", glass="AIR", thickness=30.0, diameter=diameter, tilt_x=-20.0),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Wedge Prism",
                status_label="wedge prism",
            )
            return

        if kind == "right_angle_prism":
            rows = [
                SurfaceRow(surface="Standard", name="Right-angle entrance", glass="BK7", thickness=20.0, diameter=diameter),
                SurfaceRow(surface="Mirror", name="Hypotenuse fold mirror", glass="MIRROR", thickness=20.0, diameter=diameter, tilt_x=45.0, axis_move=2.0),
                SurfaceRow(surface="Standard", name="Right-angle exit", glass="AIR", thickness=30.0, diameter=diameter, tilt_x=90.0),
            ]
            rows[1].advanced = {
                "Note": (
                    "Right-angle prism table primitive: hypotenuse is modeled as a fold mirror. "
                    "Use Optical CAD/STL Solid for arbitrary prism boundary tracing."
                )
            }
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Right-Angle Prism",
                status_label="right-angle prism primitive",
            )
            return

        if kind == "cube_beam_splitter":
            settings = _normalize_beam_splitter_settings(
                {
                    "split_mode": "Deterministic Fresnel P/S",
                    "reflectance": 0.5,
                    "absorption": 0.0,
                    "polarization_p_fraction": 0.5,
                    "max_branch_depth": 4,
                }
            )
            splitter_advanced = {
                BEAM_SPLITTER_ADVANCED_ATTR: settings,
                "Coating": _beam_splitter_coating_for_settings(settings, None),
                "Note": (
                    "Cube beam splitter primitive: entrance face, internal 45 degree splitter, and transmit exit face. "
                    "Reflected-path exit geometry is handled by non-sequential branch tracing/path components; "
                    "use an optical STL solid for a closed cube with all side faces."
                ),
            }
            rows = [
                SurfaceRow(surface="Standard", name="Cube BS entrance", glass="BK7", thickness=10.0, diameter=diameter),
                SurfaceRow(
                    surface=BEAM_SPLITTER_SURFACE,
                    name="Cube BS coated diagonal",
                    glass="BK7",
                    thickness=10.0,
                    diameter=diameter,
                    tilt_x=45.0,
                    advanced=splitter_advanced,
                ),
                SurfaceRow(surface="Standard", name="Cube BS transmit exit", glass="AIR", thickness=30.0, diameter=diameter),
            ]
            self._insert_quick_component_rows(
                rows,
                insert_after=insert_after,
                element_name="Cube Beam Splitter",
                status_label="cube beam splitter primitive",
            )
            return

    def insert_fold_mirror_below_index(self, row_index: int) -> None:
        """Insert a sequential 45-degree fold mirror below ``row_index`` so every
        surface that follows is repositioned onto the reflected path.

        A sequential ``Mirror`` row folds the optical axis for free (the system
        builder forces ``AxisMove = 2.0``), so the downstream surfaces stay on the
        beam -- unlike a promoted non-sequential prism, which folds the rays but
        leaves the table rows on the original axis.  The gap the mirror lands in
        is split between the upstream surface and the mirror, so the conjugate
        (focus) is preserved.
        """
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Insert Fold Mirror", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        insert_after = self._context_insert_after_index(row_index)
        if insert_after is None or not can_insert_fold_mirror(self.rows, insert_after):
            messagebox.showinfo(
                "Insert Fold Mirror",
                "A fold mirror needs at least one surface after it to reflect onto. "
                "Select a surface upstream of the image plane and try again.",
                parent=self,
            )
            return
        plan = plan_fold_mirror(self.rows, insert_after)
        mirror_row = plan.mirror_row
        mirror_row.element = "Fold Mirror"
        self._begin_history_capture()
        self.rows[insert_after].thickness = plan.upstream_thickness
        self._remap_inserted_element_labels([mirror_row])
        insert_at = self._insert_surface_rows([mirror_row], insert_after=insert_after)
        self._commit_history_capture()
        self.current_layout_file = None
        self.refresh_plot(suppress_analysis=True)
        self.status_var.set(
            f"Inserted fold mirror at S{insert_at}; rows below now follow the reflected path. Click Update to trace."
        )

    @staticmethod
    def _rectangle_uda(width: float, height: float) -> list[list[float]]:
        half_w = max(float(width) * 0.5, 1e-6)
        half_h = max(float(height) * 0.5, 1e-6)
        return [[-half_w, half_w, half_w, -half_w, -half_w], [-half_h, -half_h, half_h, half_h, -half_h]]

    def apply_shape_aperture_preset(self, row_index: int, preset: str) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        if self.rows[row_index].surface in {"Object", "Image"}:
            messagebox.showinfo("Shape / Aperture", "Shape presets apply to physical surfaces, not Object/Image rows.", parent=self)
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Shape / Aperture", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        row = self.rows[row_index]
        advanced = dict(row.advanced or {})
        diameter = max(float(row.diameter), 1.0)
        if preset != "spider":
            advanced.pop("Mask_Shape", None)
            advanced.pop("Mask_Type", None)
        if preset == "circular":
            row.uda = "None"
            row.in_diameter = 0.0
            status = "Set circular clear aperture."
        elif preset == "rectangular":
            row.uda = self._rectangle_uda(diameter, diameter * 0.7)
            row.in_diameter = 0.0
            status = "Set rectangular UDA aperture."
        elif preset == "annulus":
            if row.surface == "Standard":
                row.surface = "Aperture"
                self._apply_surface_type_defaults(row_index, row, "Aperture")
            row.in_diameter = max(diameter * 0.45, 0.1)
            row.uda = "None"
            status = "Set annular aperture using InDia."
        elif preset == "spider":
            advanced["Mask_Shape"] = {
                "kind": "mask_shape",
                "preset": "spider",
                "arms": 4,
                "arm_width": max(diameter / 30.0, 0.2),
                "hub_radius": max(diameter / 20.0, 0.3),
                "extent": diameter * 1.1,
            }
            advanced["Mask_Type"] = 2
            status = "Set spider mask preset."
        elif preset == "rectangular_clear":
            if row.surface == "Standard":
                row.surface = "Aperture"
                self._apply_surface_type_defaults(row_index, row, "Aperture")
            row.uda = self._rectangle_uda(diameter, diameter * 0.7)
            status = "Set rectangular clear-aperture UDA."
        else:
            self._history_pending_state = None
            return
        row.advanced = advanced
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"{status} Click Update to trace.")

    def apply_material_to_selected(self, glass: str, *, mirror_surface: bool = False) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Material", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        for index in indices:
            row = self.rows[index]
            row.glass = glass
            if mirror_surface:
                row.surface = "Mirror"
                self._apply_surface_type_defaults(index, row, "Mirror")
            elif row.surface in REFLECTIVE_PROXY_SURFACES and glass.upper() != "MIRROR":
                row.surface = "Standard"
                self._apply_surface_type_defaults(index, row, "Standard")
                row.glass = glass
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Applied material {glass} to {len(indices)} selected row(s). Click Update.")

    def apply_coating_preset_to_selected(self, preset_name: str) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        if preset_name not in COATING_PRESETS:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Polarization", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        preset = COATING_PRESETS[preset_name]
        for index in indices:
            row = self.rows[index]
            advanced = dict(row.advanced or {})
            if preset == [[], [], [], []]:
                advanced.pop("Coating", None)
                advanced.pop("CoatingMet", None)
            else:
                advanced["Coating"] = preset
            if preset_name == "Protected mirror 94%":
                row.surface = "Mirror"
                row.glass = "MIRROR"
            row.advanced = advanced
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Applied coating preset {preset_name} to {len(indices)} row(s). Click Update.")

    def apply_metal_fresnel_mode_to_selected(self) -> None:
        indices = [index for index in self._selected_table_indices() if 0 < index < len(self.rows) - 1]
        if not indices:
            return
        self._commit_pending_table_edit()
        try:
            self._read_rows_from_table()
        except Exception as exc:
            messagebox.showerror("Coating / Polarization", f"Could not read the surface table:\n\n{exc}", parent=self)
            return
        self._begin_history_capture()
        for index in indices:
            row = self.rows[index]
            advanced = dict(row.advanced or {})
            try:
                coating_met = int(float(advanced.get("CoatingMet", 0) or 0))
            except Exception:
                coating_met = 0
            advanced.pop("Coating", None)
            advanced["CoatingMet"] = max(coating_met, 0)
            row.advanced = advanced
            row.surface = "Mirror"
            row.glass = "MIRROR"
            self._apply_surface_type_defaults(index, row, "Mirror")
        self._normalize_special_rows()
        self._sync_table()
        self._select_table_indices(indices, focus_index=indices[0])
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Enabled metal Fresnel mirror mode on {len(indices)} selected row(s). Click Update.")

    def apply_beam_splitter_fresnel_ps(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        self.convert_surface_type(row_index, BEAM_SPLITTER_SURFACE)
        self._begin_history_capture()
        row = self.rows[row_index]
        advanced = dict(row.advanced or {})
        settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
        settings["split_mode"] = "Deterministic Fresnel P/S"
        advanced[BEAM_SPLITTER_ADVANCED_ATTR] = settings
        advanced["Coating"] = _beam_splitter_coating_for_settings(settings, advanced.get("Coating"))
        row.advanced = advanced
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Enabled Fresnel P/S deterministic splitting on S{row_index}. Click Update.")

    def align_surface_normal_to_previous(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        previous = next(
            (
                self.rows[index]
                for index in range(row_index - 1, 0, -1)
                if self.rows[index].surface not in {"Object", "Image"}
            ),
            None,
        )
        self._begin_history_capture()
        row = self.rows[row_index]
        if previous is None:
            row.tilt_x = row.tilt_y = row.tilt_z = 0.0
        else:
            row.tilt_x = float(previous.tilt_x)
            row.tilt_y = float(previous.tilt_y)
            row.tilt_z = float(previous.tilt_z)
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Aligned S{row_index} to the previous local table orientation. Click Update.")

    def set_surface_incidence_angle(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        value = simpledialog.askfloat(
            "Set Incidence Angle",
            "Set TiltX/display incidence angle [deg]:",
            initialvalue=float(self.rows[row_index].tilt_x),
            parent=self,
        )
        if value is None:
            return
        self._begin_history_capture()
        self.rows[row_index].tilt_x = float(value)
        self._sync_table()
        self._select_table_row(row_index)
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self.status_var.set(f"Set S{row_index} TiltX to {float(value):.6g} deg. Click Update.")

    def assign_selected_to_current_path_view(self) -> None:
        arm_key = self._current_arm_view_key()
        if not arm_key:
            self.status_var.set("Choose a Path view before assigning selected rows to the current path.")
            return
        self.assign_selected_elements_to_arm_key(arm_key)

    def reverse_element_for_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        indices = self._element_indices_for_index(self.rows, row_index)
        if len(indices) < 2:
            indices = self._selected_table_indices()
        if len(indices) < 2:
            self.status_var.set("Select at least two rows, or a grouped element, before reversing.")
            return
        self._select_table_indices(indices, focus_index=indices[0])
        self.flip_selected()

    def set_analysis_surface_to_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        self._refresh_analysis_surface_choices()
        self.analysis_surface_var.set(f"{row_index}: {self.rows[row_index].name}")
        self._mark_plot_update_pending()
        self.status_var.set(f"Analysis surface set to S{row_index}: {self.rows[row_index].name}. Click Update.")

    def set_nonseq_target_to_row(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)) or not hasattr(self, "nonseq_target_surface_var"):
            return
        self._refresh_analysis_surface_choices()
        self.nonseq_target_surface_var.set(f"{row_index}: {self.rows[row_index].name}")
        if hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set("Non-Sequential Preview")
            self.trace_mode = "Non-Sequential Preview"
        self._mark_plot_update_pending()
        self.status_var.set(f"Non-sequential target set to S{row_index}: {self.rows[row_index].name}. Click Update.")

    def validate_surface_row_physics(self, row_index: int) -> None:
        if not (0 <= row_index < len(self.rows)):
            return
        row = self.rows[row_index]
        errors: list[str] = []
        warnings_out: list[str] = []
        if row.surface not in SURFACE_TYPES:
            errors.append(f"Unsupported surface type: {row.surface}")
        for attr in ("rc", "k", "thickness", "diameter", "in_diameter", "tilt_x", "tilt_y", "tilt_z", "desp_x", "desp_y", "desp_z"):
            try:
                value = float(getattr(row, attr))
            except Exception:
                errors.append(f"{attr} is not numeric")
                continue
            if not np.isfinite(value):
                errors.append(f"{attr} is not finite")
        if float(row.diameter) <= 0.0:
            errors.append("Diameter must be positive.")
        if row.surface in REFLECTIVE_PROXY_SURFACES and str(row.glass).upper() != "MIRROR":
            warnings_out.append(f"{row.surface} rows normally use Material=MIRROR internally.")
        if row.surface == BEAM_SPLITTER_SURFACE and not isinstance((row.advanced or {}).get(BEAM_SPLITTER_ADVANCED_ATTR), dict):
            warnings_out.append("Beam Splitter row has no explicit BeamSplitter settings; defaults will be used.")
        if row.surface == DIFFUSE_OBJECT_SURFACE and not isinstance((row.advanced or {}).get(DIFFUSE_SCATTER_ADVANCED_ATTR), dict):
            warnings_out.append("Diffuse Object row has no explicit DiffuseScatter settings; defaults will be used.")
        advanced = row.advanced or {}
        if isinstance(advanced, dict) and row.surface != BEAM_SPLITTER_SURFACE:
            solid_source_text = " ".join(
                str(value or "")
                for value in (
                    row.name,
                    advanced.get("Solid_3d_stl"),
                    advanced.get("OpticalSolidSourcePath"),
                    advanced.get("OpticalSolidSourceFormat"),
                )
            ).lower()
            if self._scene_graph_value_present(advanced.get("Solid_3d_stl")) and any(
                token in solid_source_text for token in ("beam splitter", "beamsplitter", "cube bs", " 68551", "/68551", "step_68551")
            ):
                metadata = normalize_optical_solid_face_metadata(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR, {}))
                if not optical_solid_has_virtual_splitter_plane(metadata):
                    warnings_out.append(
                        "This looks like passive beam-splitter CAD. A CAD/STEP solid does not encode the internal coated diagonal; "
                        "use a Beam Splitter row or the validated cube beam-splitter primitive for branch physics."
                    )
        advanced_errors, advanced_warnings = _validate_advanced_surface_inputs(dict(row.advanced or {}), row.extra_data, row.uda)
        errors.extend(advanced_errors)
        warnings_out.extend(advanced_warnings)
        detail = [f"S{row_index}: {row.surface} / {row.name}"]
        detail.extend(f"ERROR: {item}" for item in errors)
        detail.extend(f"Warning: {item}" for item in warnings_out)
        if not errors and not warnings_out:
            detail.append("Validation passed.")
        message = "\n".join(detail)
        if errors:
            messagebox.showerror("Validate Surface Row", message, parent=self)
        elif warnings_out:
            messagebox.showwarning("Validate Surface Row", message, parent=self)
        else:
            messagebox.showinfo("Validate Surface Row", message, parent=self)

    @staticmethod
    def _advanced_surface_default_text(attr: str) -> str:
        try:
            default = getattr(Kos.surf(), attr)
        except Exception:
            return ""
        literal = _layout_literal_value(default)
        if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
            return "<native object>"
        text = " ".join(repr(literal).split())
        return text if len(text) <= 72 else text[:69] + "..."

    @staticmethod
    def _is_default_extra_data(value) -> bool:
        try:
            return bool(np.all(np.asarray(value, dtype=object) == 0))
        except Exception:
            return value in (0, 0.0, "None", None)

    @staticmethod
    def _is_default_uda(value) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value == "None"
        return False

    @staticmethod
    def _short_numeric_list(value, limit: int = 12) -> str:
        try:
            arr = np.asarray(value, dtype=float).ravel()
        except Exception:
            return ""
        if arr.size == 0:
            return ""
        significant = arr[:limit]
        while significant.size and abs(float(significant[-1])) <= 1e-15:
            significant = significant[:-1]
        return pformat(significant.tolist(), width=100) if significant.size else ""

    @staticmethod
    def _decoded_uda_polygon(value) -> tuple[np.ndarray, np.ndarray] | None:
        try:
            decoded = decode_custom_surface_value(value)
        except Exception:
            decoded = value
        if decoded is None or (isinstance(decoded, str) and decoded == "None"):
            return None
        if not isinstance(decoded, (list, tuple)) or len(decoded) != 2:
            return None
        try:
            px = np.asarray(decoded[0], dtype=float).ravel()
            py = np.asarray(decoded[1], dtype=float).ravel()
        except Exception:
            return None
        if px.size != py.size or px.size < 3:
            return None
        return px, py

    @staticmethod
    def _mask_preset_summary(value) -> str:
        if not isinstance(value, dict):
            return ""
        if str(value.get("kind", "")).strip().lower() not in {"mask_shape", "mask", "mask_preset"}:
            return ""
        preset = str(value.get("preset", "")).strip().lower()
        if preset == "ronchi":
            return "Ronchi mask"
        if preset == "spider":
            return "Spider mask"
        return str(value.get("preset", "Mask preset"))

    def _surface_preview_grid(
        self,
        row: SurfaceRow,
        advanced: dict[str, object],
        extra_data,
        *,
        samples: int = 121,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        radius = max(float(row.diameter) * 0.5, 1.0)
        axis = np.linspace(-radius, radius, int(samples))
        x_grid, y_grid = np.meshgrid(axis, axis)
        r_grid = np.hypot(x_grid, y_grid)
        inside = r_grid <= radius
        sag = np.full_like(x_grid, np.nan, dtype=float)
        c = 1.0 / float(row.rc) if abs(float(row.rc)) > 1e-12 else 0.0
        if abs(c) > 0.0:
            k = float(getattr(row, "k", 0.0))
            root = 1.0 - (1.0 + k) * c * c * r_grid * r_grid
            safe_root = np.maximum(root, 0.0)
            denom = 1.0 + np.sqrt(safe_root)
            base = np.divide(c * r_grid * r_grid, denom, out=np.zeros_like(r_grid), where=np.abs(denom) > 1e-15)
        else:
            base = np.zeros_like(r_grid)
        sag[inside] = base[inside]
        aspher = np.asarray(advanced.get("AspherData", []), dtype=float).ravel() if "AspherData" in advanced else np.empty(0)
        for index, coeff in enumerate(aspher[:12], start=1):
            if abs(float(coeff)) <= 0.0:
                continue
            sag[inside] += float(coeff) * np.power(r_grid[inside], 2 * index)
        znk = np.asarray(advanced.get("ZNK", []), dtype=float).ravel() if "ZNK" in advanced else np.empty(0)
        if znk.size:
            rho = np.divide(r_grid, radius, out=np.zeros_like(r_grid), where=radius > 0.0)
            theta = np.arctan2(y_grid, x_grid)
            z_terms = [
                np.ones_like(rho),
                rho * np.cos(theta),
                rho * np.sin(theta),
                2.0 * rho * rho - 1.0,
                rho * rho * np.cos(2.0 * theta),
                rho * rho * np.sin(2.0 * theta),
                (3.0 * rho**3 - 2.0 * rho) * np.cos(theta),
                (3.0 * rho**3 - 2.0 * rho) * np.sin(theta),
                6.0 * rho**4 - 6.0 * rho * rho + 1.0,
            ]
            for coeff, basis in zip(znk[: len(z_terms)], z_terms):
                if abs(float(coeff)) > 0.0:
                    sag[inside] += float(coeff) * basis[inside]
        try:
            decoded_extra = decode_custom_surface_value(extra_data)
            if isinstance(decoded_extra, (list, tuple)) and len(decoded_extra) == 2 and callable(decoded_extra[0]):
                extra = np.asarray(decoded_extra[0](x_grid, y_grid, decoded_extra[1]), dtype=float)
                if extra.shape == sag.shape:
                    sag[inside] += extra[inside]
        except Exception:
            pass
        return x_grid, y_grid, sag, inside

    def _main_surface_shape_builder_dialog(self) -> MainSurfaceShapeBuilderDialog:
        dialog = self.__dict__.get("_main_surface_shape_builder_dialog_instance")
        if dialog is None:
            dialog = MainSurfaceShapeBuilderDialog(
                self,
                attachment_dir=ATTACHMENT_DIR,
                project_root=PROJECT_ROOT,
                optical_solid_filetypes=OPTICAL_SOLID_FILETYPES,
                encode_custom_surface_value=encode_custom_surface_value,
                parse_literal_editor_text=_parse_literal_editor_text,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
                optical_solid_mesh_path_from_source=_optical_solid_mesh_path_from_source,
                short_error_message=_short_error_message,
            )
            self._main_surface_shape_builder_dialog_instance = dialog
        return dialog

    def open_surface_shape_builder(self, row_index: int | None = None) -> None:
        self._main_surface_shape_builder_dialog().open(row_index)

    @staticmethod
    def _coating_preset_for_value(value) -> str:
        literal = _layout_literal_value(value)
        if literal is _UNSERIALIZABLE_LAYOUT_VALUE:
            return "Custom"
        for name, preset in COATING_PRESETS.items():
            if literal == _layout_literal_value(preset):
                return name
        return "Custom"

    def _main_coating_material_dialog(self) -> MainCoatingMaterialDialog:
        dialog = self.__dict__.get("_main_coating_material_dialog_instance")
        if dialog is None:
            dialog = MainCoatingMaterialDialog(
                self,
                coating_presets=COATING_PRESETS,
                coating_preset_names=COATING_PRESET_NAMES,
                metal_catalog_dir=METAL_CATALOG_DIR,
                literal_editor_text=_literal_editor_text,
                parse_literal_editor_text=_parse_literal_editor_text,
                normalize_metal_catalog_specs=_normalize_metal_catalog_specs,
                metal_catalog_entries=_metal_catalog_entries,
                metal_catalog_type_for_path=_metal_catalog_type_for_path,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
            )
            self._main_coating_material_dialog_instance = dialog
        return dialog

    def open_coating_material_editor(self, row_index: int | None = None) -> None:
        self._main_coating_material_dialog().open(row_index)

    def _main_diffuse_scatter_dialog(self) -> MainDiffuseScatterDialog:
        dialog = self.__dict__.get("_main_diffuse_scatter_dialog_instance")
        if dialog is None:
            dialog = MainDiffuseScatterDialog(
                self,
                diffuse_object_surface=DIFFUSE_OBJECT_SURFACE,
                diffuse_scatter_advanced_attr=DIFFUSE_SCATTER_ADVANCED_ATTR,
                diffuse_scatter_default_settings=DIFFUSE_SCATTER_DEFAULT_SETTINGS,
                normalize_diffuse_scatter_settings=_normalize_diffuse_scatter_settings,
                validate_diffuse_scatter_settings=_validate_diffuse_scatter_settings,
                pyscatmech_status=pyscatmech_status,
                format_pyscatmech_parameters=format_pyscatmech_parameters,
            )
            self._main_diffuse_scatter_dialog_instance = dialog
        return dialog

    def open_diffuse_scatter_settings(self, row_index: int | None = None) -> None:
        self._main_diffuse_scatter_dialog().open(row_index)

    def _main_beam_splitter_dialog(self) -> MainBeamSplitterDialog:
        dialog = self.__dict__.get("_main_beam_splitter_dialog_instance")
        if dialog is None:
            dialog = MainBeamSplitterDialog(
                self,
                beam_splitter_surface=BEAM_SPLITTER_SURFACE,
                beam_splitter_advanced_attr=BEAM_SPLITTER_ADVANCED_ATTR,
                beam_splitter_split_modes=BEAM_SPLITTER_SPLIT_MODES,
                normalize_beam_splitter_settings=_normalize_beam_splitter_settings,
                validate_beam_splitter_settings=_validate_beam_splitter_settings,
                beam_splitter_coating_for_settings=_beam_splitter_coating_for_settings,
                beam_splitter_summary=_beam_splitter_summary,
                short_error_message=_short_error_message,
            )
            self._main_beam_splitter_dialog_instance = dialog
        return dialog

    def open_beam_splitter_settings(self, row_index: int | None = None) -> None:
        self._main_beam_splitter_dialog().open(row_index)

    def _main_error_map_dialog(self) -> MainErrorMapDialog:
        dialog = self.__dict__.get("_main_error_map_dialog_instance")
        if dialog is None:
            dialog = MainErrorMapDialog(
                self,
                attachment_dir=ATTACHMENT_DIR,
                project_root=PROJECT_ROOT,
                error_map_literal=_error_map_literal,
                error_map_summary=_error_map_summary,
                load_error_map_file=_load_error_map_file,
                validate_error_map=_validate_error_map,
            )
            self._main_error_map_dialog_instance = dialog
        return dialog

    def open_error_map_editor(self, row_index: int | None = None) -> None:
        self._main_error_map_dialog().open(row_index)

    def _main_advanced_surface_dialog(self) -> MainAdvancedSurfaceDialog:
        dialog = self.__dict__.get("_main_advanced_surface_dialog_instance")
        if dialog is None:
            dialog = MainAdvancedSurfaceDialog(
                self,
                advanced_row_shape_fields=ADVANCED_ROW_SHAPE_FIELDS,
                advanced_surface_field_groups=ADVANCED_SURFACE_FIELD_GROUPS,
                advanced_surface_attr_names=ADVANCED_SURFACE_ATTR_NAMES,
                variable_registry=VARIABLE_REGISTRY,
                column_labels=COLUMN_LABELS,
                literal_editor_text=_literal_editor_text,
                parse_literal_editor_text=_parse_literal_editor_text,
                format_float_sequence=_format_float_sequence,
                parse_float_sequence_text=_parse_float_sequence_text,
                validate_advanced_surface_inputs=_validate_advanced_surface_inputs,
            )
            self._main_advanced_surface_dialog_instance = dialog
        return dialog

    def open_advanced_surface_editor(self, row_index: int | None = None) -> None:
        self._main_advanced_surface_dialog().open(row_index)

    def _main_surface_settings_dialogs(self) -> MainSurfaceSettingsDialogs:
        dialogs = self.__dict__.get("_main_surface_settings_dialogs_instance")
        if dialogs is None:
            dialogs = MainSurfaceSettingsDialogs(
                self,
                galvo_scan_overlay_key=GALVO_SCAN_OVERLAY_KEY,
                format_float_sequence=_format_float_sequence,
                parse_float_sequence_text=_parse_float_sequence_text,
                short_error_message=_short_error_message,
            )
            self._main_surface_settings_dialogs_instance = dialogs
        return dialogs

    def open_galvo_scan_overlay_settings(self, index: int | None = None) -> None:
        self._main_surface_settings_dialogs().open_galvo_scan_overlay_settings(index)

    def open_surface_additional_settings(self, index: int | None = None) -> None:
        self._main_surface_settings_dialogs().open_surface_additional_settings(index)

    def _open_grating_settings_editor(self, row_index: int) -> None:
        self._main_surface_settings_dialogs().open_grating_settings_editor(row_index)

    def _main_context_menu(self) -> MainContextMenu:
        builder = self.__dict__.get("_main_context_menu_instance")
        if builder is None:
            builder = MainContextMenu(
                self,
                fields=FIELDS,
                scene_row_source=SCENE_ROW_SOURCE,
                object_target_surface=OBJECT_TARGET_SURFACE,
                diffuse_object_surface=DIFFUSE_OBJECT_SURFACE,
                beam_splitter_surface=BEAM_SPLITTER_SURFACE,
                coating_preset_names=COATING_PRESET_NAMES,
                element_arm_role_default=ELEMENT_ARM_ROLE_DEFAULT,
                element_arm_role_values=ELEMENT_ARM_ROLE_VALUES,
            )
            self._main_context_menu_instance = builder
        return builder

    def show_context_menu(self, event: tk.Event) -> None:
        self._main_context_menu().show_context_menu(event)


    def _finish_edit(self, row_id: str, field: str, quiet: bool = False) -> None:
        if self.editor is None:
            return
        value = self.editor.get().strip()
        self.editor.destroy()
        self.editor = None
        self._editor_row_id = None
        self._editor_field = None
        if not value:
            return
        row_index = self._table_item_row_index(row_id)
        if row_index is None:
            return
        if field in NUMERIC_FIELDS:
            accepts_pose_sequence = False
            path_local_pose_cell = self._path_local_pose_cell_enabled(row_index, field)
            if field in POSE_TOLERANCE_FIELDS and 0 <= row_index < len(self.rows) and not path_local_pose_cell:
                try:
                    pose_values = _parse_float_sequence_text(value.replace("*", "").strip())
                    if len(pose_values) > POSE_TOLERANCE_MAX_VARIANTS:
                        raise ValueError(f"Use {POSE_TOLERANCE_MAX_VARIANTS} or fewer overlay values.")
                    accepts_pose_sequence = bool(pose_values)
                except Exception:
                    accepts_pose_sequence = False
            if not accepts_pose_sequence:
                try:
                    float(value)
                except ValueError:
                    if not quiet:
                        messagebox.showerror(
                            "Invalid value",
                            f"{COLUMN_LABELS[field]} expects a number"
                            + (" or comma/range tolerance values." if field in POSE_TOLERANCE_FIELDS and not path_local_pose_cell else "."),
                        )
                    return
        if not self._table_cell_enabled(row_index, field):
            if not quiet:
                self.status_var.set(self._surface_type_disabled_message(row_index, field))
            return
        self._begin_history_capture()
        if field == "diameter" and row_index == len(self.rows) - 1:
            self._set_image_diameter_mode("Manual")
        self.table.set(row_id, field, value)
        self._read_rows_from_table()
        self._normalize_special_rows()
        self._couple_object_image_diameter_after_edit(row_index, field)
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()

    def _couple_object_image_diameter_after_edit(self, row_index: int, field: str) -> None:
        if field != "diameter" or len(self.rows) < 2:
            return
        if row_index not in {0, len(self.rows) - 1}:
            return
        if self._current_object_mode() != "Finite":
            return
        magnification = self._current_finite_paraxial_magnification()
        if magnification is None or not np.isfinite(magnification) or abs(float(magnification)) <= 1e-12:
            return
        mag = abs(float(magnification))
        self._set_image_diameter_mode("Manual")
        if row_index == 0 and self.rows[0].surface == "Object":
            object_diameter = max(float(self.rows[0].diameter), 0.0)
            self.rows[-1].diameter = max(object_diameter * mag, 1e-6)
            source = "Object"
        elif row_index == len(self.rows) - 1 and self.rows[-1].surface == "Image":
            image_diameter = max(float(self.rows[-1].diameter), 0.0)
            self.rows[0].diameter = max(image_diameter / mag, 1e-6)
            source = "Image"
        else:
            return
        self._sync_field_value_from_diameter_pair()
        status_var = self.__dict__.get("status_var")
        if status_var is not None:
            status_var.set(
                f"{source} diameter applied; paired diameter updated with |m|={mag:.6g}. Click Update to redraw."
            )

    def _sync_object_diameter_from_manual_image(self) -> bool:
        if len(self.rows) < 2 or self.rows[0].surface != "Object" or self.rows[-1].surface != "Image":
            return False
        if self._current_object_mode() != "Finite" or self._current_image_diameter_mode() != "Manual":
            return False
        magnification = self._current_finite_paraxial_magnification()
        if magnification is None or not np.isfinite(magnification) or abs(float(magnification)) <= 1e-12:
            return False
        image_diameter = max(float(self.rows[-1].diameter), 0.0)
        self.rows[0].diameter = max(image_diameter / abs(float(magnification)), 1e-6)
        self._sync_field_value_from_diameter_pair()
        return True

    def _sync_field_value_from_diameter_pair(self) -> None:
        if self.__dict__.get("field_value_var") is None or self.__dict__.get("field_type_var") is None or not self.rows:
            return
        field_type = self._current_field_type()
        object_half = max(float(self.rows[0].diameter) * 0.5, 0.0)
        image_half = max(float(self.rows[-1].diameter) * 0.5, 0.0)
        if field_type == "Object Height":
            value = object_half
        elif field_type in {"Paraxial Image Height", "Real Image Height"}:
            value = image_half
        elif field_type == "Angle":
            value = float(np.rad2deg(np.arctan2(object_half, max(self._current_object_distance(), 1e-9))))
        else:
            return
        self.field_value_var.set(self._format_table_float(value))

    def _set_image_diameter_mode(self, mode: str) -> None:
        image_diameter_mode_var = self.__dict__.get("image_diameter_mode_var")
        if image_diameter_mode_var is not None and mode in {"Auto", "Manual"}:
            image_diameter_mode_var.set(mode)

    def _cancel_edit(self) -> None:
        if self.editor is None:
            return
        self.editor.destroy()
        self.editor = None
        self._editor_row_id = None
        self._editor_field = None

    def _commit_pending_table_edit(self) -> None:
        if self.editor is None or self._editor_row_id is None or self._editor_field is None:
            return
        self._finish_edit(self._editor_row_id, self._editor_field, quiet=True)

    def _show_choice_menu(
        self,
        row_id: str,
        field: str,
        values: tuple[str, ...],
        x_root: int,
        y_root: int,
    ) -> None:
        self._cleanup_current_popup_menu()
        menu = tk.Menu(self, tearoff=0)
        for value in values:
            menu.add_command(
                label=value,
                command=lambda selected=value: self._apply_choice(row_id, field, selected),
            )
        self._post_popup_menu(menu, x_root, y_root)

    def _post_popup_menu(self, menu: tk.Menu, x_root: int, y_root: int) -> None:
        self.popup_menu = menu
        try:
            menu.tk_popup(x_root, y_root)
        finally:
            try:
                menu.grab_release()
            except tk.TclError:
                pass

    def _apply_choice(self, row_id: str, field: str, value: str) -> None:
        self._begin_history_capture()
        self.table.set(row_id, field, value)
        self._read_rows_from_table()
        if field == "surface":
            index = self._table_item_row_index(row_id)
            if index is None:
                return
            row = self.rows[index]
            self._apply_surface_type_defaults(index, row, value)
        self._normalize_special_rows()
        self._sync_table()
        self._commit_history_capture()
        self._mark_plot_update_pending()
        self._cleanup_current_popup_menu()

    def _apply_surface_type_defaults(self, index: int, row: SurfaceRow, surface_type: str) -> None:
        prev_row = self.rows[index - 1] if index > 0 else None
        next_row = self.rows[index + 1] if index + 1 < len(self.rows) else None
        neighbor_diameters = [
            float(candidate.diameter)
            for candidate in (prev_row, next_row)
            if candidate is not None and candidate.surface not in {"Object", "Image"}
        ]
        fallback_diameter = min(neighbor_diameters) if neighbor_diameters else max(float(row.diameter), 10.0)

        if surface_type in REFLECTIVE_PROXY_SURFACES:
            default_name = (
                "Object target"
                if surface_type == OBJECT_TARGET_SURFACE
                else "Diffuse object"
                if surface_type == DIFFUSE_OBJECT_SURFACE
                else "Mirror"
            )
            row.name = default_name if row.name in {"", "Surface", "Standard", "Aperture", "Mirror", "Object target", "Diffuse object"} else row.name
            row.glass = "MIRROR"
            row.rc = 0.0
            if surface_type == "Mirror" and abs(row.tilt_x) < 1e-9 and abs(row.tilt_y) < 1e-9 and abs(row.tilt_z) < 1e-9:
                row.tilt_x = 45.0
            if abs(row.axis_move) < 1e-9:
                row.axis_move = 2.0
            advanced = dict(row.advanced or {})
            if surface_type == OBJECT_TARGET_SURFACE:
                display = dict(advanced.get("Display2D", {}) or {})
                display.setdefault("label", "Object target")
                advanced["Display2D"] = display
                note = (
                    "Object Target currently traces as a specular reflective proxy so source/object split "
                    "fixtures can return rays. Use a Diffuse Object row when rough/diffuse BRDF scattering is needed."
                )
                existing_note = str(advanced.get("Note", "") or "").strip()
                if note not in existing_note:
                    advanced["Note"] = f"{note} {existing_note}".strip()
                row.element = row.element or "Object target"
            elif surface_type == DIFFUSE_OBJECT_SURFACE:
                display = dict(advanced.get("Display2D", {}) or {})
                display.setdefault("label", "Diffuse object")
                advanced["Display2D"] = display
                advanced[DIFFUSE_SCATTER_ADVANCED_ATTR] = _normalize_diffuse_scatter_settings(
                    advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR, DIFFUSE_SCATTER_DEFAULT_SETTINGS)
                )
                note = (
                    "Diffuse Object spawns deterministic built-in scatter branches in Non-Sequential Preview. "
                    "Use Diffuse/BRDF settings to control model, reflectance, samples, scatter cone, and target guidance."
                )
                existing_note = str(advanced.get("Note", "") or "").strip()
                if note not in existing_note:
                    advanced["Note"] = f"{note} {existing_note}".strip()
                row.element = row.element or "Diffuse object"
            else:
                display = dict(advanced.get("Display2D", {}) or {})
                if display.get("label") in {"Object target", "Diffuse object"}:
                    display.pop("label", None)
                if display:
                    advanced["Display2D"] = display
                else:
                    advanced.pop("Display2D", None)
                advanced.pop(DIFFUSE_SCATTER_ADVANCED_ATTR, None)
            row.advanced = advanced
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == BEAM_SPLITTER_SURFACE:
            row.name = "50/50 Beam Splitter" if row.name in {"", "Surface", "Standard", "Aperture", "Mirror", "Object target"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            row.rc = 0.0
            if abs(row.tilt_x) < 1e-9 and abs(row.tilt_y) < 1e-9 and abs(row.tilt_z) < 1e-9:
                row.tilt_x = 45.0
            advanced = dict(row.advanced or {})
            splitter_settings = _normalize_beam_splitter_settings(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR))
            advanced[BEAM_SPLITTER_ADVANCED_ATTR] = splitter_settings
            advanced["Coating"] = _beam_splitter_coating_for_settings(splitter_settings, advanced.get("Coating"))
            note = (
                "Beam Splitter rows spawn deterministic reflected/transmitted paths in Non-Sequential Preview. "
                "Use Glass + Thickness plus a following rear AIR surface for finite plate deviation; "
                "use the same rear TiltX for a parallel plate."
            )
            existing_note = str(advanced.get("Note", "") or "").strip()
            if note not in existing_note:
                advanced["Note"] = f"{note} {existing_note}".strip()
            row.advanced = advanced
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Aperture":
            row.name = "Aperture"
            row.glass = "AIR"
            row.rc = 0.0
            row.diameter = max(0.1, min(float(self._current_aperture_value()), fallback_diameter))
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Thin Lens":
            row.name = "Thin Lens" if row.name in {"", "Surface", "Standard"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            if abs(row.rc) < 1e-9:
                row.rc = 100.0
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Grating":
            row.name = "Grating" if row.name in {"", "Surface", "Standard"} else row.name
            row.rc = 0.0
            if abs(row.diff_ord) < 1e-9:
                row.diff_ord = 1.0
            if abs(row.grating_d) < 1e-9:
                row.grating_d = 1.0
            self._clear_disabled_surface_type_fields(row)
            return

        if surface_type == "Standard":
            row.name = "Surface" if row.name in {"", "Mirror", "Object target", "Diffuse object", "Aperture", "Thin Lens", "Grating", "50/50 Beam Splitter"} else row.name
            if row.glass == "MIRROR":
                row.glass = "AIR"
            row.advanced = dict(row.advanced or {})
            row.advanced.pop(BEAM_SPLITTER_ADVANCED_ATTR, None)
            row.advanced.pop(DIFFUSE_SCATTER_ADVANCED_ATTR, None)
        self._clear_disabled_surface_type_fields(row)

    def _clear_disabled_surface_type_fields(self, row: SurfaceRow) -> None:
        disabled = (set(FIELDS) | set(GRATING_SETTING_FIELDS)) - self._surface_type_enabled_fields(row.surface)
        if "glass" in disabled:
            row.glass = "MIRROR" if row.surface in REFLECTIVE_PROXY_SURFACES else "AIR"
        numeric_attrs = {
            "rc": "rc",
            "k": "k",
            "axicon": "axicon",
            "diff_ord": "diff_ord",
            "grating_d": "grating_d",
            "grating_angle": "grating_angle",
            "thickness": "thickness",
            "in_diameter": "in_diameter",
            "tilt_x": "tilt_x",
            "tilt_y": "tilt_y",
            "tilt_z": "tilt_z",
            "desp_x": "desp_x",
            "desp_y": "desp_y",
            "desp_z": "desp_z",
            "axis_move": "axis_move",
        }
        for field, attr in numeric_attrs.items():
            if field in disabled:
                setattr(row, attr, 0.0)

    @staticmethod
    def _row_has_optimization(row: SurfaceRow) -> bool:
        return row.optimize_rc or row.optimize_thickness or bool(_row_native_variable_names(row))

    @staticmethod
    def _row_native_variable_enabled(row: SurfaceRow, parameter: str) -> bool:
        return any(
            _native_variable_matches(candidate, parameter)
            for candidate in _row_native_variable_names(row)
        )

    @classmethod
    def _variable_enabled_for_row(cls, row: SurfaceRow, spec) -> bool:
        return bool(spec.is_enabled(row) or cls._row_native_variable_enabled(row, spec.parameter))

    @classmethod
    def _optimization_marker_fields_for_row(cls, row: SurfaceRow) -> tuple[str, ...]:
        marker_fields: list[str] = []
        for field in FIELDS:
            spec = VARIABLE_REGISTRY.get(field)
            if spec is None or not spec.is_supported(row):
                continue
            if cls._variable_enabled_for_row(row, spec):
                marker_fields.append(field)
        return tuple(marker_fields)

    @staticmethod
    def _remove_native_variable_from_row(row: SurfaceRow, parameter: str) -> None:
        names = [
            candidate
            for candidate in _row_native_variable_names(row)
            if not _native_variable_matches(candidate, parameter)
        ]
        row.advanced = dict(row.advanced or {})
        if names:
            row.advanced["Var"] = names
        else:
            row.advanced.pop("Var", None)
        bounds = row.advanced.get("VarBounds")
        if isinstance(bounds, dict):
            for key in list(bounds):
                if _native_variable_matches(key, parameter):
                    bounds.pop(key, None)
            if bounds:
                row.advanced["VarBounds"] = bounds
            else:
                row.advanced.pop("VarBounds", None)

    def toggle_current_optimization_cell(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        enabled = self._variable_enabled_for_row(row, spec)
        spec.set_enabled(row, not enabled)
        if enabled:
            self._remove_native_variable_from_row(row, spec.parameter)
        self._sync_table()
        self._commit_history_capture()
        self.refresh_plot()
        self._cleanup_current_popup_menu()

    def toggle_current_tolerance_compensator(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None or not self._variable_enabled_for_row(row, spec):
            return
        enabled = self._tolerance_variable_compensator_enabled(
            OpticalVariable(index, spec.parameter, 0.0, 1.0, name=f"{row.name} {spec.label}")
        )
        self._begin_history_capture()
        self.set_tolerance_compensator_enabled(index, spec.parameter, not enabled)
        self._commit_history_capture()
        role = "compensator" if not enabled else "tolerance-only"
        self.append_progress(f"Row {index} {spec.label} set to {role}.")
        self._cleanup_current_popup_menu()

    def edit_current_bounds(self) -> None:
        self._main_optimization_panel().edit_current_bounds()

    def _show_centered_dialog(self, dialog: tk.Toplevel) -> None:
        def place_dialog() -> None:
            if not dialog.winfo_exists():
                return
            dialog.update_idletasks()
            screen_width = max(dialog.winfo_screenwidth(), 1)
            screen_height = max(dialog.winfo_screenheight(), 1)
            # Cap to the usable screen so a tall dialog never grows past the edges or tucks its
            # title under a top panel bar (e.g. the AGS bar). A dialog whose content exceeds this
            # must scroll its own body -- see the Advanced Surface editor's scrollable tabs.
            max_width = max(screen_width - 80, 480)
            max_height = max(screen_height - 120, 320)
            dialog_width = min(max(dialog.winfo_reqwidth(), dialog.winfo_width(), 1), max_width)
            dialog_height = min(max(dialog.winfo_reqheight(), dialog.winfo_height(), 1), max_height)
            pos_x = max((screen_width - dialog_width) // 2, 0)
            pos_y = max((screen_height - dialog_height) // 2, 40)  # never tuck the title under a top bar
            dialog.geometry(f"{dialog_width}x{dialog_height}+{pos_x}+{pos_y}")

        place_dialog()
        dialog.deiconify()
        dialog.lift()
        dialog.focus_force()
        dialog.after_idle(place_dialog)
        dialog.after(80, place_dialog)

    @staticmethod

    def open_paraxial_matrix_report(self) -> None:
        self._main_paraxial_analysis_dialogs().open_paraxial_matrix_report()

    def _main_paraxial_analysis_dialogs(self) -> MainParaxialAnalysisDialogs:
        dialog = self.__dict__.get("_main_paraxial_analysis_dialogs_instance")
        if dialog is None:
            dialog = MainParaxialAnalysisDialogs(self, short_error_message=_short_error_message)
            self._main_paraxial_analysis_dialogs_instance = dialog
        return dialog

    def open_gaussian_beam_report(self) -> None:
        self._main_paraxial_analysis_dialogs().open_gaussian_beam_report()

    def clear_current_bounds(self) -> None:
        if self.current_menu_row_id is None or self.current_menu_field is None:
            return
        index = self._table_item_row_index(self.current_menu_row_id)
        if index is None:
            return
        row = self.rows[index]
        spec = self._variable_spec_for_field(self.current_menu_field)
        if spec is None:
            return
        self._begin_history_capture()
        spec.set_bounds(row, None)
        self._commit_history_capture()
        self.append_progress(f"Bounds cleared for row {index} {spec.label}.")
        self._cleanup_current_popup_menu()


    def clear_optimization_marks(self) -> None:
        for row in self.rows:
            row.optimize_rc = False
            row.optimize_thickness = False
            row.advanced = dict(row.advanced or {})
            row.advanced.pop("Var", None)
            row.advanced.pop("VarBounds", None)
        self._sync_table()
