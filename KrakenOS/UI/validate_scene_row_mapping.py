from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.common_optical_layouts.multi_source_illumination_example import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle
from KrakenOS.UI.scene_row_mapping import (
    SCENE_ROW_SOURCE,
    SCENE_ROW_SURFACE,
    build_scene_row_mapping,
    build_surface_table_mapping,
)


@dataclass
class SceneRowMappingCheck:
    check: str
    ok: bool
    detail: str


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
    sources = editor._collect_scene_sources(wavelength=0.532)
    surface_table_mapping = build_surface_table_mapping(rows)
    scene_mapping = build_scene_row_mapping(rows, sources, include_sources=True)
    system = _build_system_from_specs(_row_specs(rows))
    bundle = build_scene_bundle(rows=rows, system=system, rays=None, sources=sources)

    multi_rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    multi_editor = _snapshot_editor(multi_rows, SETTINGS)
    multi_sources = multi_editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
    multi_mapping = build_scene_row_mapping(multi_rows, multi_sources, include_sources=True)

    checks = [
        SceneRowMappingCheck(
            "current visible surface table stays identity mapped",
            surface_table_mapping.scene_to_trace_surface == {0: 0, 1: 1}
            and surface_table_mapping.trace_surface_to_scene == {0: 0, 1: 1}
            and not surface_table_mapping.source_records,
            surface_table_mapping.to_jsonable()["records"],
        ),
        SceneRowMappingCheck(
            "future source-visible scene rows insert source after Object",
            [record.kind for record in scene_mapping.records] == [SCENE_ROW_SURFACE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE]
            and scene_mapping.scene_to_trace_surface == {0: 0, 2: 1}
            and scene_mapping.trace_surface_to_scene == {0: 0, 1: 2}
            and scene_mapping.source_id_to_scene == {"source:0": 1},
            scene_mapping.to_jsonable()["records"],
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
            "multi-source mapping preserves trace indices while adding two source rows",
            [record.kind for record in multi_mapping.records]
            == [SCENE_ROW_SURFACE, SCENE_ROW_SOURCE, SCENE_ROW_SOURCE, SCENE_ROW_SURFACE, SCENE_ROW_SURFACE]
            and multi_mapping.scene_to_trace_surface == {0: 0, 3: 1, 4: 2}
            and multi_mapping.trace_surface_to_scene == {0: 0, 1: 3, 2: 4}
            and multi_mapping.source_id_to_scene == {"source:left": 1, "source:right": 2},
            multi_mapping.to_jsonable()["records"],
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
