#!/usr/bin/env python3
"""Image-snapshot regression test for bugs/0006: a STEP promoted to an
analytic-lens row must keep the same big Move-gizmo translate arrows it had as a
STEP overlay -- they must not shrink to the short scene-grid stub.

Why a rendered frame and not just a number: the symptom the user saw is a
rendered one -- the "big sliding arrow handles become the old short one". The
length contract is pinned display-free in
``validate_open3d_promoted_row_translate_arrow_length``; here we boot the real
inspector, import a lens STEP, and:

  * measure the STEP-overlay translate-arrow length (pre-promotion),
  * promote the STEP to an analytic-lens row,
  * build the row-placement gizmo and measure its translate-arrow length, then
  * assert the row arrow matches the STEP overlay within tolerance (the gizmo
    does not shrink on promotion) and is at least as long as the lens body, and
  * render the gizmo and confirm the arrows actually draw (changed pixels over a
    no-gizmo baseline) -- a length read from actor bounds alone would pass even
    if the arrows were invisible.

Run (boots its own private Xvfb if DISPLAY is unset):
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promoted_row_translate_arrow_length_snapshot

Exit: 0 = pass, 1 = regression (arrows shrank / invisible),
      2 = environment can't render (no Xvfb, no lens fixture).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import (
    _ensure_display,
    render_window_to_png,
)

# The row arrow must match the STEP-overlay arrow within this fraction. They are
# driven by the identical formula on the identical body, so they should be equal
# to floating point; 0.10 is slack for any minor body-bounds drift on promotion.
LENGTH_TOL_FRAC = 0.10
# The built gizmo must change at least this many pixels vs the no-gizmo frame,
# proving the arrows render (post-fix the Ball Lens gizmo changed thousands).
MIN_GIZMO_CHANGED = 200


def _load_rgb(png_path: "str | Path"):
    from PIL import Image

    return np.asarray(Image.open(png_path).convert("RGB")).astype(int)


def _changed_pixels(arr, baseline) -> int:
    return int((np.abs(arr - baseline).sum(axis=2) > 30).sum())


def _max_axis_length(inspector, map_name: str) -> float:
    """Largest single-axis bounding-box span across the actors in a handle map
    (an axis-aligned translate arrow's longest bbox dimension == its length)."""
    handle_map = getattr(inspector, map_name, {}) or {}
    best = 0.0
    for key in handle_map:
        actor = inspector._actor_by_key.get(key)
        if actor is None:
            continue
        try:
            b = np.asarray(actor.GetBounds(), dtype=float).reshape(6)
        except Exception:
            continue
        if b.size != 6 or not np.all(np.isfinite(b)) or b[0] > b[1]:
            continue
        span = max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
        best = max(best, float(span))
    return best


def _measure(out_dir: Path) -> "tuple[dict | None, str]":
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
    from KrakenOS.UI.scene_geometry import ScenePlacement3D
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import (
        _open_inspector,
        _import_step,
        LENS_FIXTURES_CLICK_ONLY,
    )

    fixtures = [f for f in LENS_FIXTURES_CLICK_ONLY if f.get("glass")]
    if not fixtures:
        return None, "no promotable lens STEP fixtures checked out under attachment/Lens/"

    app = KrakenLayoutEditor()
    inspector = _open_inspector(app)
    try:
        inspector.show_rotation_handles_var.set(True)
        inspector.show_rays_var.set(False)
    except Exception:
        pass
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object",
                   thickness=50.0, diameter=12.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image",
                   thickness=0.0, diameter=12.0, glass="AIR"),
    ]
    app._sync_table()

    chosen = None
    step_len = 0.0
    for fixture in fixtures:
        try:
            app.clear_step_imports()
        except Exception:
            pass
        _import_step(app, fixture["step"])
        inspector.refresh_from_editor(force_retrace=False)
        inspector.update_idletasks(); inspector.update()
        step_len = _max_axis_length(inspector, "_actor_step_translate_map")
        if step_len > 0.0:
            chosen = fixture
            break
    if chosen is None:
        return None, "no imported STEP produced STEP-overlay translate handles"

    # Promote the chosen STEP to an analytic-lens row.
    try:
        chain_exit = inspector._chain_exit_direction_from_trace()
    except Exception:
        chain_exit = None
    try:
        outcome = app.promote_imported_step_to_analytic_surfaces(
            "optical", glass_sequence=chosen["glass"], clear_overlay=True,
            refresh_open_3d=False, chain_exit_direction=chain_exit,
        )
    except Exception as exc:
        return None, f"promote raised {exc!r}"
    inspector.refresh_from_editor(force_retrace=False)
    inspector.update_idletasks(); inspector.update()

    std_rows = [i for i, r in enumerate(app.rows) if str(getattr(r, "surface", "")) == "Standard"]
    if not std_rows:
        return None, "promotion produced no Standard rows"
    row = std_rows[0]
    body_extent = inspector._row_display_body_extent(row)

    # No-gizmo baseline (placement handles cleared -- this removes both the
    # rotate and the move/translate placement actors).
    try:
        inspector._remove_placement_rotation_handle_actors()
    except Exception:
        pass
    inspector.render(); inspector.update_idletasks(); inspector.update()
    base_png = out_dir / "promoted_row_no_gizmo.png"
    render_window_to_png(inspector, base_png)
    baseline = _load_rgb(base_png)

    # Build the row-placement gizmo directly (the selection gating is exercised
    # elsewhere; here we isolate the sizing of the functions under change).
    body_center = inspector._row_display_actor_center(row, body_only=False)
    if body_center is None:
        body_center = np.zeros(3, dtype=float)
    body_center = np.asarray(body_center, dtype=float)
    placement = ScenePlacement3D(
        row_index=row, center_world=body_center,
        grid_spacing_mm=10.0, grid_extent_mm=100.0,
    )
    inspector._add_scene_placement_translate_handles(
        placement, center=body_center, spacing=10.0, extent=100.0)
    inspector._add_scene_placement_rotate_handles(
        placement, center=body_center, spacing=10.0, extent=100.0)
    inspector.render(); inspector.update_idletasks(); inspector.update()
    row_len = _max_axis_length(inspector, "_actor_placement_move_map")

    gizmo_png = out_dir / "promoted_row_gizmo.png"
    render_window_to_png(inspector, gizmo_png)
    changed = _changed_pixels(_load_rgb(gizmo_png), baseline)

    metrics = {
        "fixture": chosen["name"],
        "step_overlay_arrow_len": round(step_len, 3),
        "row_placement_arrow_len": round(row_len, 3),
        "body_extent": round(float(body_extent), 3) if body_extent else None,
        "gizmo_changed_px": changed,
        "baseline_png": str(base_png),
        "gizmo_png": str(gizmo_png),
    }
    return metrics, f"measured STEP->row arrow lengths on {chosen['name']}"


