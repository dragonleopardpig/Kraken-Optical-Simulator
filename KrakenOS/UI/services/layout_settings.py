"""Layout settings serialization service."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class LayoutSettingsService:
    """Collect and apply persisted layout settings while delegating state to the editor."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _collect_layout_settings(self) -> dict[str, object]:
        le = _layout_module()
        OPERAND_REGISTRY = le.OPERAND_REGISTRY
        PUPIL_PATTERN_DEFAULT = le.PUPIL_PATTERN_DEFAULT
        GAUSSIAN_INPUT_MODE_DEFAULT = le.GAUSSIAN_INPUT_MODE_DEFAULT
        GAUSSIAN_WAIST_SIDE_DEFAULT = le.GAUSSIAN_WAIST_SIDE_DEFAULT
        SOURCE_ANGULAR_WEIGHT_DEFAULT = le.SOURCE_ANGULAR_WEIGHT_DEFAULT
        SOURCE_ROW_ORDER_DEFAULT = le.SOURCE_ROW_ORDER_DEFAULT
        DETECTOR_BINS_DEFAULT = le.DETECTOR_BINS_DEFAULT
        COHERENT_SUM_MODE_DEFAULT = le.COHERENT_SUM_MODE_DEFAULT
        BRANCH_FIELD_PROPAGATION_MM_DEFAULT = le.BRANCH_FIELD_PROPAGATION_MM_DEFAULT
        CAMERA_NONE_LABEL = le.CAMERA_NONE_LABEL
        PROJECT_ROOT = le.PROJECT_ROOT
        TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS = le.TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS
        normalize_source_row_order = le.normalize_source_row_order
        _normalize_metal_catalog_specs = le._normalize_metal_catalog_specs

        def _portable_step_path_text(path_value: Any) -> str:
            if path_value is None:
                return ""
            text = str(path_value).strip()
            if not text or text.lower() in {"none", "null"}:
                return ""
            path = Path(text).expanduser()
            if not path.is_absolute():
                return path.as_posix()
            try:
                return path.resolve(strict=False).relative_to(PROJECT_ROOT.resolve()).as_posix()
            except Exception:
                return str(path)

        operand_settings: dict[str, dict[str, object]] = {}
        all_labels = {spec.label for spec in OPERAND_REGISTRY.values()}
        for label in all_labels:
            payload: dict[str, object] = {}
            var = self.operand_weight_vars.get(label)
            if var is not None:
                payload["weight"] = var.get()
            var = self.operand_target_vars.get(label)
            if var is not None:
                payload["target"] = var.get()
            var = self.operand_wavelength_vars.get(label)
            if var is not None:
                payload["wavelength"] = var.get()
            var = self.operand_field_vars.get(label)
            if var is not None:
                payload["field"] = var.get()
            var = self.operand_field_x_vars.get(label)
            if var is not None:
                payload["field_x"] = var.get()
            var = self.operand_field_y_vars.get(label)
            if var is not None:
                payload["field_y"] = var.get()
            var = self.operand_surface_vars.get(label)
            if var is not None:
                payload["surface"] = var.get()
            var = self.operand_aperture_type_vars.get(label)
            if var is not None:
                payload["aperture_type"] = var.get()
            var = self.operand_aperture_value_vars.get(label)
            if var is not None:
                payload["aperture_value"] = var.get()
            var = self.operand_frequency_vars.get(label)
            if var is not None:
                payload["frequency"] = var.get()
            var = self.operand_mtf_mode_vars.get(label)
            if var is not None:
                payload["mtf_mode"] = var.get()
            var = self.operand_mtf_algorithm_vars.get(label)
            if var is not None:
                payload["mtf_algorithm"] = var.get()
            if payload:
                operand_settings[label] = payload

        return {
            "object_mode": self._left_mode_text("object_mode_var", "Finite"),
            "display_orientation": self._current_display_orientation(),
            "projection_display_mode": self._current_projection_display_mode(),
            "wavelength": self.wavelength_var.get().strip(),
            "ray_count": self.ray_count_var.get().strip(),
            "ray_height_factor": self._left_mode_text("ray_height_factor_var", "0.8"),
            "full_pupil": bool(self.emit_full_ray_var.get()),
            "source_model": self._current_source_model(),
            "pupil_pattern": self._left_mode_text("pupil_pattern_var", PUPIL_PATTERN_DEFAULT),
            "source_radius": self._left_mode_text("source_radius_var", "5.0"),
            "source_cone_angle": self._left_mode_text("source_cone_angle_var", "0.0"),
            "gaussian_input_mode": self._left_mode_text("gaussian_input_mode_var", GAUSSIAN_INPUT_MODE_DEFAULT),
            "gaussian_waist_radius": self._left_mode_text("gaussian_waist_radius_var", "0.5"),
            "gaussian_waist_offset": self._left_mode_text("gaussian_waist_offset_var", "0.0"),
            "gaussian_beam_diameter": self._left_mode_text("gaussian_beam_diameter_var", "1.0"),
            "gaussian_full_divergence": self._left_mode_text("gaussian_full_divergence_var", "1.0"),
            "gaussian_waist_side": self._left_mode_text("gaussian_waist_side_var", GAUSSIAN_WAIST_SIDE_DEFAULT),
            "gaussian_m2": self._left_mode_text("gaussian_m2_var", "1.0"),
            "pupil_rad": self._left_mode_text("pupil_rad_var", "0.0"),
            "pupil_theta": self._left_mode_text("pupil_theta_var", "0.0"),
            "source_power": self._left_mode_text("source_power_var", "1.0"),
            "source_seed": self._left_mode_text("source_seed_var", "1"),
            "source_x": self._left_mode_text("source_x_var", "0.0"),
            "source_y": self._left_mode_text("source_y_var", "0.0"),
            "source_z": self._left_mode_text("source_z_var", "0.0"),
            "source_l": self._left_mode_text("source_l_var", "0.0"),
            "source_m": self._left_mode_text("source_m_var", "0.0"),
            "source_n": self._left_mode_text("source_n_var", "1.0"),
            "source_angular_weight": self._left_mode_text("source_angular_weight_var", SOURCE_ANGULAR_WEIGHT_DEFAULT),
            "scene_sources": list(getattr(self, "layout_scene_source_specs", []) or []),
            "scene_row_order": normalize_source_row_order(getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)),
            "analysis_surface": self.analysis_surface_var.get().strip(),
            "analysis_branch_filter": self._current_analysis_branch_filter(),
            "ray_display_mode": self._current_ray_display_mode(),
            "detector_bins": self._left_mode_text("detector_bins_var", DETECTOR_BINS_DEFAULT),
            "coherent_sum_mode": self._left_mode_text("coherent_sum_mode_var", COHERENT_SUM_MODE_DEFAULT),
            "branch_field_propagation_mm": self._left_mode_text(
                "branch_field_propagation_mm_var",
                BRANCH_FIELD_PROPAGATION_MM_DEFAULT,
            ),
            "aperture_type": self._current_aperture_type_label(),
            "aperture_value": self.aperture_value_var.get().strip(),
            "spot_view_mode": self.spot_view_mode_var.get().strip(),
            "wavefront_style": self._current_wavefront_style(),
            "tolerance_compare_view": self._current_tolerance_compare_view(),
            "show_clipped_rays": bool(self.show_clipped_rays_var.get()),
            "show_path_labels": self._current_show_path_labels(),
            "show_cardinals": bool(self.show_cardinals_var.get()),
            "show_physical_distances": bool(self.show_physical_distances_var.get()),
            "field_type": self._normalize_field_type(self._left_mode_text("field_type_var", self._current_field_type())),
            "field_value": self._left_mode_text("field_value_var", "0.0"),
            "field_count": self._left_mode_text("field_count_var", "1"),
            "atmos_plot_mode": self._current_atmos_plot_mode(),
            "atmos_observatory": self._current_atmos_observatory(),
            "atmos_wavelength_min": self.atmos_wavelength_min_var.get().strip() if hasattr(self, "atmos_wavelength_min_var") else "0.45",
            "atmos_wavelength_max": self.atmos_wavelength_max_var.get().strip() if hasattr(self, "atmos_wavelength_max_var") else "0.75",
            "atmos_wavelength_count": self.atmos_wavelength_count_var.get().strip() if hasattr(self, "atmos_wavelength_count_var") else "11",
            "atmos_zenith_deg": self.atmos_zenith_deg_var.get().strip() if hasattr(self, "atmos_zenith_deg_var") else "45.0",
            "atmos_temperature_k": self.atmos_temperature_k_var.get().strip() if hasattr(self, "atmos_temperature_k_var") else "283.15",
            "atmos_pressure_pa": self.atmos_pressure_pa_var.get().strip() if hasattr(self, "atmos_pressure_pa_var") else "101300",
            "atmos_humidity": self.atmos_humidity_var.get().strip() if hasattr(self, "atmos_humidity_var") else "0.5",
            "atmos_co2_ppm": self.atmos_co2_ppm_var.get().strip() if hasattr(self, "atmos_co2_ppm_var") else "400",
            "atmos_latitude_deg": self.atmos_latitude_deg_var.get().strip() if hasattr(self, "atmos_latitude_deg_var") else "31.0",
            "atmos_altitude_m": self.atmos_altitude_m_var.get().strip() if hasattr(self, "atmos_altitude_m_var") else "2800",
            "image_diameter_mode": self.image_diameter_mode_var.get().strip() if hasattr(self, "image_diameter_mode_var") else "Auto",
            "trace_mode": self._requested_trace_mode(),
            "folded_detector_policy": self._current_folded_detector_policy_label(),
            "nonseq_target_surface": self.nonseq_target_surface_var.get().strip() if hasattr(self, "nonseq_target_surface_var") else "Auto",
            "nonseq_ns_limit": self.nonseq_ns_limit_var.get().strip() if hasattr(self, "nonseq_ns_limit_var") else "200",
            "nonseq_energy_probability": self._current_nonseq_energy_probability(),
            "camera_model": self.camera_model_var.get().strip() if hasattr(self, "camera_model_var") else CAMERA_NONE_LABEL,
            "camera_step_path": _portable_step_path_text(self.imported_camera_step_path),
            "camera_step_rotation_x_deg": float(getattr(self, "camera_step_rotation_x_deg", 0.0)),
            "camera_step_rotation_y_deg": float(getattr(self, "camera_step_rotation_y_deg", 0.0)),
            "camera_step_rotation_z_deg": float(getattr(self, "camera_step_rotation_z_deg", 0.0)),
            "camera_step_axis_offset_xy": list(self._step_axis_offset_xy("camera")),
            "camera_step_placement_offset_xyz": list(self._step_placement_offset_xyz("camera")),
            "lens_step_path": _portable_step_path_text(self.imported_lens_step_path),
            "lens_step_largest_component_only": bool(getattr(self, "lens_step_largest_component_only", True)),
            "lens_step_rotation_x_deg": float(getattr(self, "lens_step_rotation_x_deg", 0.0)),
            "lens_step_rotation_y_deg": float(getattr(self, "lens_step_rotation_y_deg", 0.0)),
            "lens_step_rotation_z_deg": float(getattr(self, "lens_step_rotation_z_deg", 0.0)),
            "lens_step_axis_offset_xy": list(self._step_axis_offset_xy("lens")),
            "lens_step_placement_offset_xyz": list(self._step_placement_offset_xyz("lens")),
            "optical_step_path": _portable_step_path_text(self.imported_optical_step_path),
            "optical_step_rotation_x_deg": float(getattr(self, "optical_step_rotation_x_deg", 0.0)),
            "optical_step_rotation_y_deg": float(getattr(self, "optical_step_rotation_y_deg", 0.0)),
            "optical_step_rotation_z_deg": float(getattr(self, "optical_step_rotation_z_deg", 0.0)),
            "optical_step_axis_offset_xy": list(self._step_axis_offset_xy("optical")),
            "optical_step_placement_offset_xyz": list(self._step_placement_offset_xyz("optical")),
            "led_step_path": _portable_step_path_text(self.imported_led_step_path),
            "led_step_rotation_x_deg": float(getattr(self, "led_step_rotation_x_deg", 0.0)),
            "led_step_rotation_y_deg": float(getattr(self, "led_step_rotation_y_deg", 0.0)),
            "led_step_rotation_z_deg": float(getattr(self, "led_step_rotation_z_deg", 0.0)),
            "led_object_edge_distance_mm": float(getattr(self, "led_object_edge_distance_mm", 0.0)),
            "led_step_object_edge_local_z": (
                "" if getattr(self, "led_step_object_edge_local_z", None) is None else float(self.led_step_object_edge_local_z)
            ),
            "led_step_axis_offset_xy": list(self._step_axis_offset_xy("led")),
            "led_step_placement_offset_xyz": list(self._step_placement_offset_xyz("led")),
            "analysis_mode": str(self.analysis_mode or "none").strip(),
            "analysis_modes": list(self.selected_analysis_modes),
            "layout_preview_mode": "none",
            "auto_save_plot": bool(self.auto_save_plot_var.get()),
            "external_camera": self.external_camera_var.get().strip() if hasattr(self, "external_camera_var") else "None",
            "camera_overlay_mode": self.camera_overlay_mode_var.get().strip() if hasattr(self, "camera_overlay_mode_var") else "Rough envelope",
            "metal_catalogs": _normalize_metal_catalog_specs(getattr(self, "metal_catalogs", [])),
            "optimization_workers": self.optimization_workers_var.get().strip() if hasattr(self, "optimization_workers_var") else "Auto",
            "selected_operands": self._selected_operand_labels(),
            "operands": operand_settings,
            "tolerance_solve_presets": self._normalize_tolerance_solve_presets(
                getattr(self, "tolerance_solve_presets", [])
            ),
            TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS: self._normalize_tolerance_manufacturing_templates(
                self.editor.__dict__.get("tolerance_manufacturing_templates", [])
            ),
            "active_tolerance_solve_preset": str(getattr(self, "active_tolerance_solve_preset_name", "") or ""),
        }

    def _apply_layout_settings(self, settings: object) -> None:
        le = _layout_module()
        TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS = le.TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS
        _normalize_metal_catalog_specs = le._normalize_metal_catalog_specs
        normalize_source_row_order = le.normalize_source_row_order
        SOURCE_ROW_ORDER_DEFAULT = le.SOURCE_ROW_ORDER_DEFAULT
        PROJECT_ROOT = le.PROJECT_ROOT
        ATTACHMENT_DIR = le.ATTACHMENT_DIR
        normalize_projection_plane = le.normalize_projection_plane
        SOURCE_MODEL_VALUES = le.SOURCE_MODEL_VALUES
        PUPIL_PATTERN_VALUES = le.PUPIL_PATTERN_VALUES
        GAUSSIAN_INPUT_MODE_VALUES = le.GAUSSIAN_INPUT_MODE_VALUES
        GAUSSIAN_WAIST_SIDE_VALUES = le.GAUSSIAN_WAIST_SIDE_VALUES
        SOURCE_ANGULAR_WEIGHT_VALUES = le.SOURCE_ANGULAR_WEIGHT_VALUES
        ATMOS_PLOT_MODE_VALUES = le.ATMOS_PLOT_MODE_VALUES
        ANALYSIS_PATH_FILTER_DEFAULT = le.ANALYSIS_PATH_FILTER_DEFAULT
        _normalize_path_filter_label = le._normalize_path_filter_label
        DETECTOR_BINS_DEFAULT = le.DETECTOR_BINS_DEFAULT
        COHERENT_SUM_MODE_DEFAULT = le.COHERENT_SUM_MODE_DEFAULT
        _normalize_coherent_sum_mode = le._normalize_coherent_sum_mode
        BRANCH_FIELD_PROPAGATION_MM_DEFAULT = le.BRANCH_FIELD_PROPAGATION_MM_DEFAULT
        WAVEFRONT_STYLE_VALUES = le.WAVEFRONT_STYLE_VALUES
        TOLERANCE_COMPARE_VIEW_VALUES = le.TOLERANCE_COMPARE_VIEW_VALUES
        CAMERA_NONE_LABEL = le.CAMERA_NONE_LABEL
        camera_record = le.camera_record
        FIELD_TYPE_CANONICAL_VALUES = le.FIELD_TYPE_CANONICAL_VALUES
        if not isinstance(settings, dict):
            return
        self.tolerance_solve_presets = self._normalize_tolerance_solve_presets(
            settings.get("tolerance_solve_presets", [])
        )
        self.tolerance_manufacturing_templates = self._normalize_tolerance_manufacturing_templates(
            settings.get(TOLERANCE_MANUFACTURING_TEMPLATES_SETTINGS, [])
        )
        preset_names = {str(preset.get("name", "")) for preset in self.tolerance_solve_presets}
        active_preset = str(settings.get("active_tolerance_solve_preset", "") or "").strip()
        self.active_tolerance_solve_preset_name = active_preset if active_preset in preset_names else ""
        self.metal_catalogs = _normalize_metal_catalog_specs(settings.get("metal_catalogs", []))
        self.layout_scene_source_specs = self._normalize_scene_source_specs(settings.get("scene_sources", []))
        self.layout_scene_row_order = normalize_source_row_order(settings.get("scene_row_order", SOURCE_ROW_ORDER_DEFAULT))

        def _parse_bool(value) -> bool:
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)

        def _set_text(var, key: str) -> None:
            value = settings.get(key)
            if value is not None:
                var.set(str(value).strip())

        def _path_setting(key: str) -> Path | None:
            value = settings.get(key)
            if value is None:
                return None
            text = str(value).strip()
            if not text or text.lower() in {"none", "null"}:
                return None
            path = Path(text).expanduser()
            if path.is_absolute():
                return path
            for candidate in (PROJECT_ROOT / path, ATTACHMENT_DIR / path, path):
                if candidate.exists():
                    return candidate
            return PROJECT_ROOT / path

        def _offset_setting(key: str) -> tuple[float, float]:
            value = settings.get(key)
            if isinstance(value, (list, tuple)) and len(value) >= 2:
                try:
                    return (float(value[0]), float(value[1]))
                except Exception:
                    return (0.0, 0.0)
            if isinstance(value, str):
                parts = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
                if len(parts) >= 2:
                    try:
                        return (float(parts[0]), float(parts[1]))
                    except Exception:
                        return (0.0, 0.0)
            return (0.0, 0.0)

        def _offset_xyz_setting(key: str) -> tuple[float, float, float]:
            value = settings.get(key)
            if isinstance(value, (list, tuple)) and len(value) >= 3:
                try:
                    return (float(value[0]), float(value[1]), float(value[2]))
                except Exception:
                    return (0.0, 0.0, 0.0)
            if isinstance(value, str):
                parts = [part.strip() for part in value.replace(";", ",").split(",") if part.strip()]
                if len(parts) >= 3:
                    try:
                        return (float(parts[0]), float(parts[1]), float(parts[2]))
                    except Exception:
                        return (0.0, 0.0, 0.0)
            return (0.0, 0.0, 0.0)

        display_orientation = str(settings.get("display_orientation", "")).strip()
        if display_orientation in {"Vertical", "Horizontal", "YZ", "XZ", "XY"}:
            self.display_orientation_var.set(normalize_projection_plane(display_orientation))
        if hasattr(self, "projection_display_mode_var"):
            self.projection_display_mode_var.set(le.PROJECTION_MODE_FULL_3D)

        object_mode = str(settings.get("object_mode", "")).strip()
        if object_mode in {"Finite", "Infinity"}:
            self.object_mode_var.set(object_mode)

        _set_text(self.wavelength_var, "wavelength")
        _set_text(self.ray_count_var, "ray_count")
        _set_text(self.ray_height_factor_var, "ray_height_factor")
        if hasattr(self, "source_model_var"):
            source_model = str(settings.get("source_model", "")).strip()
            if source_model in SOURCE_MODEL_VALUES:
                self.source_model_var.set(source_model)
        if hasattr(self, "pupil_pattern_var"):
            pupil_pattern = str(settings.get("pupil_pattern", "")).strip()
            if pupil_pattern in PUPIL_PATTERN_VALUES:
                self.pupil_pattern_var.set(pupil_pattern)
        if hasattr(self, "source_radius_var"):
            _set_text(self.source_radius_var, "source_radius")
        if hasattr(self, "source_cone_angle_var"):
            _set_text(self.source_cone_angle_var, "source_cone_angle")
        if hasattr(self, "gaussian_input_mode_var"):
            mode = str(settings.get("gaussian_input_mode", "")).strip()
            if mode in GAUSSIAN_INPUT_MODE_VALUES:
                self.gaussian_input_mode_var.set(mode)
        if hasattr(self, "gaussian_waist_radius_var"):
            _set_text(self.gaussian_waist_radius_var, "gaussian_waist_radius")
        if hasattr(self, "gaussian_waist_offset_var"):
            _set_text(self.gaussian_waist_offset_var, "gaussian_waist_offset")
        if hasattr(self, "gaussian_beam_diameter_var"):
            _set_text(self.gaussian_beam_diameter_var, "gaussian_beam_diameter")
        if hasattr(self, "gaussian_full_divergence_var"):
            _set_text(self.gaussian_full_divergence_var, "gaussian_full_divergence")
        if hasattr(self, "gaussian_waist_side_var"):
            side = str(settings.get("gaussian_waist_side", "")).strip()
            if side in GAUSSIAN_WAIST_SIDE_VALUES:
                self.gaussian_waist_side_var.set(side)
        if hasattr(self, "gaussian_m2_var"):
            _set_text(self.gaussian_m2_var, "gaussian_m2")
        if hasattr(self, "pupil_rad_var"):
            _set_text(self.pupil_rad_var, "pupil_rad")
        if hasattr(self, "pupil_theta_var"):
            _set_text(self.pupil_theta_var, "pupil_theta")
        if hasattr(self, "source_power_var"):
            _set_text(self.source_power_var, "source_power")
        if hasattr(self, "source_seed_var"):
            _set_text(self.source_seed_var, "source_seed")
        if hasattr(self, "source_x_var"):
            _set_text(self.source_x_var, "source_x")
        if hasattr(self, "source_y_var"):
            _set_text(self.source_y_var, "source_y")
        if hasattr(self, "source_z_var"):
            _set_text(self.source_z_var, "source_z")
        if hasattr(self, "source_l_var"):
            _set_text(self.source_l_var, "source_l")
        if hasattr(self, "source_m_var"):
            _set_text(self.source_m_var, "source_m")
        if hasattr(self, "source_n_var"):
            _set_text(self.source_n_var, "source_n")
        self._sync_source_direction_preset_from_lmn()
        if hasattr(self, "source_angular_weight_var"):
            weight = str(settings.get("source_angular_weight", "")).strip()
            if weight in SOURCE_ANGULAR_WEIGHT_VALUES:
                self.source_angular_weight_var.set(weight)
        if hasattr(self, "atmos_observatory_var"):
            observatory = str(settings.get("atmos_observatory", "Manual")).strip() or "Manual"
            if observatory in self._atmos_observatory_names():
                self.atmos_observatory_var.set(observatory)
                if observatory != "Manual" and not any(
                    key in settings
                    for key in (
                        "atmos_temperature_k",
                        "atmos_pressure_pa",
                        "atmos_humidity",
                        "atmos_co2_ppm",
                        "atmos_latitude_deg",
                        "atmos_altitude_m",
                    )
                ):
                    self._apply_atmos_observatory(observatory)
        if "atmos_plot_mode" in settings and hasattr(self, "atmos_plot_mode_var"):
            atmos_plot_mode = str(settings.get("atmos_plot_mode", "")).strip()
            if atmos_plot_mode in ATMOS_PLOT_MODE_VALUES:
                self.atmos_plot_mode_var.set(atmos_plot_mode)
        for setting_key, attr_name in (
            ("atmos_wavelength_min", "atmos_wavelength_min_var"),
            ("atmos_wavelength_max", "atmos_wavelength_max_var"),
            ("atmos_wavelength_count", "atmos_wavelength_count_var"),
            ("atmos_zenith_deg", "atmos_zenith_deg_var"),
            ("atmos_temperature_k", "atmos_temperature_k_var"),
            ("atmos_pressure_pa", "atmos_pressure_pa_var"),
            ("atmos_humidity", "atmos_humidity_var"),
            ("atmos_co2_ppm", "atmos_co2_ppm_var"),
            ("atmos_latitude_deg", "atmos_latitude_deg_var"),
            ("atmos_altitude_m", "atmos_altitude_m_var"),
        ):
            if hasattr(self, attr_name):
                _set_text(getattr(self, attr_name), setting_key)
        self._update_atmosphere_summary()

        aperture_type = str(settings.get("aperture_type", "")).strip().upper()
        if aperture_type in {"STOP", "EPD", "FNO"}:
            self.aperture_type_var.set(aperture_type)
        _set_text(self.aperture_value_var, "aperture_value")

        if "spot_view_mode" in settings:
            spot_view_mode = str(settings.get("spot_view_mode", "")).strip()
            if spot_view_mode in {"Grid", "Absolute", "Centroid"}:
                self.spot_view_mode_var.set(spot_view_mode)

        if "analysis_branch_filter" in settings and hasattr(self, "analysis_branch_filter_var"):
            analysis_branch_filter = _normalize_path_filter_label(settings.get("analysis_branch_filter", ANALYSIS_PATH_FILTER_DEFAULT))
            self.analysis_branch_filter_var.set(analysis_branch_filter)
        if "ray_display_mode" in settings:
            self._set_optional_var("ray_display_mode_var", self._normalize_ray_display_mode(settings.get("ray_display_mode")))

        if "detector_bins" in settings and hasattr(self, "detector_bins_var"):
            detector_bins = str(settings.get("detector_bins", DETECTOR_BINS_DEFAULT)).strip() or DETECTOR_BINS_DEFAULT
            self.detector_bins_var.set(detector_bins)
        if "coherent_sum_mode" in settings and hasattr(self, "coherent_sum_mode_var"):
            self.coherent_sum_mode_var.set(_normalize_coherent_sum_mode(settings.get("coherent_sum_mode", COHERENT_SUM_MODE_DEFAULT)))
        if "branch_field_propagation_mm" in settings and hasattr(self, "branch_field_propagation_mm_var"):
            propagation_mm = str(settings.get("branch_field_propagation_mm", BRANCH_FIELD_PROPAGATION_MM_DEFAULT)).strip()
            self.branch_field_propagation_mm_var.set(propagation_mm or BRANCH_FIELD_PROPAGATION_MM_DEFAULT)

        if "wavefront_style" in settings and hasattr(self, "wavefront_style_var"):
            wavefront_style = str(settings.get("wavefront_style", "")).strip()
            if wavefront_style in WAVEFRONT_STYLE_VALUES:
                self.wavefront_style_var.set(wavefront_style)

        if "tolerance_compare_view" in settings and hasattr(self, "tolerance_compare_view_var"):
            tolerance_compare_view = str(settings.get("tolerance_compare_view", "")).strip()
            if tolerance_compare_view in TOLERANCE_COMPARE_VIEW_VALUES:
                self.tolerance_compare_view_var.set(tolerance_compare_view)

        field_count = settings.get("field_count")
        if field_count is not None:
            self.field_count_var.set(str(field_count).strip())

        image_diameter_mode = str(settings.get("image_diameter_mode", "")).strip()
        if image_diameter_mode in {"Auto", "Manual"} and hasattr(self, "image_diameter_mode_var"):
            self.image_diameter_mode_var.set(image_diameter_mode)

        trace_mode = str(settings.get("trace_mode", "")).strip()
        if trace_mode in {"Auto", "Sequential", "Folded Preview", "Non-Sequential Preview"} and hasattr(self, "trace_mode_var"):
            self.trace_mode_var.set(trace_mode)
            self.trace_mode = trace_mode
        if "folded_detector_policy" in settings and hasattr(self, "folded_detector_policy_var"):
            folded_policy = self._normalize_folded_detector_policy_label(settings.get("folded_detector_policy"))
            self.folded_detector_policy_var.set(folded_policy)
        if hasattr(self, "nonseq_ns_limit_var"):
            _set_text(self.nonseq_ns_limit_var, "nonseq_ns_limit")
        if "nonseq_energy_probability" in settings and hasattr(self, "nonseq_energy_probability_var"):
            self.nonseq_energy_probability_var.set(_parse_bool(settings.get("nonseq_energy_probability")))
        if "nonseq_target_surface" in settings and hasattr(self, "nonseq_target_surface_var"):
            target = str(settings.get("nonseq_target_surface", "Auto")).strip() or "Auto"
            self.nonseq_target_surface_var.set(target)

        camera_model = str(settings.get("camera_model", CAMERA_NONE_LABEL)).strip()
        if hasattr(self, "camera_model_var"):
            if camera_model == CAMERA_NONE_LABEL or camera_record(camera_model) is not None:
                self.camera_model_var.set(camera_model)
            else:
                self.camera_model_var.set(CAMERA_NONE_LABEL)
        self.imported_camera_step_path = _path_setting("camera_step_path")
        self.imported_lens_step_path = _path_setting("lens_step_path")
        self.imported_optical_step_path = _path_setting("optical_step_path")
        self.imported_led_step_path = _path_setting("led_step_path")
        self.lens_step_largest_component_only = _parse_bool(settings.get("lens_step_largest_component_only", True))
        self.camera_step_axis_offset_xy = _offset_setting("camera_step_axis_offset_xy")
        self.lens_step_axis_offset_xy = _offset_setting("lens_step_axis_offset_xy")
        self.optical_step_axis_offset_xy = _offset_setting("optical_step_axis_offset_xy")
        self.led_step_axis_offset_xy = _offset_setting("led_step_axis_offset_xy")
        self.camera_step_placement_offset_xyz = _offset_xyz_setting("camera_step_placement_offset_xyz")
        self.lens_step_placement_offset_xyz = _offset_xyz_setting("lens_step_placement_offset_xyz")
        self.optical_step_placement_offset_xyz = _offset_xyz_setting("optical_step_placement_offset_xyz")
        self.led_step_placement_offset_xyz = _offset_xyz_setting("led_step_placement_offset_xyz")
        self._cad_axis_pick_label = None
        self._cad_axis_pick_any = False
        self._cad_led_object_edge_pick = False
        self._selected_step_label = None
        try:
            self.camera_step_rotation_x_deg = float(settings.get("camera_step_rotation_x_deg", 0.0)) % 360.0
        except Exception:
            self.camera_step_rotation_x_deg = 0.0
        try:
            self.camera_step_rotation_y_deg = float(settings.get("camera_step_rotation_y_deg", 0.0)) % 360.0
        except Exception:
            self.camera_step_rotation_y_deg = 0.0
        try:
            self.camera_step_rotation_z_deg = float(settings.get("camera_step_rotation_z_deg", 0.0)) % 360.0
        except Exception:
            self.camera_step_rotation_z_deg = 0.0
        try:
            self.lens_step_rotation_x_deg = float(settings.get("lens_step_rotation_x_deg", 0.0)) % 360.0
        except Exception:
            self.lens_step_rotation_x_deg = 0.0
        try:
            self.lens_step_rotation_y_deg = float(settings.get("lens_step_rotation_y_deg", 0.0)) % 360.0
        except Exception:
            self.lens_step_rotation_y_deg = 0.0
        try:
            self.lens_step_rotation_z_deg = float(settings.get("lens_step_rotation_z_deg", 0.0)) % 360.0
        except Exception:
            self.lens_step_rotation_z_deg = 0.0
        try:
            self.optical_step_rotation_x_deg = float(settings.get("optical_step_rotation_x_deg", 0.0)) % 360.0
        except Exception:
            self.optical_step_rotation_x_deg = 0.0
        try:
            self.optical_step_rotation_y_deg = float(settings.get("optical_step_rotation_y_deg", 0.0)) % 360.0
        except Exception:
            self.optical_step_rotation_y_deg = 0.0
        try:
            self.optical_step_rotation_z_deg = float(settings.get("optical_step_rotation_z_deg", 0.0)) % 360.0
        except Exception:
            self.optical_step_rotation_z_deg = 0.0
        try:
            self.led_step_rotation_x_deg = float(settings.get("led_step_rotation_x_deg", 0.0)) % 360.0
        except Exception:
            self.led_step_rotation_x_deg = 0.0
        try:
            self.led_step_rotation_y_deg = float(settings.get("led_step_rotation_y_deg", 0.0)) % 360.0
        except Exception:
            self.led_step_rotation_y_deg = 0.0
        try:
            self.led_step_rotation_z_deg = float(settings.get("led_step_rotation_z_deg", 0.0)) % 360.0
        except Exception:
            self.led_step_rotation_z_deg = 0.0
        try:
            self.led_object_edge_distance_mm = max(float(settings.get("led_object_edge_distance_mm", 0.0)), 0.0)
        except Exception:
            self.led_object_edge_distance_mm = 0.0
        led_object_edge_local_z = settings.get("led_step_object_edge_local_z", "")
        if str(led_object_edge_local_z).strip():
            try:
                self.led_step_object_edge_local_z = float(led_object_edge_local_z)
            except Exception:
                self.led_step_object_edge_local_z = None
        else:
            self.led_step_object_edge_local_z = None

        self._sync_field_mode_ui()

        field_type = self._normalize_field_type(str(settings.get("field_type", "")).strip())
        if field_type in FIELD_TYPE_CANONICAL_VALUES:
            self.field_type_var.set(self._field_type_display_label(field_type))
            self._last_field_type = field_type

        field_value = settings.get("field_value")
        if field_value is not None:
            field_value_text = str(field_value).strip()
            self.field_value_var.set(field_value_text)
            self._field_type_defaults[self._current_field_type()] = field_value_text

        analysis_surface = settings.get("analysis_surface")
        if analysis_surface is not None:
            analysis_surface_text = str(analysis_surface).strip()
            if analysis_surface_text == "Auto":
                self.analysis_surface_var.set("Auto")
            elif analysis_surface_text in set(self.analysis_surface_menu["values"]):
                self.analysis_surface_var.set(analysis_surface_text)
            else:
                try:
                    index = int(float(analysis_surface_text))
                except (TypeError, ValueError):
                    index = -1
                if 0 <= index < len(self.rows):
                    self.analysis_surface_var.set(f"{index}: {self.rows[index].name}")

        bool_vars = {
            "show_clipped_rays": self.show_clipped_rays_var,
            "show_path_labels": self.show_path_labels_var,
            "show_cardinals": self.show_cardinals_var,
            "show_physical_distances": self.show_physical_distances_var,
            "auto_save_plot": self.auto_save_plot_var,
            "full_pupil": self.emit_full_ray_var,
        }
        for key, var in bool_vars.items():
            if key in settings:
                parsed_value = _parse_bool(settings.get(key))
                var.set(parsed_value)
                if key == "show_path_labels":
                    self.show_path_labels = parsed_value

        if hasattr(self, "optimization_workers_var") and "optimization_workers" in settings:
            worker_text = str(settings.get("optimization_workers", "Auto")).strip() or "Auto"
            self.optimization_workers_var.set(worker_text)

        if hasattr(self, "external_camera_var"):
            self.external_camera_var.set("None")
        if hasattr(self, "camera_overlay_mode_var"):
            self.camera_overlay_mode_var.set("Off")

        selected_operands = settings.get("selected_operands")
        if isinstance(selected_operands, (list, tuple)):
            self._set_selected_operand_labels([str(label) for label in selected_operands])

        operand_settings = settings.get("operands")
        if isinstance(operand_settings, dict):
            for label, payload in operand_settings.items():
                if not isinstance(payload, dict):
                    continue
                if label in self.operand_weight_vars and "weight" in payload:
                    self.operand_weight_vars[label].set(str(payload["weight"]).strip())
                if label in self.operand_target_vars and "target" in payload:
                    self.operand_target_vars[label].set(str(payload["target"]).strip())
                if label in self.operand_wavelength_vars and "wavelength" in payload:
                    self.operand_wavelength_vars[label].set(str(payload["wavelength"]).strip())
                if label in self.operand_field_vars and "field" in payload:
                    self.operand_field_vars[label].set(str(payload["field"]).strip())
                if label in self.operand_field_x_vars and "field_x" in payload:
                    self.operand_field_x_vars[label].set(str(payload["field_x"]).strip())
                if label in self.operand_field_y_vars and "field_y" in payload:
                    self.operand_field_y_vars[label].set(str(payload["field_y"]).strip())
                if label in self.operand_surface_vars and "surface" in payload:
                    surface_text = str(payload["surface"]).strip()
                    if surface_text:
                        self.operand_surface_vars[label].set(surface_text)
                if label in self.operand_aperture_type_vars and "aperture_type" in payload:
                    aperture_text = str(payload["aperture_type"]).strip().upper()
                    if aperture_text in {"STOP", "EPD", "FNO"}:
                        self.operand_aperture_type_vars[label].set(aperture_text)
                if label in self.operand_aperture_value_vars and "aperture_value" in payload:
                    self.operand_aperture_value_vars[label].set(str(payload["aperture_value"]).strip())
                if label in self.operand_frequency_vars and "frequency" in payload:
                    self.operand_frequency_vars[label].set(str(payload["frequency"]).strip())
                if label in self.operand_mtf_mode_vars and "mtf_mode" in payload:
                    mode_text = str(payload["mtf_mode"]).strip()
                    if mode_text in {"Average", "Tangential", "Sagittal"}:
                        self.operand_mtf_mode_vars[label].set(mode_text)
                if label in self.operand_mtf_algorithm_vars and "mtf_algorithm" in payload:
                    algorithm_text = str(payload["mtf_algorithm"]).strip()
                    if algorithm_text in {"Diffraction FFT", "PSF FFT", "LSF FFT"}:
                        self.operand_mtf_algorithm_vars[label].set(algorithm_text)

        self.layout_preview_mode = "none"
        analysis_modes = settings.get("analysis_modes")
        valid_analysis_modes = {
            "spot",
            "psf",
            "psf_map",
            "rms",
            "field_curvature",
            "relative_illumination",
            "polarization",
            "lateral_color",
            "detector_map",
            "coherent_detector",
            "branch_field",
            "diffraction_detector",
            "field_map",
            "illum_map",
            "wavefront_map",
            "atmosphere",
            "pupil",
            "seidel",
            "wavefront",
            "zernike",
            "interferogram",
            "tolerance_compare",
            "mtf",
        }
        if isinstance(analysis_modes, (list, tuple)):
            self.selected_analysis_modes = [str(item).strip() for item in analysis_modes if str(item).strip() in valid_analysis_modes][:2]
        else:
            analysis_mode = str(settings.get("analysis_mode", "")).strip()
            self.selected_analysis_modes = [analysis_mode] if analysis_mode in valid_analysis_modes else []
            if analysis_mode == "none":
                self.layout_preview_mode = "none"
        self.analysis_mode = self.selected_analysis_modes[0] if self.selected_analysis_modes else "none"
        self.secondary_analysis_mode = self.selected_analysis_modes[1] if len(self.selected_analysis_modes) > 1 else None
        self._sync_analysis_mode_buttons()

        if self._apply_image_diameter_mode():
            self._sync_image_row_table_value()
        self._sync_object_controls()
        self._update_field_status_hint()
        self._sync_left_mode_controls()
