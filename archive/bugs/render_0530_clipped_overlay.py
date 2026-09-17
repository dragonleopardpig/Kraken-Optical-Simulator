"""bugs/0530 visual check -- render the dragged AZ85 scene with 'Show clipped rays' ON.
Pre-fix this drew 225 chords teleporting into the camera; post-fix strays keep their
honest escape tails. Writes a PNG for eyeball verification."""
from __future__ import annotations

import sys
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")


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
        app.translate_step_overlay("lens", (53.135, 0.0, 0.0))
        app.show_clipped_rays_var.set(True)
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        # Reproduce the flag's exact viewpoint for a like-for-like comparison.
        import json

        flag = json.loads(
            Path("attachment/recorded_bug_repros/flag_20260804_073933_305/state.json").read_text()
        )["scene_state"]
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
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/claude-1000/0530_after.png"))
