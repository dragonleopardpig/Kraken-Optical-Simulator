"""Selection-state model for the embedded Open 3D inspector.

Adopts the 3D Slicer MRML-node pattern: selection state lives on a data
object that survives ``RemoveAllViewProps()``. Inspector and refresh code
no longer own picked-state fields directly; they read and write through
this model. A future ``SelectionView`` can subscribe to observer callbacks
and re-apply highlights when the model changes or when actors are rebuilt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterable


SelectionObserver = Callable[["SelectionModel"], None]


@dataclass
class SelectionModel:
    """Owns Open 3D inspector pick state across scene rebuilds."""

    picked_row_index: int | None = None
    picked_row_indices: set[int] = field(default_factory=set)
    picked_step_label: str | None = None
    picked_ray_index: int | None = None
    picked_optical_axis_id: str | None = None
    _observers: list[SelectionObserver] = field(default_factory=list, repr=False)

    def add_observer(self, callback: SelectionObserver) -> None:
        if callback not in self._observers:
            self._observers.append(callback)

    def remove_observer(self, callback: SelectionObserver) -> None:
        try:
            self._observers.remove(callback)
        except ValueError:
            pass

    def _notify(self) -> None:
        for callback in list(self._observers):
            try:
                callback(self)
            except Exception:
                continue

    def set_row(self, row_index: int | None) -> None:
        normalized = None if row_index is None else int(row_index)
        new_set = set() if normalized is None else {normalized}
        if normalized == self.picked_row_index and new_set == self.picked_row_indices:
            return
        self.picked_row_index = normalized
        self.picked_row_indices = new_set
        self._notify()

    def set_rows(self, row_indices: Iterable[int] | None) -> None:
        new_set: set[int] = set()
        for value in list(row_indices or []):
            try:
                new_set.add(int(value))
            except (TypeError, ValueError):
                continue
        picked = min(new_set) if new_set else None
        if picked == self.picked_row_index and new_set == self.picked_row_indices:
            return
        self.picked_row_index = picked
        self.picked_row_indices = new_set
        self._notify()

    def set_step_label(self, label: str | None) -> None:
        normalized = None if label is None else str(label)
        if normalized == self.picked_step_label:
            return
        self.picked_step_label = normalized
        self._notify()

    def set_ray(self, ray_index: int | None) -> None:
        normalized = None if ray_index is None else int(ray_index)
        if normalized == self.picked_ray_index:
            return
        self.picked_ray_index = normalized
        self._notify()

    def set_optical_axis(self, axis_id: str | None) -> None:
        normalized = None if axis_id is None else (str(axis_id).strip() or None)
        if normalized == self.picked_optical_axis_id:
            return
        self.picked_optical_axis_id = normalized
        self._notify()

    def clear(self) -> None:
        if (
            self.picked_row_index is None
            and not self.picked_row_indices
            and self.picked_step_label is None
            and self.picked_ray_index is None
            and self.picked_optical_axis_id is None
        ):
            return
        self.picked_row_index = None
        self.picked_row_indices = set()
        self.picked_step_label = None
        self.picked_ray_index = None
        self.picked_optical_axis_id = None
        self._notify()
