"""Reproduce flag_20260806_182735 ("changed FOV, lens body detached from surrogate, rays
defocus at sensor") on the scene the flag was recorded on.

The three flags of 2026-08-06 18:25-18:27 are one sequence on ``machine_vision_Apo75.py``:
load (FOV 23x23, focused), swap to the PYRITE 45-85 (FOV reads 15.3x15.3), solve back to 23x23.

bugs/diag_0571_swap_then_solve.py prints rows, stations, desp_z and world poses -- everything
except the one thing these flags are about, the lens STEP BODY. So the detach was invisible to
the diagnostic that certified 0571. This one measures the body against its surrogate:

    attach_err = |(body_after - body_before) - (surrogate_after - surrogate_before)|

which is the drag-path assertion from
``validate_open3d_0524_lens_drag_writes_sections.py`` ("bugs/0527: the STEP body must ride the
assembly"), restated for a SOLVE. It also runs the same slide through the DRAG so the two paths
can be compared directly -- the drag was always correct, which is what makes the asymmetry the
proof.

Run (capped -- one heavy job at a time, the desktop keeps cores):
    taskset -c 0-9 nice -n 15 xvfb-run -a .devenv/state/venv/bin/python bugs/diag_0574_solve_carries_lens_body.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SCENE = PROJECT_ROOT / "attachment" / "machine_vision_Apo75.py"
LENS_FOLDER = PROJECT_ROOT / "attachment" / "Lens" / "PYRITE_45_85_05x-20x_V38_1072517"


def _lens_body_bounds(editor):
    """World bounds of the drawn lens barrel, or None when there is no lens STEP."""
    try:
        mesh = editor._transformed_imported_step_mesh_for_label("lens")
    except Exception:
        return None
    if mesh is None:
        return None
    return np.asarray(mesh.bounds, dtype=float)


def _lens_body_centre(editor):
    bounds = _lens_body_bounds(editor)
    if bounds is None:
        return None
    return np.array(
        [
            (bounds[0] + bounds[1]) / 2.0,
            (bounds[2] + bounds[3]) / 2.0,
            (bounds[4] + bounds[5]) / 2.0,
        ],
        dtype=float,
    )


def _surrogate_datum_mid(editor):
    """World midpoint of the lens surrogate's front/rear datum rows.

    This is the SAME anchor the bugs/0503 relative glue records as
    ``step_glue_reference_datum_mid_xyz``, so "the body rode its surrogate" is measured against
    the quantity the glue itself is defined in terms of.
    """
    try:
        mid = editor._lens_surrogate_datum_mid_world()
    except Exception:
        return None
    if mid is None:
        return None
    return np.asarray(mid, dtype=float).reshape(3)


def _image_leg(editor):
    """Measured mirror -> sensor world leg, the quantity the frozen writer controls."""
    try:
        split = editor._folded_image_conjugate_split()
        geometry = editor._frozen_image_fold_world_geometry(split)
    except Exception:
        return None, None
    if geometry is None:
        return None, None
    try:
        far_gap_row = int(split["far_gap_row"])
        return float(geometry["far"]), far_gap_row
    except Exception:
        return None, None


def _snapshot(editor, tag: str) -> dict:
    from KrakenOS.UI.services import row_placement

    body = _lens_body_centre(editor)
    bounds = _lens_body_bounds(editor)
    datum = _surrogate_datum_mid(editor)
    far, far_row = _image_leg(editor)
    try:
        offset = np.asarray(editor._step_placement_offset_xyz("lens"), dtype=float)
    except Exception:
        offset = None
    sensor = None
    try:
        sensor = np.asarray(row_placement.world_pose(editor, len(editor.rows) - 1).position, dtype=float)
    except Exception:
        pass
    state = {
        "tag": tag,
        "body": body,
        "bounds": bounds,
        "datum": datum,
        "offset": offset,
        "far": far,
        "far_row": far_row,
        "far_gap": None if far_row is None else float(editor.rows[far_row].thickness),
        "sensor": sensor,
    }
    print(f"\n--- {tag}")
    print(f"    surrogate datum mid : {None if datum is None else np.round(datum, 4).tolist()}")
    print(f"    lens body centre    : {None if body is None else np.round(body, 4).tolist()}")
    print(f"    lens body bounds x  : {None if bounds is None else np.round(bounds[:2], 4).tolist()}")
    print(f"    placement offset    : {None if offset is None else np.round(offset, 4).tolist()}")
    if far is not None:
        print(f"    image leg (world)   : {far:.4f} mm   via gap row {far_row} = {state['far_gap']:.4f}")
    if sensor is not None:
        print(f"    sensor world pose   : {np.round(sensor, 4).tolist()}")
    return state


def _attachment(before: dict, after: dict, label: str) -> float:
    """|body motion - surrogate motion|: 0 means the barrel rode its own optics."""
    if before["body"] is None or after["body"] is None:
        print(f"    {label}: no lens STEP body to measure")
        return float("nan")
    if before["datum"] is None or after["datum"] is None:
        print(f"    {label}: no surrogate datums to measure")
        return float("nan")
    d_body = after["body"] - before["body"]
    d_datum = after["datum"] - before["datum"]
    err = float(np.linalg.norm(d_body - d_datum))
    print(
        f"    {label}: body {np.round(d_body, 4).tolist()} vs surrogate "
        f"{np.round(d_datum, 4).tolist()}  ->  attach_err {err:.6f} mm"
    )
    return err


def _debug_tail(editor, count: int = 14) -> None:
    try:
        text = str(editor.debug_text.get("1.0", "end")).splitlines()
    except Exception:
        return
    keys = ("lens leg slide", "fold arm slide", "snap detector iter", "Center lens body",
            "image leg", "frozen image")
    lines = [l for l in text if any(k in l for k in keys)]
    for line in lines[-count:]:
        print("    |", line.strip())


def _fresh_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor.layout_files["probe"] = SCENE
    editor.load_layout_by_name("probe")
    editor.swap_imaging_lens_from_folder(str(LENS_FOLDER), refresh=False)
    return editor


def main() -> int:
    if not SCENE.exists():
        print(f"SKIP: {SCENE} not present")
        return 0
    if not LENS_FOLDER.exists():
        print(f"SKIP: {LENS_FOLDER} not present")
        return 0
    from types import SimpleNamespace

    from KrakenOS.UI.services.quick_estimation import QuickEstimationService

    failures: list[str] = []

    # ---------------------------------------------------------------- the SOLVE (the flag)
    editor = _fresh_editor()
    try:
        before = _snapshot(editor, "AFTER THE SWAP (flag 2)")
        qe = QuickEstimationService(SimpleNamespace(editor=editor))
        solved, message = qe.fov_solve("object", "thickness", 23.0, 23.0)
        print(f"\nfov_solve(object, thickness, 23, 23) -> {solved}")
        print(f"    {message}")
        _debug_tail(editor)
        after = _snapshot(editor, "AFTER THE SOLVE (flag 3)")
        print("\n  SOLVE attachment")
        solve_err = _attachment(before, after, "solve")
        if not (solve_err == solve_err and solve_err < 0.05):
            failures.append(f"solve attach_err {solve_err:.6f} mm (want < 0.05)")
        # The image side must move the sensor TOWARD the mirror when the lens moves toward it.
        if before["far"] is not None and after["far"] is not None:
            print(f"\n  image leg {before['far']:.4f} -> {after['far']:.4f} mm "
                  f"(delta {after['far'] - before['far']:+.4f})")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass

    # ---------------------------------------------------------------- the DRAG (the control)
    editor = _fresh_editor()
    try:
        before = _snapshot(editor, "AFTER THE SWAP (drag control)")
        plan = editor._lens_leg_slide_plan()
        if plan is None or not plan[2]:
            print("    no lens fold leg -- drag control skipped")
        else:
            _members, direction, _ = plan
            delta = np.asarray(direction, dtype=float).reshape(3) * 28.4622
            editor.translate_step_overlay("lens", tuple(float(v) for v in delta), record_history=False)
            after = _snapshot(editor, "AFTER AN EQUAL DRAG")
            print("\n  DRAG attachment (this path was always correct)")
            drag_err = _attachment(before, after, "drag")
            if not (drag_err == drag_err and drag_err < 0.05):
                failures.append(f"drag attach_err {drag_err:.6f} mm (want < 0.05)")
    finally:
        try:
            editor.destroy()
        except Exception:
            pass

    print("\n" + "=" * 72)
    if failures:
        for line in failures:
            print(f"FAIL: {line}")
        return 1
    print("PASS: the lens body rides its surrogate through both a drag and a solve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
