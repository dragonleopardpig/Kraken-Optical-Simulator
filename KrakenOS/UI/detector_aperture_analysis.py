from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable, Iterable

import numpy as np


DETECTOR_APERTURE_TABLE_COLUMNS: tuple[str, ...] = (
    "detector",
    "rays",
    "hits",
    "misses",
    "other",
    "hit_fraction",
    "hit_power",
    "miss_power",
    "worst_margin",
    "worst_ray",
    "worst_xy",
    "dominant",
)

DETECTOR_APERTURE_TABLE_HEADINGS: dict[str, str] = {
    "detector": "Detector",
    "rays": "Rays",
    "hits": "Hits",
    "misses": "Misses",
    "other": "Other",
    "hit_fraction": "Hit %",
    "hit_power": "Hit power",
    "miss_power": "Miss power",
    "worst_margin": "Worst miss [mm]",
    "worst_ray": "Worst ray",
    "worst_xy": "Worst local X/Y [mm]",
    "dominant": "Dominant terminal",
}

DETECTOR_APERTURE_TABLE_LAYOUT: tuple[tuple[str, int, str], ...] = (
    ("detector", 230, "w"),
    ("rays", 70, "center"),
    ("hits", 70, "center"),
    ("misses", 70, "center"),
    ("other", 70, "center"),
    ("hit_fraction", 82, "e"),
    ("hit_power", 90, "e"),
    ("miss_power", 90, "e"),
    ("worst_margin", 115, "e"),
    ("worst_ray", 80, "center"),
    ("worst_xy", 150, "e"),
    ("dominant", 220, "w"),
)

DETECTOR_APERTURE_CSV_COLUMNS: tuple[str, ...] = (
    "detector_surface",
    "detector",
    "ray_count",
    "source_ray_count",
    "hit_count",
    "miss_count",
    "other_count",
    "hit_fraction",
    "miss_fraction",
    "total_input_power",
    "hit_power",
    "miss_power",
    "other_power",
    "worst_miss_margin_mm",
    "worst_miss_ray_index",
    "worst_miss_x_mm",
    "worst_miss_y_mm",
    "worst_miss_radial_mm",
    "worst_miss_half_mm",
    "worst_miss_distance_mm",
    "worst_miss_normal_error_mm",
    "dominant_terminal",
)


def _safe_float(value: object, default: float = np.nan) -> float:
    try:
        result = float(value)
    except Exception:
        return default
    return float(result) if np.isfinite(result) else default


def _safe_positive_float(value: object, default: float = 0.0) -> float:
    value_float = _safe_float(value, default)
    if not np.isfinite(value_float):
        return default
    return max(float(value_float), 0.0)


def _safe_int_or_none(value: object) -> int | None:
    text = str(value if value is not None else "").strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def _safe_int(value: object, default: int = 0) -> int:
    result = _safe_int_or_none(value)
    return default if result is None else int(result)


def _bool_value(value: object) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    text = str(value if value is not None else "").strip().lower()
    if text in {"1", "true", "yes", "on", "hit", "detector"}:
        return True
    if text in {"0", "false", "no", "off", "none", ""}:
        return False
    return bool(value)


def _int_list(value: object) -> list[int]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        for char in "[]();":
            text = text.replace(char, ",")
        parts = [part.strip() for part in text.replace(" ", ",").split(",")]
    else:
        try:
            parts = [str(item).strip() for item in np.asarray(value, dtype=object).reshape(-1)]
        except Exception:
            parts = [str(value).strip()]
    result: list[int] = []
    for part in parts:
        if not part:
            continue
        parsed = _safe_int_or_none(part)
        if parsed is not None:
            result.append(int(parsed))
    return result


def _source_key(record: dict[str, object]) -> tuple[int, int]:
    return (
        _safe_int(record.get("field_index", 0), 0),
        _safe_int(record.get("source_ray_index", record.get("ray_index", 0)), 0),
    )


def _source_input_power(record: dict[str, object]) -> float:
    source_weight = _safe_positive_float(record.get("source_weight"), 1.0)
    source_power = _safe_positive_float(record.get("source_power"), 1.0)
    return float(source_weight * source_power)


