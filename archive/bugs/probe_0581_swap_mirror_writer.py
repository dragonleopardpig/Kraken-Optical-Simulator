"""bugs/0581: WHO parks the fold mirror inside the lens block during the ELS-85 swap?

State entering the swap (after 55x55 + far=30 pin): prism row 7 at world x 334.37, lens block
rows at x ~228..284. After the swap the prism reads x 281.76 -- inside the block. The 0581
Safe-gap guard in _apply_frozen_image_split did not fire, so the write goes through some other
path. Wrap every desp-writing method with a tracer that prints row 7's desp/world before and
after, and run the exact sequence. The caller that moves row 7 names itself.

Run (capped): taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/probe_0581_swap_mirror_writer.py
"""
from __future__ import annotations

import functools
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
PYRITE = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"
ELS85 = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"

TRACED = [
    "slide_fold_arm_along_leg",
    "slide_lens_block_along_its_leg",
    "_rebake_frozen_row_world_center",
    "_fold_slide_carry_apply",
    "translate_scene_row_pose_vector",
    "_apply_near_leg_delta",
    "_apply_frozen_image_split",
    "_apply_folded_image_split",
    "apply_image_distance_frozen_aware",
    "snap_detector_to_image_plane",
    "_swap_reseat_preserved_rows",
    "_swap_auto_refocus_to_best_focus",
    "restore_glued_illumination_unit_world_poses",
    # second sweep: the swap's own internal steps
    "_apply_swapped_lens_step_settings",
    "_auto_assign_missing_elements",
    "_normalize_special_rows",
    "_swap_apply_frozen_block_frame",
    "_swap_downstream_gap",
    "_swap_frozen_block_frame",
    "center_lens_body_on_surrogate_axis",
    "_sync_table",
    "_read_rows_from_table",
    "_commit_pending_table_edit",
]


def _row7(app) -> str:
    from KrakenOS.UI.services import row_placement

    r = app.rows[7]
    pose = np.asarray(row_placement.world_pose(app, 7).position, dtype=float)
    return (f"row7 desp=({float(r.desp_x):.4f},{float(r.desp_z):.4f}) "
            f"th={float(r.thickness):.4f} world=({pose[0]:.4f},{pose[2]:.4f}) "
            f"| th6={float(app.rows[6].thickness):.4f}")


def _arm(app) -> None:
    depth = {"n": 0}

    def _wrap(name, fn):
        @functools.wraps(fn)
        def inner(*a, **k):
            before = _row7(app)
            depth["n"] += 1
            try:
                return fn(*a, **k)
            finally:
                depth["n"] -= 1
                after = _row7(app)
                if before != after:
                    pad = "  " * depth["n"]
                    print(f"{pad}>> {name} MOVED row7:\n{pad}   {before}\n{pad}   {after}", flush=True)
        return inner

    for name in TRACED:
        fn = getattr(app, name, None)
        if callable(fn):
            setattr(app, name, _wrap(name, fn))

    # Module-level writers the instance sweep cannot see.
    import KrakenOS.UI.nonseq_output_ports as ports

    for mod_name in ("carry_free_placed_followers_after_fold",):
        mod_fn = getattr(ports, mod_name, None)
        if callable(mod_fn):
            setattr(ports, mod_name, _wrap(f"ports.{mod_name}", mod_fn))


def main() -> int:
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        qe = inspector._quick_estimation_service()
        app.swap_imaging_lens_from_folder(str(PYRITE), refresh=False)
        qe.fov_solve("object", "thickness", 55.0, 55.0, None)
        app._apply_folded_image_split("far", 30.0)
        print("STATE BEFORE ELS SWAP:", _row7(app))
        _arm(app)
        print("\n================ ELS-85 SWAP ================")
        app.swap_imaging_lens_from_folder(str(ELS85), refresh=False)
        print("\nSTATE AFTER ELS SWAP:", _row7(app))
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
