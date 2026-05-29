"""Concrete AbstractWidget subclasses for the placement handles.

Phase 7 migrates the two placement handle ladders in
``Open3DInteractionService._on_left_button_press`` onto the AbstractWidget
pipeline. Behaviour is preserved exactly:

  * When an interaction mode is active, the click still produces the
    "Placement handle: finish the active pick mode first." status and
    consumes the event.
  * Otherwise the widget calls the existing
    ``_apply_scene_placement_*_handle`` inspector methods unchanged.
"""

from __future__ import annotations

from KrakenOS.UI.services.open3d_abstract_widget import (
    AbstractWidget,
    WidgetState,
    WIDGET_BID_NONE,
)
from KrakenOS.UI.services.open3d_interaction_event import InteractionEventData, PickTarget
from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode


_PLACEMENT_STATUS = "Placement handle: finish the active pick mode first."


def _block_if_busy(inspector) -> bool:
    """True if the inspector is mid-pick and the placement click should be blocked."""
    try:
        mode = inspector.current_interaction_mode()
    except Exception:
        return False
    return mode != InteractionMode.IDLE


class PlacementRotateWidget(AbstractWidget):
    BID = 0.3

    def can_process(self, event: InteractionEventData) -> float:
        if event.event_type != "mouse_press":
            return WIDGET_BID_NONE
        if event.pick_target != PickTarget.PLACEMENT_ROTATE:
            return WIDGET_BID_NONE
        return self.BID

    def process(self, event: InteractionEventData) -> bool:
        inspector = self._inspector
        if _block_if_busy(inspector):
            try:
                inspector.status_var.set(_PLACEMENT_STATUS)
                inspector.render()
            except Exception:
                pass
            return True
        payload = event.target_payload
        if payload is None:
            return False
        try:
            self.set_state(WidgetState.PROCESSING)
            inspector._apply_scene_placement_rotate_handle(*payload)
            inspector.render()
        except Exception:
            self.set_state(WidgetState.IDLE)
            return False
        self.set_state(WidgetState.IDLE)
        return True


class PlacementTranslateWidget(AbstractWidget):
    BID = 0.3

    def can_process(self, event: InteractionEventData) -> float:
        if event.event_type != "mouse_press":
            return WIDGET_BID_NONE
        if event.pick_target != PickTarget.PLACEMENT_TRANSLATE:
            return WIDGET_BID_NONE
        return self.BID

    def process(self, event: InteractionEventData) -> bool:
        inspector = self._inspector
        if _block_if_busy(inspector):
            try:
                inspector.status_var.set(_PLACEMENT_STATUS)
                inspector.render()
            except Exception:
                pass
            return True
        payload = event.target_payload
        if payload is None:
            return False
        try:
            self.set_state(WidgetState.PROCESSING)
            inspector._apply_scene_placement_translate_handle(*payload)
            inspector.render()
        except Exception:
            self.set_state(WidgetState.IDLE)
            return False
        self.set_state(WidgetState.IDLE)
        return True
