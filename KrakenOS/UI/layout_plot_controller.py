"""Pure plot refresh helpers for the KrakenOS layout editor.

The renderer still lives in ``layout_editor``.  This module owns small,
testable decisions that identify whether a preview trace is still valid.
"""

from __future__ import annotations

from dataclasses import replace
from collections.abc import Callable
from typing import Iterable

import numpy as np

from KrakenOS.UI.scene_projector import SceneProjector2D
from KrakenOS.UI.scene_geometry import (
    LabelSpec,
    ProjectedRay2D,
    ProjectedRayEvent2D,
    ProjectedScene2D,
    SceneBundle,
    projected_ray_terminal_marker,
    projected_ray_terminal_status,
    ray_path_reaches_image_from_events,
)


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

RAY_EVENT_ACTION_LABELS = {
    "reflection": "Reflect",
    "reflect": "Reflect",
    "mirror": "Reflect",
    "reflect_mirror": "Reflect",
    "full_reflecting": "Reflect",
    "refraction": "Transmit",
    "refract": "Transmit",
    "transmit": "Transmit",
    "transmission": "Transmit",
    "pass": "Transmit",
    "tir": "TIR",
    "total_internal_reflection": "TIR",
    "reflect_tir": "TIR",
    "absorb": "Absorb",
    "absorbed": "Absorb",
    "absorption": "Absorb",
    "detector": "Detect",
    "hit_detector": "Detect",
    "image": "Detect",
    "termination": "Stop",
    "terminal": "Stop",
    "miss": "Miss",
    "missed_detector": "Miss",
    "missed_image": "Miss",
    "no_hit": "Escape",
    "no_next_intersection": "Escape",
    "escaped": "Escape",
    "escape": "Escape",
    "diffract": "Diffract",
    "diffraction": "Diffract",
    "split_reflect": "Split R",
    "split_transmit": "Split T",
}


def analysis_mode_label(mode: str) -> str:
    return ANALYSIS_MODE_LABELS.get(str(mode or ""), str(mode or "2D"))


def _event_action_label(event_type: object, event_kind: object = "") -> str:
    normalized = str(event_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    if not normalized and str(event_kind or "").strip().lower() == "terminal":
        normalized = "terminal"
    label = RAY_EVENT_ACTION_LABELS.get(normalized)
    if label:
        return label
    if not normalized:
        return ""
    return normalized.replace("_", " ").title()


def ray_event_display_label(event: object) -> str:
    """Return a compact label for a canonical ray/surface event."""
    face_id = str(getattr(event, "mesh_face_id", "") or "").strip()
    surface_id = getattr(event, "surface_id", None)
    if not face_id and surface_id is not None:
        try:
            face_id = f"S{int(surface_id)}"
        except Exception:
            face_id = f"S{surface_id}"
    event_kind = str(getattr(event, "event_kind", "") or "")
    event_type = str(getattr(event, "event_type", "") or "")
    terminal_status = str(getattr(event, "terminal_status", "") or "")
    action = _event_action_label(terminal_status or event_type, event_kind)
    if face_id and action:
        return f"{face_id} {action}"
    return face_id or action


def projected_ray_event_label_items(
    ray: object,
    *,
    include_terminal: bool = True,
    limit: int = 14,
) -> list[tuple[str, np.ndarray, str]]:
    """Return labels and projected points for selected-ray event annotations."""
    items: list[tuple[str, np.ndarray, str]] = []
    events = list(getattr(ray, "events_2d", []) or [])
    for event in events:
        event_kind = str(getattr(event, "event_kind", "") or "").strip().lower()
        if event_kind == "terminal" and not include_terminal:
            continue
        label = ray_event_display_label(event)
        if not label:
            continue
        point = np.asarray(getattr(event, "point_2d", np.full(2, np.nan)), dtype=float).reshape(-1)
        if point.size < 2 or not np.all(np.isfinite(point[:2])):
            continue
        items.append((label, np.asarray(point[:2], dtype=float), event_kind))
    if len(items) <= max(int(limit), 0):
        return items
    limit = max(int(limit), 1)
    terminal_items = [item for item in items if item[2] == "terminal"]
    surface_items = [item for item in items if item[2] != "terminal"]
    keep_surface = max(limit - len(terminal_items[:1]), 0)
    return surface_items[:keep_surface] + terminal_items[:1]


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
    filter_projection_slice: bool = False,
    filter_projection_axis_fields: bool = False,
    slice_tolerance: float | None = None,
    refresh_auto_leg_graph: Callable[[object], object] | None = None,
    refresh_arm_view_choices: Callable[[], object] | None = None,
    filter_arm_view: Callable[[object], object] | None = None,
    filter_ray_display: Callable[[object], object] | None = None,
) -> object:
    if filter_projection_axis_fields:
        bundle = scene_bundle_for_projection_axis_fields(bundle, orientation)
    if filter_projection_slice:
        bundle = scene_bundle_for_projection_slice(bundle, orientation, tolerance=slice_tolerance)
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


def scene_bundle_launch_sampling_mode(bundle: object | None) -> str:
    if bundle is None:
        return ""
    for path in list(getattr(bundle, "ray_paths", []) or []):
        for event in list(getattr(path, "events", []) or []):
            mode = str(getattr(event, "launch_sampling_mode", "") or "").strip().lower()
            if mode:
                return mode
    for event in list(getattr(bundle, "ray_events", []) or []):
        mode = str(getattr(event, "launch_sampling_mode", "") or "").strip().lower()
        if mode:
            return mode
    return ""


def _projection_slice_axis(orientation: str) -> int | None:
    plane = SceneProjector2D(orientation).plane
    if plane == "YZ":
        return 0
    if plane == "XZ":
        return 1
    return None


def _path_source_axis_value(path: object, axis: int, *, kind: str) -> float | None:
    attr = "source_direction" if kind == "direction" else "source_position"
    values = np.asarray(getattr(path, attr, []), dtype=float).reshape(-1)
    if values.size <= axis:
        return None
    value = float(values[axis])
    if not np.isfinite(value):
        return None
    return value


