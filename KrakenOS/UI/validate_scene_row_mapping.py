from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.common_optical_layouts.multi_source_illumination_example import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import (
    GAUSSIAN_INPUT_MODE_DEFAULT,
    PUPIL_PATTERN_DEFAULT,
    SCENE_PLACEMENT_ADVANCED_ATTR,
    SOURCE_ANGULAR_WEIGHT_DEFAULT,
    SOURCE_MODEL_DEFAULT,
    SOURCE_MODEL_VALUES,
    SOURCE_MODEL_ZEMAX_RAYFILE,
    SurfaceRow,
    _build_system_from_specs,
)
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle
from KrakenOS.UI.scene_placement import normalize_scene_placement_settings
from KrakenOS.UI.scene_row_mapping import (
    SCENE_ROW_SOURCE,
    SCENE_ROW_SURFACE,
    SOURCE_ROW_ORDER_AFTER_OBJECT,
    SOURCE_ROW_ORDER_BEFORE_OBJECT,
    build_scene_row_mapping,
    build_surface_table_mapping,
)
from KrakenOS.UI.scene_source_analysis import (
    dedupe_scene_source_ids,
    normalize_scene_source_specs,
    scene_source_detail_text,
    scene_source_feature_text,
    scene_source_from_spec,
    scene_source_setting_value,
    scene_sources_summary_text,
    source_panel_summary_text,
)


@dataclass
class SceneRowMappingCheck:
    check: str
    ok: bool
    detail: str


class _FakeTable:
    def __init__(self) -> None:
        self.children: list[str] = []
        self.values: dict[str, tuple[str, ...]] = {}
        self.tags: dict[str, tuple[str, ...]] = {}

    def delete(self, *items) -> None:
        if not items:
            return
        if len(items) == 1 and isinstance(items[0], (list, tuple)):
            items = tuple(items[0])
        remove = {str(item) for item in items}
        self.children = [item for item in self.children if item not in remove]
        for item in remove:
            self.values.pop(item, None)
            self.tags.pop(item, None)

    def get_children(self):
        return tuple(self.children)

    def insert(self, _parent, _index, *, iid, values, tags=()) -> None:
        item = str(iid)
        self.children.append(item)
        self.values[item] = tuple(str(value) for value in values)
        self.tags[item] = tuple(str(tag) for tag in tags)

    def exists(self, item) -> bool:
        return str(item) in self.children

    def item(self, item, option=None):
        if option == "values":
            return self.values.get(str(item), ())
        return {"values": self.values.get(str(item), ()), "tags": self.tags.get(str(item), ())}


def _default_rows() -> list[SurfaceRow]:
    return [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=50.0, diameter=20.0, drawing=0.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
    ]


def _row_specs(rows: list[SurfaceRow]) -> list[dict[str, object]]:
    return [
        {
            "surface": row.surface,
            "name": row.name,
            "rc": row.rc,
            "k": row.k,
            "axicon": row.axicon,
            "diff_ord": row.diff_ord,
            "grating_d": row.grating_d,
            "grating_angle": row.grating_angle,
            "thickness": row.thickness,
            "diameter": row.diameter,
            "in_diameter": row.in_diameter,
            "drawing": row.drawing,
            "extra_data": row.extra_data,
            "uda": row.uda,
            "advanced": row.advanced,
            "tilt_x": row.tilt_x,
            "tilt_y": row.tilt_y,
            "tilt_z": row.tilt_z,
            "desp_x": row.desp_x,
            "desp_y": row.desp_y,
            "desp_z": row.desp_z,
            "axis_move": row.axis_move,
            "glass": row.glass,
        }
        for row in rows
    ]


