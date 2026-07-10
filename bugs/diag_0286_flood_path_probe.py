"""bugs/0286 instrumentation -- WHERE does the coaxial LED flood go after we flip the +x absorber to
transmit? The flip-and-resize proposal traces 0 rays onto the object, so dump the actual ray paths:
are the LED flood rays even recorded, which surfaces do they hit, and how far down (-z) do they reach?

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python -u bugs/diag_0286_flood_path_probe.py
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


def _load_editor(path: Path):
    info = _load_python_data(path)
    rows = _rows_from_layout_info(info)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = path
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


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing")
        return 1
    editor = _load_editor(path)
    flipped = _flip_absorber(editor)
    print(f"flipped faces: {flipped}")
    spec = {
        "source_id": "source:coax-probe", "name": "Coaxial probe LED",
        "model": "Random rectangle source", "role": "illumination",
        "physical": True, "enabled": True,
        "source_x": 60.0, "source_y": 0.0, "source_z": 229.646,
        "source_l": -1.0, "source_m": 0.0, "source_n": 0.0,
        "radius_x": 39.0, "radius_y": 27.5, "radius": 39.0,
        "cone_deg": 18.0, "ray_count": 4000, "power": 1.0,
        "wavelength": float(editor._current_wavelength()), "seed": 7,
    }
    editor.layout_scene_source_specs = [spec]

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

    bundle_records = bundle.get("ray_analysis_records", []) if isinstance(bundle, dict) else []
    print(f"bundle['ray_analysis_records'] = {len(bundle_records)}  (empty is expected: source replaces imaging)")
    # CORRECT source: the launched flood rides the collected records (bugs/0286 accessor).
    has_acc = hasattr(editor, "_coupled_object_illumination_records")
    print(f"has _coupled_object_illumination_records = {has_acc}")
    try:
        records = editor._coupled_object_illumination_records(system, float(wavelength))
    except Exception as exc:
        print(f"  accessor raised: {exc!r}")
        records = []
    if not records and hasattr(editor, "_collect_ray_analysis_records"):
        try:
            records = list(editor._collect_ray_analysis_records())
            print(f"  fell back to _collect_ray_analysis_records() = {len(records)}")
        except Exception as exc:
            print(f"  _collect_ray_analysis_records raised: {exc!r}")
    print(f"total coupled records = {len(records)}")
    if records:
        print(f"sample record keys = {sorted(records[0].keys())}")

    # partition source vs imaging
    src = [r for r in records if str(r.get("source_id", "") or "").startswith("source:")]
    print(f"records with source_id 'source:*' = {len(src)}")
    # also try other markers
    kinds = Counter(str(r.get("origin_kind", r.get("ray_kind", r.get("category", "")))) for r in records)
    print(f"record kind histogram = {dict(kinds)}")

    def hits_of(r):
        h = r.get("hits")
        return h if isinstance(h, list) else []

    pool = src if src else records
    print(f"\n--- analyzing {len(pool)} rays ({'source' if src else 'ALL (no source tag found)'}) ---")
    surf_hist = Counter()
    min_z = np.inf
    reached_obj0 = 0
    reached_below_100 = 0
    sample_paths = []
    for r in pool:
        hs = hits_of(r)
        path_seq = []
        for h in hs:
            s = h.get("surface", "")
            try:
                si = int(s)
            except Exception:
                si = None
            z = h.get("z")
            try:
                zf = float(z)
            except Exception:
                zf = None
            if si is not None:
                surf_hist[si] += 1
            if zf is not None:
                min_z = min(min_z, zf)
                if zf < 100:
                    reached_below_100 += 1
            if si == 0:
                reached_obj0 += 1
            path_seq.append(f"{si}@{zf:.0f}" if zf is not None else f"{si}")
        if len(sample_paths) < 12 and path_seq:
            sample_paths.append(" -> ".join(path_seq))

    print(f"surface-hit histogram (surface_index: count) = {dict(sorted(surf_hist.items(), key=lambda kv: kv[0] if isinstance(kv[0], int) else 999))}")
    print(f"min z reached across all hits = {min_z:.1f}")
    print(f"hits recorded on surface 0 (object) = {reached_obj0}")
    print(f"hits recorded below z=100 (near object) = {reached_below_100}")

    # WHERE are the surface-0 hits? (resolve the z-puzzle)
    s0 = []
    for r in pool:
        for h in hits_of(r):
            try:
                if int(h.get("surface", -1)) == 0:
                    s0.append((float(h.get("x")), float(h.get("y")), float(h.get("z"))))
            except Exception:
                pass
    if s0:
        arr = np.asarray(s0, dtype=float)
        print(f"\nsurface-0 hit coords: n={len(s0)}")
        print(f"  x range = [{arr[:,0].min():.1f}, {arr[:,0].max():.1f}]")
        print(f"  y range = [{arr[:,1].min():.1f}, {arr[:,1].max():.1f}]")
        print(f"  z range = [{arr[:,2].min():.1f}, {arr[:,2].max():.1f}]")
        print(f"  sample = {[tuple(round(v,1) for v in row) for row in s0[:6]]}")
    print("\nsample ray paths (surface@z):")
    for p in sample_paths:
        print("  ", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
