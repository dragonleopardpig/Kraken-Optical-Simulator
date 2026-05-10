from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

import numpy as np


DETECTOR_MAP_CSV_COLUMNS: tuple[str, ...] = (
    "filter",
    "terminal",
    "coordinate",
    "ray_count",
    "bins",
    "bin_x",
    "bin_y",
    "x_min_mm",
    "x_max_mm",
    "y_min_mm",
    "y_max_mm",
    "x_center_mm",
    "y_center_mm",
    "power",
    "total_power",
    "peak_power",
)

BRANCH_DETECTOR_PSF_CSV_COLUMNS: tuple[str, ...] = (
    "filter",
    "terminal",
    "coordinate",
    "ray_count",
    "bins",
    "centroid_x_mm",
    "centroid_y_mm",
    "bin_x",
    "bin_y",
    "x_min_centered_mm",
    "x_max_centered_mm",
    "y_min_centered_mm",
    "y_max_centered_mm",
    "x_center_centered_mm",
    "y_center_centered_mm",
    "power",
    "normalized_power",
    "total_power",
    "peak_power",
)

BRANCH_DETECTOR_MTF_CSV_COLUMNS: tuple[str, ...] = (
    "filter",
    "terminal",
    "coordinate",
    "ray_count",
    "bins",
    "method",
    "frequency_cy_per_mm",
    "tangential_mtf",
    "sagittal_mtf",
    "average_mtf",
    "target_frequency_cy_per_mm",
    "selected_curve",
    "selected_mtf_at_target",
    "max_frequency_cy_per_mm",
)


def detector_map_extent(
    samples: dict[str, object],
    x_values: np.ndarray,
    y_values: np.ndarray,
    detector_model: dict[str, object] | None = None,
) -> tuple[float, float, float, float]:
    model = dict(detector_model or {})
    active_width = float(model.get("active_width_mm", 0.0) or 0.0)
    active_height = float(model.get("active_height_mm", 0.0) or 0.0)
    if samples.get("coord") == "local" and active_width > 0.0 and active_height > 0.0:
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


def detector_map_data_from_samples(
    samples: dict[str, object],
    filter_text: str,
    *,
    bins: int,
    detector_model: dict[str, object] | None = None,
    empty_message: str | None = None,
) -> dict[str, object]:
    x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
    y_values = np.asarray(samples.get("y", np.asarray([])), dtype=float)
    weights = np.asarray(samples.get("weights", np.asarray([])), dtype=float)
    terminal_labels = list(samples.get("terminals", []) or [])
    terminal_count = len(set(terminal_labels))

    if x_values.size == 0 or y_values.size == 0:
        raise RuntimeError(empty_message or f"No detector hits for {filter_text}. Choose a detector path/terminal and click Update.")
    if terminal_count > 1:
        raise RuntimeError("Detector map needs one terminal plane. Choose a specific Terminal or output path.")

    weights_for_hist = weights if weights.size == x_values.size else None
    if weights_for_hist is None or float(np.sum(weights_for_hist)) <= 0.0:
        weights_for_hist = np.ones_like(x_values, dtype=float)
    model = dict(detector_model or {})
    x_min, x_max, y_min, y_max = detector_map_extent(samples, x_values, y_values, model)
    bin_count = int(bins)
    hist, x_edges, y_edges = np.histogram2d(
        x_values,
        y_values,
        bins=bin_count,
        range=[[x_min, x_max], [y_min, y_max]],
        weights=weights_for_hist,
    )
    if not np.any(hist > 0.0):
        raise RuntimeError("Detector map has no finite bins.")

    terminal_label = terminal_labels[0] if terminal_labels else "Detector"
    coordinate_label = "detector local" if samples.get("coord") == "local" else "world"
    return {
        "filter_text": str(filter_text),
        "samples": samples,
        "x_values": x_values,
        "y_values": y_values,
        "weights": weights_for_hist,
        "hist": hist,
        "x_edges": x_edges,
        "y_edges": y_edges,
        "bins": bin_count,
        "terminal_label": terminal_label,
        "terminal_count": terminal_count,
        "coordinate_label": coordinate_label,
        "total_power": float(np.sum(weights_for_hist)),
        "peak_power": float(np.max(hist)),
        "detector_model": model,
    }


