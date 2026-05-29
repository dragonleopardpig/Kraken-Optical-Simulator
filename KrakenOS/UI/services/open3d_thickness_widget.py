"""ThicknessDimensionWidget -- first concrete AbstractWidget migration.

Wraps the existing inline thickness-dimension click handler in
``Open3DInteractionService._on_left_button_press`` so we can demonstrate
the full Slicer-pattern pipeline (InteractionEventData + PickClassifier
+ AbstractWidget + WidgetRegistry) end-to-end on a single behaviour.

Behavior parity: identical to the inline ladder it replaces. If an
interaction mode is already active, the widget shows the same status
message and consumes the event without opening the editor; otherwise it
calls ``_edit_open3d_thickness_dimension`` on the inspector exactly as
before.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.services.open3d_abstract_widget import (
    AbstractWidget,
    WidgetState,
    WIDGET_BID_NONE,
)
from KrakenOS.UI.services.open3d_interaction_event import InteractionEventData, PickTarget
from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode


class ThicknessDimensionWidget(AbstractWidget):
    """Open the inline thickness editor when the user clicks a dimension."""

    BID = 0.4

    def can_process(self, event: InteractionEventData) -> float:
        if event.event_type != "mouse_press":
            return WIDGET_BID_NONE
        if event.pick_target != PickTarget.THICKNESS_DIMENSION:
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
                inspector.status_var.set("Thickness dimension: finish the active pick mode first.")
                inspector.render()
            except Exception:
                pass
            self.set_state(WidgetState.IDLE)
            return True
        row_index = event.target_payload
        if row_index is None:
            return False
        try:
            self.set_state(WidgetState.PROCESSING)
            inspector._edit_open3d_thickness_dimension(int(row_index))
            inspector.render()
        except Exception:
            self.set_state(WidgetState.IDLE)
            return False
        self.set_state(WidgetState.IDLE)
        return True
