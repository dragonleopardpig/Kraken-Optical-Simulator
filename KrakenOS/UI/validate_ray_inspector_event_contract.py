"""Validate Ray Inspector records against canonical ray-event CSV records."""

from __future__ import annotations

import argparse
import csv
import io
from dataclasses import asdict, dataclass
from typing import Iterable

from KrakenOS.UI.scene_builder import (
    RAY_ANALYSIS_CONTRACT_COLUMNS,
    RAY_EVENT_RECORD_COLUMNS,
    scene_bundle_ray_event_records,
)
from KrakenOS.UI.validate_branch_analysis import _load_traced_editor


DEFAULT_LAYOUTS = ("Right-Angle Beam-Splitter Illumination",)

INSPECTOR_CONTRACT_CSV_COLUMNS = (
    "ray_index",
    "branch_id",
    "branch_path",
    "termination",
    "last_surface",
    "terminal_media",
    "terminal_index",
    "analysis_source",
    *RAY_ANALYSIS_CONTRACT_COLUMNS,
)


@dataclass
class InspectorEventContractCheck:
    layout: str
    check: str
    ok: bool
    detail: str


def _csv_roundtrip(records: Iterable[dict[str, object]], columns: tuple[str, ...]) -> list[dict[str, str]]:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columns)
    writer.writeheader()
    for record in records:
        writer.writerow({column: record.get(column, "") for column in columns})
    buffer.seek(0)
    return list(csv.DictReader(buffer))


def _terminal_key(record: dict[str, object]) -> tuple[str, str, str]:
    return (
        str(record.get("ray_index", "") or ""),
        str(record.get("branch_id", "") or ""),
        str(record.get("branch_path", "") or ""),
    )


def _result(layout: str, check: str, ok: bool, detail: str) -> InspectorEventContractCheck:
    return InspectorEventContractCheck(layout=layout, check=check, ok=bool(ok), detail=str(detail))


def _contract_mismatches(
    inspector_rows: dict[tuple[str, str, str], dict[str, str]],
    terminal_rows: dict[tuple[str, str, str], dict[str, str]],
) -> list[str]:
    mismatches: list[str] = []
    for key, inspector in sorted(inspector_rows.items()):
        terminal = terminal_rows.get(key)
        if terminal is None:
            mismatches.append(f"{key}: missing terminal event")
            continue
        for column in RAY_ANALYSIS_CONTRACT_COLUMNS:
            if str(inspector.get(column, "") or "") != str(terminal.get(column, "") or ""):
                mismatches.append(
                    f"{key}:{column} inspector={inspector.get(column)!r} event={terminal.get(column)!r}"
                )
                break
        for left, right in (
            ("termination", "event_type"),
            ("last_surface", "surface"),
            ("terminal_media", "terminal_media"),
            ("terminal_index", "terminal_index"),
        ):
            if str(inspector.get(left, "") or "") != str(terminal.get(right, "") or ""):
                mismatches.append(
                    f"{key}:{left}/{right} inspector={inspector.get(left)!r} event={terminal.get(right)!r}"
                )
                break
    return mismatches


