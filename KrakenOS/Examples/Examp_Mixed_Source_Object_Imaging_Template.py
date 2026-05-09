"""Trace a layout where illumination source, object, and detector are separate.

This example mirrors the UI preset:

    Layouts -> Sources / Illumination -> Mixed Source/Object Imaging Template

The Object row is not the ray source.  A first-class ``SceneSource3D`` emitter
is declared in ``SETTINGS["scene_sources"]`` and the table uses
``scene_row_order="before_object"`` so the source can be managed independently
from the Object/Image path.  This is the intended starting point for side
illumination, source-to-object setups, and later beam-splitter source/object
splits.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.mixed_source_object_imaging_template import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


WAVELENGTH_UM = float(SETTINGS["wavelength"])


def trace_demo() -> tuple[Kos.system, Kos.raykeeper, object]:
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": SETTINGS})
    editor = _snapshot_editor(rows, SETTINGS)
    system = _build_system_from_specs(SURFACES)
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in rows), default=1.0)
    editor._trace_preview_rays(system, rays, WAVELENGTH_UM, max_radius, allow_full_pupil=False)
    return system, rays, editor


def _last_value(rays, name: str, index: int, default=""):
    values = getattr(rays, name, None)
    if values is None or index >= len(values):
        return default
    arr = np.asarray(values[index]).reshape(-1)
    if arr.size == 0:
        return default
    return arr[-1]


def main() -> int:
    system, rays, editor = trace_demo()
    sources = editor._collect_scene_sources(wavelength=WAVELENGTH_UM)
    image_index = len(system.SDT) - 1
    print(TITLE)
    print("source | role | model | origin mm | direction | rays | power")
    print("--- | --- | --- | --- | --- | --- | ---")
    for source in sources:
        origin = tuple(float(value) for value in np.asarray(source.origin, dtype=float).reshape(-1)[:3])
        direction = tuple(float(value) for value in np.asarray(source.direction, dtype=float).reshape(-1)[:3])
        print(
            f"{source.source_id} | {source.role} | {source.model} | {origin} | {direction} | "
            f"{source.ray_count} | {source.power}"
        )

    source = sources[0]
    aim_to_image = editor.scene_source_direction_to_row(dict(source.settings), image_index)
    print()
    print("target helper | L | M | N | label")
    print("--- | --- | --- | --- | ---")
    print(
        "Aim Direction At Row(Image) | "
        f"{float(aim_to_image['source_l']):.9g} | "
        f"{float(aim_to_image['source_m']):.9g} | "
        f"{float(aim_to_image['source_n']):.9g} | "
        f"{aim_to_image.get('target_label', '')}"
    )

    print()
    print("ray | source | surfaces | reaches detector | power/ray")
    print("--- | --- | --- | --- | ---")
    for ray_index, surfaces in enumerate(getattr(rays, "SURFACE", [])):
        surface_ids = [int(value) for value in np.asarray(surfaces, dtype=int).ravel()]
        source_id = str(_last_value(rays, "SOURCE_ID", ray_index, ""))
        source_weight = float(_last_value(rays, "SOURCE_WEIGHT", ray_index, 0.0) or 0.0)
        reaches_detector = bool(surface_ids and surface_ids[-1] == image_index)
        print(f"{ray_index} | {source_id} | {surface_ids} | {reaches_detector} | {source_weight:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
