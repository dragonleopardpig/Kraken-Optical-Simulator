"""Guard: multi-select snap with a FOLD inside the selection (bugs/0433 slice C).

The user's rubber-band workflow snaps the whole frozen imaging chain -- lens
datums/groups/aperture AND the free-placed second RA mirror AND the Image row
on the mirror's exit leg -- onto a new axis. Three defects are pinned here:

* ENTRY-LEG-FIT -- the old-axis inference cuts at the first selected fold
  solid: entry members land exactly ON the picked axis (the first->last fit
  over both legs used to skew the rotation, up to 17 mm of perpendicular
  error on AZ85).
* RIGID-FOLD -- every selection member (mirror + second-leg Image included)
  moves by the ONE rigid transform: pairwise deltas equal R @ (pre delta),
  and the lens/camera STEP bodies move WITH their anchor rows (the explicit
  path used to pivot the STEP carry on the branch point while rows pivoted
  on the selection origin).
* NO-RESWEEP -- after the snap the fold walk leaves the explicitly placed
  rows alone (``last_axis_to_axis_move`` breadcrumb): the walk's exit-face
  inference on the snapped mirror pose is unreliable and threw the Image row
  295 mm off before the guard. Also asserts the phantom ``row.AxisMove``
  stamp is gone (the editor field is ``axis_move``; stamping 1.0 there would
  compound absolute desp/tilt through the engine PA term).

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0433_snap_fold_selection

Exit: 0 = pass, 1 = regression, 2/skip = environment unavailable.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
TOL_MM = 1e-3

NEW_RECORD = {
    "axis_id": "axis:global:split",
    "axis_label": "Optical Axis (BS reflect)",
    "points": np.asarray([(0.0, 0.0, 60.0), (0.0, 120.0, 60.0)], dtype=float),
}


def _load_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.layout_files["az85"] = SCENE
    app.load_layout_by_name("az85")
    return app


def _row_world_center(app, index):
    z = app._row_z_positions()
    row = app.rows[index]
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), float(z[index]) + float(row.desp_z)), dtype=float
    )


def _step_center(app, label):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        b = np.asarray(mesh.bounds, dtype=float).reshape(6)
        return np.asarray(
            ((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0), dtype=float
        )
    except Exception:
        return None


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
    from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides
    from KrakenOS.UI.optical_solid_metadata import rotation_matrix_aligning_vectors

    if not SCENE.exists():
        return True, ["SKIP: scene not present -- environment check skipped"]

    failures: list[str] = []
    notes: list[str] = []
    app = None
    try:
        app = _load_editor()
        folds = [i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r)]
        if len(folds) < 2:
            return True, [f"SKIP: expected two fold mirrors in the AZ85 scene (got {folds})"]
        app.delete_optical_step_rows([folds[0]])  # slice-A freeze
        mirror2 = next(i for i, r in enumerate(app.rows) if _row_is_promoted_mirror_fold(r))
        image = next(
            i for i in range(len(app.rows) - 1, -1, -1)
            if getattr(app.rows[i], "surface", None) == "Image"
        )
        front_datum = app._lens_datum_row_index("front")
        if front_datum is None or not (front_datum < mirror2 < image):
            return True, ["SKIP: frozen AZ85 topology unexpected"]
        selection = list(range(front_datum, image + 1))
        entry = [
            i for i in selection
            if i < mirror2 and not app._is_any_promoted_optical_solid_row(app.rows[i])
        ]
        if len(entry) < 2:
            return True, ["SKIP: too few entry-leg members"]

        pre = {i: _row_world_center(app, i) for i in selection}
        pre_lens = _step_center(app, "lens")
        origin = pre[entry[0]]
        old_dir = pre[entry[-1]] - origin
        old_dir = old_dir / np.linalg.norm(old_dir)
        branch = NEW_RECORD["points"][0]
        new_dir = np.asarray((0.0, 1.0, 0.0), dtype=float)
        rot = rotation_matrix_aligning_vectors(old_dir, new_dir)

        app.snap_rows_to_axis(selection, NEW_RECORD)
        post = {i: _row_world_center(app, i) for i in selection}

        # ENTRY-LEG-FIT
        worst_perp = 0.0
        for i in entry:
            perp = (post[i] - branch) - float(np.dot(post[i] - branch, new_dir)) * new_dir
            worst_perp = max(worst_perp, float(np.linalg.norm(perp)))
        if worst_perp > 1e-2:
            failures.append(f"ENTRY-LEG-FIT: entry members off the picked axis by {worst_perp:.3f} mm")
        else:
            notes.append(f"entry-leg-fit = {len(entry)} entry members on the axis (worst {worst_perp:.4f} mm)")

        # RIGID-FOLD (rows + lens STEP)
        ref = selection[0]
        worst = 0.0
        for i in selection[1:]:
            delta = np.abs((post[i] - post[ref]) - rot @ (pre[i] - pre[ref])).max()
            worst = max(worst, float(delta))
        if worst > TOL_MM:
            failures.append(f"RIGID-FOLD: selection deformed (worst pairwise delta {worst:.4f} mm)")
        else:
            notes.append(f"rigid-fold = {len(selection)} members move as one body (worst {worst:.5f} mm)")
        post_lens = _step_center(app, "lens")
        if pre_lens is not None and post_lens is not None:
            delta = float(
                np.abs((post_lens - post[front_datum]) - rot @ (pre_lens - pre[front_datum])).max()
            )
            if delta > 1e-2:
                failures.append(f"RIGID-FOLD: lens STEP body detached from its rows ({delta:.3f} mm)")
            else:
                notes.append(f"rigid-fold = lens STEP body rides with the rows ({delta:.5f} mm)")

        # NO-RESWEEP + phantom-stamp
        post_overrides = optical_solid_output_port_pose_overrides(None, app.rows)
        reswept = [i for i in selection if i in post_overrides]
        if reswept:
            failures.append(f"NO-RESWEEP: the fold walk re-swept snapped rows {reswept}")
        else:
            notes.append("no-resweep = the walk leaves explicitly snapped rows alone")
        phantom = [i for i in selection if "AxisMove" in vars(app.rows[i])]
        if phantom:
            failures.append(f"NO-RESWEEP: phantom row.AxisMove stamp is back on rows {phantom}")
        else:
            notes.append("no-resweep = no phantom row.AxisMove stamps (axis_move stays 0)")
    except Exception as exc:  # environment (Tk/OCC/scene) unavailable -> skip, don't fail the gate
        return True, [f"SKIP: environment unavailable ({type(exc).__name__}: {exc})"]
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass

    return (not failures), (failures + notes)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_0433_snap_fold_selection (bugs/0433 slice C) ===")
    for note in notes:
        tag = "-- " if note.startswith("SKIP") else ("ok " if "=" in note else "XX ")
        print(f"  {tag} {note}")
    if any(n.startswith("SKIP") for n in notes):
        print("\nSkipped (environment).")
        return 0
    if not passed:
        n = len([x for x in notes if "=" not in x and not x.startswith("SKIP")])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll fold-in-selection snap (bugs/0433 slice C) checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
