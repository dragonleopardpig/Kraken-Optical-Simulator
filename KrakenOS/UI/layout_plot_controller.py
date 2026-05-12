"""Pure plot refresh helpers for the KrakenOS layout editor.

The renderer still lives in ``layout_editor``.  This module owns small,
testable decisions that identify whether a preview trace is still valid.
"""

from __future__ import annotations

from typing import Iterable


def max_surface_radius(rows: Iterable[object], *, default: float = 1.0) -> float:
    max_radius = float(default)
    for row in rows:
        try:
            radius = max(float(getattr(row, "diameter", 0.0)) / 2.0, 0.5)
        except Exception:
            radius = 0.5
        max_radius = max(max_radius, radius)
    return max_radius


def build_preview_trace_signature(
    *,
    row_specs_signature: object,
    object_mode: object,
    field_type: object,
    field_value: object,
    field_count: object,
    requested_trace_mode: object,
    aperture_type_label: object,
    aperture_value: object,
    wavelength: object,
    ray_count: object,
    ray_height_factor: object,
    source_model: object,
    pupil_pattern_label: object,
    source_radius: object,
    source_cone_angle: object,
    gaussian_input_mode: object,
    gaussian_waist_radius: object,
    gaussian_waist_offset: object,
    gaussian_beam_diameter: object,
    gaussian_full_divergence: object,
    gaussian_waist_after_input: object,
    gaussian_m2: object,
    pupil_rad: object,
    pupil_theta: object,
    source_power: object,
    source_seed: object,
    source_origin: Iterable[object],
    source_direction: Iterable[object],
    source_angular_weight: object,
    nonseq_energy_probability: object,
    nonseq_ns_limit: object,
    nonseq_target_surface_index: object,
    full_pupil_mode: object,
) -> tuple[object, ...]:
    return (
        row_specs_signature,
        str(object_mode),
        str(field_type),
        float(field_value),
        int(field_count),
        str(requested_trace_mode),
        str(aperture_type_label),
        float(aperture_value),
        float(wavelength),
        int(ray_count),
        float(ray_height_factor),
        str(source_model),
        str(pupil_pattern_label),
        float(source_radius),
        float(source_cone_angle),
        str(gaussian_input_mode),
        float(gaussian_waist_radius),
        float(gaussian_waist_offset),
        float(gaussian_beam_diameter),
        float(gaussian_full_divergence),
        bool(gaussian_waist_after_input),
        float(gaussian_m2),
        float(pupil_rad),
        float(pupil_theta),
        float(source_power),
        int(source_seed),
        tuple(float(value) for value in source_origin),
        tuple(float(value) for value in source_direction),
        str(source_angular_weight),
        bool(nonseq_energy_probability),
        int(nonseq_ns_limit),
        nonseq_target_surface_index,
        bool(full_pupil_mode),
    )


def preview_trace_signature_matches(last_signature: object, current_signature: object) -> bool:
    return last_signature == current_signature
