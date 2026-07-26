"""Diagnostic for bugs/0435: what exactly moves when add_beam_splitter_to_led runs
on the pristine folded AZ85 scene (flag_20260726_094845_383: chain +62.5 z, aperture
flips to straight, camera +62.5; then the mirror delete silently fails)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def snap(app, tag):
    print(f"\n=== {tag} ===")
    z = app._row_z_positions()
    overrides = optical_solid_output_port_pose_overrides(None, app.rows)
    for i, row in enumerate(app.rows):
        st = float(z[i]) if i < len(z) else float("nan")
        ov = overrides.get(i)
        if isinstance(ov, dict):
            c = np.asarray(ov.get("center"), dtype=float).reshape(3)
            r = np.asarray(ov.get("rotation"), dtype=float).reshape(3, 3)
            zdir = r @ np.array([0.0, 0.0, 1.0])
            ovs = f"ov_center=({c[0]:8.2f},{c[1]:6.2f},{c[2]:8.2f}) ov_zdir=({zdir[0]:5.2f},{zdir[1]:5.2f},{zdir[2]:5.2f}) src={ov.get('frame_source','')}"
        else:
            ovs = "ov=None"
        print(
            f"S{i}: {str(getattr(row,'name',''))[:34]:36s} thk={float(getattr(row,'thickness',0) or 0):8.3f} "
            f"st={st:8.2f} desp=({float(row.desp_x):7.2f},{float(row.desp_y):5.1f},{float(row.desp_z):8.2f}) "
            f"tilt=({float(row.tilt_x):5.1f},{float(row.tilt_y):6.1f},{float(row.tilt_z):6.1f}) {ovs}"
        )
    for label in ("lens", "camera", "led", "optical"):
        try:
            mesh = app._transformed_imported_step_mesh_for_label(label)
        except Exception:
            mesh = None
        if mesh is not None and int(getattr(mesh, "n_points", 0)) > 0:
            b = np.asarray(mesh.bounds, dtype=float)
            print(f"  step[{label}]: center=({(b[0]+b[1])/2:7.2f},{(b[2]+b[3])/2:6.2f},{(b[4]+b[5])/2:7.2f})")
    # fold transforms per row (what the STEP bodies + rings consume)
    folds = []
    for i in range(len(app.rows)):
        try:
            f = app._optical_axis_fold_world_transform_for_row(i)
        except Exception:
            f = None
        folds.append("F" if f is not None else ".")
    print("  fold-transform per row:", "".join(folds))


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        app.layout_files["az85"] = SCENE
        app.load_layout_by_name("az85")
        snap(app, "PRISTINE (before BS add)")

        res = app.add_beam_splitter_to_led("plate")
        print("\nadd_beam_splitter_to_led ->", type(res).__name__, (res or {}).get("row_index") if isinstance(res, dict) else res)
        snap(app, "AFTER BS ADD")

        # find the first mirror row (promoted solid with Mirror face) and try the browser delete
        from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
        mirror_rows = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        print("\nmirror rows:", mirror_rows)
        n_before = len(app.rows)
        removed = app.delete_optical_step_rows([mirror_rows[0]])
        print(f"delete_optical_step_rows([{mirror_rows[0]}]) -> {removed}; rows {n_before} -> {len(app.rows)}")
        snap(app, "AFTER MIRROR DELETE")
        return 0
    finally:
        try:
            app.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
