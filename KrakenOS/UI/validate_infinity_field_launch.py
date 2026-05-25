"""Validate infinity-object field-angle launch geometry."""

from __future__ import annotations

import importlib
from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
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
            "Double Gauss 2D and Open 3D previews use the same canonical sampling mode",
            preview_2d_mode == preview_3d_mode == "world_envelope",
            f"2d={preview_2d_mode}, 3d={preview_3d_mode}",
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
