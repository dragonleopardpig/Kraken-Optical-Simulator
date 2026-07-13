"""bugs/0290b -- DEFINITIVE as-file confirmation of flag_20260713_073358 "still a small patch".

Loads the REAL vendor scene unmodified and drives the exact in-app path:
  1. scene_sources:[]  -> overlay must be BLANK (no emitter, no fabrication).
  2. editor.add_illumination_led_source() -> the real default emitter -> overlay must be the SMALL PATCH.
  3. print the physical imported-LED-module world bounds (what a module-derived emitter WOULD be).

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0290b_asfile.py
"""
from __future__ import annotations

import os

os.environ.setdefault("PYVISTA_OFF_SCREEN", "true")
os.environ.setdefault("MPLBACKEND", "Agg")

from pathlib import Path

import numpy as np

import KrakenOS as Kos
from KrakenOS.UI.layout_editor import _load_python_data
from KrakenOS.UI.render_layout_snapshot import (
    _build_runtime_system,
    _rows_from_layout_info,
    _snapshot_editor,
)

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


def _report(tag, editor):
    system, bundle = _trace(editor)
    specs = editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or [])
    print(f"  scene_source_specs: {len(specs)}")
    for s in specs:
        print(f"    - {s.get('source_id')} model={s.get('model')} "
              f"origin=({s.get('source_x')},{s.get('source_y')},{s.get('source_z')}) "
              f"dir=({s.get('source_l')},{s.get('source_m')},{s.get('source_n')}) "
              f"rx={s.get('radius_x')} ry={s.get('radius_y')}")
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

    print("=" * 84)
    print("1. vendor scene AS-FILE (scene_sources:[]) -- expect BLANK")
    print("=" * 84)
    _report("as-file", _load_editor())

    print("=" * 84)
    print("2. vendor scene + add_illumination_led_source() -- the real default -- expect SMALL PATCH")
    print("=" * 84)
    editor = _load_editor()
    sid = editor.add_illumination_led_source(record_history=False)
    print(f"  added: {sid}")
    _report("added-default", editor)

    print("=" * 84)
    print("3. physical imported-LED-module world bounds (module-derived emitter reference)")
    print("=" * 84)
    editor = _load_editor()
    path = getattr(editor, "imported_led_step_path", None)
    print(f"  imported_led_step_path = {path}")
    if path is not None:
        try:
            mesh = editor._transformed_imported_led_step_mesh()
            if mesh is not None:
                b = np.asarray(mesh.bounds, dtype=float)
                print(f"  module world bounds x=[{b[0]:+.1f},{b[1]:+.1f}] "
                      f"y=[{b[2]:+.1f},{b[3]:+.1f}] z=[{b[4]:+.1f},{b[5]:+.1f}]")
                print(f"  => transverse half-extents  x={0.5*(b[1]-b[0]):.1f}  y={0.5*(b[3]-b[2]):.1f}")
                print(f"  => object-facing (min-z) face at z={b[4]:.1f}, centre "
                      f"({0.5*(b[0]+b[1]):+.1f},{0.5*(b[2]+b[3]):+.1f})")
            else:
                print("  (mesh unavailable in snapshot editor)")
        except Exception as exc:
            print(f"  (mesh probe error: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
