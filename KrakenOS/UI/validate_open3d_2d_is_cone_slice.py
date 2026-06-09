"""Guard: the 2D layout is a slice of the ONE traced 3D cone (North Star #2).

Bug 0041 (architectural). North Star invariant #2: "optical elements and ray
tracing are represented in 3D behind the scene; 2D plots are slice/projection
views of traced 3D data, not separate simulations." Previously a sequential
scene traced TWO bundles -- a flat ``world_envelope`` fan for the 2D pane and a
separate ``world_cone`` for Open 3D -- which is exactly the dual-simulation the
invariant forbids, and the two drifted apart (bugs 0034/0038/0040; the 3D
edge-on view stopped matching the 2D fan).

The fix makes the launch cone the single 3D-truth pupil and renders the 2D
layout as the cone's X=0 meridional slice. Lazily: when no Open 3D inspector is
live the 2D pane traces only the cheap fan; when the inspector opens the 2D pane
switches to ``world_cone`` and shows its slice -- the SAME data the 3D draws.

This guards that unification on the Double Gauss 28 deg layout. All checks are
display-free (Agg backend, no Xvfb / GPU):

A. Lazy mode switch -- with no inspector ``_preview_2d_sampling_mode()`` is
   "world_envelope"; with a live inspector it flips to "world_cone".
B. One trace -- ``scene_bundle_for_projection_slice(cone, "YZ")`` is a NON-empty,
   STRICT subset of the cone bundle (every sliced ray_index belongs to the cone;
   fewer paths than the cone). The 2D pane is literally a subset of the 3D data.
C. The slice is genuinely meridional -- every sliced ray stays in X=0 through the
   whole system (max |X| within tolerance), and spans both +Y and -Y (a fan).
D. The slice is the full meridional family -- it keeps more than one field point
   (the off-meridian fields are correctly dropped, the on-axis + off-axis
   meridional fields are kept), and per field the launch heights are uniform.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_2d_is_cone_slice

Exit: 0 = pass (incl. environment skips), 1 = regression.
"""
from __future__ import annotations

import types
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
from KrakenOS.UI.layout_plot_controller import (
    scene_bundle_for_projection_slice,
    scene_bundle_launch_sampling_mode,
)

LAYOUT_TITLE = "Zemax Double Gauss 28 Degree Field"


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


def _paths(bundle) -> list:
    return list(getattr(bundle, "ray_paths", []) or [])


def _ray_index_set(bundle) -> set:
    return {int(getattr(p, "ray_index", -1)) for p in _paths(bundle)}


def _launch_xy(path) -> "tuple[float, float] | None":
    source = np.asarray(getattr(path, "source_position", [np.nan] * 3), dtype=float).reshape(-1)
    if source.size >= 3 and np.all(np.isfinite(source[:3])):
        return float(source[0]), float(source[1])
    pts = np.asarray(getattr(path, "points_world", []), dtype=float)
    if pts.ndim == 2 and pts.shape[0] >= 1 and pts.shape[1] >= 3 and np.all(np.isfinite(pts[0, :3])):
        return float(pts[0, 0]), float(pts[0, 1])
    return None


