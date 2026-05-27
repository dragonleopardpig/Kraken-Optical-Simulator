"""Analysis reports, ray inspectors, detector maps, and scene graph UI helpers.

This mixin keeps report/data orchestration methods available on
``KrakenLayoutEditor`` while moving the large inspector/export/report block out
of the main editor coordinator.
"""

from __future__ import annotations

from pathlib import Path
import re

import numpy as np

from KrakenOS.UI.branch_gaussian_q_report import (
    branch_gaussian_q_summary_text,
    collect_branch_gaussian_q_records,
    default_branch_gaussian_q_beam,
)
from KrakenOS.UI.branch_throughput_analysis import (
    branch_output_label,
    branch_throughput_filter_choices,
    branch_throughput_filter_matches,
    collect_branch_throughput_records,
    filtered_branch_throughput_records,
    normalize_branch_throughput_filter_label,
)
from KrakenOS.UI.coherent_detector_analysis import COHERENT_SUM_MODE_DEFAULT, normalize_coherent_sum_mode
from KrakenOS.UI.detector_aperture_analysis import collect_detector_aperture_records, detector_aperture_record_status
from KrakenOS.UI.panels.main_branch_gaussian_q_dialog import MainBranchGaussianQDialog
from KrakenOS.UI.panels.main_branch_throughput_report_dialog import MainBranchThroughputReportDialog
from KrakenOS.UI.panels.main_detector_aperture_report_dialog import MainDetectorApertureReportDialog
from KrakenOS.UI.panels.main_nonseq_scene_graph_dialog import MainNonSequentialSceneGraphDialog
from KrakenOS.UI.panels.main_path_detector_analysis import MainPathDetectorAnalysis
from KrakenOS.UI.panels.main_ray_trace_inspectors import MainRayTraceInspectorDialogs
from KrakenOS.UI.panels.main_source_illumination_report_dialog import MainSourceIlluminationReportDialog
from KrakenOS.UI.layout_plot_controller import sequential_focus_diagnostic, trace_preview_summary
from KrakenOS.UI.scene_builder import (
    build_scene_boundary_faces,
    build_scene_bundle,
    build_scene_optical_volumes,
    build_scene_placements,
    build_scene_targets,
    scene_bundle_ray_analysis_records,
)
from KrakenOS.UI.scene_geometry import (
    RayBranch3D,
    SceneBundle,
    ScenePlacement3D,
    SceneTarget3D,
    ray_path_reaches_image_from_events,
)
from KrakenOS.UI.scene_row_mapping import SCENE_ROW_SOURCE, SOURCE_ROW_ORDER_DEFAULT, build_scene_row_mapping, normalize_source_row_order
from KrakenOS.UI.services.beam_scatter_metadata import (
    BEAM_SPLITTER_ADVANCED_ATTR,
    DIFFUSE_SCATTER_ADVANCED_ATTR,
    _beam_splitter_summary,
    _diffuse_scatter_summary,
)
from KrakenOS.UI.services.element_scene_metadata import ELEMENT_ARM_ROLE_DEFAULT, _normalize_detector_settings
from KrakenOS.UI.services.error_map_metadata import _error_map_arrays
from KrakenOS.UI.services.nonseq_scene_graph_records import NonSequentialSceneGraphRecordService
from KrakenOS.UI.services.optical_solid_geometry import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    inspect_stl_mesh,
    short_stl_mesh_diagnostics,
)
from KrakenOS.UI.services.ray_inspector_records import RayInspectorRecordService
from KrakenOS.UI.services.row_spec_contracts import _requires_scalar_trace
from KrakenOS.UI.source_illumination_analysis import (
    collect_source_illumination_records,
    empty_source_illumination_samples,
    source_illumination_hit_samples_from_records,
    source_illumination_map_data_from_samples,
    source_illumination_map_extent,
)
from KrakenOS.UI.source_trace_helpers import SOURCE_MODEL_DEFAULT
from KrakenOS.UI.trace_intent import BEAM_SPLITTER_SURFACE, DIFFUSE_OBJECT_SURFACE, OBJECT_TARGET_SURFACE

ANALYSIS_PATH_FILTER_DEFAULT = "All paths"
RAY_DISPLAY_ALL = "All rays"
RAY_DISPLAY_DETECTOR = "Detector hits"
RAY_DISPLAY_MISSED_DETECTOR = "Missed detector"
RAY_DISPLAY_ABSORBED = "Absorbed"
RAY_DISPLAY_ESCAPED = "Escaped"
RAY_DISPLAY_STOPPED = "Stopped / diagnostic"
RAY_DISPLAY_SPLITTER = "Beam-splitter paths"
RAY_DISPLAY_VALUES = (
    RAY_DISPLAY_ALL,
    RAY_DISPLAY_DETECTOR,
    RAY_DISPLAY_MISSED_DETECTOR,
    RAY_DISPLAY_ABSORBED,
    RAY_DISPLAY_ESCAPED,
    RAY_DISPLAY_STOPPED,
    RAY_DISPLAY_SPLITTER,
)
RAY_DISPLAY_DEFAULT = RAY_DISPLAY_ALL


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module

def _normalize_path_filter_label(value: object) -> str:
    return normalize_branch_throughput_filter_label(value)


def _normalize_coherent_sum_mode(value: object) -> str:
    return normalize_coherent_sum_mode(value)


