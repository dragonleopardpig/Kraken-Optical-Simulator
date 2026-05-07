"""OSRAM Zemax LED source through a beam splitter into an imaging lens.

UI preset:

    Layouts -> Sources / Illumination -> Zemax LED Beam-Splitter Imaging

The Object row is not the launch source in this example.  Rays are sampled from
the OSRAM Zemax ``.DAT`` source rayfile, launched from the top port, reflected by
the 45 degree beam splitter toward a left-side object target, returned
to the splitter, transmitted through the return-path imaging lens, and traced to
the Image plane.

The object target uses the built-in ``Diffuse Object`` Lambertian model with
guided target sampling toward the splitter return aperture.  This keeps the
flow source-driven while preserving the beam-splitter return/transmit physics
and giving the camera branch enough deterministic return rays for detector and
relative-illumination analysis.
"""

from __future__ import annotations

import copy

import numpy as np

import KrakenOS as Kos
from KrakenOS.common_optical_layouts.zemax_led_beam_splitter_imaging import SETTINGS, SURFACES, TITLE
from KrakenOS.UI.layout_editor import _build_system_from_specs
from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor


WAVELENGTH_UM = float(SETTINGS["wavelength"])


def build_system() -> Kos.system:
    return _build_system_from_specs(SURFACES)


def trace_demo(ray_count: int | None = None) -> tuple[Kos.system, Kos.raykeeper]:
    system = build_system()
    settings = copy.deepcopy(SETTINGS)
    if ray_count is not None:
        settings["ray_count"] = str(int(ray_count))
        for source in settings.get("scene_sources", []):
            source["ray_count"] = int(ray_count)
    rows = _rows_from_layout_info({"surfaces": SURFACES, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    bundles, sources = editor._build_scene_source_bundles(WAVELENGTH_UM)
    if not bundles:
        raise RuntimeError("No Zemax LED source bundle was built. Check the rayfile path in SETTINGS['scene_sources'].")

    rays = Kos.raykeeper(system)
    clean = 1
    for bundle, source in zip(bundles, sources):
        metadata = editor._source_metadata_for_bundle(bundle, WAVELENGTH_UM, source=source)
        Kos.NsTraceLoop(*bundle, WAVELENGTH_UM, rays, clean=clean, source_metadata=metadata)
        clean = 0
    return system, rays


def _last_value(rays, name: str, index: int, default=""):
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
                "source": str(_last_value(rays, "SOURCE_NAME", ray_index, "")),
                "path": str(_last_value(rays, "BRANCH_PATH", ray_index, "")),
                "surfaces": [int(value) for value in np.asarray(surfaces, dtype=int).ravel()],
                "power": float(_last_value(rays, "BRANCH_POWER", ray_index, 0.0) or 0.0),
                "top_mm": float(_last_value(rays, "TOP", ray_index, 0.0) or 0.0),
            }
        )
    return records


def _surface_path_text(surfaces: list[int], *, max_items: int = 14) -> str:
    if len(surfaces) <= max_items:
        return str(surfaces)
    head = ", ".join(str(value) for value in surfaces[:max_items])
    return f"[{head}, ... +{len(surfaces) - max_items} more]"


def main() -> int:
    system, rays = trace_demo(ray_count=21)
    object_target_index = 3
    image_index = len(system.SDT) - 1
    print(TITLE)
    print(f"source rayfile = {SETTINGS['scene_sources'][0]['rayfile_path']}")
    print("source origin = (0, 45, 45) mm, direction = (0, -1, 0)")
    print("Object row S0 is reference only; S3 is the left-side Diffuse Object with guided Lambertian scatter.")
    print("ray | source | branch path | surfaces | hits diffuse object | reaches Image | power | TOP mm")
    print("--- | --- | --- | --- | --- | --- | --- | ---")
    for record in summarize_trace(rays):
        hits_object = object_target_index in record["surfaces"]
        reaches_image = bool(record["surfaces"] and int(record["surfaces"][-1]) == image_index)
        print(
            f"{record['ray']} | {record['source']} | {record['path']} | {_surface_path_text(record['surfaces'])} | "
            f"{hits_object} | {reaches_image} | {record['power']:.6g} | {record['top_mm']:.6g}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
