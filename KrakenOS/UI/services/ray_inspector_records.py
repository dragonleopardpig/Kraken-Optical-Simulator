"""Ray Inspector record collection service."""

from __future__ import annotations

from typing import Any

import numpy as np

from KrakenOS.UI.scene_builder import build_scene_bundle, scene_bundle_ray_analysis_records
from KrakenOS.UI.scene_geometry import ray_path_reaches_image_from_events


class RayInspectorRecordService:
    """Collect Ray Inspector records while delegating editor-specific helpers."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        # bugs/0492: a facade owns nothing but its editor -- a `_`-prefixed local would shadow
        # the editor's copy for every later read through it. State belongs to the editor.
        if name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _collect_ray_inspector_records(
        self,
        rays=None,
        scene_bundle=None,
        *,
        system=None,
        rows: list[Any] | None = None,
        field_bundle_count: int | None = None,
        ray_count_per_field: int | None = None,
    ) -> list[dict[str, object]]:
        editor_state = self.editor.__dict__
        row_list = editor_state.get("rows", []) if rows is None else rows
        scene_bundle = editor_state.get("_last_scene_bundle") if scene_bundle is None and rays is None else scene_bundle
        if scene_bundle is not None:
            records = scene_bundle_ray_analysis_records(scene_bundle)
            if records:
                return records

        rays = editor_state.get("last_rays") if rays is None else rays
        if rays is None:
            return []

        preview_bundle_count = editor_state.get("_preview_field_bundle_count")
        preview_ray_count = editor_state.get("_preview_field_ray_count")
        if field_bundle_count is not None:
            field_count = int(field_bundle_count)
        elif preview_bundle_count is not None:
            field_count = int(preview_bundle_count)
        else:
            try:
                field_count = int(self._current_field_count())
            except Exception:
                field_count = 1
        field_count = max(1, field_count)
        ray_count_per_field = max(
            1,
            int(
                ray_count_per_field
                if ray_count_per_field is not None
                else preview_ray_count
                if preview_ray_count is not None
                else 1
            ),
        )
        try:
            built_bundle = build_scene_bundle(
                rows=row_list,
                system=editor_state.get("last_system") if system is None else system,
                rays=rays,
                field_count=field_count,
                ray_count_per_field=ray_count_per_field,
            )
            records = scene_bundle_ray_analysis_records(built_bundle)
            if records:
                return records
        except Exception:
            pass

        bundle_paths = {
            int(path.ray_index): path for path in getattr(scene_bundle, "ray_paths", []) or []
        }
        final_surface = max(0, len(row_list) - 1)
        total_rays = len(getattr(rays, "SURFACE", ()) or ())
        records: list[dict[str, object]] = []

        def _entry(seq_name: str, index: int, *, dtype=None, reshape_xyz: bool = False):
            seq = getattr(rays, seq_name, ())
            if seq is None or index >= len(seq):
                if reshape_xyz:
                    return np.empty((0, 3), dtype=float)
                return np.empty(0, dtype=(dtype or float))
            try:
                arr = np.asarray(seq[index], dtype=dtype)
            except Exception:
                arr = np.asarray(seq[index])
            if reshape_xyz:
                if arr.ndim == 1 and arr.size == 3:
                    arr = arr.reshape(1, 3)
                if arr.ndim != 2 or arr.shape[1] < 3:
                    return np.empty((0, 3), dtype=float)
                return np.asarray(arr[:, :3], dtype=float)
            return arr.ravel()

        for ray_index in range(total_rays):
            surface_arr = _entry("SURFACE", ray_index, dtype=int)
            name_arr = _entry("NAME", ray_index, dtype=object)
            glass_arr = _entry("GLASS", ray_index, dtype=object)
            xyz_arr = _entry("XYZ", ray_index, dtype=float, reshape_xyz=True)
            dist_arr = _entry("DISTANCE", ray_index, dtype=float)
            op_arr = _entry("OP", ray_index, dtype=float)
            tt_arr = _entry("TT", ray_index, dtype=float)
            lmn_arr = _entry("LMN", ray_index, dtype=float, reshape_xyz=True)
            r_lmn_arr = _entry("R_LMN", ray_index, dtype=float, reshape_xyz=True)
            s_lmn_arr = _entry("S_LMN", ray_index, dtype=float, reshape_xyz=True)
            n0_arr = _entry("N0", ray_index, dtype=float)
            n1_arr = _entry("N1", ray_index, dtype=float)
            rp_arr = _entry("RP", ray_index, dtype=float)
            rs_arr = _entry("RS", ray_index, dtype=float)
            tp_arr = _entry("TP", ray_index, dtype=float)
            ts_arr = _entry("TS", ray_index, dtype=float)
            ttbe_arr = _entry("TTBE", ray_index, dtype=float)
            branch_path_arr = _entry("BRANCH_PATH", ray_index, dtype=object)
            branch_termination_reason_arr = _entry("BRANCH_TERMINATION_REASON", ray_index, dtype=object)
            branch_termination_diagnostic_arr = _entry("BRANCH_TERMINATION_DIAGNOSTIC", ray_index, dtype=object)
            branch_tree_diagnostic_arr = _entry("BRANCH_TREE_DIAGNOSTIC", ray_index, dtype=object)
            branch_final_media_arr = _entry("BRANCH_FINAL_MEDIA", ray_index, dtype=object)
            branch_final_index_arr = _entry("BRANCH_FINAL_INDEX", ray_index, dtype=float)
            branch_final_inside_volumes_arr = _entry("BRANCH_FINAL_INSIDE_VOLUMES", ray_index, dtype=object)
            branch_final_media_state_arr = _entry("BRANCH_FINAL_MEDIA_STATE_METHOD", ray_index, dtype=object)
            branch_phase_arr = _entry("BRANCH_PHASE", ray_index, dtype=float)
            branch_jones_p_arr = _entry("BRANCH_JONES_P", ray_index, dtype=complex)
            branch_jones_s_arr = _entry("BRANCH_JONES_S", ray_index, dtype=complex)
            branch_polarization_arr = _entry("BRANCH_POLARIZATION_XYZ", ray_index, dtype=complex)
            branch_id_arr = _entry("BRANCH_ID", ray_index, dtype=float)
            branch_power_arr = _entry("BRANCH_POWER", ray_index, dtype=float)
            top_arr = _entry("TOP", ray_index, dtype=float)
            source_ray_arr = _entry("SOURCE_RAY", ray_index, dtype=float)
            source_xyz_arr = _entry("SOURCE_XYZ", ray_index, dtype=float, reshape_xyz=True)
            source_lmn_arr = _entry("SOURCE_LMN", ray_index, dtype=float, reshape_xyz=True)
            source_power_arr = _entry("SOURCE_POWER", ray_index, dtype=float)
            source_weight_arr = _entry("SOURCE_WEIGHT", ray_index, dtype=float)
            source_id_arr = _entry("SOURCE_ID", ray_index, dtype=object)
            source_name_arr = _entry("SOURCE_NAME", ray_index, dtype=object)
            source_role_arr = _entry("SOURCE_ROLE", ray_index, dtype=object)
            source_model_arr = _entry("SOURCE_MODEL", ray_index, dtype=object)
            interaction_type_arr = _entry("INTERACTION_TYPE", ray_index, dtype=object)
            interaction_model_arr = _entry("INTERACTION_MODEL", ray_index, dtype=object)
            interaction_target_arr = _entry("INTERACTION_TARGET_SURFACE", ray_index, dtype=float)
            interaction_in_power_arr = _entry("INTERACTION_IN_POWER", ray_index, dtype=float)
            interaction_coeff_arr = _entry("INTERACTION_COEFF", ray_index, dtype=float)
            interaction_out_power_arr = _entry("INTERACTION_OUT_POWER", ray_index, dtype=float)
            interaction_loss_power_arr = _entry("INTERACTION_LOSS_POWER", ray_index, dtype=float)
            interaction_bulk_arr = _entry("INTERACTION_BULK", ray_index, dtype=float)
            volume_id_arr = _entry("VOLUME_ID", ray_index, dtype=object)
            media_in_arr = _entry("MEDIA_IN", ray_index, dtype=object)
            media_out_arr = _entry("MEDIA_OUT", ray_index, dtype=object)
            media_transition_arr = _entry("MEDIA_TRANSITION", ray_index, dtype=object)
            media_state_method_arr = _entry("MEDIA_STATE_METHOD", ray_index, dtype=object)
            media_state_diagnostic_arr = _entry("MEDIA_STATE_DIAGNOSTIC", ray_index, dtype=object)
            inside_volumes_before_arr = _entry("INSIDE_VOLUMES_BEFORE", ray_index, dtype=object)
            inside_volumes_after_arr = _entry("INSIDE_VOLUMES_AFTER", ray_index, dtype=object)
            mesh_cell_id_arr = _entry("MESH_CELL_ID", ray_index, dtype=float)
            mesh_original_cell_id_arr = _entry("MESH_ORIGINAL_CELL_ID", ray_index, dtype=float)
            mesh_face_id_arr = _entry("MESH_FACE_ID", ray_index, dtype=object)
            mesh_face_match_method_arr = _entry("MESH_FACE_MATCH_METHOD", ray_index, dtype=object)
            mesh_face_match_score_arr = _entry("MESH_FACE_MATCH_SCORE", ray_index, dtype=float)
            mesh_face_match_warning_arr = _entry("MESH_FACE_MATCH_WARNING", ray_index, dtype=object)
            path = bundle_paths.get(ray_index)
            path_hits = list(getattr(path, "hits", []) or []) if path is not None else []
            path_events = list(getattr(path, "events", []) or []) if path is not None else []
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
            field_index = int(path.field_index) if path is not None else min(ray_index // ray_count_per_field, field_count - 1)
            source_ray_index = int(getattr(path, "source_ray_index", ray_index)) if path is not None else int(source_ray_arr[0]) if source_ray_arr.size else ray_index
            source_id = str(getattr(path, "source_id", "") or "") if path is not None else str(source_id_arr[0]) if source_id_arr.size else ""
            source_name = str(getattr(path, "source_name", "") or "") if path is not None else str(source_name_arr[0]) if source_name_arr.size else ""
            source_role = str(getattr(path, "source_role", "") or "") if path is not None else str(source_role_arr[0]) if source_role_arr.size else ""
            source_model = str(getattr(path, "source_model", "") or "") if path is not None else str(source_model_arr[0]) if source_model_arr.size else ""
            source_position = np.asarray(getattr(path, "source_position", (np.nan, np.nan, np.nan)), dtype=float).ravel() if path is not None else source_xyz_arr[0] if source_xyz_arr.shape[0] else np.full(3, np.nan)
            source_direction = np.asarray(getattr(path, "source_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel() if path is not None else source_lmn_arr[0] if source_lmn_arr.shape[0] else np.full(3, np.nan)
            source_power = getattr(path, "source_power", None) if path is not None else float(source_power_arr[0]) if source_power_arr.size else None
            source_weight = getattr(path, "source_weight", None) if path is not None else float(source_weight_arr[0]) if source_weight_arr.size else None
            reaches_image = (
                ray_path_reaches_image_from_events(path)
                if path is not None
                else bool(surface_arr.size and int(surface_arr[-1]) == final_surface)
            )
            branch_id = int(getattr(path, "branch_id", 0)) if path is not None else int(branch_id_arr[0]) if branch_id_arr.size else 0
            branch_power = getattr(path, "branch_power", None) if path is not None else float(branch_power_arr[0]) if branch_power_arr.size else None
            branch_phase = getattr(path, "branch_phase_deg", None) if path is not None else None
            if branch_phase is None and branch_phase_arr.size:
                branch_phase = float(branch_phase_arr[-1])
            if path is not None:
                branch_jones_p = getattr(path, "branch_jones_p", complex(1.0, 0.0))
                branch_jones_s = getattr(path, "branch_jones_s", complex(0.0, 0.0))
                branch_polarization_xyz = getattr(
                    path,
                    "branch_polarization_xyz",
                    np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128),
                )
            else:
                branch_jones_p = branch_jones_p_arr[0] if branch_jones_p_arr.size else complex(1.0, 0.0)
                branch_jones_s = branch_jones_s_arr[0] if branch_jones_s_arr.size else complex(0.0, 0.0)
                branch_polarization_xyz = (
                    np.asarray(branch_polarization_arr[:3], dtype=np.complex128)
                    if branch_polarization_arr.size >= 3
                    else np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
                )
            branch_jones_p, branch_jones_s = self._normalize_jones_pair(branch_jones_p, branch_jones_s)
            branch_polarization_xyz = self._normalize_complex_vector(branch_polarization_xyz)
            branch_p_fraction = float(abs(branch_jones_p) ** 2.0)
            branch_s_fraction = float(abs(branch_jones_s) ** 2.0)
            if path is not None:
                branch_path = str(getattr(path, "branch_path", "") or getattr(path, "branch_label", "") or "")
            else:
                branch_path = str(branch_path_arr[0]) if branch_path_arr.size else ""
            branch_count = len(getattr(path, "branches", []) or []) if path is not None else 1
            target_surface = getattr(path, "target_surface", final_surface) if path is not None else final_surface
            termination = str(getattr(path, "termination_reason", "") or "")
            if not termination and terminal_event is not None:
                termination = str(
                    getattr(terminal_event, "termination_reason", "")
                    or getattr(terminal_event, "event_type", "")
                    or ""
                )
            termination_diagnostic = str(getattr(path, "termination_diagnostic", "") or "") if path is not None else (
                str(branch_termination_diagnostic_arr[0]) if branch_termination_diagnostic_arr.size else ""
            )
            branch_tree_diagnostic = str(getattr(path, "branch_tree_diagnostic", "") or "") if path is not None else (
                str(branch_tree_diagnostic_arr[0]) if branch_tree_diagnostic_arr.size else ""
            )
            if not termination_diagnostic and terminal_event is not None:
                termination_diagnostic = str(getattr(terminal_event, "diagnostic", "") or "")
            if terminal_event is not None:
                terminal_media = str(getattr(terminal_event, "media_out", "") or "")
                terminal_index = getattr(terminal_event, "n1", None)
                terminal_index = "" if terminal_index is None else terminal_index
                terminal_inside_volumes = str(getattr(terminal_event, "inside_volumes_after", "") or "")
                terminal_media_state = str(getattr(terminal_event, "media_state_method", "") or "")
            else:
                terminal_media = str(branch_final_media_arr[0]) if branch_final_media_arr.size else ""
                if branch_final_index_arr.size and np.isfinite(float(branch_final_index_arr[0])):
                    terminal_index = float(branch_final_index_arr[0])
                else:
                    terminal_index = ""
                terminal_inside_volumes = str(branch_final_inside_volumes_arr[0]) if branch_final_inside_volumes_arr.size else ""
                terminal_media_state = str(branch_final_media_state_arr[0]) if branch_final_media_state_arr.size else ""
            last_surface = int(surface_arr[-1]) if surface_arr.size else None
            last_name = str(name_arr[-1]) if name_arr.size else ""
            if last_surface is None and path is not None:
                path_surface_ids = np.asarray(getattr(path, "surface_ids", []), dtype=int).ravel()
                if path_surface_ids.size:
                    last_surface = int(path_surface_ids[-1])
            if not last_name and path_surface_events:
                last_name = str(getattr(path_surface_events[-1], "surface_name", "") or "")
            if not last_name and path_hits:
                last_name = str(getattr(path_hits[-1], "name", "") or "")
            total_distance = float(np.nansum(dist_arr)) if dist_arr.size else 0.0
            total_op = float(np.nansum(op_arr)) if op_arr.size else 0.0
            total_top = float(top_arr[-1]) if top_arr.size and np.isfinite(float(top_arr[-1])) else total_op
            transmission = float(tt_arr[-1]) if tt_arr.size else 0.0
            if path_hits and not dist_arr.size:
                total_distance = float(np.nansum([
                    float(value)
                    for value in (getattr(hit, "distance", None) for hit in path_hits)
                    if value is not None and np.isfinite(float(value))
                ]))
            if path_surface_events and not dist_arr.size:
                total_distance = float(np.nansum([
                    float(value)
                    for value in (getattr(event, "distance", None) for event in path_surface_events)
                    if value is not None and np.isfinite(float(value))
                ]))
            if path_hits and not op_arr.size:
                total_op = float(np.nansum([
                    float(value)
                    for value in (getattr(hit, "optical_path", None) for hit in path_hits)
                    if value is not None and np.isfinite(float(value))
                ]))
                total_top = total_op
            if path_surface_events and not op_arr.size:
                total_op = float(np.nansum([
                    float(value)
                    for value in (getattr(event, "optical_path", None) for event in path_surface_events)
                    if value is not None and np.isfinite(float(value))
                ]))
                total_top = total_op
            if path_hits and not tt_arr.size:
                last_ttbe = getattr(path_hits[-1], "ttbe", None)
                transmission = float(last_ttbe) if last_ttbe is not None and np.isfinite(float(last_ttbe)) else 0.0
            if path_surface_events and not tt_arr.size:
                last_ttbe = getattr(path_surface_events[-1], "ttbe", None)
                transmission = float(last_ttbe) if last_ttbe is not None and np.isfinite(float(last_ttbe)) else 0.0
            if not termination:
                if branch_termination_reason_arr.size:
                    termination = str(branch_termination_reason_arr[0] or "")
            if not termination:
                termination = "image" if reaches_image else (f"stopped_at_surface_{last_surface}" if last_surface is not None else "no_hit")
            status = self._ray_termination_status_text(termination, last_surface, reaches_image)

            hits: list[dict[str, object]] = []
            if path_surface_events:
                hit_count = len(path_surface_events)
                for event in path_surface_events:
                    hits.append(self._ray_event_to_inspector_hit(event))
            elif path_hits:
                hit_count = len(path_hits)
                for hit in path_hits:
                    xyz = np.asarray(getattr(hit, "point_world", (np.nan, np.nan, np.nan)), dtype=float).ravel()
                    lmn = np.asarray(getattr(hit, "incoming_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
                    r_lmn = np.asarray(getattr(hit, "outgoing_direction", (np.nan, np.nan, np.nan)), dtype=float).ravel()
                    s_lmn = np.asarray(getattr(hit, "surface_normal", (np.nan, np.nan, np.nan)), dtype=float).ravel()
                    surface_id = getattr(hit, "surface_id", "")
                    hit_record = {
                        "step": int(getattr(hit, "step", len(hits))),
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
                        "volume_id": str(getattr(hit, "volume_id", "") or ""),
                        "media_in": str(getattr(hit, "media_in", "") or ""),
                        "media_out": str(getattr(hit, "media_out", "") or ""),
                        "media_transition": str(getattr(hit, "media_transition", "") or ""),
                        "media_state_method": str(getattr(hit, "media_state_method", "") or ""),
                        "media_state_diagnostic": str(getattr(hit, "media_state_diagnostic", "") or ""),
                        "inside_volumes_before": str(getattr(hit, "inside_volumes_before", "") or ""),
                        "inside_volumes_after": str(getattr(hit, "inside_volumes_after", "") or ""),
                        "mesh_cell_id": getattr(hit, "mesh_cell_id", np.nan),
                        "mesh_original_cell_id": getattr(hit, "mesh_original_cell_id", np.nan),
                        "mesh_face_id": str(getattr(hit, "mesh_face_id", "") or ""),
                        "mesh_face_match_method": str(getattr(hit, "mesh_face_match_method", "") or ""),
                        "mesh_face_match_score": getattr(hit, "mesh_face_match_score", np.nan),
                        "mesh_face_match_warning": str(getattr(hit, "mesh_face_match_warning", "") or ""),
                    }
                    hit_record.update(self._ray_hit_gaussian_frame_fields(lmn, r_lmn, s_lmn))
                    hits.append(hit_record)
            else:
                core_count = max(
                    name_arr.size,
                    glass_arr.size,
                    xyz_arr.shape[0],
                    dist_arr.size,
                    op_arr.size,
                    lmn_arr.shape[0],
                    r_lmn_arr.shape[0],
                    s_lmn_arr.shape[0],
                    n0_arr.size,
                    n1_arr.size,
                    interaction_type_arr.size,
                    interaction_model_arr.size,
                    interaction_target_arr.size,
                    interaction_in_power_arr.size,
                    interaction_coeff_arr.size,
                    interaction_out_power_arr.size,
                    interaction_loss_power_arr.size,
                    interaction_bulk_arr.size,
                    mesh_cell_id_arr.size,
                    mesh_original_cell_id_arr.size,
                    mesh_face_id_arr.size,
                    mesh_face_match_method_arr.size,
                    mesh_face_match_score_arr.size,
                    mesh_face_match_warning_arr.size,
                    volume_id_arr.size,
                    media_in_arr.size,
                    media_out_arr.size,
                    media_transition_arr.size,
                    media_state_method_arr.size,
                    media_state_diagnostic_arr.size,
                    inside_volumes_before_arr.size,
                    inside_volumes_after_arr.size,
                )
                hit_count = int(surface_arr.size) if surface_arr.size else core_count
                for hit_index in range(hit_count):
                    xyz_index = hit_index + 1 if surface_arr.size and xyz_arr.shape[0] == surface_arr.size + 1 else hit_index
                    xyz = xyz_arr[xyz_index] if xyz_index < xyz_arr.shape[0] else np.asarray((np.nan, np.nan, np.nan), dtype=float)
                    lmn = lmn_arr[hit_index] if hit_index < lmn_arr.shape[0] else np.asarray((np.nan, np.nan, np.nan), dtype=float)
                    r_lmn = r_lmn_arr[hit_index] if hit_index < r_lmn_arr.shape[0] else np.asarray((np.nan, np.nan, np.nan), dtype=float)
                    s_lmn = s_lmn_arr[hit_index] if hit_index < s_lmn_arr.shape[0] else np.asarray((np.nan, np.nan, np.nan), dtype=float)
                    surface_id = int(surface_arr[hit_index]) if hit_index < surface_arr.size else None
                    surface_type = row_list[surface_id].surface if surface_id is not None and 0 <= surface_id < len(row_list) else ""
                    glass = str(glass_arr[hit_index]) if hit_index < glass_arr.size else ""
                    n0_value = float(n0_arr[hit_index]) if hit_index < n0_arr.size else np.nan
                    n1_value = float(n1_arr[hit_index]) if hit_index < n1_arr.size else np.nan
                    n0_event = n0_value if np.isfinite(n0_value) else None
                    n1_event = n1_value if np.isfinite(n1_value) else None
                    interaction_type = str(interaction_type_arr[hit_index]) if hit_index < interaction_type_arr.size else ""
                    event = self._ray_hit_event_label(surface_type, glass, interaction_type, n0_event, n1_event)
                    hit_record = {
                        "step": hit_index,
                        "branch": 0,
                        "surface": "" if surface_id is None else surface_id,
                        "event": event,
                        "name": str(name_arr[hit_index]) if hit_index < name_arr.size else "",
                        "glass": glass,
                        "x": float(xyz[0]) if xyz.size >= 1 else np.nan,
                        "y": float(xyz[1]) if xyz.size >= 2 else np.nan,
                        "z": float(xyz[2]) if xyz.size >= 3 else np.nan,
                        "distance": float(dist_arr[hit_index]) if hit_index < dist_arr.size else np.nan,
                        "op": float(op_arr[hit_index]) if hit_index < op_arr.size else np.nan,
                        "l": float(lmn[0]) if lmn.size >= 1 else np.nan,
                        "m": float(lmn[1]) if lmn.size >= 2 else np.nan,
                        "n": float(lmn[2]) if lmn.size >= 3 else np.nan,
                        "out_l": float(r_lmn[0]) if r_lmn.size >= 1 else np.nan,
                        "out_m": float(r_lmn[1]) if r_lmn.size >= 2 else np.nan,
                        "out_n": float(r_lmn[2]) if r_lmn.size >= 3 else np.nan,
                        "normal_l": float(s_lmn[0]) if s_lmn.size >= 1 else np.nan,
                        "normal_m": float(s_lmn[1]) if s_lmn.size >= 2 else np.nan,
                        "normal_n": float(s_lmn[2]) if s_lmn.size >= 3 else np.nan,
                        "n0": n0_value,
                        "n1": n1_value,
                        "rp": float(rp_arr[hit_index]) if hit_index < rp_arr.size else np.nan,
                        "rs": float(rs_arr[hit_index]) if hit_index < rs_arr.size else np.nan,
                        "tp": float(tp_arr[hit_index]) if hit_index < tp_arr.size else np.nan,
                        "ts": float(ts_arr[hit_index]) if hit_index < ts_arr.size else np.nan,
                        "ttbe": float(ttbe_arr[hit_index]) if hit_index < ttbe_arr.size else np.nan,
                        "interaction_model": str(interaction_model_arr[hit_index]) if hit_index < interaction_model_arr.size else "",
                        "interaction_target_surface": float(interaction_target_arr[hit_index]) if hit_index < interaction_target_arr.size else np.nan,
                        "interaction_in_power": float(interaction_in_power_arr[hit_index]) if hit_index < interaction_in_power_arr.size else np.nan,
                        "interaction_coeff": float(interaction_coeff_arr[hit_index]) if hit_index < interaction_coeff_arr.size else np.nan,
                        "interaction_out_power": float(interaction_out_power_arr[hit_index]) if hit_index < interaction_out_power_arr.size else np.nan,
                        "interaction_loss_power": float(interaction_loss_power_arr[hit_index]) if hit_index < interaction_loss_power_arr.size else np.nan,
                        "interaction_bulk": float(interaction_bulk_arr[hit_index]) if hit_index < interaction_bulk_arr.size else np.nan,
                        "volume_id": str(volume_id_arr[hit_index]) if hit_index < volume_id_arr.size else "",
                        "media_in": str(media_in_arr[hit_index]) if hit_index < media_in_arr.size else "",
                        "media_out": str(media_out_arr[hit_index]) if hit_index < media_out_arr.size else "",
                        "media_transition": str(media_transition_arr[hit_index]) if hit_index < media_transition_arr.size else "",
                        "media_state_method": str(media_state_method_arr[hit_index]) if hit_index < media_state_method_arr.size else "",
                        "media_state_diagnostic": str(media_state_diagnostic_arr[hit_index]) if hit_index < media_state_diagnostic_arr.size else "",
                        "inside_volumes_before": str(inside_volumes_before_arr[hit_index]) if hit_index < inside_volumes_before_arr.size else "",
                        "inside_volumes_after": str(inside_volumes_after_arr[hit_index]) if hit_index < inside_volumes_after_arr.size else "",
                        "mesh_cell_id": float(mesh_cell_id_arr[hit_index]) if hit_index < mesh_cell_id_arr.size else np.nan,
                        "mesh_original_cell_id": float(mesh_original_cell_id_arr[hit_index]) if hit_index < mesh_original_cell_id_arr.size else np.nan,
                        "mesh_face_id": str(mesh_face_id_arr[hit_index]) if hit_index < mesh_face_id_arr.size else "",
                        "mesh_face_match_method": str(mesh_face_match_method_arr[hit_index]) if hit_index < mesh_face_match_method_arr.size else "",
                        "mesh_face_match_score": float(mesh_face_match_score_arr[hit_index]) if hit_index < mesh_face_match_score_arr.size else np.nan,
                        "mesh_face_match_warning": str(mesh_face_match_warning_arr[hit_index]) if hit_index < mesh_face_match_warning_arr.size else "",
                    }
                    hit_record.update(self._ray_hit_gaussian_frame_fields(lmn, r_lmn, s_lmn))
                    hits.append(hit_record)

            records.append(
                {
                    "ray_index": ray_index,
                    "source_ray_index": source_ray_index,
                    "source_id": source_id,
                    "source_name": source_name,
                    "source_role": source_role,
                    "source_model": source_model,
                    "source_x": float(source_position[0]) if source_position.size >= 1 else np.nan,
                    "source_y": float(source_position[1]) if source_position.size >= 2 else np.nan,
                    "source_z": float(source_position[2]) if source_position.size >= 3 else np.nan,
                    "source_l": float(source_direction[0]) if source_direction.size >= 1 else np.nan,
                    "source_m": float(source_direction[1]) if source_direction.size >= 2 else np.nan,
                    "source_n": float(source_direction[2]) if source_direction.size >= 3 else np.nan,
                    "source_power": source_power,
                    "source_weight": source_weight,
                    "field_index": field_index,
                    "branch_id": branch_id,
                    "branch_path": branch_path,
                    "branch_power": branch_power,
                    "branch_phase": branch_phase,
                    "branch_jones_p": branch_jones_p,
                    "branch_jones_s": branch_jones_s,
                    "branch_polarization_xyz": branch_polarization_xyz,
                    "branch_p_fraction": branch_p_fraction,
                    "branch_s_fraction": branch_s_fraction,
                    "branch_count": branch_count,
                    "target_surface": target_surface,
                    "termination": termination,
                    "status": status,
                    "hit_count": hit_count,
                    "termination_diagnostic": termination_diagnostic,
                    "terminal_media": terminal_media,
                    "terminal_index": terminal_index,
                    "terminal_inside_volumes": terminal_inside_volumes,
                    "terminal_media_state": terminal_media_state,
                    "branch_tree_diagnostic": branch_tree_diagnostic,
                    "last_surface": last_surface,
                    "last_name": last_name,
                    "distance": total_distance,
                    "op": total_op,
                    "top": total_top,
                    "transmission": transmission,
                    "reaches_image": reaches_image,
                    "analysis_source": "raykeeper",
                    "hits": hits,
                }
            )
        return records
