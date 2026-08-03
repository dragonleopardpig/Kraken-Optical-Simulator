"""bugs/0528 repro -- the GIZMO-ARROW lens drag commits the conjugate write but never
refocuses (flag_20260803_203614). Drives the REAL `_finish_step_translate_drag` with the
user's +50.54 mm along-leg drag and prints the sensor seat + status.

Pre-fix: gaps written, sensor stays at the fresh seat (-5.08), no refocus note.
Post-fix: sensor re-seats at best focus (~-23.5) with the Solve-for-FOV note.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import _open_3d_inspector
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)

        def sensor_z():
            return float(np.asarray(tree_mod.row_world_pose(app.rows, len(app.rows) - 1), float).reshape(-1)[2])

        print(f"[fresh] gaps={[round(float(r.thickness), 2) for r in app.rows]} sensor_z={sensor_z():+.3f}")

        state = {
            "label": "lens",
            "axis": "x",
            "axis_unit": (1.0, 0.0, 0.0),
            "applied_delta_mm": 50.542,
        }
        insp._finish_step_translate_drag(state)

        gaps = [round(float(r.thickness), 2) for r in app.rows]
        print(f"[after gizmo-arrow finish] gaps={gaps} sensor_z={sensor_z():+.3f}")
        print(f"  status = {insp.status_var.get()!r}")
        wrote = abs(gaps[0] - 181.18) < 0.5 and abs(gaps[6] - 52.73) < 0.5
        refocused = abs(sensor_z() - (-5.077)) > 5.0
        note = "Solve for FOV" in str(insp.status_var.get())
        print(f"  composite wrote gaps: {wrote}; sensor re-seated: {refocused}; refocus note: {note}")
        print("BUG REPRODUCED (defocus left behind)" if (wrote and not refocused) else "refocus ran")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
