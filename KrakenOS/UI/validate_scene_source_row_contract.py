from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

from KrakenOS.common_optical_layouts.multi_source_illumination_example import SETTINGS, SURFACES
from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle


@dataclass
class SceneSourceRowContractCheck:
    check: str
    ok: bool
    detail: str


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


def _default_anchor_rows() -> list[SurfaceRow]:
    return [
        SurfaceRow(
            label="0",
            surface="Object",
            name="Object",
            thickness=50.0,
            diameter=20.0,
            drawing=0.0,
            glass="AIR",
        ),
        SurfaceRow(
            label="1",
            surface="Image",
            name="Image",
            thickness=0.0,
            diameter=20.0,
            drawing=0.0,
            glass="AIR",
        ),
    ]


def validate_scene_source_row_contract() -> list[SceneSourceRowContractCheck]:
    """Validate the current source-table boundary before source rows are added.

    The UI target is Object + Illumination Source(s) + Image as fixed scene
    entities. The current KrakenOS prescription rows are still only optical
    surfaces. This validator protects that boundary so a future source-row UI
    can be added with an explicit UI-row to trace-surface index map instead of
    accidentally inserting a non-surface into KrakenOS ``surf`` lists.
    """

    rows = _default_anchor_rows()
    editor = _snapshot_editor(
        rows,
        {
            "wavelength": "0.532",
            "ray_count": "3",
            "source_model": "Collimated disk source",
            "source_radius": "1.0",
            "source_x": "0.0",
            "source_y": "0.0",
            "source_z": "0.0",
            "source_l": "0.0",
            "source_m": "0.0",
            "source_n": "1.0",
        },
    )
    sources = editor._collect_scene_sources(wavelength=0.532)
    system = _build_system_from_specs(_row_specs(rows))
    bundle = build_scene_bundle(rows=rows, system=system, rays=None, sources=sources)
    graph_records = editor._collect_nonseq_scene_graph_records()
    graph_ids = {str(record.get("id", "")) for record in graph_records}

    multi_rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    multi_editor = _snapshot_editor(multi_rows, SETTINGS)
    multi_sources = multi_editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
    multi_system = _build_system_from_specs(SURFACES)
    multi_bundle = build_scene_bundle(
        rows=multi_rows,
        system=multi_system,
        rays=None,
        sources=multi_sources,
        field_count=len(multi_sources),
        ray_count_per_field=max((source.ray_count for source in multi_sources), default=1),
    )

    reset_surfaces = [row.surface for row in rows]
    multi_surfaces = [row.surface for row in multi_rows]
    multi_source_ids = {source.source_id for source in multi_sources}
    multi_curve_source_count = sum(1 for curve in multi_bundle.surface_curves if getattr(curve, "kind", "") == "source")

    action_editor = _snapshot_editor(_rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS}), SETTINGS)
    action_surface_count = len(action_editor.rows)
    duplicate_ok = action_editor.duplicate_scene_source_by_id("source:left", record_history=False)
    duplicate_ids = [str(spec.get("source_id", "")) for spec in action_editor.layout_scene_source_specs]
    move_ok = action_editor.move_scene_source_by_id("source:right", "up", record_history=False)
    moved_ids = [str(spec.get("source_id", "")) for spec in action_editor.layout_scene_source_specs]
    delete_ok = action_editor.delete_scene_source_by_id("source:left_copy", record_history=False)
    final_ids = [str(spec.get("source_id", "")) for spec in action_editor.layout_scene_source_specs]
    action_system = _build_system_from_specs(_row_specs(action_editor.rows))
    action_sources = action_editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
    action_bundle = build_scene_bundle(
        rows=action_editor.rows,
        system=action_system,
        rays=None,
        sources=action_sources,
        field_count=len(action_sources),
        ray_count_per_field=max((source.ray_count for source in action_sources), default=1),
    )

    checks = [
        SceneSourceRowContractCheck(
            "surface prescription remains Object/Image anchored",
            reset_surfaces == ["Object", "Image"],
            f"surfaces={reset_surfaces}",
        ),
        SceneSourceRowContractCheck(
            "physical Source panel is a scene source, not a KrakenOS surface row",
            len(sources) == 1
            and sources[0].source_id == "source:0"
            and sources[0].role == "illumination"
            and "Illumination Source" not in reset_surfaces,
            f"rows={reset_surfaces} sources={[source.source_id for source in sources]}",
        ),
        SceneSourceRowContractCheck(
            "KrakenOS system surface count excludes scene sources",
            len(getattr(system, "SDT", [])) == len(rows),
            f"system_surfaces={len(getattr(system, 'SDT', []))} table_surfaces={len(rows)} sources={len(sources)}",
        ),
        SceneSourceRowContractCheck(
            "SceneBundle keeps source records beside surface records",
            len(bundle.sources) == 1
            and {curve.row_index for curve in bundle.surface_curves if not str(getattr(curve, "kind", "")).startswith("source")} == {0, 1}
            and any(getattr(curve, "kind", "") == "source" for curve in bundle.surface_curves),
            f"surface_curves={len(bundle.surface_curves)} bundle_sources={len(bundle.sources)}",
        ),
        SceneSourceRowContractCheck(
            "SceneBundle row mapping keeps source row separate from trace surfaces",
            bundle.scene_row_mapping is not None
            and bundle.scene_row_mapping.source_id_to_scene == {"source:0": 1}
            and bundle.scene_row_mapping.scene_to_trace_surface == {0: 0, 2: 1}
            and bundle.scene_row_mapping.trace_surface_to_scene == {0: 0, 1: 2},
            bundle.scene_row_mapping.to_jsonable() if bundle.scene_row_mapping is not None else "missing mapping",
        ),
        SceneSourceRowContractCheck(
            "Non-Sequential Scene Graph exposes separate source namespace",
            {"sources", "source:0"}.issubset(graph_ids),
            ", ".join(sorted(graph_ids)[:8]),
        ),
        SceneSourceRowContractCheck(
            "layout multi-source contract does not add pseudo-surface rows",
            "Illumination Source" not in multi_surfaces
            and multi_source_ids == {"source:left", "source:right"}
            and len(getattr(multi_system, "SDT", [])) == len(multi_rows),
            (
                f"rows={multi_surfaces} sources={sorted(multi_source_ids)} "
                f"system_surfaces={len(getattr(multi_system, 'SDT', []))}"
            ),
        ),
        SceneSourceRowContractCheck(
            "multi-source SceneBundle renders source objects independently",
            len(multi_bundle.sources) == 2 and multi_curve_source_count == 2,
            f"bundle_sources={len(multi_bundle.sources)} source_curves={multi_curve_source_count}",
        ),
        SceneSourceRowContractCheck(
            "source-row duplicate action creates a unique explicit source",
            duplicate_ok
            and duplicate_ids == ["source:left", "source:left_copy", "source:right"]
            and len(action_editor.rows) == action_surface_count,
            f"duplicate_ok={duplicate_ok} ids={duplicate_ids} surfaces={len(action_editor.rows)}",
        ),
        SceneSourceRowContractCheck(
            "source-row move action reorders sources without touching surfaces",
            move_ok
            and moved_ids == ["source:left", "source:right", "source:left_copy"]
            and len(action_editor.rows) == action_surface_count,
            f"move_ok={move_ok} ids={moved_ids} surfaces={len(action_editor.rows)}",
        ),
        SceneSourceRowContractCheck(
            "source-row delete action removes only the selected source",
            delete_ok
            and final_ids == ["source:left", "source:right"]
            and len(getattr(action_system, "SDT", [])) == action_surface_count,
            f"delete_ok={delete_ok} ids={final_ids} system_surfaces={len(getattr(action_system, 'SDT', []))}",
        ),
        SceneSourceRowContractCheck(
            "source-row actions preserve SceneBundle source/surface separation",
            len(action_bundle.sources) == 2
            and sum(1 for curve in action_bundle.surface_curves if getattr(curve, "kind", "") == "source") == 2
            and "Illumination Source" not in [row.surface for row in action_editor.rows],
            f"bundle_sources={len(action_bundle.sources)} rows={[row.surface for row in action_editor.rows]}",
        ),
    ]
    return checks


def _print_table(checks: list[SceneSourceRowContractCheck]) -> None:
    print("KrakenOS scene-source row contract validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate source scene rows stay separate from KrakenOS surface rows.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_scene_source_row_contract()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
