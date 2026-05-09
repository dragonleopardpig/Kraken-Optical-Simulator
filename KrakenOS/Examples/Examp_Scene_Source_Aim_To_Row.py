"""Aim a physical scene source at an optical row center.

This mirrors the Scene Source Manager workflow:

1. Choose a source record.
2. Choose ``Aim direction at row``.
3. Click ``Aim Direction At Row``.
4. Save and apply the source.

The helper computes only normalized ``Source L/M/N`` direction cosines. It does
not move the source and it does not insert or reorder KrakenOS surface rows.
"""

from __future__ import annotations

import numpy as np

from KrakenOS.UI.layout_editor import SurfaceRow
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

    print("Scene source row aiming")
    print(f"target row: {aim['row_index']} {aim['row_name']}")
    print(f"target point [mm]: {target}")
    print(f"distance [mm]: {float(aim['distance_mm']):.6g}")
    print(f"Source L/M/N: {direction}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
