"""bugs/0542 visual check -- seated LED + the 'Illum rays' master toggle, rendered from
the flag_20260804_133134 viewpoint so the user's eyeball is replaced by snapshots."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260804_144415_900/state.json")


def main(out_prefix: str) -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        app._three_d_inspector = insp
        sid = app.add_illumination_led_source()
        insp._face_assignment_service()._seat_source_on_led_floor_auto(sid)
        flag = json.loads(FLAG.read_text())["scene_state"]
        cam = insp._renderer.GetActiveCamera()
        cam.SetPosition(*flag["camera_position"])
        cam.SetFocalPoint(*flag["camera_focal"])
        cam.SetViewUp(*flag["camera_view_up"])
        try:
            cam.ParallelProjectionOn()
            cam.SetParallelScale(float(flag["camera_parallel_scale"]))
        except Exception:
            pass
        app.show_clipped_rays_var.set(True)
        for state, tag in ((False, "off"), (True, "on")):
            insp.show_source_illumination_rays_var.set(state)
            app._invalidate_preview_scene_trace()
            insp.refresh_from_editor(force_retrace=True)
            _settle(insp)
            _save_vtk_snapshot(insp, Path(f"{out_prefix}_{tag}.png"))
            print(f"wrote {out_prefix}_{tag}.png")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
