from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterator

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.coherent_detector_analysis import COHERENT_SUM_MODE_DEFAULT


BRANCH_FIELD_CSV_COLUMNS: tuple[str, ...] = (
    "filter",
    "terminal",
    "coordinate",
    "branch_codes",
    "coherence_mode",
    "wavelength_um",
    "component",
    "propagation_mm",
    "field_z_mm",
    "total_power",
    "source_power",
    "peak_intensity",
    "centroid_x_mm",
    "centroid_y_mm",
    "second_moment_radius_mm",
    "tem00_waist_mm",
    "tem00_overlap_efficiency",
    "tem00_overlap_phase_rad",
    "bin_x",
    "bin_y",
    "x_min_mm",
    "x_max_mm",
    "y_min_mm",
    "y_max_mm",
    "x_center_mm",
    "y_center_mm",
    "field_real",
    "field_imag",
    "intensity",
    "normalized_intensity",
    "phase_rad",
    "phase_valid",
)


def branch_field_analysis_data_from_coherent(
    coherent: dict[str, object],
    *,
    wavelength_um: float,
    propagation_mm: float,
    component: str = "field",
) -> dict[str, object]:
    coherent_data = dict(coherent)
    coherent_data["wavelength_um"] = float(wavelength_um)
    source_grid = Kos.branch_field_from_detector_data(coherent_data, component=component)
    z_mm = float(propagation_mm)
    if abs(z_mm) > 1e-15:
        grid = Kos.propagate_branch_field(source_grid, z_mm)
    else:
        grid = source_grid
    centroid_x, centroid_y = grid.centroid_mm()
    fitted_waist = float(grid.second_moment_radius_mm())
    minimum_waist = max(abs(grid.dx_mm), abs(grid.dy_mm), 1e-9)
    if not np.isfinite(fitted_waist) or fitted_waist <= minimum_waist:
        fitted_waist = minimum_waist
    overlap = Kos.gaussian_mode_overlap(
        grid,
        waist_radius_mm=fitted_waist,
        center_x_mm=centroid_x if np.isfinite(centroid_x) else 0.0,
        center_y_mm=centroid_y if np.isfinite(centroid_y) else 0.0,
    )
    intensity = grid.intensity
    peak = float(grid.peak_intensity)
    phase = np.angle(grid.field)
    phase_mask = intensity > max(peak * 1e-3, 1e-30)
    result = dict(coherent_data)
    result.update(
        {
            "branch_field_grid": grid,
            "branch_field_component": grid.component,
            "branch_field_intensity": intensity,
            "branch_field_phase_rad": phase,
            "branch_field_phase_mask": phase_mask,
            "branch_field_total_power": float(grid.total_power),
            "branch_field_source_power": float(source_grid.total_power),
            "branch_field_peak_intensity": peak,
            "branch_field_propagation_mm": float(z_mm),
            "branch_field_z_mm": float(grid.z_mm),
            "branch_field_centroid_x_mm": float(centroid_x),
            "branch_field_centroid_y_mm": float(centroid_y),
            "branch_field_second_moment_radius_mm": float(grid.second_moment_radius_mm()),
            "branch_field_tem00_waist_mm": fitted_waist,
            "branch_field_tem00_overlap_efficiency": float(overlap.efficiency),
            "branch_field_tem00_overlap_phase_rad": float(overlap.phase_rad),
            "branch_field_model": "Phase 8 scalar BranchFieldGrid from coherent detector field",
        }
    )
    return result


def iter_branch_field_csv_rows(data: dict[str, object], wavelength_um: float) -> Iterator[dict[str, object]]:
    grid = data["branch_field_grid"]
    field = np.asarray(grid.field, dtype=np.complex128)
    intensity = np.asarray(data["branch_field_intensity"], dtype=float)
    phase = np.asarray(data["branch_field_phase_rad"], dtype=float)
    phase_mask = np.asarray(data["branch_field_phase_mask"], dtype=bool)
    x_edges = np.asarray(grid.x_edges_mm, dtype=float)
    y_edges = np.asarray(grid.y_edges_mm, dtype=float)
    x_centers = np.asarray(grid.x_centers_mm, dtype=float)
    y_centers = np.asarray(grid.y_centers_mm, dtype=float)
    peak = max(float(data.get("branch_field_peak_intensity", 0.0) or 0.0), 1e-15)
    branch_codes = ",".join(str(code) for code in data.get("branch_codes", []) or [])
    for ix in range(field.shape[0]):
        for iy in range(field.shape[1]):
            value = complex(field[ix, iy])
            pixel_intensity = float(intensity[ix, iy])
            yield {
                "filter": str(data.get("filter_text", "")),
                "terminal": str(data.get("terminal_label", "")),
                "coordinate": str(data.get("coordinate_label", "")),
                "branch_codes": branch_codes,
                "coherence_mode": str(data.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT)),
                "wavelength_um": float(wavelength_um),
                "component": str(data.get("branch_field_component", "field")),
                "propagation_mm": float(data.get("branch_field_propagation_mm", 0.0) or 0.0),
                "field_z_mm": float(data.get("branch_field_z_mm", 0.0) or 0.0),
                "total_power": float(data.get("branch_field_total_power", 0.0) or 0.0),
                "source_power": float(data.get("branch_field_source_power", 0.0) or 0.0),
                "peak_intensity": float(data.get("branch_field_peak_intensity", 0.0) or 0.0),
                "centroid_x_mm": float(data.get("branch_field_centroid_x_mm", np.nan)),
                "centroid_y_mm": float(data.get("branch_field_centroid_y_mm", np.nan)),
                "second_moment_radius_mm": float(data.get("branch_field_second_moment_radius_mm", np.nan)),
                "tem00_waist_mm": float(data.get("branch_field_tem00_waist_mm", np.nan)),
                "tem00_overlap_efficiency": float(data.get("branch_field_tem00_overlap_efficiency", np.nan)),
                "tem00_overlap_phase_rad": float(data.get("branch_field_tem00_overlap_phase_rad", np.nan)),
                "bin_x": ix,
                "bin_y": iy,
                "x_min_mm": float(x_edges[ix]),
                "x_max_mm": float(x_edges[ix + 1]),
                "y_min_mm": float(y_edges[iy]),
                "y_max_mm": float(y_edges[iy + 1]),
                "x_center_mm": float(x_centers[ix]),
                "y_center_mm": float(y_centers[iy]),
                "field_real": float(value.real),
                "field_imag": float(value.imag),
                "intensity": pixel_intensity,
                "normalized_intensity": pixel_intensity / peak,
                "phase_rad": float(phase[ix, iy]),
                "phase_valid": bool(phase_mask[ix, iy]),
            }


def write_branch_field_csv(path: str | Path, data: dict[str, object], wavelength_um: float) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=BRANCH_FIELD_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(iter_branch_field_csv_rows(data, wavelength_um))
