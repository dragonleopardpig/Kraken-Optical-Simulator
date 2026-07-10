"""bugs/0286 follow-up (flag_20260710_105750/105825): the user added an LED on the real MV-150 scene and
asked whether the on-sensor heatmap is "supposed to be 2-sided dark / 2-sided uniform" (it draws RADIAL).
Two direct questions: (1) is the LED at the object plane? (2) what is its size?

This probe reproduces on the REAL scene and prints, WITHOUT reading anything off the screenshot:
  * the object (couplable) surface index + its z + aperture radius,
  * the DEFAULT source-panel origin the LED is seated at (add_illumination_led_source uses it),
  * the added LED spec actually appended (z + radius_x/radius_y half-size),
  * the illumination-on-OBJECT footprint shape (center vs fold-axis edge vs perp-axis edge vs corner):
    RADIAL if all four edges are dark; 2-SIDED if only the fold axis is dark and perp stays ~uniform,
  * the PROJECTED on-sensor overlay's fold vs perp edge ratios (what the user sees).

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_led_placement_probe.py
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
from KrakenOS.UI.services.source_object_coupling import (
    object_illumination_projection_map,
    project_object_map_onto_sensor,
)


def _load_editor(path: Path):
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
    editor._normalize_special_rows()
    return editor


def _trace(editor, path):
    system = _build_runtime_system(path, editor.rows)
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


def _grid_profile(density: np.ndarray) -> dict[str, float]:
    """Center vs edge-midpoint vs corner of a peak-normalized [iy, ix] grid."""
    ny, nx = density.shape
    cy, cx = ny // 2, nx // 2
    center = float(density[cy, cx]) or 1.0
    return {
        "center": float(density[cy, cx]),
        "left_x": float(density[cy, 0]) / center,
        "right_x": float(density[cy, -1]) / center,
        "top_y": float(density[0, cx]) / center,
        "bot_y": float(density[-1, cx]) / center,
        "corner": float(np.mean([density[0, 0], density[0, -1], density[-1, 0], density[-1, -1]])) / center,
    }


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1

    editor = _load_editor(path)

    # Question 1 groundwork: object plane + default source origin BEFORE adding the LED.
    origin = editor._current_source_origin()
    direction = editor._current_source_direction()
    src_radius = editor._current_source_radius()
    print("== BEFORE adding LED ==")
    print(f"  default source-panel origin (source_x/y/z_var) = "
          f"({origin[0]:.3f}, {origin[1]:.3f}, {origin[2]:.3f}) mm")
    print(f"  default source direction                       = "
          f"({direction[0]:.3f}, {direction[1]:.3f}, {direction[2]:.3f})")
    print(f"  current source-panel radius (half-size)        = {src_radius}")

    # Add the LED exactly as the browser command does.
    source_id = editor.add_illumination_led_source(record_history=False)
    led = next(
        (s for s in editor._normalize_scene_source_specs(editor.layout_scene_source_specs)
         if str(s.get("source_id")) == source_id),
        None,
    )
    print("\n== the LED that was added ==")
    if led is not None:
        print(f"  model        = {led.get('model')}")
        print(f"  source_z     = {float(led.get('source_z', 0.0)):.3f} mm")
        print(f"  source_x/y   = ({float(led.get('source_x', 0.0)):.3f}, {float(led.get('source_y', 0.0)):.3f}) mm")
        print(f"  radius_x/y   = {float(led.get('radius_x', 0.0)):.3f} x {float(led.get('radius_y', 0.0)):.3f} mm "
              f"(HALF-size => full {2*float(led.get('radius_x', 0.0)):.1f} x {2*float(led.get('radius_y', 0.0)):.1f} mm)")
        print(f"  cone_deg     = {float(led.get('cone_deg', 0.0)):.1f}")

    system, bundle = _trace(editor, path)

    obj_idx = editor._source_object_coupling_object_index()
    print("\n== object (couplable) surface ==")
    print(f"  object_surface_index = {obj_idx}")
    # object plane z + aperture radius from the runtime system
    obj_z = None
    obj_r = None
    try:
        surf = system.SDT[int(obj_idx)]
        obj_z = float(getattr(surf, "Pos3D", [0, 0, 0])[2]) if hasattr(surf, "Pos3D") else None
    except Exception:
        pass
    try:
        obj_r = float(editor.rows[int(obj_idx)].diameter) / 2.0
    except Exception:
        pass
    print(f"  object row diameter/2 (aperture radius) = {obj_r} mm")

    # Bin illumination on the object, characterize the footprint SHAPE.
    records = editor._coupled_object_illumination_records(system, bundle) \
        if hasattr(editor, "_coupled_object_illumination_records") else None
    if records is None:
        # fall back to the live-source records the coupled path would use
        records = bundle.get("ray_analysis_records", []) if isinstance(bundle, dict) else []
    obj_map = object_illumination_projection_map(
        editor, system, int(obj_idx), ray_records=records, object_radius=float(obj_r or 0.0),
    )
    print("\n== illumination-on-OBJECT footprint (peak-normalized) ==")
    if obj_map is None:
        print("  None (no illumination reached the imaged aperture)")
    else:
        density = np.asarray(obj_map["density"], dtype=float)
        prof = _grid_profile(density)
        ext = obj_map.get("extent")
        print(f"  hit_count = {obj_map.get('hit_count')}  grid = {density.shape}  extent = {ext}")
        print(f"  center={prof['center']:.3f}  x-edges L/R={prof['left_x']:.3f}/{prof['right_x']:.3f}  "
              f"y-edges T/B={prof['top_y']:.3f}/{prof['bot_y']:.3f}  corner={prof['corner']:.3f}")
        x_dark = 0.5 * (prof["left_x"] + prof["right_x"]) < 0.85
        y_dark = 0.5 * (prof["top_y"] + prof["bot_y"]) < 0.85
        shape = ("RADIAL (all edges dark)" if x_dark and y_dark
                 else "2-SIDED (one axis dark, other uniform)" if x_dark != y_dark
                 else "UNIFORM (no dark edges)")
        print(f"  => shape: {shape}")

    # The production overlay the user actually sees.
    spec = editor.source_illumination_overlay_spec(system, bundle)
    print("\n== production on-sensor overlay (what the user sees) ==")
    if not spec:
        print("  None")
    else:
        print(f"  dims={spec.get('dims')}  fold(x)={float(spec.get('x_edge_ratio', -1)):.3f}  "
              f"perp(y)={float(spec.get('y_edge_ratio', -1)):.3f}  "
              f"min_rel={float(spec.get('min_relative', -1)):.3f}")
        pts = np.asarray(spec.get("points", []), dtype=float)
        if pts.size:
            print(f"  drawn span = {pts[:,0].max()-pts[:,0].min():.1f} x {pts[:,1].max()-pts[:,1].min():.1f} mm "
                  f"(sensor is 23x23)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