def branch_detector_psf_data_from_samples(
    samples: dict[str, object],
    filter_text: str,
    *,
    bins: int,
    detector_model: dict[str, object] | None = None,
) -> dict[str, object]:
    x_values = np.asarray(samples.get("x", np.asarray([])), dtype=float)
    y_values = np.asarray(samples.get("y", np.asarray([])), dtype=float)
    weights = np.asarray(samples.get("weights", np.asarray([])), dtype=float)
    terminal_labels = list(samples.get("terminals", []) or [])
    terminal_count = len(set(terminal_labels))
    if x_values.size == 0 or y_values.size == 0:
        raise RuntimeError(f"No detector hits for {filter_text}. Choose a detector path/terminal and click Update.")
    if terminal_count > 1:
        raise RuntimeError("Path PSF/MTF needs one terminal plane. Choose a specific Terminal or output path.")

    weights_for_hist = weights if weights.size == x_values.size else None
    if weights_for_hist is None or float(np.sum(weights_for_hist)) <= 0.0:
        weights_for_hist = np.ones_like(x_values, dtype=float)
    centroid_x = float(np.average(x_values, weights=np.maximum(weights_for_hist, 0.0)))
    centroid_y = float(np.average(y_values, weights=np.maximum(weights_for_hist, 0.0)))
    centered_x = x_values - centroid_x
    centered_y = y_values - centroid_y
    span = max(float(np.ptp(centered_x)), float(np.ptp(centered_y)), 1e-3) * 1.25
    bin_count = int(bins)
    hist, x_edges, y_edges = np.histogram2d(
        centered_x,
        centered_y,
        bins=bin_count,
        range=[[-span / 2.0, span / 2.0], [-span / 2.0, span / 2.0]],
        weights=weights_for_hist,
    )
    if not np.any(hist > 0.0):
        raise RuntimeError("Path detector PSF has no finite bins.")
    terminal_label = terminal_labels[0] if terminal_labels else "Detector"
    coordinate_label = "detector local" if samples.get("coord") == "local" else "world"
    return {
        "filter_text": str(filter_text),
        "samples": samples,
        "x_values": x_values,
        "y_values": y_values,
        "centered_x": centered_x,
        "centered_y": centered_y,
        "weights": weights_for_hist,
        "hist": hist,
        "x_edges": x_edges,
        "y_edges": y_edges,
        "bins": bin_count,
        "span": span,
        "centroid_x": centroid_x,
        "centroid_y": centroid_y,
        "terminal_label": terminal_label,
        "terminal_count": terminal_count,
        "coordinate_label": coordinate_label,
        "total_power": float(np.sum(weights_for_hist)),
        "peak_power": float(np.max(hist)),
        "detector_model": dict(detector_model or {}),
    }


def branch_detector_mtf_data_from_psf(data: dict[str, object]) -> dict[str, object]:
    hist = np.asarray(data["hist"], dtype=float)
    x_edges = np.asarray(data["x_edges"], dtype=float)
    if hist.size == 0 or hist.shape[0] < 2:
        raise RuntimeError("Path detector MTF needs at least two detector bins.")
    psf = hist / max(float(np.sum(hist)), 1e-15)
    otf = np.fft.fftshift(np.fft.fft2(psf))
    mtf = np.abs(otf)
    mtf /= max(float(np.max(mtf)), 1e-15)
    dx = float(x_edges[1] - x_edges[0])
    if not np.isfinite(dx) or dx <= 0.0:
        raise RuntimeError("Path detector MTF has invalid detector bin pitch.")
    bins = int(hist.shape[0])
    freq = np.fft.fftshift(np.fft.fftfreq(bins, d=dx))
    center = bins // 2
    plot_freq = np.asarray(freq[center:], dtype=float)
    plot_tan = np.asarray(mtf[center, center:], dtype=float)
    plot_sag = np.asarray(mtf[center:, center], dtype=float)
    count = min(plot_freq.size, plot_tan.size, plot_sag.size)
    if count == 0:
        raise RuntimeError("Path detector MTF has no positive frequency samples.")
    result = dict(data)
    result.update(
        {
            "plot_freq": plot_freq[:count],
            "plot_tan": plot_tan[:count],
            "plot_sag": plot_sag[:count],
            "plot_avg": 0.5 * (plot_tan[:count] + plot_sag[:count]),
            "method": "Path Detector Geometric-PSF",
        }
    )
    return result


def iter_detector_map_csv_rows(data: dict[str, object]) -> Iterator[dict[str, object]]:
    hist = np.asarray(data["hist"], dtype=float)
    x_edges = np.asarray(data["x_edges"], dtype=float)
    y_edges = np.asarray(data["y_edges"], dtype=float)
    x_values = np.asarray(data["x_values"], dtype=float)
    filter_text = str(data["filter_text"])
    terminal_label = str(data["terminal_label"])
    coordinate_label = str(data["coordinate_label"])
    total_power = float(data["total_power"])
    peak_power = float(data["peak_power"])
    bins = int(data["bins"])
    for ix in range(hist.shape[0]):
        x_min = float(x_edges[ix])
        x_max = float(x_edges[ix + 1])
        x_center = 0.5 * (x_min + x_max)
        for iy in range(hist.shape[1]):
            y_min = float(y_edges[iy])
            y_max = float(y_edges[iy + 1])
            yield {
                "filter": filter_text,
                "terminal": terminal_label,
                "coordinate": coordinate_label,
                "ray_count": int(x_values.size),
                "bins": bins,
                "bin_x": ix,
                "bin_y": iy,
                "x_min_mm": x_min,
                "x_max_mm": x_max,
                "y_min_mm": y_min,
                "y_max_mm": y_max,
                "x_center_mm": x_center,
                "y_center_mm": 0.5 * (y_min + y_max),
                "power": float(hist[ix, iy]),
                "total_power": total_power,
                "peak_power": peak_power,
            }


