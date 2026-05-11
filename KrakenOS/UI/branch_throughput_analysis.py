from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

import numpy as np


BRANCH_THROUGHPUT_FILTER_DEFAULT = "All paths"
BRANCH_THROUGHPUT_FILTER_LEGACY_DEFAULTS = {"All branches", "All arms", "Common"}

BRANCH_THROUGHPUT_TABLE_COLUMNS: tuple[str, ...] = (
    "output",
    "code",
    "terminal",
    "rays",
    "sources",
    "detector",
    "power",
    "throughput",
    "op",
    "distance",
    "path",
)

BRANCH_THROUGHPUT_TABLE_HEADINGS: dict[str, str] = {
    "output": "Output / path",
    "code": "Code",
    "terminal": "Terminal",
    "rays": "Rays",
    "sources": "Sources",
    "detector": "Detector hits",
    "power": "Power sum",
    "throughput": "Throughput",
    "op": "Mean OP [mm]",
    "distance": "Mean dist [mm]",
    "path": "Trace path",
}

BRANCH_THROUGHPUT_TABLE_LAYOUT: tuple[tuple[str, int, str], ...] = (
    ("output", 150, "w"),
    ("code", 70, "center"),
    ("terminal", 220, "w"),
    ("rays", 70, "center"),
    ("sources", 70, "center"),
    ("detector", 90, "center"),
    ("power", 95, "e"),
    ("throughput", 90, "e"),
    ("op", 95, "e"),
    ("distance", 105, "e"),
    ("path", 260, "w"),
)

BRANCH_THROUGHPUT_CSV_COLUMNS: tuple[str, ...] = (
    "output",
    "branch_code",
    "branch_path",
    "terminal",
    "terminal_surface",
    "ray_count",
    "source_ray_count",
    "detector_hits",
    "power_sum",
    "throughput",
    "mean_op",
    "mean_distance",
    "total_input_power",
)


def _safe_positive_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except Exception:
        return default
    if not np.isfinite(result):
        return default
    return max(result, 0.0)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def format_branch_throughput_value(value: object) -> str:
    try:
        numeric = float(value)
    except Exception:
        text = str(value).strip()
        return text if text else "-"
    if not np.isfinite(numeric):
        return "-"
    return f"{numeric:.6g}"


def format_branch_throughput_percent(value: object) -> str:
    try:
        numeric = float(value)
    except Exception:
        return "-"
    if not np.isfinite(numeric):
        return "-"
    return f"{100.0 * numeric:.4g}%"


def branch_path_selector_sequence(branch_path: str) -> list[str]:
    selectors: list[str] = []
    for component in str(branch_path or "").split("->"):
        text = component.strip()
        if "/" not in text:
            continue
        selector = text.rsplit("/", 1)[1].strip().lower()
        selectors.append({"transmit": "T", "reflect": "R"}.get(selector, selector or "?"))
    return selectors


def branch_output_label(branch_path: str) -> str:
    selectors = branch_path_selector_sequence(branch_path)
    if not selectors:
        return "Primary path"
    code = "".join(selectors)
    tail = "".join(selectors[-2:])
    if tail in {"TR", "RT"}:
        return "Detector output port"
    if tail in {"TT", "RR"}:
        return "Source return port"
    if len(selectors) == 1:
        return "Transmit path" if selectors[0] == "T" else "Reflect path" if selectors[0] == "R" else f"{selectors[0]} path"
    return f"Path {code}"


def _terminal_surface_value(last_surface: object) -> int | str:
    if last_surface is None:
        return ""
    try:
        return int(last_surface)
    except Exception:
        return ""


