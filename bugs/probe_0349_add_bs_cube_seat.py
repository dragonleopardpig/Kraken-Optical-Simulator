"""Repro probe (bugs/0349): flag_20260717_212714_748 -- Add BS Cube pushed the LED away.

Scene per the flags: CO90 LED, obliquely rotated, CA snapped onto the axis
(center+normal, the flag-1 action), then right-click -> Add Beam Splitter to LED
(Cube). With the fix the LED pose must be IDENTICAL before/after the add, and the
cube seats against the through window (crossing seat when a perpendicular side
window is detected).

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0349_add_bs_cube_seat.py
"""
import sys, traceback
from pathlib import Path
import numpy as np
from KrakenOS.UI.layout_editor import KrakenLayoutEditor

app = KrakenLayoutEditor()
try:
    edge = app._default_led_object_edge_distance()
    app.imported_led_step_path = Path("attachment/LED/OPT-CO90-X-V1.6.2-H.STEP").resolve()
    app.led_step_rotation_x_deg = 0.0
    app.led_step_rotation_y_deg = 0.0
    app.led_step_rotation_z_deg = 0.0
    app.led_step_object_edge_local_z = None
    app.led_step_axis_offset_xy = (0.0, 0.0)
    app.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
    app._clear_step_overlay_axis_anchor("led")
    app._selected_step_label = "led"
    app.led_object_edge_distance_mm = float(max(edge, 0.0))
    app.open_3d_view(); app.update_idletasks(); app.update()
    insp = app._three_d_inspector
    insp.update_idletasks(); insp.update()
    svc = insp._face_assignment_service()

    def led_state(tag):
        mesh = app._transformed_imported_step_mesh_for_label("led")
        b = tuple(round(float(v), 2) for v in mesh.bounds)
        rot = (float(app.led_step_rotation_x_deg), float(app.led_step_rotation_y_deg), float(app.led_step_rotation_z_deg))
        plc = tuple(round(float(v), 3) for v in app._step_placement_offset_xyz("led"))
        print(f"[{tag}] rot={rot} placement={plc} bounds={b}")

    # 1) oblique rotation like the user's pre-snap state
    app.rotate_step_z("led", 30.0)
    app.rotate_step_x("led", 25.0) if hasattr(app, "rotate_step_x") else None
    insp.update_idletasks(); insp.update()
    led_state("oblique")

    # 2) CA snap (the flag1 action): center+normal via the menu handler
    c, n = svc._clear_aperture_opening_center_normal("led")
    print(f"[snap] CA before: center={np.round(np.asarray(c,float),3)} normal={np.round(np.asarray(n,float),3)}")
    svc._snap_clear_aperture_to_optical_axis_from_context("led", c, n)
    insp.update_idletasks(); insp.update()
    led_state("post-snap")
    c1, n1 = svc._clear_aperture_opening_center_normal("led")
    print(f"[snap] CA after : center={np.round(np.asarray(c1,float),3)} normal={np.round(np.asarray(n1,float),3)}")

    # 3) enumerate the openings the new plan sees
    openings = app._led_beam_splitter_openings()
    for fid, c, n, s in openings:
        print(f"[openings] face {fid}: centroid={np.round(c,3)} normal={np.round(n,3)} span={round(s,2)}")
    if not openings:
        print("[openings] EMPTY -> no BS flow possible")
        sys.exit(0)

    orig_resolve = type(app)._step_overlay_fine_face_centroid_normal
    def traced_resolve(self, label, fidx):
        out = orig_resolve(self, label, fidx)
        if out is not None and str(label) == "led":
            print(f"    [resolve] led face {fidx} -> centroid={np.round(out[0],3)} normal={np.round(out[1],3)}")
        return out
    type(app)._step_overlay_fine_face_centroid_normal = traced_resolve

    # 4) the flag2 action
    result = app.add_beam_splitter_to_led("cube")
    type(app)._step_overlay_fine_face_centroid_normal = orig_resolve
    insp.update_idletasks(); insp.update()
    print(f"[addbs] result={ {k: (round(v,3) if isinstance(v,float) else v) for k,v in (result or {}).items() if k not in ('bs_path',)} }")
    led_state("post-addbs")
    c2, n2 = svc._clear_aperture_opening_center_normal("led")
    print(f"[addbs] LED CA now: center={np.round(np.asarray(c2,float),3)} normal={np.round(np.asarray(n2,float),3)}")

    # 5) the promoted BS row pose + overlap check
    for i, row in enumerate(app.rows):
        adv = getattr(row, "advanced", {}) or {}
        promo = adv.get("StepOverlayPromotion") if isinstance(adv, dict) else None
        if isinstance(promo, dict):
            print(f"[bs] row {i}: center_world={promo.get('center_world')} bmin={promo.get('bounds_min_world')} bmax={promo.get('bounds_max_world')}")
            bmin = np.asarray(promo.get("bounds_min_world"), float)
            bmax = np.asarray(promo.get("bounds_max_world"), float)
            led_mesh = app._transformed_imported_step_mesh_for_label("led")
            lb = np.asarray(led_mesh.bounds, float).reshape(3, 2)
            ov = [max(0.0, min(bmax[a], lb[a][1]) - max(bmin[a], lb[a][0])) for a in range(3)]
            print(f"[bs] AABB overlap with LED (x,y,z mm): {[round(v,1) for v in ov]}")
except Exception:
    traceback.print_exc()
finally:
    try: app.destroy()
    except Exception: pass
