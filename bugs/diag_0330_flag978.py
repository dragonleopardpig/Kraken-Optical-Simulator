"""bugs/0330 -- flag_20260716_162559_978 "still the same, CA not highlighted".

The running app (started 16:18, AFTER the 0329 fix hit disk 15:28) STILL resolves the
whole panel F005 when the cursor sits INSIDE the central square (screenshot: green
crosshair inside the square, tooltip "LED STEP F005 face"). So the 0329 containment
fix did not fire live. My earlier real-inspector diag only ever probed cursors DERIVED
from proj() (self-consistent), so it could never catch a projection/coordinate mismatch.

This drives the REAL Kraken3DInspector under Xvfb with the flag's EXACT camera and the
INDEPENDENT live cursor vtk_xy=[432,428], and prints where the square projects, the
rim distance, the containment test, and both nearest_opening_loop + the full live pick.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    _configure_base_editor, _open_3d_inspector, _refresh, _settle,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.services.open3d_opening_loops import (
    opening_loops_for_mesh, nearest_opening_loop, _project_polygon, _point_in_polygon,
    loop_edge_pairs)
from KrakenOS.UI.services.open3d_face_index_edges import nearest_display_edge

LED = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
CURSOR = (432.0, 428.0)          # vtk_xy straight from the flag state.json
W, H = 1163, 904                 # screenshot.png is 1163x904; png_xy[0]==vtk_xy[0] => W=1163

# flag_20260716_162559_978 camera
CAM_POS = (288.4425137832415, 48.93806831794559, 103.720116366302)
CAM_FOCAL = (0.0, 0.0, 50.0)
CAM_UP = (-0.15360445163904188, 0.985435420008575, -0.07295687376246889)
CAM_SCALE = 101.15273775216139


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
    cam.SetPosition(*CAM_POS)
    cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP)
    cam.SetParallelScale(CAM_SCALE)
    ren.ResetCameraClippingRange()
    rw.Render()


def _is_square(lp):
    return lp is not None and 150 <= lp.perimeter <= 210 and lp.centroid[0] > 40


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
        loops = opening_loops_for_mesh(mesh) if mesh is not None else []
        sq = next((lp for lp in loops if _is_square(lp)), None)
        print(f"loops={len(loops)} square found={sq is not None}")
        if sq is None:
            return 1

        # Where does the square project, and where is the cursor relative to it?
        poly = _project_polygon(sq.points, proj)
        cur = np.asarray(CURSOR, float)
        if poly is not None:
            print(f"square proj-centroid = {tuple(np.round(proj(sq.centroid),1))}")
            print(f"square proj-bbox x[{poly[:,0].min():.0f},{poly[:,0].max():.0f}] "
                  f"y[{poly[:,1].min():.0f},{poly[:,1].max():.0f}]")
            print(f"cursor vtk_xy = {CURSOR}  inside_projected_square = {_point_in_polygon(cur, poly)}")
        hit = nearest_display_edge(sq.points, loop_edge_pairs(sq), CURSOR, proj,
                                   tolerance_px=1e9, depth_reference=None)
        rim_px = None if hit is None else float(hit[4])
        print(f"cursor->nearest square-rim distance = {rim_px}")

        near = nearest_opening_loop(loops, CURSOR, proj, tolerance_px=30.0)
        near_id = None if near is None else f"F{near.face_index:03d}(perim={near.perimeter:.0f})"
        print(f"nearest_opening_loop([432,428]) = {near_id}")

        # Full live pick, exactly as the passive-idle hover calls it.
        try:
            inspector._picker.Pick(int(CURSOR[0]), int(CURSOR[1]), 0.0, ren)
            actor = inspector._picker.GetActor()
            actor_key = inspector._actor_key(actor)
            cell_id = int(inspector._picker.GetCellId())
        except Exception:
            actor = actor_key = None
            cell_id = -1
        full = inspector._step_feature_pick_for_display_xy(
            "led", CURSOR, actor=actor, actor_key=actor_key, cell_id=cell_id)
        full_id = None if not isinstance(full, dict) else full.get("face_id")
        print(f"live cell_id={cell_id}  FULL_pick face_id={full_id!r}")
        # bugs/0330 instrumentation: what the opening-loop hover snap actually SAW
        # at this pick -- the sizes + where every mined opening projected. A real
        # flag now persists this into state.json under scene_state.opening_hover_debug.
        dbg = getattr(inspector, "_last_opening_hover_debug", None)
        print(f"opening_hover_debug = {dbg}")
        print("=> want F053 (square); F005 = whole panel = the live miss")
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
