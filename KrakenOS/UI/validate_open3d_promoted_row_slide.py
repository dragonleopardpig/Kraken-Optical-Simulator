#!/usr/bin/env python3
"""Regression test for bugs/0012: a promoted optical-solid row must slide
smoothly along the optical axis when its Move handle is dragged.

Why it was broken: a promoted optical-solid row forces a full optical retrace on
every Open 3D refresh (`has_promoted_step_optical_solid_rows`), and the
placement-translate drag committed each snap step with a full
`refresh_from_editor`. Measured at ~0.5 s per step, so an interactive drag fired
a ~0.5 s retrace every 18 px -- the slide "computed hard in the background but
never moved" (flag `flag_20260603_171838_255`: 6 move handles render, picked row
1, but the drag is a practical no-op).

The fix moves the row's body actors live with a cheap `_translate_row_actors`
(an `AddPosition`, no retrace) during the drag and defers the single model commit
+ heavy refresh to `_finish_placement_drag`. This test boots the real inspector
(its own Xvfb), promotes the tracked prism to an optical-solid row, runs a
multi-step placement-translate drag, and asserts:

  * during the drag the body **moves live** but the model `desp_z` is **not yet
    committed** (deferred -- so no per-step retrace), and
  * on release the slide is committed (`desp_z` changes by the dragged total)
    and the body slid **rigidly** (zmin and zmax move together) to the same
    place the live preview showed.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_promoted_row_slide

Exit: 0 = pass, 1 = regression, 2 = environment can't render / fixture missing.
"""
from __future__ import annotations

import inspect

import numpy as np

from KrakenOS.UI.validate_open3d_analytic_lens_selection_snapshot import _ensure_display
from KrakenOS.UI.layout_editor import KrakenLayoutEditor, SurfaceRow
from KrakenOS.UI.services.prism_fixtures import PRISM_42779_STEP
from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector, _import_step

TOL = 0.6


def _row_z(insp, ri):
    zmin, zmax = np.inf, -np.inf
    for key in (insp._row_actor_map or {}).get(int(ri), []):
        a = insp._actor_by_key.get(key)
        if a is None:
            continue
        b = np.asarray(a.GetBounds(), dtype=float)
        if b.size == 6 and b[4] <= b[5]:
            zmin = min(zmin, float(b[4])); zmax = max(zmax, float(b[5]))
    return (float(zmin), float(zmax)) if np.isfinite(zmin) else None


def _zhandle_center(insp):
    """Axial centre of the +Z placement move-handle actor (or None)."""
    for k, (ri, ax, dl) in (insp._actor_placement_move_map or {}).items():
        if ax == "z" and float(dl) > 0:
            a = insp._actor_by_key.get(k)
            if a is not None:
                return float(np.asarray(a.GetCenter(), dtype=float)[2])
    return None


