"""bugs/0625 visual verification -- render the object side after a plain load.

The user's flag view: green FOV square + the 9 launch pencils. Saves a PNG matching
that viewpoint so the '9 pencils, centred on the square' claim is EYEBALLABLE.

Run:  taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python -u bugs/diag_0625_render_object_side.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_Apo75.py")
OUT = Path("bugs/_0625_object_side_after_load.png")


def main() -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        # Aim the camera at the object plane from an oblique angle like the user's
        # screenshot: the object FOV square with the pencils leaving it.
        render_window = insp._vtk_widget.GetRenderWindow()
        renderer = render_window.GetRenderers().GetFirstRenderer()
        camera = renderer.GetActiveCamera()
        # The object end sits at the world launch origin.
        origin, direction = app._world_launch_frame()
        origin = np.asarray(origin, dtype=float)
        direction = np.asarray(direction, dtype=float)
        focal = origin + direction * 30.0
        position = origin + np.array([25.0, -55.0, -35.0])
        camera.SetFocalPoint(*focal)
        camera.SetPosition(*position)
        camera.SetViewUp(0.0, 0.0, -1.0)
        renderer.ResetCameraClippingRange()
        render_window.Render()
        _settle(insp)
        _save_vtk_snapshot(insp, OUT)
        print(f"saved {OUT}")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