def _effective_path_power(record: dict[str, object]) -> float:
    branch_power = _safe_positive_float(record.get("branch_power"), np.nan)
    if not np.isfinite(branch_power):
        branch_power = _safe_positive_float(record.get("transmission"), 1.0)
    return float(branch_power * _source_input_power(record))


def _record_hit_detector_surface(record: dict[str, object], detector_set: set[int]) -> int | None:
    if not _bool_value(record.get("reaches_detector", False)) and not _bool_value(record.get("reaches_image", False)):
        return None
    for key in ("terminal_trace_surface", "folded_detector_surface", "last_surface"):
        surface = _safe_int_or_none(record.get(key))
        if surface is not None and (not detector_set or surface in detector_set):
            return int(surface)
    return None


def _record_miss_detector_surface(record: dict[str, object], explicit_detectors: Iterable[int]) -> int | None:
    for key in ("detector_miss_surface", "folded_detector_surface"):
        surface = _safe_int_or_none(record.get(key))
        if surface is not None:
            return int(surface)
    miss_status = str(record.get("detector_miss_status", "") or "").strip().lower()
    termination = str(record.get("termination", "") or "").strip().lower()
    status = str(record.get("status", "") or "").strip().lower()
    if "miss" not in miss_status and "missed" not in termination and "missed" not in status:
        return None
    explicit = list(explicit_detectors)
    if len(explicit) == 1:
        return int(explicit[0])
    return None


def _dominant_count_text(counts: dict[str, int]) -> str:
    if not counts:
        return ""
    terminal, count = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0]
    return f"{terminal} ({count})"


def _miss_margin(record: dict[str, object]) -> float:
    candidates: list[float] = []
    radial = _safe_float(record.get("detector_miss_radial_mm"))
    half = _safe_float(record.get("detector_miss_half_mm"))
    if np.isfinite(radial) and np.isfinite(half):
        candidates.append(float(radial - half))

    x_value = _safe_float(record.get("detector_miss_x_mm"))
    y_value = _safe_float(record.get("detector_miss_y_mm"))
    width = _safe_float(record.get("detector_miss_active_width_mm"))
    height = _safe_float(record.get("detector_miss_active_height_mm"))
    if np.isfinite(x_value) and np.isfinite(width) and width > 0.0:
        candidates.append(float(abs(x_value) - 0.5 * width))
    if np.isfinite(y_value) and np.isfinite(height) and height > 0.0:
        candidates.append(float(abs(y_value) - 0.5 * height))

    finite = [value for value in candidates if np.isfinite(value)]
    return max(finite) if finite else np.nan


def _format_value(value: object) -> str:
    numeric = _safe_float(value)
    if not np.isfinite(numeric):
        text = str(value if value is not None else "").strip()
        return text if text else "-"
    return f"{numeric:.6g}"


def _format_percent(value: object) -> str:
    numeric = _safe_float(value)
    if not np.isfinite(numeric):
        return "-"
    return f"{100.0 * numeric:.4g}%"


def _format_xy(record: dict[str, object]) -> str:
    x_value = _safe_float(record.get("worst_miss_x_mm"))
    y_value = _safe_float(record.get("worst_miss_y_mm"))
    if not np.isfinite(x_value) or not np.isfinite(y_value):
        return "-"
    return f"{x_value:.6g}, {y_value:.6g}"


def _terminal_label(record: dict[str, object]) -> str:
    termination = str(record.get("termination", "") or "").strip()
    status = str(record.get("status", "") or "").strip()
    if termination:
        return termination
    if status:
        return status
    return "terminal"


def _new_entry(surface: int, label: str) -> dict[str, object]:
    return {
        "detector_surface": int(surface),
        "detector": str(label or f"S{surface}"),
        "ray_count": 0,
        "source_ray_count": 0,
        "_source_input": {},
        "hit_count": 0,
        "miss_count": 0,
        "other_count": 0,
        "hit_power": 0.0,
        "miss_power": 0.0,
        "other_power": 0.0,
        "_terminal_counts": {},
        "worst_miss_margin_mm": np.nan,
        "worst_miss_ray_index": "",
        "worst_miss_x_mm": "",
        "worst_miss_y_mm": "",
        "worst_miss_radial_mm": "",
        "worst_miss_half_mm": "",
        "worst_miss_distance_mm": "",
        "worst_miss_normal_error_mm": "",
    }


