"""bugs/0331 -- Xvfb integration proof that the trailing re-pick FIXES the live
CA miss end to end (flag_20260717_073340_408, CO90 LED).

diag_0330f proved the pick FUNCTION returns the central-window opening F164 at
the resting cursor [420,635]. This proves the HOVER WIRING + the fix's actuator:
  1. running the real hover at [420,635] sets _hover_step_cell_key to led/F164,
  2. after a stale/empty highlight, inspector._refire_scene_hover_pick() (what the
     bugs/0331 trailing timer calls) re-picks at the resting cursor and lands the
     SAME led/F164 highlight -- i.e. the resting cursor is finally hovered.
"""
from __future__ import annotations
from pathlib import Path

from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
    _configure_base_editor, _open_3d_inspector, _refresh, _settle,
)
from KrakenOS.UI.layout_editor import KrakenLayoutEditor

LED = Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP").resolve()
W, H = 1163, 904
CAM_POS = (106.42429438294444, -30.460346006750775, -244.75322758070575)
CAM_FOCAL = (-5.133493386800098, -5.791433953646112, 51.13146936002458)
CAM_UP = (-0.016887738634632794, 0.9958530832362732, -0.08939485943059908)
CAM_SCALE = 83.59730392740606
TRUE_CURSOR = (420, 635)
OFFBODY_CURSOR = (123, 589)
WANT = ("step", "led", "F164")


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
    cam = ren.GetActiveCamera(); cam.SetParallelProjection(True)
    cam.SetPosition(*CAM_POS); cam.SetFocalPoint(*CAM_FOCAL)
    cam.SetViewUp(*CAM_UP); cam.SetParallelScale(CAM_SCALE)
    ren.ResetCameraClippingRange(); rw.Render()


def _hover_at(inspector, xy, *, reforce_camera=False):
    if reforce_camera:
        _force_camera(inspector._renderer, inspector._renderer.GetRenderWindow())
    inspector._vtk_interactor.SetEventPosition(int(xy[0]), int(xy[1]))
    inspector._mouse_move_last_ts = 0.0
    inspector._on_mouse_move(None, None)
    return inspector._hover_step_cell_key


def main() -> int:
    ok = True

    def check(cond, msg):
        nonlocal ok
        print(("  ok  " if cond else "  FAIL") + "  " + msg)
        ok = ok and bool(cond)

    app = KrakenLayoutEditor(headless=True)
    try:
        app.geometry(f"{W}x{H}+0+0")
        _configure_base_editor(app)
        inspector = _open_3d_inspector(app)
        _set_led(app)
        _refresh(inspector, reset_camera=True)
        _settle(inspector, 0.3)
        _force_camera(inspector._renderer, inspector._renderer.GetRenderWindow())
        _settle(inspector, 0.2)

        # Force the passive idle-hover path + let the synthetic re-fire run.
        app._cad_axis_pick_label = None
        app._cad_axis_pick_any = False
        app._cad_led_object_edge_pick = False
        inspector._pointer_over_vtk_widget = lambda: True  # type: ignore[assignment]
        # The live app wires the VTK MouseMoveEvent observer to _on_mouse_move
        # (open3d_inspector.py:764) -- that is what _refire_scene_hover_pick()'s
        # interactor.MouseMoveEvent() fans out to. The headless capture harness
        # skips that wiring, so reproduce it here to test the actuator honestly.
        fired = {"n": 0}

        def _probe_observer(_obj, _evt):
            fired["n"] += 1
            fired["pos"] = tuple(inspector._vtk_interactor.GetEventPosition())
            inspector._on_mouse_move(_obj, _evt)

        inspector._vtk_interactor.AddObserver("MouseMoveEvent", _probe_observer)

        # 1. direct hover at the resting cursor lands the opening highlight
        key_true = _hover_at(inspector, TRUE_CURSOR)
        print(f"hover [{TRUE_CURSOR[0]},{TRUE_CURSOR[1]}] -> _hover_step_cell_key={key_true}")
        check(key_true == WANT, f"1: resting-cursor hover highlights the opening {WANT}")

        # 2. drive a STALE/empty highlight (off-body), then let the FIX actuator
        #    (_refire_scene_hover_pick, called by the trailing timer) recover it.
        key_off = _hover_at(inspector, OFFBODY_CURSOR)
        print(f"hover [{OFFBODY_CURSOR[0]},{OFFBODY_CURSOR[1]}] -> _hover_step_cell_key={key_off}")
        check(key_off != WANT, "2a: off-body hover does NOT show the opening (stale/empty)")

        # The headless clear path resets the artificially-forced camera; the live
        # app keeps the user's camera across hovers, so re-assert it here.
        _force_camera(inspector._renderer, inspector._renderer.GetRenderWindow())
        inspector._vtk_interactor.SetEventPosition(*TRUE_CURSOR)
        inspector._refire_scene_hover_pick()
        key_fix = inspector._hover_step_cell_key
        print(f"refire @ [{TRUE_CURSOR[0]},{TRUE_CURSOR[1]}] -> _hover_step_cell_key={key_fix} "
              f"(observer fired {fired['n']}x, saw pos={fired.get('pos')})")
        check(fired["n"] >= 1, "2b(i): re-fire fans out through interactor.MouseMoveEvent")
        check(key_fix == WANT, f"2b: trailing re-fire recovers the opening highlight {WANT}")

        # 2c: control -- a direct hover at the same resting cursor (bypassing
        # MouseMoveEvent) to tell a POSITION artifact from a non-idempotent hover.
        key_direct = _hover_at(inspector, TRUE_CURSOR)
        print(f"direct re-hover @ [{TRUE_CURSOR[0]},{TRUE_CURSOR[1]}] -> {key_direct}")

        print("\nRESULT:", "PASS" if ok else "FAIL")
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
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
