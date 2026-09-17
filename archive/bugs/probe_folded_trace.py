"""Scratch probe: run a layout module through the real scene-source non-seq trace harness
(mirrors validate_open3d_coaxial_led_dark_edges._trace_fov_hit_samples) and report whether
the folded/branched path reaches the image. Usage: python bugs/probe_folded_trace.py <module>
"""
import os
import sys
import importlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def probe(module_name):
    layout = importlib.import_module(f"KrakenOS.common_optical_layouts.{module_name}")
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    settings = dict(layout.SETTINGS)
    surfaces = [dict(s) for s in layout.SURFACES]
    print(f"== {module_name} ==  rows={len(surfaces)}  trace_mode={settings.get('trace_mode')}")
    for i, s in enumerate(surfaces):
        print(f"  row {i}: surface={s.get('surface'):<16} name={s.get('name','')[:42]!r} glass={s.get('glass')}")

    rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    sources = editor._collect_scene_sources(wavelength=float(settings["wavelength"]))
    print(f"  scene sources collected: {len(sources)}")
    for sc in sources:
        print(f"    src model={getattr(sc,'model',None)!r} origin={getattr(sc,'origin',None)} "
              f"dir={getattr(sc,'direction',None)} rx={getattr(sc,'radius_x',None)} ry={getattr(sc,'radius_y',None)} "
              f"rays={getattr(sc,'ray_count',None)}")
    system = _build_system_from_specs(surfaces)
    rays = Kos.raykeeper(system)
    max_radius = max((max(r.diameter / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(system, rays, float(settings["wavelength"]), max_radius, allow_full_pupil=False)
    bundle = build_scene_bundle(
        rows=rows, system=system, rays=rays, sources=sources,
        field_count=len(sources),
        ray_count_per_field=max((getattr(s, "ray_count", 1) for s in sources), default=1),
    )
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    image_index = len(rows) - 1
    recs = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    print(f"  ray records: {len(recs)}")
    samples = editor._source_illumination_hit_samples(system, image_index, ray_records=recs)
    x = np.asarray(samples.get("x", []), dtype=float)
    y = np.asarray(samples.get("y", []), dtype=float)
    print(f"  IMAGE (row {image_index}) hits: {x.size}")
    if x.size:
        print(f"    x extent [{x.min():.2f}, {x.max():.2f}]  y extent [{y.min():.2f}, {y.max():.2f}]")
    # also probe each surface to see where rays land along the fold
    for si in range(len(rows)):
        try:
            s2 = editor._source_illumination_hit_samples(system, si, ray_records=recs)
            xs = np.asarray(s2.get("x", []), dtype=float)
            ys = np.asarray(s2.get("y", []), dtype=float)
            if xs.size:
                print(f"    surf {si} ({surfaces[si].get('surface')}): {xs.size} hits  "
                      f"x[{xs.min():.1f},{xs.max():.1f}] y[{ys.min():.1f},{ys.max():.1f}]")
        except Exception as exc:
            print(f"    surf {si}: probe raised {exc!r}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "zemax_led_beam_splitter_imaging"
    try:
        probe(name)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("PROBE FAILED:", repr(exc))
