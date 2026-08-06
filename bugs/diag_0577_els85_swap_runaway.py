"""Reproduce flag_20260806_210207 + flag_20260806_210424 -- "swapped again with ELS85 lens,
everything go heywire again" then "solve for FOV 23x23".

Different scene and different lens from the 0574/0575/0576 flags: machine_vision_Pyrite85_BS.py
with attachment/Lens/ELS-85-4.5V16K. What the two flag states record:

  after the swap : rows 1..5 world X 228.74..283.74, lens body X [228.39, 287.59] (ATTACHED),
                   row7 thickness 60.039, sensor world z 84.32, fold mirror z ~49.27
                   -> the mirror->sensor leg is NEGATIVE (~ -35 mm): the sensor is BEHIND the
                      fold mirror. 0 of 558 rays reach it.
  after the solve: rows 1..5 world X 99.32..154.32, lens body X [98.98, 158.17] (still ATTACHED),
                   row7 thickness 2571.3701, sensor world z 2595.64, camera body z 2533..2607
                   -> the sensor is flung 2.5 METRES down a machine whose whole leg budget is
                      ~130 mm. 0 rays, 1 missed_image.

So the bugs/0574 body carry holds on this scene (the barrel tracked the surrogate through both
steps), and the IMAGE side is what breaks. This probe prints the leg sign at every stage plus the
snap loop's own iteration log, so the runaway is visible rather than inferred.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0577_els85_swap_runaway.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "ELS-85-4.5V16K"


def _report(app, tag: str) -> None:
    from KrakenOS.UI.services import row_placement

    print(f"\n{'=' * 74}\n{tag}")
    try:
        split = app._folded_image_conjugate_split() or {}
        geometry = app._frozen_image_fold_world_geometry(split)
    except Exception as exc:
        split, geometry = {}, None
        print(f"    split/geometry raised {type(exc).__name__}: {exc}")
    far_row = split.get("far_gap_row")
    if geometry is not None:
        far = float(geometry["far"])
        gap = float(app.rows[int(far_row)].thickness)
        print(f"    far gap row {far_row}: thickness {gap:.4f}")
        print(f"    mirror->sensor WORLD leg : {far:+.4f} mm"
              f"{'   <-- NEGATIVE: the sensor is behind its fold mirror' if far <= 0 else ''}")
        print(f"    leg budget const         : {gap + far:.4f} mm")
    else:
        print("    no frozen image-side fold geometry")

    try:
        sensor = np.asarray(row_placement.world_pose(app, len(app.rows) - 1).position, dtype=float)
        print(f"    sensor world pose        : {np.round(sensor, 3).tolist()}")
    except Exception:
        pass
    try:
        mesh = app._transformed_imported_step_mesh_for_label("lens")
        b = np.asarray(mesh.bounds, dtype=float)
        mid = app._lens_surrogate_datum_mid_world()
        print(f"    lens body bounds x       : {np.round(b[:2], 4).tolist()}")
        print(f"    surrogate datum mid      : {None if mid is None else np.round(np.asarray(mid), 4).tolist()}")
    except Exception as exc:
        print(f"    lens body unavailable ({type(exc).__name__})")
    try:
        cam = app._transformed_imported_step_mesh_for_label("camera")
        cb = np.asarray(cam.bounds, dtype=float)
        print(f"    camera body bounds z     : {np.round(cb[4:6], 3).tolist()}")
    except Exception:
        pass

    print("    best-focus estimators:")
    for name, fn in (("straight equivalent", "_real_ray_best_focus_shift_for_rows"),
                     ("traced bundle      ", "_traced_bundle_best_focus_shift")):
        try:
            print(f"      {name}: {getattr(app, fn)()}")
        except Exception as exc:
            print(f"      {name}: raised {type(exc).__name__}: {exc}")


def _debug_tail(app, count: int = 22) -> None:
    try:
        text = str(app.debug_text.get("1.0", "end")).splitlines()
    except Exception:
        return
    keys = ("snap detector iter", "lens leg slide", "fold arm slide", "Center lens body",
            "image delta re-measured", "deferred", "swap", "clearance")
    lines = [l for l in text if any(k in l for k in keys)]
    for line in lines[-count:]:
        print("    |", line.strip())


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    if not LENS_FOLDER.exists():
        print(f"SKIP: {LENS_FOLDER} not present")
        return 0

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.validate_open3d_penta_telescope_comprehensive import _open_inspector

    app = KrakenLayoutEditor()
    try:
        app.layout_files["scene"] = SCENE
        app.load_layout_by_name("scene")
        inspector = _open_inspector(app)
        _report(app, "AS LOADED (Pyrite85_BS)")

        model = app.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        print(f"\nswap -> {getattr(model, 'title', model)!r}")
        print(f"    status: {app.status_var.get()!r}")
        _debug_tail(app)
        _report(app, "AFTER THE ELS-85 SWAP (flag 210207)")

        solved, message = inspector._quick_estimation_service().fov_solve(
            "object", "thickness", 23.0, 23.0, None
        )
        print(f"\nfov_solve(object, thickness, 23, 23) -> {solved}\n    {message}")
        _debug_tail(app)
        _report(app, "AFTER THE SOLVE (flag 210424)")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
