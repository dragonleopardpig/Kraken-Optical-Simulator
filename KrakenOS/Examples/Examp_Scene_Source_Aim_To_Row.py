"""Aim a physical scene source at an optical row center.

This mirrors the Scene Source Manager workflow:

1. Choose a source record.
2. Choose ``Aim direction at row``.
3. Click ``Aim Direction At Row``.
4. Save and apply the source.

The helper computes only normalized ``Source L/M/N`` direction cosines. It does
not move the source and it does not insert or reorder KrakenOS surface rows.
The companion standoff helper places the source origin upstream of the same
target using the current direction and a user-provided distance.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_editor import (
    OPTICAL_SOLID_FACES_ADVANCED_ATTR,
    OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
    SurfaceRow,
    normalize_optical_solid_face_metadata,
)
from KrakenOS.UI.render_layout_snapshot import _snapshot_editor


def main() -> int:
    rows = [
        SurfaceRow(
            label="0",
            surface="Object",
            name="Object",
            thickness=100.0,
            diameter=30.0,
            drawing=0.0,
            glass="AIR",
        ),
        SurfaceRow(
            label="1",
            surface="Aperture",
            name="Off-axis stop",
            thickness=50.0,
            diameter=20.0,
            drawing=1.0,
            desp_y=10.0,
            glass="AIR",
        ),
        SurfaceRow(
            label="2",
            surface="Image",
            name="Detector",
            thickness=0.0,
            diameter=30.0,
            drawing=0.0,
            glass="AIR",
        ),
    ]
    settings = {
        "wavelength": "0.532",
        "source_model": "Collimated disk source",
        "source_radius": "2.0",
        "source_x": "0.0",
        "source_y": "-20.0",
        "source_z": "0.0",
    }
    editor = _snapshot_editor(rows, settings)
    source_spec = editor._scene_source_spec_from_current_panel()
    aim = editor.scene_source_direction_to_row(source_spec, 1)
    source_spec.update(
        {
            "source_l": aim["source_l"],
            "source_m": aim["source_m"],
            "source_n": aim["source_n"],
        }
    )
    source = editor._scene_source_from_spec(source_spec, 0, wavelength=0.532)
    target = tuple(float(value) for value in np.asarray(aim["target_point"], dtype=float).reshape(3))
    direction = tuple(float(value) for value in np.asarray(source.direction, dtype=float).reshape(3))
    placed = editor.scene_source_place_at_row_standoff(source_spec, 1, 40.0)
    placed_origin = tuple(
        float(value)
        for value in np.asarray(
            [placed["source_x"], placed["source_y"], placed["source_z"]],
            dtype=float,
        ).reshape(3)
    )

    print("Scene source row aiming")
    print(f"target row: {aim['row_index']} {aim['row_name']}")
    print(f"target point [mm]: {target}")
    print(f"distance [mm]: {float(aim['distance_mm']):.6g}")
    print(f"Source L/M/N: {direction}")
    print(f"40 mm standoff source XYZ [mm]: {placed_origin}")

    face_metadata = normalize_optical_solid_face_metadata(
        {
            "faces": [
                {
                    "face_id": "F001",
                    "side_2d": "Left",
                    "function": OPTICAL_SOLID_FACE_FUNCTION_TRANSMIT,
                    "normal": [0.0, 0.0, 1.0],
                    "centroid": [0.0, 5.0, 10.0],
                    "area_mm2": 100.0,
                }
            ]
        }
    )
    face_rows = [
        SurfaceRow(label="0", surface="Object", name="Object", thickness=20.0, diameter=20.0, drawing=0.0, glass="AIR"),
        SurfaceRow(
            label="1",
            surface="Solid 3D STL",
            name="CAD target",
            thickness=0.0,
            diameter=20.0,
            drawing=0.0,
            glass="AIR",
            desp_x=1.0,
            desp_y=2.0,
            desp_z=3.0,
            advanced={OPTICAL_SOLID_FACES_ADVANCED_ATTR: face_metadata},
        ),
        SurfaceRow(label="2", surface="Image", name="Image", thickness=0.0, diameter=20.0, drawing=0.0, glass="AIR"),
    ]
    face_editor = _snapshot_editor(face_rows, settings)
    face_aim = face_editor.scene_source_direction_to_row(
        {"source_x": 1.0, "source_y": 7.0, "source_z": 0.0},
        1,
        face_id="F001",
    )
    face_place = face_editor.scene_source_place_at_row_standoff(
        {"source_l": 0.0, "source_m": 0.0, "source_n": 1.0},
        1,
        8.0,
        face_id="F001",
    )
    print()
    print("CAD/STL face-anchor target")
    print(f"target label: {face_aim['target_label']}")
    print(f"target point [mm]: {face_aim['target_point']}")
    print(f"Source L/M/N to face: {(face_aim['source_l'], face_aim['source_m'], face_aim['source_n'])}")
    print(f"8 mm face-standoff source XYZ [mm]: {(face_place['source_x'], face_place['source_y'], face_place['source_z'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
