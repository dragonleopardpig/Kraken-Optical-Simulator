"""AbstractWidget base + WidgetRegistry.

Ports Slicer's ``vtkMRMLAbstractWidget`` interaction contract to KrakenOS.

Slicer pattern:
  * Each interactive thing (markups handle, ROI corner, transform gizmo)
    is a ``vtkMRMLAbstractWidget`` subclass that owns a representation,
    answers ``CanProcessInteractionEvent(eventData) -> distance`` to bid
    on input, and consumes the event via ``ProcessInteractionEvent`` if
    its bid wins.
  * A ``WidgetRegistry`` (the displayable manager in Slicer parlance)
    holds the list of active widgets and routes a single event to the
    lowest-distance bidder.

In KrakenOS the inspector currently does this inline -- ``_on_left_button_press``
checks the actor key against ten dicts and dispatches to one of a dozen
``_apply_*_handle`` methods. Phase 5 lands the abstract contract so the
existing handlers can be refactored into widgets in later phases without
breaking call-site behavior in the meantime.

Compatibility:
  * The base class is intentionally Python-only (no vtkObject inheritance)
    because KrakenOS's interaction stack uses VTK events but Python state.
  * Widgets attach to an inspector for service access (renderer, picker,
    selection model) without requiring a Slicer-style MRML scene.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from KrakenOS.UI.services.open3d_interaction_event import InteractionEventData


class WidgetState(str, Enum):
    """Slicer's vtkMRMLAbstractWidget::Idle/OnWidget/TranslatingHandle/etc.

    Simplified to four states that map cleanly onto KrakenOS's drag/hover
    machinery without needing a full state-machine table.
    """

    IDLE = "idle"
    HOVER = "hover"
    ACTIVE = "active"
    PROCESSING = "processing"


# Distance constants mirroring vtkAbstractWidget::IsInside semantics:
# return -1 when the widget should not be considered for the event.
WIDGET_BID_NONE = -1.0
WIDGET_BID_DEFAULT = 1.0
WIDGET_BID_PRECISE = 0.0


class AbstractWidget:
    """Base class for KrakenOS interaction widgets.

    Subclasses override ``can_process`` and ``process``. The base default
    is to never bid and never consume, which is safe for incremental
    rollout: the WidgetRegistry can hold a no-op widget without it
    interfering with the existing inline dispatch.
    """

    def __init__(self, inspector: Any) -> None:
        self._inspector = inspector
        self._state = WidgetState.IDLE
        self._representation: Any = None

    @property
    def inspector(self) -> Any:
        return self._inspector

    @property
    def state(self) -> WidgetState:
        return self._state

    def set_state(self, state: WidgetState) -> None:
        self._state = state

    @property
    def representation(self) -> Any:
        return self._representation

    def set_representation(self, representation: Any) -> None:
        self._representation = representation

    # ------------------------------------------------------------------
    # Slicer-style contract methods (override in subclasses)

    def can_process(self, event: InteractionEventData) -> float:
        """Return a bid distance for ``event``.

        ``WIDGET_BID_NONE`` (or any negative value) means "I don't claim
        this event". Otherwise smaller is more precise; the registry
        routes the event to the lowest-bidding widget. Override in
        subclasses to opt in to specific PickTarget / event_type combos.
        """
        return WIDGET_BID_NONE

    def process(self, event: InteractionEventData) -> bool:
        """Handle ``event`` after winning the bid. Return True if handled."""
        return False

    def update_representation(self) -> None:
        """Refresh the actor styling that visualises this widget.

        Called by the registry after model changes or representation
        rebuilds. Default no-op; subclasses that own actors should walk
        them here.
        """
        return None


class WidgetRegistry:
    """Track AbstractWidget instances and route events.

    Phase 5 stores widgets in registration order; ties on bid distance
    resolve to first registered. Phase 6+ may add view-level scoping
    once multiple representations exist for the same data.
    """

    def __init__(self) -> None:
        self._widgets: list[AbstractWidget] = []

    def add(self, widget: AbstractWidget) -> None:
        if widget not in self._widgets:
            self._widgets.append(widget)

    def remove(self, widget: AbstractWidget) -> None:
        try:
            self._widgets.remove(widget)
        except ValueError:
            pass

    def widgets(self) -> tuple[AbstractWidget, ...]:
        return tuple(self._widgets)

    def update_representations(self) -> None:
        for widget in list(self._widgets):
            try:
                widget.update_representation()
            except Exception:
                continue

    def dispatch(self, event: InteractionEventData) -> AbstractWidget | None:
        """Find the best-bidding widget and let it consume the event.

        Returns the widget that consumed the event, or ``None`` if no
        widget bid or none of them returned True from ``process``.
        """
        best: tuple[float, AbstractWidget] | None = None
        for widget in list(self._widgets):
            try:
                bid = float(widget.can_process(event))
            except Exception:
                continue
            if not (bid >= 0.0):
                continue
            if best is None or bid < best[0]:
                best = (bid, widget)
        if best is None:
            return None
        try:
            if best[1].process(event):
                return best[1]
        except Exception:
            return None
        return None
