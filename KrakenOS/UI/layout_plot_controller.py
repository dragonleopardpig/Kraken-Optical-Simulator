"""Pure plot refresh helpers for the KrakenOS layout editor.

The renderer still lives in ``layout_editor``.  This module owns small,
testable decisions that identify whether a preview trace is still valid.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Iterable

import numpy as np

from KrakenOS.UI.scene_projector import SceneProjector2D


ANALYSIS_MODE_LABELS = {
    "none": "2D",
    "spot": "Spot",
    "psf": "PSF",
    "psf_map": "PSFMap",
    "rms": "RMS",
    "field_curvature": "FC/Dist",
    "relative_illumination": "Illum",
    "polarization": "Polarization",
    "lateral_color": "LatClr",
    "detector_map": "DetMap",
    "coherent_detector": "CohDet",
    "branch_field": "BField",
    "diffraction_detector": "Diffr",
    "field_map": "FieldMap",
    "illum_map": "IllumMap",
    "wavefront_map": "WfeMap",
    "atmosphere": "Atmos",
    "pupil": "Pupil",
    "seidel": "Seidel",
    "wavefront": "Wavefront",
    "zernike": "Zernike",
    "interferogram": "Interferogram",
    "tolerance_compare": "TolCmp",
    "mtf": "MTF",
}


def analysis_mode_label(mode: str) -> str:
    return ANALYSIS_MODE_LABELS.get(str(mode or ""), str(mode or "2D"))


def active_plot_modes(selected_analysis_modes: Iterable[str], *, suppress_analysis: bool = False) -> list[str]:
    if suppress_analysis:
        return []
    return [str(mode) for mode in selected_analysis_modes if str(mode)]


def plot_status_label(active_modes: list[str], layout_preview_mode: str = "none") -> str:
    if active_modes:
        return " + ".join(analysis_mode_label(mode) for mode in active_modes)
    return analysis_mode_label(layout_preview_mode or "none")


def trace_mode_summary_from_bundle(bundle: object) -> dict[str, str]:
    extra = dict(getattr(bundle, "extra", {}) or {})
    return {
        "requested": str(extra.get("trace_mode_requested", "Auto")),
        "active": str(extra.get("trace_mode_active", "Sequential")),
        "note": str(extra.get("trace_mode_note", "")).strip(),
    }


def project_scene_bundle(
    bundle: object,
    orientation: str,
    *,
    projector_factory: Callable[[str], object] = SceneProjector2D,
    refresh_auto_leg_graph: Callable[[object], object] | None = None,
    refresh_arm_view_choices: Callable[[], object] | None = None,
    filter_arm_view: Callable[[object], object] | None = None,
    filter_ray_display: Callable[[object], object] | None = None,
) -> object:
    projector = projector_factory(orientation)
    projected = projector.project_bundle(bundle)
    if refresh_auto_leg_graph is not None:
        refresh_auto_leg_graph(projected)
    if refresh_arm_view_choices is not None:
        refresh_arm_view_choices()
    if filter_arm_view is not None:
        projected = filter_arm_view(projected)
    if filter_ray_display is not None:
        projected = filter_ray_display(projected)
    return projected


def projected_pick_state(projected: object) -> tuple[dict[int, list[np.ndarray]], list[tuple[int, np.ndarray]]]:
    pick_regions: dict[int, list[np.ndarray]] = {}
    for region in getattr(projected, "pick_regions", ()) or ():
        try:
            row_index = int(getattr(region, "row_index"))
        except Exception:
            continue
        for polyline in getattr(region, "polylines", ()) or ():
            try:
                points = np.asarray(polyline, dtype=float)
            except Exception:
                continue
            if points.ndim == 2 and points.shape[0] >= 1 and points.shape[1] >= 2:
                pick_regions.setdefault(row_index, []).append(points[:, :2])

    ray_pick_regions: list[tuple[int, np.ndarray]] = []
    for ray in getattr(projected, "rays", ()) or ():
        try:
            ray_index = int(getattr(ray, "ray_index"))
            points = np.asarray(getattr(ray, "points_2d"), dtype=float)
        except Exception:
            continue
        if points.ndim == 2 and points.shape[0] >= 2 and points.shape[1] >= 2:
            ray_pick_regions.append((ray_index, points[:, :2]))
    return pick_regions, ray_pick_regions


def distance_to_polyline(point_xy: object, polyline_xy: object) -> float:
    pts = np.asarray(polyline_xy, dtype=float)
    point = np.asarray(point_xy, dtype=float)
    if pts.ndim != 2 or pts.shape[0] == 0:
        return float("inf")
    if pts.shape[0] == 1:
        return float(np.linalg.norm(point - pts[0]))
    best = float("inf")
    for start, end in zip(pts[:-1], pts[1:]):
        seg = end - start
        denom = float(np.dot(seg, seg))
        if denom <= 1e-12:
            dist = float(np.linalg.norm(point - start))
        else:
            t = float(np.clip(np.dot(point - start, seg) / denom, 0.0, 1.0))
            proj = start + t * seg
            dist = float(np.linalg.norm(point - proj))
        if dist < best:
            best = dist
    return best


def find_nearest_pick_region(
    point_xy: object,
    pick_regions: dict[int, list[np.ndarray]],
    *,
    transform_points: Callable[[np.ndarray], object] | None = None,
    threshold: float = 14.0,
) -> int | None:
    if not pick_regions:
        return None
    best_row = None
    best_distance = float("inf")
    click_xy = np.asarray(point_xy, dtype=float)
    for row_index, polylines in pick_regions.items():
        row_distance = float("inf")
        for polyline in polylines:
            try:
                points = np.asarray(polyline, dtype=float)
                if transform_points is not None:
                    points = np.asarray(transform_points(points), dtype=float)
            except Exception:
                continue
            if points.size == 0:
                continue
            row_distance = min(row_distance, distance_to_polyline(click_xy, points))
        if row_distance < best_distance:
            best_distance = row_distance
            best_row = int(row_index)
    if best_distance <= float(threshold):
        return best_row
    return None


def find_nearest_ray_region(
    point_xy: object,
    ray_pick_regions: Iterable[tuple[int, np.ndarray]],
    *,
    transform_points: Callable[[np.ndarray], object] | None = None,
    threshold: float = 10.0,
) -> int | None:
    best_ray = None
    best_distance = float("inf")
    click_xy = np.asarray(point_xy, dtype=float)
    for ray_index, polyline in ray_pick_regions:
        try:
            points = np.asarray(polyline, dtype=float)
            if transform_points is not None:
                points = np.asarray(transform_points(points), dtype=float)
        except Exception:
            continue
        if points.size == 0:
            continue
        ray_distance = distance_to_polyline(click_xy, points)
        if ray_distance < best_distance:
            best_distance = ray_distance
            best_ray = int(ray_index)
    if best_distance <= float(threshold):
        return best_ray
    return None


def _safe_sequence_length(value: object) -> int:
    if value is None:
        return 0
    try:
        return len(value)  # type: ignore[arg-type]
    except Exception:
        return 0


def trace_preview_summary(
    *,
    rays: object | None,
    bundle: object | None,
    trace_state: dict[str, object],
    final_surface_index: int,
    scalar_required: bool,
    batch_capable: bool,
    backend: str,
) -> dict[str, object]:
    surfaces_seq = getattr(rays, "SURFACE", ()) if rays is not None else ()
    total_rays = _safe_sequence_length(surfaces_seq)
    backend = str(backend or "")
    if not backend or backend == "none":
        backend = "Batch preview" if batch_capable else "Scalar TraceLoop"

    folded_paths = None
    if bundle is not None:
        extra = dict(getattr(bundle, "extra", {}) or {})
        folded_paths = extra.get("folded_ray_display_paths")
        requested = str(extra.get("trace_mode_requested", trace_state.get("requested", "Auto")))
        active = str(extra.get("trace_mode_active", trace_state.get("active", "Sequential")))
        note = str(extra.get("trace_mode_note", trace_state.get("note", "")))
    else:
        requested = str(trace_state.get("requested", "Auto"))
        active = str(trace_state.get("active", "Sequential"))
        note = str(trace_state.get("note", ""))

    if backend == "NsTraceLoop":
        family = "Non-sequential preview"
    elif folded_paths is not None:
        family = "Folded sequential preview"
    else:
        family = "Sequential preview"

    image_hits = 0
    ray_paths = getattr(bundle, "ray_paths", ()) if bundle is not None else ()
    if ray_paths:
        image_hits = int(sum(1 for path in ray_paths if getattr(path, "reaches_image", False)))
    elif rays is not None:
        for surfaces in surfaces_seq:
            try:
                surface_arr = np.asarray(surfaces, dtype=int).ravel()
            except Exception:
                continue
            if surface_arr.size and int(surface_arr[-1]) == int(final_surface_index):
                image_hits += 1
    stopped_rays = max(total_rays - image_hits, 0)
    return {
        "family": family,
        "requested": requested,
        "active": active,
        "note": note,
        "backend": backend,
        "total_rays": total_rays,
        "image_hits": image_hits,
        "stopped_rays": stopped_rays,
        "scalar_required": bool(scalar_required),
    }


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
