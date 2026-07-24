#!/usr/bin/env python3
"""bugs/0433 slice A: stay-put freeze on fold-element removal (AZ85 scene).

The temporary first RA mirror (row 1, spacer row 2, overlapping the LED) folds
the imaging chain onto the +X leg at z=53. Deleting/unpromoting it used to
collapse the whole chain back to the straight axis (bugs/0431 reproduction:
the derived override map empties). With the 0433 freeze every surviving
downstream row keeps its CURRENT world pose, baked into its own desp/tilt.

What is verified (and why):
- ROW-frame world center (station+desp) == the pre-removal override/TRANS world
  position, for every surviving downstream row. This is the frame the display,
  snap and dimension consumers read.
- BUILT system TRANS_2A translation preserved for non-solid rows UPSTREAM of
  the parked second mirror. Rows DOWNSTREAM of it (the Image) sit exactly the
  parked solid's thickness short in the BUILT chain: neutralize_offbeam_inert_
  solids (bugs/0065) drops an off-beam solid from the physical chain -- the
  raw-vs-equivalent frame split documented in bugs/0226. Asserted explicitly.
- Drawn surface mesh (system EEE) world bounds preserved -- the VISUAL
  stay-put. (Kraken's TRANS matrices compose Rx@Ry@Rz while the drawn/NS mesh
  path composes Rz(-tz)@Ry@Rx; the tilt bake targets the mesh convention, so
  the drawn geometry is exact and the TRANS rotation may differ for the folded
  tilt family -- transient, off-beam, user re-solves after the snap.)
- Lens/camera STEP overlay bodies keep their world bounds (their fold
  transform dies with the override map; the freeze re-expresses them through
  the per-label settings).

PASS 1  delete_optical_step_rows([mirror-1 row])       -> poses preserved
PASS 2  unpromote_optical_solid_to_overlay(mirror-1)   -> poses preserved
PASS 3  negative control: non-fold ops bake nothing
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from KrakenOS.UI.layout_editor import KrakenLayoutEditor  # noqa: E402
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold  # noqa: E402

SCENE = Path("attachment/machine_vision_AZ85_RA_Mirror.py")
TOL_MM = 1e-3

failures: list[str] = []


def check(ok: bool, message: str) -> None:
    print(("  ok " if ok else "  XX ") + message)
    if not ok:
        failures.append(message)


def load(app) -> None:
    app.layout_files["az85"] = SCENE
    app.load_layout_by_name("az85")


def fold_row_indices(app) -> list[int]:
    return [i for i, row in enumerate(app.rows) if _row_is_promoted_mirror_fold(row)]


def built_state(app):
    system = app.build_system(require_solids=True, force_rebuild=True)
    trans, mesh_bounds = {}, {}
    for i in range(len(app.rows)):
        try:
            trans[i] = np.asarray(system.Pr3D.TRANS_2A[i], dtype=float).reshape(4, 4)
        except Exception:
            pass
        try:
            meshes = getattr(system, "EEE", None) or getattr(system.Pr3D, "EEE", None)
            block = meshes[i]
            if block is not None and int(getattr(block, "n_points", 0)) > 0:
                mesh_bounds[i] = np.asarray(block.bounds, dtype=float).reshape(6)
        except Exception:
            pass
    return trans, mesh_bounds


def row_world_center(app, index: int) -> np.ndarray:
    z = app._row_z_positions()
    row = app.rows[index]
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), float(z[index]) + float(row.desp_z)), dtype=float
    )


def step_bounds(app, label: str):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        return np.asarray(mesh.bounds, dtype=float).reshape(6)
    except Exception:
        return None


def capture_state(app, downstream: list[int]):
    trans, mesh_bounds = built_state(app)
    return {
        "rows": {i: app.rows[i] for i in downstream},
        "trans": {i: trans.get(i) for i in downstream},
        "mesh": {i: mesh_bounds.get(i) for i in downstream},
        "is_solid": {i: bool(_row_is_promoted_mirror_fold(app.rows[i])) for i in downstream},
        "lens": step_bounds(app, "lens"),
        "camera": step_bounds(app, "camera"),
    }


def verify_preserved(app, before, label: str) -> None:
    trans_after, mesh_after = built_state(app)
    row_to_index = {id(row): i for i, row in enumerate(app.rows)}
    surviving_solids = [
        i for i, row in enumerate(app.rows) if _row_is_promoted_mirror_fold(row)
    ]
    parked_thickness = sum(float(getattr(app.rows[i], "thickness", 0.0) or 0.0) for i in surviving_solids)
    passed_parked = False
    for old_index in sorted(before["rows"]):
        row = before["rows"][old_index]
        new_index = row_to_index.get(id(row))
        if new_index is None:
            print(f"  -- old row S{old_index} removed by the mutation itself (skipped)")
            continue
        name = str(getattr(row, "name", "") or "")[:28]
        expected_trans = before["trans"][old_index]
        if expected_trans is None:
            continue
        expected_world = expected_trans[:3, 3]
        got_center = row_world_center(app, new_index)
        check(
            bool(np.allclose(got_center, expected_world, atol=TOL_MM)),
            f"{label}: S{old_index}->S{new_index} [{name}] row-frame world center preserved "
            f"({np.round(got_center, 3)} vs {np.round(expected_world, 3)})",
        )
        if before["is_solid"][old_index]:
            passed_parked = True  # rows after this sit in the equivalent (parked-excluded) built frame
            continue
        got_trans = trans_after.get(new_index)
        if got_trans is None:
            check(False, f"{label}: S{old_index} missing TRANS_2A after mutation")
            continue
        if not passed_parked:
            check(
                bool(np.allclose(got_trans[:3, 3], expected_world, atol=TOL_MM)),
                f"{label}: S{old_index}->S{new_index} [{name}] BUILT world translation preserved "
                f"({np.round(got_trans[:3, 3], 3)} vs {np.round(expected_world, 3)})",
            )
        else:
            delta = expected_world - got_trans[:3, 3]
            check(
                bool(abs(float(np.linalg.norm(delta)) - parked_thickness) <= 0.1),
                f"{label}: S{old_index}->S{new_index} [{name}] BUILT translation short by exactly the "
                f"parked solid thickness ({np.round(np.linalg.norm(delta), 3)} vs {parked_thickness})",
            )
        expected_mesh = before["mesh"][old_index]
        got_mesh = mesh_after.get(new_index)
        if expected_mesh is not None and got_mesh is not None and not passed_parked:
            check(
                bool(np.allclose(got_mesh, expected_mesh, atol=1e-2)),
                f"{label}: S{old_index}->S{new_index} [{name}] DRAWN mesh world bounds preserved "
                f"(delta={np.round(np.abs(got_mesh - expected_mesh).max(), 4)})",
            )
    for step_label in ("lens", "camera"):
        expected = before[step_label]
        got = step_bounds(app, step_label)
        if expected is None:
            print(f"  -- {label}: no {step_label} STEP body to verify")
            continue
        if got is None:
            check(False, f"{label}: {step_label} STEP body vanished after removal")
            continue
        check(
            bool(np.allclose(got, expected, atol=1e-2)),
            f"{label}: {step_label} STEP body world bounds preserved "
            f"(delta={np.round(np.abs(got - expected).max(), 4)})",
        )


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        # ---- PASS 1: browser-style delete of the temporary fold mirror ----
        print("=== PASS 1: delete_optical_step_rows on RA-mirror-1 ===")
        load(app)
        folds = fold_row_indices(app)
        check(folds == [1, 8], f"fold rows are mirror-1 (S1) + mirror-2 (S8): {folds}")
        mirror1 = folds[0]
        downstream = [i for i in range(mirror1 + 2, len(app.rows))]  # skip mirror-1 + its spacer
        before = capture_state(app, downstream)
        folded = [
            i for i in downstream
            if before["trans"][i] is not None
            and not np.allclose(before["trans"][i][:3, :3], np.eye(3), atol=1e-6)
        ]
        check(len(folded) >= 5, f"scene starts folded ({len(folded)} rows off the straight axis)")
        removed = app.delete_optical_step_rows([mirror1])
        check(removed == 1, f"delete_optical_step_rows removed {removed} row(s)")
        verify_preserved(app, before, "delete")
        frozen_marks = sum(
            1 for row in app.rows
            if isinstance(getattr(row, "advanced", None), dict)
            and isinstance(row.advanced.get("ScenePlacement"), dict)
            and "stay_put_freeze" in row.advanced.get("ScenePlacement", {})
        )
        check(frozen_marks >= 5, f"stay_put_freeze breadcrumb on {frozen_marks} rows")

        # ---- PASS 2: unpromote of the fold mirror ----
        print("=== PASS 2: unpromote_optical_solid_to_overlay on RA-mirror-1 ===")
        load(app)
        folds = fold_row_indices(app)
        check(folds and folds[0] == 1, f"mirror-1 is S1 (got {folds})")
        downstream = [i for i in range(3, len(app.rows))]
        before = capture_state(app, downstream)
        result = app.unpromote_optical_solid_to_overlay(folds[0], refresh_open_3d=False)
        check(isinstance(result, dict), f"unpromote returned a result ({type(result).__name__})")
        verify_preserved(app, before, "unpromote")

        # ---- PASS 4 (order-independent): partial removal -- a surviving upstream fold
        # still sweeps the chain; the freeze must stand down (fold-follow wins) ----
        print("=== PASS 4: delete mirror-2 only (mirror-1 survives) -> no bake ===")
        load(app)
        folds = fold_row_indices(app)
        mirror2 = folds[-1]
        image_row = next(i for i in range(len(app.rows) - 1, -1, -1) if app.rows[i].surface == "Image")
        image_state = (
            float(app.rows[image_row].desp_x), float(app.rows[image_row].desp_y),
            float(app.rows[image_row].desp_z), float(app.rows[image_row].tilt_x),
            float(app.rows[image_row].tilt_y), float(app.rows[image_row].tilt_z),
        )
        image_obj = app.rows[image_row]
        removed = app.delete_optical_step_rows([mirror2])
        check(removed == 1, f"delete_optical_step_rows removed mirror-2 ({removed} row)")
        new_image = next(i for i, r in enumerate(app.rows) if r is image_obj)
        image_after = (
            float(app.rows[new_image].desp_x), float(app.rows[new_image].desp_y),
            float(app.rows[new_image].desp_z), float(app.rows[new_image].tilt_x),
            float(app.rows[new_image].tilt_y), float(app.rows[new_image].tilt_z),
        )
        check(
            image_after == image_state,
            "Image row NOT baked (surviving mirror-1 sweep owns it; fold-follow wins)",
        )
        advanced = getattr(app.rows[new_image], "advanced", {}) or {}
        placement = advanced.get("ScenePlacement", {}) if isinstance(advanced, dict) else {}
        check(
            "stay_put_freeze" not in placement,
            "no stay_put_freeze breadcrumb on the still-swept Image row",
        )

        # ---- PASS 3: negative control -- non-fold operations bake nothing ----
        print("=== PASS 3: negative control ===")
        load(app)
        snapshot = app._stay_put_freeze_capture([4])  # Thin Lens row: not a fold
        check(snapshot is None, "capture on a non-fold row returns None")
        state = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z), float(r.tilt_x), float(r.tilt_y), float(r.tilt_z))
            for r in app.rows
        ]
        removed = app.delete_optical_step_rows([4])
        check(removed == 0, "delete_optical_step_rows refuses a non-promoted row")
        state_after = [
            (float(r.desp_x), float(r.desp_y), float(r.desp_z), float(r.tilt_x), float(r.tilt_y), float(r.tilt_z))
            for r in app.rows
        ]
        check(state_after == state, "no desp/tilt changed by the refused delete")
    finally:
        try:
            app.destroy()
        except Exception:
            pass

    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed")
        for message in failures:
            print("  - " + message)
        return 1
    print("PASS: stay-put freeze holds on delete + unpromote; plain ops untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
