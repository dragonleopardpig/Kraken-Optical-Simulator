"""bugs/0531 visual check -- overlay OFF from the flag_20260804_082939 viewpoint.
Pre-fix: the ~25% double-bounce ghost band rose from the BS at ~35deg. Post-fix: only the
imaging path draws."""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260804_082939_199/state.json")


def main(out_png: str) -> int:
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
        app.show_clipped_rays_var.set(False)
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
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
        _settle(insp)
        _save_vtk_snapshot(insp, Path(out_png))
        print(f"wrote {out_png}")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
