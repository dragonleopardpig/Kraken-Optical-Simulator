"""Source launch and scene source modeling mixin for the Tk layout editor."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.scene_geometry import SceneSource3D
from KrakenOS.UI.scene_row_mapping import SOURCE_ROW_ORDER_DEFAULT, normalize_source_row_order
from KrakenOS.UI.scene_source_analysis import (
    dedupe_scene_source_ids,
    normalize_scene_source_specs,
    scene_source_detail_text,
    scene_source_feature_text,
    scene_source_from_spec,
    scene_source_setting_value,
    scene_sources_summary_text,
    source_panel_summary_text,
    source_spec_bool,
    source_spec_float,
    source_spec_vector,
)
from KrakenOS.UI.source_trace_helpers import (
    ATMOS_PLOT_MODE_DEFAULT,
    ATMOS_PLOT_MODE_VALUES,
    GAUSSIAN_INPUT_MODE_DEFAULT,
    GAUSSIAN_WAIST_SIDE_DEFAULT,
    PUPIL_PATTERN_DEFAULT,
    PUPIL_PATTERN_VALUES,
    SOURCE_ANGULAR_WEIGHT_DEFAULT,
    SOURCE_ANGULAR_WEIGHT_VALUES,
    SOURCE_DIRECTION_PRESETS,
    SOURCE_DIRECTION_PRESET_CUSTOM,
    SOURCE_MERIDIONAL_PREVIEW_MAX_RADIUS_FRACTION,
    SOURCE_MODEL_DEFAULT,
    SOURCE_MODEL_VALUES,
    SOURCE_MODEL_ZEMAX_RAYFILE,
)
from KrakenOS.UI.zemax_rayfile import sample_zemax_rayfile

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ATTACHMENT_DIR = PROJECT_ROOT / "attachment"


def _preferred_existing_path(*candidates: Path | str) -> Path:
    paths = [Path(candidate).expanduser() for candidate in candidates]
    for path in paths:
        if path.exists():
            return path
    return paths[0]


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip()
    if not text:
        return exc.__class__.__name__
    first = text.splitlines()[0].strip()
    if len(first) > limit:
        return first[:limit] + "..."
    return first


class SourceModelingMixin:
    def _current_gaussian_waist_radius(self) -> float:
        var = self.__dict__.get("gaussian_waist_radius_var")
        try:
            value = float(var.get()) if var is not None else 0.5
        except Exception:
            value = 0.5
        return max(float(value), 1e-9)

    def _current_gaussian_waist_offset(self) -> float:
        var = self.__dict__.get("gaussian_waist_offset_var")
        try:
            return float(var.get()) if var is not None else 0.0
        except Exception:
            return 0.0

    def _current_gaussian_m2(self) -> float:
        var = self.__dict__.get("gaussian_m2_var")
        try:
            value = float(var.get()) if var is not None else 1.0
        except Exception:
            value = 1.0
        return max(float(value), 1e-9)

    def _current_gaussian_beam_diameter(self) -> float:
        var = self.__dict__.get("gaussian_beam_diameter_var")
        try:
            value = float(var.get()) if var is not None else 1.0
        except Exception:
            value = 1.0
        return max(float(value), 1e-9)

    def _current_gaussian_full_divergence(self) -> float:
        var = self.__dict__.get("gaussian_full_divergence_var")
        try:
            value = float(var.get()) if var is not None else 1.0
        except Exception:
            value = 1.0
        return max(float(value), 1e-9)

    def _current_gaussian_waist_after_input(self) -> bool:
        var = self.__dict__.get("gaussian_waist_side_var")
        value = str(var.get()).strip() if var is not None else GAUSSIAN_WAIST_SIDE_DEFAULT
        return value == "Waist after source"

    def _current_gaussian_beam_input(self, wavelength: float | None = None):
        wavelength_value = float(self._current_wavelength() if wavelength is None else wavelength)
        if self._current_gaussian_input_mode() == "Diameter + divergence":
            return Kos.gaussian_beam_from_diameter_divergence(
                wavelength_um=wavelength_value,
                beam_diameter_mm=self._current_gaussian_beam_diameter(),
                full_divergence_mrad=self._current_gaussian_full_divergence(),
                m2=self._current_gaussian_m2(),
                waist_after_input=self._current_gaussian_waist_after_input(),
            )
        return Kos.GaussianBeamInput(
            wavelength_um=wavelength_value,
            waist_radius_mm=self._current_gaussian_waist_radius(),
            waist_offset_mm=self._current_gaussian_waist_offset(),
            m2=self._current_gaussian_m2(),
        )

    def _current_pupil_rad(self) -> float:
        pupil_rad_var = self.__dict__.get("pupil_rad_var")
        try:
            value = float(pupil_rad_var.get()) if pupil_rad_var is not None else 0.0
        except Exception:
            value = 0.0
        return float(np.clip(float(value), 0.0, 1.0))

    def _current_pupil_theta(self) -> float:
        pupil_theta_var = self.__dict__.get("pupil_theta_var")
        try:
            value = float(pupil_theta_var.get()) if pupil_theta_var is not None else 0.0
        except Exception:
            value = 0.0
        return float(value)

    def _current_source_angular_weight(self) -> str:
        source_angular_weight_var = self.__dict__.get("source_angular_weight_var")
        value = str(source_angular_weight_var.get()).strip() if source_angular_weight_var is not None else SOURCE_ANGULAR_WEIGHT_DEFAULT
        return value if value in SOURCE_ANGULAR_WEIGHT_VALUES else SOURCE_ANGULAR_WEIGHT_DEFAULT

    def _current_source_power(self) -> float:
        source_power_var = self.__dict__.get("source_power_var")
        try:
            value = float(source_power_var.get()) if source_power_var is not None else 1.0
        except Exception:
            value = 1.0
        return max(float(value), 0.0)

    def _current_source_seed(self) -> int:
        source_seed_var = self.__dict__.get("source_seed_var")
        try:
            seed = int(float(source_seed_var.get())) if source_seed_var is not None else 1
        except Exception:
            seed = 1
        return int(seed) % (2**32 - 1)

    def _current_source_origin(self) -> tuple[float, float, float]:
        def _component(name: str) -> float:
            var = self.__dict__.get(name)
            try:
                return float(var.get()) if var is not None else 0.0
            except Exception:
                return 0.0

        return (_component("source_x_var"), _component("source_y_var"), _component("source_z_var"))

    def _current_source_direction(self) -> tuple[float, float, float]:
        def _component(name: str, default: float) -> float:
            var = self.__dict__.get(name)
            try:
                return float(var.get()) if var is not None else float(default)
            except Exception:
                return float(default)

        direction = np.asarray(
            (
                _component("source_l_var", 0.0),
                _component("source_m_var", 0.0),
                _component("source_n_var", 1.0),
            ),
            dtype=float,
        )
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-12:
            direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
            norm = 1.0
        direction = direction / norm
        return (float(direction[0]), float(direction[1]), float(direction[2]))

    @staticmethod
    def _source_direction_preset_vector(label: str) -> tuple[float, float, float] | None:
        text = str(label or "").strip()
        for preset_label, vector in SOURCE_DIRECTION_PRESETS:
            if preset_label == text:
                return vector
        return None

    @staticmethod
    def _source_direction_preset_label(direction) -> str:
        try:
            vector = np.asarray(direction, dtype=float).reshape(-1)[:3]
        except Exception:
            return SOURCE_DIRECTION_PRESET_CUSTOM
        if vector.size < 3:
            return SOURCE_DIRECTION_PRESET_CUSTOM
        norm = float(np.linalg.norm(vector))
        if norm <= 1e-12:
            return SOURCE_DIRECTION_PRESET_CUSTOM
        vector = vector / norm
        for preset_label, preset_vector in SOURCE_DIRECTION_PRESETS:
            reference = np.asarray(preset_vector, dtype=float)
            if np.allclose(vector, reference, rtol=1e-6, atol=1e-6):
                return preset_label
        return SOURCE_DIRECTION_PRESET_CUSTOM

    @staticmethod
    def _format_source_direction_component(value: float) -> str:
        return f"{float(value):.12g}"

    def _sync_source_direction_preset_from_lmn(self) -> None:
        var = self.__dict__.get("source_direction_preset_var")
        if var is None:
            return
        try:
            label = self._source_direction_preset_label(self._current_source_direction())
            if str(var.get()) != label:
                var.set(label)
        except Exception:
            pass

    def _set_source_direction_lmn(self, direction) -> None:
        vector = np.asarray(direction, dtype=float).reshape(-1)
        if vector.size < 3:
            return
        norm = float(np.linalg.norm(vector[:3]))
        if norm <= 1e-12:
            return
        vector = vector[:3] / norm
        for attr, value in (
            ("source_l_var", vector[0]),
            ("source_m_var", vector[1]),
            ("source_n_var", vector[2]),
        ):
            var = self.__dict__.get(attr)
            if var is not None:
                var.set(self._format_source_direction_component(float(value)))

    def _on_source_direction_preset_changed(self, _event=None) -> None:
        var = self.__dict__.get("source_direction_preset_var")
        label = str(var.get()).strip() if var is not None else SOURCE_DIRECTION_PRESET_CUSTOM
        vector = self._source_direction_preset_vector(label)
        if vector is not None:
            self._set_source_direction_lmn(vector)
        self._update_source_summary()
        if hasattr(self, "status_var"):
            dl, dm, dn = self._current_source_direction()
            self.status_var.set(f"Source direction set to {label}: LMN=({dl:.4g}, {dm:.4g}, {dn:.4g}). Click Update.")
        self._mark_plot_update_pending()

    def _source_frame_vectors(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        w = np.asarray(self._current_source_direction(), dtype=float)
        return self._source_frame_vectors_from_direction(w)

    @staticmethod
    def _source_frame_vectors_from_direction(direction) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        w = np.asarray(direction, dtype=float).reshape(-1)
        if w.size < 3:
            w = np.pad(w, (0, 3 - w.size), constant_values=0.0)
            w[2] = 1.0
        w = w[:3]
        norm = float(np.linalg.norm(w))
        if norm <= 1e-12:
            w = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            w = w / norm
        reference = np.asarray((0.0, 0.0, 1.0), dtype=float)
        if abs(float(np.dot(w, reference))) > 0.94:
            reference = np.asarray((0.0, 1.0, 0.0), dtype=float)
        u = np.cross(reference, w)
        u_norm = float(np.linalg.norm(u))
        if u_norm <= 1e-12:
            u = np.asarray((1.0, 0.0, 0.0), dtype=float)
            u_norm = 1.0
        u = u / u_norm
        v = np.cross(w, u)
        v_norm = float(np.linalg.norm(v))
        if v_norm <= 1e-12:
            v = np.asarray((0.0, 1.0, 0.0), dtype=float)
            v_norm = 1.0
        v = v / v_norm
        return u, v, w

    @staticmethod
    def _cone_directions_about_local_base(base_direction, l_values, m_values, n_values):
        u, v, w = SourceModelingMixin._source_frame_vectors_from_direction(base_direction)
        l_arr, m_arr, n_arr = (
            np.asarray(values, dtype=float).reshape(-1)
            for values in (l_values, m_values, n_values)
        )
        dirs = (
            l_arr[:, None] * u[None, :]
            + m_arr[:, None] * v[None, :]
            + n_arr[:, None] * w[None, :]
        )
        norms = np.linalg.norm(dirs, axis=1)
        norms = np.where(norms > 1e-12, norms, 1.0)
        dirs = dirs / norms[:, None]
        return dirs[:, 0], dirs[:, 1], dirs[:, 2]

    @staticmethod
    def _orient_source_points_and_dirs_for_source(
        origin,
        direction,
        x_values,
        y_values,
        z_values,
        l_values,
        m_values,
        n_values,
    ):
        origin_arr = np.asarray(origin, dtype=float).reshape(-1)
        if origin_arr.size < 3:
            origin_arr = np.pad(origin_arr, (0, 3 - origin_arr.size), constant_values=0.0)
        origin_arr = origin_arr[:3]
        u, v, w = SourceModelingMixin._source_frame_vectors_from_direction(direction)
        x_arr, y_arr, z_arr, l_arr, m_arr, n_arr = (
            np.asarray(values, dtype=float).reshape(-1)
            for values in (x_values, y_values, z_values, l_values, m_values, n_values)
        )
        points = (
            origin_arr[None, :]
            + x_arr[:, None] * u[None, :]
            + y_arr[:, None] * v[None, :]
            + z_arr[:, None] * w[None, :]
        )
        dirs = (
            l_arr[:, None] * u[None, :]
            + m_arr[:, None] * v[None, :]
            + n_arr[:, None] * w[None, :]
        )
        norms = np.linalg.norm(dirs, axis=1)
        norms = np.where(norms > 1e-12, norms, 1.0)
        dirs = dirs / norms[:, None]
        return (
            points[:, 0],
            points[:, 1],
            points[:, 2],
            dirs[:, 0],
            dirs[:, 1],
            dirs[:, 2],
        )

    def _orient_source_points_and_dirs(
        self,
        x_values,
        y_values,
        z_values,
        l_values,
        m_values,
        n_values,
    ):
        origin = np.asarray(self._current_source_origin(), dtype=float)
        u, v, w = self._source_frame_vectors()
        x_arr, y_arr, z_arr, l_arr, m_arr, n_arr = (
            np.asarray(values, dtype=float).reshape(-1)
            for values in (x_values, y_values, z_values, l_values, m_values, n_values)
        )
        points = (
            origin[None, :]
            + x_arr[:, None] * u[None, :]
            + y_arr[:, None] * v[None, :]
            + z_arr[:, None] * w[None, :]
        )
        dirs = (
            l_arr[:, None] * u[None, :]
            + m_arr[:, None] * v[None, :]
            + n_arr[:, None] * w[None, :]
        )
        norms = np.linalg.norm(dirs, axis=1)
        norms = np.where(norms > 1e-12, norms, 1.0)
        dirs = dirs / norms[:, None]
        return (
            points[:, 0],
            points[:, 1],
            points[:, 2],
            dirs[:, 0],
            dirs[:, 1],
            dirs[:, 2],
        )

    @staticmethod
    def _default_scene_source_spec(index: int = 0) -> dict[str, object]:
        index = max(0, int(index))
        return {
            "source_id": f"source:{index}",
            "name": f"Source {index + 1}",
            "enabled": True,
            "physical": True,
            "role": "illumination",
            "model": "Collimated disk source",
            "ray_count": 5,
            "radius": 1.0,
            "cone_deg": 0.0,
            "power": 1.0,
            "seed": index + 1,
            "source_x": 0.0,
            "source_y": 0.0,
            "source_z": 0.0,
            "source_l": 0.0,
            "source_m": 0.0,
            "source_n": 1.0,
            "angular_weight": SOURCE_ANGULAR_WEIGHT_DEFAULT,
            "waist_radius": 0.5,
            "waist_offset": 0.0,
            "m2": 1.0,
        }

    def _scene_source_spec_from_current_panel(
        self,
        *,
        source_id: str = "source:0",
        name: str = "Source 1",
    ) -> dict[str, object]:
        wavelength = float(self._current_wavelength())
        stats = self._source_statistics(wavelength=wavelength)
        model = str(stats.get("source_model", self._current_source_model()))
        physical = model != SOURCE_MODEL_DEFAULT
        ox, oy, oz = self._current_source_origin()
        dl, dm, dn = self._current_source_direction()
        spec: dict[str, object] = {
            "source_id": str(source_id or "source:0"),
            "name": str(name or "Source 1"),
            "enabled": True,
            "physical": bool(physical),
            "role": "illumination" if physical else "pupil_field_reference",
            "model": model,
            "ray_count": max(1, int(stats.get("ray_count", self._current_ray_count()))),
            "power": float(stats.get("power", self._current_source_power()) or 0.0),
            "wavelength": wavelength,
            "source_x": float(ox),
            "source_y": float(oy),
            "source_z": float(oz),
            "source_l": float(dl),
            "source_m": float(dm),
            "source_n": float(dn),
        }
        if model == "Gaussian beam":
            spec.update(
                {
                    "radius": float(stats.get("launch_radius", self._current_source_radius()) or 0.0),
                    "waist_radius": float(stats.get("waist_radius", self._current_gaussian_waist_radius()) or 0.0),
                    "waist_offset": float(stats.get("waist_offset", self._current_gaussian_waist_offset()) or 0.0),
                    "m2": float(stats.get("m2", self._current_gaussian_m2()) or 1.0),
                    "gaussian_input_mode": self._current_gaussian_input_mode(),
                    "beam_diameter": float(stats.get("beam_diameter", self._current_gaussian_beam_diameter()) or 0.0),
                    "full_divergence_mrad": float(stats.get("full_divergence_mrad", self._current_gaussian_full_divergence()) or 0.0),
                }
            )
        elif model == SOURCE_MODEL_DEFAULT:
            spec.update(
                {
                    "pupil_pattern": self._current_pupil_pattern_label(),
                    "pupil_rad": self._current_pupil_rad(),
                    "pupil_theta": self._current_pupil_theta(),
                    "radius": self._current_source_radius(),
                    "cone_deg": self._current_source_cone_angle(),
                    "seed": self._current_source_seed(),
                }
            )
        else:
            spec.update(
                {
                    "radius": float(stats.get("radius", self._current_source_radius()) or 0.0),
                    "cone_deg": float(stats.get("cone_deg", self._current_source_cone_angle()) or 0.0),
                    "seed": self._current_source_seed(),
                    "angular_weight": str(stats.get("angular_weight", self._current_source_angular_weight())),
                }
            )
        return {str(key): self._scene_source_setting_value(value) for key, value in spec.items()}

    @classmethod
    def _dedupe_scene_source_ids(cls, specs: list[dict[str, object]]) -> list[dict[str, object]]:
        return dedupe_scene_source_ids(specs)

    def _sync_source_panel_from_reference_scene_source(self, specs: list[dict[str, object]]) -> None:
        if not specs:
            return
        normalized = [dict(spec) for spec in self._normalize_scene_source_specs(specs)]
        if any(
            str(spec.get("model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip() != SOURCE_MODEL_DEFAULT
            and self._source_spec_bool(spec, "physical", True)
            for spec in normalized
        ):
            return
        spec = next(
            (
                item
                for item in normalized
                if str(item.get("model", SOURCE_MODEL_DEFAULT) or SOURCE_MODEL_DEFAULT).strip() == SOURCE_MODEL_DEFAULT
            ),
            None,
        )
        if spec is None:
            return

        def _set_float_var(attr_name: str, keys, default: float) -> None:
            self._set_optional_var(attr_name, f"{self._source_spec_float(spec, keys, default):.12g}")

        self._set_optional_var("source_model_var", SOURCE_MODEL_DEFAULT)
        self._set_optional_var("ray_count_var", str(max(1, int(round(self._source_spec_float(spec, "ray_count", self._current_ray_count(), minimum=1.0))))))
        _set_float_var("source_radius_var", ("radius", "source_radius", "launch_radius"), self._current_source_radius())
        _set_float_var("source_cone_angle_var", ("cone_deg", "source_cone_angle"), self._current_source_cone_angle())
        _set_float_var("source_power_var", ("power", "source_power"), self._current_source_power())
        self._set_optional_var("source_seed_var", str(int(round(self._source_spec_float(spec, ("seed", "source_seed"), self._current_source_seed(), minimum=0.0)))))
        pupil_pattern = str(spec.get("pupil_pattern", self._current_pupil_pattern_label()) or "").strip()
        if pupil_pattern in PUPIL_PATTERN_VALUES:
            self._set_optional_var("pupil_pattern_var", pupil_pattern)
        _set_float_var("pupil_rad_var", "pupil_rad", self._current_pupil_rad())
        _set_float_var("pupil_theta_var", "pupil_theta", self._current_pupil_theta())
        origin = self._source_spec_vector(
            spec,
            ("origin", "source_xyz", "xyz"),
            ("source_x", "source_y", "source_z"),
            self._current_source_origin(),
        )
        direction = self._source_spec_vector(
            spec,
            ("direction", "source_lmn", "lmn"),
            ("source_l", "source_m", "source_n"),
            self._current_source_direction(),
        )
        for attr_name, value in (
            ("source_x_var", origin[0]),
            ("source_y_var", origin[1]),
            ("source_z_var", origin[2]),
            ("source_l_var", direction[0]),
            ("source_m_var", direction[1]),
            ("source_n_var", direction[2]),
        ):
            self._set_optional_var(attr_name, f"{float(value):.12g}")
        self._sync_source_direction_preset_from_lmn()
        if "_left_mode_controls" in self.__dict__:
            self._sync_left_mode_controls()

    def _set_scene_source_specs(
        self,
        specs: list[dict[str, object]],
        *,
        row_order: str | None = None,
        record_history: bool = False,
        status: str | None = None,
    ) -> None:
        if record_history:
            self._begin_history_capture()
        normalized = self._normalize_scene_source_specs(specs)
        self.layout_scene_source_specs = self._dedupe_scene_source_ids(normalized)
        self._sync_source_panel_from_reference_scene_source(self.layout_scene_source_specs)
        if row_order is not None:
            self.layout_scene_row_order = normalize_source_row_order(row_order)
        if self.__dict__.get("table") is not None:
            self._sync_table()
        self._update_source_summary()
        if record_history:
            self._commit_history_capture()
        if hasattr(self, "_mark_plot_update_pending") and not bool(getattr(self, "headless", False)):
            self._mark_plot_update_pending()
        status_var = self.__dict__.get("status_var")
        if status and status_var is not None:
            status_var.set(status)

    def _scene_source_specs_for_direct_editing(self) -> list[dict[str, object]]:
        specs = [
            dict(spec)
            for spec in self._normalize_scene_source_specs(
                getattr(self, "layout_scene_source_specs", [])
            )
        ]
        if not specs:
            specs = [self._scene_source_spec_from_current_panel()]
        return self._dedupe_scene_source_ids(specs)

    @staticmethod
    def _scene_source_index_for_id(specs: list[dict[str, object]], source_id: str) -> int | None:
        target = str(source_id or "").strip()
        for index, spec in enumerate(specs):
            if str(spec.get("source_id", "") or "").strip() == target:
                return index
        return None

    def _apply_scene_source_row_action_specs(
        self,
        specs: list[dict[str, object]],
        *,
        status: str,
        record_history: bool = True,
    ) -> None:
        self._set_scene_source_specs(
            specs,
            row_order=normalize_source_row_order(
                getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)
            ),
            record_history=bool(record_history and not bool(getattr(self, "headless", False))),
            status=status,
        )

    def duplicate_scene_source_by_id(self, source_id: str, *, record_history: bool = True) -> bool:
        specs = self._scene_source_specs_for_direct_editing()
        index = self._scene_source_index_for_id(specs, source_id)
        if index is None:
            status_var = self.__dict__.get("status_var")
            if status_var is not None:
                status_var.set("Source row duplicate failed: selected source is not available.")
            return False
        duplicate = dict(specs[index])
        duplicate["source_id"] = f"{duplicate.get('source_id', f'source:{index}')}_copy"
        duplicate["name"] = f"{duplicate.get('name', f'Source {index + 1}')} Copy"
        specs.insert(index + 1, duplicate)
        specs = self._dedupe_scene_source_ids(specs)
        copied_id = str(specs[index + 1].get("source_id", "") or "")
        self._apply_scene_source_row_action_specs(
            specs,
            record_history=record_history,
            status=f"Duplicated scene source {source_id} -> {copied_id}. Click Update.",
        )
        return True

    def delete_scene_source_by_id(self, source_id: str, *, record_history: bool = True) -> bool:
        specs = self._scene_source_specs_for_direct_editing()
        index = self._scene_source_index_for_id(specs, source_id)
        if index is None:
            status_var = self.__dict__.get("status_var")
            if status_var is not None:
                status_var.set("Source row delete failed: selected source is not available.")
            return False
        if len(specs) <= 1:
            status_var = self.__dict__.get("status_var")
            if status_var is not None:
                status_var.set(
                    "Cannot delete the only scene source from the table; "
                    "use Scene Source Manager to return to Source panel fallback."
                )
            return False
        del specs[index]
        self._apply_scene_source_row_action_specs(
            specs,
            record_history=record_history,
            status=f"Deleted scene source {source_id}. Click Update.",
        )
        return True

    def move_scene_source_by_id(self, source_id: str, direction: str, *, record_history: bool = True) -> bool:
        specs = self._scene_source_specs_for_direct_editing()
        index = self._scene_source_index_for_id(specs, source_id)
        if index is None:
            status_var = self.__dict__.get("status_var")
            if status_var is not None:
                status_var.set("Source row move failed: selected source is not available.")
            return False
        step = -1 if str(direction).lower() == "up" else 1
        target = index + step
        if target < 0 or target >= len(specs):
            status_var = self.__dict__.get("status_var")
            if status_var is not None:
                status_var.set(
                    f"Scene source {source_id} is already at the "
                    f"{'top' if step < 0 else 'bottom'}."
                )
            return False
        specs[index], specs[target] = specs[target], specs[index]
        self._apply_scene_source_row_action_specs(
            specs,
            record_history=record_history,
            status=f"Moved scene source {source_id} {'up' if step < 0 else 'down'}. Click Update.",
        )
        return True

    @classmethod
    def _normalize_scene_source_specs(cls, value) -> list[dict[str, object]]:
        return normalize_scene_source_specs(value)

    @staticmethod
    def _source_spec_bool(spec: dict[str, object], key: str, default: bool) -> bool:
        return source_spec_bool(spec, key, default)

    @staticmethod
    def _source_spec_float(spec: dict[str, object], keys, default: float = 0.0, *, minimum: float | None = None) -> float:
        return source_spec_float(spec, keys, default, minimum=minimum)

    @classmethod
    def _source_spec_vector(cls, spec: dict[str, object], vector_keys, component_keys, default) -> np.ndarray:
        return source_spec_vector(spec, vector_keys, component_keys, default)

    def _scene_source_from_spec(
        self,
        spec: dict[str, object],
        index: int,
        *,
        wavelength: float,
        sample_count: int | None = None,
    ) -> SceneSource3D:
        return scene_source_from_spec(
            spec,
            index,
            wavelength=wavelength,
            sample_count=sample_count,
            default_ray_count=self._current_ray_count(),
            default_radius=self._current_source_radius(),
            default_cone_deg=self._current_source_cone_angle(),
            source_model_values=SOURCE_MODEL_VALUES,
            source_model_default=SOURCE_MODEL_DEFAULT,
            angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
        )

    def _source_statistics(self, sample_count: int | None = None, wavelength: float | None = None) -> dict[str, object]:
        source_model = self._current_source_model()
        ray_count = max(1, int(sample_count if sample_count is not None else self._current_ray_count()))
        if source_model == SOURCE_MODEL_DEFAULT:
            return {
                "source_model": source_model,
                "pupil_pattern": self._current_pupil_pattern_label(),
                "pupil_rad": self._current_pupil_rad(),
                "pupil_theta": self._current_pupil_theta(),
                "ray_count": ray_count,
                "radius": self._current_source_radius(),
                "cone_deg": self._current_source_cone_angle(),
                "seed": self._current_source_seed(),
            }
        if source_model == "Gaussian beam":
            beam_input = self._current_gaussian_beam_input(wavelength=wavelength)
            wavelength_mm = max(float(beam_input.wavelength_um) * 1e-3, 1e-12)
            waist_radius = float(beam_input.waist_radius_mm)
            m2 = float(beam_input.m2)
            power = self._current_source_power()
            z_rayleigh = float(np.pi * waist_radius * waist_radius / (wavelength_mm * m2))
            divergence = float(1000.0 * wavelength_mm * m2 / (np.pi * waist_radius))
            launch_radius = float(waist_radius * np.sqrt(1.0 + (float(beam_input.waist_offset_mm) / max(z_rayleigh, 1e-12)) ** 2))
            return {
                "source_model": source_model,
                "ray_count": ray_count,
                "input_mode": self._current_gaussian_input_mode(),
                "beam_diameter": self._current_gaussian_beam_diameter(),
                "full_divergence_mrad": self._current_gaussian_full_divergence(),
                "waist_radius": float(waist_radius),
                "launch_radius": launch_radius,
                "waist_offset": float(beam_input.waist_offset_mm),
                "m2": float(m2),
                "z_rayleigh": z_rayleigh,
                "divergence_mrad": divergence,
                "power": power,
                "power_per_ray": power / float(ray_count),
                "origin": self._current_source_origin(),
                "direction": self._current_source_direction(),
            }
        if source_model == "Collimated disk source":
            radius = self._current_source_radius()
            cone_deg = self._current_source_cone_angle()
            cone_rad = float(np.deg2rad(cone_deg))
            power = self._current_source_power()
            return {
                "source_model": source_model,
                "ray_count": ray_count,
                "radius": radius,
                "cone_deg": cone_deg,
                "na": float(np.sin(cone_rad)),
                "area": float(np.pi * radius * radius),
                "length": 0.0,
                "solid_angle": float(2.0 * np.pi * (1.0 - np.cos(cone_rad))),
                "etendue": float(np.pi * radius * radius) * float(2.0 * np.pi * (1.0 - np.cos(cone_rad))),
                "power": power,
                "power_per_ray": power / float(ray_count),
                "seed": self._current_source_seed(),
                "origin": self._current_source_origin(),
                "direction": self._current_source_direction(),
                "angular_weight": SOURCE_ANGULAR_WEIGHT_DEFAULT,
            }
        if source_model == SOURCE_MODEL_ZEMAX_RAYFILE:
            ray_count = max(1, int(sample_count if sample_count is not None else self._current_ray_count()))
            power = self._current_source_power()
            return {
                "source_model": source_model,
                "ray_count": ray_count,
                "rayfile_path": "",
                "record_count": 0,
                "power": power,
                "power_per_ray": power / float(ray_count),
                "origin": self._current_source_origin(),
                "direction": self._current_source_direction(),
            }
        radius = self._current_source_radius()
        cone_deg = self._current_source_cone_angle()
        cone_rad = float(np.deg2rad(cone_deg))
        area = float(np.pi * radius * radius) if source_model == "Random circle source" else float((2.0 * radius) ** 2)
        if source_model == "Random line source":
            area = 0.0
        elif source_model == "Random point cone":
            area = 0.0
        solid_angle = float(2.0 * np.pi * (1.0 - np.cos(cone_rad)))
        power = self._current_source_power()
        return {
            "source_model": source_model,
            "ray_count": ray_count,
            "radius": radius,
            "cone_deg": cone_deg,
            "na": float(np.sin(cone_rad)),
            "area": area,
            "length": float(2.0 * radius) if source_model == "Random line source" else 0.0,
            "solid_angle": solid_angle,
            "etendue": area * solid_angle,
            "power": power,
            "power_per_ray": power / float(ray_count),
            "seed": self._current_source_seed(),
            "origin": self._current_source_origin(),
            "direction": self._current_source_direction(),
            "angular_weight": self._current_source_angular_weight(),
        }

    def _scene_source_specs_for_trace(self, specs: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized = [dict(spec) for spec in self._normalize_scene_source_specs(specs)]
        return normalized

    @staticmethod
    def _scene_source_setting_value(value):
        return scene_source_setting_value(value)

    def _collect_scene_sources(self, *, wavelength: float | None = None, sample_count: int | None = None) -> list[SceneSource3D]:
        """Return first-class scene source records.

        The current UI exposes one Source panel.  This adapter deliberately
        turns that panel into a one-item scene-source list so later work can add
        more sources without changing the tracing/display contract again.
        """
        wavelength_value = float(self._current_wavelength() if wavelength is None else wavelength)
        scene_source_specs = self._scene_source_specs_for_trace(
            self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", []))
        )
        if scene_source_specs:
            sources = [
                self._scene_source_from_spec(
                    spec,
                    index,
                    wavelength=wavelength_value,
                    sample_count=sample_count,
                )
                for index, spec in enumerate(scene_source_specs)
            ]
            if any(bool(source.enabled) and bool(source.physical) for source in sources):
                return sources
        stats = self._source_statistics(sample_count=sample_count, wavelength=wavelength_value)
        source_model = str(stats.get("source_model", self._current_source_model()))
        physical = source_model != SOURCE_MODEL_DEFAULT
        role = "illumination" if physical else "pupil_field_reference"
        origin = np.asarray(stats.get("origin", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)
        direction = np.asarray(stats.get("direction", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)
        if origin.size < 3:
            origin = np.pad(origin, (0, 3 - origin.size), constant_values=0.0)
        if direction.size < 3:
            direction = np.pad(direction, (0, 3 - direction.size), constant_values=0.0)
            direction[2] = 1.0
        direction = direction[:3].astype(float)
        norm = float(np.linalg.norm(direction))
        if norm <= 1e-12:
            direction = np.asarray((0.0, 0.0, 1.0), dtype=float)
        else:
            direction = direction / norm

        def _optional_float(key: str) -> float | None:
            try:
                value = float(stats.get(key))
            except Exception:
                return None
            return value if np.isfinite(value) else None

        return [
            SceneSource3D(
                source_id="source:0",
                name="Source 1",
                role=role,
                model=source_model,
                enabled=True,
                physical=physical,
                origin=origin[:3].astype(float),
                direction=direction.astype(float),
                ray_count=max(1, int(stats.get("ray_count", self._current_ray_count()))),
                wavelength=wavelength_value,
                power=_optional_float("power"),
                weight_per_ray=_optional_float("power_per_ray"),
                settings={
                    str(key): self._scene_source_setting_value(value)
                    for key, value in stats.items()
                },
            )
        ]

    @staticmethod
    def _scene_source_feature_text(source: SceneSource3D) -> str:
        return scene_source_feature_text(
            source,
            source_model_default=SOURCE_MODEL_DEFAULT,
            source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE,
            pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
        )

    @staticmethod
    def _scene_source_detail_text(source: SceneSource3D) -> str:
        return scene_source_detail_text(source, source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE)

    def _atmos_float(self, attr_name: str, default: float, *, minimum: float | None = None, maximum: float | None = None) -> float:
        var = self.__dict__.get(attr_name)
        try:
            value = float(var.get()) if var is not None else float(default)
        except Exception:
            value = float(default)
        if minimum is not None:
            value = max(float(minimum), value)
        if maximum is not None:
            value = min(float(maximum), value)
        return float(value)

    def _atmos_int(self, attr_name: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
        var = self.__dict__.get(attr_name)
        try:
            value = int(float(var.get())) if var is not None else int(default)
        except Exception:
            value = int(default)
        value = max(int(minimum), int(value))
        if maximum is not None:
            value = min(int(maximum), value)
        return int(value)

    def _current_atmosphere_settings(self) -> dict[str, float | int]:
        w_min = self._atmos_float("atmos_wavelength_min_var", 0.45, minimum=0.1)
        w_max = self._atmos_float("atmos_wavelength_max_var", 0.75, minimum=0.1)
        if w_max < w_min:
            w_min, w_max = w_max, w_min
        return {
            "wavelength_min": float(w_min),
            "wavelength_max": float(w_max),
            "wavelength_count": self._atmos_int("atmos_wavelength_count_var", 11, minimum=2, maximum=101),
            "zenith_deg": self._atmos_float("atmos_zenith_deg_var", 45.0, minimum=0.0, maximum=89.0),
            "temperature_k": self._atmos_float("atmos_temperature_k_var", 283.15, minimum=150.0, maximum=350.0),
            "pressure_pa": self._atmos_float("atmos_pressure_pa_var", 101300.0, minimum=1.0),
            "humidity": self._atmos_float("atmos_humidity_var", 0.5, minimum=0.0, maximum=1.0),
            "co2_ppm": self._atmos_float("atmos_co2_ppm_var", 400.0, minimum=0.0),
            "latitude_deg": self._atmos_float("atmos_latitude_deg_var", 31.0, minimum=-90.0, maximum=90.0),
            "altitude_m": self._atmos_float("atmos_altitude_m_var", 2800.0),
        }

    def _atmosphere_wavelength_samples(self) -> np.ndarray:
        settings = self._current_atmosphere_settings()
        return np.linspace(
            float(settings["wavelength_min"]),
            float(settings["wavelength_max"]),
            int(settings["wavelength_count"]),
        )

    def _current_atmos_plot_mode(self) -> str:
        value = getattr(self, "atmos_plot_mode_var", None)
        if value is None:
            return ATMOS_PLOT_MODE_DEFAULT
        mode = value.get().strip()
        if mode in ATMOS_PLOT_MODE_VALUES:
            return mode
        return ATMOS_PLOT_MODE_DEFAULT

    def _format_atmosphere_summary(self) -> str:
        settings = self._current_atmosphere_settings()
        observatory = self._current_atmos_observatory()
        prefix = "" if observatory == "Manual" else f"{observatory}: "
        return (
            f"{prefix}{self._current_atmos_plot_mode()}; "
            f"{float(settings['wavelength_min']):.4g}-{float(settings['wavelength_max']):.4g} um, "
            f"Z={float(settings['zenith_deg']):.4g} deg, "
            f"T={float(settings['temperature_k']):.4g} K, P={float(settings['pressure_pa']):.4g} Pa, "
            f"RH={float(settings['humidity']):.3g}."
        )

    def _update_atmosphere_summary(self) -> None:
        summary_var = self.__dict__.get("atmosphere_summary_var")
        if summary_var is None:
            return
        try:
            summary_var.set(self._format_atmosphere_summary())
        except Exception:
            summary_var.set("")

    @staticmethod
    def _atmos_observatory_records() -> dict[str, dict]:
        records = getattr(Kos, "observatories", {})
        return records if isinstance(records, dict) else {}

    @classmethod
    def _atmos_observatory_names(cls) -> list[str]:
        return ["Manual", *sorted(cls._atmos_observatory_records())]

    def _current_atmos_observatory(self) -> str:
        var = self.__dict__.get("atmos_observatory_var")
        value = str(var.get()).strip() if var is not None else "Manual"
        return value if value in self._atmos_observatory_names() else "Manual"

    def _apply_atmos_observatory(self, name: str) -> bool:
        record = self._atmos_observatory_records().get(str(name).strip())
        if not isinstance(record, dict):
            return False
        mapping = {
            "T": "atmos_temperature_k_var",
            "p": "atmos_pressure_pa_var",
            "RH": "atmos_humidity_var",
            "xc": "atmos_co2_ppm_var",
            "latitude": "atmos_latitude_deg_var",
            "altitude": "atmos_altitude_m_var",
        }
        for key, attr_name in mapping.items():
            var = self.__dict__.get(attr_name)
            if var is not None and key in record:
                var.set(f"{float(record[key]):g}")
        self._update_atmosphere_summary()
        return True

    def _on_atmos_observatory_changed(self, _event=None) -> None:
        name = self._current_atmos_observatory()
        if name != "Manual":
            self._apply_atmos_observatory(name)
        else:
            self._update_atmosphere_summary()
        if hasattr(self, "status_var"):
            self.status_var.set(f"Atmosphere preset set to {name}. Click Update.")
        self._mark_plot_update_pending()

    def _format_source_summary(self, sample_count: int | None = None) -> str:
        if self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", [])):
            sources = self._collect_scene_sources(sample_count=sample_count)
            return scene_sources_summary_text(sources)
        stats = self._source_statistics(sample_count)
        return source_panel_summary_text(
            stats,
            source_model_default=SOURCE_MODEL_DEFAULT,
            source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE,
            pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
            gaussian_input_mode_default=GAUSSIAN_INPUT_MODE_DEFAULT,
            angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
        )

    def _update_source_summary(self) -> None:
        source_summary_var = self.__dict__.get("source_summary_var")
        if source_summary_var is None:
            return
        try:
            source_summary_var.set(self._format_source_summary())
        except Exception as exc:
            source_summary_var.set(f"Source input invalid: {_short_error_message(exc)}")

    def _current_ray_height_factor(self) -> float:
        try:
            factor = float(self._left_mode_text("ray_height_factor_var", "0.8"))
        except ValueError:
            factor = 0.8
        return max(min(factor, 1.5), 0.05)

    def _pupil_pattern_bundle(self, pupil):
        pupil.rad = self._current_pupil_rad()
        pupil.theta = self._current_pupil_theta()
        if str(getattr(pupil, "Ptype", "")).strip().lower() != "rand":
            return tuple(np.asarray(values, dtype=float) for values in pupil.Pattern2Field())
        numpy_state = np.random.get_state()
        try:
            np.random.seed(self._current_source_seed())
            return tuple(np.asarray(values, dtype=float) for values in pupil.Pattern2Field())
        finally:
            np.random.set_state(numpy_state)

    @staticmethod
    def _random_cone_directions(ray_count: int, cone_angle_deg: float, rng: np.random.Generator):
        count = max(1, int(ray_count))
        cone_rad = max(float(np.deg2rad(cone_angle_deg)), 1e-12)
        cos_min = float(np.cos(cone_rad))
        cos_theta = rng.uniform(cos_min, 1.0, count)
        sin_theta = np.sqrt(np.clip(1.0 - cos_theta * cos_theta, 0.0, 1.0))
        phi = rng.uniform(0.0, 2.0 * np.pi, count)
        return (
            sin_theta * np.cos(phi),
            sin_theta * np.sin(phi),
            cos_theta,
        )

    def _source_angular_weight_function(self, cone_angle_deg: float):
        weight = self._current_source_angular_weight()
        if weight == SOURCE_ANGULAR_WEIGHT_DEFAULT:
            return 0
        cone_rad = max(float(np.deg2rad(cone_angle_deg)), 1e-12)
        if weight == "Cosine-weighted":
            return lambda angle: np.clip(np.cos(angle), 0.0, None)
        if weight == "Gaussian center":
            sigma = max(cone_rad * 0.35, 1e-9)
            return lambda angle, sigma=sigma: np.exp(-0.5 * (np.asarray(angle, dtype=float) / sigma) ** 2)
        if weight == "Edge-weighted":
            return lambda angle, cone_rad=cone_rad: np.maximum(np.asarray(angle, dtype=float) / cone_rad, 1e-9)
        return 0

    @staticmethod
    def _sample_source_disk_points(radius: float, ray_count: int) -> np.ndarray:
        count = max(1, int(ray_count))
        radius = max(float(radius), 0.0)
        if count == 1 or radius <= 1e-12:
            return np.asarray([[0.0, 0.0]], dtype=float)
        if count <= 9:
            # Low-count source bundles are primarily a 2-D layout preview. Use
            # equal meridional spacing so adjacent rays have equal YZ gaps, but
            # keep a margin for tilted finite plates whose projected clear
            # aperture is smaller than their nominal diameter.
            edge = radius * min(
                np.sqrt((count - 1) / float(count)),
                SOURCE_MERIDIONAL_PREVIEW_MAX_RADIUS_FRACTION,
            )
            y_values = np.linspace(-edge, edge, count)
            return np.column_stack((np.zeros(count, dtype=float), y_values.astype(float)))
        points = [[0.0, 0.0]]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        for index in range(1, count):
            # Keep preview rays inside the source disk. Placing the last ray
            # exactly on the edge makes finite apertures clip one path but
            # not its sibling because of floating-point and tilted-surface
            # coordinate transforms.
            r = radius * np.sqrt(index / float(count))
            theta = index * golden_angle
            points.append([r * np.cos(theta), r * np.sin(theta)])
        return np.asarray(points, dtype=float)

    @staticmethod
    def _sample_reference_disk_points_3d(radius: float, ray_count: int) -> np.ndarray:
        count = max(1, int(ray_count))
        radius = max(float(radius), 0.0)
        if count == 1 or radius <= 1e-12:
            return np.asarray([[0.0, 0.0]], dtype=float)
        points = [[0.0, 0.0]]
        golden_angle = np.pi * (3.0 - np.sqrt(5.0))
        for index in range(1, count):
            r = radius * np.sqrt(index / float(count))
            theta = index * golden_angle
            points.append([r * np.cos(theta), r * np.sin(theta)])
        return np.asarray(points, dtype=float)

    def _build_gaussian_source_bundle(self, sample_count: int | None = None):
        ray_count = max(1, int(sample_count if sample_count is not None else self._current_ray_count()))
        beam_input = self._current_gaussian_beam_input()
        waist_radius = float(beam_input.waist_radius_mm)
        wavelength_mm = max(float(beam_input.wavelength_um) * 1e-3, 1e-12)
        z_rayleigh = np.pi * waist_radius * waist_radius / (wavelength_mm * float(beam_input.m2))
        waist_offset = float(beam_input.waist_offset_mm)
        q_value = complex(waist_offset, float(z_rayleigh))
        inverse_q = 1.0 / q_value if abs(q_value) > 1e-18 else complex(0.0, 0.0)
        real_inverse = float(np.real(inverse_q))
        wavefront_radius = np.inf if abs(real_inverse) <= 1e-18 else float(1.0 / real_inverse)
        launch_radius = waist_radius * np.sqrt(1.0 + (waist_offset / max(float(z_rayleigh), 1e-12)) ** 2)
        disk_points = self._sample_source_disk_points(launch_radius, ray_count)
        x_offsets = disk_points[:, 0].astype(float)
        y_offsets = disk_points[:, 1].astype(float)
        x_slopes = np.zeros_like(x_offsets)
        y_slopes = np.zeros_like(y_offsets)
        if np.isfinite(wavefront_radius) and abs(wavefront_radius) > 1e-12:
            x_slopes = x_offsets / wavefront_radius
            y_slopes = y_offsets / wavefront_radius
        l_values = x_slopes.astype(float)
        m_values = y_slopes.astype(float)
        n_values = np.ones(ray_count, dtype=float)
        norms = np.sqrt(l_values * l_values + m_values * m_values + n_values * n_values)
        norms = np.where(norms > 1e-12, norms, 1.0)
        return self._orient_source_points_and_dirs(
            x_offsets,
            y_offsets,
            np.zeros(ray_count, dtype=float),
            l_values / norms,
            m_values / norms,
            n_values / norms,
        )

    def _build_random_source_bundle(self, sample_count: int | None = None):
        source_model = self._current_source_model()
        if source_model == SOURCE_MODEL_DEFAULT:
            return None
        if source_model == "Gaussian beam":
            return self._build_gaussian_source_bundle(sample_count)
        ray_count = max(1, int(sample_count if sample_count is not None else self._current_ray_count()))
        radius = max(self._current_source_radius(), 1e-9)
        if source_model == "Collimated disk source":
            disk_points = self._sample_source_disk_points(radius, ray_count)
            cone_angle = self._current_source_cone_angle()
            if cone_angle > 1e-12:
                rng = np.random.default_rng(self._current_source_seed())
                l_values, m_values, n_values = self._random_cone_directions(ray_count, cone_angle, rng)
            else:
                l_values = np.zeros(ray_count, dtype=float)
                m_values = np.zeros(ray_count, dtype=float)
                n_values = np.ones(ray_count, dtype=float)
            return self._orient_source_points_and_dirs(
                disk_points[:, 0].astype(float),
                disk_points[:, 1].astype(float),
                np.zeros(ray_count, dtype=float),
                l_values,
                m_values,
                n_values,
            )
        cone_angle = max(self._current_source_cone_angle(), 1e-9)
        if source_model in {"Random circle source", "Random square source"}:
            source = Kos.SourceRnd()
            source.num = ray_count
            source.dim = radius
            source.field = cone_angle
            source.type = 0 if source_model == "Random circle source" else 1
            source.fun = self._source_angular_weight_function(cone_angle)
            py_state = random.getstate()
            np_state = np.random.get_state()
            try:
                seed = self._current_source_seed()
                random.seed(seed)
                np.random.seed(seed)
                l_values, m_values, n_values, x_values, y_values, z_values = source.rays()
            finally:
                random.setstate(py_state)
                np.random.set_state(np_state)
        else:
            rng = np.random.default_rng(self._current_source_seed())
            l_values, m_values, n_values = self._random_cone_directions(ray_count, cone_angle, rng)
            z_values = np.zeros(ray_count, dtype=float)
            if source_model == "Random line source":
                x_values = rng.uniform(-radius, radius, ray_count)
                y_values = np.zeros(ray_count, dtype=float)
            else:
                x_values = np.zeros(ray_count, dtype=float)
                y_values = np.zeros(ray_count, dtype=float)
        return self._orient_source_points_and_dirs(
            np.asarray(x_values, dtype=float),
            np.asarray(y_values, dtype=float),
            np.asarray(z_values, dtype=float),
            np.asarray(l_values, dtype=float),
            np.asarray(m_values, dtype=float),
            np.asarray(n_values, dtype=float),
        )

    def _build_scene_source_bundle(self, source: SceneSource3D):
        settings = dict(source.settings or {})
        model = str(source.model or settings.get("source_model", "Collimated disk source"))
        ray_count = max(1, int(source.ray_count))
        radius = self._source_spec_float(settings, ("radius", "source_radius", "launch_radius"), 1.0, minimum=0.0)
        origin = np.asarray(source.origin, dtype=float)
        direction = np.asarray(source.direction, dtype=float)
        if model == SOURCE_MODEL_ZEMAX_RAYFILE:
            raw_rayfile_path = str(settings.get("rayfile_path", "") or "").strip()
            if not raw_rayfile_path:
                return None
            rayfile_path = Path(raw_rayfile_path).expanduser()
            if not rayfile_path.is_absolute():
                rayfile_path = _preferred_existing_path(
                    Path.cwd() / rayfile_path,
                    PROJECT_ROOT / rayfile_path,
                    ATTACHMENT_DIR / rayfile_path,
                )
            if not rayfile_path.exists():
                return None
            try:
                preview_cone = self._source_spec_float(
                    settings,
                    ("rayfile_preview_cone_angle_deg", "preview_cone_angle_deg"),
                    0.0,
                    minimum=0.0,
                )
                if preview_cone > 0.0:
                    default_candidates = max(ray_count, min(25000, max(2000, ray_count * 200)))
                    candidate_count = int(
                        self._source_spec_float(
                            settings,
                            ("rayfile_preview_candidates", "preview_candidates"),
                            default_candidates,
                            minimum=float(ray_count),
                        )
                    )
                else:
                    candidate_count = ray_count
                x_values, y_values, z_values, l_values, m_values, n_values, _flux = sample_zemax_rayfile(rayfile_path, candidate_count)
            except Exception as exc:
                if hasattr(self, "status_var"):
                    self.status_var.set(f"Zemax rayfile source unavailable: {_short_error_message(exc)}")
                return None
            if len(np.asarray(x_values)) <= 0:
                return None
            if preview_cone > 0.0:
                directions = np.column_stack(
                    (
                        np.asarray(l_values, dtype=float),
                        np.asarray(m_values, dtype=float),
                        np.asarray(n_values, dtype=float),
                    )
                )
                norms = np.linalg.norm(directions, axis=1)
                norms = np.where(norms > 1e-12, norms, 1.0)
                axis_dot = directions[:, 2] / norms
                cutoff = float(np.cos(np.deg2rad(min(float(preview_cone), 89.999))))
                candidates = np.where(axis_dot >= cutoff)[0]
                if candidates.size < ray_count:
                    candidates = np.argsort(axis_dot)[-ray_count:]
                elif candidates.size > ray_count:
                    candidates = candidates[np.linspace(0, candidates.size - 1, ray_count, dtype=int)]
                candidates = np.asarray(sorted(set(int(index) for index in candidates)), dtype=int)
                x_values = np.asarray(x_values, dtype=float)[candidates]
                y_values = np.asarray(y_values, dtype=float)[candidates]
                z_values = np.asarray(z_values, dtype=float)[candidates]
                l_values = np.asarray(l_values, dtype=float)[candidates]
                m_values = np.asarray(m_values, dtype=float)[candidates]
                n_values = np.asarray(n_values, dtype=float)[candidates]
            return self._orient_source_points_and_dirs_for_source(
                origin,
                direction,
                np.asarray(x_values, dtype=float),
                np.asarray(y_values, dtype=float),
                np.asarray(z_values, dtype=float),
                np.asarray(l_values, dtype=float),
                np.asarray(m_values, dtype=float),
                np.asarray(n_values, dtype=float),
            )
        if model == "Gaussian beam":
            waist_radius = self._source_spec_float(settings, ("waist_radius", "gaussian_waist_radius"), max(radius, 0.5), minimum=1e-9)
            waist_offset = self._source_spec_float(settings, ("waist_offset", "gaussian_waist_offset"), 0.0)
            m2 = self._source_spec_float(settings, ("m2", "gaussian_m2"), 1.0, minimum=1e-9)
            wavelength_um = float(source.wavelength if source.wavelength is not None else self._current_wavelength())
            wavelength_mm = max(wavelength_um * 1e-3, 1e-12)
            z_rayleigh = np.pi * waist_radius * waist_radius / (wavelength_mm * m2)
            q_value = complex(waist_offset, float(z_rayleigh))
            inverse_q = 1.0 / q_value if abs(q_value) > 1e-18 else complex(0.0, 0.0)
            real_inverse = float(np.real(inverse_q))
            wavefront_radius = np.inf if abs(real_inverse) <= 1e-18 else float(1.0 / real_inverse)
            launch_radius = waist_radius * np.sqrt(1.0 + (waist_offset / max(float(z_rayleigh), 1e-12)) ** 2)
            disk_points = self._sample_source_disk_points(launch_radius, ray_count)
            x_offsets = disk_points[:, 0].astype(float)
            y_offsets = disk_points[:, 1].astype(float)
            x_slopes = np.zeros_like(x_offsets)
            y_slopes = np.zeros_like(y_offsets)
            if np.isfinite(wavefront_radius) and abs(wavefront_radius) > 1e-12:
                x_slopes = x_offsets / wavefront_radius
                y_slopes = y_offsets / wavefront_radius
            l_values = x_slopes.astype(float)
            m_values = y_slopes.astype(float)
            n_values = np.ones(ray_count, dtype=float)
            norms = np.sqrt(l_values * l_values + m_values * m_values + n_values * n_values)
            norms = np.where(norms > 1e-12, norms, 1.0)
            return self._orient_source_points_and_dirs_for_source(
                origin,
                direction,
                x_offsets,
                y_offsets,
                np.zeros(ray_count, dtype=float),
                l_values / norms,
                m_values / norms,
                n_values / norms,
            )
        if model == "Collimated disk source":
            disk_points = self._sample_source_disk_points(radius, ray_count)
            cone_angle = self._source_spec_float(settings, ("cone_deg", "source_cone_angle"), 0.0, minimum=0.0)
            if cone_angle > 1e-12:
                seed = int(round(self._source_spec_float(settings, "seed", 1, minimum=0.0))) % (2**32 - 1)
                rng = np.random.default_rng(seed)
                l_values, m_values, n_values = self._random_cone_directions(ray_count, cone_angle, rng)
            else:
                l_values = np.zeros(ray_count, dtype=float)
                m_values = np.zeros(ray_count, dtype=float)
                n_values = np.ones(ray_count, dtype=float)
            return self._orient_source_points_and_dirs_for_source(
                origin,
                direction,
                disk_points[:, 0].astype(float),
                disk_points[:, 1].astype(float),
                np.zeros(ray_count, dtype=float),
                l_values,
                m_values,
                n_values,
            )
        seed = int(round(self._source_spec_float(settings, "seed", 1, minimum=0.0))) % (2**32 - 1)
        rng = np.random.default_rng(seed)
        cone_angle = self._source_spec_float(settings, ("cone_deg", "source_cone_angle"), 1e-9, minimum=0.0)
        l_values, m_values, n_values = self._random_cone_directions(ray_count, max(cone_angle, 1e-9), rng)
        z_values = np.zeros(ray_count, dtype=float)
        if model == "Random circle source":
            r = radius * np.sqrt(rng.uniform(0.0, 1.0, ray_count))
            theta = rng.uniform(0.0, 2.0 * np.pi, ray_count)
            x_values = r * np.cos(theta)
            y_values = r * np.sin(theta)
        elif model == "Random square source":
            x_values = rng.uniform(-radius, radius, ray_count)
            y_values = rng.uniform(-radius, radius, ray_count)
        elif model == "Random line source":
            x_values = rng.uniform(-radius, radius, ray_count)
            y_values = np.zeros(ray_count, dtype=float)
        else:
            x_values = np.zeros(ray_count, dtype=float)
            y_values = np.zeros(ray_count, dtype=float)
        return self._orient_source_points_and_dirs_for_source(
            origin,
            direction,
            np.asarray(x_values, dtype=float),
            np.asarray(y_values, dtype=float),
            z_values,
            np.asarray(l_values, dtype=float),
            np.asarray(m_values, dtype=float),
            np.asarray(n_values, dtype=float),
        )

    def _build_scene_source_bundles(self, wavelength: float) -> tuple[list[tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]], list[SceneSource3D]]:
        if not self._normalize_scene_source_specs(getattr(self, "layout_scene_source_specs", [])):
            return [], []
        bundles = []
        sources = []
        for source in self._collect_scene_sources(wavelength=wavelength):
            if not bool(source.enabled) or not bool(source.physical):
                continue
            bundle = self._build_scene_source_bundle(source)
            if bundle is None or len(np.asarray(bundle[0])) <= 0:
                continue
            bundles.append(bundle)
            sources.append(source)
        return bundles, sources

    def _trace_terminal_policy_metadata(self, trace_state: dict[str, object] | None = None) -> dict[str, object]:
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
            except Exception:
                trace_state = {"use_nonseq": False}
        if not bool(trace_state.get("use_nonseq")):
            return {}
        detectors = sorted(int(index) for index in self._scene_detector_surface_indices(trace_state))
        return {
            "terminal_target_surface": self._current_nonseq_target_surface_index(),
            "terminal_detector_surfaces": detectors,
            "terminal_policy_source": "ui_nonseq_trace_request",
        }

    def _launch_metadata_for_trace(
        self,
        trace_state: dict[str, object] | None = None,
        *,
        sampling_mode: str | None = None,
    ) -> dict[str, object]:
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=self.__dict__.get("last_system"))
            except Exception:
                trace_state = {}
        try:
            summary = self._field_launch_sample_summary()
        except Exception:
            summary = {
                "requested": 1,
                "effective": 1,
                "basis": "",
                "unit": "",
                "min": 0.0,
                "max": 0.0,
                "active": True,
            }
        try:
            ray_count = int(self._current_ray_count())
        except Exception:
            ray_count = 1
        try:
            pupil_pattern = str(self._current_pupil_pattern_label())
        except Exception:
            pupil_pattern = ""
        return {
            "launch_field_requested": int(summary.get("requested", 1) or 1),
            "launch_field_effective": int(summary.get("effective", 1) or 1),
            "launch_field_basis": str(summary.get("basis", "") or ""),
            "launch_field_unit": str(summary.get("unit", "") or ""),
            "launch_field_min": float(summary.get("min", 0.0) or 0.0),
            "launch_field_max": float(summary.get("max", 0.0) or 0.0),
            "launch_field_active": bool(summary.get("active", True)),
            "launch_ray_count": ray_count,
            "launch_pupil_pattern": pupil_pattern,
            "launch_trace_intent": str(trace_state.get("active", "") or ""),
            "launch_sampling_mode": str(sampling_mode or "ui_preview"),
        }

    def _source_metadata_for_bundle(
        self,
        bundle,
        wavelength: float,
        source: SceneSource3D | None = None,
        terminal_policy: dict[str, object] | None = None,
        launch_metadata: dict[str, object] | None = None,
    ) -> list[dict[str, object]]:
        x_values, y_values, z_values, l_values, m_values, n_values = (
            np.asarray(values, dtype=float).reshape(-1) for values in bundle
        )
        ray_count = len(x_values)
        if ray_count <= 0:
            return []
        if source is None:
            sources = self._collect_scene_sources(wavelength=wavelength, sample_count=ray_count)
            source = sources[0] if sources else SceneSource3D()
        source_model = str(source.model or self._current_source_model())
        source_power = np.nan if source.power is None else float(source.power)
        source_weight = np.nan if source.weight_per_ray is None else float(source.weight_per_ray)
        terminal_policy = dict(terminal_policy or {})
        launch_metadata = dict(launch_metadata or {})
        metadata: list[dict[str, object]] = []
        for index in range(ray_count):
            record = {
                "source_xyz": [float(x_values[index]), float(y_values[index]), float(z_values[index])],
                "source_lmn": [float(l_values[index]), float(m_values[index]), float(n_values[index])],
                "source_power": source_power,
                "source_weight": source_weight,
                "source_id": source.source_id,
                "source_name": source.name,
                "source_role": source.role,
                "source_model": source_model,
                "source_wavelength": float(wavelength),
            }
            record.update(launch_metadata)
            record.update(terminal_policy)
            metadata.append(record)
        return metadata
