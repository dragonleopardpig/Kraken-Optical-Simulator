"""0689 (flag 211438 + live follow-ups): seat the shared lens + sensor on the VENDOR
axis z=-25 (the part symmetry plane).

The two centre-flank windows tile the column and MEET at z=-25: the lens axis is
the split line and each arm rides its own half BY DESIGN. Our chain-posed lens
rode arm A's beam (z=-15.8), so arm B crossed the stop ~19 mm off-axis and 934 of
its 1083 rays died there ("side-B rays none reach the sensor").

Mechanism v2: a DECENTER WITHIN THE FOLDED FRAME. `_downstream_pose_from_frame`
poses every walk follower at `frame_origin + frame_rotation @ desp` -- so setting
each lens/filter/sensor row's desp to R.T @ (world shift onto z=-25) moves the
element in both the trace and the display through the standard pathway. (v1 tried
the 0433 absolute bake: un-overridden STANDARD rows do not pose cleanly inside a
folded non-seq scene -- rays looped at the filter.)

Also: mirror_bound_y 8 -> 5.2 (the cyan "leak" fan = mirrored launch overspill
beyond the BS acceptance window).
"""
import os
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")
AXIS_Z = -25.0
# bugs/0690: the launch cones must aim at the OFF-AXIS shared pupil (the fold
# parity maps a launch-frame y offset onto the column z where the pupil sits).
AIM_OFF_Y = float(os.environ.get("KRAKEN_0690_AIM_Y", "-9.46"))
# ONLY the first row of the contiguous follower block: the walk's carried frame
# ADVANCES FROM EACH POSED ROW'S CENTRE (nonseq_output_ports ~2321), so a desp on
# every row COMPOUNDS (-9.46 x 7 = the v2 failure); one desp shifts the whole
# downstream train -- lens, filter, mirror-2 fold, image -- onto the new axis.
SEAT_ROWS = ("Front Optical Vertex Datum",)


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import build_optical_solid_output_port_pose_overrides

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    overrides = build_optical_solid_output_port_pose_overrides(editor.rows)
    for index, row in enumerate(editor.rows):
        name = str(row.name)
        if name not in SEAT_ROWS:
            continue
        entry = overrides.get(index)
        assert isinstance(entry, dict), f"{name}: no walk override"
        centre = np.asarray(entry["center"], dtype=float)
        rotation = np.asarray(entry["rotation"], dtype=float)
        current_desp = np.asarray(
            (float(row.desp_x or 0.0), float(row.desp_y or 0.0), float(row.desp_z or 0.0)),
            dtype=float,
        )
        frame_origin = centre - rotation @ current_desp
        desired = centre.copy()
        desired[2] = AXIS_Z
        local = rotation.T @ (desired - frame_origin)
        row.desp_x, row.desp_y, row.desp_z = (float(v) for v in local)
        print(f"  {name}: world {np.round(centre,2).tolist()} -> z={AXIS_Z} via frame desp "
              f"{np.round(local, 3).tolist()}")

    specs = list(getattr(editor, "layout_scene_source_specs", []) or [])
    for spec in specs:
        if str(spec.get("source_id", "")) == "source:faceB":
            spec["mirror_bound_y"] = 5.2
    editor.layout_scene_source_specs = specs
    editor.layout_launch_pupil_aim_offset = [0.0, AIM_OFF_Y]

    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)


def verify():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")
    editor._preview_trace_deferred_until_requested = False
    system, rays, bundle = editor._build_preview_system_rays_bundle(trace_rays=True)
    a_ends, b_ends = [], []
    n_a = n_b = 0
    for rp in (bundle.ray_paths or []):
        sid = str(getattr(rp, "source_id", "") or "")
        p = np.asarray(rp.points_world, dtype=float)
        if p.ndim != 2 or not np.all(np.isfinite(p[-1])):
            continue
        e = p[-1]
        if sid == "source:faceB":
            n_b += 1
            if abs(e[0] + 272.65) < 25 and abs(e[1] + 11.4) < 2:
                b_ends.append(e)
        else:
            n_a += 1
            if bool(getattr(rp, "reaches_image", False)):
                a_ends.append(e)
    A = np.asarray(a_ends) if a_ends else np.zeros((0, 3))
    B = np.asarray(b_ends) if b_ends else np.zeros((0, 3))
    msg = f"VERIFY chain {n_a}/{len(A)}"
    if len(A):
        msg += f" strip z {A[:,2].min():.1f}..{A[:,2].max():.1f} y {A[:,1].mean():.2f}"
    msg += f" | faceB {n_b}/{len(B)}"
    if len(B):
        msg += f" strip z {B[:,2].min():.1f}..{B[:,2].max():.1f} y {B[:,1].mean():.2f}"
    print(msg)
    editor.destroy()


if __name__ == "__main__":
    main()
    verify()
