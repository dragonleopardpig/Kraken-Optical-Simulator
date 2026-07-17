"""Probe (bugs/0347): reproduce flag_20260717_164901_740 -- "right click snapping still
not working" on build 8834ecfa (the 0346 fix).

The flag scene is machine_vision_AZ85_RA_Mirror.py but its LIVE state showed a SINGLE
axis (optical_axis_records len=1 axis:global), NOTHING promoted, and the LED did NOT move
(axis_offset_xy=[0,0]). probe_0347 forced a populated single-axis pick list and the snap
worked -- so this probe instead observes the NATURAL state and tests the two things
probe_0347 did NOT:

  (A) is the LED opening actually OFF-AXIS on this scene? (if it is already on-axis the
      snap correctly moves nothing and "not working" is a perception, not a bug)
  (B) does the MENU-path handler move the opening with the pick list left in its NATURAL
      state, and separately with it EMPTIED (the real 0346 pre-refresh condition)?

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0347_menu_snap_natural.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _axis_ids(records):
    out = []
    for rec in list(records or []):
        try:
            out.append(str(rec.get("axis_id", "") or ""))
        except Exception:
            out.append("?")
    return out


def _pose(insp):
    poses = getattr(insp, "_step_overlay_poses", None)
    if isinstance(poses, dict):
        return dict(poses.get("led", {}) or {})
    return {}


def _xy_off(center):
    try:
        return float(np.linalg.norm(np.asarray(center, float).reshape(-1)[:2]))
    except Exception:
        return None


def _fire(insp, svc, tag):
    center, normal = svc._clear_aperture_opening_center_normal("led")
    if center is None or normal is None:
        print(f"[{tag}] CA did not resolve -> menu would NOT offer the snap"); return
    off_before = _xy_off(center)
    pose_before = _pose(insp)
    mode_before = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
    svc._snap_clear_aperture_to_optical_axis_from_context("led", center, normal)
    insp.update_idletasks(); insp.update()
    mode_after = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
    center2, _n2 = svc._clear_aperture_opening_center_normal("led")
    off_after = _xy_off(center2)
    moved = None
    try:
        moved = float(np.linalg.norm(np.asarray(center2, float)[:2] - np.asarray(center, float)[:2]))
    except Exception:
        pass
    print(f"[{tag}] CA center={np.asarray(center)}  XY-off-axis before={off_before}")
    print(f"[{tag}] pick_mode {mode_before}->{mode_after}   moved={moved}   XY-off after={off_after}")
    print(f"[{tag}] pose before={pose_before}  after={_pose(insp)}")
    print(f"[{tag}] status={insp.status_var.get()!r}")


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["probe"] = SCENE
        app.load_layout_by_name("probe")
        app.open_3d_view()
        app.update_idletasks(); app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            print("INSPECTOR UNAVAILABLE"); return 0
        insp.update_idletasks(); insp.update()
        svc = insp._face_assignment_service()

        fold_z = insp._folded_axis_incoming_fold_point_z()
        src = list(insp._optical_axis_records_for_3d(None) or [])
        live = list(getattr(insp, "_optical_axis_pick_records", None) or [])
        print(f"[fold] _folded_axis_incoming_fold_point_z = {fold_z}")
        print(f"[src ] _optical_axis_records_for_3d(None): n={len(src)} ids={_axis_ids(src)}")
        print(f"[live] _optical_axis_pick_records:         n={len(live)} ids={_axis_ids(live)}")

        print("\n--- (A) NATURAL pick-list state ---")
        _fire(insp, svc, "A")

        print("\n--- (B) EMPTIED pick list (0346 pre-refresh condition) ---")
        insp._optical_axis_pick_records = []
        _fire(insp, svc, "B")
    except Exception:
        traceback.print_exc()
    finally:
        try: app.destroy()
        except Exception: pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
