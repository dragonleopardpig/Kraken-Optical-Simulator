"""Validate display-only terminal-ray bounding in 2-D scene projections."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from KrakenOS.UI.scene_geometry import (
    RayEvent3D,
    RayPath3D,
    SceneBundle,
    SceneTarget3D,
    SurfaceCurve3D,
    projected_ray_terminal_status,
)
from KrakenOS.UI.scene_projector import SceneProjector2D


@dataclass(frozen=True)
class ProjectionBoundsCheck:
    check: str
    ok: bool
    detail: str


def _layout_curve() -> SurfaceCurve3D:
    return SurfaceCurve3D(
        row_index=1,
        kind="test_layout",
        points_world=np.asarray(
            (
                (0.0, -20.0, 0.0),
                (0.0, 20.0, 0.0),
                (0.0, 20.0, 500.0),
                (0.0, -20.0, 500.0),
                (0.0, -20.0, 0.0),
            ),
            dtype=float,
        ),
    )


def validate_scene_projection_terminal_bounds() -> list[ProjectionBoundsCheck]:
    checks: list[ProjectionBoundsCheck] = []

    escaped_path = RayPath3D(
        ray_index=1,
        points_world=np.asarray(
            (
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 100.0),
                (0.0, -80000.0, 500.0),
            ),
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_kind="terminal",
                event_type="no_next_intersection",
                termination_reason="no_next_intersection",
                ray_index=1,
                point_world=np.asarray((0.0, -80000.0, 500.0), dtype=float),
            )
        ],
    )
    escaped_bundle = SceneBundle(
        surface_curves=[_layout_curve()],
        ray_paths=[escaped_path],
        max_half=20.0,
    )
    escaped_projected = SceneProjector2D("YZ").project_bundle(escaped_bundle)
    escaped_points = np.asarray(escaped_projected.rays[0].points_2d, dtype=float)
    escaped_y_min = float(np.min(escaped_points[:, 1]))
    escaped_y_span = float(escaped_projected.bounds.y_max - escaped_projected.bounds.y_min)
    checks.append(
        ProjectionBoundsCheck(
            "escaped terminal tails are scene-envelope-capped before 2D autoscale",
            escaped_y_min < -300.0 and escaped_y_min > -1000.0 and escaped_y_span < 1000.0,
            f"y_min={escaped_y_min:.6g}, span={escaped_y_span:.6g}, terminal={escaped_points[-1].tolist()}",
        )
    )
    checks.append(
        ProjectionBoundsCheck(
            "escaped terminal status is preserved after display capping",
            projected_ray_terminal_status(escaped_projected.rays[0]) == "escaped",
            f"status={projected_ray_terminal_status(escaped_projected.rays[0])}",
        )
    )

    detector = SceneTarget3D(
        target_id="detector:2",
        name="Image",
        role="detector",
        row_index=2,
        trace_surface=2,
        center_world=np.asarray((0.0, 0.0, 500.0), dtype=float),
        normal_world=np.asarray((0.0, 0.0, 1.0), dtype=float),
        tangent_world=np.asarray((0.0, 1.0, 0.0), dtype=float),
        active_width_mm=10.0,
        active_height_mm=10.0,
        is_detector=True,
    )
    missed_path = RayPath3D(
        ray_index=2,
        points_world=np.asarray(
            (
                (0.0, 0.0, 0.0),
                (0.0, 0.0, 350.0),
                (0.0, 100000.0, 500.0),
            ),
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_kind="terminal",
                event_type="missed_detector",
                termination_reason="missed_detector",
                ray_index=2,
                surface_id=2,
                point_world=np.asarray((0.0, 100000.0, 500.0), dtype=float),
                metadata={"detector_miss_surface": 2},
            )
        ],
    )
    missed_bundle = SceneBundle(
        targets=[detector],
        surface_curves=[_layout_curve()],
        ray_paths=[missed_path],
        max_half=20.0,
    )
    missed_projected = SceneProjector2D("YZ").project_bundle(missed_bundle)
    missed_points = np.asarray(missed_projected.rays[0].points_2d, dtype=float)
    checks.append(
        ProjectionBoundsCheck(
            "missed-detector terminals stay on the detector plane while display-capped",
            abs(float(missed_points[-1, 0]) - 500.0) < 1.0e-9 and abs(float(missed_points[-1, 1])) < 250.0,
            f"terminal={missed_points[-1].tolist()}",
        )
    )
    checks.append(
        ProjectionBoundsCheck(
            "missed-detector terminal status is preserved after display capping",
            projected_ray_terminal_status(missed_projected.rays[0]) == "missed_detector",
            f"status={projected_ray_terminal_status(missed_projected.rays[0])}",
        )
    )
    return checks


def main() -> int:
    checks = validate_scene_projection_terminal_bounds()
    failed = [check for check in checks if not check.ok]
    for check in checks:
        status = "PASS" if check.ok else "FAIL"
        print(f"{status}: {check.check} - {check.detail}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
