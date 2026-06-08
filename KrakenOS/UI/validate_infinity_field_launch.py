"""Validate infinity-object field-angle launch geometry."""

from __future__ import annotations

import importlib
from dataclasses import dataclass

import KrakenOS as Kos
import numpy as np

from KrakenOS.UI.layout_editor import PROJECTION_MODE_FULL_3D, SurfaceRow, _build_system_from_specs
from KrakenOS.UI.layout_plot_controller import project_scene_bundle
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor


@dataclass(frozen=True)
class InfinityFieldLaunchCheck:
    check: str
    ok: bool
    detail: str


def _double_gauss_rows_settings() -> tuple[list[SurfaceRow], dict[str, object]]:
    module = importlib.import_module("KrakenOS.common_optical_layouts.zemax_double_gauss_28_degree")
    allowed = set(SurfaceRow.__dataclass_fields__)
    rows = [
        SurfaceRow(**{key: value for key, value in row.items() if key in allowed})
        for row in list(getattr(module, "SURFACES", []))
    ]
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    settings.update(
        {
            "object_mode": "Infinity",
            "field_type": "Angle",
            "field_value": "14.0",
            "field_count": "3",
            "ray_count": "21",
            "source_model": "Pupil / field",
            "display_orientation": "YZ",
        }
    )
    return rows, settings


def _bundle_arrays(bundle) -> tuple[np.ndarray, np.ndarray]:
    origins = np.column_stack([np.asarray(bundle[index], dtype=float).reshape(-1) for index in (0, 1, 2)])
    directions = np.column_stack([np.asarray(bundle[index], dtype=float).reshape(-1) for index in (3, 4, 5)])
    return origins, directions


def _bundle_intersections_at_z(bundle, z_value: float) -> np.ndarray:
    origins, directions = _bundle_arrays(bundle)
    dz = directions[:, 2]
    valid = np.isfinite(dz) & (np.abs(dz) > 1.0e-12)
    if not np.any(valid):
        return np.empty((0, 2), dtype=float)
    t = (float(z_value) - origins[valid, 2]) / dz[valid]
    return origins[valid, :2] + directions[valid, :2] * t[:, None]


