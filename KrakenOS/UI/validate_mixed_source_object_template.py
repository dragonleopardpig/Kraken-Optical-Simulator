from __future__ import annotations

import argparse
import json
from copy import deepcopy
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.mixed_source_object_imaging_template import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle


@dataclass
class MixedSourceObjectCheck:
    check: str
    ok: bool
    detail: str


def _last_text(seq, index: int, default: str = "") -> str:
    try:
        return str(np.asarray(seq[index], dtype=object).reshape(-1)[-1])
    except Exception:
        return default


def validate_mixed_source_object_template() -> list[MixedSourceObjectCheck]:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)
    sources = editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
    source = sources[0] if sources else None
    system = _build_system_from_specs(SURFACES)
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(system, rays, float(SETTINGS["wavelength"]), max_radius, allow_full_pupil=False)
    bundle = build_scene_bundle(
        rows=rows,
        system=system,
        rays=rays,
        sources=sources,
        field_count=len(sources),
        ray_count_per_field=max((scene_source.ray_count for scene_source in sources), default=1),
        source_row_order=str(SETTINGS.get("scene_row_order", "after_object")),
    )
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle

    scene_mapping = editor._current_scene_row_mapping(sources)
    image_index = len(rows) - 1
    ray_source_ids = {_last_text(getattr(rays, "SOURCE_ID", []), index) for index, _ in enumerate(getattr(rays, "SURFACE", []))}
    detector_hits = []
    for surfaces in getattr(rays, "SURFACE", []):
        surface_ids = np.asarray(surfaces, dtype=int).ravel()
        detector_hits.append(bool(surface_ids.size and int(surface_ids[-1]) == image_index))
    target_choices = editor._scene_source_aim_target_choices()
    aim_result = editor.scene_source_direction_to_row(dict(getattr(source, "settings", {}) or {}), image_index)
    aim_vector = np.asarray(
        [aim_result["source_l"], aim_result["source_m"], aim_result["source_n"]],
        dtype=float,
    )
    source_direction = np.asarray(getattr(source, "direction", (np.nan, np.nan, np.nan)), dtype=float)
    marker_count = sum(1 for curve in bundle.surface_curves if getattr(curve, "kind", "") == "source")
    label_texts = {str(getattr(label, "text", "")) for label in bundle.labels}
    graph_records = editor._collect_nonseq_scene_graph_records()
    graph_ids = {str(record.get("id", "")) for record in graph_records}
    ray_records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    illumination_records = editor._collect_source_illumination_records(image_index, ray_records=ray_records)
    illumination_by_source = {str(record.get("source_id", "")): record for record in illumination_records}

    clipped_surfaces = deepcopy(SURFACES)
    clipped_surfaces[1]["diameter"] = 1.0
    clipped_settings = deepcopy(SETTINGS)
    clipped_settings["scene_sources"][0]["radius"] = 5.0
    clipped_settings["scene_sources"][0]["origin"] = [0.0, -80.0, 0.0]
    clipped_rows = _rows_from_layout_info({"surfaces": clipped_surfaces, "settings": clipped_settings})
    clipped_editor = _snapshot_editor(clipped_rows, clipped_settings)
    clipped_system = _build_system_from_specs(clipped_surfaces)
    clipped_rays = Kos.raykeeper(clipped_system)
    clipped_editor._trace_preview_rays(
        clipped_system,
        clipped_rays,
        float(clipped_settings["wavelength"]),
        max_radius,
        allow_full_pupil=False,
    )
    clipped_editor.last_system = clipped_system
    clipped_editor.last_rays = clipped_rays
    clipped_ray_records = clipped_editor._ray_analysis_records_for_trace(system=clipped_system, rays=clipped_rays)
    clipped_records = clipped_editor._collect_source_illumination_records(image_index, ray_records=clipped_ray_records)
    clipped_record = clipped_records[0] if clipped_records else {}
    clipped_samples = clipped_editor._source_illumination_hit_samples(
        clipped_system,
        image_index,
        ray_records=clipped_ray_records,
    )
    clipped_detail = clipped_editor._source_illumination_record_detail_text(clipped_record) if clipped_record else ""

    return [
        MixedSourceObjectCheck(
            "layout is mixed source/object imaging template",
            TITLE == "Mixed Source/Object Imaging Template",
            TITLE,
        ),
        MixedSourceObjectCheck(
            "layout defines one explicit physical scene source",
            bool(
                source is not None
                and len(sources) == 1
                and source.source_id == "source:illum"
                and source.physical
                and source.role == "illumination"
            ),
            f"sources={[(item.source_id, item.role, item.physical) for item in sources]}",
        ),
        MixedSourceObjectCheck(
            "visible scene row order puts source before Object",
            bool(
                scene_mapping.source_row_order == "before_object"
                and scene_mapping.source_id_to_scene == {"source:illum": 0}
                and scene_mapping.trace_surface_to_scene.get(0) == 1
            ),
            scene_mapping.to_jsonable(),
        ),
        MixedSourceObjectCheck(
            "source manager target choices include Object and Image rows",
            len(target_choices) == len(rows) and target_choices[0].startswith("0:") and target_choices[-1].startswith("2:"),
            ", ".join(target_choices),
        ),
        MixedSourceObjectCheck(
            "Aim Direction At Row(Image) matches the layout source direction",
            bool(np.allclose(aim_vector, source_direction, atol=5e-9)),
            f"aim={aim_vector.tolist()} source={source_direction.tolist()}",
        ),
        MixedSourceObjectCheck(
            "trace preserves the explicit source ID on every ray",
            ray_source_ids == {"source:illum"},
            f"ray_source_ids={sorted(ray_source_ids)}",
        ),
        MixedSourceObjectCheck(
            "all launched source rays reach the detector/Image row",
            bool(detector_hits and all(detector_hits)),
            f"detector_hits={sum(detector_hits)}/{len(detector_hits)} detector=S{image_index}",
        ),
        MixedSourceObjectCheck(
            "SceneBundle renders source marker and source label",
            marker_count == 1 and "Independent illuminator" in label_texts,
            f"source_markers={marker_count} labels={sorted(label_texts)}",
        ),
        MixedSourceObjectCheck(
            "Non-Sequential Scene Graph exposes the explicit source object",
            {"sources", "source:illum"}.issubset(graph_ids),
            ", ".join(sorted(graph_ids)[:10]),
        ),
        MixedSourceObjectCheck(
            "detector illumination report is source-aware",
            set(illumination_by_source) == {"source:illum"}
            and all(int(record.get("hit_rays", 0) or 0) == int(record.get("launched_rays", 0) or 0) for record in illumination_records)
            and all(float(record.get("throughput", 0.0) or 0.0) > 0.0 for record in illumination_records),
            ", ".join(
                f"{source_id}: hit={record.get('hit_rays')}/{record.get('launched_rays')} throughput={record.get('throughput')}"
                for source_id, record in sorted(illumination_by_source.items())
            ),
        ),
        MixedSourceObjectCheck(
            "source diagnostics identify target misses and dominant loss terminal",
            bool(
                int(clipped_record.get("missed_rays", 0) or 0) > 0
                and float(clipped_record.get("vignetted_fraction", 0.0) or 0.0) > 0.0
                and float(clipped_record.get("missed_power", 0.0) or 0.0) > 0.0
                and str(clipped_record.get("dominant_loss", "") or "None") != "None"
            ),
            (
                f"hit={clipped_record.get('hit_rays')}/{clipped_record.get('launched_rays')}, "
                f"missed={clipped_record.get('missed_rays')}, "
                f"loss={clipped_record.get('dominant_loss')}, "
                f"breakdown={clipped_record.get('missed_terminal_breakdown')}"
            ),
        ),
        MixedSourceObjectCheck(
            "source illumination map samples carry loss summary",
            int(clipped_samples.get("missed_rays", 0) or 0) > 0
            and str(clipped_samples.get("loss_summary", "") or "None") != "None",
            (
                f"hit={clipped_samples.get('hit_rays')}/{clipped_samples.get('launched_rays')}, "
                f"loss_summary={clipped_samples.get('loss_summary')}"
            ),
        ),
        MixedSourceObjectCheck(
            "source diagnostics detail pane includes power and loss breakdown",
            "Power:" in clipped_detail and "Loss:" in clipped_detail and "Footprint:" in clipped_detail,
            clipped_detail.replace("\n", " | "),
        ),
    ]


def _print_table(checks: list[MixedSourceObjectCheck]) -> None:
    print("KrakenOS mixed source/object template validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the mixed source/object imaging layout template.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_mixed_source_object_template()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