def collect_branch_throughput_records(
    ray_records: list[dict[str, object]],
    *,
    terminal_label_for_record: Callable[[dict[str, object]], str],
    is_detector_surface: Callable[[object], bool],
    output_label_for_path: Callable[[str], str] = branch_output_label,
) -> list[dict[str, object]]:
    if not ray_records:
        return []

    source_input: dict[tuple[int, int], float] = {}
    groups: dict[tuple[str, str, str, int | str | None], dict[str, object]] = {}
    for record in ray_records:
        field_index = _safe_int(record.get("field_index", 0), 0)
        source_ray_index = _safe_int(record.get("source_ray_index", record.get("ray_index", 0)), 0)
        source_weight = _safe_positive_float(record.get("source_weight"), 1.0)
        source_power = _safe_positive_float(record.get("source_power"), 1.0)
        source_key = (field_index, source_ray_index)
        source_input[source_key] = max(source_input.get(source_key, 0.0), source_weight * source_power)

        branch_path = str(record.get("branch_path", "") or "").strip()
        branch_code = "".join(branch_path_selector_sequence(branch_path)) or "primary"
        output_label = output_label_for_path(branch_path)
        last_surface = record.get("last_surface")
        terminal_surface = _terminal_surface_value(last_surface)
        terminal = terminal_label_for_record(record)
        key = (output_label, branch_code, branch_path, terminal_surface)
        entry = groups.get(key)
        if entry is None:
            entry = {
                "output": output_label,
                "branch_code": branch_code,
                "branch_path": branch_path or "primary",
                "terminal": terminal,
                "terminal_surface": terminal_surface,
                "ray_count": 0,
                "source_ray_count": 0,
                "_sources": set(),
                "detector_hits": 0,
                "power_sum": 0.0,
                "distance_weighted_sum": 0.0,
                "op_weighted_sum": 0.0,
            }
            groups[key] = entry

        branch_power = _safe_positive_float(record.get("branch_power"), np.nan)
        if not np.isfinite(branch_power):
            branch_power = _safe_positive_float(record.get("transmission"), 1.0)
        effective_power = branch_power * source_weight * source_power
        entry["ray_count"] = int(entry["ray_count"]) + 1
        entry["_sources"].add(source_key)  # type: ignore[union-attr]
        if is_detector_surface(last_surface):
            entry["detector_hits"] = int(entry["detector_hits"]) + 1
        entry["power_sum"] = float(entry["power_sum"]) + effective_power
        distance = _safe_positive_float(record.get("distance"), 0.0)
        op = _safe_positive_float(record.get("op"), 0.0)
        entry["distance_weighted_sum"] = float(entry["distance_weighted_sum"]) + effective_power * distance
        entry["op_weighted_sum"] = float(entry["op_weighted_sum"]) + effective_power * op

    total_input = float(sum(source_input.values()))
    records: list[dict[str, object]] = []
    for entry in groups.values():
        power_sum = float(entry["power_sum"])
        source_set = set(entry.pop("_sources", set()) or set())
        entry["source_ray_count"] = len(source_set)
        entry["throughput"] = power_sum / total_input if total_input > 0.0 else np.nan
        entry["mean_distance"] = float(entry["distance_weighted_sum"]) / power_sum if power_sum > 0.0 else np.nan
        entry["mean_op"] = float(entry["op_weighted_sum"]) / power_sum if power_sum > 0.0 else np.nan
        entry["total_input_power"] = total_input
        records.append(entry)

    records.sort(
        key=lambda item: (
            str(item.get("output", "")),
            str(item.get("branch_code", "")),
            str(item.get("terminal", "")),
            str(item.get("branch_path", "")),
        )
    )
    return records


def normalize_branch_throughput_filter_label(value: object) -> str:
    text = str(value or "").strip()
    if not text or text in BRANCH_THROUGHPUT_FILTER_LEGACY_DEFAULTS:
        return BRANCH_THROUGHPUT_FILTER_DEFAULT
    return text


def branch_throughput_filter_choices(records: list[dict[str, object]]) -> list[str]:
    choices = [BRANCH_THROUGHPUT_FILTER_DEFAULT]
    for prefix, key in (
        ("Output", "output"),
        ("Code", "branch_code"),
        ("Terminal", "terminal"),
    ):
        values = sorted({str(record.get(key, "") or "").strip() for record in records})
        for value in values:
            if value:
                choices.append(f"{prefix}: {value}")
    return choices


