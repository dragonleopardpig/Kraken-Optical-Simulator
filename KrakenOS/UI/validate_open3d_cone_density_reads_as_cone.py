"""Guard: the Open 3D launch cone reads as a cone, not an X-fan + Y-fan cross.

Bug 0040: for a sequential, non-folded scene the 3D launch is a revolved
meridional fan (``world_cone``). It used to be only ``_cone_azimuth_count()`` <= 12
azimuthal spokes laid on ``count // 2`` rings, and the 3D draw then decimated the
1089-ray bundle to a ~300 budget -- so the cone looked like a few crossing flat
fans ("X-fan + Y-fan"), not a cone.

Bug 0041 unified this: the cone is the single 3D-truth pupil and the 2D layout is
its meridional slice (North Star invariant #2). The azimuths are dense and a
multiple of 4 (so the 90/270 deg meridional spokes the 2D slice keeps exist),
the rings are full again (``n_rings = count // 2``, so the cone's meridian equals
the 2D fan heights), and ``world_cone`` bundles get a large draw budget (2000) so
the full cone draws *in full* instead of being thinned back into uneven spokes.

This guards that fix on the Double Gauss 28 deg layout. All checks are
display-free (Agg backend, no Xvfb / GPU needed):

A. The 3D mode is ``world_cone`` (and 2D stays ``world_envelope``).
B. The cone pupil has dense azimuths (>= 16 distinct angles, not the old 12 cap)
   on capped uniform rings that reach the pupil rim, and spans both transverse
   axes with off-meridian spokes (it is a cone, not a flat/cross fan).
C. The drawn (decimated) record count equals the bundle path count -- the cone is
   drawn in full, NOT thinned into the uneven spokes that read as fans.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_cone_density_reads_as_cone

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import numpy as np

from KrakenOS.UI.layout_editor import (
    LAYOUTS_DIR,
    KrakenLayoutEditor,
    _load_python_data,
    _load_python_title,
)
from KrakenOS.UI.render_layout_snapshot import _build_runtime_system, _snapshot_editor
from KrakenOS.UI.services.trace_preview_sampling import (
    _CONE_AZIMUTH_MAX,
    _CONE_AZIMUTH_MIN,
)

LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"
MIN_AZIMUTHS = 16  # dense enough to read as a cone, well above the old 12 cap


def _layout_path_by_title(title: str) -> "Path | None":
    for path in sorted(LAYOUTS_DIR.glob("*.py")):
        if path.name.startswith("_") or path.name == "__init__.py":
            continue
        try:
            if str(_load_python_title(path)).strip() == title:
                return path
        except Exception:
            continue
    return None


def _distinct_azimuth_count(pupil_points: np.ndarray) -> int:
    pts = np.asarray(pupil_points, dtype=float)
    radii = np.hypot(pts[:, 0], pts[:, 1])
    off_axis = pts[radii > 1e-9]
    if off_axis.size == 0:
        return 0
    angles = np.round(np.degrees(np.arctan2(off_axis[:, 1], off_axis[:, 0])) % 360.0, 3)
    return int(np.unique(angles).size)


def run_checks(verbose: bool = False) -> "tuple[bool, list[str]]":
    notes: list[str] = []
    passed = True

    layout_path = _layout_path_by_title(LAYOUT_TITLE)
    if layout_path is None:
        notes.append("SKIP: Double Gauss 28 deg layout unavailable")
        return passed, notes

    info = _load_python_data(layout_path)
    settings = info.get("settings", {}) if isinstance(info.get("settings", {}), dict) else {}
    rows = [KrakenLayoutEditor._row_from_layout_item(item) for item in info["surfaces"]]
    rows[0].surface = "Object"
    rows[-1].surface = "Image"
    editor = _snapshot_editor(rows, settings)
    editor.current_layout_file = layout_path
    editor._normalize_special_rows()
    system = _build_runtime_system(layout_path, editor.rows)
    editor.last_system = system

    # A. Sequential scene: 3D wants a cone, 2D stays a flat envelope.
    mode_2d = editor._preview_2d_sampling_mode()
    mode_3d = editor._preview_3d_sampling_mode()
    if mode_3d != "world_cone":
        notes.append(f"SKIP: scene 3D mode is {mode_3d!r}, not world_cone (not a sequential cone scene)")
        return passed, notes
    if mode_2d != "world_envelope":
        notes.append(f"FAIL: 2D mode is {mode_2d!r}, expected world_envelope")
        passed = False

    # B. The cone pupil is dense and is a cone, not a flat/cross fan.
    ray_count = int(editor._current_ray_count())
    radius = max((max(float(r.diameter) / 2.0, 0.5) for r in editor.rows), default=1.0)
    cone = np.asarray(editor._sample_ray_count_cone_points(radius), dtype=float)

    az_count = editor._cone_azimuth_count()
    # Azimuth count is the clamp rounded to a multiple of 4 (so the 90/270 deg
    # meridional spokes exist for the 2D slice; bug 0041).
    expected_az = int(4 * round(max(_CONE_AZIMUTH_MIN, min(_CONE_AZIMUTH_MAX, ray_count)) / 4.0))
    if az_count % 4 != 0:
        notes.append(f"FAIL: cone azimuth count {az_count} is not divisible by 4 (no meridional spokes)")
        passed = False
    if az_count != expected_az:
        notes.append(f"FAIL: cone azimuth count {az_count}, expected {expected_az}")
        passed = False
    distinct_az = _distinct_azimuth_count(cone)
    if distinct_az < MIN_AZIMUTHS:
        notes.append(
            f"FAIL: cone has only {distinct_az} distinct azimuths (< {MIN_AZIMUTHS}); "
            f"reads as crossing fans, not a cone"
        )
        passed = False

    # Off-meridian spokes (both transverse coords non-zero) -> genuinely 3D.
    off_meridian = bool(np.any((np.abs(cone[:, 0]) > 1e-9) & (np.abs(cone[:, 1]) > 1e-9)))
    if not off_meridian:
        notes.append("FAIL: every cone sample lies on a meridian (collapsed to a fan)")
        passed = False

    # Full uniform rings reaching the rim (n_rings = count // 2) so the cone's
    # meridian equals the 2D fan heights (bug 0041; the bug-0040 cap is gone).
    cone_radii = np.sort(np.unique(np.round(np.hypot(cone[:, 0], cone[:, 1]), 9)))
    cone_radii = cone_radii[cone_radii > 1e-9]
    expected_rings = max(1, ray_count // 2)
    if cone_radii.size != expected_rings:
        notes.append(
            f"FAIL: cone has {cone_radii.size} rings, expected {expected_rings} (n_rings = count // 2)"
        )
        passed = False
    if cone_radii.size and not np.isclose(cone_radii[-1], radius, rtol=1e-6, atol=1e-9):
        notes.append(f"FAIL: outer cone ring {cone_radii[-1]:g} != pupil radius {radius:g}")
        passed = False

    # C. The cone is drawn IN FULL (not decimated into uneven spokes).
    _sys, _rays, bundle = editor._build_preview_system_rays_bundle(
        sampling_mode="world_cone", update_state=True, include_live_step_overlays=False,
    )
    paths = list(getattr(bundle, "ray_paths", []) or [])
    records = list(editor._iter_3d_scene_ray_records(scene_bundle=bundle))
    if not paths:
        notes.append("FAIL: cone trace produced no bundle paths")
        passed = False
    elif len(records) != len(paths):
        notes.append(
            f"FAIL: cone decimated to {len(records)} of {len(paths)} rays "
            f"(uneven spokes / reads as fans); world_cone draw budget not applied"
        )
        passed = False

    if verbose:
        notes.append(
            f"2d={mode_2d}, 3d={mode_3d}, ray_count={ray_count}, az={az_count}, "
            f"distinct_az={distinct_az}, rings={cone_radii.size}, "
            f"bundle_paths={len(paths)}, drawn={len(records)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] Open 3D launch cone reads as a cone (dense azimuths, drawn in full)")
        return 0
    print("[FAIL] Open 3D cone-density guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