def _select_paths_near_axis_plane(paths: list[object], axis: int, *, kind: str) -> list[object]:
    pairs: list[tuple[object, float]] = []
    for path in paths:
        value = _path_source_axis_value(path, axis, kind=kind)
        if value is not None:
            pairs.append((path, abs(float(value))))
    if not pairs:
        return []
    values = np.asarray([value for _path, value in pairs], dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return []
    zero_limit = max(1e-9, 1e-7 * max(float(np.nanmax(finite)), 1.0))
    selected = [path for path, value in pairs if value <= zero_limit]
    if selected:
        return selected
    return []


def scene_bundle_for_projection_axis_fields(bundle: object, orientation: str) -> object:
    """Return *bundle* filtered to the field family visible in a 2-D plane.

    Canonical ``world_envelope`` traces carry the full 3-D pupil for every
    sampled field point.  A raw YZ/XZ projection of that entire 3-D grid is
    faithful but visually misleading because off-plane fields collapse into the
    selected plane.  For ordinary 2-D layout panes, keep the traced rays whose
    launch family belongs to that axis plane: YZ uses near-zero launch X angle,
    XZ uses near-zero launch Y angle, and XY remains the full footprint.
    """
    axis = _projection_slice_axis(orientation)
    if axis is None or not isinstance(bundle, SceneBundle):
        return bundle
    if scene_bundle_launch_sampling_mode(bundle) != "world_envelope":
        return bundle
    if _bundle_uses_native_nonsequential_projection(bundle):
        return bundle
    paths = list(getattr(bundle, "ray_paths", []) or [])
    if len(paths) <= 1:
        return bundle
    selected = _select_paths_near_axis_plane(paths, axis, kind="direction")
    if not selected:
        selected = _select_paths_near_axis_plane(paths, axis, kind="position")
    if selected and not bool(getattr(bundle, "has_off_axis", False)):
        selected = _select_representative_axis_slice_paths(selected, axis)
    if not selected or len(selected) == len(paths):
        return bundle
    selected_ray_indices = {int(getattr(path, "ray_index", -1)) for path in selected}
    ray_events = [
        event
        for event in list(getattr(bundle, "ray_events", []) or [])
        if int(getattr(event, "ray_index", -1)) in selected_ray_indices
    ]
    return replace(bundle, ray_paths=selected, ray_events=ray_events)


def _path_launch_plane_coordinates(path: object, axis: int) -> tuple[float, float] | None:
    try:
        source = np.asarray(getattr(path, "source_position", np.full(3, np.nan)), dtype=float).reshape(-1)
    except Exception:
        source = np.full(3, np.nan)
    if source.size >= 3 and np.all(np.isfinite(source[:3])):
        anchor = source[:3]
    else:
        points = np.asarray(getattr(path, "points_world", []), dtype=float)
        if points.ndim != 2 or points.shape[0] < 1 or points.shape[1] < 3:
            return None
        anchor = np.asarray(points[0, :3], dtype=float)
        if not np.all(np.isfinite(anchor)):
            return None
    along_axis = 1 if int(axis) == 0 else 0
    return float(anchor[along_axis]), float(anchor[int(axis)])


def _representative_axis_slice_target_count(group_size: int) -> int:
    size = max(1, int(group_size))
    if size <= 9:
        return size
    return min(size, max(9, 2 * int(np.ceil(np.sqrt(size))) + 1))


def _select_representative_axis_slice_paths(paths: list[object], axis: int) -> list[object]:
    """Keep an ordered, near-plane subset for readable YZ/XZ axis-field layouts.

    The 3-D world-envelope trace remains unchanged. This only chooses a
    representative meridional-looking subset from the traced family for the
    2-D axis-field display of centered sequential systems.
    """
    grouped: dict[tuple[int, str], list[tuple[int, object, float, float]]] = {}
    for ordinal, path in enumerate(paths):
        coordinates = _path_launch_plane_coordinates(path, axis)
        if coordinates is None:
            continue
        along_value, perpendicular_value = coordinates
        try:
            field_index = int(getattr(path, "field_index", 0))
        except Exception:
            field_index = 0
        source_id = str(getattr(path, "source_id", "") or "")
        grouped.setdefault((field_index, source_id), []).append(
            (ordinal, path, float(along_value), abs(float(perpendicular_value)))
        )
    if not grouped:
        return paths

    selected_ordinals: set[int] = set()
    for items in grouped.values():
        if len(items) <= 2:
            selected_ordinals.update(ordinal for ordinal, _path, _along, _perp in items)
            continue
        target_count = _representative_axis_slice_target_count(len(items))
        if len(items) <= target_count:
            selected_ordinals.update(ordinal for ordinal, _path, _along, _perp in items)
            continue
        along_values = np.asarray([item[2] for item in items], dtype=float)
        lower = float(np.min(along_values))
        upper = float(np.max(along_values))
        if not np.isfinite(lower) or not np.isfinite(upper):
            selected_ordinals.update(ordinal for ordinal, _path, _along, _perp in items[:target_count])
            continue
        if abs(upper - lower) <= 1e-9:
            ranked = sorted(items, key=lambda item: (item[3], abs(item[2]), item[0]))
            selected_ordinals.update(ordinal for ordinal, _path, _along, _perp in ranked[:target_count])
            continue
        targets = np.linspace(lower, upper, target_count)
        remaining = list(items)
        chosen: list[tuple[int, object, float, float]] = []
        for target in targets:
            if not remaining:
                break
            best = min(
                remaining,
                key=lambda item: (
                    abs(item[2] - float(target)),
                    item[3],
                    abs(item[2]),
                    item[0],
                ),
            )
            chosen.append(best)
            remaining.remove(best)
        selected_ordinals.update(ordinal for ordinal, _path, _along, _perp in chosen)

    if not selected_ordinals or len(selected_ordinals) >= len(paths):
        return paths
    return [path for ordinal, path in enumerate(paths) if ordinal in selected_ordinals]


def _ray_path_slice_distance(path: object, axis: int) -> float | None:
    points = np.asarray(getattr(path, "points_world", []), dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] <= axis:
        return None
    values = points[:, axis]
    finite = np.isfinite(values)
    if not np.any(finite):
        return None
    return float(np.max(np.abs(values[finite])))


def _projection_slice_tolerance(paths: Iterable[object], axis: int, requested: float | None = None) -> float:
    if requested is not None:
        try:
            value = float(requested)
        except Exception:
            value = 0.0
        if np.isfinite(value) and value > 0.0:
            return float(value)
    points: list[np.ndarray] = []
    for path in list(paths or []):
        pts = np.asarray(getattr(path, "points_world", []), dtype=float)
        if pts.ndim == 2 and pts.shape[0] and pts.shape[1] >= 3:
            finite = np.all(np.isfinite(pts[:, :3]), axis=1)
            if np.any(finite):
                points.append(pts[finite, :3])
    if not points:
        return 1e-7
    all_points = np.vstack(points)
    span = float(np.max(np.ptp(all_points, axis=0))) if all_points.size else 1.0
    axis_span = float(np.ptp(all_points[:, axis])) if all_points.size else 0.0
    return max(1e-7, 1e-7 * max(span, axis_span, 1.0))


def scene_bundle_for_projection_slice(
    bundle: object,
    orientation: str,
    *,
    tolerance: float | None = None,
) -> object:
    """Return *bundle* with ray paths filtered to the requested section plane.

    YZ renders rays whose 3-D path lies in X=0; XZ renders rays whose path lies
    in Y=0.  XY remains a projection of the visible 3-D footprint and is not
    section-filtered.  If a scene has no rays in the requested slice, return the
    original bundle rather than drawing an empty but plausible-looking layout.
    """
    axis = _projection_slice_axis(orientation)
    if axis is None or not isinstance(bundle, SceneBundle):
        return bundle
    if _bundle_uses_native_nonsequential_projection(bundle):
        return bundle
    paths = list(getattr(bundle, "ray_paths", []) or [])
    if len(paths) <= 1:
        return bundle
    limit = _projection_slice_tolerance(paths, axis, requested=tolerance)
    selected = []
    for path in paths:
        distance = _ray_path_slice_distance(path, axis)
        if distance is not None and distance <= limit:
            selected.append(path)
    if not selected or len(selected) == len(paths):
        return bundle
    selected_ray_indices = {int(getattr(path, "ray_index", -1)) for path in selected}
    ray_events = [
        event
        for event in list(getattr(bundle, "ray_events", []) or [])
        if int(getattr(event, "ray_index", -1)) in selected_ray_indices
    ]
    return replace(bundle, ray_paths=selected, ray_events=ray_events)


def _bundle_uses_native_nonsequential_projection(bundle: object) -> bool:
    extra = dict(getattr(bundle, "extra", {}) or {})
    mode_text = " ".join(
        str(extra.get(key, "") or "").strip().lower()
        for key in ("trace_mode_requested", "trace_mode_active", "trace_mode_note")
    )
    if "non-sequential" in mode_text or "nonseq" in mode_text:
        return True
    if list(getattr(bundle, "optical_volumes", []) or []):
        return True
    if list(getattr(bundle, "boundary_faces", []) or []):
        return True
    return False


def projected_scene_for_layout_render(projected: ProjectedScene2D, *, suppress_scene_labels: bool = False) -> ProjectedScene2D:
    if not bool(suppress_scene_labels):
        return projected
    return ProjectedScene2D(
        curves=list(projected.curves),
        rays=list(projected.rays),
        planes=list(projected.planes),
        labels=[],
        pick_regions=list(projected.pick_regions),
        bounds=projected.bounds,
    )


def filter_projected_labels_for_rows_and_sources(
    labels: Iterable[LabelSpec],
    allowed_row_indices: set[int],
    visible_source_ids: set[str],
    visible_terminal_row_indices: set[int] | None = None,
) -> list[LabelSpec]:
    allowed_rows = {int(value) for value in set(allowed_row_indices or set())}
    visible_sources = {str(value).strip() for value in set(visible_source_ids or set()) if str(value).strip()}
    terminal_rows = {int(value) for value in set(visible_terminal_row_indices or set())}
    filtered: list[LabelSpec] = []
    for label in list(labels or []):
        row_index = getattr(label, "row_index", None)
        if row_index is not None:
            try:
                row_value = int(row_index)
                if row_value in allowed_rows or row_value in terminal_rows:
                    filtered.append(label)
                    continue
            except Exception:
                pass
        source_id = str(getattr(label, "source_id", "") or "").strip()
        if source_id and source_id in visible_sources:
            filtered.append(label)
    return filtered


def filter_projected_labels_for_visible_ray_set(
    labels: Iterable[LabelSpec],
    visible_source_ids: set[str],
    visible_terminal_row_indices: set[int],
    all_terminal_row_indices: set[int],
) -> list[LabelSpec]:
    visible_sources = {str(value).strip() for value in set(visible_source_ids or set()) if str(value).strip()}
    visible_terminal_rows = {int(value) for value in set(visible_terminal_row_indices or set())}
    terminal_rows = {int(value) for value in set(all_terminal_row_indices or set())}
    filtered: list[LabelSpec] = []
    for label in list(labels or []):
        source_id = str(getattr(label, "source_id", "") or "").strip()
        if source_id:
            if source_id in visible_sources:
                filtered.append(label)
            continue
        row_index = getattr(label, "row_index", None)
        if row_index is not None:
            try:
                row_value = int(row_index)
            except Exception:
                row_value = None
            if row_value is not None and row_value in terminal_rows:
                if row_value in visible_terminal_rows:
                    filtered.append(label)
                continue
        filtered.append(label)
    return filtered


def projected_ray_terminal_surface_ids(rays: Iterable[object]) -> set[int]:
    surface_ids: set[int] = set()
    for ray in list(rays or []):
        raw_ids = getattr(ray, "terminal_surface_ids", ())
        try:
            arr = np.asarray(raw_ids, dtype=int).ravel()
        except Exception:
            arr = np.empty(0, dtype=int)
        surface_ids.update(int(value) for value in arr.tolist())
        for event in list(getattr(ray, "events_2d", []) or []):
            if str(getattr(event, "event_kind", "") or "") != "terminal":
                continue
            surface_id = getattr(event, "surface_id", None)
            if surface_id is None:
                continue
            try:
                surface_ids.add(int(surface_id))
            except Exception:
                continue
    return surface_ids


def representative_projected_rays_by_branch(rays: Iterable[ProjectedRay2D]) -> list[ProjectedRay2D]:
    groups: dict[tuple[str, str, str], list[ProjectedRay2D]] = {}
    for ray in list(rays or []):
        branch_path = str(getattr(ray, "branch_path", "") or "").strip()
        branch_label = str(getattr(ray, "branch_label", "") or "").strip()
        branch_key = branch_path or branch_label or f"ray:{int(getattr(ray, 'ray_index', 0))}"
        source_key = (
            str(getattr(ray, "source_id", "") or "").strip()
            or str(getattr(ray, "source_name", "") or "").strip()
        )
        terminal_key = projected_ray_terminal_status(ray)
        groups.setdefault((source_key, terminal_key, branch_key), []).append(ray)
    representatives: list[ProjectedRay2D] = []
    for group in groups.values():
        if len(group) <= 1:
            representatives.extend(group)
            continue
        endpoints = []
        lengths = []
        for ray in group:
            pts = np.asarray(ray.points_2d, dtype=float)
            finite = pts[np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])] if pts.ndim == 2 else np.empty((0, 2))
            if finite.shape[0] >= 1:
                endpoints.append(finite[-1])
            else:
                endpoints.append(np.asarray((np.nan, np.nan), dtype=float))
            if finite.shape[0] >= 2:
                lengths.append(float(np.sum(np.linalg.norm(np.diff(finite, axis=0), axis=1))))
            else:
                lengths.append(float("inf"))
        endpoint_array = np.asarray(endpoints, dtype=float)
        finite_endpoint = np.isfinite(endpoint_array[:, 0]) & np.isfinite(endpoint_array[:, 1])
        median_endpoint = (
            np.median(endpoint_array[finite_endpoint], axis=0)
            if np.any(finite_endpoint)
            else np.asarray((0.0, 0.0), dtype=float)
        )
        finite_lengths = np.asarray([value for value in lengths if np.isfinite(value)], dtype=float)
        median_length = float(np.median(finite_lengths)) if finite_lengths.size else 0.0

        def score(index: int) -> float:
            endpoint = endpoint_array[index]
            endpoint_score = (
                float(np.linalg.norm(endpoint - median_endpoint))
                if np.all(np.isfinite(endpoint))
                else 1e9
            )
            length = lengths[index]
            length_score = abs(float(length) - median_length) if np.isfinite(length) else 1e9
            return endpoint_score + 0.05 * length_score

        representatives.append(group[min(range(len(group)), key=score)])
    return sorted(representatives, key=lambda ray: int(getattr(ray, "ray_index", 0)))


