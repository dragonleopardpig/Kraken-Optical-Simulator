"""StepRotationWidget -- migrate the STEP rotation handle click ladder."""

from __future__ import annotations

from KrakenOS.UI.services.open3d_abstract_widget import (
    AbstractWidget,
    WidgetState,
    WIDGET_BID_NONE,
)
from KrakenOS.UI.services.open3d_interaction_event import InteractionEventData, PickTarget
from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode


_BUSY_STATUS = "STEP rotation handle: finish the active pick mode first."


class StepRotationHandleWidget(AbstractWidget):
    BID = 0.25

    def can_process(self, event: InteractionEventData) -> float:
        if event.event_type != "mouse_press":
            return WIDGET_BID_NONE
        if event.pick_target != PickTarget.STEP_ROTATE_HANDLE:
            return WIDGET_BID_NONE
        return self.BID

    def process(self, event: InteractionEventData) -> bool:
        inspector = self._inspector
        try:
            mode = inspector.current_interaction_mode()
        except Exception:
            mode = InteractionMode.IDLE
        if mode != InteractionMode.IDLE:
            try:
                inspector.status_var.set(_BUSY_STATUS)
                inspector.render()
            except Exception:
                pass
            return True
        payload = event.target_payload
        if payload is None:
            # Visual-only handle actor (gizmo decoration without an action
            # tuple). Don't consume so the click can fall through to the
            # legacy ladder / row picker, matching pre-widget behaviour.
            return False
        try:
            self.set_state(WidgetState.PROCESSING)
            inspector._apply_step_rotation_handle(*payload)
            inspector.render()
        except Exception:
            self.set_state(WidgetState.IDLE)
            return False
        self.set_state(WidgetState.IDLE)
        return True
