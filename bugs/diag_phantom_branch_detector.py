"""Repro: after adding a physical illumination LED to the MV-150 imaging scene, a phantom
branch-detector plane (Sensor/Image circle) draws beside the BS cube (recording
flag_20260710_085210_625). Dumps the derived detector targets so we can see which arm the
phantom belongs to and whether the trace is a pure illumination flood.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -m bugs.diag_phantom_branch_detector
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
from KrakenOS.UI.scene_builder import ray_paths_have_diffuse_scatter


def _c(target):
    return np.asarray(getattr(target, "center_world", (0.0, 0.0, 0.0)), dtype=float).reshape(-1)[:3]


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()

    sid = editor.add_illumination_led_source()
    print("added source:", sid, "->", [s.get("source_id") for s in editor.layout_scene_source_specs])

    system = _build_runtime_system(path, editor.rows)
    wavelength = editor._current_wavelength()
    rays = Kos.raykeeper(system)
    max_radius = max((max(row.diameter / 2.0, 0.5) for row in editor.rows), default=1.0)
    editor._trace_preview_rays(system, rays, wavelength, max_radius, allow_full_pupil=False)
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()

    bundle = editor._build_scene_bundle(system, rays, max_radius)
    targets = list(getattr(bundle, "targets", []) or [])
    ray_paths = list(getattr(bundle, "ray_paths", []) or [])
    print(f"ray_paths={len(ray_paths)}  diffuse_scatter={ray_paths_have_diffuse_scatter(ray_paths)}")

    print(f"== ALL targets ({len(targets)}) ==")
    for t in targets:
        meta = getattr(t, "metadata", {}) or {}
        c = _c(t)
        print(
            f"  row={getattr(t,'row_index',None)} surf={getattr(t,'surface','')!r} "
            f"is_det={bool(getattr(t,'is_detector',False))} src={meta.get('target_source')!r} "
            f"center=({c[0]:+.1f},{c[1]:+.1f},{c[2]:+.1f}) "
            f"w={float(getattr(t,'active_width_mm',0) or 0):.1f} h={float(getattr(t,'active_height_mm',0) or 0):.1f} "
            f"branch={meta.get('branch_path')!r} focus={meta.get('focus_source')!r} "
            f"draw_suppressed={bool(meta.get('draw_suppressed'))}"
        )

    plane_curves = [c for c in getattr(bundle, "surface_curves", []) if str(getattr(c, "kind", "")) == "image"]
    print(f"image-plane curves drawn: {len(plane_curves)}")

    anchor = editor._source_illumination_anchor_target(bundle)
    if anchor is not None:
        c = _c(anchor)
        print(f"anchor row={getattr(anchor,'row_index',None)} center=({c[0]:+.1f},{c[1]:+.1f},{c[2]:+.1f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
