"""bugs/0330c -- flag_20260716_170326_798: does the PASSIVE-hover fallback return
the square at the true cursor, or does it drop it?

diag_0330b (offscreen) proved: at the flag camera + true cursor [432,652],
nearest_opening_loop returns the SQUARE -- so it is NOT a projection/snap bug.
The live miss stashed cursor [1019,402] (a stale earlier hover) with chosen=null.

The passive idle hover (open3d_interaction.py:1120-1139) runs the opening pick ONLY
when step_label resolves -- from the VTK actor map OR the ray-independent fallback
_step_feature_pick_any_for_display_xy((x,y)). On the see-through square the ray goes
THROUGH the hole, so the fallback is the path that must carry the square. This drives
the REAL Kraken3DInspector (headless, analytic pick -- no GL ray needed) at the flag
camera and prints, at BOTH cursors:
  * _step_feature_pick_for_display_xy("led", xy, actor=None,...)   -> the raw opening pick
  * _step_feature_pick_any_for_display_xy(xy)                      -> the passive fallback
  * _step_feature_pick_any_for_display_xy(xy, labels=("led",))     -> label-restricted
  * _last_opening_hover_debug (cursor + chosen)                    -> what the stash saw
If the raw pick returns F053 but the fallback returns None -> the fallback DROPS the
square (the reproducible bug). If both return F053 -> the miss is event-timing only.
"""
from __future__ import annotations
from pathlib import Path

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    _configure_base_editor, _open_3d_inspector, _refresh, _settle,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor

LED = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()
W, H = 1163, 904

# flag_20260716_170326_798 camera
CAM_POS = (290.33855105047655, -14.442679984171399, 113.04604634298116)
CAM_FOCAL = (0.0, 0.0, 50.0)
CAM_UP = (0.059512498937505, 0.997184139818969, -0.045629527322958045)
CAM_SCALE = 101.15273775216139

TRUE_CURSOR = (432.0, 652.0)
DEBUG_CURSOR = (1019.0, 402.0)


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


def _probe(inspector, cur):
    raw = inspector._step_feature_pick_for_display_xy(
        "led", cur, actor=None, actor_key=None, cell_id=-1)
    raw_id = None if not isinstance(raw, dict) else raw.get("face_id")
    dbg = getattr(inspector, "_last_opening_hover_debug", None)
    dbg_cur = None if not isinstance(dbg, dict) else dbg.get("cursor_xy")
    dbg_chosen = None if not isinstance(dbg, dict) else dbg.get("chosen_face_index")
    any_all = inspector._step_feature_pick_any_for_display_xy(cur)
    any_all_s = None if not isinstance(any_all, dict) else (
        f"{any_all.get('label')}/{(any_all.get('feature_pick') or {}).get('face_id')}")
    any_led = inspector._step_feature_pick_any_for_display_xy(cur, labels=("led",))
    any_led_s = None if not isinstance(any_led, dict) else (
        f"{any_led.get('label')}/{(any_led.get('feature_pick') or {}).get('face_id')}")
    print(f"\ncursor {cur}:")
    print(f"  raw _step_feature_pick_for_display_xy -> face_id={raw_id!r}")
    print(f"  stash cursor={dbg_cur} chosen_face={dbg_chosen}")
    print(f"  fallback _any_for_display_xy(all)     -> {any_all_s!r}")
    print(f"  fallback _any_for_display_xy(led)     -> {any_led_s!r}")


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

        _probe(inspector, TRUE_CURSOR)
        _probe(inspector, DEBUG_CURSOR)
        print("\n=> want TRUE->F053 on BOTH raw and fallback; if fallback=None the passive hover DROPS the square")
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