def validate_infinity_field_launch() -> list[InfinityFieldLaunchCheck]:
    rows, settings = _double_gauss_rows_settings()
    editor = _snapshot_editor(rows, settings)
    system = _build_system_from_specs(editor._serializable_row_specs())
    preview_2d_mode = editor._preview_2d_sampling_mode()
    preview_3d_mode = editor._preview_3d_sampling_mode()
    pupil_radius = max(float(row.diameter) for row in rows) / 2.0
    world_bundles, world_rays_per_field = editor._build_world_envelope_bundles(pupil_radius, system=system)
    world_bundle_lengths = [
        int(len(np.asarray(bundle[0], dtype=float).reshape(-1)))
        for bundle in world_bundles
    ]
    world_rays = Kos.raykeeper(system)
    editor._trace_preview_rays(
        system,
        world_rays,
        editor._current_wavelength(),
        pupil_radius,
        sampling_mode=preview_2d_mode,
    )
    traced_world_count = len(getattr(world_rays, "CC", []) or [])
    expected_world_count = int(len(world_bundles) * int(settings["ray_count"]))
    world_bundle = editor._build_scene_bundle(system, world_rays, pupil_radius)
    displayable_world_count = sum(
        1
        for path in list(getattr(world_bundle, "ray_paths", []) or [])
        if np.asarray(getattr(path, "points_world", []), dtype=float).ndim == 2
        and np.asarray(getattr(path, "points_world", []), dtype=float).shape[0] >= 2
    )
    world_yz_projection = project_scene_bundle(
        world_bundle,
        "YZ",
        filter_projection_axis_fields=editor._should_filter_projection_axis_fields(world_bundle),
        filter_projection_slice=editor._should_filter_projection_slice(world_bundle),
    )
    projected_world_count = len(list(getattr(world_yz_projection, "rays", []) or []))
    axis_projection_filter_active = editor._should_filter_projection_axis_fields(world_bundle)
    projection_slice_filter_active = editor._should_filter_projection_slice(world_bundle)
    editor.projection_display_mode_var.set(PROJECTION_MODE_FULL_3D)
    full_world_yz_projection = project_scene_bundle(
        world_bundle,
        "YZ",
        filter_projection_axis_fields=editor._should_filter_projection_axis_fields(world_bundle),
        filter_projection_slice=editor._should_filter_projection_slice(world_bundle),
    )
    full_projected_world_count = len(list(getattr(full_world_yz_projection, "rays", []) or []))
    bundles, rays_per_field = editor._build_world_section_bundles(pupil_radius, system=system)
    reference = editor._infinity_field_launch_reference_point(system=system)
    field_pairs = editor._field_cross_pairs_for_world_sections(editor._current_field_angle_deg())

    y_field_bundles: list[tuple[np.ndarray, np.ndarray, np.ndarray]] = []
    for bundle in bundles:
        origins, directions = _bundle_arrays(bundle)
        mean_direction = np.mean(directions, axis=0)
        if abs(float(mean_direction[1])) > 1.0e-4 and abs(float(mean_direction[0])) < 1.0e-4:
            hits = _bundle_intersections_at_z(bundle, float(reference[2]))
            y_field_bundles.append((origins, directions, hits))

    centered_at_reference = all(
        hits.size > 0 and np.allclose(np.median(hits, axis=0), reference[:2], atol=1.0e-7)
        for _origins, _directions, hits in y_field_bundles
    )
    shifted_launches = [
        float(np.mean(origins[:, 1]))
        for origins, directions, _hits in y_field_bundles
        if abs(float(np.mean(directions[:, 1]))) > 1.0e-4
    ]
    field_direction_spans = [
        float(np.max(np.ptp(directions, axis=0)))
        for _origins, directions, _hits in y_field_bundles
    ]

    checks = [
        InfinityFieldLaunchCheck(
            "Double Gauss 2D keeps the flat meridional fan while Open 3D revolves it into a launch cone",
            preview_2d_mode == "world_envelope" and preview_3d_mode == "world_cone",
            f"2d={preview_2d_mode}, 3d={preview_3d_mode}",
        ),
        InfinityFieldLaunchCheck(
            "canonical world-envelope trace honors Ray Count per field",
            int(world_rays_per_field) == int(settings["ray_count"])
            and bool(world_bundle_lengths)
            and all(length == int(settings["ray_count"]) for length in world_bundle_lengths)
            and traced_world_count == expected_world_count,
            (
                f"ray_count={settings['ray_count']}, rays_per_field={world_rays_per_field}, "
                f"bundle_lengths={world_bundle_lengths[:5]}, bundles={len(world_bundles)}, "
                f"traced={traced_world_count}, expected={expected_world_count}"
            ),
        ),
        InfinityFieldLaunchCheck(
            "canonical YZ projection displays every displayable full-3D ray",
            not axis_projection_filter_active
            and not projection_slice_filter_active
            and projected_world_count == displayable_world_count,
            (
                f"mode={editor._scene_bundle_launch_sampling_mode(world_bundle)}, "
                f"projected={projected_world_count}, displayable={displayable_world_count}, "
                f"traced={traced_world_count}, axis_filter={axis_projection_filter_active}"
            ),
        ),
        InfinityFieldLaunchCheck(
            "canonical YZ full-3D projection can display every displayable world-envelope ray",
            not editor._should_filter_projection_axis_fields(world_bundle)
            and not editor._should_filter_projection_slice(world_bundle)
            and full_projected_world_count == displayable_world_count,
            (
                f"projection_mode={editor._current_projection_display_mode()}, "
                f"projected={full_projected_world_count}, displayable={displayable_world_count}"
            ),
        ),
        InfinityFieldLaunchCheck(
            "Double Gauss infinity field samples build multiple world-section bundles",
            len(bundles) >= 3 and int(rays_per_field) > 1 and len(field_pairs) >= 3,
            f"bundles={len(bundles)}, rays_per_field={rays_per_field}, field_pairs={field_pairs[:5]}",
        ),
        InfinityFieldLaunchCheck(
            "off-axis Y-field bundles are stop-centered, not Object-plane centered finite fans",
            len(y_field_bundles) >= 2 and centered_at_reference,
            (
                f"reference_xy={np.round(reference[:2], 9).tolist()}, "
                f"median_hits={[np.round(np.median(item[2], axis=0), 9).tolist() for item in y_field_bundles]}"
            ),
        ),
        InfinityFieldLaunchCheck(
            "off-axis infinity-field launch origins shift before the first surface",
            len(shifted_launches) >= 2 and max(abs(value) for value in shifted_launches) > 1.0,
            f"origin_y_means={np.round(shifted_launches, 6).tolist()}",
        ),
        InfinityFieldLaunchCheck(
            "each infinity-field bundle remains internally parallel",
            bool(field_direction_spans) and max(field_direction_spans) <= 1.0e-12,
            f"direction_ptp_max={max(field_direction_spans) if field_direction_spans else float('nan'):.9g}",
        ),
    ]
    return checks


def main() -> int:
    checks = validate_infinity_field_launch()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        print(f"{'PASS' if check.ok else 'FAIL'}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
