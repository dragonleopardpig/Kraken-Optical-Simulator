"""Diagnostic: does the 3D STEP export place the camera/lens CAD where the 3D display shows them?

The AZ85 RA-mirror scene is a two-prism folded periscope. In the live inspector the
camera-body CAD and lens-barrel CAD are FOLDED into world position (camera off the axis
after prism2, lens barrel in the horizontal leg). The STEP export, however, aligns those
overlays to the STRAIGHT +Z axis via ``_step_alignment_affine`` and never applies the fold
transform the display applies (``_optical_axis_fold_world_transform_for_row``), so the
exported CAD floats away disconnected from the folded rays (attachment/STEP.png).

This prints, for camera + lens: the DISPLAY final folded-mesh centroid vs the EXPORT
affine-applied centroid, and their delta. A large delta == the reported bug.

Run: .devenv/state/venv/bin/python bugs/diag_step_export_fold.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from KrakenOS.UI.layout_editor import KrakenLayoutEditor
from KrakenOS.UI.validate_open3d_five_penta_initial_visual import _load_saved_layout

LAYOUT = Path("attachment/machine_vision_AZ85_RA_Mirror.py")


def _centroid(mesh) -> np.ndarray:
    pts = np.asarray(mesh.points, dtype=float)
    return pts.mean(axis=0)


def _export_centroid(app, label: str) -> tuple[np.ndarray, np.ndarray] | None:
    params = app._step_export_alignment_params(label)
    if params is None:
        return None
    source_mesh = app._load_step_mesh(Path(params["path"]), largest_component=bool(params.get("largest_component", False)))
    matrix = app._step_alignment_affine(params)
    if matrix is None:
        return None
    src = np.asarray(source_mesh.points, dtype=float)
    homo = np.column_stack([src, np.ones(src.shape[0])])
    placed = (np.asarray(matrix, dtype=float) @ homo.T).T[:, :3]
    return placed.mean(axis=0), placed


def main() -> int:
    app = KrakenLayoutEditor(headless=True)
    _load_saved_layout(app, LAYOUT)
    app.build_system()

    print(f"camera_step_path = {app.imported_camera_step_path}")
    print(f"lens_step_path   = {app.imported_lens_step_path}")

    for label, display_builder, row_fn in (
        ("camera", app._transformed_imported_camera_step_mesh, app._image_plane_row_index),
        ("lens", app._transformed_imported_lens_step_mesh, app._lens_front_datum_row_index),
    ):
        print(f"\n=== {label} ===")
        fold = app._optical_axis_fold_world_transform_for_row(row_fn())
        print(f"anchor row = {row_fn()}  fold_transform available = {fold is not None}")
        disp = display_builder()
        exported = _export_centroid(app, label)
        if disp is None or exported is None:
            print(f"  MISSING display={disp is not None} export={exported is not None}")
            continue
        disp_c = _centroid(disp)
        exp_c, _ = exported
        delta = float(np.linalg.norm(disp_c - exp_c))
        print(f"  DISPLAY centroid (folded)   = {np.round(disp_c, 3).tolist()}")
        print(f"  EXPORT  centroid (no fold)  = {np.round(exp_c, 3).tolist()}")
        print(f"  DELTA |display - export|    = {delta:.3f} mm  {'<-- MISMATCH' if delta > 1.0 else 'ok'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
