"""SelectionView: observe SelectionModel and project state onto actors.

Counterpart to the Slicer ``vtkMRMLAbstractWidgetRepresentation`` role: the
model owns the data, the view styles whatever actors currently live in the
renderer. Today it is intentionally minimal -- a render-on-change observer
plus a hook the inspector can use to reapply highlights after a refresh.
Phase 2 will replace the per-pick imperative ``_set_*_highlight`` walks
with a fully observer-driven repaint here.
"""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.services.open3d_selection_model import SelectionModel


class SelectionView:
    """Render-side projection of a SelectionModel."""

    def __init__(self, inspector: Any, model: SelectionModel) -> None:
        self._inspector = inspector
        self._model = model
        self._attached = False

    @property
    def model(self) -> SelectionModel:
        return self._model

    def attach(self) -> None:
        if self._attached:
            return
        self._model.add_observer(self._on_model_changed)
        self._attached = True

    def detach(self) -> None:
        if not self._attached:
            return
        self._model.remove_observer(self._on_model_changed)
        self._attached = False

    def _on_model_changed(self, _model: SelectionModel) -> None:
        # Today the imperative _set_*_highlight calls already drive VTK
        # state on the spot, so the observer just makes sure the latest
        # styling becomes visible. Phase 2 will move the styling logic
        # into this method.
        inspector = self._inspector
        try:
            renderer = getattr(inspector, "_renderer", None)
        except Exception:
            renderer = None
        if renderer is None:
            return
        try:
            inspector.render()
        except Exception:
            pass