def main() -> int:
    if not PRISM_42779_STEP.exists():
        print("SKIP: tracked prism STEP fixture missing")
        return 2
    if not _ensure_display():
        print("SKIP: no usable display (Xvfb) for rendering")
        return 2

    failures: list[str] = []
    app = KrakenLayoutEditor()
    insp = _open_inspector(app)
    app.rows = [
        SurfaceRow(label="0", surface="Object", element="", name="Object", thickness=100.0, diameter=25.0, glass="AIR"),
        SurfaceRow(label="1", surface="Image", element="", name="Image", thickness=0.0, diameter=25.0, glass="AIR"),
    ]
    app._sync_table()
    try:
        app.clear_step_imports()
    except Exception:
        pass
    insp.show_rays_var.set(False)
    insp.show_rotation_handles_var.set(True)

    _import_step(app, PRISM_42779_STEP)
    insp.refresh_from_editor(force_retrace=False); insp.update_idletasks()
    out = app.promote_imported_step_to_optical_solid_row(
        "optical", open_face_editor=False, clear_overlay=True, refresh_open_3d=False
    )
    if not isinstance(out, dict) or out.get("row_index") is None:
        print("SKIP: optical-solid-row promotion did not produce a row")
        return 2
    target = int(out["row_index"])
    insp._placement_handle_selected_row_index = target
    insp._set_row_highlight(target); app._select_table_row(target)
    insp.refresh_from_editor(force_retrace=False); insp.update_idletasks()

    move_map = insp._actor_placement_move_map or {}
    z_steps = [float(dl) for (ri, ax, dl) in move_map.values() if ax == "z" and float(dl) > 0]
    if not z_steps:
        failures.append("no +Z placement move handle on the promoted optical-solid row (cannot slide)")
        z_step = 1.78
    else:
        z_step = z_steps[0]

    # Build the drag state directly (robust -- no pixel-perfect handle pick).
    state = {
        "kind": "translate",
        "row_index": target,
        "axis": "z",
        "signed_step": float(z_step),
        "display_direction": np.asarray((1.0, 0.0), dtype=float),
        "pixel_accumulator": 0.0,
        "applied_steps": 0,
    }
    insp._placement_drag_state = state

    z0 = _row_z(insp, target)
    desp0 = float(getattr(app.rows[target], "desp_z", 0.0))
    h0 = _zhandle_center(insp)

    # Drag: each call crosses one 18 px snap step (dx=20 along +display_direction).
    n_steps = 6
    for _ in range(n_steps):
        insp._apply_placement_drag_motion(20.0, 0.0)
    insp.update_idletasks()

    z_mid = _row_z(insp, target)
    desp_mid = float(getattr(app.rows[target], "desp_z", 0.0))
    pending = float(state.get("pending_translate_mm", 0.0))
    expected = n_steps * z_step
    print(f"during drag: body z {z0} -> {z_mid}, desp_z {desp0:.3f} -> {desp_mid:.3f}, pending {pending:.3f} (expected {expected:.3f})")

    # During the drag the body must move LIVE but the model commit is DEFERRED.
    if z_mid is None or z0 is None or abs(z_mid[0] - z0[0]) < TOL:
        failures.append(f"body did not move live during the drag (z {z0} -> {z_mid})")
    if abs(desp_mid - desp0) > TOL:
        failures.append(
            f"desp_z was committed mid-drag ({desp0:.3f} -> {desp_mid:.3f}); the per-step heavy "
            "retrace is back (bugs/0012 regression)"
        )
    if abs(pending - expected) > TOL:
        failures.append(f"pending translate {pending:.3f} != expected {expected:.3f}")

    # Problem A (20:37): the Move/Rotate handles must track the body during the
    # drag, not stay behind. (Before the handle-move fix the body slid via
    # AddPosition but the gizmo stayed put.)
    h_mid = _zhandle_center(insp)
    body_moved = None if (z_mid is None or z0 is None) else 0.5 * ((z_mid[0] + z_mid[1]) - (z0[0] + z0[1]))
    if h0 is not None and h_mid is not None and body_moved is not None:
        handle_moved = h_mid - h0
        print(f"  handles: z-handle {h0:.3f} -> {h_mid:.3f} (moved {handle_moved:.3f}) vs body moved {body_moved:.3f}")
        if abs(handle_moved - body_moved) > max(TOL, 0.1 * abs(body_moved)):
            failures.append(
                f"placement Move handles did not track the body during the drag "
                f"(handle moved {handle_moved:.3f} vs body {body_moved:.3f}) -- bugs/0012 handle-lag regression"
            )

    # Release -> single commit.
    insp._finish_placement_drag(state)
    insp.update_idletasks()
    z_fin = _row_z(insp, target)
    desp1 = float(getattr(app.rows[target], "desp_z", 0.0))
    print(f"after release: body z -> {z_fin}, desp_z -> {desp1:.3f}")

    if abs((desp1 - desp0) - expected) > TOL:
        failures.append(f"committed desp_z delta {desp1 - desp0:.3f} != dragged total {expected:.3f}")
    if z_fin is not None and z0 is not None:
        dz_min, dz_max = z_fin[0] - z0[0], z_fin[1] - z0[1]
        if abs(dz_min - expected) > TOL or abs(dz_max - expected) > TOL:
            failures.append(f"body did not rigidly slide by {expected:.3f} (zmin {dz_min:.3f}, zmax {dz_max:.3f})")

    # Source-couple the fix: motion uses the cheap live move, finish commits.
    motion_src = inspect.getsource(type(insp)._apply_placement_drag_motion)
    finish_src = inspect.getsource(type(insp)._finish_placement_drag)
    if "_translate_row_actors" not in motion_src or "pending_translate_mm" not in motion_src:
        failures.append("_apply_placement_drag_motion no longer defers the translate (bugs/0012 fix removed)")
    if "_translate_placement_handle_actors" not in motion_src:
        failures.append("_apply_placement_drag_motion no longer moves the handles with the body (bugs/0012 handle-lag fix removed)")
    if "pending_translate_mm" not in finish_src or "_apply_scene_placement_translate_handle" not in finish_src:
        failures.append("_finish_placement_drag no longer commits the deferred translate (bugs/0012 fix removed)")

    if failures:
        print("\nFAIL: bugs/0012 promoted-row slide")
        for f in failures:
            print(f"  ! {f}")
        return 1
    print("\nPASS: promoted optical-solid row slides smoothly (live move, deferred commit)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