def _short_error_message(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "..."
    return text


class AnalysisReportsMixin:
    def _format_ray_inspector_value(value) -> str:
        try:
            numeric = float(value)
        except Exception:
            text = str(value).strip()
            return text if text else "-"
        if not np.isfinite(numeric):
            return "-"
        return f"{numeric:.6g}"

    def _ray_detector_aperture_record(self, record: dict[str, object]) -> dict[str, object]:
        return detector_aperture_record_status(
            record,
            detector_surface_indices=self._scene_detector_surface_indices(),
        )

    def _ray_detector_aperture_table_values(self, record: dict[str, object]) -> tuple[str, str]:
        aperture = self._ray_detector_aperture_record(record)
        status = str(aperture.get("detector_aperture_status", "") or "").strip()
        surface = aperture.get("detector_aperture_surface", "")
        try:
            surface_text = f"S{int(surface)}"
        except Exception:
            surface_text = ""
        if status == "hit":
            label = f"Hit {surface_text}".strip()
        elif status == "miss":
            label = f"Miss {surface_text}".strip()
        elif status == "bypass":
            label = f"Bypass {surface_text}".strip()
        else:
            label = "-"
        return label, self._format_ray_inspector_value(aperture.get("detector_aperture_margin_mm", ""))

    def _trace_preview_summary(self, rays=None, bundle: SceneBundle | None = None) -> dict[str, object]:
        rays = self.last_rays if rays is None else rays
        bundle = self._last_scene_bundle if bundle is None else bundle
        trace_state = self._resolved_trace_mode()
        row_specs = self._serializable_row_specs()
        scalar_required = _requires_scalar_trace(row_specs)
        batch_capable = (not scalar_required) and hasattr(self.last_system, "BatchTrace") and hasattr(rays, "batch_push")
        backend = str(getattr(self, "_last_preview_trace_backend", "") or "")
        return trace_preview_summary(
            rays=rays,
            bundle=bundle,
            trace_state=trace_state,
            final_surface_index=max(0, len(self.rows) - 1),
            scalar_required=scalar_required,
            batch_capable=batch_capable,
            backend=backend,
        )

    def _sequential_focus_diagnostic(
        self,
        rays=None,
        trace_summary: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return sequential_focus_diagnostic(
            rays=self.last_rays if rays is None else rays,
            final_surface_index=max(0, len(self.rows) - 1),
            trace_summary=trace_summary if trace_summary is not None else self._trace_preview_summary(rays),
            object_mode=self._current_object_mode(),
            field_type=self._current_field_type(),
            object_distance=self._current_object_distance(),
        )

    @staticmethod
    def _raykeeper_array(rays, seq_name: str, ray_index: int, *, dtype=float) -> np.ndarray:
        seq = getattr(rays, seq_name, ())
        if seq is None or ray_index >= len(seq):
            return np.empty(0, dtype=dtype)
        try:
            return np.asarray(seq[ray_index], dtype=dtype).ravel()
        except Exception:
            try:
                return np.asarray(seq[ray_index]).ravel()
            except Exception:
                return np.empty(0, dtype=dtype)

    @staticmethod
    def _finite_mean(values: list[float] | np.ndarray) -> float | None:
        arr = np.asarray(values, dtype=float).ravel()
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            return None
        return float(np.mean(arr))

    @staticmethod
    def _format_percent_value(value: float | None) -> str:
        if value is None or not np.isfinite(float(value)):
            return "-"
        return f"{100.0 * float(value):.4g}%"

    def _polarization_summary(self, rays=None) -> dict[str, object]:
        rays = self.last_rays if rays is None else rays
        if rays is None:
            return {
                "total_rays": 0,
                "image_rays": 0,
                "mean_tt": None,
                "image_mean_tt": None,
                "mean_tp": None,
                "mean_ts": None,
                "mean_rp": None,
                "mean_rs": None,
                "mean_ps_transmission_split": None,
                "mean_ps_reflection_split": None,
                "coated_surface_count": 0,
                "surface_rows": [],
            }

        final_surface = max(0, len(self.rows) - 1)
        total_rays = len(getattr(rays, "SURFACE", ()) or ())
        all_tt: list[float] = []
        image_tt: list[float] = []
        all_tp: list[float] = []
        all_ts: list[float] = []
        all_rp: list[float] = []
        all_rs: list[float] = []
        trans_split: list[float] = []
        refl_split: list[float] = []
        per_surface: dict[int, dict[str, list[float]]] = {}

        for ray_index in range(total_rays):
            surface_arr = self._raykeeper_array(rays, "SURFACE", ray_index, dtype=int)
            tp_arr = self._raykeeper_array(rays, "TP", ray_index, dtype=float)
            ts_arr = self._raykeeper_array(rays, "TS", ray_index, dtype=float)
            rp_arr = self._raykeeper_array(rays, "RP", ray_index, dtype=float)
            rs_arr = self._raykeeper_array(rays, "RS", ray_index, dtype=float)
            ttbe_arr = self._raykeeper_array(rays, "TTBE", ray_index, dtype=float)
            tt_arr = self._raykeeper_array(rays, "TT", ray_index, dtype=float)

            if tt_arr.size and np.isfinite(tt_arr[-1]):
                tt_value = float(tt_arr[-1])
                all_tt.append(tt_value)
                if surface_arr.size and int(surface_arr[-1]) == final_surface:
                    image_tt.append(tt_value)

            hit_count = int(max(surface_arr.size, tp_arr.size, ts_arr.size, rp_arr.size, rs_arr.size, ttbe_arr.size))
            for hit_index in range(hit_count):
                if hit_index >= surface_arr.size:
                    continue
                surface_id = int(surface_arr[hit_index])
                bucket = per_surface.setdefault(
                    surface_id,
                    {"tp": [], "ts": [], "rp": [], "rs": [], "ttbe": []},
                )

                def _append(arr: np.ndarray, key: str, aggregate: list[float]) -> None:
                    if hit_index >= arr.size:
                        return
                    value = float(arr[hit_index])
                    if np.isfinite(value):
                        bucket[key].append(value)
                        aggregate.append(value)

                _append(tp_arr, "tp", all_tp)
                _append(ts_arr, "ts", all_ts)
                _append(rp_arr, "rp", all_rp)
                _append(rs_arr, "rs", all_rs)
                if hit_index < ttbe_arr.size and np.isfinite(float(ttbe_arr[hit_index])):
                    bucket["ttbe"].append(float(ttbe_arr[hit_index]))
                if hit_index < tp_arr.size and hit_index < ts_arr.size:
                    tp = float(tp_arr[hit_index])
                    ts = float(ts_arr[hit_index])
                    if np.isfinite(tp) and np.isfinite(ts):
                        trans_split.append(abs(tp - ts))
                if hit_index < rp_arr.size and hit_index < rs_arr.size:
                    rp = float(rp_arr[hit_index])
                    rs = float(rs_arr[hit_index])
                    if np.isfinite(rp) and np.isfinite(rs):
                        refl_split.append(abs(rp - rs))

        surface_rows: list[dict[str, object]] = []
        for surface_id in sorted(per_surface):
            bucket = per_surface[surface_id]
            name = self.rows[surface_id].name if 0 <= surface_id < len(self.rows) else f"S{surface_id}"
            surface_rows.append(
                {
                    "surface": surface_id,
                    "name": name,
                    "tp": self._finite_mean(bucket["tp"]),
                    "ts": self._finite_mean(bucket["ts"]),
                    "rp": self._finite_mean(bucket["rp"]),
                    "rs": self._finite_mean(bucket["rs"]),
                    "ttbe": self._finite_mean(bucket["ttbe"]),
                }
            )

        coated_surface_count = 0
        for row in self.rows:
            advanced = row.advanced or {}
            if any(attr in advanced for attr in ("Coating", "CoatingMet")):
                coated_surface_count += 1

        return {
            "total_rays": total_rays,
            "image_rays": len(image_tt),
            "mean_tt": self._finite_mean(all_tt),
            "image_mean_tt": self._finite_mean(image_tt),
            "mean_tp": self._finite_mean(all_tp),
            "mean_ts": self._finite_mean(all_ts),
            "mean_rp": self._finite_mean(all_rp),
            "mean_rs": self._finite_mean(all_rs),
            "mean_ps_transmission_split": self._finite_mean(trans_split),
            "mean_ps_reflection_split": self._finite_mean(refl_split),
            "coated_surface_count": coated_surface_count,
            "surface_rows": surface_rows,
        }

    def _phase2_feature_summary(self) -> dict[str, object]:
        error_rows: list[str] = []
        coating_rows: list[str] = []
        max_error_pv = 0.0
        max_error_rms = 0.0
        for index, row in enumerate(self.rows):
            advanced = row.advanced or {}
            if "Error_map" in advanced:
                label = f"S{index} {row.name}".strip()
                try:
                    _x, _y, z_arr, _spacing = _error_map_arrays(advanced["Error_map"])
                    z_arr = np.asarray(z_arr, dtype=float)
                    finite = z_arr[np.isfinite(z_arr)]
                    if finite.size:
                        pv = float(np.ptp(finite))
                        rms = float(np.sqrt(np.mean((finite - float(np.mean(finite))) ** 2)))
                        max_error_pv = max(max_error_pv, pv)
                        max_error_rms = max(max_error_rms, rms)
                        label = f"{label} (PV {pv:.4g}, RMS {rms:.4g})"
                except Exception:
                    label = f"{label} (invalid map)"
                error_rows.append(label)
            if any(attr in advanced for attr in ("Coating", "CoatingMet")):
                coating_rows.append(f"S{index} {row.name}".strip())

        source_stats = self._source_statistics()
        return {
            "source_model": source_stats.get("source_model", SOURCE_MODEL_DEFAULT),
            "source_summary": self._format_source_summary(),
            "error_map_count": len(error_rows),
            "error_map_rows": error_rows,
            "max_error_pv": max_error_pv if error_rows else None,
            "max_error_rms": max_error_rms if error_rows else None,
            "coating_count": len(coating_rows),
            "coating_rows": coating_rows,
            "metal_catalog_count": len(getattr(self, "metal_catalogs", []) or []),
        }

    @staticmethod
    def _unit_ray_frame_vector(value) -> np.ndarray | None:
        try:
            vector = np.asarray(value, dtype=float).reshape(-1)[:3]
        except Exception:
            return None
        if vector.size < 3 or not np.all(np.isfinite(vector)):
            return None
        norm = float(np.linalg.norm(vector))
        if not np.isfinite(norm) or norm <= 1e-12:
            return None
        return vector / norm

    @classmethod
    def _ray_hit_gaussian_frame_fields(cls, incoming, outgoing, normal) -> dict[str, object]:
        """Return a branch-local right-handed T/S/K frame for a traced hit."""
        incoming_unit = cls._unit_ray_frame_vector(incoming)
        outgoing_unit = cls._unit_ray_frame_vector(outgoing)
        normal_unit = cls._unit_ray_frame_vector(normal)
        k_axis = outgoing_unit if outgoing_unit is not None else incoming_unit
        if k_axis is None:
            return {
                "gb_frame_valid": False,
                "gb_incidence_deg": np.nan,
                "gb_k_l": np.nan,
                "gb_k_m": np.nan,
                "gb_k_n": np.nan,
                "gb_t_l": np.nan,
                "gb_t_m": np.nan,
                "gb_t_n": np.nan,
                "gb_s_l": np.nan,
                "gb_s_m": np.nan,
                "gb_s_n": np.nan,
            }

        incidence_deg = np.nan
        if incoming_unit is not None and normal_unit is not None:
            cos_i = float(np.clip(abs(float(np.dot(incoming_unit, normal_unit))), 0.0, 1.0))
            incidence_deg = float(np.rad2deg(np.arccos(cos_i)))

        reference = normal_unit
        if reference is None or float(np.linalg.norm(reference - (np.dot(reference, k_axis) * k_axis))) <= 1e-10:
            candidates = (
                np.asarray((0.0, 1.0, 0.0), dtype=float),
                np.asarray((1.0, 0.0, 0.0), dtype=float),
                np.asarray((0.0, 0.0, 1.0), dtype=float),
            )
            reference = max(candidates, key=lambda candidate: float(np.linalg.norm(candidate - (np.dot(candidate, k_axis) * k_axis))))

        t_axis = reference - (float(np.dot(reference, k_axis)) * k_axis)
        t_norm = float(np.linalg.norm(t_axis))
        if not np.isfinite(t_norm) or t_norm <= 1e-12:
            return {
                "gb_frame_valid": False,
                "gb_incidence_deg": incidence_deg,
                "gb_k_l": float(k_axis[0]),
                "gb_k_m": float(k_axis[1]),
                "gb_k_n": float(k_axis[2]),
                "gb_t_l": np.nan,
                "gb_t_m": np.nan,
                "gb_t_n": np.nan,
                "gb_s_l": np.nan,
                "gb_s_m": np.nan,
                "gb_s_n": np.nan,
            }
        t_axis = t_axis / t_norm
        s_axis = np.cross(k_axis, t_axis)
        s_norm = float(np.linalg.norm(s_axis))
        if not np.isfinite(s_norm) or s_norm <= 1e-12:
            return {
                "gb_frame_valid": False,
                "gb_incidence_deg": incidence_deg,
                "gb_k_l": float(k_axis[0]),
                "gb_k_m": float(k_axis[1]),
                "gb_k_n": float(k_axis[2]),
                "gb_t_l": float(t_axis[0]),
                "gb_t_m": float(t_axis[1]),
                "gb_t_n": float(t_axis[2]),
                "gb_s_l": np.nan,
                "gb_s_m": np.nan,
                "gb_s_n": np.nan,
            }
        s_axis = s_axis / s_norm
        t_axis = np.cross(s_axis, k_axis)
        t_axis = t_axis / max(float(np.linalg.norm(t_axis)), 1e-12)
        return {
            "gb_frame_valid": True,
            "gb_incidence_deg": incidence_deg,
            "gb_k_l": float(k_axis[0]),
            "gb_k_m": float(k_axis[1]),
            "gb_k_n": float(k_axis[2]),
            "gb_t_l": float(t_axis[0]),
            "gb_t_m": float(t_axis[1]),
            "gb_t_n": float(t_axis[2]),
            "gb_s_l": float(s_axis[0]),
            "gb_s_m": float(s_axis[1]),
            "gb_s_n": float(s_axis[2]),
        }

    @staticmethod
    def _ray_hit_table_specs() -> tuple[tuple[str, str, int, str, bool], ...]:
        return (
            ("step", "#", 45, "center", False),
            ("branch", "Path", 62, "center", False),
            ("surface", "Surf", 55, "center", False),
            ("event", "Event", 110, "w", False),
            ("name", "Name", 150, "w", True),
            ("glass", "Material", 110, "w", False),
            ("volume_id", "Volume", 92, "w", False),
            ("media_transition", "Media", 86, "w", False),
            ("media_in", "Medium in", 96, "w", False),
            ("media_out", "Medium out", 96, "w", False),
            ("media_state_method", "Media state", 130, "w", False),
            ("media_state_diagnostic", "Media diagnostic", 190, "w", True),
            ("inside_volumes_before", "Inside before", 120, "w", False),
            ("inside_volumes_after", "Inside after", 120, "w", False),
            ("mesh_cell_id", "Cell", 62, "center", False),
            ("mesh_original_cell_id", "Orig cell", 70, "center", False),
            ("mesh_face_id", "Face", 72, "center", False),
            ("mesh_face_match_method", "Face match", 130, "w", False),
            ("mesh_face_match_score", "Match score", 82, "e", False),
            ("mesh_face_match_warning", "Face diagnostic", 220, "w", True),
            ("x", "X [mm]", 85, "e", False),
            ("y", "Y [mm]", 85, "e", False),
            ("z", "Z [mm]", 85, "e", False),
            ("distance", "Dist [mm]", 85, "e", False),
            ("op", "OP [mm]", 85, "e", False),
            ("l", "L in", 70, "e", False),
            ("m", "M in", 70, "e", False),
            ("n", "N in", 70, "e", False),
            ("out_l", "L out", 70, "e", False),
            ("out_m", "M out", 70, "e", False),
            ("out_n", "N out", 70, "e", False),
            ("normal_l", "L nrm", 70, "e", False),
            ("normal_m", "M nrm", 70, "e", False),
            ("normal_n", "N nrm", 70, "e", False),
            ("gb_frame_valid", "GB frame", 72, "center", False),
            ("gb_incidence_deg", "Inc [deg]", 74, "e", False),
            ("gb_k_l", "GB K L", 70, "e", False),
            ("gb_k_m", "GB K M", 70, "e", False),
            ("gb_k_n", "GB K N", 70, "e", False),
            ("gb_t_l", "GB T L", 70, "e", False),
            ("gb_t_m", "GB T M", 70, "e", False),
            ("gb_t_n", "GB T N", 70, "e", False),
            ("gb_s_l", "GB S L", 70, "e", False),
            ("gb_s_m", "GB S M", 70, "e", False),
            ("gb_s_n", "GB S N", 70, "e", False),
            ("n0", "n0", 62, "e", False),
            ("n1", "n1", 62, "e", False),
            ("rp", "Rp", 62, "e", False),
            ("rs", "Rs", 62, "e", False),
            ("tp", "Tp", 62, "e", False),
            ("ts", "Ts", 62, "e", False),
            ("ttbe", "TTBE", 70, "e", False),
            ("interaction_model", "Model", 110, "w", False),
            ("interaction_target_surface", "Target", 72, "center", False),
            ("interaction_in_power", "Pin", 72, "e", False),
            ("interaction_coeff", "Coeff", 72, "e", False),
            ("interaction_out_power", "Pout", 72, "e", False),
            ("interaction_loss_power", "Loss", 72, "e", False),
            ("interaction_bulk", "Bulk", 72, "e", False),
        )

    def _format_hit_target_surface(self, value) -> str:
        try:
            index = int(value)
        except Exception:
            return ""
        return f"S{index}" if index >= 0 else ""

    def _ray_hit_table_values(self, hit: dict[str, object]) -> tuple[object, ...]:
        return (
            hit.get("step", ""),
            hit.get("branch", ""),
            hit.get("surface", ""),
            hit.get("event", ""),
            hit.get("name", ""),
            hit.get("glass", ""),
            hit.get("volume_id", ""),
            hit.get("media_transition", ""),
            hit.get("media_in", ""),
            hit.get("media_out", ""),
            hit.get("media_state_method", ""),
            hit.get("media_state_diagnostic", ""),
            hit.get("inside_volumes_before", ""),
            hit.get("inside_volumes_after", ""),
            self._format_ray_inspector_value(hit.get("mesh_cell_id")),
            self._format_ray_inspector_value(hit.get("mesh_original_cell_id")),
            hit.get("mesh_face_id", ""),
            hit.get("mesh_face_match_method", ""),
            self._format_ray_inspector_value(hit.get("mesh_face_match_score")),
            hit.get("mesh_face_match_warning", ""),
            self._format_ray_inspector_value(hit.get("x")),
            self._format_ray_inspector_value(hit.get("y")),
            self._format_ray_inspector_value(hit.get("z")),
            self._format_ray_inspector_value(hit.get("distance")),
            self._format_ray_inspector_value(hit.get("op")),
            self._format_ray_inspector_value(hit.get("l")),
            self._format_ray_inspector_value(hit.get("m")),
            self._format_ray_inspector_value(hit.get("n")),
            self._format_ray_inspector_value(hit.get("out_l")),
            self._format_ray_inspector_value(hit.get("out_m")),
            self._format_ray_inspector_value(hit.get("out_n")),
            self._format_ray_inspector_value(hit.get("normal_l")),
            self._format_ray_inspector_value(hit.get("normal_m")),
            self._format_ray_inspector_value(hit.get("normal_n")),
            "Y" if bool(hit.get("gb_frame_valid", False)) else "",
            self._format_ray_inspector_value(hit.get("gb_incidence_deg")),
            self._format_ray_inspector_value(hit.get("gb_k_l")),
            self._format_ray_inspector_value(hit.get("gb_k_m")),
            self._format_ray_inspector_value(hit.get("gb_k_n")),
            self._format_ray_inspector_value(hit.get("gb_t_l")),
            self._format_ray_inspector_value(hit.get("gb_t_m")),
            self._format_ray_inspector_value(hit.get("gb_t_n")),
            self._format_ray_inspector_value(hit.get("gb_s_l")),
            self._format_ray_inspector_value(hit.get("gb_s_m")),
            self._format_ray_inspector_value(hit.get("gb_s_n")),
            self._format_ray_inspector_value(hit.get("n0")),
            self._format_ray_inspector_value(hit.get("n1")),
            self._format_ray_inspector_value(hit.get("rp")),
            self._format_ray_inspector_value(hit.get("rs")),
            self._format_ray_inspector_value(hit.get("tp")),
            self._format_ray_inspector_value(hit.get("ts")),
            self._format_ray_inspector_value(hit.get("ttbe")),
            hit.get("interaction_model", ""),
            self._format_hit_target_surface(hit.get("interaction_target_surface")),
            self._format_ray_inspector_value(hit.get("interaction_in_power")),
            self._format_ray_inspector_value(hit.get("interaction_coeff")),
            self._format_ray_inspector_value(hit.get("interaction_out_power")),
            self._format_ray_inspector_value(hit.get("interaction_loss_power")),
            self._format_ray_inspector_value(hit.get("interaction_bulk")),
        )

    def _ray_event_to_inspector_hit(self, event: RayEvent3D) -> dict[str, object]:
        xyz = np.asarray(getattr(event, "point_world", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        lmn = np.asarray(getattr(event, "incoming_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        r_lmn = np.asarray(getattr(event, "outgoing_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        s_lmn = np.asarray(getattr(event, "surface_normal", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        surface_id = getattr(event, "surface_id", None)
        record = {
            "step": int(getattr(event, "step", 0)),
            "branch": int(getattr(event, "branch_id", 0)),
            "surface": "" if surface_id is None else int(surface_id),
            "event": str(getattr(event, "event_type", "") or ""),
            "name": str(getattr(event, "surface_name", "") or ""),
            "glass": str(getattr(event, "material", "") or ""),
            "x": float(xyz[0]) if xyz.size >= 1 else np.nan,
            "y": float(xyz[1]) if xyz.size >= 2 else np.nan,
            "z": float(xyz[2]) if xyz.size >= 3 else np.nan,
            "distance": getattr(event, "distance", np.nan),
            "op": getattr(event, "optical_path", np.nan),
            "l": float(lmn[0]) if lmn.size >= 1 else np.nan,
            "m": float(lmn[1]) if lmn.size >= 2 else np.nan,
            "n": float(lmn[2]) if lmn.size >= 3 else np.nan,
            "out_l": float(r_lmn[0]) if r_lmn.size >= 1 else np.nan,
            "out_m": float(r_lmn[1]) if r_lmn.size >= 2 else np.nan,
            "out_n": float(r_lmn[2]) if r_lmn.size >= 3 else np.nan,
            "normal_l": float(s_lmn[0]) if s_lmn.size >= 1 else np.nan,
            "normal_m": float(s_lmn[1]) if s_lmn.size >= 2 else np.nan,
            "normal_n": float(s_lmn[2]) if s_lmn.size >= 3 else np.nan,
            "n0": getattr(event, "n0", np.nan),
            "n1": getattr(event, "n1", np.nan),
            "rp": getattr(event, "rp", np.nan),
            "rs": getattr(event, "rs", np.nan),
            "tp": getattr(event, "tp", np.nan),
            "ts": getattr(event, "ts", np.nan),
            "ttbe": getattr(event, "ttbe", np.nan),
            "interaction_model": str(getattr(event, "interaction_model", "") or ""),
            "interaction_target_surface": getattr(event, "interaction_target_surface", None),
            "interaction_in_power": getattr(event, "interaction_in_power", np.nan),
            "interaction_coeff": getattr(event, "interaction_coeff", np.nan),
            "interaction_out_power": getattr(event, "interaction_out_power", np.nan),
            "interaction_loss_power": getattr(event, "interaction_loss_power", np.nan),
            "interaction_bulk": getattr(event, "interaction_bulk", np.nan),
            "volume_id": str(getattr(event, "volume_id", "") or ""),
            "media_in": str(getattr(event, "media_in", "") or ""),
            "media_out": str(getattr(event, "media_out", "") or ""),
            "media_transition": str(getattr(event, "media_transition", "") or ""),
            "media_state_method": str(getattr(event, "media_state_method", "") or ""),
            "media_state_diagnostic": str(getattr(event, "media_state_diagnostic", "") or ""),
            "inside_volumes_before": str(getattr(event, "inside_volumes_before", "") or ""),
            "inside_volumes_after": str(getattr(event, "inside_volumes_after", "") or ""),
            "mesh_cell_id": getattr(event, "mesh_cell_id", np.nan),
            "mesh_original_cell_id": getattr(event, "mesh_original_cell_id", np.nan),
            "mesh_face_id": str(getattr(event, "mesh_face_id", "") or ""),
            "mesh_face_match_method": str(getattr(event, "mesh_face_match_method", "") or ""),
            "mesh_face_match_score": getattr(event, "mesh_face_match_score", np.nan),
            "mesh_face_match_warning": str(getattr(event, "mesh_face_match_warning", "") or ""),
            "event_id": str(getattr(event, "event_id", "") or ""),
            "event_kind": str(getattr(event, "event_kind", "") or ""),
            "diagnostic": str(getattr(event, "diagnostic", "") or ""),
        }
        record.update(self._ray_hit_gaussian_frame_fields(lmn, r_lmn, s_lmn))
        return record

    def _ray_hit_event_label(
        self,
        surface_type: str,
        glass: str,
        interaction_type: str,
        n0: float | None,
        n1: float | None,
    ) -> str:
        surface_type_text = str(surface_type or "").strip().lower()
        glass_text = str(glass or "").strip().upper()
        label = str(interaction_type or "").strip().lower()
        if surface_type_text == "object":
            return "launch"
        if surface_type_text == "image":
            return "image"
        if surface_type_text == "aperture":
            return "aperture"
        if label.startswith("split_reflect"):
            return "split_reflect"
        if label.startswith("split_transmit"):
            return "split_transmit"
        if label in {"scatter", "diffuse_scatter"} or surface_type_text == "diffuse object":
            return "scatter"
        if label in {"reflection", "reflect"} or glass_text == "MIRROR":
            return "reflection"
        if label in {"absorb", "absorption"}:
            return "absorb"
        if label in {"refract", "refraction"}:
            return "refraction"
        if label in {"transmit", "transmission"}:
            if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
                return "refraction"
            return "transmission"
        if label:
            return label
        if surface_type_text == "beam splitter":
            return "beam_splitter"
        if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
            return "refraction"
        return "transmission"

    def _ray_inspector_record_service(self) -> RayInspectorRecordService:
        service = self.__dict__.get("_ray_inspector_record_service_instance")
        if service is None:
            service = RayInspectorRecordService(self)
            self._ray_inspector_record_service_instance = service
        return service

    def _collect_ray_inspector_records(
        self,
        rays=None,
        scene_bundle=None,
        *,
        system=None,
        rows: list[SurfaceRow] | None = None,
        field_bundle_count: int | None = None,
        ray_count_per_field: int | None = None,
    ) -> list[dict[str, object]]:
        return self._ray_inspector_record_service()._collect_ray_inspector_records(
            rays=rays,
            scene_bundle=scene_bundle,
            system=system,
            rows=rows,
            field_bundle_count=field_bundle_count,
            ray_count_per_field=ray_count_per_field,
        )

    def _collect_ray_analysis_records(self, scene_bundle=None) -> list[dict[str, object]]:
        bundle = self._last_scene_bundle if scene_bundle is None else scene_bundle
        if bundle is None and self.last_system is not None and self.last_rays is not None:
            try:
                max_radius = max((max(row.diameter / 2.0, 0.5) for row in self.rows), default=1.0)
                bundle = self._build_scene_bundle(self.last_system, self.last_rays, max_radius)
                self._last_scene_bundle = bundle
            except Exception:
                bundle = None
        if bundle is not None:
            records = scene_bundle_ray_analysis_records(bundle)
            if records:
                return records
        return self._collect_ray_inspector_records(scene_bundle=bundle)

    def _ray_analysis_records_for_trace(self, system=None, rays=None) -> list[dict[str, object]]:
        if rays is not None:
            try:
                active_system = self.last_system if system is None else system
                if active_system is not None:
                    preview_bundle_count = self.__dict__.get("_preview_field_bundle_count")
                    preview_ray_count = self.__dict__.get("_preview_field_ray_count")
                    field_count = max(
                        1,
                        int(preview_bundle_count if preview_bundle_count is not None else self._current_field_count()),
                    )
                    ray_count_per_field = max(1, int(preview_ray_count if preview_ray_count is not None else 1))
                    bundle = build_scene_bundle(
                        rows=self.rows,
                        system=active_system,
                        rays=rays,
                        sources=self._collect_scene_sources(wavelength=self._current_wavelength()),
                        field_count=field_count,
                        ray_count_per_field=ray_count_per_field,
                        source_row_order=normalize_source_row_order(
                            getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)
                        ),
                    )
                    records = scene_bundle_ray_analysis_records(bundle)
                    if records:
                        self._last_scene_bundle = bundle
                        return records
            except Exception:
                pass
            try:
                return self._collect_ray_inspector_records(rays=rays, system=system)
            except Exception:
                pass
        return self._collect_ray_analysis_records()

    def _active_ray_analysis_records(self) -> list[dict[str, object]]:
        return self._ray_analysis_records_for_trace(system=self.last_system, rays=self.last_rays)

    def _main_ray_trace_inspector_dialogs(self) -> MainRayTraceInspectorDialogs:
        dialog = self.__dict__.get("_main_ray_trace_inspector_dialogs_instance")
        if dialog is None:
            dialog = MainRayTraceInspectorDialogs(self)
            self._main_ray_trace_inspector_dialogs_instance = dialog
        return dialog

    def open_ray_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs().open_ray_inspector()

    def _close_ray_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs()._close_ray_inspector()

    def _refresh_ray_inspector_if_open(self) -> None:
        self._main_ray_trace_inspector_dialogs()._refresh_ray_inspector_if_open()

    def _refresh_ray_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs()._refresh_ray_inspector()

    def _populate_ray_inspector_hits(self, _event=None) -> None:
        self._main_ray_trace_inspector_dialogs()._populate_ray_inspector_hits(_event)

    def export_ray_inspector_csv(self) -> None:
        self._main_ray_trace_inspector_dialogs().export_ray_inspector_csv()

    def export_ray_events_csv(self) -> None:
        self._main_ray_trace_inspector_dialogs().export_ray_events_csv()

    def _branch_gaussian_q_input_beam(self, wavelength: float):
        if self._current_source_model() == "Gaussian beam":
            return self._current_gaussian_beam_input(wavelength)
        return default_branch_gaussian_q_beam(float(wavelength))

    def _collect_branch_gaussian_q_records(
        self,
        records: list[dict[str, object]] | None = None,
        wavelength: float | None = None,
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        ray_records = list(records if records is not None else self._collect_ray_analysis_records())
        wavelength_value = float(self._current_wavelength() if wavelength is None else wavelength)
        source_model = self._current_source_model()
        try:
            beam = self._branch_gaussian_q_input_beam(wavelength_value)
        except Exception:
            beam = default_branch_gaussian_q_beam(wavelength_value)
            source_model = ""
        return collect_branch_gaussian_q_records(
            ray_records,
            surfaces=self.rows,
            beam=beam,
            wavelength_um=wavelength_value,
            source_model=source_model,
            branch_code_for_path=lambda path: "".join(self._branch_path_selector_sequence(path)) or "primary",
            error_formatter=_short_error_message,
        )

    def _branch_gaussian_q_summary_text(self, summary: dict[str, object]) -> str:
        return branch_gaussian_q_summary_text(summary)

    def _main_branch_gaussian_q_dialog(self) -> MainBranchGaussianQDialog:
        dialog = self.__dict__.get("_main_branch_gaussian_q_dialog_instance")
        if dialog is None:
            dialog = MainBranchGaussianQDialog(self)
            self._main_branch_gaussian_q_dialog_instance = dialog
        return dialog

    def open_branch_gaussian_q_report(self) -> None:
        self._main_branch_gaussian_q_dialog().open_branch_gaussian_q_report()

    def _close_branch_gaussian_q_report(self) -> None:
        self._main_branch_gaussian_q_dialog()._close_branch_gaussian_q_report()

    def _refresh_branch_gaussian_q_report_if_open(self) -> None:
        self._main_branch_gaussian_q_dialog()._refresh_branch_gaussian_q_report_if_open()

    def _refresh_branch_gaussian_q_report(self) -> None:
        self._main_branch_gaussian_q_dialog()._refresh_branch_gaussian_q_report()

    def _branch_gaussian_q_report_text(self) -> str:
        return self._main_branch_gaussian_q_dialog()._branch_gaussian_q_report_text()

    def copy_branch_gaussian_q_report_to_clipboard(self) -> None:
        self._main_branch_gaussian_q_dialog().copy_branch_gaussian_q_report_to_clipboard()

    def export_branch_gaussian_q_csv(self) -> None:
        self._main_branch_gaussian_q_dialog().export_branch_gaussian_q_csv()

    def _surface_path_text(self, surface_ids) -> str:
        labels: list[str] = []
        for surface_id in np.asarray(surface_ids, dtype=int).ravel():
            index = int(surface_id)
            name = self.rows[index].name if 0 <= index < len(self.rows) else ""
            labels.append(f"S{index}:{name}" if name else f"S{index}")
        return " -> ".join(labels)

    def _scene_hit_to_inspector_hit(self, hit) -> dict[str, object]:
        xyz = np.asarray(getattr(hit, "point_world", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        lmn = np.asarray(getattr(hit, "incoming_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        r_lmn = np.asarray(getattr(hit, "outgoing_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        s_lmn = np.asarray(getattr(hit, "surface_normal", (np.nan, np.nan, np.nan)), dtype=float).ravel()
        surface_id = getattr(hit, "surface_id", "")
        record = {
            "step": int(getattr(hit, "step", 0)),
            "branch": int(getattr(hit, "branch_id", 0)),
            "surface": "" if surface_id is None else int(surface_id),
            "event": str(getattr(hit, "interaction", "") or ""),
            "name": str(getattr(hit, "name", "") or ""),
            "glass": str(getattr(hit, "material", "") or ""),
            "x": float(xyz[0]) if xyz.size >= 1 else np.nan,
            "y": float(xyz[1]) if xyz.size >= 2 else np.nan,
            "z": float(xyz[2]) if xyz.size >= 3 else np.nan,
            "distance": getattr(hit, "distance", np.nan),
            "op": getattr(hit, "optical_path", np.nan),
            "l": float(lmn[0]) if lmn.size >= 1 else np.nan,
            "m": float(lmn[1]) if lmn.size >= 2 else np.nan,
            "n": float(lmn[2]) if lmn.size >= 3 else np.nan,
            "out_l": float(r_lmn[0]) if r_lmn.size >= 1 else np.nan,
            "out_m": float(r_lmn[1]) if r_lmn.size >= 2 else np.nan,
            "out_n": float(r_lmn[2]) if r_lmn.size >= 3 else np.nan,
            "normal_l": float(s_lmn[0]) if s_lmn.size >= 1 else np.nan,
            "normal_m": float(s_lmn[1]) if s_lmn.size >= 2 else np.nan,
            "normal_n": float(s_lmn[2]) if s_lmn.size >= 3 else np.nan,
            "n0": getattr(hit, "n0", np.nan),
            "n1": getattr(hit, "n1", np.nan),
            "rp": getattr(hit, "rp", np.nan),
            "rs": getattr(hit, "rs", np.nan),
            "tp": getattr(hit, "tp", np.nan),
            "ts": getattr(hit, "ts", np.nan),
            "ttbe": getattr(hit, "ttbe", np.nan),
            "interaction_model": str(getattr(hit, "interaction_model", "") or ""),
            "interaction_target_surface": getattr(hit, "interaction_target_surface", None),
            "interaction_in_power": getattr(hit, "interaction_in_power", np.nan),
            "interaction_coeff": getattr(hit, "interaction_coeff", np.nan),
            "interaction_out_power": getattr(hit, "interaction_out_power", np.nan),
            "interaction_loss_power": getattr(hit, "interaction_loss_power", np.nan),
            "interaction_bulk": getattr(hit, "interaction_bulk", np.nan),
        }
        record.update(self._ray_hit_gaussian_frame_fields(lmn, r_lmn, s_lmn))
        return record

    def _branch_metrics_from_hits(self, hits: list[dict[str, object]]) -> tuple[float, float, float | None]:
        distance = 0.0
        optical_path = 0.0
        transmission = None
        for hit in hits:
            try:
                value = float(hit.get("distance", np.nan))
                if np.isfinite(value):
                    distance += value
            except Exception:
                pass
            try:
                value = float(hit.get("op", np.nan))
                if np.isfinite(value):
                    optical_path += value
            except Exception:
                pass
            try:
                value = float(hit.get("ttbe", np.nan))
                if np.isfinite(value):
                    transmission = value
            except Exception:
                pass
        return distance, optical_path, transmission

    def _branch_tree_records_from_ray_records(self, ray_records: list[dict[str, object]]) -> list[dict[str, object]]:
        records: list[dict[str, object]] = []
        for ray_record in list(ray_records or []):
            grouped: dict[int, list[dict[str, object]]] = {}
            for hit in list(ray_record.get("hits", []) or []):
                try:
                    branch_id = int(hit.get("branch", 0))
                except Exception:
                    branch_id = 0
                grouped.setdefault(branch_id, []).append(hit)
            if not grouped:
                grouped[0] = []
            for branch_id, branch_hits in sorted(grouped.items()):
                surface_ids = [
                    int(hit["surface"])
                    for hit in branch_hits
                    if str(hit.get("surface", "")).strip()
                ]
                distance, optical_path, transmission = self._branch_metrics_from_hits(branch_hits)
                last_surface = int(surface_ids[-1]) if surface_ids else ray_record.get("last_surface")
                last_name = str(branch_hits[-1].get("name", "") or "") if branch_hits else str(ray_record.get("last_name", "") or "")
                records.append(
                    {
                        "ray_index": int(ray_record.get("ray_index", 0)),
                        "field_index": int(ray_record.get("field_index", 0)),
                        "branch_id": int(branch_id),
                        "branch_path": str(ray_record.get("branch_path", "") or ""),
                        "parent_branch_id": None if int(branch_id) == 0 else int(branch_id) - 1,
                        "start_step": int(min([int(hit.get("step", 0)) for hit in branch_hits] or [0])),
                        "end_step": int(max([int(hit.get("step", 0)) for hit in branch_hits] or [0])),
                        "surface_path": self._surface_path_text(surface_ids),
                        "termination": str(ray_record.get("termination", "")),
                        "termination_diagnostic": str(ray_record.get("termination_diagnostic", "") or ""),
                        "terminal_media": str(ray_record.get("terminal_media", "") or ""),
                        "terminal_index": ray_record.get("terminal_index", ""),
                        "terminal_inside_volumes": str(ray_record.get("terminal_inside_volumes", "") or ""),
                        "terminal_media_state": str(ray_record.get("terminal_media_state", "") or ""),
                        "branch_tree_diagnostic": str(ray_record.get("branch_tree_diagnostic", "") or ""),
                        "hit_count": len(branch_hits),
                        "distance": distance,
                        "op": optical_path,
                        "transmission": transmission,
                        "last_surface": last_surface,
                        "last_name": last_name,
                        "reaches_image": bool(ray_record.get("reaches_image", False)),
                        "hits": branch_hits,
                    }
                )
        return records

    def _collect_branch_tree_records(
        self,
        ray_records: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        if ray_records is not None:
            return self._branch_tree_records_from_ray_records(ray_records)
        bundle = self._last_scene_bundle
        paths = list(getattr(bundle, "ray_paths", []) or []) if bundle is not None else []
        records: list[dict[str, object]] = []
        if paths:
            for path in paths:
                path_hits = list(getattr(path, "hits", []) or [])
                path_events = list(getattr(path, "events", []) or [])
                path_surface_events = [
                    event
                    for event in path_events
                    if str(getattr(event, "event_kind", "") or "") == "surface"
                ]
                path_terminal_events = [
                    event
                    for event in path_events
                    if str(getattr(event, "event_kind", "") or "") == "terminal"
                ]
                terminal_event = path_terminal_events[-1] if path_terminal_events else None
                terminal_media = str(getattr(terminal_event, "media_out", "") or "") if terminal_event is not None else ""
                terminal_index = getattr(terminal_event, "n1", None) if terminal_event is not None else ""
                terminal_index = "" if terminal_index is None else terminal_index
                terminal_inside_volumes = (
                    str(getattr(terminal_event, "inside_volumes_after", "") or "")
                    if terminal_event is not None
                    else ""
                )
                terminal_media_state = (
                    str(getattr(terminal_event, "media_state_method", "") or "")
                    if terminal_event is not None
                    else ""
                )
                hits_by_branch: dict[int, list[dict[str, object]]] = {}
                if path_surface_events:
                    for event in path_surface_events:
                        branch_id = int(getattr(event, "branch_id", 0))
                        hits_by_branch.setdefault(branch_id, []).append(self._ray_event_to_inspector_hit(event))
                else:
                    for hit in path_hits:
                        branch_id = int(getattr(hit, "branch_id", 0))
                        hits_by_branch.setdefault(branch_id, []).append(self._scene_hit_to_inspector_hit(hit))
                branches = list(getattr(path, "branches", []) or [])
                if not branches and hits_by_branch:
                    branches = [
                        RayBranch3D(
                            branch_id=branch_id,
                            parent_branch_id=None if branch_id == 0 else max(branch_id - 1, 0),
                            start_step=int(min(int(hit.get("step", 0)) for hit in branch_hits)),
                            end_step=int(max(int(hit.get("step", 0)) for hit in branch_hits)),
                            surface_ids=np.asarray(
                                [int(hit["surface"]) for hit in branch_hits if str(hit.get("surface", "")).strip()],
                                dtype=int,
                            ),
                            termination_reason=str(getattr(path, "termination_reason", "")),
                            termination_diagnostic=str(getattr(path, "termination_diagnostic", "")),
                        )
                        for branch_id, branch_hits in sorted(hits_by_branch.items())
                    ]
                for branch in branches:
                    branch_id = int(getattr(branch, "branch_id", 0))
                    branch_hits = list(hits_by_branch.get(branch_id, []))
                    surface_ids = np.asarray(getattr(branch, "surface_ids", []), dtype=int).ravel()
                    if surface_ids.size == 0 and branch_hits:
                        surface_ids = np.asarray(
                            [int(hit["surface"]) for hit in branch_hits if str(hit.get("surface", "")).strip()],
                            dtype=int,
                        )
                    distance, optical_path, transmission = self._branch_metrics_from_hits(branch_hits)
                    last_surface = int(surface_ids[-1]) if surface_ids.size else None
                    last_name = ""
                    if last_surface is not None and 0 <= last_surface < len(self.rows):
                        last_name = self.rows[last_surface].name
                    if not last_name and branch_hits:
                        last_name = str(branch_hits[-1].get("name", "") or "")
                    records.append(
                        {
                            "ray_index": int(getattr(path, "ray_index", 0)),
                            "field_index": int(getattr(path, "field_index", 0)),
                            "branch_id": branch_id,
                            "branch_path": str(getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or ""),
                            "parent_branch_id": getattr(branch, "parent_branch_id", None),
                            "start_step": int(getattr(branch, "start_step", 0)),
                            "end_step": int(getattr(branch, "end_step", 0)),
                            "surface_path": self._surface_path_text(surface_ids),
                            "termination": str(getattr(branch, "termination_reason", "") or getattr(path, "termination_reason", "")),
                            "termination_diagnostic": str(
                                getattr(branch, "termination_diagnostic", "") or getattr(path, "termination_diagnostic", "")
                            ),
                            "terminal_media": terminal_media,
                            "terminal_index": terminal_index,
                            "terminal_inside_volumes": terminal_inside_volumes,
                            "terminal_media_state": terminal_media_state,
                            "branch_tree_diagnostic": str(getattr(path, "branch_tree_diagnostic", "") or ""),
                            "hit_count": len(branch_hits),
                            "distance": distance,
                            "op": optical_path,
                            "transmission": transmission,
                            "last_surface": last_surface,
                            "last_name": last_name,
                            "reaches_image": ray_path_reaches_image_from_events(path),
                            "hits": branch_hits,
                        }
                    )
            return records

        return self._branch_tree_records_from_ray_records(self._collect_ray_analysis_records())

    def open_branch_tree_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs().open_branch_tree_inspector()

    def _close_branch_tree_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs()._close_branch_tree_inspector()

    def _refresh_branch_tree_if_open(self) -> None:
        self._main_ray_trace_inspector_dialogs()._refresh_branch_tree_if_open()

    def _refresh_branch_tree_inspector(self) -> None:
        self._main_ray_trace_inspector_dialogs()._refresh_branch_tree_inspector()

    def _branch_tree_record_for_iid(self, iid: str) -> dict[str, object] | None:
        return self._main_ray_trace_inspector_dialogs()._branch_tree_record_for_iid(iid)

    def _branch_tree_selected_ray_index(self) -> int | None:
        return self._main_ray_trace_inspector_dialogs()._branch_tree_selected_ray_index()

    def _open_branch_tree_selected_ray(self) -> None:
        self._main_ray_trace_inspector_dialogs()._open_branch_tree_selected_ray()

    def _populate_branch_tree_hits(self, _event=None) -> None:
        self._main_ray_trace_inspector_dialogs()._populate_branch_tree_hits(_event)

    def export_branch_tree_csv(self) -> None:
        self._main_ray_trace_inspector_dialogs().export_branch_tree_csv()

    @staticmethod
    def _safe_float(value, default: float = 0.0) -> float:
        try:
            result = float(value)
        except Exception:
            return default
        if not np.isfinite(result):
            return default
        return result

    @staticmethod
    def _safe_positive_float(value, default: float = 0.0) -> float:
        try:
            result = float(value)
        except Exception:
            return default
        if not np.isfinite(result):
            return default
        return max(result, 0.0)

    @staticmethod
    def _safe_complex(value, default: complex = complex(1.0, 0.0)) -> complex:
        try:
            result = complex(value)
        except Exception:
            return default
        if not np.isfinite(result.real) or not np.isfinite(result.imag):
            return default
        return result

    @classmethod
    def _normalize_jones_pair(cls, p_value, s_value) -> tuple[complex, complex]:
        p_component = cls._safe_complex(p_value, complex(1.0, 0.0))
        s_component = cls._safe_complex(s_value, complex(0.0, 0.0))
        norm = float(np.sqrt((abs(p_component) ** 2.0) + (abs(s_component) ** 2.0)))
        if not np.isfinite(norm) or norm <= 1e-15:
            return complex(1.0, 0.0), complex(0.0, 0.0)
        return p_component / norm, s_component / norm

    @staticmethod
    def _normalize_complex_vector(value) -> np.ndarray:
        try:
            vector = np.asarray(value, dtype=np.complex128).reshape(-1)[:3]
        except Exception:
            vector = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        if vector.size < 3:
            vector = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        if not np.all(np.isfinite(vector.real) & np.isfinite(vector.imag)):
            vector = np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        norm = float(np.sqrt(np.sum(np.abs(vector) ** 2.0)))
        if not np.isfinite(norm) or norm <= 1e-15:
            return np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        return vector / norm

    @staticmethod
    def _format_jones_value(value) -> str:
        try:
            component = complex(value)
        except Exception:
            return ""
        sign = "+" if component.imag >= 0.0 else "-"
        return f"{component.real:.4g}{sign}{abs(component.imag):.4g}j"

    def _branch_output_label(self, branch_path: str) -> str:
        return branch_output_label(branch_path)

    def _terminal_surface_label(self, surface_index, fallback_name: str = "") -> str:
        try:
            index = int(surface_index)
        except Exception:
            return str(fallback_name or "No terminal surface").strip()
        if not (0 <= index < len(self.rows)):
            return str(fallback_name or f"S{index}").strip()
        row = self.rows[index]
        metadata = self._element_metadata(row)
        element = self._element_key(row) or str(metadata.get("element_name", "") or "").strip()
        name = str(getattr(row, "name", "") or fallback_name or "").strip()
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)
        prefix = "Detector" if role == "Detector" or self._row_has_detector_output_metadata(row) else str(row.surface or "Surface")
        label = element or name or f"S{index}"
        return f"S{index} {prefix}: {label}"

    @staticmethod
    def _ray_termination_status_text(termination: str, last_surface, reaches_image: bool = False) -> str:
        if reaches_image or termination == "image":
            return "Image"
        try:
            surface_text = f"S{int(last_surface)}"
        except Exception:
            surface_text = ""
        if termination == "missed_image":
            return f"Missed image after {surface_text}" if surface_text else "Missed image"
        if termination == "missed_folded_image":
            return "Missed image"
        if termination == "no_next_intersection":
            return f"Continues after {surface_text}" if surface_text else "Continues"
        if termination in {"no_hit", "no_folded_display_path"}:
            return "No hit"
        if str(termination or "").startswith("stopped_at_surface_"):
            return f"Stop @ {surface_text}" if surface_text else "Stopped"
        return str(termination or "").strip() or "No hit"

    def _surface_index_is_detector(self, surface_index) -> bool:
        try:
            index = int(surface_index)
        except Exception:
            return False
        if not (0 <= index < len(self.rows)):
            return False
        row = self.rows[index]
        metadata = self._element_metadata(row)
        role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)
        if role == "Detector" or self._row_has_detector_output_metadata(row):
            return True
        return index in self._scene_detector_surface_indices()

    def _nonseq_plain_image_detector_enabled(self) -> bool:
        """Treat a plain Image row as a detector only for conventional lens scenes."""
        for row in getattr(self, "rows", []) or []:
            surface = str(getattr(row, "surface", "") or "").strip()
            if surface in {OBJECT_TARGET_SURFACE, DIFFUSE_OBJECT_SURFACE}:
                return False
            surface_key = re.sub(r"[^a-z0-9]", "", surface.lower())
            if any(token in surface_key for token in ("solid3dstl", "cadsolid", "opticalsolid", "stlsolid")):
                return False
            advanced = getattr(row, "advanced", {})
            if not isinstance(advanced, dict):
                advanced = {}
            if self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
                return False
            if self._scene_graph_value_present(advanced.get("OpticalSolidSourcePath")):
                return False
            if self._scene_graph_value_present(advanced.get(OPTICAL_SOLID_FACES_ADVANCED_ATTR)):
                return False
        return True

    def _scene_detector_surface_indices(self, trace_state: dict[str, object] | None = None) -> set[int]:
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=getattr(self, "last_system", None))
            except Exception:
                trace_state = {"use_nonseq": False}
        use_nonseq = bool(trace_state.get("use_nonseq"))
        auto_image_detector = (not use_nonseq) or self._nonseq_plain_image_detector_enabled()
        detectors: set[int] = set()
        for index, row in enumerate(getattr(self, "rows", []) or []):
            metadata = self._element_metadata(row)
            role = str(metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT) or ELEMENT_ARM_ROLE_DEFAULT)
            surface = str(getattr(row, "surface", "") or "").strip()
            if role == "Detector" or self._row_has_detector_output_metadata(row) or (surface == "Image" and auto_image_detector):
                detectors.add(int(index))
        target_index = self._current_nonseq_target_surface_index()
        if target_index is not None and 0 <= target_index < len(self.rows):
            detectors.add(int(target_index))
        if not use_nonseq and self.rows and self.rows[-1].surface == "Image":
            detectors.add(len(self.rows) - 1)
        return detectors

    def _source_illumination_target_priority(self, surface_index: int) -> int:
        if not (0 <= int(surface_index) < len(self.rows)):
            return 99
        row = self.rows[int(surface_index)]
        if self._surface_index_is_detector(surface_index):
            return 0
        if row.surface in {OBJECT_TARGET_SURFACE, DIFFUSE_OBJECT_SURFACE, "Object"}:
            return 1
        if row.surface == "Aperture":
            return 2
        return 3

    def _source_illumination_auto_target_index(self) -> int | None:
        terminal_surfaces: set[int] = set()
        hit_surfaces: set[int] = set()
        for record in self._collect_ray_analysis_records():
            try:
                terminal_index = int(record.get("last_surface"))
            except Exception:
                terminal_index = None
            if terminal_index is not None and 0 <= terminal_index < len(self.rows):
                terminal_surfaces.add(terminal_index)
            for hit in list(record.get("hits", []) or []):
                try:
                    surface_index = int(hit.get("surface"))
                except Exception:
                    continue
                if 0 <= surface_index < len(self.rows):
                    hit_surfaces.add(surface_index)

        if terminal_surfaces:
            return min(
                terminal_surfaces,
                key=lambda index: (
                    self._source_illumination_target_priority(index),
                    -index,
                ),
            )

        if hit_surfaces:
            return min(
                hit_surfaces,
                key=lambda index: (
                    self._source_illumination_target_priority(index),
                    -index,
                ),
            )

        detector_candidates = [
            index
            for index, _row in enumerate(self.rows)
            if self._surface_index_is_detector(index)
        ]
        if detector_candidates:
            return max(detector_candidates)
        return len(self.rows) - 1 if self.rows else None

    def _detector_settings_for_surface(self, surface_index) -> dict[str, object]:
        try:
            index = int(surface_index)
        except Exception:
            return _normalize_detector_settings({})
        if not (0 <= index < len(self.rows)):
            return _normalize_detector_settings({})
        return self._detector_settings(self.rows[index])

    @staticmethod
    def _single_terminal_surface_from_samples(samples: dict[str, object]) -> int | None:
        surfaces: set[int] = set()
        for surface in list(samples.get("terminal_surfaces", []) or []):
            try:
                surfaces.add(int(surface))
            except Exception:
                pass
        if len(surfaces) != 1:
            return None
        return next(iter(surfaces))

    def _detector_model_for_samples(self, samples: dict[str, object]) -> dict[str, object]:
        surface_index = self._single_terminal_surface_from_samples(samples)
        settings = self._detector_settings_for_surface(surface_index) if surface_index is not None else _normalize_detector_settings({})
        active_width = float(settings.get("active_width_mm", 0.0))
        active_height = float(settings.get("active_height_mm", 0.0))
        if surface_index is not None and 0 <= surface_index < len(self.rows):
            diameter = self._safe_positive_float(getattr(self.rows[surface_index], "diameter", 0.0), 0.0)
            if active_width <= 0.0 and diameter > 0.0:
                active_width = diameter
            if active_height <= 0.0 and diameter > 0.0:
                active_height = diameter
        return {
            "surface_index": surface_index,
            "settings": settings,
            "active_width_mm": active_width,
            "active_height_mm": active_height,
            "bins": str(settings.get("bins", "") or ""),
            "pixel_pitch_um": float(settings.get("pixel_pitch_um", 0.0)),
        }

    def _collect_branch_throughput_records(
        self,
        ray_records: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        ray_records = list(ray_records if ray_records is not None else self._collect_ray_analysis_records())
        if not ray_records:
            return []
        return self._branch_throughput_records_for_ray_records(ray_records)

    def _branch_throughput_records_for_ray_records(self, ray_records: list[dict[str, object]]) -> list[dict[str, object]]:
        if not ray_records:
            return []
        return collect_branch_throughput_records(
            ray_records,
            terminal_label_for_record=lambda record: self._terminal_surface_label(
                record.get("last_surface"),
                str(record.get("last_name", "") or ""),
            ),
            is_detector_surface=self._surface_index_is_detector,
        )

    def _source_illumination_target_choices(self) -> list[str]:
        choices = ["Auto"]
        for index, row in enumerate(self.rows):
            choices.append(f"{index}: {row.name or row.surface}")
        return choices

    def _source_illumination_target_index(self) -> int | None:
        target_var = self.__dict__.get("_source_illumination_target_var")
        value = (
            str(target_var.get()).strip()
            if target_var is not None
            else "Auto"
        )
        if value and value != "Auto":
            try:
                index = int(value.split(":", 1)[0].strip())
                if 0 <= index < len(self.rows):
                    return index
            except Exception:
                pass
        analysis_var = self.__dict__.get("analysis_surface_var")
        analysis_text = str(analysis_var.get()).strip() if analysis_var is not None else "Auto"
        if analysis_text and analysis_text != "Auto":
            try:
                analysis_index = int(analysis_text.split(":", 1)[0].strip())
                if 0 <= analysis_index < len(self.rows):
                    return analysis_index
            except Exception:
                pass
        nonseq_target_index = self._current_nonseq_target_surface_index()
        if nonseq_target_index is not None:
            return nonseq_target_index
        return self._source_illumination_auto_target_index()

    def _source_illumination_terminal_label_for_record(self, record: dict[str, object]) -> str:
        last_surface = record.get("last_surface")
        last_name = str(record.get("last_name", "") or "")
        terminal = self._terminal_surface_label(last_surface, last_name)
        termination = str(record.get("termination", "") or "").strip()
        if terminal:
            return terminal
        return termination or "No recorded hit"

    def _collect_source_illumination_records(
        self,
        target_surface_index: int | None = None,
        *,
        ray_records: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        ray_records = list(ray_records if ray_records is not None else self._collect_ray_analysis_records())
        if not ray_records:
            return []
        if target_surface_index is None:
            target_surface_index = self._source_illumination_target_index()
        try:
            target_surface_index = int(target_surface_index)
        except Exception:
            return []
        if not (0 <= target_surface_index < len(self.rows)):
            return []
        return collect_source_illumination_records(
            ray_records,
            target_surface_index,
            self.rows[target_surface_index].name if 0 <= target_surface_index < len(self.rows) else "",
            terminal_label_for_record=self._source_illumination_terminal_label_for_record,
        )

    def _main_source_illumination_report_dialog(self) -> MainSourceIlluminationReportDialog:
        dialog = self.__dict__.get("_main_source_illumination_report_dialog_instance")
        if dialog is None:
            dialog = MainSourceIlluminationReportDialog(self)
            self._main_source_illumination_report_dialog_instance = dialog
        return dialog

    def open_source_illumination_report(self) -> None:
        self._main_source_illumination_report_dialog().open_source_illumination_report()

    def _close_source_illumination_report(self) -> None:
        self._main_source_illumination_report_dialog()._close_source_illumination_report()

    def _set_source_illumination_detail_text(self, text: str) -> None:
        self._main_source_illumination_report_dialog()._set_source_illumination_detail_text(text)

    def _source_illumination_record_detail_text(self, record: dict[str, object]) -> str:
        return self._main_source_illumination_report_dialog()._source_illumination_record_detail_text(record)

    def _refresh_source_illumination_detail(self) -> None:
        self._main_source_illumination_report_dialog()._refresh_source_illumination_detail()

    def _refresh_source_illumination_report_if_open(self) -> None:
        self._main_source_illumination_report_dialog()._refresh_source_illumination_report_if_open()

    def _refresh_source_illumination_report(self) -> None:
        self._main_source_illumination_report_dialog()._refresh_source_illumination_report()

    def _source_illumination_report_text(self) -> str:
        return self._main_source_illumination_report_dialog()._source_illumination_report_text()

    def copy_source_illumination_report_to_clipboard(self) -> None:
        self._main_source_illumination_report_dialog().copy_source_illumination_report_to_clipboard()

    def export_source_illumination_csv(self) -> None:
        self._main_source_illumination_report_dialog().export_source_illumination_csv()

    def _main_branch_throughput_report_dialog(self) -> MainBranchThroughputReportDialog:
        dialog = self.__dict__.get("_main_branch_throughput_report_dialog_instance")
        if dialog is None:
            dialog = MainBranchThroughputReportDialog(
                self,
                analysis_path_filter_default=ANALYSIS_PATH_FILTER_DEFAULT,
            )
            self._main_branch_throughput_report_dialog_instance = dialog
        return dialog

    def open_branch_throughput_report(self) -> None:
        self._main_branch_throughput_report_dialog().open_branch_throughput_report()

    def _close_branch_throughput_report(self) -> None:
        self._main_branch_throughput_report_dialog()._close_branch_throughput_report()

    def _refresh_branch_throughput_report_if_open(self) -> None:
        self._main_branch_throughput_report_dialog()._refresh_branch_throughput_report_if_open()

    @staticmethod
    def _branch_throughput_filter_choices(records: list[dict[str, object]]) -> list[str]:
        return branch_throughput_filter_choices(records)

    @staticmethod
    def _branch_throughput_filter_matches(record: dict[str, object], filter_text: str) -> bool:
        return branch_throughput_filter_matches(record, filter_text)

    def _filtered_branch_throughput_records(self, records: list[dict[str, object]]) -> list[dict[str, object]]:
        filter_var = self.__dict__.get("_branch_throughput_filter_var")
        filter_text = (
            filter_var.get()
            if filter_var is not None
            else ANALYSIS_PATH_FILTER_DEFAULT
        )
        return filtered_branch_throughput_records(records, filter_text)

    def _current_analysis_branch_filter(self) -> str:
        value = ANALYSIS_PATH_FILTER_DEFAULT
        var = getattr(self, "analysis_branch_filter_var", None)
        if var is not None:
            try:
                value = _normalize_path_filter_label(var.get())
            except Exception:
                value = ANALYSIS_PATH_FILTER_DEFAULT
        return _normalize_path_filter_label(value)

    def _current_coherent_sum_mode(self) -> str:
        value = COHERENT_SUM_MODE_DEFAULT
        var = getattr(self, "coherent_sum_mode_var", None)
        if var is not None:
            try:
                value = _normalize_coherent_sum_mode(var.get())
            except Exception:
                value = COHERENT_SUM_MODE_DEFAULT
        return _normalize_coherent_sum_mode(value)

    @staticmethod
    def _normalize_ray_display_mode(value) -> str:
        text = str(value or RAY_DISPLAY_DEFAULT).strip()
        aliases = {
            "all": RAY_DISPLAY_ALL,
            "all traced rays": RAY_DISPLAY_ALL,
            "all rays": RAY_DISPLAY_ALL,
            "detector": RAY_DISPLAY_DETECTOR,
            "detector hits": RAY_DISPLAY_DETECTOR,
            "image": RAY_DISPLAY_DETECTOR,
            "image hits": RAY_DISPLAY_DETECTOR,
            "missed": RAY_DISPLAY_MISSED_DETECTOR,
            "missed detector": RAY_DISPLAY_MISSED_DETECTOR,
            "missed detectors": RAY_DISPLAY_MISSED_DETECTOR,
            "missed image": RAY_DISPLAY_MISSED_DETECTOR,
            "absorbed": RAY_DISPLAY_ABSORBED,
            "absorber": RAY_DISPLAY_ABSORBED,
            "escaped": RAY_DISPLAY_ESCAPED,
            "escape": RAY_DISPLAY_ESCAPED,
            "stopped": RAY_DISPLAY_STOPPED,
            "diagnostic": RAY_DISPLAY_STOPPED,
            "stopped / diagnostic": RAY_DISPLAY_STOPPED,
            "split": RAY_DISPLAY_SPLITTER,
            "splitter": RAY_DISPLAY_SPLITTER,
            "beam splitter": RAY_DISPLAY_SPLITTER,
            "beam-splitter": RAY_DISPLAY_SPLITTER,
            "beam-splitter paths": RAY_DISPLAY_SPLITTER,
            "hide direct": RAY_DISPLAY_SPLITTER,
            "hide direct source rays": RAY_DISPLAY_SPLITTER,
            "useful": RAY_DISPLAY_SPLITTER,
            "useful paths": RAY_DISPLAY_SPLITTER,
        }
        return aliases.get(text.lower(), text if text in RAY_DISPLAY_VALUES else RAY_DISPLAY_DEFAULT)

    def _current_ray_display_mode(self) -> str:
        var = getattr(self, "ray_display_mode_var", None)
        if var is None:
            return RAY_DISPLAY_DEFAULT
        try:
            return self._normalize_ray_display_mode(var.get())
        except Exception:
            return RAY_DISPLAY_DEFAULT

    def _refresh_analysis_branch_choices(self) -> None:
        menu = getattr(self, "analysis_branch_filter_menu", None)
        var = getattr(self, "analysis_branch_filter_var", None)
        if menu is None or var is None:
            return
        records = self._collect_branch_throughput_records(ray_records=self._active_ray_analysis_records())
        choices = self._branch_throughput_filter_choices(records)
        current = self._current_analysis_branch_filter()
        if current not in choices and not records:
            choices.append(current)
        menu["values"] = choices
        if current not in choices:
            var.set(ANALYSIS_PATH_FILTER_DEFAULT)

    def _ray_record_branch_filter_matches(self, record: dict[str, object], filter_text: str) -> bool:
        branch_path = str(record.get("branch_path", "") or "").strip()
        last_surface = record.get("last_surface")
        terminal = self._terminal_surface_label(last_surface, str(record.get("last_name", "") or ""))
        pseudo_record = {
            "output": self._branch_output_label(branch_path),
            "branch_code": "".join(self._branch_path_selector_sequence(branch_path)) or "primary",
            "terminal": terminal,
        }
        return self._branch_throughput_filter_matches(pseudo_record, filter_text)

    def _record_terminal_hit_local_xy(self, system, record: dict[str, object]) -> tuple[float, float, str]:
        hits = list(record.get("hits", []) or [])
        if not hits:
            return (np.nan, np.nan, "world")
        hit = hits[-1]
        try:
            surface_index = int(record.get("last_surface"))
        except Exception:
            surface_index = -1
        return self._hit_local_xy(system, surface_index, hit)

    def _hit_local_xy(self, system, surface_index: int, hit: dict[str, object]) -> tuple[float, float, str]:
        try:
            world = np.asarray(
                [
                    float(hit.get("x", np.nan)),
                    float(hit.get("y", np.nan)),
                    float(hit.get("z", np.nan)),
                    1.0,
                ],
                dtype=float,
            )
        except Exception:
            return (np.nan, np.nan, "world")
        if not np.all(np.isfinite(world[:3])):
            return (np.nan, np.nan, "world")
        transforms = self._system_transform_list(system)
        if transforms is not None and 0 <= surface_index < len(transforms):
            try:
                transform = np.asarray(transforms[surface_index], dtype=float)
                local = np.linalg.inv(transform) @ world
                if np.all(np.isfinite(local[:2])):
                    return (float(local[0]), float(local[1]), "local")
            except Exception:
                pass
        return (float(world[0]), float(world[1]), "world")

    def _source_illumination_hit_samples(
        self,
        system,
        target_surface_index: int | None = None,
        *,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        if target_surface_index is None:
            target_surface_index = self._source_illumination_target_index()
        try:
            target_surface_index = int(target_surface_index)
        except Exception:
            return empty_source_illumination_samples()
        if not (0 <= target_surface_index < len(self.rows)):
            return empty_source_illumination_samples()
        source_records = list(ray_records if ray_records is not None else self._collect_ray_analysis_records())
        diagnostic_records = self._collect_source_illumination_records(
            target_surface_index,
            ray_records=source_records,
        )
        return source_illumination_hit_samples_from_records(
            source_records,
            target_surface_index,
            self.rows[target_surface_index].name,
            hit_xy_for_hit=lambda hit: self._hit_local_xy(system, target_surface_index, hit),
            diagnostic_records=diagnostic_records,
        )

    def _source_illumination_target_model(self, samples: dict[str, object]) -> dict[str, object]:
        target_index = samples.get("target_surface")
        model: dict[str, object] = {
            "target_surface": target_index,
            "is_detector": self._surface_index_is_detector(target_index),
        }
        if not bool(model["is_detector"]):
            return model
        settings = self._detector_settings_for_surface(target_index)
        model["active_width_mm"] = float(settings.get("active_width_mm", 0.0) or 0.0)
        model["active_height_mm"] = float(settings.get("active_height_mm", 0.0) or 0.0)
        try:
            model["diameter_mm"] = self._safe_positive_float(getattr(self.rows[int(target_index)], "diameter", 0.0), 0.0)
        except Exception:
            model["diameter_mm"] = 0.0
        return model

    def _source_illumination_map_extent(
        self,
        samples: dict[str, object],
        x_values: np.ndarray,
        y_values: np.ndarray,
    ) -> tuple[float, float, float, float]:
        return source_illumination_map_extent(samples, x_values, y_values, self._source_illumination_target_model(samples))

    def _source_illumination_map_data(
        self,
        system,
        target_surface_index: int | None = None,
        *,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        samples = self._source_illumination_hit_samples(system, target_surface_index, ray_records=ray_records)
        return source_illumination_map_data_from_samples(
            samples,
            target_model=self._source_illumination_target_model(samples),
        )

    def _plot_source_illumination_map_analysis(
        self,
        analysis_ax,
        system,
        *,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        target_index = self._source_illumination_target_index()
        data = self._source_illumination_map_data(system, target_index, ray_records=ray_records)
        samples = dict(data["samples"])
        x_values = np.asarray(data["x_values"], dtype=float)
        density = np.asarray(data["density"], dtype=float)
        extent = list(data["extent"])
        image = analysis_ax.imshow(density, origin="lower", extent=extent, cmap="magma", aspect="auto")
        source_ids = list(data.get("source_ids", []) or [])
        colors = self._field_colors(max(1, len(set(source_ids))))
        color_by_source = {source_id: colors[index % len(colors)] for index, source_id in enumerate(sorted(set(source_ids)))}
        for centroid in list(data.get("source_centroids", []) or []):
            source_id = str(centroid.get("source_id", ""))
            analysis_ax.scatter(
                [float(centroid.get("x_mm", 0.0) or 0.0)],
                [float(centroid.get("y_mm", 0.0) or 0.0)],
                s=42,
                color=color_by_source[source_id],
                edgecolors="white",
                linewidths=0.8,
                label=str(centroid.get("source_name", "") or source_id),
                zorder=5,
            )
        if len(set(source_ids)) > 1:
            analysis_ax.legend(loc="upper right", fontsize=7, title="Source centroid")
        coordinate_label = str(data.get("coordinate_label", "target local"))
        target_label = (
            f"S{int(samples['target_surface'])}: {samples.get('target_name', '')}"
            if samples.get("target_surface") is not None
            else "target"
        )
        input_power = float(samples.get("input_power", 0.0) or 0.0)
        hit_power = float(samples.get("hit_power", 0.0) or 0.0)
        throughput = hit_power / input_power if input_power > 0.0 else np.nan
        hit_rays = int(samples.get("hit_rays", 0) or 0)
        launched_rays = int(samples.get("launched_rays", 0) or 0)
        missed_rays = int(samples.get("missed_rays", 0) or 0)
        loss_summary = str(samples.get("loss_summary", "") or "None")
        analysis_ax.set_title(f"Source Illumination Map | {target_label}")
        analysis_ax.set_xlabel(f"X [{coordinate_label}, mm]")
        analysis_ax.set_ylabel(f"Y [{coordinate_label}, mm]")
        analysis_ax.set_box_aspect(0.72)
        analysis_ax.grid(False)
        self.figure.colorbar(image, ax=analysis_ax, fraction=0.046, pad=0.04, label="Relative hit power density")
        analysis_ax.text(
            0.02,
            0.98,
            (
                f"sources={int(samples.get('source_count', 0) or 0)} | events={x_values.size}\n"
                f"rays hit={hit_rays}/{launched_rays}, missed={missed_rays}\n"
                f"power throughput={self._format_percent_value(throughput)}"
                + (f"\nloss: {loss_summary}" if missed_rays > 0 and loss_summary != "None" else "")
            ),
            transform=analysis_ax.transAxes,
            ha="left",
            va="top",
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#cbd5e1", "alpha": 0.82, "pad": 3},
        )
        self.append_debug(
            f"Source illumination map ok: target={target_label}, events={x_values.size}, "
            f"sources={samples.get('source_count')}, throughput={throughput:.6g}"
        )

    def _main_path_detector_analysis(self) -> MainPathDetectorAnalysis:
        service = self.__dict__.get("_main_path_detector_analysis_instance")
        if service is None:
            service = MainPathDetectorAnalysis(self)
            self._main_path_detector_analysis_instance = service
        return service

    def _branch_detector_spot_samples(
        self,
        system,
        filter_text: str,
        *,
        require_detector: bool = False,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._branch_detector_spot_samples(
            system,
            filter_text,
            require_detector=require_detector,
            ray_records=ray_records,
        )

    def _plot_branch_detector_spot_analysis(
        self,
        analysis_ax,
        system,
        mode: str,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_branch_detector_spot_analysis(
            analysis_ax,
            system,
            mode,
            ray_records=ray_records,
        )

    def _detector_map_extent(
        self,
        samples: dict[str, object],
        x_values: np.ndarray,
        y_values: np.ndarray,
    ) -> tuple[float, float, float, float]:
        return self._main_path_detector_analysis()._detector_map_extent(samples, x_values, y_values)

    def _branch_detector_map_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._branch_detector_map_data(
            system,
            filter_text,
            ray_records=ray_records,
        )

    def _branch_detector_psf_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._branch_detector_psf_data(
            system,
            filter_text,
            ray_records=ray_records,
        )

    def _plot_branch_detector_psf_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_branch_detector_psf_analysis(
            analysis_ax,
            system,
            wavelength,
            ray_records=ray_records,
        )

    def _branch_detector_mtf_data(
        self,
        system,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._branch_detector_mtf_data(
            system,
            filter_text,
            ray_records=ray_records,
        )

    def _plot_branch_detector_mtf_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_branch_detector_mtf_analysis(
            analysis_ax,
            system,
            wavelength,
            ray_records=ray_records,
        )

    @staticmethod
    def _branch_psf_csv_columns() -> tuple[str, ...]:
        return MainPathDetectorAnalysis._branch_psf_csv_columns()

    def _branch_detector_psf_csv_rows(self, data: dict[str, object]) -> list[dict[str, object]]:
        return self._main_path_detector_analysis()._branch_detector_psf_csv_rows(data)

    @staticmethod
    def _branch_mtf_csv_columns() -> tuple[str, ...]:
        return MainPathDetectorAnalysis._branch_mtf_csv_columns()

    def _branch_detector_mtf_csv_rows(
        self,
        data: dict[str, object],
        *,
        target_freq: float | None = None,
        mtf_mode: str | None = None,
    ) -> list[dict[str, object]]:
        return self._main_path_detector_analysis()._branch_detector_mtf_csv_rows(
            data,
            target_freq=target_freq,
            mtf_mode=mtf_mode,
        )

    def export_branch_psf_csv(self) -> None:
        self._main_path_detector_analysis().export_branch_psf_csv()

    def export_branch_mtf_csv(self) -> None:
        self._main_path_detector_analysis().export_branch_mtf_csv()

    def _plot_branch_detector_map_analysis(
        self,
        analysis_ax,
        system,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_branch_detector_map_analysis(
            analysis_ax,
            system,
            ray_records=ray_records,
        )

    def export_detector_map_csv(self) -> None:
        self._main_path_detector_analysis().export_detector_map_csv()

    @staticmethod
    def _coherent_detector_group_key(
        coherence_mode: str,
        source_id: object,
        source_ray_index: object,
        sample_index: int,
    ) -> str:
        return MainPathDetectorAnalysis._coherent_detector_group_key(
            coherence_mode,
            source_id,
            source_ray_index,
            sample_index,
        )

    @staticmethod
    def _coherent_detector_pair_key(code_a: str, code_b: str) -> str:
        return MainPathDetectorAnalysis._coherent_detector_pair_key(code_a, code_b)

    def _should_use_gaussian_q_detector_weighting(self) -> bool:
        return self._main_path_detector_analysis()._should_use_gaussian_q_detector_weighting()

    def _gaussian_q_detector_sample_weights(
        self,
        records: list[dict[str, object]],
        x_values: np.ndarray,
        y_values: np.ndarray,
        power_values: np.ndarray,
        wavelength: float,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._gaussian_q_detector_sample_weights(
            records,
            x_values,
            y_values,
            power_values,
            wavelength,
        )

    def _coherent_detector_field_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        *,
        coherence_mode: str | None = None,
        opd_offset_um: float = 0.0,
        phase_ramp_x_mrad: float = 0.0,
        phase_ramp_y_mrad: float = 0.0,
        visibility_scale: float = 1.0,
        gaussian_q_weighting: bool = False,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._coherent_detector_field_data(
            system,
            wavelength,
            filter_text,
            coherence_mode=coherence_mode,
            opd_offset_um=opd_offset_um,
            phase_ramp_x_mrad=phase_ramp_x_mrad,
            phase_ramp_y_mrad=phase_ramp_y_mrad,
            visibility_scale=visibility_scale,
            gaussian_q_weighting=gaussian_q_weighting,
            ray_records=ray_records,
        )

    def export_coherent_detector_csv(self) -> None:
        self._main_path_detector_analysis().export_coherent_detector_csv()

    def _plot_coherent_detector_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_coherent_detector_analysis(
            analysis_ax,
            system,
            wavelength,
            ray_records=ray_records,
        )

    def _branch_field_analysis_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._branch_field_analysis_data(
            system,
            wavelength,
            filter_text,
            ray_records=ray_records,
        )

    @staticmethod
    def _write_branch_field_csv(path: str | Path, data: dict[str, object], wavelength: float) -> None:
        MainPathDetectorAnalysis._write_branch_field_csv(path, data, wavelength)

    def export_branch_field_csv(self) -> None:
        self._main_path_detector_analysis().export_branch_field_csv()

    def _plot_branch_field_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_branch_field_analysis(
            analysis_ax,
            system,
            wavelength,
            ray_records=ray_records,
        )

    @staticmethod
    def _fft_angle_axis_mrad(edges: np.ndarray, wavelength_um: float) -> tuple[np.ndarray, float]:
        return MainPathDetectorAnalysis._fft_angle_axis_mrad(edges, wavelength_um)

    @staticmethod
    def _fft_vector_field_intensity(fields: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
        return MainPathDetectorAnalysis._fft_vector_field_intensity(fields)

    def _diffraction_detector_field_data(
        self,
        system,
        wavelength: float,
        filter_text: str | None = None,
        ray_records: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        return self._main_path_detector_analysis()._diffraction_detector_field_data(
            system,
            wavelength,
            filter_text,
            ray_records=ray_records,
        )

    def _plot_diffraction_detector_analysis(
        self,
        analysis_ax,
        system,
        wavelength: float,
        ray_records: list[dict[str, object]] | None = None,
    ) -> None:
        self._main_path_detector_analysis()._plot_diffraction_detector_analysis(
            analysis_ax,
            system,
            wavelength,
            ray_records=ray_records,
        )

    def _refresh_branch_throughput_report(self) -> None:
        self._main_branch_throughput_report_dialog()._refresh_branch_throughput_report()

    def _branch_throughput_report_text(self) -> str:
        return self._main_branch_throughput_report_dialog()._branch_throughput_report_text()

    def copy_branch_throughput_report_to_clipboard(self) -> None:
        self._main_branch_throughput_report_dialog().copy_branch_throughput_report_to_clipboard()

    def export_branch_throughput_csv(self) -> None:
        self._main_branch_throughput_report_dialog().export_branch_throughput_csv()

    def _collect_detector_aperture_records(
        self,
        ray_records: list[dict[str, object]] | None = None,
    ) -> list[dict[str, object]]:
        records = list(ray_records if ray_records is not None else self._active_ray_analysis_records())
        detector_indices = self._scene_detector_surface_indices()
        return collect_detector_aperture_records(
            records,
            detector_surface_indices=detector_indices,
            terminal_label_for_surface=lambda surface: self._terminal_surface_label(surface),
        )

    @staticmethod
    def _detector_aperture_counts(records: list[dict[str, object]]) -> dict[str, object]:
        if not records:
            return {
                "detectors": 0,
                "rays": 0,
                "hits": 0,
                "misses": 0,
                "other": 0,
                "hit_power": 0.0,
                "miss_power": 0.0,
                "worst_margin": None,
                "worst_ray": "",
                "worst_detector": "",
            }
        totals = {
            "detectors": len(records),
            "rays": sum(int(record.get("ray_count", 0) or 0) for record in records),
            "hits": sum(int(record.get("hit_count", 0) or 0) for record in records),
            "misses": sum(int(record.get("miss_count", 0) or 0) for record in records),
            "other": sum(int(record.get("other_count", 0) or 0) for record in records),
            "hit_power": sum(float(record.get("hit_power", 0.0) or 0.0) for record in records),
            "miss_power": sum(float(record.get("miss_power", 0.0) or 0.0) for record in records),
            "worst_margin": None,
            "worst_ray": "",
            "worst_detector": "",
        }
        worst_margin = None
        worst_record = None
        for record in records:
            try:
                margin = float(record.get("worst_miss_margin_mm", np.nan))
            except Exception:
                margin = np.nan
            if not np.isfinite(margin):
                continue
            if worst_margin is None or margin > worst_margin:
                worst_margin = float(margin)
                worst_record = record
        if worst_record is not None:
            totals["worst_margin"] = worst_margin
            totals["worst_ray"] = worst_record.get("worst_miss_ray_index", "")
            totals["worst_detector"] = worst_record.get("detector", "")
        return totals

    def _detector_aperture_status_suffix(self) -> str:
        try:
            records = self._collect_detector_aperture_records(ray_records=self._active_ray_analysis_records())
            self._detector_aperture_records = records
            counts = self._detector_aperture_counts(records)
        except Exception:
            return ""
        misses = int(counts.get("misses", 0) or 0)
        if misses <= 0:
            return ""
        worst = counts.get("worst_margin")
        if worst is None:
            return f" | detector misses {misses}"
        return f" | detector misses {misses}, worst {float(worst):.4g} mm"

    def _main_detector_aperture_report_dialog(self) -> MainDetectorApertureReportDialog:
        dialog = self.__dict__.get("_main_detector_aperture_report_dialog_instance")
        if dialog is None:
            dialog = MainDetectorApertureReportDialog(self)
            self._main_detector_aperture_report_dialog_instance = dialog
        return dialog

    def open_detector_aperture_report(self) -> None:
        self._main_detector_aperture_report_dialog().open_detector_aperture_report()

    def _close_detector_aperture_report(self) -> None:
        self._main_detector_aperture_report_dialog()._close_detector_aperture_report()

    def _refresh_detector_aperture_report_if_open(self) -> None:
        self._main_detector_aperture_report_dialog()._refresh_detector_aperture_report_if_open()

    def _refresh_detector_aperture_report(self) -> None:
        self._main_detector_aperture_report_dialog()._refresh_detector_aperture_report()

    def _detector_aperture_report_text(self) -> str:
        return self._main_detector_aperture_report_dialog()._detector_aperture_report_text()

    def copy_detector_aperture_report_to_clipboard(self) -> None:
        self._main_detector_aperture_report_dialog().copy_detector_aperture_report_to_clipboard()

    def export_detector_aperture_csv(self) -> None:
        self._main_detector_aperture_report_dialog().export_detector_aperture_csv()

    @staticmethod
    def _scene_graph_value_present(value) -> bool:
        if value is None:
            return False
        if isinstance(value, (int, float, np.integer, np.floating)):
            return bool(np.isfinite(float(value)) and abs(float(value)) > 1e-15)
        text = str(value).strip()
        return bool(text and text.lower() not in {"none", "null", "0", "0.0", "[]", "{}"})

    def _nonseq_row_features(self, row: SurfaceRow) -> str:
        advanced = dict(row.advanced or {})
        features: list[str] = []
        if row.surface == "Mirror" or str(row.glass).upper() == "MIRROR":
            features.append("mirror")
        if row.surface == BEAM_SPLITTER_SURFACE or self._scene_graph_value_present(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR)):
            features.append("beam splitter")
        if row.surface == DIFFUSE_OBJECT_SURFACE or self._scene_graph_value_present(advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR)):
            features.append("diffuse scatter")
        if row.surface == "Thin Lens":
            features.append("thin lens")
        if abs(float(row.k)) > 1e-15 or self._scene_graph_value_present(advanced.get("AspherData")):
            features.append("asphere")
        if self._scene_graph_value_present(advanced.get("ZNK")):
            features.append("Zernike")
        if self._scene_graph_value_present(row.extra_data) or self._scene_graph_value_present(advanced.get("ExtraData")):
            features.append("custom sag")
        if self._scene_graph_value_present(row.uda) or self._scene_graph_value_present(advanced.get("UDA")):
            features.append("UDA")
        if self._scene_graph_value_present(advanced.get("Mask_Shape")) or self._scene_graph_value_present(advanced.get("Mask_Type")):
            features.append("mask")
        if self._scene_graph_value_present(advanced.get("Solid_3d_stl")):
            features.append("STL solid")
        if self._scene_graph_value_present(advanced.get("Coating")) or self._scene_graph_value_present(advanced.get("CoatingMet")):
            features.append("coating")
        if abs(float(row.diff_ord)) > 1e-15 or abs(float(row.grating_d)) > 1e-15:
            features.append("grating")
        if abs(float(row.tilt_x)) > 1e-15 or abs(float(row.tilt_y)) > 1e-15 or abs(float(row.tilt_z)) > 1e-15:
            features.append("tilted")
        if abs(float(row.desp_x)) > 1e-15 or abs(float(row.desp_y)) > 1e-15 or abs(float(row.desp_z)) > 1e-15:
            features.append("decentered")
        return ", ".join(features) if features else "-"

    def _nonseq_row_detail(self, row: SurfaceRow) -> str:
        parts = [
            f"Rc={float(row.rc):.6g}",
            f"k={float(row.k):.6g}",
            f"T={float(row.thickness):.6g}",
            f"D={float(row.diameter):.6g}",
        ]
        if abs(float(row.tilt_x)) > 1e-15 or abs(float(row.tilt_y)) > 1e-15 or abs(float(row.tilt_z)) > 1e-15:
            parts.append(f"tilt=({float(row.tilt_x):.6g}, {float(row.tilt_y):.6g}, {float(row.tilt_z):.6g})")
        if abs(float(row.desp_x)) > 1e-15 or abs(float(row.desp_y)) > 1e-15 or abs(float(row.desp_z)) > 1e-15:
            parts.append(f"decenter=({float(row.desp_x):.6g}, {float(row.desp_y):.6g}, {float(row.desp_z):.6g})")
        if abs(float(row.axis_move)) > 1e-15:
            parts.append(f"AxisMove={float(row.axis_move):.6g}")
        advanced = dict(row.advanced or {})
        stl_path = str(advanced.get("Solid_3d_stl", "") or "").strip()
        if stl_path and stl_path != "None":
            parts.append(f"STL={Path(stl_path).name}")
            path = self._stl_path_from_row(row)
            if path is not None and path.exists():
                try:
                    parts.append("mesh=" + short_stl_mesh_diagnostics(inspect_stl_mesh(path)))
                except Exception:
                    pass
        if row.surface == BEAM_SPLITTER_SURFACE or BEAM_SPLITTER_ADVANCED_ATTR in advanced:
            parts.append(_beam_splitter_summary(advanced.get(BEAM_SPLITTER_ADVANCED_ATTR)))
        if row.surface == DIFFUSE_OBJECT_SURFACE or DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
            parts.append(_diffuse_scatter_summary(advanced.get(DIFFUSE_SCATTER_ADVANCED_ATTR)))
        return " | ".join(parts)

    def _scene_optical_volumes_for_graph(self) -> list[object]:
        bundle = getattr(self, "_last_scene_bundle", None)
        volumes = list(getattr(bundle, "optical_volumes", []) or []) if isinstance(bundle, SceneBundle) else []
        if volumes:
            return volumes
        try:
            return build_scene_optical_volumes(self.rows)
        except Exception:
            return []

    @staticmethod
    def _scene_optical_volume_features(volume: object) -> str:
        parts = [
            str(getattr(volume, "volume_type", "") or "optical_solid"),
            f"faces={int(getattr(volume, 'boundary_face_count', 0) or 0)}",
        ]
        if tuple(getattr(volume, "diagnostics", ()) or ()):
            parts.append("diagnostics")
        return ", ".join(part for part in parts if part)

    @staticmethod
    def _scene_optical_volume_detail(volume: object) -> str:
        centroid = np.asarray(getattr(volume, "centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
        face_ids = [str(item) for item in tuple(getattr(volume, "boundary_face_ids", ()) or ()) if str(item)]
        diagnostics = [str(item) for item in tuple(getattr(volume, "diagnostics", ()) or ()) if str(item)]
        source_stl = str(getattr(volume, "source_stl", "") or "").strip()
        parts = [
            f"volume_id={str(getattr(volume, 'volume_id', '') or '-')}",
            f"ambient={str(getattr(volume, 'ambient_material', '') or 'AIR')}",
        ]
        if centroid.size >= 3 and np.all(np.isfinite(centroid[:3])):
            parts.append(
                "centroid=({:.6g}, {:.6g}, {:.6g})".format(
                    float(centroid[0]),
                    float(centroid[1]),
                    float(centroid[2]),
                )
            )
        if face_ids:
            parts.append("faces=" + ",".join(face_ids))
        if source_stl:
            parts.append(f"STL={Path(source_stl).name}")
        if diagnostics:
            parts.append("diagnostics=" + "; ".join(diagnostics))
        return " | ".join(parts)

    def _scene_boundary_faces_for_graph(self) -> list[object]:
        bundle = getattr(self, "_last_scene_bundle", None)
        faces = list(getattr(bundle, "boundary_faces", []) or []) if isinstance(bundle, SceneBundle) else []
        if faces:
            return faces
        try:
            return build_scene_boundary_faces(self.rows)
        except Exception:
            return []

    @staticmethod
    def _scene_boundary_face_text(face: object) -> str:
        face_id = str(getattr(face, "face_id", "") or "").strip() or "Face"
        side = str(getattr(face, "side_2d", "") or "").strip()
        function = str(getattr(face, "function", "") or "").strip()
        parts = [part for part in (side, function) if part and part not in {"Auto", "Unassigned"}]
        return f"{face_id}: {' '.join(parts)}" if parts else face_id

    @staticmethod
    def _scene_boundary_face_features(face: object) -> str:
        triangle_count = int(getattr(face, "triangle_count", 0) or 0)
        triangle_indices = tuple(getattr(face, "triangle_indices", ()) or ())
        membership = "exact triangle membership" if triangle_indices else "face-plane fallback"
        parts = [f"triangles={triangle_count}", membership]
        coating = str(getattr(face, "coating", "") or "").strip()
        if coating:
            parts.append(f"coating={coating}")
        if tuple(getattr(face, "diagnostics", ()) or ()):
            parts.append("diagnostics")
        return ", ".join(parts)

    @staticmethod
    def _scene_boundary_face_detail(face: object) -> str:
        centroid = np.asarray(getattr(face, "centroid_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
        normal = np.asarray(getattr(face, "normal_world", (np.nan, np.nan, np.nan)), dtype=float).reshape(-1)
        area = float(getattr(face, "area_mm2", 0.0) or 0.0)
        source_stl = str(getattr(face, "source_stl", "") or "").strip()
        diagnostics = [str(item) for item in tuple(getattr(face, "diagnostics", ()) or ()) if str(item)]
        parts = [
            f"side={str(getattr(face, 'side_2d', '') or '-')}",
            f"port={str(getattr(face, 'port_role', '') or '-')}",
            f"area={area:.6g} mm^2",
        ]
        if centroid.size >= 3 and np.all(np.isfinite(centroid[:3])):
            parts.append(
                "centroid=({:.6g}, {:.6g}, {:.6g})".format(
                    float(centroid[0]),
                    float(centroid[1]),
                    float(centroid[2]),
                )
            )
        if normal.size >= 3 and np.all(np.isfinite(normal[:3])):
            parts.append(
                "normal=({:.6g}, {:.6g}, {:.6g})".format(
                    float(normal[0]),
                    float(normal[1]),
                    float(normal[2]),
                )
            )
        if source_stl:
            parts.append(f"STL={Path(source_stl).name}")
        if diagnostics:
            parts.append("diagnostics=" + "; ".join(diagnostics))
        return " | ".join(parts)

    def _current_scene_row_mapping(self, scene_sources: list[SceneSource3D] | None = None):
        sources = scene_sources if scene_sources is not None else self._collect_scene_sources()
        return build_scene_row_mapping(
            self.rows,
            sources,
            include_sources=True,
            source_row_order=normalize_source_row_order(
                getattr(self, "layout_scene_row_order", SOURCE_ROW_ORDER_DEFAULT)
            ),
        )

    def _scene_targets_for_graph(self, trace_state: dict[str, object] | None = None) -> list[SceneTarget3D]:
        if trace_state is None:
            try:
                trace_state = self._resolved_trace_mode(system=getattr(self, "last_system", None))
            except Exception:
                trace_state = {"use_nonseq": False}
        return build_scene_targets(
            self.rows,
            target_surface=self._current_nonseq_target_surface_index(),
            detector_surface_indices=self._scene_detector_surface_indices(trace_state),
        )

    @staticmethod
    def _scene_target_vector_text(values: object) -> str:
        try:
            arr = np.asarray(values, dtype=float).reshape(-1)
        except Exception:
            return "(nan, nan, nan)"
        if arr.size < 3 or not np.all(np.isfinite(arr[:3])):
            return "(nan, nan, nan)"
        return "({:.6g}, {:.6g}, {:.6g})".format(float(arr[0]), float(arr[1]), float(arr[2]))

    @staticmethod
    def _scene_target_features(target: SceneTarget3D) -> str:
        parts = [str(getattr(target, "role", "") or "target")]
        if bool(getattr(target, "is_detector", False)):
            parts.append("detector")
        if bool(getattr(target, "is_object", False)):
            parts.append("object")
        if bool(getattr(target, "is_active_target", False)):
            parts.append("active TargSurf")
        bins = str(getattr(target, "detector_bins", "") or "").strip()
        if bins:
            parts.append(f"bins={bins}")
        width = float(getattr(target, "active_width_mm", 0.0) or 0.0)
        height = float(getattr(target, "active_height_mm", 0.0) or 0.0)
        if width > 0.0 or height > 0.0:
            parts.append(f"active={width:g}x{height:g} mm")
        return ", ".join(parts)

    def _scene_target_detail(self, target: SceneTarget3D) -> str:
        return (
            f"center={self._scene_target_vector_text(getattr(target, 'center_world', None))} | "
            f"normal={self._scene_target_vector_text(getattr(target, 'normal_world', None))} | "
            f"tangent={self._scene_target_vector_text(getattr(target, 'tangent_world', None))} | "
            f"diameter={float(getattr(target, 'diameter', 0.0) or 0.0):.6g} mm"
        )

    def _scene_placements_for_graph(
        self,
        scene_targets: list[SceneTarget3D] | None = None,
    ) -> list[ScenePlacement3D]:
        bundle = getattr(self, "_last_scene_bundle", None)
        placements = list(getattr(bundle, "placements", []) or []) if isinstance(bundle, SceneBundle) else []
        if placements:
            return placements
        try:
            targets = scene_targets if scene_targets is not None else self._scene_targets_for_graph()
            return build_scene_placements(self.rows, targets=targets)
        except Exception:
            return []

    @staticmethod
    def _scene_placement_features(placement: ScenePlacement3D) -> str:
        parts = [str(getattr(placement, "source_kind", "") or "surface_row")]
        parts.append(f"anchor={str(getattr(placement, 'anchor', '') or 'row_pose')}")
        if bool(getattr(placement, "snap_enabled", False)):
            parts.append(
                "snap={:.6g} mm/{:.6g} deg".format(
                    float(getattr(placement, "snap_mm", 0.0) or 0.0),
                    float(getattr(placement, "snap_deg", 0.0) or 0.0),
                )
            )
        else:
            parts.append("snap=off")
        if bool(getattr(placement, "grid_visible", True)):
            parts.append(
                "grid={:.6g}/{:.6g} mm".format(
                    float(getattr(placement, "grid_spacing_mm", 0.0) or 0.0),
                    float(getattr(placement, "grid_extent_mm", 0.0) or 0.0),
                )
            )
        else:
            parts.append("grid=off")
        metadata = dict(getattr(placement, "metadata", {}) or {})
        settings = metadata.get("scene_placement_settings", {})
        if isinstance(settings, dict):
            constraint_kind = str(settings.get("last_constraint_kind", "") or "").strip()
            target_label = str(settings.get("last_constraint_target_label", "") or "").strip()
            if constraint_kind:
                suffix = f"->{target_label}" if target_label else ""
                parts.append(f"constraint={constraint_kind}{suffix}")
        return ", ".join(parts)

    def _scene_placement_detail(self, placement: ScenePlacement3D) -> str:
        rotation = np.asarray(getattr(placement, "pose_rotation_deg", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)
        translation = np.asarray(getattr(placement, "pose_translation", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)
        metadata = dict(getattr(placement, "metadata", {}) or {})
        parts = [
            f"center={self._scene_target_vector_text(getattr(placement, 'center_world', None))}",
            f"normal={self._scene_target_vector_text(getattr(placement, 'normal_world', None))}",
            f"tangent={self._scene_target_vector_text(getattr(placement, 'tangent_world', None))}",
        ]
        if translation.size >= 3:
            parts.append(
                "row decenter=({:.6g}, {:.6g}, {:.6g})".format(
                    float(translation[0]),
                    float(translation[1]),
                    float(translation[2]),
                )
            )
        if rotation.size >= 3:
            parts.append(
                "row tilt=({:.6g}, {:.6g}, {:.6g}) deg".format(
                    float(rotation[0]),
                    float(rotation[1]),
                    float(rotation[2]),
                )
            )
        source_stl = str(metadata.get("source_stl", "") or "").strip()
        if source_stl:
            parts.append(f"STL={Path(source_stl).name}")
        placement_source = str(metadata.get("placement_source", "") or "").strip()
        if placement_source:
            parts.append(f"source={placement_source}")
        settings = metadata.get("scene_placement_settings", {})
        if isinstance(settings, dict):
            constraint_kind = str(settings.get("last_constraint_kind", "") or "").strip()
            if constraint_kind:
                target_label = str(settings.get("last_constraint_target_label", "") or "").strip()
                target_row = settings.get("last_constraint_target_row", "")
                target_role = str(settings.get("last_constraint_target_role", "") or "").strip()
                angle_error = settings.get("last_constraint_angle_error_deg", "")
                constraint_parts = [f"constraint={constraint_kind}"]
                if target_label:
                    constraint_parts.append(f"target={target_label}")
                if target_row != "":
                    constraint_parts.append(f"target_row=S{target_row}")
                if target_role:
                    constraint_parts.append(f"role={target_role}")
                try:
                    constraint_parts.append(f"error={float(angle_error):.6g} deg")
                except Exception:
                    pass
                parts.append(", ".join(constraint_parts))
        return " | ".join(parts)

    @staticmethod
    def _scene_row_record_detail(record) -> str:
        table_text = "-" if record.table_row_index is None else f"S{int(record.table_row_index)}"
        trace_text = "-" if record.trace_surface_index is None else f"S{int(record.trace_surface_index)}"
        parts = [
            f"scene row {int(record.scene_row_index)}",
            f"table={table_text}",
            f"trace={trace_text}",
        ]
        if record.kind == SCENE_ROW_SOURCE:
            parts.append(f"source_id={record.source_id or '-'}")
            parts.append("emitter: does not consume a KrakenOS surf index")
        else:
            parts.append("surface row: KrakenOS surf index is unchanged")
        return " | ".join(parts)

    def _nonseq_scene_graph_record_service(self) -> NonSequentialSceneGraphRecordService:
        service = self.__dict__.get("_nonseq_scene_graph_record_service_instance")
        if service is None:
            service = NonSequentialSceneGraphRecordService(self)
            self._nonseq_scene_graph_record_service_instance = service
        return service

    def _collect_nonseq_scene_graph_records(self) -> list[dict[str, object]]:
        return self._nonseq_scene_graph_record_service()._collect_nonseq_scene_graph_records()

    def _main_nonseq_scene_graph_dialog(self) -> MainNonSequentialSceneGraphDialog:
        dialog = self.__dict__.get("_main_nonseq_scene_graph_dialog_instance")
        if dialog is None:
            dialog = MainNonSequentialSceneGraphDialog(self)
            self._main_nonseq_scene_graph_dialog_instance = dialog
        return dialog

    def open_nonseq_scene_graph(self) -> None:
        self._main_nonseq_scene_graph_dialog().open_nonseq_scene_graph()

    def _close_nonseq_scene_graph(self) -> None:
        self._main_nonseq_scene_graph_dialog()._close_nonseq_scene_graph()

    def _refresh_nonseq_scene_graph_if_open(self) -> None:
        self._main_nonseq_scene_graph_dialog()._refresh_nonseq_scene_graph_if_open()

    def _refresh_nonseq_scene_graph(self) -> None:
        self._main_nonseq_scene_graph_dialog()._refresh_nonseq_scene_graph()

    def _nonseq_scene_selected_record(self) -> dict[str, object] | None:
        return self._main_nonseq_scene_graph_dialog()._nonseq_scene_selected_record()

    def _select_nonseq_scene_row(self) -> None:
        self._main_nonseq_scene_graph_dialog()._select_nonseq_scene_row()

    def _set_nonseq_scene_target(self) -> None:
        self._main_nonseq_scene_graph_dialog()._set_nonseq_scene_target()

    def export_nonseq_scene_graph_csv(self) -> None:
        self._main_nonseq_scene_graph_dialog().export_nonseq_scene_graph_csv()
