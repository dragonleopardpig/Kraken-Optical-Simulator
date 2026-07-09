from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

import numpy as np


SOURCE_ILLUMINATION_TABLE_COLUMNS: tuple[str, ...] = (
    "source",
    "model",
    "launched",
    "hit",
    "missed",
    "loss",
    "events",
    "hit_fraction",
    "throughput",
    "power",
    "centroid",
    "rms",
    "span",
)

SOURCE_ILLUMINATION_TABLE_HEADINGS: dict[str, str] = {
    "source": "Source",
    "model": "Model",
    "launched": "Launched",
    "hit": "Hit Rays",
    "missed": "Missed",
    "loss": "Dominant Loss",
    "events": "Hit Events",
    "hit_fraction": "Hit %",
    "throughput": "Power %",
    "power": "Hit Power",
    "centroid": "Centroid XYZ",
    "rms": "RMS r",
    "span": "Span XYZ",
}

SOURCE_ILLUMINATION_TABLE_WIDTHS: dict[str, int] = {
    "source": 180,
    "model": 150,
    "launched": 75,
    "hit": 75,
    "missed": 75,
    "loss": 165,
    "events": 80,
    "hit_fraction": 80,
    "throughput": 80,
    "power": 90,
    "centroid": 170,
    "rms": 75,
    "span": 170,
}

SOURCE_ILLUMINATION_CSV_COLUMNS: tuple[str, ...] = (
    "source_id",
    "source_name",
    "source_model",
    "target_surface",
    "target_name",
    "launched_rays",
    "hit_rays",
    "missed_rays",
    "hit_events",
    "input_power",
    "hit_power",
    "missed_power",
    "throughput",
    "hit_fraction",
    "vignetted_fraction",
    "dominant_loss",
    "missed_terminal_breakdown",
    "centroid_x",
    "centroid_y",
    "centroid_z",
    "rms_radius",
    "span_x",
    "span_y",
    "span_z",
)


def format_percent_value(value: object) -> str:
    try:
        numeric = float(value)
    except Exception:
        return "-"
    if not np.isfinite(numeric):
        return "-"
    return f"{100.0 * numeric:.4g}%"


def source_illumination_report_totals(records: list[dict[str, object]]) -> dict[str, object]:
    total_input = float(sum(float(record.get("input_power", 0.0) or 0.0) for record in records))
    total_hit = float(sum(float(record.get("hit_power", 0.0) or 0.0) for record in records))
    total_launched = int(sum(int(record.get("launched_rays", 0) or 0) for record in records))
    total_hit_rays = int(sum(int(record.get("hit_rays", 0) or 0) for record in records))
    return {
        "input_power": total_input,
        "hit_power": total_hit,
        "launched_rays": total_launched,
        "hit_rays": total_hit_rays,
        "throughput": total_hit / total_input if total_input > 0.0 else np.nan,
    }


def source_illumination_summary_text(records: list[dict[str, object]], target_label: str) -> str:
    if not records:
        return f"Target {target_label}: no source illumination records. Click Update first."
    totals = source_illumination_report_totals(records)
    return (
        f"Target {target_label}: {int(totals['hit_rays'])}/{int(totals['launched_rays'])} source rays hit | "
        f"power throughput={format_percent_value(totals['throughput'])}"
    )


def source_illumination_table_values(record: dict[str, object]) -> tuple[object, ...]:
    centroid = (
        f"{float(record.get('centroid_x', np.nan)):.5g}, "
        f"{float(record.get('centroid_y', np.nan)):.5g}, "
        f"{float(record.get('centroid_z', np.nan)):.5g}"
    )
    span = (
        f"{float(record.get('span_x', np.nan)):.5g}, "
        f"{float(record.get('span_y', np.nan)):.5g}, "
        f"{float(record.get('span_z', np.nan)):.5g}"
    )
    return (
        f"{record.get('source_id', '')}: {record.get('source_name', '')}",
        record.get("source_model", ""),
        int(record.get("launched_rays", 0) or 0),
        int(record.get("hit_rays", 0) or 0),
        int(record.get("missed_rays", 0) or 0),
        record.get("dominant_loss", "None"),
        int(record.get("hit_events", 0) or 0),
        format_percent_value(record.get("hit_fraction")),
        format_percent_value(record.get("throughput")),
        f"{float(record.get('hit_power', 0.0) or 0.0):.6g}",
        centroid,
        f"{float(record.get('rms_radius', np.nan)):.6g}",
        span,
    )


