"""Structured interaction-event abstraction.

Ports Slicer's ``vtkMRMLInteractionEventData`` idea: wrap a raw VTK input
event with the pre-resolved context (display xy, world xyz, picked actor,
classified pick target, modifier keys) so downstream handlers can branch
on intent instead of re-running the picker and checking modifier bits in
half a dozen places.

The companion ``PickClassifier`` looks the picked actor key up across the
inspector's various ``_actor_*_map`` dicts and reports a single
``PickTarget`` that names what the user actually grabbed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PickTarget(str, Enum):
    """What the user picked, normalised across actor-map kinds."""

    NONE = "none"
    ROW = "row"
    STEP_OVERLAY = "step_overlay"
    STEP_ROTATE_HANDLE = "step_rotate_handle"
    PLACEMENT_TRANSLATE = "placement_translate"
    PLACEMENT_ROTATE = "placement_rotate"
    PLACEMENT_VISUAL = "placement_visual"
    THICKNESS_DIMENSION = "thickness_dimension"
    RAY = "ray"
    OPTICAL_AXIS = "optical_axis"
    FOLLOW_VISUAL = "follow_visual"


@dataclass
class InteractionEventData:
    """Pre-resolved input-event payload for the inspector handlers.

    All optional fields default to ``None`` / empty so call sites can
    construct partial events (e.g. a key press without a picker hit).
    """

    event_type: str = ""
    display_xy: tuple[float, float] | None = None
    world_xyz: tuple[float, float, float] | None = None
    actor: Any = None
    actor_key: str | None = None
    cell_id: int | None = None
    pick_target: PickTarget = PickTarget.NONE
    target_payload: Any = None
    modifier_keys: frozenset[str] = field(default_factory=frozenset)
    raw_event: Any = None

    @property
    def shift(self) -> bool:
        return "shift" in self.modifier_keys

    @property
    def ctrl(self) -> bool:
        return "ctrl" in self.modifier_keys

    @property
    def alt(self) -> bool:
        return "alt" in self.modifier_keys


class PickClassifier:
    """Resolve a picked actor key to a ``PickTarget`` and payload."""

    def __init__(self, inspector: Any) -> None:
        self._inspector = inspector

    def classify(self, actor_key: str | None) -> tuple[PickTarget, Any]:
        if actor_key is None:
            return PickTarget.NONE, None
        inspector = self._inspector
        rotate = inspector._actor_step_rotate_map.get(actor_key)
        if rotate is not None:
            return PickTarget.STEP_ROTATE_HANDLE, rotate
        if actor_key in getattr(inspector, "_actor_step_rotate_visual_keys", set()):
            return PickTarget.STEP_ROTATE_HANDLE, None
        placement_rotate = inspector._actor_placement_rotate_map.get(actor_key)
        if placement_rotate is not None:
            return PickTarget.PLACEMENT_ROTATE, placement_rotate
        if actor_key in getattr(inspector, "_actor_placement_rotate_visual_keys", set()):
            return PickTarget.PLACEMENT_VISUAL, None
        placement_move = inspector._actor_placement_move_map.get(actor_key)
        if placement_move is not None:
            return PickTarget.PLACEMENT_TRANSLATE, placement_move
        if actor_key in getattr(inspector, "_actor_placement_move_visual_keys", set()):
            return PickTarget.PLACEMENT_VISUAL, None
        thickness_row = inspector._actor_thickness_dimension_map.get(actor_key)
        if thickness_row is not None:
            return PickTarget.THICKNESS_DIMENSION, int(thickness_row)
        step_label = inspector._actor_step_map.get(actor_key)
        if step_label is not None:
            return PickTarget.STEP_OVERLAY, step_label
        follow_label = inspector._actor_step_follow_map.get(actor_key)
        if follow_label is not None:
            return PickTarget.FOLLOW_VISUAL, follow_label
        row_index = inspector._actor_row_map.get(actor_key)
        if row_index is not None:
            try:
                return PickTarget.ROW, int(row_index)
            except Exception:
                return PickTarget.ROW, None
        ray_index = inspector._actor_ray_map.get(actor_key)
        if ray_index is not None:
            try:
                return PickTarget.RAY, int(ray_index)
            except Exception:
                return PickTarget.RAY, None
        axis_info = inspector._actor_optical_axis_map.get(actor_key)
        if axis_info is not None:
            return PickTarget.OPTICAL_AXIS, axis_info
        return PickTarget.NONE, None


def modifier_keys_from_tk_state(state: int | None) -> frozenset[str]:
    """Translate a Tk event-state bitmask into the keys used by the dataclass."""
    if state is None:
        return frozenset()
    try:
        bits = int(state)
    except (TypeError, ValueError):
        return frozenset()
    keys: set[str] = set()
    if bits & 0x0001:
        keys.add("shift")
    if bits & 0x0004:
        keys.add("ctrl")
    if bits & 0x0008 or bits & 0x20000:
        keys.add("alt")
    return frozenset(keys)
