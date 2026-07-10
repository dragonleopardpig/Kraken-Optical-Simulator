"""bugs/0286 repro -- Piece 2: the on-detector illumination overlay "shows nothing".

flag_20260710_085240_847 (sibling of the 0285 phantom flag): on the real vendor scene
`attachment/machine_vision_150mm_test.py` the user marks the beam-splitter face as an
illumination source, switches to Normal-to-Sensor, and the sensor is BLANK -- no illumination
heatmap. This script reproduces the two candidate mechanisms end-to-end and prints WHY each
produces nothing, so the fix is grounded in the real scene, not the screenshot.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_coupling_repro.py
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
    editor.last_system = system
    editor.last_rays = rays
    editor._last_preview_trace_signature = editor._preview_trace_signature()
    bundle = editor._build_scene_bundle(system, rays, max_radius)
    return system, bundle


def _report(tag, editor, system, bundle):
    print(f"\n===== {tag} =====")
    specs = editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or [])
    print("scene source specs:", len(specs))
    for s in specs:
        print("   spec:", {k: s.get(k) for k in ("role", "physical", "enabled", "face_anchor_row", "face_anchor_face_id", "surface")})

    obj_idx = editor._source_object_coupling_object_index()
    print("coupling object index:", obj_idx)

    target = editor._source_illumination_anchor_target(bundle)
    def _tsurf(t):
        v = getattr(t, "trace_surface", None)
        if v is None:
            v = getattr(t, "row_index", -1)
        try:
            return int(v)
        except Exception:
            return v
    print("anchor target:", None if target is None else
          (_tsurf(target),
           tuple(round(float(v), 1) for v in np.asarray(getattr(target, "center_world", (0, 0, 0))).reshape(-1)[:3])))
    spec = editor._compute_source_illumination_overlay_spec(system, target) if target is not None else None
    print("density heatmap overlay spec:", "None" if spec is None else "PRESENT")

    try:
        res = editor._illumination_weighted_detector_spot_samples(system, "All paths")
        print("coupling_applied:", res.get("coupling_applied"),
              "coupled_ray_count:", res.get("coupled_ray_count"),
              "matched_ray_count:", res.get("matched_ray_count"),
              "irradiance_hit_count:", res.get("irradiance_hit_count"))
    except Exception as exc:
        print("coupling raised:", repr(exc))

    # how many imaging rays actually reach the detector?
    try:
        records = editor._collect_ray_analysis_records()
        det_hits = 0
        for r in records:
            if editor._surface_index_is_detector(r.get("last_surface")):
                det_hits += 1
        print("imaging records:", len(records), "reaching detector:", det_hits)
    except Exception as exc:
        print("records raised:", repr(exc))

    # Where does the ILLUMINATION land on the OBJECT plane (row 0)?  For the marked-face case the
    # emission is ISOLATED (not in the imaging records), so trace it and bin at row 0.
    try:
        wl = editor._current_wavelength()
        iso = _isolated_emission_records(editor, system, wl)
        s_obj = editor._source_illumination_hit_samples(system, 0, ray_records=iso)
        xs = np.asarray(s_obj.get("x", []), dtype=float)
        print(f"ISOLATED emission records: {len(iso)} -> object(row0) hits: {xs.size}"
              + (f" x[{xs.min():.1f},{xs.max():.1f}]" if xs.size else ""))
        # what does binning the IMAGING records at the object give (what 0274 currently does)?
        s_img = editor._source_illumination_hit_samples(system, 0, ray_records=records)
        xi = np.asarray(s_img.get("x", []), dtype=float)
        print(f"IMAGING records -> object(row0) hits: {xi.size}"
              + (f" x[{xi.min():.1f},{xi.max():.1f}]" if xi.size else ""))
    except Exception as exc:
        print("object-landing probe raised:", repr(exc))


def _isolated_emission_records(editor, system, wavelength):
    """Trace the face-bound illumination markers into an ISOLATED keeper (mirrors
    _compute_illumination_marker_rays_overlay_spec) and return the per-ray records."""
    try:
        bundles, sources = editor._build_illumination_marker_bundles(wavelength)
    except Exception as exc:
        print("  marker bundles raised:", repr(exc))
        return []
    if not bundles:
        print("  no marker bundles")
        return []
    rays_illum = Kos.raykeeper(system)
    editor.__dict__["_force_nonseq_preview_trace"] = True
    prior_suppress = getattr(system, "_suppress_illumination_face_absorption", False)
    try:
        system._suppress_illumination_face_absorption = True
        editor._trace_preview_bundles(system, rays_illum, wavelength, bundles, bundle_sources=sources)
    finally:
        editor.__dict__["_force_nonseq_preview_trace"] = False
        system._suppress_illumination_face_absorption = prior_suppress
    return editor._isolated_ray_analysis_records(system, rays_illum)


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1

    # --- Case A: mark the beam-splitter face as an illumination source (the user's flag) ---
    editor = _load_editor(path)
    sid = editor.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward")
    print("Case A marked source id:", sid)
    system, bundle = _trace(editor, path)
    _report("Case A: marked BS face S001/F001", editor, system, bundle)

    # --- Case B: add a real physical LED source (0284 entry point) ---
    editor2 = _load_editor(path)
    lid = editor2.add_illumination_led_source()
    print("\nCase B added LED source id:", lid)
    system2, bundle2 = _trace(editor2, path)
    _report("Case B: added physical LED", editor2, system2, bundle2)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
