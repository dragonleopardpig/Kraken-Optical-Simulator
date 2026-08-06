"""The user's own experiment, run headless with snapshots (bugs/0572).

    open attachment/machine_vision_Apo75.py -> swap the imaging lens to PYRITE 45-85
    -> Solve for Thickness 35x35 -> Solve for Thickness 55x55

They expect 55x55 to fail ("I think there is another recurrence bug that prevent solving for
55x55"), so this prints, after EVERY step: the full row table with world poses, what the solve
said, the illumination unit's seat, and the ray census -- and renders a PNG from the same camera
each time, so the pictures and the numbers come from the same run.

Run (capped -- one heavy job at a time):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python \
        bugs/diag_0572_apo75_swap_then_35_and_55.py attachment/_0572
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
FLAG = PROJECT_ROOT / "attachment" / "recorded_bug_repros" / "flag_20260806_125028_234" / "state.json"


def _rows(app, tag: str) -> None:
    from KrakenOS.UI.services import row_placement

    stations = app._row_z_positions()
    print(f"\n--- {tag}")
    for index, row in enumerate(app.rows):
        pose = np.asarray(row_placement.world_pose(app, index).position, dtype=float)
        print(
            f"    {index:>2} {str(row.name)[:30]:30} th={float(row.thickness):9.3f} "
            f"station={stations[index]:9.3f} pose={np.round(pose, 3).tolist()}"
        )
    try:
        led = np.asarray(app._transformed_imported_step_mesh_for_label("led").bounds, dtype=float)
        print(f"    LED housing z centre {(led[4] + led[5]) / 2:.3f}")
    except Exception:
        pass
    for name in ("_real_ray_best_focus_shift_for_rows", "_traced_bundle_best_focus_shift"):
        try:
            print(f"    {name}() = {getattr(app, name)()}")
        except Exception as exc:
            print(f"    {name}() raised {type(exc).__name__}: {exc}")


def _debug_tail(app, count: int = 10) -> None:
    try:
        lines = [
            line for line in str(app.debug_text.get("1.0", "end")).splitlines()
            if any(k in line for k in ("snap detector iter", "hold illumination", "lens leg slide",
                                       "illumination unit held", "Center lens body"))
        ]
    except Exception:
        return
    for line in lines[-count:]:
        print("    |", line.strip())


def main(prefix: str) -> int:
    if not SCENE.exists() or not LENS_FOLDER.exists():
        print("SKIP: scene or lens folder missing")
        return 0
    import json
    from types import SimpleNamespace

    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    camera = json.loads(FLAG.read_text())["scene_state"] if FLAG.exists() else None
    app = KrakenLayoutEditor()
    try:
        app.layout_files["apo75"] = SCENE
        app.load_layout_by_name("apo75")
        insp = _open_3d_inspector(app)
        app._three_d_inspector = insp
        try:
            insp.show_rays_var.set(True)
        except Exception:
            pass

        def shoot(tag: str) -> None:
            insp.refresh_from_editor(force_retrace=True)
            _settle(insp)
            if camera is not None:
                cam = insp._renderer.GetActiveCamera()
                cam.SetPosition(*camera["camera_position"])
                cam.SetFocalPoint(*camera["camera_focal"])
                cam.SetViewUp(*camera["camera_view_up"])
                try:
                    cam.ParallelProjectionOn()
                    cam.SetParallelScale(float(camera["camera_parallel_scale"]) * 1.6)
                except Exception:
                    pass
            else:
                insp._renderer.ResetCamera()
            insp._vtk_widget.GetRenderWindow().Render()
            _settle(insp)
            _save_vtk_snapshot(insp, Path(f"{prefix}_{tag}.png"))
            print(f"  wrote {prefix}_{tag}.png")

        _rows(app, "AS LOADED (Apo75)")
        shoot("1_loaded")

        model = app.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        print(f"\nswap -> {getattr(model, 'title', model)!r}")
        print(f"    status: {app.status_var.get()!r}")
        _debug_tail(app)
        _rows(app, "AFTER THE SWAP (PYRITE 45-85)")
        shoot("2_swapped")

        qe = QuickEstimationService(SimpleNamespace(editor=app))
        for field, tag in ((35.0, "3_fov35"), (55.0, "4_fov55")):
            solved, message = qe.fov_solve("object", "thickness", field, field)
            print(f"\nfov_solve(object, thickness, {field}, {field}) -> {solved}")
            print(f"    {message}")
            _debug_tail(app)
            state = qe.current_state()
            print(f"    readout: fov_full={state.get('fov_full')} |m|={state.get('magnification')}")
            _rows(app, f"AFTER {field:g}x{field:g}")
            shoot(tag)
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "attachment/_0572"))
