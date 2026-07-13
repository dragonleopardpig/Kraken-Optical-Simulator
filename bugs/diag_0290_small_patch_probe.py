"""bugs/0290 -- reproduce flag_20260713_073358 "still a small patch of illumination".

The user's LED glyph (state.json) is BIG (led step bounds x[-55,55] y[-45,45] once the
+22.9 x display offset is removed) and sits near the BS (z[187,263]).  add_illumination_led_source
seats a 10x10 square at (0,0,0)+z, and the placement_offset does NOT feed the trace (proved).

So drive the PRODUCTION overlay for a big LED in several physical placements/aims and report the
coupling internals + overlay, to find which reproduces the small central patch and why.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0290_small_patch_probe.py
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from collections import Counter
from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)
from KrakenOS.UI.services.source_object_coupling import object_plane_illumination_samples

PATH = Path("attachment/machine_vision_150mm_test.py")


def _load_editor():
    info = _load_python_data(PATH)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = PATH
    editor._normalize_special_rows()
    return editor


def _trace(editor):
    system = _build_runtime_system(PATH, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_scene_bundle = bundle
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    return system, bundle


def _spec(ox, oy, oz, dl, dm, dn, rx, ry):
    return {
        "source_id": "source:led-1", "name": "Illumination LED 1",
        "model": "Random rectangle source", "role": "illumination",
        "physical": True, "enabled": True,
        "source_x": ox, "source_y": oy, "source_z": oz,
        "source_l": dl, "source_m": dm, "source_n": dn,
        "radius_x": rx, "radius_y": ry, "radius": max(rx, ry),
        "cone_deg": 30.0, "ray_count": 6000, "power": 1.0, "wavelength": 0.55, "seed": 7,
    }


def run(tag, spec):
    print("=" * 84)
    print(tag)
    print(f"  spec origin=({spec['source_x']},{spec['source_y']},{spec['source_z']}) "
          f"dir=({spec['source_l']},{spec['source_m']},{spec['source_n']}) rx={spec['radius_x']} ry={spec['radius_y']}")
    editor = _load_editor()
    editor.layout_scene_source_specs = [dict(spec)]
    system, bundle = _trace(editor)
    wl = float(editor._current_wavelength())
    obj_idx = int(editor._source_object_coupling_object_index())
    mag = editor._current_finite_paraxial_magnification()
    target = editor._source_illumination_anchor_target(bundle)
    hw, hh = editor._detector_target_half_extent(target)
    print(f"  |m|={abs(mag):.4f}  sensor half={hw:.2f}x{hh:.2f}  imaged-FOV half={hw/abs(mag):.2f}")

    records = editor._coupled_object_illumination_records(system, wl)
    with_poly = sum(1 for r in records if r.get("traced_polyline_world") is not None)
    print(f"  coupled records={len(records)}  with_poly={with_poly}  "
          f"terminations={dict(Counter(str(r.get('termination')) for r in records).most_common(5))}")

    clip = 1.3 * float(np.hypot(hw, hh)) / abs(mag) if mag else None
    samples = object_plane_illumination_samples(
        editor, system, obj_idx, ray_records=records,
        object_plane_z=editor._object_surface_plane_z(obj_idx),
        object_radius=float(editor.rows[obj_idx].diameter) / 2.0,
        clip_radius=clip,
    )
    n = samples["x"].size
    print(f"  object-plane samples n={n} direct={samples['direct_count']} relayed={samples['relayed_count']} (clip r<={clip:.1f})")
    if n:
        print(f"    footprint x=[{samples['x'].min():+.1f},{samples['x'].max():+.1f}] "
              f"y=[{samples['y'].min():+.1f},{samples['y'].max():+.1f}]")

    spec_out = editor.source_illumination_overlay_spec(system, bundle)
    if not spec_out:
        print("  PRODUCTION OVERLAY: None (blank)")
    else:
        print(f"  PRODUCTION OVERLAY dims={spec_out['dims']} fold(x)={spec_out['x_edge_ratio']:.3f} "
              f"perp(y)={spec_out['y_edge_ratio']:.3f} min_rel={spec_out['min_relative']:.3f}")


def main() -> int:
    if not PATH.exists():
        print("fixture missing:", PATH)
        return 1
    # a: default small LED at the object plane (add default) -- known small patch
    run("A default small LED at object plane, +z", _spec(0, 0, 0, 0, 0, 1, 5, 5))
    # b: BIG LED at the object plane, +z
    run("B big LED at object plane, +z", _spec(0, 0, 0, 0, 0, 1, 55, 45))
    # c: BIG LED near BS, aimed +z (toward lens, away from object)
    run("C big LED near BS z=225, +z", _spec(0, 0, 225, 0, 0, 1, 55, 45))
    # d: BIG LED near BS, aimed -z (toward object)
    run("D big LED near BS z=225, -z (toward object)", _spec(0, 0, 225, 0, 0, -1, 55, 45))
    # e: BIG side LED beside BS +x face, aimed -x (0289 scenario A geometry)
    run("E big side LED beside BS, -x (into +x face)", _spec(28.6, 0, 229.646, -1, 0, 0, 37, 27.5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
