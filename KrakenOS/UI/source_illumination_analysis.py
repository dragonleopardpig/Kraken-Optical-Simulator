from __future__ import annotations

import csv
from pathlib import Path

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
        diameter = float(model.get("diameter_mm", 0.0) or 0.0)
        if active_width <= 0.0 and diameter > 0.0:
            active_width = diameter
        if active_height <= 0.0 and diameter > 0.0:
            active_height = diameter
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
