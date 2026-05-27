
import numpy as np
import pyvista as pv

def extract_ray_result(System):
    """Return the last traced ray data without returning the full system.

    This mirrors the traditional RayKeeper payload while preserving the
    branch's non-sequential event, media, source, and branch metadata when the
    active System exposes it.  Parallel or deferred trace collectors can pass
    this dictionary back to RayKeeper without keeping a mutable System object.
    """

    return {
        "nelements": getattr(System, "n", 0),
        "val": getattr(System, "val", 0),
        "Wave": getattr(System, "Wave", getattr(System, "WAV", np.nan)),
        "ray_SurfHits": getattr(System, "ray_SurfHits", []),
        "RAY": getattr(System, "ray_SurfHits", []),
        "SURFACE": getattr(System, "SURFACE", []),
        "NAME": getattr(System, "NAME", []),
        "GLASS": getattr(System, "GLASS", []),
        "S_XYZ": getattr(System, "S_XYZ", []),
        "T_XYZ": getattr(System, "T_XYZ", []),
        "XYZ": getattr(System, "XYZ", []),
        "OST_XYZ": getattr(System, "OST_XYZ", []),
        "OST_LMN": getattr(System, "OST_LMN", []),
        "S_LMN": getattr(System, "S_LMN", []),
        "LMN": getattr(System, "LMN", []),
        "R_LMN": getattr(System, "R_LMN", []),
        "N0": getattr(System, "N0", []),
        "N1": getattr(System, "N1", []),
        "WAV": getattr(System, "WAV", getattr(System, "Wave", np.nan)),
        "G_LMN": getattr(System, "G_LMN", []),
        "ORDER": getattr(System, "ORDER", []),
        "GRATING": getattr(System, "GRATING", []),
        "DISTANCE": getattr(System, "DISTANCE", []),
        "OP": getattr(System, "OP", []),
        "TOP_S": getattr(System, "TOP_S", []),
        "TOP": getattr(System, "TOP", 0.0),
        "ALPHA": getattr(System, "ALPHA", []),
        "BULK_TRANS": getattr(System, "BULK_TRANS", []),
        "RP": getattr(System, "RP", []),
        "RS": getattr(System, "RS", []),
        "TP": getattr(System, "TP", []),
        "TS": getattr(System, "TS", []),
        "TTBE": getattr(System, "TTBE", []),
        "TT": getattr(System, "TT", 0.0),
        "INTERACTION_TYPE": getattr(System, "INTERACTION_TYPE", []),
        "INTERACTION_MODEL": getattr(System, "INTERACTION_MODEL", []),
        "INTERACTION_TARGET_SURFACE": getattr(System, "INTERACTION_TARGET_SURFACE", []),
        "INTERACTION_IN_POWER": getattr(System, "INTERACTION_IN_POWER", []),
        "INTERACTION_COEFF": getattr(System, "INTERACTION_COEFF", []),
        "INTERACTION_OUT_POWER": getattr(System, "INTERACTION_OUT_POWER", []),
        "INTERACTION_LOSS_POWER": getattr(System, "INTERACTION_LOSS_POWER", []),
        "INTERACTION_BULK": getattr(System, "INTERACTION_BULK", []),
        "MESH_CELL_ID": getattr(System, "MESH_CELL_ID", []),
        "MESH_ORIGINAL_CELL_ID": getattr(System, "MESH_ORIGINAL_CELL_ID", []),
        "MESH_FACE_ID": getattr(System, "MESH_FACE_ID", []),
        "MESH_FACE_MATCH_METHOD": getattr(System, "MESH_FACE_MATCH_METHOD", []),
        "MESH_FACE_MATCH_SCORE": getattr(System, "MESH_FACE_MATCH_SCORE", []),
        "MESH_FACE_MATCH_WARNING": getattr(System, "MESH_FACE_MATCH_WARNING", []),
        "VOLUME_ID": getattr(System, "VOLUME_ID", []),
        "MEDIA_IN": getattr(System, "MEDIA_IN", []),
        "MEDIA_OUT": getattr(System, "MEDIA_OUT", []),
        "MEDIA_TRANSITION": getattr(System, "MEDIA_TRANSITION", []),
        "MEDIA_STATE_METHOD": getattr(System, "MEDIA_STATE_METHOD", []),
        "MEDIA_STATE_DIAGNOSTIC": getattr(System, "MEDIA_STATE_DIAGNOSTIC", []),
        "INSIDE_VOLUMES_BEFORE": getattr(System, "INSIDE_VOLUMES_BEFORE", []),
        "INSIDE_VOLUMES_AFTER": getattr(System, "INSIDE_VOLUMES_AFTER", []),
        "branch_id": getattr(System, "BRANCH_ID", 0),
        "parent_branch_id": getattr(System, "PARENT_BRANCH_ID", -1),
        "branch_power": getattr(System, "BRANCH_POWER", np.nan),
        "branch_phase_deg": getattr(System, "BRANCH_PHASE", 0.0),
        "branch_label": getattr(System, "BRANCH_LABEL", "primary"),
        "branch_path": getattr(System, "BRANCH_PATH", "primary"),
        "branch_termination_reason": getattr(System, "BRANCH_TERMINATION_REASON", ""),
        "branch_termination_diagnostic": getattr(System, "BRANCH_TERMINATION_DIAGNOSTIC", ""),
        "branch_tree_diagnostic": getattr(System, "BRANCH_TREE_DIAGNOSTIC", ""),
        "branch_jones_p": getattr(System, "BRANCH_JONES_P", complex(1.0, 0.0)),
        "branch_jones_s": getattr(System, "BRANCH_JONES_S", complex(0.0, 0.0)),
        "branch_polarization_xyz": getattr(System, "BRANCH_POLARIZATION_XYZ", (1.0, 0.0, 0.0)),
        "branch_final_media": getattr(System, "BRANCH_FINAL_MEDIA", ""),
        "branch_final_index": getattr(System, "BRANCH_FINAL_INDEX", np.nan),
        "branch_final_inside_volumes": getattr(System, "BRANCH_FINAL_INSIDE_VOLUMES", ""),
        "branch_final_media_state_method": getattr(System, "BRANCH_FINAL_MEDIA_STATE_METHOD", ""),
    }

try:
    from .TraceEvents import (
        TRACE_EVENT_KIND_SURFACE,
        TRACE_EVENT_KIND_TERMINAL,
        TRACE_EVENT_SOURCE_RAYKEEPER,
        TraceEventRecord,
    )
except Exception:
    from TraceEvents import (
        TRACE_EVENT_KIND_SURFACE,
        TRACE_EVENT_KIND_TERMINAL,
        TRACE_EVENT_SOURCE_RAYKEEPER,
        TraceEventRecord,
    )

