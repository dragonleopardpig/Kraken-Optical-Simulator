"""bugs/0571 visual check -- the flagged gesture (swap the imaging lens, then Solve for
Thickness at 23x23) rendered from flag_20260806_125028's own viewpoint, so the user's eyeball is
replaced by snapshots.

Writes three PNGs plus a ray census per step:

    <prefix>_1_loaded.png   the scene as saved
    <prefix>_2_swapped.png  after "Swap Imaging Lens from Folder"
    <prefix>_3_solved.png   after fov_solve(object, thickness, 23x23)   <- compare with the flag

Run (capped -- one heavy job at a time):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python \
        bugs/render_0571_swap_then_solve.py attachment/_0571
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_Pyrite85_BS.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260806_125028_234/state.json")
LENS_FOLDER = Path("attachment/Lens/PYRITE_45_85_05x-20x_V38_1072517")


def _census(app, insp, tag: str) -> None:
    """What the rays actually did, beside the picture."""
    from KrakenOS.UI.services import row_placement

    counts: dict[str, int] = {}
    try:
        bundle = insp._scene_bundle
        for path in list(getattr(bundle, "ray_paths", None) or []):
            reason = str(getattr(path, "termination_reason", "") or "?")
            counts[reason] = counts.get(reason, 0) + 1
    except Exception as exc:
        counts = {f"unavailable ({type(exc).__name__})": 0}
    poses = {
        name: np.round(np.asarray(row_placement.world_pose(app, index).position, dtype=float), 3).tolist()
        for name, index in (
            ("lens front datum", 1),
            ("beam splitter", 6),
            ("fold mirror", 7),
            ("sensor", len(app.rows) - 1),
        )
        if index < len(app.rows)
    }
    print(f"    [{tag}] rays {counts} | {poses}")


def main(out_prefix: str) -> int:
    if not SCENE.exists() or not FLAG.exists() or not LENS_FOLDER.exists():
        print("SKIP: scene / flag / lens folder missing")
        return 0
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    flag = json.loads(FLAG.read_text())["scene_state"]
    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        try:
            insp.show_rays_var.set(True)
        except Exception:
            pass

        def shoot(tag: str) -> None:
            insp.refresh_from_editor(force_retrace=True)
            _settle(insp)
            camera = insp._renderer.GetActiveCamera()
            camera.SetPosition(*flag["camera_position"])
            camera.SetFocalPoint(*flag["camera_focal"])
            camera.SetViewUp(*flag["camera_view_up"])
            try:
                camera.ParallelProjectionOn()
                camera.SetParallelScale(float(flag["camera_parallel_scale"]))
            except Exception:
                pass
            insp._vtk_widget.GetRenderWindow().Render()
            _settle(insp)
            path = Path(f"{out_prefix}_{tag}.png")
            _save_vtk_snapshot(insp, path)
            print(f"  wrote {path}")
            _census(app, insp, tag)

        shoot("1_loaded")

        model = app.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        print(f"  swap -> {getattr(model, 'title', model)!r}")
        shoot("2_swapped")

        from types import SimpleNamespace

        solved, message = QuickEstimationService(SimpleNamespace(editor=app)).fov_solve(
            "object", "thickness", 23.0, 23.0
        )
        print(f"  fov_solve -> {solved}: {message}")
        shoot("3_solved")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attachment/_0571"))
