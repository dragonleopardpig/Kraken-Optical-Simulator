from __future__ import annotations

import numpy as np


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
