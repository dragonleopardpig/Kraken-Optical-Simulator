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
