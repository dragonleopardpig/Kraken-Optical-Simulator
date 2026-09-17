"""bugs/0528 diagnostic -- flag_20260803_203614: "the FOV changed after lens dragged, but
the rays are defocus, I think FOV not changed fully enough."

Replicates the user's net lens drag on the frozen AZ85 scene (recovered from the recorded
overlay pose), runs the 0520 commit refocus (snap_detector_to_image_plane), and measures
the residual defocus + FOV readout at every stage.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260803_203614_458/state.json")


class _Shim:
    def __init__(self, editor):
        self.editor = editor


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import optical_axis_tree as tree_mod
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    flag = json.loads(FLAG.read_text())
    user_lens = np.asarray(flag["scene_state"]["step_overlay_poses"]["lens"]["placement_offset_xyz"], float)
    user_cam = np.asarray(flag["scene_state"]["step_overlay_poses"]["camera"]["placement_offset_xyz"], float)

    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        qe = QuickEstimationService(_Shim(app))

        def _pose(i):
            return np.asarray(tree_mod.row_world_pose(app.rows, i), float).reshape(-1)[:3]

        def _report(tag):
            state = qe.current_state()
            try:
                rr = app._real_ray_best_focus_shift_for_rows()
            except Exception as exc:
                rr = f"ERR {exc!r}"
            try:
                tb = app._traced_bundle_best_focus_shift()
            except Exception as exc:
                tb = f"ERR {exc!r}"
            print(f"[{tag}]")
            print(f"  gaps           = {[round(float(r.thickness), 3) for r in app.rows]}")
            print(f"  lens offset    = {np.round(np.asarray(app._step_placement_offset_xyz('lens'), float), 3).tolist()}")
            print(f"  cam offset     = {np.round(np.asarray(app._step_placement_offset_xyz('camera'), float), 3).tolist()}")
            print(f"  sensor pose    = {np.round(_pose(len(app.rows) - 1), 3).tolist()}")
            print(f"  fov_full       = {state.get('fov_full')}  in_focus={state.get('in_focus')}")
            keys = [k for k in state.keys() if 'fov' in str(k).lower() or 'focus' in str(k).lower() or 'mag' in str(k).lower()]
            print(f"  qe fields      = {{{', '.join(f'{k}: {state.get(k)}' for k in sorted(keys))}}}")
            print(f"  real-ray shift = {rr}")
            print(f"  bundle shift   = {tb}")
            print(f"  status         = {app.status_var.get()!r}")
            return state

        print(f"user lens offset (flag) = {user_lens.tolist()}")
        print(f"user cam  offset (flag) = {user_cam.tolist()}")
        _report("fresh load")
        o0 = np.asarray(app._step_placement_offset_xyz("lens"), float)

        # Calibrate offset-space motion per unit world +x drag, then replicate the net drag.
        app.translate_step_overlay("lens", (1.0, 0.0, 0.0))
        o1 = np.asarray(app._step_placement_offset_xyz("lens"), float)
        per_unit = o1 - o0
        moving = int(np.argmax(np.abs(per_unit)))
        need = float((user_lens - o1)[moving] / per_unit[moving])
        print(f"\ncalibration: per-unit offset delta {np.round(per_unit, 4).tolist()}, "
              f"moving comp {moving}, remaining drag {need:+.3f} world-x")
        app.translate_step_overlay("lens", (need, 0.0, 0.0))
        o2 = np.asarray(app._step_placement_offset_xyz("lens"), float)
        print(f"replicated lens offset  = {np.round(o2, 3).tolist()}  (target {user_lens.tolist()})")
        _report("after drag (pre-snap)")

        moved = bool(app.snap_detector_to_image_plane())
        print(f"\nsnap_detector_to_image_plane -> {moved}")
        _report("after snap 1")

        # What would MORE iterations buy? Run the snap repeatedly to convergence.
        for i in range(2, 6):
            moved = bool(app.snap_detector_to_image_plane())
            print(f"\nsnap #{i} -> {moved}")
            _report(f"after snap {i}")
            if not moved:
                break
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
