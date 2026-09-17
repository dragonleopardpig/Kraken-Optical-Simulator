"""bugs/0286 option B (flag_20260710_105750/105825): the DEFAULT added LED sits AT the object plane (z=0),
10mm, so it floods a tiny radial blob and the on-sensor map is radial, not the coaxial 2-dark/2-uniform.

This probe tests whether placing the LED as a COAXIAL illuminator on the REAL vendor scene -- beside the
beam-splitter cube, aimed at its 45-deg face so the flood reflects DOWN onto the object, sized large enough
that the 55x55x78 BS CUBE (not the LED) is the limiting aperture -- makes the illumination-on-object (and
hence the 0286 projection onto the sensor) show the 2-sided fold signature: the 55mm fold face foreshortens
to 55*cos45 ~= 39mm at the object (under-fills the fold axis -> 2 dark edges) while the 78mm perp axis
overfills (2 uniform edges).

Geometry (from the scene): object S0 at z=0 (aperture ~16.3mm); BS cube centered ~ (0,0,229.6), 45-deg face
normal (-0.707,0,0.707). Light traveling -x reflects off that face to -z (down to the object): so the LED
sits at +x beside the BS, emitting -x.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_coaxial_placement_probe.py
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
from KrakenOS.UI.services.source_object_coupling import object_illumination_projection_map


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


def _profile(density: np.ndarray) -> str:
    ny, nx = density.shape
    cy, cx = ny // 2, nx // 2
    c = float(density[cy, cx]) or 1.0
    lx = 0.5 * (density[cy, 0] + density[cy, -1]) / c
    ly = 0.5 * (density[0, cx] + density[-1, cx]) / c
    corner = float(np.mean([density[0, 0], density[0, -1], density[-1, 0], density[-1, -1]])) / c
    x_dark, y_dark = lx < 0.85, ly < 0.85
    shape = ("RADIAL (both dark)" if x_dark and y_dark
             else "2-SIDED (fold dark, perp uniform)" if x_dark and not y_dark
             else "2-SIDED (perp dark, fold uniform)" if y_dark and not x_dark
             else "UNIFORM")
    return f"x-edge={lx:.3f} y-edge={ly:.3f} corner={corner:.3f} => {shape}"


def _run(pos, direction, half_fold, half_perp, cone, tag):
    path = Path("attachment/machine_vision_150mm_test.py")
    editor = _load_editor(path)
    # Append a coaxial LED spec directly (mirrors add_illumination_led_source but with our pose/size).
    spec = {
        "source_id": "source:coax-probe",
        "name": "Coaxial probe LED",
        "model": "Random rectangle source",
        "role": "illumination",
        "physical": True,
        "enabled": True,
        "source_x": float(pos[0]), "source_y": float(pos[1]), "source_z": float(pos[2]),
        "source_l": float(direction[0]), "source_m": float(direction[1]), "source_n": float(direction[2]),
        "radius_x": float(half_fold), "radius_y": float(half_perp), "radius": float(max(half_fold, half_perp)),
        "cone_deg": float(cone), "ray_count": 6000, "power": 1.0,
        "wavelength": float(editor._current_wavelength()), "seed": 7,
    }
    editor.layout_scene_source_specs = [spec]
    system, bundle = _trace(editor, path)

    obj_idx = editor._source_object_coupling_object_index()
    obj_r = float(editor.rows[int(obj_idx)].diameter) / 2.0
    records = bundle.get("ray_analysis_records", []) if isinstance(bundle, dict) else []
    # how many source rays actually reach the object surface?
    hits = editor._source_illumination_hit_samples(system, int(obj_idx), ray_records=records)
    n_obj = int(np.asarray(hits.get("x", []), dtype=float).size)

    obj_map = object_illumination_projection_map(
        editor, system, int(obj_idx), ray_records=records, object_radius=obj_r,
    )
    print(f"[{tag}] obj_idx={obj_idx} aperture={obj_r:.1f}mm  rays_on_object={n_obj}")
    if obj_map is None:
        print("    object map = None (too little illumination in aperture)")
    else:
        d = np.asarray(obj_map["density"], dtype=float)
        ext = obj_map.get("extent")
        print(f"    object footprint extent={['%.1f' % v for v in ext]}  grid={d.shape}")
        print(f"    {_profile(d)}")
    spec_out = editor.source_illumination_overlay_spec(system, bundle)
    if spec_out:
        print(f"    SENSOR overlay: fold(x)={float(spec_out.get('x_edge_ratio',-1)):.3f} "
              f"perp(y)={float(spec_out.get('y_edge_ratio',-1)):.3f} "
              f"min={float(spec_out.get('min_relative',-1)):.3f}")
    else:
        print("    SENSOR overlay: None")
    print()


def main() -> int:
    if not Path("attachment/machine_vision_150mm_test.py").exists():
        print("fixture missing")
        return 1
    bs_center = (0.0, 0.0, 229.646)
    # LED beside the BS at +x, aimed -x (reflects off the 45-deg face to -z, down onto the object).
    for dx in (100.0,):
        for (hf, hp) in ((45.0, 45.0), (30.0, 55.0)):
            _run(
                pos=(bs_center[0] + dx, bs_center[1], bs_center[2]),
                direction=(-1.0, 0.0, 0.0),
                half_fold=hf, half_perp=hp, cone=25.0,
                tag=f"dx={dx:.0f} half_fold={hf:.0f} half_perp={hp:.0f}",
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
