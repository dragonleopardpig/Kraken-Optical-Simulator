"""bugs/0286 follow-up -- test the USER's proposal on the REAL MV-150 scene:
put the illumination LED next to the BS cube's +x "Absorber/Mechanical" face (S001/F002), resize it
to 55x78, then FLIP that face Absorber -> Transmit/Port ("Uncoated"). Question: does the coaxial flood
now enter the cube, reflect off the 45-deg splitter DOWN (-z) onto the object, and show the 2-dark /
2-uniform fold signature -- instead of the 0-rays dead end the absorber caused?

Baseline (flip=False) must reproduce rays_on_object=0 (absorber blocks). The two flipped runs try both
LED axis orderings because the rectangle source's radius_x/radius_y -> world y/z mapping is unknown; we
read which OBJECT axis goes dark to pick the right 55-on-fold / 78-on-perp assignment.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0286_uncoated_face_probe.py
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


def _flip_absorber_to_transmit(editor):
    """Make every Absorber/Mechanical face on a promoted solid a plain Transmit/Port (Uncoated)."""
    flipped = []
    for ri, row in enumerate(editor.rows):
        adv = getattr(row, "advanced", None)
        if not isinstance(adv, dict):
            continue
        meta = adv.get("OpticalSolidFaces")
        if not isinstance(meta, dict):
            continue
        for face in meta.get("faces", []):
            if str(face.get("function", "")).strip() == "Absorber/Mechanical":
                face["function"] = "Transmit/Port"
                face["role"] = "Output"
                flipped.append((ri, str(face.get("face_id")), [round(float(v), 2) for v in face.get("normal", [])]))
    return flipped


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
    shape = ("RADIAL (both axes dark)" if x_dark and y_dark
             else "2-SIDED (x/fold dark, y/perp uniform)" if x_dark and not y_dark
             else "2-SIDED (y/perp dark, x/fold uniform)" if y_dark and not x_dark
             else "UNIFORM (no dark edges)")
    return f"x-edge={lx:.3f} y-edge={ly:.3f} corner={corner:.3f} => {shape}"


def _run(flip, radius_x, radius_y, tag):
    path = Path("attachment/machine_vision_150mm_test.py")
    editor = _load_editor(path)
    flipped = _flip_absorber_to_transmit(editor) if flip else []
    spec = {
        "source_id": "source:coax-probe", "name": "Coaxial probe LED",
        "model": "Random rectangle source", "role": "illumination",
        "physical": True, "enabled": True,
        # just outside the +x cube face (world x=27.5, z=229.646), emitting -x
        "source_x": 60.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": float(radius_x), "radius_y": float(radius_y), "radius": float(max(radius_x, radius_y)),
        "cone_deg": 18.0, "ray_count": 6000, "power": 1.0,
        "wavelength": float(editor._current_wavelength()), "seed": 7,
    }
    editor.layout_scene_source_specs = [spec]
    system, bundle = _trace(editor, path)

    obj_idx = editor._source_object_coupling_object_index()
    obj_r = float(editor.rows[int(obj_idx)].diameter) / 2.0
    # bugs/0286: the launched flood rides the COLLECTED records, not bundle['ray_analysis_records']
    # (which is empty when a physical source replaces the imaging rays).
    try:
        records = editor._coupled_object_illumination_records(system, float(editor._current_wavelength()))
    except Exception:
        records = []
    hits = editor._source_illumination_hit_samples(system, int(obj_idx), ray_records=records)
    n_obj = int(np.asarray(hits.get("x", []), dtype=float).size)

    obj_map = object_illumination_projection_map(
        editor, system, int(obj_idx), ray_records=records, object_radius=obj_r,
    )
    print(f"[{tag}] flip={flip} flipped={[f[1] for f in flipped]} rays_on_object={n_obj}")
    if obj_map is None:
        print("    object map = None (too little illumination in aperture)")
    else:
        d = np.asarray(obj_map["density"], dtype=float)
        ext = obj_map.get("extent")
        print(f"    obj footprint extent={['%.1f' % v for v in ext]}  grid={d.shape}")
        print(f"    {_profile(d)}")
    spec_out = editor.source_illumination_overlay_spec(system, bundle)
    if spec_out:
        print(f"    SENSOR overlay: fold(x)={float(spec_out.get('x_edge_ratio',-1)):.3f} "
              f"perp(y)={float(spec_out.get('y_edge_ratio',-1)):.3f} "
              f"min={float(spec_out.get('min_relative',-1)):.3f}")
    else:
        print("    SENSOR overlay: None")
    print(flush=True)


def main() -> int:
    if not Path("attachment/machine_vision_150mm_test.py").exists():
        print("fixture missing")
        return 1
    _run(flip=False, radius_x=27.5, radius_y=39.0, tag="no-flip 55x78 (baseline)")
    _run(flip=True, radius_x=27.5, radius_y=39.0, tag="FLIP  rx=27.5 ry=39.0")
    _run(flip=True, radius_x=39.0, radius_y=27.5, tag="FLIP  rx=39.0 ry=27.5")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
