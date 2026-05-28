"""Validate Open 3D optical-axis guide selection for sequential vs off-axis scenes."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.scene_geometry import OpticalVolume3D, RayEvent3D, RayPath3D, SceneBundle


class _FakeRenderer:
    def ComputeVisiblePropBounds(self):
        return (-20.0, 20.0, -20.0, 20.0, -10.0, 80.0)


def _records_for(bundle: SceneBundle) -> list[dict[str, object]]:
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer()
    return Kraken3DInspector._optical_axis_records_for_3d(inspector, bundle)


def _chief_path() -> RayPath3D:
    return RayPath3D(
        ray_index=7,
        field_index=1,
        points_world=np.asarray(
            [
                [0.0, -5.0, 0.0],
                [0.0, -1.0, 20.0],
                [0.0, 0.0, 40.0],
            ],
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_id="surface:1",
                event_kind="surface",
                event_type="refraction",
                ray_index=7,
                step=1,
                surface_id=1,
                mesh_face_id="F001",
                point_world=np.asarray([0.0, -1.0, 20.0], dtype=float),
            ),
            RayEvent3D(
                event_id="surface:2",
                event_kind="surface",
                event_type="refraction",
                ray_index=7,
                step=2,
                surface_id=2,
                mesh_face_id="F002",
                point_world=np.asarray([0.0, 0.0, 40.0], dtype=float),
            ),
        ],
    )


def _folded_path() -> RayPath3D:
    return RayPath3D(
        ray_index=3,
        field_index=0,
        points_world=np.asarray(
            [
                [0.0, 0.0, -10.0],
                [0.0, 0.0, 10.0],
                [12.0, 0.0, 24.0],
                [24.0, 0.0, 38.0],
            ],
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_id="surface:1",
                event_kind="surface",
                event_type="refract",
                ray_index=3,
                step=1,
                surface_id=1,
                mesh_face_id="F005",
                point_world=np.asarray([0.0, 0.0, 10.0], dtype=float),
            ),
            RayEvent3D(
                event_id="surface:1",
                event_kind="surface",
                event_type="reflect",
                ray_index=3,
                step=2,
                surface_id=1,
                mesh_face_id="F004",
                point_world=np.asarray([12.0, 0.0, 24.0], dtype=float),
            ),
        ],
    )


def main() -> int:
    centered_bundle = SceneBundle(
        ray_paths=[_chief_path()],
        has_off_axis=False,
    )
    centered_records = _records_for(centered_bundle)
    traced_centered = [
        record for record in centered_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(centered_records) != 1 or traced_centered:
        raise AssertionError(f"Centered sequential scenes should keep only the global optical axis, got {centered_records!r}")

    centered_volume_bundle = SceneBundle(
        ray_paths=[_chief_path()],
        optical_volumes=[OpticalVolume3D(volume_id="lens:1")],
        has_off_axis=False,
    )
    centered_volume_records = _records_for(centered_volume_bundle)
    traced_centered_volume = [
        record for record in centered_volume_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(centered_volume_records) != 1 or traced_centered_volume:
        raise AssertionError(
            "Centered refractive optical volumes should not create extra downstream optical-axis guides, "
            f"got {centered_volume_records!r}"
        )

    off_axis_bundle = SceneBundle(
        ray_paths=[_chief_path()],
        has_off_axis=True,
    )
    off_axis_records = _records_for(off_axis_bundle)
    traced_off_axis = [
        record for record in off_axis_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(off_axis_records) <= 1 or not traced_off_axis:
        raise AssertionError(f"Off-axis scenes should keep traced axis guides, got {off_axis_records!r}")

    folded_volume_bundle = SceneBundle(
        ray_paths=[_folded_path()],
        optical_volumes=[OpticalVolume3D(volume_id="penta:1")],
        has_off_axis=False,
    )
    folded_volume_records = _records_for(folded_volume_bundle)
    traced_folded_volume = [
        record for record in folded_volume_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(folded_volume_records) <= 1 or not traced_folded_volume:
        raise AssertionError(f"Centered folded optical volumes should keep traced exit-axis guides, got {folded_volume_records!r}")

    print("Open 3D optical-axis guide validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