def leg_label_text(workflow: str, leg_id: str, short_label: str, detail: str) -> str:
    compact_labels = {
        "michelson": {
            "input": "P1 Input",
            "transmit": "P2 Transmit",
            "reflect": "P3 Reflect",
            "detector": "P4 Detector",
        },
        "mach_zehnder": {
            "input": "P1 Input",
            "transmit": "P2 BS1-BS2 T",
            "reflect": "P3 BS1-BS2 R",
            "cross": "P4 Output A",
            "return": "P5 Output B",
        },
    }
    text = compact_labels.get(str(workflow or ""), {}).get(str(leg_id or "").strip().lower())
    if text:
        return text
    detail_text = str(detail or "").strip()
    short_text = str(short_label or "Path").strip()
    if detail_text and len(detail_text) <= 18:
        return f"{short_text}: {detail_text}"
    return short_text


def leg_geometry_point_at_fraction(leg: dict[str, object], fraction: float) -> np.ndarray | None:
    segments = list(leg.get("segments", []) or [])
    if not segments:
        return None
    lengths = [float(np.linalg.norm(np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float))) for p0, p1 in segments]
    total = float(sum(lengths))
    if total <= 1e-9:
        return None
    target = min(max(float(fraction), 0.0), 1.0) * total
    accumulated = 0.0
    for (p0, p1), length in zip(segments, lengths):
        if length <= 1e-12:
            continue
        if accumulated + length >= target:
            local = (target - accumulated) / length
            return np.asarray(p0, dtype=float) + (np.asarray(p1, dtype=float) - np.asarray(p0, dtype=float)) * local
        accumulated += length
    return np.asarray(segments[-1][1], dtype=float)


