from __future__ import annotations

from typing import Iterator

import numpy as np


COHERENT_SUM_MODE_DEFAULT = "By source ray"
COHERENT_SUM_MODE_VALUES = (
    COHERENT_SUM_MODE_DEFAULT,
    "All rays coherent",
    "By source",
    "Incoherent power only",
)

COHERENT_DETECTOR_CSV_COLUMNS: tuple[str, ...] = (
    "filter",
    "terminal",
    "coordinate",
    "branch_codes",
    "coherence_mode",
    "coherence_groups",
    "polarization_model",
    "wavelength_um",
    "reference_op_mm",
    "sample_count",
    "bins",
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
    "field_p_real",
    "field_p_imag",
    "field_s_real",
    "field_s_imag",
    "field_x_real",
    "field_x_imag",
    "field_y_real",
    "field_y_imag",
    "field_z_real",
    "field_z_imag",
    "intensity",
    "normalized_intensity",
    "all_coherent_intensity",
    "normalized_all_coherent_intensity",
    "incoherent_power",
    "total_input_power",
    "total_coherent_power",
    "all_coherent_power",
    "peak_intensity",
)


def normalize_coherent_sum_mode(value: object) -> str:
    text = str(value or "").strip()
    return text if text in COHERENT_SUM_MODE_VALUES else COHERENT_SUM_MODE_DEFAULT


def coherent_detector_group_key(
    coherence_mode: str,
    source_id: object,
    source_ray_index: object,
    sample_index: int,
) -> str:
    source_key = str(source_id or "source:0")
    ray_key = int(source_ray_index or 0)
    mode = str(coherence_mode or "").strip()
    if mode == "All rays coherent":
        return "all"
    if mode == "By source":
        return source_key
    if mode == "By source ray":
        return f"{source_key}:{ray_key}"
    return f"sample:{int(sample_index):04d}:{source_key}:{ray_key}"


def coherent_detector_pair_key(code_a: str, code_b: str) -> str:
    first, second = sorted((str(code_a or ""), str(code_b or "")))
    return f"{first}|{second}"


def fft_angle_axis_mrad(edges: np.ndarray, wavelength_um: float) -> tuple[np.ndarray, float]:
    edges = np.asarray(edges, dtype=float).reshape(-1)
    if edges.size < 3:
        raise RuntimeError("Diffraction detector needs at least two detector bins.")
    step = float(np.median(np.diff(edges)))
    if not np.isfinite(step) or abs(step) <= 1e-12:
        raise RuntimeError("Diffraction detector has invalid detector-bin spacing.")
    count = int(edges.size - 1)
    wavelength_mm = max(float(wavelength_um), 1e-12) * 1e-3
    spatial_frequency = np.fft.fftshift(np.fft.fftfreq(count, d=abs(step)))
    sine_angle = np.clip(wavelength_mm * spatial_frequency, -1.0, 1.0)
    return np.arcsin(sine_angle) * 1000.0, abs(step)


def fft_vector_field_intensity(fields: tuple[np.ndarray, np.ndarray, np.ndarray]) -> np.ndarray:
    intensity = None
    for component in fields:
        component_array = np.asarray(component, dtype=np.complex128)
        spectrum = np.fft.fftshift(np.fft.fft2(component_array, norm="ortho"))
        component_intensity = np.abs(spectrum) ** 2
        intensity = component_intensity if intensity is None else intensity + component_intensity
    if intensity is None:
        return np.asarray([], dtype=float)
    return np.asarray(intensity, dtype=float)


def diffraction_detector_field_data_from_coherent(
    coherent: dict[str, object],
    wavelength_um: float,
) -> dict[str, object]:
    x_edges = np.asarray(coherent["x_edges"], dtype=float)
    y_edges = np.asarray(coherent["y_edges"], dtype=float)
    angle_x_mrad, dx_mm = fft_angle_axis_mrad(x_edges, wavelength_um)
    angle_y_mrad, dy_mm = fft_angle_axis_mrad(y_edges, wavelength_um)
    group_fields = dict(coherent.get("coherence_group_fields_xyz", {}) or {})
    if not group_fields:
        group_fields = {
            "all": (
                np.asarray(coherent["field_x"], dtype=np.complex128),
                np.asarray(coherent["field_y"], dtype=np.complex128),
                np.asarray(coherent["field_z"], dtype=np.complex128),
            )
        }
    diffraction_intensity = np.zeros((int(coherent["bins"]), int(coherent["bins"])), dtype=float)
    near_field_power = 0.0
    for fields in group_fields.values():
        vector_fields = tuple(np.asarray(component, dtype=np.complex128) for component in fields)
        diffraction_intensity += fft_vector_field_intensity(vector_fields)
        near_field_power += float(sum(np.sum(np.abs(component) ** 2) for component in vector_fields))
    if not np.any(diffraction_intensity > 0.0):
        raise RuntimeError("Diffraction detector angular spectrum is zero.")
    far_field_power = float(np.sum(diffraction_intensity))
    peak = float(np.max(diffraction_intensity))
    result = dict(coherent)
    result.update(
        {
            "diffraction_intensity": diffraction_intensity,
            "angle_x_mrad": angle_x_mrad,
            "angle_y_mrad": angle_y_mrad,
            "angle_extent_mrad": [
                float(angle_x_mrad[0]),
                float(angle_x_mrad[-1]),
                float(angle_y_mrad[0]),
                float(angle_y_mrad[-1]),
            ],
            "detector_dx_mm": dx_mm,
            "detector_dy_mm": dy_mm,
            "diffraction_near_field_power": near_field_power,
            "diffraction_far_field_power": far_field_power,
            "diffraction_peak_intensity": peak,
            "diffraction_group_count": len(group_fields),
            "diffraction_model": "Fraunhofer angular-spectrum FFT of coherent detector field",
        }
    )
    return result


