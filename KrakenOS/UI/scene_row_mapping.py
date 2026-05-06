from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


SCENE_ROW_SURFACE = "surface"
SCENE_ROW_SOURCE = "source"


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.reshape(-1).tolist()]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    try:
        return float(value)
    except Exception:
        return str(value)


@dataclass(frozen=True, slots=True)
class SceneRowRecord:
    """One user-visible scene row and its optional trace/table identity.

    Optical surfaces have both ``table_row_index`` and ``trace_surface_index``.
    Illumination sources have neither because they are emitters, not KrakenOS
    ``surf`` records.
    """

    scene_row_index: int
    kind: str
    label: str
    name: str
    table_row_index: int | None = None
    trace_surface_index: int | None = None
    source_id: str | None = None
    source_role: str = ""
    enabled: bool = True
    physical: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "scene_row_index": int(self.scene_row_index),
            "kind": str(self.kind),
            "label": str(self.label),
            "name": str(self.name),
            "table_row_index": None if self.table_row_index is None else int(self.table_row_index),
            "trace_surface_index": None if self.trace_surface_index is None else int(self.trace_surface_index),
            "source_id": self.source_id,
            "source_role": str(self.source_role),
            "enabled": bool(self.enabled),
            "physical": bool(self.physical),
            "metadata": _jsonable(dict(self.metadata or {})),
        }


@dataclass(frozen=True, slots=True)
class SceneRowMapping:
    """Stable bridge between scene rows, table rows, and trace surfaces."""

    records: tuple[SceneRowRecord, ...] = ()

    @property
    def surface_records(self) -> tuple[SceneRowRecord, ...]:
        return tuple(record for record in self.records if record.kind == SCENE_ROW_SURFACE)

    @property
    def source_records(self) -> tuple[SceneRowRecord, ...]:
        return tuple(record for record in self.records if record.kind == SCENE_ROW_SOURCE)

    @property
    def scene_to_trace_surface(self) -> dict[int, int]:
        return {
            int(record.scene_row_index): int(record.trace_surface_index)
            for record in self.surface_records
            if record.trace_surface_index is not None
        }

    @property
    def trace_surface_to_scene(self) -> dict[int, int]:
        return {
            int(record.trace_surface_index): int(record.scene_row_index)
            for record in self.surface_records
            if record.trace_surface_index is not None
        }

    @property
    def scene_to_table_row(self) -> dict[int, int]:
        return {
            int(record.scene_row_index): int(record.table_row_index)
            for record in self.surface_records
            if record.table_row_index is not None
        }

    @property
    def table_row_to_scene(self) -> dict[int, int]:
        return {
            int(record.table_row_index): int(record.scene_row_index)
            for record in self.surface_records
            if record.table_row_index is not None
        }

    @property
    def source_id_to_scene(self) -> dict[str, int]:
        return {
            str(record.source_id): int(record.scene_row_index)
            for record in self.source_records
            if record.source_id
        }

    # Future visible editor rows can use these aliases directly.
    @property
    def ui_to_trace_surface(self) -> dict[int, int]:
        return self.scene_to_trace_surface

    @property
    def trace_surface_to_ui(self) -> dict[int, int]:
        return self.trace_surface_to_scene

    def record_for_scene_row(self, scene_row_index: int) -> SceneRowRecord | None:
        target = int(scene_row_index)
        for record in self.records:
            if int(record.scene_row_index) == target:
                return record
        return None

    def record_for_trace_surface(self, trace_surface_index: int) -> SceneRowRecord | None:
        target = int(trace_surface_index)
        for record in self.surface_records:
            if record.trace_surface_index is not None and int(record.trace_surface_index) == target:
                return record
        return None

    def record_for_table_row(self, table_row_index: int) -> SceneRowRecord | None:
        target = int(table_row_index)
        for record in self.surface_records:
            if record.table_row_index is not None and int(record.table_row_index) == target:
                return record
        return None

    def record_for_source_id(self, source_id: str) -> SceneRowRecord | None:
        target = str(source_id)
        for record in self.source_records:
            if str(record.source_id) == target:
                return record
        return None

    def to_jsonable(self) -> dict[str, Any]:
        return {
            "records": [record.to_jsonable() for record in self.records],
            "scene_to_trace_surface": {str(key): value for key, value in self.scene_to_trace_surface.items()},
            "trace_surface_to_scene": {str(key): value for key, value in self.trace_surface_to_scene.items()},
            "scene_to_table_row": {str(key): value for key, value in self.scene_to_table_row.items()},
            "table_row_to_scene": {str(key): value for key, value in self.table_row_to_scene.items()},
            "source_id_to_scene": dict(self.source_id_to_scene),
        }


def build_scene_row_mapping(
    rows: list[Any],
    sources: list[Any] | None = None,
    *,
    include_sources: bool = True,
) -> SceneRowMapping:
    """Build the source-aware scene row map used by non-sequential workflows.

    The current editable table still displays only KrakenOS surface rows. This
    map is the intermediate scene-table model: Object first, optional source
    scene rows next, then the remaining optical surface rows through Image.
    Surface trace indices stay equal to their KrakenOS row indices.
    """

    records: list[SceneRowRecord] = []
    scene_row_index = 0

    def add_surface(table_row_index: int, row: Any) -> None:
        nonlocal scene_row_index
        surface = str(getattr(row, "surface", "Surface") or "Surface")
        name = str(getattr(row, "name", "") or surface)
        element = str(getattr(row, "element", "") or "")
        records.append(
            SceneRowRecord(
                scene_row_index=scene_row_index,
                kind=SCENE_ROW_SURFACE,
                label=f"S{int(table_row_index)}",
                name=name,
                table_row_index=int(table_row_index),
                trace_surface_index=int(table_row_index),
                metadata={
                    "surface": surface,
                    "element": element,
                },
            )
        )
        scene_row_index += 1

    if rows:
        add_surface(0, rows[0])

    if include_sources:
        for source_index, source in enumerate(sources or [], start=1):
            source_id = str(getattr(source, "source_id", "") or f"source:{source_index - 1}")
            name = str(getattr(source, "name", "") or f"Source {source_index}")
            model = str(getattr(source, "model", "") or "")
            role = str(getattr(source, "role", "") or "")
            records.append(
                SceneRowRecord(
                    scene_row_index=scene_row_index,
                    kind=SCENE_ROW_SOURCE,
                    label=f"Src{source_index}",
                    name=name,
                    source_id=source_id,
                    source_role=role,
                    enabled=bool(getattr(source, "enabled", True)),
                    physical=bool(getattr(source, "physical", True)),
                    metadata={
                        "model": model,
                        "ray_count": int(getattr(source, "ray_count", 0) or 0),
                    },
                )
            )
            scene_row_index += 1

    start_index = 1 if rows else 0
    for table_row_index, row in enumerate(rows[start_index:], start=start_index):
        add_surface(table_row_index, row)

    return SceneRowMapping(tuple(records))


def build_surface_table_mapping(rows: list[Any]) -> SceneRowMapping:
    """Build the current visible table mapping without source scene rows."""

    return build_scene_row_mapping(rows, [], include_sources=False)
