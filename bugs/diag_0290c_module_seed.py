"""bugs/0290c -- end-to-end behaviour of the module-seeded emitter on the REAL vendor scene.

The headless snapshot editor never replays ``imported_led_step_path`` (settings-load path is not
driven), so the module-seed branch is dormant in diag_0290b.  Here we INJECT a synthetic physical LED
module (path + a mesh whose world bounds match the real OPT-CO90 placement: decentred +x, object-facing
face at z~187) so ``add_illumination_led_source`` takes the bugs/0290 module path, then drive the exact
in-app overlay and report what the detector now sees.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0290c_module_seed.py
"""
from __future__ import annotations

import os
import types

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

# Real OPT-CO90 placement (memory: 55x78 LED, moved +22.9 x, object-facing min-z face at z~187).
MODULE_BOUNDS = (1.1, 56.1, -39.0, 39.0, 187.0, 265.0)


def _load_editor():
    info = _load_python_data(PATH)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = PATH
    editor._normalize_special_rows()
    return editor


def _inject_module(editor, bounds=MODULE_BOUNDS):
    editor.imported_led_step_path = "synthetic-OPT-CO90-X.STEP"
    editor._transformed_imported_led_step_mesh = lambda: types.SimpleNamespace(bounds=tuple(bounds))


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
    print(f"[{tag}] scene_source_specs: {len(specs)}")
    for s in specs:
        print(f"    - {s.get('source_id')} origin=({s.get('source_x'):.1f},{s.get('source_y'):.1f},{s.get('source_z'):.1f}) "
              f"dir=({s.get('source_l'):.3f},{s.get('source_m'):.3f},{s.get('source_n'):.3f}) "
              f"rx={s.get('radius_x'):.1f} ry={s.get('radius_y'):.1f}")
    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        print(f"[{tag}] PRODUCTION OVERLAY: None (blank)")
        return None
    rel = np.asarray(spec["relative"], dtype=float)
    lit = float(np.count_nonzero(rel >= 0.5)) / float(rel.size)
    print(f"[{tag}] PRODUCTION OVERLAY dims={spec['dims']} fold(x)={spec['x_edge_ratio']:.3f} "
          f"perp(y)={spec['y_edge_ratio']:.3f} min_rel={spec['min_relative']:.3f} lit>=0.5={lit*100:.0f}%")
    return spec


def main() -> int:
    if not PATH.exists():
        print("fixture missing:", PATH)
        return 1

    print("=" * 84)
    print("A. add_illumination_led_source() with NO module -- panel default -- expect SMALL PATCH")
    print("=" * 84)
    editor = _load_editor()
    editor.add_illumination_led_source(record_history=False)
    _report("no-module", editor)

    print("=" * 84)
    print("B. add_illumination_led_source() WITH synthetic OPT-CO90 module -- bugs/0290 module seed")
    print("=" * 84)
    editor = _load_editor()
    _inject_module(editor)
    seed = editor._illumination_emitter_module_seed()
    print(f"  module seed = {seed}")
    editor.add_illumination_led_source(record_history=False)
    _report("module", editor)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
