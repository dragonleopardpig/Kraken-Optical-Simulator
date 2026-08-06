"""Reproduce flag_20260806_125028 ("swapped lens, elements dislocate") + its recording.

recording_20260806_125044.json holds exactly two commands after the (unrecorded) swap:
``fov_popup_open{plane:object,row:0}`` and ``fov_solve{plane:object,mode:thickness,23x23}``.

Prints the scene after EACH step -- load, swap, solve -- so the writer that dislocates the
elements is visible rather than inferred:

  * row 0's thickness (the object distance) and every row's station,
  * the promoted BS's ``desp_z`` and world pose (it must stay in its LED housing),
  * the mirror row's gap (the flag shows it EXACTLY doubled: 58.9238 -> 117.8476),
  * the sensor's world pose (the flag has it 14.8 mm PAST the mirror, 0 of 558 rays landing),
  * every ``append_debug`` line the snap loop / illumination hold emitted.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0571_swap_then_solve.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Pyrite85_BS.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"


def _report(editor, tag: str) -> None:
    from KrakenOS.UI.services import row_placement

    stations = editor._row_z_positions()
    print(f"\n--- {tag}")
    print(f"    {'i':>2} {'name':32} {'thick':>10} {'station':>9} {'desp_z':>10} {'pose':>34}")
    for index, row in enumerate(editor.rows):
        pose = np.asarray(row_placement.world_pose(editor, index).position, dtype=float)
        print(
            f"    {index:>2} {str(row.name)[:32]:32} {float(row.thickness):10.4f} "
            f"{stations[index]:9.3f} {float(getattr(row, 'desp_z', 0.0)):10.4f} "
            f"{str(np.round(pose, 3).tolist()):>34}"
        )
    try:
        led = editor._transformed_imported_step_mesh_for_label("led")
        bounds = np.asarray(led.bounds, dtype=float)
        print(f"    LED housing z centre {(bounds[4] + bounds[5]) / 2:.3f}")
    except Exception as exc:
        print(f"    LED housing unavailable ({exc})")


def _debug_tail(editor, count: int = 12) -> None:
    try:
        text = str(editor.debug_text.get("1.0", "end")).splitlines()
    except Exception:
        return
    lines = [l for l in text if ("snap detector iter" in l or "hold illumination unit" in l
                                 or "Center lens body" in l)]
    for line in lines[-count:]:
        print("    |", line.strip())


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    if not LENS_FOLDER.exists():
        print(f"SKIP: {LENS_FOLDER} not present")
        return 0
    from types import SimpleNamespace

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    editor = KrakenLayoutEditor()
    try:
        editor.layout_files["probe"] = SCENE
        editor.load_layout_by_name("probe")
        _report(editor, "AS LOADED")

        model = editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
        print(f"\nswap -> {getattr(model, 'title', model)!r}")
        print(f"    status: {editor.status_var.get()!r}")
        _debug_tail(editor)
        _report(editor, "AFTER THE SWAP")

        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        solved, message = qe.fov_solve("object", "thickness", 23.0, 23.0)
        print(f"\nfov_solve(object, thickness, 23, 23) -> {solved}")
        print(f"    {message}")
        _debug_tail(editor)
        _report(editor, "AFTER THE SOLVE")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
