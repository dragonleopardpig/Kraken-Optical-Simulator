"""Right-angle source/object split through a beam splitter.

This example mirrors the UI preset:

    Layouts -> Beam Splitters / Folds -> Right-Angle Beam-Splitter Illumination

The Object row is only reference geometry.  The physical illumination source is
at ``(0, -80, 45) mm`` and points along ``+Y``.  A 45 degree 50/50 splitter
turns the reflected child path into ``-Z``, where it reaches the left-side
specular object proxy. The object-return path then hits the splitter again,
transmits through it, passes a clear aperture, and reaches the right-side
camera sensor. The layout also sets ``scene_row_order="before_object"`` so the
future source-visible scene table can show Source 1 before Object without
changing KrakenOS surface indices.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.right_angle_beam_splitter_illumination import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


WAVELENGTH_UM = float(SETTINGS["wavelength"])


def build_system() -> Kos.system:
    return _build_system_from_specs(SURFACES)


def trace_demo(ray_count: int | None = None) -> tuple[Kos.system, Kos.raykeeper]:
    system = build_system()
    info = {"surfaces": SURFACES, "settings": SETTINGS}
    rows = _rows_from_layout_info(info)
    settings = dict(SETTINGS)
    if ray_count is not None:
        settings["ray_count"] = str(int(ray_count))
    editor = _snapshot_editor(rows, settings)
    source_bundle = editor._build_random_source_bundle(sample_count=ray_count)
    source_metadata = editor._source_metadata_for_bundle(source_bundle, WAVELENGTH_UM)

    rays = Kos.raykeeper(system)
    Kos.NsTraceLoop(*source_bundle, WAVELENGTH_UM, rays, clean=1, source_metadata=source_metadata)
    return system, rays


def _value(rays, name: str, index: int, default=""):
    values = getattr(rays, name, None)
    if values is None or index >= len(values):
        return default
    arr = np.asarray(values[index]).reshape(-1)
    if arr.size == 0:
        return default
    return arr[-1]


def summarize_trace(rays: Kos.raykeeper) -> list[dict[str, object]]:
    records = []
    for ray_index, surfaces in enumerate(getattr(rays, "SURFACE", [])):
        records.append(
            {
                "ray": ray_index,
                "source": str(_value(rays, "SOURCE_NAME", ray_index, "")),
                "role": str(_value(rays, "SOURCE_ROLE", ray_index, "")),
                "path": str(_value(rays, "BRANCH_PATH", ray_index, "")),
                "surfaces": [int(value) for value in np.asarray(surfaces, dtype=int).ravel()],
                "power": float(_value(rays, "BRANCH_POWER", ray_index, 0.0) or 0.0),
                "top_mm": float(_value(rays, "TOP", ray_index, 0.0) or 0.0),
            }
        )
    return records


def main() -> int:
    system, rays = trace_demo()
    object_index = 3
    camera_index = len(system.SDT) - 1
    print(TITLE)
    print("source_xyz = ({source_x}, {source_y}, {source_z}) mm".format(**SETTINGS))
    print("source_lmn = ({source_l}, {source_m}, {source_n})".format(**SETTINGS))
    print("object/reference row = S0; left-side specular object proxy = S3; right-side camera sensor = final Image row")
    print("ray | source | role | branch path | surfaces | hits object | reaches camera | power | TOP mm")
    print("--- | --- | --- | --- | --- | --- | --- | --- | ---")
    for record in summarize_trace(rays):
        hits_object = object_index in record["surfaces"]
        reaches_camera = bool(record["surfaces"] and int(record["surfaces"][-1]) == camera_index)
        print(
            f"{record['ray']} | {record['source']} | {record['role']} | "
            f"{record['path']} | {record['surfaces']} | {hits_object} | {reaches_camera} | "
            f"{record['power']:.6g} | {record['top_mm']:.6g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
