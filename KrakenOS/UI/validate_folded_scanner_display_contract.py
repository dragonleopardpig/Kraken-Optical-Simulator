"""Validate folded galvo/F-theta display semantics in the shared 2-D renderer."""

from __future__ import annotations

import importlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import LineCollection

import KrakenOS as Kos

from KrakenOS.UI.layout_editor import SurfaceRow, _build_system_from_specs
from KrakenOS.UI.layout_plot_controller import project_scene_bundle
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor
from KrakenOS.UI.scene_renderer_2d import render_scene_2d


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _rows_and_settings() -> tuple[list[SurfaceRow], dict[str, object]]:
    module = importlib.import_module("KrakenOS.common_optical_layouts.galvo_f_theta_laser_scanner")
    allowed = set(SurfaceRow.__dataclass_fields__)
    rows = [
        SurfaceRow(**{key: value for key, value in row.items() if key in allowed})
        for row in list(getattr(module, "SURFACES", []))
    ]
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    return rows, settings


def _distance_point_to_segment(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    segment = end - start
    denom = float(np.dot(segment, segment))
    if denom <= 1.0e-12:
        return float(np.linalg.norm(point - start))
    t = float(np.clip(np.dot(point - start, segment) / denom, 0.0, 1.0))
    closest = start + t * segment
    return float(np.linalg.norm(point - closest))


def _distance_point_to_polyline(point: np.ndarray, polyline: np.ndarray) -> float:
    pts = np.asarray(polyline, dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 2:
        return float("inf")
    return min(
        _distance_point_to_segment(point, pts[index], pts[index + 1])
        for index in range(pts.shape[0] - 1)
    )


def main() -> None:
    rows, settings = _rows_and_settings()
    editor = _snapshot_editor(rows, settings)
    system = _build_system_from_specs(editor._serializable_row_specs())
    rays = Kos.raykeeper(system)
    max_radius = max((max(float(row.diameter) / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(
        system,
        rays,
        float(editor._current_wavelength()),
        max_radius,
        allow_full_pupil=True,
        sampling_mode=editor._preview_2d_sampling_mode(),
    )
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    projected = project_scene_bundle(
        bundle,
        editor._current_display_orientation(),
        filter_projection_axis_fields=editor._should_filter_projection_axis_fields(bundle),
        filter_projection_slice=editor._should_filter_projection_slice(bundle),
        refresh_auto_leg_graph=editor._refresh_auto_leg_graph,
        filter_arm_view=editor._filter_projected_scene_for_arm_view,
        filter_ray_display=editor._filter_projected_scene_for_ray_display,
    )

    _require(
        bool(list(bundle.extra.get("folded_ray_display_paths") or [])),
        "expected folded scanner preview to build folded display paths",
    )
    _require(
        projected.rays and all(bool(getattr(ray, "draw_behind_surfaces", False)) for ray in projected.rays),
        "folded YZ preview rays should render behind the optical outlines",
    )

    plans = editor._folded_scan_overlay_plans(max_radius, system=system)
    field_thetas = [float(plan.get("field_theta", 0.0) or 0.0) for plan in plans]
    _require(field_thetas, "expected galvo scan overlay plans")
    _require(
        all(abs(theta) > 1.0e-9 for theta in field_thetas),
        f"nominal folded scan overlay should not duplicate the traced center bundle: {field_thetas}",
    )

    image_row_index = len(rows) - 1
    image_curves = [
        curve
        for curve in projected.curves
        if int(getattr(curve, "row_index", -1)) == image_row_index and str(getattr(curve, "kind", "")) == "image"
    ]
    _require(image_curves, "expected folded scan plane curve in projected scene")
    image_labels = [
        label
        for label in projected.labels
        if int(getattr(label, "row_index", -1)) == image_row_index
    ]
    _require(image_labels, "expected folded scan plane label")
    label_point = np.asarray((float(image_labels[0].x), float(image_labels[0].y)), dtype=float)
    image_curve_distance = min(
        _distance_point_to_polyline(label_point, np.asarray(curve.points_2d, dtype=float))
        for curve in image_curves
    )
    _require(
        image_curve_distance <= 10.0,
        f"folded scan plane label drifted away from the folded image plane: distance={image_curve_distance:.4g}",
    )

    rogue_detector_curves = [
        curve
        for curve in projected.curves
        if str(getattr(curve, "kind", "")).startswith("detector_")
    ]
    _require(
        not rogue_detector_curves,
        "folded YZ preview should not show unfurled detector footprint/crosshair overlays",
    )

    render_projected = editor._projected_scene_for_layout_render(projected)
    fig, ax = plt.subplots(figsize=(12, 7))
    try:
        surface_line_count = render_scene_2d(
            render_projected,
            ax,
            show_clipped_rays=bool(editor.show_clipped_rays_var.get()),
            show_labels=True,
            ray_count_hint=max(1, int(editor._preview_field_ray_count)),
        )
        surface_zorders = [float(line.get_zorder()) for line in ax.lines[:surface_line_count]]
        ray_zorders = [
            float(collection.get_zorder())
            for collection in ax.collections
            if isinstance(collection, LineCollection)
        ]
    finally:
        plt.close(fig)
    _require(surface_zorders, "expected rendered surface outlines")
    _require(ray_zorders, "expected rendered ray line collections")
    _require(
        max(ray_zorders) < min(surface_zorders),
        f"folded rays should render behind optics: ray={max(ray_zorders):.3f}, surface={min(surface_zorders):.3f}",
    )

    print("Folded scanner display validation passed.")


if __name__ == "__main__":
    main()
