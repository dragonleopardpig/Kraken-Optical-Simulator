"""Probe (bugs/0347): does the CA->optical-axis snap actually MOVE an OFF-AXIS opening
onto the axis after 0346, or does it "auto-complete" as a visual no-op?

flag_20260717_164901_740 (build 8834ecfa = the 0346 fix) still says "right click
snapping still not working" on a SINGLE-axis scene whose ILS0202 opening is visibly
offset from the axis, yet the LED overlay pose stayed [0,0]. The 0346 probe only checked
pick_mode cleared -- never that the opening MOVED.

This loads the AZ85 ILS0202 LED (opening offset ~0.77mm in x from axis:global), forces
the LIVE single-axis condition (_optical_axis_pick_records = one axis:global, as the
recording showed), fires the real snap handler, and reports the CA-center delta + the
LED overlay pose before/after.

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0347_snap_moves_opening.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _pose(insp):
    poses = getattr(insp, "_step_overlay_poses", None)
    if isinstance(poses, dict):
        return dict(poses.get("led", {}) or {})
    return {}


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

        center, normal = svc._clear_aperture_opening_center_normal("led")
        print(f"[1] CA center BEFORE = {np.asarray(center)}  normal={np.asarray(normal)}")
        if center is None or normal is None:
            print("VERDICT: CA did not resolve"); return 0

        # Match the LIVE recording: _optical_axis_pick_records populated with ONE axis.
        src = list(insp._optical_axis_records_for_3d(None) or [])
        one = [r for r in src if str(r.get("axis_id", "")) == "axis:global"][:1]
        insp._optical_axis_pick_records = [dict(r) for r in one]
        print(f"[2] forced _optical_axis_pick_records to n={len(insp._optical_axis_pick_records)} "
              f"(axis:global); full source had n={len(src)}")

        info = svc._single_optical_axis_pick_info(center)
        print(f"[3] _single_optical_axis_pick_info -> {'PAYLOAD' if info is not None else 'None'}")

        pose_before = _pose(insp)
        mode_before = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
        svc._snap_clear_aperture_to_optical_axis_from_context("led", center, normal)
        insp.update_idletasks(); insp.update()
        mode_after = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
        pose_after = _pose(insp)
        print(f"[4] snap fired: pick_mode {mode_before} -> {mode_after}")
        print(f"    status_var: {insp.status_var.get()!r}")
        print(f"    LED pose BEFORE: {pose_before}")
        print(f"    LED pose AFTER : {pose_after}")

        center2, normal2 = svc._clear_aperture_opening_center_normal("led")
        print(f"[5] CA center AFTER = {np.asarray(center2)}  normal={np.asarray(normal2)}")
        moved = None
        try:
            moved = float(np.linalg.norm(np.asarray(center2, float)[:2] - np.asarray(center, float)[:2]))
        except Exception:
            pass
        onaxis_before = float(np.linalg.norm(np.asarray(center, float)[:2]))
        onaxis_after = float(np.linalg.norm(np.asarray(center2, float)[:2])) if center2 is not None else None
        print(f"[6] opening XY-dist-from-axis: before={onaxis_before:.4f}  after={onaxis_after}  moved={moved}")

        if mode_after:
            verdict = "STUCK ARMED (snap never applied)"
        elif onaxis_after is not None and onaxis_after < 1e-3 < onaxis_before:
            verdict = "MOVED ONTO AXIS (good)"
        elif moved is not None and moved < 1e-6 and onaxis_before > 1e-3:
            verdict = "NO-OP (auto-completed but opening did NOT move -> bug repro)"
        else:
            verdict = f"UNCLEAR (before={onaxis_before:.4f} after={onaxis_after})"
        print(f"\nVERDICT: {verdict}")
    except Exception:
        traceback.print_exc()
    finally:
        try: app.destroy()
        except Exception: pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
