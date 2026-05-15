"""Build a SceneBundle from KrakenOS system data and surface rows.

This module has no dependency on matplotlib, VTK, or tkinter.
It converts KrakenOS tracing results and surface descriptions into
the scene geometry dataclasses defined in ``scene_geometry``.
"""

from __future__ import annotations

from typing import Any, Callable

import numpy as np

from .scene_geometry import (
    BoundsRect,
    LabelSpec,
    PickRegion,
    PlaneMarker,
    RayBranch3D,
    RayHit3D,
    RayPath3D,
    SceneBundle,
    SceneSource3D,
    StyleHint,
    SurfaceCurve3D,
)
from .scene_row_mapping import build_scene_row_mapping


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_scene_bundle(
    *,
    rows: list,
    system: Any | None,
    rays: Any | None,
    display_orientation: str = "YZ",
    show_clipped_rays: bool = True,
    field_count: int = 1,
    ray_count_per_field: int = 5,
    field_colors: list[str] | None = None,
    folded_geometry: Any | None = None,
    row_polylines_fn: Callable | None = None,
    surface_meshes_fn: Callable | None = None,
    project_fn: Callable | None = None,
    reference_plane_overrides: dict | None = None,
    folded_ray_display_paths: list[np.ndarray] | None = None,
    trace_mode_requested: str = "Auto",
    trace_mode_active: str = "Sequential",
    trace_mode_note: str = "",
    target_surface: int | None = None,
    detector_surface_indices: set[int] | None = None,
    sources: list[SceneSource3D] | None = None,
    source_row_order: str = "after_object",
) -> SceneBundle:
    """Construct a complete :class:`SceneBundle` from tracing data.

    Parameters
    ----------
    rows : list[SurfaceRow]
        The surface table rows.
    system : KrakenOS system object (may be *None* for fallback).
    rays : KrakenOS raykeeper (may be *None*).
    display_orientation : ``"YZ"``, ``"XZ"``, or ``"XY"``.
    folded_geometry :
        Pre-computed folded geometry tuple from the editor, or *None*
        for sequential layouts.  When provided the tuple is
        ``(point, direction, max_half, extent_points, elements)``.
    row_polylines_fn :
        Callback ``(system, row_index, z_pos) -> list[np.ndarray]``
        used to extract 2-D polylines for sequential surfaces.  This
        bridges the KrakenOS mesh API without importing it here.
    surface_meshes_fn :
        Optional callback ``(system) -> list[SurfaceMesh3D]`` used by 3-D
        renderers.  It is intentionally callback-based so this builder stays
        independent of PyVista/VTK.
    project_fn :
        Callback ``(z_array, y_array) -> (x_display, y_display)``.
    reference_plane_overrides :
        Mapping ``{row_index: (center, along)}`` for folded plane display.
    folded_ray_display_paths :
        Pre-computed folded ray display override paths (list of Nx2 arrays).
    """
    scene_sources = list(sources or [])
    scene_row_mapping = build_scene_row_mapping(
        rows,
        scene_sources,
        include_sources=True,
        source_row_order=source_row_order,
    )
    if not rows:
        return SceneBundle(
            sources=scene_sources,
            scene_row_mapping=scene_row_mapping,
            display_orientation=display_orientation,
        )

    max_half = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    has_off_axis = _has_off_axis_geometry(rows)
    colors = field_colors or _default_field_colors(field_count)
    detector_surface_indices = _normalized_detector_surface_indices(rows, detector_surface_indices)

    # --- surfaces ---
    extent_points: list[np.ndarray] = []
    elements = None
    if folded_geometry is not None:
        _point, _direction, max_half, extent_points_raw, elements = folded_geometry
        extent_points = list(extent_points_raw)
        surface_curves = _build_folded_surface_curves(rows, elements)
    else:
        surface_curves = _build_sequential_surface_curves(
            rows, system, row_polylines_fn,
        )
    surface_curves.extend(
        _build_reference_plane_curves(
            rows,
            project_fn=project_fn,
            overrides=reference_plane_overrides or {},
            detector_surface_indices=detector_surface_indices,
        )
    )
    surface_curves.extend(
        _build_display_overlay_curves(
            rows,
            project_fn=project_fn,
        )
    )
    source_curves, source_labels = _build_source_markers(
        scene_sources,
        display_orientation=display_orientation,
        project_fn=project_fn,
    )
    surface_curves.extend(source_curves)

    # --- rays ---
    ray_paths = _build_ray_paths(
        rows,
        rays,
        field_count,
        ray_count_per_field,
        colors,
        target_surface=target_surface,
        detector_surface_indices=detector_surface_indices,
    )
    if folded_ray_display_paths is not None and elements:
        _apply_folded_reach_flags(ray_paths, folded_ray_display_paths, elements, detector_surface_indices)

    # --- 3-D surface/body meshes ---
    surface_meshes = []
    if surface_meshes_fn is not None and system is not None:
        try:
            surface_meshes = list(surface_meshes_fn(system) or [])
        except Exception:
            surface_meshes = []

    # --- labels ---
    labels = _build_reference_plane_labels(
        rows,
        project_fn=project_fn,
        overrides=reference_plane_overrides or {},
        detector_surface_indices=detector_surface_indices,
    )
    labels.extend(source_labels)
    labels.extend(_build_key_optic_labels(rows, surface_curves))

    # --- pick regions ---
    pick_regions = _build_pick_regions(rows, surface_curves)

    # --- bounds ---
    all_points = list(extent_points)
    for curve in surface_curves:
        pts = np.asarray(curve.points_world, dtype=float)
        if pts.ndim == 2 and pts.shape[0] >= 2:
            all_points.append(pts)
    bounds = BoundsRect.from_points(all_points)

    return SceneBundle(
        sources=scene_sources,
        scene_row_mapping=scene_row_mapping,
        surface_curves=surface_curves,
        surface_meshes=surface_meshes,
        ray_paths=ray_paths,
        planes=[],
        labels=labels,
        pick_regions=pick_regions,
        bounds=bounds,
        has_off_axis=has_off_axis,
        max_half=max_half,
        display_orientation=display_orientation,
        extra={
            "elements": elements,
            "folded_ray_display_paths": folded_ray_display_paths,
            "trace_mode_requested": trace_mode_requested,
            "trace_mode_active": trace_mode_active,
            "trace_mode_note": trace_mode_note,
            "sources": scene_sources,
            "scene_row_mapping": scene_row_mapping,
            "scene_row_records": scene_row_mapping.to_jsonable()["records"],
            "trace_surface_to_scene_row": scene_row_mapping.trace_surface_to_scene,
            "scene_row_to_trace_surface": scene_row_mapping.scene_to_trace_surface,
            "detector_surface_indices": sorted(int(index) for index in detector_surface_indices),
        },
    )


# ---------------------------------------------------------------------------
# Surface curve builders
# ---------------------------------------------------------------------------