def _validate_layout(layout: str) -> list[InspectorEventContractCheck]:
    editor, _system, _rays, _wavelength = _load_traced_editor(layout)
    inspector_records = editor._collect_ray_analysis_records()
    bundle = editor._last_scene_bundle
    event_records = scene_bundle_ray_event_records(bundle)
    inspector_csv_rows = _csv_roundtrip(inspector_records, INSPECTOR_CONTRACT_CSV_COLUMNS)
    event_csv_rows = _csv_roundtrip(event_records, RAY_EVENT_RECORD_COLUMNS)
    terminal_csv_rows = [row for row in event_csv_rows if row.get("event_kind") == "terminal"]
    surface_csv_rows = [row for row in event_csv_rows if row.get("event_kind") == "surface"]

    inspector_by_key = {_terminal_key(row): row for row in inspector_csv_rows}
    terminal_by_key = {_terminal_key(row): row for row in terminal_csv_rows}
    detector_rows = [row for row in inspector_csv_rows if row.get("reaches_detector") == "True"]
    non_detector_rows = [row for row in inspector_csv_rows if row.get("reaches_detector") != "True"]
    branch_paths = {row.get("branch_path", "") for row in inspector_csv_rows if row.get("branch_path")}
    branch_ids = {row.get("branch_id", "") for row in inspector_csv_rows if row.get("branch_id")}
    split_surface_rows = [
        row
        for row in surface_csv_rows
        if str(row.get("interaction_model", "") or "").startswith("split_")
        or str(row.get("event_type", "") or "").startswith("split_")
    ]

    missing_columns = [
        column
        for column in RAY_ANALYSIS_CONTRACT_COLUMNS
        if any(column not in row for row in inspector_csv_rows)
    ]
    key_delta = set(inspector_by_key) ^ set(terminal_by_key)
    mismatches = _contract_mismatches(inspector_by_key, terminal_by_key)
    detector_contract_ok = bool(detector_rows) and all(
        row.get("terminal_policy_source") == "ui_nonseq_trace_request"
        and row.get("terminal_detector_surfaces") == "5"
        and row.get("terminal_trace_surface") == "5"
        and row.get("terminal_geometry_source") == "trace_event"
        and row.get("terminal_direction_source") == "trace_event"
        for row in detector_rows
    )

    return [
        _result(
            layout,
            "branched detector scene traced through canonical events",
            bool(inspector_csv_rows)
            and len(branch_paths) >= 3
            and len(branch_ids) >= 3
            and bool(detector_rows)
            and bool(non_detector_rows)
            and bool(split_surface_rows),
            (
                f"rays={len(inspector_csv_rows)} branches={len(branch_paths)} "
                f"detectors={len(detector_rows)} non_detectors={len(non_detector_rows)} "
                f"split_events={len(split_surface_rows)}"
            ),
        ),
        _result(
            layout,
            "Ray Inspector CSV contract columns are present after serialization",
            not missing_columns
            and all(row.get("analysis_source") == "ray_events" for row in inspector_csv_rows),
            (
                f"missing={missing_columns} "
                f"sources={sorted({row.get('analysis_source', '') for row in inspector_csv_rows})}"
            ),
        ),
        _result(
            layout,
            "Ray Inspector terminal keys match ray-event CSV terminal keys",
            not key_delta and len(inspector_by_key) == len(terminal_by_key) == len(inspector_csv_rows),
            f"inspector={len(inspector_by_key)} terminals={len(terminal_by_key)} delta={len(key_delta)}",
        ),
        _result(
            layout,
            "Ray Inspector launch terminal fields match ray-event CSV",
            not mismatches,
            "ok" if not mismatches else "; ".join(mismatches[:5]),
        ),
        _result(
            layout,
            "detector branch terminal policy survives both CSV shapes",
            detector_contract_ok,
            (
                f"detector_rows={len(detector_rows)} "
                f"paths={sorted({row.get('branch_path', '') for row in detector_rows})[:4]}"
            ),
        ),
    ]


def validate_ray_inspector_event_contract(
    layouts: Iterable[str] = DEFAULT_LAYOUTS,
) -> list[InspectorEventContractCheck]:
    checks: list[InspectorEventContractCheck] = []
    for layout in layouts:
        checks.extend(_validate_layout(layout))
    return checks


def _print_table(checks: list[InspectorEventContractCheck]) -> None:
    print("KrakenOS Ray Inspector / ray-event contract validation")
    print("layout | check | status | detail")
    print("--- | --- | --- | ---")
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{check.layout} | {check.check} | {status} | {check.detail}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compare Ray Inspector contract fields with canonical ray-event CSV "
            "terminal records."
        )
    )
    parser.add_argument("layouts", nargs="*", default=list(DEFAULT_LAYOUTS))
    parser.add_argument("--json", action="store_true", help="Print JSON records instead of a Markdown table.")
    args = parser.parse_args(argv)
    checks = validate_ray_inspector_event_contract(args.layouts)
    if args.json:
        import json

        print(json.dumps([asdict(check) for check in checks], indent=2, sort_keys=True))
    else:
        _print_table(checks)
    failed = [check for check in checks if not check.ok]
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