def iter_branch_detector_psf_csv_rows(data: dict[str, object]) -> Iterator[dict[str, object]]:
    hist = np.asarray(data["hist"], dtype=float)
    x_edges = np.asarray(data["x_edges"], dtype=float)
    y_edges = np.asarray(data["y_edges"], dtype=float)
    x_values = np.asarray(data["x_values"], dtype=float)
    filter_text = str(data["filter_text"])
    terminal_label = str(data["terminal_label"])
    coordinate_label = str(data["coordinate_label"])
    bins = int(data["bins"])
    centroid_x = float(data["centroid_x"])
    centroid_y = float(data["centroid_y"])
    total_power = float(data["total_power"])
    peak_power = float(data["peak_power"])
    for ix in range(hist.shape[0]):
        x_min = float(x_edges[ix])
        x_max = float(x_edges[ix + 1])
        x_center = 0.5 * (x_min + x_max)
        for iy in range(hist.shape[1]):
            y_min = float(y_edges[iy])
            y_max = float(y_edges[iy + 1])
            power = float(hist[ix, iy])
            yield {
                "filter": filter_text,
                "terminal": terminal_label,
                "coordinate": coordinate_label,
                "ray_count": int(x_values.size),
                "bins": bins,
                "centroid_x_mm": centroid_x,
                "centroid_y_mm": centroid_y,
                "bin_x": ix,
                "bin_y": iy,
                "x_min_centered_mm": x_min,
                "x_max_centered_mm": x_max,
                "y_min_centered_mm": y_min,
                "y_max_centered_mm": y_max,
                "x_center_centered_mm": x_center,
                "y_center_centered_mm": 0.5 * (y_min + y_max),
                "power": power,
                "normalized_power": power / max(peak_power, 1e-15),
                "total_power": total_power,
                "peak_power": peak_power,
            }


def iter_branch_detector_mtf_csv_rows(
    data: dict[str, object],
    *,
    target_freq: float,
    mtf_mode: str,
) -> Iterator[dict[str, object]]:
    plot_freq = np.asarray(data["plot_freq"], dtype=float)
    plot_tan = np.asarray(data["plot_tan"], dtype=float)
    plot_sag = np.asarray(data["plot_sag"], dtype=float)
    plot_avg = np.asarray(data["plot_avg"], dtype=float)
    count = min(plot_freq.size, plot_tan.size, plot_sag.size, plot_avg.size)
    if count == 0:
        return
    target = float(target_freq)
    mode = str(mtf_mode).strip().lower()
    if mode == "tangential":
        selected_curve = plot_tan[:count]
        selected_label = "Tangential"
    elif mode == "sagittal":
        selected_curve = plot_sag[:count]
        selected_label = "Sagittal"
    else:
        selected_curve = plot_avg[:count]
        selected_label = "Average"
    selected_value = float(
        np.interp(
            target,
            plot_freq[:count],
            selected_curve,
            left=selected_curve[0],
            right=selected_curve[-1],
        )
    )
    x_values = np.asarray(data["x_values"], dtype=float)
    for index in range(count):
        yield {
            "filter": str(data["filter_text"]),
            "terminal": str(data["terminal_label"]),
            "coordinate": str(data["coordinate_label"]),
            "ray_count": int(x_values.size),
            "bins": int(data["bins"]),
            "method": str(data.get("method", "Path Detector Geometric-PSF")),
            "frequency_cy_per_mm": float(plot_freq[index]),
            "tangential_mtf": float(plot_tan[index]),
            "sagittal_mtf": float(plot_sag[index]),
            "average_mtf": float(plot_avg[index]),
            "target_frequency_cy_per_mm": target,
            "selected_curve": selected_label,
            "selected_mtf_at_target": selected_value,
            "max_frequency_cy_per_mm": float(plot_freq[count - 1]),
        }


def write_detector_map_csv(path: str | Path, data: dict[str, object]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=DETECTOR_MAP_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_detector_map_csv_rows(data))


def write_branch_detector_psf_csv(path: str | Path, data: dict[str, object]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_DETECTOR_PSF_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_branch_detector_psf_csv_rows(data))


def write_branch_detector_mtf_csv(
    path: str | Path,
    data: dict[str, object],
    *,
    target_freq: float,
    mtf_mode: str,
) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_DETECTOR_MTF_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_branch_detector_mtf_csv_rows(data, target_freq=target_freq, mtf_mode=mtf_mode))