def validate_scene_row_mapping() -> list[SceneRowMappingCheck]:
    rows = _default_rows()
    editor = _snapshot_editor(
        rows,
        {
            "wavelength": "0.532",
            "ray_count": "3",
            "source_model": "Collimated disk source",
            "source_radius": "1.0",
            "source_l": "0.0",
            "source_m": "0.0",
            "source_n": "1.0",
        },
    )
    swapped_editor = _snapshot_editor(
        rows,
        {
            "wavelength": "0.532",
            "ray_count": "3",
            "source_model": "Collimated disk source",
            "source_radius": "1.0",
            "source_l": "0.0",
            "source_m": "0.0",
            "source_n": "1.0",
            "scene_row_order": SOURCE_ROW_ORDER_BEFORE_OBJECT,
        },
    )
    default_source_editor = _snapshot_editor(
        rows,
        {
            "wavelength": "0.532",
            "ray_count": "3",
            "source_model": "Pupil / field",
        },
    )
    sources = editor._collect_scene_sources(wavelength=0.532)
    surface_table_mapping = build_surface_table_mapping(rows)
    scene_mapping = build_scene_row_mapping(rows, sources, include_sources=True)
    swapped_mapping = build_scene_row_mapping(
        rows,
        sources,
        include_sources=True,
        source_row_order=SOURCE_ROW_ORDER_BEFORE_OBJECT,
    )
    system = _build_system_from_specs(_row_specs(rows))
    bundle = build_scene_bundle(rows=rows, system=system, rays=None, sources=sources)
    swapped_bundle = build_scene_bundle(
        rows=rows,
        system=system,
        rays=None,
        sources=sources,
        source_row_order=SOURCE_ROW_ORDER_BEFORE_OBJECT,
    )
    graph_by_id = {str(record.get("id", "")): record for record in editor._collect_nonseq_scene_graph_records()}
    swapped_graph_by_id = {
        str(record.get("id", "")): record for record in swapped_editor._collect_nonseq_scene_graph_records()
    }

    multi_rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    multi_editor = _snapshot_editor(multi_rows, SETTINGS)
    multi_sources = multi_editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
    multi_mapping = build_scene_row_mapping(multi_rows, multi_sources, include_sources=True)
    visible_scene_rows = editor._visible_scene_row_records_for_table([0, 1])
    swapped_visible_scene_rows = swapped_editor._visible_scene_row_records_for_table([0, 1])
    default_visible_scene_rows = default_source_editor._visible_scene_row_records_for_table([0, 1])
    sync_editor = _snapshot_editor(
        _default_rows(),
        {
            "wavelength": "0.532",
            "ray_count": "3",
            "source_model": "Collimated disk source",
            "source_radius": "1.0",
        },
    )
    sync_editor.table = _FakeTable()
    sync_editor._refresh_analysis_surface_choices = lambda: None
    sync_editor._refresh_operand_surface_choices = lambda: None
    sync_editor._schedule_table_grid_update = lambda *args, **kwargs: None
    sync_editor._sync_table()
    sync_children = list(sync_editor.table.get_children())
    sync_source_items = [item for item in sync_children if item.startswith("scene_source_")]
    try:
        sync_editor._read_rows_from_table()
        sync_readback_ok = [row.surface for row in sync_editor.rows] == ["Object", "Image"]
    except Exception:
        sync_readback_ok = False

    manager_editor = _snapshot_editor(
        _default_rows(),
        {
            "wavelength": "0.532",
            "ray_count": "7",
            "source_model": "Collimated disk source",
            "source_radius": "2.5",
            "source_x": "1.0",
            "source_y": "-2.0",
            "source_z": "3.0",
            "source_l": "0.0",
            "source_m": "1.0",
            "source_n": "0.0",
        },
    )
    manager_editor.table = _FakeTable()
    manager_editor._refresh_analysis_surface_choices = lambda: None
    manager_editor._refresh_operand_surface_choices = lambda: None
    manager_editor._schedule_table_grid_update = lambda *args, **kwargs: None
    panel_spec = manager_editor._scene_source_spec_from_current_panel(source_id="source:panel", name="Panel Source")
    second_spec = manager_editor._default_scene_source_spec(1)
    second_spec.update(
        {
            "source_id": "source:right",
            "name": "Right illuminator",
            "ray_count": 3,
            "source_y": 10.0,
            "source_l": 0.0,
            "source_m": -1.0,
            "source_n": 0.0,
        }
    )
    manager_editor._set_scene_source_specs(
        [panel_spec, second_spec],
        row_order=SOURCE_ROW_ORDER_BEFORE_OBJECT,
    )
    manager_sources = manager_editor._collect_scene_sources(wavelength=0.532)
    manager_visible_rows = manager_editor._visible_scene_row_records_for_table([0, 1])
    manager_children = list(manager_editor.table.get_children())
    manager_source_items = [item for item in manager_children if item.startswith("scene_source_")]
    manager_summary = manager_editor._format_source_summary()
    service_normalized = normalize_scene_source_specs({"scene_sources": manager_editor.layout_scene_source_specs})
    service_deduped = dedupe_scene_source_ids([dict(panel_spec), dict(panel_spec)])
    service_source = scene_source_from_spec(
        panel_spec,
        0,
        wavelength=0.532,
        default_ray_count=manager_editor._current_ray_count(),
        default_radius=manager_editor._current_source_radius(),
        default_cone_deg=manager_editor._current_source_cone_angle(),
        source_model_values=SOURCE_MODEL_VALUES,
        source_model_default=SOURCE_MODEL_DEFAULT,
        angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
    )
    default_panel_summary = source_panel_summary_text(
        default_source_editor._source_statistics(),
        source_model_default=SOURCE_MODEL_DEFAULT,
        source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE,
        pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
        gaussian_input_mode_default=GAUSSIAN_INPUT_MODE_DEFAULT,
        angular_weight_default=SOURCE_ANGULAR_WEIGHT_DEFAULT,
    )
    manager_feature_text = (
        scene_source_feature_text(
            manager_sources[0],
            source_model_default=SOURCE_MODEL_DEFAULT,
            source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE,
            pupil_pattern_default=PUPIL_PATTERN_DEFAULT,
        )
        if manager_sources
        else ""
    )
    manager_detail_text = (
        scene_source_detail_text(manager_sources[0], source_model_zemax_rayfile=SOURCE_MODEL_ZEMAX_RAYFILE)
        if manager_sources
        else ""
    )
    scene_target_editor = _snapshot_editor(
        [
            SurfaceRow(label="0", surface="Object", name="Object", thickness=10.0, diameter=20.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="1", surface="Standard", name="Candidate plane", thickness=40.0, diameter=12.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
        ],
        {"trace_mode": "Non-Sequential Preview", "nonseq_target_surface": "Auto"},
    )
    scene_target_editor._refresh_analysis_surface_choices = lambda: None
    detector_result = scene_target_editor._apply_scene_target_editor_update(
        1,
        target_kind="Detector",
        detector_settings={"active_width_mm": 9.0, "active_height_mm": 7.0, "bins": 48, "pixel_pitch_um": 3.45},
        active_target=True,
        row_name="Scene detector",
    )
    detector_targets = build_scene_bundle(
        rows=scene_target_editor.rows,
        system=_build_system_from_specs(_row_specs(scene_target_editor.rows)),
        rays=None,
        target_surface=scene_target_editor._current_nonseq_target_surface_index(),
        detector_surface_indices=scene_target_editor._scene_detector_surface_indices({"use_nonseq": True}),
    ).targets
    detector_target = next((target for target in detector_targets if target.row_index == 1), None)

    object_target_editor = _snapshot_editor(
        [
            SurfaceRow(label="0", surface="Object", name="Object", thickness=10.0, diameter=20.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="1", surface="Standard", name="Return plane", thickness=40.0, diameter=12.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
        ],
        {"trace_mode": "Non-Sequential Preview", "nonseq_target_surface": "Auto"},
    )
    object_target_editor._refresh_analysis_surface_choices = lambda: None
    object_target_result = object_target_editor._apply_scene_target_editor_update(
        1,
        target_kind="Object Target",
        active_target=False,
        row_name="Return object",
    )
    object_targets = build_scene_bundle(
        rows=object_target_editor.rows,
        system=_build_system_from_specs(_row_specs(object_target_editor.rows)),
        rays=None,
    ).targets
    object_target = next((target for target in object_targets if target.row_index == 1), None)

    analysis_target_editor = _snapshot_editor(
        [
            SurfaceRow(label="0", surface="Object", name="Object", thickness=10.0, diameter=20.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="1", surface="Standard", name="Analysis plane", thickness=40.0, diameter=12.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
        ],
        {"trace_mode": "Non-Sequential Preview", "nonseq_target_surface": "Auto"},
    )
    analysis_target_editor._refresh_analysis_surface_choices = lambda: None
    analysis_target_editor._apply_scene_target_editor_update(1, target_kind="Analysis Target", active_target=True)
    analysis_targets = build_scene_bundle(
        rows=analysis_target_editor.rows,
        system=_build_system_from_specs(_row_specs(analysis_target_editor.rows)),
        rays=None,
        target_surface=analysis_target_editor._current_nonseq_target_surface_index(),
        detector_surface_indices=analysis_target_editor._scene_detector_surface_indices({"use_nonseq": True}),
    ).targets
    analysis_target = next((target for target in analysis_targets if target.row_index == 1), None)
    placement_editor = _snapshot_editor(
        [
            SurfaceRow(label="0", surface="Object", name="Object", thickness=10.0, diameter=20.0, drawing=0.0, glass="AIR"),
            SurfaceRow(label="1", surface="Standard", name="Placeable solid", thickness=40.0, diameter=12.0, drawing=0.0, glass="BK7"),
            SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
        ],
        {"trace_mode": "Non-Sequential Preview", "nonseq_target_surface": "Auto"},
    )
    placement_editor._set_scene_placement_settings(
        placement_editor.rows[1],
        {
            "anchor": "target_center",
            "snap_enabled": True,
            "snap_mm": 2.5,
            "grid_visible": True,
            "grid_spacing_mm": 5.0,
            "grid_extent_mm": 60.0,
        },
    )
    placement_bundle = build_scene_bundle(
        rows=placement_editor.rows,
        system=_build_system_from_specs(_row_specs(placement_editor.rows)),
        rays=None,
    )
    placement_record = next((placement for placement in placement_bundle.placements if placement.row_index == 1), None)
    placement_graph_by_id = {
        str(record.get("id", "")): record for record in placement_editor._collect_nonseq_scene_graph_records()
    }
    constraint_result = placement_editor.snap_scene_row_anchor_to_target(1, 2)
    translate_result = placement_editor.translate_scene_row_pose(1, "x", 2.5)
    rotate_result = placement_editor.rotate_scene_row_pose(1, "z", 5.0)
    translated_settings = normalize_scene_placement_settings(
        placement_editor.rows[1].advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {})
    )

    checks = [
        SceneRowMappingCheck(
            "current visible surface table stays identity mapped",
            surface_table_mapping.scene_to_trace_surface == {0: 0, 1: 1}
            and surface_table_mapping.trace_surface_to_scene == {0: 0, 1: 1}
            and not surface_table_mapping.source_records,
            surface_table_mapping.to_jsonable()["records"],
        ),
        SceneRowMappingCheck(
            "source-visible scene rows insert source after Object",
            [record.kind for record in scene_mapping.records] == [SCENE_ROW_SURFACE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE]
            and scene_mapping.source_row_order == SOURCE_ROW_ORDER_AFTER_OBJECT
            and scene_mapping.scene_to_trace_surface == {0: 0, 2: 1}
            and scene_mapping.trace_surface_to_scene == {0: 0, 1: 2}
            and scene_mapping.source_id_to_scene == {"source:0": 1},
            scene_mapping.to_jsonable()["records"],
        ),
        SceneRowMappingCheck(
            "source/Object row order can be swapped without changing trace surfaces",
            [record.kind for record in swapped_mapping.records] == [SCENE_ROW_SOURCE, SCENE_ROW_SURFACE, SCENE_ROW_SURFACE]
            and swapped_mapping.source_row_order == SOURCE_ROW_ORDER_BEFORE_OBJECT
            and swapped_mapping.scene_to_trace_surface == {1: 0, 2: 1}
            and swapped_mapping.trace_surface_to_scene == {0: 1, 1: 2}
            and swapped_mapping.source_id_to_scene == {"source:0": 0},
            swapped_mapping.to_jsonable()["records"],
        ),
        SceneRowMappingCheck(
            "source scene row does not consume table or trace index",
            bool(scene_mapping.source_records)
            and scene_mapping.source_records[0].table_row_index is None
            and scene_mapping.source_records[0].trace_surface_index is None,
            scene_mapping.source_records[0].to_jsonable() if scene_mapping.source_records else {},
        ),
        SceneRowMappingCheck(
            "SceneBundle carries the same source-aware mapping",
            bundle.scene_row_mapping is not None
            and bundle.scene_row_mapping.scene_to_trace_surface == scene_mapping.scene_to_trace_surface
            and bundle.scene_row_mapping.source_id_to_scene == {"source:0": 1},
            bundle.scene_row_mapping.to_jsonable() if bundle.scene_row_mapping is not None else {},
        ),
        SceneRowMappingCheck(
            "SceneBundle carries explicit object and detector target records",
            {target.role for target in bundle.targets} == {"object_reference", "detector"}
            and {target.target_id for target in bundle.targets} == {"surface:0", "surface:1"}
            and any(target.is_detector and target.trace_surface == 1 for target in bundle.targets),
            [target.target_id + ":" + target.role for target in bundle.targets],
        ),
        SceneRowMappingCheck(
            "SceneBundle honors swapped source/Object order",
            swapped_bundle.scene_row_mapping is not None
            and swapped_bundle.scene_row_mapping.source_row_order == SOURCE_ROW_ORDER_BEFORE_OBJECT
            and swapped_bundle.scene_row_mapping.scene_to_trace_surface == swapped_mapping.scene_to_trace_surface
            and swapped_bundle.scene_row_mapping.source_id_to_scene == {"source:0": 0},
            swapped_bundle.scene_row_mapping.to_jsonable() if swapped_bundle.scene_row_mapping is not None else {},
        ),
        SceneRowMappingCheck(
            "Non-Sequential Scene Graph exposes source-visible scene rows",
            "scene_rows" in graph_by_id
            and graph_by_id.get("scene_row:0", {}).get("trace_surface") == "S0"
            and graph_by_id.get("scene_row:1", {}).get("source_id") == "source:0"
            and graph_by_id.get("scene_row:2", {}).get("trace_surface") == "S1",
            [graph_by_id.get(key, {}) for key in ("scene_rows", "scene_row:0", "scene_row:1", "scene_row:2")],
        ),
        SceneRowMappingCheck(
            "Non-Sequential Scene Graph exposes first-class scene targets",
            "targets" in graph_by_id
            and graph_by_id.get("target:surface:0", {}).get("surface") == "object_reference"
            and graph_by_id.get("target:surface:1", {}).get("target") == "Detector",
            [graph_by_id.get(key, {}) for key in ("targets", "target:surface:0", "target:surface:1")],
        ),
        SceneRowMappingCheck(
            "Non-Sequential Scene Graph honors source-first scene rows",
            swapped_graph_by_id.get("scene_row:0", {}).get("source_id") == "source:0"
            and swapped_graph_by_id.get("scene_row:1", {}).get("trace_surface") == "S0"
            and swapped_graph_by_id.get("scene_row:2", {}).get("trace_surface") == "S1",
            [swapped_graph_by_id.get(key, {}) for key in ("scene_row:0", "scene_row:1", "scene_row:2")],
        ),
        SceneRowMappingCheck(
            "multi-source mapping preserves trace indices while adding two source rows",
            [record.kind for record in multi_mapping.records]
            == [SCENE_ROW_SURFACE, SCENE_ROW_SOURCE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE, SCENE_ROW_SURFACE]
            and multi_mapping.scene_to_trace_surface == {0: 0, 3: 1, 4: 2}
            and multi_mapping.trace_surface_to_scene == {0: 0, 1: 3, 2: 4}
            and multi_mapping.source_id_to_scene == {"source:left": 1, "source:right": 2},
            multi_mapping.to_jsonable()["records"],
        ),
        SceneRowMappingCheck(
            "visible table scene rows show physical source between Object and Image",
            [record.kind for record in visible_scene_rows] == [SCENE_ROW_SURFACE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE]
            and visible_scene_rows[1].table_row_index is None
            and visible_scene_rows[1].trace_surface_index is None,
            [record.to_jsonable() for record in visible_scene_rows],
        ),
        SceneRowMappingCheck(
            "visible table scene rows honor source-first order",
            [record.kind for record in swapped_visible_scene_rows]
            == [SCENE_ROW_SOURCE, SCENE_ROW_SURFACE, SCENE_ROW_SURFACE]
            and swapped_visible_scene_rows[0].source_id == "source:0",
            [record.to_jsonable() for record in swapped_visible_scene_rows],
        ),
        SceneRowMappingCheck(
            "default pupil-field source does not clutter the visible surface table",
            [record.kind for record in default_visible_scene_rows] == [SCENE_ROW_SURFACE, SCENE_ROW_SURFACE],
            [record.to_jsonable() for record in default_visible_scene_rows],
        ),
        SceneRowMappingCheck(
            "table sync renders source rows without adding prescription rows",
            len(sync_children) == 3
            and len(sync_source_items) == 1
            and sync_editor._table_item_row_index(sync_source_items[0]) is None
            and sync_readback_ok,
            {
                "children": sync_children,
                "source_items": sync_source_items,
                "rows": [row.surface for row in sync_editor.rows],
            },
        ),
        SceneRowMappingCheck(
            "Scene Source Manager helper converts Source panel into explicit source spec",
            panel_spec.get("source_id") == "source:panel"
            and panel_spec.get("model") == "Collimated disk source"
            and panel_spec.get("ray_count") == 7
            and panel_spec.get("source_y") == -2.0
            and panel_spec.get("source_m") == 1.0,
            panel_spec,
        ),
        SceneRowMappingCheck(
            "Scene Source Manager applies multi-source scene rows before Object",
            [source.source_id for source in manager_sources] == ["source:panel", "source:right"]
            and [record.kind for record in manager_visible_rows]
            == [SCENE_ROW_SOURCE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE, SCENE_ROW_SURFACE]
            and len(manager_source_items) == 2
            and [row.surface for row in manager_editor.rows] == ["Object", "Image"],
            {
                "children": manager_children,
                "source_items": manager_source_items,
                "visible_rows": [record.to_jsonable() for record in manager_visible_rows],
                "sources": [source.source_id for source in manager_sources],
            },
        ),
        SceneRowMappingCheck(
            "source summary points users to Scene Source Manager",
            "Scene Source Manager" in manager_summary and "2 physical emitter" in manager_summary,
            manager_summary,
        ),
        SceneRowMappingCheck(
            "scene source analysis helpers are service-owned",
            service_normalized
            == manager_editor._normalize_scene_source_specs({"scene_sources": manager_editor.layout_scene_source_specs})
            and [spec.get("source_id") for spec in service_deduped] == ["source:panel", "source:panel_2"]
            and service_source.source_id == "source:panel"
            and service_source.ray_count == 7
            and service_source.settings.get("radius") == 2.5
            and scene_source_setting_value(float("inf")) is None
            and scene_sources_summary_text(manager_sources) == manager_summary
            and manager_feature_text == manager_editor._scene_source_feature_text(manager_sources[0])
            and manager_detail_text == manager_editor._scene_source_detail_text(manager_sources[0])
            and default_panel_summary == default_source_editor._format_source_summary(),
            {
                "normalized": service_normalized,
                "deduped_ids": [spec.get("source_id") for spec in service_deduped],
                "service_source": {
                    "source_id": service_source.source_id,
                    "ray_count": service_source.ray_count,
                    "radius": service_source.settings.get("radius"),
                },
                "manager_summary": manager_summary,
                "default_panel_summary": default_panel_summary,
            },
        ),
        SceneRowMappingCheck(
            "Scene Target editor marks detector metadata as first-class target state",
            detector_target is not None
            and detector_result.get("target_kind") == "detector"
            and detector_target.role == "detector"
            and detector_target.is_detector
            and detector_target.is_active_target
            and abs(float(detector_target.active_width_mm) - 9.0) <= 1e-12
            and detector_target.detector_bins == "48",
            {
                "result": detector_result,
                "target": None if detector_target is None else detector_target.target_id + ":" + detector_target.role,
                "active": None if detector_target is None else detector_target.is_active_target,
                "bins": None if detector_target is None else detector_target.detector_bins,
            },
        ),
        SceneRowMappingCheck(
            "Scene Target editor converts object targets through normal surface defaults",
            object_target is not None
            and object_target_result.get("surface") == "Object Target"
            and object_target.role == "object_target"
            and object_target_editor.rows[1].glass == "MIRROR"
            and not object_target.is_detector,
            {
                "result": object_target_result,
                "surface": object_target_editor.rows[1].surface,
                "glass": object_target_editor.rows[1].glass,
                "target": None if object_target is None else object_target.target_id + ":" + object_target.role,
            },
        ),
        SceneRowMappingCheck(
            "Scene Target editor can persist analysis target rows without changing surface type",
            analysis_target is not None
            and analysis_target.role == "analysis_target"
            and analysis_target.is_active_target
            and not analysis_target.is_detector
            and analysis_target_editor.rows[1].surface == "Standard",
            {
                "surface": analysis_target_editor.rows[1].surface,
                "settings": analysis_target_editor.rows[1].advanced.get("SceneTarget", {}),
                "target": None if analysis_target is None else analysis_target.target_id + ":" + analysis_target.role,
            },
        ),
        SceneRowMappingCheck(
            "ScenePlacement metadata is row-backed and normalized",
            SCENE_PLACEMENT_ADVANCED_ATTR in placement_editor.rows[1].advanced
            and normalize_scene_placement_settings(placement_editor.rows[1].advanced[SCENE_PLACEMENT_ADVANCED_ATTR])[
                "snap_mm"
            ]
            == 2.5
            and normalize_scene_placement_settings(placement_editor.rows[1].advanced[SCENE_PLACEMENT_ADVANCED_ATTR])[
                "grid_spacing_mm"
            ]
            == 5.0,
            placement_editor.rows[1].advanced.get(SCENE_PLACEMENT_ADVANCED_ATTR, {}),
        ),
        SceneRowMappingCheck(
            "SceneBundle exposes 3D placement records without adding trace surfaces",
            placement_record is not None
            and placement_record.row_index == 1
            and placement_record.trace_surface == 1
            and placement_record.snap_enabled
            and abs(float(placement_record.snap_mm) - 2.5) <= 1e-12
            and len(placement_editor.rows) == 3,
            None
            if placement_record is None
            else {
                "placement_id": placement_record.placement_id,
                "row_index": placement_record.row_index,
                "trace_surface": placement_record.trace_surface,
                "snap_mm": placement_record.snap_mm,
                "grid_spacing_mm": placement_record.grid_spacing_mm,
            },
        ),
        SceneRowMappingCheck(
            "Non-Sequential Scene Graph exposes 3D placements for export",
            "placements" in placement_graph_by_id
            and placement_graph_by_id.get("placement:surface:1", {}).get("kind") == "ScenePlacement"
            and "snap=2.5 mm" in str(placement_graph_by_id.get("placement:surface:1", {}).get("features", "")),
            [placement_graph_by_id.get(key, {}) for key in ("placements", "placement:surface:1")],
        ),
        SceneRowMappingCheck(
            "3D placement translate writes row pose and ScenePlacement metadata",
            abs(float(placement_editor.rows[1].desp_x) - 2.5) <= 1e-12
            and translated_settings.get("last_translate_axis") == "x"
            and abs(float(translated_settings.get("last_translate_step_mm", 0.0)) - 2.5) <= 1e-12
            and translate_result.get("axis") == "x",
            {
                "result": translate_result,
                "desp_x": placement_editor.rows[1].desp_x,
                "settings": translated_settings,
            },
        ),
        SceneRowMappingCheck(
            "3D placement rotate writes row pose and ScenePlacement metadata",
            abs(float(placement_editor.rows[1].tilt_z) - 5.0) <= 1e-12
            and translated_settings.get("last_rotate_axis") == "z"
            and abs(float(translated_settings.get("last_rotate_step_deg", 0.0)) - 5.0) <= 1e-12
            and rotate_result.get("axis") == "z",
            {
                "result": rotate_result,
                "tilt_z": placement_editor.rows[1].tilt_z,
                "settings": translated_settings,
            },
        ),
        SceneRowMappingCheck(
            "3D placement target snap writes row pose and ScenePlacement metadata",
            abs(float(placement_editor.rows[1].desp_z) - 40.0) <= 1e-12
            and translated_settings.get("last_constraint_kind") == "target_surface"
            and translated_settings.get("last_constraint_target_row") == 2
            and constraint_result.get("target_row_index") == 2,
            {
                "result": constraint_result,
                "desp_z": placement_editor.rows[1].desp_z,
                "settings": translated_settings,
            },
        ),
    ]
    return checks


def _print_table(checks: list[SceneRowMappingCheck]) -> None:
    print("KrakenOS scene-row mapping validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source-aware scene row mapping.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_scene_row_mapping()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
