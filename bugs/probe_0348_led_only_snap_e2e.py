"""Probe (bugs/0348): reproduce flag_20260717_204504_767 -- "still unable to right click
and snap the CA to optical axis" on build 8cfb0aad (the 0347 fix, fresh app).

The flag scene is NOT the promoted AZ85 layout: its live state shows ONLY an imported
LED STEP (step_actor_counts {led:1}), NO promoted rows, NO fold, exactly ONE axis record
(axis:global), placement/axis offsets all zero, interaction_mode idle at flag time --
with the recording showing right-click -> menu -> then two clicks ON the dotted axis.

This probe rebuilds that scene faithfully (fresh editor + direct LED STEP import, no
promote) and drives the REAL handlers end-to-end:

  1. what does the right-click BODY/OPENING menu resolve for the CA (center/normal)?
  2. fire _snap_clear_aperture_to_optical_axis_from_context with the natural state --
     catching anything a Tk menu callback would swallow;
  3. report pick mode / status / pose / opening XY-offset before+after;
  4. if the arm survives, emulate the user's axis click through the armed-click path.

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0348_led_only_snap_e2e.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

LED_STEP = Path("attachment/LED/OPT-ILS0202-X-V1.0.2-H.STEP").resolve()


def _axis_ids(records):
    out = []
    for rec in list(records or []):
        try:
            out.append(str(rec.get("axis_id", "") or ""))
        except Exception:
            out.append("?")
    return out


def _pose(app):
    return {
        "placement": tuple(float(v) for v in app._step_placement_offset_xyz("led")),
        "axis_offset": tuple(float(v) for v in getattr(app, "led_step_axis_offset_xy", (0.0, 0.0))),
        "rot": (
            float(getattr(app, "led_step_rotation_x_deg", 0.0)),
            float(getattr(app, "led_step_rotation_y_deg", 0.0)),
            float(getattr(app, "led_step_rotation_z_deg", 0.0)),
        ),
    }


def _xy_off(center):
    try:
        return float(np.linalg.norm(np.asarray(center, float).reshape(-1)[:2]))
    except Exception:
        return None


def main() -> int:
    app = KrakenLayoutEditor()
    debug_lines: list[str] = []
    orig_debug = app.append_debug

    def tap_debug(text):
        debug_lines.append(str(text))
        try:
            return orig_debug(text)
        except Exception:
            return None

    app.append_debug = tap_debug
    try:
        # --- faithful LED-only import (mirrors import_led_step minus the dialog) ---
        if not LED_STEP.exists():
            print(f"LED STEP missing: {LED_STEP}")
            return 1
        edge = max(float(getattr(app, "led_object_edge_distance_mm", 0.0)), 0.0)
        if edge <= 0.0:
            edge = app._default_led_object_edge_distance()
        app.imported_led_step_path = LED_STEP
        app.led_step_rotation_x_deg = 0.0
        app.led_step_rotation_y_deg = 0.0
        app.led_step_rotation_z_deg = 0.0
        app.led_step_object_edge_local_z = None
        app.led_step_axis_offset_xy = (0.0, 0.0)
        app.led_step_placement_offset_xyz = (0.0, 0.0, 0.0)
        app._clear_step_overlay_axis_anchor("led")
        app._selected_step_label = "led"
        app.led_object_edge_distance_mm = float(edge)
        app._live_step_overlay_trace_plan_cache = {}
        app._invalidate_preview_scene_trace()

        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            print("INSPECTOR UNAVAILABLE")
            return 1
        insp.update_idletasks(); insp.update()
        svc = insp._face_assignment_service()

        rows = list(getattr(app, "rows", []) or [])
        print(f"[scene] rows n={len(rows)}  led_edge_distance={edge}")
        try:
            mesh = app._transformed_imported_step_mesh_for_label("led")
            print(f"[scene] led mesh bounds={tuple(round(float(b), 2) for b in mesh.bounds)}")
        except Exception as exc:
            print(f"[scene] led mesh unavailable: {exc}")
        fold_z = insp._folded_axis_incoming_fold_point_z()
        src = list(insp._optical_axis_records_for_3d(None) or [])
        live = list(getattr(insp, "_optical_axis_pick_records", None) or [])
        print(f"[fold] _folded_axis_incoming_fold_point_z = {fold_z}")
        print(f"[src ] _optical_axis_records_for_3d(None): n={len(src)} ids={_axis_ids(src)}")
        print(f"[live] _optical_axis_pick_records:         n={len(live)} ids={_axis_ids(live)}")

        center, normal = svc._clear_aperture_opening_center_normal("led")
        if center is None or normal is None:
            print("[menu] CA did NOT resolve -> body menu would NOT offer the snap entry")
            return 0
        print(f"[menu] CA center={np.asarray(center)} normal={np.asarray(normal)}  XY-off={_xy_off(center)}")

        print("\n--- fire _snap_clear_aperture_to_optical_axis_from_context (natural) ---")
        pose_before = _pose(app)
        try:
            svc._snap_clear_aperture_to_optical_axis_from_context("led", center, normal)
        except Exception:
            print("[fire] HANDLER RAISED (a Tk menu callback would swallow this):")
            traceback.print_exc()
        insp.update_idletasks(); insp.update()
        mode_after = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
        center2, _n2 = svc._clear_aperture_opening_center_normal("led")
        moved = None
        try:
            moved = float(np.linalg.norm(np.asarray(center2, float)[:3] - np.asarray(center, float)[:3]))
        except Exception:
            pass
        print(f"[fire] pick_mode after={mode_after}  interaction={insp.current_interaction_mode()}")
        print(f"[fire] moved={moved}  XY-off after={_xy_off(center2)}")
        print(f"[fire] pose before={pose_before}")
        print(f"[fire] pose after ={_pose(app)}")
        print(f"[fire] status={insp.status_var.get()!r}")

        if mode_after:
            print("\n--- STILL ARMED: emulate the user's click ON the dotted axis ---")
            recs = list(getattr(insp, "_optical_axis_pick_records", None) or [])
            print(f"[click] pick records now n={len(recs)} ids={_axis_ids(recs)}")
            if recs:
                info = dict(recs[0])
                pts = np.asarray(info.get("points"), float)
                info["picked_world"] = pts[len(pts) // 2, :3]
                try:
                    insp._apply_step_normal_axis_pick(info)
                except Exception:
                    print("[click] APPLY RAISED:")
                    traceback.print_exc()
                insp.update_idletasks(); insp.update()
                center3, _n3 = svc._clear_aperture_opening_center_normal("led")
                print(f"[click] pick_mode={bool(insp._step_normal_axis_pick_mode)}  "
                      f"XY-off={_xy_off(center3)}  status={insp.status_var.get()!r}")
    except Exception:
        traceback.print_exc()
    finally:
        if debug_lines:
            print("\n[debug log tail]")
            for line in debug_lines[-15:]:
                print(f"  {line}")
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
