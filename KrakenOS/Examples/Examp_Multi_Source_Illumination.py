"""Trace two independent physical illumination sources through one scene.

This example mirrors the UI preset:

    Layouts -> Sources / Illumination -> Multi-Source Illumination Example

The legacy Object row is reference geometry only. Two layout-defined
``SceneSource3D`` records launch from different Y positions and converge toward
the same detector plane. This is the first non-UI-panel multi-source contract:
layouts can declare ``SETTINGS["scene_sources"]`` and the trace/render pipeline
will preserve per-source IDs on every ray.
"""

from __future__ import annotations

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.multi_source_illumination_example import SETTINGS, SURFACES, TITLE
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


def _value(rays, name: str, index: int, default=""):
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
    print("source | model | origin mm | direction | rays | power")
    print("--- | --- | --- | --- | --- | ---")
    for source in sources:
        origin = tuple(float(value) for value in np.asarray(source.origin, dtype=float).reshape(-1)[:3])
        direction = tuple(float(value) for value in np.asarray(source.direction, dtype=float).reshape(-1)[:3])
        print(
            f"{source.source_id} | {source.model} | {origin} | {direction} | "
            f"{source.ray_count} | {source.power}"
        )
    print()
    print("ray | source | surfaces | reaches detector | power/ray")
    print("--- | --- | --- | --- | ---")
    for ray_index, surfaces in enumerate(getattr(rays, "SURFACE", [])):
        surface_ids = [int(value) for value in np.asarray(surfaces, dtype=int).ravel()]
        source_id = str(_value(rays, "SOURCE_ID", ray_index, ""))
        source_weight = float(_value(rays, "SOURCE_WEIGHT", ray_index, 0.0) or 0.0)
        reaches_detector = bool(surface_ids and surface_ids[-1] == image_index)
        print(f"{ray_index} | {source_id} | {surface_ids} | {reaches_detector} | {source_weight:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
