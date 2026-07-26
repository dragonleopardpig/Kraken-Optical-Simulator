#!/usr/bin/env python3
"""bugs/0436 — rubber-band select + snap fixes (flags 20260726_095147 + _095224).

Reproduced defects (recording_20260726_095434):
  1. `_complete_rubber_band_select` synced the table via `_select_table_row(rows[0])`,
     whose tail `_sync_surface_selection` re-highlighted ONE row -> the plural
     multi-selection collapsed to {min} (picked=[3] while armed), so the chained
     "Rubber-Band Select + Snap to Axis..." snapped a single row.
  2. A 1-row selection has no inferable direction: snap_rows_to_axis teleported the
     lens front datum exactly onto the split-axis branch point (0,0,37.3), read by
     the user as "snapped to the first optical axis instead".
  3. The Image row has no row actor: its selection was invisible and the camera STEP
     cue was wiped by `_clear_open3d_selection` at arm time ("camera not selected").
  4. Snapping a partial slice of the lens surrogate tore the datums from the barrel.

Run:  DISPLAY=:N .devenv/state/venv/bin/python bugs/probe_0436_rubber_band_snap.py
(Needs an X display; start `Xvfb :N -screen 0 1600x1000x24` when headless.)
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
SCENE = REPO / "attachment" / "machine_vision_AZ85_RA_Mirror.py"


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.open3d_inspector import (
        expand_rows_to_lens_block,
        rubber_band_rows_in_rect,
    )

    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        print(("ok  " if ok else "XX  ") + name + ("  " + detail if detail else ""))
        if not ok:
            failures.append(name)

    if not SCENE.exists():
        print("SKIP: scene missing:", SCENE)
        return 0

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        insp.geometry("1280x860+80+60")
        insp.deiconify()
        insp.lift()
        insp.update_idletasks()
        insp.update()
        time.sleep(0.2)
        insp.update()

        pts = insp._rubber_band_display_points()
        good = {i: p for i, p in pts.items() if p is not None}
        image_row = next(
            (i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"),
            None,
        )
        check("image row is a rubber-band candidate with a display point", image_row in good, str(good.get(image_row)))

        xs = [p[0] for p in good.values()]
        ys = [p[1] for p in good.values()]
        rect_a = (min(xs) - 5, min(ys) - 5)
        rect_b = (max(xs) + 5, max(ys) + 5)
        all_rows = rubber_band_rows_in_rect(pts, rect_a, rect_b)
        check("covering rect selects every candidate", all_rows == sorted(good), str(all_rows))

        # 1: the collapse is fixed -- table sync + event drain keep the full set.
        insp._set_row_highlights(all_rows)
        insp._sync_table_to_selection(all_rows)
        app.update_idletasks()
        app.update()
        check(
            "multi-selection survives the table sync (was: collapse to {min})",
            sorted(insp._picked_row_indices) == all_rows,
            str(sorted(insp._picked_row_indices)),
        )
        check("suppression flag released after drain", not getattr(app, "_suppress_3d_row_selection_sync", False))

        # chained variant arms with the FULL set (synthetic corners; conversion
        # bypassed so the rect is already in display space).
        insp._rubber_band_select_mode = True
        insp._rubber_band_chain_snap = True
        orig_conv = insp._tk_xy_to_vtk_display_xy
        insp._tk_xy_to_vtk_display_xy = lambda xy: xy
        try:
            insp._complete_rubber_band_select(rect_a, rect_b)
        finally:
            insp._tk_xy_to_vtk_display_xy = orig_conv
        app.update_idletasks()
        app.update()
        armed_sel = sorted(int(i) for i in (getattr(insp, "_snap_rows_selection", []) or []))
        check("chained variant arms the snap", bool(getattr(insp, "_snap_rows_to_axis_pick_mode", False)))
        check("armed selection is the full set", armed_sel == all_rows, str(armed_sel))
        check(
            "picked rows stay the full set at armed state",
            sorted(insp._picked_row_indices) == all_rows,
            str(sorted(insp._picked_row_indices)),
        )
        labels = insp._selection_step_highlight_labels(all_rows)
        check("armed STEP cue lights lens + camera bodies", labels == ["lens", "camera"], str(labels))

        # 2 (semantics updated by bugs/0439): a 1-row snap is TRANSLATE-ONLY -- the arm
        # succeeds with the single-element status, the apply slides the row onto the
        # axis at the click point KEEPING its orientation (no branch-point teleport,
        # which was the 0436 degenerate rotation this section originally guarded).
        insp._snap_rows_to_axis_pick_mode = False
        insp._snap_rows_selection = []
        insp._arm_snap_to_axis([8], "selected")
        check(
            "1-row arm accepted as translate-only with guidance",
            bool(getattr(insp, "_snap_rows_to_axis_pick_mode", False))
            and "single element" in insp.status_var.get(),
            insp.status_var.get()[:70],
        )
        row8 = app.rows[8]
        tilts_before = (float(row8.tilt_x), float(row8.tilt_y), float(row8.tilt_z))
        others_before = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for i, r in enumerate(app.rows) if i != 8
        ]
        insp._apply_snap_rows_to_axis(
            {
                "axis_id": "axis:global:split",
                "points": np.array([(0.0, 0.0, 37.3), (100.0, 0.0, 37.3)]),
                "picked_world": np.array([60.0, 0.0, 37.3]),
            }
        )
        z_now = app._row_z_positions()
        center8 = np.array(
            [float(row8.desp_x), float(row8.desp_y), float(z_now[8]) + float(row8.desp_z)]
        )
        tilts_after = (float(row8.tilt_x), float(row8.tilt_y), float(row8.tilt_z))
        others_after = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z)) for i, r in enumerate(app.rows) if i != 8
        ]
        check(
            "1-row apply translates onto the clicked axis point, orientation kept, others untouched",
            bool(np.allclose(center8, (60.0, 0.0, 37.3), atol=1e-6))
            and tilts_before == tilts_after
            and others_before == others_after
            and not getattr(insp, "_snap_rows_to_axis_pick_mode", False),
            f"center={center8.round(2).tolist()} status={insp.status_var.get()[:40]}",
        )

        # 4: surrogate-group integrity.
        exp, did = expand_rows_to_lens_block([3, 4], 3, 7)
        check("pure core: partial block expands to the whole block", exp == [3, 4, 5, 6, 7] and did, str(exp))
        exp, did = expand_rows_to_lens_block([3, 4, 5, 6, 7], 3, 7)
        check("pure core: full block does not re-expand", exp == [3, 4, 5, 6, 7] and not did, str(exp))
        exp, did = expand_rows_to_lens_block([8, 9], 3, 7)
        check("pure core: selection outside the block untouched", exp == [8, 9] and not did, str(exp))
        exp2, did2 = insp._expand_selection_rows_for_groups([4, 9])
        check(
            "inspector expansion: partial lens + image -> whole block + image",
            exp2 == [3, 4, 5, 6, 7, 9] and did2,
            str(exp2),
        )

        # plain-vs-chained parity.
        insp._set_row_highlights([])
        insp._rubber_band_select_mode = True
        insp._rubber_band_chain_snap = False
        orig_conv = insp._tk_xy_to_vtk_display_xy
        insp._tk_xy_to_vtk_display_xy = lambda xy: xy
        try:
            insp._complete_rubber_band_select(rect_a, rect_b)
        finally:
            insp._tk_xy_to_vtk_display_xy = orig_conv
        app.update_idletasks()
        app.update()
        check(
            "plain variant keeps the full picked set after event drain",
            sorted(insp._picked_row_indices) == all_rows,
            str(sorted(insp._picked_row_indices)),
        )
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    if failures:
        print("FAIL:", failures)
        return 1
    print("PASS: rubber-band multi-select survives, degenerate snap refused, lens group intact")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
