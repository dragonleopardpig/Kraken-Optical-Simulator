"""Kernel-side trace event records.

These records are intentionally independent of UI scene dataclasses.  RayKeeper
emits them at the trace boundary, and UI/export code can convert them into
display-specific records without losing the original trace provenance.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any

import numpy as np


TRACE_EVENT_SOURCE_RAYKEEPER = "raykeeper_trace_events"
TRACE_EVENT_KIND_SURFACE = "surface"
TRACE_EVENT_KIND_TERMINAL = "terminal"

__all__ = [
    "TRACE_EVENT_SOURCE_RAYKEEPER",
    "TRACE_EVENT_KIND_SURFACE",
    "TRACE_EVENT_KIND_TERMINAL",
    "TraceEventRecord",
    "trace_event_to_record",
]


def _nan_vector() -> list[float]:
    return [float(np.nan), float(np.nan), float(np.nan)]


def _empty_int_list() -> list[int]:
    return []


@dataclass(slots=True)
class TraceEventRecord:
    """One trace-boundary event emitted by RayKeeper."""

    event_id: str = ""
    event_source: str = TRACE_EVENT_SOURCE_RAYKEEPER
    event_kind: str = TRACE_EVENT_KIND_SURFACE
    event_type: str = ""
    ray_index: int = 0
    source_ray_index: int | None = None
    source_id: str = ""
    source_name: str = ""
    source_role: str = ""
    source_model: str = ""
    wavelength: float | None = None
    branch_id: int = 0
    branch_path: str = ""
    branch_power: float | None = None
    branch_phase_deg: float | None = None
    step: int = 0
    surface_id: int | None = None
    surface_name: str = ""
    material: str = ""
    point_world: list[float] = field(default_factory=_nan_vector)
    incoming_direction: list[float] = field(default_factory=_nan_vector)
    outgoing_direction: list[float] = field(default_factory=_nan_vector)
    surface_normal: list[float] = field(default_factory=_nan_vector)
    n0: float | None = None
    n1: float | None = None
    distance: float | None = None
    optical_path: float | None = None
    rp: float | None = None
    rs: float | None = None
    tp: float | None = None
    ts: float | None = None
    ttbe: float | None = None
    interaction_model: str = ""
    interaction_target_surface: int | None = None
    interaction_in_power: float | None = None
    interaction_coeff: float | None = None
    interaction_out_power: float | None = None
    interaction_loss_power: float | None = None
    interaction_bulk: float | None = None
    volume_id: str = ""
    media_in: str = ""
    media_out: str = ""
    media_transition: str = ""
    media_state_method: str = ""
    media_state_diagnostic: str = ""
    inside_volumes_before: str = ""
    inside_volumes_after: str = ""
    mesh_cell_id: int | None = None
    mesh_original_cell_id: int | None = None
    mesh_face_id: str = ""
    mesh_face_match_method: str = ""
    mesh_face_match_score: float | None = None
    mesh_face_match_warning: str = ""
    termination_reason: str = ""
    terminal_target_surface: int | None = None
    terminal_detector_surfaces: list[int] = field(default_factory=_empty_int_list)
    terminal_policy_source: str = ""
    reaches_target: bool = False
    reaches_detector: bool = False
    diagnostic: str = ""

    def to_record(self) -> dict[str, Any]:
        """Return a plain mapping for CSV/UI adapters."""
        return {item.name: getattr(self, item.name) for item in fields(self)}

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        if not hasattr(self, key):
            raise KeyError(key)
        return getattr(self, key)


def trace_event_to_record(event: Any) -> dict[str, Any]:
    """Normalize typed and legacy trace-event records to a dictionary."""
    if isinstance(event, TraceEventRecord):
        return event.to_record()
    to_record = getattr(event, "to_record", None)
    if callable(to_record):
        try:
            record = to_record()
            if isinstance(record, dict):
                return dict(record)
        except Exception:
            return {}
    if isinstance(event, dict):
        return dict(event)
    return {}
