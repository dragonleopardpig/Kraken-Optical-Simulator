"""0695 stage 3b: refresh the already-stamped rows from the REBUILT meshes
(first-surface window mirror, cement-gapped far halves and centre halves).
Keys by the NEW row names; keeps the seat/refocus edits intact."""
import json
from pathlib import Path

import numpy as np

SCENE = Path("attachment/om05a_folded.py")
COMP = Path("attachment/om05a_components")
MANIFEST = json.loads((COMP / "manifest_0695v.json").read_text())

TARGETS = {
    "First RA mirror A": ("ra_mirror_A_0695v", (0.0, 0.25, 8.88)),
    "BS cube A": ("bs_near_A_0695v", (0.0, 10.89, 8.88)),
    "Centre RA mirror A": ("centre_half_A_0695v", (0.0, 10.89, -15.92)),
    "First RA mirror B": ("ra_mirror_B_0695v", (0.0, 0.25, -58.88)),
    "BS cube B": ("bs_near_B_0695v", (0.0, 10.89, -58.88)),
    "Centre RA mirror B": ("centre_half_B_0695v", (0.0, 10.89, -34.08)),
    "BS cube A (far half)": ("bs_far_A_0695v", None),
    "BS cube B (far half)": ("bs_far_B_0695v", None),
}


def main():
    import importlib.util
    spec = importlib.util.spec_from_file_location("apply0695", "bugs/0695_apply_vendor_prisms.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import row_z_positions

    editor = KrakenLayoutEditor()
    editor._prompt_for_missing_cad_assets = lambda: None
    editor.layout_files["p"] = SCENE.resolve()
    editor.load_layout_by_name("p")

    for index, row in enumerate(list(editor.rows)):
        name = str(row.name)
        if name not in TARGETS:
            continue
        mesh_name, fold_point = TARGETS[name]
        centre = np.asarray(MANIFEST[mesh_name], dtype=float)
        fresh = m.new_solid_row(editor, mesh_name)
        row.element = fresh.element
        adv = dict(row.advanced or {})
        fresh_adv = dict(fresh.advanced or {})
        for key in ("Solid_3d_stl", "OpticalSolidSourcePath", "OpticalSolidSourceFormat",
                    "OpticalSolidFaces", "Note"):
            if key in fresh_adv:
                adv[key] = fresh_adv[key]
        adv["StepOverlayPromotion"] = {"center_world": centre.tolist()}
        row.advanced = adv
        m.flag_faces(row, fold_point, centre)
        zs = row_z_positions(editor.rows)
        z_station = float(zs[index]) if index < len(zs) else 0.0
        row.desp_x, row.desp_y = float(centre[0]), float(centre[1])
        row.desp_z = float(centre[2]) - z_station
        print(f"  remeshed {name} at {np.round(centre, 2).tolist()}")

    editor._sync_table()
    editor._write_layout_file(SCENE.resolve())
    editor.destroy()
    print("saved", SCENE)
    m.verify()


if __name__ == "__main__":
    main()
