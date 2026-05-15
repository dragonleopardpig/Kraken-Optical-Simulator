from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.multi_source_illumination_example import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
from KrakenOS.UI.scene_builder import build_scene_bundle
from KrakenOS.UI.source_illumination_analysis import (
    SOURCE_ILLUMINATION_CSV_COLUMNS,
    collect_source_illumination_records,
    source_illumination_map_data_from_samples,
    source_illumination_hit_samples_from_records,
    source_illumination_record_detail_text,
    source_illumination_report_text,
    source_illumination_summary_text,
    source_illumination_table_values,
    iter_source_illumination_csv_rows,
)


@dataclass
class MultiSourceCheck:
    check: str
    ok: bool
    detail: str


def _last_text(seq, index: int, default: str = "") -> str:
    try:
        return str(np.asarray(seq[index], dtype=object).reshape(-1)[-1])
    except Exception:
        return default


def validate_multi_scene_sources() -> list[MultiSourceCheck]:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)
    sources = editor._collect_scene_sources(wavelength=float(SETTINGS["wavelength"]))
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
        ray_count_per_field=max((source.ray_count for source in sources), default=1),
    )
    editor.last_rays = rays
    editor._last_scene_bundle = bundle

    expected_ids = {"source:left", "source:right"}
    source_ids = {source.source_id for source in sources}
    ray_source_ids = {_last_text(getattr(rays, "SOURCE_ID", []), index) for index, _ in enumerate(getattr(rays, "SURFACE", []))}
    image_index = len(rows) - 1
    detector_hits = []
    for surfaces in getattr(rays, "SURFACE", []):
        surface_ids = np.asarray(surfaces, dtype=int).ravel()
        detector_hits.append(bool(surface_ids.size and int(surface_ids[-1]) == image_index))
    marker_count = sum(1 for curve in bundle.surface_curves if getattr(curve, "kind", "") == "source")
    label_texts = {str(getattr(label, "text", "")) for label in bundle.labels}
    graph_records = editor._collect_nonseq_scene_graph_records()
    graph_ids = {str(record.get("id", "")) for record in graph_records}
    auto_illumination_target = editor._source_illumination_target_index()
    ray_records = editor._collect_ray_analysis_records()
    illumination_records = editor._collect_source_illumination_records(image_index)
    service_illumination_records = collect_source_illumination_records(
        ray_records,
        image_index,
        rows[image_index].name,
        terminal_label_for_record=editor._source_illumination_terminal_label_for_record,
    )
    illumination_by_source = {str(record.get("source_id", "")): record for record in illumination_records}
    illumination_target_label = f"S{image_index}: {rows[image_index].name}"
    illumination_report_text = editor._source_illumination_report_text()
    service_report_text = source_illumination_report_text(illumination_records, illumination_target_label)
    service_summary = source_illumination_summary_text(illumination_records, illumination_target_label)
    service_csv_rows = list(iter_source_illumination_csv_rows(illumination_records))
    illumination_samples = editor._source_illumination_hit_samples(system, image_index)
    service_illumination_samples = source_illumination_hit_samples_from_records(
        ray_records,
        image_index,
        rows[image_index].name,
        hit_xy_for_hit=lambda hit: editor._hit_local_xy(system, image_index, hit),
        diagnostic_records=service_illumination_records,
    )
    illumination_map = editor._source_illumination_map_data(system, image_index)
    service_illumination_map = source_illumination_map_data_from_samples(
        illumination_samples,
        target_model=editor._source_illumination_target_model(illumination_samples),
    )
    aperture_index = next((index for index, row in enumerate(rows) if row.surface == "Aperture"), None)
    aperture_samples = editor._source_illumination_hit_samples(system, aperture_index) if aperture_index is not None else {}

    checks = [
        MultiSourceCheck(
            "layout is multi-source illumination example",
            TITLE == "Multi-Source Illumination Example",
            TITLE,
        ),
        MultiSourceCheck(
            "layout settings produce two SceneSource3D records",
            source_ids == expected_ids and len(sources) == 2,
            f"sources={sorted(source_ids)}",
        ),
        MultiSourceCheck(
            "each source is enabled physical illumination",
            all(source.enabled and source.physical and source.role == "illumination" for source in sources),
            ", ".join(f"{source.source_id}:{source.role}:{source.enabled}" for source in sources),
        ),
        MultiSourceCheck(
            "trace preserves both source IDs on rays",
            ray_source_ids == expected_ids,
            f"ray_source_ids={sorted(ray_source_ids)}",
        ),
        MultiSourceCheck(
            "all launched rays reach the shared detector",
            bool(detector_hits and all(detector_hits)),
            f"detector_hits={sum(detector_hits)}/{len(detector_hits)} detector=S{image_index}",
        ),
        MultiSourceCheck(
            "SceneBundle renders both source markers and labels",
            marker_count == 2 and {"Left illuminator", "Right illuminator"}.issubset(label_texts),
            f"source_markers={marker_count} labels={sorted(label_texts)}",
        ),
        MultiSourceCheck(
            "Non-Sequential Scene Graph exposes both sources",
            expected_ids.issubset(graph_ids),
            ", ".join(sorted(graph_ids)[:10]),
        ),
        MultiSourceCheck(
            "source illumination report separates hit power by source",
            set(illumination_by_source) == expected_ids
            and all(int(record.get("hit_rays", 0) or 0) == int(record.get("launched_rays", 0) or 0) for record in illumination_records)
            and all(float(record.get("throughput", 0.0) or 0.0) > 0.0 for record in illumination_records),
            ", ".join(
                f"{source_id}: hit={record.get('hit_rays')}/{record.get('launched_rays')} throughput={record.get('throughput')}"
                for source_id, record in sorted(illumination_by_source.items())
            ),
        ),
        MultiSourceCheck(
            "source illumination report contract is service-owned",
            illumination_report_text == service_report_text
            and "Total source power throughput" in service_report_text
            and service_summary.startswith(f"Target {illumination_target_label}:")
            and bool(illumination_records)
            and len(source_illumination_table_values(illumination_records[0])) > 0
            and "Footprint:" in source_illumination_record_detail_text(illumination_records[0])
            and len(service_csv_rows) == len(illumination_records)
            and tuple(service_csv_rows[0].keys()) == SOURCE_ILLUMINATION_CSV_COLUMNS,
            (
                f"records={len(illumination_records)}, csv_columns={len(SOURCE_ILLUMINATION_CSV_COLUMNS)}, "
                f"text_chars={len(service_report_text)}"
            ),
        ),
        MultiSourceCheck(
            "source illumination record/sample assembly is service-owned",
            illumination_records == service_illumination_records
            and np.allclose(np.asarray(illumination_samples["x"], dtype=float), np.asarray(service_illumination_samples["x"], dtype=float))
            and np.allclose(np.asarray(illumination_samples["y"], dtype=float), np.asarray(service_illumination_samples["y"], dtype=float))
            and np.allclose(np.asarray(illumination_samples["weights"], dtype=float), np.asarray(service_illumination_samples["weights"], dtype=float))
            and list(illumination_samples.get("source_ids", []) or []) == list(service_illumination_samples.get("source_ids", []) or [])
            and list(illumination_samples.get("source_names", []) or []) == list(service_illumination_samples.get("source_names", []) or [])
            and str(illumination_samples.get("coord", "")) == str(service_illumination_samples.get("coord", ""))
            and int(illumination_samples.get("launched_rays", 0) or 0) == int(service_illumination_samples.get("launched_rays", -1) or -1)
            and int(illumination_samples.get("hit_rays", 0) or 0) == int(service_illumination_samples.get("hit_rays", -1) or -1)
            and float(illumination_samples.get("hit_power", 0.0) or 0.0) == float(service_illumination_samples.get("hit_power", -1.0) or -1.0),
            (
                f"records={len(service_illumination_records)}, "
                f"samples={len(service_illumination_samples.get('source_ids', []) or [])}, "
                f"coord={service_illumination_samples.get('coord')}"
            ),
        ),
        MultiSourceCheck(
            "Auto source illumination target prefers detector/image",
            auto_illumination_target == image_index,
            f"auto_target={auto_illumination_target}, image={image_index}",
        ),
        MultiSourceCheck(
            "source illumination map samples preserve both sources",
            set(illumination_samples.get("source_ids", []) or []) == expected_ids
            and int(illumination_samples.get("hit_rays", 0) or 0) == int(illumination_samples.get("launched_rays", 0) or 0)
            and float(illumination_samples.get("hit_power", 0.0) or 0.0) > 0.0,
            (
                f"sources={sorted(set(illumination_samples.get('source_ids', []) or []))}, "
                f"events={len(illumination_samples.get('source_ids', []) or [])}, "
                f"hit={illumination_samples.get('hit_rays')}/{illumination_samples.get('launched_rays')}, "
                f"power={illumination_samples.get('hit_power')}"
            ),
        ),
        MultiSourceCheck(
            "source illumination map data is service-owned",
            int(illumination_map.get("bins", 0) or 0) == int(service_illumination_map.get("bins", -1) or -1)
            and np.allclose(np.asarray(illumination_map["hist"], dtype=float), np.asarray(service_illumination_map["hist"], dtype=float))
            and np.allclose(np.asarray(illumination_map["density"], dtype=float), np.asarray(service_illumination_map["density"], dtype=float))
            and set(str(item.get("source_id", "")) for item in illumination_map.get("source_centroids", []) or []) == expected_ids,
            (
                f"bins={illumination_map.get('bins')}, "
                f"events={len(illumination_map.get('source_ids', []) or [])}, "
                f"centroids={[item.get('source_id') for item in illumination_map.get('source_centroids', []) or []]}"
            ),
        ),
        MultiSourceCheck(
            "manual source illumination target supports pupil/aperture plane",
            aperture_index is not None
            and int(aperture_samples.get("hit_rays", 0) or 0) == int(aperture_samples.get("launched_rays", 0) or 0)
            and float(aperture_samples.get("hit_power", 0.0) or 0.0) > 0.0,
            (
                f"aperture={aperture_index}, "
                f"hit={aperture_samples.get('hit_rays')}/{aperture_samples.get('launched_rays')}, "
                f"power={aperture_samples.get('hit_power')}"
            ),
        ),
    ]
    return checks


def _print_table(checks: list[MultiSourceCheck]) -> None:
    print("KrakenOS multi-source validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for check in checks:
        print(f"{check.check} | {'PASS' if check.ok else 'FAIL'} | {check.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate layout-defined multiple scene sources.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a Markdown-style table.")
    args = parser.parse_args()
    checks = validate_multi_scene_sources()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        _print_table(checks)
    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
