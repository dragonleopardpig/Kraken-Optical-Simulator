"""bugs/0551 eyeball -- how long should an ESCAPED ray's display tail be?

`scene_projector.bounded_ray_points_for_scene_display` draws an escaped ray with a tail of
``max(75, min(scene_radius * 1.25, 600))``, EXTENDING it past its traced stub "to show the
output direction". On the swapped AZ85 scene that is ~375 mm, so every escape streams off
frame -- the user's "extra rays out of bound" (flag_20260805_081647 / _081811).

The tail length is driven by the ``radius`` argument, so each option can be rendered by
scaling that one number -- no behaviour is changed on disk, this only shows what each choice
would look like:

    current   radius x 1.00  -> 1.25 * scene_radius   (what ships today)
    shorter   radius x 0.32  -> 0.40 * scene_radius
    stub      radius x 0.00  -> the 75 mm floor (what a suppressed branch already gets)

Rendered from flag_20260805_081811's own camera so it matches what the user sees.

Run:  xvfb-run -a .devenv/state/venv/bin/python bugs/render_0551_escape_tail_options.py /tmp/0551
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCENE = Path("attachment/machine_vision_Apo75.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260805_081811_672/state.json")

OPTIONS = (
    ("current", 1.00, "ships today: 1.25 x scene_radius"),
    ("shorter", 0.32, "0.40 x scene_radius"),
    ("stub", 0.00, "75 mm floor"),
)


def _drawn_max_x(insp) -> float | None:
    lo = None
    try:
        props = insp._renderer.GetViewProps()
        props.InitTraversal()
        for _ in range(int(props.GetNumberOfItems())):
            prop = props.GetNextProp()
            try:
                if not bool(prop.GetVisibility()):
                    continue
                mapper = prop.GetMapper()
                data = mapper.GetInput() if mapper is not None else None
                if data is None or int(getattr(data, "GetNumberOfLines", lambda: 0)()) <= 0:
                    continue
                bounds = [float(v) for v in prop.GetBounds()]
                if any(bounds[i] > bounds[i + 1] for i in (0, 2, 4)):
                    continue
                lo = bounds[1] if lo is None else max(lo, bounds[1])
            except Exception:
                continue
    except Exception:
        return None
    return lo


def main(out_prefix: str) -> int:
    from KrakenOS.UI import scene_projector
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    original = scene_projector.bounded_ray_points_for_scene_display
    scale = {"value": 1.0}

    def scaled(points, center, radius, **kwargs):
        return original(points, center, float(radius) * scale["value"], **kwargs)

    scene_projector.bounded_ray_points_for_scene_display = scaled
    # three_d_scene_tools imported the symbol directly; re-point that binding too.
    try:
        from KrakenOS.UI.services import three_d_scene_tools

        three_d_scene_tools.bounded_ray_points_for_scene_display = scaled
    except Exception:
        pass

    app = KrakenLayoutEditor()
    try:
        app.layout_files["apo75"] = SCENE
        app.load_layout_by_name("apo75")
        # The saved file predates the bugs/0550 fix, so neutralise its negative gap the same
        # pose-preserving way the diagnostic does -- this is the post-fix state.
        for index, row in enumerate(app.rows):
            thickness = float(getattr(row, "thickness", 0.0) or 0.0)
            if thickness >= 0.0:
                continue
            for follower in range(index + 1, len(app.rows)):
                app.rows[follower].desp_z = float(app.rows[follower].desp_z) + thickness
            row.thickness = 0.0

        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)

        flag = json.loads(FLAG.read_text())["scene_state"]
        camera = insp._renderer.GetActiveCamera()
        camera.SetPosition(*flag["camera_position"])
        camera.SetFocalPoint(*flag["camera_focal"])
        camera.SetViewUp(*flag["camera_view_up"])
        try:
            camera.ParallelProjectionOn()
            camera.SetParallelScale(float(flag["camera_parallel_scale"]))
        except Exception:
            pass

        for tag, factor, label in OPTIONS:
            scale["value"] = float(factor)
            app._invalidate_preview_scene_trace()
            insp.refresh_from_editor(force_retrace=True)
            camera.SetPosition(*flag["camera_position"])
            camera.SetFocalPoint(*flag["camera_focal"])
            camera.SetViewUp(*flag["camera_view_up"])
            try:
                camera.ParallelProjectionOn()
                camera.SetParallelScale(float(flag["camera_parallel_scale"]))
            except Exception:
                pass
            _settle(insp)
            path = Path(f"{out_prefix}_{tag}.png")
            _save_vtk_snapshot(insp, path)
            print(f"{tag:<8} ({label}): drawn max x = {_drawn_max_x(insp)} -> {path}")
    finally:
        scene_projector.bounded_ray_points_for_scene_display = original
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/0551"))
