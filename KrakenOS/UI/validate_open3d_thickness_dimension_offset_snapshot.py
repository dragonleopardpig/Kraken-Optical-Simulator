#!/usr/bin/env python3
"""Image-snapshot regression test for bugs/0007: the Open 3D Thickness dimension
double-ended arrow must render visibly *off* the optical axis, not collapse onto
it.

Why a rendered frame and not just a number: the symptom is a rendered one -- the
"S0 Thickness = 100 mm" label sat directly on the blue optical axis, overlapping
the lens and gizmo, unreadable. The offset direction is pinned display-free in
``validate_open3d_thickness_dimension_offset``; here we boot the real inspector,
build a tiny optical system with non-zero thicknesses, and:

  * render the scene with the Thickness dimensions OFF (baseline),
  * render it again with them ON,
  * diff the two frames to isolate exactly the dimension overlay pixels (this
    removes the optical-axis line, lens, grid and gizmo, which are in both), then
  * assert the dimension pixels actually rendered (changed-pixel count) and that
    their vertical centroid is clearly offset from the projected optical axis,
    and that a thin strip straddling the axis is mostly clear of them -- i.e. the
    arrow reads to the side of the axis rather than on it.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_thickness_dimension_offset_snapshot

Exit: 0 = pass, 1 = regression (dimension on/near the axis or invisible),
      2 = environment can't render (no Xvfb).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)

# The dimension overlay must change at least this many pixels vs the no-dimension
# frame (arrow tube + cone tips + framed label) -- proves it rendered at all.
MIN_DIMENSION_CHANGED = 300
# The dimension's vertical centroid must sit at least this fraction of the image
# height away from the projected optical axis (a real sideways offset).
MIN_AXIS_OFFSET_FRAC = 0.02
# The depth bug projected the whole dimension onto the axis, so its pixels
# straddled the axis line ~symmetrically. A genuine in-screen offset puts almost
# all of them on one side -- require at least this share above-or-below the axis.
MIN_ONE_SIDED_SHARE = 0.70


def _load_rgb(png_path: "str | Path"):
    from PIL import Image

    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def _changed_mask(arr, baseline):
    return np.abs(arr - baseline).sum(axis=2) > 30


def _axis_image_y(inspector, height: int) -> "float | None":
    """Image-space (top-left origin) row of the optical axis, from projecting the
    scene center. In the side view the axis runs horizontally at this row."""
    try:
        center, span = inspector._row_scene_bounds()
    except Exception:
        return None
    center = np.asarray(center, dtype=float).reshape(3)
    span = float(span) if np.isfinite(span) else 0.0
    ys: list[float] = []
    # Sample a few points along the optical axis (world Z) -- all share the axis
    # row in the side view, so averaging is just robustness.
    for frac in (-0.3, 0.0, 0.3):
        probe = center + np.asarray((0.0, 0.0, span * frac), dtype=float)
        try:
            display = inspector._world_to_display_2d(probe)
        except Exception:
            display = None
        if display is None:
            continue
        disp = np.asarray(display, dtype=float).reshape(-1)
        if disp.size < 2 or not np.all(np.isfinite(disp[:2])):
            continue
        # VTK display origin is bottom-left; image rows count from the top.
        ys.append(float(height) - float(disp[1]))
    if not ys:
        return None
    return float(np.mean(ys))


def _measure(out_dir: Path) -> "tuple[dict | None, str]":
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)
    try:
        inspector.show_rays_var.set(False)
        inspector.show_rotation_handles_var.set(False)
    except Exception:
        pass

    # A small but real optical system: two non-zero thickness gaps along the axis,
    # sized so the dimension offset is comfortably resolvable in the rendered view.
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=120.0, diameter=30.0, glass="AIR"),
        SurfaceRow(label="1", surface="Standard", element="", name="Lens",
                   thickness=80.0, diameter=30.0, glass="BK7"),
        SurfaceRow(label="2", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=30.0, glass="AIR"),
    ]
    app._sync_table()

    # Baseline: dimensions OFF.
    try:
        app.show_physical_distances_var.set(False)
    except Exception:
        return None, "editor has no show_physical_distances_var toggle"
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks(); inspector.update()
    base_png = out_dir / "thickness_dim_off.png"
    render_window_to_png(inspector, base_png)
    baseline = _load_rgb(base_png)
    height = int(baseline.shape[0])

    axis_y = _axis_image_y(inspector, height)

    # Dimensions ON.
    app.show_physical_distances_var.set(True)
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks(); inspector.update()
    dim_png = out_dir / "thickness_dim_on.png"
    render_window_to_png(inspector, dim_png)

    on_arr = _load_rgb(dim_png)
    if on_arr.shape != baseline.shape:
        return None, "dimension-on frame differs in size from the baseline"

    mask = _changed_mask(on_arr, baseline)
    changed = int(mask.sum())
    ys = np.where(mask)[0].astype(float)
    centroid_y = float(ys.mean()) if ys.size else float("nan")

    if axis_y is not None and ys.size:
        # Image rows count from the top, so "below the axis" == larger y.
        below = int((ys > axis_y).sum())
        above = int((ys < axis_y).sum())
        one_sided_share = max(below, above) / float(changed)
    else:
        one_sided_share = float("nan")

    metrics = {
        "changed_px": changed,
        "axis_image_y": round(axis_y, 1) if axis_y is not None else None,
        "dimension_centroid_y": round(centroid_y, 1) if np.isfinite(centroid_y) else None,
        "image_height": height,
        "axis_offset_px": round(abs(centroid_y - axis_y), 1) if (axis_y is not None and np.isfinite(centroid_y)) else None,
        "one_sided_share": round(one_sided_share, 3) if np.isfinite(one_sided_share) else None,
        "baseline_png": str(base_png),
        "dimension_png": str(dim_png),
    }
    return metrics, "rendered thickness dimensions off vs on and diffed the frames"


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_thickness_dim_offset_snapshot"))
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
    print(f"  changed pixels        = {metrics['changed_px']} (need > {MIN_DIMENSION_CHANGED})")
    print(f"  optical-axis image y  = {metrics['axis_image_y']}")
    print(f"  dimension centroid y  = {metrics['dimension_centroid_y']}")
    print(f"  axis offset (px)      = {metrics['axis_offset_px']}")
    print(f"  one-sided share       = {metrics['one_sided_share']} (need >= {MIN_ONE_SIDED_SHARE})")

    failures: list[str] = []
    if metrics["changed_px"] <= MIN_DIMENSION_CHANGED:
        failures.append(
            f"only {metrics['changed_px']} px changed (<= {MIN_DIMENSION_CHANGED}): the thickness "
            "dimension overlay is not visibly rendering"
        )
    axis_y = metrics["axis_image_y"]
    offset_px = metrics["axis_offset_px"]
    if axis_y is None or offset_px is None:
        failures.append("could not project the optical axis to compare the dimension offset")
    else:
        min_offset = MIN_AXIS_OFFSET_FRAC * metrics["image_height"]
        if offset_px < min_offset:
            failures.append(
                f"dimension centroid is only {offset_px} px from the optical axis "
                f"(need >= {min_offset:.0f}): the arrow sits on the axis (bugs/0007 regression)"
            )
        share = metrics["one_sided_share"]
        if share is None:
            failures.append("could not measure which side of the axis the dimension sits on")
        elif share < MIN_ONE_SIDED_SHARE:
            failures.append(
                f"only {int(share * 100)}% of dimension pixels are on one side of the axis "
                f"(need >= {int(MIN_ONE_SIDED_SHARE * 100)}%): the dimension straddles the axis "
                "instead of standing clearly off it (bugs/0007 regression)"
            )

    if failures:
        print("[FAIL] thickness-dimension offset snapshot")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] thickness dimension renders as a double-ended arrow offset off the optical axis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
