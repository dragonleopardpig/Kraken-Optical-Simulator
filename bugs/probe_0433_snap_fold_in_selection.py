#!/usr/bin/env python3
"""bugs/0433 slice C: snap_rows_to_axis with a FOLD inside the selection (AZ85).

The user's step-6 workflow: after the stay-put freeze (slice A) the imaging
chain sits on the old +X leg; a rubber-band selection (slice B) grabs ALL of it
-- lens datums/groups/aperture AND the free-placed second RA mirror AND the
Image row on the mirror's exit leg -- and snaps it onto the new BS reflect
axis. Three defects this probe pins:

1. ENTRY-LEG INFERENCE -- the old-axis fit ran first->last over all non-solid
   members; the Image row lives on the SECOND leg (behind mirror-2), so the fit
   was a skewed diagonal and the rigid move landed misrotated. Fixed: the fit
   stops at the first selected fold solid (row order = optical order).
2. STEP-FOLLOW PIVOT -- rows pivot on the selection origin in the explicit
   path, but the lens/camera STEP carry pivoted on the branch point: the body
   landed offset by R@(origin - branch) relative to its rows.
3. AXISMOVE COMPOUNDING -- the move stamped AxisMove=1.0 on every moved row;
   the engine (Prerequisites3D.GeometricRotatAndTran / KrakenSys PA term)
   applies an upstream row's desp/tilt to every follower when AxisMove=1, so
   consecutive ABSOLUTELY-baked rows compounded in the BUILT system (row
   arithmetic looked fine -- probe_0432 never checked the build). Fixed:
   moved rows are absolutely placed, AxisMove=0.

Verified rigid-body style: entry members land ON the new axis, every pairwise
delta (incl. mirror-2's fold + the camera leg) is exactly R@(pre delta), mesh
rotations compose to R@pre, BUILT translations match row-frame centers (with
the known off-beam-neutralization thickness carve-out behind the parked
mirror, bugs/0065/0226), and the lens/camera STEP bodies move WITH their rows.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from KrakenOS.UI.layout_editor import KrakenLayoutEditor  # noqa: E402
from KrakenOS.UI.services.paraxial_tools import _row_is_promoted_mirror_fold  # noqa: E402
from KrakenOS.UI.optical_solid_metadata import (  # noqa: E402
    rotation_matrix_aligning_vectors,
    rotation_matrix_from_kraken_tilts,
)

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


def row_world_center(app, index: int) -> np.ndarray:
    z = app._row_z_positions()
    row = app.rows[index]
    return np.asarray(
        (float(row.desp_x), float(row.desp_y), float(z[index]) + float(row.desp_z)), dtype=float
    )


def row_mesh_rotation(app, index: int) -> np.ndarray:
    row = app.rows[index]
    return rotation_matrix_from_kraken_tilts(
        float(row.tilt_x), float(row.tilt_y), float(row.tilt_z)
    )


def built_translations(app) -> dict[int, np.ndarray]:
    system = app.build_system(require_solids=True, force_rebuild=True)
    out: dict[int, np.ndarray] = {}
    for i in range(len(app.rows)):
        try:
            trans = np.asarray(system.Pr3D.TRANS_2A[i], dtype=float).reshape(4, 4)
            out[i] = trans[:3, 3]
        except Exception:
            pass
    return out


def step_center(app, label: str):
    try:
        mesh = app._transformed_imported_step_mesh_for_label(label)
        if mesh is None or int(getattr(mesh, "n_points", 0)) <= 0:
            return None
        b = np.asarray(mesh.bounds, dtype=float).reshape(6)
        return np.asarray(((b[0] + b[1]) / 2.0, (b[2] + b[3]) / 2.0, (b[4] + b[5]) / 2.0), dtype=float)
    except Exception:
        return None


def frozen_scene(app) -> dict[str, object]:
    """Load AZ85 + slice-A freeze (delete the temporary fold mirror), return the
    surviving downstream row indices by role."""
    load(app)
    folds = [i for i, row in enumerate(app.rows) if _row_is_promoted_mirror_fold(row)]
    assert folds and len(folds) >= 2, f"expected two fold mirrors in AZ85, got {folds}"
    removed = app.delete_optical_step_rows([folds[0]])
    assert removed >= 1, "slice-A freeze delete removed nothing"
    mirror2 = next(i for i, row in enumerate(app.rows) if _row_is_promoted_mirror_fold(row))
    image = next(
        i for i in range(len(app.rows) - 1, -1, -1) if getattr(app.rows[i], "surface", None) == "Image"
    )
    front_datum = app._lens_datum_row_index("front")
    assert front_datum is not None and front_datum < mirror2 < image
    selection = list(range(front_datum, image + 1))
    entry = [
        i for i in selection
        if i < mirror2 and not app._is_any_promoted_optical_solid_row(app.rows[i])
    ]
    return {
        "selection": selection,
        "entry": entry,
        "mirror2": mirror2,
        "image": image,
        "front_datum": front_datum,
    }


NEW_RECORD = {
    "axis_id": "axis:global:split",
    "axis_label": "Optical Axis (BS reflect)",
    "points": np.asarray([(0.0, 0.0, 60.0), (0.0, 120.0, 60.0)], dtype=float),
}


def main() -> int:
    app = KrakenLayoutEditor()
    try:
        # ---- PART 1: fold INSIDE the selection (the user's step-6 set) ----
        print("=== PART 1: snap the whole frozen chain (incl. mirror-2 + Image) ===")
        roles = frozen_scene(app)
        selection = roles["selection"]
        entry = roles["entry"]
        mirror2 = roles["mirror2"]
        check(len(entry) >= 2, f"entry-leg fit members below mirror-2 S{mirror2}: {entry}")

        pre_center = {i: row_world_center(app, i) for i in selection}
        pre_rot = {i: row_mesh_rotation(app, i) for i in selection}
        pre_lens = step_center(app, "lens")
        pre_camera = step_center(app, "camera")

        # expected transform: entry-leg fit only (the fix under test)
        origin = pre_center[entry[0]]
        old_dir = pre_center[entry[-1]] - origin
        old_dir = old_dir / np.linalg.norm(old_dir)
        branch = NEW_RECORD["points"][0]
        new_dir = np.asarray((0.0, 1.0, 0.0), dtype=float)
        rot = rotation_matrix_aligning_vectors(old_dir, new_dir)

        result = app.snap_rows_to_axis(selection, NEW_RECORD)
        check(sorted(result.get("moved_rows") or []) == selection, f"moved rows == selection: {result.get('moved_rows')}")

        post_center = {i: row_world_center(app, i) for i in selection}
        post_rot = {i: row_mesh_rotation(app, i) for i in selection}

        # (a) entry members land ON the new axis, at the entry-leg-predicted spots
        for i in entry:
            expected = branch + rot @ (pre_center[i] - origin)
            check(
                bool(np.allclose(post_center[i], expected, atol=TOL_MM)),
                f"S{i} entry member lands at the entry-leg prediction ({np.round(post_center[i], 3)})",
            )
            perp = (post_center[i] - branch) - float(np.dot(post_center[i] - branch, new_dir)) * new_dir
            check(
                float(np.linalg.norm(perp)) <= 1e-2,
                f"S{i} entry member is ON the new axis (perp {np.linalg.norm(perp):.4f} mm)",
            )
        # (b) FULL rigidity incl. mirror-2 + Image: every delta is R @ (pre delta)
        ref = selection[0]
        for i in selection[1:]:
            got = post_center[i] - post_center[ref]
            want = rot @ (pre_center[i] - pre_center[ref])
            check(
                bool(np.allclose(got, want, atol=TOL_MM)),
                f"S{i} rigid vs S{ref} (fold preserved) delta={np.round(np.abs(got - want).max(), 4)}",
            )
        # (c) orientations compose to R @ pre (mesh convention)
        for i in selection:
            check(
                bool(np.allclose(post_rot[i], rot @ pre_rot[i], atol=1e-6)),
                f"S{i} mesh-convention rotation == R @ pre",
            )
        # (d) STEP bodies move WITH their rows (pivot audit)
        post_lens = step_center(app, "lens")
        post_camera = step_center(app, "camera")
        fd, im = roles["front_datum"], roles["image"]
        if pre_lens is not None and post_lens is not None:
            got = post_lens - post_center[fd]
            want = rot @ (pre_lens - pre_center[fd])
            check(
                bool(np.allclose(got, want, atol=1e-2)),
                f"lens STEP rigid with front datum (delta={np.round(np.abs(got - want).max(), 4)})",
            )
        else:
            check(False, "lens STEP body missing")
        if pre_camera is not None and post_camera is not None:
            # camera is sensor-anchored (flag_20260724_090954): the carry targets the
            # SENSOR (Image row) world position, so the body centre lands AT the
            # snapped sensor.
            delta = float(np.linalg.norm(post_camera - post_center[im]))
            check(
                delta <= 1e-2,
                f"camera STEP body sits AT the snapped sensor (delta={delta:.4f})",
            )
        else:
            check(False, "camera STEP body missing")
        # (e) BUILT system: translations match row-frame centers (AxisMove audit);
        # rows behind the parked mirror-2 sit its thickness short (bugs/0065/0226).
        built = built_translations(app)
        parked_thickness = float(getattr(app.rows[mirror2], "thickness", 0.0) or 0.0)
        for i in selection:
            got = built.get(i)
            if got is None:
                check(False, f"S{i} missing TRANS_2A after snap")
                continue
            if i < mirror2:
                check(
                    bool(np.allclose(got, post_center[i], atol=TOL_MM)),
                    f"S{i} BUILT translation == row-frame center ({np.round(got, 3)})",
                )
            elif i > mirror2:
                delta = float(np.linalg.norm(post_center[i] - got))
                check(
                    abs(delta - parked_thickness) <= 0.1,
                    f"S{i} BUILT translation short by exactly the parked thickness "
                    f"({delta:.3f} vs {parked_thickness})",
                )

        # ---- PART 2: control -- no fold in the selection -> fallback fit ----
        print("=== PART 2: control snap without a fold solid in the selection ===")
        app2 = KrakenLayoutEditor()
        try:
            roles2 = frozen_scene(app2)
            entry_only = [i for i in roles2["selection"] if i < roles2["mirror2"]]
            pre2 = {i: row_world_center(app2, i) for i in entry_only}
            nonsolid = [i for i in entry_only if not app2._is_any_promoted_optical_solid_row(app2.rows[i])]
            origin2 = pre2[nonsolid[0]]
            dir2 = pre2[nonsolid[-1]] - origin2
            dir2 = dir2 / np.linalg.norm(dir2)
            rot2 = rotation_matrix_aligning_vectors(dir2, new_dir)
            app2.snap_rows_to_axis(entry_only, NEW_RECORD)
            for i in entry_only:
                expected = branch + rot2 @ (pre2[i] - origin2)
                got = row_world_center(app2, i)
                check(
                    bool(np.allclose(got, expected, atol=TOL_MM)),
                    f"S{i} control lands at the classic first->last prediction",
                )
        finally:
            app2.destroy()
    finally:
        app.destroy()

    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed")
        return 1
    print("PASS: fold-in-selection snap is rigid, entry-leg-aimed, build-consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
