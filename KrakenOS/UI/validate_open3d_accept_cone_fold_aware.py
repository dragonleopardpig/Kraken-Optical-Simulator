"""Guard: the imaging lens's Accept-cone overlay is FOLD AWARE (bugs/0416).

Flag flag_20260723_073901_461 (AZ85 RA-mirror scene): "Acceptance Cone overlay is not fold aware." The
receiving-angle cone (``show_receiving_cone_var`` / "Accept cone") is built on the STRAIGHT sequential
object-space axis (``build_receiving_cone_overlay``: FOV rect at object_z -> entrance-pupil disc at
pupil_z), and ``_add_receiving_cone_overlays`` drew those points DIRECTLY -- so on a folded scene it shot
straight down the unfolded axis while the optics folded away (its sibling illumination-volume overlay,
bugs/0355, is already fold aware).

Fix: fold the cone onto the imaging arm with the SAME rigid transform the lens STEP overlay uses
(``_optical_axis_fold_world_transform_for_row`` at the lens front-datum row), so the two stay coherent.
``None`` on an unfolded layout -> mesh unchanged (no regression).

Checks
------
* MECHANISM -- ``_add_receiving_cone_overlays`` folds the mesh via
  ``_optical_axis_fold_world_transform_for_row(... _lens_front_datum_row_index() ...)`` +
  ``_mesh_with_world_transform``.
* FOLD-MATH -- on a REAL cone mesh, the shared ``_mesh_with_world_transform`` maps the pupil ring by the
  rigid transform (pupil-ring centre -> R@centre + t), and a ``None`` transform (an unfolded scene)
  leaves the mesh untouched.

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
        "the lens-row fold transform": "_optical_axis_fold_world_transform_for_row(",
        "the lens front-datum anchor": "_lens_front_datum_row_index()",
        "the mesh fold application": "_mesh_with_world_transform(mesh, fold_transform)",
    }
    missing = [label for label, token in need.items() if token not in src]
    if missing:
        failures.append("MECHANISM: _add_receiving_cone_overlays is missing " + ", ".join(missing))
    else:
        notes.append("mechanism = accept cone folds onto the lens leg (same transform/anchor as the lens STEP overlay)")


def _check_fold_math(failures, notes):
    try:
        import pyvista as pv
    except Exception as exc:
        failures.append(f"FOLD-MATH: pyvista unavailable ({exc})")
        return
    from KrakenOS.UI.services.layout_polyline_display import LayoutPolylineDisplayMixin
    from KrakenOS.UI.services.receiving_cone_overlay import build_receiving_cone_overlay

    spec = build_receiving_cone_overlay(10.0, 10.0, -200.0, -10.0, 5.0)
    if not spec:
        failures.append("FOLD-MATH: build_receiving_cone_overlay returned nothing")
        return
    points = np.asarray(spec["points"], dtype=float)
    faces = np.asarray(spec["faces"], dtype=np.int64)
    n = points.shape[0] // 2  # [fov ring (n), pupil ring (n)]
    mesh = pv.PolyData(points[:, :3], faces=faces)

    theta = np.pi / 2.0  # a real 90-deg fold + offset
    rot = np.array([[1.0, 0.0, 0.0],
                    [0.0, np.cos(theta), -np.sin(theta)],
                    [0.0, np.sin(theta), np.cos(theta)]], dtype=float)
    transform = np.eye(4, dtype=float)
    transform[:3, :3] = rot
    transform[:3, 3] = np.array([100.0, 0.0, 50.0])

    folded = LayoutPolylineDisplayMixin._mesh_with_world_transform(mesh, transform)
    pupil_center_straight = points[n:].mean(axis=0)
    pupil_center_folded = np.asarray(folded.points, dtype=float)[n:].mean(axis=0)
    expected = rot @ pupil_center_straight + transform[:3, 3]
    if not np.allclose(pupil_center_folded, expected, atol=1e-6):
        failures.append(f"FOLD-MATH: pupil ring must fold by the rigid transform (got {pupil_center_folded.round(3)}, expected {expected.round(3)})")
    # a straight scene (no fold override) must not move the cone
    unfolded = LayoutPolylineDisplayMixin._mesh_with_world_transform(mesh, None)
    if not np.allclose(np.asarray(unfolded.points, dtype=float), points[:, :3], atol=1e-9):
        failures.append("FOLD-MATH: a None (unfolded) transform must leave the cone untouched")
    if not [f for f in failures if f.startswith("FOLD-MATH")]:
        notes.append(f"fold-math = pupil ring folds by the rigid transform ({np.linalg.norm(pupil_center_folded - pupil_center_straight):.1f}mm); unfolded = no-op")


def run_checks() -> "tuple[bool, list[str]]":
    failures: list[str] = []
    notes: list[str] = []
    for check in (_check_mechanism, _check_fold_math):
        try:
            check(failures, notes)
        except Exception as exc:
            failures.append(f"{check.__name__}: raised {type(exc).__name__}: {exc}")
    info = [n if "=" in n else n.replace(":", " =", 1) for n in notes]
    return (not failures), (failures + info)


def run() -> int:
    passed, notes = run_checks()
    print("=== validate_open3d_accept_cone_fold_aware (bugs/0416) ===")
    for note in notes:
        print(f"  {'ok ' if '=' in note else 'XX '} {note}")
    if not passed:
        n = len([x for x in notes if "=" not in x])
        print(f"\n{n} failure(s).")
        return 1
    print("\nAll accept-cone fold-aware checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
