from __future__ import annotations

import argparse
import csv
import io
import inspect
from dataclasses import asdict, dataclass

import numpy as np

from KrakenOS.UI.detector_aperture_analysis import (
    DETECTOR_APERTURE_CSV_COLUMNS,
    collect_detector_aperture_records,
    detector_aperture_report_text,
    detector_aperture_summary_text,
    detector_aperture_table_values,
    iter_detector_aperture_csv_rows,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


@dataclass
class DetectorApertureValidationResult:
    check: str
    ok: bool
    detail: str


def _result(check: str, ok: bool, detail: str) -> DetectorApertureValidationResult:
    return DetectorApertureValidationResult(check=check, ok=bool(ok), detail=str(detail))


def _synthetic_records() -> list[dict[str, object]]:
    return [
        {
            "ray_index": 0,
            "field_index": 0,
            "source_ray_index": 0,
            "source_weight": 1.0,
            "source_power": 2.0,
            "branch_power": 0.8,
            "terminal_detector_surfaces": "2",
            "reaches_detector": True,
            "reaches_image": True,
            "last_surface": 2,
            "terminal_trace_surface": 2,
            "termination": "image",
            "status": "Image",
        },
        {
            "ray_index": 1,
            "field_index": 0,
            "source_ray_index": 1,
            "source_weight": 1.0,
            "source_power": 2.0,
            "branch_power": 0.5,
            "terminal_detector_surfaces": "2",
            "reaches_detector": False,
            "reaches_image": False,
            "last_surface": 1,
            "detector_miss_surface": 2,
            "detector_miss_status": "outside_active_area",
            "detector_miss_distance_mm": 10.0,
            "detector_miss_radial_mm": 3.1,
            "detector_miss_half_mm": 2.0,
            "detector_miss_x_mm": 3.1,
            "detector_miss_y_mm": 0.2,
            "detector_miss_active_width_mm": 4.0,
            "detector_miss_active_height_mm": 2.0,
            "detector_miss_normal_error_mm": 0.0,
            "termination": "missed_image",
            "status": "Missed image",
        },
        {
            "ray_index": 2,
            "field_index": 0,
            "source_ray_index": 2,
            "source_weight": 1.0,
            "source_power": 2.0,
            "branch_power": 0.2,
            "terminal_detector_surfaces": "2",
            "reaches_detector": False,
            "last_surface": 1,
            "termination": "stopped_at_surface_1",
            "status": "Stop @ S1",
        },
    ]


def _csv_roundtrip(records: list[dict[str, object]]) -> list[dict[str, str]]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=DETECTOR_APERTURE_CSV_COLUMNS)
    writer.writeheader()
    writer.writerows(iter_detector_aperture_csv_rows(records))
    buffer.seek(0)
    return list(csv.DictReader(buffer))


def validate_detector_aperture_analysis() -> list[DetectorApertureValidationResult]:
    records = collect_detector_aperture_records(
        _synthetic_records(),
        detector_surface_indices={2},
        terminal_label_for_surface=lambda surface: f"S{surface} Detector: Synthetic",
    )
    record = records[0] if records else {}
    table_values = detector_aperture_table_values(record)
    summary = detector_aperture_summary_text(records)
    report = detector_aperture_report_text(records)
    csv_rows = _csv_roundtrip(records)
    inferred_records = collect_detector_aperture_records(
        [
            {"ray_index": 10, "source_ray_index": 10, "reaches_detector": True, "last_surface": 3, "termination": "image"},
            {"ray_index": 11, "source_ray_index": 11, "reaches_detector": True, "last_surface": 4, "termination": "image"},
        ]
    )

    editor_collect_source = inspect.getsource(KrakenLayoutEditor._collect_detector_aperture_records)
    refresh_source = inspect.getsource(KrakenLayoutEditor._refresh_detector_aperture_report)
    menu_source = inspect.getsource(KrakenLayoutEditor.open_detector_aperture_report)
    results_source = inspect.getsource(KrakenLayoutEditor._update_results)
    status_source = inspect.getsource(KrakenLayoutEditor._detector_aperture_status_suffix)
    try:
        editor, system, rays, _wavelength = _load_traced_editor("Right-Angle Beam-Splitter Illumination")
        traced_ray_records = editor._ray_analysis_records_for_trace(system=system, rays=rays)
        traced_aperture_records = editor._collect_detector_aperture_records(ray_records=traced_ray_records)
        traced_error = ""
    except Exception as exc:
        traced_aperture_records = []
        traced_error = str(exc)

    return [
        _result(
            "detector aperture service groups hit/miss/other paths",
            len(records) == 1
            and int(record.get("detector_surface", -1)) == 2
            and int(record.get("ray_count", 0)) == 3
            and int(record.get("hit_count", 0)) == 1
            and int(record.get("miss_count", 0)) == 1
            and int(record.get("other_count", 0)) == 1,
            f"records={records}",
        ),
        _result(
            "miss margin and power accounting survive aggregation",
            abs(float(record.get("hit_power", 0.0)) - 1.6) < 1e-12
            and abs(float(record.get("miss_power", 0.0)) - 1.0) < 1e-12
            and abs(float(record.get("total_input_power", 0.0)) - 6.0) < 1e-12
            and np.isclose(float(record.get("worst_miss_margin_mm", 0.0)), 1.1),
            (
                f"hit_power={record.get('hit_power')} miss_power={record.get('miss_power')} "
                f"input={record.get('total_input_power')} margin={record.get('worst_miss_margin_mm')}"
            ),
        ),
        _result(
            "table, report, and CSV expose detector aperture diagnostics",
            len(table_values) == 12
            and "hits=1" in report
            and "misses=1" in report
            and "hits=1 (33.33%)" in summary
            and csv_rows
            and csv_rows[0].get("worst_miss_ray_index") == "1",
            f"summary={summary} csv={csv_rows[:1]}",
        ),
        _result(
            "service can infer multiple detector hit surfaces from events",
            [int(item.get("detector_surface", -1)) for item in inferred_records] == [3, 4]
            and all(int(item.get("hit_count", 0) or 0) == 1 for item in inferred_records),
            f"inferred={inferred_records}",
        ),
        _result(
            "layout editor routes detector aperture report through scene ray records",
            "collect_detector_aperture_records" in editor_collect_source
            and "_active_ray_analysis_records" in refresh_source
            and "DETECTOR_APERTURE_TABLE_COLUMNS" in menu_source,
            "editor hooks present",
        ),
        _result(
            "results panel and status bar expose detector aperture health",
            "Detector aperture" in results_source
            and "Detector misses" in results_source
            and "detector misses" in status_source
            and "_detector_aperture_records" in results_source,
            "results/status hooks present",
        ),
        _result(
            "traced non-sequential detector scene produces aperture records",
            bool(traced_aperture_records)
            and any(int(item.get("hit_count", 0) or 0) > 0 for item in traced_aperture_records),
            traced_error or f"records={traced_aperture_records}",
        ),
    ]


def _print_table(results: list[DetectorApertureValidationResult]) -> None:
    print("KrakenOS detector aperture validation")
    print("check | status | detail")
    print("--- | --- | ---")
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"{result.check} | {status} | {result.detail}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Validate detector hit/miss aperture aggregation.")
    parser.add_argument("--json", action="store_true", help="Print JSON result payload.")
    args = parser.parse_args(argv)
    results = validate_detector_aperture_analysis()
    if args.json:
        import json

        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        _print_table(results)
    if not all(result.ok for result in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
