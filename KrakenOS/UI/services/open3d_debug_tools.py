"""Debug and timing helpers for the Open 3D inspector."""

from __future__ import annotations

import json
import time

import numpy as np

from KrakenOS.UI.services.open3d_timing import (
    open3d_timing_event,
    open3d_timing_log_path,
    open3d_timing_span,
)
from KrakenOS.UI.services.optical_solid_geometry import (
    OPTICAL_SOLID_FACE_FUNCTION_DEFAULT,
    _normalize_optical_solid_face_function,
    _normalize_optical_solid_face_port_role,
)


def _short_debug_error(exc: Exception, limit: int = 220) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    text = " ".join(text.split())
    if len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "..."
    return text


class Open3DDebugToolsMixin:
    """Mixin for Open 3D structured debug traces and timing spans."""

    @staticmethod
    def _debug_vector(value, *, digits: int = 6):
        try:
            array = np.asarray(value, dtype=float).reshape(-1)
        except Exception:
            return None
        if array.size <= 0 or not np.all(np.isfinite(array)):
            return None
        return [round(float(item), digits) for item in array[:3]]

    def _debug_mode_state(self) -> dict[str, object]:
        return {
            "source_target": bool(self._source_target_pick_mode),
            "center_row_axis": bool(self._center_row_to_ray_mode),
            "center_row_index": self._center_row_to_ray_index,
            "placement_target": bool(self._placement_target_pick_mode),
            "placement_orient": bool(self._placement_orient_pick_mode),
            "placement_orient_ray": bool(self._placement_orient_ray_mode),
            "step_normal_axis": bool(self._step_normal_axis_pick_mode),
            "step_carry": self._step_carry_label(),
            "step_follow": self._step_carry_follow_state is not None,
            "step_drag": self._step_carry_drag_state is not None,
            "thickness_drag": self._thickness_drag_state is not None,
            "step_snap_ray": bool(self._step_carry_snap_ray_mode),
            "step_snap_target": bool(self._step_carry_snap_target_mode),
            "cad_axis_pick": bool(getattr(self.editor, "_cad_axis_pick_any", False)),
            "cad_axis_label": getattr(self.editor, "_cad_axis_pick_label", None),
            "step_surface_center_axis": bool(self._step_surface_center_axis_pick_mode),
        }

    def _debug_actor_counts(self) -> dict[str, object]:
        view_props = None
        try:
            if self._renderer is not None:
                view_props = int(self._renderer.GetViewProps().GetNumberOfItems())
        except Exception:
            view_props = None
        return {
            "view_props": view_props,
            "actors_by_key": len(getattr(self, "_actor_by_key", {}) or {}),
            "row_actor_rows": sorted(int(row) for row in getattr(self, "_row_actor_map", {}) or {}),
            "row_actor_count": sum(len(items) for items in (getattr(self, "_row_actor_map", {}) or {}).values()),
            "ray_actors": len(getattr(self, "_actor_ray_map", {}) or {}),
            "axis_actors": len(getattr(self, "_actor_optical_axis_map", {}) or {}),
            "step_actor_labels": {
                str(label): len(items)
                for label, items in sorted((getattr(self, "_step_actor_map", {}) or {}).items())
            },
            "step_rotate_handles": len(getattr(self, "_actor_step_rotate_map", {}) or {}),
            "placement_move_handles": len(getattr(self, "_actor_placement_move_map", {}) or {}),
            "placement_rotate_handles": len(getattr(self, "_actor_placement_rotate_map", {}) or {}),
            "thickness_dimension_actors": len(getattr(self, "_actor_thickness_dimension_map", {}) or {}),
            "thickness_dimension_drag_actors": len(getattr(self, "_thickness_dimension_drag_map", {}) or {}),
            "show_rays": bool(self.show_rays_var.get()),
            "selected_step": getattr(self.editor, "_selected_step_label", None),
            "picked_row": self._picked_row_index,
            "picked_axis": self._picked_optical_axis_id,
        }

    def _debug_face_metadata_summary(self, metadata: object) -> dict[str, object]:
        faces = list(metadata.get("faces", []) or []) if isinstance(metadata, dict) else []
        function_counts: dict[str, int] = {}
        role_counts: dict[str, int] = {}
        port_counts: dict[str, int] = {}
        assigned = 0
        for face in faces:
            if not isinstance(face, dict):
                continue
            function = _normalize_optical_solid_face_function(face.get("function"), legacy_role=face.get("role"))
            role = str(face.get("role", "") or "")
            port_role = _normalize_optical_solid_face_port_role(face.get("port_role"))
            function_counts[function] = function_counts.get(function, 0) + 1
            role_counts[role] = role_counts.get(role, 0) + 1
            port_counts[port_role] = port_counts.get(port_role, 0) + 1
            if function != OPTICAL_SOLID_FACE_FUNCTION_DEFAULT:
                assigned += 1
        return {
            "faces": len(faces),
            "assigned_faces": assigned,
            "function_counts": function_counts,
            "role_counts": role_counts,
            "port_counts": port_counts,
        }

    def _debug_trace(self, event: str, **fields: object) -> None:
        try:
            self._open3d_debug_seq = int(getattr(self, "_open3d_debug_seq", 0) or 0) + 1
            payload = {
                "seq": self._open3d_debug_seq,
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "event": str(event),
                **fields,
            }
            text = json.dumps(payload, sort_keys=True, default=str)
        except Exception as exc:
            text = f'{{"event": "{event}", "debug_error": "{_short_debug_error(exc)}"}}'
        try:
            self.editor.append_debug(f"Open3DTrace {text}")
        except Exception:
            pass

    def _timing_event(self, event: str, **fields: object) -> None:
        try:
            open3d_timing_event(
                event,
                counts=self._debug_actor_counts(),
                modes=self._debug_mode_state(),
                **fields,
            )
        except Exception:
            pass

    def _timing_start(self, event: str, **fields: object) -> dict[str, object]:
        token = {"event": str(event), "start": time.perf_counter(), "fields": dict(fields)}
        self._timing_event(f"{event}_start", **fields)
        return token

    def _timing_finish(self, token: dict[str, object] | None, **fields: object) -> None:
        if not isinstance(token, dict):
            return
        try:
            duration_ms = (time.perf_counter() - float(token.get("start", time.perf_counter()))) * 1000.0
        except Exception:
            duration_ms = 0.0
        base_fields = token.get("fields", {})
        if not isinstance(base_fields, dict):
            base_fields = {}
        event = str(token.get("event", "open3d_action"))
        payload = {**base_fields, **fields, "duration_ms": round(float(duration_ms), 3)}
        self._timing_event(f"{event}_done", **payload)
        try:
            slow_ms = float(getattr(self, "_open3d_timing_slow_ms", 100.0) or 100.0)
        except Exception:
            slow_ms = 100.0
        if duration_ms >= slow_ms:
            try:
                self.editor.append_debug(
                    f"Open3DTiming slow {event}: {duration_ms:.1f} ms "
                    f"(log: {open3d_timing_log_path()})"
                )
            except Exception:
                pass

    def _timing_span(self, event: str, **fields: object):
        return open3d_timing_span(event, **fields)

    def _debug_pick_payload(self, actor_key: str | None, *, x: int | None = None, y: int | None = None) -> dict[str, object]:
        cell_id = None
        pick_world = None
        try:
            cell_id = int(self._picker.GetCellId()) if self._picker is not None else None
        except Exception:
            cell_id = None
        try:
            pick_world = self._debug_vector(self._picker.GetPickPosition()) if self._picker is not None else None
        except Exception:
            pick_world = None
        axis_info = self._actor_optical_axis_map.get(actor_key) if actor_key is not None else None
        return {
            "x": x,
            "y": y,
            "actor_key": actor_key,
            "cell_id": cell_id,
            "pick_world": pick_world,
            "row_index": self._actor_row_map.get(actor_key) if actor_key is not None else None,
            "ray_index": self._ray_index_for_actor(actor_key, cell_id),  # bugs/0223: merged cell -> ray
            "step_label": self._actor_step_map.get(actor_key) if actor_key is not None else None,
            "axis_id": axis_info.get("axis_id") if isinstance(axis_info, dict) else None,
            "step_rotate": self._actor_step_rotate_map.get(actor_key) if actor_key is not None else None,
            "placement_move": self._actor_placement_move_map.get(actor_key) if actor_key is not None else None,
            "placement_rotate": self._actor_placement_rotate_map.get(actor_key) if actor_key is not None else None,
            "thickness_dimension_row": self._actor_thickness_dimension_map.get(actor_key) if actor_key is not None else None,
        }