def _max_abs_x(path) -> float:
    pts = np.asarray(getattr(path, "points_world", []), dtype=float)
    if pts.ndim != 2 or pts.shape[0] < 1 or pts.shape[1] < 1:
        return float("inf")
    col = pts[:, 0]
    finite = col[np.isfinite(col)]
    return float(np.max(np.abs(finite))) if finite.size else float("inf")


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
    editor.last_system = _build_runtime_system(layout_path, editor.rows)

    if editor._preview_3d_sampling_mode() != "world_cone":
        notes.append("SKIP: scene 3D mode is not world_cone (not a sequential cone scene)")
        return passed, notes

    # A. Lazy mode switch.
    mode_closed = editor._preview_2d_sampling_mode()
    if mode_closed != "world_envelope":
        notes.append(f"FAIL: with no inspector 2D mode is {mode_closed!r}, expected world_envelope")
        passed = False
    editor.__dict__["_three_d_inspector"] = types.SimpleNamespace(winfo_exists=lambda: True)
    try:
        mode_open = editor._preview_2d_sampling_mode()
    finally:
        editor.__dict__.pop("_three_d_inspector", None)
    if mode_open != "world_cone":
        notes.append(f"FAIL: with a live inspector 2D mode is {mode_open!r}, expected world_cone")
        passed = False

    # Build the single cone bundle (the 3D truth) and its 2D meridional slice.
    _sys, _rays, cone = editor._build_preview_system_rays_bundle(
        sampling_mode="world_cone", update_state=True, include_live_step_overlays=False,
    )
    if scene_bundle_launch_sampling_mode(cone) != "world_cone":
        notes.append("FAIL: cone bundle did not bake a world_cone launch mode")
        passed = False
    sliced = scene_bundle_for_projection_slice(cone, "YZ")

    cone_paths = _paths(cone)
    slice_paths = _paths(sliced)

    # B. One trace: the 2D slice is a non-empty strict subset of the 3D cone.
    if not cone_paths:
        notes.append("FAIL: cone bundle produced no paths")
        passed = False
    if not slice_paths:
        notes.append("FAIL: cone YZ slice is empty (the 2D pane would fall back to the whole cone)")
        passed = False
    elif len(slice_paths) >= len(cone_paths):
        notes.append(
            f"FAIL: slice ({len(slice_paths)}) is not a strict subset of the cone "
            f"({len(cone_paths)}) -- the 2D pane is not a slice of the 3D data"
        )
        passed = False
    elif not _ray_index_set(sliced).issubset(_ray_index_set(cone)):
        notes.append("FAIL: sliced ray indices are not all present in the cone bundle (separate trace?)")
        passed = False

    # C. The slice is genuinely meridional (X=0) and a two-sided fan.
    tol = 1e-6 * max(1.0, max((_max_abs_x(p) for p in cone_paths), default=1.0))
    off_plane = [p for p in slice_paths if _max_abs_x(p) > max(tol, 1e-6)]
    if off_plane:
        notes.append(f"FAIL: {len(off_plane)} sliced rays leave the X=0 meridian (not a clean slice)")
        passed = False
    launch = [xy for xy in (_launch_xy(p) for p in slice_paths) if xy is not None]
    ys = np.asarray([y for _x, y in launch], dtype=float)
    if ys.size and not (np.any(ys > 1e-9) and np.any(ys < -1e-9)):
        notes.append("FAIL: meridional slice does not span both +Y and -Y (collapsed, not a fan)")
        passed = False

    # D. The slice keeps the full meridional family (more than one field) with
    # uniform per-field launch heights.
    fields = {}
    for path in slice_paths:
        try:
            fi = int(getattr(path, "field_index", 0))
        except Exception:
            fi = 0
        xy = _launch_xy(path)
        if xy is not None:
            fields.setdefault(fi, []).append(round(float(xy[1]), 6))
    if len(fields) < 2:
        notes.append(
            f"FAIL: slice kept only {len(fields)} field(s); the off-axis meridional fields were dropped"
        )
        passed = False
    for fi, heights in fields.items():
        uniq = np.sort(np.unique(np.asarray(heights, dtype=float)))
        gaps = np.diff(uniq)
        if gaps.size and not np.allclose(gaps, gaps[0], rtol=1e-6, atol=1e-9):
            notes.append(f"FAIL: field {fi} meridional heights are not uniform: {uniq.tolist()}")
            passed = False

    if verbose:
        notes.append(
            f"2d closed={mode_closed} -> open={mode_open}; cone paths={len(cone_paths)}, "
            f"slice paths={len(slice_paths)}, slice fields={sorted(fields)}, "
            f"strict_subset={len(slice_paths) < len(cone_paths)}"
        )
    return passed, notes


def main() -> int:
    passed, notes = run_checks(verbose=True)
    for note in notes:
        print(note)
    if passed:
        print("[PASS] 2D layout is a meridional slice of the single 3D launch cone (North Star #2)")
        return 0
    print("[FAIL] 2D-is-cone-slice guard")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
