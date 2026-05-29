"""Open3DApplicationLogic -- high-level workflow facade.

Ports the spirit of Slicer's ``vtkMRMLApplicationLogic``: a single class
that orchestrates inspector workflows so callers don't have to know
which boolean to set or which inspector method to call to start, finish,
or cancel an interaction.

Phase 11 is intentionally a thin facade -- each method here delegates to
the existing inspector method. The value is the named, discoverable API
surface that lives outside the 9000-line inspector module and can be
tested or wrapped by future tooling (e.g. a CLI/MCP driver, a remote
debugger, a script-recorded macro player) without importing the Tk-bound
Kraken3DInspector class wholesale.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.services.open3d_interaction_mode import InteractionMode


class Open3DApplicationLogic:
    """Workflow-level entry points for the Open 3D inspector."""

    def __init__(self, inspector: Any) -> None:
        self._inspector = inspector

    @property
    def inspector(self) -> Any:
        return self._inspector

    # ------------------------------------------------------------------
    # Interaction-mode lifecycle

    def current_mode(self) -> InteractionMode:
        return self._inspector.current_interaction_mode()

    def cancel_active_operation(self) -> bool:
        return bool(self._inspector.cancel_active_3d_operation())

    def is_busy(self) -> bool:
        return self.current_mode() != InteractionMode.IDLE

    # ------------------------------------------------------------------
    # Pick-mode initiators (named entry points -- the inspector methods
    # already exist, we just give them a stable public API)

    def start_source_target_pick(self) -> None:
        self._inspector.start_source_target_pick()

    def start_center_row_to_ray(self) -> None:
        self._inspector.start_center_row_to_ray()

    def start_placement_target_pick(self) -> None:
        self._inspector.start_placement_target_pick()

    def start_placement_orient_pick(self) -> None:
        self._inspector.start_placement_orient_pick()

    def start_placement_orient_ray_pick(self) -> None:
        self._inspector.start_placement_orient_ray_pick()

    # ------------------------------------------------------------------
    # Selection model / view passthroughs

    @property
    def selection_model(self):
        return self._inspector._selection_model

    @property
    def selection_representation(self):
        return self._inspector._selection_representation

    @property
    def interaction_mode_state(self):
        return self._inspector._interaction_mode_state

    @property
    def widget_registry(self):
        return self._inspector._widget_registry

    # ------------------------------------------------------------------
    # Selection convenience

    def clear_selection(self, *, render: bool = True) -> bool:
        return bool(self._inspector._clear_open3d_selection(render=bool(render)))