def main() -> int:
    out_dir = Path(os.environ.get("KRAKEN_SNAPSHOT_DIR", "/tmp/kraken_promoted_row_handle_snapshot"))
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

    step_len = metrics["step_overlay_arrow_len"]
    row_len = metrics["row_placement_arrow_len"]
    body = metrics["body_extent"]
    print(f"snapshot dir: {out_dir}")
    print(f"  {message}")
    print(f"  STEP overlay arrow length = {step_len}")
    print(f"  row placement arrow length = {row_len}")
    print(f"  body extent               = {body}")
    print(f"  gizmo changed pixels      = {metrics['gizmo_changed_px']} (need > {MIN_GIZMO_CHANGED})")

    failures: list[str] = []
    if row_len <= 0.0:
        failures.append("row placement built no measurable translate arrow")
    elif step_len > 0.0 and abs(row_len - step_len) > LENGTH_TOL_FRAC * step_len:
        failures.append(
            f"row arrow {row_len} differs from STEP overlay {step_len} by more than "
            f"{int(LENGTH_TOL_FRAC * 100)}%: the gizmo shrank on promotion (bugs/0006 regression)"
        )
    if body is not None and row_len < body * 1.0:
        failures.append(
            f"row arrow {row_len} is shorter than the body extent {body}: the arrows no "
            "longer clear the glass"
        )
    if metrics["gizmo_changed_px"] <= MIN_GIZMO_CHANGED:
        failures.append(
            f"gizmo changed only {metrics['gizmo_changed_px']} px (<= {MIN_GIZMO_CHANGED}): the "
            "translate arrows are not visibly rendering"
        )

    if failures:
        print("[FAIL] promoted-row translate-arrow snapshot")
        for item in failures:
            print(f"  - {item}")
        return 1
    print("[PASS] promoted-row Move-gizmo keeps the big STEP-overlay translate arrows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