def projected_ray_surface_hit_markers(ray: object, points: object) -> list[tuple[int, int, int]]:
    """Return projected surface-hit markers as (ordinal, surface_id, point_index)."""
    pts = np.asarray(points, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 1:
        return []
    event_markers: list[tuple[int, int, int]] = []
    for event in list(getattr(ray, "events_2d", []) or []):
        if str(getattr(event, "event_kind", "") or "") != "surface":
            continue
        surface_id = getattr(event, "surface_id", None)
        if surface_id is None:
            continue
        try:
            point_index = int(getattr(event, "point_index", len(event_markers) + 1))
        except Exception:
            point_index = len(event_markers) + 1
        point_index = min(max(point_index, 0), pts.shape[0] - 1)
        event_markers.append((len(event_markers), int(surface_id), point_index))
    if event_markers:
        return event_markers

    surface_ids = np.asarray(getattr(ray, "surface_ids", []), dtype=int).ravel()
    markers: list[tuple[int, int, int]] = []
    for hit_index, surface_id in enumerate(surface_ids.tolist()):
        if pts.shape[0] >= surface_ids.size + 1:
            point_index = min(max(int(hit_index) + 1, 0), pts.shape[0] - 1)
        else:
            point_index = min(max(int(hit_index), 0), pts.shape[0] - 1)
        markers.append((hit_index, int(surface_id), point_index))
    return markers


def projected_ray_events_for_segment(
    ray: object,
    start_index: int,
    end_index: int,
    segment_points: object,
) -> list[ProjectedRayEvent2D]:
    """Copy projected event markers that fall inside a displayed ray subsegment."""
    events = list(getattr(ray, "events_2d", []) or [])
    if not events:
        return []
    points = np.asarray(segment_points, dtype=float)
    if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 2:
        return []
    start = int(start_index)
    end = int(end_index)
    if end < start:
        start, end = end, start
    span = max(end - start, 1)
    copied: list[ProjectedRayEvent2D] = []
    for event in events:
        try:
            original_index = int(getattr(event, "point_index", -1))
        except Exception:
            continue
        if original_index < start or original_index > end:
            continue
        fraction = min(max((original_index - start) / float(span), 0.0), 1.0)
        local_index = 0 if fraction <= 0.5 else points.shape[0] - 1
        point_2d = points[0, :2] + (points[-1, :2] - points[0, :2]) * fraction
        surface_id = getattr(event, "surface_id", None)
        copied.append(
            ProjectedRayEvent2D(
                event_id=str(getattr(event, "event_id", "") or ""),
                event_kind=str(getattr(event, "event_kind", "") or ""),
                event_type=str(getattr(event, "event_type", "") or ""),
                step=int(getattr(event, "step", 0) or 0),
                surface_id=None if surface_id is None else int(surface_id),
                mesh_face_id=str(getattr(event, "mesh_face_id", "") or ""),
                surface_name=str(getattr(event, "surface_name", "") or ""),
                interaction_model=str(getattr(event, "interaction_model", "") or ""),
                point_index=int(local_index),
                point_2d=np.asarray(point_2d, dtype=float),
                terminal_status=str(getattr(event, "terminal_status", "") or ""),
            )
        )
    return copied


def physical_leg_label_plan(
    *,
    definitions: Iterable[tuple[str, str, str]],
    geometry: dict[str, dict[str, object]],
    workflow: str,
    axis_limits: tuple[float, float, float, float],
    view_leg_id: str = "",
) -> list[dict[str, object]]:
    x0, x1, y0, y1 = axis_limits
    x_min, x_max = min(float(x0), float(x1)), max(float(x0), float(x1))
    y_min, y_max = min(float(y0), float(y1)), max(float(y0), float(y1))
    span_x = max(x_max - x_min, 1.0)
    span_y = max(y_max - y_min, 1.0)
    workflow = str(workflow or "")
    if workflow == "mach_zehnder":
        offsets = {
            "input": np.array([-0.020 * span_x, 0.060 * span_y], dtype=float),
            "transmit": np.array([0.030 * span_x, 0.060 * span_y], dtype=float),
            "reflect": np.array([-0.050 * span_x, -0.030 * span_y], dtype=float),
            "cross": np.array([0.050 * span_x, 0.050 * span_y], dtype=float),
            "return": np.array([0.055 * span_x, -0.020 * span_y], dtype=float),
        }
        marker_fraction = {
            "input": 0.45,
            "transmit": 0.28,
            "reflect": 0.62,
            "cross": 0.55,
            "return": 0.55,
        }
    elif workflow == "michelson":
        offsets = {
            "input": np.array([-0.020 * span_x, 0.060 * span_y], dtype=float),
            "reflect": np.array([0.075 * span_x, 0.000 * span_y], dtype=float),
            "transmit": np.array([0.030 * span_x, 0.055 * span_y], dtype=float),
            "detector": np.array([0.075 * span_x, -0.010 * span_y], dtype=float),
        }
        marker_fraction = {
            "input": 0.50,
            "reflect": 0.46,
            "transmit": 0.48,
            "detector": 0.72,
        }
    else:
        offsets = {}
        marker_fraction = {leg_id: 0.50 for leg_id, _short_label, _detail in definitions}

    view_leg_id = str(view_leg_id or "").strip()
    plans: list[dict[str, object]] = []
    for leg_id, short_label, detail in definitions:
        leg_id = str(leg_id or "").strip()
        if view_leg_id and leg_id != view_leg_id:
            continue
        leg = geometry.get(leg_id)
        if leg is None:
            continue
        fraction = float(marker_fraction.get(leg_id, 0.5))
        point = leg_geometry_point_at_fraction(leg, min(max(fraction, 0.05), 0.95))
        if point is None:
            continue
        if leg_id in offsets:
            offset = offsets[leg_id]
        else:
            direction = np.asarray(leg.get("unit", np.array([1.0, 0.0])), dtype=float).ravel()
            if direction.size < 2 or float(np.linalg.norm(direction[:2])) <= 1e-9:
                direction = np.array([1.0, 0.0], dtype=float)
            direction = direction[:2] / max(float(np.linalg.norm(direction[:2])), 1e-12)
            normal = np.array([-direction[1], direction[0]], dtype=float)
            offset = normal * (0.055 * min(span_x, span_y)) + direction * (0.020 * min(span_x, span_y))
        text_point = np.asarray(point, dtype=float)[:2] + offset
        text_point[0] = min(max(float(text_point[0]), x_min + 0.03 * span_x), x_max - 0.03 * span_x)
        text_point[1] = min(max(float(text_point[1]), y_min + 0.04 * span_y), y_max - 0.04 * span_y)
        plans.append(
            {
                "leg_id": leg_id,
                "label": leg_label_text(workflow, leg_id, short_label, detail),
                "point": np.asarray(point, dtype=float)[:2],
                "text_point": text_point,
            }
        )
    return plans


def folded_path_plane_at_distance(
    path_distance: float,
    vertices: Iterable[tuple[float, object]],
    initial_direction: object,
) -> tuple[np.ndarray, np.ndarray] | None:
    if not np.isfinite(float(path_distance)):
        return None
    path_vertices: list[tuple[float, np.ndarray]] = []
    for distance, point in list(vertices or []):
        try:
            d_val = float(distance)
            p_val = np.asarray(point, dtype=float).reshape(-1)
        except Exception:
            continue
        if p_val.size < 2 or not np.all(np.isfinite(p_val[:2])):
            continue
        path_vertices.append((d_val, np.asarray(p_val[:2], dtype=float)))
    if len(path_vertices) < 2:
        return None
    path_vertices.sort(key=lambda item: item[0])
    s = float(path_distance)
    tolerance = max(1e-6, 1e-6 * max(path_vertices[-1][0] - path_vertices[0][0], 1.0))
    if s < path_vertices[0][0] - tolerance or s > path_vertices[-1][0] + tolerance:
        return None
    s = min(max(s, path_vertices[0][0]), path_vertices[-1][0])
    fallback_axis = np.asarray(initial_direction, dtype=float).reshape(-1)
    if fallback_axis.size < 2 or not np.all(np.isfinite(fallback_axis[:2])):
        fallback_axis = np.asarray((1.0, 0.0), dtype=float)
    fallback_axis = np.asarray(fallback_axis[:2], dtype=float)
    for (d0, p0), (d1, p1) in zip(path_vertices, path_vertices[1:]):
        if s > d1 + tolerance:
            continue
        span = max(float(d1) - float(d0), 1e-12)
        t = min(max((s - float(d0)) / span, 0.0), 1.0)
        center = p0 + (p1 - p0) * t
        axis = p1 - p0
        norm = float(np.linalg.norm(axis))
        if norm <= 1e-12:
            axis = fallback_axis
            norm = float(np.linalg.norm(axis))
        if norm <= 1e-12:
            axis = np.asarray((1.0, 0.0), dtype=float)
            norm = 1.0
        axis = axis / norm
        tangent = np.asarray((-axis[1], axis[0]), dtype=float)
        tangent /= max(float(np.linalg.norm(tangent)), 1e-12)
        return center, tangent
    return None


def folded_optics_marker_plan(
    marker_specs: Iterable[tuple[str, object, object, str]],
    *,
    axis_limits: tuple[float, float, float, float],
    path_plane_at_distance: Callable[[float], tuple[np.ndarray, np.ndarray] | None],
) -> list[dict[str, object]]:
    x0, x1, y0, y1 = axis_limits
    x_min, x_max = min(float(x0), float(x1)), max(float(x0), float(x1))
    y_min, y_max = min(float(y0), float(y1)), max(float(y0), float(y1))
    span_x = max(x_max - x_min, 1e-9)
    span_y = max(y_max - y_min, 1e-9)
    marker_half = max(2.0, min(0.09 * span_x, 0.16 * span_y))
    cap_half = max(0.8, min(0.025 * span_x, 0.035 * span_y))
    plans: list[dict[str, object]] = []
    for index, (label, path_distance, half_length, color) in enumerate(list(marker_specs or [])):
        if path_distance is None:
            continue
        try:
            plane = path_plane_at_distance(float(path_distance))
        except Exception:
            plane = None
        if plane is None:
            continue
        center, tangent = plane
        center = np.asarray(center, dtype=float).reshape(-1)
        tangent = np.asarray(tangent, dtype=float).reshape(-1)
        if center.size < 2 or tangent.size < 2:
            continue
        center = np.asarray(center[:2], dtype=float)
        tangent = np.asarray(tangent[:2], dtype=float)
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm <= 1e-12 or not (np.all(np.isfinite(center)) and np.all(np.isfinite(tangent))):
            continue
        tangent = tangent / tangent_norm
        if not (x_min <= float(center[0]) <= x_max and y_min <= float(center[1]) <= y_max):
            continue
        try:
            half_value = float(half_length)
        except Exception:
            half_value = 0.0
        use_extent = str(label) in {"EP", "XP"} and np.isfinite(half_value) and half_value > 1e-9
        half_span = half_value if use_extent else marker_half
        p0 = center - tangent * half_span
        p1 = center + tangent * half_span
        normal = np.asarray((-tangent[1], tangent[0]), dtype=float)
        normal /= max(float(np.linalg.norm(normal)), 1e-12)
        offsets = (0.030, 0.060, -0.040, 0.090)
        tangent_stagger = ((index % 2) - 0.5) * 0.75 * marker_half
        label_pos = center + normal * offsets[index % len(offsets)] * span_y + tangent * tangent_stagger
        label_pos[0] = min(max(float(label_pos[0]), x_min + 0.02 * span_x), x_max - 0.02 * span_x)
        label_pos[1] = min(max(float(label_pos[1]), y_min + 0.04 * span_y), y_max - 0.04 * span_y)
        plans.append(
            {
                "label": str(label),
                "color": str(color),
                "p0": np.asarray(p0, dtype=float),
                "p1": np.asarray(p1, dtype=float),
                "label_pos": np.asarray(label_pos, dtype=float),
                "use_extent": bool(use_extent),
                "cap_half": float(cap_half),
            }
        )
    return plans


def folded_scan_overlay_style(ray_count_hint: int) -> dict[str, float]:
    count = max(1, int(ray_count_hint))
    if count <= 9:
        return {"linewidth": 1.1, "alpha": 0.92}
    if count <= 16:
        return {"linewidth": 0.7, "alpha": 0.48}
    return {"linewidth": 0.55, "alpha": 0.32}


def folded_scan_overlay_plan(
    paths: Iterable[object],
    *,
    field_theta: float,
    display_tilt: float,
    mirror_center: object,
    mirror_diameter: float,
    color: str,
    ray_count_hint: int,
) -> dict[str, object]:
    valid_paths: list[np.ndarray] = []
    bounds_points: list[np.ndarray] = []
    for path in list(paths or []):
        pts = np.asarray(path, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 2:
            continue
        pts = np.asarray(pts[:, :2], dtype=float)
        valid_paths.append(pts)
        bounds_points.append(pts)
    draw_overlay_geometry = abs(float(field_theta)) > 1e-9
    style = folded_scan_overlay_style(ray_count_hint)
    mirror_line = None
    if draw_overlay_geometry:
        tangent = np.asarray(
            (np.cos(np.deg2rad(float(display_tilt))), np.sin(np.deg2rad(float(display_tilt)))),
            dtype=float,
        )
        tangent /= max(float(np.linalg.norm(tangent)), 1e-12)
        center = np.asarray(mirror_center, dtype=float).reshape(-1)
        if center.size >= 2 and np.all(np.isfinite(center[:2])):
            half = max(float(mirror_diameter) / 2.0, 0.5)
            mirror_line = np.vstack((center[:2] - tangent * half, center[:2] + tangent * half))
            bounds_points.append(mirror_line)

    hits = [path[-1] for path in valid_paths if path.shape[0] >= 2]
    label_point = None
    if hits:
        hit = np.mean(np.vstack(hits), axis=0)
        bounds_points.append(np.asarray([hit], dtype=float))
        prev_hits = [path[-2] for path in valid_paths if path.shape[0] >= 2]
        if prev_hits:
            previous = np.mean(np.vstack(prev_hits), axis=0)
            final_dir = hit - previous
            final_dir /= max(float(np.linalg.norm(final_dir)), 1e-12)
            label_point = hit - final_dir * 12.0
        else:
            label_point = hit + np.asarray((0.0, 5.0), dtype=float)
        bounds_points.append(np.asarray([label_point], dtype=float))

    return {
        "paths": valid_paths if draw_overlay_geometry else [],
        "mirror_line": mirror_line,
        "label_point": label_point,
        "label": f"theta={float(field_theta):g} deg",
        "color": str(color),
        "linewidth": float(style["linewidth"]),
        "alpha": float(style["alpha"]),
        "bounds_points": bounds_points,
    }


def folded_fallback_source_start_specs(
    point: object,
    direction: object,
    tangent: object,
    field_values: Iterable[object],
    pupil_samples: Iterable[object],
    *,
    object_mode: str,
    object_distance: float,
) -> list[tuple[np.ndarray, np.ndarray]]:
    base_point = np.asarray(point, dtype=float).reshape(-1)
    axis = np.asarray(direction, dtype=float).reshape(-1)
    transverse = np.asarray(tangent, dtype=float).reshape(-1)
    if base_point.size < 2 or axis.size < 2 or transverse.size < 2:
        return []
    base_point = np.asarray(base_point[:2], dtype=float)
    axis = np.asarray(axis[:2], dtype=float)
    transverse = np.asarray(transverse[:2], dtype=float)
    axis_norm = float(np.linalg.norm(axis))
    trans_norm = float(np.linalg.norm(transverse))
    if axis_norm <= 1e-12 or trans_norm <= 1e-12:
        return []
    axis = axis / axis_norm
    transverse = transverse / trans_norm
    fields = [float(value) for value in list(field_values or [])]
    pupils = [float(value) for value in list(pupil_samples or [])]
    starts: list[tuple[np.ndarray, np.ndarray]] = []
    if str(object_mode or "") == "Infinity":
        for field_value in fields:
            angle = np.deg2rad(float(field_value))
            chief_dir = np.cos(angle) * axis + np.sin(angle) * transverse
            chief_dir /= max(float(np.linalg.norm(chief_dir)), 1e-12)
            for pupil_y in pupils:
                starts.append((base_point + transverse * float(pupil_y), chief_dir.copy()))
    else:
        distance = max(float(object_distance), 1e-9)
        for field_value in fields:
            origin_base = base_point + transverse * float(field_value)
            for pupil_y in pupils:
                target = base_point + axis * distance + transverse * float(pupil_y)
                ray_dir = target - origin_base
                ray_dir /= max(float(np.linalg.norm(ray_dir)), 1e-12)
                starts.append((origin_base.copy(), ray_dir))
    return starts


def folded_scan_incoming_states(nominal_paths: Iterable[object]) -> list[tuple[np.ndarray, np.ndarray]]:
    states: list[tuple[np.ndarray, np.ndarray]] = []
    for path in list(nominal_paths or []):
        pts = np.asarray(path, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2 or pts.shape[1] < 2:
            continue
        previous = np.asarray(pts[-2, :2], dtype=float)
        nominal_hit = np.asarray(pts[-1, :2], dtype=float)
        ray_dir = nominal_hit - previous
        ray_norm = float(np.linalg.norm(ray_dir))
        if ray_norm <= 1e-12:
            continue
        states.append((previous, ray_dir / ray_norm))
    return states


def arm_ray_label_targets(
    projected: object,
    catalog: list[dict[str, str]],
    view_key: str = "",
    *,
    indices_for_arm_key: Callable[[str], Iterable[int]],
    branch_path_for_arm_key: Callable[[str], str],
    ray_matches_arm_key: Callable[[object, str], bool],
    branch_path_selector_sequence: Callable[[str], Iterable[str]],
) -> list[dict[str, object]]:
    targets: list[dict[str, object]] = []
    rays = list(getattr(projected, "rays", []) or [])
    if not rays:
        return targets
    view_key = str(view_key or "")
    for arm_index, entry in enumerate(catalog):
        arm_key = str(entry.get("key", "") or "")
        if view_key and arm_key != view_key:
            continue
        arm_indices = {int(index) for index in indices_for_arm_key(arm_key)}
        target_path = str(branch_path_for_arm_key(arm_key) or "")
        candidates: list[tuple[np.ndarray, np.ndarray]] = []
        for ray in rays:
            points = np.asarray(getattr(ray, "points_2d", []), dtype=float)
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            surface_markers = projected_ray_surface_hit_markers(ray, points)
            ray_matches_arm = bool(ray_matches_arm_key(ray, arm_key))
            matching_hit_positions = [
                (hit_index, point_index)
                for hit_index, surface_id, point_index in surface_markers
                if int(surface_id) in arm_indices
            ]
            if target_path:
                if not ray_matches_arm:
                    continue
                start_index = max(0, points.shape[0] - 2)
                end_index = points.shape[0] - 1
                selector_code = "".join(str(item) for item in branch_path_selector_sequence(target_path))[-2:]
                marker_fraction = {
                    "TT": 0.36,
                    "RR": 0.64,
                    "TR": 0.36,
                    "RT": 0.64,
                }.get(selector_code, 0.5)
            elif matching_hit_positions:
                _hit_index, point_index = matching_hit_positions[0]
                end_index = max(0, min(int(point_index), points.shape[0] - 1))
                start_index = max(0, min(end_index - 1, points.shape[0] - 1))
                marker_fraction = 0.5
            elif ray_matches_arm:
                start_index = 1 if points.shape[0] > 2 else 0
                end_index = min(points.shape[0] - 1, max(start_index + 1, points.shape[0] // 2))
                marker_fraction = 0.5
            else:
                continue
            p0 = np.asarray(points[start_index], dtype=float)
            p1 = np.asarray(points[end_index], dtype=float)
            if not np.all(np.isfinite(p0)) or not np.all(np.isfinite(p1)):
                continue
            tangent = p1 - p0
            if np.linalg.norm(tangent) <= 1e-9:
                tangent = np.asarray(points[-1], dtype=float) - np.asarray(points[0], dtype=float)
            if np.linalg.norm(tangent) <= 1e-9:
                continue
            marker_fraction = min(max(float(marker_fraction), 0.05), 0.95)
            candidates.append((p0 + (p1 - p0) * marker_fraction, tangent))
        if not candidates:
            continue
        candidate_points = np.vstack([point for point, _tangent in candidates])
        median_point = np.median(candidate_points, axis=0)
        point, tangent = min(candidates, key=lambda candidate: float(np.linalg.norm(candidate[0] - median_point)))
        targets.append(
            {
                "entry": entry,
                "point": point,
                "tangent": tangent,
                "arm_index": arm_index,
                "branch_code": "".join(str(item) for item in branch_path_selector_sequence(target_path))[-2:] if target_path else "",
            }
        )
    return targets


def arm_ray_label_plan(
    targets: Iterable[dict[str, object]],
    *,
    axis_limits: tuple[float, float, float, float],
    palette: tuple[str, ...],
) -> list[dict[str, object]]:
    targets = list(targets)
    if not targets:
        return []
    x0, x1, y0, y1 = axis_limits
    x_min, x_max = min(float(x0), float(x1)), max(float(x0), float(x1))
    y_min, y_max = min(float(y0), float(y1)), max(float(y0), float(y1))
    span_x = max(x_max - x_min, 1.0)
    span_y = max(y_max - y_min, 1.0)
    point_tolerance = max(5.0, 0.035 * min(span_x, span_y))
    clusters: list[dict[str, object]] = []
    for target in targets:
        point = np.asarray(target.get("point"), dtype=float)
        tangent = np.asarray(target.get("tangent"), dtype=float)
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm <= 1e-9:
            continue
        tangent = tangent / tangent_norm
        entry = target.get("entry")
        entry_key = str(entry.get("key", "") or "") if isinstance(entry, dict) else ""
        if entry_key.startswith("path|"):
            clusters.append({"targets": [target], "point": point, "tangent": tangent, "count": 1})
            continue
        matched_cluster = False
        for cluster in clusters:
            cluster_point = np.asarray(cluster["point"], dtype=float)
            cluster_tangent = np.asarray(cluster["tangent"], dtype=float)
            same_line = abs(float(np.dot(tangent, cluster_tangent))) >= 0.985
            if same_line and float(np.linalg.norm(point - cluster_point)) <= point_tolerance:
                cluster_targets = cluster["targets"]
                if isinstance(cluster_targets, list):
                    cluster_targets.append(target)
                count = int(cluster.get("count", 1)) + 1
                cluster["count"] = count
                cluster["point"] = cluster_point + (point - cluster_point) / float(count)
                matched_cluster = True
                break
        if not matched_cluster:
            clusters.append({"targets": [target], "point": point, "tangent": tangent, "count": 1})

    plans: list[dict[str, object]] = []
    output_port_index = 1
    for cluster in clusters:
        cluster_targets = cluster.get("targets")
        if not isinstance(cluster_targets, list) or not cluster_targets:
            continue
        point = np.asarray(cluster["point"], dtype=float)
        tangent = np.asarray(cluster["tangent"], dtype=float)
        branch_code = ""
        if len(cluster_targets) == 1:
            branch_code = str(cluster_targets[0].get("branch_code", "") or "").upper()
        branch_offsets = {
            "TT": np.array([0.060 * span_x, 0.048 * span_y], dtype=float),
            "RR": np.array([-0.060 * span_x, -0.048 * span_y], dtype=float),
            "TR": np.array([0.060 * span_x, -0.052 * span_y], dtype=float),
            "RT": np.array([0.060 * span_x, 0.052 * span_y], dtype=float),
        }
        if branch_code in branch_offsets:
            offset = branch_offsets[branch_code]
        elif abs(float(tangent[0])) >= abs(float(tangent[1])):
            downstream = 1.0 if float(tangent[0]) >= 0.0 else -1.0
            offset = np.array([0.035 * span_x * downstream, 0.045 * span_y], dtype=float)
        else:
            downstream = 1.0 if float(tangent[1]) >= 0.0 else -1.0
            offset = np.array([0.045 * span_x, 0.035 * span_y * downstream], dtype=float)

        arm_index = min(int(target.get("arm_index", 0)) for target in cluster_targets)
        if not branch_code:
            offset *= 1.0 + 0.18 * (arm_index % 3)
        text_point = point + offset
        text_point[0] = min(max(float(text_point[0]), x_min + 0.03 * span_x), x_max - 0.03 * span_x)
        text_point[1] = min(max(float(text_point[1]), y_min + 0.04 * span_y), y_max - 0.04 * span_y)

        entries: list[dict[str, object]] = []
        for target in cluster_targets:
            entry = target.get("entry")
            if isinstance(entry, dict) and str(entry.get("key", "") or ""):
                entries.append(entry)
        if not entries:
            continue
        is_branch_output = all(str(entry.get("key", "") or "").startswith("path|") for entry in entries)
        is_branch_group = len(entries) > 1 and is_branch_output
        color = "#334155" if is_branch_output else palette[arm_index % len(palette)]
        if len(entries) == 1:
            entry = entries[0]
            detail = str(entry.get("detail", "") or "").strip()
            short_label = str(entry.get("short_label", "") or "Path").strip()
            label = f"{short_label}: {detail}" if detail else short_label
        else:
            branch_codes = {
                str(target.get("branch_code", "") or "").upper()
                for target in cluster_targets
                if isinstance(target.get("entry"), dict)
                and str(target.get("entry", {}).get("key", "") or "").startswith("path|")
                and str(target.get("branch_code", "") or "")
            }
            if branch_codes == {"TR", "RT"}:
                title = "Detector output"
            elif branch_codes == {"TT", "RR"}:
                title = "Source return"
            else:
                title = f"Output {output_port_index}" if is_branch_group else "Shared ray"
            if is_branch_group:
                output_port_index += 1
            lines = [title]
            for entry in entries[:5]:
                detail = str(entry.get("detail", "") or "").strip()
                short_label = str(entry.get("short_label", "") or "Path").strip()
                lines.append(f"{short_label}: {detail}" if detail else short_label)
            if len(entries) > 5:
                lines.append(f"+{len(entries) - 5} more")
            label = "\n".join(lines)
        plans.append(
            {
                "label": label,
                "point": point,
                "text_point": text_point,
                "color": color,
                "marker_color": "#111827" if branch_code else color,
                "entry_keys": [str(entry.get("key", "") or "") for entry in entries],
            }
        )
    return plans


def thin_lens_glyph_polyline(
    row: object,
    z_pos: float,
    *,
    transform: object | None = None,
    project_fn: Callable[[object, object], tuple[object, object]] | None = None,
    samples: int = 65,
) -> np.ndarray | None:
    try:
        diameter = float(getattr(row, "diameter", 0.0))
    except Exception:
        diameter = 0.0
    half_height = max(diameter / 2.0, 0.5)
    visual_half_width = min(max(0.12 * max(diameter, 1.0), 1.5), max(0.45 * half_height, 2.5))
    samples = max(int(samples), 9)
    u = np.linspace(-1.0, 1.0, samples, dtype=float)
    local_y = half_height * u
    try:
        focal = float(getattr(row, "rc", 0.0) or 0.0)
    except Exception:
        focal = 0.0

    if focal < 0.0:
        center_half_width = max(0.22 * visual_half_width, 0.35)
        profile = center_half_width + (visual_half_width - center_half_width) * (u * u)
    else:
        profile = visual_half_width * (1.0 - u * u)

    outline_y = np.concatenate((local_y, local_y[::-1], local_y[:1]))
    outline_z = np.concatenate((-profile, profile[::-1], -profile[:1]))

    matrix = None
    if transform is not None:
        try:
            candidate = np.asarray(transform, dtype=float)
            if candidate.shape == (4, 4):
                matrix = candidate
        except Exception:
            matrix = None

    if matrix is not None:
        local = np.column_stack((np.zeros_like(outline_y), outline_y, outline_z, np.ones_like(outline_y)))
        world = (matrix @ local.T).T
        world_z = world[:, 2]
        world_y = world[:, 1]
    else:
        try:
            center_z = float(z_pos) + float(getattr(row, "desp_z", 0.0) or 0.0)
            center_y = float(getattr(row, "desp_y", 0.0) or 0.0)
        except Exception:
            center_z = float(z_pos)
            center_y = 0.0
        world_z = center_z + outline_z
        world_y = center_y + outline_y

    if project_fn is not None:
        try:
            x_vals, y_vals = project_fn(world_z, world_y)
            points = np.column_stack((np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)))
        except Exception:
            return None
    else:
        points = np.column_stack((np.asarray(world_z, dtype=float), np.asarray(world_y, dtype=float)))

    if points.ndim != 2 or points.shape[0] < 2 or not np.any(np.all(np.isfinite(points), axis=1)):
        return None
    return points


def projected_ray_pick_polylines(ray: object) -> list[np.ndarray]:
    polylines: list[np.ndarray] = []
    try:
        points = np.asarray(getattr(ray, "points_2d"), dtype=float)
    except Exception:
        points = np.empty((0, 2), dtype=float)
    if points.ndim == 2 and points.shape[0] >= 2 and points.shape[1] >= 2:
        finite = np.isfinite(points[:, 0]) & np.isfinite(points[:, 1])
        start_index: int | None = None
        for index, ok in enumerate(finite.tolist() + [False]):
            if ok and start_index is None:
                start_index = index
            elif not ok and start_index is not None:
                if index - start_index >= 2:
                    polylines.append(np.asarray(points[start_index:index, :2], dtype=float))
                start_index = None
    has_terminal_event = any(
        str(getattr(event, "event_kind", "") or "") == "terminal"
        for event in list(getattr(ray, "events_2d", []) or [])
    )
    marker = projected_ray_terminal_marker(ray)
    if marker is not None and (polylines or has_terminal_event):
        marker_point = np.asarray((float(marker[0]), float(marker[1])), dtype=float)
        if np.all(np.isfinite(marker_point)):
            duplicate = False
            for polyline in polylines:
                if polyline.ndim != 2 or polyline.shape[0] < 1:
                    continue
                try:
                    distances = np.linalg.norm(polyline[:, :2] - marker_point.reshape(1, 2), axis=1)
                except Exception:
                    continue
                if distances.size and float(np.min(distances)) <= 1e-9:
                    duplicate = True
                    break
            if not duplicate:
                polylines.append(marker_point.reshape(1, 2))
    return polylines


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
        except Exception:
            continue
        for polyline in projected_ray_pick_polylines(ray):
            ray_pick_regions.append((ray_index, polyline))
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
        image_hits = int(sum(1 for path in ray_paths if ray_path_reaches_image_from_events(path)))
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


def sequential_focus_diagnostic(
    *,
    rays: object | None,
    final_surface_index: int,
    trace_summary: dict[str, object] | None = None,
    object_mode: str = "",
    field_type: str = "",
    object_distance: float | None = None,
) -> dict[str, object]:
    """Estimate whether a sequential trace is focused at the Image plane.

    The estimate extends each ray's last traced segment and finds the axial
    station that minimizes transverse RMS after removing the centroid.  It is a
    preview diagnostic, not an optimizer, but it catches prescriptions whose
    rays reach the Image row only because the preview uses a catch plane.
    """
    if rays is None:
        return {}
    summary = dict(trace_summary or {})
    family = str(summary.get("family", "Sequential preview") or "")
    if family != "Sequential preview" or str(summary.get("backend", "")) == "NsTraceLoop":
        return {}
    surfaces_seq = list(getattr(rays, "SURFACE", ()) or ())
    paths_seq = list(getattr(rays, "CC", ()) or ())
    image_points: list[np.ndarray] = []
    slopes: list[np.ndarray] = []
    for path, surface_ids in zip(paths_seq, surfaces_seq):
        try:
            surface_arr = np.asarray(surface_ids, dtype=int).ravel()
        except Exception:
            continue
        if not surface_arr.size or int(surface_arr[-1]) != int(final_surface_index):
            continue
        try:
            points = np.asarray(path, dtype=float)
        except Exception:
            continue
        if points.ndim != 2 or points.shape[0] < 2 or points.shape[1] < 3:
            continue
        final = points[-1, :3]
        if not np.all(np.isfinite(final)):
            continue
        previous = None
        for candidate in points[-2::-1, :3]:
            if not np.all(np.isfinite(candidate)):
                continue
            dz = float(final[2] - candidate[2])
            if abs(dz) > 1e-12:
                previous = candidate
                break
        if previous is None:
            continue
        dz = float(final[2] - previous[2])
        slope = (final[:2] - previous[:2]) / dz
        if not np.all(np.isfinite(slope)):
            continue
        image_points.append(final)
        slopes.append(np.asarray(slope, dtype=float))
    if len(image_points) < 3:
        return {}
    image_points_arr = np.asarray(image_points, dtype=float)
    slopes_arr = np.asarray(slopes, dtype=float)
    image_z = float(np.median(image_points_arr[:, 2]))
    transverse_at_image = image_points_arr[:, :2] + slopes_arr * (image_z - image_points_arr[:, 2])[:, None]
    centered_image = transverse_at_image - np.mean(transverse_at_image, axis=0)
    centered_slopes = slopes_arr - np.mean(slopes_arr, axis=0)
    denominator = float(np.sum(centered_slopes * centered_slopes))
    image_rms = float(np.sqrt(np.mean(np.sum(centered_image * centered_image, axis=1))))
    if denominator <= 1e-18 or not np.isfinite(image_rms):
        return {}
    shift = -float(np.sum(centered_image * centered_slopes)) / denominator
    best_focus_z = image_z + shift
    transverse_at_focus = transverse_at_image + slopes_arr * shift
    centered_focus = transverse_at_focus - np.mean(transverse_at_focus, axis=0)
    best_focus_rms = float(np.sqrt(np.mean(np.sum(centered_focus * centered_focus, axis=1))))
    if not all(np.isfinite(value) for value in (shift, best_focus_z, best_focus_rms)):
        return {}
    axial_scale = max(abs(image_z), 1.0)
    threshold = max(1.0, 0.02 * axial_scale)
    improved = image_rms > max(best_focus_rms * 1.25, best_focus_rms + 1e-6)
    warning = bool(abs(shift) > threshold and improved)
    if shift > 0:
        direction = "after"
    elif shift < 0:
        direction = "before"
    else:
        direction = "at"
    diagnostic = ""
    if warning:
        diagnostic = (
            f"Best focus is {abs(shift):.4g} mm {direction} the Image plane "
            f"(image RMS {image_rms:.4g} mm, best-focus RMS {best_focus_rms:.4g} mm)."
        )
        if str(object_mode).strip() == "Finite":
            detail = "Finite object mode uses the Object row thickness as object distance"
            try:
                object_distance_value = float(object_distance)
            except Exception:
                object_distance_value = np.nan
            if np.isfinite(object_distance_value):
                detail += f" ({object_distance_value:.4g} mm)"
            if str(field_type).strip() == "Angle":
                detail += "; for a usual collimated lens prescription, use Object mode = Infinity"
            diagnostic = f"{diagnostic} {detail}."
    return {
        "ray_count": len(image_points),
        "image_z": image_z,
        "best_focus_z": float(best_focus_z),
        "focus_shift": float(shift),
        "image_rms": image_rms,
        "best_focus_rms": best_focus_rms,
        "warning": warning,
        "diagnostic": diagnostic,
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
