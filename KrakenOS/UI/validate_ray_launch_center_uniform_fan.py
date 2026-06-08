"""Guard: single-field launch centring, uniform meridional ray fan, and
visible clipped rays in Open 3D.

Covers three display-preview contracts (all display-free; no Xvfb needed):

1. Field Samples = 1 launches a single bundle from the object centre (the
   on-axis field point), not the field edge -- ``_sample_field_grid_pairs`` and
   ``_field_cross_pairs_for_world_sections`` return ``[(0.0, 0.0)]``.
2. The ``Ray Count`` pupil for a sequential (non-folded) scene is a uniformly
   spaced fan along the display-slice meridian -- ``_sample_ray_count_pupil_points``
   returns evenly spaced samples on the slice axis with zero sagittal offset.
3. Clipped ("stopped") rays render in Open 3D plainly enough to read against the
   scene -- ``_ray_terminal_3d_style(..., "stopped")`` keeps a non-faint opacity,
   and the 3D ray records include every bundle path (parity with the 2D layout).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_ray_launch_center_uniform_fan

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LAYOUT = PROJECT_ROOT / "KrakenOS" / "common_optical_layouts" / "machine_vision_150mm_datasheet_1x.py"


def _machine_vision_editor(field_count: str, ray_count: str):
    import KrakenOS as Kos
    from KrakenOS.UI.render_layout_snapshot import (
        _load_layout_module, _rows_from_layout_info, _snapshot_editor, _build_system_from_specs,
    )

    module = _load_layout_module(LAYOUT)
    rows = _rows_from_layout_info({"surfaces": list(getattr(module, "SURFACES", []) or [])})
    settings = dict(getattr(module, "SETTINGS", {}) or {})
    settings["field_count"] = str(field_count)
    settings["ray_count"] = str(ray_count)
    settings["show_clipped_rays"] = True
    editor = _snapshot_editor(rows, settings)
    editor._normalize_special_rows()
    return editor, rows, Kos, _build_system_from_specs


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    if not LAYOUT.exists():
        notes.append("SKIP: machine-vision layout unavailable")
        return passed, notes

    editor, rows, Kos, _build_system_from_specs = _machine_vision_editor("1", "15")

    # 1. Field Samples = 1 -> single on-axis (object-centre) field point.
    grid = editor._sample_field_grid_pairs(editor._launch_field_radial_max())
    if grid != [(0.0, 0.0)]:
        notes.append(f"FAIL: field_count=1 grid pairs {grid}, expected [(0.0, 0.0)] (object centre)")
        passed = False
    cross = editor._field_cross_pairs_for_world_sections(editor._current_field_height())
    if cross != [(0.0, 0.0)]:
        notes.append(f"FAIL: field_count=1 cross pairs {cross}, expected [(0.0, 0.0)]")
        passed = False

    # 2. Uniform meridional fan for a sequential scene.
    if not editor._launch_pupil_prefers_meridional_fan():
        notes.append("FAIL: sequential machine-vision scene should prefer the uniform meridional fan")
        passed = False
    radius = max(editor._launch_field_radial_max(), 1.0)
    pupil = np.asarray(editor._sample_ray_count_pupil_points(radius), dtype=float)
    count = int(editor._current_ray_count())
    if pupil.shape != (count, 2):
        notes.append(f"FAIL: pupil shape {pupil.shape}, expected ({count}, 2)")
        passed = False
    else:
        axis = editor._current_display_slice_axis()
        slice_idx = 0 if axis == "x" else 1
        ortho_idx = 1 - slice_idx
        if not np.allclose(pupil[:, ortho_idx], 0.0):
            notes.append(f"FAIL: meridional fan has non-zero sagittal offset on axis {ortho_idx}")
            passed = False
        heights = np.sort(pupil[:, slice_idx])
        gaps = np.diff(heights)
        if gaps.size and not np.allclose(gaps, gaps[0], rtol=1e-6, atol=1e-9):
            notes.append(f"FAIL: meridional fan gaps not uniform: {np.round(gaps, 4).tolist()}")
            passed = False
        if not (np.isclose(heights[0], -radius) and np.isclose(heights[-1], radius)):
            notes.append(f"FAIL: meridional fan does not span [-{radius}, {radius}]: {heights[0]}..{heights[-1]}")
            passed = False

    # A nonsequential / folded scene must keep the area-filling disk (sagittal
    # width preserved for branched paths).
    editor._headless_force_nonseq = True
    try:
        original = editor._resolved_trace_mode
        editor._resolved_trace_mode = lambda *a, **k: {"use_nonseq": True}
        if editor._launch_pupil_prefers_meridional_fan():
            notes.append("FAIL: nonsequential scene must keep the disk, not the meridional fan")
            passed = False
        disk = np.asarray(editor._sample_ray_count_pupil_points(radius), dtype=float)
        if disk.shape[0] >= 3 and np.allclose(disk[:, 0], 0.0):
            notes.append("FAIL: nonseq pupil collapsed to a meridional line (lost sagittal width)")
            passed = False
    finally:
        editor._resolved_trace_mode = original

    # 3. Clipped ("stopped") rays render plainly in Open 3D.
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    style = KrakenLayoutEditor._ray_terminal_3d_style((0.1, 0.8, 0.1), "stopped")
    if float(style.get("line_opacity", 0.0)) < 0.5:
        notes.append(f"FAIL: stopped-ray 3D opacity {style.get('line_opacity')} too faint (need >= 0.5)")
        passed = False
    hit_style = KrakenLayoutEditor._ray_terminal_3d_style((0.1, 0.8, 0.1), "hit_detector")
    if float(style.get("line_opacity", 0.0)) > float(hit_style.get("line_opacity", 1.0)):
        notes.append("FAIL: stopped rays must not be drawn more prominently than detector hits")
        passed = False

    # Parity: every bundle path (incl. clipped) is a 3D ray record.
    row_specs = [{k: getattr(r, k) for k in (
        "surface", "name", "rc", "k", "axicon", "diff_ord", "grating_d", "grating_angle", "thickness",
        "diameter", "in_diameter", "drawing", "extra_data", "uda", "advanced", "tilt_x", "tilt_y", "tilt_z",
        "desp_x", "desp_y", "desp_z", "axis_move", "glass")} for r in rows]
    if row_specs and getattr(editor, "metal_catalogs", None):
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    wavelength = float(editor._current_wavelength())
    raysk = Kos.raykeeper(system)
    max_radius = max((max(float(r.diameter) / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(system, raysk, wavelength, max_radius,
                               allow_full_pupil=True, sampling_mode=editor._preview_3d_sampling_mode())
    editor.last_system = system
    editor.last_rays = raysk
    bundle = editor._build_scene_bundle(system, raysk, max_radius)
    editor._last_scene_bundle = bundle
    paths = list(getattr(bundle, "ray_paths", []) or [])
    records = list(editor._iter_3d_scene_ray_records(raysk, bundle))
    if len(records) != len(paths):
        notes.append(f"FAIL: 3D records={len(records)} != bundle paths={len(paths)} (clipped rays dropped)")
        passed = False
    statuses = {str(rec[3]) for rec in records}
    from KrakenOS.UI.scene_geometry import ray_path_terminal_status_from_events
    bundle_statuses = {ray_path_terminal_status_from_events(p) for p in paths}
    if "stopped" in bundle_statuses and "stopped" not in statuses:
        notes.append("FAIL: bundle has clipped (stopped) rays but the 3D records dropped them")
        passed = False

    # Launch origin is the object centre, not the field edge.
    origins = {tuple(np.round(np.asarray(p.points_world, float)[0, :3], 4)) for p in paths
               if np.asarray(p.points_world, float).ndim == 2 and len(p.points_world)}
    if origins and not all(abs(o[0]) < 1e-3 and abs(o[1]) < 1e-3 for o in origins):
        notes.append(f"FAIL: field=1 launch origins not centred: {sorted(origins)}")
        passed = False

    if verbose:
        notes.append(
            f"field=1 grid={grid}; pupil meridional gaps uniform; "
            f"stopped opacity={style.get('line_opacity')}; "
            f"3D records={len(records)} == paths={len(paths)}; statuses={sorted(statuses)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] ray launch centre + uniform fan + visible clipped rays")
        return 0
    print("[FAIL] ray launch centre / uniform fan / clipped-ray guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