class raykeeper():
    """raykeeper.
    """


    def __init__(self, System):
        """__init__.

        Parameters
        ----------
        System :
            System
        """
        self.SYSTEM = System
        self.clean()

    def set_launch_metadata(
        self,
        *,
        source_xyz=None,
        source_lmn=None,
        source_power=None,
        source_weight=None,
        source_id=None,
        source_name=None,
        source_role=None,
        source_model=None,
        source_wavelength=None,
        launch_field_requested=None,
        launch_field_effective=None,
        launch_field_basis=None,
        launch_field_unit=None,
        launch_field_min=None,
        launch_field_max=None,
        launch_field_active=None,
        launch_ray_count=None,
        launch_pupil_pattern=None,
        launch_trace_intent=None,
        launch_sampling_mode=None,
        terminal_target_surface=None,
        terminal_detector_surfaces=None,
        terminal_policy_source=None,
    ):
        """Attach launch/source metadata to the next pushed ray.

        Deterministic beam-splitter branches produce multiple pushed ray
        records from one physical launch.  The pending metadata is therefore
        consumed after the whole branch result set is pushed, not after the
        first branch.
        """
        self._pending_launch_metadata = {
            "source_xyz": source_xyz,
            "source_lmn": source_lmn,
            "source_power": source_power,
            "source_weight": source_weight,
            "source_id": source_id,
            "source_name": source_name,
            "source_role": source_role,
            "source_model": source_model,
            "source_wavelength": source_wavelength,
            "launch_field_requested": launch_field_requested,
            "launch_field_effective": launch_field_effective,
            "launch_field_basis": launch_field_basis,
            "launch_field_unit": launch_field_unit,
            "launch_field_min": launch_field_min,
            "launch_field_max": launch_field_max,
            "launch_field_active": launch_field_active,
            "launch_ray_count": launch_ray_count,
            "launch_pupil_pattern": launch_pupil_pattern,
            "launch_trace_intent": launch_trace_intent,
            "launch_sampling_mode": launch_sampling_mode,
            "terminal_target_surface": terminal_target_surface,
            "terminal_detector_surfaces": terminal_detector_surfaces,
            "terminal_policy_source": terminal_policy_source,
        }

    @staticmethod
    def _metadata_vector(value, fallback=None, dtype=float):
        if value is None:
            value = fallback
        try:
            arr = np.asarray(value, dtype=dtype).reshape(-1)
            finite = np.isfinite(arr[:3].real) & np.isfinite(arr[:3].imag) if np.iscomplexobj(arr) else np.isfinite(arr[:3])
            if arr.size >= 3 and np.all(finite):
                return arr[:3]
        except Exception:
            pass
        return np.asarray([np.nan, np.nan, np.nan], dtype=dtype)

    @staticmethod
    def _metadata_float(value, fallback=np.nan):
        if value is None:
            value = fallback
        try:
            scalar = float(np.asarray(value, dtype=float).reshape(-1)[0])
        except Exception:
            return np.asarray(np.nan)
        return np.asarray(scalar if np.isfinite(scalar) else np.nan)

    @staticmethod
    def _metadata_text(value, fallback=""):
        if value is None:
            value = fallback
        try:
            return np.asarray(str(value))
        except Exception:
            return np.asarray("")

    @staticmethod
    def _safe_array(value, dtype=None):
        try:
            return np.asarray(value, dtype=dtype)
        except Exception:
            return np.asarray(value, dtype=object)

    @staticmethod
    def _event_array(seq, index, dtype=None):
        try:
            if seq is None or index >= len(seq):
                return np.asarray([], dtype=dtype if dtype is not None else object)
            return np.asarray(seq[index], dtype=dtype)
        except Exception:
            try:
                return np.asarray(seq[index])
            except Exception:
                return np.asarray([], dtype=dtype if dtype is not None else object)

    @staticmethod
    def _event_scalar(arr, index=0, default=None):
        try:
            flat = np.asarray(arr).reshape(-1)
            if index >= flat.size:
                return default
            value = float(flat[index])
        except Exception:
            return default
        if not np.isfinite(value):
            return default
        if abs(value - round(value)) < 1e-9:
            return int(round(value))
        return float(value)

    @staticmethod
    def _event_bool(arr, index=0, default=None):
        try:
            flat = np.asarray(arr, dtype=object).reshape(-1)
            if index >= flat.size:
                return default
            value = flat[index]
        except Exception:
            return default
        if value is None:
            return default
        if isinstance(value, (bool, np.bool_)):
            return bool(value)
        try:
            numeric = float(value)
            if np.isfinite(numeric):
                return bool(numeric)
        except Exception:
            pass
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "on", "active"}:
            return True
        if text in {"0", "false", "no", "off", "inactive"}:
            return False
        return default

    @staticmethod
    def _event_text(arr, index=0, default=""):
        try:
            flat = np.asarray(arr, dtype=object).reshape(-1)
            if index >= flat.size:
                return default
            return str(flat[index])
        except Exception:
            return default

    @staticmethod
    def _event_int_list(value):
        if value is None:
            return []
        if isinstance(value, str):
            parts = value.replace(";", ",").split(",")
        else:
            try:
                parts = list(np.asarray(value, dtype=object).reshape(-1))
            except Exception:
                parts = [value]
        result = []
        for part in parts:
            text = str(part or "").strip()
            if not text:
                continue
            try:
                result.append(int(float(text)))
            except Exception:
                continue
        return result

    @staticmethod
    def _metadata_int_list_text(value):
        values = raykeeper._event_int_list(value)
        return np.asarray(",".join(str(int(item)) for item in values))

    @staticmethod
    def _event_vector(arr, index=0):
        try:
            data = np.asarray(arr, dtype=float)
            if data.ndim == 1 and data.size >= 3:
                return [float(data[0]), float(data[1]), float(data[2])]
            if data.ndim >= 2 and index < data.shape[0] and data.shape[1] >= 3:
                return [float(data[index, 0]), float(data[index, 1]), float(data[index, 2])]
        except Exception:
            pass
        return [np.nan, np.nan, np.nan]

    @staticmethod
    def _polyline_direction(points, from_index, to_index):
        """Unit travel direction between two ray-polyline vertices, or ``None``.

        The traced polyline is stored in physical world coordinates, so a
        segment between consecutive vertices is the authoritative physical
        propagation direction regardless of the interaction that produced it.
        """
        try:
            arr = np.asarray(points, dtype=float)
        except Exception:
            return None
        if getattr(arr, "ndim", 0) != 2 or arr.shape[0] < 2 or arr.shape[1] < 3:
            return None
        n = int(arr.shape[0])
        if not (0 <= int(from_index) < n and 0 <= int(to_index) < n):
            return None
        segment = arr[int(to_index), :3] - arr[int(from_index), :3]
        if not np.all(np.isfinite(segment)):
            return None
        norm = float(np.linalg.norm(segment))
        if norm <= 1.0e-9:
            return None
        return segment / norm

    @staticmethod
    def _reconciled_direction(stored, reference):
        """Sign-correct a stored R_LMN/LMN direction against traced geometry.

        KrakenOS ``R_LMN``/``LMN`` store the raw ``ResVec`` and omit the
        cumulative ``SIGN`` flip, so they point backwards after an odd number
        of reflections.  The traced polyline (built from ``ResVec * SIGN``) is
        authoritative; flip the stored vector when it is clearly anti-parallel
        to the physical segment.  A near-orthogonal reference is treated as an
        index mismatch and the stored vector is kept unchanged.
        """
        try:
            stored_vec = np.asarray(stored, dtype=float).reshape(-1)[:3]
        except Exception:
            stored_vec = np.asarray([np.nan, np.nan, np.nan], dtype=float)
        if reference is None:
            return [float(v) for v in stored_vec]
        reference_vec = np.asarray(reference, dtype=float).reshape(-1)[:3]
        if stored_vec.size < 3 or not np.all(np.isfinite(stored_vec)):
            return [float(v) for v in reference_vec]
        if float(np.dot(stored_vec, reference_vec)) < -0.5:
            stored_vec = -stored_vec
        return [float(v) for v in stored_vec]

    @staticmethod
    def _event_type_label(raw_type, glass, n0, n1):
        label = str(raw_type or "").strip().lower()
        if label.startswith("split_"):
            return label
        if label in {"reflect_tir", "reflect_mirror"}:
            return label
        if label in {"reflection", "reflect"}:
            return "reflection"
        if label in {"scatter", "diffuse_scatter"}:
            return "scatter"
        if label in {"absorb", "absorption"}:
            return "absorb"
        if label in {"refract", "refraction"}:
            return "refraction"
        if label in {"transmit", "transmission"}:
            try:
                if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
                    return "refraction"
            except Exception:
                pass
            return "transmission"
        if label:
            return label
        if str(glass or "").strip().upper() == "MIRROR":
            return "reflection"
        try:
            if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
                return "refraction"
        except Exception:
            pass
        return "transmission"

    def _trace_event_records_for_index(self, ray_index):
        surface_arr = self._event_array(self.SURFACE, ray_index, dtype=int).reshape(-1)
        name_arr = self._event_array(self.NAME, ray_index, dtype=object).reshape(-1)
        glass_arr = self._event_array(self.GLASS, ray_index, dtype=object).reshape(-1)
        xyz_arr = self._event_array(self.XYZ, ray_index, dtype=float)
        lmn_arr = self._event_array(self.LMN, ray_index, dtype=float)
        r_lmn_arr = self._event_array(self.R_LMN, ray_index, dtype=float)
        s_lmn_arr = self._event_array(self.S_LMN, ray_index, dtype=float)
        cc_arr = self._event_array(self.CC, ray_index, dtype=float)
        cc_len = (
            int(cc_arr.shape[0])
            if getattr(cc_arr, "ndim", 0) == 2 and cc_arr.shape[0] >= 2 and cc_arr.shape[1] >= 3
            else 0
        )
        n0_arr = self._event_array(self.N0, ray_index, dtype=float).reshape(-1)
        n1_arr = self._event_array(self.N1, ray_index, dtype=float).reshape(-1)
        distance_arr = self._event_array(self.DISTANCE, ray_index, dtype=float).reshape(-1)
        op_arr = self._event_array(self.OP, ray_index, dtype=float).reshape(-1)
        rp_arr = self._event_array(self.RP, ray_index, dtype=float).reshape(-1)
        rs_arr = self._event_array(self.RS, ray_index, dtype=float).reshape(-1)
        tp_arr = self._event_array(self.TP, ray_index, dtype=float).reshape(-1)
        ts_arr = self._event_array(self.TS, ray_index, dtype=float).reshape(-1)
        ttbe_arr = self._event_array(self.TTBE, ray_index, dtype=float).reshape(-1)
        interaction_type_arr = self._event_array(self.INTERACTION_TYPE, ray_index, dtype=object).reshape(-1)
        interaction_model_arr = self._event_array(self.INTERACTION_MODEL, ray_index, dtype=object).reshape(-1)
        interaction_target_arr = self._event_array(self.INTERACTION_TARGET_SURFACE, ray_index, dtype=float).reshape(-1)
        interaction_in_power_arr = self._event_array(self.INTERACTION_IN_POWER, ray_index, dtype=float).reshape(-1)
        interaction_coeff_arr = self._event_array(self.INTERACTION_COEFF, ray_index, dtype=float).reshape(-1)
        interaction_out_power_arr = self._event_array(self.INTERACTION_OUT_POWER, ray_index, dtype=float).reshape(-1)
        interaction_loss_power_arr = self._event_array(self.INTERACTION_LOSS_POWER, ray_index, dtype=float).reshape(-1)
        interaction_bulk_arr = self._event_array(self.INTERACTION_BULK, ray_index, dtype=float).reshape(-1)
        volume_id_arr = self._event_array(self.VOLUME_ID, ray_index, dtype=object).reshape(-1)
        media_in_arr = self._event_array(self.MEDIA_IN, ray_index, dtype=object).reshape(-1)
        media_out_arr = self._event_array(self.MEDIA_OUT, ray_index, dtype=object).reshape(-1)
        media_transition_arr = self._event_array(self.MEDIA_TRANSITION, ray_index, dtype=object).reshape(-1)
        media_state_method_arr = self._event_array(self.MEDIA_STATE_METHOD, ray_index, dtype=object).reshape(-1)
        media_state_diagnostic_arr = self._event_array(self.MEDIA_STATE_DIAGNOSTIC, ray_index, dtype=object).reshape(-1)
        inside_before_arr = self._event_array(self.INSIDE_VOLUMES_BEFORE, ray_index, dtype=object).reshape(-1)
        inside_after_arr = self._event_array(self.INSIDE_VOLUMES_AFTER, ray_index, dtype=object).reshape(-1)
        mesh_cell_id_arr = self._event_array(self.MESH_CELL_ID, ray_index, dtype=float).reshape(-1)
        mesh_original_cell_id_arr = self._event_array(self.MESH_ORIGINAL_CELL_ID, ray_index, dtype=float).reshape(-1)
        mesh_face_id_arr = self._event_array(self.MESH_FACE_ID, ray_index, dtype=object).reshape(-1)
        mesh_face_method_arr = self._event_array(self.MESH_FACE_MATCH_METHOD, ray_index, dtype=object).reshape(-1)
        mesh_face_score_arr = self._event_array(self.MESH_FACE_MATCH_SCORE, ray_index, dtype=float).reshape(-1)
        mesh_face_warning_arr = self._event_array(self.MESH_FACE_MATCH_WARNING, ray_index, dtype=object).reshape(-1)

        source_ray_index = self._event_scalar(self._event_array(self.SOURCE_RAY, ray_index), default=None)
        source_id = self._event_text(self._event_array(self.SOURCE_ID, ray_index))
        source_name = self._event_text(self._event_array(self.SOURCE_NAME, ray_index))
        source_role = self._event_text(self._event_array(self.SOURCE_ROLE, ray_index))
        source_model = self._event_text(self._event_array(self.SOURCE_MODEL, ray_index))
        source_wavelength = self._event_scalar(self._event_array(self.SOURCE_WAVELENGTH, ray_index), default=None)
        wave = self._event_scalar(self._event_array(self.RayWave, ray_index), default=source_wavelength)
        launch_field_requested = self._event_scalar(self._event_array(self.LAUNCH_FIELD_REQUESTED, ray_index), default=None)
        launch_field_effective = self._event_scalar(self._event_array(self.LAUNCH_FIELD_EFFECTIVE, ray_index), default=None)
        launch_field_basis = self._event_text(self._event_array(self.LAUNCH_FIELD_BASIS, ray_index))
        launch_field_unit = self._event_text(self._event_array(self.LAUNCH_FIELD_UNIT, ray_index))
        launch_field_min = self._event_scalar(self._event_array(self.LAUNCH_FIELD_MIN, ray_index), default=None)
        launch_field_max = self._event_scalar(self._event_array(self.LAUNCH_FIELD_MAX, ray_index), default=None)
        launch_field_active = self._event_bool(self._event_array(self.LAUNCH_FIELD_ACTIVE, ray_index), default=None)
        launch_ray_count = self._event_scalar(self._event_array(self.LAUNCH_RAY_COUNT, ray_index), default=None)
        launch_pupil_pattern = self._event_text(self._event_array(self.LAUNCH_PUPIL_PATTERN, ray_index))
        launch_trace_intent = self._event_text(self._event_array(self.LAUNCH_TRACE_INTENT, ray_index))
        launch_sampling_mode = self._event_text(self._event_array(self.LAUNCH_SAMPLING_MODE, ray_index))
        branch_id = self._event_scalar(self._event_array(self.BRANCH_ID, ray_index), default=0)
        branch_path = self._event_text(self._event_array(self.BRANCH_PATH, ray_index))
        branch_power = self._event_scalar(self._event_array(self.BRANCH_POWER, ray_index), default=None)
        branch_phase = self._event_scalar(self._event_array(self.BRANCH_PHASE, ray_index), default=None)
        termination_reason = self._event_text(self._event_array(self.BRANCH_TERMINATION_REASON, ray_index))
        termination_diagnostic = self._event_text(self._event_array(self.BRANCH_TERMINATION_DIAGNOSTIC, ray_index))
        branch_tree_diagnostic = self._event_text(self._event_array(self.BRANCH_TREE_DIAGNOSTIC, ray_index))
        branch_final_media = self._event_text(self._event_array(self.BRANCH_FINAL_MEDIA, ray_index))
        branch_final_index = self._event_scalar(self._event_array(self.BRANCH_FINAL_INDEX, ray_index), default=None)
        branch_final_inside = self._event_text(self._event_array(self.BRANCH_FINAL_INSIDE_VOLUMES, ray_index))
        branch_final_method = self._event_text(self._event_array(self.BRANCH_FINAL_MEDIA_STATE_METHOD, ray_index))
        terminal_target_surface = self._event_scalar(self._event_array(self.TERMINAL_TARGET_SURFACE, ray_index), default=None)
        terminal_detector_surfaces = self._event_int_list(
            self._event_text(self._event_array(self.TERMINAL_DETECTOR_SURFACES, ray_index))
        )
        terminal_policy_source = self._event_text(self._event_array(self.TERMINAL_POLICY_SOURCE, ray_index))

        hit_count = int(max(
            surface_arr.size,
            name_arr.size,
            glass_arr.size,
            distance_arr.size,
            op_arr.size,
            interaction_type_arr.size,
        ))
        records = []
        for step in range(hit_count):
            surface_id = self._event_scalar(surface_arr, step, default=None)
            n0 = self._event_scalar(n0_arr, step, default=None)
            n1 = self._event_scalar(n1_arr, step, default=None)
            glass = self._event_text(glass_arr, step)
            point_index = step + 1 if surface_arr.size and getattr(xyz_arr, "ndim", 0) == 2 and xyz_arr.shape[0] == surface_arr.size + 1 else step
            media_diag = self._event_text(media_state_diagnostic_arr, step)
            face_warning = self._event_text(mesh_face_warning_arr, step)
            diagnostic = "; ".join(value for value in (media_diag, face_warning) if str(value or "").strip())
            incoming_reference = self._polyline_direction(xyz_arr, point_index - 1, point_index)
            outgoing_reference = self._polyline_direction(xyz_arr, point_index, point_index + 1)
            if outgoing_reference is None and step == hit_count - 1:
                outgoing_reference = self._polyline_direction(cc_arr, cc_len - 2, cc_len - 1)
            incoming_direction = self._reconciled_direction(
                self._event_vector(lmn_arr, step), incoming_reference
            )
            outgoing_direction = self._reconciled_direction(
                self._event_vector(r_lmn_arr, step), outgoing_reference
            )
            records.append(
                TraceEventRecord(
                    event_id=f"ray:{int(ray_index)}:hit:{int(step)}",
                    event_source=TRACE_EVENT_SOURCE_RAYKEEPER,
                    event_kind=TRACE_EVENT_KIND_SURFACE,
                    event_type=self._event_type_label(self._event_text(interaction_type_arr, step), glass, n0, n1),
                    ray_index=int(ray_index),
                    source_ray_index=source_ray_index,
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    source_model=source_model,
                    wavelength=wave,
                    launch_field_requested=launch_field_requested,
                    launch_field_effective=launch_field_effective,
                    launch_field_basis=launch_field_basis,
                    launch_field_unit=launch_field_unit,
                    launch_field_min=launch_field_min,
                    launch_field_max=launch_field_max,
                    launch_field_active=launch_field_active,
                    launch_ray_count=launch_ray_count,
                    launch_pupil_pattern=launch_pupil_pattern,
                    launch_trace_intent=launch_trace_intent,
                    launch_sampling_mode=launch_sampling_mode,
                    branch_id=0 if branch_id is None else int(branch_id),
                    branch_path=branch_path,
                    branch_power=branch_power,
                    branch_phase_deg=branch_phase,
                    step=int(step),
                    surface_id=surface_id,
                    surface_name=self._event_text(name_arr, step),
                    material=glass,
                    point_world=self._event_vector(xyz_arr, point_index),
                    incoming_direction=incoming_direction,
                    outgoing_direction=outgoing_direction,
                    surface_normal=self._event_vector(s_lmn_arr, step),
                    n0=n0,
                    n1=n1,
                    distance=self._event_scalar(distance_arr, step, default=None),
                    optical_path=self._event_scalar(op_arr, step, default=None),
                    rp=self._event_scalar(rp_arr, step, default=None),
                    rs=self._event_scalar(rs_arr, step, default=None),
                    tp=self._event_scalar(tp_arr, step, default=None),
                    ts=self._event_scalar(ts_arr, step, default=None),
                    ttbe=self._event_scalar(ttbe_arr, step, default=None),
                    interaction_model=self._event_text(interaction_model_arr, step),
                    interaction_target_surface=self._event_scalar(interaction_target_arr, step, default=None),
                    interaction_in_power=self._event_scalar(interaction_in_power_arr, step, default=None),
                    interaction_coeff=self._event_scalar(interaction_coeff_arr, step, default=None),
                    interaction_out_power=self._event_scalar(interaction_out_power_arr, step, default=None),
                    interaction_loss_power=self._event_scalar(interaction_loss_power_arr, step, default=None),
                    interaction_bulk=self._event_scalar(interaction_bulk_arr, step, default=None),
                    volume_id=self._event_text(volume_id_arr, step),
                    media_in=self._event_text(media_in_arr, step),
                    media_out=self._event_text(media_out_arr, step),
                    media_transition=self._event_text(media_transition_arr, step),
                    media_state_method=self._event_text(media_state_method_arr, step),
                    media_state_diagnostic=media_diag,
                    inside_volumes_before=self._event_text(inside_before_arr, step),
                    inside_volumes_after=self._event_text(inside_after_arr, step),
                    mesh_cell_id=self._event_scalar(mesh_cell_id_arr, step, default=None),
                    mesh_original_cell_id=self._event_scalar(mesh_original_cell_id_arr, step, default=None),
                    mesh_face_id=self._event_text(mesh_face_id_arr, step),
                    mesh_face_match_method=self._event_text(mesh_face_method_arr, step),
                    mesh_face_match_score=self._event_scalar(mesh_face_score_arr, step, default=None),
                    mesh_face_match_warning=face_warning,
                    termination_reason="",
                    diagnostic=diagnostic,
                )
            )

        terminal_diagnostic = "; ".join(
            value for value in (termination_diagnostic, branch_tree_diagnostic) if str(value or "").strip()
        )
        last_surface = self._event_scalar(surface_arr, max(surface_arr.size - 1, 0), default=None)
        reaches_detector = last_surface is not None and int(last_surface) in set(int(item) for item in terminal_detector_surfaces)
        reaches_target = (
            last_surface is not None
            and terminal_target_surface is not None
            and int(last_surface) == int(terminal_target_surface)
        )
        if not str(termination_reason or "").strip() and str(terminal_policy_source or "").strip():
            try:
                terminal_continuation = (
                    np.asarray(cc_arr, dtype=float).ndim == 2
                    and np.asarray(cc_arr, dtype=float).shape[0] > int(surface_arr.size) + 1
                )
            except Exception:
                terminal_continuation = False
            if reaches_detector:
                termination_reason = "image"
            elif reaches_target:
                termination_reason = "target_surface_reached"
            elif last_surface is None:
                termination_reason = "no_hit"
            elif terminal_continuation:
                termination_reason = "missed_image" if terminal_detector_surfaces else "no_next_intersection"
            else:
                termination_reason = f"stopped_at_surface_{int(last_surface)}"
        if str(termination_reason or "").strip() or terminal_diagnostic:
            records.append(
                TraceEventRecord(
                    event_id=f"ray:{int(ray_index)}:terminal",
                    event_source=TRACE_EVENT_SOURCE_RAYKEEPER,
                    event_kind=TRACE_EVENT_KIND_TERMINAL,
                    event_type=str(termination_reason or "terminal"),
                    ray_index=int(ray_index),
                    source_ray_index=source_ray_index,
                    source_id=source_id,
                    source_name=source_name,
                    source_role=source_role,
                    source_model=source_model,
                    wavelength=wave,
                    launch_field_requested=launch_field_requested,
                    launch_field_effective=launch_field_effective,
                    launch_field_basis=launch_field_basis,
                    launch_field_unit=launch_field_unit,
                    launch_field_min=launch_field_min,
                    launch_field_max=launch_field_max,
                    launch_field_active=launch_field_active,
                    launch_ray_count=launch_ray_count,
                    launch_pupil_pattern=launch_pupil_pattern,
                    launch_trace_intent=launch_trace_intent,
                    launch_sampling_mode=launch_sampling_mode,
                    branch_id=0 if branch_id is None else int(branch_id),
                    branch_path=branch_path,
                    branch_power=branch_power,
                    branch_phase_deg=branch_phase,
                    step=int(hit_count),
                    surface_id=last_surface,
                    point_world=self._event_vector(cc_arr, -1),
                    incoming_direction=self._reconciled_direction(
                        self._event_vector(lmn_arr, max(hit_count - 1, 0)),
                        self._polyline_direction(cc_arr, cc_len - 2, cc_len - 1),
                    ),
                    outgoing_direction=self._reconciled_direction(
                        self._event_vector(r_lmn_arr, max(hit_count - 1, 0)),
                        self._polyline_direction(cc_arr, cc_len - 2, cc_len - 1),
                    ),
                    n1=branch_final_index,
                    media_in=branch_final_media,
                    media_out=branch_final_media,
                    media_transition="terminal_state" if branch_final_media or branch_final_index is not None else "",
                    media_state_method=branch_final_method,
                    inside_volumes_before=branch_final_inside,
                    inside_volumes_after=branch_final_inside,
                    termination_reason=str(termination_reason or ""),
                    terminal_target_surface=terminal_target_surface,
                    terminal_detector_surfaces=terminal_detector_surfaces,
                    terminal_policy_source=terminal_policy_source,
                    reaches_target=bool(reaches_target),
                    reaches_detector=bool(reaches_detector),
                    diagnostic=terminal_diagnostic,
                )
            )
        return records

    def _append_trace_event_records(self, ray_index):
        while len(self.TRACE_EVENTS) < ray_index:
            self.TRACE_EVENTS.append([])
        self.TRACE_EVENTS.append(self._trace_event_records_for_index(ray_index))

    def _append_source_metadata(self, source_ray_index, *, data=None, metadata=None):
        metadata = dict(metadata or {})
        data = data or {}

        source_xyz = metadata.get("source_xyz")
        if source_xyz is None:
            ray_arr = data.get("RAY", getattr(self.SYSTEM, "RAY", []))
            try:
                if len(ray_arr):
                    source_xyz = ray_arr[0]
            except Exception:
                source_xyz = None

        source_lmn = metadata.get("source_lmn")
        if source_lmn is None:
            lmn_arr = data.get("LMN", getattr(self.SYSTEM, "LMN", []))
            try:
                if len(lmn_arr):
                    source_lmn = lmn_arr[0]
            except Exception:
                source_lmn = None

        self.SOURCE_RAY.append(np.asarray(source_ray_index))
        self.SOURCE_XYZ.append(self._metadata_vector(source_xyz))
        self.SOURCE_LMN.append(self._metadata_vector(source_lmn))
        self.SOURCE_POWER.append(self._metadata_float(metadata.get("source_power")))
        self.SOURCE_WEIGHT.append(self._metadata_float(metadata.get("source_weight")))
        self.SOURCE_ID.append(self._metadata_text(metadata.get("source_id")))
        self.SOURCE_NAME.append(self._metadata_text(metadata.get("source_name")))
        self.SOURCE_ROLE.append(self._metadata_text(metadata.get("source_role")))
        self.SOURCE_MODEL.append(self._metadata_text(metadata.get("source_model")))
        self.SOURCE_WAVELENGTH.append(
            self._metadata_float(
                metadata.get("source_wavelength"),
                data.get("Wave", data.get("WAV", getattr(self.SYSTEM, "Wave", np.nan))),
            )
        )
        self.LAUNCH_FIELD_REQUESTED.append(self._metadata_float(metadata.get("launch_field_requested")))
        self.LAUNCH_FIELD_EFFECTIVE.append(self._metadata_float(metadata.get("launch_field_effective")))
        self.LAUNCH_FIELD_BASIS.append(self._metadata_text(metadata.get("launch_field_basis")))
        self.LAUNCH_FIELD_UNIT.append(self._metadata_text(metadata.get("launch_field_unit")))
        self.LAUNCH_FIELD_MIN.append(self._metadata_float(metadata.get("launch_field_min")))
        self.LAUNCH_FIELD_MAX.append(self._metadata_float(metadata.get("launch_field_max")))
        launch_field_active = metadata.get("launch_field_active")
        self.LAUNCH_FIELD_ACTIVE.append(
            self._metadata_float(None if launch_field_active is None else (1.0 if launch_field_active else 0.0))
        )
        self.LAUNCH_RAY_COUNT.append(self._metadata_float(metadata.get("launch_ray_count")))
        self.LAUNCH_PUPIL_PATTERN.append(self._metadata_text(metadata.get("launch_pupil_pattern")))
        self.LAUNCH_TRACE_INTENT.append(self._metadata_text(metadata.get("launch_trace_intent")))
        self.LAUNCH_SAMPLING_MODE.append(self._metadata_text(metadata.get("launch_sampling_mode")))
        target_surface = metadata.get("terminal_target_surface")
        if target_surface is None:
            target_surface = np.nan
        self.TERMINAL_TARGET_SURFACE.append(self._metadata_float(target_surface))
        self.TERMINAL_DETECTOR_SURFACES.append(self._metadata_int_list_text(metadata.get("terminal_detector_surfaces")))
        self.TERMINAL_POLICY_SOURCE.append(self._metadata_text(metadata.get("terminal_policy_source")))

    def valid(self):
        """valid.
        """
        z = np.argwhere((self.vld == 1))
        return z

    def _push_trace_snapshot(self, data, source_ray_index=None, source_metadata=None):
        """Append one traced branch/result snapshot to this raykeeper."""
        self.nelements = self.SYSTEM.n
        surface_arr = np.asarray(data.get('SURFACE', []))
        is_valid = bool(data.get('val', 1) == 1 and surface_arr.size > 0)

        name_arr = self._safe_array(data.get('NAME', []))
        glass_arr = self._safe_array(data.get('GLASS', []))
        s_xyz_arr = self._safe_array(data.get('S_XYZ', []), dtype=float)
        t_xyz_arr = self._safe_array(data.get('T_XYZ', []), dtype=float)
        xyz_arr = self._safe_array(data.get('XYZ', []), dtype=float)
        ost_xyz_arr = self._safe_array(data.get('OST_XYZ', []), dtype=float)
        ost_lmn_arr = self._safe_array(data.get('OST_LMN', []), dtype=float)
        s_lmn_arr = self._safe_array(data.get('S_LMN', []), dtype=float)
        lmn_arr = self._safe_array(data.get('LMN', []), dtype=float)
        r_lmn_arr = self._safe_array(data.get('R_LMN', []), dtype=float)
        n0_arr = self._safe_array(data.get('N0', []), dtype=float)
        n1_arr = self._safe_array(data.get('N1', []), dtype=float)
        wav_val = np.asarray(data.get('WAV', data.get('Wave', getattr(self.SYSTEM, 'Wave', 0.0))))
        g_lmn_arr = self._safe_array(data.get('G_LMN', []), dtype=float)
        order_arr = self._safe_array(data.get('ORDER', []), dtype=float)
        grating_arr = self._safe_array(data.get('GRATING', []), dtype=float)
        dist_arr = self._safe_array(data.get('DISTANCE', []), dtype=float)
        op_arr = self._safe_array(data.get('OP', []), dtype=float)
        top_s_arr = self._safe_array(data.get('TOP_S', []), dtype=float)
        top_val = np.asarray(data.get('TOP', 0.0))
        alpha_arr = self._safe_array(data.get('ALPHA', []), dtype=float)
        bulk_trans_arr = self._safe_array(data.get('BULK_TRANS', []), dtype=float)
        rp_arr = self._safe_array(data.get('RP', []), dtype=float)
        rs_arr = self._safe_array(data.get('RS', []), dtype=float)
        tp_arr = self._safe_array(data.get('TP', []), dtype=float)
        ts_arr = self._safe_array(data.get('TS', []), dtype=float)
        ttbe_arr = self._safe_array(data.get('TTBE', []), dtype=float)
        tt_val = np.asarray(data.get('TT', 0.0))
        ray_arr = self._safe_array(data.get('RAY', []), dtype=float)
        interaction_type_arr = self._safe_array(data.get('INTERACTION_TYPE', []), dtype=object)
        interaction_model_arr = self._safe_array(data.get('INTERACTION_MODEL', []), dtype=object)
        interaction_target_arr = self._safe_array(data.get('INTERACTION_TARGET_SURFACE', []), dtype=int)
        interaction_in_power_arr = self._safe_array(data.get('INTERACTION_IN_POWER', []), dtype=float)
        interaction_coeff_arr = self._safe_array(data.get('INTERACTION_COEFF', []), dtype=float)
        interaction_out_power_arr = self._safe_array(data.get('INTERACTION_OUT_POWER', []), dtype=float)
        interaction_loss_power_arr = self._safe_array(data.get('INTERACTION_LOSS_POWER', []), dtype=float)
        interaction_bulk_arr = self._safe_array(data.get('INTERACTION_BULK', []), dtype=float)
        mesh_cell_id_arr = self._safe_array(data.get('MESH_CELL_ID', []), dtype=int)
        mesh_original_cell_id_arr = self._safe_array(data.get('MESH_ORIGINAL_CELL_ID', []), dtype=int)
        mesh_face_id_arr = self._safe_array(data.get('MESH_FACE_ID', []), dtype=object)
        mesh_face_match_method_arr = self._safe_array(data.get('MESH_FACE_MATCH_METHOD', []), dtype=object)
        mesh_face_match_score_arr = self._safe_array(data.get('MESH_FACE_MATCH_SCORE', []), dtype=float)
        mesh_face_match_warning_arr = self._safe_array(data.get('MESH_FACE_MATCH_WARNING', []), dtype=object)
        volume_id_arr = self._safe_array(data.get('VOLUME_ID', []), dtype=object)
        media_in_arr = self._safe_array(data.get('MEDIA_IN', []), dtype=object)
        media_out_arr = self._safe_array(data.get('MEDIA_OUT', []), dtype=object)
        media_transition_arr = self._safe_array(data.get('MEDIA_TRANSITION', []), dtype=object)
        media_state_method_arr = self._safe_array(data.get('MEDIA_STATE_METHOD', []), dtype=object)
        media_state_diagnostic_arr = self._safe_array(data.get('MEDIA_STATE_DIAGNOSTIC', []), dtype=object)
        inside_volumes_before_arr = self._safe_array(data.get('INSIDE_VOLUMES_BEFORE', []), dtype=object)
        inside_volumes_after_arr = self._safe_array(data.get('INSIDE_VOLUMES_AFTER', []), dtype=object)
        branch_final_media = data.get('branch_final_media', None)
        if branch_final_media is None or not str(branch_final_media).strip():
            branch_final_media = self._event_text(media_out_arr, max(media_out_arr.size - 1, 0)) if media_out_arr.size else ""
        branch_final_index = data.get('branch_final_index', None)
        if branch_final_index is None:
            branch_final_index = self._event_scalar(n1_arr, max(n1_arr.size - 1, 0), default=np.nan)
        branch_final_inside = data.get('branch_final_inside_volumes', None)
        if branch_final_inside is None or not str(branch_final_inside).strip():
            branch_final_inside = (
                self._event_text(inside_volumes_after_arr, max(inside_volumes_after_arr.size - 1, 0))
                if inside_volumes_after_arr.size
                else ""
            )
        branch_final_method = data.get('branch_final_media_state_method', None)
        if branch_final_method is None or not str(branch_final_method).strip():
            branch_final_method = (
                self._event_text(media_state_method_arr, max(media_state_method_arr.size - 1, 0))
                if media_state_method_arr.size
                else ""
            )

        if is_valid:
            self.vld = np.append(self.vld, 1)
            self.valid_vld = np.append(self.vld, 0)
            self.valid_SURFACE.append(surface_arr)
            self.valid_NAME.append(name_arr)
            self.valid_GLASS.append(glass_arr)
            self.valid_S_XYZ.append(s_xyz_arr)
            self.valid_T_XYZ.append(t_xyz_arr)
            self.valid_XYZ.append(xyz_arr)
            self.valid_OST_XYZ.append(ost_xyz_arr)
            self.valid_OST_LMN.append(ost_lmn_arr)
            self.valid_S_LMN.append(s_lmn_arr)
            self.valid_LMN.append(lmn_arr)
            self.valid_R_LMN.append(r_lmn_arr)
            self.valid_N0.append(n0_arr)
            self.valid_N1.append(n1_arr)
            self.valid_WAV.append(wav_val)
            self.valid_G_LMN.append(g_lmn_arr)
            self.valid_ORDER.append(order_arr)
            self.valid_GRATING.append(grating_arr)
            self.valid_DISTANCE.append(dist_arr)
            self.valid_OP.append(op_arr)
            self.valid_TOP_S.append(top_s_arr)
            self.valid_TOP.append(top_val)
            self.valid_ALPHA.append(alpha_arr)
            self.valid_BULK_TRANS.append(bulk_trans_arr)
            self.valid_RP.append(rp_arr)
            self.valid_RS.append(rs_arr)
            self.valid_TP.append(tp_arr)
            self.valid_TS.append(ts_arr)
            self.valid_TTBE.append(ttbe_arr)
            self.valid_TT.append(tt_val)
            self.valid_INTERACTION_TYPE.append(interaction_type_arr)
            self.valid_INTERACTION_MODEL.append(interaction_model_arr)
            self.valid_INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
            self.valid_INTERACTION_IN_POWER.append(interaction_in_power_arr)
            self.valid_INTERACTION_COEFF.append(interaction_coeff_arr)
            self.valid_INTERACTION_OUT_POWER.append(interaction_out_power_arr)
            self.valid_INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
            self.valid_INTERACTION_BULK.append(interaction_bulk_arr)
            self.valid_MESH_CELL_ID.append(mesh_cell_id_arr)
            self.valid_MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
            self.valid_MESH_FACE_ID.append(mesh_face_id_arr)
            self.valid_MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
            self.valid_MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
            self.valid_MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
            self.valid_VOLUME_ID.append(volume_id_arr)
            self.valid_MEDIA_IN.append(media_in_arr)
            self.valid_MEDIA_OUT.append(media_out_arr)
            self.valid_MEDIA_TRANSITION.append(media_transition_arr)
            self.valid_MEDIA_STATE_METHOD.append(media_state_method_arr)
            self.valid_MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
            self.valid_INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
            self.valid_INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)
        else:
            self.vld = np.append(self.vld, 0)
            self.invalid_vld = np.append(self.vld, 0)
            self.invalid_SURFACE.append(surface_arr)
            self.invalid_NAME.append(name_arr)
            self.invalid_GLASS.append(glass_arr)
            self.invalid_S_XYZ.append(s_xyz_arr)
            self.invalid_T_XYZ.append(t_xyz_arr)
            self.invalid_XYZ.append(xyz_arr)
            self.invalid_OST_XYZ.append(ost_xyz_arr)
            self.invalid_OST_LMN.append(ost_lmn_arr)
            self.invalid_S_LMN.append(s_lmn_arr)
            self.invalid_LMN.append(lmn_arr)
            self.invalid_R_LMN.append(r_lmn_arr)
            self.invalid_N0.append(n0_arr)
            self.invalid_N1.append(n1_arr)
            self.invalid_WAV.append(wav_val)
            self.invalid_G_LMN.append(g_lmn_arr)
            self.invalid_ORDER.append(order_arr)
            self.invalid_GRATING.append(grating_arr)
            self.invalid_DISTANCE.append(dist_arr)
            self.invalid_OP.append(op_arr)
            self.invalid_TOP_S.append(top_s_arr)
            self.invalid_TOP.append(top_val)
            self.invalid_ALPHA.append(alpha_arr)
            self.invalid_BULK_TRANS.append(bulk_trans_arr)
            self.invalid_RP.append(rp_arr)
            self.invalid_RS.append(rs_arr)
            self.invalid_TP.append(tp_arr)
            self.invalid_TS.append(ts_arr)
            self.invalid_TTBE.append(ttbe_arr)
            self.invalid_TT.append(tt_val)
            self.invalid_INTERACTION_TYPE.append(interaction_type_arr)
            self.invalid_INTERACTION_MODEL.append(interaction_model_arr)
            self.invalid_INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
            self.invalid_INTERACTION_IN_POWER.append(interaction_in_power_arr)
            self.invalid_INTERACTION_COEFF.append(interaction_coeff_arr)
            self.invalid_INTERACTION_OUT_POWER.append(interaction_out_power_arr)
            self.invalid_INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
            self.invalid_INTERACTION_BULK.append(interaction_bulk_arr)
            self.invalid_MESH_CELL_ID.append(mesh_cell_id_arr)
            self.invalid_MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
            self.invalid_MESH_FACE_ID.append(mesh_face_id_arr)
            self.invalid_MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
            self.invalid_MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
            self.invalid_MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
            self.invalid_VOLUME_ID.append(volume_id_arr)
            self.invalid_MEDIA_IN.append(media_in_arr)
            self.invalid_MEDIA_OUT.append(media_out_arr)
            self.invalid_MEDIA_TRANSITION.append(media_transition_arr)
            self.invalid_MEDIA_STATE_METHOD.append(media_state_method_arr)
            self.invalid_MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
            self.invalid_INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
            self.invalid_INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)

        self.nrays = (self.nrays + 1)
        self.RayWave.append(data.get('Wave', getattr(self.SYSTEM, 'Wave', wav_val)))
        self.CC.append(ray_arr)
        self.SURFACE.append(surface_arr)
        self.NAME.append(name_arr)
        self.GLASS.append(glass_arr)
        self.S_XYZ.append(s_xyz_arr)
        self.T_XYZ.append(t_xyz_arr)
        self.XYZ.append(xyz_arr)
        self.OST_XYZ.append(ost_xyz_arr)
        self.OST_LMN.append(ost_lmn_arr)
        self.S_LMN.append(s_lmn_arr)
        self.LMN.append(lmn_arr)
        self.R_LMN.append(r_lmn_arr)
        self.N0.append(n0_arr)
        self.N1.append(n1_arr)
        self.WAV.append(wav_val)
        self.G_LMN.append(g_lmn_arr)
        self.ORDER.append(order_arr)
        self.GRATING.append(grating_arr)
        self.DISTANCE.append(dist_arr)
        self.OP.append(op_arr)
        self.TOP_S.append(top_s_arr)
        self.TOP.append(top_val)
        self.ALPHA.append(alpha_arr)
        self.BULK_TRANS.append(bulk_trans_arr)
        self.RP.append(rp_arr)
        self.RS.append(rs_arr)
        self.TP.append(tp_arr)
        self.TS.append(ts_arr)
        self.TTBE.append(ttbe_arr)
        self.TT.append(tt_val)
        self.INTERACTION_TYPE.append(interaction_type_arr)
        self.INTERACTION_MODEL.append(interaction_model_arr)
        self.INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
        self.INTERACTION_IN_POWER.append(interaction_in_power_arr)
        self.INTERACTION_COEFF.append(interaction_coeff_arr)
        self.INTERACTION_OUT_POWER.append(interaction_out_power_arr)
        self.INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
        self.INTERACTION_BULK.append(interaction_bulk_arr)
        self.MESH_CELL_ID.append(mesh_cell_id_arr)
        self.MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
        self.MESH_FACE_ID.append(mesh_face_id_arr)
        self.MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
        self.MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
        self.MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
        self.VOLUME_ID.append(volume_id_arr)
        self.MEDIA_IN.append(media_in_arr)
        self.MEDIA_OUT.append(media_out_arr)
        self.MEDIA_TRANSITION.append(media_transition_arr)
        self.MEDIA_STATE_METHOD.append(media_state_method_arr)
        self.MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
        self.INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
        self.INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)
        self._append_source_metadata(
            source_ray_index if source_ray_index is not None else data.get('source_ray_index', -1),
            data=data,
            metadata=source_metadata,
        )
        self.BRANCH_ID.append(np.asarray(data.get('branch_id', 0)))
        parent_branch = data.get('parent_branch_id', -1)
        self.PARENT_BRANCH_ID.append(np.asarray(-1 if parent_branch is None else parent_branch))
        self.BRANCH_POWER.append(np.asarray(data.get('branch_power', float(np.asarray(tt_val).ravel()[-1]) if np.asarray(tt_val).size else 0.0)))
        self.BRANCH_PHASE.append(np.asarray(data.get('branch_phase_deg', 0.0)))
        self.BRANCH_LABEL.append(np.asarray(data.get('branch_label', 'primary')))
        self.BRANCH_PATH.append(np.asarray(data.get('branch_path', data.get('branch_label', 'primary'))))
        self.BRANCH_TERMINATION_REASON.append(np.asarray(data.get('branch_termination_reason', '')))
        self.BRANCH_TERMINATION_DIAGNOSTIC.append(np.asarray(data.get('branch_termination_diagnostic', '')))
        self.BRANCH_TREE_DIAGNOSTIC.append(np.asarray(data.get('branch_tree_diagnostic', '')))
        self.BRANCH_JONES_P.append(np.asarray(data.get('branch_jones_p', complex(1.0, 0.0))))
        self.BRANCH_JONES_S.append(np.asarray(data.get('branch_jones_s', complex(0.0, 0.0))))
        self.BRANCH_POLARIZATION_XYZ.append(self._metadata_vector(data.get('branch_polarization_xyz'), dtype=np.complex128))
        self.BRANCH_FINAL_MEDIA.append(self._metadata_text(branch_final_media))
        self.BRANCH_FINAL_INDEX.append(self._metadata_float(branch_final_index))
        self.BRANCH_FINAL_INSIDE_VOLUMES.append(self._metadata_text(branch_final_inside))
        self.BRANCH_FINAL_MEDIA_STATE_METHOD.append(self._metadata_text(branch_final_method))
        self._append_trace_event_records(self.nrays - 1)

    def _push_branch_results(self, branch_results):
        source_ray_index = self._launch_count
        source_metadata = self._pending_launch_metadata
        for result in branch_results:
            self._push_trace_snapshot(result, source_ray_index=source_ray_index, source_metadata=source_metadata)
        self._launch_count += 1
        self._pending_launch_metadata = None

    def push(self):
        """push.
        """
        branch_results = getattr(self.SYSTEM, "NS_BRANCH_RESULTS", None)
        if branch_results:
            self._push_branch_results(branch_results)
            self.SYSTEM.NS_BRANCH_RESULTS = []
            return

        self.nelements = self.SYSTEM.n
        if (self.SYSTEM.val == 0):
            self.invalid_vld = np.append(self.vld, 0)
            self.invalid_SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
            self.invalid_NAME.append(np.asarray(self.SYSTEM.NAME))
            self.invalid_GLASS.append(np.asarray(self.SYSTEM.GLASS))
            self.invalid_S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
            self.invalid_T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
            self.invalid_XYZ.append(np.asarray(self.SYSTEM.XYZ))

            lst = self.SYSTEM.OST_XYZ
            ll = filter(None, lst)
            self.invalid_OST_XYZ.append(np.asarray(ll))
            self.invalid_OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
            self.invalid_S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
            self.invalid_LMN.append(np.asarray(self.SYSTEM.LMN))
            self.invalid_R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
            self.invalid_N0.append(np.asarray(self.SYSTEM.N0))
            self.invalid_N1.append(np.asarray(self.SYSTEM.N1))
            self.invalid_WAV.append(np.asarray(self.SYSTEM.WAV))
            self.invalid_G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
            self.invalid_ORDER.append(np.asarray(self.SYSTEM.ORDER))
            self.invalid_GRATING.append(np.asarray(self.SYSTEM.GRATING))
            self.invalid_DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
            self.invalid_OP.append(np.asarray(self.SYSTEM.OP))
            self.invalid_TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
            self.invalid_TOP.append(np.asarray(self.SYSTEM.TOP))
            lst = self.SYSTEM.ALPHA
            ll = filter(None, lst)
            self.invalid_ALPHA.append(np.asarray(ll))
            self.invalid_BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
            self.invalid_RP.append(np.asarray(self.SYSTEM.RP))
            self.invalid_RS.append(np.asarray(self.SYSTEM.RS))
            self.invalid_TP.append(np.asarray(self.SYSTEM.TP))
            self.invalid_TS.append(np.asarray(self.SYSTEM.TS))
            self.invalid_TTBE.append(np.asarray(self.SYSTEM.TTBE))
            self.invalid_TT.append(np.asarray(self.SYSTEM.TT))
            self.invalid_INTERACTION_TYPE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TYPE", []), dtype=object))
            self.invalid_INTERACTION_MODEL.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_MODEL", []), dtype=object))
            self.invalid_INTERACTION_TARGET_SURFACE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TARGET_SURFACE", []), dtype=int))
            self.invalid_INTERACTION_IN_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_IN_POWER", []), dtype=float))
            self.invalid_INTERACTION_COEFF.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_COEFF", []), dtype=float))
            self.invalid_INTERACTION_OUT_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_OUT_POWER", []), dtype=float))
            self.invalid_INTERACTION_LOSS_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_LOSS_POWER", []), dtype=float))
            self.invalid_INTERACTION_BULK.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_BULK", []), dtype=float))
            self.invalid_MESH_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_CELL_ID", []), dtype=int))
            self.invalid_MESH_ORIGINAL_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_ORIGINAL_CELL_ID", []), dtype=int))
            self.invalid_MESH_FACE_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_ID", []), dtype=object))
            self.invalid_MESH_FACE_MATCH_METHOD.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_METHOD", []), dtype=object))
            self.invalid_MESH_FACE_MATCH_SCORE.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_SCORE", []), dtype=float))
            self.invalid_MESH_FACE_MATCH_WARNING.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_WARNING", []), dtype=object))
            self.invalid_VOLUME_ID.append(np.asarray(getattr(self.SYSTEM, "VOLUME_ID", []), dtype=object))
            self.invalid_MEDIA_IN.append(np.asarray(getattr(self.SYSTEM, "MEDIA_IN", []), dtype=object))
            self.invalid_MEDIA_OUT.append(np.asarray(getattr(self.SYSTEM, "MEDIA_OUT", []), dtype=object))
            self.invalid_MEDIA_TRANSITION.append(np.asarray(getattr(self.SYSTEM, "MEDIA_TRANSITION", []), dtype=object))
            self.invalid_MEDIA_STATE_METHOD.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_METHOD", []), dtype=object))
            self.invalid_MEDIA_STATE_DIAGNOSTIC.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_DIAGNOSTIC", []), dtype=object))
            self.invalid_INSIDE_VOLUMES_BEFORE.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_BEFORE", []), dtype=object))
            self.invalid_INSIDE_VOLUMES_AFTER.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_AFTER", []), dtype=object))
        else:
            self.vld = np.append(self.vld, 1)
            self.valid_vld = np.append(self.vld, 0)
            self.valid_SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
            self.valid_NAME.append(np.asarray(self.SYSTEM.NAME))
            self.valid_GLASS.append(np.asarray(self.SYSTEM.GLASS))
            self.valid_S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
            self.valid_T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
            self.valid_XYZ.append(np.asarray(self.SYSTEM.XYZ))
            self.valid_OST_XYZ.append(np.asarray(self.SYSTEM.OST_XYZ))
            self.valid_OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
            self.valid_S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
            self.valid_LMN.append(np.asarray(self.SYSTEM.LMN))
            self.valid_R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
            self.valid_N0.append(np.asarray(self.SYSTEM.N0))
            self.valid_N1.append(np.asarray(self.SYSTEM.N1))
            self.valid_WAV.append(np.asarray(self.SYSTEM.WAV))
            self.valid_G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
            self.valid_ORDER.append(np.asarray(self.SYSTEM.ORDER))
            self.valid_GRATING.append(np.asarray(self.SYSTEM.GRATING))
            self.valid_DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
            self.valid_OP.append(np.asarray(self.SYSTEM.OP))
            self.valid_TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
            self.valid_TOP.append(np.asarray(self.SYSTEM.TOP))
            self.valid_ALPHA.append(np.asarray(self.SYSTEM.ALPHA))
            self.valid_BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
            self.valid_RP.append(np.asarray(self.SYSTEM.RP))
            self.valid_RS.append(np.asarray(self.SYSTEM.RS))
            self.valid_TP.append(np.asarray(self.SYSTEM.TP))
            self.valid_TS.append(np.asarray(self.SYSTEM.TS))
            self.valid_TTBE.append(np.asarray(self.SYSTEM.TTBE))
            self.valid_TT.append(np.asarray(self.SYSTEM.TT))
            self.valid_INTERACTION_TYPE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TYPE", []), dtype=object))
            self.valid_INTERACTION_MODEL.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_MODEL", []), dtype=object))
            self.valid_INTERACTION_TARGET_SURFACE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TARGET_SURFACE", []), dtype=int))
            self.valid_INTERACTION_IN_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_IN_POWER", []), dtype=float))
            self.valid_INTERACTION_COEFF.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_COEFF", []), dtype=float))
            self.valid_INTERACTION_OUT_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_OUT_POWER", []), dtype=float))
            self.valid_INTERACTION_LOSS_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_LOSS_POWER", []), dtype=float))
            self.valid_INTERACTION_BULK.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_BULK", []), dtype=float))
            self.valid_MESH_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_CELL_ID", []), dtype=int))
            self.valid_MESH_ORIGINAL_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_ORIGINAL_CELL_ID", []), dtype=int))
            self.valid_MESH_FACE_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_ID", []), dtype=object))
            self.valid_MESH_FACE_MATCH_METHOD.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_METHOD", []), dtype=object))
            self.valid_MESH_FACE_MATCH_SCORE.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_SCORE", []), dtype=float))
            self.valid_MESH_FACE_MATCH_WARNING.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_WARNING", []), dtype=object))
            self.valid_VOLUME_ID.append(np.asarray(getattr(self.SYSTEM, "VOLUME_ID", []), dtype=object))
            self.valid_MEDIA_IN.append(np.asarray(getattr(self.SYSTEM, "MEDIA_IN", []), dtype=object))
            self.valid_MEDIA_OUT.append(np.asarray(getattr(self.SYSTEM, "MEDIA_OUT", []), dtype=object))
            self.valid_MEDIA_TRANSITION.append(np.asarray(getattr(self.SYSTEM, "MEDIA_TRANSITION", []), dtype=object))
            self.valid_MEDIA_STATE_METHOD.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_METHOD", []), dtype=object))
            self.valid_MEDIA_STATE_DIAGNOSTIC.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_DIAGNOSTIC", []), dtype=object))
            self.valid_INSIDE_VOLUMES_BEFORE.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_BEFORE", []), dtype=object))
            self.valid_INSIDE_VOLUMES_AFTER.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_AFTER", []), dtype=object))
        self.nrays = (self.nrays + 1)


        self.RayWave.append(self.SYSTEM.Wave)
        self.CC.append(self.SYSTEM.ray_SurfHits)



        self.SURFACE.append(np.asarray(self.SYSTEM.SURFACE))
        self.NAME.append(np.asarray(self.SYSTEM.NAME))
        self.GLASS.append(np.asarray(self.SYSTEM.GLASS))
        self.S_XYZ.append(np.asarray(self.SYSTEM.S_XYZ))
        self.T_XYZ.append(np.asarray(self.SYSTEM.T_XYZ))
        self.XYZ.append(np.asarray(self.SYSTEM.XYZ))

        # revisar
        lst = self.SYSTEM.OST_XYZ
        ll = filter(None, lst)
        self.OST_XYZ.append(np.asarray(ll))

        # self.OST_XYZ.append(np.asarray(self.SYSTEM.OST_XYZ))
        self.OST_LMN.append(np.asarray(self.SYSTEM.OST_LMN))
        self.S_LMN.append(np.asarray(self.SYSTEM.S_LMN))
        self.LMN.append(np.asarray(self.SYSTEM.LMN))
        self.R_LMN.append(np.asarray(self.SYSTEM.R_LMN))
        self.N0.append(np.asarray(self.SYSTEM.N0))
        self.N1.append(np.asarray(self.SYSTEM.N1))
        self.WAV.append(np.asarray(self.SYSTEM.WAV))
        self.G_LMN.append(np.asarray(self.SYSTEM.G_LMN))
        self.ORDER.append(np.asarray(self.SYSTEM.ORDER))
        self.GRATING.append(np.asarray(self.SYSTEM.GRATING))
        self.DISTANCE.append(np.asarray(self.SYSTEM.DISTANCE))
        self.OP.append(np.asarray(self.SYSTEM.OP))
        self.TOP_S.append(np.asarray(self.SYSTEM.TOP_S))
        self.TOP.append(np.asarray(self.SYSTEM.TOP))
        lst = self.SYSTEM.ALPHA
        ll = filter(None, lst)
        self.ALPHA.append(np.asarray(ll))
        self.BULK_TRANS.append(np.asarray(self.SYSTEM.BULK_TRANS))
        self.RP.append(np.asarray(self.SYSTEM.RP))
        self.RS.append(np.asarray(self.SYSTEM.RS))
        self.TP.append(np.asarray(self.SYSTEM.TP))
        self.TS.append(np.asarray(self.SYSTEM.TS))
        self.TTBE.append(np.asarray(self.SYSTEM.TTBE))
        self.TT.append(np.asarray(self.SYSTEM.TT))
        self.INTERACTION_TYPE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TYPE", []), dtype=object))
        self.INTERACTION_MODEL.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_MODEL", []), dtype=object))
        self.INTERACTION_TARGET_SURFACE.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_TARGET_SURFACE", []), dtype=int))
        self.INTERACTION_IN_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_IN_POWER", []), dtype=float))
        self.INTERACTION_COEFF.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_COEFF", []), dtype=float))
        self.INTERACTION_OUT_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_OUT_POWER", []), dtype=float))
        self.INTERACTION_LOSS_POWER.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_LOSS_POWER", []), dtype=float))
        self.INTERACTION_BULK.append(np.asarray(getattr(self.SYSTEM, "INTERACTION_BULK", []), dtype=float))
        self.MESH_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_CELL_ID", []), dtype=int))
        self.MESH_ORIGINAL_CELL_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_ORIGINAL_CELL_ID", []), dtype=int))
        self.MESH_FACE_ID.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_ID", []), dtype=object))
        self.MESH_FACE_MATCH_METHOD.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_METHOD", []), dtype=object))
        self.MESH_FACE_MATCH_SCORE.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_SCORE", []), dtype=float))
        self.MESH_FACE_MATCH_WARNING.append(np.asarray(getattr(self.SYSTEM, "MESH_FACE_MATCH_WARNING", []), dtype=object))
        self.VOLUME_ID.append(np.asarray(getattr(self.SYSTEM, "VOLUME_ID", []), dtype=object))
        self.MEDIA_IN.append(np.asarray(getattr(self.SYSTEM, "MEDIA_IN", []), dtype=object))
        self.MEDIA_OUT.append(np.asarray(getattr(self.SYSTEM, "MEDIA_OUT", []), dtype=object))
        self.MEDIA_TRANSITION.append(np.asarray(getattr(self.SYSTEM, "MEDIA_TRANSITION", []), dtype=object))
        self.MEDIA_STATE_METHOD.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_METHOD", []), dtype=object))
        self.MEDIA_STATE_DIAGNOSTIC.append(np.asarray(getattr(self.SYSTEM, "MEDIA_STATE_DIAGNOSTIC", []), dtype=object))
        self.INSIDE_VOLUMES_BEFORE.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_BEFORE", []), dtype=object))
        self.INSIDE_VOLUMES_AFTER.append(np.asarray(getattr(self.SYSTEM, "INSIDE_VOLUMES_AFTER", []), dtype=object))
        self._append_source_metadata(self._launch_count, metadata=self._pending_launch_metadata)
        self.BRANCH_ID.append(np.asarray(0))
        self.PARENT_BRANCH_ID.append(np.asarray(-1))
        self.BRANCH_POWER.append(np.asarray(float(np.asarray(self.SYSTEM.TT).ravel()[-1]) if np.asarray(self.SYSTEM.TT).size else 0.0))
        self.BRANCH_PHASE.append(np.asarray(0.0))
        self.BRANCH_LABEL.append(np.asarray("primary"))
        self.BRANCH_PATH.append(np.asarray("primary"))
        self.BRANCH_TERMINATION_REASON.append(np.asarray(""))
        self.BRANCH_TERMINATION_DIAGNOSTIC.append(np.asarray(""))
        self.BRANCH_TREE_DIAGNOSTIC.append(np.asarray(""))
        self.BRANCH_JONES_P.append(np.asarray(complex(1.0, 0.0)))
        self.BRANCH_JONES_S.append(np.asarray(complex(0.0, 0.0)))
        self.BRANCH_POLARIZATION_XYZ.append(self._metadata_vector((1.0, 0.0, 0.0), dtype=np.complex128))
        self.BRANCH_FINAL_MEDIA.append(self._metadata_text(getattr(self.SYSTEM, "BRANCH_FINAL_MEDIA", "")))
        self.BRANCH_FINAL_INDEX.append(self._metadata_float(getattr(self.SYSTEM, "BRANCH_FINAL_INDEX", np.nan)))
        self.BRANCH_FINAL_INSIDE_VOLUMES.append(self._metadata_text(getattr(self.SYSTEM, "BRANCH_FINAL_INSIDE_VOLUMES", "")))
        self.BRANCH_FINAL_MEDIA_STATE_METHOD.append(
            self._metadata_text(getattr(self.SYSTEM, "BRANCH_FINAL_MEDIA_STATE_METHOD", ""))
        )
        self._append_trace_event_records(self.nrays - 1)
        self._launch_count += 1
        self._pending_launch_metadata = None

    def clean(self):
        """clean.
        """
        self.vld = np.asarray([])
        self.nrays = 0
        self.RayWave = []
        self.CC =[]
        self.SURFACE = []
        self.NAME = []
        self.GLASS = []
        self.S_XYZ = []
        self.T_XYZ = []
        self.XYZ = []
        self.OST_XYZ = []
        self.OST_LMN = []
        self.S_LMN = []
        self.LMN = []
        self.R_LMN = []
        self.N0 = []
        self.N1 = []
        self.WAV = []
        self.G_LMN = []
        self.ORDER = []
        self.GRATING = []
        self.DISTANCE = []
        self.OP = []
        self.TOP_S = []
        self.TOP = []
        self.ALPHA = []
        self.BULK_TRANS = []
        self.RP = []
        self.RS = []
        self.TP = []
        self.TS = []
        self.TTBE = []
        self.TT = []
        self.INTERACTION_TYPE = []
        self.INTERACTION_MODEL = []
        self.INTERACTION_TARGET_SURFACE = []
        self.INTERACTION_IN_POWER = []
        self.INTERACTION_COEFF = []
        self.INTERACTION_OUT_POWER = []
        self.INTERACTION_LOSS_POWER = []
        self.INTERACTION_BULK = []
        self.MESH_CELL_ID = []
        self.MESH_ORIGINAL_CELL_ID = []
        self.MESH_FACE_ID = []
        self.MESH_FACE_MATCH_METHOD = []
        self.MESH_FACE_MATCH_SCORE = []
        self.MESH_FACE_MATCH_WARNING = []
        self.VOLUME_ID = []
        self.MEDIA_IN = []
        self.MEDIA_OUT = []
        self.MEDIA_TRANSITION = []
        self.MEDIA_STATE_METHOD = []
        self.MEDIA_STATE_DIAGNOSTIC = []
        self.INSIDE_VOLUMES_BEFORE = []
        self.INSIDE_VOLUMES_AFTER = []
        self.SOURCE_RAY = []
        self.SOURCE_XYZ = []
        self.SOURCE_LMN = []
        self.SOURCE_POWER = []
        self.SOURCE_WEIGHT = []
        self.SOURCE_ID = []
        self.SOURCE_NAME = []
        self.SOURCE_ROLE = []
        self.SOURCE_MODEL = []
        self.SOURCE_WAVELENGTH = []
        self.LAUNCH_FIELD_REQUESTED = []
        self.LAUNCH_FIELD_EFFECTIVE = []
        self.LAUNCH_FIELD_BASIS = []
        self.LAUNCH_FIELD_UNIT = []
        self.LAUNCH_FIELD_MIN = []
        self.LAUNCH_FIELD_MAX = []
        self.LAUNCH_FIELD_ACTIVE = []
        self.LAUNCH_RAY_COUNT = []
        self.LAUNCH_PUPIL_PATTERN = []
        self.LAUNCH_TRACE_INTENT = []
        self.LAUNCH_SAMPLING_MODE = []
        self.TERMINAL_TARGET_SURFACE = []
        self.TERMINAL_DETECTOR_SURFACES = []
        self.TERMINAL_POLICY_SOURCE = []
        self.BRANCH_ID = []
        self.PARENT_BRANCH_ID = []
        self.BRANCH_POWER = []
        self.BRANCH_PHASE = []
        self.BRANCH_LABEL = []
        self.BRANCH_PATH = []
        self.BRANCH_TERMINATION_REASON = []
        self.BRANCH_TERMINATION_DIAGNOSTIC = []
        self.BRANCH_TREE_DIAGNOSTIC = []
        self.BRANCH_JONES_P = []
        self.BRANCH_JONES_S = []
        self.BRANCH_POLARIZATION_XYZ = []
        self.BRANCH_FINAL_MEDIA = []
        self.BRANCH_FINAL_INDEX = []
        self.BRANCH_FINAL_INSIDE_VOLUMES = []
        self.BRANCH_FINAL_MEDIA_STATE_METHOD = []
        self.TRACE_EVENTS = []
        self._launch_count = 0
        self._pending_launch_metadata = None
        self.valid_vld = np.asarray([])
        self.valid_RayWave = []
        self.valid_CCC = pv.MultiBlock()
        self.valid_SURFACE = []
        self.valid_NAME = []
        self.valid_GLASS = []
        self.valid_S_XYZ = []
        self.valid_T_XYZ = []
        self.valid_XYZ = []
        self.valid_OST_XYZ = []
        self.valid_OST_LMN = []
        self.valid_S_LMN = []
        self.valid_LMN = []
        self.valid_R_LMN = []
        self.valid_N0 = []
        self.valid_N1 = []
        self.valid_WAV = []
        self.valid_G_LMN = []
        self.valid_ORDER = []
        self.valid_GRATING = []
        self.valid_DISTANCE = []
        self.valid_OP = []
        self.valid_TOP_S = []
        self.valid_TOP = []
        self.valid_ALPHA = []
        self.valid_BULK_TRANS = []
        self.valid_RP = []
        self.valid_RS = []
        self.valid_TP = []
        self.valid_TS = []
        self.valid_TTBE = []
        self.valid_TT = []
        self.valid_INTERACTION_TYPE = []
        self.valid_INTERACTION_MODEL = []
        self.valid_INTERACTION_TARGET_SURFACE = []
        self.valid_INTERACTION_IN_POWER = []
        self.valid_INTERACTION_COEFF = []
        self.valid_INTERACTION_OUT_POWER = []
        self.valid_INTERACTION_LOSS_POWER = []
        self.valid_INTERACTION_BULK = []
        self.valid_MESH_CELL_ID = []
        self.valid_MESH_ORIGINAL_CELL_ID = []
        self.valid_MESH_FACE_ID = []
        self.valid_MESH_FACE_MATCH_METHOD = []
        self.valid_MESH_FACE_MATCH_SCORE = []
        self.valid_MESH_FACE_MATCH_WARNING = []
        self.valid_VOLUME_ID = []
        self.valid_MEDIA_IN = []
        self.valid_MEDIA_OUT = []
        self.valid_MEDIA_TRANSITION = []
        self.valid_MEDIA_STATE_METHOD = []
        self.valid_MEDIA_STATE_DIAGNOSTIC = []
        self.valid_INSIDE_VOLUMES_BEFORE = []
        self.valid_INSIDE_VOLUMES_AFTER = []
        self.invalid_vld = np.asarray([])
        self.invalid_RayWave = []
        self.invalid_CCC = pv.MultiBlock()
        self.invalid_SURFACE = []
        self.invalid_NAME = []
        self.invalid_GLASS = []
        self.invalid_S_XYZ = []
        self.invalid_T_XYZ = []
        self.invalid_XYZ = []
        self.invalid_OST_XYZ = []
        self.invalid_OST_LMN = []
        self.invalid_S_LMN = []
        self.invalid_LMN = []
        self.invalid_R_LMN = []
        self.invalid_N0 = []
        self.invalid_N1 = []
        self.invalid_WAV = []
        self.invalid_G_LMN = []
        self.invalid_ORDER = []
        self.invalid_GRATING = []
        self.invalid_DISTANCE = []
        self.invalid_OP = []
        self.invalid_TOP_S = []
        self.invalid_TOP = []
        self.invalid_ALPHA = []
        self.invalid_BULK_TRANS = []
        self.invalid_RP = []
        self.invalid_RS = []
        self.invalid_TP = []
        self.invalid_TS = []
        self.invalid_TTBE = []
        self.invalid_TT = []
        self.invalid_INTERACTION_TYPE = []
        self.invalid_INTERACTION_MODEL = []
        self.invalid_INTERACTION_TARGET_SURFACE = []
        self.invalid_INTERACTION_IN_POWER = []
        self.invalid_INTERACTION_COEFF = []
        self.invalid_INTERACTION_OUT_POWER = []
        self.invalid_INTERACTION_LOSS_POWER = []
        self.invalid_INTERACTION_BULK = []
        self.invalid_MESH_CELL_ID = []
        self.invalid_MESH_ORIGINAL_CELL_ID = []
        self.invalid_MESH_FACE_ID = []
        self.invalid_MESH_FACE_MATCH_METHOD = []
        self.invalid_MESH_FACE_MATCH_SCORE = []
        self.invalid_MESH_FACE_MATCH_WARNING = []
        self.invalid_VOLUME_ID = []
        self.invalid_MEDIA_IN = []
        self.invalid_MEDIA_OUT = []
        self.invalid_MEDIA_TRANSITION = []
        self.invalid_MEDIA_STATE_METHOD = []
        self.invalid_MEDIA_STATE_DIAGNOSTIC = []
        self.invalid_INSIDE_VOLUMES_BEFORE = []
        self.invalid_INSIDE_VOLUMES_AFTER = []

    def batch_push(self, batch_results, batch_active, wave, source_metadata=None):
        """Push all batch ray-trace results at once.

        Bypasses the per-ray ``_apply_batch_result`` → ``push()`` round-trip,
        directly reading from the batch result dicts and writing into the
        raykeeper lists.  This eliminates ~60 attribute accesses per ray
        compared to the old path.

        Parameters
        ----------
        batch_results : list[dict] — per-ray result dicts from ``BatchTrace``
        batch_active : (N,) bool array — ``True`` for rays that reached the image
        wave : float — wavelength
        source_metadata : optional sequence of per-ray launch metadata dicts
        """
        self.nelements = self.SYSTEM.n
        N_rays = len(batch_results)
        metadata_seq = list(source_metadata or [])

        for i in range(N_rays):
            d = batch_results[i]
            is_valid = bool(batch_active[i]) and d.get('val', 1) == 1 and len(d['SURFACE']) > 0
            n_surf = len(d['SURFACE'])

            # Build numpy arrays from the batch dict
            surface_arr = np.asarray(d['SURFACE'])
            name_arr = np.asarray(d['NAME'])
            glass_arr = np.asarray(d['GLASS'])
            s_xyz_arr = np.asarray(d['S_XYZ']) if d['S_XYZ'] else np.empty((0, 3))
            t_xyz_arr = np.asarray(d['T_XYZ']) if d['T_XYZ'] else np.empty((0, 3))
            xyz_arr = np.asarray(d['XYZ'])
            ost_xyz_arr = np.asarray(d['OST_XYZ'])
            ost_lmn_arr = np.asarray(d['OST_LMN']) if d['OST_LMN'] else np.empty((0, 3))
            s_lmn_arr = np.asarray(d['S_LMN']) if d['S_LMN'] else np.empty((0, 3))
            lmn_arr = np.asarray(d['LMN']) if d['LMN'] else np.empty((0, 3))
            r_lmn_arr = np.asarray(d['R_LMN']) if d['R_LMN'] else np.empty((0, 3))
            n0_arr = np.asarray(d['N0'])
            n1_arr = np.asarray(d['N1'])
            dist_arr = np.asarray(d['DISTANCE'])
            op_arr = np.asarray(d['OP'])
            top_s_arr = np.asarray(d['TOP_S'])
            top_val = np.asarray(d['TOP'])
            wav_val = np.asarray(wave)

            # Placeholders that BatchTrace doesn't compute
            g_lmn_arr = np.asarray([[0, 1, 0]] * n_surf) if n_surf > 0 else np.empty((0, 3))
            order_arr = np.zeros(n_surf)
            grating_arr = np.zeros(n_surf)
            alpha_arr = np.zeros(n_surf + 2)
            bulk_trans_arr = np.asarray([])
            rp_arr = np.zeros(n_surf)
            rs_arr = np.zeros(n_surf)
            tp_arr = np.ones(n_surf)
            ts_arr = np.ones(n_surf)
            ttbe_arr = np.ones(n_surf)
            tt_val = np.asarray(1.0)
            interaction_type_values = []
            for step in range(n_surf):
                glass_text = str(glass_arr[step]).strip().upper() if step < glass_arr.size else ""
                if glass_text == "MIRROR":
                    interaction_type_values.append("reflect")
                elif step < n0_arr.size and step < n1_arr.size and abs(float(n0_arr[step]) - float(n1_arr[step])) > 1e-9:
                    interaction_type_values.append("refract")
                else:
                    interaction_type_values.append("transmit")
            interaction_type_arr = np.asarray(interaction_type_values, dtype=object)
            interaction_model_arr = np.full(n_surf, "", dtype=object)
            interaction_target_arr = np.full(n_surf, -1, dtype=int)
            interaction_in_power_arr = np.full(n_surf, np.nan, dtype=float)
            interaction_coeff_arr = np.full(n_surf, np.nan, dtype=float)
            interaction_out_power_arr = np.full(n_surf, np.nan, dtype=float)
            interaction_loss_power_arr = np.full(n_surf, np.nan, dtype=float)
            interaction_bulk_arr = np.full(n_surf, np.nan, dtype=float)
            mesh_cell_id_arr = np.full(n_surf, -1, dtype=int)
            mesh_original_cell_id_arr = np.full(n_surf, -1, dtype=int)
            mesh_face_id_arr = np.full(n_surf, "", dtype=object)
            mesh_face_match_method_arr = np.full(n_surf, "", dtype=object)
            mesh_face_match_score_arr = np.full(n_surf, np.nan, dtype=float)
            mesh_face_match_warning_arr = np.full(n_surf, "", dtype=object)
            volume_id_arr = np.full(n_surf, "", dtype=object)
            media_in_arr = np.full(n_surf, "", dtype=object)
            media_out_arr = np.full(n_surf, "", dtype=object)
            media_transition_arr = np.full(n_surf, "", dtype=object)
            media_state_method_arr = np.full(n_surf, "", dtype=object)
            media_state_diagnostic_arr = np.full(n_surf, "", dtype=object)
            inside_volumes_before_arr = np.full(n_surf, "", dtype=object)
            inside_volumes_after_arr = np.full(n_surf, "", dtype=object)

            ray_list = d['RAY']
            ray_arr = np.asarray(ray_list) if len(ray_list) > 0 else np.empty((0, 3))

            if is_valid:
                self.vld = np.append(self.vld, 1)
                self.valid_SURFACE.append(surface_arr)
                self.valid_NAME.append(name_arr)
                self.valid_GLASS.append(glass_arr)
                self.valid_S_XYZ.append(s_xyz_arr)
                self.valid_T_XYZ.append(t_xyz_arr)
                self.valid_XYZ.append(xyz_arr)
                self.valid_OST_XYZ.append(ost_xyz_arr)
                self.valid_OST_LMN.append(ost_lmn_arr)
                self.valid_S_LMN.append(s_lmn_arr)
                self.valid_LMN.append(lmn_arr)
                self.valid_R_LMN.append(r_lmn_arr)
                self.valid_N0.append(n0_arr)
                self.valid_N1.append(n1_arr)
                self.valid_WAV.append(wav_val)
                self.valid_G_LMN.append(g_lmn_arr)
                self.valid_ORDER.append(order_arr)
                self.valid_GRATING.append(grating_arr)
                self.valid_DISTANCE.append(dist_arr)
                self.valid_OP.append(op_arr)
                self.valid_TOP_S.append(top_s_arr)
                self.valid_TOP.append(top_val)
                self.valid_ALPHA.append(alpha_arr)
                self.valid_BULK_TRANS.append(bulk_trans_arr)
                self.valid_RP.append(rp_arr)
                self.valid_RS.append(rs_arr)
                self.valid_TP.append(tp_arr)
                self.valid_TS.append(ts_arr)
                self.valid_TTBE.append(ttbe_arr)
                self.valid_TT.append(tt_val)
                self.valid_INTERACTION_TYPE.append(interaction_type_arr)
                self.valid_INTERACTION_MODEL.append(interaction_model_arr)
                self.valid_INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
                self.valid_INTERACTION_IN_POWER.append(interaction_in_power_arr)
                self.valid_INTERACTION_COEFF.append(interaction_coeff_arr)
                self.valid_INTERACTION_OUT_POWER.append(interaction_out_power_arr)
                self.valid_INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
                self.valid_INTERACTION_BULK.append(interaction_bulk_arr)
                self.valid_MESH_CELL_ID.append(mesh_cell_id_arr)
                self.valid_MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
                self.valid_MESH_FACE_ID.append(mesh_face_id_arr)
                self.valid_MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
                self.valid_MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
                self.valid_MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
                self.valid_VOLUME_ID.append(volume_id_arr)
                self.valid_MEDIA_IN.append(media_in_arr)
                self.valid_MEDIA_OUT.append(media_out_arr)
                self.valid_MEDIA_TRANSITION.append(media_transition_arr)
                self.valid_MEDIA_STATE_METHOD.append(media_state_method_arr)
                self.valid_MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
                self.valid_INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
                self.valid_INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)
            else:
                self.invalid_SURFACE.append(surface_arr)
                self.invalid_NAME.append(name_arr)
                self.invalid_GLASS.append(glass_arr)
                self.invalid_S_XYZ.append(s_xyz_arr)
                self.invalid_T_XYZ.append(t_xyz_arr)
                self.invalid_XYZ.append(xyz_arr)
                self.invalid_OST_XYZ.append(ost_xyz_arr)
                self.invalid_OST_LMN.append(ost_lmn_arr)
                self.invalid_S_LMN.append(s_lmn_arr)
                self.invalid_LMN.append(lmn_arr)
                self.invalid_R_LMN.append(r_lmn_arr)
                self.invalid_N0.append(n0_arr)
                self.invalid_N1.append(n1_arr)
                self.invalid_WAV.append(wav_val)
                self.invalid_G_LMN.append(g_lmn_arr)
                self.invalid_ORDER.append(order_arr)
                self.invalid_GRATING.append(grating_arr)
                self.invalid_DISTANCE.append(dist_arr)
                self.invalid_OP.append(op_arr)
                self.invalid_TOP_S.append(top_s_arr)
                self.invalid_TOP.append(top_val)
                self.invalid_ALPHA.append(alpha_arr)
                self.invalid_BULK_TRANS.append(bulk_trans_arr)
                self.invalid_RP.append(rp_arr)
                self.invalid_RS.append(rs_arr)
                self.invalid_TP.append(tp_arr)
                self.invalid_TS.append(ts_arr)
                self.invalid_TTBE.append(ttbe_arr)
                self.invalid_TT.append(tt_val)
                self.invalid_INTERACTION_TYPE.append(interaction_type_arr)
                self.invalid_INTERACTION_MODEL.append(interaction_model_arr)
                self.invalid_INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
                self.invalid_INTERACTION_IN_POWER.append(interaction_in_power_arr)
                self.invalid_INTERACTION_COEFF.append(interaction_coeff_arr)
                self.invalid_INTERACTION_OUT_POWER.append(interaction_out_power_arr)
                self.invalid_INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
                self.invalid_INTERACTION_BULK.append(interaction_bulk_arr)
                self.invalid_MESH_CELL_ID.append(mesh_cell_id_arr)
                self.invalid_MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
                self.invalid_MESH_FACE_ID.append(mesh_face_id_arr)
                self.invalid_MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
                self.invalid_MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
                self.invalid_MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
                self.invalid_VOLUME_ID.append(volume_id_arr)
                self.invalid_MEDIA_IN.append(media_in_arr)
                self.invalid_MEDIA_OUT.append(media_out_arr)
                self.invalid_MEDIA_TRANSITION.append(media_transition_arr)
                self.invalid_MEDIA_STATE_METHOD.append(media_state_method_arr)
                self.invalid_MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
                self.invalid_INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
                self.invalid_INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)

            # General lists (always appended)
            self.nrays += 1
            self.RayWave.append(wave)
            self.CC.append(ray_arr)
            self.SURFACE.append(surface_arr)
            self.NAME.append(name_arr)
            self.GLASS.append(glass_arr)
            self.S_XYZ.append(s_xyz_arr)
            self.T_XYZ.append(t_xyz_arr)
            self.XYZ.append(xyz_arr)
            self.OST_XYZ.append(ost_xyz_arr)
            self.OST_LMN.append(ost_lmn_arr)
            self.S_LMN.append(s_lmn_arr)
            self.LMN.append(lmn_arr)
            self.R_LMN.append(r_lmn_arr)
            self.N0.append(n0_arr)
            self.N1.append(n1_arr)
            self.WAV.append(wav_val)
            self.G_LMN.append(g_lmn_arr)
            self.ORDER.append(order_arr)
            self.GRATING.append(grating_arr)
            self.DISTANCE.append(dist_arr)
            self.OP.append(op_arr)
            self.TOP_S.append(top_s_arr)
            self.TOP.append(top_val)
            self.ALPHA.append(alpha_arr)
            self.BULK_TRANS.append(bulk_trans_arr)
            self.RP.append(rp_arr)
            self.RS.append(rs_arr)
            self.TP.append(tp_arr)
            self.TS.append(ts_arr)
            self.TTBE.append(ttbe_arr)
            self.TT.append(tt_val)
            self.INTERACTION_TYPE.append(interaction_type_arr)
            self.INTERACTION_MODEL.append(interaction_model_arr)
            self.INTERACTION_TARGET_SURFACE.append(interaction_target_arr)
            self.INTERACTION_IN_POWER.append(interaction_in_power_arr)
            self.INTERACTION_COEFF.append(interaction_coeff_arr)
            self.INTERACTION_OUT_POWER.append(interaction_out_power_arr)
            self.INTERACTION_LOSS_POWER.append(interaction_loss_power_arr)
            self.INTERACTION_BULK.append(interaction_bulk_arr)
            self.MESH_CELL_ID.append(mesh_cell_id_arr)
            self.MESH_ORIGINAL_CELL_ID.append(mesh_original_cell_id_arr)
            self.MESH_FACE_ID.append(mesh_face_id_arr)
            self.MESH_FACE_MATCH_METHOD.append(mesh_face_match_method_arr)
            self.MESH_FACE_MATCH_SCORE.append(mesh_face_match_score_arr)
            self.MESH_FACE_MATCH_WARNING.append(mesh_face_match_warning_arr)
            self.VOLUME_ID.append(volume_id_arr)
            self.MEDIA_IN.append(media_in_arr)
            self.MEDIA_OUT.append(media_out_arr)
            self.MEDIA_TRANSITION.append(media_transition_arr)
            self.MEDIA_STATE_METHOD.append(media_state_method_arr)
            self.MEDIA_STATE_DIAGNOSTIC.append(media_state_diagnostic_arr)
            self.INSIDE_VOLUMES_BEFORE.append(inside_volumes_before_arr)
            self.INSIDE_VOLUMES_AFTER.append(inside_volumes_after_arr)
            metadata = metadata_seq[i] if i < len(metadata_seq) else {
                "source_xyz": ray_arr[0] if ray_arr.shape[0] else None,
                "source_lmn": d.get("LMN", [None])[0] if d.get("LMN") else None,
                "source_wavelength": wave,
            }
            self._append_source_metadata(self._launch_count, data=d, metadata=metadata)
            self.BRANCH_ID.append(np.asarray(0))
            self.PARENT_BRANCH_ID.append(np.asarray(-1))
            self.BRANCH_POWER.append(tt_val)
            self.BRANCH_PHASE.append(np.asarray(0.0))
            self.BRANCH_LABEL.append(np.asarray("primary"))
            self.BRANCH_PATH.append(np.asarray("primary"))
            self.BRANCH_TERMINATION_REASON.append(np.asarray(""))
            self.BRANCH_TERMINATION_DIAGNOSTIC.append(np.asarray(""))
            self.BRANCH_TREE_DIAGNOSTIC.append(np.asarray(""))
            self.BRANCH_JONES_P.append(np.asarray(complex(1.0, 0.0)))
            self.BRANCH_JONES_S.append(np.asarray(complex(0.0, 0.0)))
            self.BRANCH_POLARIZATION_XYZ.append(self._metadata_vector((1.0, 0.0, 0.0), dtype=np.complex128))
            self.BRANCH_FINAL_MEDIA.append(self._metadata_text(""))
            self.BRANCH_FINAL_INDEX.append(self._metadata_float(np.nan))
            self.BRANCH_FINAL_INSIDE_VOLUMES.append(self._metadata_text(""))
            self.BRANCH_FINAL_MEDIA_STATE_METHOD.append(self._metadata_text(""))
            self._append_trace_event_records(self.nrays - 1)
            self._launch_count += 1

    def pick(self, N_ELEMENT=(- 1), coordinates = "global"):
        """pick.

        Parameters
        ----------
        N_ELEMENT :
            N_ELEMENT

            coordinates = "global" or "local"
        """

        gls = self.SYSTEM.SDT[N_ELEMENT].Glass
        if gls == "NULL":
            print("NULL surface has been chosen, the return values correspond to those of the previous surface")

        self.numsup = (self.nelements - 1)

        if coordinates == "global":
            self.xyz = self.valid_XYZ
            self.lmn = self.valid_LMN
        else:
            self.xyz = self.valid_OST_XYZ
            self.lmn = self.valid_OST_LMN

        self.s = self.valid_SURFACE
        if ((N_ELEMENT < 0) or (N_ELEMENT > self.numsup)):
            N_ELEMENT = self.numsup
        else:
            N_ELEMENT = N_ELEMENT
        # AA = []
        BB = []
        for k in self.s:
            aa = np.argwhere((k == N_ELEMENT))
            aa = np.squeeze(aa)
            # print(aa)
            # AA.append(aa)
            BB.append(np.size(aa))
        # AA = np.asarray(AA)
        BB = np.asarray(BB)
        if (N_ELEMENT != 0):
            BB = np.argwhere((BB == 1))
        else:
            BB = np.argwhere((BB == 0))
        X = []
        Y = []
        Z = []
        L = []
        M = []
        N = []
        for c in BB:
            for d in c:
                ray0 = self.xyz[d]

                [x1, y1, z1] = ray0[N_ELEMENT]
                X.append(x1)
                Y.append(y1)
                Z.append(z1)
                ray1 = self.lmn[d]
                if (N_ELEMENT != 0):
                    el = (N_ELEMENT - 1)
                else:
                    el = 0
                [l1, m1, n1] = ray1[el]
                L.append(l1)
                M.append(m1)
                N.append(n1)
        return (np.asarray(X), np.asarray(Y), np.asarray(Z), np.asarray(L), np.asarray(M), np.asarray(N))