def iter_coherent_detector_csv_rows(
    data: dict[str, object],
    wavelength_um: float,
) -> Iterator[dict[str, object]]:
    field = np.asarray(data["field"], dtype=np.complex128)
    field_p = np.asarray(data["field_p"], dtype=np.complex128)
    field_s = np.asarray(data["field_s"], dtype=np.complex128)
    field_x = np.asarray(data["field_x"], dtype=np.complex128)
    field_y = np.asarray(data["field_y"], dtype=np.complex128)
    field_z = np.asarray(data["field_z"], dtype=np.complex128)
    intensity = np.asarray(data["intensity"], dtype=float)
    power_hist = np.asarray(data["power_hist"], dtype=float)
    x_edges = np.asarray(data["x_edges"], dtype=float)
    y_edges = np.asarray(data["y_edges"], dtype=float)
    filter_text = str(data["filter_text"])
    terminal_label = str(data["terminal_label"])
    coordinate_label = str(data["coordinate_label"])
    branch_codes = ",".join(str(code) for code in data["branch_codes"])
    polarization_model = str(data.get("polarization_model", "Jones P/S vector sum"))
    coherence_mode = str(data.get("coherence_mode", COHERENT_SUM_MODE_DEFAULT))
    coherence_groups = int(data.get("coherence_group_count", 0) or 0)
    bins = int(data["bins"])
    sample_count = int(data["sample_count"])
    total_input_power = float(data["total_input_power"])
    total_coherent_power = float(data["total_coherent_power"])
    all_coherent_power = float(data.get("all_coherent_power", total_coherent_power))
    peak_intensity = float(data["peak_intensity"])
    reference_op_mm = float(data["reference_op_mm"])
    all_coherent_intensity = np.asarray(data.get("all_coherent_intensity", data["intensity"]), dtype=float)
    peak_all_coherent_intensity = float(np.max(all_coherent_intensity)) if all_coherent_intensity.size else 0.0
    for ix in range(field.shape[0]):
        x_min = float(x_edges[ix])
        x_max = float(x_edges[ix + 1])
        x_center = 0.5 * (x_min + x_max)
        for iy in range(field.shape[1]):
            y_min = float(y_edges[iy])
            y_max = float(y_edges[iy + 1])
            value = complex(field[ix, iy])
            value_p = complex(field_p[ix, iy])
            value_s = complex(field_s[ix, iy])
            value_x = complex(field_x[ix, iy])
            value_y = complex(field_y[ix, iy])
            value_z = complex(field_z[ix, iy])
            pixel_intensity = float(intensity[ix, iy])
            all_pixel_intensity = float(all_coherent_intensity[ix, iy])
            yield {
                "filter": filter_text,
                "terminal": terminal_label,
                "coordinate": coordinate_label,
                "branch_codes": branch_codes,
                "coherence_mode": coherence_mode,
                "coherence_groups": coherence_groups,
                "polarization_model": polarization_model,
                "wavelength_um": float(wavelength_um),
                "reference_op_mm": reference_op_mm,
                "sample_count": sample_count,
                "bins": bins,
                "bin_x": ix,
                "bin_y": iy,
                "x_min_mm": x_min,
                "x_max_mm": x_max,
                "y_min_mm": y_min,
                "y_max_mm": y_max,
                "x_center_mm": x_center,
                "y_center_mm": 0.5 * (y_min + y_max),
                "field_real": float(value.real),
                "field_imag": float(value.imag),
                "field_p_real": float(value_p.real),
                "field_p_imag": float(value_p.imag),
                "field_s_real": float(value_s.real),
                "field_s_imag": float(value_s.imag),
                "field_x_real": float(value_x.real),
                "field_x_imag": float(value_x.imag),
                "field_y_real": float(value_y.real),
                "field_y_imag": float(value_y.imag),
                "field_z_real": float(value_z.real),
                "field_z_imag": float(value_z.imag),
                "intensity": pixel_intensity,
                "normalized_intensity": pixel_intensity / max(peak_intensity, 1e-15),
                "all_coherent_intensity": all_pixel_intensity,
                "normalized_all_coherent_intensity": all_pixel_intensity / max(peak_all_coherent_intensity, 1e-15),
                "incoherent_power": float(power_hist[ix, iy]),
                "total_input_power": total_input_power,
                "total_coherent_power": total_coherent_power,
                "all_coherent_power": all_coherent_power,
                "peak_intensity": peak_intensity,
            }