def branch_throughput_filter_matches(record: dict[str, object], filter_text: str) -> bool:
    text = normalize_branch_throughput_filter_label(filter_text)
    if text == BRANCH_THROUGHPUT_FILTER_DEFAULT:
        return True
    prefix, separator, value = text.partition(":")
    if not separator:
        return True
    key = {
        "Output": "output",
        "Code": "branch_code",
        "Terminal": "terminal",
    }.get(prefix.strip())
    if not key:
        return True
    return str(record.get(key, "") or "").strip() == value.strip()


def filtered_branch_throughput_records(records: list[dict[str, object]], filter_text: str) -> list[dict[str, object]]:
    return [record for record in records if branch_throughput_filter_matches(record, filter_text)]


def branch_throughput_summary_text(
    records: list[dict[str, object]],
    all_records: list[dict[str, object]],
    filter_text: str,
) -> str:
    if not all_records:
        return "No path throughput data. Click Update first."
    total_power = sum(float(record.get("power_sum", 0.0) or 0.0) for record in records)
    total_input = float(all_records[0].get("total_input_power", 0.0) or 0.0)
    throughput = total_power / total_input if total_input > 0.0 else np.nan
    return (
        f"{len(records)}/{len(all_records)} path/output group(s) | filter={filter_text} | input={total_input:.6g} | "
        f"output sum={total_power:.6g} | total throughput={format_branch_throughput_percent(throughput)}"
    )


def branch_throughput_table_values(record: dict[str, object]) -> tuple[object, ...]:
    return (
        record.get("output", ""),
        record.get("branch_code", ""),
        record.get("terminal", ""),
        int(record.get("ray_count", 0) or 0),
        int(record.get("source_ray_count", 0) or 0),
        int(record.get("detector_hits", 0) or 0),
        format_branch_throughput_value(record.get("power_sum")),
        format_branch_throughput_percent(record.get("throughput")),
        format_branch_throughput_value(record.get("mean_op")),
        format_branch_throughput_value(record.get("mean_distance")),
        record.get("branch_path", ""),
    )


def branch_throughput_report_text(
    records: list[dict[str, object]],
    all_records: list[dict[str, object]],
    filter_text: str,
) -> str:
    if not records:
        if all_records:
            return f"# KrakenOS Path Throughput Report\n\nFilter: {filter_text}\n\nNo path throughput data matches this filter.\n"
        return "# KrakenOS Path Throughput Report\n\nNo path throughput data. Click Update first.\n"
    total_input = float(all_records[0].get("total_input_power", 0.0) or 0.0) if all_records else 0.0
    total_power = sum(float(record.get("power_sum", 0.0) or 0.0) for record in records)
    throughput = total_power / total_input if total_input > 0.0 else np.nan
    lines = [
        "# KrakenOS Path Throughput Report",
        "",
        f"Filter: {filter_text}",
        f"Input source weight: {total_input:.6g}",
        f"Summed output path power: {total_power:.6g}",
        f"Total throughput: {format_branch_throughput_percent(throughput)}",
        "",
    ]
    for record in records:
        lines.append(
            "- {output} | code={code} | terminal={terminal} | rays={rays} | sources={sources} | "
            "detector_hits={detector_hits} | power={power:.6g} | throughput={throughput} | mean_op={op} mm | path={path}".format(
                output=record.get("output", ""),
                code=record.get("branch_code", ""),
                terminal=record.get("terminal", ""),
                rays=int(record.get("ray_count", 0) or 0),
                sources=int(record.get("source_ray_count", 0) or 0),
                detector_hits=int(record.get("detector_hits", 0) or 0),
                power=float(record.get("power_sum", 0.0) or 0.0),
                throughput=format_branch_throughput_percent(record.get("throughput")),
                op=format_branch_throughput_value(record.get("mean_op")),
                path=record.get("branch_path", ""),
            )
        )
    return "\n".join(lines).strip() + "\n"


def iter_branch_throughput_csv_rows(records: list[dict[str, object]]):
    for record in records:
        yield {column: record.get(column, "") for column in BRANCH_THROUGHPUT_CSV_COLUMNS}


def write_branch_throughput_csv(path: str | Path, records: list[dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_THROUGHPUT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_branch_throughput_csv_rows(records))
