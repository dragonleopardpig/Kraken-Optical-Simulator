from pathlib import Path

import numpy as np


def main():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor
    from KrakenOS.UI.nonseq_output_ports import (
        _row_has_optical_solid,
        build_optical_solid_output_port_pose_overrides,
        optical_solid_face_world_records,
        row_z_positions,
        select_optical_solid_explicit_input_face,
        select_optical_solid_explicit_output_face,
        select_optical_solid_output_face,
    )

    for scene, label in (("attachment/om05a_folded.py", "mine"),
                         ("attachment/machine_vision_Pyrite85.py", "reference")):
        editor = KrakenLayoutEditor()
        editor._prompt_for_missing_cad_assets = lambda: None
        editor.layout_files["p"] = Path(scene).resolve()
        editor.load_layout_by_name("p")
        rows = editor.rows
        zs = row_z_positions(rows)
        print(f"== {label}")
        for i, row in enumerate(rows):
            if not _row_has_optical_solid(row):
                continue
            try:
                world = optical_solid_face_world_records(row, float(zs[i]), assigned_only=True)
            except Exception as exc:
                print(f"  row {i} {row.name}: world records FAILED: {exc}")
                continue
            out = select_optical_solid_output_face(world)
            eout = select_optical_solid_explicit_output_face(world)
            ein = select_optical_solid_explicit_input_face(world)
            print(f"  row {i} {str(row.name)[:36]:36s} assigned={len(world or [])} "
                  f"output={'Y' if out else '-'} explicit_out={'Y' if eout else '-'} explicit_in={'Y' if ein else '-'}")
            for rec in (world or [])[:4]:
                print(f"      {rec.get('face_id')} fn={rec.get('function')} port={rec.get('port_role')} "
                      f"n={np.round(np.asarray(rec.get('world_normal', rec.get('normal')) or [0,0,0], dtype=float),3)}")
        overrides = build_optical_solid_output_port_pose_overrides(rows)
        print(f"  pose overrides (no system): {list(overrides.keys())}")
        editor.destroy()


if __name__ == "__main__":
    main()