def collect_detector_aperture_records(
    ray_records: list[dict[str, object]],
    *,
    detector_surface_indices: Iterable[int] | None = None,
    terminal_label_for_surface: Callable[[int], str] | None = None,
) -> list[dict[str, object]]:
    """Aggregate hit/miss aperture diagnostics by detector surface."""
    detector_indices = [] if detector_surface_indices is None else list(detector_surface_indices)
    if not ray_records and not detector_indices:
        return []

    detector_set = {int(surface) for surface in detector_indices}
    for record in ray_records:
        detector_set.update(_int_list(record.get("terminal_detector_surfaces")))
        miss_surface = _safe_int_or_none(record.get("detector_miss_surface"))
        if miss_surface is not None:
            detector_set.add(int(miss_surface))
        hit_surface = _record_hit_detector_surface(record, set())
        if hit_surface is not None:
            detector_set.add(int(hit_surface))
    if not detector_set:
        return []

    label_for_surface = terminal_label_for_surface or (lambda surface: f"S{int(surface)}")
    entries = {
        int(surface): _new_entry(int(surface), label_for_surface(int(surface)))
        for surface in sorted(detector_set)
    }

    for record in ray_records:
        explicit_detectors = _int_list(record.get("terminal_detector_surfaces"))
        hit_surface = _record_hit_detector_surface(record, detector_set)
        miss_surface = _record_miss_detector_surface(record, explicit_detectors)
        candidate_surfaces = set(explicit_detectors)
        if hit_surface is not None:
            candidate_surfaces.add(int(hit_surface))
        if miss_surface is not None:
            candidate_surfaces.add(int(miss_surface))
        candidate_surfaces &= detector_set
        if not candidate_surfaces and len(detector_set) == 1:
            candidate_surfaces = set(detector_set)
        if not candidate_surfaces:
            continue

        effective_power = _effective_path_power(record)
        source_key = _source_key(record)
        source_input = _source_input_power(record)
        terminal_label = _terminal_label(record)
        for surface in sorted(candidate_surfaces):
            entry = entries[int(surface)]
            entry["ray_count"] = int(entry["ray_count"]) + 1
            source_input_map = entry["_source_input"]
            if isinstance(source_input_map, dict):
                source_input_map[source_key] = max(float(source_input_map.get(source_key, 0.0)), source_input)
            terminal_counts = entry["_terminal_counts"]
            if isinstance(terminal_counts, dict):
                terminal_counts[terminal_label] = int(terminal_counts.get(terminal_label, 0)) + 1

            if hit_surface == surface:
                entry["hit_count"] = int(entry["hit_count"]) + 1
                entry["hit_power"] = float(entry["hit_power"]) + effective_power
                continue
            if miss_surface == surface:
                entry["miss_count"] = int(entry["miss_count"]) + 1
                entry["miss_power"] = float(entry["miss_power"]) + effective_power
                margin = _miss_margin(record)
                previous_margin = _safe_float(entry.get("worst_miss_margin_mm"))
                if np.isfinite(margin) and (not np.isfinite(previous_margin) or margin > previous_margin):
                    entry["worst_miss_margin_mm"] = float(margin)
                    entry["worst_miss_ray_index"] = record.get("ray_index", "")
                    entry["worst_miss_x_mm"] = record.get("detector_miss_x_mm", "")
                    entry["worst_miss_y_mm"] = record.get("detector_miss_y_mm", "")
                    entry["worst_miss_radial_mm"] = record.get("detector_miss_radial_mm", "")
                    entry["worst_miss_half_mm"] = record.get("detector_miss_half_mm", "")
                    entry["worst_miss_distance_mm"] = record.get("detector_miss_distance_mm", "")
                    entry["worst_miss_normal_error_mm"] = record.get("detector_miss_normal_error_mm", "")
                continue
            entry["other_count"] = int(entry["other_count"]) + 1
            entry["other_power"] = float(entry["other_power"]) + effective_power

    records: list[dict[str, object]] = []
    for entry in entries.values():
        source_input_map = dict(entry.pop("_source_input", {}) or {})
        terminal_counts = dict(entry.pop("_terminal_counts", {}) or {})
        ray_count = int(entry.get("ray_count", 0) or 0)
        if ray_count <= 0:
            continue
        hit_count = int(entry.get("hit_count", 0) or 0)
        miss_count = int(entry.get("miss_count", 0) or 0)
        total_input = float(sum(float(value) for value in source_input_map.values()))
        entry["source_ray_count"] = len(source_input_map)
        entry["total_input_power"] = total_input
        entry["hit_fraction"] = hit_count / ray_count if ray_count > 0 else np.nan
        entry["miss_fraction"] = miss_count / ray_count if ray_count > 0 else np.nan
        entry["dominant_terminal"] = _dominant_count_text(terminal_counts)
        records.append(entry)

    records.sort(key=lambda item: int(item.get("detector_surface", 0) or 0))
    return records


