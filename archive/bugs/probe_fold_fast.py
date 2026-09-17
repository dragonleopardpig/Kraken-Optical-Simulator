"""Fast fold probe: load a layout, cap LED ray_count, trace, and report the footprint at a
few key surfaces (object/diffuse + image). Usage: python bugs/probe_fold_fast.py <module> [rays] [surf,surf,...]
"""
import os
import sys
import importlib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def probe(module_name, rays_cap, surfs):
    layout = importlib.import_module(f"KrakenOS.common_optical_layouts.{module_name}")
    import KrakenOS as Kos
    from KrakenOS.UI.layout_editor import _build_system_from_specs
    from KrakenOS.UI.render_layout_snapshot import _rows_from_layout_info, _snapshot_editor
    from KrakenOS.UI.scene_builder import build_scene_bundle

    settings = dict(layout.SETTINGS)
    settings["scene_sources"] = [dict(s) for s in settings["scene_sources"]]
    cone_override = os.environ.get("PROBE_CONE")
    for s in settings["scene_sources"]:
        s["ray_count"] = rays_cap
        if cone_override is not None:
            s["cone_deg"] = float(cone_override)
    surfaces = [dict(s) for s in layout.SURFACES]
    print(f"== {module_name} ==  rows={len(surfaces)} rays={rays_cap}")

    rows = _rows_from_layout_info({"surfaces": surfaces, "settings": settings})
    editor = _snapshot_editor(rows, settings)
    sources = editor._collect_scene_sources(wavelength=float(settings["wavelength"]))
    for sc in sources:
        print(f"  src model={getattr(sc,'model',None)!r} origin={getattr(sc,'origin',None)} "
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
    recs = editor._ray_analysis_records_for_trace(system=system, rays=rays)
    print(f"  ray records: {len(recs)}")
    if not surfs:
        surfs = list(range(len(rows)))
    for si in surfs:
        try:
            s2 = editor._source_illumination_hit_samples(system, si, ray_records=recs)
            xs = np.asarray(s2.get("x", []), dtype=float)
            ys = np.asarray(s2.get("y", []), dtype=float)
            label = surfaces[si].get("surface")
            if xs.size:
                print(f"  surf {si} ({label}): {xs.size} hits  "
                      f"x[{xs.min():.1f},{xs.max():.1f}] (w={xs.max()-xs.min():.1f})  "
                      f"y[{ys.min():.1f},{ys.max():.1f}] (h={ys.max()-ys.min():.1f})")
            else:
                print(f"  surf {si} ({label}): 0 hits")
        except Exception as exc:
            print(f"  surf {si}: probe raised {exc!r}")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "machine_vision_150mm_coaxial_led_folded"
    rays_cap = int(sys.argv[2]) if len(sys.argv) > 2 else 250
    surfs = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 else []
    try:
        probe(name, rays_cap, surfs)
    except Exception as exc:
        import traceback
        traceback.print_exc()
        print("PROBE FAILED:", repr(exc))
