"""Non-sequential scene-graph record collection service."""

from __future__ import annotations

from typing import Any

from KrakenOS.UI.scene_builder import scene_placement_to_runtime_record, scene_target_to_runtime_record
from KrakenOS.UI.scene_row_mapping import SCENE_ROW_SOURCE


def _layout_module():
    from KrakenOS.UI import layout_editor as layout_editor_module

    return layout_editor_module


class NonSequentialSceneGraphRecordService:
    """Collect non-sequential scene-graph rows while delegating editor-specific helpers."""

    def __init__(self, editor: Any) -> None:
        object.__setattr__(self, "editor", editor)

    def __getattr__(self, name: str) -> Any:
        return getattr(self.editor, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_") or name == "editor":
            object.__setattr__(self, name, value)
            return
        setattr(self.editor, name, value)

    def _collect_nonseq_scene_graph_records(self) -> list[dict[str, object]]:
        le = _layout_module()
        ELEMENT_ARM_ROLE_DEFAULT = le.ELEMENT_ARM_ROLE_DEFAULT
        _element_metadata_summary = le._element_metadata_summary
        records: list[dict[str, object]] = []
        scene_sources = self._collect_scene_sources()
        scene_row_mapping = self._current_scene_row_mapping(scene_sources)
        optical_volumes = self._scene_optical_volumes_for_graph()
        optical_volumes_by_row: dict[int, list[object]] = {}
        for volume in optical_volumes:
            try:
                row_index = int(getattr(volume, "row_index", -1))
            except Exception:
                continue
            optical_volumes_by_row.setdefault(row_index, []).append(volume)
        boundary_faces = self._scene_boundary_faces_for_graph()
        boundary_faces_by_row: dict[int, list[object]] = {}
        for face in boundary_faces:
            try:
                row_index = int(getattr(face, "row_index", -1))
            except Exception:
                continue
            boundary_faces_by_row.setdefault(row_index, []).append(face)
        records.append(
            {
                "id": "scene_rows",
                "parent": "",
                "text": "Scene row order",
                "scene_row": f"{len(scene_row_mapping.records)} rows",
                "row": "-",
                "trace_surface": "-",
                "source_id": "-",
                "kind": "SceneRows",
                "surface": str(scene_row_mapping.source_row_order),
                "material": "-",
                "features": "source-visible table order",
                "target": "-",
                "detail": "Maps visible scene rows to current table rows and KrakenOS trace surfaces.",
                "row_index": None,
            }
        )
        for record in scene_row_mapping.records:
            metadata = dict(record.metadata or {})
            is_source = record.kind == SCENE_ROW_SOURCE
            table_text = "-" if record.table_row_index is None else f"S{int(record.table_row_index)}"
            trace_text = "-" if record.trace_surface_index is None else f"S{int(record.trace_surface_index)}"
            records.append(
                {
                    "id": f"scene_row:{int(record.scene_row_index)}",
                    "parent": "scene_rows",
                    "text": f"{record.label}: {record.name}",
                    "scene_row": int(record.scene_row_index),
                    "row": table_text,
                    "trace_surface": trace_text,
                    "source_id": str(record.source_id or "-"),
                    "kind": "Illumination Source" if is_source else "Scene Surface",
                    "surface": str(metadata.get("model") if is_source else metadata.get("surface", "")),
                    "material": "-",
                    "features": (
                        f"role={record.source_role}, rays={metadata.get('ray_count', '-')}"
                        if is_source
                        else f"element={metadata.get('element', '-') or '-'}"
                    ),
                    "target": "-",
                    "detail": self._scene_row_record_detail(record),
                    "row_index": record.table_row_index,
                }
            )
        records.append(
            {
                "id": "sources",
                "parent": "",
                "text": "Scene sources",
                "scene_row": "-",
                "row": "-",
                "trace_surface": "-",
                "source_id": "-",
                "kind": "SourceList",
                "surface": f"{len(scene_sources)} source",
                "material": "-",
                "features": "object/source split",
                "target": "-",
                "detail": "First-class scene source records. Use Scene Source Manager for explicit multi-source authoring; otherwise the Source panel maps to Source 1.",
                "row_index": None,
            }
        )
        for source in scene_sources:
            source_scene_row = scene_row_mapping.source_id_to_scene.get(str(source.source_id))
            records.append(
                {
                    "id": str(source.source_id),
                    "parent": "sources",
                    "text": str(source.name),
                    "scene_row": "-" if source_scene_row is None else int(source_scene_row),
                    "row": "-",
                    "trace_surface": "-",
                    "source_id": str(source.source_id),
                    "kind": "Source",
                    "surface": str(source.model),
                    "material": "-",
                    "features": self._scene_source_feature_text(source),
                    "target": "-",
                    "detail": self._scene_source_detail_text(source),
                    "row_index": None,
                }
            )
        trace_state = self._resolved_trace_mode(system=self.last_system)
        scene_targets = self._scene_targets_for_graph(trace_state)
        detector_count = sum(1 for target in scene_targets if bool(getattr(target, "is_detector", False)))
        target_index = self._current_nonseq_target_surface_index()
        target_label = "Auto"
        if target_index is not None and 0 <= target_index < len(self.rows):
            target_label = f"{target_index}: {self.rows[target_index].name}"
        records.append(
            {
                "id": "targets",
                "parent": "",
                "text": "Scene targets",
                "scene_row": "-",
                "row": f"{len(scene_targets)} targets",
                "trace_surface": f"{detector_count} detectors",
                "source_id": "-",
                "kind": "TargetList",
                "surface": "object/detector roles",
                "material": "-",
                "features": "first-class target records",
                "target": target_label,
                "detail": "Object/reference, aperture, detector, and active analysis target records derived from the scene without adding KrakenOS surf indices.",
                "row_index": None,
            }
        )
        for target in scene_targets:
            mapped_scene_row = scene_row_mapping.trace_surface_to_scene.get(int(target.trace_surface)) if target.trace_surface is not None else None
            target_record = scene_target_to_runtime_record(target)
            records.append(
                {
                    "id": f"target:{target.target_id}",
                    "parent": "targets",
                    "text": f"S{int(target.row_index)}: {target.name}",
                    "scene_row": "-" if mapped_scene_row is None else int(mapped_scene_row),
                    "row": int(target.row_index),
                    "trace_surface": "-" if target.trace_surface is None else f"S{int(target.trace_surface)}",
                    "source_id": "-",
                    "kind": "SceneTarget",
                    "surface": str(target.role),
                    "material": str(target.material or "-"),
                    "features": self._scene_target_features(target),
                    "target": "TargSurf" if bool(target.is_active_target) else "Detector" if bool(target.is_detector) else "-",
                    "detail": self._scene_target_detail(target),
                    "row_index": int(target.row_index),
                    "target_record": target_record,
                }
            )
        scene_placements = self._scene_placements_for_graph(scene_targets)
        records.append(
            {
                "id": "placements",
                "parent": "",
                "text": "3D placements",
                "scene_row": "-",
                "row": f"{len(scene_placements)} placements",
                "trace_surface": "-",
                "source_id": "-",
                "kind": "PlacementList",
                "surface": "row-backed scene authoring",
                "material": "-",
                "features": "grid/snap/pose metadata",
                "target": "-",
                "detail": "Direct 3D placement state is derived from row pose plus ScenePlacement metadata; future 3D handles must persist back here.",
                "row_index": None,
            }
        )
        for placement in scene_placements:
            try:
                placement_row = int(placement.row_index)
            except Exception:
                placement_row = -1
            mapped_scene_row = (
                scene_row_mapping.trace_surface_to_scene.get(int(placement.trace_surface))
                if placement.trace_surface is not None
                else None
            )
            placement_record = scene_placement_to_runtime_record(placement)
            records.append(
                {
                    "id": f"placement:{placement.placement_id}",
                    "parent": "placements",
                    "text": f"S{placement_row}: {self.rows[placement_row].name if 0 <= placement_row < len(self.rows) else placement.placement_id}",
                    "scene_row": "-" if mapped_scene_row is None else int(mapped_scene_row),
                    "row": "-" if placement_row < 0 else int(placement_row),
                    "trace_surface": "-" if placement.trace_surface is None else f"S{int(placement.trace_surface)}",
                    "source_id": "-",
                    "kind": "ScenePlacement",
                    "surface": str(getattr(placement, "anchor", "") or "row_pose"),
                    "material": "-",
                    "features": self._scene_placement_features(placement),
                    "target": str(getattr(placement, "target_id", "") or "-"),
                    "detail": self._scene_placement_detail(placement),
                    "row_index": None if placement_row < 0 else int(placement_row),
                    "placement_record": placement_record,
                }
            )
        records.append(
            {
                "id": "trace",
                "parent": "sources",
                "text": "Trace settings",
                "scene_row": "-",
                "row": "-",
                "trace_surface": "-",
                "source_id": "-",
                "kind": "Trace",
                "surface": str(trace_state.get("active", "")),
                "material": "-",
                "features": f"NsLimit={self._current_nonseq_ns_limit()}, energy_probability={int(self._current_nonseq_energy_probability())}",
                "target": target_label,
                "detail": str(trace_state.get("note", "") or "KrakenOS trace paths are generated by NsTrace/NsTraceLoop at trace time."),
                "row_index": None,
            }
        )
        records.append(
            {
                "id": "objects",
                "parent": "",
                "text": "Optical object list",
                "scene_row": "-",
                "row": f"{len(self.rows)} rows",
                "trace_surface": f"{len(self.rows)} surfaces",
                "source_id": "-",
                "kind": "System",
                "surface": "KrakenOS SDT",
                "material": "-",
                "features": "ordered surfaces/elements",
                "target": target_label,
                "detail": "This is the scene graph consumed by KrakenOS non-sequential tracing.",
                "row_index": None,
            }
        )
        index = 0
        target_index = self._current_nonseq_target_surface_index()
        while index < len(self.rows):
            row = self.rows[index]
            element_key = self._element_key(row)
            if element_key:
                start, end = self._element_block_for_index(self.rows, index)
                element_id = f"element:{start}:{end}:{element_key}"
                element_metadata = self._element_metadata(self.rows[start])
                element_role = str(element_metadata.get("arm_role", ELEMENT_ARM_ROLE_DEFAULT))
                element_features = "grouped component"
                if element_role != ELEMENT_ARM_ROLE_DEFAULT:
                    element_features += f", path={element_role}"
                records.append(
                    {
                        "id": element_id,
                        "parent": "objects",
                        "text": element_key,
                        "scene_row": "-",
                        "row": f"{start}-{end}",
                        "trace_surface": f"S{start}-S{end}",
                        "source_id": "-",
                        "kind": "Element",
                        "surface": f"{end - start + 1} surfaces",
                        "material": "-",
                        "features": element_features,
                        "target": "-",
                        "detail": (
                            "Move Up/Down and Flip act on this contiguous element block. "
                            + _element_metadata_summary(element_metadata)
                        ),
                        "row_index": start,
                    }
                )
                parent = element_id
                stop = end + 1
            else:
                parent = "objects"
                stop = index + 1
            while index < stop:
                surface_row = self.rows[index]
                mapped_scene_row = scene_row_mapping.trace_surface_to_scene.get(int(index))
                target_text = ""
                if target_index is None:
                    target_text = "Auto target" if index == len(self.rows) - 1 else ""
                elif index == target_index:
                    target_text = "TargSurf"
                records.append(
                    {
                        "id": f"surface:{index}",
                        "parent": parent,
                        "text": f"S{index}: {surface_row.name}",
                        "scene_row": "-" if mapped_scene_row is None else int(mapped_scene_row),
                        "row": index,
                        "trace_surface": f"S{index}",
                        "source_id": "-",
                        "kind": "Surface",
                        "surface": surface_row.surface,
                        "material": surface_row.glass,
                        "features": self._nonseq_row_features(surface_row),
                        "target": target_text or "-",
                        "detail": self._nonseq_row_detail(surface_row),
                        "row_index": index,
                    }
                )
                volume_parent_by_row = f"surface:{index}"
                for volume_offset, volume in enumerate(optical_volumes_by_row.get(int(index), [])):
                    volume_id = str(getattr(volume, "volume_id", "") or f"volume:{index}:{volume_offset}")
                    mapped_volume_scene_row = scene_row_mapping.trace_surface_to_scene.get(int(index))
                    volume_node_id = f"optical_volume:{index}:{volume_offset}:{volume_id}"
                    if volume_offset == 0:
                        volume_parent_by_row = volume_node_id
                    records.append(
                        {
                            "id": volume_node_id,
                            "parent": f"surface:{index}",
                            "text": volume_id,
                            "scene_row": "-" if mapped_volume_scene_row is None else int(mapped_volume_scene_row),
                            "row": index,
                            "trace_surface": f"S{index}",
                            "source_id": "-",
                            "kind": "OpticalVolume",
                            "surface": str(getattr(volume, "volume_type", "") or "optical_solid"),
                            "material": str(getattr(volume, "material", "") or surface_row.glass or "-"),
                            "features": self._scene_optical_volume_features(volume),
                            "target": "-",
                            "detail": self._scene_optical_volume_detail(volume),
                            "row_index": index,
                        }
                    )
                for face_offset, face in enumerate(boundary_faces_by_row.get(int(index), [])):
                    face_id = str(getattr(face, "face_id", "") or "").strip() or f"face{face_offset + 1}"
                    mapped_face_scene_row = scene_row_mapping.trace_surface_to_scene.get(int(index))
                    records.append(
                        {
                            "id": f"boundary_face:{index}:{face_offset}:{face_id}",
                            "parent": volume_parent_by_row,
                            "text": self._scene_boundary_face_text(face),
                            "scene_row": "-" if mapped_face_scene_row is None else int(mapped_face_scene_row),
                            "row": index,
                            "trace_surface": f"S{index}",
                            "source_id": "-",
                            "kind": "BoundaryFace",
                            "surface": str(getattr(face, "function", "") or "-"),
                            "material": str(getattr(face, "material", "") or surface_row.glass or "-"),
                            "features": self._scene_boundary_face_features(face),
                            "target": str(getattr(face, "port_role", "") or "-"),
                            "detail": self._scene_boundary_face_detail(face),
                            "row_index": index,
                        }
                    )
                index += 1
        return records
    