def detector_aperture_summary_text(records: list[dict[str, object]]) -> str:
    if not records:
        return "No detector aperture data. Click Update first."
    detector_count = len(records)
    ray_count = sum(int(record.get("ray_count", 0) or 0) for record in records)
    hit_count = sum(int(record.get("hit_count", 0) or 0) for record in records)
    miss_count = sum(int(record.get("miss_count", 0) or 0) for record in records)
    other_count = sum(int(record.get("other_count", 0) or 0) for record in records)
    hit_fraction = hit_count / ray_count if ray_count > 0 else np.nan
    miss_fraction = miss_count / ray_count if ray_count > 0 else np.nan
    return (
        f"{detector_count} detector(s) | rays={ray_count} | hits={hit_count} "
        f"({_format_percent(hit_fraction)}) | misses={miss_count} "
        f"({_format_percent(miss_fraction)}) | other={other_count}"
    )


def detector_aperture_table_values(record: dict[str, object]) -> tuple[object, ...]:
    return (
        record.get("detector", ""),
        int(record.get("ray_count", 0) or 0),
        int(record.get("hit_count", 0) or 0),
        int(record.get("miss_count", 0) or 0),
        int(record.get("other_count", 0) or 0),
        _format_percent(record.get("hit_fraction")),
        _format_value(record.get("hit_power")),
        _format_value(record.get("miss_power")),
        _format_value(record.get("worst_miss_margin_mm")),
        record.get("worst_miss_ray_index", "") or "-",
        _format_xy(record),
        record.get("dominant_terminal", ""),
    )


def detector_aperture_report_text(records: list[dict[str, object]]) -> str:
    if not records:
        return "# KrakenOS Detector Aperture Report\n\nNo detector aperture data. Click Update first.\n"
    lines = [
        "# KrakenOS Detector Aperture Report",
        "",
        detector_aperture_summary_text(records),
        "",
    ]
    for record in records:
        lines.append(
            "- {detector} | rays={rays} | hits={hits} | misses={misses} | hit_fraction={hit_fraction} | "
            "hit_power={hit_power} | miss_power={miss_power} | worst_margin={margin} mm | dominant={dominant}".format(
                detector=record.get("detector", ""),
                rays=int(record.get("ray_count", 0) or 0),
                hits=int(record.get("hit_count", 0) or 0),
                misses=int(record.get("miss_count", 0) or 0),
                hit_fraction=_format_percent(record.get("hit_fraction")),
                hit_power=_format_value(record.get("hit_power")),
                miss_power=_format_value(record.get("miss_power")),
                margin=_format_value(record.get("worst_miss_margin_mm")),
                dominant=record.get("dominant_terminal", ""),
            )
        )
    return "\n".join(lines).strip() + "\n"


def iter_detector_aperture_csv_rows(records: list[dict[str, object]]):
    for record in records:
        yield {column: record.get(column, "") for column in DETECTOR_APERTURE_CSV_COLUMNS}


def write_detector_aperture_csv(path: str | Path, records: list[dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETECTOR_APERTURE_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_detector_aperture_csv_rows(records))
