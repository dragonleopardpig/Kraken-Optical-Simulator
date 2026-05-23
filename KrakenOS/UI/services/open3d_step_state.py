"""Open 3D STEP state-transition helpers.

This service is intentionally toolkit-light. It owns selection resolution for
STEP state transitions while the Tk/VTK inspector owns rendering and key/mouse
events.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class StepDeleteSelection:
    """Resolved target for a targeted STEP delete operation."""

    import_label: str = ""
    row_indices: tuple[int, ...] = ()

    @property
    def has_target(self) -> bool:
        return bool(self.import_label or self.row_indices)


class Open3DStepStateService:
    """Resolve Open 3D STEP state transitions outside the widget layer."""

    def __init__(self, editor: Any, *, valid_labels: Iterable[str]) -> None:
        self.editor = editor
        self.valid_labels = {str(label).strip().lower() for label in valid_labels}

    def selected_import_label(self, candidates: Iterable[object]) -> str:
        """Return the first candidate label with a loaded STEP overlay."""
        for candidate in candidates:
            label = str(candidate or "").strip().lower()
            if label not in self.valid_labels:
                continue
            try:
                if self.editor._step_path_for_label(label) is not None:
                    return label
            except Exception:
                continue
        return ""

    def promoted_step_row_indices(self, candidates: Iterable[object]) -> tuple[int, ...]:
        """Return unique promoted STEP optical-solid rows from candidate indices."""
        targets: set[int] = set()
        rows = list(getattr(self.editor, "rows", []) or [])
        for candidate in candidates:
            try:
                index = int(candidate)
            except Exception:
                continue
            if index < 0 or index >= len(rows):
                continue
            try:
                if self.editor._is_open3d_promoted_optical_solid_row(rows[index]):
                    targets.add(index)
            except Exception:
                continue
        return tuple(sorted(targets))

    def resolve_delete_selection(
        self,
        *,
        import_label_candidates: Iterable[object],
        row_index_candidates: Iterable[object],
    ) -> StepDeleteSelection:
        """Resolve a single imported overlay first, then promoted STEP rows."""
        label = self.selected_import_label(import_label_candidates)
        if label:
            return StepDeleteSelection(import_label=label)
        return StepDeleteSelection(row_indices=self.promoted_step_row_indices(row_index_candidates))
