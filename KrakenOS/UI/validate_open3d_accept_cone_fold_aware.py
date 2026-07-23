"""Guard: the imaging lens's Accept-cone overlay CREASES at the fold, following the folded axis (bugs/0416+0418).

Flags flag_20260723_073901 ("Acceptance Cone overlay is not fold aware") + flag_20260723_083109
("Acceptance Cone is not folding"), AZ85 RA-mirror scene. The receiving-angle cone ("Accept cone",
bugs/0354) is built on the STRAIGHT sequential object-space axis (FOV rect at object_z -> entrance-pupil
disc at pupil_z) and was drawn with no fold (0416 flag). bugs/0416 then folded the WHOLE mesh rigidly onto
the lens leg -> the object end swung onto the lens leg too, so the cone lay flat along it (0418 flag).

Fix (bugs/0418): CREASE at the fold. ``_crease_overlay_mesh_at_fold`` folds ONLY the points DOWNSTREAM of
the fold hinge (the fold transform's fixed point on the straight axis) onto the reflected leg; the FOV
ring stays up the object leg (base frame). So the cone goes up the object leg AND bends onto the lens leg,
hinged at the mirror. ``None`` transform (unfolded scene) -> mesh unchanged.

Checks
------
* MECHANISM -- ``_add_receiving_cone_overlays`` creases via ``_crease_overlay_mesh_at_fold`` with the lens
  front-datum fold transform (NOT the old whole-mesh ``_mesh_with_world_transform``).
* CREASE-MATH -- on a real cone mesh straddling a Z->X fold hinge (z=53), the upstream FOV ring is left
  put while the downstream pupil ring folds onto the reflected leg; a ``None`` transform is a no-op.

Run:
    .devenv/state/venv/bin/python -m KrakenOS.UI.validate_open3d_accept_cone_fold_aware

Exit: 0 = pass, 1 = regression.
"""
from __future__ import annotations

import inspect

import numpy as np


def _check_mechanism(failures, notes):
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    src = inspect.getsource(Kraken3DInspector._add_receiving_cone_overlays)
    need = {
        "the crease fold": "_crease_overlay_mesh_at_fold(mesh, fold_transform)",
        "the lens-row fold transform": "_optical_axis_fold_world_transform_for_row(",
        "the lens front-datum anchor": "_lens_front_datum_row_index()",
    }
    missing = [label for label, token in need.items() if token not in src]
    if "_mesh_with_world_transform(mesh, fold_transform)" in src:
        missing.append("the OLD whole-mesh fold must be gone (it rigidly swings the cone onto the lens leg)")
    if missing:
        failures.append("MECHANISM: _add_receiving_cone_overlays is missing " + ", ".join(missing))
    else:
        notes.append("mechanism = accept cone CREASES via _crease_overlay_mesh_at_fold at the lens-row fold")


def _check_crease_math(failures, notes):
    try:
        import pyvista as pv
    except Exception as exc:
        failures.append(f"CREASE-MATH: pyvista unavailable ({exc})")
        return
    from KrakenOS.UI.open3d_inspector import Kraken3DInspector
    from KrakenOS.UI.services.receiving_cone_overlay import build_receiving_cone_overlay

    # cone straddling the fold: FOV ring at z=-200 (upstream), pupil ring at z=+100 (downstream of hinge 53)
    spec = build_receiving_cone_overlay(10.0, 10.0, -200.0, 100.0, 5.0)
    if not spec:
        failures.append("CREASE-MATH: build_receiving_cone_overlay returned nothing")
        return
    points = np.asarray(spec["points"], dtype=float)
    faces = np.asarray(spec["faces"], dtype=np.int64)
    n = points.shape[0] // 2  # [fov ring (n), pupil ring (n)]
    mesh = pv.PolyData(points[:, :3], faces=faces)

    # a 90-deg Z->X fold with the hinge at z=53: R@[0,0,1]=[1,0,0]; F([0,0,53])=[0,0,53] -> t=[-53,0,53]
    rot = np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]], dtype=float)
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rot
    transform[:3, 3] = np.array([-53.0, 0.0, 53.0])

    creased = Kraken3DInspector._crease_overlay_mesh_at_fold(None, mesh, transform)
    out = np.asarray(creased.points, dtype=float)
    # upstream FOV ring untouched (still up the object leg)
    if not np.allclose(out[:n], points[:n, :3], atol=1e-6):
        failures.append("CREASE-MATH: the upstream FOV ring must stay on the object leg (unfolded)")
    # downstream pupil ring folded onto the reflected leg: centre (0,0,100) -> R@c + t = (47,0,53)
    pupil_center = out[n:].mean(axis=0)
    expected = rot @ np.array([0.0, 0.0, 100.0]) + transform[:3, 3]
    if not np.allclose(pupil_center, expected, atol=1e-6):
        failures.append(f"CREASE-MATH: the downstream pupil ring must fold onto the leg (got {pupil_center.round(2)}, expected {expected.round(2)})")
    # a straight scene (no fold) must not move the cone
    unfolded = Kraken3DInspector._crease_overlay_mesh_at_fold(None, mesh, None)
    if not np.allclose(np.asarray(unfolded.points, dtype=float), points[:, :3], atol=1e-9):
        failures.append("CREASE-MATH: a None (unfolded) transform must leave the cone untouched")
    if not [f for f in failures if f.startswith("CREASE-MATH")]:
        notes.append(f"crease-math = FOV ring stays (leg 1); pupil ring folds to {pupil_center.round(1)} (leg 2); unfolded = no-op")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_mechanism, _check_crease_math):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_accept_cone_fold_aware (bugs/0416+0418) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll accept-cone crease-fold checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
