"""bugs/0286 -- Approach A probe: PROJECT the illumination-on-object map onto the sensor.

The 0286 flag (flag_20260710_085240_847, sibling of the 0285 phantom): on the real vendor scene
`attachment/machine_vision_150mm_test.py` the user marks the beam-splitter face as an illumination
source, switches to Normal-to-Sensor, and the sensor is BLANK.  Root cause (see diag_0286_coupling_repro):
only ~5-14 illumination rays reach the sensor, so the DENSITY heatmap (>=50 hits) can't build, and the
marked-face case is marker-gated off.  The DENSE signal is the illumination landing on the OBJECT plane
(row 0): 18 hits for the marked BS face, 1738 for a physical LED.

Approach A: the lens images the object onto the sensor, so bin the illumination-on-object map and
PROJECT it onto the SENSOR extent (rescale the object-map grid edges to the sensor active area).  This
probe validates that pipeline end-to-end on the REAL scene for both source cases and for a MIRROR object.

    PYVISTA_OFF_SCREEN=true MPLBACKEND=Agg .devenv/state/venv/bin/python bugs/diag_0286_projection_probe.py
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
from KrakenOS.UI.scene_source_analysis import scene_source_spec_is_face_bound_marker
from KrakenOS.UI.services.source_illumination_overlay import build_source_illumination_overlay
from KrakenOS.UI.services.source_object_coupling import object_irradiance_map


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


def _isolated_emission_records(editor, system, wavelength):
    bundles, sources = editor._build_illumination_marker_bundles(wavelength)
    if not bundles:
        return []
    rays_illum = Kos.raykeeper(system)
    editor.__dict__["_force_nonseq_preview_trace"] = True
    prior = getattr(system, "_suppress_illumination_face_absorption", False)
    try:
        system._suppress_illumination_face_absorption = True
        editor._trace_preview_bundles(system, rays_illum, wavelength, bundles, bundle_sources=sources)
    finally:
        editor.__dict__["_force_nonseq_preview_trace"] = False
        system._suppress_illumination_face_absorption = prior
    return editor._isolated_ray_analysis_records(system, rays_illum)


def _object_index(editor):
    """Generalized recognition: Diffuse > Mirror/Object Target > plain sequential Object."""
    from KrakenOS.UI.trace_intent import (
        DIFFUSE_OBJECT_SURFACE,
        DIFFUSE_SCATTER_ADVANCED_ATTR,
        OBJECT_TARGET_SURFACE,
    )

    reflective = None
    plain_object = None
    for index, row in enumerate(list(getattr(editor, "rows", []) or [])):
        surface = str(getattr(row, "surface", "") or "")
        advanced = getattr(row, "advanced", {}) or {}
        advanced = advanced if isinstance(advanced, dict) else {}
        if surface == DIFFUSE_OBJECT_SURFACE or DIFFUSE_SCATTER_ADVANCED_ATTR in advanced:
            return index
        if surface in {"Mirror", OBJECT_TARGET_SURFACE} and reflective is None:
            reflective = index
        if surface == "Object" and plain_object is None:
            plain_object = index
    if reflective is not None:
        return reflective
    return plain_object


def _illum_records(editor, system, wavelength):
    specs = editor._normalize_scene_source_specs(getattr(editor, "layout_scene_source_specs", []) or [])
    def _live(spec):
        return bool(spec.get("enabled", True)) and bool(spec.get("physical", True))
    has_nonmarker = any(_live(s) and not scene_source_spec_is_face_bound_marker(s) for s in specs)
    has_marker = any(_live(s) and scene_source_spec_is_face_bound_marker(s) for s in specs)
    recs = []
    if has_nonmarker:
        recs.extend(editor._collect_ray_analysis_records())
    if has_marker:
        recs.extend(_isolated_emission_records(editor, system, wavelength))
    return recs, has_nonmarker, has_marker


def _sensor_half_extent(editor, target):
    hw = float(getattr(target, "active_width_mm", 0.0) or 0.0) / 2.0
    hh = float(getattr(target, "active_height_mm", 0.0) or 0.0) / 2.0
    if hw > 0.0 and hh > 0.0:
        return hw, hh
    try:
        overrides = editor._camera_detector_active_dims_overrides() or {}
    except Exception:
        overrides = {}
    for attr in ("row_index", "trace_surface"):
        try:
            key = int(getattr(target, attr))
        except Exception:
            continue
        if key in overrides:
            dims = overrides[key]
            return float(dims[0]) / 2.0, float(dims[1]) / 2.0
    return hw, hh


def _project(obj_map, hw, hh):
    density = np.asarray(obj_map["density"], dtype=float)
    ny, nx = density.shape
    return {
        "density": density,
        "x_edges": np.linspace(-hw, hw, nx + 1),
        "y_edges": np.linspace(-hh, hh, ny + 1),
        "extent": [-hw, hw, -hh, hh],
    }


def _report(tag, editor, system, bundle):
    print(f"\n===== {tag} =====")
    wl = editor._current_wavelength()
    obj_idx = _object_index(editor)
    print("object index (generalized):", obj_idx)
    if obj_idx is None:
        print("  NO couplable object -> abort")
        return

    recs, has_nonmarker, has_marker = _illum_records(editor, system, wl)
    print(f"illum records: {len(recs)}  (nonmarker={has_nonmarker} marker={has_marker})")

    obj_map = object_irradiance_map(editor, system, int(obj_idx), ray_records=recs, bins=12)
    if not obj_map:
        print("  object_irradiance_map -> None (no illumination on object)")
        return
    print(f"object map: hits={obj_map['hit_count']} density{np.asarray(obj_map['density']).shape}"
          f" extent={[round(v,1) for v in obj_map['extent']]}")

    target = editor._source_illumination_anchor_target(bundle)
    if target is None:
        print("  NO sensor anchor target -> abort")
        return
    hw, hh = _sensor_half_extent(editor, target)
    tz = float(np.asarray(getattr(target, "center_world", (0, 0, 0))).reshape(-1)[2])
    print(f"sensor anchor: z={tz:.1f} half_extent=({hw:.1f},{hh:.1f})")
    if hw <= 0 or hh <= 0:
        print("  sensor has no active extent -> abort")
        return

    projected = _project(obj_map, hw, hh)
    overlay = build_source_illumination_overlay(
        projected,
        center=np.asarray(getattr(target, "center_world", (0.0, 0.0, 0.0)), dtype=float),
        normal=np.asarray(getattr(target, "normal_world", (0.0, 0.0, 1.0)), dtype=float),
        tangent=np.asarray(getattr(target, "tangent_world", (0.0, 1.0, 0.0)), dtype=float),
        chroma="Mono",
    )
    if overlay is None:
        print("  build_source_illumination_overlay -> None")
        return
    pts = np.asarray(overlay["points"], dtype=float)
    print(f"OVERLAY PRESENT: dims={overlay['dims']} points={pts.shape[0]}")
    print(f"  x_edge_ratio(fold)={overlay['x_edge_ratio']:.2f}  y_edge_ratio(perp)={overlay['y_edge_ratio']:.2f}"
          f"  min_rel={overlay['min_relative']:.2f} max_rel={overlay['max_relative']:.2f}")
    # sanity: the drawn quad must span the SENSOR, not the object/FOV (0275 trap)
    span_x = float(pts[:, 0].max() - pts[:, 0].min()) if pts.size else 0.0
    span_y = float(pts[:, 1].max() - pts[:, 1].min()) if pts.size else 0.0
    print(f"  drawn quad span (world): x={span_x:.1f} y={span_y:.1f}  (sensor ~= {2*hw:.1f} x {2*hh:.1f})")


def main() -> int:
    path = Path("attachment/machine_vision_150mm_test.py")
    if not path.exists():
        print("fixture missing:", path)
        return 1

    # Case A: mark the beam-splitter face as an illumination source.
    editor = _load_editor(path)
    sid = editor.create_illumination_source_at_face(1, face_id="S001/F001", aim="inward")
    print("Case A marked source id:", sid)
    system, bundle = _trace(editor, path)
    _report("Case A: marked BS face S001/F001", editor, system, bundle)

    # Case B: add a physical LED source.
    editor2 = _load_editor(path)
    lid = editor2.add_illumination_led_source()
    print("\nCase B added LED source id:", lid)
    system2, bundle2 = _trace(editor2, path)
    _report("Case B: added physical LED", editor2, system2, bundle2)

    # Case C: LED + make the OBJECT (row 0) a MIRROR (user's request -- specular = sharp dark edges).
    editor3 = _load_editor(path)
    editor3.rows[0].surface = "Mirror"
    lid3 = editor3.add_illumination_led_source()
    print("\nCase C row0->Mirror + LED source id:", lid3, "row0 surface:", editor3.rows[0].surface)
    system3, bundle3 = _trace(editor3, path)
    _report("Case C: Mirror object + LED", editor3, system3, bundle3)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