def _build_sequential_surface_curves(
    rows: list,
    system: Any | None,
    row_polylines_fn: Callable | None,
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    curve_map: dict[int, np.ndarray] = {}
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        if row.surface in {"Object", "Image"}:
            z_pos += float(row.thickness)
            continue
        color, linewidth, alpha = surface_style_for_row(row)
        style = StyleHint(color=color, linewidth=linewidth, alpha=alpha)
        polylines: list[np.ndarray] = []
        if row_polylines_fn is not None and system is not None:
            polylines = row_polylines_fn(system, row_index, z_pos)
        for polyline in polylines:
            points = np.asarray(polyline, dtype=float)
            if points.shape[0] < 2:
                continue
            kind = row.surface.lower().replace(" ", "_")
            advanced = getattr(row, "advanced", {}) or {}
            if isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None"):
                kind = "stl_solid"
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind=kind,
                points_world=points,
                style=style,
            ))
            if row_index not in curve_map:
                curve_map[row_index] = points
        z_pos += float(row.thickness)
    curves.extend(_build_lens_edge_curves(rows, curve_map))
    return curves


def _build_folded_surface_curves(
    rows: list,
    elements: list,
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    curve_map: dict[int, np.ndarray] = {}
    for idx, elem in enumerate(elements):
        # Elements may be 4-tuples (legacy) or 5-tuples (with mirror_tangent).
        surface_type, center, row, branch_dir = elem[0], elem[1], elem[2], elem[3]
        mirror_tangent = elem[4] if len(elem) > 4 else None
        row_index = idx + 1
        if surface_type in {"Mirror", "Object Target", "Diffuse Object"}:
            half = max(row.diameter / 2.0, 0.5)
            if mirror_tangent is not None:
                tangent = np.asarray(mirror_tangent, dtype=float).copy()
                tn = np.linalg.norm(tangent)
                if tn > 1e-12:
                    tangent /= tn
                else:
                    theta = np.deg2rad(-float(row.tilt_x))
                    tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
            else:
                theta = np.deg2rad(-float(row.tilt_x))
                tangent = np.array([np.cos(theta), np.sin(theta)], dtype=float)
                tangent /= max(np.linalg.norm(tangent), 1e-12)
            points = np.vstack((center - tangent * half, center + tangent * half))
            if surface_type == "Object Target":
                kind = "object_target"
                style = StyleHint(color="#202020", linewidth=2.2, alpha=0.95)
            elif surface_type == "Diffuse Object":
                kind = "diffuse_object"
                style = StyleHint(color="#16a34a", linewidth=2.2, alpha=0.95)
            else:
                kind = "mirror"
                style = StyleHint(color="#202020", linewidth=2.2, alpha=0.95)
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind=kind,
                points_world=points,
                style=style,
            ))
        elif surface_type == "Standard":
            axis = branch_dir / max(np.linalg.norm(branch_dir), 1e-12)
            tangent = np.array([-axis[1], axis[0]], dtype=float)
            half = max(row.diameter / 2.0, 0.5)
            yy = np.linspace(-half, half, 128)
            if abs(float(row.rc)) <= half + 1e-9:
                xx = np.zeros_like(yy)
            else:
                rr = abs(float(row.rc))
                sign = 1.0 if float(row.rc) >= 0.0 else -1.0
                xx = float(row.rc) - sign * np.sqrt(np.maximum(rr * rr - yy * yy, 0.0))
            points = center[None, :] + np.outer(xx, axis) + np.outer(yy, tangent)
            curve_map[row_index] = np.asarray(points, dtype=float)
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind="standard",
                points_world=points,
                style=StyleHint(color="#2563eb", linewidth=1.8, alpha=0.95),
            ))
        elif surface_type == "Aperture":
            tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
            tangent /= max(np.linalg.norm(tangent), 1e-12)
            half = max(row.diameter / 2.0, 0.5)
            points = np.vstack((center - tangent * half, center + tangent * half))
            curves.append(SurfaceCurve3D(
                row_index=row_index,
                kind="aperture",
                points_world=points,
                style=StyleHint(color="#b45309", linewidth=1.6, alpha=0.95),
            ))
    curves.extend(_build_lens_edge_curves(rows, curve_map))
    return curves


