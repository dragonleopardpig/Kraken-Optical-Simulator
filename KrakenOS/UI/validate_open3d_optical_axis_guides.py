"""Validate Open 3D optical-axis guide selection for sequential vs off-axis scenes."""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.open3d_inspector import Kraken3DInspector
from KrakenOS.UI.scene_geometry import OpticalVolume3D, RayEvent3D, RayPath3D, SceneBundle


class _FakeRenderer:
    def ComputeVisiblePropBounds(self):
        return (-20.0, 20.0, -20.0, 20.0, -10.0, 80.0)


class _FakeBoolVar:
    def __init__(self, value: bool) -> None:
        self._value = bool(value)

    def get(self) -> bool:
        return self._value


def _records_for(bundle: SceneBundle) -> list[dict[str, object]]:
    inspector = object.__new__(Kraken3DInspector)
    inspector._renderer = _FakeRenderer()
    # The traced-axis branch in _optical_axis_records_for_3d gates on the
    # inspector's show_rays toggle; the fake inspector skips __init__ so we
    # have to provide a stand-in or the function early-returns the global
    # guide only.
    inspector.show_rays_var = _FakeBoolVar(True)
    # The rays-off cache reads these on every call; the fake inspector skips
    # __init__, so seed them or _optical_axis_records_for_3d raises AttributeError
    # before it ever reaches the axis-selection logic under test.
    inspector._cached_traced_axis_signature = None
    inspector._cached_traced_axis_records = []
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


def _finite_field_transmit_path() -> RayPath3D:
    """A finite/off-axis source FIELD chief ray launched tilted that transmits
    straight through a beam splitter. Every segment stays collinear with the
    ray's OWN launch direction (only the field angle tilts it off +Z), so it
    must NOT spawn an extra optical axis. bugs/0083: the old fold test measured
    deviation from the global +Z axis, so the field tilt (~8 deg here) read as a
    fold and each field ray spawned an unwanted 'Optical Axis N'. The splitter
    event makes the path a non-refractive-steering 'physical path', so it reaches
    the fold gate exactly like the recording's field rays did."""
    return RayPath3D(
        ray_index=22,
        field_index=3,
        points_world=np.asarray(
            [
                [0.0, -9.0, -20.0],
                [0.0, -6.0, 0.0],
                [0.0, -3.0, 20.0],
                [0.0, 0.0, 40.0],
            ],
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_id="surface:1",
                event_kind="surface",
                event_type="refraction",
                ray_index=22,
                step=1,
                surface_id=1,
                mesh_face_id="F101",
                point_world=np.asarray([0.0, -6.0, 0.0], dtype=float),
            ),
            RayEvent3D(
                event_id="surface:2",
                event_kind="surface",
                event_type="transmit",
                surface_name="Beam Splitter",
                ray_index=22,
                step=2,
                surface_id=2,
                mesh_face_id="F102",
                point_world=np.asarray([0.0, -3.0, 20.0], dtype=float),
            ),
        ],
    )


def _off_axis_launch_fold_path() -> RayPath3D:
    """A field ray launched tilted that GENUINELY folds (90 deg reflection to
    +X). Its reflected segment deviates ~90 deg from the ray's own launch
    direction, so it must still earn a traced axis -- guarding bugs/0083 against
    over-suppressing real folds carried by off-axis-launched rays."""
    return RayPath3D(
        ray_index=9,
        field_index=2,
        points_world=np.asarray(
            [
                [0.0, -9.0, -20.0],
                [0.0, -6.0, 0.0],
                [0.0, -3.0, 20.0],
                [20.0, -3.0, 20.0],
            ],
            dtype=float,
        ),
        events=[
            RayEvent3D(
                event_id="surface:1",
                event_kind="surface",
                event_type="refraction",
                ray_index=9,
                step=1,
                surface_id=1,
                mesh_face_id="F201",
                point_world=np.asarray([0.0, -6.0, 0.0], dtype=float),
            ),
            RayEvent3D(
                event_id="surface:2",
                event_kind="surface",
                event_type="reflect",
                surface_name="Fold Mirror",
                ray_index=9,
                step=2,
                surface_id=2,
                mesh_face_id="F202",
                point_world=np.asarray([0.0, -3.0, 20.0], dtype=float),
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
    if len(off_axis_records) != 1 or traced_off_axis:
        raise AssertionError(
            "Off-axis refractive ray spread alone should not create extra optical-axis guides, "
            f"got {off_axis_records!r}"
        )

    off_axis_folded_bundle = SceneBundle(
        ray_paths=[_folded_path()],
        has_off_axis=True,
    )
    off_axis_folded_records = _records_for(off_axis_folded_bundle)
    traced_off_axis_folded = [
        record for record in off_axis_folded_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(off_axis_folded_records) <= 1 or not traced_off_axis_folded:
        raise AssertionError(f"Off-axis folded scenes should keep traced axis guides, got {off_axis_folded_records!r}")

    finite_field_bundle = SceneBundle(
        ray_paths=[_finite_field_transmit_path()],
        optical_volumes=[OpticalVolume3D(volume_id="splitter:1")],
        has_off_axis=True,
    )
    finite_field_records = _records_for(finite_field_bundle)
    traced_finite_field = [
        record for record in finite_field_records if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(finite_field_records) != 1 or traced_finite_field:
        raise AssertionError(
            "Finite/off-axis field rays that transmit straight through must not spawn extra optical axes "
            f"(bugs/0083), got {finite_field_records!r}"
        )

    off_axis_launch_fold_bundle = SceneBundle(
        ray_paths=[_off_axis_launch_fold_path()],
        has_off_axis=True,
    )
    off_axis_launch_fold_records = _records_for(off_axis_launch_fold_bundle)
    traced_off_axis_launch_fold = [
        record
        for record in off_axis_launch_fold_records
        if str(record.get("axis_kind", "") or "") == "traced_chief_ray_segment"
    ]
    if len(off_axis_launch_fold_records) <= 1 or not traced_off_axis_launch_fold:
        raise AssertionError(
            "A genuinely folded ray launched off-axis must still keep its traced axis (bugs/0083), "
            f"got {off_axis_launch_fold_records!r}"
        )

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
