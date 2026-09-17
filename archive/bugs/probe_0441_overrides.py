"""bugs/0441: with-system override map before/after BS-add on the frozen scene."""
from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides


def dump_row_fields(app, tag):
    for i, r in enumerate(app.rows):
        if str(getattr(r, "surface", "")) == "Aperture":
            print(
                f"  [{tag}] aperture row {i}: tilt=({float(r.tilt_x):.3f},{float(r.tilt_y):.3f},{float(r.tilt_z):.3f}) "
                f"desp=({float(r.desp_x):.3f},{float(r.desp_y):.3f},{float(r.desp_z):.3f}) axis_move={float(getattr(r, 'axis_move', 0) or 0)}"
            )


def dump_over(app, tag):
    system = app.build_system(require_solids=True, force_rebuild=True)
    ov = optical_solid_output_port_pose_overrides(system, app.rows)
    print(f"--- {tag}: WITH-SYSTEM override rows = {sorted(ov)}")
    for i, e in sorted(ov.items()):
        rot = np.asarray(e.get("rotation"), dtype=float).reshape(3, 3)
        z = rot @ np.array([0.0, 0.0, 1.0])
        row = app.rows[i]
        print(
            f"  row {i} {str(getattr(row, 'surface', '')):9s} "
            f"{str(getattr(row, 'name', ''))[:26]:28s} src={e.get('source_index')} "
            f"frame={e.get('frame_source')} localZ=({z[0]:+.2f},{z[1]:+.2f},{z[2]:+.2f})"
        )


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
        app.load_layout_by_name("az85")
        m1 = next(i for i, r in enumerate(app.rows) if "Promoted" in str(getattr(r, "name", "")))
        app.delete_optical_step_rows([m1])
        dump_row_fields(app, "POST-FREEZE")
        dump_over(app, "POST-FREEZE")
        app.add_beam_splitter_to_led(kind="plate")
        dump_row_fields(app, "POST-BS-ADD")
        dump_over(app, "POST-BS-ADD")
    finally:
        app.destroy()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
