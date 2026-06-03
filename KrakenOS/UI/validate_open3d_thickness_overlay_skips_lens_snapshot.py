#!/usr/bin/env python3
"""Image-snapshot regression test for bugs/0009: the persistent thickness
overlay must break around an imported optical lens (measuring the physical gap
on each side) instead of painting one arrow straight through it to the next
analytic surface.

Why a rendered frame and not just a number: the symptom is a rendered one --
"S0 Thickness = 100 mm" drew a single arrow across the lens (flag
``flag_20260603_133340_743``). The span-splitting math is pinned display-free in
``validate_open3d_thickness_overlay_skips_lens``; here we boot the real
inspector, place a tracked prism overlay strictly between Object(z=0) and
Image(z=100), force the side view, and:

  * render the scene with the Thickness dimensions on, then hide only the
    dimension actors (no rebuild, no camera move) and render again, diffing the
    pair to isolate exactly the dimension overlay pixels (the lens body, optical
    axis, surfaces and grid are byte-identical in both frames, so they cancel),
  * project the lens's screen column span and assert the dimension pixels land
    on *both* sides of the lens (the two physical gaps) but the lens's central
    column is essentially clear (the arrow no longer crosses it), and
  * as a sensitivity control, remove the lens and re-render: the dimension then
    legitimately spans the full width and that same central column lights up --
    proving the central window is where a crossing arrow lands and that the fix
    specifically cleared it.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_overlay_skips_lens_snapshot

Exit: 0 = pass, 1 = regression (arrow crosses the lens / a gap missing),
      2 = environment can't render (no Xvfb) or fixture unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)

# Each physical gap (Object->lens, lens->Image) must show an isolated arrow
# spanning at least this many distinct screen columns of its window. The gap
# windows are ~90 cols wide; a fully drawn gap arrow covers ~91 of them, a
# missing gap covers 0. We count columns, not raw pixels, so the metric is
# independent of the thin (~2 px) arrow-shaft height.
MIN_SIDE_COLS = 50
# With the lens present the arrow must NOT cross its interior: the central
# column band carries at most this fraction of the lighter gap's coverage
# (0 columns in practice; a crossing arrow fills the whole ~40-col band).
MAX_CENTER_FRAC = 0.25
# Sensitivity control: with the lens removed the single full-span arrow crosses
# that same central band, which must exceed the split frame's center by this
# factor and clear an absolute column floor -- proof the band detects a crossing.
MIN_CONTROL_RATIO = 3.0
MIN_CONTROL_COLS = 20


def _load_rgb(png_path: "str | Path"):
    from PIL import Image

    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def _changed_mask(arr, baseline):
    return np.abs(arr - baseline).sum(axis=2) > 30


def _force_side_view(inspector) -> None:
    """Look along -X at the scene center (parallel), so world Z maps to the
    horizontal screen axis and the lens occludes a central column band."""
    try:
        center, span = inspector._row_scene_bounds()
    except Exception:
        return
    center = np.asarray(center, dtype=float).reshape(3)
    span = float(span) if np.isfinite(span) and span > 1e-6 else 100.0
    cam = inspector._renderer.GetActiveCamera()
    cam.SetFocalPoint(float(center[0]), float(center[1]), float(center[2]))
    cam.SetPosition(float(center[0] - 4.0 * span), float(center[1]), float(center[2]))
    cam.SetViewUp(0.0, 1.0, 0.0)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(0.62 * span)
    try:
        inspector._renderer.ResetCameraClippingRange()
    except Exception:
        pass


def _world_column(inspector, z: float) -> "float | None":
    try:
        disp = inspector._world_to_display_2d(np.asarray((0.0, 0.0, float(z)), dtype=float))
    except Exception:
        return None
    if disp is None:
        return None
    disp = np.asarray(disp, dtype=float).reshape(-1)
    if disp.size < 2 or not np.all(np.isfinite(disp[:2])):
        return None
    return float(disp[0])  # VTK display x == image column (origin left, not flipped)


def _col_span(mask, lo: float, hi: float) -> int:
    """Number of *distinct* screen columns in [lo, hi) carrying a changed pixel
    -- i.e. how wide a band the isolated arrow paints there. Counting columns
    rather than raw pixels makes the metric independent of the arrow shaft's
    (thin, ~2 px) pixel height, so it stays stable across anti-aliasing."""
    if not np.isfinite(lo) or not np.isfinite(hi):
        return 0
    a, b = (lo, hi) if lo <= hi else (hi, lo)
    cols = np.where(mask)[1].astype(float)
    in_range = cols[(cols >= a) & (cols < b)]
    return int(np.unique(in_range).size)


def _overlay_z_span(inspector) -> "tuple[float, float] | None":
    keys = (inspector._step_actor_map or {}).get("optical", [])
    zmin, zmax = np.inf, -np.inf
    for key in keys:
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        bounds = np.asarray(actor.GetBounds(), dtype=float)
        if bounds.size == 6 and bounds[4] <= bounds[5]:
            zmin = min(zmin, float(bounds[4]))
            zmax = max(zmax, float(bounds[5]))
    if not (np.isfinite(zmin) and np.isfinite(zmax)) or zmax - zmin <= 1e-6:
        return None
    return zmin, zmax


def _deselect_all(app, inspector) -> None:
    try:
        inspector._clear_open3d_selection()
    except Exception:
        pass
    app._selected_step_label = None
    inspector._step_rotation_active_label = None
    inspector._step_carry_active_label = None
    inspector._picked_row_index = None
    inspector._stl_placement_row_index = None
    inspector._row_carry_hold_candidate_index = None


def _enumerate_view_props(renderer) -> list:
    props: list = []
    try:
        coll = renderer.GetViewProps()
        coll.InitTraversal()
        prop = coll.GetNextProp()
        while prop is not None:
            props.append(prop)
            prop = coll.GetNextProp()
    except Exception:
        pass
    return props


def _diff_dimension_pixels(app, inspector, out_dir: Path, tag: str):
    """Isolate the Thickness dimension pixels with *zero* lens interaction.

    The imported lens is translucent (opacity ~0.34). VTK composites translucent
    actors as a set, so hiding any other actor and re-rendering shifts the lens
    body's own pixels -- which contaminates a naive on/off diff exactly where it
    matters most: the central column that sits *inside* the lens (an early
    attempt read ~569 stray px there with no arrow present). So we render the
    dimensions in isolation instead: capture the full scene once for eyeballing,
    then hide *every* view prop for a blank frame, then show *only* the dimension
    *arrow* meshes for a second frame. Diffing those two yields exactly the arrow
    pixels over an identical background, with the lens absent from both -- so it
    cannot pollute the crossing test.

    Only the arrow shafts (``vtkActor`` meshes) are isolated, *not* the framed
    ``gap = .. mm`` labels (``vtkBillboardTextActor3D``): the bug is the
    dimension *line* skipping the lens, and a label box is left-anchored at the
    gap midpoint, so its text legitimately overhangs the lens columns and would
    otherwise be miscounted as a crossing arrow. Both kinds register in
    ``_actor_thickness_dimension_map``; we keep the meshes and drop the
    billboards by ``IsA("vtkActor")``.
    """
    app.show_physical_distances_var.set(True)
    inspector.refresh_from_editor(force_retrace=False)
    _force_side_view(inspector)
    inspector.update_idletasks(); inspector.update()
    full_png = out_dir / f"{tag}_full.png"
    render_window_to_png(inspector, full_png)

    renderer = inspector._renderer
    props = _enumerate_view_props(renderer)
    saved = [(prop, int(prop.GetVisibility())) for prop in props]
    try:
        for prop in props:
            try:
                prop.VisibilityOff()
            except Exception:
                pass
        inspector.update_idletasks(); inspector.update()
        blank_png = out_dir / f"{tag}_blank.png"
        render_window_to_png(inspector, blank_png)
        blank = _load_rgb(blank_png)

        for key in list(getattr(inspector, "_actor_thickness_dimension_map", {}).keys()):
            actor = inspector._actor_by_key.get(key)
            if actor is None:
                continue
            try:
                if not actor.IsA("vtkActor"):  # skip billboard text labels
                    continue
                actor.VisibilityOn()
            except Exception:
                pass
        inspector.update_idletasks(); inspector.update()
        dims_png = out_dir / f"{tag}_dims.png"
        render_window_to_png(inspector, dims_png)
        dims = _load_rgb(dims_png)
    finally:
        for prop, vis in saved:
            try:
                prop.SetVisibility(vis)
            except Exception:
                pass
        inspector.update_idletasks(); inspector.update()

    if dims.shape != blank.shape:
        return None, full_png, dims_png
    return _changed_mask(dims, blank), full_png, dims_png


def _measure(out_dir: Path) -> "tuple[dict | None, str]":
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _import_step, _open_inspector

    if not PRISM_42779_STEP.exists():
        return None, "tracked prism STEP fixture missing"

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)
    try:
        inspector.show_rays_var.set(False)
        inspector.show_rotation_handles_var.set(False)
    except Exception:
        pass

    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    app._sync_table()
    try:
        app.clear_step_imports()
    except Exception:
        pass

    # Place the lens strictly between Object(0) and Image(100): center it on z=50.
    _import_step(app, PRISM_42779_STEP)
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    native = _overlay_z_span(inspector)
    if native is None:
        return None, "optical overlay did not import"
    native_center = 0.5 * (native[0] + native[1])
    app.optical_step_placement_offset_xyz = (0.0, 0.0, 50.0 - native_center)
    app.select_step_component("optical")
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    span = _overlay_z_span(inspector)
    if span is None:
        return None, "optical overlay lost after repositioning"
    lens_zmin, lens_zmax = span

    _deselect_all(app, inspector)

    # --- Scene 1: lens present (the fixed behaviour). -----------------------
    mask, full1, dims1 = _diff_dimension_pixels(app, inspector, out_dir, "lens")
    if mask is None:
        return None, "dimension isolation frame differs in size from blank (lens)"

    c_obj = _world_column(inspector, 0.0)
    c_ln = _world_column(inspector, lens_zmin)
    c_lf = _world_column(inspector, lens_zmax)
    c_img = _world_column(inspector, 100.0)
    if None in (c_obj, c_ln, c_lf, c_img):
        return None, "could not project the surface/lens columns"

    # Order columns left->right and define the windows.
    lo_lens, hi_lens = (c_ln, c_lf) if c_ln <= c_lf else (c_lf, c_ln)
    w = hi_lens - lo_lens
    center_lo = lo_lens + 0.20 * w   # inner 60% of the lens, clear of the faces
    center_hi = hi_lens - 0.20 * w

    left_lo, left_hi = (min(c_obj, lo_lens), max(c_obj, lo_lens))
    right_lo, right_hi = (min(hi_lens, c_img), max(hi_lens, c_img))
    # Trim a few cols off the lens faces so an arrowhead at the face isn't
    # ambiguously attributed to the wrong side.
    pad = max(0.05 * w, 4.0)
    left_window = (left_lo + pad, left_hi - pad)
    right_window = (right_lo + pad, right_hi - pad)

    left_cols = _col_span(mask, *left_window)
    right_cols = _col_span(mask, *right_window)
    center_cols = _col_span(mask, center_lo, center_hi)

    # --- Scene 2: lens removed (sensitivity control). -----------------------
    try:
        app.clear_step_imports()
    except Exception:
        pass
    app.imported_optical_step_path = None
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks()
    mask_ctrl, full2, dims2 = _diff_dimension_pixels(app, inspector, out_dir, "nolens")
    control_center_cols = _col_span(mask_ctrl, center_lo, center_hi) if mask_ctrl is not None else -1

    metrics = {
        "lens_z": (round(lens_zmin, 2), round(lens_zmax, 2)),
        "columns": {
            "object": round(c_obj, 1), "lens_near": round(c_ln, 1),
            "lens_far": round(c_lf, 1), "image": round(c_img, 1),
        },
        "center_window": (round(center_lo, 1), round(center_hi, 1)),
        "left_cols": left_cols,
        "right_cols": right_cols,
        "center_cols": center_cols,
        "control_center_cols": control_center_cols,
        "frames": {
            "lens_full": str(full1), "lens_dims": str(dims1),
            "nolens_full": str(full2), "nolens_dims": str(dims2),
        },
    }
    return metrics, "rendered split (lens present) vs full-span (lens removed) dimension frames"


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_thickness_skip_snapshot"))
    out_dir.mkdir(parents=True, exist_ok=True)

    xvfb_proc, env_err = _ensure_display()
    if env_err is not None:
        print(f"[SKIP] cannot render snapshot: {env_err}")
        return 2
    try:
        metrics, message = _measure(out_dir)
    finally:
        if xvfb_proc is not None:
            xvfb_proc.terminate()
            try:
                xvfb_proc.wait(timeout=5)
            except Exception:
                xvfb_proc.kill()

    if metrics is None:
        print(f"[SKIP] {message}")
        return 2

    print(f"snapshot dir: {out_dir}")
    print(f"  {message}")
    print(f"  lens z span           = {metrics['lens_z']}")
    print(f"  projected columns     = {metrics['columns']}")
    print(f"  center window (cols)  = {metrics['center_window']}")
    print(f"  left  gap arrow cols  = {metrics['left_cols']} (need >= {MIN_SIDE_COLS})")
    print(f"  right gap arrow cols  = {metrics['right_cols']} (need >= {MIN_SIDE_COLS})")
    print(f"  lens center arrow cols= {metrics['center_cols']} (want ~0)")
    print(f"  control center cols   = {metrics['control_center_cols']} (lens removed)")

    failures: list[str] = []
    left_cols = metrics["left_cols"]
    right_cols = metrics["right_cols"]
    center_cols = metrics["center_cols"]
    control = metrics["control_center_cols"]

    if left_cols < MIN_SIDE_COLS or right_cols < MIN_SIDE_COLS:
        failures.append(
            f"a physical gap is missing: left={left_cols}, right={right_cols} arrow cols "
            f"(each needs >= {MIN_SIDE_COLS}); the overlay did not split around the lens"
        )
    lighter_side = min(left_cols, right_cols)
    if center_cols > MAX_CENTER_FRAC * max(lighter_side, 1):
        failures.append(
            f"the dimension arrow still crosses the lens: {center_cols} arrow cols in its "
            f"central band (>{MAX_CENTER_FRAC:.0%} of the {lighter_side}-col lighter gap) "
            "-- bugs/0009 regression"
        )
    if control < MIN_CONTROL_COLS or control < MIN_CONTROL_RATIO * max(center_cols, 1):
        failures.append(
            f"sensitivity control weak: lens-removed center={control} cols vs "
            f"lens-present center={center_cols} cols (need >= {MIN_CONTROL_COLS} and "
            f">= {MIN_CONTROL_RATIO}x): the central band may not detect a crossing arrow"
        )

    if failures:
        print("[FAIL] thickness-overlay-skips-lens snapshot")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] thickness overlay splits into two physical gaps around the lens (no crossing arrow)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
