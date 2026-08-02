"""bugs/0508 A -- generality probe: is the built-system image double-advance
specific to machine_vision_AZ85_RA_Mirror_BS.py, or does any scene whose
mid-chain solid slides laterally past ray reachability reproduce it?

ONE CONFIG PER PROCESS (a fresh interpreter per measurement -- the literal
"fresh load + one raw desp edit" shape of the doc's one-line repro, and it
sidesteps the Tk destroy/re-init hang a multi-editor process risks).

    python -u bugs/probe_0508a_generality.py <scene_key>                  # baseline + row inventory
    python -u bugs/probe_0508a_generality.py <scene_key> <row|auto> <axis> <delta>

Compare the MODEL image pose (row_world_pose) against the BUILT SYSTEM image
pose (TRANS_2A[-1]). The 0508 signature: the MODEL holds while the SYSTEM
image drops by ~one extra gap along the leg.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SCENES = {
    "az85_bs": Path("attachment/machine_vision_AZ85_RA_Mirror_BS.py"),
    "az85_periscope": Path("KrakenOS/common_optical_layouts/machine_vision_AZ85_RA_Mirror.py"),
    "gn150_straight": Path("attachment/machine_vision_150mm_GN.py"),
}


def promoted_solid_rows(editor) -> list[int]:
    out = []
    for i, row in enumerate(editor.rows):
        adv = getattr(row, "advanced", None)
        if isinstance(adv, dict) and adv.get("OpticalSolidFaces"):
            out.append(i)
    return out


def main() -> None:
    scene_key = sys.argv[1]
    scene = SCENES[scene_key]
    if not scene.exists():
        print(f"RESULT {scene_key} SKIP missing {scene}", flush=True)
        return

    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.services import optical_axis_tree as tree_mod

    editor = KrakenLayoutEditor()
    editor.layout_files["probe"] = scene
    editor.load_layout_by_name("probe")

    solids = promoted_solid_rows(editor)
    label = "baseline"
    if len(sys.argv) > 2:
        row_arg, axis, delta = sys.argv[2], sys.argv[3], float(sys.argv[4])
        r = solids[0] if row_arg == "auto" else int(row_arg)
        setattr(editor.rows[r], axis, float(getattr(editor.rows[r], axis)) + delta)
        label = f"rows[{r}].{axis}{delta:+g}"
    else:
        for i, row in enumerate(editor.rows):
            print(
                f"ROW {scene_key} {i:2d} {type(row).__name__:14s} "
                f"name={getattr(row, 'name', '?')!s:28s} th={float(getattr(row, 'thickness', 0.0)):9.3f} "
                f"desp=({float(getattr(row, 'desp_x', 0.0)):7.2f},{float(getattr(row, 'desp_y', 0.0)):7.2f},"
                f"{float(getattr(row, 'desp_z', 0.0)):7.2f}) solid={i in solids}",
                flush=True,
            )

    image_idx = len(editor.rows) - 1
    model = np.asarray(tree_mod.row_world_pose(editor.rows, image_idx), dtype=float).reshape(-1)[:3]
    system, _, _ = editor._build_preview_system_rays_bundle(
        update_state=False, include_live_step_overlays=False
    )
    built = np.asarray(system.TRANS_2A[image_idx], dtype=float)[:3, 3].reshape(3)
    print(
        f"RESULT {scene_key} {label} solids={solids} "
        f"model=({model[0]:.3f},{model[1]:.3f},{model[2]:.3f}) "
        f"built=({built[0]:.3f},{built[1]:.3f},{built[2]:.3f})",
        flush=True,
    )


if __name__ == "__main__":
    main()
