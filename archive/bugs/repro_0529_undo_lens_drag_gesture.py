"""bugs/0529 repro -- flag_20260804_073309: "dragged lens to the right, FOV changed, ray
refocus. Ctrl-z not going back to previous state."

The drag+refocus gesture pushes TWO history entries (translate, snap), so the first Ctrl-Z
only pops the sensor re-seat -- the flag's recorded state exactly (drag kept, image gap
back to fresh 44.12). Per the 0449 doctrine one gesture must be ONE undo step.

Drives both drag surfaces on the frozen AZ85 scene and counts the Ctrl-Z presses needed to
return to the pre-gesture state; also checks redo reapplies the whole gesture.
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

        def snapshot():
            return {
                "gaps": tuple(round(float(r.thickness), 3) for r in app.rows),
                "lens_off": tuple(round(float(v), 3) for v in app._step_placement_offset_xyz("lens")),
                "sensor_z": round(float(np.asarray(tree_mod.row_world_pose(app.rows, len(app.rows) - 1), float).reshape(-1)[2]), 3),
            }

        fresh = snapshot()
        depth0 = len(app._undo_stack)
        print(f"[fresh] {fresh}  undo_depth={depth0}")

        print("\n=== gizmo-arrow gesture ===")
        insp._finish_step_translate_drag(
            {"label": "lens", "axis": "x", "axis_unit": (1.0, 0.0, 0.0), "applied_delta_mm": 53.135}
        )
        dragged = snapshot()
        print(f"[dragged+refocused] {dragged}  undo_depth={len(app._undo_stack)} (+{len(app._undo_stack) - depth0} entries)")
        presses = 0
        while snapshot() != fresh and presses < 4:
            app.undo()
            presses += 1
            print(f"  after Ctrl-Z #{presses}: {snapshot()}")
        print(f"arrow gesture undo presses to restore: {presses} {'(ONE = pass)' if presses == 1 else '(BUG if >1)'}")
        app.redo()
        redone = snapshot()
        print(f"[after redo] matches dragged+refocused: {redone == dragged}")
        while snapshot() != fresh:
            app.undo()

        print("\n=== body-grab carry gesture ===")
        depth1 = len(app._undo_stack)
        app._begin_history_capture()  # live: first carry motion frame begins the capture
        for _ in range(10):
            app.translate_step_overlay("lens", (5.3135, 0.0, 0.0), refresh=False, record_history=False)
        insp._finish_step_carry_drag({"label": "lens", "applied_steps": 10, "history_started": True})
        carried = snapshot()
        print(f"[carried+refocused] {carried}  undo_depth={len(app._undo_stack)} (+{len(app._undo_stack) - depth1} entries)")
        presses = 0
        while snapshot() != fresh and presses < 4:
            app.undo()
            presses += 1
            print(f"  after Ctrl-Z #{presses}: {snapshot()}")
        print(f"carry gesture undo presses to restore: {presses} {'(ONE = pass)' if presses == 1 else '(BUG if >1)'}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
