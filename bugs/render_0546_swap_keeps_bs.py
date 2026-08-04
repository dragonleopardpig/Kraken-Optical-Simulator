"""bugs/0546 + 0547 in-app check -- run the REAL "Swap Imaging Lens from Folder" on the flagged
AZ85 + RA-mirror + BS scene, snapshot before/after from the flag's own viewpoint, and print
every row's WORLD pose on both sides.

bugs/0546: the swap used to refuse this scene outright ("no imaging-lens surrogate ... to
swap") because the promoted BS cube's ROW sat inside the front/rear datum span. It must now run
and leave every promoted solid exactly where it was.

bugs/0547 (flag_20260804_212159): with the swap unblocked, the replacement block lands on the
STRAIGHT global axis instead of the frozen (0433) fold leg the old block was baked onto -- "the
surrogate is snapped to another axis".  The pose table below is the evidence.

Run:  xvfb-run -a .devenv/state/venv/bin/python bugs/render_0546_swap_keeps_bs.py /tmp/0546
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py")
FLAG = Path("attachment/recorded_bug_repros/flag_20260804_212159_302/state.json")
# The folder the user actually swapped to in flag_20260804_212159. Override with argv[2] --
# passing the scene's OWN lens (ELS-85-4.5V16K) is the identity test: swapping a lens for itself
# must leave the scene numerically and visually unchanged, which separates "the swap machinery is
# wrong" from "this replacement lens genuinely images somewhere else".
REPLACEMENT = Path("attachment/Lens/0703-005-000-40-EXC")


def _row_poses(app):
    """(index, name, world pose, station) for every row -- pose = (desp_x, desp_y, station+desp_z)."""
    stations = app._row_z_positions()
    out = []
    for index, row in enumerate(app.rows):
        station = float(stations[index]) if index < len(stations) else 0.0
        out.append(
            (
                index,
                str(getattr(row, "name", "")),
                (
                    float(getattr(row, "desp_x", 0.0) or 0.0),
                    float(getattr(row, "desp_y", 0.0) or 0.0),
                    station + float(getattr(row, "desp_z", 0.0) or 0.0),
                ),
                station,
                (
                    float(getattr(row, "tilt_x", 0.0) or 0.0),
                    float(getattr(row, "tilt_y", 0.0) or 0.0),
                    float(getattr(row, "tilt_z", 0.0) or 0.0),
                ),
            )
        )
    return out


def _print_poses(tag, poses):
    print(f"\n{tag}")
    print(f"  {'row':<4}{'station':>10}{'pose x':>12}{'pose y':>9}{'pose z':>10}   {'tilt':<22}name")
    for index, name, pose, station, tilt in poses:
        print(
            f"  S{index:<3}{station:>10.3f}{pose[0]:>12.3f}{pose[1]:>9.3f}{pose[2]:>10.3f}   "
            f"{str(tuple(round(v, 1) for v in tilt)):<22}{name}"
        )


def main(out_prefix: str, replacement: Path = REPLACEMENT) -> int:
    from KrakenOS.UI.capture_open3d_step_workflow_screenshots import (
        _open_3d_inspector,
        _save_vtk_snapshot,
        _settle,
    )
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    failures: list[str] = []
    try:
        app.layout_files["az85_bs"] = SCENE
        app.load_layout_by_name("az85_bs")
        insp = _open_3d_inspector(app)
        insp.refresh_from_editor(sampling_mode=app._preview_3d_sampling_mode(), force_retrace=True)
        _settle(insp)
        app._three_d_inspector = insp

        flag = json.loads(FLAG.read_text())["scene_state"]
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
        _save_vtk_snapshot(insp, Path(f"{out_prefix}_before.png"))
        print(f"wrote {out_prefix}_before.png")

        before = _row_poses(app)
        _print_poses("ROW POSES BEFORE the swap:", before)
        front, rear = app._imaging_lens_block_indices()
        print(f"\nlens block: ({front}, {rear})")
        if front is None:
            failures.append("bugs/0546: the swap is still refused -- block not detected")
            return _report(failures)

        model = app.swap_imaging_lens_from_folder(str(replacement), refresh=True)
        if model is None:
            failures.append(f"swap returned None for {replacement}")
            return _report(failures)
        print(f"\nswapped in: {getattr(model, 'title', '?')} (EFL {getattr(model, 'effl', float('nan')):.4g} mm)")
        print(f"status: {app.status_var.get()}")

        after = _row_poses(app)
        _print_poses("ROW POSES AFTER the swap:", after)

        # bugs/0546 -- every promoted solid must hold its world pose.
        def _promoted(poses):
            return [p for p in poses if app._is_swap_preservable_block_row(app.rows[0]) or "promoted" in p[1].lower()]

        prom_before = [p for p in before if "promoted" in p[1].lower()]
        prom_after = [p for p in after if "promoted" in p[1].lower()]
        if len(prom_before) != len(prom_after):
            failures.append(f"bugs/0546: promoted solid count {len(prom_before)} -> {len(prom_after)}")
        else:
            for (i0, name, pose0, _s0, _t0), (i1, _n1, pose1, _s1, _t1) in zip(prom_before, prom_after):
                drift = max(abs(a - b) for a, b in zip(pose0, pose1))
                print(f"  promoted S{i0} -> S{i1}: max pose drift {drift:.3e} mm  "
                      f"[{'OK' if drift <= 1e-6 else 'MOVED'}]")
                if drift > 1e-6:
                    failures.append(f"bugs/0546: {name} (S{i0}->S{i1}) moved by {drift:.4g} mm")

        # bugs/0547 -- the replacement block must stay on the leg the old block was baked onto.
        new_front, new_rear = app._imaging_lens_block_indices()
        if new_front is not None:
            old_front_pose = before[front][2]
            new_front_pose = after[new_front][2]
            drift = max(abs(a - b) for a, b in zip(old_front_pose, new_front_pose))
            print(
                f"\n  front datum: {tuple(round(v, 3) for v in old_front_pose)} -> "
                f"{tuple(round(v, 3) for v in new_front_pose)}  (drift {drift:.4g} mm)"
            )
            if drift > 1e-6:
                failures.append(
                    f"bugs/0547: the swapped block left the frozen leg -- front datum moved "
                    f"{drift:.4g} mm ({tuple(round(v, 3) for v in old_front_pose)} -> "
                    f"{tuple(round(v, 3) for v in new_front_pose)})"
                )

        insp.refresh_from_editor(force_retrace=True)
        _settle(insp)
        _save_vtk_snapshot(insp, Path(f"{out_prefix}_after.png"))
        print(f"wrote {out_prefix}_after.png")
    finally:
        try:
            app.destroy()
        except Exception:
            pass
    return _report(failures)


def _report(failures: list[str]) -> int:
    print()
    if failures:
        print("0546/0547 in-app check FAILED:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("0546/0547 in-app check passed: the swap ran, every promoted solid held its world pose, "
          "and the replacement block stayed on the frozen leg.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(
        sys.argv[1] if len(sys.argv) > 1 else "/tmp/0546",
        Path(sys.argv[2]) if len(sys.argv) > 2 else REPLACEMENT,
    ))