def source_illumination_record_detail_text(record: dict[str, object]) -> str:
    target_surface = record.get("target_surface", "")
    target_name = str(record.get("target_name", "") or "")
    target = f"S{target_surface}: {target_name}" if str(target_surface).strip() != "" else target_name or "None"
    input_power = float(record.get("input_power", 0.0) or 0.0)
    hit_power = float(record.get("hit_power", 0.0) or 0.0)
    missed_power = float(record.get("missed_power", 0.0) or 0.0)
    return "\n".join(
        [
            f"Source: {record.get('source_id', '')} ({record.get('source_name', '')}) | {record.get('source_model', '')}",
            f"Target: {target}",
            (
                f"Rays: launched={int(record.get('launched_rays', 0) or 0)}, "
                f"hit={int(record.get('hit_rays', 0) or 0)} "
                f"({format_percent_value(record.get('hit_fraction'))}), "
                f"missed={int(record.get('missed_rays', 0) or 0)} "
                f"({format_percent_value(record.get('vignetted_fraction'))})"
            ),
            (
                f"Power: input={input_power:.6g}, hit={hit_power:.6g}, "
                f"missed={missed_power:.6g}, throughput={format_percent_value(record.get('throughput'))}"
            ),
            (
                f"Loss: dominant={record.get('dominant_loss', 'None')}; "
                f"all missed terminals={record.get('missed_terminal_breakdown', 'None')}"
            ),
            (
                "Footprint: "
                f"centroid=({float(record.get('centroid_x', np.nan)):.6g}, "
                f"{float(record.get('centroid_y', np.nan)):.6g}, "
                f"{float(record.get('centroid_z', np.nan)):.6g}) mm; "
                f"RMS r={float(record.get('rms_radius', np.nan)):.6g} mm; "
                f"span=({float(record.get('span_x', np.nan)):.6g}, "
                f"{float(record.get('span_y', np.nan)):.6g}, "
                f"{float(record.get('span_z', np.nan)):.6g}) mm"
            ),
        ]
    )


def source_illumination_report_text(records: list[dict[str, object]], target_label: str) -> str:
    if not records:
        return f"# KrakenOS Source Illumination Report\n\nTarget: {target_label}\n\nNo source illumination records. Click Update first.\n"
    totals = source_illumination_report_totals(records)
    lines = [
        "# KrakenOS Source Illumination Report",
        "",
        f"Target: {target_label}",
        f"Total source power throughput: {format_percent_value(totals['throughput'])}",
        "",
    ]
    for record in records:
        lines.append(
            "- {source_id} ({source_name}) | launched={launched} | hit={hit} | missed={missed} | "
            "hit_fraction={hit_fraction} | power={power:.6g} | throughput={throughput} | "
            "dominant_loss={dominant_loss} | missed_terminals={missed_terminals} | "
            "centroid=({cx:.6g}, {cy:.6g}, {cz:.6g}) mm | rms={rms:.6g} mm".format(
                source_id=record.get("source_id", ""),
                source_name=record.get("source_name", ""),
                launched=int(record.get("launched_rays", 0) or 0),
                hit=int(record.get("hit_rays", 0) or 0),
                missed=int(record.get("missed_rays", 0) or 0),
                hit_fraction=format_percent_value(record.get("hit_fraction")),
                power=float(record.get("hit_power", 0.0) or 0.0),
                throughput=format_percent_value(record.get("throughput")),
                dominant_loss=record.get("dominant_loss", "None"),
                missed_terminals=record.get("missed_terminal_breakdown", "None"),
                cx=float(record.get("centroid_x", np.nan)),
                cy=float(record.get("centroid_y", np.nan)),
                cz=float(record.get("centroid_z", np.nan)),
                rms=float(record.get("rms_radius", np.nan)),
            )
        )
    return "\n".join(lines) + "\n"


def iter_source_illumination_csv_rows(records: list[dict[str, object]]):
    for record in records:
        yield {column: record.get(column, "") for column in SOURCE_ILLUMINATION_CSV_COLUMNS}


