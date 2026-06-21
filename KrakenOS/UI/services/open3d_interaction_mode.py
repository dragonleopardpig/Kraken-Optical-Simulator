"""Centralised interaction-mode model.

Ports Slicer's ``vtkMRMLInteractionNode`` idea: a single source of truth
for "what is the user currently doing?", separate from per-widget state.
Slicer uses the node to coordinate widgets across views (only the active
mode handles input); KrakenOS has one 3D view but still benefits from the
single observable mode because today the inspector keeps ten different
booleans (``_source_target_pick_mode``, ``_center_row_to_ray_mode``, ...)
that have to be reset in lock-step every time the user cancels.

Phase 4 keeps the existing booleans intact and adds an ``InteractionMode``
enum plus ``derive_interaction_mode(inspector)`` so observers can react
to a single value. Phase 5 will route the boolean reads/writes through
``InteractionModeState`` and remove the duplicated reset bookkeeping.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Callable


class InteractionMode(str, Enum):
    IDLE = "idle"
    SOURCE_TARGET = "source_target"
    CENTER_ROW_TO_RAY = "center_row_to_ray"
    PLACEMENT_TARGET = "placement_target"
    PLACEMENT_ORIENT = "placement_orient"
    PLACEMENT_ORIENT_RAY = "placement_orient_ray"
    STEP_CARRY_SNAP_RAY = "step_carry_snap_ray"
    STEP_CARRY_SNAP_TARGET = "step_carry_snap_target"
    STEP_NORMAL_AXIS_PICK = "step_normal_axis_pick"
    STEP_SURFACE_CENTER_AXIS_PICK = "step_surface_center_axis_pick"
    STEP_CARRY_HOLD = "step_carry_hold"
    ROW_CARRY_HOLD = "row_carry_hold"
    AXIS_SLIDE = "axis_slide"
    CAD_AXIS_PICK = "cad_axis_pick"
    MEASURE = "measure"  # CAD-style 2-point measure tool (pick two edges/surfaces -> draggable dimension)


ModeObserver = Callable[["InteractionModeState"], None]


class InteractionModeState:
    """Observable single mode value."""

    def __init__(self, initial: InteractionMode = InteractionMode.IDLE) -> None:
        self._mode = initial
        self._observers: list[ModeObserver] = []

    @property
    def mode(self) -> InteractionMode:
        return self._mode

    def set_mode(self, mode: InteractionMode) -> None:
        if mode == self._mode:
            return
        self._mode = mode
        for callback in list(self._observers):
            try:
                callback(self)
            except Exception:
                continue

    def add_observer(self, callback: ModeObserver) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: ModeObserver) -> None:
        try:
            self._observers.remove(callback)
        except ValueError:
            pass


def derive_interaction_mode(inspector: Any) -> InteractionMode:
    """Inspect the current inspector booleans and return one mode value.

    Order matters: when more than one flag is true (the state machine is
    transiently inconsistent during cleanup), pick whichever was most
    recently entered. Today's call sites set/reset in a deterministic
    order, so the picks here mirror that order.
    """
    if bool(getattr(inspector, "_measure_pick_mode", False)):
        return InteractionMode.MEASURE
    if bool(getattr(inspector, "_step_normal_axis_pick_mode", False)):
        return InteractionMode.STEP_NORMAL_AXIS_PICK
    if bool(getattr(inspector, "_step_surface_center_axis_pick_mode", False)):
        return InteractionMode.STEP_SURFACE_CENTER_AXIS_PICK
    if bool(getattr(inspector, "_step_carry_snap_ray_mode", False)):
        return InteractionMode.STEP_CARRY_SNAP_RAY
    if bool(getattr(inspector, "_step_carry_snap_target_mode", False)):
        return InteractionMode.STEP_CARRY_SNAP_TARGET
    if bool(getattr(inspector, "_placement_orient_ray_mode", False)):
        return InteractionMode.PLACEMENT_ORIENT_RAY
    if bool(getattr(inspector, "_placement_orient_pick_mode", False)):
        return InteractionMode.PLACEMENT_ORIENT
    if bool(getattr(inspector, "_placement_target_pick_mode", False)):
        return InteractionMode.PLACEMENT_TARGET
    if bool(getattr(inspector, "_center_row_to_ray_mode", False)):
        return InteractionMode.CENTER_ROW_TO_RAY
    if bool(getattr(inspector, "_source_target_pick_mode", False)):
        return InteractionMode.SOURCE_TARGET
    editor = getattr(inspector, "editor", None)
    if editor is not None and bool(getattr(editor, "_cad_axis_pick_any", False)):
        return InteractionMode.CAD_AXIS_PICK
    if getattr(inspector, "_step_carry_hold_after_id", None) is not None:
        return InteractionMode.STEP_CARRY_HOLD
    if getattr(inspector, "_row_carry_hold_after_id", None) is not None:
        return InteractionMode.ROW_CARRY_HOLD
    if getattr(inspector, "_axis_slide_drag_state", None) is not None:
        return InteractionMode.AXIS_SLIDE
    return InteractionMode.IDLE


def any_pick_mode_active(inspector: Any) -> bool:
    """Convenience for the ``_*_pick_mode`` or-ladder seen in handlers."""
    return derive_interaction_mode(inspector) != InteractionMode.IDLE
