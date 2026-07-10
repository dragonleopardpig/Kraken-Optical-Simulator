"""bugs/0289 -- the user's requested experiment: a full 55x74 mm LED attached to the SIDE of the
beam-splitter cube on the REAL vendor scene; do 2 fold-axis dark edges appear on the detector?

Three scenarios, all through the PRODUCTION overlay pipeline (no bespoke math):

  A  bare side LED.  The cube's +x face is authored Absorber/Mechanical (it models the opaque LED
     module), so the flood is eaten at the face -- expect a BLANK overlay.  This is also the answer to
     flag_20260710_205215_159 "why do the purple rays stop at the BS": the beam-splitter REFLECT arm of
     any flood heads +x into that same absorber face.

  B  side LED + that face flipped to Transmit/Port (the LED shines through its own window).  The flood
     refracts in, reflects DOWN off the 45-deg diagonal, exits the bottom face, and the bugs/0288 relay
     lands it on the object plane.  Physics prediction: with no limiting stop between the LED and the
     object (202 mm below), EVERY point of the imaged 39x39 FOV sees the WHOLE 55x74 LED, so the
     illumination is ~UNIFORM -- no fold dark edges (they need an aperture that under-fills).

  C  scenario B + the illuminator's 30x78 exit window (the teaching layout's limiting stop,
     machine_vision_150mm_coaxial_led.py: half_x=15 / half_y=39) inserted 5 mm below the cube.  The
     window under-fills the FOV on the fold axis -> expect the 2 fold-dark edges the user's real 25MP
     image shows.  Inserted AFTER the cube in row index (trace order) and desp_z-shifted below it, so
     the DESCENDING flood is tested against it while the ASCENDING imaging fan (which passes z=197
     before the cube but is traced in index order) is untouched.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0289_side_led_probe.py
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
    _build_system_from_specs,
    _rows_from_layout_info,
    _snapshot_editor,
)
from KrakenOS.UI.services.source_object_coupling import object_plane_illumination_samples

PATH = Path("attachment/machine_vision_150mm_test.py")

# The 55x74 LED flush at the cube's +x face (cube: x +-27.5, y +-39, z 202.1..257.1, centre z 229.646).
# For launch direction (-1, 0, 0) the rectangle-source transverse axes map radius_x -> y, radius_y -> z
# (verified from launch-event spans below).
SIDE_LED = {
    "source_id": "source:side-led", "name": "Side LED 55x74", "model": "Random rectangle source",
    "role": "illumination", "physical": True, "enabled": True,
    "source_x": 28.6, "source_y": 0.0, "source_z": 229.646,
    "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
    "radius_x": 37.0,   # -> y half (74 mm perp)
    "radius_y": 27.5,   # -> z half (55 mm fold, becomes x at the object after the fold)
    "radius": 37.0,
    "cone_deg": 30.0, "ray_count": 24000, "power": 1.0, "wavelength": 0.55, "seed": 7,
}

STOP_ROW = {
    "surface": "Standard",
    "name": "Illuminator exit window 30x78",
    "rc": 0.0, "k": 0.0,
    "thickness": 0.0,
    "diameter": 85.8,
    "tilt_x": 0.0, "tilt_y": 0.0, "tilt_z": 0.0,
    "desp_x": 0.0, "desp_y": 0.0, "desp_z": -60.0,  # cumulative z 257 -> plane at 197 (5 mm under the cube)
    "axis_move": 0.0,
    "glass": "AIR",
    "uda": {"kind": "rectangle", "half_x": 15.0, "half_y": 39.0},
}


def _load_editor(with_stop: bool):
    info = _load_python_data(PATH)
    if with_stop:
        rows_data = list(info.get("rows", []))
        rows_data.insert(2, dict(STOP_ROW))  # after the cube (row 1), before the lens datums
        info = dict(info)
        info["rows"] = rows_data
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = PATH
    editor._normalize_special_rows()
    return editor


def _flip_absorber(editor):
    flipped = []
    for row in editor.rows:
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
                flipped.append(str(face.get("face_id")))
    return flipped


def _build_system(editor):
    """Build from the editor's ROW SPECS (the in-app path). The vendor layout module defines its own
    build_runtime_system(), so render_layout_snapshot._build_runtime_system SHORT-CIRCUITS to it and
    silently ignores every row mutation (face flips, inserted rows) -- in-app the editor always
    rebuilds from specs, so this is what matches the user's session."""
    row_specs = [
        {
            "surface": row.surface, "name": row.name, "rc": row.rc, "k": row.k,
            "axicon": row.axicon, "diff_ord": row.diff_ord, "grating_d": row.grating_d,
            "grating_angle": row.grating_angle, "thickness": row.thickness,
            "diameter": row.diameter, "in_diameter": row.in_diameter, "drawing": row.drawing,
            "extra_data": row.extra_data, "uda": row.uda, "advanced": row.advanced,
            "tilt_x": row.tilt_x, "tilt_y": row.tilt_y, "tilt_z": row.tilt_z,
            "desp_x": row.desp_x, "desp_y": row.desp_y, "desp_z": row.desp_z,
            "axis_move": row.axis_move, "glass": row.glass,
        }
        for row in editor.rows
    ]
    return _build_system_from_specs(row_specs)


