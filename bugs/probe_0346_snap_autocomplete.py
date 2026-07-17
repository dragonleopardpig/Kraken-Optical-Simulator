"""Probe (bugs/0346): the CA->optical-axis snap arms the two-step pick but never
auto-completes on a SINGLE-axis scene ("right click snap ... still not working,
optical axis no highlight, click on it no snap" -- flag_20260717_160019_506, on a
build-stamped app running 0815ab71, so NOT stale).

Opens the real GL inspector on the AZ85 LED scene, resolves the CA opening, fires
_snap_clear_aperture_to_optical_axis_from_context, and reports whether the pick
auto-completed (mode -> False) or stayed armed (mode stuck True), plus WHY
_single_optical_axis_pick_info did or didn't return a payload.

Run under Xvfb:
    DISPLAY=:99 .devenv/state/venv/bin/python bugs/probe_0346_snap_autocomplete.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor

DEFAULT_SCENE = Path("attachment/machine_vision_150mm_test.py")


def main() -> int:
    scene = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SCENE
    app = KrakenLayoutEditor()
    try:
        app.layout_files["probe"] = scene
        app.load_layout_by_name("probe")
        print(f"[1] scene loaded: {scene}")

        app.open_3d_view()
        app.update_idletasks()
        app.update()
        insp = app._three_d_inspector
        if insp is None or not insp.available:
            print("INSPECTOR UNAVAILABLE")
            return 0
        insp.update_idletasks()
        insp.update()
        print("[2] inspector open; available =", insp.available)

        svc = insp._face_assignment_service()

        recs = list(getattr(insp, "_optical_axis_pick_records", None) or [])
        axis_ids = {str(r.get("axis_id", "") or "") for r in recs}
        print(f"[3] _optical_axis_pick_records: n={len(recs)}  axis_ids={sorted(axis_ids)}")
        try:
            src = list(insp._optical_axis_records_for_3d(None) or [])
            print(f"[3b] _optical_axis_records_for_3d(None): n={len(src)}  "
                  f"axis_ids={sorted({str(r.get('axis_id','') or '') for r in src})}")
        except Exception as exc:
            print(f"[3b] _optical_axis_records_for_3d(None) raised: {exc!r}")
        try:
            insp.refresh_from_editor()
            insp.update_idletasks(); insp.update()
            recs2 = list(getattr(insp, "_optical_axis_pick_records", None) or [])
            print(f"[3c] after refresh_from_editor: _optical_axis_pick_records n={len(recs2)}")
        except Exception as exc:
            print(f"[3c] refresh_from_editor raised: {exc!r}")
        for r in recs:
            pts = np.asarray(r.get("points"), float) if r.get("points") is not None else None
            print("      rec axis_id=", r.get("axis_id"),
                  " points_shape=", (pts.shape if pts is not None else None))

        center, normal = svc._clear_aperture_opening_center_normal("led")
        print(f"[4] CA resolve: center={center}  normal={normal}")
        if center is None or normal is None:
            print("VERDICT: CA opening did not resolve -> snap item would be absent")
            return 0

        info = svc._single_optical_axis_pick_info(center)
        print(f"[5] _single_optical_axis_pick_info -> {'PAYLOAD' if info is not None else 'None'}")
        if info is not None:
            print("      payload keys:", sorted(info.keys()))
            print("      picked_world:", info.get("picked_world"))

        mode_before = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
        svc._snap_clear_aperture_to_optical_axis_from_context("led", center, normal)
        mode_after = bool(getattr(insp, "_step_normal_axis_pick_mode", False))
        print(f"[6] snap fired: pick_mode {mode_before} -> {mode_after}")
        print(f"    status_var: {insp.status_var.get()!r}")

        verdict = "AUTO-COMPLETED (good)" if not mode_after else "STUCK ARMED (bug repro)"
        print(f"\nVERDICT: {verdict}")
    except Exception:
        traceback.print_exc()
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