def _build_reference_plane_curves(
    rows: list,
    *,
    project_fn: Callable | None,
    overrides: dict,
    detector_surface_indices: set[int],
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        if display_settings.get("show_reference_plane") is False:
            z_pos += float(row.thickness)
            continue
        if row.surface == "Image" and int(row_index) not in detector_surface_indices:
            z_pos += float(row.thickness)
            continue
        if row.surface in {"Object", "Image"}:
            points = _reference_plane_display_points(row_index, row, z_pos, overrides, project_fn)
            if points is not None and points.shape[0] >= 2:
                curves.append(SurfaceCurve3D(
                    row_index=row_index,
                    kind=row.surface.lower(),
                    points_world=points,
                    style=StyleHint(color="#202020", linewidth=1.2, alpha=0.9),
                ))
        z_pos += float(row.thickness)
    return curves


def _build_display_overlay_curves(
    rows: list,
    *,
    project_fn: Callable | None,
) -> list[SurfaceCurve3D]:
    curves: list[SurfaceCurve3D] = []
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        raw_polylines = display_settings.get("overlay_polylines", display_settings.get("extra_polylines", ()))
        if not isinstance(raw_polylines, (list, tuple)):
            continue
        for item in raw_polylines:
            if isinstance(item, dict):
                raw_points = item.get("points")
                color = str(item.get("color", "#b45309") or "#b45309")
                try:
                    linewidth = float(item.get("linewidth", 1.6))
                except Exception:
                    linewidth = 1.6
                try:
                    alpha = float(item.get("alpha", 0.95))
                except Exception:
                    alpha = 0.95
            else:
                raw_points = item
                color = "#b45309"
                linewidth = 1.6
                alpha = 0.95
            try:
                points_zy = np.asarray(raw_points, dtype=float)
            except Exception:
                continue
            if points_zy.ndim != 2 or points_zy.shape[0] < 2 or points_zy.shape[1] < 2:
                continue
            z_values = points_zy[:, 0]
            y_values = points_zy[:, 1]
            if project_fn is not None:
                try:
                    x_values, display_y_values = project_fn(z_values, y_values)
                    points = np.column_stack((np.asarray(x_values, dtype=float), np.asarray(display_y_values, dtype=float)))
                except Exception:
                    points = points_zy[:, :2]
            else:
                points = points_zy[:, :2]
            if points.ndim != 2 or points.shape[0] < 2:
                continue
            curves.append(
                SurfaceCurve3D(
                    row_index=row_index,
                    kind="display_overlay",
                    points_world=points,
                    style=StyleHint(color=color, linewidth=linewidth, alpha=alpha),
                )
            )
    return curves


def _build_lens_edge_curves(
    rows: list,
    curve_map: dict[int, np.ndarray],
    color: str = "#6b7280",
    linewidth: float = 1.2,
    alpha: float = 0.9,
) -> list[SurfaceCurve3D]:
    groups = _build_row_surface_groups(rows, curve_map)
    edge_curves: list[SurfaceCurve3D] = []
    for group in groups:
        first, last = group[0], group[-1]
        curve_a = np.asarray(curve_map.get(first), dtype=float)
        curve_b = np.asarray(curve_map.get(last), dtype=float)
        if curve_a.shape[0] < 2 or curve_b.shape[0] < 2:
            continue
        base_row = rows[first] if 0 <= first < len(rows) else None
        if base_row is not None:
            edge_color, edge_width, edge_alpha = surface_style_for_row(base_row)
            style = StyleHint(
                color=edge_color,
                linewidth=max(linewidth, edge_width),
                alpha=max(alpha, edge_alpha),
            )
        else:
            style = StyleHint(color=color, linewidth=linewidth, alpha=alpha)
        aperture_axis = _curve_group_aperture_axis(curve_a, curve_b)
        a0, a1 = _curve_edge_points(curve_a, aperture_axis)
        b0, b1 = _curve_edge_points(curve_b, aperture_axis)
        if a0 is None or b0 is None:
            continue
        for start, end in ((a0, b0), (a1, b1)):
            edge_curves.append(SurfaceCurve3D(
                row_index=first,
                kind="lens_edge",
                points_world=np.vstack((start, end)),
                style=style,
            ))
    return edge_curves


# ---------------------------------------------------------------------------
# Ray path builder
# ---------------------------------------------------------------------------

def _build_ray_paths(
    rows: list,
    rays: Any | None,
    field_count: int,
    ray_count_per_field: int,
    colors: list[str],
    *,
    target_surface: int | None = None,
    detector_surface_indices: set[int] | None = None,
) -> list[RayPath3D]:
    if rays is None:
        return []
    final_surface_index = max(0, len(rows) - 1)
    detector_surface_indices = _normalized_detector_surface_indices(rows, detector_surface_indices)
    target_surface_index = final_surface_index if target_surface is None else int(target_surface)
    paths: list[RayPath3D] = []
    ray_waves = getattr(rays, "RayWave", ())
    wavelengths = list(ray_waves) if ray_waves is not None else []
    for ray_index, ray in enumerate(getattr(rays, "CC", ())):
        points_world = np.asarray(ray, dtype=float)
        if points_world.shape[0] < 2:
            continue
        hits = _build_ray_hit_records(rows, rays, ray_index)
        if hits:
            surface_ids = np.asarray(
                [hit.surface_id for hit in hits if hit.surface_id is not None],
                dtype=int,
            )
        else:
            surface_ids = _raykeeper_array(rays, "SURFACE", ray_index, dtype=int)
        points_world, hits, surface_ids = _strip_nonterminal_image_hits(
            rows,
            points_world,
            hits,
            surface_ids,
            detector_surface_indices=detector_surface_indices,
        )
        last_surface = int(surface_ids[-1]) if surface_ids.size else None
        terminal_continuation = _has_terminal_continuation(points_world, surface_ids)
        if surface_ids.size and points_world.shape[0] > surface_ids.size + 1:
            # Kraken raykeeper may include an extrapolated continuation point
            # after the last surface hit. Preserve that point for non-absorbed
            # non-sequential rays so reflected/refracted rays do not appear to
            # stop inside prisms or optical solids. Image and absorber hits are
            # true terminal interactions and should remain clipped to the hit.
            last_surface_type = ""
            if last_surface is not None and 0 <= last_surface < len(rows):
                last_surface_type = str(getattr(rows[last_surface], "surface", "") or "")
            last_interaction = str(getattr(hits[-1], "interaction", "") or "").strip().lower() if hits else ""
            if last_surface_type == "Image" or last_interaction in {"absorb", "absorption"}:
                points_world = points_world[: surface_ids.size + 1]
                terminal_continuation = False
        source_ray_index = _raykeeper_metadata_scalar(rays, "SOURCE_RAY", ray_index)
        if source_ray_index is None:
            source_ray_index = ray_index
        source_position_arr = _raykeeper_xyz_array(rays, "SOURCE_XYZ", ray_index)
        source_direction_arr = _raykeeper_xyz_array(rays, "SOURCE_LMN", ray_index)
        source_position = source_position_arr[0] if source_position_arr.shape[0] else np.full(3, np.nan, dtype=float)
        source_direction = source_direction_arr[0] if source_direction_arr.shape[0] else np.full(3, np.nan, dtype=float)
        source_power = _raykeeper_metadata_scalar(rays, "SOURCE_POWER", ray_index)
        source_weight = _raykeeper_metadata_scalar(rays, "SOURCE_WEIGHT", ray_index)
        source_id = _raykeeper_metadata_text(rays, "SOURCE_ID", ray_index)
        source_name = _raykeeper_metadata_text(rays, "SOURCE_NAME", ray_index)
        source_role = _raykeeper_metadata_text(rays, "SOURCE_ROLE", ray_index)
        source_model = _raykeeper_metadata_text(rays, "SOURCE_MODEL", ray_index)
        field_index = min(int(source_ray_index) // max(ray_count_per_field, 1), field_count - 1)
        reaches_image = last_surface in detector_surface_indices
        if reaches_image:
            termination_reason = "image"
        elif last_surface is None:
            termination_reason = "no_hit"
        elif terminal_continuation:
            termination_reason = "missed_image" if detector_surface_indices else "no_next_intersection"
        else:
            termination_reason = f"stopped_at_surface_{last_surface}"
        branch_id = _raykeeper_metadata_scalar(rays, "BRANCH_ID", ray_index)
        parent_branch_id = _raykeeper_metadata_scalar(rays, "PARENT_BRANCH_ID", ray_index)
        branch_power = _raykeeper_metadata_scalar(rays, "BRANCH_POWER", ray_index)
        branch_phase = _raykeeper_metadata_scalar(rays, "BRANCH_PHASE", ray_index)
        branch_jones_p = _raykeeper_metadata_complex(rays, "BRANCH_JONES_P", ray_index, complex(1.0, 0.0))
        branch_jones_s = _raykeeper_metadata_complex(rays, "BRANCH_JONES_S", ray_index, complex(0.0, 0.0))
        branch_polarization_arr = _raykeeper_complex_xyz_array(rays, "BRANCH_POLARIZATION_XYZ", ray_index)
        branch_polarization = (
            branch_polarization_arr[0]
            if branch_polarization_arr.shape[0]
            else np.asarray((1.0 + 0.0j, 0.0 + 0.0j, 0.0 + 0.0j), dtype=np.complex128)
        )
        branch_label = _raykeeper_metadata_text(rays, "BRANCH_LABEL", ray_index)
        branch_path = _raykeeper_metadata_text(rays, "BRANCH_PATH", ray_index)
        if branch_id is not None:
            for hit in hits:
                hit.branch_id = int(branch_id)
            branches = [
                RayBranch3D(
                    branch_id=int(branch_id),
                    parent_branch_id=None if parent_branch_id is None or int(parent_branch_id) < 0 else int(parent_branch_id),
                    start_step=0,
                    end_step=max(0, len(hits) - 1),
                    surface_ids=surface_ids,
                    termination_reason=termination_reason,
                )
            ] if hits else []
        else:
            branches = _build_ray_branches(hits, termination_reason)
            branch_id = branches[-1].branch_id if branches else 0
        paths.append(RayPath3D(
            ray_index=ray_index,
            source_ray_index=int(source_ray_index) if source_ray_index is not None else None,
            source_id=source_id or "",
            source_name=source_name or "",
            source_role=source_role or "",
            source_model=source_model or "",
            source_position=np.asarray(source_position, dtype=float),
            source_direction=np.asarray(source_direction, dtype=float),
            source_power=float(source_power) if source_power is not None else None,
            source_weight=float(source_weight) if source_weight is not None else None,
            field_index=field_index,
            wavelength=float(wavelengths[ray_index]) if ray_index < len(wavelengths) else None,
            color=colors[field_index % len(colors)],
            points_world=points_world,
            surface_ids=surface_ids,
            reaches_image=reaches_image,
            branch_id=int(branch_id),
            branch_power=float(branch_power) if branch_power is not None else None,
            branch_phase_deg=float(branch_phase) if branch_phase is not None else None,
            branch_jones_p=branch_jones_p,
            branch_jones_s=branch_jones_s,
            branch_polarization_xyz=np.asarray(branch_polarization, dtype=np.complex128),
            branch_label=branch_label or "",
            branch_path=branch_path or branch_label or "",
            target_surface=target_surface_index,
            termination_reason=termination_reason,
            hits=hits,
            branches=branches,
        ))
    return paths


def _has_terminal_continuation(points_world: np.ndarray, surface_ids: np.ndarray) -> bool:
    return bool(
        surface_ids.size
        and points_world.ndim == 2
        and points_world.shape[0] > int(surface_ids.size) + 1
    )


def _normalized_detector_surface_indices(rows: list, detector_surface_indices: set[int] | None) -> set[int]:
    if detector_surface_indices is None:
        return {
            int(index)
            for index, row in enumerate(rows)
            if str(getattr(row, "surface", "") or "") == "Image"
        }
    normalized: set[int] = set()
    for raw_index in detector_surface_indices:
        try:
            index = int(raw_index)
        except Exception:
            continue
        if 0 <= index < len(rows):
            normalized.add(index)
    return normalized


def _strip_nonterminal_image_hits(
    rows: list,
    points_world: np.ndarray,
    hits: list[RayHit3D],
    surface_ids: np.ndarray,
    *,
    detector_surface_indices: set[int],
) -> tuple[np.ndarray, list[RayHit3D], np.ndarray]:
    """Remove intermediate Image-plane hits from display ray paths.

    In non-sequential layouts the final Image row may be either an explicit
    detector or only the sequential prescription sentinel.  Preserve only
    detector Image hits as terminal events.  When a non-detector Image hit is
    terminal, keep its point as continuation geometry but remove the hit event
    so the scene does not report a physical detector that the user did not
    create.
    """
    if not rows or points_world.ndim != 2 or not hits or surface_ids.size == 0:
        return points_world, hits, surface_ids
    final_index = len(rows) - 1
    if final_index < 0 or str(getattr(rows[final_index], "surface", "") or "") != "Image":
        return points_world, hits, surface_ids
    last_image_step = None
    for step, surface_id in enumerate(surface_ids):
        if int(surface_id) == final_index:
            last_image_step = step
    if last_image_step is None:
        return points_world, hits, surface_ids
    final_image_is_detector = int(final_index) in detector_surface_indices
    keep_steps = [
        step
        for step, surface_id in enumerate(surface_ids)
        if int(surface_id) != final_index
        or (final_image_is_detector and int(step) == int(last_image_step))
    ]
    if len(keep_steps) == len(surface_ids):
        return points_world, hits, surface_ids
    point_indices = [0]
    point_indices.extend(step + 1 for step in keep_steps if step + 1 < points_world.shape[0])
    if not final_image_is_detector and int(last_image_step) == int(len(surface_ids) - 1):
        terminal_point_index = int(last_image_step) + 1
        if terminal_point_index < points_world.shape[0] and terminal_point_index not in point_indices:
            point_indices.append(terminal_point_index)
    filtered_points = np.asarray(points_world[point_indices], dtype=float)
    filtered_hits = [hits[step] for step in keep_steps if step < len(hits)]
    for new_step, hit in enumerate(filtered_hits):
        hit.step = int(new_step)
    filtered_surface_ids = np.asarray([int(surface_ids[step]) for step in keep_steps], dtype=int)
    _assign_hit_branch_ids(filtered_hits)
    return filtered_points, filtered_hits, filtered_surface_ids


def _raykeeper_array(rays: Any, seq_name: str, ray_index: int, *, dtype=None) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty(0, dtype=(dtype or float))
    try:
        return np.asarray(seq[ray_index], dtype=dtype).ravel()
    except Exception:
        try:
            return np.asarray(seq[ray_index]).ravel()
        except Exception:
            return np.empty(0, dtype=(dtype or float))


def _raykeeper_xyz_array(rays: Any, seq_name: str, ray_index: int) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty((0, 3), dtype=float)
    try:
        arr = np.asarray(seq[ray_index], dtype=float)
    except Exception:
        return np.empty((0, 3), dtype=float)
    if arr.ndim == 1 and arr.size == 3:
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return np.empty((0, 3), dtype=float)
    return np.asarray(arr[:, :3], dtype=float)


def _raykeeper_complex_xyz_array(rays: Any, seq_name: str, ray_index: int) -> np.ndarray:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return np.empty((0, 3), dtype=np.complex128)
    try:
        arr = np.asarray(seq[ray_index], dtype=np.complex128)
    except Exception:
        return np.empty((0, 3), dtype=np.complex128)
    if arr.ndim == 1 and arr.size == 3:
        arr = arr.reshape(1, 3)
    if arr.ndim != 2 or arr.shape[1] < 3:
        return np.empty((0, 3), dtype=np.complex128)
    real_finite = np.isfinite(arr[:, :3].real)
    imag_finite = np.isfinite(arr[:, :3].imag)
    if not np.all(real_finite & imag_finite):
        return np.empty((0, 3), dtype=np.complex128)
    return np.asarray(arr[:, :3], dtype=np.complex128)


def _raykeeper_scalar(arr: np.ndarray, index: int) -> float | None:
    if index >= arr.size:
        return None
    try:
        value = float(arr[index])
    except Exception:
        return None
    if not np.isfinite(value):
        return None
    return value


def _raykeeper_vector(arr: np.ndarray, index: int) -> np.ndarray:
    if index >= arr.shape[0]:
        return np.full(3, np.nan, dtype=float)
    value = np.asarray(arr[index], dtype=float).ravel()
    if value.size < 3:
        return np.full(3, np.nan, dtype=float)
    return value[:3]


def _raykeeper_metadata_scalar(rays: Any, seq_name: str, ray_index: int) -> int | float | None:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return None
    try:
        arr = np.asarray(seq[ray_index]).ravel()
    except Exception:
        return None
    if arr.size == 0:
        return None
    try:
        value = float(arr[0])
    except Exception:
        return None
    if not np.isfinite(value):
        return None
    if abs(value - round(value)) < 1e-9:
        return int(round(value))
    return value


def _raykeeper_metadata_complex(rays: Any, seq_name: str, ray_index: int, default: complex) -> complex:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return default
    try:
        arr = np.asarray(seq[ray_index]).ravel()
    except Exception:
        return default
    if arr.size == 0:
        return default
    try:
        value = complex(arr[0])
    except Exception:
        return default
    if not np.isfinite(value.real) or not np.isfinite(value.imag):
        return default
    return value


def _raykeeper_metadata_text(rays: Any, seq_name: str, ray_index: int) -> str:
    seq = getattr(rays, seq_name, ())
    if seq is None or ray_index >= len(seq):
        return ""
    try:
        arr = np.asarray(seq[ray_index], dtype=object).ravel()
    except Exception:
        return ""
    if arr.size == 0:
        return ""
    return str(arr[0])


def _raykeeper_text(arr: np.ndarray, index: int) -> str:
    if index >= arr.size:
        return ""
    try:
        return str(arr[index])
    except Exception:
        return ""


def _classify_ray_interaction(rows: list, surface_id: int | None, n0: float | None, n1: float | None) -> str:
    if surface_id is None or not (0 <= surface_id < len(rows)):
        return "unknown"
    row = rows[surface_id]
    surface_type = str(getattr(row, "surface", "") or "").strip().lower()
    glass = str(getattr(row, "glass", "") or "").strip().upper()
    if surface_type == "diffuse object":
        return "diffuse_scatter"
    if surface_type == "mirror" or glass == "MIRROR":
        return "reflection"
    if surface_type == "beam splitter":
        return "beam_splitter"
    if surface_type == "aperture":
        return "aperture"
    if surface_type == "object":
        return "launch"
    if surface_type == "image":
        return "image"
    if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
        return "refraction"
    return "transmission"


def _interaction_event_label(
    rows: list,
    surface_id: int | None,
    interaction_type: str,
    n0: float | None,
    n1: float | None,
) -> str:
    label = str(interaction_type or "").strip().lower()
    if surface_id is not None and 0 <= surface_id < len(rows):
        surface_type = str(getattr(rows[surface_id], "surface", "") or "").strip().lower()
        if surface_type == "object":
            return "launch"
        if surface_type == "image":
            return "image"
        if surface_type == "aperture":
            return "aperture"
    if label in {"reflect_tir", "reflect_mirror"}:
        return label
    if label in {"reflection", "reflect"}:
        return "reflection"
    if label in {"scatter", "diffuse_scatter"}:
        return "scatter"
    if label in {"absorb", "absorption"}:
        return "absorb"
    if label in {"refract", "refraction"}:
        return "refraction"
    if label == "transmit":
        if n0 is not None and n1 is not None and abs(float(n0) - float(n1)) > 1e-9:
            return "refraction"
        return "transmission"
    if label:
        return label
    return _classify_ray_interaction(rows, surface_id, n0, n1)


def _build_ray_hit_records(rows: list, rays: Any, ray_index: int) -> list[RayHit3D]:
    surface_arr = _raykeeper_array(rays, "SURFACE", ray_index, dtype=int)
    name_arr = _raykeeper_array(rays, "NAME", ray_index, dtype=object)
    glass_arr = _raykeeper_array(rays, "GLASS", ray_index, dtype=object)
    xyz_arr = _raykeeper_xyz_array(rays, "XYZ", ray_index)
    lmn_arr = _raykeeper_xyz_array(rays, "LMN", ray_index)
    r_lmn_arr = _raykeeper_xyz_array(rays, "R_LMN", ray_index)
    s_lmn_arr = _raykeeper_xyz_array(rays, "S_LMN", ray_index)
    n0_arr = _raykeeper_array(rays, "N0", ray_index, dtype=float)
    n1_arr = _raykeeper_array(rays, "N1", ray_index, dtype=float)
    dist_arr = _raykeeper_array(rays, "DISTANCE", ray_index, dtype=float)
    op_arr = _raykeeper_array(rays, "OP", ray_index, dtype=float)
    rp_arr = _raykeeper_array(rays, "RP", ray_index, dtype=float)
    rs_arr = _raykeeper_array(rays, "RS", ray_index, dtype=float)
    tp_arr = _raykeeper_array(rays, "TP", ray_index, dtype=float)
    ts_arr = _raykeeper_array(rays, "TS", ray_index, dtype=float)
    ttbe_arr = _raykeeper_array(rays, "TTBE", ray_index, dtype=float)
    interaction_type_arr = _raykeeper_array(rays, "INTERACTION_TYPE", ray_index, dtype=object)
    interaction_model_arr = _raykeeper_array(rays, "INTERACTION_MODEL", ray_index, dtype=object)
    interaction_target_arr = _raykeeper_array(rays, "INTERACTION_TARGET_SURFACE", ray_index, dtype=float)
    interaction_in_power_arr = _raykeeper_array(rays, "INTERACTION_IN_POWER", ray_index, dtype=float)
    interaction_coeff_arr = _raykeeper_array(rays, "INTERACTION_COEFF", ray_index, dtype=float)
    interaction_out_power_arr = _raykeeper_array(rays, "INTERACTION_OUT_POWER", ray_index, dtype=float)
    interaction_loss_power_arr = _raykeeper_array(rays, "INTERACTION_LOSS_POWER", ray_index, dtype=float)
    interaction_bulk_arr = _raykeeper_array(rays, "INTERACTION_BULK", ray_index, dtype=float)
    mesh_cell_id_arr = _raykeeper_array(rays, "MESH_CELL_ID", ray_index, dtype=float)
    mesh_original_cell_id_arr = _raykeeper_array(rays, "MESH_ORIGINAL_CELL_ID", ray_index, dtype=float)
    mesh_face_id_arr = _raykeeper_array(rays, "MESH_FACE_ID", ray_index, dtype=object)
    mesh_face_match_method_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_METHOD", ray_index, dtype=object)
    mesh_face_match_score_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_SCORE", ray_index, dtype=float)
    mesh_face_match_warning_arr = _raykeeper_array(rays, "MESH_FACE_MATCH_WARNING", ray_index, dtype=object)

    core_count = int(max(
        name_arr.size,
        glass_arr.size,
        xyz_arr.shape[0],
        lmn_arr.shape[0],
        r_lmn_arr.shape[0],
        s_lmn_arr.shape[0],
        n0_arr.size,
        n1_arr.size,
        dist_arr.size,
        op_arr.size,
    ))
    hit_count = int(surface_arr.size) if surface_arr.size else core_count
    hits: list[RayHit3D] = []
    for step in range(hit_count):
        surface_id = int(surface_arr[step]) if step < surface_arr.size else None
        n0 = _raykeeper_scalar(n0_arr, step)
        n1 = _raykeeper_scalar(n1_arr, step)
        point_step = step + 1 if surface_arr.size and xyz_arr.shape[0] == surface_arr.size + 1 else step
        interaction_type = _raykeeper_text(interaction_type_arr, step)
        hits.append(RayHit3D(
            step=step,
            surface_id=surface_id,
            name=str(name_arr[step]) if step < name_arr.size else "",
            material=str(glass_arr[step]) if step < glass_arr.size else "",
            point_world=_raykeeper_vector(xyz_arr, point_step),
            incoming_direction=_raykeeper_vector(lmn_arr, step),
            outgoing_direction=_raykeeper_vector(r_lmn_arr, step),
            surface_normal=_raykeeper_vector(s_lmn_arr, step),
            n0=n0,
            n1=n1,
            distance=_raykeeper_scalar(dist_arr, step),
            optical_path=_raykeeper_scalar(op_arr, step),
            rp=_raykeeper_scalar(rp_arr, step),
            rs=_raykeeper_scalar(rs_arr, step),
            tp=_raykeeper_scalar(tp_arr, step),
            ts=_raykeeper_scalar(ts_arr, step),
            ttbe=_raykeeper_scalar(ttbe_arr, step),
            interaction=_interaction_event_label(rows, surface_id, interaction_type, n0, n1),
            interaction_model=_raykeeper_text(interaction_model_arr, step),
            interaction_target_surface=_raykeeper_scalar(interaction_target_arr, step),
            interaction_in_power=_raykeeper_scalar(interaction_in_power_arr, step),
            interaction_coeff=_raykeeper_scalar(interaction_coeff_arr, step),
            interaction_out_power=_raykeeper_scalar(interaction_out_power_arr, step),
            interaction_loss_power=_raykeeper_scalar(interaction_loss_power_arr, step),
            interaction_bulk=_raykeeper_scalar(interaction_bulk_arr, step),
            mesh_cell_id=_raykeeper_scalar(mesh_cell_id_arr, step),
            mesh_original_cell_id=_raykeeper_scalar(mesh_original_cell_id_arr, step),
            mesh_face_id=_raykeeper_text(mesh_face_id_arr, step),
            mesh_face_match_method=_raykeeper_text(mesh_face_match_method_arr, step),
            mesh_face_match_score=_raykeeper_scalar(mesh_face_match_score_arr, step),
            mesh_face_match_warning=_raykeeper_text(mesh_face_match_warning_arr, step),
        ))
    _assign_hit_branch_ids(hits)
    return hits


def _interaction_is_reflective(value: object) -> bool:
    text = str(value or "").strip().lower()
    return text in {"reflection", "reflect", "reflect_tir", "reflect_mirror"} or text.startswith("split_reflect")


def _assign_hit_branch_ids(hits: list[RayHit3D]) -> None:
    branch_id = 0
    previous_surface: int | None = None
    for index, hit in enumerate(hits):
        if previous_surface is not None and hit.surface_id is not None and hit.surface_id <= previous_surface:
            branch_id += 1
        hit.branch_id = branch_id
        previous_surface = hit.surface_id
        if _interaction_is_reflective(hit.interaction) and index < len(hits) - 1:
            branch_id += 1
            previous_surface = None


def _build_ray_branches(hits: list[RayHit3D], termination_reason: str) -> list[RayBranch3D]:
    if not hits:
        return []
    grouped: list[tuple[int, list[RayHit3D]]] = []
    for hit in hits:
        if not grouped or grouped[-1][0] != hit.branch_id:
            grouped.append((hit.branch_id, []))
        grouped[-1][1].append(hit)
    branches: list[RayBranch3D] = []
    parent: int | None = None
    for index, (branch_id, branch_hits) in enumerate(grouped):
        end_step = int(branch_hits[-1].step)
        if index < len(grouped) - 1:
            reason = (
                "reflection"
                if _interaction_is_reflective(branch_hits[-1].interaction)
                else "nonsequential_transition"
            )
        else:
            reason = termination_reason
        surface_ids = np.asarray(
            [hit.surface_id for hit in branch_hits if hit.surface_id is not None],
            dtype=int,
        )
        branches.append(RayBranch3D(
            branch_id=int(branch_id),
            parent_branch_id=parent,
            start_step=int(branch_hits[0].step),
            end_step=end_step,
            surface_ids=surface_ids,
            termination_reason=reason,
        ))
        parent = int(branch_id)
    return branches


def _apply_folded_reach_flags(
    ray_paths: list[RayPath3D],
    folded_ray_display_paths: list[np.ndarray],
    elements: list,
    detector_surface_indices: set[int],
) -> None:
    image_element = None
    for element_index, element in reversed(list(enumerate(elements, start=1))):
        if element and element[0] == "Image" and int(element_index) in detector_surface_indices:
            image_element = element
            break
    if image_element is None:
        return
    _surface_type, center, row, branch_dir, *_rest = image_element
    center = np.asarray(center, dtype=float)
    branch_dir = np.asarray(branch_dir, dtype=float)
    branch_dir /= max(np.linalg.norm(branch_dir), 1e-12)
    tangent = np.array([-branch_dir[1], branch_dir[0]], dtype=float)
    half = max(float(getattr(row, "diameter", 1.0)) / 2.0, 0.5)
    for path in ray_paths:
        if path.ray_index >= len(folded_ray_display_paths):
            continue
        pts = np.asarray(folded_ray_display_paths[path.ray_index], dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            path.reaches_image = False
            path.termination_reason = "no_folded_display_path"
            continue
        delta = pts[-1] - center
        normal_error = abs(float(np.dot(delta, branch_dir)))
        along = abs(float(np.dot(delta, tangent)))
        path.reaches_image = normal_error <= 1e-5 and along <= half + 1e-6
        if path.reaches_image:
            path.termination_reason = "image"
        elif path.termination_reason in {"missed_image", "no_next_intersection"}:
            continue
        elif path.surface_ids.size:
            path.termination_reason = f"stopped_at_surface_{int(path.surface_ids[-1])}"
        else:
            path.termination_reason = "missed_folded_image"


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def _build_reference_plane_labels(
    rows: list,
    *,
    project_fn: Callable | None,
    overrides: dict,
    detector_surface_indices: set[int],
) -> list[LabelSpec]:
    labels: list[LabelSpec] = []
    z_pos = 0.0
    for row_index, row in enumerate(rows):
        display_settings = _row_display_settings(row)
        if display_settings.get("show_reference_label") is False:
            z_pos += row.thickness
            continue
        if row.surface == "Image" and int(row_index) not in detector_surface_indices:
            z_pos += row.thickness
            continue
        if row.surface in {"Object", "Image", "Aperture"}:
            label_text = row.name or row.surface
            points = _reference_plane_display_points(row_index, row, z_pos, overrides, project_fn)
            if points is None or points.shape[0] < 2:
                z_pos += row.thickness
                continue
            x_vals = points[:, 0].astype(float)
            y_vals = points[:, 1].astype(float)
            center_x = float(np.mean(x_vals))
            center_y = float(np.mean(y_vals))
            line_vec = np.array([float(x_vals[-1] - x_vals[0]), float(y_vals[-1] - y_vals[0])], dtype=float)
            norm = np.linalg.norm(line_vec)
            if norm <= 1e-12:
                normal = np.array([0.0, 1.0], dtype=float)
            else:
                tangent = line_vec / norm
                normal = np.array([-tangent[1], tangent[0]], dtype=float)
            offset = max(float(row.diameter) * 0.08, 1.2)
            text_x = center_x + normal[0] * offset
            text_y = center_y + normal[1] * offset
            text_ha = "center"
            if row.surface == "Object":
                text_x = center_x + offset
                text_y = float(np.max(y_vals)) + offset
                text_ha = "left"
            elif row.surface == "Image":
                text_x = center_x - offset
                text_y = float(np.max(y_vals)) + offset
                text_ha = "right"
            labels.append(LabelSpec(
                text=label_text,
                x=text_x,
                y=text_y,
                row_index=row_index,
                fontsize=9.0,
                color="#202020",
                ha=text_ha,
                va="bottom",
            ))
        z_pos += row.thickness
    return labels


def _row_display_settings(row: Any) -> dict:
    advanced = getattr(row, "advanced", {}) or {}
    if not isinstance(advanced, dict):
        return {}
    settings = advanced.get("Display2D", {})
    if isinstance(settings, dict):
        return settings
    return {}


def _build_key_optic_labels(rows: list, surface_curves: list[SurfaceCurve3D]) -> list[LabelSpec]:
    labels: list[LabelSpec] = []
    label_surfaces = {"Mirror", "Object Target", "Diffuse Object", "Beam Splitter"}
    labeled_rows: set[int] = set()
    all_points = [
        np.asarray(curve.points_world, dtype=float)
        for curve in surface_curves
        if np.asarray(curve.points_world).ndim == 2 and np.asarray(curve.points_world).shape[0] >= 2
    ]
    scene_span = 1.0
    if all_points:
        finite_points = np.vstack(all_points)
        finite = np.isfinite(finite_points[:, 0]) & np.isfinite(finite_points[:, 1])
        if np.any(finite):
            finite_points = finite_points[finite]
            span_x = float(np.max(finite_points[:, 0]) - np.min(finite_points[:, 0]))
            span_y = float(np.max(finite_points[:, 1]) - np.min(finite_points[:, 1]))
            scene_span = max(span_x, span_y, 1.0)

    for curve in surface_curves:
        row_index = int(curve.row_index)
        if row_index in labeled_rows or row_index < 0 or row_index >= len(rows):
            continue
        row = rows[row_index]
        if row.surface not in label_surfaces and curve.kind != "stl_solid":
            continue
        pts = np.asarray(curve.points_world, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        finite = np.isfinite(pts[:, 0]) & np.isfinite(pts[:, 1])
        if not np.any(finite):
            continue
        pts = pts[finite]
        center = np.mean(pts, axis=0)
        tangent = np.asarray(pts[-1] - pts[0], dtype=float)
        tangent_norm = float(np.linalg.norm(tangent))
        if tangent_norm <= 1e-12:
            normal = np.array([0.0, 1.0], dtype=float)
        else:
            tangent /= tangent_norm
            normal = np.array([-tangent[1], tangent[0]], dtype=float)
        if normal[1] < 0.0:
            normal *= -1.0
        offset = max(0.045 * scene_span, 1.4, 0.10 * max(float(row.diameter), 1.0))
        if curve.kind == "stl_solid":
            color = "#0369a1"
        else:
            color = "#0e7490" if row.surface == "Beam Splitter" else "#202020"
        display_settings = _row_display_settings(row)
        label_text = str(
            display_settings.get("label", display_settings.get("label_text", row.name or row.surface))
            or row.surface
        ).strip()
        labels.append(
            LabelSpec(
                text=label_text,
                x=float(center[0] + normal[0] * offset),
                y=float(center[1] + normal[1] * offset),
                row_index=row_index,
                fontsize=8.0,
                color=color,
                ha="center",
                va="bottom",
            )
        )
        labeled_rows.add(row_index)
    return labels


def _build_source_markers(
    sources: list[SceneSource3D],
    *,
    display_orientation: str,
    project_fn: Callable | None,
) -> tuple[list[SurfaceCurve3D], list[LabelSpec]]:
    curves: list[SurfaceCurve3D] = []
    labels: list[LabelSpec] = []
    for source in sources:
        if not bool(getattr(source, "enabled", True)) or not bool(getattr(source, "physical", False)):
            continue
        settings = getattr(source, "settings", {}) or {}
        if not isinstance(settings, dict):
            settings = {}
        origin = np.asarray(getattr(source, "origin", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)
        direction = np.asarray(getattr(source, "direction", (0.0, 0.0, 1.0)), dtype=float).reshape(-1)
        if origin.size < 3 or direction.size < 3:
            continue
        origin = origin[:3]
        direction = direction[:3]
        if not np.all(np.isfinite(origin)) or not np.all(np.isfinite(direction)):
            continue
        direction_norm = float(np.linalg.norm(direction))
        if direction_norm <= 1e-12:
            continue
        direction = direction / direction_norm
        radius = _source_marker_radius(source)
        center = _project_3d_yz_point(origin, display_orientation=display_orientation, project_fn=project_fn)
        tip = _project_3d_yz_point(
            origin + direction * max(2.0 * radius, 6.0),
            display_orientation=display_orientation,
            project_fn=project_fn,
        )
        if center is None or tip is None:
            continue
        axis = np.asarray(tip - center, dtype=float)
        axis_norm = float(np.linalg.norm(axis))
        if axis_norm <= 1e-12:
            tangent = np.asarray((0.0, 1.0), dtype=float)
        else:
            axis = axis / axis_norm
            tangent = np.asarray((-axis[1], axis[0]), dtype=float)
        half = max(radius, 1.5)
        aperture = np.vstack((center - tangent * half, center + tangent * half))
        axis_line = np.vstack((center, tip))
        curves.append(SurfaceCurve3D(
            row_index=-1,
            kind="source",
            points_world=aperture,
            style=StyleHint(color="#f97316", linewidth=2.3, alpha=0.95),
        ))
        if _source_marker_setting_bool(settings, ("show_source_axis", "show_axis", "show_launch_axis"), True):
            curves.append(SurfaceCurve3D(
                row_index=-1,
                kind="source_axis",
                points_world=axis_line,
                style=StyleHint(color="#f97316", linewidth=1.2, alpha=0.75),
            ))
        text_offset = max(radius * 0.35, 1.4)
        labels.append(LabelSpec(
            text=str(getattr(source, "name", "") or getattr(source, "source_id", "") or "Source"),
            x=float(center[0] + tangent[0] * (half + text_offset)),
            y=float(center[1] + tangent[1] * (half + text_offset)),
            row_index=-1,
            fontsize=8.5,
            color="#c2410c",
            ha="center",
            va="bottom",
        ))
    return curves, labels


def _source_marker_setting_bool(settings: dict[str, object], keys: tuple[str, ...], default: bool) -> bool:
    for key in keys:
        if key not in settings:
            continue
        value = settings.get(key)
        if isinstance(value, str):
            return value.strip().lower() not in {"0", "false", "no", "off", "hide", ""}
        return bool(value)
    return bool(default)


def _source_marker_radius(source: SceneSource3D) -> float:
    settings = getattr(source, "settings", {}) or {}
    for key in ("launch_radius", "radius", "waist_radius"):
        try:
            value = float(settings.get(key))
        except Exception:
            continue
        if np.isfinite(value) and value > 0.0:
            return max(value, 1.5)
    try:
        length = float(settings.get("length"))
    except Exception:
        length = 0.0
    if np.isfinite(length) and length > 0.0:
        return max(0.5 * length, 1.5)
    return 2.0


def _project_3d_yz_point(
    point: np.ndarray,
    *,
    display_orientation: str,
    project_fn: Callable | None,
) -> np.ndarray | None:
    try:
        p = np.asarray(point, dtype=float).reshape(-1)
    except Exception:
        return None
    if p.size < 3 or not np.all(np.isfinite(p[:3])):
        return None
    if project_fn is not None:
        try:
            x_vals, y_vals = project_fn([float(p[2])], [float(p[1])])
            return np.asarray((float(np.asarray(x_vals, dtype=float).ravel()[0]), float(np.asarray(y_vals, dtype=float).ravel()[0])), dtype=float)
        except Exception:
            return None
    if display_orientation == "Horizontal":
        return np.asarray((-float(p[1]), -float(p[2])), dtype=float)
    return np.asarray((float(p[2]), float(p[1])), dtype=float)


# ---------------------------------------------------------------------------
# Pick regions
# ---------------------------------------------------------------------------

def _build_pick_regions(rows: list, surface_curves: list[SurfaceCurve3D]) -> list[PickRegion]:
    region_map: dict[int, list[np.ndarray]] = {}
    for curve in surface_curves:
        if curve.kind == "lens_edge" or int(curve.row_index) < 0:
            continue
        pts = np.asarray(curve.points_world, dtype=float)
        if pts.ndim != 2 or pts.shape[0] < 2:
            continue
        region_map.setdefault(curve.row_index, []).append(pts)
    return [PickRegion(row_index=ri, polylines=polys) for ri, polys in region_map.items()]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def surface_style_for_row(row: Any) -> tuple[str, float, float]:
    surface = getattr(row, "surface", "Standard")
    advanced = getattr(row, "advanced", {}) or {}
    if isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None"):
        return "#64748b", 1.45, 0.72
    if surface == "Diffuse Object":
        return "#16a34a", 2.2, 0.95
    if surface in {"Mirror", "Object Target"}:
        return "#202020", 2.2, 0.95
    if surface == "Beam Splitter":
        return "#0891b2", 2.0, 0.92
    if surface == "Aperture":
        return "#b45309", 1.6, 0.95
    if surface == "Thin Lens":
        return "#7c3aed", 1.5, 0.9
    if surface == "Grating":
        return "#0f766e", 1.5, 0.9
    return "#2563eb", 1.4, 0.85


def _has_off_axis_geometry(rows: list) -> bool:
    for row in rows:
        if row.surface in {"Mirror", "Object Target", "Diffuse Object"}:
            return True
        if any(
            abs(value) > 1e-9
            for value in (row.tilt_x, row.tilt_y, row.tilt_z, row.desp_x, row.desp_y, row.desp_z, row.axis_move)
        ):
            return True
    return False


def _default_field_colors(count: int) -> list[str]:
    if count <= 1:
        return ["#39FF14"]
    cmap = [
        "#39FF14", "#00E5FF", "#FF9F1C", "#FF4D6D",
        "#9B5DE5", "#FFD166", "#2EC4B6", "#E71D36",
    ]
    return [cmap[i % len(cmap)] for i in range(count)]


def _reference_plane_display_points(
    row_index: int,
    row: Any,
    z_pos: float,
    overrides: dict,
    project_fn: Callable | None,
) -> np.ndarray | None:
    if row.surface not in {"Object", "Image", "Aperture"}:
        return None
    display_settings = _row_display_settings(row)
    center_value = display_settings.get("plane_center")
    tangent_value = display_settings.get("plane_tangent")
    if center_value is not None and tangent_value is not None:
        try:
            center = np.asarray(center_value, dtype=float).ravel()
            tangent = np.asarray(tangent_value, dtype=float).ravel()
            if center.size >= 2 and tangent.size >= 2:
                center = center[:2]
                tangent = tangent[:2]
                tangent_norm = float(np.linalg.norm(tangent))
                if tangent_norm > 1e-12:
                    tangent = tangent / tangent_norm
                    half_height = max(row.diameter / 2.0, 0.5)
                    p0 = center - tangent * half_height
                    p1 = center + tangent * half_height
                    return np.vstack((p0, p1))
        except Exception:
            pass
    override = overrides.get(row_index)
    if override is not None:
        center, along = override
        tangent = np.array([-along[1], along[0]], dtype=float)
        tangent /= max(np.linalg.norm(tangent), 1e-12)
        half_height = max(row.diameter / 2.0, 0.5)
        p0 = center - tangent * half_height
        p1 = center + tangent * half_height
        return np.vstack((p0, p1))
    half_height = max(row.diameter / 2.0, 0.5)
    center_z = z_pos + float(row.desp_z)
    if row.surface == "Image" and abs(float(row.thickness)) > 1e-12:
        center_z += float(row.thickness)
    center_y = float(row.desp_y)
    if project_fn is not None:
        x_vals, y_vals = project_fn(
            [center_z, center_z],
            [center_y - half_height, center_y + half_height],
        )
        return np.column_stack((np.asarray(x_vals, dtype=float), np.asarray(y_vals, dtype=float)))
    return np.array([[center_z, center_y - half_height], [center_z, center_y + half_height]], dtype=float)


def _build_row_surface_groups(rows: list, curve_map: dict[int, np.ndarray]) -> list[list[int]]:
    groups: list[list[int]] = []
    group: list[int] = []
    refractive_surface_types = {"Standard", "Thin Lens", "Grating", "Beam Splitter"}
    for row_index, row in enumerate(rows):
        advanced = getattr(row, "advanced", {}) or {}
        is_optical_solid = isinstance(advanced, dict) and advanced.get("Solid_3d_stl") not in (None, "", "None")
        if row_index in curve_map and row.surface in refractive_surface_types and not is_optical_solid:
            group.append(row_index)
            if str(row.glass).strip().upper() == "AIR":
                if len(group) >= 2:
                    groups.append(group[:])
                group = []
        else:
            if len(group) >= 2:
                groups.append(group[:])
            group = []
    if len(group) >= 2:
        groups.append(group[:])
    return groups


def _polyline_endpoints(polyline: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    pts = np.asarray(polyline, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return None, None
    return pts[0].copy(), pts[-1].copy()


def _curve_group_aperture_axis(curve_a: np.ndarray, curve_b: np.ndarray) -> np.ndarray:
    axes: list[np.ndarray] = []
    for curve in (curve_a, curve_b):
        p0, p1 = _polyline_endpoints(curve)
        if p0 is None or p1 is None:
            continue
        axis = np.asarray(p1 - p0, dtype=float)
        norm = np.linalg.norm(axis)
        if norm <= 1e-12:
            continue
        axis /= norm
        if axes and float(np.dot(axis, axes[0])) < 0.0:
            axis *= -1.0
        axes.append(axis)
    if not axes:
        return np.array([0.0, 1.0], dtype=float)
    combined = np.sum(np.asarray(axes, dtype=float), axis=0)
    norm = np.linalg.norm(combined)
    if norm <= 1e-12:
        return axes[0]
    return combined / norm


def _curve_edge_points(curve: np.ndarray, aperture_axis: np.ndarray) -> tuple[np.ndarray | None, np.ndarray | None]:
    pts = np.asarray(curve, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return None, None
    axis = np.asarray(aperture_axis, dtype=float)
    norm = np.linalg.norm(axis)
    if norm <= 1e-12:
        return _polyline_endpoints(pts)
    axis /= norm
    coord = pts @ axis
    low_idx = int(np.argmin(coord))
    high_idx = int(np.argmax(coord))
    return pts[low_idx].copy(), pts[high_idx].copy()