def _trace(editor):
    system = _build_system(editor)
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


def _edge_profile(spec):
    rel = np.asarray(spec["relative"], dtype=float)
    nx, ny = spec["dims"]
    grid = rel.reshape(ny, nx)
    cx, cy = nx // 2, ny // 2
    centre = grid[cy, cx] or 1.0
    return {
        "fold_edges(x)": (float(grid[cy, 0]) / centre, float(grid[cy, -1]) / centre),
        "perp_edges(y)": (float(grid[0, cx]) / centre, float(grid[-1, cx]) / centre),
        "corners": float(np.mean([grid[0, 0], grid[0, -1], grid[-1, 0], grid[-1, -1]])) / centre,
    }


def run(tag: str, *, flip: bool, with_stop: bool):
    print("=" * 88)
    print(tag)
    print("=" * 88)
    editor = _load_editor(with_stop)
    if flip:
        print(f"  flipped Absorber->Transmit: {_flip_absorber(editor)}")
    editor.layout_scene_source_specs = [dict(SIDE_LED)]
    system, bundle = _trace(editor)
    wl = float(editor._current_wavelength())

    obj_idx = int(editor._source_object_coupling_object_index())
    mag = editor._current_finite_paraxial_magnification()
    target = editor._source_illumination_anchor_target(bundle)
    hw, hh = editor._detector_target_half_extent(target)
    print(f"  object idx={obj_idx}  |m|={abs(mag):.4f}  sensor half={hw:.2f}x{hh:.2f}  "
          f"imaged-FOV half={hw/abs(mag):.2f}")

    records = editor._coupled_object_illumination_records(system, wl)
    with_poly = sum(1 for r in records if r.get("traced_polyline_world") is not None)
    print(f"  records={len(records)}  with traced_polyline_world={with_poly}")
    print(f"  terminations: {dict(Counter(str(r.get('termination')) for r in records).most_common(6))}")
    if with_stop:
        stop_hits = sum(
            1 for r in records for h in (r.get("hits") or []) if str(h.get("surface")) == "2"
        )
        print(f"  hits recorded ON the stop row (surface 2): {stop_hits}")

    clip = 1.3 * float(np.hypot(hw, hh)) / abs(mag) if mag else None
    samples = object_plane_illumination_samples(
        editor, system, obj_idx, ray_records=records,
        object_plane_z=editor._object_surface_plane_z(obj_idx),
        object_radius=float(editor.rows[obj_idx].diameter) / 2.0,
        clip_radius=clip,
    )
    n = samples["x"].size
    print(f"  object-plane samples: n={n}  direct={samples['direct_count']}  relayed={samples['relayed_count']}"
          f"  (clip r<={clip:.1f})")
    if n:
        print(f"  footprint x=[{samples['x'].min():+.1f},{samples['x'].max():+.1f}] "
              f"y=[{samples['y'].min():+.1f},{samples['y'].max():+.1f}]")

    spec = editor.source_illumination_overlay_spec(system, bundle)
    if not spec:
        print("  PRODUCTION OVERLAY: None (blank sensor)")
        return
    prof = _edge_profile(spec)
    print(f"  PRODUCTION OVERLAY: dims={spec['dims']}  fold(x) edge/centre={spec['x_edge_ratio']:.3f}  "
          f"perp(y)={spec['y_edge_ratio']:.3f}  min_rel={spec['min_relative']:.3f}")
    print(f"    profile: fold edges {prof['fold_edges(x)'][0]:.3f}/{prof['fold_edges(x)'][1]:.3f}  "
          f"perp edges {prof['perp_edges(y)'][0]:.3f}/{prof['perp_edges(y)'][1]:.3f}  "
          f"corners {prof['corners']:.3f}")
    fold_mean = float(np.mean(prof["fold_edges(x)"]))
    perp_mean = float(np.mean(prof["perp_edges(y)"]))
    if fold_mean < 0.85 and perp_mean >= 0.85:
        verdict = "2-SIDED fold-dark (the user's expected pattern)"
    elif fold_mean < 0.85 and perp_mean < 0.85:
        verdict = "dark on ALL edges"
    else:
        verdict = "UNIFORM (no dark edges)"
    print(f"    => {verdict}")


def main() -> int:
    import sys

    if not PATH.exists():
        print("fixture missing:", PATH)
        return 1
    wanted = set(sys.argv[1:]) or {"A", "B", "C"}
    if "A" in wanted:
        run("A: 55x74 side LED, +x face as authored (Absorber/Mechanical)", flip=False, with_stop=False)
    if "B" in wanted:
        run("B: 55x74 side LED, +x face flipped to Transmit (no limiting stop)", flip=True, with_stop=False)
    if "C" in wanted:
        run("C: B + illuminator 30x78 exit window 5 mm under the cube", flip=True, with_stop=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
