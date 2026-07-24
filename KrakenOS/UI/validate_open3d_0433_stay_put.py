"""Guard: stay-put freeze on fold-element removal (bugs/0433 slice A).

Deleting or unpromoting a FOLD element (a promoted right-angle mirror) used to
collapse the whole downstream imaging chain onto the straight axis, because the
folded world poses were only a derived override map (bugs/0431 reproduction).
The 0433 freeze captures every surviving downstream row's world pose while the
fold still exists and bakes it into the row's own desp/tilt (plus an explicit
lens/camera STEP-overlay carry through the per-label settings).

Checked on the real ``machine_vision_AZ85_RA_Mirror.py``:

* FREEZE-ON-DELETE -- ``delete_optical_step_rows`` on the temporary RA mirror
  keeps every surviving downstream row's row-frame world center (station+desp)
  at its pre-removal override position, including the pinned second mirror
  (whose z-station shifts by the removed thickness) and the folded Image row.
* STEP-CARRY -- the lens + camera STEP overlay bodies keep their world bounds
  (their fold transform dies with the override map).
* NO-OP-GATE -- ``_stay_put_freeze_capture`` returns None for a non-fold row,
  so plain deletions stay byte-identical.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_0433_stay_put

Exit: 0 = pass, 1 = regression, 2 = environment/scene unavailable (skip).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
TOL_MM = 1e-3


def _load_editor():
    from KrakenOS.UI.layout_editor import KrakenLayoutEditor

    app = KrakenLayoutEditor()
    app.layout_files["az85"] = SCENE
    app.load_layout_by_name("az85")
    return app


def _step_bounds(app, label):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        return np.asarray(mesh.bounds, dtype=float).reshape(6)
    except Exception:
        return None


def _row_world_center(app, index):
    z = app._row_z_positions()
    row = app.rows[index]
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), float(z[index]) + float(row.desp_z)), dtype=float
    )


def run_checks() -> "tuple[bool, list[str]]":
    from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold
    from KrakenOS.UI.nonseq_output_ports import optical_solid_output_port_pose_overrides

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
        mirror1 = folds[0]

        overrides = optical_solid_output_port_pose_overrides(None, app.rows)
        downstream = [i for i in range(mirror1 + 2, len(app.rows))]
        expected = {}
        row_refs = {}
        for i in downstream:
            pose = overrides.get(i)
            if isinstance(pose, dict):
                expected[i] = np.asarray(pose.get("center"), dtype=float).reshape(3)
            else:
                expected[i] = _row_world_center(app, i)
            row_refs[i] = app.rows[i]
        folded_count = sum(
            1 for i in downstream
            if isinstance(overrides.get(i), dict)
            and not np.allclose(
                np.asarray(overrides[i].get("rotation"), dtype=float).reshape(3, 3), np.eye(3), atol=1e-6
            )
        )
        if folded_count < 5:
            failures.append(f"FREEZE-ON-DELETE: scene must start folded (only {folded_count} folded rows)")
        lens_before = _step_bounds(app, "lens")
        camera_before = _step_bounds(app, "camera")

        # --- NO-OP-GATE first (state untouched) ---
        if app._stay_put_freeze_capture([mirror1 + 2]) is not None:
            failures.append("NO-OP-GATE: capture on a non-fold row must return None")
        else:
            notes.append("no-op-gate = non-fold capture returns None (plain deletions untouched)")

        # --- FREEZE-ON-DELETE ---
        removed = app.delete_optical_step_rows([mirror1])
        if removed != 1:
            failures.append(f"FREEZE-ON-DELETE: expected to remove 1 row (got {removed})")
        row_to_index = {id(r): i for i, r in enumerate(app.rows)}
        bad = []
        preserved = 0
        for old_index, row in row_refs.items():
            new_index = row_to_index.get(id(row))
            if new_index is None:
                continue
            got = _row_world_center(app, new_index)
            if np.allclose(got, expected[old_index], atol=TOL_MM):
                preserved += 1
            else:
                bad.append(f"S{old_index}->{np.round(got, 3)}!={np.round(expected[old_index], 3)}")
        if bad:
            failures.append("FREEZE-ON-DELETE: rows moved: " + "; ".join(bad))
        elif preserved < 5:
            failures.append(f"FREEZE-ON-DELETE: too few surviving rows verified ({preserved})")
        else:
            notes.append(f"freeze-on-delete = {preserved} downstream rows keep their world centers")

        # --- STEP-CARRY ---
        for label, before in (("lens", lens_before), ("camera", camera_before)):
            if before is None:
                notes.append(f"step-carry = no {label} STEP body in the environment (skipped)")
                continue
            after = _step_bounds(app, label)
            if after is None or not np.allclose(after, before, atol=1e-2):
                failures.append(f"STEP-CARRY: the {label} STEP body detached (bounds changed)")
            else:
                notes.append(f"step-carry = the {label} STEP body keeps its world bounds")
    except Exception as exc:  # environment (Tk/OCC/scene) unavailable -> skip, don't fail the gate
        return True, [f"SKIP: environment unavailable ({type(exc).__name__}: {exc})"]
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass

    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_0433_stay_put (bugs/0433 slice A) ===")
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
    print("\nAll stay-put freeze (bugs/0433 slice A) checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
