"""bugs/0329 -- reproduce the LIVE hover with the REAL Kraken3DInspector (not a
_FakeInspector). The user restarts the app every test, so flag_20260716_150110_640
("still can't highlight the CA opening") is NOT stale: on the real app plain hover
resolves the whole panel F005 (opening left as a HOLE) and the 0328 opening-loop snap
never fires. My display-free harness returns the square (F053), so the divergence is
in the real runtime. Drive the real inspector under a private Xvfb and pinpoint where
_step_opening_hover_pick returns None.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    _configure_base_editor, _open_3d_inspector, _refresh, _settle,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_round_lens_pick import _step_opening_hover_pick
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop)

LED = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
CURSOR = (886.0, 607.0)
W, H = 1838, 904


def _set_led(app):
    app.imported_led_step_path = LED
    app.led_step_rotation_x_deg = app.led_step_rotation_y_deg = app.led_step_rotation_z_deg = 0.0
    app.led_step_axis_offset_xy = (0.0, 0.0)
    app.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
    app._selected_step_label = "led"
    app._live_step_overlay_trace_plan_cache = {}
    app._invalidate_preview_scene_trace()
    app.select_step_component("led")


def _force_camera(ren, rw):
    rw.SetSize(W, H)
    cam = ren.GetActiveCamera()
    cam.SetParallelProjection(True)
    cam.SetPosition(285.12211524555573, 44.86112856896071, 121.92167776210495)
    cam.SetFocalPoint(0.0, 0.0, 50.0)
    cam.SetViewUp(-0.13607788549386488, 0.9877295233717259, -0.0766367910300376)
    cam.SetParallelScale(101.15273775216139)
    ren.ResetCameraClippingRange()
    rw.Render()


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry(f"{W}x{H}+0+0")
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)
        _set_led(app)
        _refresh(inspector, reset_camera=True)
        _settle(inspector, 0.3)

        ren = inspector._renderer
        rw = ren.GetRenderWindow()
        _force_camera(ren, rw)
        _settle(inspector, 0.2)
        print(f"render-window size = {tuple(rw.GetSize())} (want {W}x{H})")

        proj = inspector._world_to_display_2d
        mesh = app._transformed_imported_step_mesh_for_label("led")
        print("mesh is None:", mesh is None)
        loops = opening_loops_for_mesh(mesh) if mesh is not None else []
        print(f"opening_loops_for_mesh -> {len(loops)} loops")
        sq = next(lp for lp in loops if 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40)
        sc = proj(sq.centroid)
        square_center = (round(float(sc[0])), round(float(sc[1])))
        print(f"square proj-centroid = {square_center}")

        # The gesture that FAILED live: hovering the OPEN MIDDLE of the square.
        for name, xy in (("recorded rim cursor", CURSOR), ("square center (interior)", square_center)):
            near = nearest_opening_loop(loops, xy, proj, tolerance_px=30.0) if loops else None
            near_id = None if near is None else f"F{near.face_index:03d}(perim={near.perimeter:.0f})"
            try:
                inspector._picker.Pick(int(xy[0]), int(xy[1]), 0.0, ren)
                actor = inspector._picker.GetActor()
                actor_key = inspector._actor_key(actor)
                cell_id = int(inspector._picker.GetCellId())
            except Exception:
                actor = actor_key = None
                cell_id = -1
            full = inspector._step_feature_pick_for_display_xy(
                "led", xy, actor=actor, actor_key=actor_key, cell_id=cell_id)
            full_id = None if not isinstance(full, dict) else full.get("face_id")
            print(f"  {name:26s} xy={tuple(map(int,xy))} nearest_loop={near_id} FULL_pick={full_id}")
        print("=> want F053 for BOTH (square); F005 = whole panel = the live miss")
    finally:
        try:
            if app._three_d_inspector is not None:
                app._three_d_inspector._on_close()
        except Exception:
            pass
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