def write_source_illumination_csv(path: str | Path, records: list[dict[str, object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SOURCE_ILLUMINATION_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_source_illumination_csv_rows(records))


def _safe_positive_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except Exception:
        return default
    if not np.isfinite(result):
        return default
    return max(result, 0.0)


def _hit_matches_target_surface(hit: dict[str, object], target_surface_index: int) -> bool:
    surface = str(hit.get("surface", "")).strip()
    if surface in {"", "-"}:
        return False
    try:
        return int(hit.get("surface")) == int(target_surface_index)
    except Exception:
        return False


def _candidate_power(candidate: tuple[float, str]) -> float:
    try:
        value = float(candidate[0])
    except Exception:
        return 0.0
    return value if np.isfinite(value) else 0.0


def finite_centroid_and_rms(points: list[tuple[float, float, float]]) -> tuple[float, float, float, float, float, float, float]:
    arr = np.asarray(points, dtype=float).reshape(-1, 3) if points else np.empty((0, 3), dtype=float)
    if arr.size == 0:
        return (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan)
    mask = np.all(np.isfinite(arr), axis=1)
    arr = arr[mask]
    if arr.size == 0:
        return (np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan)
    centroid = np.mean(arr, axis=0)
    radial = np.linalg.norm(arr[:, :2] - centroid[:2], axis=1)
    rms = float(np.sqrt(np.mean(radial * radial))) if radial.size else np.nan
    span_x = float(np.max(arr[:, 0]) - np.min(arr[:, 0])) if arr.shape[0] else np.nan
    span_y = float(np.max(arr[:, 1]) - np.min(arr[:, 1])) if arr.shape[0] else np.nan
    span_z = float(np.max(arr[:, 2]) - np.min(arr[:, 2])) if arr.shape[0] else np.nan
    return (float(centroid[0]), float(centroid[1]), float(centroid[2]), rms, span_x, span_y, span_z)


def source_illumination_terminal_label_for_record(record: dict[str, object]) -> str:
    last_surface = record.get("last_surface")
    last_name = str(record.get("last_name", "") or "")
    try:
        index = int(last_surface)
        terminal = f"S{index}: {last_name or 'Surface'}"
    except Exception:
        terminal = last_name
    termination = str(record.get("termination", "") or "").strip()
    if terminal:
        return terminal
    return termination or "No recorded hit"


def source_illumination_format_terminal_counts(counts: dict[str, int], *, limit: int = 3) -> str:
    items = [
        (str(label), int(count))
        for label, count in (counts or {}).items()
        if str(label).strip() and int(count) > 0
    ]
    if not items:
        return "None"
    items.sort(key=lambda item: (-item[1], item[0]))
    shown = [f"{label} ({count})" for label, count in items[: max(1, int(limit))]]
    remainder = sum(count for _label, count in items[max(1, int(limit)):])
    if remainder > 0:
        shown.append(f"+{remainder} more")
    return "; ".join(shown)


def collect_source_illumination_records(
    ray_records: list[dict[str, object]],
    target_surface_index: int | None,
    target_name: str = "",
    *,
    terminal_label_for_record: Callable[[dict[str, object]], str] | None = None,
) -> list[dict[str, object]]:
    if not ray_records or target_surface_index is None:
        return []
    try:
        target_index = int(target_surface_index)
    except Exception:
        return []
    if target_index < 0:
        return []

    terminal_label = terminal_label_for_record or source_illumination_terminal_label_for_record
    source_input: dict[tuple[str, int], float] = {}
    groups: dict[str, dict[str, object]] = {}

    def group_for(record: dict[str, object]) -> dict[str, object]:
        source_id = str(record.get("source_id", "") or "source:0")
        entry = groups.get(source_id)
        if entry is None:
            entry = {
                "source_id": source_id,
                "source_name": str(record.get("source_name", "") or source_id),
                "source_model": str(record.get("source_model", "") or ""),
                "target_surface": target_index,
                "target_name": str(target_name or ""),
                "launched_rays": 0,
                "hit_rays": 0,
                "hit_events": 0,
                "input_power": 0.0,
                "hit_power": 0.0,
                "_launched_keys": set(),
                "_hit_keys": set(),
                "_points": [],
                "_miss_candidates": {},
            }
            groups[source_id] = entry
        return entry

    for record in ray_records:
        source_id = str(record.get("source_id", "") or "source:0")
        source_ray_index = int(record.get("source_ray_index", record.get("ray_index", 0)) or 0)
        source_key = (source_id, source_ray_index)
        source_weight = _safe_positive_float(record.get("source_weight"), 1.0)
        source_power = _safe_positive_float(record.get("source_power"), 1.0)
        input_power = source_weight * source_power
        source_input[source_key] = max(float(source_input.get(source_key, 0.0)), input_power)
        entry = group_for(record)
        entry["_launched_keys"].add(source_key)  # type: ignore[union-attr]
        branch_power = _safe_positive_float(record.get("branch_power"), np.nan)
        if not np.isfinite(branch_power):
            branch_power = _safe_positive_float(record.get("transmission"), 1.0)
        effective_power = max(float(input_power * branch_power), 0.0)

        hits = [
            hit
            for hit in list(record.get("hits", []) or [])
            if _hit_matches_target_surface(hit, target_index)
        ]
        if not hits:
            miss_candidates = entry["_miss_candidates"]  # type: ignore[assignment]
            candidates = miss_candidates.setdefault(source_key, [])
            candidates.append((effective_power, terminal_label(record)))
            continue
        entry["_hit_keys"].add(source_key)  # type: ignore[union-attr]
        entry["hit_events"] = int(entry["hit_events"]) + len(hits)
        entry["hit_power"] = float(entry["hit_power"]) + effective_power
        points = entry["_points"]  # type: ignore[assignment]
        for hit in hits:
            points.append(
                (
                    float(hit.get("x", np.nan)),
                    float(hit.get("y", np.nan)),
                    float(hit.get("z", np.nan)),
                )
            )

    for entry in groups.values():
        launched_keys = set(entry.pop("_launched_keys", set()) or set())
        hit_keys = set(entry.pop("_hit_keys", set()) or set())
        points = list(entry.pop("_points", []) or [])
        miss_candidates = dict(entry.pop("_miss_candidates", {}) or {})
        missed_keys = launched_keys - hit_keys
        terminal_counts: dict[str, int] = {}
        missed_power = 0.0
        for source_key in missed_keys:
            candidates = list(miss_candidates.get(source_key, []) or [])
            terminal = "No recorded hit"
            if candidates:
                candidates.sort(key=_candidate_power, reverse=True)
                terminal = str(candidates[0][1] or terminal)
            terminal_counts[terminal] = int(terminal_counts.get(terminal, 0)) + 1
            missed_power += float(source_input.get(source_key, 0.0))
        input_power = float(sum(source_input.get(key, 0.0) for key in launched_keys))
        hit_power = float(entry.get("hit_power", 0.0))
        cx, cy, cz, rms, span_x, span_y, span_z = finite_centroid_and_rms(points)
        entry["launched_rays"] = len(launched_keys)
        entry["hit_rays"] = len(hit_keys)
        entry["missed_rays"] = max(len(launched_keys) - len(hit_keys), 0)
        entry["missed_power"] = missed_power
        entry["input_power"] = input_power
        entry["hit_power"] = hit_power
        entry["throughput"] = hit_power / input_power if input_power > 0.0 else np.nan
        entry["hit_fraction"] = len(hit_keys) / len(launched_keys) if launched_keys else np.nan
        entry["vignetted_fraction"] = 1.0 - float(entry["hit_fraction"]) if np.isfinite(float(entry["hit_fraction"])) else np.nan
        entry["missed_terminal_counts"] = dict(sorted(terminal_counts.items(), key=lambda item: (-item[1], item[0])))
        entry["missed_terminal_breakdown"] = source_illumination_format_terminal_counts(terminal_counts)
        entry["dominant_loss"] = source_illumination_format_terminal_counts(terminal_counts, limit=1)
        entry["centroid_x"] = cx
        entry["centroid_y"] = cy
        entry["centroid_z"] = cz
        entry["rms_radius"] = rms
        entry["span_x"] = span_x
        entry["span_y"] = span_y
        entry["span_z"] = span_z

    records = list(groups.values())
    records.sort(key=lambda item: str(item.get("source_id", "")))
    return records


def empty_source_illumination_samples(target_surface_index: int | None = None, target_name: str = "") -> dict[str, object]:
    return {
        "x": np.asarray([], dtype=float),
        "y": np.asarray([], dtype=float),
        "weights": np.asarray([], dtype=float),
        "source_ids": [],
        "source_names": [],
        "coord": "local",
        "target_surface": target_surface_index,
        "target_name": str(target_name or ""),
        "launched_rays": 0,
        "hit_rays": 0,
        "missed_rays": 0,
        "input_power": 0.0,
        "hit_power": 0.0,
        "source_count": 0,
    }


def source_illumination_hit_samples_from_records(
    ray_records: list[dict[str, object]],
    target_surface_index: int | None,
    target_name: str = "",
    *,
    hit_xy_for_hit: Callable[[dict[str, object]], tuple[float, float, str]] | None = None,
    diagnostic_records: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    if target_surface_index is None:
        return empty_source_illumination_samples()
    try:
        target_index = int(target_surface_index)
    except Exception:
        return empty_source_illumination_samples()
    if target_index < 0:
        return empty_source_illumination_samples()

    x_values: list[float] = []
    y_values: list[float] = []
    weights: list[float] = []
    source_ids: list[str] = []
    source_names: list[str] = []
    coord_modes: set[str] = set()
    launched_keys: set[tuple[str, int]] = set()
    hit_keys: set[tuple[str, int]] = set()
    source_input: dict[tuple[str, int], float] = {}

    def hit_xy(hit: dict[str, object]) -> tuple[float, float, str]:
        if hit_xy_for_hit is not None:
            return hit_xy_for_hit(hit)
        return (float(hit.get("x", np.nan)), float(hit.get("y", np.nan)), "world")

    for record in ray_records:
        source_id = str(record.get("source_id", "") or "source:0")
        source_name = str(record.get("source_name", "") or source_id)
        source_ray_index = int(record.get("source_ray_index", record.get("ray_index", 0)) or 0)
        source_key = (source_id, source_ray_index)
        source_weight = _safe_positive_float(record.get("source_weight"), 1.0)
        source_power = _safe_positive_float(record.get("source_power"), 1.0)
        input_power = source_weight * source_power
        source_input[source_key] = max(float(source_input.get(source_key, 0.0)), input_power)
        launched_keys.add(source_key)
        hits = [
            hit
            for hit in list(record.get("hits", []) or [])
            if _hit_matches_target_surface(hit, target_index)
        ]
        if not hits:
            continue
        branch_power = _safe_positive_float(record.get("branch_power"), np.nan)
        if not np.isfinite(branch_power):
            branch_power = _safe_positive_float(record.get("transmission"), 1.0)
        effective_power = max(float(input_power * branch_power), 0.0)
        hit_keys.add(source_key)
        for hit in hits:
            try:
                x_value, y_value, coord_mode = hit_xy(hit)
            except Exception:
                x_value, y_value, coord_mode = (np.nan, np.nan, "world")
            if not np.isfinite(x_value) or not np.isfinite(y_value):
                continue
            x_values.append(float(x_value))
            y_values.append(float(y_value))
            weights.append(effective_power)
            source_ids.append(source_id)
            source_names.append(source_name)
            coord_modes.add(str(coord_mode or "world"))

    input_total = float(sum(source_input.get(key, 0.0) for key in launched_keys))
    hit_total = float(sum(weights))
    coord = "local" if coord_modes == {"local"} or not coord_modes else "world"
    records_for_loss = diagnostic_records
    if records_for_loss is None:
        records_for_loss = collect_source_illumination_records(ray_records, target_index, target_name)
    loss_parts = [
        f"{record.get('source_id', '')}: {record.get('dominant_loss', 'None')}"
        for record in records_for_loss
        if int(record.get("missed_rays", 0) or 0) > 0
    ]
    return {
        "x": np.asarray(x_values, dtype=float),
        "y": np.asarray(y_values, dtype=float),
        "weights": np.asarray(weights, dtype=float),
        "source_ids": source_ids,
        "source_names": source_names,
        "coord": coord,
        "target_surface": target_index,
        "target_name": str(target_name or ""),
        "launched_rays": len(launched_keys),
        "hit_rays": len(hit_keys),
        "missed_rays": max(len(launched_keys) - len(hit_keys), 0),
        "input_power": input_total,
        "hit_power": hit_total,
        "source_count": len({source_id for source_id in source_ids}),
        "loss_summary": "; ".join(loss_parts) if loss_parts else "None",
    }


def source_illumination_map_extent(
    samples: dict[str, object],
    x_values: np.ndarray,
    y_values: np.ndarray,
    target_model: dict[str, object] | None = None,
) -> tuple[float, float, float, float]:
    model = dict(target_model or {})
    if samples.get("coord") == "local" and bool(model.get("is_detector", False)):
        active_width = float(model.get("active_width_mm", 0.0) or 0.0)
        active_height = float(model.get("active_height_mm", 0.0) or 0.0)
        # bugs/0163 + flag_20260709_093800_013: a detector's round clear-aperture DIAMETER is not a
        # sensor size. Only an explicit rectangular active area (both dims > 0 -- the orange sensor
        # footprint) defines the heatmap window. Do NOT fall back to the diameter, or the map draws a
        # square up to 2x the real sensor (e.g. a 78 mm catch aperture over the 39x39 FOV): it spills
        # past the image circle and buries the fold/perp dark-edge asymmetry under a symmetric dark
        # border. Without explicit dims, fall through to the illuminated data footprint below.
        if active_width > 0.0 and active_height > 0.0:
            return (-0.5 * active_width, 0.5 * active_width, -0.5 * active_height, 0.5 * active_height)

    x_array = np.asarray(x_values, dtype=float)
    y_array = np.asarray(y_values, dtype=float)
    x_min = float(np.min(x_array))
    x_max = float(np.max(x_array))
    y_min = float(np.min(y_array))
    y_max = float(np.max(y_array))
    x_span = max(x_max - x_min, 1e-6)
    y_span = max(y_max - y_min, 1e-6)
    pad = max(x_span, y_span, 1e-3) * 0.2
    return (x_min - pad, x_max + pad, y_min - pad, y_max + pad)


def source_illumination_map_data_from_samples(
    samples: dict[str, object],
    *,
    target_model: dict[str, object] | None = None,
    bins: int | None = None,
) -> dict[str, object]:
    x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
    y_values = np.asarray(samples.get("y", np.asarray([])), dtype=float)
    weights = np.asarray(samples.get("weights", np.asarray([])), dtype=float)
    if x_values.size == 0 or y_values.size == 0:
        raise RuntimeError("No source illumination hits on the selected target. Click Update and select Object, Detector, or Image.")
    if weights.size != x_values.size or float(np.sum(weights)) <= 0.0:
        weights = np.ones_like(x_values, dtype=float)

    bin_count = int(bins) if bins is not None else min(max(24, int(np.sqrt(max(x_values.size, 1)) * 3)), 128)
    x_min, x_max, y_min, y_max = source_illumination_map_extent(samples, x_values, y_values, target_model)
    hist, x_edges, y_edges = np.histogram2d(
        x_values,
        y_values,
        bins=bin_count,
        range=[[x_min, x_max], [y_min, y_max]],
        weights=weights,
    )
    if not np.any(hist > 0.0):
        raise RuntimeError("Source illumination map has no finite bins.")
    peak = float(np.max(hist))
    density = hist.T / max(peak, 1e-12)
    source_ids = list(samples.get("source_ids", []) or [])
    source_names = list(samples.get("source_names", []) or [])
    centroids: list[dict[str, object]] = []
    for source_id in sorted(set(source_ids)):
        mask = np.asarray([item == source_id for item in source_ids], dtype=bool)
        if not np.any(mask):
            continue
        source_weights = np.maximum(weights[mask], 0.0)
        if float(np.sum(source_weights)) > 0.0:
            cx = float(np.average(x_values[mask], weights=source_weights))
            cy = float(np.average(y_values[mask], weights=source_weights))
        else:
            cx = float(np.mean(x_values[mask]))
            cy = float(np.mean(y_values[mask]))
        try:
            first_name = source_names[next(index for index, item in enumerate(source_ids) if item == source_id)]
        except Exception:
            first_name = source_id
        centroids.append(
            {
                "source_id": str(source_id),
                "source_name": str(first_name or source_id),
                "x_mm": cx,
                "y_mm": cy,
                "event_count": int(np.count_nonzero(mask)),
                "power": float(np.sum(source_weights)),
            }
        )

    return {
        "samples": samples,
        "x_values": x_values,
        "y_values": y_values,
        "weights": weights,
        "hist": hist,
        "density": density,
        "x_edges": x_edges,
        "y_edges": y_edges,
        "extent": [float(x_edges[0]), float(x_edges[-1]), float(y_edges[0]), float(y_edges[-1])],
        "bins": bin_count,
        "peak_power": peak,
        "total_power": float(np.sum(weights)),
        "source_ids": source_ids,
        "source_names": source_names,
        "source_centroids": centroids,
        "target_model": dict(target_model or {}),
        "coordinate_label": "target local" if samples.get("coord") == "local" else "world",
    }
