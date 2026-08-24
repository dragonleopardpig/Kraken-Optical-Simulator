from __future__ import annotations

import tkinter as tk

from KrakenOS.UI.services.open3d_live_refresh import MAIN_PANEL_LIVE_REFRESH_DELAY_MS
from KrakenOS.UI.widgets import bind_entry_commit


_PROTECTED_GLOBALS = {
    "LayoutShellControlsMixin",
    "_PROTECTED_GLOBALS",
    "_sync_layout_globals",
}


def _sync_layout_globals(source: dict[str, object]) -> None:
    target = globals()
    for name, value in source.items():
        if name.startswith("__") or name in _PROTECTED_GLOBALS:
            continue
        target[name] = value


class LayoutShellControlsMixin:
    def _main_trace_display_controls_panel(self) -> MainTraceDisplayControlsPanel:
        panel = self.__dict__.get("_main_trace_display_controls_panel_instance")
        if panel is None:
            panel = MainTraceDisplayControlsPanel(
                self,
                source_model_default=SOURCE_MODEL_DEFAULT,
                folded_detector_policy_default=FOLDED_DETECTOR_POLICY_DEFAULT,
                folded_detector_policy_values=FOLDED_DETECTOR_POLICY_VALUES,
                wavefront_style_default=WAVEFRONT_STYLE_DEFAULT,
                wavefront_style_values=WAVEFRONT_STYLE_VALUES,
                tolerance_compare_view_default=TOLERANCE_COMPARE_VIEW_DEFAULT,
                tolerance_compare_view_values=TOLERANCE_COMPARE_VIEW_VALUES,
                analysis_path_filter_default=ANALYSIS_PATH_FILTER_DEFAULT,
                detector_bins_default=DETECTOR_BINS_DEFAULT,
                coherent_sum_mode_default=COHERENT_SUM_MODE_DEFAULT,
                coherent_sum_mode_values=COHERENT_SUM_MODE_VALUES,
                branch_field_propagation_mm_default=BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
            )
            self._main_trace_display_controls_panel_instance = panel
        return panel

    def _build_controls_panel(self, parent) -> None:
        self._main_trace_display_controls_panel().build(parent)

    def _main_field_controls_panel(self) -> MainFieldControlsPanel:
        panel = self.__dict__.get("_main_field_controls_panel_instance")
        if panel is None:
            panel = MainFieldControlsPanel(
                self,
                field_type_values=FIELD_TYPE_CANONICAL_VALUES,
                camera_none_label=CAMERA_NONE_LABEL,
                camera_names=camera_names,
            )
            self._main_field_controls_panel_instance = panel
        return panel

    def _build_field_panel(self, parent) -> None:
        self._main_field_controls_panel().build(parent)

    def _main_source_controls_panel(self) -> MainSourceControlsPanel:
        panel = self.__dict__.get("_main_source_controls_panel_instance")
        if panel is None:
            panel = MainSourceControlsPanel(
                self,
                source_model_default=SOURCE_MODEL_DEFAULT,
                source_model_values=SOURCE_MODEL_VALUES,
                pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
                pupil_pattern_values=PUPIL_PATTERN_VALUES,
                gaussian_input_mode_default=GAUSSIAN_INPUT_MODE_DEFAULT,
                gaussian_input_mode_values=GAUSSIAN_INPUT_MODE_VALUES,
                gaussian_waist_side_default=GAUSSIAN_WAIST_SIDE_DEFAULT,
                gaussian_waist_side_values=GAUSSIAN_WAIST_SIDE_VALUES,
                source_direction_preset_values=SOURCE_DIRECTION_PRESET_VALUES,
                source_angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
                source_angular_weight_values=SOURCE_ANGULAR_WEIGHT_VALUES,
            )
            self._main_source_controls_panel_instance = panel
        return panel

    def _build_source_panel(self, parent) -> None:
        self._main_source_controls_panel().build(parent)

    def _main_analysis_toolbar_panel(self) -> MainAnalysisToolbarPanel:
        panel = self.__dict__.get("_main_analysis_toolbar_panel_instance")
        if panel is None:
            panel = MainAnalysisToolbarPanel(self)
            self._main_analysis_toolbar_panel_instance = panel
        return panel

    def _main_information_panel(self) -> MainInformationPanel:
        panel = self.__dict__.get("_main_information_panel_instance")
        if panel is None:
            panel = MainInformationPanel(self)
            self._main_information_panel_instance = panel
        return panel

    def _register_left_mode_control(
        self,
        var_name: str,
        widget,
        relevant,
        *,
        normal_state: str = "normal",
        extra_widgets=(),
        include_label: bool = True,
    ) -> None:
        if not hasattr(self, "_left_mode_controls"):
            self._left_mode_controls = []
        managed_widgets = self._left_mode_control_grid_widgets(
            widget,
            extra_widgets=extra_widgets,
            include_label=include_label,
        )
        var = getattr(self, var_name, None)
        try:
            fallback = str(var.get()) if var is not None else ""
        except Exception:
            fallback = ""
        grid_records = []
        for managed_widget in managed_widgets:
            try:
                grid_records.append((managed_widget, dict(managed_widget.grid_info())))
            except Exception:
                pass
        self._left_mode_controls.append(
            {
                "var_name": var_name,
                "widget": widget,
                "managed_widgets": managed_widgets,
                "grid_records": grid_records,
                "relevant": relevant,
                "normal_state": normal_state,
                "fallback": fallback,
            }
        )

    @staticmethod
    def _left_mode_control_grid_widgets(widget, *, extra_widgets=(), include_label: bool = True) -> list:
        managed = []

        def add(candidate) -> None:
            if candidate is not None and candidate not in managed:
                managed.append(candidate)

        add(widget)
        try:
            grid_info = widget.grid_info()
            parent = widget.master
            row = int(grid_info.get("row", 0))
            column = int(grid_info.get("column", 0))
            columnspan = int(grid_info.get("columnspan", 1))
            label_row = row - 1
        except Exception:
            row = column = label_row = -1
            columnspan = 1
            parent = None
        if include_label and parent is not None and label_row >= 0:
            wanted = set(range(column, column + max(columnspan, 1)))
            try:
                for candidate in parent.grid_slaves(row=label_row):
                    if candidate is widget:
                        continue
                    info = candidate.grid_info()
                    candidate_column = int(info.get("column", 0))
                    candidate_span = int(info.get("columnspan", 1))
                    candidate_columns = set(range(candidate_column, candidate_column + max(candidate_span, 1)))
                    if wanted & candidate_columns:
                        add(candidate)
            except Exception:
                pass
        for candidate in extra_widgets or ():
            add(candidate)
        return managed

    def _register_source_mode_controls(self, **widgets) -> None:
        if hasattr(self, "field_type_menu"):
            self._register_left_mode_control(
                "field_type_var",
                self.field_type_menu,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
                normal_state="readonly",
            )
        if hasattr(self, "field_value_entry"):
            self._register_left_mode_control(
                "field_value_var",
                self.field_value_entry,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            )
        if hasattr(self, "field_count_entry"):
            self._register_left_mode_control(
                "field_count_var",
                self.field_count_entry,
                lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            )
        self._register_left_mode_control(
            "pupil_pattern_var",
            self.pupil_pattern_menu,
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "source_radius_var",
            widgets["source_radius_entry"],
            lambda: self._current_source_model() in {
                "Collimated disk source",
                "Random circle source",
                "Random square source",
                "Random line source",
            },
        )
        self._register_left_mode_control(
            "source_cone_angle_var",
            widgets["source_cone_angle_entry"],
            lambda: self._current_source_model() in {
                SOURCE_MODEL_DEFAULT,
                "Collimated disk source",
                "Random circle source",
                "Random square source",
                "Random line source",
                "Random point cone",
            },
        )
        self._register_left_mode_control(
            "gaussian_input_mode_var",
            widgets["gaussian_input_mode_menu"],
            lambda: self._current_source_model() == "Gaussian beam",
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "gaussian_waist_radius_var",
            widgets["gaussian_waist_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == GAUSSIAN_INPUT_MODE_DEFAULT,
        )
        self._register_left_mode_control(
            "gaussian_waist_offset_var",
            widgets["gaussian_offset_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == GAUSSIAN_INPUT_MODE_DEFAULT,
        )
        self._register_left_mode_control(
            "gaussian_beam_diameter_var",
            widgets["gaussian_diameter_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
        )
        self._register_left_mode_control(
            "gaussian_full_divergence_var",
            widgets["gaussian_divergence_entry"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
        )
        self._register_left_mode_control(
            "gaussian_m2_var",
            widgets["gaussian_m2_entry"],
            lambda: self._current_source_model() == "Gaussian beam",
        )
        self._register_left_mode_control(
            "gaussian_waist_side_var",
            widgets["gaussian_waist_side_menu"],
            lambda: self._current_source_model() == "Gaussian beam" and self._current_gaussian_input_mode() == "Diameter + divergence",
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "pupil_rad_var",
            widgets["pupil_rad_entry"],
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "R-theta",
        )
        self._register_left_mode_control(
            "pupil_theta_var",
            widgets["pupil_theta_entry"],
            lambda: self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "R-theta",
        )
        self._register_left_mode_control(
            "source_power_var",
            widgets["source_power_entry"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
        )
        self._register_left_mode_control(
            "source_seed_var",
            widgets["source_seed_entry"],
            lambda: self._current_source_model() in {
                "Random circle source",
                "Random square source",
                "Random line source",
                "Random point cone",
            } or (self._current_source_model() == SOURCE_MODEL_DEFAULT and self._current_pupil_pattern_label() == "Random disk"),
        )
        for var_name, widget_name in (
            ("source_x_var", "source_x_entry"),
            ("source_y_var", "source_y_entry"),
            ("source_z_var", "source_z_entry"),
            ("source_l_var", "source_l_entry"),
            ("source_m_var", "source_m_entry"),
            ("source_n_var", "source_n_entry"),
        ):
            self._register_left_mode_control(
                var_name,
                widgets[widget_name],
                lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            )
        self._register_left_mode_control(
            "source_direction_preset_var",
            widgets["source_direction_preset_menu"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "source_angular_weight_var",
            widgets["source_angular_weight_menu"],
            lambda: self._current_source_model() in {"Random circle source", "Random square source"},
            normal_state="readonly",
        )
        self._register_left_mode_control(
            "",
            widgets["source_physical_note"],
            lambda: self._current_source_model() != SOURCE_MODEL_DEFAULT,
            include_label=False,
        )
        self._register_left_mode_control(
            "",
            widgets["source_summary_label"],
            lambda: True,
            include_label=False,
        )
        self._register_left_mode_control(
            "",
            widgets["source_manager_button"],
            lambda: True,
            include_label=False,
        )

    def _sync_left_mode_controls(self) -> None:
        controls = list(getattr(self, "_left_mode_controls", []) or [])
        if not controls:
            return
        saved = getattr(self, "_left_mode_saved_values", None)
        if saved is None:
            saved = {}
            self._left_mode_saved_values = saved
        for control in controls:
            var_name = str(control.get("var_name", ""))
            var = getattr(self, var_name, None)
            widget = control.get("widget")
            relevant = control.get("relevant")
            normal_state = str(control.get("normal_state", "normal"))
            if widget is None or not callable(relevant):
                continue
            try:
                is_relevant = bool(relevant())
            except Exception:
                is_relevant = True
            try:
                current = str(var.get())
            except Exception:
                current = ""
            if is_relevant:
                if current == "NA":
                    restored = saved.pop(var_name, str(control.get("fallback", "")))
                    if restored:
                        try:
                            var.set(restored)
                        except Exception:
                            pass
                try:
                    widget.configure(state=normal_state)
                except Exception:
                    pass
            else:
                if var is not None and current not in {"", "NA"}:
                    saved.setdefault(var_name, current)
                try:
                    widget.configure(state="disabled")
                except Exception:
                    pass
            control["visible"] = is_relevant
        self._sync_left_source_panel_layout()
        self._sync_left_field_panel_visibility()
        self._reflow_left_mode_controls()
        self._sync_field_sample_count_state()

    def _sync_left_source_panel_layout(self) -> None:
        is_default_source = self._current_source_model() == SOURCE_MODEL_DEFAULT
        span = 1 if is_default_source else 2
        for widget in (getattr(self, "source_model_label", None), getattr(self, "source_model_menu", None)):
            if widget is None:
                continue
            try:
                widget.grid_configure(columnspan=span)
            except Exception:
                pass

    def _sync_left_field_panel_visibility(self) -> None:
        field_panel = getattr(self, "field_panel", None)
        if field_panel is None:
            return
        try:
            if self._current_source_model() == SOURCE_MODEL_DEFAULT:
                field_panel.grid()
            else:
                field_panel.grid_remove()
        except Exception:
            pass

    def _reflow_left_mode_controls(self) -> None:
        controls = list(getattr(self, "_left_mode_controls", []) or [])
        if not controls:
            return
        managed_widgets = {
            widget
            for control in controls
            for widget in (control.get("managed_widgets") or ())
            if widget is not None
        }
        parent_controls: dict[tk.Widget, list[dict[str, object]]] = {}
        for index, control in enumerate(controls):
            visible = bool(control.get("visible", True))
            records = []
            parent = None
            for widget, original_info in control.get("grid_records", []) or []:
                if widget is None or not isinstance(original_info, dict) or not original_info:
                    continue
                widget_parent = getattr(widget, "master", None)
                if widget_parent is None:
                    continue
                if parent is None:
                    parent = widget_parent
                if widget_parent is not parent:
                    continue
                records.append((widget, dict(original_info)))
            if parent is not None and records:
                parent_controls.setdefault(parent, []).append(
                    {
                        "index": index,
                        "records": records,
                        "visible": visible,
                    }
                )

        for parent, panel_controls in parent_controls.items():
            fixed_cells: set[tuple[int, int]] = set()
            try:
                children = list(parent.grid_slaves())
            except Exception:
                children = []
            for child in children:
                if child in managed_widgets:
                    continue
                try:
                    info = child.grid_info()
                    row = int(info.get("row", 0))
                    column = int(info.get("column", 0))
                    rowspan = max(int(info.get("rowspan", 1)), 1)
                    columnspan = max(int(info.get("columnspan", 1)), 1)
                except Exception:
                    continue
                for rr in range(row, row + rowspan):
                    for cc in range(column, column + columnspan):
                        fixed_cells.add((rr, cc))

            items = []
            for control in panel_controls:
                records = list(control.get("records") or [])
                if not bool(control.get("visible", True)):
                    for widget, _info in records:
                        try:
                            widget.grid_remove()
                        except Exception:
                            pass
                    continue

                parsed = []
                for widget, info in records:
                    try:
                        row = int(info.get("row", 0))
                        column = int(info.get("column", 0))
                        rowspan = max(int(info.get("rowspan", 1)), 1)
                        columnspan = max(int(info.get("columnspan", 1)), 1)
                    except Exception:
                        row = column = 0
                        rowspan = columnspan = 1
                    parsed.append(
                        {
                            "widget": widget,
                            "info": info,
                            "row": row,
                            "column": column,
                            "rowspan": rowspan,
                            "columnspan": columnspan,
                        }
                    )
                if not parsed:
                    continue

                base_row = min(int(record["row"]) for record in parsed)
                base_column = min(int(record["column"]) for record in parsed)
                max_column = max(int(record["column"]) + int(record["columnspan"]) for record in parsed)
                if any(int(record["columnspan"]) > 1 for record in parsed):
                    kind = "wide"
                elif max_column - base_column > 1:
                    kind = "multi"
                else:
                    kind = "single"
                height = max(
                    int(record["row"]) - base_row + int(record["rowspan"])
                    for record in parsed
                )
                items.append(
                    {
                        "index": int(control.get("index", 0)),
                        "records": parsed,
                        "base_row": base_row,
                        "base_column": base_column,
                        "kind": kind,
                        "height": max(height, 1),
                    }
                )

            if not items:
                continue

            items.sort(key=lambda item: (int(item["base_row"]), int(item["base_column"]), int(item["index"])))
            occupied = set(fixed_cells)
            first_row = min(int(item["base_row"]) for item in items)
            cursor_row = first_row

            def cells_for_item(item: dict[str, object], target_row: int, target_column: int) -> list[tuple[int, int]]:
                kind = str(item["kind"])
                cells: list[tuple[int, int]] = []
                for record in item["records"]:
                    row_delta = int(record["row"]) - int(item["base_row"])
                    rowspan = int(record["rowspan"])
                    if kind == "wide":
                        column = 0
                        columnspan = 2
                    elif kind == "multi":
                        column = int(record["column"]) - int(item["base_column"])
                        columnspan = int(record["columnspan"])
                    else:
                        column = target_column
                        columnspan = 1
                    for rr in range(target_row + row_delta, target_row + row_delta + rowspan):
                        for cc in range(column, column + columnspan):
                            cells.append((rr, cc))
                return cells

            def first_available_slot(item: dict[str, object], start_row: int) -> tuple[int, int]:
                columns = (0, 1) if str(item["kind"]) == "single" else (0,)
                target_row = max(start_row, first_row)
                while target_row < first_row + 200:
                    for target_column in columns:
                        cells = cells_for_item(item, target_row, target_column)
                        if not any(cell in occupied for cell in cells):
                            return target_row, target_column
                    target_row += 1
                return target_row, 0

            for item in items:
                target_row, target_column = first_available_slot(item, cursor_row)
                occupied.update(cells_for_item(item, target_row, target_column))
                for record in item["records"]:
                    info = dict(record["info"])
                    row_delta = int(record["row"]) - int(item["base_row"])
                    info["row"] = target_row + row_delta
                    kind = str(item["kind"])
                    if kind == "wide":
                        info["column"] = 0
                        info["columnspan"] = 2
                    elif kind == "multi":
                        info["column"] = int(record["column"]) - int(item["base_column"])
                    else:
                        info["column"] = target_column
                        info["columnspan"] = 1
                        info["padx"] = (8, 0) if target_column else (0, 0)
                    try:
                        record["widget"].grid(**info)
                    except Exception:
                        pass
                if str(item["kind"]) != "single":
                    cursor_row = max(cursor_row, target_row + int(item["height"]))

    def _left_mode_text(self, var_name: str, fallback: str = "") -> str:
        var = getattr(self, var_name, None)
        try:
            text = str(var.get()).strip() if var is not None else str(fallback)
        except Exception:
            text = str(fallback)
        if text == "NA":
            saved = getattr(self, "_left_mode_saved_values", {}) or {}
            text = str(saved.get(var_name, fallback)).strip()
        return text

    def _main_atmosphere_panel(self) -> MainAtmospherePanel:
        panel = self.__dict__.get("_main_atmosphere_panel_instance")
        if panel is None:
            panel = MainAtmospherePanel(
                self,
                atmos_plot_mode_default=ATMOS_PLOT_MODE_DEFAULT,
                atmos_plot_mode_values=ATMOS_PLOT_MODE_VALUES,
            )
            self._main_atmosphere_panel_instance = panel
        return panel

    def _build_atmosphere_panel(self, parent) -> None:
        self._main_atmosphere_panel().build_hidden_panel(parent)

    def open_atmosphere_settings_dialog(self) -> None:
        self._main_atmosphere_panel().open_settings_dialog()

    def _close_atmosphere_settings_dialog(self) -> None:
        self._main_atmosphere_panel().close_settings_dialog()

    def _on_control_stack_configure(self, _event=None) -> None:
        if not hasattr(self, "control_canvas"):
            return
        self.control_canvas.configure(scrollregion=self.control_canvas.bbox("all"))

    def _on_control_canvas_configure(self, event=None) -> None:
        if not hasattr(self, "control_canvas") or not hasattr(self, "control_stack_window"):
            return
        width = self.control_canvas.winfo_width() if event is None else int(event.width)
        self.control_canvas.itemconfigure(self.control_stack_window, width=max(width, 1))

    def _on_left_panel_mousewheel(self, event=None):
        canvas = getattr(self, "control_canvas", None)
        if canvas is None or event is None:
            return None
        try:
            pointer_x = canvas.winfo_pointerx()
            pointer_y = canvas.winfo_pointery()
            canvas_x = canvas.winfo_rootx()
            canvas_y = canvas.winfo_rooty()
            inside_canvas = (
                canvas_x <= pointer_x < canvas_x + canvas.winfo_width()
                and canvas_y <= pointer_y < canvas_y + canvas.winfo_height()
            )
        except Exception:
            return None
        if not inside_canvas:
            return None
        try:
            bbox = canvas.bbox("all")
            if not bbox or int(bbox[3] - bbox[1]) <= canvas.winfo_height():
                return "break"
        except Exception:
            pass

        delta = 0
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            wheel_delta = int(getattr(event, "delta", 0) or 0)
            if wheel_delta:
                delta = -max(1, abs(wheel_delta) // 120) if wheel_delta > 0 else max(1, abs(wheel_delta) // 120)
        if delta:
            try:
                canvas.yview_scroll(delta, "units")
            except Exception:
                return None
            return "break"
        return None

    def _update_field_status_hint(self) -> None:
        if not hasattr(self, "status_hint_var"):
            return
        note = self.field_mode_note_var.get().strip() if hasattr(self, "field_mode_note_var") else ""
        warning = self.field_warning_var.get().strip() if hasattr(self, "field_warning_var") else ""
        summary = self.field_summary_var.get().strip() if hasattr(self, "field_summary_var") else ""
        summary = summary.replace("\n", " | ")
        sampling_note = ""
        try:
            if self._current_source_model() == SOURCE_MODEL_DEFAULT and not self._field_sampling_is_active():
                basis, unit, _span = self._field_sampling_basis_span()
                sampling_note = f"Field samples: NA while {basis} span is 0 {unit}."
        except Exception:
            sampling_note = ""
        parts = [part for part in (note, sampling_note, warning, summary) if part]
        self.status_hint_var.set("  ||  ".join(parts))

    def _main_optimization_panel(self) -> MainOptimizationPanel:
        panel = self.__dict__.get("_main_optimization_panel_instance")
        if panel is None:
            panel = MainOptimizationPanel(self, operand_specs=OPERAND_REGISTRY.values())
            self._main_optimization_panel_instance = panel
        return panel

    def _build_optimization_panel(self, parent) -> None:
        self._main_optimization_panel().build(parent)

    def _build_results_panel(self, parent) -> None:
        self._main_information_panel().build(parent)

    def _bind_deferred_refresh(self, widget: tk.Widget) -> None:
        bind_entry_commit(
            widget,
            self._mark_plot_update_pending,
            on_focus_in=self._begin_history_capture,
        )

    def _bind_deferred_manual_update(self, widget: tk.Widget, *, sync_fields: bool = False) -> None:
        def _on_commit(_event=None):
            if sync_fields:
                self._sync_object_controls()
            else:
                self._sync_left_mode_controls()
            self._mark_plot_update_pending()

        bind_entry_commit(widget, _on_commit, on_focus_in=self._begin_history_capture)

    def _invalidate_preview_scene_trace(self, reason: str = "") -> None:
        self._preview_scene_trace_dirty = True
        self._last_preview_trace_signature = None
        if reason:
            try:
                self.append_debug(f"Preview trace invalidated: {reason}")
            except Exception:
                pass

    def _invalidate_optical_solid_face_assignment_trace(
        self,
        row_index: int | None = None,
        face_id: str = "",
        function: str = "",
    ) -> None:
        reason_bits = ["CAD/STL face assignment"]
        if row_index is not None:
            try:
                reason_bits.append(f"S{int(row_index)}")
            except Exception:
                pass
        face_text = str(face_id or "").strip()
        if face_text:
            reason_bits.append(face_text)
        function_text = _optical_solid_face_function_display(function) if function else ""
        if function_text:
            reason_bits.append(function_text)
        self._invalidate_preview_scene_trace(" ".join(reason_bits))
        self.last_system = None
        self.last_rays = None
        self._last_scene_bundle = None
        self._last_live_step_overlay_trace_rows = None
        self._last_live_step_overlay_trace_records = []
        self._last_live_step_overlay_scene_bundle = None
        self._live_step_overlay_trace_plan_cache = {}

    def _mark_plot_update_pending(self, _event=None) -> None:
        self._commit_history_capture()
        self._invalidate_preview_scene_trace()
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set("Display settings changed. Click Update.")
        self._schedule_open3d_live_refresh("left panel edit")

    def _schedule_open3d_live_refresh(self, reason: str, *, delay_ms: int = MAIN_PANEL_LIVE_REFRESH_DELAY_MS) -> bool:
        inspector = getattr(self, "_three_d_inspector", None)
        if inspector is None:
            return False
        try:
            if not inspector.winfo_exists():
                self._three_d_inspector = None
                return False
        except Exception:
            self._three_d_inspector = None
            return False
        try:
            return bool(inspector.schedule_live_refresh(reason, delay_ms=delay_ms))
        except Exception as exc:
            self.append_debug(f"Open 3D live refresh scheduling failed: {exc}")
            return False

    def _on_display_plane_changed(self, _event=None) -> None:
        self._commit_history_capture()
        if hasattr(self, "display_orientation_var"):
            raw = str(self.display_orientation_var.get()).strip()
            normalized = "All" if raw == "All" else normalize_projection_plane(raw)
            self.display_orientation_var.set(normalized)
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set("2D plane changed. Refreshing layout.")
        try:
            self.after_idle(self.refresh_plot)
        except Exception:
            self._mark_plot_update_pending()

    def _on_projection_display_mode_changed(self, _event=None) -> None:
        self._commit_history_capture()
        if hasattr(self, "projection_display_mode_var"):
            self.projection_display_mode_var.set(PROJECTION_MODE_FULL_3D)
        self._sync_trace_state_badge()
        if hasattr(self, "status_var"):
            self.status_var.set("2D projection is always Full 3D. Refreshing layout.")
        try:
            self.after_idle(self.refresh_plot)
        except Exception:
            self._mark_plot_update_pending()

    def _apply_operand_control_visibility(self, label: str) -> None:
        spec = self._merit_spec_for_label(label)
        if spec is None:
            return
        visible_controls = set(spec.controls)
        widget_groups = self.operand_control_widgets.get(label, {})
        for control_name, widgets in widget_groups.items():
            for widget in widgets:
                if control_name in visible_controls:
                    widget.grid()
                else:
                    widget.grid_remove()

    def _update_operand_setup_visibility(self) -> None:
        if not hasattr(self, "merit_mode_list"):
            return
        self._commit_history_capture()
        selected = {self.merit_mode_list.get(i) for i in self.merit_mode_list.curselection()}
        for label, frame in self.operand_setup_frames.items():
            visible = label in selected
            if visible:
                frame.grid()
            else:
                frame.grid_remove()

    def _pane_present(self, widget: tk.Widget) -> bool:
        if not hasattr(self, "main_pane"):
            return False
        widget_name = str(widget)
        return widget_name in {str(pane) for pane in self.main_pane.panes()}

    def toggle_left_sidebar(self) -> None:
        if not hasattr(self, "left_sidebar_host"):
            return
        if self._pane_present(self.left_sidebar_host):
            self.main_pane.forget(self.left_sidebar_host)
            self.left_restore_frame.grid()
            self._left_sidebar_collapsed = True
            message = "Left controls hidden."
        else:
            self.left_restore_frame.grid_remove()
            self.main_pane.insert(0, self.left_sidebar_host, weight=0)
            self._left_sidebar_collapsed = False
            message = "Left controls shown."
        self._initial_layout_passes = 40
        self._set_initial_pane_layout(force=True)
        if hasattr(self, "status_var"):
            self.status_var.set(message)

    def toggle_right_sidebar(self) -> None:
        if not hasattr(self, "right_sidebar_host"):
            return
        if self._pane_present(self.right_sidebar_host):
            self.main_pane.forget(self.right_sidebar_host)
            self.right_restore_frame.grid()
            self._right_sidebar_collapsed = True
            message = "Right panels hidden."
        else:
            self.right_restore_frame.grid_remove()
            self.main_pane.add(self.right_sidebar_host, weight=1)
            self._right_sidebar_collapsed = False
            message = "Right panels shown."
        self._initial_layout_passes = 40
        self._set_initial_pane_layout(force=True)
        if hasattr(self, "status_var"):
            self.status_var.set(message)

    def _set_initial_pane_layout(self, force: bool = False) -> None:
        self.update_idletasks()
        total_width = self.main_pane.winfo_width()
        if total_width < 500:
            self.after(100, self._set_initial_pane_layout)
            return
        try:
            left_visible = hasattr(self, "left_sidebar_host") and self._pane_present(self.left_sidebar_host)
            right_visible = hasattr(self, "right_sidebar_host") and self._pane_present(self.right_sidebar_host)
            left_width = max(240, min(360, int(total_width * 0.20)))
            right_width = max(300, min(460, int(total_width * 0.23)))
            if left_visible and right_visible:
                center_min = max(360, int(total_width * 0.42))
                side_total = left_width + right_width
                side_limit = max(240, total_width - center_min)
                if side_total > side_limit:
                    scale = max(0.35, side_limit / max(side_total, 1))
                    left_width = max(180, int(left_width * scale))
                    right_width = max(220, int(right_width * scale))
                self.main_pane.sashpos(0, left_width)
                self.main_pane.sashpos(1, max(left_width + 250, total_width - right_width))
            elif left_visible:
                self.main_pane.sashpos(0, left_width)
            elif right_visible:
                self.main_pane.sashpos(0, max(250, total_width - right_width))

            if hasattr(self, "center_panel"):
                total_height = self.center_panel.winfo_height()
                if total_height >= 360:
                    self.center_panel.sashpos(0, int(total_height * 0.36))
            if not force:
                self._initial_layout_passes += 1
        except Exception:
            self.after(100, self._set_initial_pane_layout)

    def _maybe_refresh_initial_pane_layout(self, _event=None) -> None:
        if self._initial_layout_passes >= 40:
            return
        self.after(100, self._set_initial_pane_layout)

    def _layout_menu_category(self, name: str) -> str:
        return layout_menu_category(name, self.layout_files.get(name))

    def _example_menu_category(self, name: str) -> str:
        return example_menu_category(name, self.example_files.get(name))

    def _refresh_selector_menus(self) -> None:
        if self.layout_menu is not None:
            self.layout_menu.delete(0, "end")
            self._layout_category_menus = []
            if self.layout_names:
                categories = {category: [] for category in LAYOUT_CATEGORY_ORDER}
                for name in self.layout_names:
                    category = self._layout_menu_category(name)
                    categories.setdefault(category, []).append(name)
                for category, names in categories.items():
                    if not names:
                        continue
                    submenu = tk.Menu(self.layout_menu, tearoff=0)
                    self._layout_category_menus.append(submenu)
                    for name in names:
                        submenu.add_command(
                            label=name,
                            command=lambda value=name: self.load_layout_by_name(value),
                        )
                    self.layout_menu.add_cascade(label=category, menu=submenu)
            else:
                self.layout_menu.add_command(label="No common layouts found", state="disabled")

        self._refresh_insert_component_menu()

        if self.machine_vision_menu is not None:
            self.machine_vision_menu.delete(0, "end")
            if self.machine_vision_names:
                for name in self.machine_vision_names:
                    self.machine_vision_menu.add_command(
                        label=name,
                        command=lambda value=name: self.load_layout_by_name(value),
                    )
            else:
                self.machine_vision_menu.add_command(label="No machine-vision layouts found", state="disabled")

        if self.example_menu is not None:
            self.example_menu.delete(0, "end")
            self._example_category_menus = []
            self._zemax_example_category_menus = []
            if self.example_names:
                categories = {category: [] for category in EXAMPLE_CATEGORY_ORDER}
                for name in self.example_names:
                    category = self._example_menu_category(name)
                    categories.setdefault(category, []).append(name)
                for category, names in categories.items():
                    if not names:
                        continue
                    submenu = tk.Menu(self.example_menu, tearoff=0)
                    self._example_category_menus.append(submenu)
                    for name in names:
                        submenu.add_command(
                            label=name,
                            command=lambda value=name: self.load_example_by_name(value),
                        )
                    self.example_menu.add_cascade(label=category, menu=submenu)
            if self.example_names and self.zemax_example_files:
                self.example_menu.add_separator()
            if self.zemax_example_files:
                self._refresh_zemax_example_menu(self.example_menu)
            elif not self.example_names:
                self.example_menu.add_command(label="No examples found", state="disabled")

    def _insertable_common_layout_names(self) -> list[str]:
        names: list[str] = []
        for name in self.layout_names:
            path = self.layout_files.get(name)
            if path is None:
                continue
            info: dict[str, object] = {}
            try:
                info = _load_python_data(path)
            except Exception:
                info = {}
            if self._is_insertable_common_layout(name, [], info):
                names.append(name)
        return sorted(names, key=str.lower)

    def _refresh_insert_component_menu(self) -> None:
        menu = self._insert_component_menu
        if menu is None:
            return
        menu.delete(0, "end")
        names = self._insertable_common_layout_names()
        if not names:
            menu.add_command(label="No insertable common components found", state="disabled")
            return
        for name in names:
            menu.add_command(
                label=name,
                command=lambda value=name: self.insert_layout_component_by_name(value),
            )

    def _refresh_zemax_example_menu(self, parent_menu: tk.Menu) -> None:
        zemax_menu = tk.Menu(parent_menu, tearoff=0)
        self._zemax_example_category_menus.append(zemax_menu)
        if not self.zemax_example_files:
            zemax_menu.add_command(label=f"No .zmx files found in {ZEMAX_ATTACHMENT_DIR}", state="disabled")
            parent_menu.add_cascade(label="Zemax Prescriptions (attachment)", menu=zemax_menu)
            return

        # Build a tree mirroring the on-disk directory structure so deep
        # collections (e.g. Sequential/<category>, Short course/<category>)
        # nest as browsable submenus instead of a flat list of long
        # slash-joined group labels. Loose files at the zemax root live under
        # a "Top Level" submenu so they don't crowd out the category folders.
        tree: dict[str, object] = {"dirs": {}, "files": []}
        for label, path in self.zemax_example_files.items():
            try:
                relative = path.relative_to(ZEMAX_ATTACHMENT_DIR)
            except ValueError:
                relative = Path(label)
            parts = relative.parts
            if len(parts) <= 1:
                node = tree["dirs"].setdefault("Top Level", {"dirs": {}, "files": []})
                node["files"].append((relative.name, path))
                continue
            node = tree
            for part in parts[:-1]:
                node = node["dirs"].setdefault(part, {"dirs": {}, "files": []})
            node["files"].append((parts[-1], path))

        self._populate_zemax_tree_menu(zemax_menu, tree)
        parent_menu.add_cascade(label="Zemax Prescriptions (attachment)", menu=zemax_menu)

    def _populate_zemax_tree_menu(self, menu: tk.Menu, node: dict[str, object]) -> None:
        """Recursively fill ``menu`` from a {dirs, files} tree node.

        Directories come first (as cascading submenus, "Top Level" floated to
        the top), then files as load commands -- both alphabetised.
        """
        for dir_name in sorted(node["dirs"], key=lambda value: (value != "Top Level", value.lower())):
            submenu = tk.Menu(menu, tearoff=0)
            self._zemax_example_category_menus.append(submenu)
            self._populate_zemax_tree_menu(submenu, node["dirs"][dir_name])
            menu.add_cascade(label=dir_name, menu=submenu)
        for item_label, path in sorted(node["files"], key=lambda item: item[0].lower()):
            menu.add_command(
                label=item_label,
                command=lambda value=path: self.load_zemax_example_file(value),
            )

    def load_layouts(self) -> None:
        discovered = _discover_layouts(LAYOUTS_DIR, default_layout_title=DEFAULT_LAYOUT_TITLE)
        self.layout_files = dict(discovered.layout_files)
        self.machine_vision_files = dict(discovered.machine_vision_files)
        self.layout_names = list(discovered.layout_names)
        self.machine_vision_names = list(discovered.machine_vision_names)
        self.layout_var.set("Common Optical Layout")
        self.machine_vision_var.set("Machine Vision Lens")
        self._refresh_selector_menus()

    def load_examples(self) -> None:
        discovered = _discover_examples(EXAMPLES_DIR, ZEMAX_TESTING_DIR)
        self.example_files = dict(discovered.example_files)
        self.example_names = list(discovered.example_names)
        self.zemax_example_files = dict(discovered.zemax_example_files)
        self.example_var.set("Examples")
        self._refresh_selector_menus()

    def set_analysis_mode(self, mode: str) -> None:
        self.selected_analysis_modes = [] if mode == "none" else [mode]
        self.analysis_mode = self.selected_analysis_modes[0] if self.selected_analysis_modes else "none"
        self.secondary_analysis_mode = None
        self._sync_analysis_mode_buttons()
        mode_label_map = {
            "none": "2D",
            "spot": "Spot",
            "psf": "PSF",
            "psf_map": "PSFMap",
            "rms": "RMS",
            "field_curvature": "FldCurv",
            "distortion": "Dist",
            "relative_illumination": "Illum",
            "polarization": "Polarization",
            "lateral_color": "LatClr",
            "detector_map": "DetMap",
            "coherent_detector": "CohDet",
            "branch_field": "BField",
            "diffraction_detector": "Diffr",
            "field_map": "FieldMap",
            "illum_map": "IllumMap",
            "wavefront_map": "WfeMap",
            "atmosphere": "Atmos",
            "pupil": "Pupil",
            "seidel": "Seidel",
            "wavefront": "Wavefront",
            "zernike": "Zernike",
            "interferogram": "Interferogram",
            "tolerance_compare": "TolCmp",
            "mtf": "MTF",
        }
        mode_label = mode_label_map.get(mode, mode or "2D")
        if hasattr(self, "status_var"):
            self.status_var.set(f"Analysis mode set to {mode_label}. Click Update.")
        self.append_progress(f"Mode selected: {mode_label} (pending update).")

    def set_layout_preview_mode(self, mode: str) -> None:
        self.layout_preview_mode = "none"
        if hasattr(self, "layout_preview_mode_var"):
            self.layout_preview_mode_var.set(self.layout_preview_mode)
        mode_label = "2D"
        if hasattr(self, "status_var"):
            self.status_var.set(f"Layout mode set to {mode_label}. Click Update.")
        self.append_progress(f"Layout mode selected: {mode_label} (pending update).")

    def toggle_layout_2d(self) -> None:
        var = self.__dict__.get("show_layout_2d_var")
        if var is not None and hasattr(var, "get"):
            try:
                self.show_layout_2d = bool(var.get())
            except Exception:
                self.show_layout_2d = not bool(self.__dict__.get("show_layout_2d", True))
        else:
            self.show_layout_2d = not bool(self.__dict__.get("show_layout_2d", True))
        state = "shown" if self.show_layout_2d else "hidden"
        # Defer the replot to the Update button, matching set_analysis_mode /
        # set_layout_preview_mode -- toggling the checkbox only records the intent.
        if hasattr(self, "status_var"):
            self.status_var.set(f"2D layout {state}. Click Update.")
        self.append_progress(f"2D layout {state} (pending update).")

    def _requested_trace_mode(self) -> str:
        trace_mode_var = self.__dict__.get("trace_mode_var")
        if trace_mode_var is None:
            value = str(self.__dict__.get("trace_mode", "Auto")).strip()
        else:
            value = str(trace_mode_var.get()).strip()
        if value in {"Auto", "Sequential", "Folded Preview", "Non-Sequential Preview"}:
            return value
        return "Auto"

    def _resolved_trace_mode(self, *, system=None) -> dict[str, object]:
        requested = self._requested_trace_mode()
        can_folded = self._can_build_folded_layout() and bool(self.rows)
        intent = resolve_trace_intent(
            self.rows,
            {
                "source_model": self._current_source_model(),
                "scene_sources": getattr(self, "layout_scene_source_specs", []),
            },
            requested=requested,
            can_folded=can_folded,
            ns_trace_available=system is None or hasattr(system, "NsTrace"),
            has_physical_source=self._current_source_model() != SOURCE_MODEL_DEFAULT,
            nonseq_energy_probability=self._current_nonseq_energy_probability(),
            nonseq_target_surface_index=self._current_nonseq_target_surface_index(),
        )
        return intent.as_dict()

    def _sync_trace_state_badge(self, trace_state: dict[str, object] | None = None) -> None:
        badge_var = self.__dict__.get("trace_state_badge_var")
        if badge_var is None:
            return
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=self.last_system)
            except Exception:
                trace_state = {"requested": self._requested_trace_mode(), "active": "Unknown"}
        requested = str(trace_state.get("requested", "Auto") or "Auto")
        active = str(trace_state.get("active", "") or "")
        if active and requested != active:
            label = f"{requested} -> {active}"
        else:
            label = active or requested
        try:
            badge_var.set(f"Scene: {label}")
        except Exception:
            pass

    def _on_trace_mode_changed(self, _event=None) -> None:
        self.trace_mode = self._requested_trace_mode()
        trace_state = self._resolved_trace_mode()
        active = str(trace_state.get("active", "Sequential"))
        self._sync_trace_state_badge(trace_state)
        if hasattr(self, "status_var"):
            self.status_var.set(f"Trace mode set to {self.trace_mode} -> {active}. Click Update.")
        self.append_progress(f"Trace mode selected: {self.trace_mode} -> {active} (pending update).")

    def _current_nonseq_ns_limit(self) -> int:
        var = self.__dict__.get("nonseq_ns_limit_var")
        try:
            value = int(float(var.get())) if var is not None else 200
        except Exception:
            value = 200
        return max(1, min(int(value), 100000))

    def _current_nonseq_energy_probability(self) -> bool:
        var = self.__dict__.get("nonseq_energy_probability_var")
        try:
            return bool(var.get()) if var is not None else False
        except Exception:
            return False

    @staticmethod
    def _normalize_folded_detector_policy_label(value: object) -> str:
        text = str(value or "").strip()
        if text in FOLDED_DETECTOR_POLICY_VALUES:
            return text
        normalized = text.lower().replace("-", " ").replace("_", " ")
        if normalized in {"display", "display path", "display compatibility", "compatibility", "legacy", "authoritative"}:
            return FOLDED_DETECTOR_POLICY_DISPLAY
        return FOLDED_DETECTOR_POLICY_DEFAULT

    def _current_folded_detector_policy_label(self) -> str:
        var = self.__dict__.get("folded_detector_policy_var")
        value = str(var.get()).strip() if var is not None else FOLDED_DETECTOR_POLICY_DEFAULT
        return self._normalize_folded_detector_policy_label(value)

    def _current_folded_detector_policy(self) -> str:
        if self._current_folded_detector_policy_label() == FOLDED_DETECTOR_POLICY_DISPLAY:
            return FOLDED_TERMINAL_POLICY_DISPLAY_COMPATIBILITY
        return FOLDED_TERMINAL_POLICY_TRACE_EVENTS

    def _folded_detector_policy_control_enabled(self) -> bool:
        try:
            trace_state = self._resolved_trace_mode()
            return bool(trace_state.get("use_folded")) or self._can_build_folded_layout()
        except Exception:
            return False

    def _current_nonseq_target_surface_index(self) -> int | None:
        var = self.__dict__.get("nonseq_target_surface_var")
        value = str(var.get()).strip() if var is not None else "Auto"
        if not value or value == "Auto":
            return None
        try:
            index = int(value.split(":", 1)[0].strip())
        except Exception:
            return None
        if 0 <= index < len(self.rows):
            return index
        return None

    def _apply_nonseq_trace_settings(self, system):
        old_energy = getattr(system, "energy_probability", 0)
        old_limit = getattr(system, "NsLimit", 200)
        old_target = getattr(system, "Targ_Surf", len(self.rows))
        try:
            system.energy_probability = 1 if self._current_nonseq_energy_probability() else 0
            system.NsLimit = self._current_nonseq_ns_limit()
            target_index = self._current_nonseq_target_surface_index()
            if target_index is None:
                if hasattr(system, "TargSurfRest"):
                    system.TargSurfRest()
                else:
                    system.Targ_Surf = getattr(system, "n", len(self.rows))
            elif hasattr(system, "TargSurf"):
                system.TargSurf(int(target_index))
            else:
                system.Targ_Surf = int(target_index) + 1
        except Exception as exc:
            self.append_debug(f"Non-sequential trace settings ignored: {_short_error_message(exc)}")

        def restore() -> None:
            try:
                system.energy_probability = old_energy
                system.NsLimit = old_limit
                system.Targ_Surf = old_target
            except Exception:
                pass

        return restore

    def _on_source_model_changed(self, _event=None) -> None:
        source_model = self._current_source_model()
        if source_model == SOURCE_MODEL_DEFAULT:
            pattern = self._current_pupil_pattern_label()
            detail = f"pupil pattern {pattern}"
            if pattern == "R-theta":
                detail = f"{detail}, r {self._current_pupil_rad():.6g}, theta {self._current_pupil_theta():.6g} deg"
        elif source_model == "Gaussian beam":
            try:
                beam = self._current_gaussian_beam_input()
                detail = (
                    f"Gaussian beam, w0 {float(beam.waist_radius_mm):.6g} mm, "
                    f"waist offset {float(beam.waist_offset_mm):.6g} mm, "
                    f"M2 {float(beam.m2):.6g}"
                )
            except Exception as exc:
                detail = f"Gaussian beam input invalid: {_short_error_message(exc)}"
        elif source_model == "Collimated disk source":
            ox, oy, oz = self._current_source_origin()
            cone_deg = self._current_source_cone_angle()
            cone_note = f", cone {cone_deg:.6g} deg" if cone_deg > 1e-12 else ""
            detail = (
                f"Collimated disk source, radius {self._current_source_radius():.6g} mm, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm{cone_note}"
            )
        elif source_model == "Random point cone":
            ox, oy, oz = self._current_source_origin()
            detail = (
                f"Random point cone, cone {self._current_source_cone_angle():.6g} deg, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm"
            )
        else:
            ox, oy, oz = self._current_source_origin()
            weight_note = ""
            weight = self._current_source_angular_weight()
            if source_model in {"Random circle source", "Random square source"} and weight != SOURCE_ANGULAR_WEIGHT_DEFAULT:
                weight_note = f", {weight}"
            detail = (
                f"{source_model}, radius {self._current_source_radius():.6g} mm, "
                f"cone {self._current_source_cone_angle():.6g} deg{weight_note}, "
                f"origin ({ox:.6g}, {oy:.6g}, {oz:.6g}) mm"
            )
        if hasattr(self, "status_var"):
            self.status_var.set(f"Source model set to {detail}. Click Update.")
        self._update_source_summary()
        self._sync_left_mode_controls()
        self.append_progress(f"Source model selected: {detail} (pending update).")
        self._mark_plot_update_pending()

    def _main_scene_source_manager_dialog(self) -> MainSceneSourceManagerDialog:
        dialog = self.__dict__.get("_main_scene_source_manager_dialog_instance")
        if dialog is None:
            dialog = MainSceneSourceManagerDialog(
                self,
                source_model_values=SOURCE_MODEL_VALUES,
                source_model_default=SOURCE_MODEL_DEFAULT,
                source_direction_preset_values=SOURCE_DIRECTION_PRESET_VALUES,
                source_angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
                source_angular_weight_values=SOURCE_ANGULAR_WEIGHT_VALUES,
                source_row_order_default=SOURCE_ROW_ORDER_DEFAULT,
                source_row_order_before_object=SOURCE_ROW_ORDER_BEFORE_OBJECT,
                source_row_order_after_object=SOURCE_ROW_ORDER_AFTER_OBJECT,
                normalize_source_row_order=normalize_source_row_order,
                # bugs/0402: the retired left Source panel's imaging controls live here now.
                pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
                pupil_pattern_values=PUPIL_PATTERN_VALUES,
                gaussian_input_mode_default=GAUSSIAN_INPUT_MODE_DEFAULT,
                gaussian_input_mode_values=GAUSSIAN_INPUT_MODE_VALUES,
                gaussian_waist_side_default=GAUSSIAN_WAIST_SIDE_DEFAULT,
                gaussian_waist_side_values=GAUSSIAN_WAIST_SIDE_VALUES,
            )
            self._main_scene_source_manager_dialog_instance = dialog
        return dialog

    def open_scene_source_manager(
        self,
        selected_source_id: str | None = None,
        *,
        aim_row_index: int | None = None,
        aim_face_id: str = "",
    ) -> None:
        self._main_scene_source_manager_dialog().open_scene_source_manager(
            selected_source_id=selected_source_id,
            aim_row_index=aim_row_index,
            aim_face_id=aim_face_id,
        )


    def toggle_analysis_mode(self, mode: str) -> None:
        current = list(self.selected_analysis_modes)
        if mode in current:
            current.remove(mode)
        else:
            current.append(mode)
        self.selected_analysis_modes = current
        self.analysis_mode = current[0] if current else "none"
        self.secondary_analysis_mode = current[1] if len(current) > 1 else None
        self._sync_analysis_mode_buttons()
        self._sync_left_mode_controls()
        label = " + ".join(self._analysis_mode_label(m) for m in current) if current else "2D"
        if hasattr(self, "status_var"):
            self.status_var.set(f"Analysis selection set to {label}. Click Update.")
        self.append_progress(f"Analysis selection updated: {label} (pending update).")

    def _sync_analysis_mode_buttons(self) -> None:
        if hasattr(self, "layout_preview_mode_var"):
            self.layout_preview_mode_var.set(self.layout_preview_mode)
        for mode, var in getattr(self, "analysis_mode_vars", {}).items():
            var.set(mode in self.selected_analysis_modes)
        menubutton = self.__dict__.get("analysis_mode_menubutton")
        if menubutton is not None:
            count = len(self.selected_analysis_modes)
            label = "Select plots ▾" if count == 0 else f"Plots: {count} ▾"
            try:
                menubutton.configure(text=label)
            except Exception:
                pass

    def _analysis_mode_label(self, mode: str) -> str:
        return analysis_mode_label(mode)

    def _trace_now(self) -> None:
        """bugs/0646: the explicit ray trace after a fast (rays-deferred) load.

        A load draws geometry only ("don't trace the ray upon startup. Let the user click
        Trace Now"); this button runs the deferred trace WITHOUT the analysis panels --
        lighter than Update, which re-runs the selected analyses too."""
        if self.editor is not None:
            row_id = self._editor_row_id
            field = self._editor_field
            if row_id is not None and field is not None:
                self._finish_edit(row_id, field, quiet=True)
        self.refresh_plot(suppress_analysis=True)
        self.status_var.set("Rays traced.")

    def _manual_update_plot(self) -> None:
        # Commit any pending inline table edit before refreshing.
        if self.editor is not None:
            row_id = self._editor_row_id
            field = self._editor_field
            if row_id is not None and field is not None:
                self._finish_edit(row_id, field, quiet=True)
        self._sync_object_controls()
        mode = (self.layout_preview_mode or "none").strip()
        if self.selected_analysis_modes:
            mode_label = " + ".join(self._analysis_mode_label(item) for item in self.selected_analysis_modes)
        else:
            mode_label = self._analysis_mode_label(mode)
        modes_with_internal_progress = {
            "psf",
            "psf_map",
            "pupil",
            "seidel",
            "wavefront",
            "zernike",
            "field_curvature",
            "distortion",
            "relative_illumination",
            "lateral_color",
            "field_map",
            "illum_map",
            "wavefront_map",
            "atmosphere",
            "interferogram",
            "tolerance_compare",
            "mtf",
        }
        if any(item in modes_with_internal_progress for item in self.selected_analysis_modes):
            self.append_progress(f"Display update requested ({mode_label}).")
            self.refresh_plot()
            self.append_progress(f"Display update completed ({mode_label}).")
            return
        self._begin_analysis_progress("Display update")
        self._update_analysis_progress(f"Refreshing {mode_label}", 1, 2)
        self.refresh_plot()
        self._update_analysis_progress("Rendering", 2, 2)
        self._finish_analysis_progress("Display update", success=True)
