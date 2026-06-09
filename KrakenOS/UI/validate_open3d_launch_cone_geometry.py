"""Guard: the launch cone is the 3D-truth pupil; the 2D fan is its meridian.

A sequential scene traces ONE revolved launch cone as the 3D-truth pupil. The
2D layout is the X=0 meridional slice of that same cone (North Star invariant
#2), so the cone MUST contain a uniform meridional fan whose heights match the
2D fan. Two requirements follow and are guarded here (bug 0041):
  * full radial rings (``n_rings = count // 2``) so for an odd ray count the
    cone ring radii land exactly on the 2D fan's positive radii, and
  * an azimuth count divisible by 4 so the 90 deg / 270 deg spokes (the rays in
    the YZ meridian) exist -- otherwise the meridional slice would be empty.
Lazily, when no Open 3D inspector is live the 2D pane traces only the cheap
``world_envelope`` fan (its meridional heights still equal the cone spine); when
the inspector opens, the 2D pane switches to ``world_cone`` and shows its slice.

All checks are display-free (no Xvfb / GPU needed):

A. Mode coupling -- with no inspector a sequential scene reports
   ``_preview_2d_sampling_mode()`` == "world_envelope" while
   ``_preview_3d_sampling_mode()`` == "world_cone"; with a live inspector the
   2D mode flips to "world_cone" (it becomes the cone's slice).
B. The 2D fan stays planar -- ``_sample_ray_count_pupil_points`` keeps a zero
   sagittal offset and even gaps along the display-slice meridian.
C. The 3D cone is the revolved fan -- ``_sample_ray_count_cone_points`` adds
   azimuthal spokes (both transverse axes span) on a multiple-of-4 azimuth set,
   and its full ring radii equal the 2D fan's positive radii (uniform gap to the
   pupil rim) so the cone's meridian IS the 2D fan.
D. The cone propagates through the bundle builder -- the cone bundle launch
   directions span BOTH transverse axes, while the flat fan bundle spans only
   the meridian.
E. The cone renders end-to-end -- a traced cone produces one 3D ray record per
   bundle path (parity with the 2D layout), launched from the object centre.
F. Nonsequential / folded scenes keep the flat envelope -- the cone is
   sequential-only, so ``_preview_3d_sampling_mode()`` stays "world_envelope".

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_launch_cone_geometry

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


def _bundle_direction_spans(bundles):
    """Return (max L span, max M span) over the transverse direction columns."""
    l_span = 0.0
    m_span = 0.0
    for bundle in bundles:
        directions = np.column_stack([np.asarray(bundle[idx], dtype=float).reshape(-1) for idx in (3, 4)])
        if directions.size:
            l_span = max(l_span, float(np.ptp(directions[:, 0])))
            m_span = max(m_span, float(np.ptp(directions[:, 1])))
    return l_span, m_span


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    if not LAYOUT.exists():
        notes.append("SKIP: machine-vision layout unavailable")
        return passed, notes

    # Odd ray count: the fan's positive radii land exactly on the cone rings.
    ray_count = 11
    editor, rows, Kos, _build_system_from_specs = _machine_vision_editor("1", str(ray_count))

    # A. Mode coupling on a sequential scene: cheap fan when 3D is closed, and
    # the 2D pane becomes the cone's slice when the inspector is live.
    import types as _types

    mode_2d = editor._preview_2d_sampling_mode()
    mode_3d = editor._preview_3d_sampling_mode()
    if mode_2d != "world_envelope":
        notes.append(f"FAIL: 2D sampling mode {mode_2d!r}, expected 'world_envelope' (flat fan)")
        passed = False
    if mode_3d != "world_cone":
        notes.append(f"FAIL: 3D sampling mode {mode_3d!r}, expected 'world_cone' (revolved cone)")
        passed = False
    editor.__dict__["_three_d_inspector"] = _types.SimpleNamespace(winfo_exists=lambda: True)
    try:
        mode_2d_live = editor._preview_2d_sampling_mode()
    finally:
        editor.__dict__.pop("_three_d_inspector", None)
    if mode_2d_live != "world_cone":
        notes.append(
            f"FAIL: with a live 3D inspector the 2D pane should slice the cone "
            f"(mode {mode_2d_live!r}, expected 'world_cone')"
        )
        passed = False

    radius = max(editor._launch_field_radial_max(), 1.0)

    # B. 2D fan stays planar with even gaps.
    fan = np.asarray(editor._sample_ray_count_pupil_points(radius), dtype=float)
    axis = editor._current_display_slice_axis()
    slice_idx = 0 if axis == "x" else 1
    ortho_idx = 1 - slice_idx
    if fan.shape != (ray_count, 2):
        notes.append(f"FAIL: 2D fan shape {fan.shape}, expected ({ray_count}, 2)")
        passed = False
    elif not np.allclose(fan[:, ortho_idx], 0.0):
        notes.append("FAIL: 2D fan has a non-zero sagittal offset (not planar)")
        passed = False

    # C. 3D cone = revolved fan: azimuthal spread + ring radii match the fan.
    cone = np.asarray(editor._sample_ray_count_cone_points(radius), dtype=float)
    cone_x_span = float(np.ptp(cone[:, 0])) if cone.size else 0.0
    cone_y_span = float(np.ptp(cone[:, 1])) if cone.size else 0.0
    if not (cone_x_span > 1e-9 and cone_y_span > 1e-9):
        notes.append(f"FAIL: cone has no azimuthal spread (x_span={cone_x_span:g}, y_span={cone_y_span:g})")
        passed = False
    # At least one spoke is off the meridian (both transverse coords non-zero).
    off_meridian = np.any((np.abs(cone[:, 0]) > 1e-9) & (np.abs(cone[:, 1]) > 1e-9))
    if not off_meridian:
        notes.append("FAIL: every cone sample lies on a meridian (cone collapsed to a fan)")
        passed = False
    # Center sample present.
    if not np.any(np.all(np.abs(cone) < 1e-9, axis=1)):
        notes.append("FAIL: cone is missing its on-axis centre sample")
        passed = False
    # Azimuth count divisible by 4 so the 90/270 deg meridional spokes exist
    # (the YZ-plane rays the 2D slice keeps). Without this the slice is empty.
    az_count = editor._cone_azimuth_count()
    if az_count % 4 != 0:
        notes.append(f"FAIL: cone azimuth count {az_count} is not divisible by 4 (no meridional spokes)")
        passed = False
    # Full rings (n_rings = count // 2): for an odd ray count the cone ring radii
    # land exactly on the 2D fan's positive radii, so the cone's meridian IS the
    # 2D fan (bug 0041 restored the bug-0034 invariant the bug-0040 cap broke).
    cone_radii = np.sort(np.unique(np.round(np.hypot(cone[:, 0], cone[:, 1]), 9)))
    cone_radii = cone_radii[cone_radii > 1e-9]
    fan_radii = np.sort(np.unique(np.round(np.abs(fan[:, slice_idx]), 9)))
    fan_radii = fan_radii[fan_radii > 1e-9]
    if not (cone_radii.size == fan_radii.size and np.allclose(cone_radii, fan_radii, rtol=1e-6, atol=1e-9)):
        notes.append(
            f"FAIL: cone ring radii {np.round(cone_radii, 4).tolist()} != 2D fan positive radii "
            f"{np.round(fan_radii, 4).tolist()} (the cone meridian must equal the 2D fan)"
        )
        passed = False
    if cone_radii.size and not np.isclose(cone_radii[-1], radius, rtol=1e-6, atol=1e-9):
        notes.append(
            f"FAIL: outer cone ring {cone_radii[-1]:g} != pupil radius {radius:g}"
        )
        passed = False
    # Ring gaps uniform.
    ring_gaps = np.diff(cone_radii)
    if ring_gaps.size and not np.allclose(ring_gaps, ring_gaps[0], rtol=1e-6, atol=1e-9):
        notes.append(f"FAIL: cone ring gaps not uniform: {np.round(ring_gaps, 4).tolist()}")
        passed = False

    # D. Cone propagates through the bundle builder: directions span both axes.
    row_specs = [{k: getattr(r, k) for k in (
        "surface", "name", "rc", "k", "axicon", "diff_ord", "grating_d", "grating_angle", "thickness",
        "diameter", "in_diameter", "drawing", "extra_data", "uda", "advanced", "tilt_x", "tilt_y", "tilt_z",
        "desp_x", "desp_y", "desp_z", "axis_move", "glass")} for r in rows]
    if row_specs and getattr(editor, "metal_catalogs", None):
        row_specs[0]["_metal_catalogs"] = editor.metal_catalogs
    system = _build_system_from_specs(row_specs)
    cone_bundles, _cone_count = editor._build_world_cone_bundles(radius, system=system)
    fan_bundles, _fan_count = editor._build_world_envelope_bundles(radius, system=system)
    cone_l_span, cone_m_span = _bundle_direction_spans(cone_bundles)
    fan_l_span, fan_m_span = _bundle_direction_spans(fan_bundles)
    if not (cone_l_span > 1e-9 and cone_m_span > 1e-9):
        notes.append(
            f"FAIL: cone bundle directions are planar (L_span={cone_l_span:g}, M_span={cone_m_span:g})"
        )
        passed = False
    fan_transverse_axes = int(fan_l_span > 1e-9) + int(fan_m_span > 1e-9)
    if fan_transverse_axes != 1:
        notes.append(
            f"FAIL: flat fan bundle should span exactly one transverse axis, spanned {fan_transverse_axes} "
            f"(L_span={fan_l_span:g}, M_span={fan_m_span:g})"
        )
        passed = False

    # E. The cone renders end-to-end: one 3D record per bundle path, centred.
    wavelength = float(editor._current_wavelength())
    raysk = Kos.raykeeper(system)
    max_radius = max((max(float(r.diameter) / 2.0, 0.5) for r in rows), default=1.0)
    editor._trace_preview_rays(system, raysk, wavelength, max_radius,
                               allow_full_pupil=True, sampling_mode="world_cone")
    editor.last_system = system
    editor.last_rays = raysk
    bundle = editor._build_scene_bundle(system, raysk, max_radius)
    editor._last_scene_bundle = bundle
    paths = list(getattr(bundle, "ray_paths", []) or [])
    records = list(editor._iter_3d_scene_ray_records(raysk, bundle))
    if not paths:
        notes.append("FAIL: cone trace produced no bundle paths")
        passed = False
    if len(records) != len(paths):
        notes.append(f"FAIL: 3D cone records={len(records)} != bundle paths={len(paths)}")
        passed = False
    origins = {tuple(np.round(np.asarray(p.points_world, float)[0, :3], 4)) for p in paths
               if np.asarray(p.points_world, float).ndim == 2 and len(p.points_world)}
    if origins and not all(abs(o[0]) < 1e-3 and abs(o[1]) < 1e-3 for o in origins):
        notes.append(f"FAIL: field=1 cone launch origins not centred: {sorted(origins)}")
        passed = False
    # The traced cone paths spread in both transverse axes downstream.
    path_pts = [np.asarray(p.points_world, float) for p in paths
                if np.asarray(p.points_world, float).ndim == 2 and len(p.points_world) >= 2]
    if path_pts:
        finals = np.asarray([pts[-1, :2] for pts in path_pts], dtype=float)
        if not (float(np.ptp(finals[:, 0])) > 1e-6 and float(np.ptp(finals[:, 1])) > 1e-6):
            notes.append(
                f"FAIL: traced cone is planar downstream (x_span={np.ptp(finals[:, 0]):g}, "
                f"y_span={np.ptp(finals[:, 1]):g})"
            )
            passed = False

    # F. Nonsequential / folded scenes keep the flat envelope (cone is seq-only).
    original = editor._resolved_trace_mode
    try:
        editor._resolved_trace_mode = lambda *a, **k: {"use_nonseq": True}
        if editor._preview_3d_sampling_mode() != "world_envelope":
            notes.append("FAIL: nonsequential scene must keep the flat world envelope in 3D, not the cone")
            passed = False
    finally:
        editor._resolved_trace_mode = original

    if verbose:
        notes.append(
            f"2d={mode_2d}->{mode_2d_live} (inspector live), 3d={mode_3d}; az={az_count}; "
            f"cone rings={np.round(cone_radii, 4).tolist()} == fan radii; "
            f"cone bundle L/M span=({cone_l_span:g},{cone_m_span:g}); "
            f"fan transverse axes={fan_transverse_axes}; 3D records={len(records)} == paths={len(paths)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Open 3D launch cone geometry (2D fan stays flat, 3D revolves into a cone)")
        return 0
    print("[FAIL] Open 3D launch cone geometry guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
